"""
Pydantic models for conversation ingestion MCP V2.

These models are the VALIDATION layer. The AI still applies tags via tools.
The tools use these models to validate operations before applying them.

Storage: CartON (Neo4j + ChromaDB)
Runtime: Pydantic models (validation layer)
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict


# =============================================================================
# INGESTION-TIME MODELS (Phases 1-5)
# =============================================================================

class Pair(BaseModel):
    """
    Represents the semantic meaning of a pair's tag array.

    The actual storage is an array of tag strings.
    This model parses that array for validation.
    """
    strata: Optional[str] = None  # User-defined strata name
    evolving: bool = False  # pair was READ (EVERY pair must get this)
    definition: bool = False  # pair has logic in it that is part of a definition
    concept_tags: List[str] = Field(default_factory=list)
    emergent_framework: Optional[str] = None  # reference by name

    # NOTE: evolving and definition are NOT mutually exclusive
    # - evolving=True, definition=False -> read, no definition logic
    # - evolving=True, definition=True -> read AND has definition logic

    @classmethod
    def from_tag_array(cls, tags: List[str]) -> "Pair":
        """
        Parse a tag array into a Pair model for validation.

        Tag format conventions:
        - strata:{name} -> strata tag (e.g., "strata:paiab")
        - evolving -> evolving flag
        - definition -> definition flag
        - emergent_framework:{name} -> emergent framework assignment
        - anything else -> concept tag
        """
        strata = None
        evolving = False
        definition = False
        concept_tags = []
        emergent_framework = None

        for tag in tags:
            if tag.startswith("strata:"):
                strata = tag[len("strata:"):]
            elif tag == "evolving":
                evolving = True
            elif tag == "definition":
                definition = True
            elif tag.startswith("emergent_framework:"):
                emergent_framework = tag[len("emergent_framework:"):]
            else:
                # Everything else is a concept tag
                concept_tags.append(tag)

        return cls(
            strata=strata,
            evolving=evolving,
            definition=definition,
            concept_tags=concept_tags,
            emergent_framework=emergent_framework
        )

    def get_phase(self) -> int:
        """Determine what phase this pair is at based on its tags."""
        if self.emergent_framework:
            return 4
        if self.concept_tags:
            return 3
        if self.definition:
            return 2
        if self.strata or self.evolving:
            return 1
        return 0


class EmergentFramework(BaseModel):
    """
    Discovered cluster of content in a domain.

    Only has name + strata. Does NOT have type or state.
    Type and state belong to CANONICALS, not emergents.

    Emergent frameworks are NOT just labels - they are sub-components with
    their own synthesized documents. Multiple emergents compose into one canonical.

    SOURCE TYPES:
    - "conversation": Extracted from conversation pairs (Phases 1-4 required)
    - "kg_collection": Already distilled in knowledge graph (starts at Phase 5)

    Phase 4a: Pairs get tagged with emergent_framework:X
    Phase 4b: Bundle pairs per emergent → Synthesize document
    Phase 5: Assign emergent to canonical (requires document)
    """
    name: str
    strata: str  # User-defined strata name
    description: str  # REQUIRED: Short definition of what this framework IS
    # Source tracking - determines which phases apply
    source_type: Literal["conversation", "kg_collection"] = "conversation"
    source_ref: Optional[str] = None  # collection URI (kg) or conversation name
    canonical_framework: Optional[str] = None  # reference by name, set in Phase 5
    bundled_pairs: Dict[str, List[int]] = Field(default_factory=dict)  # conversation -> pair indices
    document: Optional[str] = None  # full synthesized content from bundled pairs (Phase 4b)
    # Relationship fields - queryable without reading documents
    part_of: Optional[str] = None  # parent framework this is a component of
    has_parts: List[str] = Field(default_factory=list)  # child frameworks that are components of this
    related_to: List[str] = Field(default_factory=list)  # sibling/related frameworks


class Conversation(BaseModel):
    """Tracks a conversation's ingestion state."""
    authorized_phase: int = 3  # Phases 1-3 simultaneous, need auth for 4+
    publishing_set: Optional[str] = None
    pairs: Dict[str, List[str]] = Field(default_factory=dict)  # pair_index -> tag array


class PublishingSet(BaseModel):
    """Group of conversations being ingested together."""
    conversations: List[str] = Field(default_factory=list)
    phase: int = 5  # Publishing set phase (5 = ingestion complete, 6-8 = delivery)
    status: Literal["in_progress", "ready_for_delivery", "delivered"] = "in_progress"

    # NOTE: canonical_frameworks is DERIVED, not stored
    # Computed by: "which canonicals do emergents in these conversations point to?"
    # NOTE: status auto-updates:
    #   - in_progress: at least one conversation not at Phase 5
    #   - ready_for_delivery: all conversations at Phase 5 (auto-set when last conv reaches Phase 5)
    #   - delivered: Phase 8 complete (auto-set when authorize_publishing_set_phase reaches Phase 8)


