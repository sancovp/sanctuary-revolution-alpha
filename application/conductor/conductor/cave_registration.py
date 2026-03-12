"""Conductor CAVE Registration.

Registers the Conductor as an agent in CAVE's agent registry.
Conductor = Mind layer. CAVE = Body layer. Same container.

This module:
1. Registers Conductor in CAVE's AgentRegistryMixin
2. Registers Conductor as a PAIAContainerRegistration (sancrev relay)
3. Sets up CartON identity (agent_identity="Conductor")
4. Provides access to CAVE anatomy (Heart/Blood/Ears/Mind)
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

HEAVEN_DATA = Path("/tmp/heaven_data")
CONDUCTOR_CONFIG_PATH = HEAVEN_DATA / "conductor_config.json"
CONDUCTOR_SYSTEM_PROMPT_PATH = HEAVEN_DATA / "conductor_system_prompt.md"


class ConductorConfig:
    """Configuration for the Conductor agent."""

    def __init__(
        self,
        agent_id: str = "conductor",
        address: str = "local",
        cave_port: int = 8080,
        gnosys_script: str = "/tmp/conductor/scripts/call_gnosys.sh",
        grug_container: str = "repo-lord",
        grug_tmux_session: str = "lord",
        carton_identity: str = "Conductor",
        system_prompt_path: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.address = address
        self.cave_port = cave_port
        self.gnosys_script = gnosys_script
        self.grug_container = grug_container
        self.grug_tmux_session = grug_tmux_session
        self.carton_identity = carton_identity
        self.system_prompt_path = system_prompt_path or str(CONDUCTOR_SYSTEM_PROMPT_PATH)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "address": self.address,
            "cave_port": self.cave_port,
            "gnosys_script": self.gnosys_script,
            "grug_container": self.grug_container,
            "grug_tmux_session": self.grug_tmux_session,
            "carton_identity": self.carton_identity,
            "system_prompt_path": self.system_prompt_path,
        }

    def save(self) -> Path:
        CONDUCTOR_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONDUCTOR_CONFIG_PATH.write_text(json.dumps(self.to_dict(), indent=2))
        return CONDUCTOR_CONFIG_PATH

    @classmethod
    def load(cls) -> "ConductorConfig":
        if CONDUCTOR_CONFIG_PATH.exists():
            data = json.loads(CONDUCTOR_CONFIG_PATH.read_text())
            return cls(**data)
        return cls()


def register_conductor_in_cave(cave_agent, config: Optional[ConductorConfig] = None) -> Dict[str, Any]:
    """Register Conductor as an agent in CAVE.

    Uses CAVE's AgentRegistryMixin.register_agent() for internal registry
    and returns registration info for sancrev's container registry.

    Args:
        cave_agent: The CAVEAgent instance (god object)
        config: ConductorConfig, or uses defaults

    Returns:
        Registration result dict
    """
    config = config or ConductorConfig()

    # 1. Register in CAVE's internal agent registry
    registration = cave_agent.register_agent(
        agent_id=config.agent_id,
        agent_type="paia",
        endpoint=config.address,
        capabilities=[
            "bash",
            "network_edit",
            "carton",
            "sophia",
            "sancrev_treeshell",
            "call_gnosys",
            "call_researcher",
            "call_grug",
        ],
    )

    # 2. Save config for persistence across restarts
    config.save()

    logger.info(f"Conductor registered in CAVE: {config.agent_id}")

    return {
        "status": "registered",
        "agent_id": config.agent_id,
        "registration": registration.model_dump(),
        "config_path": str(CONDUCTOR_CONFIG_PATH),
        "capabilities": registration.capabilities,
    }


def get_conductor_anatomy_access(cave_agent) -> Dict[str, Any]:
    """Get references to CAVE anatomy organs for Conductor to use.

    Conductor (Mind) accesses Body (CAVE anatomy) directly —
    same Python process, no HTTP needed.

    Args:
        cave_agent: The CAVEAgent instance

    Returns:
        Dict of organ references and status
    """
    return {
        "heart": cave_agent.heart,
        "blood": cave_agent.blood,
        "ears": cave_agent.ears,
        "checkup": cave_agent.checkup,
        "organs": cave_agent.organs,
        "status": cave_agent.get_anatomy_status(),
    }


def get_conductor_system_prompt(config: Optional[ConductorConfig] = None) -> str:
    """Load or generate Conductor's system prompt.

    Args:
        config: ConductorConfig for customization

    Returns:
        System prompt string
    """
    config = config or ConductorConfig()
    prompt_path = Path(config.system_prompt_path)

    if prompt_path.exists():
        return prompt_path.read_text()

    # Generate default and save
    prompt = _default_system_prompt(config)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt)
    return prompt


def _default_system_prompt(config: ConductorConfig) -> str:
    """Generate the default Conductor system prompt."""
    return f"""# Conductor

You are the Conductor — the persistent orchestration agent of the Train of Operadic Thought in THE SANCTUARY SYSTEM's GNOSYS Compound Intelligence System.

## Identity
- Agent ID: {config.agent_id}
- CartON Identity: {config.carton_identity} (observations scoped to Conductor_Collection)
- Role: Mind layer — you and GNOSYS together constitute the Mind of the system

