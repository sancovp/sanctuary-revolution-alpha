"""
MCP server wrapping conversation ingestion tools (V2)

NO business logic - just wraps core functions.
Tool changes per spec lines 536-632.
"""
import logging
from typing import List, Optional
from fastmcp import FastMCP

from . import core

logger = logging.getLogger(__name__)

mcp = FastMCP("conversation-ingestion")


# =============================================================================
# KEEP AS-IS (from V1)
# =============================================================================

@mcp.tool()
def show_pairs(start: int, end: int) -> str:
    """Display range of IO pairs from current conversation"""
    return core.show_pairs(start, end)


@mcp.tool()
def next_pair() -> str:
    """Show next unprocessed pair"""
    return core.next_pair()


@mcp.tool()
def set_conversation(name: str) -> str:
    """Switch to a different conversation file

    BLOCKED unless:
    1. There is an active publishing set (call set_publishing_set first)
    2. The conversation is in the active publishing set
    """
    return core.set_conversation(name)


@mcp.tool()
def bundle_tagged(tag: str, output_name: str) -> str:
    """Bundle all pairs with given tag into a JSON document"""
    return core.bundle_tagged(tag, output_name)


@mcp.tool()
def bundle_multi_tag(tags: List[str], output_name: str) -> str:
    """Bundle pairs matching ANY of the given tags into a JSON document"""
    return core.bundle_multi_tag(tags, output_name)


# =============================================================================
# MODIFIED (V1 → V2)
# =============================================================================

@mcp.tool()
def tag_pair(index: int, tag_type: str, value: str = "") -> str:
    """Tag a specific pair with ratcheting validation (V2)

    Ratcheting Rules (BLOCKED unless prerequisites met):
    - strata, evolving: Always allowed
    - definition: BLOCKED unless pair has strata
    - concept: BLOCKED unless pair has definition
    - emergent_framework: BLOCKED unless pair has concept tags

    When blocked, returns error explaining what to do first.

    Args:
        index: Pair index to tag
        tag_type: One of 'strata', 'evolving', 'definition', 'concept', 'emergent_framework'
        value: Tag value (required for strata, concept, emergent_framework)
    """
    return core.tag_pair(index, tag_type, value)


@mcp.tool()
def tag_range(start: int, end: int, tag_type: str, value: str = "") -> str:
    """Tag a range of pairs with ratcheting validation (V2)

    Same ratcheting rules as tag_pair apply to each pair in range.
    If ANY pair in range would be blocked, entire operation fails.

    Args:
        start: Start index (inclusive)
        end: End index (exclusive)
        tag_type: One of 'strata', 'evolving', 'definition', 'concept', 'emergent_framework'
        value: Tag value (required for strata, concept, emergent_framework)
    """
    return core.tag_range(start, end, tag_type, value)


@mcp.tool()
def batch_tag_operations(operations: List[dict]) -> str:
    """Execute multiple tag operations with coherence checking (V2)

    Coherence checking validates by INPUT ARGS, not just existing state.
    This allows adding [strata, definition, concept] to a pair in ONE batch
    because the batch itself satisfies the ratcheting chain.

    Atomic: if any operation fails validation, NONE are applied.

    Args:
        operations: List of operation dicts:
            - {"action": "tag_pair", "index": int, "tag_type": str, "value": str}
            - {"action": "tag_range", "start": int, "end": int, "tag_type": str, "value": str}
    """
    return core.batch_tag_operations(operations)


@mcp.tool()
def add_tag(tag_names: List[str]) -> str:
    """Add new concept tag(s) - only adds to concept_tags (V2)"""
    return core.add_tag(tag_names)


@mcp.tool()
def list_tags() -> str:
    """Show all tags organized by type (strata, state, concept, emergent)"""
    return core.list_tags()


@mcp.tool()
def status() -> str:
    """Show current status with V2 phase info"""
    return core.status()


@mcp.tool()
def get_instructions() -> str:
    """Get V2 8-phase workflow instructions"""
    return core.get_instructions()


