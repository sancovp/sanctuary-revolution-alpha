"""
CodeAgent - Base class for code agents with Actor model inbox.

This is the fundamental building block. CodeAgent IS a llegos Actor,
meaning it has message passing as a first-class citizen.

Hierarchy:
    CodeAgent(Actor)              # Base - any code agent, has inbox
        └── ClaudeCodeAgent       # Claude-specific impl (tmux-based)
            └── ClaudeCodeSubAgent  # Isolated workers (claude -p based)

    PAIAAgent                     # Wraps CodeAgent with omnisanc/guru loop
"""
import asyncio
import logging
import subprocess
import time
import traceback
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
import json
import os

from pydantic import Field, PrivateAttr

# Import llegos Actor model (LGPL-3.0)
# pip install -e /tmp/sanctuary-system/llegos
from llegos import Actor, Message, Object
from enum import Enum


class IngressType(str, Enum):
    """Ingress points for messages into the agent inbox.

    MVP: Only FRONTEND is active. Others stubbed for future.
    """
    FRONTEND = "frontend"      # Active - from http_server.py /send endpoint
    # Stubbed for future:
    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    SYSTEM = "system"          # Internal system events

logger = logging.getLogger(__name__)


# =============================================================================
# MESSAGE TYPES
# =============================================================================

class InboxMessage(Message):
    """Base message for inbox delivery."""
    ingress: IngressType = IngressType.FRONTEND  # Where message came from
    priority: int = 0  # Higher = more urgent
    content: str = ""


class UserPromptMessage(InboxMessage):
    """Message from a user prompt (any ingress point)."""
    ingress: IngressType = IngressType.FRONTEND
    source_id: Optional[str] = None  # Who sent it (discord user id, email, etc.)


class SystemEventMessage(InboxMessage):
    """System-level events (hooks, timers, etc.)."""
    ingress: IngressType = IngressType.SYSTEM
    event_type: str = ""  # hook_fired, timer_tick, etc.
    event_data: Dict[str, Any] = Field(default_factory=dict)


class BlockedMessage(Message):
    """Agent is blocked and needs external input."""
    reason: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)
    blocking_question: Optional[str] = None


class CompletedMessage(Message):
    """Agent completed a task."""
    result: Any = None
    summary: str = ""


# =============================================================================
# CODE AGENT BASE CLASS
# =============================================================================

@dataclass
class CodeAgentConfig:
    """Configuration for a code agent.

    User MUST configure agent_command - this is what gets run in tmux.
    Examples:
        - "claude" (Claude Code)
        - "aider" (Aider)
        - "cursor" (if it had CLI)
        - Any interactive CLI agent
    """
    # REQUIRED: The command to run the agent
    agent_command: str = ""  # User must set this, e.g., "claude"

    # Agent identity
    name: str = "code-agent"
    working_directory: str = field(default_factory=os.getcwd)
    tmux_session: str = "code-agent"  # tmux session name

    # Inbox settings
    inbox_poll_interval: float = 5.0  # seconds
    max_inbox_size: int = 100

    # Response detection (subclass can override)
    response_marker: str = ""  # e.g., "◇" for Claude Code
    poll_interval: float = 0.5
    max_wait_seconds: float = 300.0

    # Persistence
    state_file: Optional[str] = None


