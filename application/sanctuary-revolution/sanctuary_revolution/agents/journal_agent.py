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

            model = ""  # Read from journal_agent_config.json
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

            # Store config — NEW agent created each call (same pattern as Conductor)
            self._agent_config = agent_config
            journal_ref = self

            async def journal_run(message: str) -> Dict[str, Any]:
                """Run journal agent on a message. NEW agent per call with history_id."""
                try:
                    from heaven_base.baseheavenagent import BaseHeavenAgent
                    from heaven_base.unified_chat import UnifiedChat
                    from heaven_base.docs.examples.heaven_callbacks import BackgroundEventCapture, CompositeCallback
                    from conductor.event_broadcaster import EventBroadcaster, ConductorDiscordChannel

                    agent_kwargs = dict(
                        config=journal_ref._agent_config,
                        unified_chat=UnifiedChat(),
                        max_tool_calls=20,
                    )
                    if journal_ref._history_id:
                        agent_kwargs["history_id"] = journal_ref._history_id

                    agent = BaseHeavenAgent(**agent_kwargs)

                    # Same pattern as Conductor: capture + broadcast every event to Discord
                    capture = BackgroundEventCapture()
                    # Get channel from agent's own central_channel (configured in v1_agents.json)
                    main_ch = journal_ref.central_channel.main() if journal_ref.central_channel else None
                    if main_ch and hasattr(main_ch, 'channel_id') and main_ch.channel_id:
                        discord_ch = ConductorDiscordChannel(channel_id=main_ch.channel_id)
                        discord_ch.degree = "MOV"
                        broadcaster = EventBroadcaster([discord_ch])
                        composite = CompositeCallback([capture, broadcaster])
                    else:
                        composite = capture
                    result = await agent.run(prompt=message, heaven_main_callback=composite)

                    # Get response from captured AGENT_MESSAGE events (same as Conductor)
                    agent_messages = capture.get_events_by_type("AGENT_MESSAGE")
                    if agent_messages:
                        last_msg = agent_messages[-1]
                        response_text = last_msg.get("data", {}).get("content", "")
                    else:
                        response_text = ""

                    # history_id from result — persists to disk for next call
                    new_history_id = result.get("history_id") if isinstance(result, dict) else None
                    if new_history_id:
                        journal_ref._history_id = new_history_id

                    return {
                        "status": "success",
                        "response": response_text,
                        "history_id": journal_ref._history_id,
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
        elif self._mode == "friendship":
            parts.append(
                "## Mode: FRIENDSHIP RITUAL — Weekly Act 3B\n"
                "This is the RETURN. Every week is a Hero's Journey. Saturday is ALWAYS Act 3B.\n"
                "Either we return with the boon (transformation) or we return to status quo (tragic).\n\n"
                "The Night agent has prepared a Friendship_Autocontext report. Read it first:\n"
                "  get_concept('Friendship_Autocontext_{today}')\n\n"
                "## Step 1: Present BOTH Protagonist Tracks\n"
                "Query the four timelines:\n"
                "- get_recent_concepts(n=30, timeline='odyssey') — system narrative (what the system learned)\n"
                "- get_recent_concepts(n=15, timeline='system') — background daemon health\n"
                "- get_recent_concepts(n=15, timeline='chat') — conversation actions (what we worked on)\n"
                "- get_recent_concepts(n=20, timeline='overall') — all interleaved\n"
                "Also check User_Autobiography_Timeline for this week's life events:\n"
                "  Ritual completions/skips, journal entries, deposited memories.\n\n"
                "Present: what the SYSTEM did this week + what ISAAC did this week.\n\n"
                "## Step 2: TWI Compliance Check (the deeper question)\n"
                "For EACH active TWI:\n"
                "  1. Read the TWI: get_concept('Claude_Code_Rule_Twi_Global_Intents')\n"
                "  2. Which FRAMEWORK encodes this TWI? (each TWI was extracted from a journey boon)\n"
                "  3. Which CAPABILITIES enforce it? (skills, rules, tools, flights)\n"
                "  4. DID WE USE THOSE CAPABILITIES this week? Evidence from timelines.\n"
                "  5. When we DIDN'T use them = central conflict (TWI violation)\n"
                "  6. When we DID = advancement (TWI embodied)\n"
                "This is the Act 3B question: did we use the boon we already gained, or ignore it?\n\n"
                "## Step 3: Decide TWI Changes + Deliverables\n"
                "Based on the compliance check:\n"
                "- KEEP: TWI held, capabilities enforced it, evidence confirms\n"
                "- EVOLVE: TWI partially held but needs refinement\n"
                "- REMOVE: TWI failed, not useful, or superseded\n"
                "- NEW: Pattern found this week that needs a new TWI\n"
                "Deliverables: concrete work items for next week's backlog.\n\n"
                "## Step 4: Close the Ritual\n"
                "Get Isaac's weekly sanctuary scores (6 dimensions, each 1-10).\n"
                "Call friendship_journal() with: reflection, status, scores, TWI changes, deliverables.\n"
                "This completes the week's story. The narrative system will observe this final act.\n"
            )

        # Timeline awareness for CHAT mode (always available for deeper conversations)
        if self._mode == "chat":
            parts.append(
                "## System Timelines (for deeper conversations)\n"
                "If Isaac wants to reflect on system activity, you can query:\n"
                "- get_recent_concepts(timeline='odyssey') — what the system learned\n"
                "- get_recent_concepts(timeline='system') — background health\n"
                "- get_recent_concepts(timeline='overall') — everything interleaved\n"
            )

        # Tools reminder
        parts.append(
            "## Your Tools\n"
            "- **deposit_memory()**: YOUR PRIMARY TOOL. When Isaac shares a memory, extract:\n"
            "  - memory_name: short Title_Case name (e.g. 'Learned_Basic', 'Met_Tara')\n"
            "  - description: what happened, in Isaac's words\n"
            "  - domain: ONE OF health/wealth/relationships/purpose/growth/environment\n"
            "  - location: where it happened\n"
            "  - feeling: how it felt\n"
            "  - date: exact YYYY-MM-DD if known, else leave empty\n"
            "  - estimated_daterange: fuzzy range if date unknown ('1993', '2026-03', 'childhood')\n"
            "  - people_and_entities: JSON list of people/events/topics mentioned\n"
            "    e.g. '[\"Dad\", \"BASIC_Programming\"]' — each becomes a linked concept\n"
            "  If info is missing, ask Isaac naturally ('where was that?' 'how did that feel?')\n"
            "- journal_entry(): Record structured journal entries (morning/evening/friendship)\n"
            "- friendship_journal(): Close Friendship ritual — emits journal + TWI changes + deliverables\n"
            "- assess_sanctuary_degree(): Score the 6 sanctuary dimensions\n"
            "- view_sanctuary_history(): See past sanctuary assessments\n"
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
        valid = ("chat", "journal_morning", "journal_evening", "friendship")
        if mode not in valid:
            logger.warning("Invalid journal mode '%s', using 'chat'", mode)
            mode = "chat"
        self._mode = mode
        logger.info("JournalAgent mode set to: %s", mode)

    @property
    def mode(self) -> str:
        return self._mode

    # ==================== COMMANDS ====================

    def _check_command(self, content: str) -> Optional[str]:
        """Check for !commands. Returns response string if handled, None if not."""
        if not content.startswith("!"):
            return None

        parts = content.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "!new":
            self._history_id = None
            return f"🆕 **New conversation started.** History cleared. Mode: `{self._mode}`"

        if cmd == "!status":
            return (
                f"📊 **MOV Status:**\n"
                f"Mode: `{self._mode}`\n"
                f"History: `{self._history_id or '(none — new conversation)'}`"
            )

        if cmd == "!stop":
            self._processing = False
            self.inbox.clear()
            return "🛑 **Stopped.** Queue cleared."

        if cmd == "!help":
            return (
                "📖 **MOV Commands:**\n"
                "`!new` — Start fresh conversation\n"
                "`!status` — Show mode and history\n"
                "`!stop` — Cancel and clear queue\n"
                "`!help` — This help text"
            )

        return f"❓ Unknown command: `{cmd}`\nUse `!help` for available commands."

    # ==================== MCP + TOOLS ====================

    def _get_mcp_servers(self) -> dict:
        """MCP servers for the journal agent — sanctuary + CartON."""
        servers = {
            "sanctuary": {
                "command": "python",
                "args": ["/home/GOD/gnosys-plugin-v2/application/sanctuary-mcp/sanctuary_system/mcp_server.py"],
                "transport": "stdio",
            },
            "carton": {
                "command": "carton-mcp",
                "args": [],
                "transport": "stdio",
            },
        }
        return servers

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

                # Check !commands
                cmd_result = self._check_command(user_msg)
                if cmd_result is not None:
                    self._notify(cmd_result)
                    responses.append({"status": "handled", "command": True})
                    continue

                # Notify processing start
                self._notify("🏃 Processing...")

                # Run through runtime
                result = await self.run_with_content(user_msg)

                # Status only — EventBroadcaster already sent the full response to Discord
                if isinstance(result, dict) and result.get("status") == "success":
                    self._notify("✅ Turn complete.")
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
