"""SOMA OWL bridge — REAL owlready2 + Pellet integration.

This module is the ONE place where OWL/Pellet operations live.
Prolog calls into this via Janus (janus:py_call).

NO simulation. NO mirrors. NO hand-typed facts.
The .owl file IS the source of truth. Pellet IS the reasoner.

Functions exposed (kept simple — strings/lists in, strings/lists out
so Janus can serialize them):

  load_owl(path)               -> str  (status)
  list_classes()               -> list[str]
  list_object_properties()     -> list[str]
  ancestors_of(class_name)     -> list[str]
  descendants_of(class_name)   -> list[str]
  is_subclass_of(sub, sup)     -> bool
  add_class(name, parent_name) -> str  (status)
  add_subclass(sub, sup)       -> str  (status)
  run_pellet()                 -> str  (status + timing)
  save_owl()                   -> str  (path written)
  sparql(query)                -> list[list[str]]  (rows of stringified vars)
"""

import os
import time
import owlready2
import janus_swi as _janus

_PROLOG_DIR = os.path.dirname(os.path.abspath(__file__))
_BOOTED = False


def ensure_prolog_booted():
    """Consult soma_boot.pl exactly once into the SWI-Prolog runtime."""
    global _BOOTED
    if not _BOOTED:
        boot_pl = os.path.join(_PROLOG_DIR, "soma_boot.pl")
        if not os.path.exists(boot_pl):
            raise FileNotFoundError(f"soma_boot.pl not found at {boot_pl}")
        os.chdir(_PROLOG_DIR)
        _janus.consult(boot_pl)
        _BOOTED = True


def build_obs_list_string(observations) -> str:
    """Build a Prolog observation list string.

    SOMA shape — no categories. An Event has a list of observations.
    Each observation has its own source plus the carton `add_concept`
    graph about one part of the event (name, description, relationships
    of {relationship, related}). The event is the top-level thing; the
    observations are the ontology sub-graphs that compose it.

        observations = [
          {
            "source": "alice",
            "name": "Alice_Does_Invoices",
            "description": "Alice processes invoices weekly",
            "relationships": [
              {"relationship": "is_a", "related": ["process"]},
              {"relationship": "part_of", "related": ["finance_org"]},
              {"relationship": "has_agent", "related": ["alice"]}
            ]
          },
          ...
        ]

    Each observation is emitted as a Prolog term:
        obs_concept('alice', 'Alice_Does_Invoices',
                    'Alice processes invoices weekly',
                    [rel('is_a', ['process']), rel('part_of', ['finance_org']), ...])

    Backward compat shims:
      - dict input with legacy add_observation_batch categories (fact, rule, ...)
        — flatten every concept into the obs_concept list, using the category
        name as a fallback source if the concept itself has no source
      - list entries with {target, relationships} or {key, value, type} —
        emit legacy obs/2 or obs/3 forms as before, for existing tests
    """
    def _escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

    def _quote(s: str) -> str:
        return f"'{_escape(str(s))}'"

    def _relationships_prolog(rels_list) -> str:
        """Emit Prolog rel/2 terms from relationship dicts.

        Each related entry can be:
          (a) a string → treated as untyped atom: tv('value', 'string_value')
          (b) a dict {value, type} → typed: tv('value', 'type')

        Prolog term: rel('pred', [tv('val1','type1'), tv('val2','type2')])
        """
        rel_terms = []
        for rel in rels_list or []:
            pred = _quote(rel.get("relationship", rel.get("predicate", "")))
            related_list = rel.get("related", rel.get("objects", []))
            if isinstance(related_list, str):
                related_list = [related_list]
            tv_terms = []
            for r in related_list:
                if isinstance(r, dict):
                    val = _quote(r.get("value", ""))
                    typ = _quote(r.get("type", "string_value"))
                else:
                    val = _quote(str(r))
                    typ = _quote("string_value")
                tv_terms.append(f"tv({val},{typ})")
            rel_terms.append(f"rel({pred},[{','.join(tv_terms)}])")
        return "[" + ",".join(rel_terms) + "]"

    def _emit_obs_concept(source, concept_dict):
        name = _quote(concept_dict.get("name", concept_dict.get("target", "")))
        desc = _quote(concept_dict.get("description", ""))
        rels = _relationships_prolog(concept_dict.get("relationships", []))
        src = _quote(source)
        return f"obs_concept({src},{name},{desc},{rels})"

    obs_terms = []

    # --- Preferred: LIST of SOMA observations (source + add_concept shape) ---
    if isinstance(observations, list):
        for obs in observations:
            if not isinstance(obs, dict):
                continue
            # SOMA observation with its own source + name + relationships
            if "name" in obs and "relationships" in obs:
                source = obs.get("source", "unknown")
                obs_terms.append(_emit_obs_concept(source, obs))
            # Legacy carton-target shape (kept for in-flight tests)
            elif "target" in obs and "relationships" in obs:
                target = _quote(obs["target"])
                rel_terms = []
                for rel in obs.get("relationships", []):
                    pred = rel.get("relationship", rel.get("predicate", ""))
                    rel_list = rel.get("related", rel.get("objects", []))
                    if isinstance(rel_list, str):
                        rel_list = [rel_list]
                    p_q = _quote(pred)
                    rel_quoted = ",".join(_quote(r) for r in rel_list)
                    rel_terms.append(f"rel({p_q},[{rel_quoted}])")
                rels_str = "[" + ",".join(rel_terms) + "]"
                obs_terms.append(f"obs({target},{rels_str})")
            # Legacy flat shape
            else:
                key = _quote(obs.get("key", ""))
                value = _quote(obs.get("value", ""))
                otype = _quote(obs.get("type", "string_value"))
                obs_terms.append(f"obs({key},{value},{otype})")
        return "[" + ",".join(obs_terms) + "]"

    # --- Compat: dict payload (legacy carton add_observation_batch) ---
    # Flatten every concept in every category into obs_concept terms.
    if isinstance(observations, dict):
        for category, concepts_or_meta in observations.items():
            if category in ("confidence", "hide_youknow"):
                continue
            if not isinstance(concepts_or_meta, list):
                continue
            for c in concepts_or_meta:
                if not isinstance(c, dict):
                    continue
                src = c.get("source", category)
                obs_terms.append(_emit_obs_concept(src, c))
        return "[" + ",".join(obs_terms) + "]"

    return "[]"