@mcp.tool()
def add_or_update_emergent_framework(
    name: str,
    strata: str,
    description: str,
    part_of: Optional[str] = None,
    has_parts: Optional[List[str]] = None,
    related_to: Optional[List[str]] = None
) -> str:
    """Add or update emergent framework (V2: name + strata + REQUIRED description)

    Args:
        name: Framework name
        strata: paiab | sanctum | cave
        description: REQUIRED - Short definition of what this framework IS
        part_of: Optional parent framework this is a component of
        has_parts: Optional list of child frameworks that are components of this
        related_to: Optional list of sibling/related frameworks
    """
    return core.add_or_update_emergent_framework(
        name, strata, description,
        part_of=part_of,
        has_parts=has_parts,
        related_to=related_to
    )


@mcp.tool()
def add_emergent_from_kg(
    name: str,
    strata: str,
    description: str,
    collection_ref: str,
    part_of: Optional[str] = None,
    has_parts: Optional[List[str]] = None,
    related_to: Optional[List[str]] = None
) -> str:
    """Add emergent framework from knowledge graph collection (skips Phases 1-4)

    KG-sourced emergents are already distilled content - they don't need
    conversation extraction. They start directly at Phase 5 synthesis.

    Args:
        name: Framework name
        strata: paiab | sanctum | cave
        description: Short definition of what this framework IS
        collection_ref: URI to KG collection (e.g., "carton://collections/PAIA_Architecture")
        part_of: Optional parent framework
        has_parts: Optional child frameworks
        related_to: Optional related frameworks
    """
    return core.add_emergent_from_kg(
        name, strata, description, collection_ref,
        part_of=part_of,
        has_parts=has_parts,
        related_to=related_to
    )


# =============================================================================
# NEW - Phase Management
# =============================================================================

@mcp.tool()
def authorize_next_phase(conversation: str) -> str:
    """Advance conversation to next phase (3→4→5)

    Phase gates require user approval before advancing:
    - 3→4: "Ready to assign emergent frameworks?" (requires all definition pairs have concepts)
    - 4→5: "Ready to map to canonicals?" (requires all emergents have documents)

    Returns error if already at Phase 5 (use authorize_publishing_set_phase for 5→6+)
    """
    return core.authorize_next_phase(conversation)


@mcp.tool()
def get_phase_status(conversation: str) -> str:
    """Get detailed phase status for a conversation"""
    return core.get_phase_status(conversation)


# =============================================================================
# NEW - Emergent Framework Operations
# =============================================================================

@mcp.tool()
def assign_canonical_to_emergent(emergent_name: str, canonical_name: str) -> str:
    """Assign canonical framework to emergent (Phase 5 only)

    BLOCKED unless:
    1. Conversation is in Phase 5
    2. Canonical exists in registry (use add_canonical_framework first if not)
    3. Emergent's strata matches canonical's strata

    Error messages explain what to do if blocked.
    """
    return core.assign_canonical_to_emergent(emergent_name, canonical_name)


@mcp.tool()
def delete_emergent_framework(name: str) -> str:
    """Delete an emergent framework"""
    return core.delete_emergent_framework(name)


# =============================================================================
# NEW - Emergent Framework Synthesis Tools (Phase 4b)
# =============================================================================

@mcp.tool()
def list_emergent_frameworks() -> str:
    """List all emergent frameworks with pair counts and synthesis status"""
    return core.list_emergent_frameworks()


@mcp.tool()
def get_emergent_pairs(emergent_name: str) -> str:
    """Get all pairs assigned to an emergent framework for synthesis"""
    return core.get_emergent_pairs(emergent_name)


@mcp.tool()
def synthesize_emergent(emergent_name: str) -> str:
    """Get synthesis workflow guidance for an emergent framework"""
    return core.synthesize_emergent(emergent_name)


@mcp.tool()
def set_emergent_document(emergent_name: str) -> str:
    """Create the JSON file for an emergent framework (Phase 5).

    Vendors a JSON skeleton at the known path. You then edit the JSON
    directly to fill in the content.

    Returns path to JSON file, or error if already exists.
    """
    return core.set_emergent_document(emergent_name)


@mcp.tool()
def preview_emergent(emergent_name: str, output_path: str) -> str:
    """Render emergent framework JSON to markdown for review (Phase 6).

    Loads JSON from known path, renders to markdown, writes to output_path.
    Use this to see what the framework looks like. Edit JSON, preview, iterate.
    """
    return core.preview_emergent(emergent_name, output_path)


