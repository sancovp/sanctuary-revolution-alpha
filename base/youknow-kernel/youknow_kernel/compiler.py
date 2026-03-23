#!/usr/bin/env python3
"""
YOUKNOW COMPILER - The ONE Entry Point

This is THE way to interact with YOUKNOW. Everything goes through here.

WHAT THIS IS:
    A tautology-shaping machine that exploits LLM pattern completion to grow ontologies.

    Input: Any statement (e.g., "Dog is_a Animal")
    Output: "You said X. {OK|Wrong} because {because()}"

    The output IS the spiral - a derivation chain that DOES what it SAYS.
    The LLM reads the spiral and completes the placeholders.
    Forward (compiler) + Backward (LLM) = SPIN = Lotus growth.

WHAT'S REAL (implemented):
    - HyperedgeValidator: validates is_a claims against hyperedge context
    - DerivationValidator: checks L0-L6 derivation levels
    - UARLValidator: SHACL validation with conversational error messages
    - DualSubstrate: writes to OWL + mirrors to Carton
    - Cat_of_Cat: traces is_a chains to root

WHAT'S TODO:
    - Statement parser (extract subject/predicate/object from natural language)
    - Spiral form generator (build the full derivation chain as response)
    - Strong compression (use named patterns instead of raw structures)
    - Wiring all validators into the single compile() function

THE SPIRAL FORM:
    "Dog is_a Pet"
    → "Dog is_a Pet" is_a Claim
    → Claim is_a Autology (claiming IS instantiating)
    → Autology is_a Self_Description
    → Self_Description is_a Self_Reference
    → Self_Reference is_a Pattern_Of_Invariance
    → Pattern_Of_Invariance is_a Pattern_Of_Pattern
    → Pattern_Of_Pattern is_a Cat_Of_Pattern
    → Cat_Of_Pattern part_of Cat_Of_Cat

    If chain breaks: "Wrong because Y is_a ?, part_of ?, produces ?"
    If chain closes: "OK because [full spiral with inclusion maps]"

THREE DATA LAYERS:
    1. Foundation OWL (frozen) - core types, SHACL shapes, in library
    2. Domain OWL (dynamic) - user entities, updated every call
    3. Carton (soup) - persistence, reasoner state

STATELESS:
    This compiler has NO memory. NO conversational context.
    The LLM's attention networks keep work coherent.
    YOUKNOW just mirrors truth about each statement independently.
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
    "instantiates": "produces",  # backward compat alias → produces
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
}
_STRUCTURAL_PREDICATES = {"is_a", "part_of", "has_part", "produces"}


# =============================================================================
# RESPONSE TYPES
# =============================================================================

class ResponseType(Enum):
    """Whether the quine closes or breaks."""
    OK = "OK"      # Quine closes - traces to Cat_of_Cat
    WRONG = "Wrong"  # Quine breaks - chain is incomplete


@dataclass
class SpiralStep:
    """One step in the derivation spiral.

    REAL: This data structure exists.
    TODO: Populate it from actual validators.
    """
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
    """The full response from the compiler.

    REAL: This data structure exists.
    TODO: Build it from actual validation.
    """
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
    """A parsed YOUKNOW statement.

    REAL: Basic regex parsing works.
    TODO: Handle complex statements (multiple predicates, nested structures).
    """
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
    """Parse a YOUKNOW statement.

    REAL: Basic pattern matching.
    TODO: More sophisticated NLP parsing, handle edge cases.

    Examples:
        "Dog is_a Animal" → ParsedStatement(Dog, is_a, Animal)
        "Animal is_a Entity, part_of Living_Things" → ParsedStatement with additional
    """
    statement = statement.strip()

    # Pattern: Subject predicate Object [, predicate Object]*
    subject_pattern = r"[A-Za-z0-9_:.+-]+"
    object_pattern = r"(?:\"[^\"]+\"|'[^']+'|[A-Za-z0-9_:.+-]+)"
    predicate_pattern = "|".join(
        sorted(
            (re.escape(name) for name in _PREDICATE_CANONICAL.keys()),
            key=len,
            reverse=True,
        )
    )

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

    WHAT'S REAL:
        - Statement parsing (basic)
        - Response structure

    WHAT'S TODO:
        - Wire to HyperedgeValidator for embodies/manifests/reifies
        - Wire to DerivationValidator for L0-L6 levels
        - Wire to UARLValidator for SHACL validation
        - Wire to Cat_of_Cat for chain tracing
        - Wire to DualSubstrate for persistence
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

    # 9. Persist and render outward response while preserving current style
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
        return "OK"

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
    from .cat_of_cat import get_cat
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

    blocking: List[str] = []
    if not chain_complete:
        blocking.extend(chain_missing)
    if abcd_state["required"] and not abcd_state["complete"]:
        blocking.append(
            "ABCD missing slots: " + ", ".join(abcd_state["missing_slots"])
        )
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
    has_msc = _has_msc(subject_concept)
    compression = CompressionReport(
        has_msc=has_msc,
        required_rel_count=coverage.required_rel_count,
        justified_rel_count=coverage.justified_rel_count,
        all_required_justified=coverage.all_required_justified,
        mode=(
            "strong"
            if has_msc and coverage.all_required_justified
            else "weak"
        ),
    )

    is_programs = emr_state == "programs"
    is_strong_compression = compression.mode == "strong"
    is_catofcat_bounded = (
        cat.is_declared_bounded(parsed.subject)
        or _concept_declares_bounded(subject_concept)
    )
    has_blocking_violations = len(blocking) > 0
    admit_to_ont = (
        is_programs
        and is_strong_compression
        and is_catofcat_bounded
        and not has_blocking_violations
    )

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
        whats_missing=list(chain_missing),
    )


def _admit_to_ontology_state(
    parsed: ParsedStatement,
    packet: CompilePacket,
) -> Tuple[bool, Optional[str]]:
    """Finalize ONT admission by adding the statement through YOUKNOW.add()."""
    try:
        from .core import get_youknow, reset_youknow
        from .cat_of_cat import get_cat

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

        yk.add(
            name=parsed.subject,
            is_a=is_a or [parsed.object],
            part_of=part_of,
            has_part=has_part,
            produces=produces,
            y_layer=subject_concept.get("y_layer"),
            properties=properties,
            description=subject_concept.get("description", ""),
            skip_pipeline=True,
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
    for relation in ("part_of", "has_part", "produces", "embodies", "manifests", "reifies"):
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
    report = compute_ses_typed_depth(
        constructor_name=concept.get("name", "unknown"),
        constructor_args=constructor_args,
        typed_symbols=typed_symbols,
    )
    return report.to_dict()


def _collect_missingness(packet: CompilePacket) -> List[str]:
    """Aggregate explicit missingness for SOUP output and persistence."""
    missing = list(packet.whats_missing)
    decision = packet.decision
    compression = packet.compression_report

    if not decision["is_programs"]:
        missing.append("programs threshold not reached")
    if not compression["has_msc"]:
        missing.append("MSC missing for target entity")
    if not compression["all_required_justified"]:
        missing.append(
            "justifies coverage incomplete "
            f"({compression['justified_rel_count']}/{compression['required_rel_count']})"
        )
    if not decision["is_catofcat_bounded"]:
        missing.append("CatOfCat chain is not declared bounded")

    missing.extend(packet.diagnostics.get("blocking", []))

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
    from .cat_of_cat import get_cat
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


def _get_chain(entity: str) -> List[Tuple[str, str]]:
    """Get is_a chain from Cat_of_Cat.

    REAL: Uses actual CategoryOfCategories.trace_to_root()
    """
    from .cat_of_cat import get_cat

    cat = get_cat()

    # Check if entity exists
    if entity not in cat.entities:
        return [(entity, "?")]  # Unknown entity

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

    WHAT'S REAL:
        - Checks for placeholder steps

    WHAT'S TODO:
        - Use actual DerivationValidator
        - Check L0-L6 levels
        - Verify inclusion maps

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
    """Persist valid statements to domain OWL + Carton.

    WHAT'S REAL:
        - DualSubstrate exists in owl_substrate.py

    WHAT'S TODO:
        - Actually call DualSubstrate.add_entity()
        - Update domain OWL
        - Mirror to Carton
    """
    import json
    import os
    from datetime import datetime
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

    try:
        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        soup_dir = Path(heaven_data) / "soup"
        soup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        soup_file = soup_dir / f"{timestamp}_{soup_fingerprint}_{unique_id}_hallucination.json"

        soup_entry = {
            "type": "Hallucination",
            "created_at": datetime.now().isoformat(),
            "metadata": hallucination_meta,
            "waiting_for": [parsed.object],
            "promoted": False,
            "promoted_at": None,
        }

        with open(soup_file, "w") as f:
            json.dump(soup_entry, f, indent=2)
    except Exception:
        # SOUP persistence should not crash the compiler path.
        pass

    # Add to Cat_of_Cat as unbounded so iterative refinement works.
    # Concept stays in SOUP but is now "known" for future calls.
    try:
        from .cat_of_cat import get_cat
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
    """Upsert Hallucination + Requires_Evolution nodes into domain.owl."""
    try:
        from .uarl_validator import UARLValidator

        validator = UARLValidator()
        soup_fingerprint = str(hallucination_meta.get("soup_fingerprint") or _soup_fingerprint(parsed))
        subject_key = _safe_identifier(parsed.subject)
        hallucination_name = f"Hallucination_{subject_key}_{soup_fingerprint}"
        evolution_name = f"RequiresEvolution_{subject_key}_{soup_fingerprint}"
        pattern_name = f"PartialPattern_{subject_key}_{soup_fingerprint}"
        claim_name = f"SelfClaim_{subject_key}_{soup_fingerprint}"

        error_patterns = [
            str(item) for item in hallucination_meta.get("error_patterns", [])
            if item not in (None, "")
        ] or [f"{parsed.predicate}_unknown_target"]

        missing_items = [
            str(item) for item in whats_missing
            if item not in (None, "")
        ] or [
            str(item) for item in hallucination_meta.get("whats_missing", [])
            if item not in (None, "")
        ]
        if not missing_items:
            missing_items = [f"{parsed.object} is_a ?"]

        traceable_from = [f"pattern:{pattern}" for pattern in error_patterns]
        if break_point:
            traceable_from.append(f"break_point:{break_point}")
        traceable_from = _dedupe_ordered(traceable_from)

        # Replace prior state for this claim so iterative calls update in place.
        for concept_name in (hallucination_name, evolution_name, pattern_name, claim_name):
            if validator.concept_exists(concept_name):
                validator.remove_from_domain(concept_name)

        # Ensure canonical metaphor anchor exists.
        if not validator.concept_exists("THE_Metaphor"):
            validator.add_to_domain(
                {
                    "name": "THE_Metaphor",
                    "type": "Metaphor",
                }
            )

        validator.add_to_domain(
            {
                "name": pattern_name,
                "type": "PartialIsomorphicPattern",
                "patternFragment": _dedupe_ordered(error_patterns + missing_items),
            }
        )
        validator.add_to_domain(
            {
                "name": claim_name,
                "type": "ClaimAboutSelf",
                "claimText": parsed.raw,
            }
        )
        validator.add_to_domain(
            {
                "name": evolution_name,
                "type": "Requires_Evolution",
                "reason": _dedupe_ordered(missing_items),
            }
        )
        # Explicitly assert PIOEntity typing, then Hallucination details.
        validator.add_to_domain(
            {
                "name": hallucination_name,
                "type": "PIOEntity",
                "produces": "THE_Metaphor",
                "hasPartialIsomorphicPattern": [pattern_name],
                "hasSelfClaim": [claim_name],
            }
        )
        validator.add_to_domain(
            {
                "name": hallucination_name,
                "type": "Hallucination",
                "errorPattern": _dedupe_ordered(error_patterns),
                "whatsMissing": _dedupe_ordered(missing_items),
                "traceableFrom": traceable_from,
                "requiresEvolution": evolution_name,
            }
        )
    except Exception:
        # Domain mirroring failures should not break compile response path.
        pass


def _build_soup_response(
    parsed: ParsedStatement,
    break_point: Optional[str],
    chain_missing: List[str],
    whats_missing: List[str],
) -> str:
    """Build outward SOUP response for incomplete derivation chains."""
    if chain_missing:
        unknown_text = ", ".join(chain_missing)
    elif break_point:
        unknown_text = f"{break_point} is_a ? (unknown)"
    else:
        unknown_text = "unresolved chain"

    extra_missing = [
        item for item in whats_missing
        if item not in chain_missing
    ]
    if not extra_missing:
        return (
            f"SOUP: {parsed.subject} {parsed.predicate} {parsed.object}. "
            f"Unknown: {unknown_text}"
        )

    missing_text = ", ".join(extra_missing)
    return (
        f"SOUP: {parsed.subject} {parsed.predicate} {parsed.object}. "
        f"Unknown: {unknown_text}. "
        f"Missing: {missing_text}"
    )


# =============================================================================
# CONVENIENCE / INTEGRATION
# =============================================================================

def compile_and_respond(statement: str) -> str:
    """Alias for youknow(). THE entry point."""
    return youknow(statement)


# For integration with existing code
def validate_statement(statement: str) -> Dict[str, Any]:
    """Return structured validation result.

    TODO: Return structured data instead of string for programmatic use.
    """
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
