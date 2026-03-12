"""
Navigation tools for conversation ingestion.

Tools: show_pairs, next_pair, set_conversation, status
"""

from . import utils
from .models import Pair, Conversation
from .state_machine import PairStateMachine, ConversationStateMachine


def show_pairs(start: int, end: int) -> str:
    """Display range of IO pairs from current conversation."""
    state = utils.load_state()

    if not state.get('current_conversation'):
        return "❌ No conversation selected. Use set_conversation() first."

    conv_name = state['current_conversation']
    conv = utils.load_conversation(conv_name)
    pairs = utils.extract_io_pairs(conv)

    if start < 0 or end > len(pairs):
        return f"❌ Invalid range. Conversation has {len(pairs)} pairs."

    output = [
        f"Conversation: {conv_name}",
        f"Pairs {start}-{end} of {len(pairs)}",
        "=" * 60
    ]

    for i in range(start, end):
        _, user_msg, _, asst_msg = pairs[i]
        tags = utils.get_pair_tags(state, conv_name, i)
        pair = Pair.from_tag_array(tags)
        pair_display = utils.format_pair_display_v2(i, user_msg, asst_msg, pair)
        output.append(f"\n{pair_display}")

    return "\n".join(output)


def next_pair() -> str:
    """Show next unprocessed pair."""
    state = utils.load_state()

    if not state.get('current_conversation'):
        return "❌ No conversation selected."

    idx = state.get('current_index', 0)
    return show_pairs(idx, idx + 1)


def set_conversation(name: str) -> str:
    """Switch to a different conversation."""
    state = utils.load_state()

    try:
        conv = utils.load_conversation(name)
    except FileNotFoundError:
        available = state.get('conversation_priority', [])
        return f"❌ Conversation '{name}' not found. Available: {available}"

    # Gate: must have active publishing set and conversation must be in it
    if utils.is_v2_state(state):
        active_ps = state.get("active_publishing_set")

        # Check 1: Is there an active publishing set?
        if not active_ps:
            return (
                f"BLOCKED: Cannot set conversation '{name}'.\n"
                f"No active publishing set.\n"
                f"→ Call set_publishing_set('set_name') first."
            )

        # Check 2: Is the conversation in the ACTIVE publishing set?
        ps_data = state.get("publishing_sets", {}).get(active_ps, {})
        ps_conversations = ps_data.get("conversations", [])

        if name not in ps_conversations:
            # Check if it's in a DIFFERENT publishing set
            in_other_ps = None
            for ps_name, other_ps_data in state.get("publishing_sets", {}).items():
                if ps_name != active_ps and name in other_ps_data.get("conversations", []):
                    in_other_ps = ps_name
                    break

            if in_other_ps:
                return (
                    f"BLOCKED: Cannot set conversation '{name}'.\n"
                    f"Conversation is in publishing set '{in_other_ps}', not active set '{active_ps}'.\n"
                    f"→ Call set_publishing_set('{in_other_ps}') to switch publishing sets."
                )
            else:
                return (
                    f"BLOCKED: Cannot set conversation '{name}'.\n"
                    f"Conversation is not in active publishing set '{active_ps}'.\n"
                    f"Available conversations: {ps_conversations}\n"
                    f"→ Choose from available conversations or add this one to the publishing set."
                )

        publishing_set_name = active_ps
    else:
        publishing_set_name = None

    state['current_conversation'] = name
    state['current_index'] = 0
    utils.save_state(state)

    pairs = utils.extract_io_pairs(conv)
    ps_info = f" (publishing set: {publishing_set_name})" if publishing_set_name else ""
    return f"✓ Switched to '{name}' ({len(pairs)} pairs){ps_info}"


def status() -> str:
    """Show current status with V2 phase info."""
    state = utils.load_state()

    if not state.get('current_conversation'):
        return "❌ No conversation selected."

    conv_name = state['current_conversation']
    conv_file = utils.load_conversation(conv_name)
    pairs = utils.extract_io_pairs(conv_file)

    output = [
        f"=== Status: {conv_name} ===",
        f"",
        f"Total pairs: {len(pairs)}",
        f"Current index: {state.get('current_index', 0)}",
    ]

    # V2 info
    if utils.is_v2_state(state):
        active_ps = state.get("active_publishing_set")
        conv_data = state.get("conversations", {}).get(conv_name, {})
        phase = conv_data.get("authorized_phase", 3)
        publishing_set = conv_data.get("publishing_set")
        pairs_data = conv_data.get("pairs", {})

        # Show active publishing set
        output.append(f"")
        output.append(f"Active publishing set: {active_ps or 'None'}")

        # Count pairs by state (only for pairs in state)
        state_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        for tags in pairs_data.values():
            pair = Pair.from_tag_array(tags)
            pair_state = PairStateMachine.get_state(pair)
            state_counts[int(pair_state)] += 1

        # Calculate truly UNTAGGED pairs (in file but not in state)
        total_pairs = len(pairs)
        pairs_in_state = len(pairs_data)
        truly_untagged = total_pairs - pairs_in_state
        state_counts[0] = truly_untagged  # Override with correct count

        tagged_count = sum(state_counts[i] for i in range(1, 5))

        output.extend([
            f"",
            f"Tagged: {tagged_count} / {total_pairs}",
            f"Authorized phase: {phase}",
            f"Publishing set: {publishing_set or 'None'}",
            f"",
            f"Pairs by state:",
            f"  Untagged: {state_counts[0]}",
            f"  Has strata (Phase 1): {state_counts[1]}",
            f"  Has definition (Phase 2): {state_counts[2]}",
            f"  Has concepts (Phase 3): {state_counts[3]}",
            f"  Has emergent (Phase 4): {state_counts[4]}",
        ])

        # Emergent frameworks count
        emergents = state.get("emergent_frameworks", {})
        output.append(f"")
        output.append(f"Emergent frameworks: {len(emergents)}")

        # Concept tags count
        concepts = state.get("concept_tags", [])
        output.append(f"Concept tags: {len(concepts)}")

    return "\n".join(output)
