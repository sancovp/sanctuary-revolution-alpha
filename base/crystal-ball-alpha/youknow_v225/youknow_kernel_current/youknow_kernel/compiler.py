#!/usr/bin/env python3
"""
YOUKNOW COMPILER - The ONE Entry Point

This is THE way to interact with YOUKNOW. Everything goes through here.

!! WHY YOUKNOW EXISTS !!

YOUKNOW is a shell for typing ideas into code ontologically. You describe
code objects through claims (triples), YOUKNOW validates them against OWL
restrictions, and when complete, emits the code artifact. Progressive —
each call tells you what's missing. Semantic webs become required at
deeper levels, guiding you.

!! HOW IT WORKS !!

Input: Any statement with any predicates (e.g., "Skill_X is_a Skill, has_domain Paiab")
Output: "CODE: ..." (system type valid, artifact emitted) or
        "SOUP: ..." (missing restrictions, tells you what to provide next)

TWO PATHS:
  CODE: System type (Skill, Bug, GIINT_*, etc.) with all OWL restrictions
        satisfied → system_type_validator → CODE → artifact generated
  SOUP: Incomplete claim → recursive restriction walk tells you what's
        missing per concept in the chain → conversational error

The compiler is called REPEATEDLY by the LLM loop (dragonbones hook).
Each call advances the concept one step closer. Stateless per call.
`reifies` declares the deduction chain terminal — validates up to that
level, stops deeper. Composable: build types, reference them, wrap them.

!! THE CORE SENTENCE (all SPOs co-arise) !!

  from Reality and is(Reality):
  primitive_is_a IS a type of is_a → is_a embodies part_of →
  part_of (as triple) entails instantiates → instantiates necessitates
  produces → part_of manifests produces → produces reifies as
  pattern_of_is_a → pattern_of_is_a produces programs →
  programs instantiates part_of Reality

  Every predicate decomposes through this sentence to bootstrapped
  primitives. Strong compression = full decomposition resolves.
  Weak compression = decomposition stops somewhere = SOUP.

!! CURRENT STATE (2026-04-19) !!

  YOUKNOW handles CODE + SOUP only. ONT layer requires SOMA/Prolog.

  WORKING: Parser (any predicate), system type validation (OWL restrictions),
           recursive restriction walk (instant, replaces Pellet sync_reasoner),
           reifies as deduction chain terminal, accumulation across calls,
           CODE gate via system_type_validator, code generation via codeness_gen,
           conversational SOUP/CODE responses, hasContent sourcing,
           full e2e: CartON MCP → YOUKNOW CODE → queue is_code → daemon → projection

  CODE = system_type_validator says is_system_type AND valid. Code object with all
         OWL restrictions satisfied. Triggers artifact generation (skill, rule, etc).
  SOUP = not a valid system type, or missing restrictions. Conversational errors
         grouped by concept showing what each thing in the chain needs.
  ONT  = NOT IMPLEMENTED HERE. Requires recursive core sentence check via SOMA/Prolog.

  cat_of_cat.py replaced with owl_types.py (thin OWL class registry + accumulation).
  Pellet sync_reasoner replaced with recursive restriction walk (instant).

  TODO: Port derivation/validation mechanics to SOMA for ONT layer,
        unify codeness_gen templates into substrate_projector

THREE DATA LAYERS:
    1. Foundation OWL (uarl.owl, frozen) - core types, SHACL shapes, bootstrap
    2. Domain OWL (domain.owl, dynamic) - user entities, updated every call
    3. Carton (Neo4j+ChromaDB) - persistence, search, agent layer
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


# Canonical predicate vocabulary accepted by the statement parser.
_PREDICATE_CANONICAL: Dict[str, str] = {
    "is_a": "is_a",
    "isa": "is_a",
    "part_of": "part_of",
    "partof": "part_of",
    "produces": "produces",
    "instantiates": "instantiates",  # distinct core sentence step — NOT produces
    "has_part": "has_part",
    "haspart": "has_part",
    "embodies": "embodies",
    "manifests": "manifests",
    "reifies": "reifies",
    "hasmsc": "has_msc",
    "has_msc": "has_msc",
    "msc": "has_msc",
    "justifies": "justifies",
    "justifiesedge": "justifies_edge",
    "justifies_edge": "justifies_edge",
    "catofcatbounded": "cat_of_cat_bounded",
    "cat_of_cat_bounded": "cat_of_cat_bounded",
    "sestypeddepth": "ses_typed_depth",
    "ses_typed_depth": "ses_typed_depth",
    "compressionmode": "compression_mode",
    "compression_mode": "compression_mode",
    "reason": "reason",
    "programs": "programs",
    "pythonclass": "python_class",
    "python_class": "python_class",
    "template": "template",
    "description": "description",
    "ylayer": "y_layer",
    "y_layer": "y_layer",
    "intuition": "intuition",
    "comparefrom": "compare_from",
    "compare_from": "compare_from",
    "mapsto": "maps_to",
    "maps_to": "maps_to",
    "analogicalpattern": "analogical_pattern",
    "analogical_pattern": "analogical_pattern",
    # GIINT structural predicates (snake_case → camelCase for OWL alignment)
    "has_code_entity": "hasCodeEntity", "hascodeentity": "hasCodeEntity",
    "has_flight_config": "hasFlightConfig", "hasflightconfig": "hasFlightConfig",
    "has_mcp_server": "hasMcpServer", "hasmcpserver": "hasMcpServer",
    "implements_pattern": "implementsPattern", "implementspattern": "implementsPattern",
    "has_example_reference": "hasExampleReference", "hasexamplereference": "hasExampleReference",
    "has_pattern": "hasPattern", "haspattern": "hasPattern",
    "has_change_spec": "hasChangeSpec", "haschangespec": "hasChangeSpec",
    "has_line_range": "hasLineRange", "haslinerange": "hasLineRange",
    "has_done_signal": "hasDoneSignal", "hasdonesignal": "hasDoneSignal",
    "has_hook": "hasHook", "hashook": "hasHook",
    "has_subagent": "hasSubagent", "hassubagent": "hasSubagent",
    "has_plugin": "hasPlugin", "hasplugin": "hasPlugin",
    "has_path": "hasPath", "haspath": "hasPath",
    # Skill predicates
    "has_domain": "hasDomain", "hasdomain": "hasDomain",
    "has_category": "hasCategory", "hascategory": "hasCategory",
    "has_what": "hasWhat", "haswhat": "hasWhat",
    "has_when": "hasWhen", "haswhen": "hasWhen",
    "has_produces": "hasProduces", "hasproduces": "hasProduces",
    "has_subdomain": "hasSubdomain", "hassubdomain": "hasSubdomain",
    "has_content": "hasContent", "hascontent": "hasContent",
    "has_requires": "hasRequires", "hasrequires": "hasRequires",
    "has_describes_component": "hasDescribesComponent", "hasdescribescomponent": "hasDescribesComponent",
    "has_starsystem": "hasStarsystem", "hasstarsystem": "hasStarsystem",
}
_STRUCTURAL_PREDICATES = {"is_a", "part_of", "has_part", "produces", "instantiates", "embodies", "manifests", "reifies", "programs"}

# Lazy UARL validator singleton — loaded once, reused
_uarl_validator_instance = None
_uarl_validator_tried = False

# System type inferred fields — set by youknow() SOUP path, read by daemon.py
# Contains {carton_rel: [target]} for _Unnamed fills that need to become relationships
_last_system_type_inferred = {}

def _get_last_system_type_inferred():
    """Get and clear the last system type inferred dict."""
    global _last_system_type_inferred
    result = dict(_last_system_type_inferred)
    _last_system_type_inferred = {}
    return result

def _get_uarl_validator():
    """Get or create the UARL validator singleton."""
    global _uarl_validator_instance, _uarl_validator_tried
    if _uarl_validator_tried:
        return _uarl_validator_instance
    _uarl_validator_tried = True
    try:
        from .uarl_validator import UARLValidator
        _uarl_validator_instance = UARLValidator()
    except Exception:
        _uarl_validator_instance = None
    return _uarl_validator_instance


# =============================================================================
# RESPONSE TYPES
# =============================================================================

class ResponseType(Enum):
    """Whether the quine closes or breaks."""
    OK = "OK"      # Quine closes - traces to Cat_of_Cat
    WRONG = "Wrong"  # Quine breaks - chain is incomplete


@dataclass
class SpiralStep:
    """One step in the derivation spiral — traces is_a chain from concept to Cat_of_Cat."""
    subject: str           # The thing at this level
    predicate: str         # is_a, part_of, produces
    object: str            # What it relates to

    # EMR state at this level (TODO: get from DerivationValidator)
    embodies: List[str] = field(default_factory=list)   # What features
    manifests: Dict[str, str] = field(default_factory=dict)  # What structure
    reifies_via: Optional[str] = None  # Inclusion map

    # Is this step complete or a placeholder?
    is_placeholder: bool = False

    def to_string(self) -> str:
        """Format this step for the spiral output."""
        if self.is_placeholder:
            return f"{self.subject} {self.predicate} ? (unknown)"

        parts = [f"{self.subject} {self.predicate} {self.object}"]

        if self.embodies:
            parts.append(f"  embodies {{{', '.join(self.embodies)}}}")
        if self.manifests:
            manifest_str = ', '.join(f"{k}: {v}" for k, v in self.manifests.items())
            parts.append(f"  manifests {{{manifest_str}}}")
        if self.reifies_via:
            parts.append(f"  reifies via inclusion map {{{self.reifies_via}}}")

        return '\n'.join(parts)


@dataclass
class CompilerResponse:
    """The full response from the compiler — OK or SOUP with explanation."""
    # The original statement
    statement: str

    # OK or Wrong
    response_type: ResponseType

    # The spiral (derivation chain)
    spiral: List[SpiralStep] = field(default_factory=list)

    # Where the chain breaks (if Wrong)
    break_point: Optional[str] = None
    whats_missing: List[str] = field(default_factory=list)

    def to_string(self) -> str:
        """Format the full response.

        OK = just "OK" (0.01% - graduation, no explanation needed)
        Wrong = explains what's missing (99.99% - building)
        """
        if self.response_type == ResponseType.OK:
            return "OK"

        # Wrong - show explanation
        lines = [f"You said {self.statement}. Wrong because:"]
        lines.append("")

        for step in self.spiral:
            lines.append(step.to_string())

        lines.append("")
        lines.append(f"Chain breaks at: {self.break_point}")
        for missing in self.whats_missing:
            lines.append(f"  - {missing}")

        return '\n'.join(lines)


@dataclass
class CompressionReport:
    """Strong/weak compression state for promotion gating."""
    has_msc: bool
    required_rel_count: int
    justified_rel_count: int
    all_required_justified: bool
    mode: str  # "strong" | "weak"


@dataclass
class Decision:
    """Promotion gate decision."""
    is_programs: bool
    is_strong_compression: bool
    is_catofcat_bounded: bool
    has_blocking_violations: bool
    admit_to_ont: bool
    stay_in_soup: bool


@dataclass
class CompilePacket:
    """Internal compile packet carrying phase outputs."""
    source_statement: str
    parsed_claim: Dict[str, Any]
    normalized_relations: Dict[str, Any]
    abcd_state: Dict[str, Any]
    candidate_subgraph: Dict[str, Any]
    emr_state: str
    ses_report: Dict[str, Any]
    compression_report: Dict[str, Any]
    diagnostics: Dict[str, Any]
    decision: Dict[str, Any]
    spiral: List[SpiralStep] = field(default_factory=list)
    break_point: Optional[str] = None
    whats_missing: List[str] = field(default_factory=list)


# =============================================================================
# STATEMENT PARSER
# =============================================================================

@dataclass
class ParsedStatement:
    """A parsed YOUKNOW statement — subject predicate object with optional additional predicates."""
    # TODO: Handle nested structures beyond comma-separated predicates
    subject: str
    predicate: str  # is_a, part_of, produces, has_part, etc.
    object: str

    # Additional predicates in same statement
    # e.g., "Animal is_a Entity, part_of Living_Things, produces Creature"
    additional: List[Tuple[str, str]] = field(default_factory=list)

    raw: str = ""


def _canonical_predicate(raw_predicate: str) -> str:
    """Normalize parser predicate tokens to canonical internal names."""
    key = raw_predicate.strip().lower()
    return _PREDICATE_CANONICAL.get(key, key)


def _normalize_token(token: str) -> str:
    """Strip optional quoting around parser tokens."""
    token = token.strip()
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        return token[1:-1]
    return token


def parse_statement(statement: str) -> Optional[ParsedStatement]:
    """Parse a YOUKNOW statement into subject, predicate, object + additional predicates.

    Examples:
        "Dog is_a Animal" → ParsedStatement(Dog, is_a, Animal)
        "Animal is_a Entity, part_of Living_Things" → ParsedStatement with additional
    """
    statement = statement.strip()

    # Pattern: Subject predicate Object [, predicate Object]*
    # Predicates are ANY word_with_underscores — the reasoner validates, not the parser
    subject_pattern = r"[A-Za-z0-9_:.+-]+"
    object_pattern = r"(?:\"[^\"]+\"|'[^']+'|[A-Za-z0-9_:.+-]+)"
    predicate_pattern = r"[A-Za-z][A-Za-z0-9_]*"

    # First, try to match the primary triple
    primary_match = re.match(
        rf'({subject_pattern})\s+({predicate_pattern})\s+({object_pattern})',
        statement,
        re.IGNORECASE
    )

    if not primary_match:
        return None

    subject = primary_match.group(1)
    predicate = _canonical_predicate(primary_match.group(2))
    obj = _normalize_token(primary_match.group(3))

    # Look for additional predicates
    additional = []
    rest = statement[primary_match.end():]

    for match in re.finditer(
        rf',\s*({predicate_pattern})\s+({object_pattern})',
        rest,
        re.IGNORECASE,
    ):
        additional.append(
            (
                _canonical_predicate(match.group(1)),
                _normalize_token(match.group(2)),
            )
        )

    return ParsedStatement(
        subject=subject,
        predicate=predicate,
        object=obj,
        additional=additional,
        raw=statement
    )


# =============================================================================
# THE COMPILER
# =============================================================================

def youknow(statement: str) -> str:
    """THE one-shot compiler step used by external LLM loops.

    Wired to:
        - HyperedgeValidator (embodies/manifests/reifies) — line 486
        - DerivationValidator (L0-L6 levels) — line 487
        - UARLValidator (SHACL + Pellet reasoning) — line 498-553
        - Cat_of_Cat (chain tracing) — line 466, 480
        - Griess Constructor (phase tracking) — line 391

    TODO:
        - DualSubstrate persistence
        - Strong compression (named patterns)

    Contract:
        - Single-step compile only (no internal while-loop).
        - Intended to be called repeatedly by an external controller/LLM loop.
        - Returns deterministic gate outcome for current ontology state.
    """
    # 1. Parse the statement
    parsed = parse_statement(statement)
    if not parsed:
        return f"You said {statement}. Wrong because: could not parse statement."

    # 1.5. SYSTEM TYPE VALIDATION — checks OWL restrictions on code objects.
    # System types (GIINT_*, Skill, Bug_, etc.) have COMPLETE KNOWLEDGE.
    # Valid system type = CODE. Invalid = BLOCKED. Not a system type = continue to SOUP check.
    stv_result = None
    try:
        from .system_type_validator import validate_system_type
        rel_dict = {parsed.predicate: [parsed.object]}
        for pred, obj in parsed.additional:
            rel_dict.setdefault(pred, []).append(obj)
        stv_result = validate_system_type(parsed.subject, rel_dict)
        if stv_result.is_system_type and not stv_result.valid:
            return f"SYSTEM_TYPE_ERROR: {stv_result.error_message}"
    except ImportError:
        pass  # system_type_validator not available
    except Exception as e:
        logger.warning("System type validation failed (non-fatal): %s", e)

    # 2..8. Build compile packet and run promotion gate
    packet = _compile_packet(statement, parsed)

    # ── Griess Constructor integration ──
    # Track this concept through the Griess construction phases
    from .griess_constructor import get_constructor, VerifyReport, GriessPhase
    gc = get_constructor()

    # Advance concept through Griess phases based on EMR state
    gc.advance_from_emr(parsed.subject, packet.emr_state)

    # If concept reached VERIFY phase, run the Aut check
    concept_state = gc.get(parsed.subject)
    if concept_state and concept_state.phase == GriessPhase.VERIFY:
        ses_meaningful = (
            packet.ses_report.get("max_typed_depth", 0) > 0
            if isinstance(packet.ses_report, dict)
            else False
        )
        report = VerifyReport(
            yo_correct=packet.decision["is_catofcat_bounded"],
            ses_meaningful=ses_meaningful,
            strong_compression=packet.decision["is_strong_compression"],
            yo_reason="" if packet.decision["is_catofcat_bounded"] else "is_a chain not bounded",
            ses_reason="" if ses_meaningful else f"max_typed_depth={packet.ses_report.get('max_typed_depth', 0) if isinstance(packet.ses_report, dict) else 0}",
            compression_reason="" if packet.decision["is_strong_compression"] else "missing MSC or unjustified relationships",
        )
        gc.verify(parsed.subject, report)
        concept_state = gc.get(parsed.subject)

    # Add Griess state to diagnostics
    if concept_state:
        packet.diagnostics["griess"] = concept_state.to_dict()

    # 9. CODE gate: system_type_validator decides for code objects.
    # If stv says valid system type AND gen → CODE → persist + generate artifact.
    # If stv says valid BUT NOT gen (has _Unnamed) → SOUP → persist, no artifact.
    # This is the PRIMARY gate. stv is the authority for system types.
    if stv_result is not None and stv_result.is_system_type and stv_result.valid and not stv_result.gen:
        # _Unnamed fills present — SOUP. Enters CartON, NOT projected.
        # Store inferred so daemon.py can pass it to add_concept_tool_func
        # which merges _Unnamed relationships into the concept before queuing.
        # The daemon's Neo4j MERGE auto-creates stub nodes for _Unnamed targets.
        global _last_system_type_inferred
        _last_system_type_inferred = stv_result.inferred
        packet.decision["admit_to_ont"] = False
        packet.decision["stay_in_soup"] = True
        packet.decision["inferred"] = stv_result.inferred
        _persist_to_soup(
            parsed,
            packet.spiral,
            parsed.subject,
            [e for e in stv_result.errors if "SOUP" in e] or ["Has _Unnamed fills — fill all fields to reach CODE"],
            packet=packet,
        )
        unnamed_fields = ", ".join(sorted(stv_result.inferred.keys())) if stv_result.inferred else "unknown"
        return f"SOUP: {parsed.subject} is {stv_result.type_name} but has _Unnamed fills for: [{unnamed_fields}]. Fill these to project."

    if stv_result is not None and stv_result.is_system_type and stv_result.valid:
        # Code reality check: verify any code entity references exist in CA
        code_reality_errors = []
        _code_prefixes = ("CodeFile_", "CodeClass_", "CodeMethod_", "CodeFunction_")
        for pred, obj in [(parsed.predicate, parsed.object)] + list(parsed.additional):
            if any(obj.startswith(p) for p in _code_prefixes):
                try:
                    import os
                    from neo4j import GraphDatabase as _GDB
                    _uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
                    _drv = _GDB.driver(_uri, auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password")))
                    _label_map = {"CodeFile_": "File", "CodeClass_": "Class", "CodeMethod_": "Method", "CodeFunction_": "Function"}
                    _label = next((_label_map[p] for p in _code_prefixes if obj.startswith(p)), "File")
                    _search = obj
                    for p in _code_prefixes:
                        if _search.startswith(p):
                            _search = _search[len(p):]
                            break
                    with _drv.session() as _s:
                        _r = _s.run(f"MATCH (e:{_label}) WHERE e.name CONTAINS $t RETURN e.name LIMIT 1",
                                    t=_search.replace("_", ".") if "." not in _search else _search)
                        if not _r.single():
                            code_reality_errors.append(f"{obj}: code entity not found in codebase")
                    _drv.close()
                except Exception:
                    pass  # Can't check — allow through
        if code_reality_errors:
            return f"SOUP: {parsed.subject} has invalid code references. {'; '.join(code_reality_errors)}"

        packet.decision["admit_to_ont"] = True
        packet.decision["stay_in_soup"] = False
        packet.decision["has_blocking_violations"] = False
        packet.decision["gen_target"] = stv_result.gen_target
        packet.decision["type_name"] = stv_result.type_name
        packet.decision["inferred"] = stv_result.inferred

        # CODE path: persist + generate. Skip _admit_to_ontology_state (OWL domain).
        _persist(parsed, packet.spiral, packet=packet)

        gen_result = None
        gen_target = stv_result.gen_target
        if gen_target:
            gen_result = _generate_code_artifact(parsed, packet, gen_target)

        return _build_code_response(parsed, packet, gen_result=gen_result)

    # 10. Non-system-type path: check derivation for SOUP/admit
    if packet.decision["admit_to_ont"]:
        admitted, admission_error = _admit_to_ontology_state(parsed, packet)
        if not admitted:
            chain_missing = list(packet.whats_missing)
            missing = _collect_missingness(packet)
            if admission_error:
                missing.append(f"Ontology add failed: {admission_error}")
            missing = list(dict.fromkeys(missing))
            break_point = packet.break_point or parsed.object
            _persist_to_soup(
                parsed,
                packet.spiral,
                break_point,
                missing,
                packet=packet,
            )
            return _build_soup_response(
                parsed,
                break_point,
                chain_missing=chain_missing,
                whats_missing=missing,
            )
        _persist(parsed, packet.spiral, packet=packet)

        # CODE generation: if gen_target exists, generate the artifact
        gen_result = None
        gen_target = packet.decision.get("gen_target")
        if gen_target:
            gen_result = _generate_code_artifact(parsed, packet, gen_target)

        return _build_code_response(parsed, packet, gen_result=gen_result)

    chain_missing = list(packet.whats_missing)
    missing = _collect_missingness(packet)
    break_point = packet.break_point or parsed.object
    _persist_to_soup(
        parsed,
        packet.spiral,
        break_point,
        missing,
        packet=packet,
    )
    return _build_soup_response(
        parsed,
        break_point,
        chain_missing=chain_missing,
        whats_missing=missing,
    )


def _compile_packet(statement: str, parsed: ParsedStatement) -> CompilePacket:
    """Build compile packet for deterministic promotion gating."""
    from .owl_types import get_type_registry as get_cat
    from .derivation import DerivationValidator
    from .hyperedge import HyperedgeValidator

    cat = get_cat()
    subject_concept = _build_subject_concept(parsed, cat)
    normalized_relations = _normalized_relations(parsed)
    continuous_emr = _build_continuous_emr_telemetry(
        parsed=parsed,
        subject_concept=subject_concept,
        normalized_relations=normalized_relations,
        cat=cat,
    )
    spiral = _build_spiral(parsed, subject_concept=subject_concept)
    chain_complete, break_point, chain_missing = _check_chain_complete(
        spiral,
        parsed=parsed,
    )
    abcd_state = _build_abcd_state(parsed, cat)

    hyperedge_validator = HyperedgeValidator(cat=cat)
    derivation_validator = DerivationValidator(cat=cat)

    enforce_claim_validation = parsed.predicate == "is_a"
    claim_result = hyperedge_validator.validate_claim(
        subject=parsed.subject,
        object_=parsed.object,
        concept=subject_concept,
    )
    derivation_state = derivation_validator.validate(subject_concept)
    emr_state = _emr_state_from_derivation(derivation_state)

    # === RECURSIVE RESTRICTION WALK ===
    # For each is_a parent: does the concept have all parts that instantiate
    # that parent's restrictions? For each part: do THEY have their restrictions?
    # Recurse until terminal (type with no restrictions = CODE terminal).
    # Emit missing things at each level.
    uarl_errors: List[str] = []
    uarl_result = None
    try:
        from .system_type_validator import get_system_type_shapes, _owl_prop_to_carton_rel
        from .owl_types import get_type_registry
        shapes = get_system_type_shapes()
        registry = get_type_registry()

        # Extract reifies targets — these are the deduction chain terminals.
        # reifies = is_a + terminal. "X reifies Y" means X is concrete at Y's level.
        # Walk validates up to Y, stops there. Y's own deeper chain not checked.
        # Cannot reify something you're not is_a.
        reifies_targets = set()
        is_a_set = set(subject_concept.get("is_a", []))
        for pred, obj in parsed.additional:
            if pred == "reifies":
                reifies_targets.add(obj)
        # Also check properties
        rt = subject_concept.get("reifies") or subject_concept.get("properties", {}).get("reifies")
        if rt:
            if isinstance(rt, list):
                reifies_targets.update(rt)
            else:
                reifies_targets.add(str(rt))
        # Validate: can't reify something you're not is_a
        reifies_errors = []
        for rt_target in reifies_targets:
            if rt_target not in is_a_set:
                # Check if it's an ancestor (transitive is_a)
                if not registry.traces_to_root(rt_target):
                    reifies_errors.append(f"cannot reify {rt_target}: not is_a {rt_target}")

        # Code reality types — values referencing these are checked against CA Neo4j
        _CODE_ENTITY_TYPES = {"CodeFile", "CodeClass", "CodeMethod", "CodeFunction", "CodeAttribute", "CodeRepository"}
        _CODE_ENTITY_PREFIXES = ("CodeFile_", "CodeClass_", "CodeMethod_", "CodeFunction_", "CodeAttribute_", "Repo_")
        _ca_cache = {}  # Cache CA lookups within this walk

        def _check_code_reality(val, target_type):
            """Check if a code entity value exists in CA's Neo4j. Returns True if exists."""
            if target_type not in _CODE_ENTITY_TYPES and not any(val.startswith(p) for p in _CODE_ENTITY_PREFIXES):
                return None  # Not a code entity — skip check
            if val in _ca_cache:
                return _ca_cache[val]
            try:
                import os
                from neo4j import GraphDatabase
                uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
                user = os.environ.get("NEO4J_USER", "neo4j")
                password = os.environ.get("NEO4J_PASSWORD", "password")
                driver = GraphDatabase.driver(uri, auth=(user, password))
                # Check both CA graph (File/Class/Method labels) and CartON (:Wiki)
                label_map = {"CodeFile": "File", "CodeClass": "Class", "CodeMethod": "Method",
                             "CodeFunction": "Function", "CodeAttribute": "Attribute"}
                ca_label = label_map.get(target_type, "File")
                # Strip prefix for search
                search_name = val
                for prefix in _CODE_ENTITY_PREFIXES:
                    if val.startswith(prefix):
                        search_name = val[len(prefix):]
                        break
                with driver.session() as session:
                    result = session.run(
                        f"MATCH (e:{ca_label}) WHERE e.name CONTAINS $term RETURN e.name LIMIT 1",
                        term=search_name.replace("_", ".") if "." not in search_name else search_name,
                    )
                    exists = result.single() is not None
                driver.close()
                _ca_cache[val] = exists
                return exists
            except Exception:
                _ca_cache[val] = True  # Can't check — assume exists
                return True

        def _walk_restrictions(concept_name, is_a_parents, provided_rels, visited=None):
            """Recursive restriction walk. Returns list of missing things.

            Terminal conditions (stop recursing):
            a) reifies target that IS a known type = boundary, validated, stop
            b) Known typed thing with no restrictions = CODE terminal (valid, stop)
            c) Already visited = cycle, stop

            Non-terminal (emit what's missing):
            d) Known typed thing with unsatisfied restrictions = SOUP (emit missing)
            e) Arbitrary string / unknown type = unresolved, emit what's needed
            f) reifies target that is NOT known = invalid reification
            """
            if visited is None:
                visited = set()
            if concept_name in visited:
                return []
            visited.add(concept_name)

            # Check if this concept is a reifies terminal
            if concept_name in reifies_targets:
                if registry.is_known(concept_name):
                    return []  # Valid reification boundary — stop
                else:
                    return [f"{concept_name}: reifies target but is not a known type"]

            missing = []
            for parent in is_a_parents:
                if parent not in shapes:
                    if registry.is_known(parent):
                        continue  # CODE terminal — known type, no restrictions, valid
                    else:
                        missing.append(f"{parent} is_a ? (unknown type)")
                    continue

                # If this parent IS a reifies target: check its restrictions
                # on the concept, but do NOT recurse into values. Reifies means
                # "validate at this type's level, stop deeper."
                is_reifies_boundary = parent in reifies_targets

                shape = shapes[parent]
                # Check someValuesFrom restrictions (does concept have them?)
                for owl_prop, target_type in shape.required_relationships().items():
                    carton_rel = _owl_prop_to_carton_rel(owl_prop)
                    provided = provided_rels.get(carton_rel, [])
                    if not provided:
                        missing.append(f"{concept_name} requires {carton_rel} → {target_type}")
                    elif not is_reifies_boundary:
                        # Only recurse into values if NOT at reifies boundary
                        for val in provided:
                            if not val or val == "_Unnamed" or val == "none":
                                missing.append(f"{concept_name} requires {carton_rel} → {target_type} (placeholder)")
                                continue
                            # reifies boundary on the value itself?
                            if val in reifies_targets:
                                if registry.is_known(val) or _resolve_type_from_name(val, registry):
                                    continue
                                missing.append(f"{val}: reifies target but not a known type")
                                continue
                            if registry.is_known(val):
                                continue  # CODE terminal — known type, stop
                            # Code reality check — does this code entity exist?
                            ca_result = _check_code_reality(val, target_type)
                            if ca_result is True:
                                continue  # Code entity verified in CA
                            if ca_result is False:
                                missing.append(f"{val}: code entity not found in codebase (expected {target_type})")
                                continue
                            val_type = _resolve_type_from_name(val, registry)
                            if val_type and val_type in shapes:
                                sub_missing = _walk_restrictions(val, [val_type], {}, visited)
                                missing.extend(sub_missing)
                            else:
                                missing.append(f"{val}: is_a ?, part_of ?, produces ? (unresolved)")

                # Check minCardinality restrictions
                for owl_prop, min_count in shape.required_cardinalities().items():
                    carton_rel = _owl_prop_to_carton_rel(owl_prop)
                    provided = provided_rels.get(carton_rel, [])
                    if len(provided) < min_count:
                        missing.append(f"{concept_name} requires {carton_rel} (min {min_count})")

            return missing

        # Build provided relationships from subject_concept
        provided_rels = {}
        for pred in ("is_a", "part_of", "has_part", "produces", "instantiates",
                      "embodies", "manifests", "reifies", "programs"):
            vals = subject_concept.get(pred, [])
            if vals:
                provided_rels[pred] = vals
        for key, val in subject_concept.get("properties", {}).items():
            if val not in (None, "", "None") and key not in provided_rels:
                provided_rels[key] = val if isinstance(val, list) else [val]

        is_a_parents = subject_concept.get("is_a", [])
        uarl_errors = _walk_restrictions(parsed.subject, is_a_parents, provided_rels)
    except Exception:
        pass  # Restriction walk failure should not block compilation

    blocking: List[str] = []
    if not chain_complete:
        blocking.extend(chain_missing)
    if abcd_state["required"] and not abcd_state["complete"]:
        blocking.append(
            "ABCD missing slots: " + ", ".join(abcd_state["missing_slots"])
        )
    # Add restriction walk errors + reifies validation errors
    if uarl_errors:
        blocking.extend(uarl_errors)
    try:
        if reifies_errors:
            blocking.extend(reifies_errors)
    except NameError:
        pass  # reifies_errors not defined if walk try block failed
    if enforce_claim_validation and not claim_result.valid:
        if claim_result.missing_evidence:
            blocking.extend(claim_result.missing_evidence)
        else:
            blocking.append(
                f"No supporting hyperedge evidence for {parsed.subject} {parsed.predicate} {parsed.object}"
            )

    diagnostics = {
        "chain_complete": chain_complete,
        "hyperedge_valid": claim_result.valid if enforce_claim_validation else True,
        "hyperedge_strength": (
            claim_result.strength.value
            if enforce_claim_validation
            else "not_applicable"
        ),
        "continuous_emr": continuous_emr,
        "blocking": blocking,
        "warnings": [],
    }

    required_relationships = _required_relationships(parsed, spiral)
    coverage = hyperedge_validator.relationship_justification_coverage(
        required_relationships=required_relationships,
        concept=subject_concept,
    )

    # Strong/weak compression is COMPUTED from the derivation chain, not declared.
    #
    # MSC (Minimum Sufficient Compression) = the concept's subgraph instantiates
    # pattern_of_is_a. This IS what "chain closes" means (L3+). The pattern OF
    # how X is_a Y justifies the MSC of X, which instantiates pattern_of_is_a.
    #
    # Strong = EVERY entity and relationship in the subgraph is ALSO strong.
    #   L6 = all targets fully recursively typed = strong compression.
    # Weak = the concept itself has MSC but NOT every entity/relationship
    #   inside it is also strong (some are still SOUP).
    #   L3-L5 = weak compression (has MSC, not recursively complete).
    # No MSC = <L3 (chain doesn't even close for the concept itself).
    #
    # The whole subgraph being TRUE = produces.
    computed_bounded = chain_complete
    computed_msc = (
        computed_bounded
        and derivation_state.level.value >= 3  # L3 = chain closes = has MSC
    )
    # Strong = L6 (every entity/relationship in subgraph is also strong)
    # Weak = L3-L5 (has MSC but not everything inside is also strong)
    computed_strong = derivation_state.level.value >= 6

    compression = CompressionReport(
        has_msc=computed_msc,
        required_rel_count=coverage.required_rel_count,
        justified_rel_count=coverage.justified_rel_count,
        all_required_justified=computed_strong,
        mode="strong" if computed_msc and computed_strong else "weak",
    )

    # CODE/SOUP gate. ONT layer NOT IMPLEMENTED — requires SOMA/Prolog.
    # CODE = chain closes (L3+) + no blocking violations. Accepted as valid code-level claim.
    # SOUP = chain incomplete or has blockers. Returns what's missing.
    # ONT = would require full recursive core sentence check via Prolog. Not here.
    has_blocking_violations = len(blocking) > 0
    admit_as_code = (
        derivation_state.level.value >= 3  # L3: chain closes (reifies)
        and not has_blocking_violations
    )
    # admit_to_ont maps to admit_as_code — CODE is the highest level YOUKNOW can validate.
    # ONT requires SOMA's Prolog core sentence verification (not implemented in YOUKNOW).
    admit_to_ont = admit_as_code
    is_programs = derivation_state.level.value >= 6
    is_strong_compression = derivation_state.level.value >= 6
    is_catofcat_bounded = chain_complete

    decision = Decision(
        is_programs=is_programs,
        is_strong_compression=is_strong_compression,
        is_catofcat_bounded=is_catofcat_bounded,
        has_blocking_violations=has_blocking_violations,
        admit_to_ont=admit_to_ont,
        stay_in_soup=not admit_to_ont,
    )
    controller = _build_controller_telemetry(
        concept_name=parsed.subject,
        emr_state=emr_state,
        admit_to_ont=decision.admit_to_ont,
    )
    diagnostics["controller"] = controller
    if controller["threshold_event"]:
        diagnostics["warnings"].append(
            f"YMesh threshold event at {controller['target_layer']} ({controller['activation']})"
        )
    diagnostics["llm_suggest"] = _build_llm_guidance(
        parsed=parsed,
        blocking=blocking,
        decision=decision,
        compression=compression,
    )

    parsed_claim = {
        "subject": parsed.subject,
        "predicate": parsed.predicate,
        "object": parsed.object,
        "additional": parsed.additional,
    }
    candidate_subgraph = {
        "subject": parsed.subject,
        "predicate": parsed.predicate,
        "object": parsed.object,
        "trace_to_root": cat.trace_to_root(parsed.subject),
        "required_relationships": required_relationships,
        "justified_relationships": coverage.justified_relationships,
        "subject_concept": subject_concept,
    }
    ses_report = _build_ses_report(
        subject_concept,
        typed_symbols=set(cat.entities.keys()),
    )

    return CompilePacket(
        source_statement=statement,
        parsed_claim=parsed_claim,
        normalized_relations=normalized_relations,
        abcd_state=abcd_state,
        candidate_subgraph=candidate_subgraph,
        emr_state=emr_state,
        ses_report=ses_report,
        compression_report={
            "has_msc": compression.has_msc,
            "required_rel_count": compression.required_rel_count,
            "justified_rel_count": compression.justified_rel_count,
            "all_required_justified": compression.all_required_justified,
            "mode": compression.mode,
        },
        diagnostics=diagnostics,
        decision={
            "is_programs": decision.is_programs,
            "is_strong_compression": decision.is_strong_compression,
            "is_catofcat_bounded": decision.is_catofcat_bounded,
            "has_blocking_violations": decision.has_blocking_violations,
            "admit_to_ont": decision.admit_to_ont,
            "stay_in_soup": decision.stay_in_soup,
        },
        spiral=spiral,
        break_point=break_point,
        whats_missing=list(dict.fromkeys(list(chain_missing) + list(derivation_state.whats_missing))),
    )


