"""Sanctuary Revolution HTTP Server — extends CAVE.

This server imports CAVE's FastAPI app (which provides all runtime control
endpoints: configs, loops, DNA, modules, hooks, omnisanc, metabrainhook,
PAIA mode, live mirror, remote agents, SSE, health) and adds sancrev-specific
domain endpoints on top: GEAR events, domain builders (CAVE/SANCTUM/PAIAB),
agent registry, llegos messaging, persona control, self commands, code execution,
and Claude control.

Run with: uvicorn sanctuary_revolution.harness.server.http_server:app --reload
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel

# === CAVE base — imports the app with all CAVE routes + CAVEAgent startup ===
from cave.server.http_server import app, cave

# === Sancrev-specific core ===
from ..core.persona_control import PersonaControl

# llegos-based agent messaging
from ..core.agent import (
    CodeAgent, InboxMessage, UserPromptMessage, SystemEventMessage,
    BlockedMessage, CompletedMessage, IngressType,
    create_user_message, create_system_event
)
from llegos import Message
from llegos.llegos import message_chain, message_list

# Domain builders
from cave_builder import CAVEBuilder
from sanctum_builder import SANCTUMBuilder
from paia_builder.core import PAIABuilder

logger = logging.getLogger(__name__)

# Heartbeat loop (REMOVED: now handled by CAVE Heart organ in anatomy.py)
# from .heartbeat_loop import heartbeat_loop

# CORS for browser access (CAVE doesn't add this by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Sancrev globals ===
_event_queue: asyncio.Queue = asyncio.Queue()
print(f"[SSE-DEBUG] _event_queue created at module level, id={id(_event_queue)}", flush=True)

# Domain builder instances
_cave_builder: Optional[CAVEBuilder] = None
_sanctum_builder: Optional[SANCTUMBuilder] = None
_paiab_builder: Optional[PAIABuilder] = None


def get_cave_builder() -> CAVEBuilder:
    global _cave_builder
    if _cave_builder is None:
        _cave_builder = CAVEBuilder()
    return _cave_builder


def get_sanctum_builder() -> SANCTUMBuilder:
    global _sanctum_builder
    if _sanctum_builder is None:
        _sanctum_builder = SANCTUMBuilder()
    return _sanctum_builder


def get_paiab_builder() -> PAIABuilder:
    global _paiab_builder
    if _paiab_builder is None:
        _paiab_builder = PAIABuilder()
    return _paiab_builder


# ==================== HEARTBEAT ====================
# Heartbeat prompt injection is handled by CAVE Heart organ (anatomy.py).
# The Heart's "heartbeat_prompt" Tick fires on interval, checks user-active lock,
# and sends prompts to Claude Code via tmux send_keys.
# Old standalone heartbeat_loop removed — it only logged, never sent prompts.


# ==================== MODELS ====================

class GenericEventRequest(BaseModel):
    """Generic event for treeshell -> SSE -> frontend."""
    event_type: str
    data: dict = {}
    paia_name: Optional[str] = None
    message: Optional[str] = None


# ==================== SANCREV EVENT PUSH ====================

@app.post("/event")
async def push_event(req: GenericEventRequest):
    """Push generic event to SSE stream -> frontend.

    TreeShell calls this when game actions happen:
    - journey_created, journey_completed
    - mvs_created, mvs_viable
    - vec_created, vec_deployed
    - level_up, xp_gained
    """
    from datetime import datetime

    event_data = {
        "type": req.event_type,
        "data": req.data,
        "paia_name": req.paia_name,
        "message": req.message or f"Event: {req.event_type}",
        "timestamp": datetime.now().isoformat()
    }

    if _event_queue:
        try:
            _event_queue.put_nowait(event_data)
            return {"success": True, "event_type": req.event_type}
        except asyncio.QueueFull:
            return {"success": False, "error": "Event queue full"}

    return {"success": False, "error": "Event queue not initialized"}


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


# ==================== GEAR EVENTS (Bidirectional Bus) ====================

from ..events.gear_events import (
    GEAREventType, GEARDimensionType,
    AcceptanceEvent, GEARProofHandler,
    emit_gear_state, parse_acceptance_event
)

# PAIA store - JSON file persistence
HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
PAIA_STORE_FILE = HEAVEN_DATA_DIR / "paia_store.json"


def _ensure_store_dir():
    """Ensure storage directory exists."""
    HEAVEN_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_paia_store() -> dict:
    """Load all PAIAs from JSON file."""
    if not PAIA_STORE_FILE.exists():
        return {}
    try:
        return json.loads(PAIA_STORE_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {}


def _save_paia_store(store: dict):
    """Save all PAIAs to JSON file."""
    _ensure_store_dir()
    PAIA_STORE_FILE.write_text(json.dumps(store, indent=2, default=str))


def get_paia(name: str):
    """Get PAIA from JSON store."""
    store = _load_paia_store()
    paia_data = store.get(name)
    if not paia_data:
        return None
    try:
        from paia_builder.models import PAIA
        return PAIA.model_validate(paia_data)
    except Exception:
        return None


def set_paia(name: str, paia):
    """Store PAIA in JSON file."""
    store = _load_paia_store()
    store[name] = paia.model_dump(mode='json')
    _save_paia_store(store)


# Initialize proof handler
_proof_handler = GEARProofHandler(paia_store=get_paia)


class GEARAcceptRequest(BaseModel):
    """Frontend acceptance event."""
    event_type: str
    paia_name: str
    component_type: Optional[str] = None
    component_name: Optional[str] = None
    dimension: Optional[str] = None
    proof_note: Optional[str] = None
    accepted: bool = True


class GEARStateRequest(BaseModel):
    """Request to emit GEAR state."""
    paia_name: str


@app.post("/gear/accept")
async def accept_gear_proof(req: GEARAcceptRequest):
    """Receive acceptance event from frontend -> update GEAR proof."""
    try:
        event = AcceptanceEvent(
            event_type=GEAREventType(req.event_type),
            paia_name=req.paia_name,
            component_type=req.component_type,
            component_name=req.component_name,
            dimension=GEARDimensionType(req.dimension) if req.dimension else None,
            proof_note=req.proof_note,
            accepted=req.accepted,
        )
        success = _proof_handler.handle(event)
        return {"success": success, "event_type": req.event_type, "paia": req.paia_name}
    except ValueError as e:
        return {"success": False, "error": str(e)}


@app.post("/gear/emit")
async def emit_gear(req: GEARStateRequest):
    """Emit current GEAR state to SSE for frontend to receive."""
    paia = get_paia(req.paia_name)
    if not paia:
        return {"success": False, "error": f"PAIA '{req.paia_name}' not found"}

    # Use CAVE's event system
    emit_gear_state(cave.router if hasattr(cave, 'router') else None, req.paia_name, paia.gear_state)
    return {"success": True, "emitted": req.paia_name}


@app.get("/gear/{paia_name}")
async def get_gear_state(paia_name: str):
    """Get current GEAR state for a PAIA."""
    paia = get_paia(paia_name)
    if not paia:
        return {"error": f"PAIA '{paia_name}' not found"}

    gs = paia.gear_state
    return {
        "paia_name": paia_name,
        "level": gs.level,
        "phase": gs.phase.value if hasattr(gs.phase, 'value') else str(gs.phase),
        "total_points": gs.total_points,
        "overall": gs.overall,
        "dimensions": {
            "gear": {"score": gs.gear.score, "notes": gs.gear.notes[-5:]},
            "experience": {"score": gs.experience.score, "notes": gs.experience.notes[-5:]},
            "achievements": {"score": gs.achievements.score, "notes": gs.achievements.notes[-5:]},
            "reality": {"score": gs.reality.score, "notes": gs.reality.notes[-5:]},
        }
    }


@app.post("/gear/register")
async def register_paia(paia_data: dict):
    """Register a PAIA for GEAR tracking."""
    try:
        from paia_builder.models import PAIA
        paia = PAIA.model_validate(paia_data)
        set_paia(paia.name, paia)
        return {"success": True, "registered": paia.name}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/gear/list")
async def list_registered_paias():
    """List all registered PAIAs."""
    store = _load_paia_store()
    return {"paias": list(store.keys()), "count": len(store)}


# ==================== CAVE ENDPOINTS (Business/Funnels) ====================

@app.get("/cave/list")
async def cave_list():
    """List cave projects/funnels."""
    builder = get_cave_builder()
    caves = builder.list_caves()
    return {"items": caves, "count": len(caves)}

@app.get("/cave/status")
async def cave_status():
    """Get cave domain status."""
    builder = get_cave_builder()
    current = builder.which()
    if current == "No CAVE selected":
        return {"active": False, "current_project": None}
    return {"active": True, "current_project": current, "status": builder.status()}

@app.get("/cave/offers")
async def cave_offers():
    """List cave offers."""
    builder = get_cave_builder()
    try:
        offers = builder.list_offers()
        return {"offers": offers, "count": len(offers)}
    except ValueError:
        return {"offers": [], "count": 0, "error": "No CAVE selected"}

@app.get("/cave/journeys")
async def cave_journeys():
    """List cave customer journeys."""
    builder = get_cave_builder()
    try:
        journeys = builder.list_journeys()
        return {"journeys": journeys, "count": len(journeys)}
    except ValueError:
        return {"journeys": [], "count": 0, "error": "No CAVE selected"}


# ==================== SANCTUM ENDPOINTS (Life Architecture) ====================

@app.get("/sanctum/list")
async def sanctum_list():
    """List sanctum items."""
    builder = get_sanctum_builder()
    sanctums = builder.list_sanctums()
    return {"items": sanctums, "count": len(sanctums)}

@app.get("/sanctum/status")
async def sanctum_status():
    """Get sanctum domain status."""
    builder = get_sanctum_builder()
    current = builder.which()
    if "[HIEL]" in current:
        return {"active": False, "current_sanctum": None}
    return {"active": True, "current_sanctum": current, "status": builder.status()}

@app.get("/sanctum/rituals")
async def sanctum_rituals():
    """List sanctum rituals."""
    builder = get_sanctum_builder()
    try:
        sanctum = builder._ensure_current()
        rituals = [{"name": r.name, "domain": r.domain.value, "frequency": r.frequency.value}
                   for r in sanctum.rituals]
        return {"rituals": rituals, "count": len(rituals)}
    except ValueError:
        return {"rituals": [], "count": 0, "error": "No SANCTUM selected"}

@app.get("/sanctum/goals")
async def sanctum_goals():
    """List sanctum goals."""
    builder = get_sanctum_builder()
    try:
        sanctum = builder._ensure_current()
        goals = [{"name": g.name, "domain": g.domain.value, "progress": g.progress}
                 for g in sanctum.goals]
        return {"goals": goals, "count": len(goals)}
    except ValueError:
        return {"goals": [], "count": 0, "error": "No SANCTUM selected"}


# --- Sanctum Ritual ↔ Canopy Bridge ---

@app.post("/sanctum/ritual/populate")
async def populate_rituals():
    """Populate Canopy items for all due sanctum rituals."""
    from cave.core import sanctum_canopy
    result = await sanctum_canopy.populate_all_due_rituals()
    return result


@app.post("/sanctum/ritual/complete")
async def complete_ritual_endpoint(data: Dict[str, Any]):
    """Mark a sanctum ritual complete via Canopy. Auto-populates if not yet in today's map."""
    from cave.core import sanctum_canopy
    from datetime import datetime

    ritual_name = data.get("ritual_name", "")
    source = data.get("source", "unknown")
    if not ritual_name:
        return {"status": "error", "error": "ritual_name required"}

    # Auto-populate if ritual not in today's map yet
    status = sanctum_canopy.get_ritual_status()
    if ritual_name not in status["rituals"]:
        sanctum_name = sanctum_canopy._get_active_sanctum_name()
        if sanctum_name:
            sanctum_data = sanctum_canopy._load_sanctum(sanctum_name)
            if sanctum_data:
                for r in sanctum_data.get("rituals", []):
                    if r["name"] == ritual_name:
                        await sanctum_canopy.populate_ritual(ritual_name, r.get("description", ""))
                        break

    result = await sanctum_canopy.complete_ritual(ritual_name)

    # Discord confirmation
    status_val = result.get("status")
    if status_val in ("completed", "already_completed"):
        from cave.core.channel import UserDiscordChannel
        discord = UserDiscordChannel()
        if discord.token and discord.channel_id:
            now = datetime.now().strftime("%H:%M")
            if status_val == "completed":
                streak = result.get("streak", 0)
                msg = f"done {ritual_name} at {now} (streak: {streak})"
            else:
                msg = f"{ritual_name} already done today"
            try:
                discord.deliver({"message": msg})
            except Exception:
                pass  # best-effort confirmation
    return result


