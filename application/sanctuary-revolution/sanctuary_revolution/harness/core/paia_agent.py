"""
PAIAAgent - Code agent that executes a PAIABlueprint.

PAIAAgent = CodeAgent + Blueprint + Instance GEAR

The compilation pattern:
1. Blueprint defines what PAIA SHOULD have (from paia-builder)
2. Agent EXECUTES blueprint - creates actual code files
3. Instance GEAR tracks compilation progress
4. check_win() signals compilation complete
5. Docker commit creates evolved image

This is NOT about adding components to paia-builder.
The blueprint is ALREADY DEFINED. Agent's job is to REALIZE it.
"""

import json
import logging
import os
import subprocess
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from pydantic import Field

from .agent import CodeAgent, CodeAgentConfig, Message, CompletedMessage, BlockedMessage

logger = logging.getLogger(__name__)

# Try to import paia-builder models
try:
    from paia_builder.models import PAIA, GEAR, AchievementTier, GoldenStatus, ComponentBase
    from paia_builder.core import PAIABuilder
    from paia_builder import utils as paia_utils
    HAS_PAIA_BUILDER = True
except ImportError as e:
    logger.debug(f"paia-builder not available: {e}\n{traceback.format_exc()}")
    HAS_PAIA_BUILDER = False
    PAIA = None
    GEAR = None


# =============================================================================
# PAIA AGENT CONFIG
# =============================================================================

@dataclass
class PAIAAgentConfig(CodeAgentConfig):
    """Configuration for a PAIA agent.

    Extends CodeAgentConfig with blueprint and compilation settings.
    """
    # Blueprint location
    blueprint_path: str = ""  # Path to paia.json
    working_dir: str = ""     # Where agent creates files (packaged into image)

    # Compilation settings
    auto_commit_on_win: bool = False  # Auto docker commit when check_win() == True
    commit_tag_prefix: str = "paia"   # Docker image tag prefix

    # State tracking
    gear_state_file: str = ""  # Where to persist instance GEAR

    # Claude Code specifics
    tmux_session: str = "paia-agent"
    response_marker: str = "❯"


# =============================================================================
# COMPILATION STATE
# =============================================================================

