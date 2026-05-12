"""HTTP Server for harness control - Railgun talks to this.

Endpoints:
- POST /spawn - Start agent with harness
- GET /status - Get harness/agent status
- POST /send - Send prompt to agent
- POST /inject - Inject event into agent
- GET /events - SSE stream of detected events (block reports, giint, etc)
"""
import asyncio
import json
import logging
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.harness import PAIAHarness, HarnessConfig
from ..core.hook_control import HookControl, HookType, ALL_HOOKS
from ..core.persona_control import PersonaControl
from ..core.self_command_generator import (
    SelfCommandGenerator, RestartConfig, CompactConfig, InjectConfig
)

logger = logging.getLogger(__name__)

# Global harness instance
_harness: Optional[PAIAHarness] = None
_event_queue: asyncio.Queue = None


def get_harness() -> PAIAHarness:
    global _harness
    if _harness is None:
        _harness = PAIAHarness()
        _harness.on_event(event_callback)  # Register SSE callback immediately
    return _harness


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    global _event_queue
    _event_queue = asyncio.Queue()
    yield
    # Cleanup
    if _harness:
        _harness.stop()


app = FastAPI(title="PAIA Harness", lifespan=lifespan)


# ==================== MODELS ====================

class SpawnRequest(BaseModel):
    agent_command: str = "claude"
    working_directory: str = "/home/GOD"
    psyche_config: str = "default"
    world_config: str = "default"


class SendRequest(BaseModel):
    prompt: str
    timeout: Optional[float] = None


class InjectRequest(BaseModel):
    domain: str  # psyche, world, system
    message: str


# ==================== EVENT HANDLING ====================

def event_callback(event):
    """Called by harness when events detected. Pushes to SSE queue."""
    if _event_queue:
        try:
            _event_queue.put_nowait({
                "type": event.event_type.value,
                "content": event.content,
                "metadata": event.metadata
            })
        except asyncio.QueueFull:
            pass  # Drop if queue full


async def event_generator():
    """SSE generator - yields events as they come in."""
    while True:
        try:
            event = await asyncio.wait_for(_event_queue.get(), timeout=30.0)
            yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            # Send keepalive
            yield f": keepalive\n\n"


# ==================== ENDPOINTS ====================

@app.post("/spawn")
async def spawn_agent(req: SpawnRequest):
    """Spawn a new agent with harness."""
    harness = get_harness()

    # Configure
    harness.config.agent_command = req.agent_command
    harness.config.working_directory = req.working_directory

    # Register event callback for SSE
    harness.on_event(event_callback)

    # Start
    harness.start()

    return {
        "status": "spawned",
        "session": harness.config.tmux_session,
        "agent": req.agent_command
    }


@app.get("/status")
async def get_status():
    """Get harness status."""
    harness = get_harness()

    return {
        "running": harness.running,
        "session_exists": harness.session_exists(),
        "session": harness.config.tmux_session,
        "agent_command": harness.config.agent_command
    }


@app.post("/send")
async def send_to_agent(req: SendRequest):
    """Send prompt to agent and get response."""
    harness = get_harness()

    if not harness.session_exists():
        return {"error": "Agent not running. Call /spawn first."}

    # Run in thread to not block
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: harness.send_and_wait(req.prompt, req.timeout)
    )

    return {
        "response": response,
        "prompt": req.prompt
    }


@app.post("/inject")
async def inject_event(req: InjectRequest):
    """Manually inject an event/message."""
    harness = get_harness()

    harness.inject([f"[{req.domain.upper()}]: {req.message}"])

    return {"injected": True, "domain": req.domain, "message": req.message}


@app.get("/events")
async def events_stream(request: Request):
    """SSE stream of detected events.

    Railgun connects here to get real-time:
    - Block reports
    - GIINT responses
    - CogLog entries
    - SkillLog predictions
    - Context warnings
    - Errors
    """
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/omnisanc")
async def get_omnisanc_state():
    """Get current omnisanc state."""
    from ..core.harness import OmnisancState
    state = OmnisancState.load()
    return state.to_dict()


@app.get("/capture")
async def capture_terminal():
    """Get current terminal content (for debugging)."""
    harness = get_harness()
    content = harness.capture_pane(history_limit=500)
    return {"content": content, "lines": len(content.splitlines())}


@app.post("/stop")
async def stop_harness():
    """Stop the harness and optionally kill agent."""
    harness = get_harness()
    harness.stop()
    return {"stopped": True}


# ==================== HOOK EVENTS (from Claude hooks) ====================

class HookEventRequest(BaseModel):
    event: str
    data: dict
    ts: float


@app.post("/hook/{event_type}")
async def receive_hook_event(event_type: str, req: HookEventRequest):
    """Receive event from Claude hook, return decision.

    This is where the harness decides: continue | block | inject context.
    """
    start = time.time()

    # Log the event
    tool_name = req.data.get("tool_name", "unknown")

    # TODO: Add actual decision logic here based on game state
    # For now, just continue and report latency

    return {
        "result": "continue",
        "event": event_type,
        "tool": tool_name,
        "harness_latency_ms": (time.time() - start) * 1000
    }


