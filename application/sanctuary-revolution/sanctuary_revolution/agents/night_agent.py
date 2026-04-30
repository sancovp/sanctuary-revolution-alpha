"""AutobiographerNight — Autobiographer NIGHT mode.

ServiceAgent subclass for autonomous processing. Three jobs:
- Job A: Missing days queue — query CartON timeline, find gaps, write queue file
- Job B: Journal contextualization — compile context, create Journal_Autocontext concept
- Job C: Friendship contextualization — gather timelines + TWIs, map hypotheses to narratives, build report

Pattern: SAME AS RESEARCHER. Thin CAVE shell. Runtime = async callable.
Triggered by: heartbeat (user AFK), cron (pre-journal/friendship), manual via HTTP endpoint.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from cave.core.agent import ServiceAgent

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
MISSING_DAYS_QUEUE = HEAVEN_DATA_DIR / "missing_days_queue.json"
def _get_night_model_config() -> dict:
    """Read model config from journal_agent_config.json. No hardcoded values."""
    _cfg_path = HEAVEN_DATA_DIR / "journal_agent_config.json"
    if _cfg_path.exists():
        try:
            return json.loads(_cfg_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}

_NIGHT_CFG = _get_night_model_config()
_NIGHT_MODEL = _NIGHT_CFG.get("model", "")
_NIGHT_API_URL = _NIGHT_CFG.get("extra_model_kwargs", {}).get("anthropic_api_url", "")


class AutobiographerNight(ServiceAgent):
    """MOV Night — autonomous deepening and contextualization.

    SAME PATTERN AS RESEARCHER: thin shell, runtime = async callable.
    Three jobs dispatched by job_type parameter.
    Night agent is the autonomous intelligence driving the autobiography forward.
    It scans gaps, notifies CHAT channel, compiles context for journals/friendship.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chat_channel_id: Optional[str] = None

    def set_chat_channel(self, channel_id: str) -> None:
        """Set the CHAT autobiographer's Discord channel for cross-notifications."""
        self._chat_channel_id = channel_id

    def init_runtime(self) -> bool:
        """DI the night processing callable as runtime."""
        try:
            night_agent_ref = self

            def _notify(text: str):
                """Notify via central_channel — same pattern as researcher."""
                if not night_agent_ref.central_channel:
                    return
                main_ch = night_agent_ref.central_channel.main()
                if not main_ch:
                    return
                try:
                    if len(text) <= 1900:
                        main_ch.deliver({"message": text})
                    else:
                        remaining = text
                        while remaining:
                            chunk = remaining[:1900]
                            remaining = remaining[1900:]
                            main_ch.deliver({"message": chunk})
                except Exception as e:
                    logger.error("AutobiographerNight notify error: %s", e)

            def _notify_chat(text: str):
                """Notify the CHAT autobiographer's Discord channel about gaps."""
                if not night_agent_ref._chat_channel_id:
                    logger.debug("No chat channel ID set, skipping chat notification")
                    return
                try:
                    from cave.core.channel import UserDiscordChannel
                    ch = UserDiscordChannel(channel_id=night_agent_ref._chat_channel_id)
                    if ch.token:
                        if len(text) <= 1900:
                            ch.deliver({"message": text})
                        else:
                            remaining = text
                            while remaining:
                                chunk = remaining[:1900]
                                remaining = remaining[1900:]
                                ch.deliver({"message": chunk})
                except Exception as e:
                    logger.error("AutobiographerNight chat notify error: %s", e)

            def _make_callback():
                """Create CompositeCallback that broadcasts every event to the night agent's Discord channel."""
                try:
                    from heaven_base.docs.examples.heaven_callbacks import BackgroundEventCapture, CompositeCallback
                    from conductor.event_broadcaster import EventBroadcaster, ConductorDiscordChannel
                    capture = BackgroundEventCapture()
                    main_ch = night_agent_ref.central_channel.main() if night_agent_ref.central_channel else None
                    if main_ch and hasattr(main_ch, 'channel_id') and main_ch.channel_id:
                        discord_ch = ConductorDiscordChannel(channel_id=main_ch.channel_id)
                        discord_ch.degree = "MOV_Night"
                        broadcaster = EventBroadcaster([discord_ch])
                        return CompositeCallback([capture, broadcaster]), capture
                    return capture, capture
                except ImportError:
                    from heaven_base.docs.examples.heaven_callbacks import BackgroundEventCapture
                    capture = BackgroundEventCapture()
                    return capture, capture

            async def _run_night(message=None):
                """Run night processing. Dispatches by job_type."""
                job_type = "missing_days"  # default
                if isinstance(message, dict):
                    job_type = message.get("job_type", "missing_days")
                elif isinstance(message, str):
                    if "friendship" in message.lower():
                        job_type = "friendship"
                    elif "contextualize" in message.lower():
                        job_type = "contextualize"

                if job_type == "missing_days":
                    return await _run_missing_days(on_notify=_notify, on_notify_chat=_notify_chat)
                elif job_type == "contextualize":
                    period = "morning"
                    if isinstance(message, dict):
                        period = message.get("period", "morning")
                    elif isinstance(message, str) and "evening" in message.lower():
                        period = "evening"
                    return await _run_contextualize(period=period, on_notify=_notify, make_callback=_make_callback)
                elif job_type == "friendship":
                    return await _run_friendship_contextualize(on_notify=_notify, make_callback=_make_callback)
                elif job_type == "content_production":
                    # STUB — future: produce blogs/demos/YouTube for completed VECs
                    _notify("📝 Content production not yet implemented — stubbed for future.")
                    return {"status": "stubbed", "job_type": "content_production"}
                else:
                    return {"status": "error", "error": f"Unknown job_type: {job_type}"}

            self.set_runtime(_run_night)
            logger.info("AutobiographerNight: runtime initialized")
            return True

        except Exception as e:
            logger.error("AutobiographerNight: failed to init runtime: %s", e, exc_info=True)
            return False

    @property
    def status(self) -> Dict[str, Any]:
        """Current night agent status."""
        queue_exists = MISSING_DAYS_QUEUE.exists()
        queue_count = 0
        if queue_exists:
            try:
                data = json.loads(MISSING_DAYS_QUEUE.read_text())
                queue_count = len(data) if data else 0
            except Exception:
                pass
        return {
            "queue_exists": queue_exists,
            "queue_count": queue_count,
            "queue_path": str(MISSING_DAYS_QUEUE),
        }