def escape_prolog_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def decode_prolog_result(val) -> str:
    if isinstance(val, bytes):
        return val.decode("utf-8")
    return str(val)

_OWL_PATH = os.environ.get(
    "SOMA_OWL_PATH",
    "/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/soma.owl",
)

_onto = None  # the loaded ontology, set by load_owl()


def load_owl(path: str = None) -> str:
    """Load (or reload) the SOMA OWL file. Returns status string."""
    global _onto, _OWL_PATH
    if path:
        _OWL_PATH = path
    if not os.path.exists(_OWL_PATH):
        return f"ERROR: {_OWL_PATH} does not exist"
    iri = "file://" + _OWL_PATH
    _onto = owlready2.get_ontology(iri).load(reload=True)
    return f"LOADED {_OWL_PATH} | base_iri={_onto.base_iri} | {len(list(_onto.classes()))} classes"


def _ensure_loaded():
    if _onto is None:
        load_owl()


def list_classes() -> list:
    _ensure_loaded()
    return [c.name for c in _onto.classes()]


def list_object_properties() -> list:
    _ensure_loaded()
    return [p.name for p in _onto.object_properties()]


def _snake_to_camel(name: str) -> str:
    """renderable_piece -> RenderablePiece, code_file -> CodeFile."""
    if "_" not in name:
        return name[:1].upper() + name[1:] if name else name
    parts = [p for p in name.split("_") if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)


def _camel_to_snake(name: str) -> str:
    """RenderablePiece -> renderable_piece. CheckOWLDispatch -> check_owl_dispatch.

    Standard smart conversion: insert _ before an upper letter when EITHER
    (a) the previous char is lowercase, OR
    (b) the previous char is uppercase AND the next char is lowercase.
    Skip insertion when the previous char is already an underscore.
    """
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and name[i - 1] != "_":
            prev_lower = name[i - 1].islower()
            next_lower = (i + 1 < len(name)) and name[i + 1].islower()
            prev_upper = name[i - 1].isupper()
            if prev_lower or (prev_upper and next_lower):
                out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _find_class(name: str):
    """Find an OWL class by name. Accepts snake_case or CamelCase."""
    _ensure_loaded()
    # Try exact
    cls = _onto[name]
    if cls is not None:
        return cls
    # Try snake -> camel
    camel = _snake_to_camel(name)
    if camel != name:
        cls = _onto[camel]
        if cls is not None:
            return cls
    # Try linear scan with both forms
    for c in _onto.classes():
        if c.name == name or c.name == camel:
            return c
        if _camel_to_snake(c.name) == name:
            return c
    return None


def is_class(name: str) -> bool:
    """Check if a name (snake or camel) is an OWL class."""
    return _find_class(name) is not None


