"""
Tagging tools for conversation ingestion.

Tools: tag_pair, tag_range, batch_tag_operations, add_tag, list_tags
Uses state_machine for validation.
"""

from typing import List, Dict

from . import utils
from .models import Pair
from .state_machine import PairStateMachine, check_batch_coherence


def _format_tag_for_storage(tag_type: str, value: str) -> str:
    """Format a tag for storage in the tag array."""
    if tag_type == "strata":
        return f"strata:{value}"
    elif tag_type == "evolving":
        return "evolving"
    elif tag_type == "definition":
        return "definition"
    elif tag_type == "concept":
        return value  # Concept tags stored as-is
    elif tag_type == "emergent_framework":
        return f"emergent_framework:{value}"
    else:
        raise ValueError(f"Unknown tag_type: {tag_type}")


def tag_pair(index: int, tag_type: str, value: str = "") -> str:
    """
    Tag a specific pair with ratcheting validation.

    Args:
        index: Pair index to tag
        tag_type: One of 'strata', 'evolving', 'definition', 'concept', 'emergent_framework'
        value: Tag value (required for strata, concept, emergent_framework)

    Returns:
        Success message or BLOCKED error with guidance
    """
    state = utils.load_state()

    if not state['current_conversation']:
        return "❌ No conversation selected."

    conv_name = state['current_conversation']

    if not utils.is_v2_state(state):
        return "❌ tag_pair requires V2 state format."

    registry = utils.load_registry()

    # Initialize conversation if needed
    if conv_name not in state.get("conversations", {}):
        state["conversations"][conv_name] = {
            "authorized_phase": 3,
            "publishing_set": None,
            "pairs": {}
        }

    conv_data = state["conversations"][conv_name]
    idx_str = str(index)
    current_tags = conv_data.get("pairs", {}).get(idx_str, [])

    # Parse to Pair model
    pair = Pair.from_tag_array(current_tags)

    # Check conversation phase gate for emergent_framework
    if tag_type == "emergent_framework":
        authorized_phase = conv_data.get("authorized_phase", 3)
        if authorized_phase < 4:
            return (
                f"BLOCKED: Cannot perform Phase 4 operation on conversation '{conv_name}'.\n"
                f"Current authorized phase: {authorized_phase}\n"
                f"Required: Phase 4 must be authorized.\n"
                f"→ Call authorize_next_phase('{conv_name}') to advance to Phase 4.\n"
                f"→ This requires user approval - ask: \"Ready to assign emergent frameworks?\""
            )

    # Use state machine for per-pair validation
    if tag_type == "strata":
        allowed, error = PairStateMachine.can_add_strata(pair, value, registry)
    elif tag_type == "evolving":
        allowed, error = PairStateMachine.can_add_evolving(pair)
    elif tag_type == "definition":
        allowed, error = PairStateMachine.can_add_definition(pair, index)
    elif tag_type == "concept":
        allowed, error = PairStateMachine.can_add_concept(pair, index, value)
    elif tag_type == "emergent_framework":
        allowed, error = PairStateMachine.can_add_emergent(pair, index, value)
    else:
        return f"❌ Unknown tag_type: {tag_type}"

    if not allowed:
        return error

    # Format and apply tag
    formatted_tag = _format_tag_for_storage(tag_type, value)

    if idx_str not in conv_data["pairs"]:
        conv_data["pairs"][idx_str] = []

    if formatted_tag not in conv_data["pairs"][idx_str]:
        conv_data["pairs"][idx_str].append(formatted_tag)

        # Track concept tags globally
        if tag_type == "concept" and value not in state.get("concept_tags", []):
            if "concept_tags" not in state:
                state["concept_tags"] = []
            state["concept_tags"].append(value)

    utils.save_state(state)
    return f"✓ Tagged pair {index} with {tag_type}:{value if value else tag_type}"


