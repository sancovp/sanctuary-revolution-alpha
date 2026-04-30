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

        # Load agents from v1_agents.json — generate scaffold if missing
        agents_path = agents_config_path or V1_AGENTS_CONFIG
        if not cave_config.agents:
            if agents_path.exists():
                self._load_agents_from_file(cave_config, agents_path)
            else:
                self._generate_agents_scaffold(agents_path)

        # Initialize CAVEAgent
        super().__init__(config=cave_config)

        # Config watching
        self._agents_config_path = agents_path
        self._config_watcher: Optional[threading.Thread] = None
        self._watching = False

        # Wire runtime backends for agents that have them
        self._wire_conductor_runtime()
        self._wire_journal_runtime()
        self._wire_journal_runtime(agent_name="autobiographer_journal", default_mode="journal_morning")
        self._wire_researcher_runtime()
        self._wire_night_runtime()
        self._wire_odyssey_runtime()
        self._wire_narrative_runtime()

        # Wire conductor heartbeat tick (file inbox delivery on interval)
        self._wire_conductor_heartbeat()

        # Disable legacy main_agent heartbeat tick — it sends prompts to
        # Inner GNOSYS (this tmux session) via send_keys, flooding the
        # interactive session. Conductor heartbeat goes through file inbox
        # via _wire_conductor_heartbeat(). Legacy tick is single-agent mode only.
        if hasattr(self, 'heart') and "heartbeat_prompt" in self.heart.ticks:
            self.heart.ticks["heartbeat_prompt"].enabled = False
            logger.info("Disabled legacy heartbeat_prompt tick (WakingDreamer manages heartbeats via channels)")

        # Wire journal completion → sanctum ritual auto-done + rituals channel notify
        self._wire_journal_completion_watcher()

        # Wire sanctuary degree calculator (recomputes SD every 10 min)
        self._wire_sanctuary_degree_tick()

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

    @staticmethod
    def _generate_agents_scaffold(path: Path) -> None:
        """Generate v1_agents.json scaffold from model. Fails loud — user must fill in values."""
        scaffold = {
            "agents": [
                {"name": "conductor", "agent_type": "chat", "channels": {"main": {"type": "discord", "channel_id": ""}}},
                {"name": "gnosys", "agent_type": "code", "command": "claude", "tmux_session": "lord", "channels": {"main": {"type": "tmux", "session": "lord"}}},
                {"name": "autobiographer", "agent_type": "chat", "channel_mode": "complete_mirror", "channels": {"main": {"type": "discord", "channel_id": ""}}},
                {"name": "autobiographer_journal", "agent_type": "chat", "channel_mode": "complete_mirror", "channels": {"main": {"type": "discord", "channel_id": ""}}},
                {"name": "researcher", "agent_type": "service", "channel_mode": "notify", "channels": {"main": {"type": "discord", "channel_id": ""}}},
                {"name": "autobiographer_night", "agent_type": "service", "channel_mode": "notify", "channels": {"main": {"type": "discord", "channel_id": ""}}},
                {"name": "openclaw", "agent_type": "claw", "channels": {"main": {"type": "discord", "channel_id": ""}}},
            ]
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scaffold, indent=2))
        raise RuntimeError(
            f"Generated agent config scaffold at {path}. "
            f"Fill in all channel_id values and restart."
        )

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

    def _wire_journal_runtime(self, agent_name: str = "autobiographer", default_mode: str = "chat"):
        """Replace generic ChatAgent with JournalAgent and init its runtime.

        JournalAgent(ChatAgent) handles CHAT/JOURNAL/FRIENDSHIP modes.
        Called once per autobiographer agent (chat + journal are separate agents).
        Same pattern as _wire_conductor_runtime.
        """
        generic = self.cave_agents.get(agent_name)
        if not generic:
            return

        try:
            from sanctuary_revolution.agents.journal_agent import JournalAgent

            journal_agent = JournalAgent(config=generic.config)
            journal_agent.central_channel = generic.central_channel
            journal_agent.set_mode(default_mode)

            if journal_agent.init_runtime():
                logger.info("JournalAgent runtime initialized for %s (mode=%s)", agent_name, default_mode)
            else:
                logger.warning("JournalAgent init_runtime returned False for %s", agent_name)

            self.cave_agents[agent_name] = journal_agent
            logger.info("JournalAgent replaced generic ChatAgent for %s", agent_name)

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

    def _wire_night_runtime(self):
        """Replace generic ServiceAgent with AutobiographerNight.

        AutobiographerNight(ServiceAgent) handles autonomous deepening + contextualization.
        Same pattern as _wire_researcher_runtime.
        Also wires: chat channel for cross-notifications, nightly scan tick.
        """
        generic = self.cave_agents.get("autobiographer_night")
        if not generic:
            return

        try:
            from sanctuary_revolution.agents.night_agent import AutobiographerNight

            night = AutobiographerNight(config=generic.config)
            night.central_channel = generic.central_channel
            night.init_runtime()

            # Wire chat channel for cross-notifications (night → chat)
            chat_agent = self.cave_agents.get("autobiographer")
            if chat_agent and chat_agent.central_channel:
                main_ch = chat_agent.central_channel.main()
                if main_ch and hasattr(main_ch, 'channel_id'):
                    night.set_chat_channel(main_ch.channel_id)
                    logger.info("AutobiographerNight: chat channel wired for cross-notifications")

            self.cave_agents["autobiographer_night"] = night

            # Add all night agent ticks (scan + journal ctx + friendship ctx)
            self._wire_night_agent_ticks(night)

            logger.info("AutobiographerNight replaced generic agent")

        except ImportError as e:
            logger.warning("AutobiographerNight not available: %s", e)
        except Exception as e:
            logger.error("Failed to wire AutobiographerNight: %s", e, exc_info=True)

    def _wire_night_agent_ticks(self, night_agent):
        """Heart ticks for night agent jobs: missing days scan, journal/friendship contextualization."""
        from cave.core.mixins.anatomy import Tick
        import asyncio

        # Read journal times from config
        journal_config_path = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "sanctuary" / "journal_config.json"
        morning_hour, morning_min = 13, 0  # defaults (UTC)
        night_hour, night_min = 1, 0
        if journal_config_path.exists():
            try:
                jc = json.loads(journal_config_path.read_text())
                mh, mm = map(int, jc.get("morning_time", "13:00").split(":"))
                nh, nm = map(int, jc.get("night_time", "01:00").split(":"))
                morning_hour, morning_min = mh, mm
                night_hour, night_min = nh, nm
            except Exception:
                pass

        fired_today = {"scan": None, "ctx_morning": None, "ctx_evening": None, "ctx_friendship": None}

        def _fire_async(job_type, **kwargs):
            try:
                msg = {"job_type": job_type, **kwargs}
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(night_agent.run_with_content(msg))
                else:
                    loop.run_until_complete(night_agent.run_with_content(msg))
            except Exception as e:
                logger.error("Night agent tick error (%s): %s", job_type, e)

        def _night_agent_tick():
            from datetime import datetime as _dt
            now = _dt.now()
            today_str = now.strftime("%Y-%m-%d")
            hour, minute = now.hour, now.minute
            day_of_week = now.strftime("%A").lower()

            # Job A: Missing days scan — once per day during night hours
            if fired_today["scan"] != today_str and 1 <= hour <= 12:
                fired_today["scan"] = today_str
                logger.info("Night tick: triggering missing days scan")
                _fire_async("missing_days")

            # Job B morning: Contextualize 30 min before morning journal
            target_min = morning_hour * 60 + morning_min - 30
            current_min = hour * 60 + minute
            if fired_today["ctx_morning"] != today_str and abs(current_min - target_min) < 3:
                fired_today["ctx_morning"] = today_str
                logger.info("Night tick: triggering morning contextualization")
                _fire_async("contextualize", period="morning")

            # Job B evening: Contextualize 30 min before night journal
            target_min = night_hour * 60 + night_min - 30
            if target_min < 0:
                target_min += 24 * 60
            if fired_today["ctx_evening"] != today_str and abs(current_min - target_min) < 3:
                fired_today["ctx_evening"] = today_str
                logger.info("Night tick: triggering evening contextualization")
                _fire_async("contextualize", period="evening")

            # Job C: Friendship contextualize — Saturday, 1 hour before morning
            if day_of_week == "saturday":
                target_min = morning_hour * 60 + morning_min - 60
                if fired_today["ctx_friendship"] != today_str and abs(current_min - target_min) < 3:
                    fired_today["ctx_friendship"] = today_str
                    logger.info("Night tick: triggering friendship contextualization")
                    _fire_async("friendship")

        self.heart.add_tick(Tick(
            name="night_agent_jobs",
            callback=_night_agent_tick,
            every=60.0,  # Check every minute
        ))
        logger.info("Night agent ticks installed (scan + journal ctx + friendship ctx)")

    def _wire_odyssey_runtime(self):
        """Install OdysseyOrgan into the anatomy system.

        OdysseyOrgan auto-verifies BUILD output via adversarial SDNAC agents.
        Triggered by observation_worker_daemon when done_signal concepts appear.
        """
        try:
            from odyssey.core import OdysseyOrgan

            organ = OdysseyOrgan()
            self.add_organ(organ)
            logger.info("OdysseyOrgan installed (enabled=%s)", organ.enabled)

        except ImportError as e:
            logger.warning("OdysseyOrgan not available: %s", e)
        except Exception as e:
            logger.error("Failed to wire OdysseyOrgan: %s", e, exc_info=True)

    def _wire_narrative_runtime(self):
        """Install NarrativeOrgan — periodic narrative harvest from L5 summaries.

        Detects unnarrated Executive_Summary concepts in CartON, queues them,
        and processes via SDNAC harvest agents (Episode → Journey → Epic → Odyssey).
        """
        try:
            from odyssey.narrative_organ import NarrativeOrgan

            organ = NarrativeOrgan()
            self.add_organ(organ)
            organ.start()
            logger.info("NarrativeOrgan installed and started")

        except ImportError as e:
            logger.warning("NarrativeOrgan not available: %s", e)
        except Exception as e:
            logger.error("Failed to wire NarrativeOrgan: %s", e, exc_info=True)

    # === SANCTUARY DEGREE TICK ===

    def _wire_sanctuary_degree_tick(self):
        """Heart tick: recompute Sanctuary Degree every 10 minutes.

        Reads ritual completions from CartON, computes SD float,
        writes sanctuary_degree.json + conductor orientation prompt.
        Also runs once on startup.
        """
        from cave.core.mixins.anatomy import Tick

        def _sd_tick():
            try:
                from cave.core.sanctuary_degree_calculator import compute_sanctuary_degree
                result = compute_sanctuary_degree()
                logger.debug("SD tick: %.3f → %s", result["sd"], result["degree"])
            except Exception as e:
                logger.warning("SD tick error: %s", e)

        # Run once now on startup
        _sd_tick()

        self.heart.add_tick(Tick(
            name="sanctuary_degree",
            callback=_sd_tick,
            every=600.0,  # Every 10 minutes
        ))
        logger.info("Sanctuary degree tick installed (every 10min)")

    # === JOURNAL COMPLETION WATCHER ===

    _JOURNAL_TYPE_TO_RITUAL = {
        "opening": "morning-journal",
        "closing": "night-journal",
        "friendship": "friendship-saturday",
    }

    def _wire_journal_completion_watcher(self):
        """Heart tick: watch journal marker files → auto-complete sanctum rituals.

        # TRIGGERS: SD calculator + sanctum ritual completion via file write to /tmp/heaven_data/sanctuary/journals/
        journal_entry() MCP writes markers to /tmp/heaven_data/sanctuary/journals/.
        This tick detects new ones, marks the corresponding ritual done,
        and notifies the rituals Discord channel.
        """
        from cave.core.mixins.anatomy import Tick

        JOURNALS_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "sanctuary" / "journals"
        PROCESSED_FILE = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "sanctuary" / "journals_processed.json"
        wd_ref = self

        def _load_processed() -> set:
            if PROCESSED_FILE.exists():
                try:
                    return set(json.loads(PROCESSED_FILE.read_text()))
                except Exception:
                    pass
            return set()

        def _save_processed(processed: set):
            PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
            PROCESSED_FILE.write_text(json.dumps(sorted(processed)))

        def _journal_completion_tick():
            if not JOURNALS_DIR.exists():
                return

            processed = _load_processed()
            new_markers = [
                f for f in JOURNALS_DIR.glob("*.json")
                if f.name not in processed and f.name != "journals_processed.json"
            ]

            if not new_markers:
                return

            from datetime import datetime as _dt
            today_prefix = _dt.now().strftime("%Y_%m_%d")

            for marker_file in new_markers:
                try:
                    # Only process today's markers — old ones should not trigger today's rituals
                    if not marker_file.name.startswith(today_prefix):
                        processed.add(marker_file.name)
                        continue

                    data = json.loads(marker_file.read_text())
                    entry_type = data.get("entry_type", "")
                    ritual_name = wd_ref._JOURNAL_TYPE_TO_RITUAL.get(entry_type)

                    if ritual_name:
                        # Mark ritual done in sanctum
                        from cave.core.sanctum_cli import handle_done
                        result = handle_done(ritual_name)
                        logger.info("Journal completion → sanctum done: %s → %s", entry_type, result)

                        # Notify rituals channel
                        sanctum_cli = wd_ref.mini_clis.get("sanctum")
                        if sanctum_cli:
                            sanctum_cli.notify(f"📝 {result}")

                    processed.add(marker_file.name)
                except Exception as e:
                    logger.error("Journal completion watcher error for %s: %s", marker_file.name, e)
                    processed.add(marker_file.name)  # Don't retry broken files

            _save_processed(processed)

        self.heart.add_tick(Tick(
            name="journal_completion_watcher",
            callback=_journal_completion_tick,
            every=30.0,
        ))
        logger.info("Journal completion watcher tick installed (every 30s)")

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