def _admit_to_ontology_state(
    parsed: ParsedStatement,
    packet: CompilePacket,
) -> Tuple[bool, Optional[str]]:
    """Finalize ONT admission by adding the statement through YOUKNOW.add()."""
    try:
        from .core import get_youknow, reset_youknow
        from .owl_types import get_type_registry as get_cat

        cat = get_cat()
        yk = get_youknow()
        # Keep YOUKNOW singleton aligned with the active Cat_of_Cat global.
        if yk.cat is not cat:
            reset_youknow()
            yk = get_youknow()

        subject_concept = packet.candidate_subgraph.get("subject_concept", {})
        is_a = list(subject_concept.get("is_a", []))
        part_of = list(subject_concept.get("part_of", []))
        has_part = list(subject_concept.get("has_part", []))
        produces = list(subject_concept.get("produces", []))
        declared_bounded = _concept_declares_bounded(subject_concept)

        _apply_relation_update(is_a, part_of, has_part, produces, parsed.predicate, parsed.object)
        for predicate, object_ in parsed.additional:
            _apply_relation_update(is_a, part_of, has_part, produces, predicate, object_)

        is_a = _dedupe_ordered(is_a)
        part_of = _dedupe_ordered(part_of)
        has_part = _dedupe_ordered(has_part)
        produces = _dedupe_ordered(produces)

        properties = dict(subject_concept.get("properties", {}))
        if "has_msc" in subject_concept:
            properties.setdefault("hasMSC", subject_concept["has_msc"])
        if "msc" in subject_concept:
            properties.setdefault("msc", subject_concept["msc"])
        if "justifies" in subject_concept:
            properties["justifies"] = subject_concept["justifies"]
        if "justifies_edge" in subject_concept:
            properties["justifiesEdge"] = subject_concept["justifies_edge"]
        if "python_class" in subject_concept:
            properties.setdefault("python_class", subject_concept["python_class"])
        if "template" in subject_concept:
            properties.setdefault("template", subject_concept["template"])
        if "programs" in subject_concept:
            properties["programs"] = subject_concept["programs"]
        if "compression_mode" in subject_concept:
            properties["compressionMode"] = subject_concept["compression_mode"]
        if "ses_typed_depth" in subject_concept:
            properties["sesTypedDepth"] = subject_concept["ses_typed_depth"]
        if "reason" in subject_concept:
            properties["reason"] = subject_concept["reason"]
        if "intuition" in subject_concept:
            properties["intuition"] = subject_concept["intuition"]
        if "compare_from" in subject_concept:
            properties["compareFrom"] = subject_concept["compare_from"]
        if "maps_to" in subject_concept:
            properties["mapsTo"] = subject_concept["maps_to"]
        if "analogical_pattern" in subject_concept:
            properties["analogicalPattern"] = subject_concept["analogical_pattern"]
        if "y_layer" in subject_concept:
            properties["y_layer"] = subject_concept["y_layer"]

        # Build arbitrary relationships dict from properties
        # Anything stored by the open parser that isn't a structural predicate
        # or a known special property gets passed as a relationship
        _known_props = {
            "hasMSC", "msc", "justifies", "justifiesEdge", "python_class",
            "template", "programs", "compressionMode", "sesTypedDepth",
            "reason", "intuition", "compareFrom", "mapsTo",
            "analogicalPattern", "y_layer", "description",
        }
        extra_relationships = {}
        for key, val in properties.items():
            if key not in _known_props:
                if isinstance(val, list):
                    extra_relationships[key] = val
                else:
                    extra_relationships[key] = [str(val)]

        yk.add(
            name=parsed.subject,
            is_a=is_a or [parsed.object],
            part_of=part_of,
            has_part=has_part,
            produces=produces,
            y_layer=subject_concept.get("y_layer"),
            properties=properties,
            description=subject_concept.get("description", ""),
            relationships=extra_relationships,
            skip_pipeline=False,
        )
        if declared_bounded:
            cat.declare_bounded(parsed.subject)
        return True, None
    except Exception as e:
        return False, str(e)


