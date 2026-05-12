"""YOUKNOW Utils - ALL THE LOGIC.

Primitives, assemblies, mixins. Everything that does actual work.
Now integrated with UARL SHACL validation.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from pathlib import Path

from .models import (
    Entity, PIOEntity, ValidationLevel, SelfSimulationLevel,
    InteractionMode, CertaintyState, SuperclassChain,
    CategoryStructure, Morphism, ValidationResult,
    Chain, Link, LinkType, DualLoop,
)

logger = logging.getLogger(__name__)

# UARL validator - lazy loaded
_uarl_validator = None

# Module-level output setting - set to True for LLM token optimization
MINIFY_OUTPUT = False

def get_uarl_validator():
    """Get or create the UARL validator instance."""
    global _uarl_validator
    if _uarl_validator is None:
        try:
            from .uarl_validator import UARLValidator
            uarl_dir = Path(__file__).parent
            _uarl_validator = UARLValidator(uarl_dir)
            logger.info("UARL validator initialized successfully")
        except Exception as e:
            logger.warning(f"UARL validator not available: {e}")
            _uarl_validator = False  # Mark as unavailable
    return _uarl_validator if _uarl_validator else None


# =============================================================================
# LLM_SUGGEST - The passthrough shell
# =============================================================================

def llm_suggest(context: str, error: str, choices: Optional[Dict[str, List[str]]] = None, minify: bool = None) -> str:
    """WE are the oracle. Just surface the error.

    This function doesn't call an API. It formats the error
    so the human+agent in the conversation can see it and respond.

    Args:
        minify: If True, return compact one-line format for LLM token optimization.
                Defaults to module-level MINIFY_OUTPUT setting.
    """
    if minify is None:
        minify = MINIFY_OUTPUT
    if minify:
        return f"YOUKNOW: {error}"

    choice_str = ""
    if choices:
        choice_str = f"\n  Known choices: {list(choices.keys())}"

    return f"""
╔══════════════════════════════════════════════════════════════╗
║  YOUKNOW NEEDS INPUT                                         ║
╠══════════════════════════════════════════════════════════════╣
║  Context: {context[:50]}{'...' if len(context) > 50 else ''}
║  Error: {error}
║  {choice_str}
║
║  What should I do?
╚══════════════════════════════════════════════════════════════╝
"""


def build_missingness_payload(
    statement: str,
    missingness: List[str],
    *,
    source: str = "compiler",
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic payload for queueing unresolved missingness."""
    unique = sorted(set(missingness))
    return {
        "source": source,
        "statement": statement,
        "missingness": unique,
        "count": len(unique),
        "extras": extras or {},
    }


# =============================================================================
# ROOT ENTITIES - Self-grounding bootstrap
# =============================================================================

def create_root_entities() -> Dict[str, Entity]:
    """Create the root entities that ground everything.

    pattern_of_isa is the root - YOUKNOW is its instantiation.
    """
    roots = {}

    roots["pattern_of_isa"] = Entity(
        name="pattern_of_isa",
        description="The self-referential root. YOUKNOW is this pattern.",
        is_a=[],
        python_class="Entity"
    )

    roots["PythonClass"] = Entity(
        name="PythonClass",
        description="Any Python class is_a PythonClass",
        is_a=["pattern_of_isa"],
        python_class="type"
    )

    roots["Entity"] = Entity(
        name="Entity",
        description="Base entity - requires python_class tracing to pattern_of_isa",
        is_a=["PythonClass"],
        python_class="Entity"
    )

    roots["PIOEntity"] = Entity(
        name="PIOEntity",
        description="Entity with polysemic agentic potential",
        is_a=["Entity"],
        python_class="PIOEntity"
    )

    roots["programs"] = Entity(
        name="programs",
        description="Things that execute when reified. REIFIES -> is_a programs.",
        is_a=["pattern_of_isa"],
        python_class="Callable"
    )

    # Relationships ARE entities - the UARL chain
    roots["IsA"] = Entity(
        name="IsA",
        description="The is_a relationship itself",
        is_a=["pattern_of_isa"],
        python_class="relationship"
    )

    roots["PartOf"] = Entity(
        name="PartOf",
        description="The part_of relationship itself",
        is_a=["pattern_of_isa"],
        python_class="relationship"
    )

    roots["Embodies"] = Entity(
        name="Embodies",
        description="Declare you think you know something",
        is_a=["pattern_of_isa"],
        python_class="relationship"
    )

    roots["Manifests"] = Entity(
        name="Manifests",
        description="Try to type it",
        is_a=["pattern_of_isa"],
        python_class="relationship"
    )

    roots["Reifies"] = Entity(
        name="Reifies",
        description="Succeeded - is_a programs = EXECUTING",
        is_a=["pattern_of_isa"],
        python_class="relationship"
    )

    roots["Instantiates"] = Entity(
        name="Instantiates",
        description="Golden, can produce more",
        is_a=["pattern_of_isa"],
        python_class="relationship"
    )

    return roots