# ==================== JOB A: MISSING DAYS ====================

NOTIFIED_GAPS_FILE = HEAVEN_DATA_DIR / "notified_gaps.json"


def _load_notified_gaps() -> set:
    """Load previously notified gap periods to avoid spamming."""
    if not NOTIFIED_GAPS_FILE.exists():
        return set()
    try:
        return set(json.loads(NOTIFIED_GAPS_FILE.read_text()))
    except Exception:
        return set()


def _save_notified_gaps(notified: set):
    NOTIFIED_GAPS_FILE.write_text(json.dumps(sorted(notified)))


async def _run_missing_days(on_notify=None, on_notify_chat=None) -> Dict[str, Any]:
    """Query CartON for Day_ concepts, find gaps, write queue, notify CHAT.

    Smart notifications: only notify CHAT about NEW gaps not previously surfaced.
    The CHAT agent sees the full queue in its system prompt (missing_days_queue.json).
    """
    try:
        if on_notify:
            on_notify("🌙 **NIGHT MODE:** Scanning timeline for missing days...")

        # Query Neo4j for existing Day_ and Biographical_Memory concepts
        existing_days = set()
        memory_days = set()
        try:
            from carton_mcp.concept_config import ConceptConfig
            config = ConceptConfig()
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password))
            with driver.session() as session:
                # Check Day_ concepts
                result = session.run("MATCH (d:Wiki) WHERE d.n STARTS WITH 'Day_' RETURN d.n")
                for record in result:
                    existing_days.add(record["d.n"])
                # Check Biographical_Memory concepts linked to days
                result = session.run(
                    "MATCH (m:Wiki)-[:PART_OF]->(d:Wiki) "
                    "WHERE m.n STARTS WITH 'Biographical_Memory_' AND d.n STARTS WITH 'Day_' "
                    "RETURN DISTINCT d.n"
                )
                for record in result:
                    memory_days.add(record["d.n"])
            driver.close()
        except Exception as e:
            logger.warning("AutobiographerNight: Neo4j query failed: %s", e)

        # Build expected days (last 90 days)
        today = datetime.now().date()
        expected_days = set()
        for i in range(90):
            d = today - timedelta(days=i)
            expected_days.add(f"Day_{d.year}_{d.month:02d}_{d.day:02d}")

        # Find gaps — days with no memories
        all_known = existing_days | memory_days
        missing = sorted(expected_days - all_known, reverse=True)

        # Write queue
        queue_entries = []
        for day_name in missing[:30]:
            parts = day_name.replace("Day_", "").split("_")
            if len(parts) == 3:
                date_str = f"{parts[0]}-{parts[1]}-{parts[2]}"
            else:
                date_str = day_name
            queue_entries.append({
                "period": date_str,
                "day_concept": day_name,
                "note": "No memories found for this day",
            })

        MISSING_DAYS_QUEUE.write_text(json.dumps(queue_entries, indent=2))

        summary = (
            f"Timeline scan: {len(all_known)} days with data, "
            f"{len(missing)} gaps (last 90 days)."
        )
        logger.info("AutobiographerNight: %s", summary)
        if on_notify:
            on_notify(f"🌙 **NIGHT MODE:** {summary}")

        # Smart notification to CHAT — only NEW gaps
        if on_notify_chat and queue_entries:
            previously_notified = _load_notified_gaps()
            new_gaps = [e for e in queue_entries if e["period"] not in previously_notified]

            if new_gaps:
                # Pick top 5 most recent new gaps to surface
                top_gaps = new_gaps[:5]
                gap_list = "\n".join(f"• {g['period']}" for g in top_gaps)
                remaining = len(new_gaps) - len(top_gaps)
                more_text = f"\n(+{remaining} more)" if remaining > 0 else ""

                on_notify_chat(
                    f"🌙 **MOV Night found gaps in your timeline:**\n{gap_list}{more_text}\n\n"
                    f"When you get a chance, tell me what was happening during those times. "
                    f"Any memories — where you were, how you felt, what was going on."
                )

                # Mark as notified
                for g in new_gaps:
                    previously_notified.add(g["period"])
                _save_notified_gaps(previously_notified)

        return {"status": "success", "existing": len(all_known), "missing": len(missing)}

    except Exception as e:
        logger.error("AutobiographerNight missing_days error: %s", e, exc_info=True)
        if on_notify:
            on_notify(f"❌ **NIGHT MODE error:** {e}")
        return {"status": "error", "error": str(e)}


