"""
Journey metadata tools for conversation ingestion.

Tools: set_journey_metadata, get_journey_metadata
"""

from . import utils


def set_journey_metadata(
    canonical_framework: str,
    obstacle: str,
    overcome: str,
    dream: str
) -> str:
    """
    Set journey metadata for a canonical framework.

    Only allowed when a publishing set is in Phase 6+.
    All three fields required together.

    Args:
        canonical_framework: Name of the canonical framework
        obstacle: What obstacle/challenge does this framework address?
        overcome: How does applying this framework overcome the obstacle?
        dream: What becomes possible after mastering this framework?
    """
    state = utils.load_state()
    registry = utils.load_registry()

    if not utils.is_v2_state(state):
        return "BLOCKED: set_journey_metadata requires V2 state format."

    # Validate canonical exists
    canonical_info = registry.get_canonical(canonical_framework)
    if not canonical_info:
        return (
            f"BLOCKED: Canonical framework '{canonical_framework}' not in registry.\n"
            f"→ First add it using: add_canonical_framework(strata, slot_type, '{canonical_framework}', framework_state)"
        )

    # Check emergent frameworks point to this canonical
    emergents = state.get("emergent_frameworks", {})
    related = [
        ef_name for ef_name, ef in emergents.items()
        if ef.get("canonical_framework") == canonical_framework
    ]

    if not related:
        return (
            f"BLOCKED: No emergent frameworks assigned to canonical '{canonical_framework}'.\n"
            f"→ Complete Phase 5 (assign_canonical_to_emergent) first."
        )

    # Check a publishing set is at Phase 6+
    publishing_sets = state.get("publishing_sets", {})
    ps_at_phase_6 = [
        ps_name for ps_name, ps in publishing_sets.items()
        if ps.get("phase", 5) >= 6
    ]

    if not ps_at_phase_6:
        return (
            f"BLOCKED: Cannot set journey metadata for '{canonical_framework}'.\n"
            f"No publishing set is at Phase 6+.\n"
            f"→ Call authorize_publishing_set_phase() to advance to Phase 6."
        )

    # Validate all fields non-empty
    if not obstacle or not overcome or not dream:
        missing = []
        if not obstacle:
            missing.append("obstacle")
        if not overcome:
            missing.append("overcome")
        if not dream:
            missing.append("dream")
        return (
            f"BLOCKED: All three journey fields required.\n"
            f"Missing: {', '.join(missing)}"
        )

    # Set metadata
    if "journey_metadata" not in state:
        state["journey_metadata"] = {}

    state["journey_metadata"][canonical_framework] = {
        "obstacle": obstacle,
        "overcome": overcome,
        "dream": dream
    }

    utils.save_state(state)

    return (
        f"✓ Set journey metadata for: {canonical_framework}\n"
        f"  Obstacle: {obstacle[:60]}{'...' if len(obstacle) > 60 else ''}\n"
        f"  Overcome: {overcome[:60]}{'...' if len(overcome) > 60 else ''}\n"
        f"  Dream: {dream[:60]}{'...' if len(dream) > 60 else ''}"
    )


def get_journey_metadata(canonical_framework: str) -> str:
    """
    Get journey metadata for a canonical framework.

    Returns:
    - obstacle, overcome, dream (or not set)
    - Whether ready for Phase 7
    """
    state = utils.load_state()
    registry = utils.load_registry()

    if not utils.is_v2_state(state):
        return "get_journey_metadata requires V2 state format."

    # Check canonical exists
    canonical_info = registry.get_canonical(canonical_framework)
    if not canonical_info:
        return f"Canonical framework '{canonical_framework}' not in registry."

    # Get journey metadata
    jm = state.get("journey_metadata", {}).get(canonical_framework, {})

    obstacle = jm.get("obstacle")
    overcome = jm.get("overcome")
    dream = jm.get("dream")

    is_complete = all([obstacle, overcome, dream])

    output = [
        f"=== Journey Metadata: {canonical_framework} ===",
        f"",
        f"Registry Info:",
        f"  Type: {canonical_info[0]}",
        f"  Strata: {canonical_info[1]}",
        f"  State: {canonical_info[2]}",
        f"",
        f"Journey:",
        f"  Obstacle: {obstacle or '(not set)'}",
        f"  Overcome: {overcome or '(not set)'}",
        f"  Dream: {dream or '(not set)'}",
        f"",
        f"Ready for Phase 7: {'Yes ✓' if is_complete else 'No ○'}"
    ]

    if not is_complete:
        missing = []
        if not obstacle:
            missing.append("obstacle")
        if not overcome:
            missing.append("overcome")
        if not dream:
            missing.append("dream")
        output.append(f"  Missing: {', '.join(missing)}")

    return "\n".join(output)
