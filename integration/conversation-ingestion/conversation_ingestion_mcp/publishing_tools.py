"""
Publishing set tools for conversation ingestion.

Tools: create_publishing_set, get_publishing_set_status, authorize_publishing_set_phase
Uses state_machine for validation.
"""

from typing import List

from . import utils
from .models import Conversation, PublishingSet, JourneyMetadata, EmergentFramework
from .state_machine import PublishingSetStateMachine, PublishingSetPhase


def create_publishing_set(name: str, conversations: List[str], force: bool = False) -> str:
    """
    Create a new publishing set with specified conversations.

    Each conversation gets linked to this publishing set.
    Warns if any conversation already in a publishing set (use force=True to override).
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: create_publishing_set requires V2 state format."

    if "publishing_sets" not in state:
        state["publishing_sets"] = {}

    # Check name doesn't exist
    if name in state["publishing_sets"]:
        existing = state["publishing_sets"][name].get("conversations", [])
        return (
            f"BLOCKED: Publishing set '{name}' already exists.\n"
            f"Conversations: {existing}"
        )

    # Check conversations not already assigned
    already_assigned = []
    for conv in conversations:
        conv_data = state.get("conversations", {}).get(conv, {})
        existing_ps = conv_data.get("publishing_set")
        if existing_ps:
            ps_status = state.get("publishing_sets", {}).get(existing_ps, {}).get("status", "unknown")
            already_assigned.append(f"{conv} → {existing_ps} (status: {ps_status})")

    if already_assigned and not force:
        return (
            f"WARNING: Some conversations already in publishing sets:\n" +
            "\n".join(f"  - {a}" for a in already_assigned) +
            f"\n\nOnly continue if you intend to RE-INGEST these conversations.\n"
            f"This will reassign them to the new publishing set.\n"
            f"→ Call create_publishing_set('{name}', [...], force=True) to proceed"
        )

    # Create
    state["publishing_sets"][name] = {
        "conversations": conversations,
        "phase": 5,
        "status": "in_progress"
    }

    # Link conversations
    if "conversations" not in state:
        state["conversations"] = {}

    for conv in conversations:
        if conv not in state["conversations"]:
            state["conversations"][conv] = {
                "authorized_phase": 3,
                "publishing_set": None,
                "pairs": {}
            }
        state["conversations"][conv]["publishing_set"] = name

    utils.save_state(state)

    return (
        f"✓ Created publishing set: {name}\n"
        f"  Conversations: {len(conversations)}\n"
        f"  Status: in_progress\n"
        f"→ Call set_publishing_set('{name}') to activate it"
    )


def get_publishing_set_status(name: str) -> str:
    """
    Get status of a publishing set.

    Returns:
    - Conversations and their phases
    - Whether ready for Phase 6
    - Canonical frameworks and journey progress
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "get_publishing_set_status requires V2 state format."

    ps_data = state.get("publishing_sets", {}).get(name)
    if not ps_data:
        return f"Publishing set '{name}' not found."

    conversations = ps_data.get("conversations", [])
    ps_phase = ps_data.get("phase", 5)
    ps_status = ps_data.get("status", "in_progress")
    active_ps = state.get("active_publishing_set")

    # Check each conversation
    conv_phases = []
    all_at_phase_5 = True
    for conv in conversations:
        conv_data = state.get("conversations", {}).get(conv, {})
        phase = conv_data.get("authorized_phase", 3)
        conv_phases.append(f"  {conv}: Phase {phase}")
        if phase < 5:
            all_at_phase_5 = False

    # Collect canonicals from emergents
    emergents = state.get("emergent_frameworks", {})
    canonicals = set()
    for ef in emergents.values():
        canonical = ef.get("canonical_framework")
        if canonical:
            canonicals.add(canonical)

    # Check journey metadata
    journey_metadata = state.get("journey_metadata", {})
    canonicals_with_journey = sum(
        1 for c in canonicals
        if c in journey_metadata and all([
            journey_metadata[c].get("obstacle"),
            journey_metadata[c].get("overcome"),
            journey_metadata[c].get("dream")
        ])
    )

    active_marker = " ← ACTIVE" if name == active_ps else ""
    output = [
        f"=== Publishing Set: {name}{active_marker} ===",
        f"",
        f"Status: {ps_status}",
        f"Phase: {ps_phase}",
        f"Ready for Phase 6: {'Yes' if all_at_phase_5 else 'No'}",
        f"",
        f"Conversations ({len(conversations)}):",
    ]
    output.extend(conv_phases)
    output.append("")
    output.append(f"Canonical Frameworks: {len(canonicals)}")

    if canonicals:
        for c in sorted(canonicals):
            jm = journey_metadata.get(c, {})
            has_journey = all([jm.get("obstacle"), jm.get("overcome"), jm.get("dream")])
            journey_status = "✓ journey complete" if has_journey else "○ needs journey"
            output.append(f"  - {c} ({journey_status})")

    output.append("")
    output.append(f"Journey Progress: {canonicals_with_journey}/{len(canonicals)} complete")

    return "\n".join(output)


