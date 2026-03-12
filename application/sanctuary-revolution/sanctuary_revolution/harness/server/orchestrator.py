#!/usr/bin/env python3
"""
DEPRECATED: This module is obsolete.

The docker.sock orchestrator pattern was eliminated when we moved to HTTP-everything.
Container communication now happens via http_server.py endpoints directly.

Use http_server.py as the game server backend. It handles:
- Frontend API (PAIAB/CAVE/SANCTUM endpoints)
- SSE events
- Relay to other containers via HTTP

n8n handles docker.sock for workflow automation if needed.

---
Original docstring (historical reference):

PAIA Orchestrator Server

Control plane for multi-agent Claude Code system.
- Spawns/manages agent containers
- Routes messages between agents via llegos
- Maintains global state visibility
- Provides dashboard data

Run on host, Electron boots this as subprocess.
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import docker
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

ORCHESTRATOR_PORT = 8420
CONTAINER_HANDOFF_PORT = 8421
PAIA_PAIA_NETWORK_NAME = "paia-network"
SHARED_VOLUME = "/tmp/paia-shared"
PAIA_PAIA_AGENT_IMAGE = "paia-agent:latest"  # Base image with claude cli + handoff server

# ============================================================================
# Models
# ============================================================================

class PAIAContainerConfig(BaseModel):
    """Configuration for spawning a PAIA agent in a Docker container."""
    agent_id: str
    persona: str | None = None
    claude_md_path: str | None = None
    hooks_dir: str | None = None
    env_vars: dict[str, str] = Field(default_factory=dict)


class PAIAContainerState(BaseModel):
    """Current state of a PAIA agent container."""
    agent_id: str
    container_id: str | None = None
    status: str = "stopped"  # stopped, starting, running, error
    last_activity: datetime | None = None
    inbox_count: int = 0
    current_task: str | None = None
    error: str | None = None


class PAIAMessage(BaseModel):
    """Message between PAIA agent containers."""
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "default"
    priority: int = 5
    metadata: dict[str, Any] = Field(default_factory=dict)


class PAIAExecuteRequest(BaseModel):
    """Request to execute code in a PAIA agent container."""
    agent_id: str
    code: str
    language: str = "python"  # python or bash


# ============================================================================
# Global State
# ============================================================================

class PAIAPAIAOrchestratorState:
    """Global orchestrator state."""

    def __init__(self):
        self.agents: dict[str, PAIAContainerState] = {}
        self.docker_client: docker.DockerClient | None = None
        self.message_queue: dict[str, list[Message]] = {}  # agent_id -> messages
        self.history: list[dict] = []  # All messages for observability

    def init_docker(self):
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
            self._ensure_network()
            self._ensure_shared_volume()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to initialize Docker: {e}")
            raise

    def _ensure_network(self):
        """Ensure Docker network exists."""
        try:
            self.docker_client.networks.get(PAIA_NETWORK_NAME)
        except docker.errors.NotFound:
            self.docker_client.networks.create(PAIA_NETWORK_NAME, driver="bridge")
            logger.info(f"Created Docker network: {PAIA_NETWORK_NAME}")

    def _ensure_shared_volume(self):
        """Ensure shared volume directory exists."""
        shared = Path(SHARED_VOLUME)
        shared.mkdir(parents=True, exist_ok=True)
        (shared / "inboxes").mkdir(exist_ok=True)
        (shared / "history").mkdir(exist_ok=True)
        (shared / "network").mkdir(exist_ok=True)
        logger.info(f"Shared volume ready: {SHARED_VOLUME}")


state = PAIAOrchestratorState()

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="PAIA Orchestrator",
    description="Control plane for multi-agent Claude Code system",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    state.init_docker()


# ============================================================================
# Agent Management Routes
# ============================================================================

@app.post("/agents/spawn_andor_attach")
async def spawn_andor_attach(config: PAIAContainerConfig, attach: bool = False) -> dict:
    """Spawn agent if not running, optionally return attach command."""
    result = {}

    # Check if already running
    if config.agent_id in state.agents:
        existing = state.agents[config.agent_id]
        if existing.status == "running":
            result["spawned"] = False
            result["agent"] = existing.model_dump()
        else:
            # Exists but stopped - respawn
            agent_state = await _do_spawn(config)
            result["spawned"] = True
            result["agent"] = agent_state.model_dump()
    else:
        # New agent
        agent_state = await _do_spawn(config)
        result["spawned"] = True
        result["agent"] = agent_state.model_dump()

    if attach:
        result["attach_cmd"] = f"docker exec -it paia-agent-{config.agent_id} tmux attach -t claude"

    return result


async def _do_spawn(config: PAIAContainerConfig) -> PAIAContainerState:
    """Internal spawn logic."""
    # Create agent state
    agent_state = PAIAContainerState(
        agent_id=config.agent_id,
        status="starting",
        last_activity=datetime.now()
    )
    state.agents[config.agent_id] = agent_state

    # Prepare inbox directory
    inbox_dir = Path(SHARED_VOLUME) / "inboxes" / config.agent_id
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # Container environment
    env = {
        "AGENT_ID": config.agent_id,
        "ORCHESTRATOR_URL": f"http://host.docker.internal:{ORCHESTRATOR_PORT}",
        "INBOX_DIR": f"/shared/inboxes/{config.agent_id}",
        "HANDOFF_PORT": str(CONTAINER_HANDOFF_PORT),
        **config.env_vars
    }

    if config.persona:
        env["PERSONA"] = config.persona

    # Volume mounts
    volumes = {
        SHARED_VOLUME: {"bind": "/shared", "mode": "rw"},
    }

    if config.claude_md_path:
        volumes[config.claude_md_path] = {"bind": "/agent/CLAUDE.md", "mode": "ro"}
    if config.hooks_dir:
        volumes[config.hooks_dir] = {"bind": "/agent/.claude/hooks", "mode": "ro"}

    try:
        container = state.docker_client.containers.run(
            PAIA_AGENT_IMAGE,
            detach=True,
            name=f"paia-agent-{config.agent_id}",
            environment=env,
            volumes=volumes,
            network=PAIA_NETWORK_NAME,
            ports={f"{CONTAINER_HANDOFF_PORT}/tcp": None},
            remove=True,
        )

        agent_state.container_id = container.id
        agent_state.status = "running"
        logger.info(f"Spawned agent {config.agent_id}: {container.id[:12]}")

    except docker.errors.DockerException as e:
        agent_state.status = "error"
        agent_state.error = str(e)
        logger.error(f"Failed to spawn agent {config.agent_id}: {e}")
        raise HTTPException(500, f"Failed to spawn agent: {e}")

    return agent_state


@app.post("/agents/spawn")
async def spawn_agent(config: PAIAContainerConfig) -> PAIAContainerState:
    """Spawn a new agent container."""
    if config.agent_id in state.agents:
        existing = state.agents[config.agent_id]
        if existing.status == "running":
            raise HTTPException(400, f"Agent {config.agent_id} already running")

    # Create agent state
    agent_state = PAIAContainerState(
        agent_id=config.agent_id,
        status="starting",
        last_activity=datetime.now()
    )
    state.agents[config.agent_id] = agent_state

    # Prepare inbox directory
    inbox_dir = Path(SHARED_VOLUME) / "inboxes" / config.agent_id
    inbox_dir.mkdir(parents=True, exist_ok=True)

    # Container environment
    env = {
        "AGENT_ID": config.agent_id,
        "ORCHESTRATOR_URL": f"http://host.docker.internal:{ORCHESTRATOR_PORT}",
        "INBOX_DIR": f"/shared/inboxes/{config.agent_id}",
        "HANDOFF_PORT": str(CONTAINER_HANDOFF_PORT),
        **config.env_vars
    }

    if config.persona:
        env["PERSONA"] = config.persona

    # Volume mounts
    volumes = {
        SHARED_VOLUME: {"bind": "/shared", "mode": "rw"},
    }

    if config.claude_md_path:
        volumes[config.claude_md_path] = {"bind": "/agent/CLAUDE.md", "mode": "ro"}
    if config.hooks_dir:
        volumes[config.hooks_dir] = {"bind": "/agent/.claude/hooks", "mode": "ro"}

    try:
        container = state.docker_client.containers.run(
            PAIA_AGENT_IMAGE,
            detach=True,
            name=f"paia-agent-{config.agent_id}",
            environment=env,
            volumes=volumes,
            network=PAIA_NETWORK_NAME,
            ports={f"{CONTAINER_HANDOFF_PORT}/tcp": None},  # Dynamic port
            remove=True,
        )

        agent_state.container_id = container.id
        agent_state.status = "running"
        logger.info(f"Spawned agent {config.agent_id}: {container.id[:12]}")

    except docker.errors.DockerException as e:
        agent_state.status = "error"
        agent_state.error = str(e)
        logger.error(f"Failed to spawn agent {config.agent_id}: {e}")
        raise HTTPException(500, f"Failed to spawn agent: {e}")

    return agent_state


@app.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str) -> dict:
    """Stop an agent container."""
    if agent_id not in state.agents:
        raise HTTPException(404, f"Agent {agent_id} not found")

    agent_state = state.agents[agent_id]
    if not agent_state.container_id:
        raise HTTPException(400, f"Agent {agent_id} has no container")

    try:
        container = state.docker_client.containers.get(agent_state.container_id)
        container.stop(timeout=10)
        agent_state.status = "stopped"
        agent_state.container_id = None
        logger.info(f"Stopped agent {agent_id}")
    except docker.errors.NotFound:
        agent_state.status = "stopped"
        agent_state.container_id = None
    except docker.errors.DockerException as e:
        logger.error(f"Failed to stop agent {agent_id}: {e}")
        raise HTTPException(500, f"Failed to stop agent: {e}")

    return {"status": "stopped", "agent_id": agent_id}


@app.get("/agents/{agent_id}/state")
async def get_agent_state(agent_id: str) -> PAIAContainerState:
    """Get current state of an agent."""
    if agent_id not in state.agents:
        raise HTTPException(404, f"Agent {agent_id} not found")

    agent_state = state.agents[agent_id]

    # Update inbox count
    inbox_dir = Path(SHARED_VOLUME) / "inboxes" / agent_id
    if inbox_dir.exists():
        agent_state.inbox_count = len(list(inbox_dir.glob("*.json")))

    return agent_state


@app.get("/agents")
async def list_agents() -> dict[str, PAIAContainerState]:
    """List all agents and their states."""
    return state.agents


# ============================================================================
# Message Routing
# ============================================================================

@app.post("/messages/send")
async def send_message(message: Message) -> dict:
    """Send a message from one agent to another."""
    # Validate target agent exists
    if message.to_agent not in state.agents:
        # Create inbox anyway - agent might spawn later
        logger.warning(f"Target agent {message.to_agent} not registered")

    # Write to inbox
    inbox_dir = Path(SHARED_VOLUME) / "inboxes" / message.to_agent
    inbox_dir.mkdir(parents=True, exist_ok=True)

    msg_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{message.from_agent}"
    msg_file = inbox_dir / f"{msg_id}.json"

    msg_data = {
        "id": msg_id,
        "from": message.from_agent,
        "to": message.to_agent,
        "content": message.content,
        "type": message.message_type,
        "priority": message.priority,
        "metadata": message.metadata,
        "timestamp": datetime.now().isoformat(),
    }

    msg_file.write_text(json.dumps(msg_data, indent=2))

    # Record in history for observability
    state.history.append(msg_data)

    # Also write to shared history
    history_file = Path(SHARED_VOLUME) / "history" / f"{msg_id}.json"
    history_file.write_text(json.dumps(msg_data, indent=2))

    logger.info(f"Message sent: {message.from_agent} -> {message.to_agent}")

    return {"status": "sent", "message_id": msg_id}


@app.get("/messages/inbox/{agent_id}")
async def get_inbox(agent_id: str) -> list[dict]:
    """Get all messages in an agent's inbox."""
    inbox_dir = Path(SHARED_VOLUME) / "inboxes" / agent_id
    if not inbox_dir.exists():
        return []

    messages = []
    for msg_file in sorted(inbox_dir.glob("*.json")):
        try:
            messages.append(json.loads(msg_file.read_text()))
        except json.JSONDecodeError:
            logger.warning(f"Invalid message file: {msg_file}")

    return messages


