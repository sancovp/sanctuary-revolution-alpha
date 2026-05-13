"""
System Type Validator — OWL restriction-driven validation for known types.

Parses uarl.owl ONCE at import time, builds a dict of type restrictions.
Used by CartON's add_concept to validate system types (GIINT_*, Skill, Bug_, etc.)
WITHOUT calling youknow() per-relationship or querying Neo4j REQUIRES_RELATIONSHIP.

This replaces THREE parallel validation systems:
1. validate_giint_hierarchy() — hardcoded Python (DEPRECATED, commented out)
2. Neo4j REQUIRES_RELATIONSHIP queries — per-parent DB roundtrip (DEPRECATED, commented out)
3. youknow_validate() per-relationship loop — full compiler per rel (DEPRECATED for system types)

The OWL file IS the single source of truth for system type shapes.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# OWL/RDF namespaces
OWL_NS = "http://www.w3.org/2002/07/owl#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"


@dataclass
class TypeRestriction:
    """A single OWL restriction on a type."""
    property_name: str          # e.g. "partOf", "hasDomain"
    restriction_type: str       # "someValuesFrom" or "minCardinality"
    target_type: Optional[str] = None   # For someValuesFrom: the required range type
    min_count: Optional[int] = None     # For minCardinality: minimum count


@dataclass
class SystemTypeShape:
    """The complete shape (set of restrictions) for a system type."""
    type_name: str
    parent_type: Optional[str] = None  # rdfs:subClassOf (direct class, not restrictions)
    restrictions: List[TypeRestriction] = field(default_factory=list)

    def required_relationships(self) -> Dict[str, str]:
        """Get map of required relationship -> required target type (someValuesFrom only)."""
        result = {}
        for r in self.restrictions:
            if r.restriction_type == "someValuesFrom" and r.target_type:
                result[r.property_name] = r.target_type
        return result

    def required_cardinalities(self) -> Dict[str, int]:
        """Get map of required relationship -> min count (minCardinality only)."""
        result = {}
        for r in self.restrictions:
            if r.restriction_type == "minCardinality" and r.min_count is not None:
                result[r.property_name] = r.min_count
        return result


# ──────────────────────────────────────────────────────────────
# OWL Parser — runs ONCE at module load
# ──────────────────────────────────────────────────────────────

def _strip_ns(uri: str) -> str:
    """Strip namespace/fragment from URI, return local name."""
    if "#" in uri:
        return uri.split("#")[-1]
    if "/" in uri:
        return uri.split("/")[-1]
    return uri


def _parse_owl_restrictions(owl_path: str) -> Dict[str, SystemTypeShape]:
    """
    Parse OWL file and extract all class restrictions.

    Returns dict of {type_name: SystemTypeShape} for all owl:Class entries
    that have restrictions defined.
    """
    shapes: Dict[str, SystemTypeShape] = {}

    try:
        tree = ET.parse(owl_path)
        root = tree.getroot()
    except Exception as e:
        logger.error(f"Failed to parse OWL file {owl_path}: {e}")
        return shapes

    # Find all owl:Class elements
    for cls_elem in root.iter(f"{{{OWL_NS}}}Class"):
        about = cls_elem.get(f"{{{RDF_NS}}}about")
        if not about:
            continue

        type_name = _strip_ns(about)
        shape = SystemTypeShape(type_name=type_name)

        # Walk subClassOf elements
        for subclass_of in cls_elem.iter(f"{{{RDFS_NS}}}subClassOf"):
            # Direct parent class (no restriction, just rdf:resource)
            resource = subclass_of.get(f"{{{RDF_NS}}}resource")
            if resource:
                parent = _strip_ns(resource)
                if parent != "Thing":  # Skip owl:Thing
                    shape.parent_type = parent
                continue

            # OWL Restriction
            for restriction in subclass_of.iter(f"{{{OWL_NS}}}Restriction"):
                prop_elem = restriction.find(f"{{{OWL_NS}}}onProperty")
                if prop_elem is None:
                    continue
                prop_ref = prop_elem.get(f"{{{RDF_NS}}}resource")
                if not prop_ref:
                    continue
                prop_name = _strip_ns(prop_ref)

                # Check for someValuesFrom
                svf = restriction.find(f"{{{OWL_NS}}}someValuesFrom")
                if svf is not None:
                    target_ref = svf.get(f"{{{RDF_NS}}}resource")
                    if target_ref:
                        target_type = _strip_ns(target_ref)
                        shape.restrictions.append(TypeRestriction(
                            property_name=prop_name,
                            restriction_type="someValuesFrom",
                            target_type=target_type,
                        ))

                # Check for minCardinality
                mc = restriction.find(f"{{{OWL_NS}}}minCardinality")
                if mc is not None and mc.text:
                    try:
                        min_count = int(mc.text)
                        shape.restrictions.append(TypeRestriction(
                            property_name=prop_name,
                            restriction_type="minCardinality",
                            min_count=min_count,
                        ))
                    except ValueError:
                        pass

        if shape.restrictions:
            shapes[type_name] = shape

    return shapes


# ──────────────────────────────────────────────────────────────
# Module-level cache — loaded ONCE
# ──────────────────────────────────────────────────────────────

_OWL_PATH = str(Path(__file__).parent / "uarl.owl")
_STARSYSTEM_OWL_PATH = str(Path(__file__).parent / "starsystem.owl")
_SYSTEM_TYPE_SHAPES: Optional[Dict[str, SystemTypeShape]] = None

# UARLValidator singleton — used by d-chains to query canonical individuals in domain.owl.
# Lazy: only loaded when a d-chain actually needs OWL access. Returns None on import error
# (owlready2/rdflib missing), in which case d-chains that need OWL FAIL instead of silent-skip.
_uarl_validator_instance = None
_uarl_validator_tried = False

def _get_uarl_validator():
    """Get or create the UARLValidator singleton for OWL individual queries."""
    global _uarl_validator_instance, _uarl_validator_tried
    if _uarl_validator_tried:
        return _uarl_validator_instance
    _uarl_validator_tried = True
    try:
        from .uarl_validator import UARLValidator
        _uarl_validator_instance = UARLValidator()
    except Exception as e:
        logger.warning("UARLValidator unavailable: %s", e)
        _uarl_validator_instance = None
    return _uarl_validator_instance


def get_system_type_shapes() -> Dict[str, SystemTypeShape]:
    """Get cached system type shapes (parsed from BOTH uarl.owl AND starsystem.owl)."""
    global _SYSTEM_TYPE_SHAPES
    if _SYSTEM_TYPE_SHAPES is None:
        _SYSTEM_TYPE_SHAPES = _parse_owl_restrictions(_OWL_PATH)
        uarl_count = len(_SYSTEM_TYPE_SHAPES)
        if Path(_STARSYSTEM_OWL_PATH).exists():
            starsystem_shapes = _parse_owl_restrictions(_STARSYSTEM_OWL_PATH)
            _SYSTEM_TYPE_SHAPES.update(starsystem_shapes)
            logger.info(f"[SystemTypeValidator] Loaded {uarl_count} from uarl.owl + {len(starsystem_shapes)} from starsystem.owl = {len(_SYSTEM_TYPE_SHAPES)} total")
        else:
            logger.info(f"[SystemTypeValidator] Loaded {uarl_count} type shapes from {_OWL_PATH} (starsystem.owl not found)")
    return _SYSTEM_TYPE_SHAPES


def get_known_system_types() -> Set[str]:
    """Get set of all type names that have OWL restrictions."""
    return set(get_system_type_shapes().keys())


# ──────────────────────────────────────────────────────────────
# OWL property name → CartON relationship name mapping
# ──────────────────────────────────────────────────────────────

# OWL convention is camelCase property names (hasName, hasScope, isA). CartON
# stores relationships in snake_case (has_name, has_scope, is_a). The conversion
# is purely structural — no hand-maintained map. Any new OWL property added in
# any domain ontology works without code changes.
#
# Aliases (intentional shortenings) live in _OWL_TO_CARTON_ALIAS. Only one exists:
# hasModelPref → has_model (the Claude Code skill frontmatter uses "model", not
# "model_pref", so the carton-side rel name was shortened).

_OWL_TO_CARTON_ALIAS = {
    "hasModelPref": "has_model",
}
_CARTON_TO_OWL_ALIAS = {v: k for k, v in _OWL_TO_CARTON_ALIAS.items()}

# Pure camelCase → snake_case (used by _owl_prop_to_carton_rel below)
_CAMEL_SPLIT_1 = re.compile(r'(.)([A-Z][a-z]+)')
_CAMEL_SPLIT_2 = re.compile(r'([a-z0-9])([A-Z])')


def _owl_prop_to_carton_rel(owl_prop: str) -> str:
    """Convert OWL camelCase property name to CartON snake_case relationship name.

    Handles arbitrary camelCase input via structural conversion. Falls back to
    the input unchanged if it's already snake_case (no uppercase letters).
    Honors _OWL_TO_CARTON_ALIAS for known shortened aliases.
    """
    if owl_prop in _OWL_TO_CARTON_ALIAS:
        return _OWL_TO_CARTON_ALIAS[owl_prop]
    s1 = _CAMEL_SPLIT_1.sub(r'\1_\2', owl_prop)
    return _CAMEL_SPLIT_2.sub(r'\1_\2', s1).lower()


def _carton_rel_to_owl_prop(carton_rel: str) -> str:
    """Convert CartON snake_case relationship name to OWL camelCase property name.

    Structural conversion via splitting on underscore + capitalizing each part
    after the first. Honors _CARTON_TO_OWL_ALIAS for the reverse of known aliases.
    """
    if carton_rel in _CARTON_TO_OWL_ALIAS:
        return _CARTON_TO_OWL_ALIAS[carton_rel]
    parts = carton_rel.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])


# ──────────────────────────────────────────────────────────────
# Validation API
# ──────────────────────────────────────────────────────────────

# Types that should trigger file materialization when ONT-complete
# gen=true means "when all OWL restrictions are met, create a file artifact"
_GEN_TYPES = {
    "Skill": "skill_package",        # → skill directory with SKILL.md
    "SkillSpec": None,               # idea only, no gen
    "Flight_Config": "flight_json",  # → flight config JSON
    "Persona": "persona_json",       # → persona JSON
    "MCPSpec": "mcp_package",        # → MCP server directory
    "HookSpec": "hook_file",         # → hook Python file
    "AgentSpec": "agent_file",       # → agent markdown
    "SlashCommandSpec": "command_file",  # → command markdown
    "Claude_Code_Rule": "rule_file", # → .claude/rules/*.md via project_to_rule
}


@dataclass
class SystemTypeValidationResult:
    """Result of system type validation.

    The unified pipeline result:
    - is_system_type: Was it recognized?
    - valid: All OWL restrictions met? (ONT if true, SOUP if false)
    - gen: Should this type produce a file when complete?
    - gen_target: What kind of file (skill_package, flight_json, etc.)
    - inferred: Fields that were deduced from context (not provided by user)
    - missing_*: What's still needed for ONT status
    """
    is_system_type: bool            # Was the type recognized as a system type?
    valid: bool                     # Did it pass validation? (ONT vs SOUP)
    type_name: Optional[str] = None # The resolved system type name
    gen: bool = False               # Should materialization happen when complete?
    gen_target: Optional[str] = None  # What kind of artifact to produce
    inferred: Dict[str, Any] = field(default_factory=dict)  # Deduced from context
    missing_relationships: List[str] = field(default_factory=list)
    missing_cardinalities: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        """ONT if complete, SOUP if incomplete."""
        return "ONT" if self.valid else "SOUP"

    @property
    def error_message(self) -> Optional[str]:
        if self.valid:
            return None
        parts = []
        if self.missing_relationships:
            parts.append(f"Missing required relationships: {', '.join(self.missing_relationships)}")
        if self.missing_cardinalities:
            parts.append(f"Missing required fields: {', '.join(self.missing_cardinalities)}")
        if self.errors:
            parts.extend(self.errors)
        return "; ".join(parts)


def resolve_system_type(concept_name: str, is_a_list: List[str]) -> Optional[str]:
    """
    Resolve a concept to its system type, if any.

    Checks:
    1. Direct is_a match to a known system type
    2. Concept name prefix match (e.g. GIINT_Task_Foo → GIINT_Task)

    Returns the system type name or None if not a system type.
    """
    shapes = get_system_type_shapes()

    # 1. Direct is_a match (case-insensitive)
    shapes_lower = {k.lower(): k for k in shapes}
    for is_a_target in is_a_list:
        if is_a_target.lower() in shapes_lower:
            return shapes_lower[is_a_target.lower()]

    # 2. Prefix match on concept name (case-insensitive)
    # Sort by length descending so longer prefixes match first
    # e.g. "GIINT_Deliverable" matches before "GIINT"
    name_lower = concept_name.lower()
    sorted_types = sorted(shapes.keys(), key=len, reverse=True)
    for type_name in sorted_types:
        prefix = type_name.lower() + "_"
        if name_lower.startswith(prefix) or name_lower == type_name.lower():
            return type_name

    return None


def validate_system_type(
    concept_name: str,
    relationship_dict: Dict[str, List[str]],
) -> SystemTypeValidationResult:
    """
    Validate a concept against OWL-defined system type restrictions.

    This is the FAST PATH for system types — no youknow() call, no Neo4j query.
    Just: resolve type → check OWL restrictions → return result.

    Args:
        concept_name: The concept being created
        relationship_dict: {rel_type: [targets]} as provided to add_concept

    Returns:
        SystemTypeValidationResult with is_system_type=False if not a known type
    """
    # Normalize ALL keys to snake_case FIRST — parse_statement() outputs camelCase
    # (hasCategory) but all downstream code expects snake_case (has_category).
    # Do this ONCE before anything else so inference + validation use consistent keys.
    normalized_dict = {}
    for k, v in relationship_dict.items():
        carton_key = _owl_prop_to_carton_rel(k)
        normalized_dict[carton_key] = v
    relationship_dict = normalized_dict

    is_a_list = relationship_dict.get("is_a", [])
    system_type = resolve_system_type(concept_name, is_a_list)

    if system_type is None:
        return SystemTypeValidationResult(is_system_type=False, valid=True)

    shapes = get_system_type_shapes()
    shape = shapes[system_type]

    missing_rels = []
    missing_cards = []
    errors = []
    has_unnamed = False  # Track if any _Unnamed fills occurred

    # INFER FIRST, then validate — ontology deduces before checking
    inferred = _infer_from_context(system_type, relationship_dict, [], concept_name=concept_name)

    # Pull out the d-chain rejection sentinel from inferred BEFORE merging into
    # effective_rels. _infer_from_context uses inferred["__chain_rejections__"]
    # to surface chain-failure reasons (naming pattern, granularity, etc.) that
    # must flip valid=False with a specific message — not pollute the graph.
    _chain_rejections = inferred.pop("__chain_rejections__", [])
    if _chain_rejections:
        errors.extend(_chain_rejections)

    # Merge inferred into a working copy for validation
    effective_rels = dict(relationship_dict)
    for k, v in inferred.items():
        if k not in effective_rels:
            effective_rels[k] = v

    # Check someValuesFrom restrictions
    # STRUCTURAL (part_of wrong/missing) = HARD BLOCK
    # ANY OTHER missing field = auto-fill _Unnamed, tracked as SOUP
    for owl_prop, required_target_type in shape.required_relationships().items():
        carton_rel = _owl_prop_to_carton_rel(owl_prop)

        provided_targets = effective_rels.get(carton_rel, [])
        if not provided_targets:
            if carton_rel == "part_of":
                missing_rels.append(
                    f"part_of must include a {required_target_type} "
                    f"(e.g. part_of=['{required_target_type}_YourName'])"
                )
            else:
                inferred[carton_rel] = [f"{required_target_type}_Unnamed"]
                has_unnamed = True
        else:
            if carton_rel == "part_of":
                has_valid = any(
                    t.lower().startswith(required_target_type.lower()) or t.lower() == required_target_type.lower()
                    for t in provided_targets
                )
                if not has_valid:
                    missing_rels.append(
                        f"part_of targets {provided_targets} don't match required type "
                        f"{required_target_type}. Need part_of=['{required_target_type}_...']"
                    )

    # Check minCardinality — missing = auto-fill _Unnamed, concept is SOUP
    for owl_prop, min_count in shape.required_cardinalities().items():
        carton_rel = _owl_prop_to_carton_rel(owl_prop)
        provided_targets = effective_rels.get(carton_rel, [])
        if len(provided_targets) < min_count:
            inferred[carton_rel] = ["_Unnamed"]
            has_unnamed = True

    # Structural violations = hard block (concept rejected entirely)
    valid = len(missing_rels) == 0 and len(errors) == 0

    # _Unnamed = SOUP. Concept enters CartON but is NOT CODE, NOT projected.
    # Projection only when ALL restricted fields have real values (not _Unnamed).
    # Gen (artifact projection) blocked when has_unnamed.
    gen_target = _GEN_TYPES.get(system_type)
    should_gen = gen_target is not None and valid and not has_unnamed

    return SystemTypeValidationResult(
        is_system_type=True,
        valid=valid,
        type_name=system_type,
        gen=should_gen,
        gen_target=gen_target,
        inferred=inferred,
        missing_relationships=missing_rels,
        missing_cardinalities=missing_cards,
        errors=errors if not has_unnamed else errors + ["SOUP: concept has _Unnamed fills — not projected until all fields real"],
    )


def _infer_from_context(
    system_type: str,
    relationship_dict: Dict[str, List[str]],
    missing_cards: List[str],
    concept_name: str = "",
) -> Dict[str, Any]:
    """Infer missing fields from runtime context.

    This is where YOUKNOW acts as an ontology, not just a validator.
    Instead of "missing 15 fields, rejected" we say "I deduced 12 from context."

    Sources of inference:
    - OMNISANC course state (current starsystem, project path)
    - Provided relationships (desc → content, domain from starsystem)
    - Type defaults (understand skills aren't user_invocable, etc.)
    """
    inferred = {}

    # Read starsystem context from OMNISANC course state
    try:
        import json
        from pathlib import Path
        import os

        heaven_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        course_state = Path(heaven_dir) / "omnisanc_core" / ".course_state"
        if course_state.exists():
            state = json.loads(course_state.read_text())
            project_path = state.get("last_oriented") or (state.get("projects", [None])[0])
            if project_path:
                slug = project_path.strip("/").replace("/", "_").replace("-", "_").title()
                starsystem_name = f"Starsystem_{slug}"

                # Infer has_starsystem if missing
                if not relationship_dict.get("has_starsystem"):
                    inferred["has_starsystem"] = [starsystem_name]
    except Exception:
        pass

    # Skill always HAS a SkillSpec — manufacture it from provided args if not explicit
    if system_type == "Skill" and not relationship_dict.get("has_spec"):
        # If the 5 SkillSpec fields are present, the spec is implied
        spec_fields = ["has_domain", "has_category", "has_what", "has_when", "has_produces"]
        if all(relationship_dict.get(f) for f in spec_fields):
            inferred["has_spec"] = [f"SkillSpec_{concept_name}"]

    # Type-specific defaults
    if system_type == "Skill" or system_type == "SkillSpec":
        # Category-based defaults
        categories = relationship_dict.get("has_category", [])
        cat = categories[0].lower().replace("skill_category_", "") if categories else None

        if cat == "understand":
            if not relationship_dict.get("has_user_invocable"):
                inferred["has_user_invocable"] = ["false"]
            if not relationship_dict.get("has_context_mode"):
                inferred["has_context_mode"] = ["inline"]
        elif cat == "preflight":
            if not relationship_dict.get("has_user_invocable"):
                inferred["has_user_invocable"] = ["true"]
            if not relationship_dict.get("has_context_mode"):
                inferred["has_context_mode"] = ["inline"]
        elif cat == "single_turn_process":
            if not relationship_dict.get("has_user_invocable"):
                inferred["has_user_invocable"] = ["true"]
            if not relationship_dict.get("has_context_mode"):
                inferred["has_context_mode"] = ["inline"]

        # Default model
        if not relationship_dict.get("has_model"):
            inferred["has_model"] = ["sonnet"]

        # Default agent type
        if not relationship_dict.get("has_agent_type"):
            inferred["has_agent_type"] = ["none"]

        # Empty defaults for structural fields that can be empty initially
        for field_name in ["has_reference", "has_resources", "has_scripts",
                          "has_templates", "has_hook", "has_allowed_tools",
                          "has_disable_model_invocation", "has_argument_hint"]:
            if not relationship_dict.get(field_name):
                inferred[field_name] = ["none"]

        # Infer has_requires from empty if not provided
        if not relationship_dict.get("has_requires"):
            inferred["has_requires"] = ["none"]

    # Claude_Code_Rule per-argument d-chain evaluation.
    # Each d-chain is SAT (with value) or FAIL (with reason). No silent skip.
    # The whole concept becomes SYSTEM_TYPE only when every d-chain SATs.
    #
    # Phase 1 active chains (data exists to evaluate):
    #   has_scope, has_starsystem, has_name, has_content, naming_pattern
    #
    # Phase 2 chains (gated on canonicalization pipeline writing rdf:type for
    # starsystems / Giint_Components / Bugs / Ideas to domain.owl):
    #   has_component, has_caused_by, granularity
    # Currently these references appear in domain.owl only as rdf:resource
    # targets, never as rdf:about subjects with rdf:type. So canonical-existence
    # checks against domain.owl can't resolve them. These chains return when
    # the canonicalization pipeline lands their data.
    if system_type == "Claude_Code_Rule":
        _failures = []  # (chain_name, reason) — surfaced via __chain_rejections__ sentinel

        def _provided(key):
            return relationship_dict.get(key) or inferred.get(key)

        # ── d-chain: has_scope ──
        # SAT: value provided in {global, project} OR derivable from part_of.
        # FAIL: neither.
        scope = None
        _scope_val = _provided("has_scope")
        if _scope_val:
            v = str(_scope_val[0]).lower()
            if v in ("global", "project"):
                scope = v
            else:
                _failures.append(("has_scope", f"value {v!r} not in {{global, project}}"))
        else:
            part_of_all = list(relationship_dict.get("part_of", [])) + list(inferred.get("part_of", []))
            if any(t == "Seed_Ship" or t == "Seed_Ship_Starsystems" for t in part_of_all):
                scope = "global"
                inferred["has_scope"] = ["global"]
            elif any(t.startswith("Starsystem_") for t in part_of_all):
                scope = "project"
                inferred["has_scope"] = ["project"]
            else:
                # Default to global if user provided no signal — matches the rule emission
                # convention where bare rules without part_of are global.
                scope = "global"
                inferred["has_scope"] = ["global"]

        # ── d-chain: has_starsystem ──
        # SAT: value provided OR self-heal from scope.
        #   global → Seed_Ship
        #   project → starsystem from part_of=Starsystem_* OR from OMNISANC course state inference
        # No canonical-individual existence check at this phase — see Phase 2 comment.
        starsystem = None
        _hs_val = _provided("has_starsystem")
        if _hs_val:
            starsystem = _hs_val[0]
        elif scope == "global":
            starsystem = "Seed_Ship"
            inferred["has_starsystem"] = ["Seed_Ship"]
            if not relationship_dict.get("part_of"):
                inferred["part_of"] = ["Seed_Ship"]
        elif scope == "project":
            part_of_all = list(relationship_dict.get("part_of", [])) + list(inferred.get("part_of", []))
            starsystem = next((t for t in part_of_all if t.startswith("Starsystem_")), None)
            if starsystem:
                inferred["has_starsystem"] = [starsystem]
            else:
                _failures.append(("has_starsystem", "project-scope rule with no part_of=Starsystem_*"))

        # ── d-chain: has_name (slug) — always self-heals from concept_name ──
        if not relationship_dict.get("has_name") and concept_name:
            _slug = concept_name
            if _slug.lower().startswith("claude_code_rule_"):
                _slug = _slug[len("claude_code_rule_"):]
            _slug = _slug.lower().replace("_", "-")
            inferred["has_name"] = [_slug]

        # ── d-chain: naming pattern (cross-arg invariant, NO self-heal) ──
        # Project scope: concept_name must start with Claude_Code_Rule_{Starsystem_short}_
        if scope == "project" and starsystem and concept_name:
            ss_short = starsystem.replace("Starsystem_", "")
            if not concept_name.startswith(f"Claude_Code_Rule_{ss_short}_"):
                _failures.append((
                    "naming_pattern",
                    f"project-scope rule must start with Claude_Code_Rule_{ss_short}_ ; got {concept_name}",
                ))

        # ── d-chain: has_content (str arg) ──
        # SAT: value provided OR self-heal to concept_name (projector reads c.d as body).
        if not relationship_dict.get("has_content"):
            if concept_name:
                inferred["has_content"] = [concept_name]
            else:
                _failures.append(("has_content", "no concept_name to self-heal from"))

        # Surface failures via the __chain_rejections__ sentinel.
        if _failures:
            inferred["__chain_rejections__"] = [
                f"d-chain FAIL [{chain}]: {reason}" for chain, reason in _failures
            ]

    return inferred


# ──────────────────────────────────────────────────────────────
# Diagnostic / introspection
# ──────────────────────────────────────────────────────────────

def describe_type(type_name: str) -> Optional[str]:
    """Get human-readable description of a system type's requirements."""
    shapes = get_system_type_shapes()
    if type_name not in shapes:
        return None

    shape = shapes[type_name]
    lines = [f"System type: {type_name}"]
    if shape.parent_type:
        lines.append(f"  Parent: {shape.parent_type}")

    req_rels = shape.required_relationships()
    if req_rels:
        lines.append("  Required relationships (someValuesFrom):")
        for prop, target in req_rels.items():
            carton = _owl_prop_to_carton_rel(prop)
            lines.append(f"    {carton} → {target}")

    req_cards = shape.required_cardinalities()
    if req_cards:
        lines.append("  Required fields (minCardinality):")
        for prop, count in req_cards.items():
            carton = _owl_prop_to_carton_rel(prop)
            lines.append(f"    {carton} >= {count}")

    return "\n".join(lines)


def describe_all_types() -> str:
    """Get human-readable description of all system types."""
    shapes = get_system_type_shapes()
    parts = []
    for type_name in sorted(shapes.keys()):
        desc = describe_type(type_name)
        if desc:
            parts.append(desc)
    return "\n\n".join(parts)