class CodeAgent(Actor):
    """Base class for code agents with message inbox.

    This is NOT a PAIA-specific thing - inbox is fundamental to any
    code agent that needs to receive messages from external sources.

    The inbox pattern:
    1. Ingress points (email, discord, etc.) write to inbox
    2. Agent checks inbox on stop hook or poll
    3. Messages processed one-by-one (Actor pattern)
    4. Responses emitted back to appropriate channels

    Subclasses:
    - ClaudeCodeAgent: Uses tmux for interactive sessions
    - ClaudeCodeSubAgent: Uses claude -p for isolated workers
    """

    config: CodeAgentConfig = Field(default_factory=CodeAgentConfig)

    # The actual inbox queue - what llegos describes but doesn't implement
    _inbox: deque = PrivateAttr(default_factory=deque)
    _processing: bool = PrivateAttr(default=False)

    def __init__(self, config: Optional[CodeAgentConfig] = None, **kwargs):
        super().__init__(**kwargs)
        if config:
            self.config = config
        self._inbox = deque(maxlen=self.config.max_inbox_size)
        self._processing = False

        # Load persisted inbox if exists
        if self.config.state_file:
            self._load_inbox()

    # ==================== INBOX OPERATIONS ====================

    def enqueue(self, message: InboxMessage) -> bool:
        """Add message to inbox. Called by ingress points."""
        if len(self._inbox) >= self.config.max_inbox_size:
            self.emit("inbox:overflow", message)
            return False

        self._inbox.append(message)
        self.emit("inbox:enqueued", message)

        # Persist if configured
        if self.config.state_file:
            self._save_inbox()

        return True

    def dequeue(self) -> Optional[InboxMessage]:
        """Remove and return next message from inbox."""
        if not self._inbox:
            return None

        # Sort by priority (higher first), then by created_at (older first)
        sorted_inbox = sorted(
            self._inbox,
            key=lambda m: (-m.priority, m.created_at)
        )

        # Get highest priority message
        message = sorted_inbox[0]
        self._inbox.remove(message)

        self.emit("inbox:dequeued", message)
        return message

    def peek(self) -> Optional[InboxMessage]:
        """Look at next message without removing it."""
        if not self._inbox:
            return None
        sorted_inbox = sorted(
            self._inbox,
            key=lambda m: (-m.priority, m.created_at)
        )
        return sorted_inbox[0]

    @property
    def inbox_count(self) -> int:
        """Number of messages waiting."""
        return len(self._inbox)

    @property
    def has_messages(self) -> bool:
        """Check if inbox has messages."""
        return len(self._inbox) > 0

    # ==================== TMUX CONTROL ====================

    def _run_tmux(self, *args) -> subprocess.CompletedProcess:
        """Run a tmux command."""
        cmd = ["tmux"] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def session_exists(self) -> bool:
        """Check if our tmux session exists."""
        result = self._run_tmux("has-session", "-t", self.config.tmux_session)
        return result.returncode == 0

    def create_session(self) -> bool:
        """Create the tmux session for the agent."""
        if self.session_exists():
            return True
        result = self._run_tmux(
            "new-session", "-d", "-s", self.config.tmux_session,
            "-c", self.config.working_directory
        )
        return result.returncode == 0

    def kill_session(self) -> bool:
        """Kill the tmux session."""
        result = self._run_tmux("kill-session", "-t", self.config.tmux_session)
        return result.returncode == 0

    def spawn_agent(self) -> bool:
        """Spawn the agent inside tmux. Requires config.agent_command."""
        if not self.config.agent_command:
            raise RuntimeError("agent_command not configured")
        if not self.session_exists():
            if not self.create_session():
                return False
        result = self._run_tmux(
            "send-keys", "-t", self.config.tmux_session,
            self.config.agent_command, "Enter"
        )
        return result.returncode == 0

    def send_keys(self, *sequence) -> bool:
        """Send key sequence. Items can be str (keys) or float (sleep)."""
        for item in sequence:
            if isinstance(item, (int, float)):
                time.sleep(item)
            else:
                result = self._run_tmux("send-keys", "-t", self.config.tmux_session, item)
                if result.returncode != 0:
                    return False
        return True

    def capture_pane(self, history_limit: int = 5000) -> str:
        """Capture current pane content."""
        result = self._run_tmux(
            "capture-pane", "-t", self.config.tmux_session,
            "-p", "-S", f"-{history_limit}"
        )
        return result.stdout if result.returncode == 0 else ""

    def send_and_wait(self, prompt: str, timeout: Optional[float] = None) -> str:
        """Send prompt and wait for response (detected by response_marker)."""
        timeout = timeout or self.config.max_wait_seconds
        before = self.capture_pane()
        before_lines = len(before.splitlines())

        self.send_keys(prompt, "Enter")

        start_time = time.time()
        last_content = before
        stable_count = 0

        while time.time() - start_time < timeout:
            time.sleep(self.config.poll_interval)
            current = self.capture_pane()
            if current == last_content:
                stable_count += 1
                if stable_count >= 3 and self.config.response_marker and self.config.response_marker in current:
                    break
            else:
                stable_count = 0
                last_content = current

        after_lines = self.capture_pane().splitlines()
        response_lines = after_lines[before_lines:]
        cleaned = []
        for line in response_lines:
            if self.config.response_marker and line.strip().startswith(self.config.response_marker):
                break
            cleaned.append(line)
        return "\n".join(cleaned)

    # ==================== INBOX PROCESSING ====================

    def check_inbox(self) -> List[Message]:
        """Check inbox and process all pending messages.

        Called by:
        - Stop hook (when agent finishes a task)
        - Poll timer (periodic check)
        - External trigger (harness says "check now")

        Returns list of response messages.
        """
        if self._processing:
            return []  # Prevent re-entry

        self._processing = True
        responses = []

        try:
            while self.has_messages:
                message = self.dequeue()
                if message:
                    # Use Actor's receive() which calls receive_{intent}
                    for response in self.receive(message):
                        responses.append(response)
        finally:
            self._processing = False

        return responses

    def process_one(self) -> Optional[Message]:
        """Process single message from inbox. Returns response if any."""
        message = self.dequeue()
        if not message:
            return None

        responses = list(self.receive(message))
        return responses[0] if responses else None

    # ==================== MESSAGE HANDLERS ====================
    # Subclasses override these with actual implementations

    def receive_user_prompt_message(self, message: UserPromptMessage) -> Iterator[Message]:
        """Handle user prompt from any ingress point.

        Subclasses should override to actually process the prompt.
        """
        self.emit("user_prompt:received", message)
        # Default: just acknowledge
        yield CompletedMessage(
            sender=self,
            receiver=message.sender,
            parent=message,
            summary=f"Received prompt from {message.ingress}"
        )

    def receive_system_event_message(self, message: SystemEventMessage) -> Iterator[Message]:
        """Handle system events (hooks, timers, etc.)."""
        self.emit("system_event:received", message)
        # Default: log and continue
        yield from []

    def receive_inbox_message(self, message: InboxMessage) -> Iterator[Message]:
        """Generic inbox message handler."""
        self.emit("inbox:received", message)
        yield from []

    # ==================== PERSISTENCE ====================

    def _save_inbox(self):
        """Persist inbox to disk."""
        if not self.config.state_file:
            return

        path = Path(self.config.state_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "agent_id": self.id,
            "saved_at": datetime.utcnow().isoformat(),
            "messages": [m.model_dump() for m in self._inbox]
        }
        path.write_text(json.dumps(data, indent=2, default=str))

    def _load_inbox(self):
        """Load inbox from disk."""
        if not self.config.state_file:
            return

        path = Path(self.config.state_file)
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())
            for msg_data in data.get("messages", []):
                # Reconstruct message (simplified - real impl needs type registry)
                msg = InboxMessage(**msg_data)
                self._inbox.append(msg)
            logger.info(f"Loaded {len(self._inbox)} messages from inbox")
            self.emit("inbox:loaded", {"count": len(self._inbox)})
        except Exception as e:
            logger.error(f"Failed to load inbox: {e}\n{traceback.format_exc()}")
            self.emit("inbox:load_error", {"error": str(e), "traceback": traceback.format_exc()})

    # ==================== LIFECYCLE ====================

    def start(self):
        """Start the agent. Subclasses override for specific startup."""
        self.emit("agent:starting", {"agent_id": self.id})

    def stop(self):
        """Stop the agent. Process remaining inbox, persist state."""
        self.emit("agent:stopping", {"agent_id": self.id})

        # Process any remaining messages
        self.check_inbox()

        # Persist inbox
        if self.config.state_file:
            self._save_inbox()

    async def run_poll_loop(self):
        """Async loop that periodically checks inbox."""
        while True:
            await asyncio.sleep(self.config.inbox_poll_interval)
            self.check_inbox()