@app.delete("/messages/inbox/{agent_id}/{message_id}")
async def ack_message(agent_id: str, message_id: str) -> dict:
    """Acknowledge (delete) a message from inbox."""
    inbox_dir = Path(SHARED_VOLUME) / "inboxes" / agent_id
    msg_file = inbox_dir / f"{message_id}.json"

    if msg_file.exists():
        msg_file.unlink()
        return {"status": "acknowledged", "message_id": message_id}

    raise HTTPException(404, f"Message {message_id} not found")


# ============================================================================
# Code Execution
# ============================================================================

@app.post("/agents/{agent_id}/execute")
async def execute_in_agent(agent_id: str, request: ExecuteRequest) -> dict:
    """Execute code in an agent container via handoff HTTP."""
    if agent_id not in state.agents:
        raise HTTPException(404, f"Agent {agent_id} not found")

    agent_state = state.agents[agent_id]
    if agent_state.status != "running":
        raise HTTPException(400, f"Agent {agent_id} not running")

    # Get container's mapped port
    try:
        container = state.docker_client.containers.get(agent_state.container_id)
        ports = container.ports
        handoff_port = ports.get(f"{CONTAINER_HANDOFF_PORT}/tcp", [{}])[0].get("HostPort")

        if not handoff_port:
            raise HTTPException(500, "Container handoff port not mapped")

        # Call handoff endpoint
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://localhost:{handoff_port}/execute",
                json={"code": request.code, "language": request.language},
                timeout=60.0
            )
            return resp.json()

    except docker.errors.NotFound:
        agent_state.status = "error"
        agent_state.error = "Container not found"
        raise HTTPException(404, "Agent container not found")
    except Exception as e:
        logger.error(f"Execute failed for {agent_id}: {e}")
        raise HTTPException(500, f"Execution failed: {e}")