# =============================================================================
# VALIDATION - Pattern of ISA
# =============================================================================

def validate_pattern_of_isa(
    entity_name: str,
    entities: Dict[str, Any],
    visited: Optional[set] = None
) -> ValidationResult:
    """Validate that entity traces to pattern_of_isa.

    Uses simple graph traversal.
    Returns clear errors when chain breaks.
    """
    if visited is None:
        visited = set()

    # Root case
    if entity_name == "pattern_of_isa":
        return ValidationResult(
            valid=True,
            chain=["pattern_of_isa"],
            message="Reached root: pattern_of_isa"
        )

    # Cycle detection
    if entity_name in visited:
        return ValidationResult(
            valid=False,
            chain=list(visited),
            message=llm_suggest(
                context=f"Validating chain for {entity_name}",
                error=f"Cycle detected: {entity_name} already in chain {visited}"
            )
        )

    visited.add(entity_name)

    # Entity doesn't exist
    if entity_name not in entities:
        return ValidationResult(
            valid=False,
            missing=[entity_name],
            message=llm_suggest(
                context=f"Validating {entity_name}",
                error=f"Entity '{entity_name}' doesn't exist in ontology"
            )
        )

    entity = entities[entity_name]

    # No is_a chain
    if not hasattr(entity, 'is_a') or not entity.is_a:
        return ValidationResult(
            valid=False,
            chain=[entity_name],
            message=llm_suggest(
                context=f"Validating {entity_name}",
                error=f"Entity '{entity_name}' has no is_a chain to root"
            )
        )

    # Recursively validate parents
    all_missing = []
    for parent in entity.is_a:
        result = validate_pattern_of_isa(parent, entities, visited.copy())
        if result.valid:
            return ValidationResult(
                valid=True,
                chain=[entity_name] + result.chain,
                message=f"Valid chain: {entity_name} → {' → '.join(result.chain)}"
            )
        all_missing.extend(result.missing)

    return ValidationResult(
        valid=False,
        chain=[entity_name],
        missing=all_missing,
        message=llm_suggest(
            context=f"Validating {entity_name}",
            error=f"No valid chain to pattern_of_isa. Missing: {all_missing}"
        )
    )


# =============================================================================
# UARL SHACL VALIDATION - Integration with UARL foundation ontology
# =============================================================================

def uarl_validate_concept(
    concept_data: Dict[str, Any],
    entities: Optional[Dict[str, PIOEntity]] = None
) -> ValidationResult:
    """Validate a concept against UARL SHACL shapes.
    
    Now with PERSISTENT DOMAIN ONTOLOGY:
    - Checks if is_a targets exist in domain.owl
    - Adds validated concepts to domain.owl
    - Uses closed-world validation with actionable error messages.
    
    Args:
        concept_data: Dict with concept properties (name, type, etc.)
                      OR a PIOEntity object
        entities: Optional entities dict for in-memory context (deprecated, use domain.owl)
    
    Returns:
        ValidationResult compatible with YOUKNOW
    """
    validator = get_uarl_validator()
    
    if validator is None:
        # Fallback: UARL not available, just pass through
        return ValidationResult(
            valid=True,
            chain=[concept_data.get("name", "unknown") if isinstance(concept_data, dict) else getattr(concept_data, "name", "unknown")],
            message="UARL validator not available - skipping SHACL validation"
        )
    
    # Convert PIOEntity to dict if needed
    if hasattr(concept_data, 'model_dump'):
        concept_dict = concept_data.model_dump()
        concept_dict['type'] = 'PIOEntity'
    elif hasattr(concept_data, '__dict__'):
        concept_dict = concept_data.__dict__.copy()
        concept_dict['type'] = type(concept_data).__name__
    else:
        concept_dict = dict(concept_data)
    
    concept_name = concept_dict.get("name", "unknown")
    
    # Check if is_a targets exist in domain ontology
    is_a_targets = concept_dict.get("is_a", [])
    missing_targets = []
    for target in is_a_targets:
        if not validator.concept_exists(target):
            missing_targets.append(target)
    
    if missing_targets:
        # Return error with missing concepts
        return ValidationResult(
            valid=False,
            chain=[concept_name],
            missing=missing_targets,
            message=llm_suggest(
                context=f"Validating {concept_name}",
                error=f"is_a targets not in domain ontology: {missing_targets}. Define them first."
            )
        )
    
    # Call UARL SHACL validator
    uarl_result = validator.validate_concept(concept_dict)
    
    if uarl_result.valid:
        # Add to domain ontology (persist!)
        validator.add_to_domain(concept_dict)
        
        return ValidationResult(
            valid=True,
            chain=[concept_name],
            message=f"UARL validation passed: {uarl_result.concept_uri} (added to domain.owl)"
        )
    else:
        # Convert UARL errors to YOUKNOW ValidationResult
        missing = [e.property_path for e in uarl_result.errors]
        error_messages = "\n".join(uarl_result.error_messages)
        
        return ValidationResult(
            valid=False,
            chain=[concept_name],
            missing=missing,
            message=llm_suggest(
                context=f"UARL validation for {concept_name}",
                error=f"SHACL validation failed:\n{error_messages}"
            ),
            certainty=0.5  # Hallucination - lower certainty
        )