# ==================== JOB B: CONTEXTUALIZE ====================

async def _run_contextualize(period: str = "morning", on_notify=None, make_callback=None) -> Dict[str, Any]:
    """Compile context for upcoming journal session.

    Creates Journal_Autocontext_{Morning|Evening}_{date} concept in CartON.
    Uses BaseHeavenAgent with CartON MCP for intelligent compilation.
    """
    try:
        from heaven_base.baseheavenagent import BaseHeavenAgent, HeavenAgentConfig
        from heaven_base.unified_chat import UnifiedChat

        today = datetime.now().strftime("%Y_%m_%d")
        period_cap = period.capitalize()
        concept_name = f"Journal_Autocontext_{period_cap}_{today}"

        if on_notify:
            on_notify(f"🌙 **NIGHT MODE:** Contextualizing for {period} journal...")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        system_prompt = (
            f"You are MOV_Night. Your job: compile context for Isaac's {period} journal.\n"
            f"It is currently {now_str}.\n\n"
            f"## Step 1: Read the last 2 weeks of journals\n"
            f'query_wiki_graph("MATCH (j:Wiki)-[:PART_OF]->(:Wiki {{n:\'User_Autobiography_Timeline\'}}) '
            f"WHERE j.n STARTS WITH 'Journal_Entry_' RETURN j.n, substring(j.d,0,500) ORDER BY j.t DESC LIMIT 14\")\n\n"
            f"## Step 2: Read recent biographical memories\n"
            f'query_wiki_graph("MATCH (m:Wiki)-[:PART_OF]->(:Wiki {{n:\'User_Autobiography_Timeline\'}}) '
            f"WHERE m.n STARTS WITH 'Biographical_Memory_' RETURN m.n, substring(m.d,0,300) ORDER BY m.t DESC LIMIT 10\")\n\n"
            f"## Step 3: Read what GNOSYS worked on recently\n"
            f"get_recent_concepts(n=20, timeline='chat')\n\n"
            f"## Step 4: Read the webs of the most important things\n"
            f"For the 3-5 concepts that seem most important for the upcoming journal "
            f"(by contextual expectations — what Isaac will care about), call:\n"
            f"get_concept_network(concept_name, depth=1)\n"
            f"This gives you the connected web so you understand the full picture.\n\n"
            f"## Step 5: Compile the context brief\n"
            f"Your FINAL message IS the context that gets injected into the journal agent.\n"
            f"Write it as a briefing: what happened since the last journal, key themes, "
            f"what's connected to what, and what to ask Isaac about.\n\n"
            f"Also save it to CartON:\n"
            f"add_concept(concept_name='{concept_name}', is_a=['Journal_Autocontext'], "
            f"part_of=['Day_{today}'], "
            f"instantiates=['Journal_Autocontext'], concept='<your compiled brief>')\n\n"
            f"## NEVER\n"
            f"- NEVER call journal_entry() or deposit_memory(). You are READ-ONLY.\n"
            f"- NEVER make up data. If a query returns nothing, say so.\n"
        )

        config = HeavenAgentConfig(
            name="night_contextualizer",
            system_prompt=system_prompt,
            tools=[],
            model=_NIGHT_MODEL,
            use_uni_api=False,
            max_tokens=4000,
            extra_model_kwargs={"anthropic_api_url": _NIGHT_API_URL},
            mcp_servers={
                "carton": {
                    "command": "carton-mcp",
                    "args": [],
                    "transport": "stdio",
                },
            },
        )

        agent = BaseHeavenAgent(
            config=config,
            unified_chat=UnifiedChat(),
            max_tool_calls=20,
        )

        # Broadcast every event to night agent's Discord channel (same pattern as Conductor)
        if make_callback:
            composite, capture = make_callback()
        else:
            from heaven_base.docs.examples.heaven_callbacks import BackgroundEventCapture
            capture = BackgroundEventCapture()
            composite = capture

        result = await agent.run(
            prompt=f"Compile context for Isaac's {period} journal session. Create the {concept_name} concept.",
            heaven_main_callback=composite,
        )

        # Extract agent's final response — this IS the autocontext
        agent_messages = capture.get_events_by_type("AGENT_MESSAGE")
        autocontext_text = ""
        if agent_messages:
            autocontext_text = agent_messages[-1].get("data", {}).get("content", "")

        # Write to file for journal trigger to read
        autocontext_path = HEAVEN_DATA_DIR / f"journal_autocontext_{period}.txt"
        autocontext_path.write_text(autocontext_text or f"Night agent compiled {concept_name} but no summary was captured.")

        summary = f"Contextualization complete: {concept_name}"
        logger.info("AutobiographerNight: %s", summary)
        if on_notify:
            on_notify(f"🌙 **NIGHT MODE:** {summary}")

        return {"status": "success", "concept": concept_name, "autocontext_file": str(autocontext_path)}

    except Exception as e:
        logger.error("AutobiographerNight contextualize error: %s", e, exc_info=True)
        if on_notify:
            on_notify(f"❌ **NIGHT MODE error:** {e}")
        return {"status": "error", "error": str(e)}