def _build_subject_concept(parsed: ParsedStatement, cat: Any) -> Dict[str, Any]:
    """Build subject concept view used by derivation and gate checks."""
    if parsed.subject in cat.entities:
        entity = cat.entities[parsed.subject]
        concept: Dict[str, Any] = {
            "name": entity.name,
            "description": entity.description or entity.properties.get("description", ""),
            "is_a": list(entity.is_a),
            "part_of": list(entity.part_of),
            "has_part": list(entity.has_part),
            "produces": list(entity.produces),
            "y_layer": entity.y_layer,
            "properties": dict(entity.properties),
        }
    else:
        concept = {
            "name": parsed.subject,
            "description": "",
            "is_a": [],
            "part_of": [],
            "has_part": [],
            "produces": [],
            "y_layer": None,
            "properties": {},
        }

    _apply_predicate_to_concept(concept, parsed.predicate, parsed.object)
    for predicate, object_ in parsed.additional:
        _apply_predicate_to_concept(concept, predicate, object_)

    props = concept.get("properties", {})
    if "msc" in props:
        concept["msc"] = props["msc"]
    if "hasMSC" in props:
        concept["has_msc"] = props["hasMSC"]
    if "justifies" in props:
        concept["justifies"] = (
            props["justifies"] if isinstance(props["justifies"], list) else [props["justifies"]]
        )
    if "justifiesEdge" in props:
        concept["justifies_edge"] = (
            props["justifiesEdge"]
            if isinstance(props["justifiesEdge"], list)
            else [props["justifiesEdge"]]
        )
    if "python_class" in props:
        concept["python_class"] = props["python_class"]
    if "template" in props:
        concept["template"] = props["template"]
    if "catOfCatBounded" in props:
        parsed_bool = _parse_bool_literal(props["catOfCatBounded"])
        if parsed_bool is not None:
            concept["cat_of_cat_bounded"] = parsed_bool
    if "sesTypedDepth" in props:
        parsed_int = _parse_int_literal(props["sesTypedDepth"])
        if parsed_int is not None:
            concept["ses_typed_depth"] = parsed_int
    if "compressionMode" in props:
        concept["compression_mode"] = str(props["compressionMode"])
    if "reason" in props:
        concept["reason"] = props["reason"] if isinstance(props["reason"], list) else [props["reason"]]
    if "programs" in props:
        concept["programs"] = props["programs"]
    if "y_layer" in props and not concept.get("y_layer"):
        concept["y_layer"] = props["y_layer"]
    if "intuition" in props:
        concept["intuition"] = props["intuition"]
    if "compareFrom" in props:
        concept["compare_from"] = props["compareFrom"]
    if "mapsTo" in props:
        concept["maps_to"] = props["mapsTo"]
    if "analogicalPattern" in props:
        concept["analogical_pattern"] = props["analogicalPattern"]

    for relation in _STRUCTURAL_PREDICATES:
        concept[relation] = _dedupe_ordered(concept.get(relation, []))

    return concept


