"""compile() — the Compoctopus top-level entrypoint."""

from __future__ import annotations

from typing import Optional


async def compile(
    request: str,
    project_id: Optional[str] = None,
):
    """Top-level Compoctopus entry point.

    Routes based on context:
    - project_id set + planner hasn't run → Planner first (no LLM, code decision)
    - planner already ran → Bandit for each task (SELECT/CONSTRUCT)
    - no project_id → Bandit directly

    Args:
        request: what the user wants done
        project_id: existing GIINT project or None for ad-hoc

    Returns:
        CompilationResult with outputs from all tasks
    """
    from compoctopus.agents.planner import make_planner

    ctx = {
        "request": request,
        "project_id": project_id,
        "_planner_ran": False,
    }

    # Deterministic routing — no LLM call
    if project_id and not ctx.get("_planner_ran"):
        # Route to Planner first
        planner = make_planner()
        planner_result = await planner.execute(ctx)

        # Mark planner as done so recursive Bandit calls don't re-plan
        ctx["_planner_ran"] = True

        # Get tasks from planner output, send each to Bandit
        tasks = ctx.get("tasks_created", [])
        results = []
        for task_id in tasks:
            task_ctx = {
                **ctx,
                "task_id": task_id,
                "_planner_ran": True,  # prevent re-planning
            }
            # TODO: Bandit.execute(task_ctx) once Bandit is wired as agent
            results.append(task_ctx)

        return {"status": "planned", "project_id": project_id, "tasks": tasks, "results": results}

    else:
        # No project — Bandit decides everything
        # TODO: Bandit.execute(ctx) once Bandit is wired
        return {"status": "direct", "request": request, "ctx": ctx}
