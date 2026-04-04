"""EventBroadcaster - bridges HeavenEvent → Channel delivery.

Single callback that parses langchain messages into HeavenEvents
and broadcasts to all registered Channels. Replaces hardcoded
DiscordEventForwarder with a pluggable channel system.

Usage in handle_message:
    broadcaster = EventBroadcaster([
        ConductorDiscordChannel(),
        # SSEChannel(queue),       # frontend
        # FileLogChannel(path),    # event log
    ])
    composite = CompositeCallback([capture, broadcaster])

TRUNCATION POLICY: NEVER truncate message content. EVER.
Discord has a 2000 char limit — we CHUNK, we do NOT truncate.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from cave.core.channel import Channel, UserDiscordChannel, SSEChannel
from heaven_base.memory.heaven_event import HeavenEvent

logger = logging.getLogger(__name__)

# Discord message limit (leave room for markdown formatting overhead)
DISCORD_CHUNK_SIZE = 1900


def _chunk_for_discord(text: str, chunk_size: int = DISCORD_CHUNK_SIZE) -> List[str]:
    """Split text into chunks that fit in Discord's 2000 char limit.

    Prefers splitting at newlines for readability. NEVER truncates.
    Every character of the original message will be delivered.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break

        # Try to split at last newline within chunk_size
        split_at = remaining.rfind("\n", 0, chunk_size)
        if split_at <= 0:
            # No good newline — split at chunk_size (hard break)
            split_at = chunk_size

        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")  # strip leading newline from next chunk

    return chunks


class EventBroadcaster:
    """LangChain callback that broadcasts HeavenEvents to registered Channels."""

    def __init__(self, channels: List[Channel]):
        self.channels = channels

    def __call__(self, raw_langchain_message):
        try:
            events = HeavenEvent.from_langchain_message(raw_langchain_message)
            for event in events:
                payload = event.to_dict()
                for channel in self.channels:
                    try:
                        channel.deliver(payload)
                    except Exception as e:
                        logger.debug("Channel %s failed: %s", channel.channel_type(), e)
        except Exception as e:
            logger.debug("EventBroadcaster parse failed: %s", e)


@dataclass
class ConductorDiscordChannel(UserDiscordChannel):
    """Discord channel with HeavenEvent formatting for Conductor output.

    Accepts HeavenEvent dicts (event_type + data) and formats them
    with Discord markdown before delivering via UserDiscordChannel.

    TRUNCATION POLICY: NOTHING is truncated. Long messages are chunked
    into multiple Discord messages. Every character is delivered.
    """

    degree: str = ""
    _tool_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self):
        super().__post_init__()
        if not self.degree:
            from .conductor import _get_sanctuary_degree
            self.degree = _get_sanctuary_degree()

    def channel_type(self) -> str:
        return "user.discord.conductor"

    def _deliver_chunked(self, full_message: str) -> Dict[str, Any]:
        """Deliver a message, chunking into multiple Discord messages if needed.

        NEVER truncates. Every character is sent.
        """
        chunks = _chunk_for_discord(full_message)
        last_result = {"status": "skipped"}
        for chunk in chunks:
            last_result = super().deliver({"message": chunk})
        return last_result

    def deliver(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format HeavenEvent payload and deliver to Discord. NO TRUNCATION."""
        etype = payload.get("event_type")
        data = payload.get("data", {})

        if etype == "TOOL_USE":
            self._tool_count += 1
            name = data.get("name", "?")
            args = self._format_args(name, data.get("input", {}))
            msg = f"\U0001f527 `[{self._tool_count}]` **{name}**"
            if args:
                msg += f"\n```\n{args}\n```"
            return self._deliver_chunked(msg)

        elif etype == "TOOL_RESULT":
            output = str(data.get("output", ""))
            if output:
                msg = f"\U0001f4cb `[{self._tool_count}]` result:\n```\n{output}\n```"
                return self._deliver_chunked(msg)

        elif etype == "AGENT_MESSAGE":
            content = data.get("content", "")
            if content.strip():
                msg = f"\U0001f4ac **{self.degree}:**\n{content}"
                return self._deliver_chunked(msg)

        return {"status": "skipped"}

    def _format_args(self, tool_name: str, tool_input: dict) -> str:
        """Format tool args for display. NO TRUNCATION."""
        if not tool_input:
            return ""
        if "command" in tool_input:
            return tool_input["command"]
        if "file_path" in tool_input:
            return tool_input["file_path"]
        try:
            return json.dumps(tool_input, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            return str(tool_input)