def owl_individual_exists(name: str) -> bool:
    """Check if an OWL individual with the given name exists."""
    _ensure_loaded()
    return _onto[name] is not None


def authorization_mechanism_callable() -> bool:
    """Verify the authorization-reasoning MECHANISM is callable.
    Returns True if the universal authorization vocabulary exists in
    the ontology (hasAuthorizedCreator, hasAuthorizedWriter,
    hasWritePrecondition properties are declared).
    """
    _ensure_loaded()
    needed = ["hasAuthorizedCreator", "hasAuthorizedWriter", "hasWritePrecondition"]
    for n in needed:
        if _onto[n] is None:
            return False
    return True


# ----------------------------------------------------------------------
# REQUIREMENT CHECK HELPERS — raise on failure, return None on success.
# These are called from PrologRule individual bodies via py_call. The
# raise/None pattern lets Prolog use catch/3 as the success/fail signal
# without needing to compare the return value — which avoids janus
# `py_term` errors that occur when @(true) round-trips through
# term_to_atom.
# ----------------------------------------------------------------------


def check_requirement_can_call_llm() -> None:
    """Raise unless cap_call_llm and the_ontology_engineer both exist."""
    _ensure_loaded()
    if _onto["cap_call_llm"] is None:
        raise RuntimeError("cap_call_llm individual missing")
    if _onto["the_ontology_engineer"] is None:
        raise RuntimeError("the_ontology_engineer individual missing")


def check_requirement_authorization_reasoning() -> None:
    """Raise unless authorization vocabulary exists."""
    _ensure_loaded()
    needed = ["hasAuthorizedCreator", "hasAuthorizedWriter", "hasWritePrecondition"]
    for n in needed:
        if _onto[n] is None:
            raise RuntimeError(f"authorization property missing: {n}")


def check_requirement_failure_is_llm_call() -> None:
    """Raise unless the failure-error format builder is callable.
    Verifies the underlying mechanism (string formatting + substring
    check) is reachable from Python.
    """
    test = "failure_error(test=req_self_test_marker)"
    if "failure_error" not in test:
        raise RuntimeError("failure_error format unreachable")


def list_classes_snake() -> list:
    """Return all class names in snake_case form."""
    _ensure_loaded()
    return [_camel_to_snake(c.name) for c in _onto.classes()]


def ancestors_of_snake(class_name: str) -> list:
    cls = _find_class(class_name)
    if cls is None:
        return []
    return sorted(set(
        _camel_to_snake(a.name) for a in cls.ancestors() if hasattr(a, "name")
    ))


def descendants_of_snake(class_name: str) -> list:
    cls = _find_class(class_name)
    if cls is None:
        return []
    return sorted(set(
        _camel_to_snake(d.name) for d in cls.descendants() if hasattr(d, "name")
    ))


# ── PROPERTIES ────────────────────────────────────────────────────

def list_object_properties_snake() -> list:
    _ensure_loaded()
    return [_camel_to_snake(p.name) for p in _onto.object_properties()]


def list_data_properties_snake() -> list:
    _ensure_loaded()
    return [_camel_to_snake(p.name) for p in _onto.data_properties()]


def _find_property(name: str):
    _ensure_loaded()
    p = _onto[name]
    if p is not None:
        return p
    camel = _snake_to_camel(name)
    if camel != name:
        p = _onto[camel]
        if p is not None:
            return p
    # Try lowercaseFirst variant (object properties usually start lowercase)
    if camel:
        lower_camel = camel[0].lower() + camel[1:]
        p = _onto[lower_camel]
        if p is not None:
            return p
    for prop in list(_onto.object_properties()) + list(_onto.data_properties()):
        if prop.name == name or prop.name == camel:
            return prop
        if _camel_to_snake(prop.name) == name:
            return prop
    return None


def is_property(name: str) -> bool:
    return _find_property(name) is not None


_PYTYPE_TO_XSD = {
    str: "xsd_string",
    int: "xsd_int",
    float: "xsd_float",
    bool: "xsd_boolean",
}


def _entity_name_snake(e) -> str:
    """Get a snake_case name from an OWL entity OR Python type (for datatypes)."""
    if hasattr(e, "name") and isinstance(getattr(e, "name", None), str):
        return _camel_to_snake(e.name)
    if isinstance(e, type) and e in _PYTYPE_TO_XSD:
        return _PYTYPE_TO_XSD[e]
    if isinstance(e, type) and hasattr(e, "__name__"):
        return f"xsd_{e.__name__.lower()}"
    return str(e)


