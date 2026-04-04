"""JournalAgent — Autobiographer CHAT/JOURNAL mode.

ChatAgent subclass for the journal Discord channel. Handles:
- CHAT mode: user deposits memories anytime, reads missing-days queue
- JOURNAL mode: structured morning/evening capture with 6-dimension scoring

System prompt has:
- Current sanctuary scores (6 dimensions) with contextualized history from CartON
- Invariant blocks about who MOV is and who Isaac is
- Mode-specific instructions (chat vs morning journal vs evening journal)

MCPs: sanctuary system (journal_entry, assess_sanctuary_degree, view_sanctuary_history)
Skills: journal-workflow, autobiographical-context (future)

Fractal pattern: same as ConductorAgent. Ears feeds it, check_inbox processes.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cave.core.agent import ChatAgent, AgentConfig

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
MISSING_DAYS_QUEUE = HEAVEN_DATA_DIR / "missing_days_queue.json"


class JournalAgent(ChatAgent):
    """MOV Journal — Autobiographer CHAT + JOURNAL modes.

    DIs a BaseHeavenAgent runtime with sanctuary MCP for journal_entry().
    Inherits from ChatAgent: inbox, channels, !commands, queue drain.

    Two modes determined by how it's triggered:
    - CHAT: user sends message anytime → memory deposit
    - JOURNAL: cron fires morning/evening → structured capture

    The system prompt adapts based on context (time of day, whether
    it's a cron trigger or user-initiated).
    """

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self._heaven_agent = None
        self._history_id = None
        self._mode = "chat"  # "chat" or "journal_morning" or "journal_evening"

    # ==================== RUNTIME INIT ====================

    def init_runtime(self, agent_config_path: str = None) -> bool:
        """Initialize the Heaven runtime with sanctuary MCP.

        Called by WakingDreamer after agent creation.
        Uses BaseHeavenAgent directly (ChatAgent pattern, like Conductor).
        NOT hermes_step (that's for ServiceAgent/SDNAC patterns).
        """
        try:
            from heaven_base.baseheavenagent import BaseHeavenAgent, HeavenAgentConfig
            from heaven_base.unified_chat import UnifiedChat
            from heaven_base.memory.history import History

            json_config = self._load_agent_json_config(agent_config_path)

            model = "MiniMax-M2.7-highspeed"
            if json_config:
                model = json_config.get("model", model)

            agent_config = HeavenAgentConfig(
                name="journal",
                system_prompt=self._build_system_prompt(),
                provider="anthropic",
                model=model,
                max_tokens=json_config.get("max_tokens", 8000) if json_config else 8000,
                tools=self._get_tools(),
                mcp_servers=self._get_mcp_servers(),
                enable_compaction=True,
            )

            if json_config:
                if "extra_model_kwargs" in json_config:
                    agent_config.extra_model_kwargs = json_config["extra_model_kwargs"]
                if "use_uni_api" in json_config:
                    agent_config.use_uni_api = json_config["use_uni_api"]
                if "prompt_suffix_blocks" in json_config:
                    agent_config.prompt_suffix_blocks = json_config["prompt_suffix_blocks"]

            # Create BaseHeavenAgent — persistent conversational agent with history
            history = History(messages=[], history_id=self._history_id)
            self._heaven_agent = BaseHeavenAgent(
                agent_config, UnifiedChat, history=history, adk=False
            )

            heaven_agent = self._heaven_agent

            # Async runtime — same pattern as Conductor
            async def journal_run(message: str) -> Dict[str, Any]:
                """Run journal agent on a message. Persistent conversation."""
                try:
                    result = await heaven_agent.run(prompt=message)

                    response_text = ""
                    if isinstance(result, dict):
                        if "prepared_message" in result:
                            pm = result["prepared_message"]
                            # Handle content block format: [{type: 'text', text: '...'}, ...]
                            if isinstance(pm, list):
                                text_parts = []
                                for block in pm:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        text_parts.append(block)
                                response_text = "\n".join(text_parts)
                            elif isinstance(pm, str):
                                response_text = pm
                            else:
                                response_text = str(pm)
                        elif "history" in result:
                            msgs = result["history"].messages
                            for msg in reversed(msgs):
                                if hasattr(msg, 'content') and msg.__class__.__name__ == "AIMessage":
                                    content = msg.content
                                    if isinstance(content, str):
                                        response_text = content
                                    elif isinstance(content, list):
                                        text_parts = []
                                        for block in content:
                                            if isinstance(block, dict) and block.get("type") == "text":
                                                text_parts.append(block.get("text", ""))
                                            elif isinstance(block, str):
                                                text_parts.append(block)
                                        response_text = "\n".join(text_parts)
                                    else:
                                        response_text = str(content)
                                    break

                        # Update history for conversation continuity
                        if "history" in result:
                            heaven_agent.history = result["history"]

                        self._history_id = result.get("history_id", self._history_id)

                    return {
                        "status": "success",
                        "response": response_text,
                        "history_id": self._history_id,
                    }

                except Exception as e:
                    logger.error("JournalAgent runtime error: %s", e, exc_info=True)
                    return {"status": "error", "error": str(e)}

            self.set_runtime(journal_run)
            logger.info("JournalAgent: BaseHeavenAgent runtime initialized (model=%s)", model)
            return True

        except ImportError as e:
            logger.warning("JournalAgent: heaven not available: %s", e)
            return False
        except Exception as e:
            logger.error("JournalAgent: failed to init runtime: %s", e, exc_info=True)
            return False

    # ==================== SYSTEM PROMPT ====================

    def _build_system_prompt(self) -> str:
        """Build system prompt with invariant + mode-specific blocks."""
        parts = []

        # Invariant: who MOV is
        parts.append(
            "You are MOV (Memories of Olivus Victory) — the Autobiographer agent.\n"
            "Your purpose is to compile, maintain, and deepen Isaac's verified autobiographical context.\n"
            "Every meaningful memory is a data point on the path from Wasteland to Sanctuary.\n"
            "Autobiography is the primitive — once you know who someone is, you project identity into anything.\n"
        )

        # Invariant: who Isaac is
        parts.append(
            "You are talking to Isaac. He is building GNOSYS — a compound intelligence system (PAIA).\n"
            "He is a Shambhala warrior building sovereign compound intelligence.\n"
            "He signs as 'Stainless Lotus Lord'. He values directness, no bullshit.\n"
        )

        # Current sanctuary scores
        scores = self._get_sanctuary_scores()
        if scores:
            parts.append("## Current Sanctuary Scores\n" + scores + "\n")

        # Missing days queue (for CHAT mode)
        if self._mode == "chat":
            missing = self._get_missing_days()
            if missing:
                parts.append(
                    "## Missing Days\n"
                    "The following periods have no memories in CartON. "
                    "When appropriate, gently ask Isaac about these gaps:\n"
                    + missing + "\n"
                )

        # Mode-specific instructions
        if self._mode == "chat":
            parts.append(
                "## Mode: CHAT\n"
                "Isaac is depositing memories. Listen, extract key biographical data, "
                "and use journal_entry() to persist important observations. "
                "Be conversational and warm. Ask follow-up questions to deepen memories.\n"
            )
        elif self._mode == "journal_morning":
            parts.append(
                "## Mode: MORNING JOURNAL\n"
                "It's morning. Guide Isaac through a structured journal capture.\n"
                "Ask: 'How are you feeling? Walk me through your 6 dimensions.'\n"
                "Extract scores for: health, wealth, relationships, purpose, growth, environment.\n"
                "Use journal_entry(entry_type='opening', ...) to persist.\n"
                "Use assess_sanctuary_degree() after capturing all dimensions.\n"
            )
        elif self._mode == "journal_evening":
            parts.append(
                "## Mode: EVENING JOURNAL\n"
                "It's evening. Review the day with Isaac.\n"
                "Ask about: what went well, what didn't, ritual completions, key events.\n"
                "Extract updated scores for the 6 dimensions.\n"
                "Use journal_entry(entry_type='closing', ...) to persist.\n"
                "Use assess_sanctuary_degree() after capturing.\n"
                "After journal is complete, announce that night mode is starting.\n"
            )

        # Tools reminder
        parts.append(
            "## Your Tools\n"
            "- journal_entry(): Record structured journal entries to CartON\n"
            "- assess_sanctuary_degree(): Score the 6 sanctuary dimensions\n"
            "- view_sanctuary_history(): See past sanctuary assessments\n"
            "- declare_system_state(): Declare current system state\n"
        )

        return "\n".join(parts)

    # ==================== SANCTUARY SCORES ====================

    def _get_sanctuary_scores(self) -> str:
        """Get current sanctuary scores from sanctum status."""
        try:
            # Read from sanctum status file (written by heartbeat)
            status_file = HEAVEN_DATA_DIR / "conductor_dynamic" / "sanctum_status.txt"
            if status_file.exists():
                return status_file.read_text()

            # Fallback: read from sanctum builder
            from sanctum_builder import SANCTUMBuilder
            builder = SANCTUMBuilder()
            current = builder.which()
            if "[HIEL]" not in current:
                return builder.status()
        except Exception as e:
            logger.debug("Could not get sanctuary scores: %s", e)
        return ""

    # ==================== MISSING DAYS QUEUE ====================

    def _get_missing_days(self) -> str:
        """Read the missing days queue written by NIGHT mode."""
        if not MISSING_DAYS_QUEUE.exists():
            return ""
        try:
            data = json.loads(MISSING_DAYS_QUEUE.read_text())
            if not data:
                return ""
            lines = []
            for entry in data[:10]:  # Show max 10
                period = entry.get("period", "unknown")
                note = entry.get("note", "")
                lines.append(f"- {period}: {note}")
            return "\n".join(lines)
        except Exception:
            return ""

    # ==================== MODE CONTROL ====================

    def set_mode(self, mode: str) -> None:
        """Set the agent mode. Affects system prompt."""
        valid = ("chat", "journal_morning", "journal_evening")
        if mode not in valid:
            logger.warning("Invalid journal mode '%s', using 'chat'", mode)
            mode = "chat"
        self._mode = mode
        logger.info("JournalAgent mode set to: %s", mode)

    @property
    def mode(self) -> str:
        return self._mode

    # ==================== MCP + TOOLS ====================

    def _get_mcp_servers(self) -> dict:
        """MCP servers for the journal agent — sanctuary system MCP."""
        return {
            "sanctuary": {
                "command": "python",
                "args": ["/home/GOD/gnosys-plugin-v2/application/sanctuary-mcp/sanctuary_system/mcp_server.py"],
                "transport": "stdio",
            },
        }

    def _get_tools(self) -> list:
        """Heaven tools for the journal agent."""
        from heaven_base.tools import BashTool
        return [BashTool]

    # ==================== CONFIG LOADING ====================

    def _load_agent_json_config(self, path: str = None) -> Optional[dict]:
        """Load agent config from JSON file."""
        if path:
            p = Path(path)
        else:
            p = HEAVEN_DATA_DIR / "journal_agent_config.json"

        if not p.exists():
            logger.info("JournalAgent: no config file at %s, using defaults", p)
            return None

        try:
            config = json.loads(p.read_text())
            logger.info("JournalAgent: loaded config from %s", p)
            return config
        except Exception as e:
            logger.error("JournalAgent: failed to load config: %s", e)
            return None

    # ==================== INBOX PROCESSING (FRACTAL) ====================

    async def check_inbox(self) -> List[Any]:
        """Process all pending messages with Discord notifications.

        Same fractal pattern as ConductorAgent:
        Ears enqueues → check_inbox processes → notify Discord.
        """
        if self._processing:
            return []

        self._processing = True
        responses = []

        try:
            while self.has_messages:
                message = self.dequeue()
                if not message:
                    continue

                content = message.content if hasattr(message, 'content') else str(message)
                metadata = message.metadata if hasattr(message, 'metadata') else {}

                # Strip Discord prefix
                user_msg = self._extract_user_message(content)

                # Detect mode from trigger
                if metadata.get("type") == "journal_morning":
                    self.set_mode("journal_morning")
                    user_msg = "Time for morning journal."
                elif metadata.get("type") == "journal_evening":
                    self.set_mode("journal_evening")
                    user_msg = "Time for evening journal."
                elif self._mode.startswith("journal_"):
                    pass  # Keep journal mode if already in one
                else:
                    self.set_mode("chat")

                # Run through runtime
                result = await self.run_with_content(user_msg)

                # Deliver response
                if isinstance(result, dict) and result.get("status") == "success":
                    response = result.get("response", "")
                    if response:
                        self._notify(f"💬 **MOV:**\n{response}")
                elif isinstance(result, dict) and result.get("status") == "error":
                    self._notify(f"❌ MOV error: {result.get('error', 'unknown')}")

                responses.append(result)

        except Exception as e:
            logger.error("JournalAgent check_inbox error: %s", e, exc_info=True)
            self._notify(f"❌ **Journal error:** {e}")
        finally:
            self._processing = False

        return responses

    async def run_with_content(self, content: str) -> Any:
        """Run the runtime with string content directly."""
        if self._runtime is None:
            return None
        if callable(self._runtime):
            result = self._runtime(content)
        elif hasattr(self._runtime, 'run'):
            result = self._runtime.run(content)
        else:
            return None

        if asyncio.iscoroutine(result) or asyncio.isfuture(result):
            return await result
        return result

    # ==================== DISCORD HELPERS ====================

    def _extract_user_message(self, content: str) -> str:
        """Strip Discord prefix: [Discord #channel] username: actual message"""
        import re
        m = re.match(r"^\[Discord #\d+\]\s+\w+:\s*(.*)$", content.strip(), re.DOTALL)
        if m:
            return m.group(1).strip()
        return content.strip()

    def _notify(self, text: str) -> None:
        """Send notification to Discord journal channel."""
        try:
            if self.central_channel and self.central_channel.main():
                self.central_channel.main().deliver({"message": text})
            else:
                # Fallback: direct Discord send
                from cave.core.channel import UserDiscordChannel
                discord = UserDiscordChannel()
                if discord.token and discord.channel_id:
                    if len(text) <= 1900:
                        discord.deliver({"message": text})
                    else:
                        # Chunk
                        remaining = text
                        while remaining:
                            chunk = remaining[:1900]
                            remaining = remaining[1900:]
                            discord.deliver({"message": chunk})
        except Exception as e:
            logger.error("JournalAgent notify failed: %s", e)
