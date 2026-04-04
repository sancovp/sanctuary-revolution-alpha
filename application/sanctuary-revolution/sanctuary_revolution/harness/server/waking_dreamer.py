"""WakingDreamer — The SANCREV implementation of CAVEAgent.

Singleton god object. Loads config from file. Hot-reloads changes.
IS svabhavikakaya (the unity of all kayas).

Agents edit config → WakingDreamer hot-reloads → behavior changes.

Usage:
    wd = WakingDreamer()
    # or with custom config:
    wd = WakingDreamer(config_path="/path/to/config.json")

From start_sancrev.py:
    from sanctuary_revolution.harness.server.waking_dreamer import WakingDreamer
    from cave.server.cave_http_server import CAVEHTTPServer
    wd = WakingDreamer()
    server = CAVEHTTPServer(cave=wd, port=8080)
    server.run()
"""
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from cave.core.cave_agent import CAVEAgent
from cave.core.config import CAVEConfig
from cave.core.models import CaveAgentEntry

logger = logging.getLogger(__name__)

# Default v1 agents config
V1_AGENTS_CONFIG = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "v1_agents.json"


class WakingDreamer(CAVEAgent):
    """Singleton SANCREV implementation of CAVEAgent.

    The god object. Lucid inside the cave.
    Has Conductor, Inner GNOSYS, Autobiographer, OpenClaw.
    Agents edit config → WakingDreamer hot-reloads → behavior changes.
    The system modifies itself. That's the reflective part.

    OVP (Omniscient Viewer Perspective) is not a separate agent —
    it's the USER's oversight perspective encoded into how
    WakingDreamer operates. Building OVP = teaching the
    WakingDreamer how the user sees.
    """

    _instance: Optional["WakingDreamer"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        config: Optional[CAVEConfig] = None,
        config_path: Optional[Path] = None,
        agents_config_path: Optional[Path] = None,
    ):
        # Singleton guard — don't re-init
        if hasattr(self, '_wd_initialized') and self._wd_initialized:
            return

        # Load config
        if config:
            cave_config = config
        elif config_path and config_path.exists():
            data = json.loads(config_path.read_text())
            cave_config = CAVEConfig.model_validate(data)
        else:
            cave_config = CAVEConfig.load()

        # Load agents from v1_agents.json if config.agents is empty
        agents_path = agents_config_path or V1_AGENTS_CONFIG
        if not cave_config.agents and agents_path.exists():
            self._load_agents_from_file(cave_config, agents_path)

        # Initialize CAVEAgent
        super().__init__(config=cave_config)

        # Config watching
        self._agents_config_path = agents_path
        self._config_watcher: Optional[threading.Thread] = None
        self._watching = False

        # Wire runtime backends for agents that have them
        self._wire_conductor_runtime()
        self._wire_journal_runtime()
        self._wire_researcher_runtime()

        # Disable legacy main_agent heartbeat tick — it sends prompts to
        # Inner GNOSYS (this tmux session) via send_keys, flooding the
        # interactive session. Conductor heartbeat goes through file inbox
        # via _wire_conductor_heartbeat(). Legacy tick is single-agent mode only.
        if hasattr(self, 'heart') and "heartbeat_prompt" in self.heart.ticks:
            self.heart.ticks["heartbeat_prompt"].enabled = False
            logger.info("Disabled legacy heartbeat_prompt tick (WakingDreamer manages heartbeats via channels)")

        self._wd_initialized = True
        logger.info(
            "WakingDreamer initialized: %d agents, port %d",
            len(self.cave_agents),
            self.config.port,
        )

    @staticmethod
    def _load_agents_from_file(config: CAVEConfig, path: Path) -> None:
        """Load agent entries from JSON file into config."""
        try:
            data = json.loads(path.read_text())
            agents_data = data.get("agents", [])
            config.agents = [CaveAgentEntry.model_validate(a) for a in agents_data]
            logger.info("Loaded %d agents from %s", len(config.agents), path)
        except Exception as e:
            logger.error("Failed to load agents config from %s: %s", path, e)

    # === RUNTIME WIRING ===

    def _wire_conductor_runtime(self):
        """Replace generic ChatAgent with ConductorAgent and init its runtime.

        ConductorAgent(ChatAgent) is the typed subclass that knows how to
        create and DI the Conductor runtime. WakingDreamer just calls init.
        """
        generic = self.cave_agents.get("conductor")
        if not generic:
            return

        try:
            from sanctuary_revolution.agents.conductor_agent import ConductorAgent

            # Create typed ConductorAgent with same config
            conductor_agent = ConductorAgent(config=generic.config)
            conductor_agent.central_channel = generic.central_channel

            # Init the Conductor runtime
            if conductor_agent.init_conductor(cave_agent=self):
                self._conductor_instance = conductor_agent.conductor
            else:
                logger.warning("ConductorAgent init_conductor returned False")

            # Replace generic with typed in registry
            self.cave_agents["conductor"] = conductor_agent
            logger.info("ConductorAgent replaced generic ChatAgent")

        except ImportError as e:
            logger.warning("ConductorAgent not available: %s", e)
        except Exception as e:
            logger.error("Failed to wire ConductorAgent: %s", e, exc_info=True)

    def _wire_journal_runtime(self):
        """Replace generic ChatAgent with JournalAgent and init its runtime.

        JournalAgent(ChatAgent) handles CHAT + JOURNAL modes for the
        autobiographer system. Same pattern as _wire_conductor_runtime.
        """
        generic = self.cave_agents.get("autobiographer")
        if not generic:
            return

        try:
            from sanctuary_revolution.agents.journal_agent import JournalAgent

            journal_agent = JournalAgent(config=generic.config)
            journal_agent.central_channel = generic.central_channel

            if journal_agent.init_runtime():
                logger.info("JournalAgent runtime initialized")
            else:
                logger.warning("JournalAgent init_runtime returned False")

            self.cave_agents["autobiographer"] = journal_agent
            logger.info("JournalAgent replaced generic ChatAgent for autobiographer")

        except ImportError as e:
            logger.warning("JournalAgent not available: %s", e)
        except Exception as e:
            logger.error("Failed to wire JournalAgent: %s", e, exc_info=True)

    def _wire_researcher_runtime(self):
        """Replace generic ServiceAgent with ResearcherAgent.

        ResearcherAgent(ServiceAgent) handles the research queue.
        Route /research/run dispatches to this agent.
        """
        generic = self.cave_agents.get("researcher")
        if not generic:
            return

        try:
            from sanctuary_revolution.agents.researcher_agent import ResearcherAgent

            researcher = ResearcherAgent(config=generic.config)
            researcher.central_channel = generic.central_channel
            researcher.init_runtime()

            self.cave_agents["researcher"] = researcher
            logger.info("ResearcherAgent replaced generic agent")

        except ImportError as e:
            logger.warning("ResearcherAgent not available: %s", e)
        except Exception as e:
            logger.error("Failed to wire ResearcherAgent: %s", e, exc_info=True)

    # === HOT RELOAD ===

    def reload_agents(self) -> Dict[str, Any]:
        """Reload agents from config file. Hot-reloads without restart."""
        if not self._agents_config_path or not self._agents_config_path.exists():
            return {"error": "no agents config path"}

        old_agents = set(self.cave_agents.keys())

        # Re-load config
        self._load_agents_from_file(self.config, self._agents_config_path)

        # Re-init agents
        self.cave_agents.clear()
        self.central_channels.clear()
        self._init_cave_agents()

        new_agents = set(self.cave_agents.keys())
        added = new_agents - old_agents
        removed = old_agents - new_agents

        logger.info("Hot-reloaded agents: added=%s, removed=%s", added, removed)
        return {
            "status": "reloaded",
            "agents": list(new_agents),
            "added": list(added),
            "removed": list(removed),
        }

    # === SINGLETON RESET (for testing) ===

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance. For testing only."""
        cls._instance = None