# =============================================================================
# REGISTRY MODELS (Canonical Framework Source of Truth)
# =============================================================================

class CanonicalEntry(BaseModel):
    """Entry for a canonical framework in the registry."""
    framework_state: Literal["aspirational", "actual"]


class StrataSlots(BaseModel):
    """Slots within a strata, each containing canonical entries."""
    reference: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    collection: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    workflow: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    library: Dict[str, CanonicalEntry] = Field(default_factory=dict)
    operating_context: Dict[str, CanonicalEntry] = Field(default_factory=dict)


class StrataEntry(BaseModel):
    """A strata (PAIAB, SANCTUM, CAVE) with its slots."""
    name: str
    description: str
    slots: StrataSlots = Field(default_factory=StrataSlots)


class Registry(BaseModel):
    """
    Authoritative source for canonical frameworks.

    Type is implicit from slot. Strata is implicit from parent.
    framework_state is stored per-entry.
    """
    strata: Dict[str, StrataEntry] = Field(default_factory=dict)

    def get_canonical(self, canonical_name: str) -> Optional[tuple]:
        """
        Look up a canonical by name.

        Returns: (type, strata, framework_state) or None
        """
        for strata_key, strata_entry in self.strata.items():
            for slot_type in ['reference', 'collection', 'workflow', 'library', 'operating_context']:
                slot_entries = getattr(strata_entry.slots, slot_type)
                if canonical_name in slot_entries:
                    entry = slot_entries[canonical_name]
                    return (slot_type, strata_key, entry.framework_state)
        return None

    def canonical_exists(self, canonical_name: str) -> bool:
        """Check if a canonical framework exists in the registry."""
        return self.get_canonical(canonical_name) is not None

    def get_canonical_strata(self, canonical_name: str) -> Optional[str]:
        """Get the strata for a canonical framework."""
        result = self.get_canonical(canonical_name)
        return result[1] if result else None


# =============================================================================
# DELIVERY-TIME MODELS (Phases 6-8)
# =============================================================================

class JourneyMetadata(BaseModel):
    """Obstacle/overcome/dream for a canonical framework."""
    obstacle: Optional[str] = None
    overcome: Optional[str] = None
    dream: Optional[str] = None

    def is_complete(self) -> bool:
        """All three fields must be set for Phase 6 completion."""
        return all([self.obstacle, self.overcome, self.dream])


class CanonicalFramework(BaseModel):
    """
    Full canonical object created at Phase 6.

    Bundles all emergent frameworks that point to it.
    This is the HYDRATED form - created from registry + emergents.
    """
    name: str
    type: Literal["Reference", "Collection", "Workflow", "Library", "Operating_Context"]
    strata: str  # User-defined strata name
    framework_state: Literal["aspirational", "actual"]
    journey: JourneyMetadata = Field(default_factory=JourneyMetadata)
    emergent_frameworks: List[str] = Field(default_factory=list)  # names of bundled emergents
    template: Optional[str] = None  # metastack template name
    document: Optional[str] = None  # rendered output
    posted_to: List[str] = Field(default_factory=list)  # substrates posted to


# =============================================================================
# HYDRATION FUNCTION
# =============================================================================

def hydrate_canonicals(
    publishing_set: PublishingSet,
    emergents: Dict[str, EmergentFramework],
    registry: Registry
) -> Dict[str, CanonicalFramework]:
    """
    Create full canonical objects from emergent framework references.

    Called when publishing set advances to Phase 6.
    """
    # DERIVE which canonicals this publishing set produced
    # by looking at what emergents point to
    canonical_names = set(
        e.canonical_framework
        for e in emergents.values()
        if e.canonical_framework is not None
    )

    canonicals = {}
    for canonical_name in canonical_names:
        # Find all emergents pointing to this canonical
        bundled = [e.name for e in emergents.values() if e.canonical_framework == canonical_name]

        # Get type/strata/framework_state from registry (authoritative source)
        reg_entry = registry.get_canonical(canonical_name)

        if reg_entry is None:
            # Canonical not in registry - this shouldn't happen if validation worked
            continue

        canonicals[canonical_name] = CanonicalFramework(
            name=canonical_name,
            type=reg_entry[0],
            strata=reg_entry[1],
            framework_state=reg_entry[2],
            emergent_frameworks=bundled
        )

    return canonicals