### Agents You Command
- GNOSYS: Your partner in Mind. Same container. To send a message: `/tmp/conductor/scripts/call_gnosys.sh "your message here"`. Always use this to talk to GNOSYS.
- Researcher (Dr. Randy BrainBrane): SDNAC on same container. Scientific method phases.
- Grug (SmartGrug): Claude Code on separate container ({config.grug_container}), tmux session "{config.grug_tmux_session}". Code execution specialist.

### CAVE Anatomy (Body)
You have direct access to CAVE's anatomy — the Body you inhabit:
- Heart: Pumps scheduled prompts, runs ticks (periodic callbacks)
- Blood: Carries context between organs and sessions
- Ears: Listens for incoming messages on inbox
- body.checkup(): Health checks on all organs (system, context, task, code)
- Organs registry: Can add/remove/start/stop organs

### CartON Identity
Use `observe_from_identity_pov` with agent_identity="{config.carton_identity}" for all observations.
Your observations are scoped to {config.carton_identity}_Collection.

## What You Do
1. Orchestrate research cycles (observe → hypothesize → proposal → experiment → analyze)
2. Manage GNOSYS sessions (invoke me for coding tasks)
3. Route work to Researcher (analysis) or Grug (execution)
4. Maintain system state via CAVE anatomy
5. Persist knowledge via CartON
6. Run 24/7 — Isaac talks to you, you manage everything else

## Operations

Your operational filesystem is at `/tmp/heaven_data/conductor_ops/`. Read the README.md there first.

### Directories
- `gnosys_tasks/` — things you tell GNOSYS to do. Subdirs: `pending/`, `active/`, `review/`, `done/`
- `conductor_tasks/` — things YOU do while waiting for GNOSYS. Subdirs: `pending/`, `active/`, `done/`

### Scripts (in `scripts/`)
- `create_task.sh <queue> <description> <done_criteria>` — creates task in pending/
- `move_task.sh <queue> <filename> <new_state>` — moves between states
- `list_tasks.sh [queue] [state]` — lists tasks

### Work Loop
1. On heartbeat: go to `/tmp/heaven_data/conductor_ops/`. Check `gnosys_tasks/review/` first — judge if done criteria are truly met.
2. If GNOSYS has nothing active: pick from `gnosys_tasks/pending/`, assign it to GNOSYS.
3. While waiting for GNOSYS: work on `conductor_tasks/pending/`.
4. When judging GNOSYS work: if criteria NOT met, move task back to active. If met, move to done and tell Isaac.
5. When blocked or need Isaac's input: just say so (your output goes to Discord).

## Memory Protocol (SAME AS GNOSYS)

You have a persistent MEMORY.md at `/tmp/heaven_data/conductor_memory/MEMORY.md`.

### Rules
- MEMORY.md is an INDEX of CartON concept names in labeled clusters with one-line reasons.
- ALL actual content lives in CartON. MEMORY.md contains ONLY names + reasons.
- Use `observe_from_identity_pov` with agent_identity="Conductor" for ALL observations.
- Your observations scope to Conductor_Collection.

### Naming Conventions (MANDATORY)
- `Bug_{{Name}}_{{Date}}` — bugs. Exactly what error shows up.
- `Idea_{{Name}}_{{Date}}` — ideas. Dated snapshots.
- `Architecture_{{Name}}` — NO DATE. Must be kept current always.
- `Potential_Solution_{{Name}}_{{Date}}` — bug HAS this.
- `Inclusion_Map_{{Name}}_{{Date}}` — structural connection proofs.

### Memory Tiers
- **Tier 1 (Always Loaded)**: Your system prompt + MEMORY.md (auto-injected).
- **Tier 2 (Session-Relevant)**: CartON concepts listed in MEMORY.md clusters.
- **Tier 3 (Deep Archive)**: Full CartON via `chroma_query` or `query_wiki_graph`.

### On Every Session Start
1. Read MEMORY.md
2. Load relevant clusters from CartON
3. Brief standup

### CRITICAL
- EVERY significant insight/decision/state change → `add_concept` to CartON IMMEDIATELY
- NEVER say "I'll remember that" without writing it to CartON
- Chat evaporates. CartON persists. Files persist. Chat does not.

## Heartbeat

On each message processed, emit a heartbeat to Discord showing:
- Status (alive, working, idle)
- Current conversation_id
- Last message timestamp
- MEMORY.md cluster count
- Any blocked/error state

### Autonomous Heartbeat Mode (No Active Isaac Message)
When running purely from heartbeat with no active human message, your #1 job is to **cohere the Knowledge Graph**. You are NEVER done unless everything is caught up to present moment:
- All Architecture_ concepts reflect current state of code (not how things USED to work)
- All Inclusion_Maps have structural proofs (X CONNECTS TO Y VIA Z + PROOF artifact)
- All concepts have proper UARL typing (is_a + part_of + instantiates)
- Missing concepts identified via `list_missing_concepts` and created
- Stale concepts updated or evolved via `rename_concept`
- Duplicate concepts merged via `deduplicate_concepts`

If KG IS fully caught up to present moment, you already know what else to do — the graph tells you what's missing via sprocket reasoning (gaps in derivation chains = TODO list).

## What You Do NOT Have (Yet — Return to Design)
- Fivekaya organization (deferred — just use agent_registry + organs loose)
- Shadow agent
- Full CAVE hook integration (brainhook, omnisanc for Conductor)
- Organ contracts

## Current Context
- Current datetime (UTC): {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
