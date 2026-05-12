"""Ralph core — entry point that orchestrates context-alignment + TDD agent.

launch_ralph_compoctopus(starsystem_path, code_target, requirements_doc_path)

Flow:
1. Call context-alignment get_dependency_context for code_target
2. Read requirements doc
3. Create implementation_plan_{datetime}.md combining both
4. Create make_ralph_coder(plan_path, workspace)
5. Run agent
6. Return result (changed files on disk, ready for git diff)
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def _call_analyzer(code_target: str, search_dirs: List[str]) -> Dict[str, Any]:
    """Call analyze_dependencies directly. Raises ImportError if unavailable."""
    from dependency_analyzer import analyze_dependencies
    return analyze_dependencies(
        target_name=code_target,
        search_dirs=search_dirs,
        contextualizer=False,
        exclude_from_contextualizer=None,
        include_external_packages=True,
        external_depth=1,
        recursive=True,
        recursive_depth=5,
    )


def _get_dependency_context(code_target: str, search_dirs: List[str]) -> Dict[str, Any]:
    """Get dependency context, falling back gracefully."""
    try:
        return _call_analyzer(code_target, search_dirs)
    except ImportError:
        logger.warning("dependency_analyzer not available")
    except Exception:
        logger.warning("Dependency analysis failed:\n%s", traceback.format_exc())

    return {"status": "not_found", "dependencies": [], "file": "unknown"}


def _read_file_contents(file_path: str) -> str:
    """Read complete file contents, return empty string if missing."""
    p = Path(file_path)
    if p.exists():
        return p.read_text()
    return ""


def _collect_ordered_files(dep_result: Dict[str, Any]) -> List[str]:
    """Collect unique files from dep result in dependency order."""
    files_seen = set()
    ordered = []

    target_file = dep_result.get("file")
    if target_file:
        files_seen.add(target_file)
        ordered.append(target_file)

    for dep in dep_result.get("dependencies", []):
        dep_file = dep.get("file", "")
        if dep_file and dep_file not in files_seen:
            files_seen.add(dep_file)
            ordered.append(dep_file)

    return ordered


def _build_implementation_plan(
    code_target: str,
    dep_result: Dict[str, Any],
    requirements_content: str,
) -> str:
    """Build the implementation plan document.

    Contains:
    1. Requirements (what to build)
    2. Dependency graph (what files to read, in order)
    3. Full source code of each dependency (the actual lines)
    """
    sections = [
        f"# Implementation Plan: {code_target}",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "## Requirements",
        requirements_content,
        "",
        "## Dependency Graph",
        f"Target: {code_target}",
        f"Status: {dep_result.get('status', 'unknown')}",
        f"Target file: {dep_result.get('file', 'unknown')}",
        f"Target line range: {dep_result.get('line_range', 'unknown')}",
        "",
    ]

    deps = dep_result.get("dependencies", [])
    if deps:
        sections.append(f"### Dependencies ({len(deps)} found)")
        for dep in deps:
            sections.append(
                f"- {dep['name']} ({dep['type']}) in {dep['file']} "
                f"lines {dep.get('line_range', '?')}"
            )
        sections.append("")

    # Full source code for each file in the dependency chain
    sections.append("## Source Code (Complete Callgraph)")
    sections.append("")

    for file_path in _collect_ordered_files(dep_result):
        content = _read_file_contents(file_path)
        if content:
            sections.extend([f"### {file_path}", "```python", content, "```", ""])
        else:
            sections.extend([f"### {file_path} (NOT FOUND)", ""])

    inferred = dep_result.get("inferred_dependencies", [])
    if inferred:
        sections.append("## Inferred Dependencies (unresolved)")
        for inf in inferred:
            sections.append(
                f"- {inf.get('name', '?')} ({inf.get('kind', '?')}) "
                f"line {inf.get('line', '?')}: {inf.get('why', '')}"
            )
        sections.append("")

    return "\n".join(sections)


async def launch_ralph_compoctopus(
    starsystem_path: str,
    code_target: str,
    requirements_doc_path: str,
    workspace: Optional[str] = None,
    max_cycles: int = 5,
    test_files: Optional[List[str]] = None,
    agent_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Launch Ralph — TDD coding agent with context-alignment pre-loading.

    Args:
        starsystem_path: Root directory of the starsystem/project.
        code_target: Name of the class/function to modify (for context-alignment).
        requirements_doc_path: Path to requirements document describing what to build.
        workspace: Where ralph writes output. Defaults to starsystem_path.
        max_cycles: Maximum CODE->VERIFY cycles.
        test_files: Specific test files for verification.

    Returns:
        Dict with status, plan_path, iterations, and result details.
    """
    from compoctopus.agents.ralph.factory import run_ralph

    workspace = workspace or starsystem_path
    n_runs = max_cycles  # reuse param name, means N independent runs

    logger.info("RALPH: target=%s, workspace=%s, n_runs=%d",
                code_target, workspace, n_runs)

    # 1. Get dependency context — prefer CA cache (written by GNOSYS before launch)
    import os
    ca_cache_path = os.environ.get("RALPH_CA_CACHE", "")
    if ca_cache_path and Path(ca_cache_path).exists():
        logger.info("Using CA cache: %s", ca_cache_path)
        cache_data = json.loads(Path(ca_cache_path).read_text())
        # Cache format: {git_commit, git_dir, target_entity, search_dirs, result}
        dep_result = cache_data.get("result", cache_data)  # fallback for old format
        logger.info("Cache commit: %s", cache_data.get("git_commit", "unknown"))
    else:
        logger.info("No CA cache — calling analyzer live (slower)")
        dep_result = _get_dependency_context(code_target, [starsystem_path])
    dep_count = len(dep_result.get("dependencies", []))
    logger.info("Dependencies: %d found (status=%s)", dep_count, dep_result.get("status"))

    # 2. Read requirements
    requirements_content = _read_file_contents(requirements_doc_path)
    if not requirements_content:
        return {"status": "error", "error": f"Requirements not found: {requirements_doc_path}"}

    # 3. Build implementation plan
    plan_content = _build_implementation_plan(code_target, dep_result, requirements_content)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_dir = Path("/tmp/ralph_runs")
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = str(plan_dir / f"implementation_plan_{timestamp}.md")
    Path(plan_path).write_text(plan_content)
    logger.info("Plan: %s (%d lines)", plan_path, plan_content.count("\n"))

    # 4. Run ralph N times (each is a fresh conversation)
    try:
        result = await run_ralph(
            plan_path=plan_path,
            workspace=workspace,
            n_runs=n_runs,
            agent_config=agent_config,
        )
        result["plan_path"] = plan_path
        logger.info("RALPH COMPLETE: %d runs", n_runs)
        return result
    except Exception:
        logger.error("Ralph failed:\n%s", traceback.format_exc())
        return {"status": "error", "error": traceback.format_exc(), "plan_path": plan_path}


def launch_ralph_sync(
    starsystem_path: str,
    code_target: str,
    requirements_doc_path: str,
    **kwargs,
) -> Dict[str, Any]:
    """Synchronous wrapper for launch_ralph_compoctopus."""
    return asyncio.run(
        launch_ralph_compoctopus(
            starsystem_path, code_target, requirements_doc_path, **kwargs
        )
    )
