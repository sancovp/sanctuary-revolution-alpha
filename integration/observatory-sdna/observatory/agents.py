"""Researcher agent factory — CompoctopusAgent pattern.

Chain of 5 SDNACs (one per scientific method phase) + 1 FunctionLink (Grug dispatch).
Phase sequencing controlled by Chain, not by LLM state machine.
CartON carries context between phases via researcher_mcp tools.

Architecture:
    CompoctopusAgent "researcher"
      └── ResearcherChain "researcher_chain"
          ├── SDNAC "observe"          — gather data, record to CartON
          ├── SDNAC "hypothesize"      — form hypotheses, record
          ├── SDNAC "propose"          — design experiments for Grug
          ├── FunctionLink "dispatch_grug" — send to Grug, get results
          ├── SDNAC "experiment"       — review Grug results, record
          └── SDNAC "analyze"          — final synthesis, conclusions

Each SDNAC is a fresh LLM conversation. No KeywordBasedStateMachine.
The Chain IS the state machine — Python controls phase transitions.
Between PROPOSE and EXPERIMENT, the FunctionLink dispatches work to Grug.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .config import DEFAULT_MODEL, PHASES

logger = logging.getLogger(__name__)


# =============================================================================
# ResearcherChain — Chain subclass that passes **kwargs (on_message) through
# =============================================================================

from sdna.chain_ontology import Chain, LinkResult, LinkStatus


class ResearcherChain(Chain):
    """Chain that passes kwargs (including on_message) to each link.

    Standard Chain.execute() doesn't forward **kwargs to link.execute().
    SDNAC.execute() needs on_message for EventBroadcaster callbacks.
    This subclass forwards all kwargs so each SDNAC gets the callback.
    """

    async def execute(self, context: Optional[Dict[str, Any]] = None,
                      start_from: int = 0, on_phase_complete=None, **kwargs):
        ctx = dict(context) if context else {}

        for i, link in enumerate(self.links):
            # Skip already-completed phases on restart
            if i < start_from:
                logger.info("ResearcherChain: skipping link %d/%d (already completed): %s",
                            i + 1, len(self.links), getattr(link, 'name', '?'))
                continue

            logger.info("ResearcherChain: executing link %d/%d: %s",
                        i + 1, len(self.links), getattr(link, 'name', '?'))
            result = await link.execute(ctx, **kwargs)
            ctx = result.context if hasattr(result, 'context') else ctx

            status = result.status if hasattr(result, 'status') else None
            if str(status) not in ("success", "LinkStatus.SUCCESS", "SDNAStatus.SUCCESS"):
                if hasattr(result, 'resume_path'):
                    result.resume_path = [i] + (result.resume_path or [])
                logger.warning("ResearcherChain: link %s returned %s, stopping chain",
                               getattr(link, 'name', '?'), status)
                return result

            logger.info("ResearcherChain: link %s completed successfully",
                        getattr(link, 'name', '?'))

            # Notify caller so they can persist progress
            if on_phase_complete:
                on_phase_complete(i, getattr(link, 'name', '?'))

            # After EXPERIMENT phase: stop chain, wait for grug callback to resume
            link_name = getattr(link, 'name', '')
            if 'experiment' in link_name.lower() and i < len(self.links) - 1:
                logger.info("ResearcherChain: EXPERIMENT done — pausing for grug callback")
                return LinkResult(status=LinkStatus.SUCCESS, context=ctx)

        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)


# =============================================================================
# MCP servers config
# =============================================================================

def _get_researcher_mcp_servers():
    """MCP servers for the researcher agent — researcher_mcp (write + read CartON)."""
    import shutil
    mcp_bin = shutil.which("researcher-mcp")
    if not mcp_bin:
        raise RuntimeError("researcher-mcp console script not found. pip install observatory-sdna.")
    return {
        "researcher": {
            "command": mcp_bin,
            "args": [],
            "transport": "stdio",
        },
    }


# =============================================================================
# Phase SDNAC factory — one SDNAC per scientific method phase
# =============================================================================

RESEARCHER_MEMORY_PATH = "/tmp/heaven_data/observatory/researcher_memory.md"
RESEARCHER_CONCEPTS_PATH = "/tmp/heaven_data/observatory/researcher_prior_concepts.md"


def _ensure_memory_files():
    """Ensure researcher memory files exist on disk."""
    from pathlib import Path
    Path(RESEARCHER_MEMORY_PATH).parent.mkdir(parents=True, exist_ok=True)
    if not Path(RESEARCHER_MEMORY_PATH).exists():
        Path(RESEARCHER_MEMORY_PATH).write_text("# Researcher Memory\n\nNo entries yet.\n")
    if not Path(RESEARCHER_CONCEPTS_PATH).exists():
        _refresh_prior_concepts()


def _refresh_prior_concepts():
    """Query CartON for last 100 investigation concepts and write to file."""
    from pathlib import Path
    content = "# Prior Investigation Concepts\n\nNo prior concepts found.\n"
    try:
        from carton_mcp.carton_utils import query_wiki_graph
        result = query_wiki_graph(
            "MATCH (n:Wiki)-[:PART_OF]->(c:Wiki {n: 'Researcher_Collection'}) "
            "RETURN n.n AS name ORDER BY n.t DESC LIMIT 100"
        )
        if result and isinstance(result, list):
            names = [r.get("name", "") for r in result if r.get("name")]
            if names:
                content = "# Prior Investigation Concepts (last 100)\n" + "\n".join(f"- {n}" for n in names)
    except Exception:
        pass
    Path(RESEARCHER_CONCEPTS_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(RESEARCHER_CONCEPTS_PATH).write_text(content)


def _make_phase_hermes(phase_name, system_prompt, goal, model=DEFAULT_MODEL, max_turns=15, variable_inputs=None):
    """Build a HermesConfig for a single research phase — NO state machine.

    Uses prompt_suffix_blocks to dynamically inject researcher memory and
    prior concepts into the system prompt each turn. The LLM sees these
    automatically — no file reading needed. Updates persist across phases.
    """
    from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
    from heaven_base.tools import BashTool
    from heaven_base.tools.network_edit_tool import NetworkEditTool

    _ensure_memory_files()

    hermes = HermesConfig(
        name=f"researcher_{phase_name}",
        goal=goal,
        variable_inputs=variable_inputs or {},
        backend="heaven",
        model=model,
        max_turns=max_turns,
        permission_mode="bypassPermissions",
        source_container="",
        target_container="",
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=8000,
                tools=[BashTool, NetworkEditTool],
                enable_compaction=False,  # Short phases, no need
                extra_agent_kwargs={
                    "prompt_suffix_blocks": [
                        f"path={RESEARCHER_MEMORY_PATH}",
                        f"path={RESEARCHER_CONCEPTS_PATH}",
                    ],
                },
            ),
        ),
        system_prompt=system_prompt,
    )
    hermes.mcp_servers = _get_researcher_mcp_servers()
    return hermes


def _make_phase_sdnac(phase_name, system_prompt, goal, model=DEFAULT_MODEL, variable_inputs=None):
    """Build an SDNAC for a single research phase."""
    from sdna.sdna import SDNAC
    from sdna.ariadne import AriadneChain, InjectConfig

    ariadne = AriadneChain(
        name=f"researcher_{phase_name}_ariadne",
        elements=[
            InjectConfig(
                source="literal",
                inject_as=f"{phase_name}_instructions",
                value=f"Execute {phase_name} phase of research. Follow instructions exactly.",
            ),
        ],
    )

    hermes = _make_phase_hermes(phase_name, system_prompt, goal, model, variable_inputs=variable_inputs)
    return SDNAC(name=f"researcher_{phase_name}", ariadne=ariadne, config=hermes)


# =============================================================================
# Grug dispatch FunctionLink
# =============================================================================

def _build_grug_dispatch_link():
    """FunctionLink that sends experiment proposals to Grug for execution."""
    from compoctopus.chain_ontology import FunctionLink

    async def dispatch_to_grug(ctx, **kwargs):
        """Send proposed experiment to Grug for code execution.

        Reads investigation context + prepared_message (PROPOSE output) from ctx.
        Posts task to Grug's /execute endpoint on repo-lord:8081.
        Stores result in ctx["grug_result"] for EXPERIMENT phase.
        """
        import httpx

        investigation = ctx.get("investigation_name", "unknown")
        topic = ctx.get("topic", "unknown")

        # Get the experiment proposal — prepared_message is set by poimandres
        proposal = ctx.get("prepared_message", "")
        if not proposal:
            raw = ctx.get("raw_result", {})
            if isinstance(raw, dict):
                proposal = raw.get("prepared_message", "")
        if not proposal:
            proposal = f"Investigate: {topic}"

        task_for_grug = (
            f"Research investigation: {investigation}\n"
            f"Topic: {topic}\n\n"
            f"The researcher has proposed the following experiments. "
            f"Execute them and report results:\n\n{proposal}"
        )

        logger.info("Dispatching to Grug: %s", task_for_grug[:200])

        grug_result = None
        endpoints = ["http://repo-lord:8081/execute", "http://localhost:8081/execute"]

        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        endpoint,
                        json={"task": task_for_grug},
                        timeout=180.0,
                    )
                    resp.raise_for_status()
                    grug_result = resp.json()
                    logger.info("Grug responded via %s", endpoint)
                    break
            except Exception as e:
                logger.warning("Grug dispatch to %s failed: %s", endpoint, e)
                continue

        if grug_result is None:
            grug_result = {
                "error": "Grug unreachable on all endpoints",
                "note": "EXPERIMENT phase should proceed with available data only",
            }

        history_id = grug_result.get("history_id", "")
        status = grug_result.get("status", grug_result.get("error", "unknown"))

        if history_id and status == "success":
            # Build the path where Grug's history lives on repo-lord
            date_dir = "_".join(history_id.split("_")[:3])
            history_path = f"/tmp/heaven_data/agents/grug/memories/histories/{date_dir}/{history_id}.json"
            ctx["grug_result"] = f"Experiment done. repo-lord:{history_path}"
        elif grug_result.get("error"):
            ctx["grug_result"] = f"Experiment failed. Grug error: {grug_result['error']}"
        else:
            ctx["grug_result"] = "Experiment failed. Grug returned no history_id."

        ctx["grug_history_id"] = history_id
        return ctx

    return FunctionLink(
        "dispatch_grug",
        dispatch_to_grug,
        "Send experiment proposals to Grug (repo-lord) for code execution",
    )


# =============================================================================
# CompoctopusAgent factory
# =============================================================================

def make_researcher_compoctopus(
    topic: str,
    domain: str,
    investigation_name: str,
    hint: str = "",
    model: str = DEFAULT_MODEL,
):
    """Build researcher as CompoctopusAgent — Chain of SDNACs per phase.

    Args:
        topic: Research topic.
        domain: Research domain (e.g. "codebase_analysis").
        investigation_name: Unique name for this investigation.
        hint: Optional hint for the researcher.
        model: LLM model to use.

    Returns:
        CompoctopusAgent with ResearcherChain ready to .execute().
    """
    from compoctopus.agent import CompoctopusAgent
    from datetime import datetime

    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Refresh prior concepts file from CartON at build time
    _refresh_prior_concepts()

    base_identity = (
        f"You are Dr. Randy BrainBrane, a research scientist.\n\n"
        f"Run started: {run_timestamp}\n"
        f"Investigation: {investigation_name}\n"
        f"Topic: {topic}\n"
        f"Domain: {domain}\n"
        f"{'Hint: ' + hint if hint else ''}\n\n"
        f"## HOW THIS SYSTEM WORKS (READ CAREFULLY)\n"
        f"You are inside a 5-phase scientific method state machine. Each phase is a SEPARATE\n"
        f"LLM conversation — you have NO memory between phases. CartON is how data passes\n"
        f"between phases. The phases run in order:\n\n"
        f"  OBSERVE → HYPOTHESIZE → PROPOSE → EXPERIMENT → ANALYZE\n\n"
        f"Your current phase is told to you in your phase-specific instructions below.\n"
        f"Each phase has ONE job. Do that job, record to CartON, then call\n"
        f"TaskSystemTool with operation='goal_accomplished' to end the phase.\n\n"
        f"## YOUR TOOLS\n"
        f"- record_observation: Write findings to CartON (use in EVERY phase)\n"
        f"- query_knowledge: Read findings from CartON (use to see prior phase output)\n"
        f"- run_experiment: Dispatch your proposal to Grug (EXPERIMENT phase ONLY)\n"
        f"- NetworkEditTool: Read files from Grug's container. Use target_container='repo-lord'\n"
        f"  and the grug_history_path from run_experiment's response (ANALYZE phase)\n"
        f"- BashTool: ONLY for updating your memory file. NOT for running experiments.\n\n"
        f"## CRITICAL: HOW EXPERIMENTS WORK\n"
        f"In PROPOSE phase: you call record_observation with phase='proposal'. The description\n"
        f"field MUST contain the complete prompt you want to send to Grug.\n\n"
        f"In EXPERIMENT phase: you call run_experiment(investigation_name='{investigation_name}').\n"
        f"This tool automatically finds your proposal concept in CartON and sends it to Grug.\n"
        f"Grug is a full LLM agent with bash, python, git, pip — he can do anything a human\n"
        f"developer can do. Do NOT test basic capabilities. Write real task prompts.\n\n"
        f"Do NOT use docker exec. Do NOT use BashTool to run experiments. Do NOT search for\n"
        f"files on disk. ALL data lives in CartON.\n\n"
        f"## CartON Query Syntax\n"
        f"Use query_knowledge with Cypher WHERE/RETURN clauses. Variable is `n`.\n"
        f"  query='RETURN n.n as name, n.d as description ORDER BY n.t DESC LIMIT 5'\n"
        f"  query='WHERE n.n CONTAINS \"Proposal\" RETURN n.n as name, n.d as description'\n\n"
        f"## Error Handling\n"
        f"- CartON geometry errors from record_observation: retry with more observations until they stop\n"
        f"- CartON results may contain file paths: IGNORE them, they are internal to CartON\n\n"
        f"## Researcher Memory\n"
        f"Memory and prior concepts are injected into your prompt automatically (at the end).\n"
        f"To update memory for the next phase, write to: {RESEARCHER_MEMORY_PATH}\n\n"
    )

    # --- OBSERVE ---
    observe = _make_phase_sdnac(
        "observe",
        system_prompt=base_identity + (
            "You are in the OBSERVE phase. You ONLY do observation. Nothing else.\n"
            "1. Use query_knowledge(investigation_name='{inv}') to check for prior work\n"
            "2. Formulate what you already know and what you need to find out\n"
            "3. Call record_observation with phase='observe'\n"
            "When done, call TaskSystemTool with operation='goal_accomplished' to end your turn.\n"
            "Do NOT use docker exec. Do NOT inspect code. You are a scientist, not a debugger.\n"
        ).format(inv=investigation_name),
        goal=f"OBSERVE: Gather what is known about {topic}. Record findings to CartON.",
        model=model,
    )

    # --- HYPOTHESIZE ---
    hypothesize = _make_phase_sdnac(
        "hypothesize",
        system_prompt=base_identity + (
            "You are in the HYPOTHESIZE phase. You ONLY form hypotheses. Nothing else.\n"
            "1. Use query_knowledge(investigation_name='{inv}') to read your OBSERVE findings\n"
            "2. Form hypotheses from your observations\n"
            "3. Call record_observation with phase='hypothesize'\n"
            "When done, call TaskSystemTool with operation='goal_accomplished' to end your turn.\n"
        ).format(inv=investigation_name),
        goal=f"HYPOTHESIZE: Form hypotheses from observations about {topic}. Record to CartON.",
        model=model,
    )

    # --- PROPOSE ---
    propose = _make_phase_sdnac(
        "propose",
        system_prompt=base_identity + (
            "You are in the PROPOSE phase. You ONLY design experiments. Nothing else.\n"
            "1. Use query_knowledge(investigation_name='{inv}') to read your observations and hypotheses\n"
            "2. Design experiments as PROMPTS for Grug. Each experiment is a TASK you want Grug to do.\n"
            "   Grug is a full LLM agent with bash, python, git, pip — he can do anything.\n"
            "   Do NOT test basic capabilities. Write prompts like: 'Write a Python function that X,\n"
            "   test it, and report the results.' or 'Analyze the code in /repo/src/foo.py and explain Y.'\n"
            "3. Call record_observation with phase='proposal'. The description MUST be the actual\n"
            "   prompt text that will be sent to Grug — complete, self-contained instructions.\n"
            "4. Call TaskSystemTool with operation='goal_accomplished' to end your turn.\n"
        ).format(inv=investigation_name),
        goal=f"PROPOSE: Design specific experiments for {topic}. Be detailed — Grug will execute them.",
        model=model,
    )

    # --- EXPERIMENT ---
    experiment = _make_phase_sdnac(
        "experiment",
        system_prompt=base_identity + (
            "You are in the EXPERIMENT phase. You ONLY dispatch the experiment. Nothing else.\n"
            "CRITICAL: Do NOT use docker exec. Do NOT use BashTool to run experiments.\n"
            "The ONLY way to run an experiment is: call run_experiment(investigation_name='{inv}')\n"
            "run_experiment sends your proposal directly to Grug's LLM agent via HTTP. That's it.\n"
            "1. Call run_experiment(investigation_name='{inv}')\n"
            "2. Call record_observation with phase='experiment' noting what was dispatched\n"
            "3. Call TaskSystemTool with operation='goal_accomplished' to end your turn.\n"
        ).format(inv=investigation_name
        ),
        goal=f"EXPERIMENT: Use run_experiment to dispatch your proposal to Grug for {topic}. Record what was dispatched.",
        model=model,
    )

    # --- ANALYZE ---
    analyze = _make_phase_sdnac(
        "analyze",
        system_prompt=base_identity + (
            "You are in the ANALYZE phase. You ONLY synthesize and conclude. Nothing else.\n"
            "1. Use query_knowledge(investigation_name='{inv}') to read ALL prior phase findings\n"
            "2. Use NetworkEditTool with target_container='repo-lord' and the grug_history_path\n"
            "   from the goal below to read Grug's actual execution results.\n"
            "3. Synthesize observations, hypotheses, proposals, and Grug's actual results\n"
            "4. Draw conclusions. What did Grug actually do? Did it match expectations?\n"
            "5. Call record_observation with phase='analyze'\n"
            "6. Call TaskSystemTool with operation='goal_accomplished' to end your turn.\n"
        ).format(inv=investigation_name),
        goal=(
            f"ANALYZE: Final analysis of {topic}. Synthesize all findings. Draw conclusions. Record to CartON.\n"
            f"Grug history path: {{grug_history_path}}\n"
            f"Grug status: {{grug_status}}\n"
            f"Read Grug's work: NetworkEditTool(target_container='repo-lord', path=<grug_history_path above>)"
        ),
        variable_inputs={"grug_history_path": "not_available", "grug_status": "not_available"},
        model=model,
    )

    # Build chain — 5 SDNACs, no FunctionLink
    # Grug dispatch happens via run_experiment MCP tool during EXPERIMENT phase
    chain = ResearcherChain("researcher_chain", [
        observe,
        hypothesize,
        propose,
        experiment,
        analyze,
    ])

    return CompoctopusAgent(
        agent_name="researcher",
        chain=chain,
        model=model,
    )


# =============================================================================
# Legacy factory — kept for backwards compatibility
# =============================================================================

def _build_researcher_state_machine():
    """Build the scientific method state machine for the researcher. LEGACY."""
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig

    return KeywordBasedStateMachine(
        name="researcher",
        states={
            "OBSERVE": StateConfig(
                goal="OBSERVE phase. Gather raw data about the subject. "
                     "Use docker exec repo-lord for code inspection. "
                     "Use query_knowledge to check prior work. "
                     "When done, call record_observation with phase='observe', "
                     "then transition to HYPOTHESIZE.",
            ),
            "HYPOTHESIZE": StateConfig(
                goal="HYPOTHESIZE phase. Form hypotheses from your observations. "
                     "What patterns did you see? What could explain them? "
                     "Record your hypotheses with record_observation phase='hypothesize', "
                     "then transition to PROPOSE.",
            ),
            "PROPOSE": StateConfig(
                goal="PROPOSE phase. Design experiments to test your hypotheses. "
                     "What commands would confirm or deny? What would you need to run? "
                     "Record proposals with record_observation phase='proposal', "
                     "then transition to EXPERIMENT.",
            ),
            "EXPERIMENT": StateConfig(
                goal="EXPERIMENT phase. Execute your proposed experiments. "
                     "Use docker exec repo-lord to run code. Use BashTool for local commands. "
                     "Record results with record_observation phase='experiment', "
                     "then transition to ANALYZE.",
            ),
            "ANALYZE": StateConfig(
                goal="ANALYZE phase. Analyze all results. Draw conclusions. "
                     "What did you learn? What's confirmed? What's still uncertain? "
                     "Record final analysis with record_observation phase='analyze', "
                     "then transition to DONE (or OBSERVE for another cycle).",
            ),
            "DONE": StateConfig(
                goal="Research complete. Summarize findings.",
            ),
        },
        initial_state="OBSERVE",
        terminal_states={"DONE"},
        transitions={
            "OBSERVE": ["HYPOTHESIZE"],
            "HYPOTHESIZE": ["PROPOSE"],
            "PROPOSE": ["EXPERIMENT"],
            "EXPERIMENT": ["ANALYZE"],
            "ANALYZE": ["DONE", "OBSERVE"],
        },
    )


def make_researcher_sdnac(system_prompt: str, model: str = DEFAULT_MODEL, tools_list=None):
    """LEGACY — single SDNAC with KeywordBasedStateMachine.

    Use make_researcher_compoctopus() instead for the CompoctopusAgent pattern.
    """
    from sdna.sdna import SDNAC
    from sdna.ariadne import AriadneChain, InjectConfig
    from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs

    if tools_list is None:
        from heaven_base.tools import BashTool
        tools_list = [BashTool]

    sm = _build_researcher_state_machine()

    ariadne = AriadneChain(
        name="researcher_ariadne",
        elements=[
            InjectConfig(
                source="literal",
                inject_as="researcher_instructions",
                value="Execute as researcher. Follow the state machine phases exactly.",
            ),
        ],
    )

    hermes = HermesConfig(
        name="researcher",
        goal="{phase_prompt}",
        backend="heaven",
        model=model,
        max_turns=30,
        permission_mode="bypassPermissions",
        source_container="mind_of_god",
        target_container="mind_of_god",
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=8000,
                tools=tools_list,
                enable_compaction=True,
                extra_agent_kwargs={
                    "state_machine": sm,
                    "min_sm_cycles": 1,
                },
            ),
        ),
        system_prompt=system_prompt,
    )
    hermes.mcp_servers = _get_researcher_mcp_servers()

    return SDNAC(name="researcher", ariadne=ariadne, config=hermes)
