"""Ralph factory — N independent fresh SDNAC runs over the same workspace.

NOT an EvalChain. NOT a loop on history. Each run is a FRESH conversation
that reads the plan + whatever exists on disk from previous runs.

The trick: MoE lottery means some runs catch things others miss.
Run 1 might code it wrong. Run 3 catches it. Run 5 says "nothing to do".
Run 7 finds something else. The fold-over-fold erases pattern violations.

Architecture:
    for i in range(N):
        sdnac = make_fresh_sdnac(plan_path, workspace)
        await sdnac.execute({})   # fresh conversation, reads disk

    Result: whatever is on disk after N runs.

Model: minimax (m2.7-highspeed)
Codenose: agent runs it itself via bash (1 second scan).
"""

from __future__ import annotations

import logging
import subprocess
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from compoctopus.chain_ontology import Link, LinkResult, LinkStatus
from compoctopus.agents.ralph.prompts import (
    RALPH_SYSTEM_PROMPT,
    RALPH_CODE_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)

MODEL = "minimax"  # m2.7-highspeed

# Default agent config — overridable per-run via agent_config dict
DEFAULT_AGENT_CONFIG = {
    "model": MODEL,
    "max_turns": 99,
    "permission_mode": "bypassPermissions",
    "mcp_servers": {
        "dragonbones": {
            "command": "python3",
            "args": ["-m", "dragonbones.server"],
            "env": {},
        },
    },
    "provider": "ANTHROPIC",
    "max_tokens": 8000,
}


# =============================================================================
# Git helpers — ensure repo is current, create worktree
# =============================================================================