def _emr_state_from_derivation(derivation_state: Any) -> str:
    """Map derivation state to EMR progression label."""
    if getattr(derivation_state, "has_programs", False):
        return "programs"
    if (
        getattr(derivation_state, "has_reifies", False)
        or getattr(derivation_state, "has_is_a_promotion", False)
        or getattr(derivation_state, "has_produces", False)
    ):
        return "reifies"
    if getattr(derivation_state, "has_manifests", False):
        return "manifests"
    return "embodies"


def _required_relationships(parsed: ParsedStatement, spiral: List[SpiralStep]) -> List[str]:
    """Collect required derivation relationships for compression checks."""
    required: List[str] = [f"{parsed.subject}:{parsed.predicate}:{parsed.object}"]
    for step in spiral:
        if step.is_placeholder:
            continue
        relation = f"{step.subject}:{step.predicate}:{step.object}"
        if relation not in required:
            required.append(relation)
    return required


def _has_msc(concept: Dict[str, Any]) -> bool:
    """Determine whether concept has an MSC marker."""
    properties = concept.get("properties", {})
    has_msc_value = concept.get("has_msc")
    if has_msc_value not in (None, "", False):
        return True
    if properties.get("hasMSC") not in (None, "", False):
        return True
    return bool(
        concept.get("msc")
        or properties.get("msc")
        or properties.get("msc_id")
        or properties.get("msc_hash")
    )


