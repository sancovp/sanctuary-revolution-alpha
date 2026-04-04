"""Sancrev-specific routes that extend CAVEHTTPServer.

CAVE is a library. CAVEHTTPServer has CAVE-only routes.
This module adds all sancrev domain routes on top:
- Event push (SSE)
- Persona control
- GEAR system
- Domain builders (CAVE/SANCTUM/PAIAB)
- Agent registry + relay
- Messaging (llegos-based)
- Conductor control
- Conversation management
- Automations CRUD

Usage:
    from cave.server.cave_http_server import CAVEHTTPServer
    from sanctuary_revolution.harness.server.sancrev_routes import SancrevExtension

    server = CAVEHTTPServer(cave=wd, port=8080)
    ext = SancrevExtension(server)
    server.run()
"""
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
PAIA_STORE_FILE = HEAVEN_DATA_DIR / "paia_store.json"


# ==================== PYDANTIC MODELS ====================

class GenericEventRequest(BaseModel):
    event_type: str
    data: dict = {}
    paia_name: Optional[str] = None
    message: Optional[str] = None

class GEARAcceptRequest(BaseModel):
    event_type: str
    paia_name: str
    component_type: Optional[str] = None
    component_name: Optional[str] = None
    dimension: Optional[str] = None
    proof_note: Optional[str] = None
    accepted: bool = True

class GEARStateRequest(BaseModel):
    paia_name: str

class AddAutomationRequest(BaseModel):
    name: str
    description: str = ""
    schedule: Optional[str] = None
    prompt_template: Optional[str] = None
    code_pointer: Optional[str] = None
    channels: Optional[List[Dict[str, Any]]] = None
    priority: int = 5
    tags: Optional[List[str]] = None

class FireAutomationRequest(BaseModel):
    extra_vars: Optional[Dict[str, Any]] = None

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

class PAIAContainerRegistration(BaseModel):
    agent_id: str
    address: str
    paia_name: Optional[str] = None
    metadata: Dict[str, Any] = {}

class PAIARelayExecuteRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = 60

class SendMessageRequest(BaseModel):
    from_agent: str
    to_agent: str
    content: str
    ingress: str = "frontend"
    priority: int = 0
    metadata: Dict[str, Any] = {}

class ReplyMessageRequest(BaseModel):
    parent_message_id: str
    content: str
    priority: int = 0
    metadata: Dict[str, Any] = {}

class PAIAForwardMessageRequest(BaseModel):
    message_id: str
    to_agent: str
    metadata: Dict[str, Any] = {}

class PAIAThreadAliasRequest(BaseModel):
    alias: str

class ConductorMessageRequest(BaseModel):
    content: str
    source: str = "api"
    priority: int = 5
    metadata: Dict[str, Any] = {}


# ==================== HELPERS ====================