@app.get("/sanctum/ritual/status")
def get_ritual_completion_status():
    """Get today's ritual completion status from the Canopy map."""
    from cave.core import sanctum_canopy
    return sanctum_canopy.get_ritual_status()


# ==================== AUTOMATIONS (CAVE Core) ====================

class AddAutomationRequest(BaseModel):
    """Request to add an automation."""
    name: str
    description: str = ""
    schedule: Optional[str] = None
    prompt_template: Optional[str] = None
    code_pointer: Optional[str] = None
    channels: Optional[List[Dict[str, Any]]] = None
    priority: int = 5
    tags: Optional[List[str]] = None


class FireAutomationRequest(BaseModel):
    """Request to fire an automation with optional extra variables."""
    extra_vars: Optional[Dict[str, Any]] = None


def _build_channels(channel_specs: Optional[List[Dict[str, Any]]]) -> list:
    """Build Channel objects from request specs.

    Each spec is a dict with "type" key and type-specific fields:
    - {"type": "user.discord", "channel_id": "...", "guild_id": "...", "token": "..."}
    - {"type": "agent.inbox", "inbox_dir": "/path/to/inbox"}
    - {"type": "agent.tmux", "session": "claude"}
    """
    if not channel_specs:
        return []

    from cave.core.channel import (
        UserDiscordChannel, AgentInboxChannel, AgentTmuxChannel,
    )

    channels = []
    for spec in channel_specs:
        ch_type = spec.get("type", "")
        if ch_type == "user.discord":
            channels.append(UserDiscordChannel(
                channel_id=spec.get("channel_id", ""),
                guild_id=spec.get("guild_id", ""),
                token=spec.get("token", ""),
            ))
        elif ch_type == "agent.inbox":
            channels.append(AgentInboxChannel(
                inbox_dir=Path(spec["inbox_dir"]) if "inbox_dir" in spec else Path("/tmp/heaven_data/inbox"),
            ))
        elif ch_type == "agent.tmux":
            channels.append(AgentTmuxChannel(
                session=spec.get("session", "claude"),
            ))
        else:
            logger.warning(f"Unknown channel type: {ch_type}")
    return channels


@app.get("/automations")
async def list_automations():
    """List all automations with status."""
    return cave.get_automation_status()


@app.post("/automations")
async def add_automation(req: AddAutomationRequest):
    """Add a new automation with optional channel delivery targets."""
    channels = _build_channels(req.channels)
    return cave.add_automation(
        name=req.name,
        description=req.description,
        schedule=req.schedule,
        prompt_template=req.prompt_template,
        code_pointer=req.code_pointer,
        channels=channels,
        priority=req.priority,
        tags=req.tags,
    )


@app.post("/automations/fire_due")
async def fire_all_due():
    """Fire all automations that are due (called by Heart on rhythm)."""
    results = cave.fire_all_due()
    return {"results": results, "count": len(results)}


@app.post("/automations/{name}/fire")
async def fire_automation(name: str, req: FireAutomationRequest = None):
    """Fire a specific automation by name."""
    extra_vars = req.extra_vars if req else None
    return cave.fire_automation(name, extra_vars)


@app.delete("/automations/{name}")
async def remove_automation(name: str):
    """Remove an automation by name."""
    return cave.remove_automation(name)


# ==================== PAIAB ENDPOINTS (AI Agent Building) ====================

class NewPAIARequest(BaseModel):
    name: str
    description: str
    git_dir: Optional[str] = None
    source_dir: Optional[str] = None
    init_giint: bool = True

class ForkPAIARequest(BaseModel):
    source_name: str
    new_name: str
    fork_type: str = "child"
    description: Optional[str] = None
    git_dir: Optional[str] = None
    init_giint: bool = True

class TickVersionRequest(BaseModel):
    new_version: str
    new_description: Optional[str] = None

class AddSkillRequest(BaseModel):
    name: str
    domain: str
    category: str
    description: str

class AddMCPRequest(BaseModel):
    name: str
    description: str

class AddHookRequest(BaseModel):
    name: str
    hook_type: str
    description: str

class AddCommandRequest(BaseModel):
    name: str
    description: str
    argument_hint: Optional[str] = None

class AddAgentRequest(BaseModel):
    name: str
    description: str

class AddPersonaRequest(BaseModel):
    name: str
    domain: str
    description: str
    frame: str

class AddPluginRequest(BaseModel):
    name: str
    description: str
    git_url: Optional[str] = None

class AddFlightRequest(BaseModel):
    name: str
    domain: str
    description: str

class AddMetastackRequest(BaseModel):
    name: str
    domain: str
    description: str

class AdvanceTierRequest(BaseModel):
    comp_type: str
    name: str
    fulfillment: str

class SetTierRequest(BaseModel):
    comp_type: str
    name: str
    tier: str
    note: Optional[str] = None

class GoldifyRequest(BaseModel):
    comp_type: str
    name: str
    note: Optional[str] = None

class RegressGoldenRequest(BaseModel):
    comp_type: str
    name: str
    reason: str

class UpdateGEARRequest(BaseModel):
    dimension: str
    score: int
    note: Optional[str] = None

class SetSkillMdRequest(BaseModel):
    skill_name: str
    content: str

class SetSkillReferenceRequest(BaseModel):
    skill_name: str
    content: str

class AddSkillResourceRequest(BaseModel):
    skill_name: str
    filename: str
    content: str
    content_type: str = "markdown"

class SetMCPServerRequest(BaseModel):
    mcp_name: str
    content: str

class AddMCPToolRequest(BaseModel):
    mcp_name: str
    core_function: str
    ai_description: Optional[str] = None

class SetHookScriptRequest(BaseModel):
    hook_name: str
    content: str

class SetCommandPromptRequest(BaseModel):
    cmd_name: str
    content: str

class SetAgentPromptRequest(BaseModel):
    agent_name: str
    content: str

class SetPersonaFrameRequest(BaseModel):
    persona_name: str
    content: str

class AddFlightStepRequest(BaseModel):
    flight_name: str
    step_number: int
    title: str
    instruction: str
    skills_to_equip: Optional[List[str]] = None

class AddMetastackFieldRequest(BaseModel):
    metastack_name: str
    field_name: str
    field_type: str
    description: Optional[str] = None
    default: Optional[str] = None


# --- PAIAB Management ---

@app.get("/paiab/list")
async def paiab_list():
    builder = get_paiab_builder()
    paias = builder.list_paias()
    return {"items": paias, "count": len(paias)}

@app.get("/paiab/status")
async def paiab_status():
    builder = get_paiab_builder()
    try:
        status = builder.status()
        which = builder.which()
        return {"active": True, "current": which, "status": status}
    except ValueError as e:
        return {"active": False, "current": None, "error": str(e)}

@app.get("/paiab/which")
async def paiab_which():
    builder = get_paiab_builder()
    return {"current": builder.which()}

@app.post("/paiab/select/{name}")
async def paiab_select(name: str):
    builder = get_paiab_builder()
    result = builder.select(name)
    return {"result": result}

@app.post("/paiab/new")
async def paiab_new(req: NewPAIARequest):
    builder = get_paiab_builder()
    result = builder.new(req.name, req.description, req.git_dir, req.source_dir, req.init_giint)
    return {"result": result}