# ==================== JOB C: FRIENDSHIP CONTEXTUALIZE ====================

async def _run_friendship_contextualize(on_notify=None, make_callback=None) -> Dict[str, Any]:
    """Gather timelines + TWIs, map hypotheses to narratives, build Friendship report.

    Creates Friendship_Autocontext_{date} concept in CartON.
    Uses BaseHeavenAgent with CartON MCP for intelligent analysis.
    Pings user when report is ready.
    """
    try:
        from heaven_base.baseheavenagent import BaseHeavenAgent, HeavenAgentConfig
        from heaven_base.unified_chat import UnifiedChat

        today = datetime.now().strftime("%Y_%m_%d")
        concept_name = f"Friendship_Autocontext_{today}"

        if on_notify:
            on_notify("🤝 **FRIENDSHIP MODE:** Building weekly report...")

        system_prompt = (
            f"You are MOV in NIGHT mode, preparing the weekly Friendship report.\n"
            f"Today is {datetime.now().strftime('%Y-%m-%d')}.\n\n"
            f"Steps:\n"
            f"1. Query the three timelines for this week's activity:\n"
            f"   - get_recent_concepts(n=30, timeline='odyssey') — what the system learned\n"
            f"   - get_recent_concepts(n=15, timeline='system') — background system health\n"
            f"   - get_recent_concepts(n=15, timeline='chat') — what was worked on\n"
            f"2. Read current TWIs: get_concept('Claude_Code_Rule_Twi_Global_Intents')\n"
            f"3. Read recent TWI hypotheses:\n"
            f"   query_wiki_graph(\"MATCH (t:Wiki)-[:IS_A]->(:Wiki {{n: 'Twi_Hypothesis'}}) "
            f"RETURN t.n, t.d ORDER BY t.t DESC LIMIT 10\")\n"
            f"4. Read recent Episodes/narratives:\n"
            f"   query_wiki_graph(\"MATCH (e:Wiki)-[:IS_A]->(:Wiki {{n: 'Episode'}}) "
            f"RETURN e.n, e.d ORDER BY e.t DESC LIMIT 10\")\n"
            f"5. Query recent Odyssey learning decisions:\n"
            f"   query_wiki_graph(\"MATCH (d:Wiki)-[:IS_A]->(:Wiki {{n: 'Odyssey_Learning_Decision'}}) "
            f"RETURN d.n, substring(d.d, 0, 200) ORDER BY d.t DESC LIMIT 5\")\n"
            f"6. Query recent Odyssey narrative analyses:\n"
            f"   query_wiki_graph(\"MATCH (a:Wiki)-[:IS_A]->(:Wiki {{n: 'Odyssey_Narrative_Analysis'}}) "
            f"RETURN a.n, substring(a.d, 0, 200) ORDER BY a.t DESC LIMIT 5\")\n\n"
            f"Include these Odyssey outputs in your friendship report under a section called "
            f"'## System Narrative (Odyssey Output)' — this gives the friendship ritual the full picture "
            f"of what the system's ML pipeline concluded this week.\n"
            f"7. For each existing TWI, find evidence on the timelines that it was followed or violated\n"
            f"6. Compile everything into one concept using add_concept():\n"
            f"   concept_name='{concept_name}'\n"
            f"   is_a=['Friendship_Autocontext']\n"
            f"   part_of=['Day_{today}']\n"
            f"   instantiates=['Friendship_Autocontext']\n"
            f"   description should include:\n"
            f"   - BUILT this week: key deliverables, concepts, skills\n"
            f"   - LEARNED this week: episodes, TWI hypotheses, odyssey decisions\n"
            f"   - SYSTEM HEALTH: daemon activity, errors, gaps\n"
            f"   - TWI MAPPING: for each TWI, evidence for/against from timelines\n"
            f"   - SUGGESTED ACTIONS: what might need to change\n\n"
            f"Be thorough. This report is what Isaac reviews during the Friendship ritual."
        )

        config = HeavenAgentConfig(
            name="night_friendship",
            system_prompt=system_prompt,
            tools=[],
            model=_NIGHT_MODEL,
            use_uni_api=False,
            max_tokens=6000,
            extra_model_kwargs={"anthropic_api_url": _NIGHT_API_URL},
            mcp_servers={
                "carton": {
                    "command": "carton-mcp",
                    "args": [],
                    "transport": "stdio",
                },
            },
        )

        agent = BaseHeavenAgent(
            config=config,
            unified_chat=UnifiedChat(),
            max_tool_calls=30,
        )

        if make_callback:
            composite, capture = make_callback()
        else:
            composite = None

        result = await agent.run(
            prompt=f"Build the weekly Friendship report. Create the {concept_name} concept.",
            **({"heaven_main_callback": composite} if composite else {}),
        )

        summary = f"Friendship report ready: {concept_name}"
        logger.info("AutobiographerNight: %s", summary)
        if on_notify:
            on_notify(f"🤝 **FRIENDSHIP READY:** Weekly report compiled. Time for the ritual! Use /friendship-ritual")

        return {"status": "success", "concept": concept_name}

    except Exception as e:
        logger.error("AutobiographerNight friendship error: %s", e, exc_info=True)
        if on_notify:
            on_notify(f"❌ **FRIENDSHIP error:** {e}")
        return {"status": "error", "error": str(e)}