def uarl_validate_embodiment_claim(
    name: str,
    intuition: str,
    compare_from: str,
    maps_to: str,
    analogical_pattern: Optional[str] = None
) -> ValidationResult:
    """Convenience method for validating an EmbodimentClaim via UARL.
    
    Structure: A with B embodies C wrt D
    - A = intuition
    - B = compare_from  
    - C = maps_to
    - D = analogical_pattern (THE ACTUAL PATTERN)
    """
    validator = get_uarl_validator()
    
    if validator is None:
        return ValidationResult(
            valid=False,
            chain=[name],
            message="UARL validator not available"
        )
    
    uarl_result = validator.validate_embodiment_claim(
        name=name,
        intuition=intuition,
        compare_from=compare_from,
        maps_to=maps_to,
        analogical_pattern=analogical_pattern
    )
    
    if uarl_result.valid:
        return ValidationResult(
            valid=True,
            chain=[name, "EmbodimentClaim", "pattern_of_isa"],
            message=f"EmbodimentClaim validated: bridge structure complete"
        )
    else:
        return ValidationResult(
            valid=False,
            chain=[name],
            missing=uarl_result.hallucination_metadata.get("error_patterns", []),
            message=llm_suggest(
                context=f"EmbodimentClaim '{name}'",
                error="\n".join(uarl_result.error_messages)
            )
        )


# =============================================================================
# ENTITY OPERATIONS
# =============================================================================

def add_entity_to_lattice(
    entity: PIOEntity,
    entities: Dict[str, PIOEntity],
    is_a_edges: List[tuple],
    part_of_edges: List[tuple],
    produces_edges: List[tuple],
    y4_instances: List[str],
    y5_patterns: List[str],
    y6_implementations: List[str],
) -> bool:
    """Add an entity to the lattice. Returns True if YOUKNOW added."""
    entities[entity.name] = entity

    # Track by validation level
    if entity.validation_level == ValidationLevel.EMBODIES:
        if entity.name not in y4_instances:
            y4_instances.append(entity.name)
    elif entity.validation_level == ValidationLevel.MANIFESTS:
        if entity.name not in y5_patterns:
            y5_patterns.append(entity.name)
    elif entity.validation_level in [ValidationLevel.REIFIES, ValidationLevel.INSTANTIATES]:
        if entity.name not in y6_implementations:
            y6_implementations.append(entity.name)

    # Add edges
    for superclass in entity.is_a:
        edge = (entity.name, superclass)
        if edge not in is_a_edges:
            is_a_edges.append(edge)

    for whole in entity.part_of:
        edge = (entity.name, whole)
        if edge not in part_of_edges:
            part_of_edges.append(edge)

    for product in entity.produces:
        edge = (entity.name, product)
        if edge not in produces_edges:
            produces_edges.append(edge)

    # The moment of terror
    return entity.name == "YOUKNOW"


def check_edge(edge: tuple, edge_list: List[tuple]) -> Tuple[bool, str]:
    """Check if edge exists in list."""
    exists = edge in edge_list
    reason = f"Edge {edge} {'exists' if exists else 'not found'}"
    return (exists, reason)


def get_superclass_chain(name: str, entities: Dict[str, PIOEntity]) -> List[str]:
    """Walk up the is_a chain."""
    chain = []
    current = name
    visited = set()

    while current and current not in visited:
        visited.add(current)
        if current in entities:
            parents = entities[current].is_a
            if parents:
                parent = parents[0]
                chain.append(parent)
                current = parent
            else:
                break
        else:
            break

    return chain