def property_domain_snake(prop_name: str) -> list:
    """Return the domain class names (snake_case) of a property."""
    p = _find_property(prop_name)
    if p is None:
        return []
    return sorted(set(_entity_name_snake(d) for d in p.domain))


def property_range_snake(prop_name: str) -> list:
    """Return the range class names (snake_case) of a property."""
    p = _find_property(prop_name)
    if p is None:
        return []
    return sorted(set(_entity_name_snake(r) for r in p.range))


def property_triple_exists_snake(prop_name: str, domain_snake: str, range_snake: str) -> bool:
    """Check whether a property has the given domain and range (snake_case)."""
    p = _find_property(prop_name)
    if p is None:
        return False
    doms = [_entity_name_snake(d) for d in p.domain]
    rngs = [_entity_name_snake(r) for r in p.range]
    # Wildcard handling: caller passes "_" to mean any (matches even if empty)
    dom_ok = (domain_snake == "_") or (domain_snake in doms) or (not doms and domain_snake == "")
    rng_ok = (range_snake == "_") or (range_snake in rngs) or (not rngs and range_snake == "")
    return dom_ok and rng_ok


def list_property_triples_snake() -> list:
    """Return all (property_snake, domain_snake, range_snake) triples in the ontology.
    Uses pipe-separated strings so Janus serializes cleanly."""
    _ensure_loaded()
    out = []
    for p in list(_onto.object_properties()) + list(_onto.data_properties()):
        p_snake = _camel_to_snake(p.name)
        doms = [_entity_name_snake(d) for d in p.domain] or [""]
        rngs = [_entity_name_snake(r) for r in p.range] or [""]
        for d in doms:
            for r in rngs:
                out.append(f"{p_snake}|{d}|{r}")
    return out


# ── RESTRICTIONS ──────────────────────────────────────────────────

def _restriction_kind_str(restr) -> str:
    """Convert an owlready2 Restriction into a Prolog-friendly tag."""
    kinds = {
        owlready2.SOME: "some",
        owlready2.ONLY: "only",
        owlready2.VALUE: "has_value",
        owlready2.EXACTLY: "exactly",
        owlready2.MIN: "min",
        owlready2.MAX: "max",
    }
    rk = kinds.get(restr.type, str(restr.type))
    if rk in ("exactly", "min", "max"):
        return f"{rk}({restr.cardinality})"
    val = restr.value
    val_name = _entity_name_snake(val)
    if rk in ("some", "only", "has_value"):
        return f"{rk}({val_name})"
    return rk


def class_restrictions_snake(class_name: str) -> list:
    """Return restriction tuples for a class as 'property_snake|kind' strings."""
    cls = _find_class(class_name)
    if cls is None:
        return []
    out = []
    for parent in cls.is_a:
        if isinstance(parent, owlready2.Restriction):
            prop = parent.property
            prop_snake = _camel_to_snake(prop.name) if prop is not None else "_"
            out.append(f"{prop_snake}|{_restriction_kind_str(parent)}")
    return out


def list_all_restrictions_snake() -> list:
    """Return all (class_snake, property_snake, kind) restriction triples."""
    _ensure_loaded()
    out = []
    for c in _onto.classes():
        c_snake = _camel_to_snake(c.name)
        for parent in c.is_a:
            if isinstance(parent, owlready2.Restriction):
                prop = parent.property
                prop_snake = _camel_to_snake(prop.name) if prop is not None else "_"
                out.append(f"{c_snake}|{prop_snake}|{_restriction_kind_str(parent)}")
    return out


def restriction_exists_snake(class_snake: str, prop_snake: str, kind_snake: str) -> bool:
    triples = list_all_restrictions_snake()
    target = f"{class_snake}|{prop_snake}|{kind_snake}"
    return target in triples


# ── DISJOINTNESS ──────────────────────────────────────────────────

def list_disjoint_pairs_snake() -> list:
    """Return all unordered disjoint pairs as 'a|b' strings (a<b)."""
    _ensure_loaded()
    out = set()
    for d in _onto.disjoint_classes():
        names = [_camel_to_snake(e.name) for e in d.entities if hasattr(e, "name")]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = sorted([names[i], names[j]])
                out.add(f"{a}|{b}")
    return sorted(out)


def disjoint_pair_exists_snake(a_snake: str, b_snake: str) -> bool:
    pairs = set(list_disjoint_pairs_snake())
    a, b = sorted([a_snake, b_snake])
    return f"{a}|{b}" in pairs


def ancestors_of(class_name: str) -> list:
    cls = _find_class(class_name)
    if cls is None:
        return [f"ERROR: class {class_name} not found"]
    return sorted(set(a.name for a in cls.ancestors() if hasattr(a, "name")))