def set_publishing_set(name: str) -> str:
    """
    Activate a publishing set as the current working set.

    Sets active_publishing_set in state.
    Returns error if publishing set not found or status is 'delivered'.
    Shows list of available conversations (not yet at Phase 5).
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: set_publishing_set requires V2 state format."

    ps_data = state.get("publishing_sets", {}).get(name)
    if not ps_data:
        available = list(state.get("publishing_sets", {}).keys())
        return (
            f"BLOCKED: Publishing set '{name}' not found.\n"
            f"Available publishing sets: {available}"
        )

    ps_status = ps_data.get("status", "in_progress")
    if ps_status == "delivered":
        return (
            f"BLOCKED: Publishing set '{name}' is already delivered.\n"
            f"Delivered sets cannot be activated.\n"
            f"→ Create a new publishing set if you need to re-ingest conversations."
        )

    # Activate
    state["active_publishing_set"] = name
    utils.save_state(state)

    # Show available conversations
    conversations = ps_data.get("conversations", [])
    available_convs = []
    for conv in conversations:
        conv_data = state.get("conversations", {}).get(conv, {})
        phase = conv_data.get("authorized_phase", 3)
        if phase < 5:
            available_convs.append(f"  {conv}: Phase {phase}")

    output = [
        f"✓ Activated publishing set: {name}",
        f"  Status: {ps_status}",
        f"",
        f"Available conversations ({len(available_convs)}):",
    ]

    if available_convs:
        output.extend(available_convs)
        output.append("")
        output.append(f"→ Call set_conversation('conv_name') to start working")
    else:
        output.append("  (all conversations at Phase 5)")
        output.append("")
        output.append(f"→ Ready for Phase 6: call authorize_publishing_set_phase('{name}')")

    return "\n".join(output)


def list_publishing_sets(include_delivered: bool = False) -> str:
    """
    List all publishing sets with their status.

    By default hides 'delivered' sets.
    Shows: name, status, conversation count, conversations at Phase 5 count.
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "list_publishing_sets requires V2 state format."

    publishing_sets = state.get("publishing_sets", {})
    active_ps = state.get("active_publishing_set")

    if not publishing_sets:
        return "No publishing sets found.\n→ Call create_publishing_set('name', ['conv1', 'conv2']) to create one."

    output = ["=== Publishing Sets ===", ""]

    shown_count = 0
    for ps_name, ps_data in publishing_sets.items():
        ps_status = ps_data.get("status", "in_progress")

        # Skip delivered unless requested
        if ps_status == "delivered" and not include_delivered:
            continue

        shown_count += 1
        conversations = ps_data.get("conversations", [])

        # Count conversations at Phase 5
        at_phase_5 = 0
        for conv in conversations:
            conv_data = state.get("conversations", {}).get(conv, {})
            if conv_data.get("authorized_phase", 3) >= 5:
                at_phase_5 += 1

        # Mark active
        active_marker = " ← ACTIVE" if ps_name == active_ps else ""
        output.append(f"{ps_name}{active_marker}")
        output.append(f"  Status: {ps_status}")
        output.append(f"  Conversations: {at_phase_5}/{len(conversations)} at Phase 5")
        output.append("")

    if shown_count == 0:
        output.append("(all publishing sets are delivered)")
        output.append("")
        output.append("→ Use include_delivered=True to see delivered sets")

    if not active_ps:
        output.append("→ No active publishing set. Call set_publishing_set('name') to activate one.")

    return "\n".join(output)


