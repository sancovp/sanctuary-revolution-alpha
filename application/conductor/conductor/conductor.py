"""Conductor: persistent agent. Isaac's interface.

Manages Grug (claude -p via ClaudePConnector), Researcher (SDNAC),
and orchestrates the research loop.

Freestyle chat mode: Isaac's message → BaseHeavenAgent.run() → response.
Uses Heaven's callback API (NOT extract_heaven_response):
  - BaseHeavenAgent instantiated directly from HeavenAgentConfig
  - BackgroundEventCapture callback captures AGENT_MESSAGE events
  - agent.run(prompt, heaven_main_callback=capture) — agent loops internally on tools
  - history_id from result["history_id"] directly
  - start_chat/continue_chat for conversation meta-tracking
  - history_id persisted to disk for restart recovery

BUILT:
- Connector abstraction (ClaudePConnector for Grug, SDNACConnector for Researcher)
- State machine (scientific method phases)
- Runner (orchestration with 3 modes)
- Agent factories (SDNAC wrappers)
- CAVE registration + anatomy access
- Freestyle handle_message via BaseHeavenAgent.run() + BackgroundEventCapture
- Conversation meta-tracking via ConversationManager (start_chat/continue_chat)
- Disk persistence of history_id for restart recovery

NOT YET BUILT:
- Shadow agent (adversarial simulation SDNAC)
- Organ management (health check + restart policy)
- Memory domain (STM/MTM/LTM via CartON)

"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from heaven_base.baseheavenagent import BaseHeavenAgent
from heaven_base.unified_chat import UnifiedChat
from heaven_base.docs.examples.heaven_callbacks import BackgroundEventCapture, CompositeCallback
from heaven_base.memory.heaven_event import HeavenEvent

from .connector import GrugConnector
from .runner import Runner
from .state_machine import StateMachine
from .cave_registration import (
    ConductorConfig,
    register_conductor_in_cave,
    get_conductor_anatomy_access,
    get_conductor_system_prompt,
    HEAVEN_DATA,
)

logger = logging.getLogger(__name__)


SANCTUARY_DEGREES = [
    "WakingDreamer",
    "OlivusVictory-Promise",
    "DemonChampion",
    "OlivusVictory-Ability",
]


def _get_sanctuary_degree() -> str:
    """Read current sanctuary degree from config. Default: WakingDreamer."""
    try:
        p = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "sanctuary_degree.json"
        if p.exists():
            data = json.loads(p.read_text())
            deg = data.get("degree", "WakingDreamer")
            if deg in SANCTUARY_DEGREES:
                return deg
    except Exception:
        pass
    return "WakingDreamer"


def _chunk_for_discord(text: str, chunk_size: int = 1900):
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
            # No good newline — hard break at chunk_size
            split_at = chunk_size

        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    return chunks


class DiscordEventForwarder:
    """Callback that forwards Conductor events to Discord in real-time.

    Forwards in exact order received:
    - TOOL_USE: which tool + args
    - TOOL_RESULT: output (FULL — no truncation)
    - AGENT_MESSAGE: text between tool calls (FULL — no truncation)

    TRUNCATION POLICY: NOTHING is ever truncated. Long messages are
    chunked into multiple Discord messages. Every character is sent.
    """

    def __init__(self):
        self._last_send = 0.0
        self._throttle_sec = 2.0
        self._tool_count = 0
        self._degree = _get_sanctuary_degree()

    def __call__(self, raw_langchain_message):
        import time
        now = time.time()

        try:
            # Try HeavenEvent parsing first
            events = HeavenEvent.from_langchain_message(raw_langchain_message)
            for event in events:
                ed = event.to_dict()
                etype = ed.get("event_type")
                data = ed.get("data", {})

                if etype == "TOOL_USE":
                    self._tool_count += 1
                    tool_name = data.get("name", "?")
                    tool_input = data.get("input", {})
                    args_str = self._format_args(tool_name, tool_input)
                    msg = f"🔧 `[{self._tool_count}]` **{tool_name}**"
                    if args_str:
                        msg += f"\n```\n{args_str}\n```"
                    self._send(msg)
                    self._last_send = time.time()

                elif etype == "TOOL_RESULT":
                    output = str(data.get("output", ""))
                    if output:
                        self._send(f"📋 `[{self._tool_count}]` result:\n```\n{output}\n```")
                        self._last_send = time.time()

                elif etype == "AGENT_MESSAGE":
                    content = data.get("content", "")
                    if content.strip():
                        self._send(f"💬 **{self._degree}:**\n{content}")
                        self._last_send = time.time()

        except Exception:
            # Fallback: parse langchain message directly
            try:
                self._fallback_parse(raw_langchain_message, now)
            except Exception as e2:
                logger.debug("DiscordEventForwarder fallback failed: %s", e2)

    def _fallback_parse(self, msg, now):
        """Parse tool calls directly from langchain AIMessage/ToolMessage."""
        import time
        # AIMessage with tool_calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                self._tool_count += 1
                name = tc.get("name", "?") if isinstance(tc, dict) else getattr(tc, "name", "?")
                args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                args_str = self._format_args(name, args)
                out = f"🔧 `[{self._tool_count}]` **{name}**"
                if args_str:
                    out += f"\n```\n{args_str}\n```"
                self._send(out)
                self._last_send = time.time()
        # ToolMessage with content (result)
        elif hasattr(msg, 'type') and msg.type == 'tool':
            content = str(getattr(msg, 'content', ''))
            if content:
                self._send(f"📋 `[{self._tool_count}]` result:\n```\n{content}\n```")
                self._last_send = time.time()
        # AIMessage with text content (no tool calls) — intermediate text response
        elif hasattr(msg, 'type') and msg.type == 'ai' and not getattr(msg, 'tool_calls', None):
            content = getattr(msg, 'content', '')
            # MiniMax may return content as a list of blocks
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = '\n'.join(text_parts)
            content = str(content)
            if content and content.strip():
                self._send(f"💬 **{self._degree}:**\n{content}")
                self._last_send = time.time()

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

    def _send(self, text: str):
        """Send message to Discord, chunking if needed. NEVER truncates."""
        import time as _time
        try:
            from cave.core.channel import UserDiscordChannel
            discord = UserDiscordChannel()
            if not (discord.token and discord.channel_id):
                return
        except Exception:
            return
        chunks = _chunk_for_discord(text)
        for i, chunk in enumerate(chunks):
            try:
                discord.deliver({"message": chunk})
                if len(chunks) > 1 and i < len(chunks) - 1:
                    _time.sleep(0.3)  # Rate limit buffer between chunks
            except Exception as e:
                logger.error("Discord chunk %d/%d failed: %s", i + 1, len(chunks), e)
                # Retry once after a short delay
                try:
                    _time.sleep(1.0)
                    discord.deliver({"message": chunk})
                except Exception:
                    logger.error("Discord chunk %d/%d retry also failed, SKIPPING", i + 1, len(chunks))


MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"



def _build_agent_config(system_prompt: str):
    """Build HeavenAgentConfig for completion-style execution.

    Lazy import to avoid import-time dependency on heaven_base.
    MiniMax requires extra_model_kwargs with anthropic_api_url and use_uni_api=False.
    MCPs: carton (knowledge graph), sophia (wisdom/routing), sancrev_treeshell (game/builder).
    """
    from heaven_base.baseheavenagent import HeavenAgentConfig
    from heaven_base.tools.bash_tool import BashTool
    from heaven_base.tools.network_edit_tool import NetworkEditTool
    from heaven_base.tools.skill_tool import SkillTool
    from heaven_base.tools.hermes_tool import HermesTool
    from heaven_base.tools.view_history_tool import ViewHistoryTool
    from heaven_base.tools.chain_tool import ChainTool

    return HeavenAgentConfig(
        name="conductor",
        system_prompt=system_prompt,
        tools=[BashTool, NetworkEditTool, SkillTool, HermesTool, ViewHistoryTool, ChainTool],
        model="MiniMax-M2.5-highspeed",
        use_uni_api=False,
        max_tokens=8000,
        extra_model_kwargs={"anthropic_api_url": MINIMAX_BASE_URL},
        persona="conductor",
        mcp_servers={
            "carton": {
                "command": "carton-mcp",
                "args": [],
                "transport": "stdio",
            },
            "sophia": {
                "command": "sophia-mcp",
                "args": [],
                "transport": "stdio",
            },
            "sancrev_treeshell": {
                "command": "python",
                "args": ["-m", "sanctuary_revolution_treeshell.mcp_server"],
                "transport": "stdio",
            },
        },
        prompt_suffix_blocks=[
            "path=/tmp/heaven_data/conductor_dynamic/memory.txt",
            "path=/tmp/heaven_data/conductor_dynamic/skill_info.txt",
            "path=/tmp/heaven_data/conductor_memory/MEMORY.md",
            "path=/tmp/heaven_data/conductor_dynamic/status.txt",
            "path=/tmp/heaven_data/conductor_dynamic/tasks.txt",
            "path=/tmp/heaven_data/conductor_dynamic/notepad.txt",
        ],
    )


def _parse_compaction_summaries(text: str) -> list:
    """Extract all <COMPACTION_SUMMARY> blocks from text."""
    import re
    pattern = re.compile(r'<COMPACTION_SUMMARY>(.*?)</COMPACTION_SUMMARY>', re.DOTALL)
    return [block.strip() for block in pattern.findall(text)]


def _build_compaction_config():
    """No-tools config for compaction summarization.

    Same model, same history access — but NO tools and a compaction-focused system prompt.
    No tools = agent can only produce text. Can't read docs, can't call GNOSYS, can't go rogue.
    If it wants to remind itself to talk to GNOSYS, it puts that in the summary.
    """
    from heaven_base.baseheavenagent import HeavenAgentConfig

    return HeavenAgentConfig(
        name="conductor-compaction",
        system_prompt=(
            "You are the Conductor in COMPACTION MODE. Your ONLY job is to produce an exhaustive, "
            "detailed, chronological narrative of everything that happened in this conversation. "
            "You have NO tools. Just read the history and produce summaries.\n\n"
            "CRITICAL RULES:\n"
            "- Write as if you are producing a meticulous incident log for someone who was NOT present.\n"
            "- Be EXHAUSTIVE. Include every file path, every command, every tool call, every error message.\n"
            "- Narrate chronologically: 'First, the user asked X. Then the agent did Y. The result was Z.'\n"
            "- Include EXACT file paths and container names (e.g., 'mind_of_god:/tmp/conductor/conductor/conductor.py').\n"
            "- Include the EXACT commands that were run and their outputs when relevant.\n"
            "- Include EXACT error messages when things failed, and what was done to fix them.\n"
            "- Include the reasoning and decisions made: WHY something was done, not just WHAT.\n"
            "- Include the user's stated goals, preferences, frustrations, and standing instructions.\n"
            "- Include any patterns, workarounds, or conventions that were discovered or established.\n"
            "- If something is in progress, describe EXACTLY what was being done and what the next step is.\n"
            "- Do NOT compress, abbreviate, or abstract. The next instance needs the FULL picture.\n"
            "- Do NOT editorialize or add commentary. Just describe what happened, faithfully and exactly.\n"
            "- Your summaries should be LONG. A thorough retelling of a long conversation should be long.\n\n"
            "Output your narrative inside <COMPACTION_SUMMARY> blocks. Use as many blocks as needed.\n"
            "If you need to do something after compaction (talk to GNOSYS, check a file, etc), "
            "put it in the summary as a concrete reminder with exact commands. "
            "Do NOT try to do it now."
        ),
        tools=[],
        model="MiniMax-M2.5-highspeed",
        use_uni_api=False,
        max_tokens=8000,
        extra_model_kwargs={"anthropic_api_url": MINIMAX_BASE_URL},
    )


CONDUCTOR_CONVERSATION_STATE = HEAVEN_DATA / "conductor_conversation.json"


class Conductor:
    """Persistent agent. Isaac's interface. Manages Grug + Researcher.

    Uses direct BaseHeavenAgent + BackgroundEventCapture callback:
    - BaseHeavenAgent instantiated per-message from HeavenAgentConfig
    - BackgroundEventCapture captures AGENT_MESSAGE events during execution
    - agent.run(prompt, heaven_main_callback=capture) — agent loops on tools internally
    - history_id from result["history_id"] directly
    - start_chat/continue_chat for conversation meta-tracking
    - history_id persisted to disk for restart recovery
    """

    def __init__(
        self,
        connector: GrugConnector,
        researcher_sdnac,
        state: StateMachine,
        config: Optional[ConductorConfig] = None,
    ):
        self.config = config or ConductorConfig()
        self.runner = Runner(connector, researcher_sdnac, state)
        self.cave_agent = None  # Set by register()
        self.anatomy = None  # Set by register()
        self.system_prompt = get_conductor_system_prompt(self.config)
        self._agent_config = _build_agent_config(self.system_prompt)

        # Conversation state — persisted to disk, survives restarts
        self.history_id = None
        self.conversation_id = None
        self._busy = False  # Lock: skip heartbeats while processing/compacting
        self._current_task = None  # asyncio.Task for the running agent call
        self._compacting = False  # Re-entrant guard for auto-compaction
        self._transcript_chars = 0  # Running estimate of transcript size
        self._compact_threshold = 800_000  # ~350k tokens ≈ 800k chars
        self._compaction_count = 0  # How many times we've auto-compacted
        self._load_conversation_state()

    def _load_conversation_state(self):
        """Load conversation state from disk. Recovers history_id across restarts."""
        try:
            if CONDUCTOR_CONVERSATION_STATE.exists():
                data = json.loads(CONDUCTOR_CONVERSATION_STATE.read_text())
                self.conversation_id = data.get("conversation_id")
                self.history_id = data.get("history_id")
                self._transcript_chars = data.get("transcript_chars", 0)
                self._compaction_count = data.get("compaction_count", 0)

                if self.history_id:
                    logger.info(
                        "Resumed conversation %s with history %s (transcript ~%dk chars, %d compactions)",
                        self.conversation_id, self.history_id,
                        self._transcript_chars // 1000, self._compaction_count,
                    )
        except Exception:
            logger.exception("Failed to load conversation state, starting fresh")
            self.history_id = None
            self.conversation_id = None

    def _save_conversation_state(self):
        """Persist conversation state to disk."""
        try:
            CONDUCTOR_CONVERSATION_STATE.parent.mkdir(parents=True, exist_ok=True)
            CONDUCTOR_CONVERSATION_STATE.write_text(json.dumps({
                "conversation_id": self.conversation_id,
                "history_id": self.history_id,
                "transcript_chars": self._transcript_chars,
                "compaction_count": self._compaction_count,
            }))
        except Exception:
            logger.exception("Failed to save conversation state")

    def _update_conversation(self):
        """Track conversation via ConversationManager (meta-tracking, not message storage)."""
        from heaven_base.memory.conversations import start_chat, continue_chat

        if not self.history_id:
            return

        try:
            if not self.conversation_id:
                conv = start_chat(
                    title="Conductor — Isaac's Interface",
                    first_history_id=self.history_id,
                    agent_name="conductor",
                    tags=["conductor", "isaac"],
                )
                self.conversation_id = conv["conversation_id"]
                logger.info("Started conversation %s", self.conversation_id)
            else:
                continue_chat(self.conversation_id, self.history_id)

            self._save_conversation_state()
        except Exception:
            logger.exception("Failed to update conversation")

    def new_conversation(self):
        """Start a fresh conversation (clear history). Call when Isaac wants a clean slate."""
        self.history_id = None
        self.conversation_id = None
        self._transcript_chars = 0
        self._save_conversation_state()
        logger.info("Started new conversation (cleared state)")

    def register(self, cave_agent) -> Dict[str, Any]:
        """Register Conductor in CAVE and get anatomy access."""
        self.cave_agent = cave_agent
        result = register_conductor_in_cave(cave_agent, self.config)
        self.anatomy = get_conductor_anatomy_access(cave_agent)
        return result

    def _notify_discord(self, message: str):
        """Send a notification to Discord. Chunks if needed. NEVER truncates."""
        try:
            from cave.core.channel import UserDiscordChannel
            discord = UserDiscordChannel()
            if discord.token and discord.channel_id:
                for chunk in _chunk_for_discord(message):
                    discord.deliver({"message": chunk})
        except Exception:
            pass

    async def _handle_compact(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Compact: new agent (same system, no special tools) on same history → summarize → wipe → bootstrap.

        1. Create new BaseHeavenAgent with compaction config (tools=[]) on SAME history
        2. Run it with compaction prompt — it outputs <COMPACTION_SUMMARY> blocks
        3. Discord broadcaster shows the run live
        4. Parse ALL blocks, roll into one
        5. Wipe history
        6. Start new conversation: inject summary as user message, run the Conductor again
        """
        if not self.history_id:
            return {"status": "success", "response": "Nothing to compact — no conversation history yet.", "metadata": metadata}

        old_history_id = self.history_id
        logger.info("Compacting: running agent on history %s with compaction prompt", old_history_id)
        self._notify_discord("🗜️ Compacting — summarizing before wipe...")

        # Step 1: New agent with compaction config on the SAME history
        all_blocks = []
        self._busy = True
        try:
            agent = BaseHeavenAgent(
                config=_build_compaction_config(),
                unified_chat=UnifiedChat(),
                history_id=self.history_id,
            )

            # Import for Discord broadcasting during compaction passes
            from .event_broadcaster import EventBroadcaster, ConductorDiscordChannel

            compaction_prompt = (
                "# COMPACTION MODE — PRODUCE EXHAUSTIVE NARRATIVE\n\n"
                "Your context is about to be wiped. A NEW instance of you — with ZERO memory — "
                "will receive ONLY what you write here. If you leave something out, it is GONE FOREVER.\n\n"
                "## Instructions\n\n"
                "Go through the ENTIRE conversation history from beginning to end. For each phase "
                "of work, write a detailed <COMPACTION_SUMMARY> block that narrates EXACTLY what "
                "happened, as if telling the story to someone who was not present.\n\n"
                "### What to include in EVERY block:\n"
                "- What the user asked for and WHY (their stated goals and reasoning)\n"
                "- What actions were taken: exact commands, exact file paths, exact tool calls\n"
                "- What the results were: outputs, errors, successes\n"
                "- What decisions were made and WHY\n"
                "- What was learned: working patterns, container names, path conventions, gotchas\n"
                "- If something failed, the EXACT error and what was done about it\n\n"
                "### Format\n\n"
                "<COMPACTION_SUMMARY>\n"
                "[Detailed chronological narrative of this chunk of work. Be specific and thorough.\n"
                "Include file paths, command outputs, error messages, decisions, and reasoning.\n"
                "This should read like a detailed incident report, not a bullet-point summary.\n"
                "The next instance should be able to understand EXACTLY what happened and continue\n"
                "without asking 'wait, what was that about?']\n"
                "</COMPACTION_SUMMARY>\n\n"
                "### Rules\n"
                "- Be EXHAUSTIVE. Long is good. Thorough is good. Vague is UNACCEPTABLE.\n"
                "- Write in plain narrative prose, chronologically.\n"
                "- Include the user's current goals, standing instructions, preferences, and frustrations.\n"
                "- Include infrastructure knowledge: which containers exist, how to access them, "
                "what's installed where, which paths work.\n"
                "- If work is in progress, describe EXACTLY where it left off and what to do next.\n"
                "- Include environmental facts: environment variables, config file locations, "
                "service URLs, running processes.\n"
                "- Do NOT compress or abstract. The next instance needs the FULL picture.\n"
                "- Do NOT skip things because they seem minor. Minor details are often critical.\n"
                "- Output as many blocks as needed. A thorough retelling of a long conversation should be LONG.\n\n"
                "When you have covered EVERYTHING, output <COMPACTION_COMPLETE/> as the very last line."
            )

            # Multi-pass compaction: keep calling the agent until it signals completion
            # or we hit the max passes. Each pass continues on the SAME history.
            max_passes = 10
            for pass_num in range(max_passes):
                if pass_num == 0:
                    prompt = compaction_prompt
                else:
                    prompt = (
                        "Continue your compaction summary from where you left off. "
                        "You have NOT finished yet. Keep going through the conversation history "
                        "and produce more <COMPACTION_SUMMARY> blocks for the parts you haven't covered yet.\n\n"
                        "When you have covered EVERYTHING, output <COMPACTION_COMPLETE/> as the very last line."
                    )

                capture = BackgroundEventCapture()
                broadcaster = EventBroadcaster([ConductorDiscordChannel()])
                composite = CompositeCallback([capture, broadcaster])

                # Use context guard — if context fills up during multi-pass compaction,
                # the guard pops the oldest messages (already summarized in prior passes)
                # to make room. Better than crashing and forcing a restart.
                result = await self._run_with_context_guard(
                    agent, prompt, heaven_main_callback=composite,
                )

                # Parse blocks from this pass
                pass_blocks = []
                pass_text = ""
                for event in capture.captured_events:
                    data = event.get("data", {})
                    content = data.get("content", "")
                    if content:
                        pass_text += content
                        pass_blocks.extend(_parse_compaction_summaries(content))

                all_blocks.extend(pass_blocks)
                logger.info("Compaction pass %d: collected %d blocks (%d total)", pass_num + 1, len(pass_blocks), len(all_blocks))
                self._notify_discord(f"🗄️ Compaction pass {pass_num + 1}: {len(pass_blocks)} blocks (total: {len(all_blocks)})")

                # Check if agent signaled completion or produced no new blocks
                if "<COMPACTION_COMPLETE/>" in pass_text or "<COMPACTION_COMPLETE>" in pass_text:
                    logger.info("Compaction complete signal received on pass %d", pass_num + 1)
                    break
                if not pass_blocks and pass_num > 0:
                    logger.info("No new blocks on pass %d, stopping", pass_num + 1)
                    break

        except Exception:
            logger.exception("Compaction summarize step failed")
        finally:
            self._busy = False

        # Step 2: Roll up all blocks
        if all_blocks:
            rolled_summary = "\n---\n".join(all_blocks)
        else:
            rolled_summary = "(Summarizer produced no COMPACTION_SUMMARY blocks)"
        logger.info("Compaction collected %d summary blocks", len(all_blocks))

        # Step 3: Wipe history + reset transcript counter
        self.history_id = None
        self.conversation_id = None
        self._transcript_chars = 0
        self._compaction_count += 1
        self._save_conversation_state()
        logger.info("Compaction #%d complete — transcript counter reset", self._compaction_count)

        # Step 4: Bootstrap — new conversation with summary injected, run the Conductor again
        hb_prompt = ""
        try:
            hb_path = Path(HEAVEN_DATA / "conductor_heartbeat_config.json")
            if hb_path.exists():
                hb_cfg = json.loads(hb_path.read_text())
                if hb_cfg.get("enabled"):
                    hb_prompt = hb_cfg.get("prompt", "")
        except Exception:
            pass

        bootstrap_msg = (
            f"{hb_prompt}\n\n"
            "---\n\n"
            "# CONTINUATION AFTER COMPACTION\n\n"
            "Your conversation history was just compacted. The summary below contains "
            "everything from the previous conversation. Use it to orient yourself, "
            "then proceed with your heartbeat directive above.\n\n"
            f"<COMPACTION_SUMMARY>\n{rolled_summary}\n</COMPACTION_SUMMARY>"
        )
        # Notify FIRST — compaction is done, THEN bootstrap runs
        self._notify_discord(f"✅ Compacted #{self._compaction_count}. Old: `{old_history_id}`, new: `{self.history_id}`")
        # Bootstrap: run the special heartbeat with summary brace
        result = await self.handle_message(bootstrap_msg, metadata)
        # Return simple completion — bootstrap already ran and broadcast to Discord.
        # Do NOT propagate bootstrap result back, that causes the echo bug.
        return {"status": "success", "response": f"Compaction #{self._compaction_count} complete.", "metadata": metadata}

    async def _handle_stop(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel the currently running agent call via asyncio.Task cancellation."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await self._current_task
            except (asyncio.CancelledError, Exception):
                pass
            self._current_task = None
            self._busy = False
            self._notify_discord("🛑 Agent stopped.")
            logger.info("Agent call cancelled via !stop")
            return {"status": "success", "response": "Agent stopped.", "metadata": metadata}
        return {"status": "success", "response": "Nothing running to stop.", "metadata": metadata}

    async def _run_with_context_guard(self, agent, prompt, as_task=False, **run_kwargs):
        """Run agent with context window overflow protection.

        Catches 'context window exceeds limit' (MiniMax error 2013) from the API,
        pops oldest messages from history (~30k chars per attempt) to shed context,
        and retries. Maintains clean message boundaries (always lands on a HumanMessage).

        This is the reactive safety net — the heuristic _transcript_chars counter
        provides proactive compaction, but this catches the cases where:
        - The counter drifted from reality
        - Tool-call loops grew the context within a single turn
        - The system prompt + suffix blocks are larger than expected

        Args:
            agent: BaseHeavenAgent instance
            prompt: Prompt to pass to agent.run()
            as_task: If True, wrap in asyncio.Task for !stop cancellation support
            **run_kwargs: Additional kwargs for agent.run()
        """
        from langchain_core.messages import HumanMessage as HM, SystemMessage as SM

        max_attempts = 20
        chars_per_pop = 30_000  # ~13k tokens per pop

        for attempt in range(max_attempts):
            try:
                if as_task:
                    self._current_task = asyncio.create_task(
                        agent.run(prompt, **run_kwargs)
                    )
                    result = await self._current_task
                    self._current_task = None
                else:
                    result = await agent.run(prompt, **run_kwargs)
                return result
            except asyncio.CancelledError:
                self._current_task = None
                raise  # Don't retry on user cancellation
            except (RuntimeError, Exception) as e:
                err_str = str(e)
                is_context_error = "context window" in err_str.lower()
                if not is_context_error or attempt >= max_attempts - 1:
                    if as_task:
                        self._current_task = None
                    raise

                # --- Context window exceeded: pop oldest messages and retry ---
                if not agent.history or not hasattr(agent.history, 'messages'):
                    if as_task:
                        self._current_task = None
                    raise

                messages = agent.history.messages
                if len(messages) <= 2:  # Only system prompt + current message left
                    if as_task:
                        self._current_task = None
                    raise  # Nothing left to trim

                chars_popped = 0
                msgs_popped = 0
                iterations_popped = 0

                # Pop whole iterations (HumanMessage → next HumanMessage)
                # An iteration = one user turn + all agent responses, tool calls, results
                # This keeps history structurally valid after trimming
                while len(messages) > 2 and chars_popped < chars_per_pop:
                    # Pop the HumanMessage that starts this iteration
                    msg = messages.pop(1)
                    chars_popped += len(str(getattr(msg, 'content', '')))
                    msgs_popped += 1

                    # Pop all subsequent messages until next HumanMessage (or end)
                    while len(messages) > 1 and not isinstance(messages[1], HM):
                        msg = messages.pop(1)
                        chars_popped += len(str(getattr(msg, 'content', '')))
                        msgs_popped += 1

                    iterations_popped += 1

                logger.warning(
                    "Context window exceeded (attempt %d/%d): popped %d iterations (%d msgs, ~%dk chars), %d msgs remain",
                    attempt + 1, max_attempts, iterations_popped, msgs_popped, chars_popped // 1000, len(messages),
                )
                self._notify_discord(
                    f"⚠️ Context overflow — trimmed {iterations_popped} iterations "
                    f"(~{chars_popped // 1000}k chars), retrying (attempt {attempt + 1}/{max_attempts})"
                )

        # Should never reach here (last attempt raises above), but just in case
        raise RuntimeError("Context window still exceeded after maximum trim attempts")

    async def handle_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a message from Isaac using BaseHeavenAgent + callback.

        Args:
            message: The raw message content from Isaac
            metadata: Optional metadata (discord_message_id, source, etc.)

        Returns:
            Dict with status, response text, and metadata
        """
        metadata = metadata or {}

        cmd = message.strip().lower()
        if cmd == "!compact":
            return await self._handle_compact(metadata)
        if cmd == "!stop":
            return await self._handle_stop(metadata)

        # Auto-compaction: if transcript exceeds threshold, compact before processing
        if (
            not self._compacting
            and self.history_id
            and self._transcript_chars >= self._compact_threshold
        ):
            logger.info(
                "Auto-compaction triggered: %d chars >= %d threshold (compaction #%d)",
                self._transcript_chars, self._compact_threshold, self._compaction_count + 1,
            )
            self._notify_discord(
                f"🗜️ Auto-compacting — transcript ~{self._transcript_chars // 1000}k chars "
                f"(threshold: {self._compact_threshold // 1000}k)"
            )
            self._compacting = True
            try:
                await self._handle_compact(metadata)
            finally:
                self._compacting = False

        logger.info("Conductor executing (history=%s): %s", self.history_id, message[:80])

        try:
            agent_kwargs = dict(
                config=self._agent_config,
                unified_chat=UnifiedChat(),
                max_tool_calls=99,
            )
            if self.history_id:
                agent_kwargs["history_id"] = self.history_id

            agent = BaseHeavenAgent(**agent_kwargs)

            # Callback captures events + broadcasts to registered channels
            from .event_broadcaster import EventBroadcaster, ConductorDiscordChannel
            capture = BackgroundEventCapture()
            broadcaster = EventBroadcaster([
                ConductorDiscordChannel(),
                # SSEChannel(queue),     # Future: frontend
                # FileLogChannel(path),  # Future: event log
            ])
            composite = CompositeCallback([capture, broadcaster])

            # Agent loops internally on tool calls — wrapped in context guard for overflow protection
            # as_task=True wraps in asyncio.Task so !stop can cancel mid-run
            result = await self._run_with_context_guard(
                agent, message, as_task=True, heaven_main_callback=composite,
            )

            # Get response from captured AGENT_MESSAGE events (last one is final)
            agent_messages = capture.get_events_by_type("AGENT_MESSAGE")
            if agent_messages:
                last_msg = agent_messages[-1]
                response_text = last_msg.get("data", {}).get("content", "")
            else:
                response_text = ""

            # history_id directly from result — no string-max bug
            new_history_id = result.get("history_id")

            if new_history_id:
                self.history_id = new_history_id
                self._update_conversation()

            # Track transcript size: system prompt + message + all captured events
            # System prompt loads every turn — must count it
            turn_chars = len(self.system_prompt) + len(message)
            # prompt_suffix_blocks load dynamic files each turn too
            for block in (self._agent_config.prompt_suffix_blocks or []):
                if block.startswith("path="):
                    try:
                        suffix_path = Path(block[5:])
                        if suffix_path.exists():
                            turn_chars += suffix_path.stat().st_size
                    except Exception:
                        pass
            # Captured events: tool calls, results, agent messages
            for event in capture.captured_events:
                data = event.get("data", {})
                for key in ("content", "input", "output"):
                    val = data.get(key)
                    if val:
                        turn_chars += len(str(val))
            self._transcript_chars += turn_chars
            self._save_conversation_state()
            logger.info(
                "Conductor response (%d turn chars, %dk total): %s",
                turn_chars, self._transcript_chars // 1000,
                response_text[:200] if response_text else "(empty)",
            )

            return {
                "status": "success",
                "response": response_text or "",
                "metadata": metadata,
            }
        except asyncio.CancelledError:
            self._current_task = None
            logger.info("Agent call cancelled")
            return {"status": "cancelled", "response": "Agent stopped.", "metadata": metadata}
        except Exception:
            self._current_task = None
            import traceback
            tb = traceback.format_exc()
            logger.exception("Conductor execution error")
            return {
                "status": "error",
                "response": f"Conductor execution failed:\n```\n{tb}\n```",
                "error": tb,
                "metadata": metadata,
            }