def crystallize_entity(
    name: str,
    python_class_name: str,
    python_module: str,
    entities: Dict[str, PIOEntity],
    y4_instances: List[str],
    y5_patterns: List[str],
    y6_implementations: List[str],
) -> None:
    """Move entity to REIFIES level."""
    if name in entities:
        entity = entities[name]
        entity.validation_level = ValidationLevel.REIFIES
        entity.python_class_name = python_class_name
        entity.python_module = python_module
        entity.crystallized = datetime.now()

        if name in y4_instances:
            y4_instances.remove(name)
        if name in y5_patterns:
            y5_patterns.remove(name)
        if name not in y6_implementations:
            y6_implementations.append(name)


def goldenize_entity(name: str, entities: Dict[str, PIOEntity]) -> None:
    """Move entity to INSTANTIATES level (golden)."""
    if name in entities:
        entity = entities[name]
        entity.validation_level = ValidationLevel.INSTANTIATES
        entity.goldenized = datetime.now()


# =============================================================================
# CATEGORY PERCEPTION
# =============================================================================

def perceive_as_category(structure: Any) -> CategoryStructure:
    """Perceive any structure as objects + morphisms."""
    objects = []
    morphisms = []

    if isinstance(structure, dict):
        for key, value in structure.items():
            objects.append(str(key))
            if isinstance(value, (list, tuple)):
                for v in value:
                    morphisms.append(Morphism(source=str(key), target=str(v)))
            elif value is not None:
                morphisms.append(Morphism(source=str(key), target=str(value)))

    elif hasattr(structure, 'is_a'):
        objects.append(structure.name)
        for parent in getattr(structure, 'is_a', []):
            objects.append(parent)
            morphisms.append(Morphism(source=structure.name, target=parent, name="is_a"))
        for whole in getattr(structure, 'part_of', []):
            objects.append(whole)
            morphisms.append(Morphism(source=structure.name, target=whole, name="part_of"))

    else:
        objects.append(str(structure))

    return CategoryStructure(
        objects=list(set(objects)),
        morphisms=morphisms,
        has_identity=len(objects) > 0,
        has_composition=len(morphisms) > 1
    )


# =============================================================================
# PIO DETECTION
# =============================================================================

def detect_pio_candidates(entities: Dict[str, PIOEntity]) -> List[tuple]:
    """Detect entities with isomorphic is_a chains - PIO opportunities."""
    chain_groups: Dict[tuple, List[str]] = {}
    for name, entity in entities.items():
        chain = tuple(sorted(entity.is_a)) if entity.is_a else ()
        if chain not in chain_groups:
            chain_groups[chain] = []
        chain_groups[chain].append(name)

    candidates = []
    for chain, names in chain_groups.items():
        if len(names) > 1 and chain:
            candidates.append((chain, names))

    return candidates


def pio_report(entities: Dict[str, PIOEntity]) -> str:
    """Generate PIO detection report."""
    candidates = detect_pio_candidates(entities)
    if not candidates:
        return "No PIO candidates detected."

    lines = ["PIO Candidates (isomorphic is_a chains):"]
    for chain, names in candidates:
        lines.append(f"  Chain {chain}: {names}")
        lines.append(f"    -> Are these the same concept? Consider PIO collapse.")
    return "\n".join(lines)


# =============================================================================
# CONVERSATIONAL INTERFACE
# =============================================================================

def because(entity_name: str, entities: Dict[str, PIOEntity]) -> str:
    """Why is X what it is? Returns the reasoning chain."""
    if entity_name not in entities:
        return f"I don't know what '{entity_name}' is. It doesn't exist in my ontology."

    entity = entities[entity_name]
    result = validate_pattern_of_isa(entity_name, entities)

    if not result.valid:
        return f"'{entity_name}' exists but doesn't trace to pattern_of_isa: {result.message}"

    superclass_chain = " → ".join(result.chain)
    pattern_trace = result.chain[-1] if result.chain else "unknown"

    return (
        f"Because {entity_name} is_a {superclass_chain} "
        f"due to its pattern of isa being: {pattern_trace} (root). "
        f"Validation level: {entity.validation_level.value}."
    )