def tag_range(start: int, end: int, tag_type: str, value: str = "") -> str:
    """
    Tag a range of pairs with ratcheting validation.

    Atomic: if any pair fails, none are tagged.
    """
    state = utils.load_state()

    if not state['current_conversation']:
        return "❌ No conversation selected."

    conv_name = state['current_conversation']

    if not utils.is_v2_state(state):
        return "❌ tag_range requires V2 state format."

    registry = utils.load_registry()

    # Initialize conversation if needed
    if conv_name not in state.get("conversations", {}):
        state["conversations"][conv_name] = {
            "authorized_phase": 3,
            "publishing_set": None,
            "pairs": {}
        }

    conv_data = state["conversations"][conv_name]

    # Check conversation phase gate for emergent_framework
    if tag_type == "emergent_framework":
        authorized_phase = conv_data.get("authorized_phase", 3)
        if authorized_phase < 4:
            return (
                f"BLOCKED: Cannot perform Phase 4 operation on conversation '{conv_name}'.\n"
                f"Current authorized phase: {authorized_phase}\n"
                f"Required: Phase 4 must be authorized.\n"
                f"→ Call authorize_next_phase('{conv_name}') to advance to Phase 4.\n"
                f"→ This requires user approval - ask: \"Ready to assign emergent frameworks?\""
            )

    # Validation pass
    blocked_pairs = []
    for index in range(start, end):
        idx_str = str(index)
        current_tags = conv_data.get("pairs", {}).get(idx_str, [])
        pair = Pair.from_tag_array(current_tags)

        if tag_type == "strata":
            allowed, error = PairStateMachine.can_add_strata(pair, value, registry)
        elif tag_type == "evolving":
            allowed, error = PairStateMachine.can_add_evolving(pair)
        elif tag_type == "definition":
            allowed, error = PairStateMachine.can_add_definition(pair, index)
        elif tag_type == "concept":
            allowed, error = PairStateMachine.can_add_concept(pair, index, value)
        elif tag_type == "emergent_framework":
            allowed, error = PairStateMachine.can_add_emergent(pair, index, value)
        else:
            return f"❌ Unknown tag_type: {tag_type}"

        if not allowed:
            blocked_pairs.append((index, error))

    if blocked_pairs:
        first_idx, first_error = blocked_pairs[0]
        return (
            f"BLOCKED: Range operation failed at pair {first_idx}.\n"
            f"{len(blocked_pairs)} pair(s) would be blocked.\n\n"
            f"{first_error}"
        )

    # Apply pass
    formatted_tag = _format_tag_for_storage(tag_type, value)
    tagged_count = 0

    for index in range(start, end):
        idx_str = str(index)
        if idx_str not in conv_data["pairs"]:
            conv_data["pairs"][idx_str] = []

        if formatted_tag not in conv_data["pairs"][idx_str]:
            conv_data["pairs"][idx_str].append(formatted_tag)
            tagged_count += 1

    # Track concept tags
    if tag_type == "concept" and value not in state.get("concept_tags", []):
        if "concept_tags" not in state:
            state["concept_tags"] = []
        state["concept_tags"].append(value)

    utils.save_state(state)
    return f"✓ Tagged {tagged_count} pair(s) ({start}-{end-1}) with {tag_type}:{value if value else tag_type}"


def batch_tag_operations(operations: List[Dict]) -> str:
    """
    Execute multiple tag operations with coherence checking.

    Coherence allows [strata, definition, concept] in one batch
    by validating operations IN ORDER.

    Atomic: if any fail, none applied.
    """
    from collections import defaultdict

    state = utils.load_state()

    if not state['current_conversation']:
        return "❌ No conversation selected."

    conv_name = state['current_conversation']

    if not utils.is_v2_state(state):
        return "❌ batch_tag_operations requires V2 state format."

    registry = utils.load_registry()

    # Initialize conversation if needed
    if conv_name not in state.get("conversations", {}):
        state["conversations"][conv_name] = {
            "authorized_phase": 3,
            "publishing_set": None,
            "pairs": {}
        }

    conv_data = state["conversations"][conv_name]

    # Group operations by pair index
    ops_by_pair = defaultdict(list)
    range_ops = []

    for op in operations:
        action = op.get("action")
        tag_type = op.get("tag_type", "concept")
        value = op.get("value", op.get("tag", ""))

        if action == "tag_pair":
            index = op.get("index")
            ops_by_pair[index].append({"tag_type": tag_type, "value": value})

        elif action == "tag_range":
            start = op.get("start")
            end = op.get("end")
            range_ops.append({"start": start, "end": end, "tag_type": tag_type, "value": value})
            for idx in range(start, end):
                ops_by_pair[idx].append({"tag_type": tag_type, "value": value})

    # Check conversation phase gate for emergent_framework operations
    has_emergent_ops = any(
        op.get("tag_type") == "emergent_framework"
        for pair_ops in ops_by_pair.values()
        for op in pair_ops
    )
    if has_emergent_ops:
        authorized_phase = conv_data.get("authorized_phase", 3)
        if authorized_phase < 4:
            return (
                f"BLOCKED: Cannot perform Phase 4 operation on conversation '{conv_name}'.\n"
                f"Current authorized phase: {authorized_phase}\n"
                f"Required: Phase 4 must be authorized.\n"
                f"→ Call authorize_next_phase('{conv_name}') to advance to Phase 4.\n"
                f"→ This requires user approval - ask: \"Ready to assign emergent frameworks?\""
            )

    # Validation pass with coherence checking
    errors = []
    for pair_index, pair_ops in ops_by_pair.items():
        idx_str = str(pair_index)
        current_tags = conv_data.get("pairs", {}).get(idx_str, [])
        pair = Pair.from_tag_array(current_tags)

        allowed, error = check_batch_coherence(pair, pair_index, pair_ops, registry)
        if not allowed:
            errors.append((pair_index, error))

    if errors:
        first_idx, first_error = errors[0]
        return (
            f"BLOCKED: Batch operation failed at pair {first_idx}.\n"
            f"{len(errors)} pair(s) have coherence violations.\n\n"
            f"{first_error}"
        )

    # Apply pass
    pair_count = 0
    concept_tags_added = set()

    for pair_index, pair_ops in ops_by_pair.items():
        idx_str = str(pair_index)
        if idx_str not in conv_data["pairs"]:
            conv_data["pairs"][idx_str] = []

        for op in pair_ops:
            formatted_tag = _format_tag_for_storage(op["tag_type"], op["value"])
            if formatted_tag not in conv_data["pairs"][idx_str]:
                conv_data["pairs"][idx_str].append(formatted_tag)
                pair_count += 1

            if op["tag_type"] == "concept":
                concept_tags_added.add(op["value"])

    # Track concept tags
    for concept in concept_tags_added:
        if concept not in state.get("concept_tags", []):
            if "concept_tags" not in state:
                state["concept_tags"] = []
            state["concept_tags"].append(concept)

    utils.save_state(state)

    return (
        f"✓ Batch operations complete:\n"
        f"  - {len(ops_by_pair)} pairs affected\n"
        f"  - {pair_count} tags applied\n"
        f"  - {len(range_ops)} range operations"
    )