def list_available_conversations() -> str:
    """
    List conversations in the ACTIVE publishing set that are not yet at Phase 5.

    Returns error if no active publishing set.
    Shows conversation name and current phase.
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "list_available_conversations requires V2 state format."

    active_ps = state.get("active_publishing_set")
    if not active_ps:
        return (
            "BLOCKED: No active publishing set.\n"
            "→ Call set_publishing_set('name') first."
        )

    ps_data = state.get("publishing_sets", {}).get(active_ps)
    if not ps_data:
        return f"BLOCKED: Active publishing set '{active_ps}' not found in state."

    conversations = ps_data.get("conversations", [])
    available = []
    completed = []

    for conv in conversations:
        conv_data = state.get("conversations", {}).get(conv, {})
        phase = conv_data.get("authorized_phase", 3)
        if phase < 5:
            available.append((conv, phase))
        else:
            completed.append(conv)

    output = [
        f"=== Available Conversations in '{active_ps}' ===",
        "",
    ]

    if available:
        output.append(f"Not yet at Phase 5 ({len(available)}):")
        for conv, phase in available:
            output.append(f"  {conv}: Phase {phase}")
        output.append("")
        output.append(f"→ Call set_conversation('conv_name') to start working")
    else:
        output.append("(all conversations at Phase 5)")

    if completed:
        output.append("")
        output.append(f"Completed ({len(completed)}):")
        for conv in completed:
            output.append(f"  {conv}: Phase 5 ✓")

    return "\n".join(output)


def authorize_publishing_set_phase(name: str, force: bool = False) -> str:
    """
    Advance publishing set to the next phase.

    Phase gates:
    - Phase 5 → 6: All conversations at Phase 5
    - Phase 6 → 7: All canonicals have journey metadata
    - Phase 7 → 8: All canonical documents written (REQUIRES force=True + user confirmation)

    The 7→8 transition is the COMMIT POINT. Once delivered, the publishing set is finalized.
    This requires force=True to ensure the user has explicitly confirmed the synthesis is complete.
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: authorize_publishing_set_phase requires V2 state format."

    ps_data = state.get("publishing_sets", {}).get(name)
    if not ps_data:
        return f"Publishing set '{name}' not found."

    # Build models
    ps = PublishingSet(
        conversations=ps_data.get("conversations", []),
        phase=ps_data.get("phase", 5)
    )

    current_phase = PublishingSetStateMachine.get_phase(ps)

    if current_phase == PublishingSetPhase.PHASE_8:
        return f"Publishing set '{name}' already at Phase 8 (complete)."

    # Check gates based on current phase
    if current_phase == PublishingSetPhase.PHASE_5:
        # Build conversation models
        conversations = {}
        for conv_name in ps.conversations:
            conv_data = state.get("conversations", {}).get(conv_name, {})
            conversations[conv_name] = Conversation(
                authorized_phase=conv_data.get("authorized_phase", 3),
                publishing_set=conv_data.get("publishing_set"),
                pairs=conv_data.get("pairs", {})
            )

        allowed, error = PublishingSetStateMachine.can_advance_to_6(ps, conversations)
        if not allowed:
            return error

    elif current_phase == PublishingSetPhase.PHASE_6:
        # Build emergent and journey models
        emergents = {}
        for ef_name, ef_data in state.get("emergent_frameworks", {}).items():
            emergents[ef_name] = EmergentFramework(
                name=ef_data.get("name"),
                strata=ef_data.get("strata"),
                description=ef_data.get("description", ""),
                canonical_framework=ef_data.get("canonical_framework")
            )

        journey_metadata = {}
        for c_name, jm_data in state.get("journey_metadata", {}).items():
            journey_metadata[c_name] = JourneyMetadata(
                obstacle=jm_data.get("obstacle"),
                overcome=jm_data.get("overcome"),
                dream=jm_data.get("dream")
            )

        allowed, error = PublishingSetStateMachine.can_advance_to_7(ps, emergents, journey_metadata)
        if not allowed:
            return error

    elif current_phase == PublishingSetPhase.PHASE_7:
        # Phase 7→8 is the COMMIT POINT - requires explicit user confirmation
        if not force:
            return (
                "⚠️  FINALIZATION CHECK - Phase 7→8 is the COMMIT POINT\n"
                "=" * 60 + "\n\n"
                "Once you advance to Phase 8, the publishing set is marked 'delivered'.\n"
                "This means the synthesis is FINALIZED and ready for Discord.\n\n"
                "Before proceeding, confirm with the user:\n"
                "  'Is this the exact geometry you want from this publishing set?'\n"
                "  'Are all framework documents at the quality bar (graduate-level, full journey)?'\n\n"
                "If YES, call:\n"
                f"  authorize_publishing_set_phase('{name}', force=True)\n\n"
                "If NO, go back and edit the framework JSONs until ready."
            )

        allowed, error = PublishingSetStateMachine.can_advance_to_8(ps, [])
        if not allowed:
            return error

    # Advance
    new_ps = PublishingSetStateMachine.advance(ps)
    ps_data["phase"] = new_ps.phase

    # Auto-update status to 'delivered' when reaching Phase 8
    if new_ps.phase == 8:
        ps_data["status"] = "delivered"

    utils.save_state(state)

    phase_descriptions = {
        6: "journey definition (obstacle/overcome/dream)",
        7: "document writing",
        8: "posting to substrates (complete)"
    }

    output = [
        f"✓ Publishing set '{name}' advanced to Phase {new_ps.phase}",
        f"  Now authorized for: {phase_descriptions.get(new_ps.phase, 'unknown')}"
    ]

    if new_ps.phase == 8:
        output.append(f"  Status: delivered")
        # Clear active publishing set if this was the active one
        if state.get("active_publishing_set") == name:
            state["active_publishing_set"] = None
            utils.save_state(state)
            output.append(f"  (Active publishing set cleared)")

    return "\n".join(output)
