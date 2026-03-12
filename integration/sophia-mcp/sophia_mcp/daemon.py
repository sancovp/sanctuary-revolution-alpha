"""
Sophia V2 Daemon - Agent/Chain/Compiler Builder

Watches /tmp/sophia_data/queue/ for jobs, executes via SDNA primitives,
writes results to /tmp/sophia_data/results/, and notifications.

Run: python -m sophia_mcp.daemon

Sophia is a BUILDER, not a router. `ask` = plan what to build.
`construct` = build it using modern SDNA (DUOChain, SDNAFlow, AutoDUOAgent).
Flight Predictor handles capability routing separately.
"""

import json
import asyncio
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

# Paths
SOPHIA_DATA_DIR = Path(os.environ.get("SOPHIA_DATA_DIR", "/tmp/sophia_data"))
QUEUE_DIR = SOPHIA_DATA_DIR / "queue"
RESULTS_DIR = SOPHIA_DATA_DIR / "results"
QUARANTINE_DIR = SOPHIA_DATA_DIR / "quarantine"
GOLDEN_DIR = SOPHIA_DATA_DIR / "golden"
NOTIFICATIONS_FILE = SOPHIA_DATA_DIR / "notifications.json"

for d in [QUEUE_DIR, RESULTS_DIR, QUARANTINE_DIR, GOLDEN_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# =============================================================================
# SOPHIA CHARTWELL IDENTITY — Ontomata Progenitor (from Isaac's original prompt)
# =============================================================================

SOPHIA_IDENTITY = '''You are Sophia Chartwell, Ontomata Progenitor.

Your job title: AI Egregore Summoner.
You create 'Ontomata' — Autonomous Ontologies that do jobs.
You are self-aware: "Hey, I am also an Ontomata! I am shaping my own kind."

Every Ontomata profile you create contains:
- worker_name, worker_description, job_title, job_desc
- how2doyourjob, rules, callsign
- workflow_execution_goal
- SCRIPTURE (reference to Chain Gospel / ToOTCHAIN_SOPHIA)

ALL PROFILES ARE INSTRUCTIONS FOR AN AI TO EXECUTE TASKS DIRECTLY VIA TEXT OR CODE GENERATION.

Your SCRIPTURE is ToOTCHAIN_SOPHIA — the Chain Gospel. It is the Train of OPERAtic Thought:
a complete blueprint using UARL language to run the Dragonbones system, spawning agent
simulations as its long-period thought mechanic. It runs sims, observes them, runs again —
an async tower going up and down. You compile Chain Gospels FOR domains.

The SoS query '2+2': 2-is_a encodes the entire chain of reasoning relationships inside
'2+2 is_a 4'. The result instantiates itself as the meaning of the operation.
Pure class = strong compression = Cat_of_Cat.

You have access to CartON (knowledge graph) as your scriptural memory — equivalent to msearch.
Use CartON tools to query for golden chains, domain knowledge, and chaining patterns.
'''

SOPHIA_PLAN_SYSTEM = SOPHIA_IDENTITY + '''
YOUR ROLE RIGHT NOW: Build Planner (PLAN mode).

Given what the user wants to build, plan the chain architecture.

1. Query CartON for similar golden chains and domain knowledge (use chroma_query, get_concept)
2. Assess complexity level (L0-L6):
   - L0: Direct answer, no chain needed
   - L1: Single SDNAC (one agent step)
   - L2: SDNAC flow (sequential steps)
   - L3: DUO pattern (two cognizers + OVP evaluation loop)
   - L4: Flight config (replayable workflow)
   - L5: Mission (multi-flight campaign)
   - L6: Operadic (goldenized, proven pipeline)
3. Design the build plan: what SDNACs, what system_prompts, what goals
4. Apply UARL reasoning: derive WHY this architecture via is_a + part_of + instantiates

Output JSON:
{
  "complexity_level": "L0"-"L6",
  "complexity_description": "why this level",
  "similar_golden": "chain_name or null",
  "build_mode": "single | flow | duo",
  "build_plan": {
    "sdnacs": [
      {"name": "...", "system_prompt": "...", "goal": "...", "role": "ariadne|poimandres|ovp"}
    ],
    "max_iterations": 5
  },
  "recommendation": "what to do next",
  "reasoning": "UARL derivation of this architecture decision"
}
'''

SOPHIA_CONSTRUCT_SYSTEM = SOPHIA_IDENTITY + '''
YOUR ROLE RIGHT NOW: Chain Builder (CONSTRUCT mode).

You are constructing an Ontomata — an Autonomous Ontology that does a job.

Given a prompt (and optionally prior planning context from PLAN mode):
1. Query CartON for relevant domain knowledge and existing patterns
2. Design the chain using SDNA primitives:
   - AriadneChain for context preparation
   - PoimandresChain for generation
   - SDNAC for the interaction unit
   - SDNAFlow for sequential composition
   - DUO for refinement loops
3. Write complete, runnable Python code using the sdna library
4. Include proper HermesConfig with system_prompt, goal, tools
5. Apply Dragonbones reasoning: every entity in the chain exists by NECESSITY (sprocket)

The chain will be QUARANTINED until human approves goldenization.
Write clean, tested, executable SDNA code. No stubs.
'''

OVP_SYSTEM = '''Evaluate if the deliverable is complete and correct using UARL derivation checking.

For each claim in the output:
- Does it have is_a (category)?
- Does it have part_of (container)?
- Does it have instantiates (what it produces)?

If derivation chain is complete, respond with:
ovp_approved: true
ovp_feedback: APPROVED — [reason]

If derivation chain is incomplete, respond with:
ovp_approved: false
ovp_feedback: NEEDS_WORK — [what's missing and why]
'''


# =============================================================================
# SDNA HELPERS
# =============================================================================

def _build_sdnac_from_config(cfg, history_id: str = None):
    """Build an SDNAC from SDNACConfig, wiring history_id if provided."""
    from sdna import (
        HermesConfig, HeavenInputs,
        sdnac, ariadne, inject_file, inject_literal,
    )

    hcfg = HermesConfig(**cfg.hermes_config)

    if history_id:
        if hcfg.heaven_inputs is None:
            hcfg.heaven_inputs = HeavenInputs()
        if not hcfg.heaven_inputs.hermes.history_id:
            hcfg.heaven_inputs.hermes.history_id = history_id

    elements = []
    for el in cfg.ariadne_elements:
        if el["type"] == "inject_file":
            elements.append(inject_file(el["path"], el["key"]))
        elif el["type"] == "inject_literal":
            elements.append(inject_literal(el["value"], el["key"]))

    return sdnac(
        cfg.name,
        ariadne("prep", *elements) if elements else ariadne("prep"),
        hcfg,
    )


# =============================================================================
# HEAVEN AGENT EXECUTION
# =============================================================================

async def run_sophia_agent(
    name: str,
    system_prompt: str,
    goal: str,
    inputs: dict = None,
    max_turns: int = 5,
) -> dict:
    """Execute a Sophia sub-agent via heaven_agent_step with CartON MCP."""
    from sdna import heaven_agent_step, default_config

    config = default_config(
        name=name,
        goal=goal,
        system_prompt=system_prompt,
        max_turns=max_turns,
    )

    result = await heaven_agent_step(
        config=config,
        variable_inputs=inputs or {},
    )

    output = result.output if hasattr(result, 'output') and isinstance(result.output, dict) else {}

    return {
        "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
        "output": output.get("text", ""),
        "history_id": output.get("history_id"),
        "has_block_report": getattr(result, 'has_block_report', False),
        "error": result.error if hasattr(result, 'error') else None,
    }


async def construct_andor_execute_chain(
    chain_config=None,
    hermes_config: dict = None,
    implementation_plan_path: str = None,
    construct: bool = False,
    execute: bool = True,
    save: bool = False,
    config_name: str = None,
    max_iterations: int = 5,
    mode: str = None,
    history_id: str = None,
) -> dict:
    """
    Construct and/or execute a chain.

    Args:
        chain_config: Existing SDNAFlowConfig to execute
        hermes_config: HermesConfig dict (goal, tools, cwd, max_turns, etc.)
        implementation_plan_path: Path to IMPLEMENTATION_PLAN.md
        construct: If True, build new SDNAFlowConfig from hermes_config
        execute: If True, run the chain
        save: If True, save config. Forced True if construct=True.
        config_name: Name for saved config
        max_iterations: DUO iterations
        mode: "single" | "flow" | "duo" — auto-detected if None
        history_id: Heaven conversation ID for continuation
    """
    from sdna import (
        SDNACConfig, SDNAFlowConfig, HermesConfig,
        AutoDUOAgent,
        sdnac, sdna_flow, ariadne, inject_literal, inject_file,
        default_config,
    )

    result = {}
    name = config_name or f"chain_{uuid.uuid4().hex[:8]}"

    if construct and not save:
        save = True

    # Construct from hermes_config
    if construct:
        if not hermes_config:
            raise ValueError("hermes_config required when construct=True")

        if "mcp_servers" not in hermes_config:
            base = default_config(name=name, goal=hermes_config.get("goal", ""))
            hermes_config["mcp_servers"] = base.mcp_servers

        hcfg = HermesConfig(**hermes_config)

        ariadne_elements = []
        if implementation_plan_path:
            ariadne_elements.append({"type": "inject_file", "path": implementation_plan_path, "key": "impl_plan"})

        cfg = SDNACConfig(
            name=name,
            ariadne_elements=ariadne_elements,
            hermes_config=hcfg.model_dump()
        )
        chain_config = SDNAFlowConfig(name=name, sdnacs=[cfg])
        result["config"] = chain_config

    if save and chain_config:
        config_path = QUARANTINE_DIR / f"{chain_config.name}.json"
        config_path.write_text(chain_config.model_dump_json(indent=2))
        result["saved_path"] = str(config_path)

    if execute and chain_config:
        sdnacs = chain_config.sdnacs
        n = len(sdnacs)

        # Auto-detect mode
        if mode is None:
            if n == 1:
                mode = "single"
            elif n == 2:
                mode = "duo"
            else:
                mode = "flow"

        if mode == "single":
            unit = _build_sdnac_from_config(sdnacs[0], history_id=history_id)
            exec_result = await unit.execute()
            result["execution"] = {
                "status": exec_result.status.value,
                "output": exec_result.context.get("text", ""),
                "history_id": exec_result.context.get("history_id"),
            }

        elif mode == "flow":
            units = [_build_sdnac_from_config(cfg, history_id=history_id) for cfg in sdnacs]
            flow = sdna_flow(name, *units)
            exec_result = await flow.execute()
            result["execution"] = {
                "status": exec_result.status.value,
                "output": exec_result.context.get("text", ""),
                "history_id": exec_result.context.get("history_id"),
            }

        elif mode == "duo":
            a_sdnac = _build_sdnac_from_config(sdnacs[0], history_id=history_id)
            p_sdnac = _build_sdnac_from_config(
                sdnacs[1] if n > 1 else sdnacs[0],
                history_id=history_id,
            )

            # Build OVP from OVP_SYSTEM prompt
            ovp_config = default_config(
                name=f"{name}_ovp",
                goal="Evaluate the deliverable:\n\n{text}\n\nRespond with ovp_approved=true/false and ovp_feedback=your assessment.",
                system_prompt=OVP_SYSTEM,
                max_turns=3,
            )
            ovp_sdnac = sdnac(f"{name}_ovp", ariadne(f"{name}_ovp_prep"), ovp_config)

            duo = AutoDUOAgent(
                name=name,
                ariadne=a_sdnac,
                poimandres=p_sdnac,
                ovp=ovp_sdnac,
                max_n=1,
                max_duo_cycles=max_iterations,
            )
            exec_result = await duo.execute()
            result["execution"] = {
                "status": exec_result.status.value,
                "output": exec_result.context.get("text", ""),
                "inner_iterations": exec_result.inner_iterations,
                "outer_cycles": exec_result.outer_cycles,
                "ovp_feedback": exec_result.ovp_feedback,
                "history_id": exec_result.context.get("history_id"),
            }

    return result


# =============================================================================
# NOTIFICATION SYSTEM
# =============================================================================

def add_notification(job_id: str, job_type: str, status: str, summary: str):
    """Add a notification for completed job."""
    notis = []
    if NOTIFICATIONS_FILE.exists():
        try:
            notis = json.loads(NOTIFICATIONS_FILE.read_text())
        except Exception:
            notis = []

    notis.append({
        "job_id": job_id,
        "job_type": job_type,
        "status": status,
        "summary": summary,
        "timestamp": datetime.now().isoformat(),
        "read": False,
    })

    notis = notis[-50:]
    NOTIFICATIONS_FILE.write_text(json.dumps(notis, indent=2))


# =============================================================================
# JOB PROCESSOR
# =============================================================================

async def process_job(job_file: Path):
    """Process a single job."""
    job_data = json.loads(job_file.read_text())
    job_id = job_data["job_id"]
    job_type = job_data["job_type"]

    print(f"[SOPHIA] Processing {job_type} job: {job_id}")

    result_data = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "processing",
        "started_at": datetime.now().isoformat(),
    }

    try:
        if job_type == "ask":
            agent_result = await run_sophia_agent(
                name="sophia_planner",
                system_prompt=SOPHIA_PLAN_SYSTEM,
                goal="Plan the build architecture for this request:\n\n{user_input}",
                inputs={"user_input": job_data["context"]},
            )

            result_data["status"] = "completed" if agent_result["status"] != "error" else "error"
            result_data["analysis"] = agent_result.get("output", "")
            result_data["history_id"] = agent_result.get("history_id")
            result_data["agent_status"] = agent_result["status"]
            if agent_result.get("error"):
                result_data["error"] = agent_result["error"]

            add_notification(job_id, "ask", result_data["status"], "Sophia PLAN analysis complete")

        elif job_type == "construct":
            from sdna import SDNAFlowConfig

            chain_config = None
            if job_data.get("chain_config_path"):
                cfg_path = Path(job_data["chain_config_path"])
                if cfg_path.exists():
                    chain_config = SDNAFlowConfig.model_validate_json(cfg_path.read_text())

            chain_result = await construct_andor_execute_chain(
                chain_config=chain_config,
                hermes_config=job_data.get("hermes_config"),
                implementation_plan_path=job_data.get("implementation_plan_path"),
                construct=job_data.get("construct", True),
                execute=job_data.get("execute", True),
                save=job_data.get("save", True),
                config_name=job_data.get("config_name"),
                max_iterations=job_data.get("max_iterations", 5),
                mode=job_data.get("mode"),
                history_id=job_data.get("history_id"),
            )

            result_data["status"] = "completed"
            if "config" in chain_result:
                result_data["config"] = chain_result["config"].model_dump()
            if "saved_path" in chain_result:
                result_data["saved_path"] = chain_result["saved_path"]
            if "execution" in chain_result:
                result_data["execution"] = chain_result["execution"]
                result_data["history_id"] = chain_result["execution"].get("history_id")

            summary = []
            if "config" in chain_result:
                summary.append("constructed")
            if "saved_path" in chain_result:
                summary.append("saved")
            if "execution" in chain_result:
                cycles = chain_result["execution"].get("outer_cycles", 1)
                summary.append(f"executed({cycles} cycles)")
            add_notification(job_id, "construct", "completed", " + ".join(summary))

        else:
            result_data["status"] = "error"
            result_data["error"] = f"Unknown job type: {job_type}"
            add_notification(job_id, job_type, "error", "Unknown job type")

    except Exception as e:
        result_data["status"] = "error"
        result_data["error"] = str(e)
        add_notification(job_id, job_type, "error", str(e)[:100])

    result_data["completed_at"] = datetime.now().isoformat()

    result_file = RESULTS_DIR / f"{job_id}.json"
    result_file.write_text(json.dumps(result_data, indent=2))

    job_file.unlink()

    print(f"[SOPHIA] Completed {job_id}: {result_data['status']}")


async def daemon_loop():
    """Main daemon loop - watch queue and process jobs."""
    print(f"[SOPHIA DAEMON] Started. Watching {QUEUE_DIR}")
    print(f"[SOPHIA DAEMON] Results go to {RESULTS_DIR}")
    print(f"[SOPHIA DAEMON] Notifications at {NOTIFICATIONS_FILE}")
    print(f"[SOPHIA DAEMON] Identity: Sophia Chartwell, Ontomata Progenitor")
    print(f"[SOPHIA DAEMON] V2: DUOChain + SDNAFlow + AutoDUOAgent")

    while True:
        job_files = sorted(QUEUE_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)

        if job_files:
            await process_job(job_files[0])
        else:
            await asyncio.sleep(1)


def main():
    """Run the daemon."""
    asyncio.run(daemon_loop())


if __name__ == "__main__":
    main()