@app.delete("/paiab/{name}")
async def paiab_delete(name: str):
    builder = get_paiab_builder()
    result = builder.delete(name)
    return {"result": result}

@app.post("/paiab/fork")
async def paiab_fork(req: ForkPAIARequest):
    builder = get_paiab_builder()
    result = builder.fork_paia(req.source_name, req.new_name, req.fork_type, req.description, req.git_dir, req.init_giint)
    return {"result": result}

@app.post("/paiab/tick_version")
async def paiab_tick_version(req: TickVersionRequest):
    builder = get_paiab_builder()
    result = builder.tick_version(req.new_version, req.new_description)
    return {"result": result}


# --- PAIAB Components ---

@app.get("/paiab/components/{comp_type}")
async def paiab_list_components(comp_type: str):
    builder = get_paiab_builder()
    try:
        components = builder.list_components(comp_type)
        return {"items": components, "count": len(components)}
    except ValueError as e:
        return {"items": [], "count": 0, "error": str(e)}

@app.get("/paiab/component/{comp_type}/{name}")
async def paiab_get_component(comp_type: str, name: str):
    builder = get_paiab_builder()
    return builder.get_component(comp_type, name)

@app.delete("/paiab/component/{comp_type}/{name}")
async def paiab_remove_component(comp_type: str, name: str):
    builder = get_paiab_builder()
    result = builder.remove_component(comp_type, name)
    return {"result": result}


# --- PAIAB Add Components ---

@app.post("/paiab/add/skill")
async def paiab_add_skill(req: AddSkillRequest):
    builder = get_paiab_builder()
    spec = builder.add_skill(req.name, req.domain, req.category, req.description)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/mcp")
async def paiab_add_mcp(req: AddMCPRequest):
    builder = get_paiab_builder()
    spec = builder.add_mcp(req.name, req.description)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/hook")
async def paiab_add_hook(req: AddHookRequest):
    builder = get_paiab_builder()
    spec = builder.add_hook(req.name, req.hook_type, req.description)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/command")
async def paiab_add_command(req: AddCommandRequest):
    builder = get_paiab_builder()
    spec = builder.add_command(req.name, req.description, req.argument_hint)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/agent")
async def paiab_add_agent(req: AddAgentRequest):
    builder = get_paiab_builder()
    spec = builder.add_agent(req.name, req.description)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/persona")
async def paiab_add_persona(req: AddPersonaRequest):
    builder = get_paiab_builder()
    spec = builder.add_persona(req.name, req.domain, req.description, req.frame)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/plugin")
async def paiab_add_plugin(req: AddPluginRequest):
    builder = get_paiab_builder()
    spec = builder.add_plugin(req.name, req.description, req.git_url)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/flight")
async def paiab_add_flight(req: AddFlightRequest):
    builder = get_paiab_builder()
    spec = builder.add_flight(req.name, req.domain, req.description)
    return {"result": "added", "spec": spec.model_dump()}

@app.post("/paiab/add/metastack")
async def paiab_add_metastack(req: AddMetastackRequest):
    builder = get_paiab_builder()
    spec = builder.add_metastack(req.name, req.domain, req.description)
    return {"result": "added", "spec": spec.model_dump()}


# --- PAIAB Tier/Golden ---

@app.post("/paiab/advance_tier")
async def paiab_advance_tier(req: AdvanceTierRequest):
    builder = get_paiab_builder()
    result = builder.advance_tier(req.comp_type, req.name, req.fulfillment)
    return {"result": result}

@app.post("/paiab/set_tier")
async def paiab_set_tier(req: SetTierRequest):
    builder = get_paiab_builder()
    result = builder.set_tier(req.comp_type, req.name, req.tier, req.note)
    return {"result": result}

@app.post("/paiab/goldify")
async def paiab_goldify(req: GoldifyRequest):
    builder = get_paiab_builder()
    result = builder.goldify(req.comp_type, req.name, req.note)
    return {"result": result}

@app.post("/paiab/regress_golden")
async def paiab_regress_golden(req: RegressGoldenRequest):
    builder = get_paiab_builder()
    result = builder.regress_golden(req.comp_type, req.name, req.reason)
    return {"result": result}


# --- PAIAB GEAR ---

@app.post("/paiab/update_gear")
async def paiab_update_gear(req: UpdateGEARRequest):
    builder = get_paiab_builder()
    result = builder.update_gear(req.dimension, req.score, req.note)
    return {"result": result}

@app.post("/paiab/sync_gear")
async def paiab_sync_gear():
    builder = get_paiab_builder()
    result = builder.sync_and_emit_gear()
    return {"result": result}

@app.get("/paiab/check_win")
async def paiab_check_win():
    builder = get_paiab_builder()
    won = builder.check_win()
    return {"won": won}

@app.post("/paiab/publish")
async def paiab_publish():
    builder = get_paiab_builder()
    result = builder.publish()
    return {"result": result}


# --- PAIAB Field Setters ---

@app.post("/paiab/set/skill_md")
async def paiab_set_skill_md(req: SetSkillMdRequest):
    builder = get_paiab_builder()
    result = builder.set_skill_md(req.skill_name, req.content)
    return {"result": result}

@app.post("/paiab/set/skill_reference")
async def paiab_set_skill_reference(req: SetSkillReferenceRequest):
    builder = get_paiab_builder()
    result = builder.set_skill_reference(req.skill_name, req.content)
    return {"result": result}

@app.post("/paiab/set/skill_resource")
async def paiab_set_skill_resource(req: AddSkillResourceRequest):
    builder = get_paiab_builder()
    result = builder.add_skill_resource(req.skill_name, req.filename, req.content, req.content_type)
    return {"result": result}

@app.post("/paiab/set/mcp_server")
async def paiab_set_mcp_server(req: SetMCPServerRequest):
    builder = get_paiab_builder()
    result = builder.set_mcp_server(req.mcp_name, req.content)
    return {"result": result}

@app.post("/paiab/set/mcp_tool")
async def paiab_set_mcp_tool(req: AddMCPToolRequest):
    builder = get_paiab_builder()
    result = builder.add_mcp_tool(req.mcp_name, req.core_function, req.ai_description)
    return {"result": result}

@app.post("/paiab/set/hook_script")
async def paiab_set_hook_script(req: SetHookScriptRequest):
    builder = get_paiab_builder()
    result = builder.set_hook_script(req.hook_name, req.content)
    return {"result": result}

@app.post("/paiab/set/command_prompt")
async def paiab_set_command_prompt(req: SetCommandPromptRequest):
    builder = get_paiab_builder()
    result = builder.set_command_prompt(req.cmd_name, req.content)
    return {"result": result}

@app.post("/paiab/set/agent_prompt")
async def paiab_set_agent_prompt(req: SetAgentPromptRequest):
    builder = get_paiab_builder()
    result = builder.set_agent_prompt(req.agent_name, req.content)
    return {"result": result}

@app.post("/paiab/set/persona_frame")
async def paiab_set_persona_frame(req: SetPersonaFrameRequest):
    builder = get_paiab_builder()
    result = builder.set_persona_frame(req.persona_name, req.content)
    return {"result": result}

@app.post("/paiab/set/flight_step")
async def paiab_set_flight_step(req: AddFlightStepRequest):
    builder = get_paiab_builder()
    result = builder.add_flight_step(req.flight_name, req.step_number, req.title, req.instruction, req.skills_to_equip)
    return {"result": result}

@app.post("/paiab/set/metastack_field")
async def paiab_set_metastack_field(req: AddMetastackFieldRequest):
    builder = get_paiab_builder()
    result = builder.add_metastack_field(req.metastack_name, req.field_name, req.field_type, req.description, req.default)
    return {"result": result}


# ==================== AGENT REGISTRY & RELAY ====================

class PAIAContainerRegistration(BaseModel):
    """Agent/PAIA container registration."""
    agent_id: str
    address: str
    paia_name: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PAIARelayExecuteRequest(BaseModel):
    """Request to execute code in a remote agent container."""
    code: str
    language: str = "python"
    timeout: int = 60


# Agent registry: agent_id -> PAIAContainerRegistration
_agent_registry: Dict[str, PAIAContainerRegistration] = {}


@app.post("/agents/register")
async def register_agent(reg: PAIAContainerRegistration):
    """Register an agent container with its address."""
    _agent_registry[reg.agent_id] = reg
    logger.info(f"Agent registered: {reg.agent_id} at {reg.address}")
    return {"registered": reg.agent_id, "address": reg.address}


@app.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Unregister an agent container."""
    if agent_id in _agent_registry:
        del _agent_registry[agent_id]
        return {"unregistered": agent_id}
    return {"error": f"Agent {agent_id} not found"}


@app.get("/agents")
async def list_agents():
    """List all registered agents."""
    return {
        "agents": {aid: reg.model_dump() for aid, reg in _agent_registry.items()},
        "count": len(_agent_registry)
    }


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent registration info."""
    if agent_id not in _agent_registry:
        return {"error": f"Agent {agent_id} not found"}
    return _agent_registry[agent_id].model_dump()


@app.post("/agents/{agent_id}/execute")
async def relay_execute(agent_id: str, req: PAIARelayExecuteRequest):
    """Relay execute command to agent container."""
    if agent_id not in _agent_registry:
        return {"error": f"Agent {agent_id} not found"}

    reg = _agent_registry[agent_id]
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{reg.address}/execute",
                json={"code": req.code, "language": req.language, "timeout": req.timeout},
                timeout=float(req.timeout + 5)
            )
            return resp.json()
    except Exception as e:
        logger.error(f"Relay to {agent_id} failed: {e}")
        return {"error": str(e)}


@app.post("/agents/{agent_id}/interrupt")
async def relay_interrupt(agent_id: str, double: bool = False):
    """Relay interrupt (Esc) to agent container."""
    if agent_id not in _agent_registry:
        return {"error": f"Agent {agent_id} not found"}

    reg = _agent_registry[agent_id]
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{reg.address}/interrupt", params={"double": double}, timeout=10)
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