# ============================================================================
# Global State / Dashboard
# ============================================================================

@app.get("/network/status")
async def network_status() -> dict:
    """Get global network status for dashboard."""
    running = sum(1 for a in state.agents.values() if a.status == "running")
    total_messages = len(state.history)

    # Count pending messages per agent
    pending = {}
    inbox_base = Path(SHARED_VOLUME) / "inboxes"
    if inbox_base.exists():
        for inbox in inbox_base.iterdir():
            if inbox.is_dir():
                pending[inbox.name] = len(list(inbox.glob("*.json")))

    return {
        "agents": {
            "total": len(state.agents),
            "running": running,
            "stopped": len(state.agents) - running,
        },
        "messages": {
            "total_sent": total_messages,
            "pending_by_agent": pending,
        },
        "agents_detail": {aid: a.model_dump() for aid, a in state.agents.items()},
    }


@app.get("/history")
async def get_history(limit: int = 100, agent: str | None = None) -> list[dict]:
    """Get message history for observability."""
    history = state.history[-limit:]

    if agent:
        history = [m for m in history if m["from"] == agent or m["to"] == agent]

    return history


# ============================================================================
# Agent Callback (containers call this)
# ============================================================================

@app.post("/callback/state")
async def agent_state_callback(agent_id: str, status: str, task: str | None = None) -> dict:
    """Callback from agent container to report state."""
    if agent_id in state.agents:
        state.agents[agent_id].status = status
        state.agents[agent_id].current_task = task
        state.agents[agent_id].last_activity = datetime.now()
    return {"received": True}


# ============================================================================
# Transcript Tracking (stop hooks call this)
# ============================================================================

class PAIATranscriptCallback(BaseModel):
    transcript_path: str
    agent_id: str = "main"
    reason: str = "unknown"


_agent_transcripts: dict[str, list[dict]] = {}


@app.post("/callback/transcript")
async def transcript_callback(data: PAIATranscriptCallback) -> dict:
    """Callback from stop hook with transcript path."""
    if data.agent_id not in _agent_transcripts:
        _agent_transcripts[data.agent_id] = []
    _agent_transcripts[data.agent_id].append({
        "path": data.transcript_path,
        "reason": data.reason,
        "timestamp": datetime.now().isoformat()
    })
    _agent_transcripts[data.agent_id] = _agent_transcripts[data.agent_id][-50:]
    logger.info(f"Transcript from {data.agent_id}: {data.transcript_path}")
    return {"received": True}


@app.get("/transcripts/{agent_id}")
async def get_transcripts(agent_id: str, limit: int = 10) -> list[dict]:
    """Get recent transcripts for an agent."""
    return _agent_transcripts.get(agent_id, [])[-limit:]


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Run the orchestrator server."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=ORCHESTRATOR_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