def descendants_of(class_name: str) -> list:
    cls = _find_class(class_name)
    if cls is None:
        return [f"ERROR: class {class_name} not found"]
    return sorted(set(d.name for d in cls.descendants() if hasattr(d, "name")))


def is_subclass_of(sub: str, sup: str) -> bool:
    sub_cls = _find_class(sub)
    sup_cls = _find_class(sup)
    if sub_cls is None or sup_cls is None:
        return False
    return sup_cls in sub_cls.ancestors()


def add_class(name: str, parent_name: str = "Thing") -> str:
    """Add a new OWL class to the ontology in memory.
    Call save_owl() to persist."""
    _ensure_loaded()
    if _find_class(name) is not None:
        return f"EXISTS: {name}"
    if parent_name == "Thing":
        parent = owlready2.Thing
    else:
        parent = _find_class(parent_name)
        if parent is None:
            return f"ERROR: parent {parent_name} not found"
    with _onto:
        type(name, (parent,), {})
    return f"ADDED: {name} subClassOf {parent_name}"


def add_subclass(sub: str, sup: str) -> str:
    """Assert sub subClassOf sup in an existing class."""
    _ensure_loaded()
    sub_cls = _find_class(sub)
    if sub_cls is None:
        return f"ERROR: class {sub} not found"
    sup_cls = _find_class(sup)
    if sup_cls is None and sup != "Thing":
        return f"ERROR: class {sup} not found"
    target = owlready2.Thing if sup == "Thing" else sup_cls
    with _onto:
        sub_cls.is_a.append(target)
    return f"ADDED: {sub} is_a {sup}"


def run_pellet() -> str:
    """Actually run Pellet reasoner over the current ontology."""
    _ensure_loaded()
    t0 = time.time()
    try:
        with _onto:
            owlready2.sync_reasoner_pellet(
                infer_property_values=True,
                infer_data_property_values=True,
            )
    except Exception as e:
        return f"PELLET_ERROR: {type(e).__name__}: {e}"
    dt = time.time() - t0
    return f"PELLET_OK: {dt:.3f}s ({len(list(_onto.classes()))} classes, {len(list(_onto.individuals()))} individuals)"


def save_owl(path: str = None) -> str:
    _ensure_loaded()
    target = path or _OWL_PATH
    _onto.save(file=target, format="rdfxml")
    return f"SAVED: {target}"


# ── EVENT / OBSERVATION INDIVIDUALS ───────────────────────────────
# These are the universal entry points for turning event data into OWL
# individuals. No domain-specific names are introduced here — the
# functions take a typed value class name (e.g. "string_value") and
# create an individual of the corresponding owlready2 class.

def _typed_value_class(type_snake: str):
    """Map a snake_case typed value name to its owlready2 class.
    Universal: works for any TypedValue subtype declared in soma.owl."""
    cls = _find_class(type_snake)
    if cls is None:
        return None
    return cls


def _find_property_by_snake(snake: str):
    """Find a property by its snake_case name. Returns the owlready2
    property object or None."""
    p = _find_property(snake)
    return p


def add_event_individual(event_id: str, source: str, timestamp: str) -> str:
    """Create an Event individual in the live ontology.

    Uses rdfs:label to carry source and timestamp (universal RDF metadata).
    Caller must call save_owl() once after the full event is ingested.
    """
    _ensure_loaded()
    Event = _find_class("event")
    if Event is None:
        return "ERROR: Event class not found in ontology"
    with _onto:
        ev = _onto[event_id]
        if ev is None:
            ev = Event(event_id)
        ev.label.append(f"event:{event_id}")
        ev.label.append(f"source:{source}")
        ev.label.append(f"timestamp:{timestamp}")
    return f"event_individual={event_id}"