@app.post("/agents/{agent_id}/inject")
async def relay_inject(agent_id: str, message: str, press_enter: bool = True):
    """Relay message injection to agent container's tmux."""
    if agent_id not in _agent_registry:
        return {"error": f"Agent {agent_id} not found"}

    reg = _agent_registry[agent_id]
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{reg.address}/self/inject",
                json={"message": message, "press_enter": press_enter},
                timeout=10
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ==================== AGENT MESSAGING (llegos-based) ====================

# Agent registry: agent_id -> CodeAgent instance
_agent_instances: Dict[str, CodeAgent] = {}

# Message store for threading/history (by message ID)
_message_store: Dict[str, Message] = {}
_message_history: List[str] = []

# Read status tracking: message_id -> set of agent_ids who have read it
_read_status: Dict[str, set] = {}


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    from_agent: str
    to_agent: str
    content: str
    ingress: str = "frontend"
    priority: int = 0
    metadata: Dict[str, Any] = {}


class ReplyMessageRequest(BaseModel):
    """Request to reply to a message."""
    parent_message_id: str
    content: str
    priority: int = 0
    metadata: Dict[str, Any] = {}


def _get_agent(agent_id: str) -> Optional[CodeAgent]:
    """Get agent instance by ID."""
    if agent_id in _agent_instances:
        return _agent_instances[agent_id]
    if agent_id in _agent_registry:
        return None
    return None


def _serialize_message(msg: Message) -> Dict[str, Any]:
    """Serialize llegos Message to dict for JSON response."""
    return {
        "id": msg.id,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,
        "parent_id": msg.parent_id,
        "content": getattr(msg, 'content', ''),
        "priority": getattr(msg, 'priority', 0),
        "ingress": getattr(msg, 'ingress', IngressType.FRONTEND).value if hasattr(msg, 'ingress') else 'frontend',
        "created_at": msg.created_at.isoformat(),
        "metadata": msg.metadata,
    }


@app.post("/messages/send")
async def send_message(req: SendMessageRequest):
    """Send message using llegos email semantics."""
    ingress = IngressType(req.ingress) if req.ingress in [e.value for e in IngressType] else IngressType.FRONTEND

    msg = create_user_message(
        content=req.content,
        ingress=ingress,
        source_id=req.from_agent,
        priority=req.priority
    )
    msg.metadata.update(req.metadata)
    msg.metadata["from_agent"] = req.from_agent
    msg.metadata["to_agent"] = req.to_agent

    _message_store[msg.id] = msg
    _message_history.append(msg.id)
    if len(_message_history) > 1000:
        old_id = _message_history.pop(0)
        _message_store.pop(old_id, None)

    target_agent = _get_agent(req.to_agent)
    if target_agent:
        success = target_agent.enqueue(msg)
        if not success:
            return {"error": "Agent inbox full", "message_id": msg.id}
    else:
        # No live agent — fall back to cave.route_message (file inbox)
        # NOTE: must use module-level access because `cave` was None at import time.
        import cave.server.http_server as _cave_http
        if _cave_http.cave is not None:
            _cave_http.cave.route_message(
                from_agent=req.from_agent,
                to_agent=req.to_agent,
                content=req.content,
                priority=req.priority,
                metadata=req.metadata,
            )
        else:
            # Last resort: write directly to file inbox
            import json, os, time
            inbox_dir = os.path.join(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "inboxes", req.to_agent)
            os.makedirs(inbox_dir, exist_ok=True)
            msg_file = os.path.join(inbox_dir, f"{int(time.time()*1000)}.json")
            with open(msg_file, "w") as f:
                json.dump({"from": req.from_agent, "to": req.to_agent, "content": req.content, "priority": req.priority, "metadata": req.metadata}, f)

    logger.info(f"Message sent: {req.from_agent} -> {req.to_agent} [{msg.id}]")

    if req.to_agent == "human" and _event_queue:
        try:
            _event_queue.put_nowait({
                "type": "human_message",
                "data": _serialize_message(msg)
            })
        except Exception:
            pass

    return {"status": "sent", "message_id": msg.id, "message": _serialize_message(msg)}


@app.post("/messages/reply")
async def reply_to_message(req: ReplyMessageRequest):
    """Reply to an existing message using llegos email threading."""
    parent = _message_store.get(req.parent_message_id)
    if not parent:
        return {"error": f"Parent message {req.parent_message_id} not found"}

    reply = parent.reply(content=req.content, priority=req.priority)
    reply.metadata.update(req.metadata)

    _message_store[reply.id] = reply
    _message_history.append(reply.id)

    if parent.sender:
        target_agent = _get_agent(parent.sender_id)
        if target_agent:
            target_agent.enqueue(reply)

    logger.info(f"Reply sent: {reply.sender_id} -> {reply.receiver_id} [parent: {parent.id}]")

    return {"status": "sent", "message_id": reply.id, "message": _serialize_message(reply)}


@app.get("/messages/thread/{message_id}")
async def get_message_thread(message_id: str, height: int = 10):
    """Get message thread using llegos message_chain."""
    msg = _message_store.get(message_id)
    if not msg:
        return {"error": f"Message {message_id} not found"}

    chain = list(message_chain(msg, height))
    return {
        "thread": [_serialize_message(m) for m in chain],
        "count": len(chain),
        "root_id": chain[0].id if chain else None
    }


@app.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Get a single message by ID."""
    msg = _message_store.get(message_id)
    if not msg:
        return {"error": f"Message {message_id} not found"}
    return {"message": _serialize_message(msg)}


@app.get("/messages/inbox/{agent_id}")
async def get_inbox(agent_id: str, unread: Optional[bool] = None):
    """Get all messages in agent's llegos inbox."""
    agent = _get_agent(agent_id)
    if agent:
        messages = []
        for m in agent._inbox:
            is_read = _is_message_read_by(m.id, agent_id)
            if unread is None or (unread and not is_read) or (not unread and is_read):
                msg_data = _serialize_message(m)
                msg_data["is_read"] = is_read
                messages.append(msg_data)
        return {"messages": messages, "count": len(messages)}

    messages = []
    for mid in _message_history:
        if mid not in _message_store:
            continue
        msg = _message_store[mid]
        to_agent = msg.metadata.get("to_agent") or msg.receiver_id
        if to_agent != agent_id:
            continue
        is_read = _is_message_read_by(mid, agent_id)
        if unread is None or (unread and not is_read) or (not unread and is_read):
            msg_data = _serialize_message(msg)
            msg_data["is_read"] = is_read
            messages.append(msg_data)
    return {"messages": messages, "count": len(messages)}


@app.get("/messages/inbox/{agent_id}/count")
async def get_inbox_count(agent_id: str, unread: Optional[bool] = None):
    """Get inbox message count."""
    agent = _get_agent(agent_id)
    if agent:
        if unread is None:
            return {"count": agent.inbox_count, "unread_count": None}
        count = sum(
            1 for m in agent._inbox
            if (unread and not _is_message_read_by(m.id, agent_id)) or
               (not unread and _is_message_read_by(m.id, agent_id))
        )
        return {"count": count}

    total = 0
    unread_total = 0
    for mid in _message_history:
        if mid in _message_store:
            msg = _message_store[mid]
            to_agent = msg.metadata.get("to_agent") or msg.receiver_id
            if to_agent == agent_id:
                total += 1
                if not _is_message_read_by(mid, agent_id):
                    unread_total += 1

    if unread is None:
        return {"count": total, "unread_count": unread_total}
    elif unread:
        return {"count": unread_total}
    else:
        return {"count": total - unread_total}


@app.get("/messages/inbox/{agent_id}/peek")
async def peek_inbox(agent_id: str):
    """Peek at next message without removing it."""
    agent = _get_agent(agent_id)
    if agent:
        msg = agent.peek()
        if msg:
            return {"message": _serialize_message(msg)}
    return {"message": None}


@app.get("/messages/inbox/{agent_id}/pop")
async def pop_message(agent_id: str):
    """Pop next message from inbox (dequeue)."""
    agent = _get_agent(agent_id)
    if agent:
        msg = agent.dequeue()
        if msg:
            return {"message": _serialize_message(msg)}
    return {"message": None}


@app.delete("/messages/inbox/{agent_id}/{message_id}")
async def ack_message(agent_id: str, message_id: str):
    """Acknowledge (remove) a specific message from inbox."""
    agent = _get_agent(agent_id)
    if agent:
        for i, msg in enumerate(agent._inbox):
            if msg.id == message_id:
                del agent._inbox[i]
                return {"acknowledged": message_id}
        return {"error": f"Message {message_id} not in inbox"}
    return {"error": f"Agent {agent_id} not found"}


@app.get("/messages/history")
async def get_message_history(limit: int = 100, agent: Optional[str] = None):
    """Get message history for observability."""
    history_ids = _message_history[-limit:]
    messages = []
    for mid in history_ids:
        if mid in _message_store:
            msg = _message_store[mid]
            if agent is None or msg.sender_id == agent or msg.receiver_id == agent:
                messages.append(_serialize_message(msg))
    return {"messages": messages, "count": len(messages)}


class PAIAForwardMessageRequest(BaseModel):
    """Request to forward a message."""
    message_id: str
    to_agent: str
    metadata: Dict[str, Any] = {}


class PAIAThreadAliasRequest(BaseModel):
    """Request to set thread alias."""
    alias: str


@app.post("/messages/forward")
async def forward_message(req: PAIAForwardMessageRequest):
    """Forward an existing message to a new recipient."""
    original = _message_store.get(req.message_id)
    if not original:
        return {"error": f"Message {req.message_id} not found"}

    target_agent = _get_agent(req.to_agent)

    if target_agent:
        forwarded = original.forward_to(target_agent)
    else:
        forwarded = original.forward_to(None)

    forwarded.metadata.update(req.metadata)

    _message_store[forwarded.id] = forwarded
    _message_history.append(forwarded.id)

    if target_agent:
        target_agent.enqueue(forwarded)

    logger.info(f"Forwarded: {original.id} -> {req.to_agent} [{forwarded.id}]")

    return {"status": "forwarded", "message_id": forwarded.id, "message": _serialize_message(forwarded)}


