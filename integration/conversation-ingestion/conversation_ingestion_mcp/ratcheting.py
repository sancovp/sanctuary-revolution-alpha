"""
Ratcheting logic for conversation ingestion V2.

Per-pair ratcheting rules:
- evolving → always allowed
- strata → always allowed
- definition → BLOCKED unless strata already present on that pair
- concept tags → BLOCKED unless definition already present on that pair
- emergent framework → BLOCKED unless concept tags already present on that pair
"""
from typing import Optional, List, Tuple
from .models import Pair, Registry


class RatchetingError(Exception):
    """Raised when a tagging operation is blocked by ratcheting rules."""
    pass


def check_strata_tag(
    pair: Pair,
    strata_value: str,
    registry: Registry
) -> Tuple[bool, Optional[str]]:
    """
    Check if strata tag can be added.

    Returns: (allowed, error_message)
    """
    # Validate strata exists in registry
    if strata_value not in registry.strata:
        valid_strata = list(registry.strata.keys())
        return False, (
            f"BLOCKED: Cannot add strata '{strata_value}'.\n"
            f"Strata not found in registry.\n"
            f"Valid strata: {valid_strata}\n"
            f"→ Use add_strata('{strata_value}', 'description') to add it first."
        )

    return True, None


def check_evolving_tag(pair: Pair) -> Tuple[bool, Optional[str]]:
    """
    Check if evolving tag can be added.
    Always allowed.
    """
    return True, None


def check_definition_tag(
    pair: Pair,
    pair_index: int
) -> Tuple[bool, Optional[str]]:
    """
    Check if definition tag can be added.
    Requires strata to be present.
    """
    if not pair.strata:
        return False, (
            f"BLOCKED: Cannot add 'definition' to pair {pair_index}.\n"
            f"Current state: No strata assigned.\n"
            f"Required: Pair must have strata before adding definition.\n"
            f"→ First call: tag_pair({pair_index}, 'strata', '<strata_name>')"
        )

    return True, None


def check_concept_tag(
    pair: Pair,
    pair_index: int,
    concept_value: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if concept tag can be added.
    Requires definition to be present.
    """
    if not pair.definition:
        has_strata = "has strata" if pair.strata else "no strata"
        return False, (
            f"BLOCKED: Cannot add concept_tag '{concept_value}' to pair {pair_index}.\n"
            f"Current state: Pair {has_strata} but no definition.\n"
            f"Required: Pair must have 'definition' state before adding concept tags.\n"
            f"→ If this pair has substantive content, add definition first.\n"
            f"→ If this pair has no substantive content, it stays as evolving-only."
        )

    return True, None


def check_emergent_framework_tag(
    pair: Pair,
    pair_index: int,
    emergent_name: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if emergent framework tag can be added.
    Requires concept tags to be present.
    """
    if not pair.concept_tags:
        return False, (
            f"BLOCKED: Cannot assign emergent_framework '{emergent_name}' to pair {pair_index}.\n"
            f"Current state: Pair has no concept tags.\n"
            f"Required: Pair must have concept tags before emergent framework assignment.\n"
            f"→ Complete Phase 3 (concept tagging) for this pair first."
        )

    return True, None


def check_tag_operation(
    pair: Pair,
    pair_index: int,
    tag_type: str,
    value: str,
    registry: Registry
) -> Tuple[bool, Optional[str]]:
    """
    Check if a tag operation is allowed given current pair state.

    Args:
        pair: Current Pair state (parsed from tag array)
        pair_index: Index of the pair
        tag_type: One of 'strata', 'evolving', 'definition', 'concept', 'emergent_framework'
        value: The value to tag with
        registry: Registry for strata validation

    Returns:
        (allowed, error_message) - error_message is None if allowed
    """
    if tag_type == "strata":
        return check_strata_tag(pair, value, registry)
    elif tag_type == "evolving":
        return check_evolving_tag(pair)
    elif tag_type == "definition":
        return check_definition_tag(pair, pair_index)
    elif tag_type == "concept":
        return check_concept_tag(pair, pair_index, value)
    elif tag_type == "emergent_framework":
        return check_emergent_framework_tag(pair, pair_index, value)
    else:
        return False, f"BLOCKED: Unknown tag_type '{tag_type}'. Valid types: strata, evolving, definition, concept, emergent_framework"


def format_tag_for_storage(tag_type: str, value: str) -> str:
    """
    Format a tag for storage in the tag array.

    Args:
        tag_type: Type of tag
        value: Tag value

    Returns:
        Formatted tag string for storage
    """
    if tag_type == "strata":
        return f"strata:{value}"
    elif tag_type == "evolving":
        return "evolving"
    elif tag_type == "definition":
        return "definition"
    elif tag_type == "concept":
        return value  # Concept tags are stored as-is
    elif tag_type == "emergent_framework":
        return f"emergent_framework:{value}"
    else:
        raise ValueError(f"Unknown tag_type: {tag_type}")


def check_batch_coherence(
    pair: Pair,
    pair_index: int,
    operations: List[dict],
    registry: Registry
) -> Tuple[bool, Optional[str]]:
    """
    Check if a batch of operations is coherent.

    A batch is coherent if the operations, when applied in order,
    would satisfy ratcheting rules. This allows adding
    [strata, definition, concept] in one batch.

    Args:
        pair: Current pair state
        pair_index: Pair index
        operations: List of {tag_type, value} dicts for this pair
        registry: Registry for validation

    Returns:
        (allowed, error_message)
    """
    # Simulate applying operations to check coherence
    simulated = Pair(
        strata=pair.strata,
        evolving=pair.evolving,
        definition=pair.definition,
        concept_tags=list(pair.concept_tags),
        emergent_framework=pair.emergent_framework
    )

    for op in operations:
        tag_type = op.get("tag_type")
        value = op.get("value", "")

        # Check if this operation would be allowed
        allowed, error = check_tag_operation(simulated, pair_index, tag_type, value, registry)
        if not allowed:
            return False, error

        # Simulate applying the operation
        if tag_type == "strata":
            simulated.strata = value
        elif tag_type == "evolving":
            simulated.evolving = True
        elif tag_type == "definition":
            simulated.definition = True
        elif tag_type == "concept":
            if value not in simulated.concept_tags:
                simulated.concept_tags.append(value)
        elif tag_type == "emergent_framework":
            simulated.emergent_framework = value

    return True, None