# ==================== HOOK CONTROL ====================

@app.get("/hooks")
async def get_hooks():
    """Get all hook states."""
    return HookControl.get_all()


@app.post("/hooks/{hook_type}/enable")
async def enable_hook(hook_type: str):
    """Enable a specific hook."""
    if hook_type not in ALL_HOOKS:
        return {"error": f"Unknown hook type: {hook_type}", "valid": ALL_HOOKS}
    HookControl.enable(hook_type)
    return {"hook": hook_type, "enabled": True}


@app.post("/hooks/{hook_type}/disable")
async def disable_hook(hook_type: str):
    """Disable a specific hook."""
    if hook_type not in ALL_HOOKS:
        return {"error": f"Unknown hook type: {hook_type}", "valid": ALL_HOOKS}
    HookControl.disable(hook_type)
    return {"hook": hook_type, "enabled": False}


@app.post("/hooks/{hook_type}/toggle")
async def toggle_hook(hook_type: str):
    """Toggle a specific hook."""
    if hook_type not in ALL_HOOKS:
        return {"error": f"Unknown hook type: {hook_type}", "valid": ALL_HOOKS}
    new_state = HookControl.toggle(hook_type)
    return {"hook": hook_type, "enabled": new_state}


# ==================== PERSONA CONTROL ====================

@app.get("/persona")
async def get_persona():
    """Get currently active persona."""
    return {
        "active": PersonaControl.is_active(),
        "persona": PersonaControl.get_active()
    }


@app.post("/persona/{name}")
async def activate_persona(name: str):
    """Activate a persona."""
    PersonaControl.activate(name)
    return {"persona": name, "activated": True}


@app.delete("/persona")
async def deactivate_persona():
    """Deactivate current persona."""
    PersonaControl.deactivate()
    return {"deactivated": True}


# ==================== SELF COMMANDS ====================

class RestartRequest(BaseModel):
    tmux_session: str = "claude"
    autopoiesis: bool = False
    resume_enabled: bool = True
    post_restart_message: str = "ALIVE! Hot restart complete."


class CompactRequest(BaseModel):
    tmux_session: str = "claude"
    pre_compact_message: str = ""
    post_compact_message: str = ""


class InjectMessageRequest(BaseModel):
    tmux_session: str = "claude"
    message: str
    press_enter: bool = True


@app.post("/self/restart")
async def self_restart(req: RestartRequest):
    """Execute restart with config."""
    config = RestartConfig(
        tmux_session=req.tmux_session,
        autopoiesis=req.autopoiesis,
        resume_enabled=req.resume_enabled,
        post_restart_message=req.post_restart_message,
    )
    SelfCommandGenerator.execute_restart(config)
    return {"scheduled": True, "config": req.model_dump()}


@app.post("/self/compact")
async def self_compact(req: CompactRequest):
    """Execute compact with config."""
    config = CompactConfig(
        tmux_session=req.tmux_session,
        pre_compact_message=req.pre_compact_message,
        post_compact_message=req.post_compact_message,
    )
    success = SelfCommandGenerator.execute_compact(config)
    return {"success": success, "config": req.model_dump()}


@app.post("/self/inject")
async def self_inject(req: InjectMessageRequest):
    """Inject message into tmux session."""
    config = InjectConfig(
        tmux_session=req.tmux_session,
        message=req.message,
        press_enter=req.press_enter,
    )
    success = SelfCommandGenerator.execute_inject(config)
    return {"success": success, "message": req.message}


# ==================== CAVE ENDPOINTS (Business/Funnels) ====================

@app.get("/cave/list")
async def cave_list():
    """List cave projects/funnels."""
    return {"items": [], "count": 0}


@app.get("/cave/status")
async def cave_status():
    """Get cave domain status."""
    return {"active": False, "current_project": None}


@app.get("/cave/offers")
async def cave_offers():
    """List cave offers."""
    return {"offers": [], "count": 0}


@app.get("/cave/journeys")
async def cave_journeys():
    """List cave customer journeys."""
    return {"journeys": [], "count": 0}


# ==================== SANCTUM ENDPOINTS (Life Architecture) ====================

@app.get("/sanctum/list")
async def sanctum_list():
    """List sanctum items."""
    return {"items": [], "count": 0}


@app.get("/sanctum/status")
async def sanctum_status():
    """Get sanctum domain status."""
    return {"active": False, "current_ritual": None}


@app.get("/sanctum/rituals")
async def sanctum_rituals():
    """List sanctum rituals."""
    return {"rituals": [], "count": 0}


@app.get("/sanctum/goals")
async def sanctum_goals():
    """List sanctum goals."""
    return {"goals": [], "count": 0}


# Run with: uvicorn game_wrapper.server.http_server:app --reload