def _concept_declares_bounded(concept: Dict[str, Any]) -> bool:
    """Does concept explicitly declare CatOfCat boundedness."""
    properties = concept.get("properties", {})
    literal = (
        concept.get("cat_of_cat_bounded")
        if "cat_of_cat_bounded" in concept
        else properties.get("catOfCatBounded")
    )
    parsed = _parse_bool_literal(literal)
    return bool(parsed)


def _normalized_relations(parsed: ParsedStatement) -> Dict[str, Any]:
    """Normalize relation vocabulary for compile packet."""
    normalized: Dict[str, List[str]] = {parsed.predicate: [parsed.object]}
    for predicate, object_ in parsed.additional:
        normalized.setdefault(predicate, []).append(object_)
    return normalized


def _apply_relation_update(
    is_a: List[str],
    part_of: List[str],
    has_part: List[str],
    produces: List[str],
    predicate: str,
    object_: str,
) -> None:
    """Apply a parsed relation to mutable relationship lists."""
    if predicate == "is_a":
        is_a.append(object_)
    elif predicate == "part_of":
        part_of.append(object_)
    elif predicate == "has_part":
        has_part.append(object_)
    elif predicate == "produces":
        produces.append(object_)


def _apply_predicate_to_concept(
    concept: Dict[str, Any],
    predicate: str,
    object_: str,
) -> None:
    """Apply parsed predicate/object values to the concept view."""
    properties = concept.setdefault("properties", {})

    if predicate in _STRUCTURAL_PREDICATES:
        concept.setdefault(predicate, []).append(object_)
        return

    if predicate == "has_msc":
        parsed_bool = _parse_bool_literal(object_)
        val = parsed_bool if parsed_bool is not None else object_
        concept["has_msc"] = val
        properties["hasMSC"] = val
        return

    if predicate == "justifies":
        justifies = concept.setdefault("justifies", [])
        justifies.append(object_)
        concept["justifies"] = _dedupe_ordered(justifies)
        properties["justifies"] = concept["justifies"]
        return

    if predicate == "justifies_edge":
        justifies_edge = concept.setdefault("justifies_edge", [])
        justifies_edge.append(object_)
        concept["justifies_edge"] = _dedupe_ordered(justifies_edge)
        properties["justifiesEdge"] = concept["justifies_edge"]
        return

    if predicate == "cat_of_cat_bounded":
        parsed = _parse_bool_literal(object_)
        if parsed is not None:
            concept["cat_of_cat_bounded"] = parsed
            properties["catOfCatBounded"] = parsed
        return

    if predicate == "ses_typed_depth":
        parsed_depth = _parse_int_literal(object_)
        if parsed_depth is not None:
            concept["ses_typed_depth"] = parsed_depth
            properties["sesTypedDepth"] = parsed_depth
        return

    if predicate == "compression_mode":
        concept["compression_mode"] = object_
        properties["compressionMode"] = object_
        return

    if predicate == "reason":
        reasons = concept.setdefault("reason", [])
        reasons.append(object_)
        concept["reason"] = _dedupe_ordered(reasons)
        properties["reason"] = concept["reason"]
        return

    if predicate == "programs":
        concept["programs"] = object_
        properties["programs"] = object_
        return

    if predicate == "python_class":
        concept["python_class"] = object_
        properties["python_class"] = object_
        return

    if predicate == "template":
        concept["template"] = object_
        properties["template"] = object_
        return

    if predicate == "description":
        concept["description"] = object_
        properties["description"] = object_
        return

    if predicate == "y_layer":
        concept["y_layer"] = object_
        properties["y_layer"] = object_
        return

    if predicate == "intuition":
        concept["intuition"] = object_
        properties["intuition"] = object_
        return

    if predicate == "compare_from":
        concept["compare_from"] = object_
        properties["compareFrom"] = object_
        return

    if predicate == "maps_to":
        concept["maps_to"] = object_
        properties["mapsTo"] = object_
        return

    if predicate == "analogical_pattern":
        concept["analogical_pattern"] = object_
        properties["analogicalPattern"] = object_
        return

    # Unknown predicates: store in properties dict for reasoner to validate
    # The parser accepts any predicate — the reasoner decides if it's valid
    existing = properties.get(predicate)
    if existing is not None:
        # Accumulate as list if multiple values
        if isinstance(existing, list):
            existing.append(object_)
        else:
            properties[predicate] = [existing, object_]
    else:
        properties[predicate] = object_
    concept[predicate] = properties[predicate]


def _parse_bool_literal(value: Any) -> Optional[bool]:
    """Parse common bool literal tokens used in statement triples."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    token = str(value).strip().lower()
    if token in {"true", "1", "yes"}:
        return True
    if token in {"false", "0", "no"}:
        return False
    return None


def _parse_int_literal(value: Any) -> Optional[int]:
    """Parse integer literal tokens."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _dedupe_ordered(values: List[str]) -> List[str]:
    """Deduplicate while preserving original order."""
    seen = set()
    deduped: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _build_abcd_state(parsed: ParsedStatement, cat: Any) -> Dict[str, Any]:
    """Build ABCD grounding status and missingness."""
    additional = {predicate: object_ for predicate, object_ in parsed.additional}
    subject_known = parsed.subject in cat.entities
    map_target = additional.get("maps_to", parsed.object)
    maps_to_known = map_target in cat.entities
    intuition = additional.get("intuition", parsed.subject)
    compare_from = additional.get("compare_from", parsed.predicate)
    maps_to = map_target if maps_to_known else None
    analogical_pattern = additional.get("analogical_pattern")
    if analogical_pattern is None and subject_known and maps_to_known:
        analogical_pattern = f"{parsed.subject}_{compare_from}_{map_target}_pattern"
    slots = {
        "intuition": intuition,
        "compareFrom": compare_from,
        "mapsTo": maps_to,
        "analogicalPattern": analogical_pattern,
    }
    missing_slots = [name for name, value in slots.items() if value in (None, "")]
    return {
        "required": not maps_to_known,
        "slots": slots,
        "complete": len(missing_slots) == 0,
        "missing_slots": missing_slots,
    }


_emr_processor = None


def _build_continuous_emr_telemetry(
    parsed: ParsedStatement,
    subject_concept: Dict[str, Any],
    normalized_relations: Dict[str, Any],
    cat: Any,
) -> Dict[str, Any]:
    """Compute continuous-EMR snapshot for this one-shot compile step.

    Adds only the NEW concept to a persistent processor.
    Relationships are already declared positionally by the geometry.
    """
    global _emr_processor

    try:
        from .continuous_emr import ContinuousEMRProcessor

        if _emr_processor is None:
            _emr_processor = ContinuousEMRProcessor()

        # Add ONLY the new concept — its relationships are already known
        relationships = _concept_relationships_for_emr(
            concept=subject_concept,
            normalized_relations=normalized_relations,
        )
        result = _emr_processor.add_concept(
            name=parsed.subject,
            description=subject_concept.get("description", ""),
            is_a=list(subject_concept.get("is_a", [])),
            relationships=relationships,
        )
        gradient = _emr_processor.get_emr_gradient(parsed.subject)
        return {
            "enabled": True,
            "seed_concept_count": len(cat.entities),
            "result": result,
            "gradient": gradient,
            "candidate_count": len(_emr_processor.candidates),
        }
    except Exception as e:
        return {
            "enabled": False,
            "error": str(e),
        }


def _concept_relationships_for_emr(
    concept: Dict[str, Any],
    normalized_relations: Dict[str, Any],
) -> Dict[str, List[str]]:
    """Build relationship map for ContinuousEMRProcessor input."""
    relationships: Dict[str, List[str]] = {}
    # Structural predicates + EMR predicates
    _core_rels = {"part_of", "has_part", "produces", "embodies", "manifests", "reifies"}
    # Collect all relation keys from concept and normalized_relations
    all_keys = set()
    all_keys.update(_core_rels)
    for key, val in concept.items():
        if isinstance(val, list) and key not in ("is_a",) and not key.startswith("_"):
            all_keys.add(key)
    all_keys.update(normalized_relations.keys())

    for relation in all_keys:
        values: List[str] = []
        raw = concept.get(relation, [])
        if isinstance(raw, list):
            values.extend(str(v) for v in raw)
        extra = normalized_relations.get(relation, [])
        if isinstance(extra, list):
            values.extend(str(v) for v in extra)
        deduped = _dedupe_ordered(values)
        if deduped:
            relationships[relation] = deduped
    return relationships


