"""Pilot factory — queue manager + agent launcher for waypoint-driven pilots.

The pilot's logic lives in starship_pilot_flight_config, NOT in Python.
This factory just:
1. Manages the queue (pending/processing/done/response)
2. Launches pilot agents with waypoint on the flight config
3. Handles OVP approve/reject flow

Queue dirs:
    {PILOT_QUEUE}/pending/     — we drop deliverables/tasks here
    {PILOT_QUEUE}/processing/  — pilot moves items here while working
    {PILOT_QUEUE}/done/        — pilot writes results here, awaits our OVP
    {PILOT_QUEUE}/response/    — we write OVP responses here
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PILOT_QUEUE = os.path.join(
    os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "pilot_queue"
)

PILOT_FLIGHT_CONFIG = "starship_pilot_flight_config"


# =============================================================================
# QUEUE OPERATIONS
# =============================================================================

def _ensure_queue_dirs():
    for subdir in ("pending", "processing", "done", "response"):
        Path(PILOT_QUEUE, subdir).mkdir(parents=True, exist_ok=True)


def submit_deliverable(workspace: str, goal: str, branch_name: Optional[str] = None) -> str:
    """Drop a GIINT_Deliverable in the pilot queue. Pilot breaks into tasks."""
    _ensure_queue_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    item_id = f"{ts}_deliverable"
    item = {
        "id": item_id,
        "type": "deliverable",
        "goal": goal,
        "workspace": workspace,
        "branch_name": branch_name or Path(workspace).name.lower().replace(" ", "-"),
        "submitted_at": datetime.now().isoformat(),
    }
    path = Path(PILOT_QUEUE, "pending", f"{item_id}.json")
    path.write_text(json.dumps(item, indent=2))
    logger.info("Submitted deliverable: %s", item_id)
    return item_id


def submit_task(workspace: str, task_description: str, code_target: str,
                worktree: Optional[str] = None, branch_name: Optional[str] = None) -> str:
    """Drop a GIINT_Task in the pilot queue. Pilot goes straight to ralph."""
    _ensure_queue_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    item_id = f"{ts}_task"
    item = {
        "id": item_id,
        "type": "task",
        "task_description": task_description,
        "code_target": code_target,
        "workspace": workspace,
        "worktree": worktree,
        "branch_name": branch_name or Path(workspace).name.lower().replace(" ", "-"),
        "submitted_at": datetime.now().isoformat(),
    }
    path = Path(PILOT_QUEUE, "pending", f"{item_id}.json")
    path.write_text(json.dumps(item, indent=2))
    logger.info("Submitted task: %s", item_id)
    return item_id


def submit_ovp_response(item_id: str, approved: bool, feedback: str = "") -> None:
    """Write our OVP response for a done item. Pilot reads this on resume."""
    _ensure_queue_dirs()
    response = {
        "item_id": item_id,
        "approved": approved,
        "feedback": feedback,
        "responded_at": datetime.now().isoformat(),
    }
    path = Path(PILOT_QUEUE, "response", f"{item_id}_response.json")
    path.write_text(json.dumps(response, indent=2))
    logger.info("OVP response for %s: approved=%s", item_id, approved)


def list_queue(subdir: str = "pending") -> List[Dict]:
    """List items in a queue subdir."""
    _ensure_queue_dirs()
    items = []
    for f in sorted(Path(PILOT_QUEUE, subdir).glob("*.json")):
        items.append(json.loads(f.read_text()))
    return items


# =============================================================================
# GIT HELPERS
# =============================================================================

def _run_git(cmd: str, cwd: str) -> str:
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def _setup_starsystem_branch(workspace: str, branch_name: str) -> str:
    full_branch = f"starsystem/{branch_name}"
    try:
        _run_git(f"git rev-parse --verify {full_branch}", workspace)
        _run_git(f"git checkout {full_branch}", workspace)
        logger.info("Checked out existing branch: %s", full_branch)
    except RuntimeError:
        _run_git(f"git checkout -b {full_branch}", workspace)
        logger.info("Created new branch: %s", full_branch)
    return full_branch


# =============================================================================
# PILOT AGENT LAUNCHER (waypoint-driven)
# =============================================================================

def _build_pilot_input(item: Dict, full_branch: str,
                       flight: str = PILOT_FLIGHT_CONFIG,
                       ovp_feedback: Optional[str] = None) -> str:
    """Build the input prompt: run flight X + context."""
    workspace = item["workspace"]
    goal = item.get("goal") or item.get("task_description", "")

    parts = [f"Run flight: {flight}\n"]

    parts.append(f"## Goal\n{goal}\n")
    parts.append(f"## Workspace: {workspace}\n## Branch: {full_branch}\n")
    parts.append(f"## Queue Item: {item['id']} ({item['type']})\n")

    # CLAUDE.md + rules auto-injected via claude_parity hook (AFTER_TOOL_CALL)

    if ovp_feedback:
        parts.append(f"## OVP Feedback\n{ovp_feedback}\n")

    if item["type"] == "task" and item.get("code_target"):
        parts.append(f"## Code Target: {item['code_target']}\n")

    return "\n".join(parts)


def run_pilot_on_item(item: Dict, flight: str = PILOT_FLIGHT_CONFIG) -> Dict[str, Any]:
    """Launch a pilot agent on a queue item via SDNAC.

    Uses first-class HeavenAgentArgs fields for skillset, hook_registry, mcp_servers.
    Input prompt: "Run flight: X" + context.
    """
    workspace = item["workspace"]
    branch_name = item["branch_name"]
    item_id = item["id"]

    # Validate workspace
    try:
        _run_git("git rev-parse --git-dir", workspace)
        status = _run_git("git status --porcelain --ignore-submodules", workspace)
        # Ignore untracked dirs like __pycache__
        dirty = [l for l in status.splitlines() if l.strip() and not l.startswith("??")]
        if dirty:
            return {"status": "error", "error": f"Workspace not clean:\n" + "\n".join(dirty)}
    except RuntimeError as e:
        return {"status": "error", "error": str(e)}

    full_branch = _setup_starsystem_branch(workspace, branch_name)
    ovp_feedback = item.get("ovp_feedback")
    input_prompt = _build_pilot_input(item, full_branch, flight, ovp_feedback)

    from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
    from sdna.sdna import SDNAC
    from sdna.ariadne import AriadneChain, InjectConfig
    from heaven_base.baseheavenagent import HookRegistry, HookPoint
    from heaven_base.tools import BashTool
    from compoctopus.agents.pilot.prompts import build_pilot_system_prompt
    from compoctopus.agents.pilot.tools import pilot_before_tool_call

    # Starsystem name from workspace dir name
    starsystem_name = Path(workspace).name

    # Build hook registry with write-blocking hook
    pilot_hooks = HookRegistry()
    pilot_hooks.register(HookPoint.BEFORE_TOOL_CALL, pilot_before_tool_call)

    ariadne = AriadneChain(
        name="pilot_waypoint",
        elements=[InjectConfig(source="literal", inject_as="instructions", value=input_prompt)],
    )

    # Shared Neo4j env
    _neo4j_env = {
        "NEO4J_URI": "bolt://host.docker.internal:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
    }
    _heaven_env = {"HEAVEN_DATA_DIR": os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")}

    # Escape curly braces in input_prompt so resolve_goal doesn't try to .format() them
    safe_prompt = input_prompt.replace("{", "{{").replace("}", "}}")

    hermes = HermesConfig(
        name=f"pilot_{item_id}",
        goal=safe_prompt,
        backend="heaven",
        model="MiniMax-M2.7-highspeed",
        max_turns=10,
        permission_mode="bypassPermissions",
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=16000,
                tools=[BashTool],
                skillset="starship-pilot",
                hook_registry=pilot_hooks,
                carton_identity=f"{starsystem_name}_Starship_Pilot",
            ),
        ),
        mcp_servers={
            "context-alignment": {
                "command": "python3",
                "args": ["/home/GOD/context_alignment_utils/neo4j_codebase_mcp/server.py"],
                "env": {"TRANSPORT": "stdio", **_neo4j_env},
            },
            "starlog": {
                "command": "python",
                "args": ["-m", "starlog_mcp.starlog_mcp"],
                "env": {**_heaven_env, **_neo4j_env},
            },
            "starship": {
                "command": "python",
                "args": ["-m", "starship_mcp.starship_mcp"],
                "env": _heaven_env,
            },
            "waypoint": {
                "command": "python",
                "args": ["-m", "payload_discovery.mcp_server_v2"],
                "env": _heaven_env,
            },
            "carton": {
                "command": "carton-mcp",
                "args": [],
                "env": {
                    **_heaven_env, **_neo4j_env,
                    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
                    "CHROMA_PERSIST_DIR": "/tmp/carton_chroma_db",
                },
            },
            "dragonbones": {
                "command": "python3",
                "args": ["-m", "dragonbones.server"],
                "env": {},
            },
        },
        system_prompt=build_pilot_system_prompt(starsystem_name, workspace),
    )

    import asyncio
    sdnac = SDNAC(name=f"pilot_{item_id}", ariadne=ariadne, config=hermes)
    result = asyncio.run(sdnac.execute({}))

    logger.info("SDNAC result: status=%s error=%s", result.status, result.error)
    if result.error:
        logger.error("Pilot SDNAC failed: %s", result.error)

    output = result.context.get("text", "")

    # Check if pilot wrote a done file
    done_path = Path(PILOT_QUEUE, "done", f"{item_id}.json")
    if done_path.exists():
        done_result = json.loads(done_path.read_text())
        logger.info("Pilot completed %s with done file", item_id)
        return done_result

    # Pilot didn't write done file — create one from output
    _ensure_queue_dirs()
    pilot_result = {
        "id": item_id,
        "type": item["type"],
        "workspace": workspace,
        "branch": full_branch,
        "pilot_output_tail": output[-500:] if output else "",
        "completed_at": datetime.now().isoformat(),
    }

    done_path.write_text(json.dumps(pilot_result, indent=2))

    # Clean up processing
    processing_path = Path(PILOT_QUEUE, "processing", f"{item_id}.json")
    if processing_path.exists():
        processing_path.unlink()

    logger.info("Pilot done for %s", item_id)
    return pilot_result


def process_queue() -> List[Dict]:
    """Process all pending items in the queue."""
    _ensure_queue_dirs()
    results = []

    pending_dir = Path(PILOT_QUEUE, "pending")
    for item_file in sorted(pending_dir.glob("*.json")):
        item = json.loads(item_file.read_text())

        # Move to processing
        processing_path = Path(PILOT_QUEUE, "processing", item_file.name)
        shutil.move(str(item_file), str(processing_path))

        result = run_pilot_on_item(item)
        results.append(result)

    return results


def resume_from_ovp(item_id: str) -> Optional[Dict]:
    """Resume a done item after OVP response."""
    _ensure_queue_dirs()

    response_path = Path(PILOT_QUEUE, "response", f"{item_id}_response.json")
    done_path = Path(PILOT_QUEUE, "done", f"{item_id}.json")

    if not response_path.exists():
        logger.warning("No OVP response for %s", item_id)
        return None
    if not done_path.exists():
        logger.warning("No done item for %s", item_id)
        return None

    response = json.loads(response_path.read_text())
    done_item = json.loads(done_path.read_text())

    if response["approved"]:
        # OVP approved — PR starsystem branch to main
        workspace = done_item["workspace"]
        branch = done_item["branch"]
        try:
            pr_result = subprocess.run(
                f"gh pr create --base main --head {branch} "
                f"--title 'Starsystem: {branch}' "
                f"--body 'Pilot-driven evolution. Auto-merged ralph PRs.'",
                shell=True, cwd=workspace, capture_output=True, text=True,
            )
            done_item["main_pr_url"] = pr_result.stdout.strip()
            done_item["status"] = "pr_to_main"
        except Exception as e:
            done_item["status"] = "error"
            done_item["error"] = str(e)

        done_path.write_text(json.dumps(done_item, indent=2))
        response_path.unlink()
        return done_item

    else:
        # OVP rejected — resume with feedback
        original_item = {
            "id": item_id,
            "type": done_item["type"],
            "workspace": done_item["workspace"],
            "branch_name": done_item["branch"].replace("starsystem/", ""),
            "goal": done_item.get("goal", ""),
            "task_description": done_item.get("task_description", ""),
            "ovp_feedback": response["feedback"],
        }

        # Move back to processing
        processing_path = Path(PILOT_QUEUE, "processing", f"{item_id}.json")
        processing_path.write_text(json.dumps(original_item, indent=2))
        done_path.unlink()
        response_path.unlink()

        result = run_pilot_on_item(original_item)
        return result