# =============================================================================
# INGRESS POINT HELPERS
# =============================================================================

def create_user_message(
    content: str,
    ingress: IngressType = IngressType.FRONTEND,
    source_id: Optional[str] = None,
    priority: int = 0
) -> UserPromptMessage:
    """Helper to create user prompt messages from any ingress."""
    return UserPromptMessage(
        content=content,
        ingress=ingress,
        source_id=source_id,
        priority=priority
    )


def create_system_event(
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None,
    priority: int = 0
) -> SystemEventMessage:
    """Helper to create system event messages."""
    return SystemEventMessage(
        event_type=event_type,
        event_data=event_data or {},
        priority=priority
    )


# =============================================================================
# CLAUDE CODE AGENT
# =============================================================================

@dataclass
class ClaudeCodeAgentConfig(CodeAgentConfig):
    """Config for Claude Code agent - just sets Claude-specific defaults."""
    tmux_session: str = "claude"
    response_marker: str = "◇"  # Claude Code input prompt marker


class ClaudeCodeAgent(CodeAgent):
    """CodeAgent configured for Claude Code.

    This just sets Claude-specific defaults (response marker).
    The actual command comes from user settings.
    """
    config: ClaudeCodeAgentConfig = Field(default_factory=ClaudeCodeAgentConfig)

    def __init__(self, config: Optional[ClaudeCodeAgentConfig] = None, **kwargs):
        super().__init__(config=config or ClaudeCodeAgentConfig(), **kwargs)