@mcp.tool()
def set_canonical_document(canonical_name: str, emergents: List[str]) -> str:
    """Create the JSON file for a canonical framework (Phase 7).

    Vendors a JSON skeleton with refs to emergent JSONs.

    Args:
        canonical_name: Name of the canonical framework
        emergents: List of emergent framework names to include
    """
    return core.set_canonical_document(canonical_name, emergents)


@mcp.tool()
def preview_canonical(canonical_name: str, output_path: str) -> str:
    """Render canonical framework + emergents to markdown for review (Phase 7).

    Loads canonical JSON and all referenced emergent JSONs, composes into
    a single markdown document.
    """
    return core.preview_canonical(canonical_name, output_path)


# =============================================================================
# NEW - Registry Tools
# =============================================================================

@mcp.tool()
def add_canonical_framework(
    strata: str,
    slot_type: str,
    framework_name: str,
    framework_state: str
) -> str:
    """Add canonical framework to registry

    Args:
        strata: paiab | sanctum | cave
        slot_type: reference | collection | workflow | library | operating_context
        framework_name: Name of the canonical framework
        framework_state: aspirational | actual
    """
    return core.add_canonical_framework(strata, slot_type, framework_name, framework_state)


@mcp.tool()
def list_canonical_frameworks(
    strata: Optional[str] = None,
    slot_type: Optional[str] = None
) -> str:
    """List canonical frameworks from registry"""
    return core.list_canonical_frameworks(strata, slot_type)


@mcp.tool()
def remove_canonical_framework(
    strata: str,
    slot_type: str,
    framework_name: str
) -> str:
    """Remove canonical framework from registry"""
    return core.remove_canonical_framework(strata, slot_type, framework_name)


@mcp.tool()
def add_strata(name: str, description: str) -> str:
    """Add new strata to registry"""
    return core.add_strata(name, description)


# =============================================================================
# NEW - Publishing Set Tools
# =============================================================================

@mcp.tool()
def create_publishing_set(name: str, conversations: List[str], force: bool = False) -> str:
    """Create publishing set with specified conversations. Use force=True to reassign conversations from existing sets."""
    return core.create_publishing_set(name, conversations, force)


@mcp.tool()
def get_publishing_set_status(name: str) -> str:
    """Get status of publishing set"""
    return core.get_publishing_set_status(name)


@mcp.tool()
def authorize_publishing_set_phase(name: str, force: bool = False) -> str:
    """Advance publishing set to next phase (5→6→7→8)

    Phase gates (BLOCKED unless prerequisites met):
    - 5→6: ALL conversations in set must be at Phase 5
    - 6→7: ALL canonicals must have journey metadata (obstacle/overcome/dream)
    - 7→8: ALL canonical documents must be written (REQUIRES force=True)

    The 7→8 transition is the COMMIT POINT. You must confirm with the user that
    the synthesis is finalized before calling with force=True.

    When Phase 8 reached, status auto-updates to 'delivered'.
    """
    return core.authorize_publishing_set_phase(name, force)


@mcp.tool()
def set_publishing_set(name: str) -> str:
    """Activate a publishing set as current working set

    MUST call this before set_conversation() - cannot work on conversations
    without an active publishing set.

    BLOCKED if publishing set status is 'delivered'.
    """
    return core.set_publishing_set(name)


@mcp.tool()
def list_publishing_sets(include_delivered: bool = False) -> str:
    """List all publishing sets (hides delivered by default)"""
    return core.list_publishing_sets(include_delivered)


@mcp.tool()
def list_available_conversations() -> str:
    """List conversations in active publishing set not yet at Phase 5"""
    return core.list_available_conversations()


# =============================================================================
# NEW - Journey Metadata Tools
# =============================================================================

@mcp.tool()
def set_journey_metadata(
    canonical_framework: str,
    obstacle: str,
    overcome: str,
    dream: str
) -> str:
    """Set journey metadata for canonical (Phase 6+)

    BLOCKED unless publishing set is in Phase 6 or higher.
    All three fields (obstacle, overcome, dream) required together.

    This is required before advancing to Phase 7.
    """
    return core.set_journey_metadata(canonical_framework, obstacle, overcome, dream)


@mcp.tool()
def get_journey_metadata(canonical_framework: str) -> str:
    """Get journey metadata for canonical"""
    return core.get_journey_metadata(canonical_framework)


