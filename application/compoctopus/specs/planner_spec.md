# Planner Spec — CompoctopusAgent (coded)

## Name
planner

## What It Compiles
Request context → GIINT project structure.

Given a request string and an optional project_id:
- If project_id exists: query it, atomize the request into its hierarchy
- If project_id is None: create a new project, then atomize into it

## Routing (compile() entrypoint)

The Bandit is always the entry point. But the routing is
**deterministic code, not an LLM call**:

```python
if project_id and not ctx["_planner_ran"]:
    # Code decision — no LLM call
    ctx["_planner_ran"] = True
    planner.execute(ctx)  # decompose into GIINT
    for task in tasks:
        bandit.execute(task_ctx)  # _planner_ran=True prevents re-planning

else:
    bandit.execute(ctx)  # no project — Bandit decides everything
```

This means:
- First call with project_id → Planner runs (deterministic, not LLM)
- Tasks returning from Planner go to Bandit with _planner_ran=True
- Bandit never re-plans — it does SELECT/CONSTRUCT on each task
- No project_id → Bandit handles directly

## Tools
- giint-llm-intelligence MCP (create_project, add_feature_to_project,
  add_component_to_feature, add_deliverable_to_component,
  add_task_to_deliverable, get_project_overview, update_task_status)
- NetworkEditTool — read specs, existing code, project files
- BashTool — inspect filesystem, check state

## State Machine
    PLAN → VALIDATE → PLAN|DONE

## Context Keys
- request: str — the user's request
- project_id: Optional[str] — existing project or None
- _planner_ran: bool — prevents re-planning on recursive Bandit calls
- tasks_created: List[str] — task_ids created by Planner

## Factory
make_planner() → CompoctopusAgent
  - SM: PLAN → VALIDATE → DONE
  - HermesConfig: backend="heaven", model="minimax"
  - Tools: [BashTool, NetworkEditTool]
  - MCP: giint-llm-intelligence
  - System prompt: PLANNER_SYSTEM_PROMPT (in octopus_coder.py)