# =============================================================================
# OMNISANC STATE
# =============================================================================

OMNISANC_STATE_FILE = Path("/tmp/heaven_data/omnisanc_core/.course_state")


@dataclass
class OmnisancState:
    """Reflects omnisanc state from the state file.

    The agent HAS this state - harness routes events, agent owns state.
    """
    course_plotted: bool = False
    fly_called: bool = False
    flight_selected: bool = False
    session_active: bool = False
    needs_review: bool = False
    mission_active: bool = False
    # Additional context
    waypoint_step: int = 0
    last_oriented: Optional[str] = None
    domain: str = "HOME"

    @classmethod
    def load(cls) -> "OmnisancState":
        """Load state from file."""
        if not OMNISANC_STATE_FILE.exists():
            return cls()
        try:
            data = json.loads(OMNISANC_STATE_FILE.read_text())
            return cls(
                course_plotted=data.get("course_plotted", False),
                fly_called=data.get("fly_called", False),
                flight_selected=data.get("flight_selected", False),
                session_active=data.get("session_active", False),
                needs_review=data.get("needs_review", False),
                mission_active=data.get("mission_active", False),
                waypoint_step=data.get("waypoint_step", 0),
                last_oriented=data.get("last_oriented"),
                domain=data.get("domain", "HOME"),
            )
        except Exception:
            return cls()

    @property
    def zone(self) -> str:
        """Infer current zone from state flags.

        Flow: HOME → STARPORT → LAUNCH → SESSION → LANDING → STARPORT → ... → HOME

        Zones determined by omnisanc enforcement conditions:
        - HOME: course_plotted = false
        - STARPORT: course_plotted but fly not called yet
        - LAUNCH: fly called but flight not selected (waypoint not started)
        - SESSION: flight_selected and session_active
        - LANDING: needs_review = true (3-step end sequence)
        - MISSION: mission_active but not in active session (between sessions)
        """
        if not self.course_plotted:
            return "HOME"
        elif self.needs_review:
            return "LANDING"
        elif self.mission_active and not self.session_active and self.flight_selected:
            return "MISSION"
        elif not self.fly_called:
            return "STARPORT"
        elif not self.flight_selected:
            return "LAUNCH"
        elif self.session_active:
            return "SESSION"
        else:
            return "STARPORT"  # Back at starport after session

    def to_dict(self) -> dict:
        return {
            "zone": self.zone,  # Computed from flags
            "course_plotted": self.course_plotted,
            "fly_called": self.fly_called,
            "flight_selected": self.flight_selected,
            "session_active": self.session_active,
            "needs_review": self.needs_review,
            "mission_active": self.mission_active,
            "waypoint_step": self.waypoint_step,
        }


# =============================================================================
# PAIA AGENT
# =============================================================================

class PAIAAgent(ClaudeCodeAgent):
    """ClaudeCodeAgent wrapped with omnisanc/guru loop.

    This is the full PAIA - the agent that:
    - HAS omnisanc state (Home/Journey mode)
    - Can run guru loops (bodhisattva vow)
    - Receives events from harness
    """

    _omnisanc: OmnisancState = PrivateAttr(default=None)

    def __init__(self, config: Optional[ClaudeCodeAgentConfig] = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self._omnisanc = OmnisancState.load()

    @property
    def omnisanc(self) -> OmnisancState:
        """Get current omnisanc state (refreshes from file)."""
        self._omnisanc = OmnisancState.load()
        return self._omnisanc

    @property
    def in_journey_mode(self) -> bool:
        """Check if agent is in journey mode (has active course)."""
        return self.omnisanc.course_plotted

    @property
    def in_home_mode(self) -> bool:
        """Check if agent is in home mode (no active course)."""
        return not self.omnisanc.course_plotted