def add_tag(tag_names) -> str:
    """
    Add new concept tag(s).

    Only adds to concept_tags list.
    Strata managed via registry. State tags (evolving/definition) are fixed.
    """
    state = utils.load_state()

    if isinstance(tag_names, str):
        tag_names = [tag_names]

    added = []
    skipped = []
    blocked = []

    reserved_prefixes = ("strata:", "emergent_framework:")
    reserved_exact = {"evolving", "definition", "paiab", "sanctum", "cave"}

    for tag in tag_names:
        if tag in reserved_exact:
            blocked.append(f"{tag} (reserved)")
            continue
        if any(tag.startswith(prefix) for prefix in reserved_prefixes):
            blocked.append(f"{tag} (reserved prefix)")
            continue

        if utils.is_v2_state(state):
            if tag in state.get('concept_tags', []):
                skipped.append(tag)
            else:
                if 'concept_tags' not in state:
                    state['concept_tags'] = []
                state['concept_tags'].append(tag)
                added.append(tag)
        else:
            if tag in state.get('tag_enum', []):
                skipped.append(tag)
            else:
                if 'tag_enum' not in state:
                    state['tag_enum'] = []
                state['tag_enum'].append(tag)
                added.append(tag)

    utils.save_state(state)

    result = []
    if added:
        result.append(f"✓ Added {len(added)} concept tag(s): {', '.join(added)}")
    if skipped:
        result.append(f"⚠ Skipped {len(skipped)} existing: {', '.join(skipped)}")
    if blocked:
        result.append(f"✗ Blocked {len(blocked)} reserved: {', '.join(blocked)}")

    return "\n".join(result) if result else "No tags to add"


def list_tags() -> str:
    """Show all tags organized by type."""
    state = utils.load_state()

    output = ["=== Tags ===", ""]

    # Strata (from registry)
    registry = utils.load_registry()
    strata_keys = list(registry.strata.keys())
    output.append(f"Strata ({len(strata_keys)}):")
    for s in strata_keys:
        entry = registry.strata[s]
        output.append(f"  - {s}: {entry.description}")

    output.append("")
    output.append("State tags (fixed):")
    output.append("  - evolving: Pair was read")
    output.append("  - definition: Pair has logic")

    # Concept tags
    if utils.is_v2_state(state):
        concepts = state.get("concept_tags", [])
    else:
        concepts = [t for t in state.get("tag_enum", [])
                   if t not in {"evolving", "definition", "paiab", "sanctum", "cave"}]

    output.append("")
    output.append(f"Concept tags ({len(concepts)}):")
    if concepts:
        for c in sorted(concepts)[:20]:
            output.append(f"  - {c}")
        if len(concepts) > 20:
            output.append(f"  ... and {len(concepts) - 20} more")

    # Emergent frameworks
    emergents = state.get("emergent_frameworks", {})
    output.append("")
    output.append(f"Emergent frameworks ({len(emergents)}):")
    for name, ef in list(emergents.items())[:10]:
        canonical = ef.get("canonical_framework") or "unassigned"
        output.append(f"  - {name} → {canonical}")
    if len(emergents) > 10:
        output.append(f"  ... and {len(emergents) - 10} more")

    return "\n".join(output)
