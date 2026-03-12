"""
Claude Code transcript parsing utilities.

Parses .jsonl transcript files from Claude Code sessions.
Handles conversation segmentation by slug.

Transcript structure:
- Each line is a JSON object (entry)
- Key fields: type, sessionId, slug, uuid, parentUuid, timestamp, message
- slug identifies a conversation within a session
- isCompactSummary/isMeta entries should be skipped for content extraction
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class TranscriptEntry:
    """A single entry from a Claude Code transcript."""
    raw: Dict[str, Any]

    @property
    def type(self) -> str:
        return self.raw.get('type', '')

    @property
    def session_id(self) -> str:
        return self.raw.get('sessionId', '')

    @property
    def slug(self) -> Optional[str]:
        return self.raw.get('slug')

    @property
    def uuid(self) -> str:
        return self.raw.get('uuid', '')

    @property
    def parent_uuid(self) -> Optional[str]:
        return self.raw.get('parentUuid')

    @property
    def timestamp(self) -> str:
        return self.raw.get('timestamp', '')

    @property
    def is_compact_summary(self) -> bool:
        return self.raw.get('isCompactSummary', False)

    @property
    def is_meta(self) -> bool:
        return self.raw.get('isMeta', False)

    @property
    def should_skip(self) -> bool:
        """True if this entry should be skipped for content extraction."""
        return self.is_compact_summary or self.is_meta

    def extract_text(self) -> str:
        """Extract text content from message."""
        message = self.raw.get('message', {})
        content_items = message.get('content', [])

        # Handle string content directly
        if isinstance(message.get('content'), str):
            return message['content']

        text_parts = []
        for item in content_items:
            if isinstance(item, dict):
                item_type = item.get('type', '')
                if item_type == 'text':
                    text_parts.append(item.get('text', ''))
                elif item_type == 'tool_result':
                    # Tool results can have string or list content
                    tool_content = item.get('content', '')
                    if isinstance(tool_content, str):
                        text_parts.append(tool_content)
                    elif isinstance(tool_content, list):
                        for tc in tool_content:
                            if isinstance(tc, dict) and tc.get('type') == 'text':
                                text_parts.append(tc.get('text', ''))
            elif isinstance(item, str):
                text_parts.append(item)

        return ''.join(text_parts)

    def extract_tool_uses(self) -> List[Dict[str, Any]]:
        """Extract tool use blocks from message."""
        message = self.raw.get('message', {})
        content_items = message.get('content', [])

        tool_uses = []
        for item in content_items:
            if isinstance(item, dict) and item.get('type') == 'tool_use':
                tool_uses.append({
                    'id': item.get('id', ''),
                    'name': item.get('name', 'unknown'),
                    'input': item.get('input', {})
                })

        return tool_uses


@dataclass
class Conversation:
    """A conversation within a Claude Code session, identified by slug."""
    slug: str
    session_id: str
    entries: List[TranscriptEntry] = field(default_factory=list)

    @property
    def user_entries(self) -> List[TranscriptEntry]:
        return [e for e in self.entries if e.type == 'user' and not e.should_skip]

    @property
    def assistant_entries(self) -> List[TranscriptEntry]:
        return [e for e in self.entries if e.type == 'assistant' and not e.should_skip]

    @property
    def first_user_message(self) -> Optional[str]:
        """Get first user message text (useful for display)."""
        user_entries = self.user_entries
        if user_entries:
            return user_entries[0].extract_text()[:200]
        return None

    @property
    def start_timestamp(self) -> Optional[str]:
        """Get earliest timestamp."""
        timestamps = [e.timestamp for e in self.entries if e.timestamp]
        return min(timestamps) if timestamps else None

    @property
    def end_timestamp(self) -> Optional[str]:
        """Get latest timestamp."""
        timestamps = [e.timestamp for e in self.entries if e.timestamp]
        return max(timestamps) if timestamps else None


def _parse_jsonl_line(line: str, line_num: int) -> Optional[TranscriptEntry]:
    """Parse a single JSONL line into a TranscriptEntry."""
    line = line.strip()
    if not line:
        return None
    try:
        raw = json.loads(line)
        return TranscriptEntry(raw=raw)
    except json.JSONDecodeError as e:
        logger.warning("JSON decode error at line %d: %s", line_num, e, exc_info=True)
        return None


def parse_transcript_file(filepath: str) -> List[TranscriptEntry]:
    """
    Parse a Claude Code JSONL transcript file.

    Args:
        filepath: Path to .jsonl file

    Returns:
        List of TranscriptEntry objects, sorted by timestamp
    """
    path = Path(filepath)
    if not path.exists():
        logger.error("Transcript file not found: %s", filepath)
        return []

    entries = []
    with open(path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            entry = _parse_jsonl_line(line, line_num)
            if entry:
                entries.append(entry)

    entries.sort(key=lambda e: e.timestamp or '')
    return entries


def get_unique_slugs(entries: List[TranscriptEntry]) -> List[str]:
    """Get unique slugs from entries, preserving order of first appearance."""
    seen = set()
    slugs = []
    for entry in entries:
        slug = entry.slug
        if slug and slug not in seen:
            seen.add(slug)
            slugs.append(slug)
    return slugs


def segment_by_slug(entries: List[TranscriptEntry]) -> Dict[str, Conversation]:
    """
    Segment transcript entries into conversations by slug.

    Args:
        entries: List of TranscriptEntry objects

    Returns:
        Dict mapping slug -> Conversation
    """
    conversations: Dict[str, Conversation] = {}

    for entry in entries:
        slug = entry.slug
        if not slug:
            continue

        if slug not in conversations:
            conversations[slug] = Conversation(
                slug=slug,
                session_id=entry.session_id
            )

        conversations[slug].entries.append(entry)

    return conversations


def get_conversation_by_slug(filepath: str, slug: str) -> Optional[Conversation]:
    """
    Get a single conversation by slug from a transcript file.

    Args:
        filepath: Path to .jsonl file
        slug: The conversation slug

    Returns:
        Conversation or None if not found
    """
    entries = parse_transcript_file(filepath)
    conversations = segment_by_slug(entries)
    return conversations.get(slug)


def list_conversations_in_file(filepath: str) -> List[Dict[str, Any]]:
    """
    List all conversations in a transcript file with summary info.

    Returns list of dicts with: slug, session_id, entry_count, first_message, start_time
    """
    entries = parse_transcript_file(filepath)
    conversations = segment_by_slug(entries)

    result = []
    for slug, conv in conversations.items():
        result.append({
            'slug': slug,
            'session_id': conv.session_id,
            'entry_count': len(conv.entries),
            'user_message_count': len(conv.user_entries),
            'assistant_message_count': len(conv.assistant_entries),
            'first_message': conv.first_user_message,
            'start_time': conv.start_timestamp,
            'end_time': conv.end_timestamp
        })

    # Sort by start_time
    result.sort(key=lambda x: x.get('start_time') or '')

    return result