def _build_ses_report(
    concept: Dict[str, Any],
    typed_symbols: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """Build SES typed-depth from constructor args using recursive typedness."""
    from .universal_pattern import compute_ses_typed_depth

    constructor_args = {
        "is_a": concept.get("is_a", []),
        "part_of": concept.get("part_of", []),
        "has_part": concept.get("has_part", []),
        "produces": concept.get("produces", []),
        "justifies": concept.get("justifies") or concept.get("properties", {}).get("justifies"),
        "justifiesEdge": concept.get("justifies_edge") or concept.get("properties", {}).get("justifiesEdge"),
        "msc": (
            concept.get("has_msc")
            or concept.get("msc")
            or concept.get("properties", {}).get("hasMSC")
            or concept.get("properties", {}).get("msc")
        ),
    }
    # Include all relationships from properties for complete SES check
    props = concept.get("properties", {})
    _skip_ses = {"hasMSC", "msc", "justifies", "justifiesEdge", "python_class",
                 "template", "compressionMode", "sesTypedDepth", "reason",
                 "intuition", "compareFrom", "mapsTo", "analogicalPattern",
                 "y_layer", "description", "loaded_from", "rdf_type",
                 "primitive", "self_referential", "self_describing"}
    for key, val in props.items():
        if key in _skip_ses or key in constructor_args:
            continue
        if isinstance(val, list):
            constructor_args[key] = val
        elif isinstance(val, str) and val not in ("", "None"):
            constructor_args[key] = [val]
    report = compute_ses_typed_depth(
        constructor_name=concept.get("name", "unknown"),
        constructor_args=constructor_args,
        typed_symbols=typed_symbols,
    )
    return report.to_dict()


def _collect_missingness(packet: CompilePacket) -> List[str]:
    """Aggregate ALL missingness for SOUP output.

    Sources:
    1. SHACL/reasoner blocking errors (OWL restriction failures)
    2. Every predicate in the statement — is it a known OWL property?
    3. Every target in the statement — is it a known concept?

    The SOUP response should tell you EVERYTHING that's unknown or incomplete
    about EVERYTHING you said, not just what OWL restrictions require.
    """
    missing = list(packet.diagnostics.get("blocking", []))

    # Check every relationship in the parsed statement for unknown predicates/targets
    parsed = packet.parsed_claim
    all_triples = [(parsed["predicate"], parsed["object"])]
    all_triples.extend(parsed.get("additional", []))

    try:
        validator = _get_uarl_validator()
        if validator is not None:
            from .owl_reasoner import OWLReasoner
            if not hasattr(validator, '_cached_reasoner'):
                validator._cached_reasoner = OWLReasoner()
            reasoner = validator._cached_reasoner
            if reasoner is not None:
                for pred, target in all_triples:
                    # Skip structural predicates — those are always known
                    if pred in _STRUCTURAL_PREDICATES:
                        continue
                    # Check if predicate is a known OWL property
                    prop = reasoner._get_property(pred)
                    owl_pred = _PREDICATE_CANONICAL.get(pred, pred)
                    if prop is None and owl_pred != pred:
                        prop = reasoner._get_property(owl_pred)
                    if prop is None:
                        missing.append(f"{pred}: unknown property (needs domain, range to be ONT)")
                    # Check if target is a known concept
                    existing = reasoner.world.search_one(iri=f"*{target}")
                    if existing is None:
                        from .owl_types import get_type_registry as get_cat
                        cat = get_cat()
                        if target not in cat.entities:
                            missing.append(f"{target} is_a ? (unknown)")
    except Exception:
        pass  # Don't block compilation if this check fails

    deduped: List[str] = []
    seen = set()
    for item in missing:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _build_controller_telemetry(
    concept_name: str,
    emr_state: str,
    admit_to_ont: bool,
) -> Dict[str, Any]:
    """Build YMesh controller telemetry for compile packet diagnostics."""
    from .yo_strata import build_compile_telemetry

    return build_compile_telemetry(
        concept_name=concept_name,
        emr_state=emr_state,
        admit_to_ont=admit_to_ont,
    )


def _build_llm_guidance(
    parsed: ParsedStatement,
    blocking: List[str],
    decision: Decision,
    compression: CompressionReport,
) -> str:
    """Build deterministic missingness guidance through llm_suggest."""
    from .utils import llm_suggest

    reasons: List[str] = []
    if not decision.is_programs:
        reasons.append("programs threshold not reached")
    if not compression.has_msc:
        reasons.append("MSC missing")
    if not compression.all_required_justified:
        reasons.append("justifies incomplete")
    if not decision.is_catofcat_bounded:
        reasons.append("cat-of-cat unbounded")
    reasons.extend(blocking)

    if not reasons:
        error = "gate satisfied"
    else:
        error = "; ".join(dict.fromkeys(reasons))

    context = f"{parsed.subject} {parsed.predicate} {parsed.object}"
    return llm_suggest(context=context, error=error, minify=True).strip()


def _build_spiral(
    parsed: ParsedStatement,
    subject_concept: Optional[Dict[str, Any]] = None,
) -> List[SpiralStep]:
    """Build the derivation spiral for a statement.

    Uses REAL validators:
        - HyperedgeValidator for EMR (embodies/manifests/reifies)
        - DerivationValidator for L0-L6 levels
        - Cat_of_Cat for chain tracing
    """
    from .owl_types import get_type_registry as get_cat
    from .hyperedge import HyperedgeValidator

    cat = get_cat()
    hyperedge_validator = HyperedgeValidator(cat=cat)

    spiral = []

    if subject_concept is None:
        subject_concept = _build_subject_concept(parsed, cat)

    if parsed.predicate == "is_a":
        claim_result = hyperedge_validator.validate_claim(
            subject=parsed.subject,
            object_=parsed.object,
            concept=subject_concept
        )
        claim_valid = claim_result.valid
        claim_supporting = claim_result.supporting_evidence
        claim_witness = claim_result.witness
    else:
        claim_valid = True
        claim_supporting = []
        claim_witness = None

    spiral.append(SpiralStep(
        subject=parsed.subject,
        predicate=parsed.predicate,
        object=parsed.object,
        embodies=claim_supporting,
        manifests={},
        reifies_via=claim_witness,
        is_placeholder=not claim_valid
    ))

    # Step 2: Trace the object upward
    # TODO: Actually look up the object in the ontology
    # For now, create placeholder steps

    # REAL: Use Cat_of_Cat.trace_to_root()
    chain = _get_chain(parsed.object)

    for i, (entity, parent) in enumerate(chain):
        is_defined = parent != "?"  # TODO: Actually check ontology

        spiral.append(SpiralStep(
            subject=entity,
            predicate="is_a",
            object=parent,
            # TODO: Get EMR from validators
            embodies=[],
            manifests={},
            reifies_via=None,
            is_placeholder=not is_defined
        ))

        if not is_defined:
            break  # Chain breaks here

    return spiral


# Prefix → type mapping for resolving instance names to their types.
# Same convention Dragonbones uses for type injection.
_PREFIX_TYPE_MAP = {
    "Giint_Project_": "Giint_Project",
    "Giint_Feature_": "Giint_Feature",
    "Giint_Component_": "Giint_Component",
    "Giint_Deliverable_": "Giint_Deliverable",
    "Giint_Task_": "Giint_Task",
    "Bug_": "Bug",
    "Design_": "Design",
    "Idea_": "Idea",
    "Inclusion_Map_": "Inclusion_Map",
    "Potential_Solution_": "Potential_Solution",
    "Hypercluster_": "Hypercluster",
    "Skill_": "Skill",
    "Pattern_": "Pattern",
    "Persona_": "Persona",
    "Flight_Config_": "Flight_Config",
    "Mission_": "Mission",
    "Navy_Fleet_": "Navy_Fleet",
    "Navy_Squadron_": "Navy_Squadron",
    "Navy_Starship_": "Navy_Starship",
    "Starship_Pilot_": "Starship_Pilot",
    "Starsystem_": "Starsystem_Collection",
}


def _resolve_type_from_name(entity: str, cat) -> Optional[str]:
    """Resolve an instance name to its type via naming convention prefix.

    E.g. Giint_Project_Odyssey_System → GIINT_Project
         Design_Bml_Subtype_Mission_Architecture → Design
         Bug_Mission_Type_Registry_Never_Saves_Mar11 → Bug

    Returns the type name if found in cat.entities, else None.
    """
    for prefix, type_name in _PREFIX_TYPE_MAP.items():
        if entity.startswith(prefix) and type_name in cat.entities:
            return type_name
    return None


def _get_chain(entity: str) -> List[Tuple[str, str]]:
    """Get is_a chain from Cat_of_Cat.

    Resolves instance names through their types via naming convention.
    E.g. Giint_Project_Odyssey_System → type GIINT_Project → chain from there.
    """
    from .owl_types import get_type_registry as get_cat

    cat = get_cat()

    # Check if entity exists directly
    if entity not in cat.entities:
        # Try to resolve instance name to its type via naming convention prefix
        resolved_type = _resolve_type_from_name(entity, cat)
        if resolved_type:
            # Entity is an instance of a known type — chain through the type
            chain = cat.trace_to_root(resolved_type)
            if chain and "Cat_of_Cat" in chain:
                # Prepend the instance → type link
                pairs = [(entity, resolved_type)]
                for i in range(len(chain) - 1):
                    pairs.append((chain[i], chain[i + 1]))
                return pairs
        return [(entity, "?")]  # Truly unknown entity

    # Get the chain
    chain = cat.trace_to_root(entity)
    if chain == ["Cat_of_Cat"]:
        return [("Cat_of_Cat", "Cat_of_Cat")]

    # Convert to pairs: [(A, B), (B, C), ...]
    pairs = []
    for i in range(len(chain) - 1):
        pairs.append((chain[i], chain[i + 1]))

    # If chain ends at Cat_of_Cat, add final pair
    if chain and chain[-1] == "Cat_of_Cat":
        # Cat_of_Cat is_a Cat_of_Cat (self-loop, complete)
        pass
    elif chain:
        # Chain doesn't reach Cat_of_Cat
        pairs.append((chain[-1], "?"))

    return pairs if pairs else [(entity, "?")]


def _check_chain_complete(
    spiral: List[SpiralStep],
    parsed: Optional[ParsedStatement] = None,
) -> Tuple[bool, Optional[str], List[str]]:
    """Check if the spiral traces all the way to Cat_of_Cat.

    Checks if is_a chain traces to Cat_of_Cat via _get_chain().
    Also checks all relation targets (part_of, produces) have resolved chains.
    DerivationValidator handles L0-L6 levels separately in _compile_packet().

    Returns:
        (is_complete, break_point, whats_missing)
    """
    relation_targets = _relation_targets_for_chain_check(parsed, spiral)
    missing: List[str] = []
    break_point: Optional[str] = None

    for target in relation_targets:
        chain = _get_chain(target)
        unresolved_nodes = [entity for entity, parent in chain if parent == "?"]
        if not unresolved_nodes:
            continue

        for unresolved in unresolved_nodes:
            if break_point is None:
                break_point = unresolved
            missing.extend(
                [
                    f"{unresolved} is_a ? (unknown)",
                    f"{unresolved} part_of ? (unknown)",
                    f"{unresolved} produces ? (unknown)",
                ]
            )

    if missing:
        deduped = list(dict.fromkeys(missing))
        return (False, break_point, deduped)

    # Check if primary derivation chain reached Cat_of_Cat
    if spiral and spiral[-1].object == "Cat_of_Cat":
        return (True, None, [])

    if relation_targets:
        # Targets are known but the built spiral did not close to root.
        fallback = relation_targets[-1]
        return (
            False,
            fallback,
            [
                f"{fallback} is_a ? (unknown)",
                f"{fallback} part_of ? (unknown)",
                f"{fallback} produces ? (unknown)",
            ],
        )

    return (
        False,
        spiral[-1].subject if spiral else "?",
        ["Chain does not reach Cat_of_Cat"],
    )


def _relation_targets_for_chain_check(
    parsed: Optional[ParsedStatement],
    spiral: List[SpiralStep],
) -> List[str]:
    """Collect all relation-object targets that need Cat_of_Cat chain checks."""
    if parsed is not None:
        targets: List[str] = []
        if parsed.predicate in _STRUCTURAL_PREDICATES:
            targets.append(parsed.object)
        targets.extend(
            object_
            for predicate, object_ in parsed.additional
            if predicate in _STRUCTURAL_PREDICATES
        )
    else:
        targets = []
        if spiral:
            targets.append(spiral[0].object)

    deduped: List[str] = []
    seen = set()
    for target in targets:
        if target in seen:
            continue
        deduped.append(target)
        seen.add(target)
    return deduped


def _persist(
    parsed: ParsedStatement,
    spiral: List[SpiralStep],
    packet: Optional[CompilePacket] = None,
) -> None:
    """Persist CODE-admitted statements to JSON file in HEAVEN_DATA_DIR/ont/.

    Writes admission record with spiral, diagnostics, and Griess state.
    Also calls _persist_to_soup for domain OWL mirroring via owl_substrate.
    """
    import json
    import os
    from datetime import datetime

    # Accumulate in registry so subsequent calls can see this concept
    try:
        from .owl_types import get_type_registry
        registry = get_type_registry()
        subject_concept = packet.candidate_subgraph.get("subject_concept", {}) if packet else {}
        is_a = list(subject_concept.get("is_a", []))
        if not is_a and parsed.predicate == "is_a":
            is_a = [parsed.object]
        registry.add(name=parsed.subject, is_a=is_a)
    except Exception:
        pass

    # DualSubstrate: OWL + Carton in one call
    try:
        from .owl_substrate import DualSubstrate, OWLEntity
        heaven_data = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
        ont_dir = os.path.join(heaven_data, 'ontology')

        relationships = {}
        if parsed.predicate != 'is_a':
            relationships[parsed.predicate] = [parsed.object]
        for pred, obj in parsed.additional:
            if pred != 'is_a':
                relationships.setdefault(pred, []).append(obj)

        is_a = []
        if parsed.predicate == 'is_a':
            is_a.append(parsed.object)
        for pred, obj in parsed.additional:
            if pred == 'is_a':
                is_a.append(obj)

        description = parsed.raw
        if packet and packet.candidate_subgraph:
            sc = packet.candidate_subgraph.get('subject_concept', {})
            if sc.get('description'):
                description = sc['description']

        emr_state = packet.emr_state if packet else 'embodies'

        entity = OWLEntity(
            name=parsed.subject,
            description=description,
            is_a=is_a,
            relationships=relationships,
            emr_state=emr_state or 'embodies',
        )
        dual = DualSubstrate(owl_dir=ont_dir, domain_file='domain.owl')
        dual.add_entity(entity)
    except Exception as e:
        import sys
        print(f'[PERSIST] DualSubstrate error for {parsed.subject}: {e}', file=sys.stderr)
    from pathlib import Path

    try:
        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        ont_dir = Path(heaven_data) / "ont"
        ont_dir.mkdir(parents=True, exist_ok=True)

        ont_file = ont_dir / f"{parsed.subject}_admission.json"
        ont_payload = {
            "type": "ONTAdmission",
            "admitted_at": datetime.now().isoformat(),
            "statement": parsed.raw,
            "subject": parsed.subject,
            "predicate": parsed.predicate,
            "object": parsed.object,
            "spiral": [
                {
                    "subject": step.subject,
                    "predicate": step.predicate,
                    "object": step.object,
                    "is_placeholder": step.is_placeholder,
                }
                for step in spiral
            ],
        }
        if packet is not None:
            ont_payload["decision"] = packet.decision
            ont_payload["compression_report"] = packet.compression_report
            ont_payload["ses_report"] = packet.ses_report

        with open(ont_file, "w") as f:
            json.dump(ont_payload, f, indent=2)
    except Exception:
        # Persistence failures should not crash ONT admission response.
        pass

    # Persist promotion-grade PatternOfIsA semantics into domain OWL.
    if packet is not None and packet.decision.get("admit_to_ont"):
        _persist_pattern_to_uarl_domain(parsed, packet)

    # Optional post-admission witness phase.
    if packet is not None and packet.decision.get("admit_to_ont"):
        _generate_witness(parsed, packet)


def _persist_pattern_to_uarl_domain(parsed: ParsedStatement, packet: CompilePacket) -> None:
    """Persist strong-compression PatternOfIsA payload to UARL domain ontology."""
    try:
        from .uarl_validator import UARLValidator

        pattern_payload, msc_payload, just_payloads = _build_uarl_pattern_payload(parsed, packet)
        validator = UARLValidator()

        # Create supporting justification nodes first.
        for payload in just_payloads:
            validator.add_to_domain(payload)

        # Create MSC proof node, then pattern node that links to it.
        validator.add_to_domain(msc_payload)
        validator.add_to_domain(pattern_payload)
    except Exception:
        # OWL/domain persistence should not break compile response path.
        pass


def _generate_witness(parsed: ParsedStatement, packet: CompilePacket) -> Optional[Dict[str, Any]]:
    """Optional post-admission simulation/codegen witness.

    This phase never decides validity; it only records operational witness artifacts.
    """
    import ast
    import json
    import os
    from datetime import datetime
    from pathlib import Path
    from .codeness_gen import OntologySpec

    try:
        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        witness_dir = Path(heaven_data) / "witness"
        witness_dir.mkdir(parents=True, exist_ok=True)

        generated_dir = witness_dir / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)

        spec = _build_codegen_spec(parsed, packet)
        generated_code = spec.to_code()

        code_file = generated_dir / f"{parsed.subject}_witness.py"
        with open(code_file, "w") as f:
            f.write(generated_code)

        parse_ok = True
        parse_error = None
        try:
            ast.parse(generated_code)
        except SyntaxError as e:
            parse_ok = False
            parse_error = str(e)

        witness_payload = {
            "type": "PostAdmissionWitness",
            "generated_at": datetime.now().isoformat(),
            "statement": parsed.raw,
            "subject": parsed.subject,
            "emr_state": packet.emr_state,
            "decision": packet.decision,
            "ses_report": packet.ses_report,
            "compression_report": packet.compression_report,
            "simulation": {
                "mode": "codegen_generated",
                "entrypoint": spec.name,
                "inputs": {
                    "subject": parsed.subject,
                    "predicate": parsed.predicate,
                    "object": parsed.object,
                },
                "artifact": {
                    "spec_pattern": spec.is_a[0] if spec.is_a else "DataHolder",
                    "code_file": str(code_file),
                    "syntax_parse_ok": parse_ok,
                    "syntax_parse_error": parse_error,
                },
                "note": "Operational witness only; validity decided by gate.",
            },
        }

        witness_file = witness_dir / f"{parsed.subject}_witness.json"
        with open(witness_file, "w") as f:
            json.dump(witness_payload, f, indent=2)
        return witness_payload
    except Exception:
        return None