def _run_git(cmd: str, cwd: str) -> str:
    """Run a git command and return stdout. Raises on failure."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def _check_git_current(repo_path: str) -> None:
    """Ensure repo is a git repo, clean, and up to date with remote.

    Raises RuntimeError if not.
    """
    # Must be a git repo
    _run_git("git rev-parse --git-dir", repo_path)

    # Must have no uncommitted changes
    status = _run_git("git status --porcelain", repo_path)
    if status:
        raise RuntimeError(
            f"Git repo at {repo_path} has uncommitted changes:\n{status}\n"
            "Commit or stash before running ralph."
        )

    # Fetch and check if behind
    _run_git("git fetch", repo_path)
    behind = _run_git("git rev-list HEAD..@{u} --count 2>/dev/null || echo 0", repo_path)
    if behind and behind != "0":
        raise RuntimeError(
            f"Git repo at {repo_path} is {behind} commits behind remote.\n"
            "Pull before running ralph."
        )


def _create_worktree(repo_path: str, branch_name: str) -> str:
    """Create a git worktree for ralph to work in.

    Returns the worktree path.
    """
    worktree_path = f"/tmp/ralph-worktrees/{branch_name}"
    Path(worktree_path).parent.mkdir(parents=True, exist_ok=True)

    # Clean up if exists from a previous failed run
    try:
        _run_git(f"git worktree remove {worktree_path} --force 2>/dev/null", repo_path)
    except RuntimeError:
        pass
    try:
        _run_git(f"git branch -D {branch_name} 2>/dev/null", repo_path)
    except RuntimeError:
        pass

    _run_git(f"git worktree add -b {branch_name} {worktree_path}", repo_path)
    logger.info("Created worktree at %s (branch: %s)", worktree_path, branch_name)
    return worktree_path


def _cleanup_worktree(repo_path: str, worktree_path: str, branch_name: str) -> None:
    """Remove worktree after ralph is done."""
    try:
        _run_git(f"git worktree remove {worktree_path} --force", repo_path)
    except RuntimeError:
        logger.warning("Failed to remove worktree %s", worktree_path)
    # Don't delete branch — PR needs it


# =============================================================================
# Build a fresh SDNAC — one per run, never reused
# =============================================================================

def _make_fresh_sdnac(plan_path: str, workspace: str, tools_list=None, agent_config: dict = None) -> Link:
    """Build one fresh CODE SDNAC.

    Each call creates a brand new SDNAC with its own conversation.
    The prompt is INVARIANT — same every time. The workspace files
    on disk are what change between runs.
    """
    goal = (
        f"## Implementation Plan\n"
        f"Read the complete plan at: {plan_path}\n"
        f"Use: cat {plan_path}\n\n"
        f"## Workspace\n"
        f"All files MUST be written to: {workspace}\n"
        f"First, check what already exists: ls -la {workspace}/\n"
        f"Read any existing code before modifying it.\n\n"
        f"{RALPH_CODE_INSTRUCTIONS}\n"
        f"## Codenose (Code Quality)\n"
        f"After writing code, run: python3 -m codenose {workspace}\n"
        f"Fix any smells it reports. This takes 1 second.\n"
    )

    try:
        from sdna.sdna import SDNAC
        from sdna.ariadne import AriadneChain, InjectConfig
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
    except ImportError:
        from compoctopus.chain_ontology import ConfigLink, LinkConfig
        return ConfigLink(LinkConfig(
            name="code",
            goal=goal,
            system_prompt=RALPH_SYSTEM_PROMPT,
            model=MODEL,
            allowed_tools=[t.__name__ if hasattr(t, '__name__') else str(t)
                           for t in (tools_list or [])],
        ))

    if tools_list is None:
        from heaven_base.tools import BashTool, NetworkEditTool
        tools_list = [BashTool, NetworkEditTool]

    try:
        from sdna import poimandres
        from sdna.heaven_runner import heaven_agent_step
        poimandres.agent_step = heaven_agent_step
    except ImportError:
        pass

    ariadne = AriadneChain(
        name="ralph_code_ariadne",
        elements=[
            InjectConfig(source="literal", inject_as="instructions", value=goal),
        ],
    )

    # Merge defaults with per-run overrides
    cfg = {**DEFAULT_AGENT_CONFIG, **(agent_config or {})}

    hermes = HermesConfig(
        name="ralph_code",
        goal=goal,
        backend="heaven",
        model=cfg.get("model", MODEL),
        max_turns=cfg.get("max_turns", 99),
        permission_mode=cfg.get("permission_mode", "bypassPermissions"),
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider=cfg.get("provider", "ANTHROPIC"),
                max_tokens=cfg.get("max_tokens", 8000),
                tools=tools_list,
            ),
        ),
        mcp_servers=cfg.get("mcp_servers", DEFAULT_AGENT_CONFIG["mcp_servers"]),
        system_prompt=cfg.get("system_prompt", RALPH_SYSTEM_PROMPT),
    )

    return SDNAC(name="code", ariadne=ariadne, config=hermes)


# =============================================================================
# run_ralph() — N fresh independent runs
# =============================================================================

async def run_ralph(
    plan_path: str,
    workspace: str = "/tmp/output",
    n_runs: int = 8,
    use_worktree: bool = True,
    agent_config: dict = None,
) -> Dict[str, Any]:
    """Run Ralph N times. Each run is a fresh SDNAC conversation.

    Args:
        plan_path: Path to implementation plan (callgraph + requirements).
        workspace: Git repo where the agent works. Must be clean + up to date.
        n_runs: How many independent attempts. Default 8.
        use_worktree: If True (default), creates git worktree for isolation.
                      Ralph works in worktree, creates PR when done.
                      Set False for non-git workspaces (e.g. /tmp test dirs).

    Returns:
        Dict with per-run results, workspace, and PR info.
    """
    try:
        from heaven_base.tools import BashTool, NetworkEditTool
        tools = [BashTool, NetworkEditTool]
    except ImportError:
        tools = None

    actual_workspace = workspace
    branch_name = None
    worktree_path = None

    if use_worktree:
        # Git checks — fail loud if not current
        _check_git_current(workspace)

        # Create worktree
        ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        branch_name = f"ralph-{ts}"
        worktree_path = _create_worktree(workspace, branch_name)
        actual_workspace = worktree_path
        logger.info("Ralph working in worktree: %s", actual_workspace)
    else:
        Path(actual_workspace).mkdir(parents=True, exist_ok=True)

    run_results = []

    for i in range(n_runs):
        logger.info("Ralph run %d/%d (fresh conversation)", i + 1, n_runs)

        sdnac = _make_fresh_sdnac(plan_path, actual_workspace, tools, agent_config)
        try:
            result = await sdnac.execute({})
            status = str(result.status) if hasattr(result, "status") else "unknown"
            run_results.append({"run": i + 1, "status": status})
            logger.info("Ralph run %d/%d: %s", i + 1, n_runs, status)
        except Exception as e:
            run_results.append({"run": i + 1, "status": "error", "error": str(e)})
            logger.warning("Ralph run %d/%d failed: %s", i + 1, n_runs, e)

    # Check if PR was created
    pr_url = None
    if use_worktree and worktree_path:
        try:
            pr_url = _run_git("gh pr view --json url -q .url 2>/dev/null", worktree_path)
        except RuntimeError:
            pr_url = None

        # Clean up worktree (branch stays for PR)
        _cleanup_worktree(workspace, worktree_path, branch_name)

    result_dict = {
        "total_runs": n_runs,
        "results": run_results,
        "workspace": actual_workspace,
        "plan_path": plan_path,
    }
    if branch_name:
        result_dict["branch"] = branch_name
    if pr_url:
        result_dict["pr_url"] = pr_url
    else:
        result_dict["pr_url"] = None
        if use_worktree:
            result_dict["warning"] = "No PR created — ralph may have failed"

    return result_dict