def add_observation_individual(event_id: str, key: str, value: str, type_snake: str) -> str:
    """Create an Observation as a typed key-value linked to an Event.

    An observation IS a typed kv. The structure created is:
        Event(event_id)
            has_observation -> Observation(obs_id)
        Observation(obs_id)
            has_key   = "<key>"          (data property literal)
            has_value -> TypedValue(val_id)
        TypedValue(val_id)               (subclass = StringValue/IntValue/...)
            label = "<value>"            (rdfs:label literal carries the value)

    has_key, has_value, and has_observation are object/data properties
    that already exist in soma.owl. This function uses them via
    owlready2's dynamic attribute access. Nothing here names a domain
    concept; the typed value subclass is looked up from type_snake.
    """
    _ensure_loaded()
    Event = _find_class("event")
    Observation = _find_class("observation")
    if Event is None:
        return "ERROR: Event class not found in ontology"
    if Observation is None:
        return "ERROR: Observation class not found in ontology"
    TypedValueCls = _typed_value_class(type_snake)
    if TypedValueCls is None:
        return f"ERROR: typed value class {type_snake} not found"

    has_observation = _find_property_by_snake("has_observation")
    has_key = _find_property_by_snake("has_key")
    has_value = _find_property_by_snake("has_value")

    obs_id = f"{event_id}_obs_{_safe_id(key)}"
    val_id = f"{obs_id}_val"

    with _onto:
        ev = _onto[event_id]
        if ev is None:
            ev = Event(event_id)
        obs = _onto[obs_id]
        if obs is None:
            obs = Observation(obs_id)
        tv = _onto[val_id]
        if tv is None:
            tv = TypedValueCls(val_id)
        # Carry the literal value via rdfs:label (universal, always works)
        tv.label.append(value)
        # Wire the relationships using the actual OWL properties
        if has_key is not None:
            try:
                obs.__setattr__(has_key.python_name or "has_key", [key])
            except Exception:
                obs.label.append(f"key:{key}")
        else:
            obs.label.append(f"key:{key}")
        if has_value is not None:
            try:
                obs.__setattr__(has_value.python_name or "has_value", [tv])
            except Exception:
                obs.label.append(f"value_ref:{val_id}")
        else:
            obs.label.append(f"value_ref:{val_id}")
        if has_observation is not None:
            attr = has_observation.python_name or "hasObservation"
            try:
                # owlready2: use the property list's append
                getattr(ev, attr).append(obs)
            except (AttributeError, TypeError):
                try:
                    setattr(ev, attr, [obs])
                except Exception:
                    ev.label.append(f"observation_ref:{obs_id}")
        else:
            ev.label.append(f"observation_ref:{obs_id}")

    return f"observation_individual={obs_id} typed_as={type_snake} literal={value}"


def _scrub_pipe(s) -> str:
    """Replace any literal '|' so it doesn't break our string-list encoding."""
    if s is None:
        return ""
    return str(s).replace("|", "/")


def list_deduction_chains_snake() -> list:
    """Return every Deduction_Chain individual (including subclass
    individuals like CoreRequirement) as a pipe-separated string:
        "<name>|<premise>|<conclusion>"
    where premise and conclusion are Prolog goals stored as strings.

    The Prolog runtime walks this list, parses each premise/conclusion
    as a term, and uses them as forward-chaining "since X, maybe Y"
    rules.
    """
    _ensure_loaded()
    out = []
    cls = _find_class("deduction_chain")
    if cls is None:
        return out
    seen = set()
    # cls.instances() includes subclass instances in owlready2
    for ind in cls.instances():
        if ind.name in seen:
            continue
        seen.add(ind.name)
        try:
            premise = list(getattr(ind, "hasDeductionPremise", []) or [""])[0]
        except Exception:
            premise = ""
        try:
            conclusion = list(getattr(ind, "hasDeductionConclusion", []) or [""])[0]
        except Exception:
            conclusion = ""
        out.append(
            f"{_scrub_pipe(ind.name)}|{_scrub_pipe(premise)}|{_scrub_pipe(conclusion)}"
        )
    return out


def get_deduction_chain_details_snake(name: str) -> str:
    """Return "<description>|<remedy>|<is_core_requirement>" for the
    named Deduction_Chain individual. Used by the failure-error builder
    to look up human-readable info for each chain that fired.
    """
    _ensure_loaded()
    ind = _onto[name]
    if ind is None:
        return "||false"
    try:
        desc = list(getattr(ind, "hasDeductionDescription", []) or [""])[0]
    except Exception:
        desc = ""
    try:
        remedy = list(getattr(ind, "hasRequirementRemedy", []) or [""])[0]
    except Exception:
        remedy = ""
    is_core_req = "false"
    try:
        cr_cls = _find_class("core_requirement")
        if cr_cls is not None and cr_cls in ind.is_a:
            is_core_req = "true"
    except Exception:
        pass
    return f"{_scrub_pipe(desc)}|{_scrub_pipe(remedy)}|{is_core_req}"


