# JSON Registry → CartON Migration

Last updated: 2026-04-17

## What

The GIINT JSON registry (`projects.json`) stores project hierarchies + operational state (status, is_ready, assignee, specs). CartON already stores the same hierarchy via Dragonbones sync. The JSON is redundant and should be removed.

## Why

- Dragonbones `_sync_to_giint_registry` in compiler.py already writes to BOTH stores
- `has_ready_tasks` in omnisanc checks CartON `_Unnamed` nodes, not JSON `is_ready`
- JSON spec validation (`_task_has_complete_specs`) is equivalent to CartON `_Unnamed` check
- Status tracking is done by TreeKanban lanes, not JSON `TaskStatus` enum
- Assignee tracking is done by TreeKanban tags, not JSON `assignee` field

## Approach

Keep `projects.py` as API surface. Rewrite internals from `_load_projects()` → JSON to CartON queries. Same functions, same signatures, different backend.

## External Consumers (must keep working)

1. **carton daemon** (observation_worker_daemon.py:1206) — `update_task_status` for PBML auto-lane-move
2. **starlog** (starlog.py:241,309) — `create_project` on starlog init
3. **starlog_sessions** (starlog_sessions.py:356) — `ProjectRegistry` for starsystem detection
4. **compoctopus** (run_planner.py:74) — `get_registry` for planning
5. **omnisanc** (omnisanc_logic.py:42) — `has_ready_tasks`, `get_project_by_dir`, `ProjectType`

## Operational State Mapping

| JSON field | CartON equivalent |
|---|---|
| `is_ready` | `_Unnamed` check (no unnamed nodes = ready) |
| `status` | TreeKanban lane (plan/build/measure/learn/archive) |
| `is_blocked` | TreeKanban blocked lane |
| `assignee` | TreeKanban `assignee:*` tags |
| `spec` files | CartON concept descriptions (are the specs) |
| `github_issue` | CartON `has_github_issue` relationship |
| Pydantic validation | YOUKNOW/OWL type system |

## Design Decision: Code Stub Protocol

Components = code files. Created BEFORE component concept. Stubs have:
- Top-level comment with features (API design)
- Function/class signatures with `NotImplementedError`
- Docstrings pointing to CartON: `"""See: Giint_Deliverable_X"""`
- During BUILD, ralph reads stub → looks up CartON ref → implements → replaces docstring
- For existing code changes: `# Change: Giint_Task_X` comment at change point
- CA validates refs resolve, provides callgraph context

## carton_sync.py Status

5 sync functions exist, only 2 called from projects.py directly. BUT `_sync_to_giint_registry` in dragonbones/compiler.py calls ALL 5 via library functions. The carton_sync in projects.py is redundant with Dragonbones path — can be removed when JSON backend is removed.
