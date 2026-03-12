"""
State machine for conversation ingestion MCP V2.

Three levels of state machines:
1. PairStateMachine - Per-pair: untagged → strata → definition → concept → emergent
2. ConversationStateMachine - Per-conversation: Phase 3 → 4 → 5
3. PublishingSetStateMachine - Per-set: Phase 5 → 6 → 7 → 8

All operate on Pydantic models (validated data).
All methods are static - no object instantiation needed.
"""

from enum import IntEnum
from typing import Tuple, Optional, List, Dict

from .models import (
    Pair, Conversation, PublishingSet,
    EmergentFramework, Registry, JourneyMetadata
)


# =============================================================================
# STATE ENUMS
# =============================================================================

class PairState(IntEnum):
    """Per-pair states (Phases 1-4 at pair level)."""
    UNTAGGED = 0
    HAS_STRATA = 1      # Phase 1: has strata and/or evolving
    HAS_DEFINITION = 2  # Phase 2: has definition flag
    HAS_CONCEPTS = 3    # Phase 3: has concept tags
    HAS_EMERGENT = 4    # Phase 4: has emergent framework assignment


class ConversationPhase(IntEnum):
    """Per-conversation phases."""
    PHASE_3 = 3  # Tagging (strata, evolving, definition, concepts)
    PHASE_4 = 4  # Emergent framework assignment
    PHASE_5 = 5  # Canonical assignment


class PublishingSetPhase(IntEnum):
    """Per-publishing-set phases."""
    PHASE_5 = 5  # Ingestion complete
    PHASE_6 = 6  # Journey metadata
    PHASE_7 = 7  # Document writing
    PHASE_8 = 8  # Posting complete


# =============================================================================
# PAIR STATE MACHINE
# =============================================================================

class PairStateMachine:
    """
    State machine for individual pairs.

    Transition guards (ratcheting):
    - strata/evolving: always allowed
    - definition: requires strata present
    - concept: requires definition present
    - emergent: requires concepts present
    """

    @staticmethod
    def get_state(pair: Pair) -> PairState:
        """Compute current state from Pair model."""
        if pair.emergent_framework:
            return PairState.HAS_EMERGENT
        if pair.concept_tags:
            return PairState.HAS_CONCEPTS
        if pair.definition:
            return PairState.HAS_DEFINITION
        if pair.strata or pair.evolving:
            return PairState.HAS_STRATA
        return PairState.UNTAGGED

    @staticmethod
    def can_add_strata(pair: Pair, value: str, registry: Registry) -> Tuple[bool, Optional[str]]:
        """Check if strata can be added. Validates against registry."""
        valid_strata = list(registry.strata.keys())
        if value not in valid_strata:
            return False, (
                f"BLOCKED: Invalid strata '{value}'.\n"
                f"Valid strata: {valid_strata}\n"
                f"→ Use add_strata('{value}', 'description') to add it first."
            )
        return True, None

    @staticmethod
    def can_add_evolving(pair: Pair) -> Tuple[bool, Optional[str]]:
        """Check if evolving can be added. Always allowed."""
        return True, None

    @staticmethod
    def can_add_definition(pair: Pair, pair_index: int) -> Tuple[bool, Optional[str]]:
        """Check if definition can be added. Requires strata."""
        if not pair.strata:
            return False, (
                f"BLOCKED: Cannot add 'definition' to pair {pair_index}.\n"
                f"Current state: No strata assigned.\n"
                f"Required: Pair must have strata before adding definition.\n"
                f"→ First call: tag_pair({pair_index}, 'strata', '<strata_name>')"
            )
        return True, None

    @staticmethod
    def can_add_concept(pair: Pair, pair_index: int, value: str) -> Tuple[bool, Optional[str]]:
        """Check if concept tag can be added. Requires definition."""
        if not pair.definition:
            has_strata = "has strata" if pair.strata else "no strata"
            return False, (
                f"BLOCKED: Cannot add concept_tag '{value}' to pair {pair_index}.\n"
                f"Current state: Pair {has_strata} but no definition.\n"
                f"Required: Pair must have 'definition' before adding concept tags.\n"
                f"→ If this pair has substantive content, add definition first.\n"
                f"→ If no substantive content, it stays as evolving-only."
            )
        return True, None

    @staticmethod
    def can_add_emergent(pair: Pair, pair_index: int, value: str) -> Tuple[bool, Optional[str]]:
        """Check if emergent framework can be added. Requires concepts."""
        if not pair.concept_tags:
            return False, (
                f"BLOCKED: Cannot assign emergent_framework '{value}' to pair {pair_index}.\n"
                f"Current state: Pair has no concept tags.\n"
                f"Required: Pair must have concept tags before emergent assignment.\n"
                f"→ Complete Phase 3 (concept tagging) for this pair first."
            )
        return True, None

    @staticmethod
    def apply_strata(pair: Pair, value: str) -> Pair:
        """Return new Pair with strata applied."""
        return Pair(
            strata=value,
            evolving=pair.evolving,
            definition=pair.definition,
            concept_tags=list(pair.concept_tags),
            emergent_framework=pair.emergent_framework
        )

    @staticmethod
    def apply_evolving(pair: Pair) -> Pair:
        """Return new Pair with evolving applied."""
        return Pair(
            strata=pair.strata,
            evolving=True,
            definition=pair.definition,
            concept_tags=list(pair.concept_tags),
            emergent_framework=pair.emergent_framework
        )

    @staticmethod
    def apply_definition(pair: Pair) -> Pair:
        """Return new Pair with definition applied."""
        return Pair(
            strata=pair.strata,
            evolving=pair.evolving,
            definition=True,
            concept_tags=list(pair.concept_tags),
            emergent_framework=pair.emergent_framework
        )

    @staticmethod
    def apply_concept(pair: Pair, value: str) -> Pair:
        """Return new Pair with concept tag added."""
        new_concepts = list(pair.concept_tags)
        if value not in new_concepts:
            new_concepts.append(value)
        return Pair(
            strata=pair.strata,
            evolving=pair.evolving,
            definition=pair.definition,
            concept_tags=new_concepts,
            emergent_framework=pair.emergent_framework
        )

    @staticmethod
    def apply_emergent(pair: Pair, value: str) -> Pair:
        """Return new Pair with emergent framework applied."""
        return Pair(
            strata=pair.strata,
            evolving=pair.evolving,
            definition=pair.definition,
            concept_tags=list(pair.concept_tags),
            emergent_framework=value
        )