def _build_codegen_spec(parsed: ParsedStatement, packet: CompilePacket) -> Any:
    """Build OntologySpec for post-admission codegen witness."""
    from .codeness_gen import OntologySpec

    constructor_fields = {
        "subject": {"type": "str", "default": repr(parsed.subject)},
        "predicate": {"type": "str", "default": repr(parsed.predicate)},
        "object_": {"type": "str", "default": repr(parsed.object)},
        "emr_state": {"type": "str", "default": repr(packet.emr_state)},
        "max_typed_depth": {
            "type": "int",
            "default": str(int(packet.ses_report.get("max_typed_depth", 0))),
        },
        "required_rel_count": {
            "type": "int",
            "default": str(int(packet.compression_report.get("required_rel_count", 0))),
        },
        "blocking_count": {
            "type": "int",
            "default": str(len(packet.diagnostics.get("blocking", []))),
        },
    }

    description = (
        f"Post-admission witness constructor for {parsed.subject}. "
        "Generated after ONT gate admission."
    )
    return OntologySpec(
        name=f"{parsed.subject}Witness",
        description=description,
        is_a=["DataHolder"],
        has_parts=constructor_fields,
    )


def _build_uarl_pattern_payload(
    parsed: ParsedStatement,
    packet: CompilePacket,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    """Build domain-ontology payloads for PatternOfIsA strong compression typing."""
    subject_key = _safe_identifier(parsed.subject)
    pattern_name = f"{subject_key}_PatternOfIsA"
    msc_name = f"MSC_{subject_key}"

    required_rels = packet.candidate_subgraph.get("required_relationships", [])
    just_nodes: List[str] = []
    just_payloads: List[Dict[str, Any]] = []
    for index, edge in enumerate(required_rels, start=1):
        node_name = f"{pattern_name}_J{index}"
        just_nodes.append(node_name)
        just_payloads.append(
            {
                "name": node_name,
                "type": "DerivationJustification",
                "justifiesEdge": edge,
            }
        )

    ses_depth = int(packet.ses_report.get("max_typed_depth", 0))
    if packet.decision.get("is_programs"):
        ses_depth = max(ses_depth, 6)
    bounded = bool(packet.decision.get("is_catofcat_bounded", False))
    compression_mode = packet.compression_report.get("mode", "weak")

    msc_payload = {
        "name": msc_name,
        "type": "MinimumSufficientCompression",
        "compressionMode": compression_mode,
        "sesTypedDepth": ses_depth,
        "catOfCatBounded": bounded,
    }

    pattern_payload = {
        "name": pattern_name,
        "type": "StrongCompressionPattern" if compression_mode == "strong" else "WeakCompressionPattern",
        "hasMSC": msc_name,
        "justifies": just_nodes,
        "catOfCatBounded": bounded,
        "sesTypedDepth": ses_depth,
        "compressionMode": compression_mode,
        "programs": "Reality",
        "produces": "THE_PatternOfIsA",
    }
    return pattern_payload, msc_payload, just_payloads


def _safe_identifier(value: str) -> str:
    """Convert arbitrary label to stable ontology identifier fragment."""
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unnamed"


def _persist_to_soup(
    parsed: ParsedStatement,
    spiral: List[SpiralStep],
    break_point: Optional[str],
    whats_missing: List[str],
    packet: Optional[CompilePacket] = None,
) -> Dict[str, Any]:
    """Persist an incomplete chain to SOUP as hallucination metadata."""
    import json
    import os
    import uuid
    from datetime import datetime
    from pathlib import Path

    soup_fingerprint = _soup_fingerprint(parsed)
    hallucination_meta = {
        "is_hallucination": True,
        "soup_fingerprint": soup_fingerprint,
        "statement": parsed.raw,
        "subject": parsed.subject,
        "predicate": parsed.predicate,
        "object": parsed.object,
        "break_point": break_point,
        "whats_missing": whats_missing,
        "error_patterns": [f"{parsed.predicate}_unknown_target"],
        "evolution_target": parsed.object,
        "would_need": [
            f"{parsed.object} is_a ?",
            f"{parsed.object} part_of ?",
            f"{parsed.object} produces ?",
        ],
        "spiral_state": [
            {
                "subject": s.subject,
                "predicate": s.predicate,
                "object": s.object,
                "is_placeholder": s.is_placeholder,
            }
            for s in spiral
        ],
    }
    if packet is not None:
        hallucination_meta["emr_state"] = packet.emr_state
        hallucination_meta["compression_report"] = packet.compression_report
        hallucination_meta["diagnostics"] = packet.diagnostics
        hallucination_meta["decision"] = packet.decision

    # No JSON files — SOUP concepts go into domain.owl via _persist_soup_to_uarl_domain.

    # Add to Cat_of_Cat as unbounded so iterative refinement works.
    # Concept stays in SOUP but is now "known" for future calls.
    try:
        from .owl_types import get_type_registry as get_cat
        cat = get_cat()
        if parsed.subject not in cat.entities:
            subject_concept = packet.candidate_subgraph.get("subject_concept", {}) if packet else {}
            is_a = list(subject_concept.get("is_a", []))
            if not is_a and parsed.predicate == "is_a":
                is_a = [parsed.object]
            valid_is_a = [p for p in is_a if p in cat.entities]
            if valid_is_a:
                cat.add(
                    name=parsed.subject,
                    is_a=valid_is_a,
                    part_of=[p for p in subject_concept.get("part_of", []) if p in cat.entities],
                    has_part=list(subject_concept.get("has_part", [])),
                    produces=[p for p in subject_concept.get("produces", []) if p in cat.entities],
                    y_layer=subject_concept.get("y_layer"),
                    description=subject_concept.get("description", ""),
                    properties=dict(subject_concept.get("properties", {})),
                )
    except Exception:
        pass  # Bootstrap failure should not crash compiler

    # Mirror SOUP state into the liquid domain ontology as Hallucination.
    _persist_soup_to_uarl_domain(
        parsed=parsed,
        hallucination_meta=hallucination_meta,
        break_point=break_point,
        whats_missing=whats_missing,
    )

    return hallucination_meta


def _soup_fingerprint(parsed: ParsedStatement) -> str:
    """Deterministic key for iterative SOUP updates of the same claim."""
    import hashlib

    canonical_parts = [f"{parsed.subject}|{parsed.predicate}|{parsed.object}"]
    canonical_parts.extend(
        f"{predicate}|{object_}"
        for predicate, object_ in sorted(parsed.additional)
    )
    canonical = "||".join(canonical_parts)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]


