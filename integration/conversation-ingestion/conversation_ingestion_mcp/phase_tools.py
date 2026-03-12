"""
Phase management tools for conversation ingestion.

Tools: authorize_next_phase, get_phase_status
Uses state_machine for validation.
"""

from . import utils
from .models import Pair, Conversation
from .state_machine import (
    PairStateMachine, ConversationStateMachine,
    PairState, ConversationPhase
)


def authorize_next_phase(conversation: str) -> str:
    """
    Advance conversation to the next phase.

    Phase progression:
    - Phases 1-3 are always authorized (simultaneous)
    - First call: authorizes Phase 4 (emergent framework assignment)
    - Second call: authorizes Phase 5 (canonical framework assignment)
    - At Phase 5: use publishing set tools for Phase 6+

    Gates:
    - Phase 3 → 4: ALL pairs must have strata + evolving
    - Phase 4 → 5: ALL definition pairs must have emergent framework
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "BLOCKED: authorize_next_phase requires V2 state format."

    # Load conversation file to get total pair count
    try:
        conv_file = utils.load_conversation(conversation)
        pairs = utils.extract_io_pairs(conv_file)
        total_pairs = len(pairs)
    except FileNotFoundError:
        return f"BLOCKED: Conversation file '{conversation}' not found."

    # Ensure conversations dict exists
    if "conversations" not in state:
        state["conversations"] = {}

    # Get or create conversation entry
    if conversation not in state["conversations"]:
        state["conversations"][conversation] = {
            "authorized_phase": 3,
            "publishing_set": None,
            "pairs": {}
        }

    conv_data = state["conversations"][conversation]

    # Build Conversation model
    conv = Conversation(
        authorized_phase=conv_data.get("authorized_phase", 3),
        publishing_set=conv_data.get("publishing_set"),
        pairs=conv_data.get("pairs", {})
    )

    # Get emergent frameworks for Phase 4→5 document check
    emergent_frameworks = state.get("emergent_frameworks", {})

    # Use state machine with total_pairs for proper validation
    allowed, error = ConversationStateMachine.can_advance(
        conv, total_pairs, conversation, emergent_frameworks
    )
    if not allowed:
        return error

    # Advance
    new_conv = ConversationStateMachine.advance(conv)
    conv_data["authorized_phase"] = new_conv.authorized_phase

    phase_descriptions = {
        4: "emergent framework assignment",
        5: "canonical framework assignment"
    }

    output = [
        f"✓ Conversation '{conversation}' advanced to Phase {new_conv.authorized_phase}",
        f"  Now authorized for: {phase_descriptions.get(new_conv.authorized_phase, 'unknown')}"
    ]

    # Auto-update publishing set status when reaching Phase 5
    if new_conv.authorized_phase == 5:
        publishing_set_name = conv_data.get("publishing_set")
        if publishing_set_name:
            ps_data = state.get("publishing_sets", {}).get(publishing_set_name)
            if ps_data:
                # Check if ALL conversations in this publishing set are at Phase 5
                all_at_phase_5 = True
                ps_conversations = ps_data.get("conversations", [])
                for ps_conv in ps_conversations:
                    ps_conv_data = state.get("conversations", {}).get(ps_conv, {})
                    if ps_conv_data.get("authorized_phase", 3) < 5:
                        all_at_phase_5 = False
                        break

                if all_at_phase_5:
                    ps_data["status"] = "ready_for_delivery"
                    output.append("")
                    output.append(f"✓ Publishing set '{publishing_set_name}' is now ready_for_delivery")
                    output.append(f"  All conversations at Phase 5")
                    output.append(f"→ Call authorize_publishing_set_phase('{publishing_set_name}') to advance to Phase 6")

    utils.save_state(state)

    return "\n".join(output)


def get_phase_status(conversation: str) -> str:
    """
    Get detailed phase status for a conversation.

    Returns:
    - Current authorized phase
    - Count of pairs in each state (including untagged from file)
    - Emergent framework counts
    - Concept tag summary
    """
    state = utils.load_state()

    if not utils.is_v2_state(state):
        return "get_phase_status requires V2 state format."

    # Load conversation file to get total pair count
    try:
        conv_file = utils.load_conversation(conversation)
        pairs = utils.extract_io_pairs(conv_file)
        total_pairs = len(pairs)
    except FileNotFoundError:
        return f"Conversation file '{conversation}' not found."

    conv_data = state.get("conversations", {}).get(conversation)
    if not conv_data:
        # Conversation exists in file but not in state - all untagged
        phase_counts = {0: total_pairs, 1: 0, 2: 0, 3: 0, 4: 0}
        authorized_phase = 3
        publishing_set = None
        conv = Conversation(authorized_phase=3, publishing_set=None, pairs={})
    else:
        # Build Conversation model
        conv = Conversation(
            authorized_phase=conv_data.get("authorized_phase", 3),
            publishing_set=conv_data.get("publishing_set"),
            pairs=conv_data.get("pairs", {})
        )
        authorized_phase = conv.authorized_phase
        publishing_set = conv.publishing_set

        # Use state machine to get phase counts for TAGGED pairs
        phase_counts = ConversationStateMachine.get_pair_phase_counts(conv)

        # Calculate truly UNTAGGED pairs (in file but not in state)
        pairs_in_state = len(conv.pairs)
        truly_untagged = total_pairs - pairs_in_state
        phase_counts[0] = truly_untagged  # Override with correct count

    # Collect concept tags
    all_concept_tags = set()
    for tags in conv.pairs.values():
        pair = Pair.from_tag_array(tags)
        for tag in pair.concept_tags:
            all_concept_tags.add(tag)

    # Count emergent frameworks
    emergent_frameworks = state.get("emergent_frameworks", {})
    total_emergents = len(emergent_frameworks)
    emergents_with_docs = sum(
        1 for ef in emergent_frameworks.values()
        if ef.get("document") is not None
    )
    emergents_with_canonical = sum(
        1 for ef in emergent_frameworks.values()
        if ef.get("canonical_framework") is not None
    )

    # Build output
    tagged_count = sum(phase_counts[i] for i in range(1, 5))
    output = [
        f"=== Phase Status: {conversation} ===",
        f"",
        f"Total Pairs: {total_pairs}",
        f"Tagged: {tagged_count} / {total_pairs}",
        f"Authorized Phase: {authorized_phase}",
        f"Publishing Set: {publishing_set or 'None'}",
        f"",
        f"Pairs by State:",
        f"  UNTAGGED: {phase_counts[0]}",
        f"  HAS_STRATA (Phase 1): {phase_counts[1]}",
        f"  HAS_DEFINITION (Phase 2): {phase_counts[2]}",
        f"  HAS_CONCEPTS (Phase 3): {phase_counts[3]}",
        f"  HAS_EMERGENT (Phase 4): {phase_counts[4]}",
        f"",
        f"Emergent Frameworks: {total_emergents}",
        f"  With document (Phase 4b): {emergents_with_docs}/{total_emergents}",
        f"  With canonical (Phase 5): {emergents_with_canonical}/{total_emergents}",
        f"",
        f"Concept Tags Found: {len(all_concept_tags)}"
    ]

    if all_concept_tags and len(all_concept_tags) <= 20:
        output.append(f"  Tags: {', '.join(sorted(all_concept_tags))}")
    elif all_concept_tags:
        sample = sorted(all_concept_tags)[:10]
        output.append(f"  Sample: {', '.join(sample)}...")

    return "\n".join(output)