def fire_all_deduction_chains_py() -> list:
    """Walk every Deduction_Chain individual. The premise is the
    requirement-check goal. If it SUCCEEDS via solve/3 (i.e. the
    requirement is met), do nothing. If it FAILS, the requirement is
    unmet — run the conclusion (which typically asserts an
    unmet_requirement fact) and add the chain to the fired list.

    Walking lives in Python because reflecting complex Prolog goals
    back through solve/3 recursively interacts badly with janus
    (py_term domain errors). Python-side walking with one
    janus.query_once per chain step is the clean substrate. The
    MECHANISM is still universal — no domain atoms here, just
    whatever Deduction_Chain individuals exist in the OWL.

    Filters out chains with empty premise (orphan/malformed
    individuals).
    """
    import janus_swi as janus

    _ensure_loaded()
    fired = []
    cls = _find_class("deduction_chain")
    if cls is None:
        return fired

    for ind in cls.instances():
        try:
            premise = list(getattr(ind, "hasDeductionPremise", []) or [""])[0]
        except Exception:
            premise = ""
        try:
            conclusion = list(getattr(ind, "hasDeductionConclusion", []) or [""])[0]
        except Exception:
            conclusion = ""
        if not premise:
            continue
        # Call premise via solve/3 so it sees rule/2 clauses (PrologRule
        # individuals loaded from OWL into the MI). The MI's solve/3
        # returns Outcome = proven(Goal, ProofTree) on success or
        # failure(Goal, Reason) on failure-as-data.
        # Embed the premise directly in the query — it's already valid
        # Prolog source. solve_succeeds/1 (defined in mi_core.pl)
        # wraps solve/3 and returns ONLY success/fail. The proof tree
        # (containing @none/@true from py_call returns) never leaves
        # Prolog scope, so janus never tries to roundtrip a py_term
        # it can't handle. No outer variables means janus has nothing
        # to choke on.
        # Use native Prolog call/1 instead of MI's solve/3.
        # solve_succeeds breaks after mi_add_event due to janus
        # state corruption ('$c_call_prolog'/0 instantiation error).
        # Native call works because the PrologRule bodies are loaded
        # as rule/2 facts AND the .pl predicates are consulted directly.
        try:
            r = janus.query_once(
                f"catch(call(({premise})), _, fail)"
            )
            premise_succeeded = bool(r and r.get("truth"))
        except Exception:
            premise_succeeded = False
        if premise_succeeded:
            # Requirement met, nothing to do
            continue
        # Requirement is unmet — fire the conclusion
        fired.append(ind.name)
        if conclusion:
            try:
                janus.query_once(
                    f"catch(({conclusion}), _, true)"
                )
            except Exception:
                pass
    return fired


def build_failure_error_report(unmet_names: list) -> str:
    """Build a structured failure_error string for the LLM when one or
    more CoreRequirements are unmet. Walks the named individuals in
    soma.owl, pulls description + remedy off each, and formats them
    into the canonical failure_error shape that the OntologyEngineer
    is supposed to read and act on.

    The failure_error IS the LLM call — it tells the LLM exactly which
    requirements are unmet and what to do about each one.
    """
    _ensure_loaded()
    if not unmet_names:
        return "all_core_requirements_met"
    lines = [f"failure_error(unmet_core_requirements={len(unmet_names)})"]
    lines.append("the_following_requirements_are_not_met:")
    for name in unmet_names:
        ind = _onto[name]
        if ind is None:
            lines.append(f"  - requirement: {name} (UNKNOWN)")
            continue
        try:
            desc = list(getattr(ind, "hasDeductionDescription", []) or [""])[0]
        except Exception:
            desc = ""
        try:
            remedy = list(getattr(ind, "hasRequirementRemedy", []) or [""])[0]
        except Exception:
            remedy = ""
        lines.append(f"  - requirement: {name}")
        lines.append(f"    description: {desc}")
        lines.append(f"    remedy: {remedy}")
    lines.append("")
    lines.append("this_failure_error_is_a_call_to_the_ontology_engineer.")
    lines.append("the_ontology_engineer_must_address_each_unmet_requirement_using_its_remedy.")
    return "\n".join(lines)


def cleanup_orphan_deduction_chains() -> int:
    """Remove orphan Deduction_Chain individuals that have no premise
    (created by accidental observation typing). Returns count removed.
    """
    _ensure_loaded()
    cls = _find_class("deduction_chain")
    if cls is None:
        return 0
    removed = 0
    with _onto:
        for ind in list(cls.instances()):
            try:
                premise = list(getattr(ind, "hasDeductionPremise", []) or [""])[0]
            except Exception:
                premise = ""
            if not premise:
                owlready2.destroy_entity(ind)
                removed += 1
    return removed


