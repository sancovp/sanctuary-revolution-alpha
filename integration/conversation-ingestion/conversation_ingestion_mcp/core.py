"""
Core module - imports and re-exports all tools.

This module is kept slim. All logic lives in:
- state_machine.py - State machine classes
- navigation.py - show_pairs, next_pair, set_conversation, status
- tagging.py - tag_pair, tag_range, batch_tag_operations, add_tag, list_tags
- phase_tools.py - authorize_next_phase, get_phase_status
- emergent_tools.py - add_or_update_emergent_framework, assign_canonical_to_emergent
- registry_tools.py - add_canonical_framework, list_canonical_frameworks, etc.
- publishing_tools.py - create_publishing_set, get_publishing_set_status, etc.
- journey_tools.py - set_journey_metadata, get_journey_metadata
- bundle_tools.py - bundle_tagged, bundle_multi_tag
- legacy.py - deprecated V1 tools
"""

# Navigation
from .navigation import (
    show_pairs,
    next_pair,
    set_conversation,
    status,
)

# Tagging
from .tagging import (
    tag_pair,
    tag_range,
    batch_tag_operations,
    add_tag,
    list_tags,
)

# Phase Management
from .phase_tools import (
    authorize_next_phase,
    get_phase_status,
)

# Emergent Frameworks
from .emergent_tools import (
    add_or_update_emergent_framework,
    add_emergent_from_kg,  # KG-sourced emergents (skip Phases 1-4)
    assign_canonical_to_emergent,
    delete_emergent_framework,
    # Synthesis tools (Phase 4b)
    list_emergent_frameworks,
    get_emergent_pairs,
    synthesize_emergent,
    # Phase 5/6/7 tools
    set_emergent_document,
    preview_emergent,
    set_canonical_document,
    preview_canonical,
)

# Registry
from .registry_tools import (
    add_canonical_framework,
    list_canonical_frameworks,
    remove_canonical_framework,
    add_strata,
)

# Publishing Sets
from .publishing_tools import (
    create_publishing_set,
    get_publishing_set_status,
    authorize_publishing_set_phase,
    set_publishing_set,
    list_publishing_sets,
    list_available_conversations,
)

# Journey Metadata
from .journey_tools import (
    set_journey_metadata,
    get_journey_metadata,
)

# Bundling
from .bundle_tools import (
    bundle_tagged,
    bundle_multi_tag,
)

# Scores Registry
from .scores_tools import (
    get_scores_registry,
)

# get_instructions lives in legacy but is still used (V2 version)
from .legacy import get_instructions

# Waitlist (Claude Code native ingestion)
from .waitlist_utils import (
    flag_for_ingestion,
    flag_conversation,
    get_ingestion_waitlist,
    update_waitlist_status,
    remove_from_waitlist,
    get_waitlist_stats,
)

# Claude Code transcript parsing
from .claude_transcript_utils import (
    TranscriptEntry,
    Conversation,
    parse_transcript_file,
    get_unique_slugs,
    segment_by_slug,
    get_conversation_by_slug,
    list_conversations_in_file,
)

# Converters — JSON transcript files → CartON concepts
from .utils import (
    ingest_openai_transcript,
    ingest_claude_transcript,
)

# Expose all for * imports
__all__ = [
    # Navigation
    'show_pairs',
    'next_pair',
    'set_conversation',
    'status',
    # Tagging
    'tag_pair',
    'tag_range',
    'batch_tag_operations',
    'add_tag',
    'list_tags',
    # Phase Management
    'authorize_next_phase',
    'get_phase_status',
    # Emergent Frameworks
    'add_or_update_emergent_framework',
    'add_emergent_from_kg',
    'assign_canonical_to_emergent',
    'delete_emergent_framework',
    'list_emergent_frameworks',
    'get_emergent_pairs',
    'synthesize_emergent',
    'set_emergent_document',
    'preview_emergent',
    'set_canonical_document',
    'preview_canonical',
    # Registry
    'add_canonical_framework',
    'list_canonical_frameworks',
    'remove_canonical_framework',
    'add_strata',
    # Publishing Sets
    'create_publishing_set',
    'get_publishing_set_status',
    'authorize_publishing_set_phase',
    'set_publishing_set',
    'list_publishing_sets',
    'list_available_conversations',
    # Journey Metadata
    'set_journey_metadata',
    'get_journey_metadata',
    # Bundling
    'bundle_tagged',
    'bundle_multi_tag',
    # Scores Registry
    'get_scores_registry',
    # Instructions (still used in V2)
    'get_instructions',
    # Waitlist (Claude Code native ingestion)
    'flag_for_ingestion',
    'flag_conversation',
    'get_ingestion_waitlist',
    'update_waitlist_status',
    'remove_from_waitlist',
    'get_waitlist_stats',
    # Claude Code transcript parsing
    'TranscriptEntry',
    'Conversation',
    'parse_transcript_file',
    'get_unique_slugs',
    'segment_by_slug',
    'get_conversation_by_slug',
    'list_conversations_in_file',
    # Converters
    'ingest_openai_transcript',
    'ingest_claude_transcript',
]