def _ensure_store_dir():
    HEAVEN_DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load_paia_store() -> dict:
    if not PAIA_STORE_FILE.exists():
        return {}
    try:
        return json.loads(PAIA_STORE_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return {}

def _save_paia_store(store: dict):
    _ensure_store_dir()
    PAIA_STORE_FILE.write_text(json.dumps(store, indent=2, default=str))

def _get_paia(name: str):
    store = _load_paia_store()
    paia_data = store.get(name)
    if not paia_data:
        return None
    try:
        from paia_builder.models import PAIA
        return PAIA.model_validate(paia_data)
    except Exception:
        return None

def _set_paia(name: str, paia):
    store = _load_paia_store()
    store[name] = paia.model_dump(mode='json')
    _save_paia_store(store)

def _build_channels(channel_specs: Optional[List[Dict[str, Any]]]) -> list:
    if not channel_specs:
        return []
    from cave.core.channel import UserDiscordChannel, AgentInboxChannel, AgentTmuxChannel
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
            channels.append(AgentTmuxChannel(session=spec.get("session", "claude")))
    return channels


async def _send_discord_notify(text: str):
    """Send notification to Discord — splits if >1900 chars."""
    try:
        from cave.core.channel import UserDiscordChannel
        discord = UserDiscordChannel()
        if not (discord.token and discord.channel_id):
            return
        if len(text) <= 1900:
            discord.deliver({"message": text})
        else:
            remaining = text
            chunks = []
            while remaining:
                if len(remaining) <= 1900:
                    chunks.append(remaining)
                    break
                split_at = 1900
                for i in range(1900, max(1700, 0), -1):
                    if i < len(remaining) and remaining[i] in '\n \t':
                        split_at = i
                        break
                chunks.append(remaining[:split_at])
                remaining = remaining[split_at:].lstrip()
            for i, chunk in enumerate(chunks):
                if i > 0:
                    chunk = f"(cont {i+1}/{len(chunks)})\n{chunk}"
                discord.deliver({"message": chunk})
    except Exception as e:
        logger.error("Discord notify failed: %s", e)


def _is_gnosys_compacting() -> bool:
    lock_file = Path("/tmp/heaven_data/gnosys_compacting.lock")
    if not lock_file.exists():
        return False
    try:
        data = json.loads(lock_file.read_text())
        compacting_since = datetime.fromisoformat(data["compacting_since"])
        elapsed = (datetime.now() - compacting_since).total_seconds()
        if elapsed > 300:
            lock_file.unlink(missing_ok=True)
            return False
        return True
    except Exception:
        return False


def _extract_user_message(content: str) -> str:
    m = re.match(r"^\[Discord #\d+\]\s+\w+:\s*(.*)$", content.strip(), re.DOTALL)
    if m:
        return m.group(1).strip()
    return content.strip()


# ==================== SANCREV EXTENSION ====================

class SancrevExtension:
    """Registers sancrev-specific routes on a CAVEHTTPServer.

    CAVEHTTPServer holds self.cave (a WakingDreamer). This extension
    adds sancrev domain routes to server.app. Routes call methods on
    server.cave. That's it.
    """

    def __init__(self, server):
        self.server = server
        self.app = server.app
        self.cave = server.cave

        # Sancrev state
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._container_registry: Dict[str, PAIAContainerRegistration] = {}
        self._agent_instances: Dict[str, Any] = {}
        self._message_store: Dict[str, Any] = {}
        self._message_history: List[str] = []
        self._read_status: Dict[str, set] = {}
        self._conductor_processing = False

        # Domain builders (lazy)
        self._cave_builder = None
        self._sanctum_builder = None
        self._paiab_builder = None

        # GEAR
        self._proof_handler = None

        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register all route groups
        self._register_event_routes()
        self._register_persona_routes()
        self._register_gear_routes()
        self._register_cave_builder_routes()
        self._register_sanctum_routes()
        self._register_automation_routes()
        self._register_paiab_routes()
        self._register_agent_registry_routes()
        self._register_messaging_routes()
        self._register_conductor_routes()
        self._register_conversation_routes()
        self._register_research_routes()
        self._register_agent_message_routes()
        self._register_startup()

    # === LAZY BUILDERS ===

    def _get_cave_builder(self):
        if self._cave_builder is None:
            from cave_builder import CAVEBuilder
            self._cave_builder = CAVEBuilder()
        return self._cave_builder

    def _get_sanctum_builder(self):
        if self._sanctum_builder is None:
            from sanctum_builder import SANCTUMBuilder
            self._sanctum_builder = SANCTUMBuilder()
        return self._sanctum_builder

    def _get_paiab_builder(self):
        if self._paiab_builder is None:
            from paia_builder.core import PAIABuilder
            self._paiab_builder = PAIABuilder()
        return self._paiab_builder

    def _get_proof_handler(self):
        if self._proof_handler is None:
            from sanctuary_revolution.events.gear_events import GEARProofHandler
            self._proof_handler = GEARProofHandler(paia_store=_get_paia)
        return self._proof_handler

    # === AGENT INSTANCE HELPERS ===

    def _get_agent(self, agent_id: str):
        if agent_id in self._agent_instances:
            return self._agent_instances[agent_id]
        return None

    def _register_agent_instance(self, agent_id: str, agent):
        self._agent_instances[agent_id] = agent
        logger.info("Registered agent instance: %s", agent_id)

    def _serialize_message(self, msg) -> Dict[str, Any]:
        from sanctuary_revolution.harness.core.agent import IngressType
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

    def _is_message_read_by(self, message_id: str, agent_id: str) -> bool:
        return agent_id in self._read_status.get(message_id, set())

    def _get_root_id(self, msg_id: str) -> Optional[str]:
        if msg_id not in self._message_store:
            return None
        msg = self._message_store[msg_id]
        while msg.parent_id and msg.parent_id in self._message_store:
            msg = self._message_store[msg.parent_id]
        return msg.id

    # ==================== EVENT ROUTES ====================

    def _register_event_routes(self):
        ext = self

        @self.app.post("/event")
        async def push_event(req: GenericEventRequest):
            event_data = {
                "type": req.event_type,
                "data": req.data,
                "paia_name": req.paia_name,
                "message": req.message or f"Event: {req.event_type}",
                "timestamp": datetime.now().isoformat(),
            }
            try:
                ext._event_queue.put_nowait(event_data)
                return {"success": True, "event_type": req.event_type}
            except asyncio.QueueFull:
                return {"success": False, "error": "Event queue full"}

        @self.app.get("/events")
        async def unified_events():
            """Unified SSE stream — ALL agent events, tagged with agent name.

            Frontend connects here. Events have {"agent": "conductor", "event": "...", "data": ...}.
            Filter client-side by agent name if needed.
            Same queue as /conductor/events (backwards compat).
            """
            async def generate():
                while not ext._event_queue.empty():
                    event = ext._event_queue.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"
                while True:
                    try:
                        event = await asyncio.wait_for(ext._event_queue.get(), timeout=15.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")

    # ==================== PERSONA ROUTES ====================

    def _register_persona_routes(self):
        @self.app.get("/persona")
        async def get_persona():
            from sanctuary_revolution.core.persona_control import PersonaControl
            return {"active": PersonaControl.is_active(), "persona": PersonaControl.get_active()}

        @self.app.post("/persona/{name}")
        async def activate_persona(name: str):
            from sanctuary_revolution.core.persona_control import PersonaControl
            PersonaControl.activate(name)
            return {"persona": name, "activated": True}

        @self.app.delete("/persona")
        async def deactivate_persona():
            from sanctuary_revolution.core.persona_control import PersonaControl
            PersonaControl.deactivate()
            return {"deactivated": True}

    # ==================== GEAR ROUTES ====================

    def _register_gear_routes(self):
        ext = self

        @self.app.post("/gear/accept")
        async def accept_gear_proof(req: GEARAcceptRequest):
            from sanctuary_revolution.events.gear_events import (
                GEAREventType, GEARDimensionType, AcceptanceEvent,
            )
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
                success = ext._get_proof_handler().handle(event)
                return {"success": success, "event_type": req.event_type, "paia": req.paia_name}
            except ValueError as e:
                return {"success": False, "error": str(e)}

        @self.app.post("/gear/emit")
        async def emit_gear(req: GEARStateRequest):
            from sanctuary_revolution.events.gear_events import emit_gear_state
            paia = _get_paia(req.paia_name)
            if not paia:
                return {"success": False, "error": f"PAIA '{req.paia_name}' not found"}
            emit_gear_state(ext.cave.router if hasattr(ext.cave, 'router') else None, req.paia_name, paia.gear_state)
            return {"success": True, "emitted": req.paia_name}

        @self.app.post("/gear/register")
        async def register_paia(paia_data: dict):
            try:
                from paia_builder.models import PAIA
                paia = PAIA.model_validate(paia_data)
                _set_paia(paia.name, paia)
                return {"success": True, "registered": paia.name}
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.app.get("/gear/list")
        async def list_registered_paias():
            store = _load_paia_store()
            return {"paias": list(store.keys()), "count": len(store)}

        # Parameterized route AFTER static routes
        @self.app.get("/gear/{paia_name}")
        async def get_gear_state(paia_name: str):
            paia = _get_paia(paia_name)
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
                },
            }

    # ==================== CAVE BUILDER ROUTES ====================

    def _register_cave_builder_routes(self):
        ext = self

        @self.app.get("/cave/list")
        async def cave_list():
            builder = ext._get_cave_builder()
            caves = builder.list_caves()
            return {"items": caves, "count": len(caves)}

        @self.app.get("/cave/status")
        async def cave_status():
            builder = ext._get_cave_builder()
            current = builder.which()
            if current == "No CAVE selected":
                return {"active": False, "current_project": None}
            return {"active": True, "current_project": current, "status": builder.status()}

        @self.app.get("/cave/offers")
        async def cave_offers():
            builder = ext._get_cave_builder()
            try:
                offers = builder.list_offers()
                return {"offers": offers, "count": len(offers)}
            except ValueError:
                return {"offers": [], "count": 0, "error": "No CAVE selected"}

        @self.app.get("/cave/journeys")
        async def cave_journeys():
            builder = ext._get_cave_builder()
            try:
                journeys = builder.list_journeys()
                return {"journeys": journeys, "count": len(journeys)}
            except ValueError:
                return {"journeys": [], "count": 0, "error": "No CAVE selected"}

    # ==================== SANCTUM ROUTES ====================

    def _register_sanctum_routes(self):
        ext = self

        @self.app.get("/sanctum/list")
        async def sanctum_list():
            builder = ext._get_sanctum_builder()
            sanctums = builder.list_sanctums()
            return {"items": sanctums, "count": len(sanctums)}

        @self.app.get("/sanctum/status")
        async def sanctum_status():
            builder = ext._get_sanctum_builder()
            current = builder.which()
            if "[HIEL]" in current:
                return {"active": False, "current_sanctum": None}
            return {"active": True, "current_sanctum": current, "status": builder.status()}

        @self.app.get("/sanctum/rituals")
        async def sanctum_rituals():
            builder = ext._get_sanctum_builder()
            try:
                sanctum = builder._ensure_current()
                rituals = [{"name": r.name, "domain": r.domain.value, "frequency": r.frequency.value}
                           for r in sanctum.rituals]
                return {"rituals": rituals, "count": len(rituals)}
            except ValueError:
                return {"rituals": [], "count": 0, "error": "No SANCTUM selected"}

        @self.app.get("/sanctum/goals")
        async def sanctum_goals():
            builder = ext._get_sanctum_builder()
            try:
                sanctum = builder._ensure_current()
                goals = [{"name": g.name, "domain": g.domain.value, "progress": g.progress}
                         for g in sanctum.goals]
                return {"goals": goals, "count": len(goals)}
            except ValueError:
                return {"goals": [], "count": 0, "error": "No SANCTUM selected"}

        @self.app.post("/sanctum/ritual/populate")
        async def populate_rituals():
            from cave.core import sanctum_canopy
            return await sanctum_canopy.populate_all_due_rituals()

        @self.app.post("/sanctum/ritual/complete")
        async def complete_ritual_endpoint(data: Dict[str, Any]):
            from cave.core import sanctum_canopy
            ritual_name = data.get("ritual_name", "")
            if not ritual_name:
                return {"status": "error", "error": "ritual_name required"}
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
            status_val = result.get("status")
            if status_val in ("completed", "already_completed"):
                from cave.core.channel import UserDiscordChannel
                discord = UserDiscordChannel()
                if discord.token and discord.channel_id:
                    now = datetime.now().strftime("%H:%M")
                    if status_val == "completed":
                        msg = f"done {ritual_name} at {now} (streak: {result.get('streak', 0)})"
                    else:
                        msg = f"{ritual_name} already done today"
                    try:
                        discord.deliver({"message": msg})
                    except Exception:
                        pass
            return result

        @self.app.get("/sanctum/ritual/status")
        def get_ritual_completion_status():
            from cave.core import sanctum_canopy
            return sanctum_canopy.get_ritual_status()

    # ==================== AUTOMATION ROUTES ====================

    def _register_automation_routes(self):
        cave = self.cave

        @self.app.get("/automations")
        async def list_automations():
            return cave.get_automation_status()

        @self.app.post("/automations")
        async def add_automation(req: AddAutomationRequest):
            channels = _build_channels(req.channels)
            return cave.add_automation(
                name=req.name, description=req.description, schedule=req.schedule,
                prompt_template=req.prompt_template, code_pointer=req.code_pointer,
                channels=channels, priority=req.priority, tags=req.tags,
            )

        @self.app.post("/automations/fire_due")
        async def fire_all_due():
            results = cave.fire_all_due()
            return {"results": results, "count": len(results)}

        @self.app.post("/automations/{name}/fire")
        async def fire_automation(name: str, req: FireAutomationRequest = None):
            extra_vars = req.extra_vars if req else None
            return cave.fire_automation(name, extra_vars)

        @self.app.delete("/automations/{name}")
        async def remove_automation(name: str):
            return cave.remove_automation(name)

    # ==================== PAIAB ROUTES ====================

    def _register_paiab_routes(self):
        ext = self

        # --- Management ---
        @self.app.get("/paiab/list")
        async def paiab_list():
            return {"items": ext._get_paiab_builder().list_paias(), "count": len(ext._get_paiab_builder().list_paias())}

        @self.app.get("/paiab/status")
        async def paiab_status():
            b = ext._get_paiab_builder()
            try:
                return {"active": True, "current": b.which(), "status": b.status()}
            except ValueError as e:
                return {"active": False, "current": None, "error": str(e)}

        @self.app.get("/paiab/which")
        async def paiab_which():
            return {"current": ext._get_paiab_builder().which()}

        @self.app.post("/paiab/select/{name}")
        async def paiab_select(name: str):
            return {"result": ext._get_paiab_builder().select(name)}

        @self.app.post("/paiab/new")
        async def paiab_new(req: NewPAIARequest):
            return {"result": ext._get_paiab_builder().new(req.name, req.description, req.git_dir, req.source_dir, req.init_giint)}

        @self.app.delete("/paiab/{name}")
        async def paiab_delete(name: str):
            return {"result": ext._get_paiab_builder().delete(name)}

        @self.app.post("/paiab/fork")
        async def paiab_fork(req: ForkPAIARequest):
            return {"result": ext._get_paiab_builder().fork_paia(req.source_name, req.new_name, req.fork_type, req.description, req.git_dir, req.init_giint)}

        @self.app.post("/paiab/tick_version")
        async def paiab_tick_version(req: TickVersionRequest):
            return {"result": ext._get_paiab_builder().tick_version(req.new_version, req.new_description)}

        # --- Components ---
        @self.app.get("/paiab/components/{comp_type}")
        async def paiab_list_components(comp_type: str):
            try:
                components = ext._get_paiab_builder().list_components(comp_type)
                return {"items": components, "count": len(components)}
            except ValueError as e:
                return {"items": [], "count": 0, "error": str(e)}

        @self.app.get("/paiab/component/{comp_type}/{name}")
        async def paiab_get_component(comp_type: str, name: str):
            return ext._get_paiab_builder().get_component(comp_type, name)

        @self.app.delete("/paiab/component/{comp_type}/{name}")
        async def paiab_remove_component(comp_type: str, name: str):
            return {"result": ext._get_paiab_builder().remove_component(comp_type, name)}

        # --- Add Components ---
        @self.app.post("/paiab/add/skill")
        async def paiab_add_skill(req: AddSkillRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_skill(req.name, req.domain, req.category, req.description).model_dump()}

        @self.app.post("/paiab/add/mcp")
        async def paiab_add_mcp(req: AddMCPRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_mcp(req.name, req.description).model_dump()}

        @self.app.post("/paiab/add/hook")
        async def paiab_add_hook(req: AddHookRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_hook(req.name, req.hook_type, req.description).model_dump()}

        @self.app.post("/paiab/add/command")
        async def paiab_add_command(req: AddCommandRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_command(req.name, req.description, req.argument_hint).model_dump()}

        @self.app.post("/paiab/add/agent")
        async def paiab_add_agent(req: AddAgentRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_agent(req.name, req.description).model_dump()}

        @self.app.post("/paiab/add/persona")
        async def paiab_add_persona(req: AddPersonaRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_persona(req.name, req.domain, req.description, req.frame).model_dump()}

        @self.app.post("/paiab/add/plugin")
        async def paiab_add_plugin(req: AddPluginRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_plugin(req.name, req.description, req.git_url).model_dump()}

        @self.app.post("/paiab/add/flight")
        async def paiab_add_flight(req: AddFlightRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_flight(req.name, req.domain, req.description).model_dump()}

        @self.app.post("/paiab/add/metastack")
        async def paiab_add_metastack(req: AddMetastackRequest):
            return {"result": "added", "spec": ext._get_paiab_builder().add_metastack(req.name, req.domain, req.description).model_dump()}

        # --- Tier/Golden ---
        @self.app.post("/paiab/advance_tier")
        async def paiab_advance_tier(req: AdvanceTierRequest):
            return {"result": ext._get_paiab_builder().advance_tier(req.comp_type, req.name, req.fulfillment)}

        @self.app.post("/paiab/set_tier")
        async def paiab_set_tier(req: SetTierRequest):
            return {"result": ext._get_paiab_builder().set_tier(req.comp_type, req.name, req.tier, req.note)}

        @self.app.post("/paiab/goldify")
        async def paiab_goldify(req: GoldifyRequest):
            return {"result": ext._get_paiab_builder().goldify(req.comp_type, req.name, req.note)}

        @self.app.post("/paiab/regress_golden")
        async def paiab_regress_golden(req: RegressGoldenRequest):
            return {"result": ext._get_paiab_builder().regress_golden(req.comp_type, req.name, req.reason)}

        # --- GEAR ---
        @self.app.post("/paiab/update_gear")
        async def paiab_update_gear(req: UpdateGEARRequest):
            return {"result": ext._get_paiab_builder().update_gear(req.dimension, req.score, req.note)}

        @self.app.post("/paiab/sync_gear")
        async def paiab_sync_gear():
            return {"result": ext._get_paiab_builder().sync_and_emit_gear()}

        @self.app.get("/paiab/check_win")
        async def paiab_check_win():
            return {"won": ext._get_paiab_builder().check_win()}

        @self.app.post("/paiab/publish")
        async def paiab_publish():
            return {"result": ext._get_paiab_builder().publish()}

        # --- Field Setters ---
        @self.app.post("/paiab/set/skill_md")
        async def paiab_set_skill_md(req: SetSkillMdRequest):
            return {"result": ext._get_paiab_builder().set_skill_md(req.skill_name, req.content)}

        @self.app.post("/paiab/set/skill_reference")
        async def paiab_set_skill_reference(req: SetSkillReferenceRequest):
            return {"result": ext._get_paiab_builder().set_skill_reference(req.skill_name, req.content)}

        @self.app.post("/paiab/set/skill_resource")
        async def paiab_set_skill_resource(req: AddSkillResourceRequest):
            return {"result": ext._get_paiab_builder().add_skill_resource(req.skill_name, req.filename, req.content, req.content_type)}

        @self.app.post("/paiab/set/mcp_server")
        async def paiab_set_mcp_server(req: SetMCPServerRequest):
            return {"result": ext._get_paiab_builder().set_mcp_server(req.mcp_name, req.content)}

        @self.app.post("/paiab/set/mcp_tool")
        async def paiab_set_mcp_tool(req: AddMCPToolRequest):
            return {"result": ext._get_paiab_builder().add_mcp_tool(req.mcp_name, req.core_function, req.ai_description)}

        @self.app.post("/paiab/set/hook_script")
        async def paiab_set_hook_script(req: SetHookScriptRequest):
            return {"result": ext._get_paiab_builder().set_hook_script(req.hook_name, req.content)}

        @self.app.post("/paiab/set/command_prompt")
        async def paiab_set_command_prompt(req: SetCommandPromptRequest):
            return {"result": ext._get_paiab_builder().set_command_prompt(req.cmd_name, req.content)}

        @self.app.post("/paiab/set/agent_prompt")
        async def paiab_set_agent_prompt(req: SetAgentPromptRequest):
            return {"result": ext._get_paiab_builder().set_agent_prompt(req.agent_name, req.content)}

        @self.app.post("/paiab/set/persona_frame")
        async def paiab_set_persona_frame(req: SetPersonaFrameRequest):
            return {"result": ext._get_paiab_builder().set_persona_frame(req.persona_name, req.content)}

        @self.app.post("/paiab/set/flight_step")
        async def paiab_set_flight_step(req: AddFlightStepRequest):
            return {"result": ext._get_paiab_builder().add_flight_step(req.flight_name, req.step_number, req.title, req.instruction, req.skills_to_equip)}

        @self.app.post("/paiab/set/metastack_field")
        async def paiab_set_metastack_field(req: AddMetastackFieldRequest):
            return {"result": ext._get_paiab_builder().add_metastack_field(req.metastack_name, req.field_name, req.field_type, req.description, req.default)}

    # ==================== AGENT REGISTRY + RELAY ROUTES ====================

    def _register_agent_registry_routes(self):
        ext = self

        @self.app.post("/agents/register")
        async def register_agent(reg: PAIAContainerRegistration):
            ext._container_registry[reg.agent_id] = reg
            logger.info("Agent registered: %s at %s", reg.agent_id, reg.address)
            return {"registered": reg.agent_id, "address": reg.address}

        @self.app.delete("/agents/{agent_id}")
        async def unregister_agent(agent_id: str):
            if agent_id in ext._container_registry:
                del ext._container_registry[agent_id]
                return {"unregistered": agent_id}
            return {"error": f"Agent {agent_id} not found"}

        @self.app.get("/agents")
        async def list_agents():
            return {
                "agents": {aid: reg.model_dump() for aid, reg in ext._container_registry.items()},
                "count": len(ext._container_registry),
            }

        @self.app.get("/agents/{agent_id}")
        async def get_agent(agent_id: str):
            if agent_id not in ext._container_registry:
                return {"error": f"Agent {agent_id} not found"}
            return ext._container_registry[agent_id].model_dump()

        @self.app.post("/agents/{agent_id}/execute")
        async def relay_execute(agent_id: str, req: PAIARelayExecuteRequest):
            if agent_id not in ext._container_registry:
                return {"error": f"Agent {agent_id} not found"}
            reg = ext._container_registry[agent_id]
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{reg.address}/execute",
                        json={"code": req.code, "language": req.language, "timeout": req.timeout},
                        timeout=float(req.timeout + 5),
                    )
                    return resp.json()
            except Exception as e:
                return {"error": str(e)}

        @self.app.post("/agents/{agent_id}/interrupt")
        async def relay_interrupt(agent_id: str, double: bool = False):
            if agent_id not in ext._container_registry:
                return {"error": f"Agent {agent_id} not found"}
            reg = ext._container_registry[agent_id]
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(f"{reg.address}/interrupt", params={"double": double}, timeout=10)
                    return resp.json()
            except Exception as e:
                return {"error": str(e)}

        @self.app.post("/agents/{agent_id}/inject")
        async def relay_inject(agent_id: str, message: str, press_enter: bool = True):
            if agent_id not in ext._container_registry:
                return {"error": f"Agent {agent_id} not found"}
            reg = ext._container_registry[agent_id]
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{reg.address}/self/inject",
                        json={"message": message, "press_enter": press_enter},
                        timeout=10,
                    )
                    return resp.json()
            except Exception as e:
                return {"error": str(e)}

    # ==================== MESSAGING ROUTES ====================

    def _register_messaging_routes(self):
        ext = self

        @self.app.post("/messages/send")
        async def send_message(req: SendMessageRequest):
            from sanctuary_revolution.harness.core.agent import IngressType, create_user_message
            ingress = IngressType(req.ingress) if req.ingress in [e.value for e in IngressType] else IngressType.FRONTEND
            msg = create_user_message(content=req.content, ingress=ingress, source_id=req.from_agent, priority=req.priority)
            msg.metadata.update(req.metadata)
            msg.metadata["from_agent"] = req.from_agent
            msg.metadata["to_agent"] = req.to_agent
            ext._message_store[msg.id] = msg
            ext._message_history.append(msg.id)
            if len(ext._message_history) > 1000:
                old_id = ext._message_history.pop(0)
                ext._message_store.pop(old_id, None)
            target_agent = ext._get_agent(req.to_agent)
            if target_agent:
                success = target_agent.enqueue(msg)
                if not success:
                    return {"error": "Agent inbox full", "message_id": msg.id}
            else:
                ext.cave.route_message(
                    from_agent=req.from_agent, to_agent=req.to_agent,
                    content=req.content, priority=req.priority, metadata=req.metadata,
                ) if hasattr(ext.cave, 'route_message') else None
            if req.to_agent == "human" and ext._event_queue:
                try:
                    ext._event_queue.put_nowait({"type": "human_message", "data": ext._serialize_message(msg)})
                except Exception:
                    pass
            return {"status": "sent", "message_id": msg.id, "message": ext._serialize_message(msg)}

        @self.app.post("/messages/reply")
        async def reply_to_message(req: ReplyMessageRequest):
            parent = ext._message_store.get(req.parent_message_id)
            if not parent:
                return {"error": f"Parent message {req.parent_message_id} not found"}
            reply = parent.reply(content=req.content, priority=req.priority)
            reply.metadata.update(req.metadata)
            ext._message_store[reply.id] = reply
            ext._message_history.append(reply.id)
            if parent.sender:
                target_agent = ext._get_agent(parent.sender_id)
                if target_agent:
                    target_agent.enqueue(reply)
            return {"status": "sent", "message_id": reply.id, "message": ext._serialize_message(reply)}

        @self.app.get("/messages/thread/{message_id}")
        async def get_message_thread(message_id: str, height: int = 10):
            from llegos.llegos import message_chain
            msg = ext._message_store.get(message_id)
            if not msg:
                return {"error": f"Message {message_id} not found"}
            chain = list(message_chain(msg, height))
            return {"thread": [ext._serialize_message(m) for m in chain], "count": len(chain), "root_id": chain[0].id if chain else None}

        @self.app.get("/messages/{message_id}")
        async def get_message(message_id: str):
            msg = ext._message_store.get(message_id)
            if not msg:
                return {"error": f"Message {message_id} not found"}
            return {"message": ext._serialize_message(msg)}

        @self.app.get("/messages/inbox/{agent_id}")
        async def get_inbox(agent_id: str, unread: Optional[bool] = None):
            agent = ext._get_agent(agent_id)
            if agent:
                messages = []
                for m in agent._inbox:
                    is_read = ext._is_message_read_by(m.id, agent_id)
                    if unread is None or (unread and not is_read) or (not unread and is_read):
                        msg_data = ext._serialize_message(m)
                        msg_data["is_read"] = is_read
                        messages.append(msg_data)
                return {"messages": messages, "count": len(messages)}
            messages = []
            for mid in ext._message_history:
                if mid not in ext._message_store:
                    continue
                msg = ext._message_store[mid]
                to_agent = msg.metadata.get("to_agent") or msg.receiver_id
                if to_agent != agent_id:
                    continue
                is_read = ext._is_message_read_by(mid, agent_id)
                if unread is None or (unread and not is_read) or (not unread and is_read):
                    msg_data = ext._serialize_message(msg)
                    msg_data["is_read"] = is_read
                    messages.append(msg_data)
            return {"messages": messages, "count": len(messages)}

        @self.app.get("/messages/inbox/{agent_id}/count")
        async def get_inbox_count(agent_id: str, unread: Optional[bool] = None):
            agent = ext._get_agent(agent_id)
            if agent:
                if unread is None:
                    return {"count": agent.inbox_count, "unread_count": None}
                count = sum(1 for m in agent._inbox if (unread and not ext._is_message_read_by(m.id, agent_id)) or (not unread and ext._is_message_read_by(m.id, agent_id)))
                return {"count": count}
            total = sum(1 for mid in ext._message_history if mid in ext._message_store and (ext._message_store[mid].metadata.get("to_agent") or ext._message_store[mid].receiver_id) == agent_id)
            return {"count": total}

        @self.app.get("/messages/inbox/{agent_id}/peek")
        async def peek_inbox(agent_id: str):
            agent = ext._get_agent(agent_id)
            if agent:
                msg = agent.peek()
                if msg:
                    return {"message": ext._serialize_message(msg)}
            return {"message": None}

        @self.app.get("/messages/inbox/{agent_id}/pop")
        async def pop_message(agent_id: str):
            agent = ext._get_agent(agent_id)
            if agent:
                msg = agent.dequeue()
                if msg:
                    return {"message": ext._serialize_message(msg)}
            return {"message": None}

        @self.app.delete("/messages/inbox/{agent_id}/{message_id}")
        async def ack_message(agent_id: str, message_id: str):
            agent = ext._get_agent(agent_id)
            if agent:
                for i, msg in enumerate(agent._inbox):
                    if msg.id == message_id:
                        del agent._inbox[i]
                        return {"acknowledged": message_id}
                return {"error": f"Message {message_id} not in inbox"}
            return {"error": f"Agent {agent_id} not found"}

        @self.app.get("/messages/history")
        async def get_message_history(limit: int = 100, agent: Optional[str] = None):
            history_ids = ext._message_history[-limit:]
            messages = []
            for mid in history_ids:
                if mid in ext._message_store:
                    msg = ext._message_store[mid]
                    if agent is None or msg.sender_id == agent or msg.receiver_id == agent:
                        messages.append(ext._serialize_message(msg))
            return {"messages": messages, "count": len(messages)}

        @self.app.post("/messages/forward")
        async def forward_message(req: PAIAForwardMessageRequest):
            original = ext._message_store.get(req.message_id)
            if not original:
                return {"error": f"Message {req.message_id} not found"}
            target_agent = ext._get_agent(req.to_agent)
            forwarded = original.forward_to(target_agent) if target_agent else original.forward_to(None)
            forwarded.metadata.update(req.metadata)
            ext._message_store[forwarded.id] = forwarded
            ext._message_history.append(forwarded.id)
            if target_agent:
                target_agent.enqueue(forwarded)
            return {"status": "forwarded", "message_id": forwarded.id, "message": ext._serialize_message(forwarded)}

        # --- Read/Unread ---
        @self.app.post("/messages/{message_id}/read")
        async def mark_message_read(message_id: str, agent_id: str):
            if message_id not in ext._message_store:
                return {"error": f"Message {message_id} not found"}
            if message_id not in ext._read_status:
                ext._read_status[message_id] = set()
            ext._read_status[message_id].add(agent_id)
            return {"status": "marked_read", "message_id": message_id, "agent_id": agent_id}

        @self.app.delete("/messages/{message_id}/read")
        async def mark_message_unread(message_id: str, agent_id: str):
            if message_id in ext._read_status:
                ext._read_status[message_id].discard(agent_id)
            return {"status": "marked_unread", "message_id": message_id, "agent_id": agent_id}

        @self.app.get("/messages/{message_id}/read_by")
        async def get_message_read_by(message_id: str):
            readers = list(ext._read_status.get(message_id, set()))
            return {"message_id": message_id, "read_by": readers, "read_count": len(readers)}

        # --- Threads ---
        @self.app.put("/messages/thread/{message_id}/alias")
        async def set_thread_alias(message_id: str, req: PAIAThreadAliasRequest):
            msg = ext._message_store.get(message_id)
            if not msg:
                return {"error": f"Message {message_id} not found"}
            root = msg
            while root.parent_id and root.parent_id in ext._message_store:
                root = ext._message_store[root.parent_id]
            root.metadata["thread_alias"] = req.alias
            return {"status": "alias_set", "root_id": root.id, "alias": req.alias}

        @self.app.get("/threads")
        async def list_threads(alias: Optional[str] = None):
            threads = []
            seen_roots = set()
            for msg_id in ext._message_history:
                if msg_id not in ext._message_store:
                    continue
                root_id = ext._get_root_id(msg_id)
                if not root_id or root_id in seen_roots:
                    continue
                seen_roots.add(root_id)
                root = ext._message_store[root_id]
                thread_alias = root.metadata.get("thread_alias")
                if alias and (not thread_alias or alias.lower() not in thread_alias.lower()):
                    continue
                thread_count = sum(1 for mid in ext._message_history if mid in ext._message_store and ext._get_root_id(mid) == root_id)
                threads.append({
                    "root_id": root_id,
                    "alias": thread_alias,
                    "message_count": thread_count,
                    "created_at": root.created_at.isoformat(),
                    "preview": getattr(root, 'content', '')[:100],
                })
            return {"threads": threads, "count": len(threads)}

    # ==================== CONDUCTOR ROUTES ====================

    def _register_conductor_routes(self):
        ext = self
        cave = self.cave

        @self.app.post("/conductor/process")
        async def conductor_process():
            if ext._conductor_processing:
                return {"status": "busy", "error": "Already processing a message"}
            agent = ext._get_agent("conductor")
            if not agent or agent.inbox_count == 0:
                return {"status": "empty", "error": "No messages in inbox"}
            conductor = getattr(cave, '_conductor_instance', None)
            if not conductor:
                return {"status": "error", "error": "Conductor not initialized"}
            ext._conductor_processing = True
            try:
                msg = agent.dequeue()
                if not msg:
                    return {"status": "empty"}
                content = getattr(msg, 'content', '')
                metadata = msg.metadata if hasattr(msg, 'metadata') else {}
                metadata["sse_queue"] = ext._event_queue
                result = await conductor.handle_message(content, metadata)
                return result
            except Exception as e:
                return {"status": "error", "error": str(e)}
            finally:
                ext._conductor_processing = False

        @self.app.get("/conductor/status")
        async def conductor_status():
            agent = ext._get_agent("conductor")
            if not agent:
                return {"registered": False, "error": "Conductor not registered"}
            return {"registered": True, "agent_id": "conductor", "inbox_count": agent.inbox_count}

        @self.app.get("/conductor/inbox")
        async def conductor_inbox(limit: int = 20):
            agent = ext._get_agent("conductor")
            if not agent:
                return {"messages": [], "count": 0}
            messages = [ext._serialize_message(msg) for msg in list(agent._inbox)[:limit]]
            return {"messages": messages, "count": len(messages)}

        @self.app.get("/conductor/inbox/count")
        async def conductor_inbox_count():
            agent = ext._get_agent("conductor")
            return {"count": agent.inbox_count if agent else 0}

        @self.app.post("/conductor/message")
        async def conductor_message(req: ConductorMessageRequest):
            from sanctuary_revolution.harness.core.agent import IngressType, create_user_message
            msg = create_user_message(content=req.content, ingress=IngressType.FRONTEND, source_id=req.source, priority=req.priority)
            msg.metadata.update(req.metadata)
            msg.metadata["from_agent"] = req.source
            msg.metadata["to_agent"] = "conductor"
            agent = ext._get_agent("conductor")
            if not agent:
                return {"error": "Conductor agent not available"}
            success = agent.enqueue(msg)
            if not success:
                return {"error": "Conductor inbox full"}
            ext._message_store[msg.id] = msg
            ext._message_history.append(msg.id)
            return {"status": "delivered", "message_id": msg.id}

        @self.app.delete("/conductor/inbox/{message_id}")
        async def conductor_ack_message(message_id: str):
            agent = ext._get_agent("conductor")
            if not agent:
                return {"error": "Conductor agent not available"}
            for i, msg in enumerate(agent._inbox):
                if msg.id == message_id:
                    del agent._inbox[i]
                    return {"acknowledged": message_id}
            return {"error": f"Message {message_id} not found"}

        @self.app.get("/conductor/events")
        async def conductor_events():
            async def generate():
                while not ext._event_queue.empty():
                    event = ext._event_queue.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"
                while True:
                    try:
                        event = await asyncio.wait_for(ext._event_queue.get(), timeout=15.0)
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")

        @self.app.post("/conductor/conversation/new")
        async def conductor_new_conversation():
            conductor = getattr(cave, '_conductor_instance', None)
            if not conductor:
                return {"error": "Conductor not initialized"}
            conductor.new_conversation()
            return {"status": "new_conversation"}

        @self.app.post("/conductor/conversation/load")
        async def conductor_load_conversation(data: Dict[str, Any]):
            conductor = getattr(cave, '_conductor_instance', None)
            if not conductor:
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
                return {"error": f"No histories for {conversation_id}"}
            conductor.conversation_id = conversation_id
            conductor.history_id = latest
            conductor._transcript_chars = 0
            conductor._compaction_count = 0
            conductor._save_conversation_state()
            return {"status": "loaded", "conversation_id": conversation_id, "history_id": latest, "title": conv.get("title", "")}

        @self.app.get("/conductor/conversation")
        async def conductor_current_conversation():
            conductor = getattr(cave, '_conductor_instance', None)
            if not conductor:
                return {"error": "Conductor not initialized"}
            return {
                "conversation_id": conductor.conversation_id,
                "history_id": conductor.history_id,
                "transcript_chars": conductor._transcript_chars,
                "compaction_count": conductor._compaction_count,
            }

    # ==================== CONVERSATION ROUTES ====================

    def _register_conversation_routes(self):
        @self.app.get("/conversations")
        async def list_conversations(limit: int = 20):
            from heaven_base.memory.conversations import list_chats
            return {"conversations": list_chats(limit=limit)}

        @self.app.get("/conversations/search")
        async def search_conversations(q: str):
            from heaven_base.memory.conversations import search_chats
            return {"conversations": search_chats(q)}

        @self.app.get("/conversations/{conversation_id}")
        async def get_conversation(conversation_id: str):
            from heaven_base.memory.conversations import load_chat
            conv = load_chat(conversation_id)
            return conv if conv else {"error": f"Conversation {conversation_id} not found"}

        @self.app.get("/conversations/{conversation_id}/histories")
        async def get_conversation_histories(conversation_id: str):
            from heaven_base.memory.conversations import ConversationManager
            return {"conversation_id": conversation_id, "histories": ConversationManager.get_conversation_histories(conversation_id)}

        @self.app.get("/conversations/{conversation_id}/latest")
        async def get_conversation_latest(conversation_id: str):
            from heaven_base.memory.conversations import get_latest_history
            history_id = get_latest_history(conversation_id)
            if not history_id:
                return {"error": f"Conversation {conversation_id} not found or empty"}
            return {"conversation_id": conversation_id, "latest_history_id": history_id}

        @self.app.delete("/conversations/{conversation_id}")
        async def delete_conversation(conversation_id: str):
            from heaven_base.memory.conversations import ConversationManager
            deleted = ConversationManager.delete_conversation(conversation_id)
            return {"deleted": conversation_id} if deleted else {"error": f"Not found"}

        @self.app.post("/conversations")
        async def create_conversation(data: Dict[str, Any]):
            from heaven_base.memory.conversations import start_chat
            title = data.get("title", "")
            first_history_id = data.get("first_history_id", "")
            agent_name = data.get("agent_name", "")
            tags = data.get("tags", [])
            if not title or not first_history_id or not agent_name:
                return {"error": "title, first_history_id, and agent_name required"}
            return start_chat(title, first_history_id, agent_name, tags)

        @self.app.post("/conversations/{conversation_id}/continue")
        async def continue_conversation(conversation_id: str, data: Dict[str, Any]):
            from heaven_base.memory.conversations import continue_chat
            new_history_id = data.get("history_id", "")
            if not new_history_id:
                return {"error": "history_id required"}
            try:
                return continue_chat(conversation_id, new_history_id)
            except FileNotFoundError:
                return {"error": f"Conversation {conversation_id} not found"}

        @self.app.get("/histories/{history_id}")
        async def get_history(history_id: str):
            from heaven_base.memory.history import History
            try:
                hist = History._load_history_file(history_id)
                return hist.to_json()
            except FileNotFoundError:
                return {"error": f"History {history_id} not found"}

        @self.app.get("/histories/{history_id}/markdown")
        async def get_history_markdown(history_id: str):
            from heaven_base.memory.history import History
            try:
                hist = History._load_history_file(history_id)
                return {"history_id": history_id, "markdown": hist.to_markdown()}
            except FileNotFoundError:
                return {"error": f"History {history_id} not found"}

        @self.app.get("/conversations/{conversation_id}/content")
        async def get_conversation_content(conversation_id: str):
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

    # ==================== RESEARCH DISPATCH ====================

    def _register_research_routes(self):
        ext = self

        @self.app.post("/research/run")
        async def dispatch_research(request: Request = None):
            """Dispatch next pending research to ResearcherAgent. Returns immediately.

            Two queue entry types:
            - START: no body or empty body → picks next pending investigation
            - RESUME: body with {investigation_name, history_id, grug_history_path, status}
              → writes resume entry to queue file, then processes
            """
            researcher = ext.cave.cave_agents.get("researcher")
            if not researcher:
                return {"error": "ResearcherAgent not registered in runtime"}

            # Parse grug callback — write RESUME to queue file directly
            if request:
                try:
                    body = await request.json()
                    if body and isinstance(body, dict) and body.get("grug_history_path"):
                        from observatory.runner import write_resume
                        write_resume(body)
                except Exception:
                    pass

            # Agent.run() is async — triggers observatory runner via DI'd runtime
            asyncio.create_task(researcher.run())

            return {"status": "dispatched"}

        @self.app.get("/research/status")
        async def research_queue_status():
            """View researcher status + queue."""
            researcher = ext.cave.cave_agents.get("researcher")
            if not researcher:
                return {"error": "ResearcherAgent not registered"}
            return researcher.status

    # ==================== GENERIC AGENT MESSAGE ====================

    def _register_agent_message_routes(self):
        ext = self

        @self.app.post("/agents/{agent_name}/message")
        async def agent_message(agent_name: str, request: Request):
            """Send a message to any registered CAVE agent's inbox.

            Generic endpoint — works for any agent in cave_agents.
            The agent's check_inbox() processes it via its DI'd runtime.
            Response delivered through agent's broadcast channels.

            Body: {"content": "message text", "source": "frontend", "priority": 0}
            """
            agent = ext.cave.cave_agents.get(agent_name)
            if not agent:
                return {"error": f"Agent '{agent_name}' not registered", "available": list(ext.cave.cave_agents.keys())}

            try:
                body = await request.json()
            except Exception:
                return {"error": "Request body must be JSON with 'content' field"}

            content = body.get("content", "")
            if not content:
                return {"error": "Message content is required"}

            from cave.core.agent import UserPromptMessage, IngressType
            msg = UserPromptMessage(
                content=content,
                ingress=IngressType.FRONTEND,
                source_id=body.get("source", "frontend"),
                priority=body.get("priority", 0),
            )

            success = agent.enqueue(msg)
            if not success:
                return {"error": f"Agent '{agent_name}' inbox full"}

            # Trigger processing
            import asyncio
            asyncio.create_task(agent.check_inbox())

            return {"status": "delivered", "agent": agent_name, "message_id": msg.id}

        @self.app.get("/agents/{agent_name}/status")
        async def agent_status(agent_name: str):
            """Get status of a specific CAVE agent."""
            agent = ext.cave.cave_agents.get(agent_name)
            if not agent:
                return {"error": f"Agent '{agent_name}' not registered"}

            return {
                "name": agent_name,
                "type": agent.__class__.__name__,
                "inbox_count": agent.inbox_count,
                "has_runtime": agent.runtime is not None,
                "channels": agent.central_channel.list_conversations() if agent.central_channel else [],
            }

    # ==================== STOP WATCHER ====================

    async def _conductor_stop_watcher(self):
        """Peek at conductor inbox for !stop even while conductor is busy processing.

        check_inbox() blocks during run_with_content(), so !stop sits unseen.
        This watcher checks every 2s and handles !stop immediately.
        """
        while True:
            try:
                conductor = self.cave.cave_agents.get("conductor")
                if conductor and getattr(conductor, '_processing', False):
                    # Peek at queued messages for !stop
                    inbox_queue = getattr(conductor.inbox, '_queue', None)
                    if inbox_queue:
                        for msg in list(inbox_queue):
                            raw = msg.content if hasattr(msg, 'content') else str(msg)
                            user_msg = conductor._extract_user_message(raw)
                            if user_msg.strip() == "!stop":
                                # Remove from inbox
                                try:
                                    inbox_queue.remove(msg)
                                except ValueError:
                                    pass
                                # Execute stop
                                result = conductor._handle_stop()
                                conductor._notify(result)
                                logger.info("Stop watcher: !stop processed")
                                break
            except Exception as e:
                logger.error("Stop watcher error: %s", e)
            await asyncio.sleep(2)

    # ==================== STARTUP ====================

    def _register_startup(self):
        ext = self
        cave = self.cave

        @self.app.on_event("startup")
        async def sancrev_startup():
            import time as _time
            ext.app.state.start_time = _time.time()

            # Register conductor agent instance for message routing
            wd_agent = cave.cave_agents.get("conductor")
            if wd_agent:
                ext._register_agent_instance("conductor", wd_agent)
                logger.info("ConductorAgent registered in sancrev agent instances")

            # Start Ears poll_loop
            if hasattr(cave, 'ears') and cave.ears:
                cave.ears.proprioception_rate = 2.0
                cave.ears.poll_interval = 2.0
                asyncio.create_task(cave.ears.poll_loop())
                logger.info("CaveAgent Ears poll_loop started (poll=2s)")

            # Register main agent in container registry
            ext._container_registry["main"] = PAIAContainerRegistration(
                agent_id="main",
                address=f"http://localhost:{cave.config.port}",
                paia_name="gnosys",
                metadata={"type": "tmux", "session": "claude"},
            )
            logger.info("Main agent registered in container_registry")

            # Start stop watcher — peeks at conductor inbox for !stop even while busy
            asyncio.create_task(ext._conductor_stop_watcher())
            logger.info("Conductor stop watcher started")

            # Auto-resume research queue if pending items exist
            researcher = cave.cave_agents.get("researcher")
            if researcher:
                from observatory.runner import get_status
                rs = get_status()
                if rs.get("queue_pending", 0) > 0 or rs.get("queue_resume", 0) > 0 or rs.get("queue_in_progress", 0) > 0:
                    asyncio.create_task(researcher.run())
                    logger.info("Auto-resumed research queue (pending=%d, resume=%d)",
                                rs.get("queue_pending", 0), rs.get("queue_resume", 0))

            logger.info("SancrevExtension startup complete")