def actually(entity_name: str, entities: Dict[str, PIOEntity], claim: Optional[str] = None) -> str:
    """What is X actually? Compare against a claim."""
    if entity_name not in entities:
        if claim:
            return f"Actually '{entity_name}' doesn't exist, so '{claim}' cannot be True (right now)."
        return f"Actually '{entity_name}' doesn't exist in my ontology."

    entity = entities[entity_name]
    result = validate_pattern_of_isa(entity_name, entities)
    superclass_chain = " → ".join(result.chain) if result.chain else entity_name

    if not claim:
        return (
            f"Actually {entity_name} is_a {superclass_chain}. "
            f"Validation: {entity.validation_level.value}. "
            f"Part of: {entity.part_of if entity.part_of else 'nothing'}."
        )

    # Parse and evaluate the claim
    claim_lower = claim.lower().strip()

    if " is_a " in claim_lower:
        parts = claim.split(" is_a ", 1)
        if len(parts) == 2:
            claimed_parent = parts[1].strip()
            can_be_true = claimed_parent in result.chain or claimed_parent in entity.is_a
            verdict = "can" if can_be_true else "cannot"
            return f"Actually {entity_name} is_a {superclass_chain}, so '{claim}' {verdict} be True (right now)."

    elif " part_of " in claim_lower:
        parts = claim.split(" part_of ", 1)
        if len(parts) == 2:
            claimed_whole = parts[1].strip()
            can_be_true = claimed_whole in entity.part_of
            verdict = "can" if can_be_true else "cannot"
            return f"Actually {entity_name} is_a {superclass_chain}, so '{claim}' {verdict} be True (right now)."

    return f"Actually {entity_name} is_a {superclass_chain}. I couldn't parse the claim '{claim}'."


# =============================================================================
# CERTAINTY
# =============================================================================

def get_certainty_state(certainty: float) -> CertaintyState:
    """What's YOUKNOW's epistemic state?"""
    if certainty > 0.8:
        return CertaintyState.SANCTUARY
    elif certainty >= 0.5:
        return CertaintyState.CAUTION
    else:
        return CertaintyState.WASTELAND


def adjust_certainty(certainty: float, delta: float) -> Tuple[float, str]:
    """Adjust certainty and return warning if entering wasteland."""
    old_state = get_certainty_state(certainty)
    new_certainty = max(0.0, min(1.0, certainty + delta))
    new_state = get_certainty_state(new_certainty)

    if new_state == CertaintyState.WASTELAND and old_state != CertaintyState.WASTELAND:
        warning = (
            f"Warning: CERTAINTY {new_certainty:.2f} - ENTERING WASTELAND\n"
            f"Options: [R]evert, [C]ontinue risky, [S]top\n(R/C/S)?"
        )
        return (new_certainty, warning)
    return (new_certainty, f"Certainty: {new_certainty:.2f} ({new_state.value})")


# =============================================================================
# UCO - Chain operations
# =============================================================================

def core_sentence_chain() -> Chain:
    """Get the core sentence as a chain."""
    chain = Chain(name="core_sentence")
    chain.add_link("embodies", "manifests", LinkType.EMBODIES)
    chain.add_link("manifests", "reifies", LinkType.MANIFESTS)
    chain.add_link("reifies", "produces", LinkType.REIFIES)
    chain.add_link("produces", "pattern_of_isa", LinkType.INSTANTIATES)
    return chain


def chain_from_validation_result(result: ValidationResult) -> Chain:
    """Convert ValidationResult to Chain."""
    chain = Chain(name=result.chain[0] if result.chain else "unknown")
    for i in range(len(result.chain) - 1):
        chain.add_link(result.chain[i], result.chain[i + 1], LinkType.ISA)
    return chain


def dual_loop_from_entity(entity: PIOEntity) -> Optional[DualLoop]:
    """Create DualLoop if entity has both is_a and part_of."""
    if not entity.is_a and not entity.part_of:
        return None

    isa_chain = Chain(name=f"{entity.name}_isa")
    for parent in entity.is_a:
        isa_chain.add_link(entity.name, parent, LinkType.ISA)

    partof_chain = Chain(name=f"{entity.name}_partof")
    for whole in entity.part_of:
        partof_chain.add_link(entity.name, whole, LinkType.PARTOF)

    if not isa_chain.links and not partof_chain.links:
        return None

    return DualLoop(
        entity_name=entity.name,
        isa_chain=isa_chain,
        partof_chain=partof_chain
    )


def find_dual_loops(entities: Dict[str, PIOEntity]) -> List[DualLoop]:
    """Find all dual-loops in the ontology."""
    loops = []
    for name, entity in entities.items():
        dl = dual_loop_from_entity(entity)
        if dl:
            loops.append(dl)
    return loops


def find_closed_dual_loops(entities: Dict[str, PIOEntity]) -> List[DualLoop]:
    """Find dual-loops where syntax and content entail each other."""
    return [dl for dl in find_dual_loops(entities) if dl.is_closed()]
