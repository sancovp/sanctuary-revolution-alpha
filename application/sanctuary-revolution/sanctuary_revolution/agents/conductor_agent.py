"""ConductorAgent — SANCREV's coordinator agent.

ChatAgent subclass that DIs Conductor as its runtime.
Conductor manages BaseHeavenAgent, conversation history, compaction,
Discord broadcasting, context overflow protection.

ConductorAgent adds CAVE infrastructure: inbox, channels, commands, queue.

ALL message processing goes through check_inbox() → intercept_command() → run().
Ears feeds this agent like any other — no special-case inbox loops needed.
Discord notifications, !commands, status markers all live HERE on the agent.
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cave.core.agent import ChatAgent, AgentConfig

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))


class ConductorAgent(ChatAgent):
    """Conductor — Isaac's interface. Coordinates everything.

    DIs Conductor runtime (BaseHeavenAgent-based) for message processing.
    Inherits from ChatAgent: inbox, channels, !commands, queue drain.

    Fractal pattern: ConductorAgent is a full self-contained unit.
    Ears enqueues messages. check_inbox() processes them. No external loops.

    ConductorAgent provides:
    - ALL !command handling (moved from sancrev http_server)
    - Discord notifications (🏃 processing, ✅ complete, ❌ error)
    - Discord prefix stripping
    - Heartbeat timer reset
    - GNOSYS compaction guard
    - SSE event queue passing
    """

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self._conductor = None  # Set by init_conductor()
        self._sse_queue = None  # Set externally for SSE streaming

    # ==================== RUNTIME INIT ====================

    def init_conductor(self, cave_agent=None, agent_config_path: str = None) -> bool:
        """Initialize the Conductor runtime and DI it.

        Called by WakingDreamer after agent creation.
        Loads agent config from JSON if provided — tools, MCPs, prompt_suffix_blocks
        all configurable without code changes.
        Returns True if successful, False if conductor package unavailable.
        """
        try:
            from conductor.conductor import Conductor
            from conductor.state_machine import StateMachine
            from conductor.cave_registration import ConductorConfig

            config = ConductorConfig()
            json_config = self._load_agent_json_config(agent_config_path)

            state = StateMachine(name="conductor")
            self._conductor = Conductor(
                connector=None,
                researcher_sdnac=None,
                state=state,
                config=config,
            )

            if json_config:
                self._apply_json_config(json_config)

            if cave_agent:
                self._conductor.register(cave_agent)

            # Async runtime — Agent.run() awaits coroutines automatically
            conductor = self._conductor

            async def conductor_run(message: str) -> Dict[str, Any]:
                """Run conductor and return full result dict."""
                metadata = {}
                if self._sse_queue:
                    metadata["sse_queue"] = self._sse_queue

                # Inject GNOSYS compaction warning
                if self._is_gnosys_compacting():
                    metadata["gnosys_compacting"] = True
                    message = (
                        "[SYSTEM: GNOSYS is currently compacting context. "
                        "Do NOT send messages to GNOSYS via call_gnosys.sh "
                        "until compaction completes. Process this message "
                        "using your own capabilities only.]\n\n" + message
                    )

                return await conductor.handle_message(message, metadata)

            self.set_runtime(conductor_run)
            self._conductor_ref = conductor  # For !prune/!heartbeat commands
            logger.info("ConductorAgent: runtime initialized (history=%s)", conductor.history_id)
            return True

        except ImportError as e:
            logger.warning("ConductorAgent: conductor package not available: %s", e)
            return False
        except Exception as e:
            logger.error("ConductorAgent: failed to init runtime: %s", e, exc_info=True)
            return False

    @property
    def conductor(self):
        """Access the underlying Conductor instance."""
        return self._conductor

    # ==================== INBOX PROCESSING (FRACTAL) ====================

    async def check_inbox(self) -> List[Any]:
        """Process all pending messages with Discord notifications.

        This is the SOLE consumer of conductor messages. Ears enqueues,
        check_inbox processes. No external _conductor_inbox_loop needed.

        For each message:
        1. Strip Discord prefix
        2. Check !commands (intercept_command)
        3. Send 🏃 notification
        4. Run through conductor runtime
        5. Send ✅/❌ notification
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

                # Strip Discord prefix: [Discord #channel] username: actual message
                user_msg = self._extract_user_message(content)

                # Reset heartbeat timer on EVERY message
                self._reset_heartbeat_timer()

                # Check !commands first
                # We need to check on the stripped message, but intercept_command
                # checks msg.content directly. Temporarily override for command check.
                cmd_result = await self._check_command(user_msg)
                if cmd_result is not None:
                    # Command handled — send as system notification
                    self._notify(cmd_result)
                    responses.append({"status": "handled", "command": True})
                    continue

                # Not a command — process through runtime
                is_heartbeat = metadata.get("type") == "heartbeat"
                if is_heartbeat:
                    self._notify(f"\U0001F493 **Heartbeat fired** ({metadata.get('source', 'heart')})")
                else:
                    from conductor.conductor import _get_sanctuary_degree
                    deg = _get_sanctuary_degree()
                    preview = user_msg[:10] + ("..." if len(user_msg) > 10 else "")
                    self._notify(f"🏃 **{deg}:** {preview}")

                # Run through conductor runtime
                result = await self.run_with_content(user_msg)

                # Send completion notification
                if isinstance(result, dict):
                    status = result.get("status", "")
                    if status == "success":
                        from conductor.conductor import _get_sanctuary_degree
                        self._notify(f"✅ Turn iteration complete. — {_get_sanctuary_degree()}")
                    elif status == "blocked":
                        self._notify("⚠️ **Blocked** — needs external input")
                    elif status == "cancelled":
                        self._notify("🛑 **Stopped.**")
                    elif status == "error":
                        err = result.get("error", "unknown")
                        self._notify(f"❌ **Error:** {err}")
                    else:
                        from conductor.conductor import _get_sanctuary_degree
                        self._notify(f"✅ Turn iteration complete. — {_get_sanctuary_degree()}")
                elif result is not None:
                    from conductor.conductor import _get_sanctuary_degree
                    self._notify(f"✅ Turn iteration complete. — {_get_sanctuary_degree()}")

                responses.append(result)

        except Exception as e:
            logger.error("ConductorAgent check_inbox error: %s", e, exc_info=True)
            self._notify(f"❌ **Error:** {e}")
        finally:
            self._processing = False

        return responses

    async def run_with_content(self, content: str) -> Any:
        """Run the runtime with string content directly (not a Message object).

        Unlike Agent.run(message) which extracts .content, this passes
        the already-extracted string to the runtime.
        """
        if self._runtime is None:
            return None

        if callable(self._runtime):
            result = self._runtime(content)
        elif hasattr(self._runtime, 'run'):
            result = self._runtime.run(content)
        elif hasattr(self._runtime, 'handle_message'):
            result = self._runtime.handle_message(content)
        else:
            return None

        if asyncio.iscoroutine(result) or asyncio.isfuture(result):
            return await result
        return result

    # ==================== COMMAND HANDLING ====================

    async def _check_command(self, content: str) -> Optional[str]:
        """Check for !commands on already-extracted user message.

        Returns response string if command handled, None if not a command.
        All !commands from sancrev _handle_conductor_command live here now.
        """
        if not content.startswith("!"):
            return None

        # !new
        if content == "!new":
            self._conductor.new_conversation()
            return "🆕 **New conversation started.** History cleared."

        # !resume
        if content == "!resume":
            self._conductor._load_conversation_state()
            if self._conductor.history_id:
                return f"▶️ **Resumed conversation** `{self._conductor.conversation_id}`"
            return "⚠️ **No saved conversation to resume.** Use `!new` to start fresh."

        # !status / !ping
        if content in ("!status", "!ping"):
            return self._build_status()

        # !list
        if content == "!list":
            return self._build_conversation_list()

        # !{number} — select from last list
        m = re.match(r"^!(\d+)$", content)
        if m:
            return self._select_conversation(int(m.group(1)))

        # !agent <name>
        m = re.match(r"^!agent\s+(\w+)$", content)
        if m:
            return f"🔀 **Routing to agent `{m.group(1)}`.** (Not yet implemented.)"

        # !gnosys <msg>
        m = re.match(r"^!gnosys\s+(.+)$", content, re.DOTALL)
        if m:
            return self._send_to_gnosys(m.group(1).strip())

        # !heartbeat [on|off|interval|prompt|status]
        if content == "!heartbeat" or content.startswith("!heartbeat "):
            return self._handle_heartbeat_command(content)

        # !compact
        if content == "!compact":
            result = await self._cmd_compact()
            return result.get("response", "Compacted.")

        # !stop
        if content == "!stop":
            return await self._handle_stop()

        # !help
        if content == "!help":
            return (
                "📖 **Conductor Commands:**\n"
                "`!ping` — Full system health\n"
                "`!status` — Same as !ping\n"
                "`!new` — Start fresh conversation\n"
                "`!resume` — Reload saved conversation\n"
                "`!list` — List recent conversations\n"
                "`!<number>` — Select conversation from `!list`\n"
                "`!agent <name>` — Route to specific agent\n"
                "`!gnosys <msg>` — Send message to GNOSYS\n"
                "`!compact` — Compact context\n"
                "`!stop` — Cancel running agent call\n"
                "`!heartbeat [on|off|interval N|prompt text]` — Control heartbeat\n"
                "`!help` — This help text"
            )

        return f"❓ Unknown command: `{content}`\nUse `!help` for available commands."

    def intercept_command(self, msg) -> Optional[Dict[str, Any]]:
        """Override — we handle commands in check_inbox via _check_command.

        This is still called by ChatAgent.handle_message() for the async path.
        Route through _check_command for consistency.
        """
        content = msg.content.strip() if hasattr(msg, 'content') else ""
        user_msg = self._extract_user_message(content)
        result = self._check_command(user_msg)
        if result is not None:
            return {"command": True, "response": result}
        return None

    # ==================== COMMAND IMPLEMENTATIONS ====================

    def _build_status(self) -> str:
        """Build full system health status."""
        lines = ["📊 **System Health:**"]

        # Conductor
        h = self._conductor.history_id or "(none)" if self._conductor else "(none)"
        c = self._conductor.conversation_id or "(none)" if self._conductor else "(none)"
        lines.append(f"🎭 **Conductor:** ✅ ONLINE | conv: `{str(c)[:20]}...`")

        # GNOSYS
        if self._is_gnosys_compacting():
            lines.append("🧠 **GNOSYS:** ⏳ COMPACTING")
        else:
            import subprocess
            try:
                r = subprocess.run(["tmux", "has-session", "-t", "cave"], capture_output=True, timeout=3)
                if r.returncode == 0:
                    lines.append("🧠 **GNOSYS:** ✅ ONLINE (tmux:cave)")
                else:
                    lines.append("🧠 **GNOSYS:** ❌ OFFLINE")
            except Exception:
                lines.append("🧠 **GNOSYS:** ❓ UNKNOWN")

        # Processing
        if self._processing:
            lines.append("⚙️ **Processing:** 🔄 YES")
        else:
            lines.append(f"⚙️ **Processing:** 💤 IDLE ({self.inbox_count} queued)")

        return "\n".join(lines)

    def _build_conversation_list(self) -> str:
        """List recent conversations."""
        try:
            from heaven_base.memory.conversations import list_chats
            chats = list_chats(limit=10)
            if not chats:
                return "📭 **No conversations found.**"
            lines = ["📋 **Recent conversations:**"]
            for i, chat in enumerate(chats, 1):
                title = chat.get("title", "Untitled")
                turns = chat.get("turn_count", "?")
                lines.append(f"`{i}` — **{title}** ({turns} turns)")
            lines.append("\nUse `!<number>` to select one.")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ **Error listing conversations:** {e}"

    def _select_conversation(self, idx: int) -> str:
        """Select a conversation by index from last !list."""
        try:
            from heaven_base.memory.conversations import list_chats, get_latest_history
            chats = list_chats(limit=10)
            if not chats or idx < 1 or idx > len(chats):
                return f"⚠️ **Invalid selection.** Use `!list` first."
            chat = chats[idx - 1]
            cid = chat.get("conversation_id")
            hist = get_latest_history(cid)
            if hist:
                self._conductor.history_id = hist
                self._conductor.conversation_id = cid
                self._conductor._save_conversation_state()
                title = chat.get("title", "Untitled")
                return f"✅ **Selected:** {title}\n**Conversation:** `{cid}`"
            return "⚠️ **Conversation found but no history ID.**"
        except Exception as e:
            return f"❌ **Error:** {e}"

    def _send_to_gnosys(self, msg: str) -> str:
        """Send message to GNOSYS file inbox."""
        try:
            import uuid
            inbox_dir = HEAVEN_DATA_DIR / "inboxes" / "main"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().isoformat()
            msg_id = uuid.uuid4().hex[:8]
            msg_file = inbox_dir / f"{ts}_{msg_id}.json"
            msg_file.write_text(json.dumps({
                "id": msg_id, "from": "discord", "to": "main",
                "content": msg, "timestamp": ts, "priority": 10,
            }, indent=2))
            return f"📨 **Sent to GNOSYS inbox:** {msg}"
        except Exception as e:
            return f"❌ **Failed:** {e}"

    def _handle_heartbeat_command(self, content: str) -> str:
        """Handle !heartbeat [on|off|interval|prompt|status]."""
        hb_path = HEAVEN_DATA_DIR / "conductor_heartbeat_config.json"
        try:
            if hb_path.exists():
                hb_cfg = json.loads(hb_path.read_text())
            else:
                hb_cfg = {"enabled": False, "interval_seconds": 300,
                          "prompt": "Heartbeat: check rituals, check inbox, report status."}

            parts = content.split(None, 2)
            sub = parts[1] if len(parts) > 1 else "status"

            if sub == "on":
                hb_cfg["enabled"] = True
                hb_path.write_text(json.dumps(hb_cfg, indent=2))
                return f"💓 **Heartbeat ON** — every {hb_cfg['interval_seconds']}s"
            elif sub == "off":
                hb_cfg["enabled"] = False
                hb_path.write_text(json.dumps(hb_cfg, indent=2))
                return "💤 **Heartbeat OFF**"
            elif sub == "interval":
                val = parts[2] if len(parts) > 2 else None
                if not val or not val.isdigit():
                    return "⚠️ Usage: `!heartbeat interval <seconds>`"
                hb_cfg["interval_seconds"] = int(val)
                hb_path.write_text(json.dumps(hb_cfg, indent=2))
                return f"⏱️ **Heartbeat interval set to {val}s**"
            elif sub == "prompt":
                val = parts[2] if len(parts) > 2 else None
                if not val:
                    return "⚠️ Usage: `!heartbeat prompt <text>`"
                hb_cfg["prompt"] = val
                hb_path.write_text(json.dumps(hb_cfg, indent=2))
                return f"📝 **Heartbeat prompt updated:** {val}"
            else:
                state = "ON 💓" if hb_cfg.get("enabled") else "OFF 💤"
                interval = hb_cfg.get("interval_seconds", "?")
                prompt = hb_cfg.get("prompt", "(none)")
                return f"**Heartbeat Config:**\nState: {state}\nInterval: {interval}s\nPrompt: {prompt}"
        except Exception as e:
            return f"❌ **Heartbeat error:** {e}"

    async def _handle_stop(self) -> str:
        """Cancel running agent call."""
        if self._conductor and hasattr(self._conductor, '_handle_stop'):
            try:
                result = await self._conductor._handle_stop({})
                return result.get("response", "🛑 **Stopped.**")
            except Exception:
                pass
        self._busy = False
        self.inbox.clear()
        return "🛑 **Stopped.** Queue cleared."

    async def _cmd_compact(self) -> Dict[str, Any]:
        """Trigger compaction on Conductor's conversation history."""
        if not self._conductor:
            return {"command": "compact", "status": "no conductor runtime"}
        try:
            result = await self._conductor._handle_compact({})
            return {"command": "compact", **result}
        except Exception as e:
            return {"command": "compact", "status": "error", "reason": str(e)}

    # ==================== DISCORD HELPERS ====================

    @staticmethod
    def _extract_user_message(content: str) -> str:
        """Strip Discord prefix: [Discord #channel] username: actual message"""
        m = re.match(r"^\[Discord #\d+\]\s+\w+:\s*(.*)$", content.strip(), re.DOTALL)
        if m:
            return m.group(1).strip()
        return content.strip()

    def _notify(self, text: str) -> None:
        """Send notification to Discord via this agent's main channel.

        Splits long messages into chunks (Discord 2000 char limit).
        """
        if not self.central_channel:
            return
        main_ch = self.central_channel.main()
        if not main_ch:
            return

        try:
            if len(text) <= 1900:
                main_ch.deliver({"message": text})
            else:
                remaining = text
                chunk_num = 0
                while remaining:
                    if len(remaining) <= 1900:
                        chunk = remaining
                        remaining = ""
                    else:
                        split_at = 1900
                        for i in range(1900, max(1700, 0), -1):
                            if i < len(remaining) and remaining[i] in '\n \t':
                                split_at = i
                                break
                        chunk = remaining[:split_at]
                        remaining = remaining[split_at:].lstrip()

                    if chunk_num > 0:
                        chunk = f"(cont)\n{chunk}"
                    main_ch.deliver({"message": chunk})
                    chunk_num += 1
        except Exception as e:
            logger.error("ConductorAgent notify failed: %s", e)

    def _reset_heartbeat_timer(self) -> None:
        """Reset heartbeat timer — user is active."""
        ts_path = HEAVEN_DATA_DIR / "conductor_ops" / "heartbeat" / "last_user_message.txt"
        ts_path.parent.mkdir(parents=True, exist_ok=True)
        ts_path.write_text(datetime.utcnow().isoformat())

    @staticmethod
    def _is_gnosys_compacting() -> bool:
        """Check if GNOSYS is currently compacting context."""
        lock_file = HEAVEN_DATA_DIR / "gnosys_compacting.lock"
        if not lock_file.exists():
            return False
        try:
            data = json.loads(lock_file.read_text())
            since = datetime.fromisoformat(data["compacting_since"])
            elapsed = (datetime.now() - since).total_seconds()
            if elapsed > 300:
                lock_file.unlink(missing_ok=True)
                return False
            return True
        except Exception:
            return False

    # ==================== CONFIG ====================

    def _load_agent_json_config(self, path: str = None) -> Optional[Dict]:
        """Load agent JSON config from disk."""
        config_path = Path(path) if path else HEAVEN_DATA_DIR / "conductor_agent_config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                logger.info("ConductorAgent: loaded config from %s", config_path)
                return data
            except Exception as e:
                logger.error("ConductorAgent: failed to load config: %s", e)
        return None

    def _apply_json_config(self, json_config: Dict) -> None:
        """Apply JSON config to the Conductor's HeavenAgentConfig."""
        if not self._conductor or not hasattr(self._conductor, '_agent_config'):
            return

        ac = self._conductor._agent_config

        if "prompt_suffix_blocks" in json_config:
            ac.prompt_suffix_blocks = json_config["prompt_suffix_blocks"]
            logger.info("ConductorAgent: %d prompt_suffix_blocks from JSON", len(ac.prompt_suffix_blocks))
        if "model" in json_config:
            ac.model = json_config["model"]
        if "max_tokens" in json_config:
            ac.max_tokens = json_config["max_tokens"]
        if "mcps" in json_config:
            ac.mcp_servers = json_config["mcps"]
        if "persona" in json_config:
            ac.persona = json_config["persona"]

        logger.info("ConductorAgent: JSON config applied (model=%s, persona=%s)",
                     ac.model, ac.persona)