@app.post("/agents/instance/register")
async def register_agent_instance(agent_id: str, agent: CodeAgent):
    """Register a CodeAgent instance for message routing."""
    _agent_instances[agent_id] = agent
    return {"registered": agent_id}


def register_agent_instance_internal(agent_id: str, agent: CodeAgent):
    """Internal function to register agent instance (called by harness)."""
    _agent_instances[agent_id] = agent
    logger.info(f"Registered agent instance: {agent_id}")


# ==================== THREAD ALIASING ====================

@app.put("/messages/thread/{message_id}/alias")
async def set_thread_alias(message_id: str, req: PAIAThreadAliasRequest):
    """Set alias for a thread."""
    msg = _message_store.get(message_id)
    if not msg:
        return {"error": f"Message {message_id} not found"}

    root = msg
    while root.parent_id and root.parent_id in _message_store:
        root = _message_store[root.parent_id]

    root.metadata["thread_alias"] = req.alias

    return {"status": "alias_set", "root_id": root.id, "alias": req.alias}


@app.get("/messages/thread/{message_id}/alias")
async def get_thread_alias(message_id: str):
    """Get alias for a thread."""
    msg = _message_store.get(message_id)
    if not msg:
        return {"error": f"Message {message_id} not found"}

    root = msg
    while root.parent_id and root.parent_id in _message_store:
        root = _message_store[root.parent_id]

    alias = root.metadata.get("thread_alias")
    return {"root_id": root.id, "alias": alias}


@app.put("/messages/thread/{message_id}/priority")
async def set_thread_priority(message_id: str, priority: str = "normal"):
    """Set priority for a thread."""
    if priority not in ("urgent", "normal", "low"):
        return {"error": "Priority must be urgent, normal, or low"}

    msg = _message_store.get(message_id)
    if not msg:
        return {"error": f"Message {message_id} not found"}

    root = msg
    while root.parent_id and root.parent_id in _message_store:
        root = _message_store[root.parent_id]

    root.metadata["thread_priority"] = priority
    return {"status": "priority_set", "root_id": root.id, "priority": priority}


@app.delete("/messages/thread/{message_id}/alias")
async def delete_thread_alias(message_id: str):
    """Remove alias from a thread."""
    msg = _message_store.get(message_id)
    if not msg:
        return {"error": f"Message {message_id} not found"}

    root = msg
    while root.parent_id and root.parent_id in _message_store:
        root = _message_store[root.parent_id]

    old_alias = root.metadata.pop("thread_alias", None)
    return {"status": "alias_removed", "root_id": root.id, "old_alias": old_alias}


@app.get("/threads")
async def list_threads(alias: Optional[str] = None):
    """List all threads (root messages) with their aliases."""
    threads = []
    seen_roots = set()

    for msg_id in _message_history:
        if msg_id not in _message_store:
            continue
        msg = _message_store[msg_id]

        root = msg
        while root.parent_id and root.parent_id in _message_store:
            root = _message_store[root.parent_id]

        if root.id in seen_roots:
            continue
        seen_roots.add(root.id)

        thread_alias = root.metadata.get("thread_alias")

        if alias and (not thread_alias or alias.lower() not in thread_alias.lower()):
            continue

        thread_count = sum(
            1 for mid in _message_history
            if mid in _message_store and _get_root_id(mid) == root.id
        )

        threads.append({
            "root_id": root.id,
            "alias": thread_alias,
            "message_count": thread_count,
            "created_at": root.created_at.isoformat(),
            "preview": getattr(root, 'content', '')[:100]
        })

    return {"threads": threads, "count": len(threads)}


def _get_root_id(msg_id: str) -> Optional[str]:
    """Helper to get root message ID for any message."""
    if msg_id not in _message_store:
        return None
    msg = _message_store[msg_id]
    while msg.parent_id and msg.parent_id in _message_store:
        msg = _message_store[msg.parent_id]
    return msg.id


# ==================== READ/UNREAD STATUS ====================

@app.post("/messages/{message_id}/read")
async def mark_message_read(message_id: str, agent_id: str):
    """Mark a message as read by an agent."""
    if message_id not in _message_store:
        return {"error": f"Message {message_id} not found"}

    if message_id not in _read_status:
        _read_status[message_id] = set()

    _read_status[message_id].add(agent_id)

    return {
        "status": "marked_read",
        "message_id": message_id,
        "agent_id": agent_id,
        "read_by_count": len(_read_status[message_id])
    }


@app.delete("/messages/{message_id}/read")
async def mark_message_unread(message_id: str, agent_id: str):
    """Mark a message as unread by an agent."""
    if message_id not in _message_store:
        return {"error": f"Message {message_id} not found"}

    if message_id in _read_status:
        _read_status[message_id].discard(agent_id)

    return {"status": "marked_unread", "message_id": message_id, "agent_id": agent_id}


@app.get("/messages/{message_id}/read_by")
async def get_message_read_by(message_id: str):
    """Get list of agents who have read this message."""
    if message_id not in _message_store:
        return {"error": f"Message {message_id} not found"}

    readers = list(_read_status.get(message_id, set()))
    return {"message_id": message_id, "read_by": readers, "read_count": len(readers)}


@app.get("/messages/{message_id}/is_read")
async def check_message_read(message_id: str, agent_id: str):
    """Check if a specific agent has read this message."""
    if message_id not in _message_store:
        return {"error": f"Message {message_id} not found"}

    is_read = agent_id in _read_status.get(message_id, set())
    return {"message_id": message_id, "agent_id": agent_id, "is_read": is_read}


def _is_message_read_by(message_id: str, agent_id: str) -> bool:
    """Helper to check if agent has read message."""
    return agent_id in _read_status.get(message_id, set())


def unregister_agent_instance_internal(agent_id: str):
    """Internal function to unregister agent instance."""
    if agent_id in _agent_instances:
        del _agent_instances[agent_id]
        logger.info(f"Unregistered agent instance: {agent_id}")


# ==================== CONDUCTOR (Mind Layer) ====================
# Uses llegos CodeAgent inbox — same messaging system as every other agent.

from conductor.cave_registration import (
    ConductorConfig,
    register_conductor_in_cave,
    get_conductor_anatomy_access,
)
from conductor.conductor import Conductor
from conductor.connector import ClaudePConnector
from conductor.state_machine import StateMachine

_conductor_config = ConductorConfig()
_conductor_registered = False
_conductor_registration = None
_conductor_instance: Optional["Conductor"] = None
_conductor_processing = False  # Lock to prevent concurrent processing


import re

def _extract_user_message(content: str) -> str:
    """Extract the actual user message from Discord-prefixed content.

    Discord source wraps messages as: [Discord #channel] username: actual message
    This extracts 'actual message' from that format.
    """
    m = re.match(r"^\[Discord #\d+\]\s+\w+:\s*(.*)$", content.strip(), re.DOTALL)
    if m:
        return m.group(1).strip()
    return content.strip()