class CompilationState:
    """Tracks the compilation progress of a PAIA.

    This is the INSTANCE state (what the agent has actually built),
    separate from the BLUEPRINT state (what it should build).
    """

    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # Track what's been created
        self.created_files: List[str] = []
        self.created_components: Dict[str, List[str]] = {
            "skills": [],
            "mcps": [],
            "hooks": [],
            "commands": [],
            "agents": [],
            "personas": [],
            "plugins": [],
            "flights": [],
        }

        # Instance GEAR - separate from blueprint GEAR
        self.instance_gear: Optional[Any] = None  # GEAR instance if available

    def start(self):
        """Mark compilation as started."""
        self.started_at = datetime.now()

    def complete(self):
        """Mark compilation as complete."""
        self.completed_at = datetime.now()

    def register_file(self, path: str):
        """Register a created file."""
        self.created_files.append(path)

    def register_component(self, comp_type: str, name: str):
        """Register a created component."""
        if comp_type in self.created_components:
            self.created_components[comp_type].append(name)

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for persistence."""
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_files": self.created_files,
            "created_components": self.created_components,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], working_dir: Path) -> "CompilationState":
        """Deserialize state from persistence."""
        state = cls(working_dir)
        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])
        state.created_files = data.get("created_files", [])
        state.created_components = data.get("created_components", state.created_components)
        return state


# =============================================================================
# PAIA AGENT
# =============================================================================

class PAIAAgent(CodeAgent):
    """Code agent that executes a PAIABlueprint.

    PAIAAgent = CodeAgent + Blueprint + Instance State

    The agent's job:
    1. Load blueprint (what PAIA should have)
    2. Execute blueprint (create actual files)
    3. Track progress (instance GEAR)
    4. Signal completion (check_win)
    5. Enable docker commit (evolved image)

    This agent does NOT modify paia-builder.
    It REALIZES the blueprint into actual code.
    """

    config: PAIAAgentConfig = Field(default_factory=PAIAAgentConfig)

    # Blueprint (loaded from paia.json)
    _blueprint: Optional[Any] = None  # PAIA model if available
    _blueprint_raw: Dict[str, Any] = {}  # Raw JSON fallback

    # Compilation state (instance tracking)
    _compilation: Optional[CompilationState] = None

    # PAIABuilder reference (for tracking, not adding)
    _builder: Optional[Any] = None

    def __init__(self, config: Optional[PAIAAgentConfig] = None, **kwargs):
        super().__init__(config=config or PAIAAgentConfig(), **kwargs)

        # Initialize working directory
        if self.config.working_dir:
            self._working_path = Path(self.config.working_dir)
            self._working_path.mkdir(parents=True, exist_ok=True)
        else:
            self._working_path = Path.cwd()

        # Initialize compilation state
        self._compilation = CompilationState(self._working_path)

        # Load blueprint if path provided
        if self.config.blueprint_path:
            self._load_blueprint()

        # Initialize builder if available (for tracking only)
        if HAS_PAIA_BUILDER:
            self._builder = PAIABuilder()

    # ==================== BLUEPRINT OPERATIONS ====================

    def _load_blueprint(self) -> bool:
        """Load PAIABlueprint from paia.json."""
        path = Path(self.config.blueprint_path)
        if not path.exists():
            self.emit("blueprint:not_found", {"path": str(path)})
            return False

        try:
            self._blueprint_raw = json.loads(path.read_text())

            # Try to load as PAIA model if available
            if HAS_PAIA_BUILDER and PAIA:
                self._blueprint = PAIA(**self._blueprint_raw)
                self.emit("blueprint:loaded", {
                    "name": self._blueprint.name,
                    "level": self._blueprint.gear_state.level,
                    "components": len(self._blueprint.all_components())
                })
            else:
                self.emit("blueprint:loaded_raw", {
                    "name": self._blueprint_raw.get("name", "unknown"),
                    "keys": list(self._blueprint_raw.keys())
                })

            return True

        except Exception as e:
            self.emit("blueprint:load_error", {"error": str(e)})
            return False

    @property
    def blueprint(self) -> Optional[Any]:
        """Get the loaded blueprint (PAIA model or raw dict)."""
        return self._blueprint or self._blueprint_raw

    @property
    def blueprint_name(self) -> str:
        """Get blueprint name."""
        if self._blueprint:
            return self._blueprint.name
        return self._blueprint_raw.get("name", "unknown")

    @property
    def blueprint_level(self) -> int:
        """Get blueprint target level."""
        if self._blueprint:
            return self._blueprint.gear_state.level
        gear = self._blueprint_raw.get("gear_state", {})
        return gear.get("level", 1)

    # ==================== COMPILATION OPERATIONS ====================

    def start_compilation(self):
        """Start the compilation process."""
        self._compilation.start()
        self.emit("compilation:started", {
            "blueprint": self.blueprint_name,
            "target_level": self.blueprint_level,
            "working_dir": str(self._working_path)
        })

    def register_created_file(self, path: str):
        """Register a file created during compilation."""
        self._compilation.register_file(path)
        self.emit("compilation:file_created", {"path": path})

    def register_created_component(self, comp_type: str, name: str):
        """Register a component created during compilation."""
        self._compilation.register_component(comp_type, name)
        self.emit("compilation:component_created", {
            "type": comp_type,
            "name": name
        })

        # Update paia-builder tracking (not adding, just advancing tier)
        if self._builder and self._blueprint:
            try:
                # This advances the component in the blueprint, marking it as built
                self._builder.select(self.blueprint_name)
                self._builder.advance_tier(
                    comp_type, name,
                    f"Component realized during compilation at {datetime.now().isoformat()}"
                )
            except Exception as e:
                self.emit("builder:track_error", {"error": str(e)})

    def get_remaining_components(self) -> Dict[str, List[str]]:
        """Get components from blueprint not yet created."""
        remaining = {}

        if self._blueprint:
            for comp_type in ["skills", "mcps", "hooks", "commands",
                           "agents", "personas", "plugins", "flights"]:
                blueprint_comps = [c.name for c in getattr(self._blueprint, comp_type, [])]
                created_comps = self._compilation.created_components.get(comp_type, [])
                not_created = [c for c in blueprint_comps if c not in created_comps]
                if not_created:
                    remaining[comp_type] = not_created
        elif self._blueprint_raw:
            for comp_type in ["skills", "mcps", "hooks", "commands",
                           "agents", "personas", "plugins", "flights"]:
                blueprint_comps = [c.get("name") for c in self._blueprint_raw.get(comp_type, [])]
                created_comps = self._compilation.created_components.get(comp_type, [])
                not_created = [c for c in blueprint_comps if c and c not in created_comps]
                if not_created:
                    remaining[comp_type] = not_created

        return remaining

    def compilation_progress(self) -> Dict[str, Any]:
        """Get compilation progress report."""
        remaining = self.get_remaining_components()
        total_remaining = sum(len(v) for v in remaining.values())

        created = self._compilation.created_components
        total_created = sum(len(v) for v in created.values())

        total = total_remaining + total_created
        progress = (total_created / total * 100) if total > 0 else 0

        return {
            "blueprint": self.blueprint_name,
            "target_level": self.blueprint_level,
            "progress_pct": round(progress, 1),
            "created": total_created,
            "remaining": total_remaining,
            "remaining_by_type": remaining,
            "files_created": len(self._compilation.created_files),
            "is_complete": total_remaining == 0
        }

    # ==================== CHECK WIN ====================

    def check_win(self) -> bool:
        """Check if compilation is complete.

        Returns True when all blueprint components have been realized.
        This signals readiness for docker commit.
        """
        remaining = self.get_remaining_components()
        is_complete = len(remaining) == 0

        if is_complete and not self._compilation.is_complete:
            self._compilation.complete()
            self.emit("compilation:complete", {
                "blueprint": self.blueprint_name,
                "files_created": len(self._compilation.created_files),
                "ready_for_commit": True
            })

            # Auto commit if configured
            if self.config.auto_commit_on_win:
                self.docker_commit()

        return is_complete

    # ==================== DOCKER OPERATIONS ====================

    def get_container_id(self) -> Optional[str]:
        """Get current container ID (if running in Docker)."""
        # Method 1: Check hostname (often equals container ID)
        hostname = os.environ.get("HOSTNAME", "")
        if len(hostname) == 12 and all(c in "0123456789abcdef" for c in hostname):
            return hostname

        # Method 2: Check cgroup
        try:
            cgroup = Path("/proc/1/cgroup").read_text()
            for line in cgroup.splitlines():
                if "docker" in line:
                    return line.split("/")[-1][:12]
        except:
            pass

        return None

    def docker_commit(self, tag: Optional[str] = None) -> Optional[str]:
        """Commit current container as new image.

        Returns the new image tag if successful.
        """
        container_id = self.get_container_id()
        if not container_id:
            self.emit("docker:not_in_container", {})
            return None

        # Generate tag
        if not tag:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tag = f"{self.config.commit_tag_prefix}-{self.blueprint_name}:{timestamp}"

        try:
            result = subprocess.run(
                ["docker", "commit", container_id, tag],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                self.emit("docker:committed", {
                    "container_id": container_id,
                    "image_tag": tag
                })
                return tag
            else:
                self.emit("docker:commit_failed", {
                    "error": result.stderr
                })
                return None

        except Exception as e:
            self.emit("docker:commit_error", {"error": str(e)})
            return None

    # ==================== STATE PERSISTENCE ====================

    def save_state(self):
        """Persist compilation state to disk."""
        if not self.config.gear_state_file:
            state_path = self._working_path / ".paia_compilation_state.json"
        else:
            state_path = Path(self.config.gear_state_file)

        state_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "agent_id": self.id,
            "blueprint_name": self.blueprint_name,
            "blueprint_level": self.blueprint_level,
            "compilation": self._compilation.to_dict(),
            "saved_at": datetime.now().isoformat()
        }

        state_path.write_text(json.dumps(state, indent=2))
        self.emit("state:saved", {"path": str(state_path)})

    def load_state(self) -> bool:
        """Load compilation state from disk."""
        if not self.config.gear_state_file:
            state_path = self._working_path / ".paia_compilation_state.json"
        else:
            state_path = Path(self.config.gear_state_file)

        if not state_path.exists():
            return False

        try:
            state = json.loads(state_path.read_text())
            self._compilation = CompilationState.from_dict(
                state.get("compilation", {}),
                self._working_path
            )
            self.emit("state:loaded", {"path": str(state_path)})
            return True
        except Exception as e:
            logger.error(f"Failed to load state: {e}\n{traceback.format_exc()}")
            self.emit("state:load_error", {"error": str(e), "traceback": traceback.format_exc()})
            return False

    # ==================== MESSAGE HANDLERS ====================

    def receive_blocked_message(self, message: BlockedMessage) -> Iterator[Message]:
        """Handle blocked state during compilation.

        When agent hits a block, we save state and signal to host.
        """
        self.save_state()
        self.emit("compilation:blocked", {
            "reason": message.reason,
            "progress": self.compilation_progress()
        })
        yield from []

    # ==================== LIFECYCLE ====================

    def start(self):
        """Start PAIA agent - load blueprint and begin compilation."""
        super().start()

        if not self._blueprint and not self._blueprint_raw:
            if self.config.blueprint_path:
                self._load_blueprint()

        # Try to load existing state
        self.load_state()

        # Start compilation if not already started
        if not self._compilation.started_at:
            self.start_compilation()

        self.emit("paia_agent:started", {
            "blueprint": self.blueprint_name,
            "progress": self.compilation_progress()
        })

    def stop(self):
        """Stop PAIA agent - save state."""
        self.save_state()
        super().stop()


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_paia_agent(
    blueprint_path: str,
    working_dir: str,
    agent_command: str = "claude",
    **kwargs
) -> PAIAAgent:
    """Create a PAIAAgent from a blueprint file.

    Args:
        blueprint_path: Path to paia.json
        working_dir: Where agent creates files
        agent_command: Command to run the code agent
        **kwargs: Additional config options

    Returns:
        Configured PAIAAgent ready to start
    """
    config = PAIAAgentConfig(
        blueprint_path=blueprint_path,
        working_dir=working_dir,
        agent_command=agent_command,
        **kwargs
    )
    return PAIAAgent(config=config)


def load_blueprint(path: str) -> Dict[str, Any]:
    """Load and return blueprint without creating agent."""
    return json.loads(Path(path).read_text())