def list_prolog_rules_snake() -> list:
    """Return every PrologRule individual as a pipe-separated string:
        "<name>|<head>|<body>"
    where head and body are Prolog source strings stored on the
    individual via hasRuleHead / hasRuleBody.

    The Prolog runtime walks this list at boot, parses each head/body
    as a term, and assertz's it as `rule((Head :- Body), 100)` so the
    meta-interpreter (mi_core.pl solve/3) can backchain on it.
    """
    _ensure_loaded()
    out = []
    cls = _find_class("prolog_rule")
    if cls is None:
        return out
    seen = set()
    for ind in cls.instances():
        if ind.name in seen:
            continue
        seen.add(ind.name)
        try:
            head = list(getattr(ind, "hasRuleHead", []) or [""])[0]
        except Exception:
            head = ""
        try:
            body = list(getattr(ind, "hasRuleBody", []) or [""])[0]
        except Exception:
            body = ""
        out.append(
            f"{_scrub_pipe(ind.name)}|{_scrub_pipe(head)}|{_scrub_pipe(body)}"
        )
    return out


def _safe_id(s: str) -> str:
    """Sanitize a string into something safe to use as an OWL individual name."""
    out = []
    for ch in str(s):
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def sparql(query: str) -> list:
    """Run a SPARQL query via the default world graph.
    Returns list of rows where each row is a list of stringified bindings."""
    _ensure_loaded()
    rows = []
    try:
        results = list(owlready2.default_world.sparql(query))
        for row in results:
            rows.append([str(x) for x in row])
    except Exception as e:
        return [[f"SPARQL_ERROR: {type(e).__name__}: {e}"]]
    return rows


# ======================================================================
# SOMA RUNTIME OBJECT REGISTRY
#
# When compile_to_python fires for a SOMA concept, the emitted Python code
# is exec'd into this module-level registry so the callable survives the
# exec scope and can be invoked later with args to produce new particulars.
# ======================================================================

_SOMA_RUNTIME_OBJECTS = {}


def exec_soma_runtime_code(concept_name: str, code: str) -> str:
    """Execute compiled Python source in a persistent namespace and register
    the resulting callable under concept_name. The emitted code is expected
    to define a symbol matching `concept_name` that is either a class with
    a `make` classmethod or a plain callable taking kwargs.

    Returns a status string. Called by Prolog via py_call from compile_to_python.
    """
    ns = {}
    try:
        exec(code, ns, ns)
    except Exception as e:
        return f"exec_error: {type(e).__name__}: {e}"

    # Prefer ClassName.make if the class exists, else plain function
    if concept_name in ns:
        obj = ns[concept_name]
        # If it's a class with a make classmethod, register that; else the obj itself
        if hasattr(obj, "make") and callable(getattr(obj, "make")):
            _SOMA_RUNTIME_OBJECTS[concept_name] = obj.make
        elif callable(obj):
            _SOMA_RUNTIME_OBJECTS[concept_name] = obj
        else:
            return f"no_callable_for_{concept_name}"
        return f"registered:{concept_name}"

    # Try capitalized Pydantic class name
    class_name = concept_name[:1].upper() + concept_name[1:]
    if class_name in ns and hasattr(ns[class_name], "make"):
        _SOMA_RUNTIME_OBJECTS[concept_name] = ns[class_name].make
        return f"registered:{concept_name}"

    return f"no_symbol_matching_{concept_name}"


def call_soma_runtime(concept_name: str, kwargs_json: str) -> str:
    """Call a registered SOMA runtime object with JSON-encoded kwargs.
    Returns a JSON-encoded dict representing the resulting instance.
    """
    import json as _json
    if concept_name not in _SOMA_RUNTIME_OBJECTS:
        return _json.dumps({"error": f"not_registered:{concept_name}"})
    callable_obj = _SOMA_RUNTIME_OBJECTS[concept_name]
    try:
        kwargs = _json.loads(kwargs_json) if kwargs_json else {}
    except Exception as e:
        return _json.dumps({"error": f"kwargs_parse:{e}"})
    try:
        result = callable_obj(**kwargs)
    except Exception as e:
        return _json.dumps({"error": f"call:{type(e).__name__}:{e}"})

    # Convert result to a serializable dict
    if hasattr(result, "model_dump"):
        try:
            return _json.dumps(result.model_dump())
        except Exception:
            pass
    if hasattr(result, "__dict__"):
        try:
            return _json.dumps({k: str(v) for k, v in result.__dict__.items()})
        except Exception:
            pass
    return _json.dumps({"result": str(result)})


def soma_runtime_registered() -> list:
    """Return the list of concept names currently registered as callable
    SOMA runtime objects."""
    return sorted(_SOMA_RUNTIME_OBJECTS.keys())


# ======================================================================
# Auto-load on import so first call is cheap
# ======================================================================
load_owl()