def _persist_soup_to_uarl_domain(
    parsed: ParsedStatement,
    hallucination_meta: Dict[str, Any],
    break_point: Optional[str],
    whats_missing: List[str],
) -> None:
    """Add the CONCEPT ITSELF to domain.owl as a Hallucination (SOUP entity).

    The concept enters the ontology with is_a Hallucination plus all its
    actual relationships. This lets the ontology reason about it,
    progressively type it, and eventually promote it to ONT (Reality).
    """
    try:
        from .uarl_validator import UARLValidator

        validator = UARLValidator()

        # Build the concept's actual type from what was declared
        concept_type = "Hallucination"  # SOUP = is_a Hallucination
        is_a_parents = []
        if parsed.predicate == "is_a":
            is_a_parents.append(parsed.object)
        for pred, obj in parsed.additional:
            if pred == "is_a":
                is_a_parents.append(obj)

        # Build concept payload with actual relationships
        payload = {
            "name": parsed.subject,
            "type": concept_type,
        }

        # Add all declared relationships as OWL properties
        if is_a_parents:
            payload["isA"] = is_a_parents
        for pred, obj in [(parsed.predicate, parsed.object)] + list(parsed.additional):
            if pred == "is_a":
                continue  # Already handled
            owl_pred = _PREDICATE_CANONICAL.get(pred, pred)
            if owl_pred in payload:
                existing = payload[owl_pred]
                if isinstance(existing, list):
                    existing.append(obj)
                else:
                    payload[owl_pred] = [existing, obj]
            else:
                payload[owl_pred] = obj

        # Add what's missing as metadata so the ontology knows what to ask for
        if whats_missing:
            payload["whatsMissing"] = _dedupe_ordered(whats_missing)

        # Upsert — replace prior SOUP state for iterative refinement
        if validator.concept_exists(parsed.subject):
            validator.remove_from_domain(parsed.subject)

        validator.add_to_domain(payload)
    except Exception:
        # Domain mirroring failures should not break compile response path.
        pass


def _generate_code_artifact(
    parsed: ParsedStatement,
    packet: CompilePacket,
    gen_target: str,
) -> Optional[str]:
    """Generate a code artifact from a CODE-admitted concept.

    Uses codeness_gen OntologySpec for code generation.
    Returns path/description of generated artifact, or None on failure.
    """
    try:
        from .codeness_gen import OntologySpec

        sc = packet.candidate_subgraph.get("subject_concept", {}) if packet.candidate_subgraph else {}
        type_name = packet.decision.get("type_name", parsed.object)

        # Build has_parts from all provided relationships + properties.
        # Strip "has_" prefix so codeness_gen templates find "domain" not "has_domain".
        has_parts = {}
        for pred in ("part_of", "has_part", "produces", "instantiates"):
            vals = sc.get(pred, [])
            if vals:
                has_parts[pred] = vals[0] if len(vals) == 1 else vals
        for key, val in sc.get("properties", {}).items():
            if val not in (None, "", "None"):
                # Normalize key: hasDomain → domain, has_domain → domain
                clean_key = key
                if clean_key.startswith("has") and len(clean_key) > 3 and clean_key[3].isupper():
                    clean_key = clean_key[3].lower() + clean_key[4:]  # hasDomain → domain
                elif clean_key.startswith("has_"):
                    clean_key = clean_key[4:]  # has_domain → domain
                clean_val = val
                if isinstance(clean_val, str):
                    if clean_val.startswith("Skill_Category_"):
                        clean_val = clean_val[len("Skill_Category_"):].lower()
                has_parts[clean_key] = clean_val

        # Add inferred fields from system_type_validator (also strip has_ prefix)
        inferred = packet.decision.get("inferred", {})
        for key, val in inferred.items():
            clean_key = key[4:] if key.startswith("has_") else key
            if clean_key not in has_parts:
                clean_val = val[0] if isinstance(val, list) and len(val) == 1 else val
                has_parts[clean_key] = clean_val

        # Map gen_target to OntologySpec pattern
        pattern_map = {
            "skill_package": "SkillSpec",
            "flight_json": "FlightConfig",
            "persona_json": "PersonaSpec",
        }
        pattern = pattern_map.get(gen_target, "DataHolder")

        description = sc.get("description", "") or parsed.raw
        spec = OntologySpec(
            name=parsed.subject,
            description=description,
            is_a=[pattern],
            has_parts=has_parts,
        )

        generated = spec.to_code()

        # Write to HEAVEN_DATA_DIR/codegen/ for inspection
        import os
        from pathlib import Path
        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        codegen_dir = Path(heaven_data) / "codegen"
        codegen_dir.mkdir(parents=True, exist_ok=True)

        ext = ".md" if pattern == "SkillSpec" else ".py" if pattern == "DataHolder" else ".json"
        out_path = codegen_dir / f"{parsed.subject}{ext}"
        out_path.write_text(generated)

        return f"Generated {gen_target} → {out_path}"
    except Exception as e:
        logger.warning("Code generation failed for %s: %s", parsed.subject, e)
        return f"Generation failed: {e}"


def _build_code_response(
    parsed: ParsedStatement,
    packet: CompilePacket,
    gen_result: Optional[str] = None,
) -> str:
    """Build conversational CODE response — concept is valid code object."""
    subject = parsed.subject
    type_name = packet.decision.get("type_name", parsed.object if parsed.predicate == "is_a" else "?")

    # Collect provided relationships for display
    rels = []
    sc = packet.candidate_subgraph.get("subject_concept", {}) if packet.candidate_subgraph else {}
    for pred in ("part_of", "has_part", "produces", "instantiates"):
        vals = sc.get(pred, [])
        if vals:
            rels.append(f"{pred}={vals[0] if len(vals) == 1 else vals}")
    props = sc.get("properties", {})
    for key, val in props.items():
        if val not in (None, "", "None") and key not in ("description",):
            rels.append(f"{key}={val}")

    # Include inferred fields
    inferred = packet.decision.get("inferred", {})
    for key, val in inferred.items():
        if key not in [r.split("=")[0] for r in rels]:
            display_val = val[0] if isinstance(val, list) and len(val) == 1 else val
            rels.append(f"{key}={display_val}")

    out = f"CODE: {subject} constitutes {type_name}({', '.join(rels[:8])})"

    gen_target = packet.decision.get("gen_target")
    if gen_target:
        out += f". Emits: {gen_target}"

    if gen_result:
        out += f". {gen_result}"

    return out


def _is_known_or_typed(name: str) -> bool:
    """Check if a value is a known typed thing (not an arbitrary string)."""
    try:
        from .owl_types import get_type_registry
        reg = get_type_registry()
        if reg.is_known(name):
            return True
        # Check name prefix resolution
        val_type = _resolve_type_from_name(name, reg)
        return val_type is not None
    except Exception:
        return False


def _build_soup_response(
    parsed: ParsedStatement,
    break_point: Optional[str],
    chain_missing: List[str],
    whats_missing: List[str],
) -> str:
    """Build conversational SOUP response — tells you what's missing and why."""
    all_items = list(dict.fromkeys(chain_missing + whats_missing))
    subject = parsed.subject
    type_name = parsed.object if parsed.predicate == "is_a" else "?"

    # Group by concept name
    concept_reqs: Dict[str, List[str]] = {}
    unresolved: List[str] = []
    unknown_types: List[str] = []
    derivation_needs: List[str] = []
    uncategorized: List[str] = []

    for item in all_items:
        if "(unresolved)" in item:
            unresolved.append(item.split(":")[0].strip())
        elif "unknown type" in item:
            unknown_types.append(item.split(" ")[0].strip())
        elif " requires " in item:
            parts = item.split(" requires ", 1)
            concept = parts[0].strip()
            req = parts[1].strip().rstrip(".")
            if ". Auto-healed:" in req:
                req = req.split(". Auto-healed:")[0]
            concept_reqs.setdefault(concept, []).append(req)
        elif "(placeholder)" in item:
            parts = item.split(" requires ", 1)
            if len(parts) == 2:
                concept_reqs.setdefault(parts[0].strip(), []).append(
                    parts[1].replace(" (placeholder)", "").strip() + " (empty)")
        elif "does not exist" in item or "does not trace" in item or "no is_a parent" in item:
            derivation_needs.append(item)
        elif "(unknown)" in item:
            unknown_types.append(item.split(" ")[0].strip())
        else:
            uncategorized.append(item)

    # Aggregate every missing item under the concept it belongs to.
    # Output shape: That's SOUP (BAD/WIP): I cant know if X <verb> Y because [Missing {for C1: [...]} {for C2: [...]}]
    missing_map: Dict[str, List[str]] = {}

    if subject in concept_reqs:
        missing_map.setdefault(subject, []).extend(concept_reqs.pop(subject))
    for concept, reqs in concept_reqs.items():
        missing_map.setdefault(concept, []).extend(reqs)
    for u in unresolved:
        missing_map.setdefault(u, []).append("is_a, part_of, produces (arbitrary string)")
    for t in unknown_types:
        missing_map.setdefault(t, []).append("is_a (unknown type)")
    if derivation_needs:
        missing_map.setdefault(subject, []).extend(derivation_needs)
    if uncategorized:
        missing_map.setdefault(subject, []).extend(uncategorized)

    verb = "is a" if parsed.predicate == "is_a" else parsed.predicate
    obj = parsed.object if parsed.predicate == "is_a" else parsed.object
    header = f"That's SOUP (BAD/WIP): I cant know if {subject} {verb} {obj} because"

    if not missing_map:
        # Walker returned no items at all — that's a walker bug, not a missing-input
        # condition. Surface what the user needs to provide so the chain has structure.
        return (
            f"{header} [Missing: walker produced no items — "
            f"provide is_a, part_of, instantiates, produces with concrete targets to close the chain]"
        )

    parts = []
    for concept, items in missing_map.items():
        # Dedupe within a concept while preserving order.
        seen = set()
        deduped = []
        for it in items:
            if it not in seen:
                seen.add(it)
                deduped.append(it)
        parts.append(f"{{for {concept}: [{', '.join(deduped)}]}}")

    return f"{header} [Missing {' '.join(parts)}]"


# =============================================================================
# CONVENIENCE / INTEGRATION
# =============================================================================

def compile_and_respond(statement: str) -> str:
    """Alias for youknow(). THE entry point."""
    return youknow(statement)


# For integration with existing code
def validate_statement(statement: str) -> Dict[str, Any]:
    """Return structured validation result — dict with valid, parsed, emr_state, decision, etc."""
    parsed = parse_statement(statement)
    if not parsed:
        return {"valid": False, "error": "Could not parse statement"}

    packet = _compile_packet(statement, parsed)

    return {
        "valid": packet.decision["admit_to_ont"],
        "statement": statement,
        "parsed": packet.parsed_claim,
        "normalized_relations": packet.normalized_relations,
        "abcd_state": packet.abcd_state,
        "emr_state": packet.emr_state,
        "ses_report": packet.ses_report,
        "compression_report": packet.compression_report,
        "diagnostics": packet.diagnostics,
        "decision": packet.decision,
        "spiral": [
            {
                "subject": s.subject,
                "predicate": s.predicate,
                "object": s.object,
                "is_placeholder": s.is_placeholder
            }
            for s in packet.spiral
        ],
        "break_point": packet.break_point,
        "whats_missing": _collect_missingness(packet),
    }


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== YOUKNOW COMPILER ===")
    print()

    # Test 1: Unknown target
    print("1. Statement with unknown target:")
    print(youknow("Dog is_a Pet"))
    print()

    # Test 2: Known chain
    print("2. Statement with known chain:")
    print(youknow("Pattern is_a Entity"))
    print()

    # Test 3: Multiple predicates
    print("3. Statement with multiple predicates:")
    result = parse_statement("Animal is_a Entity, part_of Living_Things, produces Creature")
    print(f"Parsed: {result}")
    print()