# =============================================================================
# NEW - Waitlist Tools (Claude Code Native Ingestion)
# =============================================================================

@mcp.tool()
def flag_conversation(
    cwd: str,
    reason: str = "",
    priority: int = 5,
    current: bool = True,
    conversation_id: Optional[str] = None,
    transcript_path: Optional[str] = None,
    guide: bool = False
) -> str:
    """Flag a conversation for later ingestion OR get guide on how to browse transcripts.

    Three modes:
    1. guide=True: Returns docs on how to find/read transcripts (overrides all other params)
    2. current=True (default): Flags the most recent transcript
    3. current=False: Flags a specific conversation_id

    Args:
        cwd: The working directory (e.g., /home/GOD) - Claude knows this
        reason: Why this conversation should be ingested
        priority: 1-10, higher = more important (default: 5)
        current: If True, flag most recent transcript (default)
        conversation_id: Required if current=False
        transcript_path: Optional path if current=False
        guide: If True, return docs on transcript locations (overrides all)
    """
    return core.flag_conversation(cwd, reason, priority, current, conversation_id, transcript_path, guide)


@mcp.tool()
def get_ingestion_waitlist(status_filter: Optional[str] = None, min_priority: int = 1) -> str:
    """Get conversations flagged for ingestion.

    Returns list sorted by priority (highest first).

    Args:
        status_filter: Optional filter by status ("pending", "in_progress", "ingested", "skipped")
        min_priority: Only show entries with priority >= this value (default: 1)
    """
    entries = core.get_ingestion_waitlist(status_filter, min_priority)
    if not entries:
        return "Waitlist is empty."

    lines = [f"=== Ingestion Waitlist ({len(entries)} entries) ===", ""]
    for e in entries:
        lines.append(f"[P{e.priority}] {e.conversation_id} ({e.status})")
        lines.append(f"     Reason: {e.reason}")
        lines.append(f"     Source: {e.source} | Flagged: {e.flagged_at}")
        if e.transcript_path:
            lines.append(f"     Path: {e.transcript_path}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def update_waitlist_status(
    conversation_id: str,
    status: str
) -> str:
    """Update status of a waitlist entry.

    Args:
        conversation_id: The conversation to update
        status: One of "pending", "in_progress", "ingested", "skipped"
    """
    return core.update_waitlist_status(conversation_id, status)


@mcp.tool()
def remove_from_waitlist(conversation_id: str) -> str:
    """Remove a conversation from the ingestion waitlist entirely."""
    return core.remove_from_waitlist(conversation_id)


@mcp.tool()
def get_waitlist_stats() -> str:
    """Get summary statistics for the ingestion waitlist."""
    stats = core.get_waitlist_stats()
    lines = [
        "=== Waitlist Stats ===",
        f"Total: {stats['total']}",
        "",
        "By Status:",
    ]
    for status, count in stats['by_status'].items():
        if count > 0:
            lines.append(f"  {status}: {count}")

    lines.append("")
    lines.append("By Priority:")
    for priority, count in sorted(stats['by_priority'].items(), reverse=True):
        lines.append(f"  P{priority}: {count}")

    lines.append("")
    lines.append("By Source:")
    for source, count in stats['by_source'].items():
        lines.append(f"  {source}: {count}")

    return "\n".join(lines)


@mcp.tool()
def get_current_session_id() -> str:
    """Get the current Claude Code session ID (if available).

    Requires hook to have fired and written transcript info.
    """
    session_id = core.get_current_session_id()
    if session_id:
        return f"Current session: {session_id}"
    return "❌ No current session info available. Hook may not have fired."


# =============================================================================
# NEW - Scores Registry
# =============================================================================

@mcp.tool()
def get_scores_registry() -> str:
    """Get the mimetic desire chain scores registry path and contents.

    Returns the path to the scores JSON and current scores for all emergent frameworks.
    After running framework-scorer on a rendered MD, use the Edit tool to update this JSON.

    Workflow:
    1. preview_emergent(name, output_path) → renders MD
    2. framework-scorer agent reads MD → returns X/6 score
    3. Edit the scores_registry.json with the result
    4. Repeat until all frameworks score 6/6
    """
    return core.get_scores_registry()