async def _handle_conductor_command(content: str, metadata: Dict[str, Any]) -> Optional[str]:
    """Parse Discord !commands before they reach handle_message.

    Returns response string if command was handled, None if not a command.

    Commands:
        !new              — Start fresh conversation (clear history)
        !resume           — Re-load persisted conversation state
        !list             — List recent conversations
        !3                — Select conversation #3 from last !list
        !agent <name>     — Route next messages to a specific agent
        !status           — Show current conversation state
    """
    content = _extract_user_message(content)
    if not content.startswith("!"):
        return None

    # !new — fresh conversation
    if content == "!new":
        _conductor_instance.new_conversation()
        return "🆕 **New conversation started.** History cleared. Next message starts fresh."

    # !resume — reload from disk
    if content == "!resume":
        _conductor_instance._load_conversation_state()
        if _conductor_instance.history_id:
            return f"▶️ **Resumed conversation** `{_conductor_instance.conversation_id}` (history: `{_conductor_instance.history_id}`)"
        return "⚠️ **No saved conversation to resume.** Use `!new` to start fresh."

    # !status / !ping — full system health
    if content in ("!status", "!ping"):
        lines = ["📊 **System Health:**"]

        # Conductor status
        h = _conductor_instance.history_id or "(none)"
        c = _conductor_instance.conversation_id or "(none)"
        lines.append(f"🎭 **Conductor:** ✅ ONLINE | conv: `{c[:20]}...`")

        # GNOSYS status
        if _is_gnosys_compacting():
            lines.append("🧠 **GNOSYS:** ⏳ COMPACTING (hold messages)")
        else:
            # Check if tmux cave session exists
            import subprocess as _sp
            try:
                r = _sp.run(["tmux", "has-session", "-t", "cave"], capture_output=True, timeout=3)
                if r.returncode == 0:
                    lines.append("🧠 **GNOSYS:** ✅ ONLINE (tmux:cave)")
                else:
                    lines.append("🧠 **GNOSYS:** ❌ OFFLINE (no tmux:cave)")
            except Exception:
                lines.append("🧠 **GNOSYS:** ❓ UNKNOWN")

        # Server uptime
        import time as _time
        if hasattr(app.state, 'start_time'):
            elapsed = _time.time() - app.state.start_time
            hours = int(elapsed // 3600)
            mins = int((elapsed % 3600) // 60)
            lines.append(f"🖥️ **Server:** ✅ UP ({hours}h {mins}m)")
        else:
            lines.append("🖥️ **Server:** ✅ UP")

        # Processing state
        if _conductor_processing:
            lines.append("⚙️ **Processing:** 🔄 YES (working on a message)")
        else:
            agent = _get_agent("conductor")
            inbox_ct = agent.inbox_count if agent else 0
            lines.append(f"⚙️ **Processing:** 💤 IDLE ({inbox_ct} queued)")

        return "\n".join(lines)

    # !list — list recent conversations
    if content == "!list":
        try:
            from heaven_base.memory.conversations import list_chats
            chats = list_chats(limit=10)
            if not chats:
                return "📭 **No conversations found.**"
            lines = ["📋 **Recent conversations:**"]
            for i, chat in enumerate(chats, 1):
                title = chat.get("title", "Untitled")
                cid = chat.get("conversation_id", "?")
                turns = chat.get("turn_count", "?")
                lines.append(f"`{i}` — **{title}** ({turns} turns) `{cid}`")
            lines.append("\nUse `!<number>` to select one.")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ **Error listing conversations:** {e}"

    # !{number} — select from last list
    m = re.match(r"^!(\d+)$", content)
    if m:
        idx = int(m.group(1))
        try:
            from heaven_base.memory.conversations import list_chats, get_latest_history
            chats = list_chats(limit=10)
            if not chats or idx < 1 or idx > len(chats):
                return f"⚠️ **Invalid selection.** Use `!list` first, then `!1` through `!{len(chats) if chats else 0}`."
            chat = chats[idx - 1]
            cid = chat.get("conversation_id")
            hist = get_latest_history(cid)
            if hist:
                _conductor_instance.history_id = hist
                _conductor_instance.conversation_id = cid
                _conductor_instance._save_conversation_state()
                title = chat.get("title", "Untitled")
                return f"✅ **Selected:** {title}\n**Conversation:** `{cid}`\n**History:** `{hist}`"
            return f"⚠️ **Conversation found but no history ID.** May be empty."
        except Exception as e:
            return f"❌ **Error selecting conversation:** {e}"

    # !agent <name> — route to specific agent
    m = re.match(r"^!agent\s+(\w+)$", content)
    if m:
        agent_name = m.group(1)
        target = _get_agent(agent_name)
        if target:
            return f"🔀 **Routing to agent `{agent_name}`.** (Not yet implemented — WakingDreamer handles all messages for now.)"
        available = [name for name in _agent_instances.keys()] if _agent_instances else ["conductor"]
        return f"⚠️ **Agent `{agent_name}` not found.** Available: {', '.join(available)}"

    # !help — show all commands
    if content == "!help":
        return (
            "📖 **Conductor Commands:**\n"
            "`!ping` — Full system health (Conductor + GNOSYS + Server)\n"
            "`!status` — Same as !ping\n"
            "`!new` — Start fresh conversation\n"
            "`!resume` — Reload saved conversation\n"
            "`!list` — List recent conversations\n"
            "`!<number>` — Select conversation from `!list`\n"
            "`!agent <name>` — Route to specific agent\n"
            "`!gnosys <msg>` — Send message directly to GNOSYS\n"
            "`!compact` — Compact context (fresh history + bootstrap)\n"
            "`!stop` — Cancel running agent call\n"
            "`!heartbeat [on|off|interval N|prompt text]` — Control heartbeat\n"
            "`!help` — This help text"
        )

    # !gnosys <msg> — deliver to GNOSYS file inbox (NOT tmux — call_gnosys.sh is for Conductor only)
    # No compaction guard needed — file inbox works regardless of GNOSYS state
    m = re.match(r"^!gnosys\s+(.+)$", content, re.DOTALL)
    if m:
        gnosys_msg = m.group(1).strip()
        try:
            import uuid
            from datetime import datetime
            inbox_dir = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "inboxes" / "main"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().isoformat()
            msg_id = uuid.uuid4().hex[:8]
            msg_file = inbox_dir / f"{ts}_{msg_id}.json"
            msg_file.write_text(json.dumps({
                "id": msg_id,
                "from": "discord",
                "to": "main",
                "content": gnosys_msg,
                "timestamp": ts,
                "priority": 10,
            }, indent=2))
            return f"📨 **Sent to GNOSYS inbox:** {gnosys_msg}"
        except Exception as e:
            return f"❌ **Failed to send to GNOSYS:** {e}"

    # !heartbeat [on|off|interval <N>|prompt <text>|status] — control conductor heartbeat
    if content == "!heartbeat" or content.startswith("!heartbeat "):
        hb_path = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "conductor_heartbeat_config.json"
        try:
            if hb_path.exists():
                hb_cfg = json.loads(hb_path.read_text())
            else:
                hb_cfg = {"enabled": False, "interval_seconds": 300, "prompt": "Heartbeat: check rituals, check inbox, report status.", "_comment": "Isaac controls this file. Agent reads only."}

            parts = content.split(None, 2)  # ['!heartbeat', subcommand, value?]
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
                    return "⚠️ Usage: `!heartbeat interval <seconds>` (e.g. `!heartbeat interval 60`)"
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

            else:  # status (default)
                state = "ON 💓" if hb_cfg.get("enabled") else "OFF 💤"
                interval = hb_cfg.get("interval_seconds", "?")
                prompt = hb_cfg.get("prompt", "(none)")
                return (
                    f"**Heartbeat Config:**\n"
                    f"State: {state}\n"
                    f"Interval: {interval}s\n"
                    f"Prompt: {prompt}"
                )
        except Exception as e:
            return f"❌ **Heartbeat error:** {e}"

    # !compact — retire history, start fresh with bootstrap
    if content == "!compact":
        result = await _conductor_instance._handle_compact(metadata)
        return result.get("response", "Compacted.")

    # !stop — cancel running agent call
    if content == "!stop":
        result = await _conductor_instance._handle_stop(metadata)
        return result.get("response", "Stopped.")

    # Unknown command
    return f"❓ Unknown command: `{content}`\nAvailable: `!new` `!resume` `!list` `!<number>` `!agent <name>` `!gnosys <msg>` `!heartbeat` `!compact` `!stop` `!status` `!help`"


class ConductorMessageRequest(BaseModel):
    """Direct message to Conductor."""
    content: str
    source: str = "api"
    priority: int = 5
    metadata: Dict[str, Any] = {}


@app.on_event("startup")
async def _register_conductor():
    """Create Conductor CodeAgent, SDNAC instance, and register in CAVE."""
    global _conductor_registered, _conductor_registration, _conductor_instance
    import time as _time
    app.state.start_time = _time.time()
    # Create Conductor as a CodeAgent with llegos inbox
    from sanctuary_revolution.harness.core.agent import CodeAgentConfig
    conductor_agent = CodeAgent(
        config=CodeAgentConfig(name="conductor", agent_command=""),
    )
    register_agent_instance_internal("conductor", conductor_agent)
    logger.info("Conductor CodeAgent registered in _agent_instances")

    # Create Conductor SDNAC instance (connector/state for future Runner use)
    connector = ClaudePConnector()
    state = StateMachine("conductor")
    _conductor_instance = Conductor(
        connector=connector,
        researcher_sdnac=None,  # Not needed for basic message handling
        state=state,
        config=_conductor_config,
    )

    # Register in CAVE registry (non-blocking)
    # NOTE: must use module-level access because `cave` was None at import time
    import cave.server.http_server as _cave_http
    try:
        if _cave_http.cave is not None:
            _conductor_registration = register_conductor_in_cave(_cave_http.cave, _conductor_config)
            _conductor_registered = True
            logger.info("Conductor registered in CAVE: %s", _conductor_config.agent_id)
        else:
            logger.warning("CaveAgent not initialized yet — Conductor CAVE registration skipped")
    except Exception as e:
        logger.error("Conductor CAVE registration failed (non-blocking): %s", e)

    # Start background inbox processor
    asyncio.create_task(_conductor_inbox_loop())
    asyncio.create_task(_conductor_stop_watcher())
    logger.info("Conductor inbox processor + stop watcher started")

    # Start CaveAgent Ears poll_loop — World perception + Discord routing.
    # ARCHITECTURE RULE (Isaac, Mar 01 2026): CaveAgent is the ONLY thing
    # that polls Discord. All routing flows through Ears.perceive_world().
    # organ_daemon is passive (no World, no polling).
    # NOTE: must use module-level access because `cave` was None at import time.
    import cave.server.http_server as _cave_http
    if _cave_http.cave is not None:
        # Override CAVE's hardcoded proprioception_rate (30s is way too slow)
        _cave_http.cave.ears.proprioception_rate = 2.0
        _cave_http.cave.ears.poll_interval = 2.0
        asyncio.create_task(_cave_http.cave.ears.poll_loop())
        logger.info("CaveAgent Ears poll_loop started (poll=2s, perception=2s)")
    else:
        logger.error("CaveAgent not initialized — Ears poll_loop NOT started")

    # Register main agent in sancrev agent_registry so /agents/main/inject works.
    # Route: /agents/main/inject → relay to http://localhost:8080/self/inject → tmux:claude
    _agent_registry["main"] = PAIAContainerRegistration(
        agent_id="main",
        address="http://localhost:8080",
        paia_name="gnosys",
        metadata={"type": "tmux", "session": "claude"},
    )
    logger.info("Main agent registered in agent_registry (tmux:claude via CAVE /self/inject)")


def _is_gnosys_compacting() -> bool:
    """Check if GNOSYS is currently compacting context.

    Returns True if gnosys_compacting.lock exists and is less than 5 minutes old.
    Conductor should avoid sending messages to GNOSYS during this window.
    """
    lock_file = Path("/tmp/heaven_data/gnosys_compacting.lock")
    if not lock_file.exists():
        return False
    try:
        import json as _json
        data = _json.loads(lock_file.read_text())
        from datetime import datetime as _dt
        compacting_since = _dt.fromisoformat(data["compacting_since"])
        elapsed = (_dt.now() - compacting_since).total_seconds()
        if elapsed > 300:  # 5 min expiry
            lock_file.unlink(missing_ok=True)
            return False
        return True
    except Exception:
        return False


def _dequeue_file_inbox(agent_id: str) -> Optional[Dict[str, Any]]:
    """Dequeue oldest message from file-based inbox. Returns dict or None."""
    inbox_dir = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "inboxes" / agent_id
    if not inbox_dir.exists():
        return None
    files = sorted(inbox_dir.glob("*.json"))
    if not files:
        return None
    msg_file = files[0]
    try:
        data = json.loads(msg_file.read_text())
        msg_file.unlink()  # ack by deleting
        return data
    except Exception as e:
        # Move bad file out of the way so it doesn't block the queue forever
        bad_path = msg_file.with_suffix(".bad")
        msg_file.rename(bad_path)
        logger.error("Bad inbox file %s moved to %s: %s", msg_file.name, bad_path.name, e)
        return None


async def _conductor_inbox_loop():
    """Background loop: poll Conductor inbox, process messages via SDNAC."""
    global _conductor_processing
    while True:
        try:
            agent = _get_agent("conductor")
            if agent and not _conductor_processing:
                # Check in-memory inbox first, then file-based inbox
                msg = None
                content = ""
                metadata = {}
                if agent.inbox_count > 0:
                    raw = agent.dequeue()
                    if raw:
                        content = getattr(raw, 'content', '')
                        metadata = raw.metadata if hasattr(raw, 'metadata') else {}
                        msg = raw
                else:
                    file_msg = _dequeue_file_inbox("conductor")
                    if file_msg:
                        content = file_msg.get("content", "")
                        metadata = file_msg.get("metadata", {})
                        msg = file_msg

                if msg:
                    _conductor_processing = True
                    # Set flag file so Heart tick can check from its thread
                    _flag = Path("/tmp/heaven_data/conductor_processing.flag")
                    _flag.parent.mkdir(parents=True, exist_ok=True)
                    _flag.write_text("1")
                    try:
                        logger.info("Conductor processing: %s", content[:80])

                        # Extract actual user message from Discord prefix
                        user_msg = _extract_user_message(content)

                        # Check for !commands before sending to handle_message
                        cmd_response = await _handle_conductor_command(user_msg, metadata)
                        if cmd_response is not None:
                            # System command — send as system notification, NOT Conductor response
                            await _send_discord_notify(cmd_response)
                            result = {"status": "handled"}  # Skip _send_conductor_response
                        else:
                            # Inject GNOSYS compaction status so Conductor knows not to reach GNOSYS
                            if _is_gnosys_compacting():
                                metadata["gnosys_compacting"] = True
                                user_msg = f"[SYSTEM: GNOSYS is currently compacting context. Do NOT send messages to GNOSYS via call_gnosys.sh until compaction completes. Process this message using your own capabilities only.]\n\n{user_msg}"

                            # Notify Discord: run started — show input
                            is_heartbeat = metadata.get("type") == "heartbeat"
                            # Reset heartbeat timer on EVERY message (user, command, compact, heartbeat)
                            _ts_path = Path("/tmp/heaven_data/conductor_ops/heartbeat/last_user_message.txt")
                            _ts_path.parent.mkdir(parents=True, exist_ok=True)
                            _ts_path.write_text(datetime.utcnow().isoformat())
                            if is_heartbeat:
                                await _send_discord_notify(f"\U0001F493 **Heartbeat fired** ({metadata.get('source', 'heart')})")
                            else:
                                from conductor.conductor import _get_sanctuary_degree
                                _deg = _get_sanctuary_degree()
                                preview = user_msg[:10] + ("..." if len(user_msg) > 10 else "")
                                await _send_discord_notify(f"🏃 **{_deg}:** {preview}")

                            metadata["sse_queue"] = _event_queue
                            print(f"[SSE-DEBUG] inbox loop passing queue id={id(_event_queue)} to handle_message", flush=True)
                            result = await _conductor_instance.handle_message(
                                user_msg, metadata,
                            )

                        # Route status back to Discord
                        # NOTE: intermediate text + tool events already sent in real-time
                        # by DiscordEventForwarder. We only need status markers here.
                        if result.get("status") == "success":
                            from conductor.conductor import _get_sanctuary_degree
                            await _send_discord_notify(f"✅ Turn iteration complete. — {_get_sanctuary_degree()}")
                        elif result.get("status") == "blocked":
                            await _send_discord_notify("⚠️ **Blocked** — needs external input")
                        elif result.get("status") == "cancelled":
                            await _send_discord_notify("🛑 **Stopped.**")
                        elif result.get("status") == "error":
                            err = result.get("error", "unknown")
                            await _send_discord_notify(f"❌ **Error:** {err}")
                    finally:
                        _conductor_processing = False
                        # Remove processing flag
                        _flag = Path("/tmp/heaven_data/conductor_processing.flag")
                        if _flag.exists():
                            _flag.unlink(missing_ok=True)
                        # Check for pending heartbeat queued while we were busy
                        _pending = Path("/tmp/heaven_data/conductor_ops/heartbeat/pending.json")
                        if _pending.exists():
                            try:
                                hb = json.loads(_pending.read_text())
                                _pending.unlink()
                                # Deliver to file inbox for next loop iteration
                                # DEDUP: Clear existing heartbeat files first
                                inbox_dir = Path("/tmp/heaven_data/inboxes/conductor")
                                inbox_dir.mkdir(parents=True, exist_ok=True)
                                for stale in inbox_dir.glob("heartbeat_*.json"):
                                    try:
                                        stale.unlink()
                                    except Exception:
                                        pass
                                from datetime import datetime as _dt
                                fname = f"heartbeat_{_dt.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
                                (inbox_dir / fname).write_text(json.dumps(hb))
                                logger.info("Pending heartbeat delivered to Conductor inbox")
                            except Exception as hb_err:
                                logger.error("Failed to deliver pending heartbeat: %s", hb_err)
        except Exception as e:
            logger.error("Conductor inbox loop error: %s", e, exc_info=True)
            _conductor_processing = False
        await asyncio.sleep(2)  # Poll every 2 seconds


async def _conductor_stop_watcher():
    """Fast loop: check for !stop even while conductor is processing.

    The main inbox loop skips dequeue when _conductor_processing=True,
    so !stop would never be seen until the current message finishes.
    This watcher checks every 2s and kills the running task immediately.
    """
    while True:
        try:
            if _conductor_processing and _conductor_instance:
                agent = _get_agent("conductor")
                if agent:
                    # Peek at all queued messages for !stop
                    for i, queued_msg in enumerate(list(agent._inbox)):
                        raw_content = getattr(queued_msg, 'content', '')
                        user_content = _extract_user_message(raw_content).strip()
                        if user_content == "!stop":
                            # Remove from inbox
                            try:
                                agent._inbox.remove(queued_msg)
                            except ValueError:
                                pass
                            # Kill the running task
                            result = await _conductor_instance._handle_stop({})
                            await _send_discord_notify(result.get("response", "Stopped."))
                            break
                # Also check file inbox for !stop
                stop_inbox = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "inboxes" / "conductor"
                if stop_inbox.exists():
                    for f in sorted(stop_inbox.glob("*.json")):
                        try:
                            data = json.loads(f.read_text())
                            content = _extract_user_message(data.get("content", "")).strip()
                            if content == "!stop":
                                f.unlink()
                                result = await _conductor_instance._handle_stop({})
                                await _send_discord_notify(result.get("response", "Stopped."))
                                break
                        except Exception:
                            continue
        except Exception as e:
            logger.error("Stop watcher error: %s", e)
        await asyncio.sleep(2)


async def _send_discord_notify(text: str):
    """Send notification to Discord - splits into multiple messages if needed (NO TRUNCATION)."""
    try:
        from cave.core.channel import UserDiscordChannel
        discord = UserDiscordChannel()
        if discord.token and discord.channel_id:
            # Split into chunks if too long for Discord (2000 char limit)
            # NEVER truncate - send everything
            if len(text) <= 1900:
                discord.deliver({"message": text})
            else:
                # Split into chunks
                chunks = []
                remaining = text
                while remaining:
                    if len(remaining) <= 1900:
                        chunks.append(remaining)
                        break
                    # Find a good split point (newline, space, or hard cut)
                    split_at = 1900
                    for i in range(1900, max(1700, 0), -1):
                        if i < len(remaining) and remaining[i] in '\n \t':
                            split_at = i
                            break
                    chunks.append(remaining[:split_at])
                    remaining = remaining[split_at:].lstrip()

                # Send all chunks
                for i, chunk in enumerate(chunks):
                    if i > 0:
                        chunk = f"(cont {i+1}/{len(chunks)})\n{chunk}"
                    discord.deliver({"message": chunk})
    except Exception as e:
        logger.error("Discord notify failed: %s", e)


async def _send_conductor_response(response: str, metadata: Dict[str, Any]):
    """Send Conductor's response back to Discord - splits into chunks if needed (NO TRUNCATION)."""
    try:
        from cave.core.channel import UserDiscordChannel
        discord = UserDiscordChannel()
        if discord.token and discord.channel_id:
            # Prepare full message with header
            full_msg = f"\U0001F682 **WakingDreamer:**\n{response}"

            # Split if too long (2000 char limit) - NEVER truncate
            if len(full_msg) <= 1900:
                discord.deliver({"message": full_msg})
            else:
                # Split into chunks
                chunks = []
                remaining = full_msg
                while remaining:
                    if len(remaining) <= 1900:
                        chunks.append(remaining)
                        break
                    # Find a good split point (newline, space, or hard cut)
                    split_at = 1900
                    for i in range(1900, max(1700, 0), -1):
                        if i < len(remaining) and remaining[i] in '\n \t':
                            split_at = i
                            break
                    chunks.append(remaining[:split_at])
                    remaining = remaining[split_at:].lstrip()

                # Send all chunks
                for i, chunk in enumerate(chunks):
                    if i > 0:
                        chunk = f"(cont {i+1}/{len(chunks)})\n{chunk}"
                    discord.deliver({"message": chunk})

            logger.info("Conductor response sent to Discord: %s", response[:80])
        else:
            logger.warning("No Discord channel configured for Conductor response")
    except Exception as e:
        logger.error("Failed to send Conductor response to Discord: %s", e)


@app.post("/conductor/process")
async def conductor_process():
    """Manually trigger processing of next message in Conductor inbox."""
    global _conductor_processing
    if _conductor_processing:
        return {"status": "busy", "error": "Already processing a message"}
    agent = _get_agent("conductor")
    if not agent or agent.inbox_count == 0:
        return {"status": "empty", "error": "No messages in inbox"}
    if not _conductor_instance:
        return {"status": "error", "error": "Conductor SDNAC not initialized"}

    _conductor_processing = True
    try:
        msg = agent.dequeue()
        if not msg:
            return {"status": "empty"}
        content = getattr(msg, 'content', '')
        metadata = msg.metadata if hasattr(msg, 'metadata') else {}
        cmd_response = await _handle_conductor_command(content, metadata)
        if cmd_response is not None:
            await _send_conductor_response(cmd_response, metadata)
            return {"status": "success", "response": cmd_response}
        preview = content[:100] + ("..." if len(content) > 100 else "")
        await _send_discord_notify(f"\U0001F3C3 **WakingDreamer processing:** {preview}")
        metadata["sse_queue"] = _event_queue
        result = await _conductor_instance.handle_message(content, metadata)
        # Response already sent in real-time by DiscordEventForwarder
        return result
    except Exception as e:
        logger.error("Conductor process error: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        _conductor_processing = False


@app.get("/conductor/status")
async def conductor_status():
    """Get Conductor status."""
    agent = _get_agent("conductor")
    if not agent:
        return {"registered": False, "error": "Conductor agent not in _agent_instances"}
    return {
        "registered": True,
        "agent_id": "conductor",
        "inbox_count": agent.inbox_count,
        "cave_registered": _conductor_registered,
    }


@app.get("/conductor/inbox")
async def conductor_inbox(limit: int = 20):
    """Read Conductor's llegos inbox."""
    agent = _get_agent("conductor")
    if not agent:
        return {"messages": [], "count": 0}
    messages = []
    for msg in list(agent._inbox)[:limit]:
        messages.append(_serialize_message(msg))
    return {"messages": messages, "count": len(messages)}


@app.get("/conductor/inbox/count")
async def conductor_inbox_count():
    """Count messages in Conductor's llegos inbox."""
    agent = _get_agent("conductor")
    if not agent:
        return {"count": 0}
    return {"count": agent.inbox_count}


@app.post("/conductor/message")
async def conductor_message(req: ConductorMessageRequest):
    """Send message to Conductor via llegos enqueue (same as /messages/send)."""
    msg = create_user_message(
        content=req.content,
        ingress=IngressType.FRONTEND,
        source_id=req.source,
        priority=req.priority,
    )
    msg.metadata.update(req.metadata)
    msg.metadata["from_agent"] = req.source
    msg.metadata["to_agent"] = "conductor"
    agent = _get_agent("conductor")
    if not agent:
        return {"error": "Conductor agent not available"}
    success = agent.enqueue(msg)
    if not success:
        return {"error": "Conductor inbox full"}
    _message_store[msg.id] = msg
    _message_history.append(msg.id)
    logger.info("Conductor <- %s: %s (%s)", req.source, req.content[:80], msg.id)
    return {"status": "delivered", "message_id": msg.id}


@app.delete("/conductor/inbox/{message_id}")
async def conductor_ack_message(message_id: str):
    """Acknowledge (dequeue) a message from Conductor's inbox."""
    agent = _get_agent("conductor")
    if not agent:
        return {"error": "Conductor agent not available"}
    # Find and remove message by ID
    for i, msg in enumerate(agent._inbox):
        if msg.id == message_id:
            del agent._inbox[i]
            return {"acknowledged": message_id}
    return {"error": f"Message {message_id} not found"}


# === SSE Events (Conductor + system events streamed to frontend) ===
@app.get("/conductor/events")
async def conductor_events():
    """Stream Conductor events to frontend via Server-Sent Events.

    Conductor events (tool use, tool result, agent message) are pushed
    to _event_queue by SSEChannel via EventBroadcaster. This endpoint
    reads from the queue and streams them as SSE.
    """
    async def generate():
        # Drain any existing events first
        while not _event_queue.empty():
            event = _event_queue.get_nowait()
            yield f"data: {json.dumps(event)}\n\n"
        # Then wait for new events
        while True:
            try:
                event = await asyncio.wait_for(_event_queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# === Conversation Management ===

@app.get("/conversations")
async def list_conversations(limit: int = 20):
    """List all conversations, newest first."""
    from heaven_base.memory.conversations import list_chats
    return {"conversations": list_chats(limit=limit)}


@app.get("/conversations/search")
async def search_conversations(q: str):
    """Search conversations by title or tags."""
    from heaven_base.memory.conversations import search_chats
    return {"conversations": search_chats(q)}


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Load a specific conversation."""
    from heaven_base.memory.conversations import load_chat
    conv = load_chat(conversation_id)
    if not conv:
        return {"error": f"Conversation {conversation_id} not found"}
    return conv


@app.get("/conversations/{conversation_id}/histories")
async def get_conversation_histories(conversation_id: str):
    """Get all history IDs from a conversation."""
    from heaven_base.memory.conversations import ConversationManager
    histories = ConversationManager.get_conversation_histories(conversation_id)
    return {"conversation_id": conversation_id, "histories": histories}


@app.get("/conversations/{conversation_id}/latest")
async def get_conversation_latest(conversation_id: str):
    """Get the latest history ID (most complete snapshot)."""
    from heaven_base.memory.conversations import get_latest_history
    history_id = get_latest_history(conversation_id)
    if not history_id:
        return {"error": f"Conversation {conversation_id} not found or empty"}
    return {"conversation_id": conversation_id, "latest_history_id": history_id}


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    from heaven_base.memory.conversations import ConversationManager
    deleted = ConversationManager.delete_conversation(conversation_id)
    if not deleted:
        return {"error": f"Conversation {conversation_id} not found"}
    return {"deleted": conversation_id}


@app.post("/conversations")
async def create_conversation(data: Dict[str, Any]):
    """Start a new conversation."""
    from heaven_base.memory.conversations import start_chat
    title = data.get("title", "")
    first_history_id = data.get("first_history_id", "")
    agent_name = data.get("agent_name", "")
    tags = data.get("tags", [])
    if not title or not first_history_id or not agent_name:
        return {"error": "title, first_history_id, and agent_name required"}
    return start_chat(title, first_history_id, agent_name, tags)


@app.post("/conversations/{conversation_id}/continue")
async def continue_conversation(conversation_id: str, data: Dict[str, Any]):
    """Add a new history_id to an existing conversation's chain."""
    from heaven_base.memory.conversations import continue_chat
    new_history_id = data.get("history_id", "")
    if not new_history_id:
        return {"error": "history_id required"}
    try:
        return continue_chat(conversation_id, new_history_id)
    except FileNotFoundError:
        return {"error": f"Conversation {conversation_id} not found"}


# === History Content ===

@app.get("/histories/{history_id}")
async def get_history(history_id: str):
    """Load a history's full content (messages, metadata) by ID."""
    from heaven_base.memory.history import History
    try:
        hist = History._load_history_file(history_id)
        return hist.to_json()
    except FileNotFoundError:
        return {"error": f"History {history_id} not found"}


@app.get("/histories/{history_id}/markdown")
async def get_history_markdown(history_id: str):
    """Load a history rendered as human-readable markdown."""
    from heaven_base.memory.history import History
    try:
        hist = History._load_history_file(history_id)
        return {"history_id": history_id, "markdown": hist.to_markdown()}
    except FileNotFoundError:
        return {"error": f"History {history_id} not found"}


@app.get("/conversations/{conversation_id}/content")
async def get_conversation_content(conversation_id: str):
    """Load a conversation's latest history content (full messages)."""
    from heaven_base.memory.conversations import get_latest_history
    from heaven_base.memory.history import History
    history_id = get_latest_history(conversation_id)
    if not history_id:
        return {"error": f"Conversation {conversation_id} not found or empty"}
    try:
        hist = History._load_history_file(history_id)
        return {"conversation_id": conversation_id, "history_id": history_id, **hist.to_json()}
    except FileNotFoundError:
        return {"error": f"History {history_id} not found on disk"}


# === Conductor Conversation Control ===

@app.post("/conductor/conversation/new")
async def conductor_new_conversation():
    """Start a fresh Conductor conversation (clear history)."""
    if not _conductor_instance:
        return {"error": "Conductor not initialized"}
    _conductor_instance.new_conversation()
    return {"status": "new_conversation", "conversation_id": None, "history_id": None}


@app.post("/conductor/conversation/load")
async def conductor_load_conversation(data: Dict[str, Any]):
    """Load a prior Conductor conversation by ID.

    Looks up the conversation, gets the latest history_id,
    and sets the Conductor to continue from that point.
    """
    if not _conductor_instance:
        return {"error": "Conductor not initialized"}
    conversation_id = data.get("conversation_id", "")
    if not conversation_id:
        return {"error": "conversation_id required"}

    from heaven_base.memory.conversations import load_chat, get_latest_history
    conv = load_chat(conversation_id)
    if not conv:
        return {"error": f"Conversation {conversation_id} not found"}

    latest = get_latest_history(conversation_id)
    if not latest:
        return {"error": f"Conversation {conversation_id} has no histories"}

    _conductor_instance.conversation_id = conversation_id
    _conductor_instance.history_id = latest
    _conductor_instance._transcript_chars = 0
    _conductor_instance._compaction_count = 0
    _conductor_instance._save_conversation_state()

    return {
        "status": "loaded",
        "conversation_id": conversation_id,
        "history_id": latest,
        "title": conv.get("title", ""),
        "history_count": len(conv.get("history_chain", [])),
    }


@app.get("/conductor/conversation")
async def conductor_current_conversation():
    """Get Conductor's current conversation state."""
    if not _conductor_instance:
        return {"error": "Conductor not initialized"}
    return {
        "conversation_id": _conductor_instance.conversation_id,
        "history_id": _conductor_instance.history_id,
        "transcript_chars": _conductor_instance._transcript_chars,
        "compaction_count": _conductor_instance._compaction_count,
    }


def main():
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser(description="Sanctuary Revolution HTTP Server")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

# Also runnable with: uvicorn sanctuary_revolution.harness.server.http_server:app --reload