# =============================================================================
# CONVERSATION STATE MACHINE
# =============================================================================

class ConversationStateMachine:
    """
    State machine for conversations.

    Phase gates:
    - Phase 3 → 4: User authorization (emergent framework assignment)
    - Phase 4 → 5: User authorization (canonical assignment)
    - Phase 5+: Use PublishingSetStateMachine
    """

    @staticmethod
    def get_phase(conv: Conversation) -> ConversationPhase:
        """Get current authorized phase."""
        phase = conv.authorized_phase
        if phase <= 3:
            return ConversationPhase.PHASE_3
        elif phase == 4:
            return ConversationPhase.PHASE_4
        else:
            return ConversationPhase.PHASE_5

    @staticmethod
    def can_advance(
        conv: Conversation,
        total_pairs: int,
        conv_name: str,
        emergent_frameworks: Optional[Dict[str, dict]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if conversation can advance to next phase.

        Args:
            conv: Conversation model with pairs dict
            total_pairs: Total number of pairs from conversation file
            conv_name: Name of conversation (for error messages)
            emergent_frameworks: Dict of emergent frameworks (for Phase 4→5 document check)

        Gates:
            Phase 3 → 4: ALL pairs must have strata + evolving + concept tags on definition pairs
            Phase 4 → 5: ALL definition pairs must have emergent framework
                         AND all emergent frameworks must have documents (Phase 4b)
        """
        current = conv.authorized_phase

        if current >= 5:
            return False, (
                f"BLOCKED: Conversation already at Phase 5.\n"
                f"→ Use publishing set tools to advance to Phase 6+."
            )

        # Count pairs in state
        pairs_in_state = len(conv.pairs)

        # Phase 3 → 4: ALL pairs must be tagged with at least strata + evolving
        if current == 3:
            if pairs_in_state < total_pairs:
                return False, (
                    f"BLOCKED: Cannot advance '{conv_name}' to Phase 4.\n"
                    f"Only {pairs_in_state} of {total_pairs} pairs have been tagged.\n"
                    f"Required: ALL pairs must have strata + evolving before Phase 4.\n"
                    f"→ Tag remaining {total_pairs - pairs_in_state} pairs first."
                )

            # Check all pairs have strata + evolving
            missing_strata = []
            missing_evolving = []
            for idx_str, tags in conv.pairs.items():
                pair = Pair.from_tag_array(tags)
                if not pair.strata:
                    missing_strata.append(idx_str)
                if not pair.evolving:
                    missing_evolving.append(idx_str)

            if missing_strata:
                return False, (
                    f"BLOCKED: Cannot advance '{conv_name}' to Phase 4.\n"
                    f"{len(missing_strata)} pairs missing strata: {missing_strata[:10]}{'...' if len(missing_strata) > 10 else ''}\n"
                    f"→ Tag all pairs with strata before advancing."
                )

            if missing_evolving:
                return False, (
                    f"BLOCKED: Cannot advance '{conv_name}' to Phase 4.\n"
                    f"{len(missing_evolving)} pairs missing evolving: {missing_evolving[:10]}{'...' if len(missing_evolving) > 10 else ''}\n"
                    f"→ Tag all pairs with evolving before advancing."
                )

            # Check all DEFINITION pairs have concept tags
            definition_missing_concepts = []
            for idx_str, tags in conv.pairs.items():
                pair = Pair.from_tag_array(tags)
                if pair.definition and not pair.concept_tags:
                    definition_missing_concepts.append(idx_str)

            if definition_missing_concepts:
                return False, (
                    f"BLOCKED: Cannot advance '{conv_name}' to Phase 4.\n"
                    f"{len(definition_missing_concepts)} definition pairs missing concept tags: {definition_missing_concepts[:10]}{'...' if len(definition_missing_concepts) > 10 else ''}\n"
                    f"Required: ALL definition pairs must have concept tags before Phase 4.\n"
                    f"→ Add concept tags to all definition pairs first."
                )

        # Phase 4 → 5: ALL definition pairs must have emergent framework
        #              AND all emergent frameworks must have documents (Phase 4b)
        if current == 4:
            missing_emergent = []
            used_emergents = set()
            for idx_str, tags in conv.pairs.items():
                pair = Pair.from_tag_array(tags)
                if pair.definition and not pair.emergent_framework:
                    missing_emergent.append(idx_str)
                elif pair.emergent_framework:
                    used_emergents.add(pair.emergent_framework)

            if missing_emergent:
                return False, (
                    f"BLOCKED: Cannot advance '{conv_name}' to Phase 5.\n"
                    f"{len(missing_emergent)} definition pairs missing emergent framework: {missing_emergent[:10]}{'...' if len(missing_emergent) > 10 else ''}\n"
                    f"→ Assign emergent frameworks to all definition pairs before advancing."
                )

            # Check that all emergent frameworks used by this conversation have documents (JSON files)
            if emergent_frameworks and used_emergents:
                import os
                heaven_data_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
                frameworks_dir = os.path.join(heaven_data_dir, "frameworks")
                missing_docs = []
                for emergent_name in used_emergents:
                    json_path = os.path.join(frameworks_dir, f"emergent_{emergent_name}.json")
                    if not os.path.exists(json_path):
                        missing_docs.append(emergent_name)

                if missing_docs:
                    return False, (
                        f"BLOCKED: Cannot advance '{conv_name}' to Phase 5.\n"
                        f"{len(missing_docs)} emergent frameworks missing synthesized documents:\n" +
                        "\n".join(f"  - {e}" for e in missing_docs[:10]) +
                        ("\n  ..." if len(missing_docs) > 10 else "") +
                        f"\n\nRequired: All emergent frameworks must have documents (Phase 4b).\n"
                        f"→ For each emergent, run:\n"
                        f"  1. get_emergent_pairs('{missing_docs[0]}')\n"
                        f"  2. Read the pairs and synthesize the meaning\n"
                        f"  3. set_emergent_document('{missing_docs[0]}', document)"
                    )

        return True, None

    @staticmethod
    def advance(conv: Conversation) -> Conversation:
        """Return new Conversation with phase incremented."""
        new_phase = min(conv.authorized_phase + 1, 5)
        return Conversation(
            authorized_phase=new_phase,
            publishing_set=conv.publishing_set,
            pairs=dict(conv.pairs)
        )

    @staticmethod
    def get_pair_phase_counts(conv: Conversation) -> Dict[int, int]:
        """Count pairs at each phase level."""
        counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        for tags in conv.pairs.values():
            pair = Pair.from_tag_array(tags)
            state = PairStateMachine.get_state(pair)
            counts[int(state)] = counts.get(int(state), 0) + 1
        return counts


# =============================================================================
# PUBLISHING SET STATE MACHINE
# =============================================================================

class PublishingSetStateMachine:
    """
    State machine for publishing sets.

    Phase gates:
    - Phase 5 → 6: All conversations at Phase 5
    - Phase 6 → 7: All canonicals have journey metadata
    - Phase 7 → 8: All canonical documents written
    """

    @staticmethod
    def get_phase(ps: PublishingSet) -> PublishingSetPhase:
        """Get current phase."""
        phase = ps.phase
        if phase <= 5:
            return PublishingSetPhase.PHASE_5
        elif phase == 6:
            return PublishingSetPhase.PHASE_6
        elif phase == 7:
            return PublishingSetPhase.PHASE_7
        else:
            return PublishingSetPhase.PHASE_8

    @staticmethod
    def can_advance_to_6(
        ps: PublishingSet,
        conversations: Dict[str, Conversation]
    ) -> Tuple[bool, Optional[str]]:
        """Check if publishing set can advance to Phase 6."""
        not_ready = []
        for conv_name in ps.conversations:
            conv = conversations.get(conv_name)
            if not conv:
                not_ready.append(f"{conv_name} (not found)")
            elif conv.authorized_phase < 5:
                not_ready.append(f"{conv_name} (Phase {conv.authorized_phase})")

        if not_ready:
            return False, (
                f"BLOCKED: Cannot advance to Phase 6.\n"
                f"{len(not_ready)} of {len(ps.conversations)} conversations not at Phase 5:\n" +
                "\n".join(f"  - {c}" for c in not_ready) +
                "\n→ Complete ingestion for remaining conversations first."
            )
        return True, None

    @staticmethod
    def can_advance_to_7(
        ps: PublishingSet,
        emergents: Dict[str, EmergentFramework],
        journey_metadata: Dict[str, JourneyMetadata]
    ) -> Tuple[bool, Optional[str]]:
        """Check if publishing set can advance to Phase 7."""
        # Get all canonicals from emergents
        canonicals = set(
            e.canonical_framework
            for e in emergents.values()
            if e.canonical_framework
        )

        missing = []
        for canonical in canonicals:
            jm = journey_metadata.get(canonical)
            if not jm or not jm.is_complete():
                missing.append(canonical)

        if missing:
            return False, (
                f"BLOCKED: Cannot advance to Phase 7.\n"
                f"Canonicals missing journey metadata:\n" +
                "\n".join(f"  - {c}" for c in missing) +
                "\n→ Call set_journey_metadata() for each canonical."
            )
        return True, None

    @staticmethod
    def can_advance_to_8(
        ps: PublishingSet,
        canonicals_with_documents: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Check if publishing set can advance to Phase 8."""
        # This would check if all canonical documents are written
        # For now, we assume if we're at Phase 7, documents can be checked
        return True, None

    @staticmethod
    def advance(ps: PublishingSet) -> PublishingSet:
        """Return new PublishingSet with phase incremented."""
        new_phase = min(ps.phase + 1, 8)
        return PublishingSet(
            conversations=list(ps.conversations),
            phase=new_phase
        )


# =============================================================================
# BATCH COHERENCE CHECK
# =============================================================================

def check_batch_coherence(
    pair: Pair,
    pair_index: int,
    operations: List[dict],
    registry: Registry
) -> Tuple[bool, Optional[str]]:
    """
    Check if a batch of operations is coherent.

    A batch is coherent if the operations, when applied in order,
    satisfy ratcheting rules. Allows [strata, definition, concept] in one batch.
    """
    # Simulate applying operations
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

        # Check guard
        if tag_type == "strata":
            allowed, error = PairStateMachine.can_add_strata(simulated, value, registry)
        elif tag_type == "evolving":
            allowed, error = PairStateMachine.can_add_evolving(simulated)
        elif tag_type == "definition":
            allowed, error = PairStateMachine.can_add_definition(simulated, pair_index)
        elif tag_type == "concept":
            allowed, error = PairStateMachine.can_add_concept(simulated, pair_index, value)
        elif tag_type == "emergent_framework":
            allowed, error = PairStateMachine.can_add_emergent(simulated, pair_index, value)
        else:
            return False, f"Unknown tag_type: {tag_type}"

        if not allowed:
            return False, error

        # Apply to simulation
        if tag_type == "strata":
            simulated = PairStateMachine.apply_strata(simulated, value)
        elif tag_type == "evolving":
            simulated = PairStateMachine.apply_evolving(simulated)
        elif tag_type == "definition":
            simulated = PairStateMachine.apply_definition(simulated)
        elif tag_type == "concept":
            simulated = PairStateMachine.apply_concept(simulated, value)
        elif tag_type == "emergent_framework":
            simulated = PairStateMachine.apply_emergent(simulated, value)

    return True, None
