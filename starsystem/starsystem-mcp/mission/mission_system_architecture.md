# Mission System Architecture

## Overview

Mission system provides cross-session sequence enforcement with step injection, ratcheting on failure, and mission extraction capabilities.

## Core Concepts

### Mission = Cross-Session Enforcement
- **Flight Config**: Enforces pattern WITHIN a session (start → work → end)
- **Mission**: Enforces pattern ACROSS sessions (session 1 → session 2 → session 3)

### Key Features

1. **Sequential Enforcement**: Forces ordered execution of sessions
2. **Step Injection**: Add new steps before current step as obstacles are discovered
3. **Ratcheting**: On abort, stay at current step (don't lose progress)
4. **Mission Extraction**: Analyze failure, generate report, reset to HOME

## Integration with OMNISANC Core

### Course State Extensions

```json
{
  "course_plotted": true,
  "projects": [...],
  "mission_active": false,        // NEW: Is mission running?
  "mission_id": null,              // NEW: Active mission ID
  "mission_step": 0,               // NEW: Current step in sequence
  "flight_selected": false,
  "waypoint_step": 0,
  "session_active": false
}
```

### Enforcement Flow

```
Mission Active + Session Ends:
  1. end_starlog() called
  2. session_active = false
  3. OMNISANC checks: mission_active && has_more_steps?
  4. If yes: Block all tools except starting next session
  5. Error message shows: next project_path + flight_config
  6. User must call waypoint.start_waypoint_journey() for next step
```

### Abort Behavior

```
Without Mission:
  abort() → flight_selected = false, waypoint_step = 0
  Clean reset

With Mission:
  abort() → mission.session_sequence[current_step].status = "aborted"
  mission_step stays same (ratcheting!)
  User options:
    A) waypoint.start() → retry same step
    B) mission.request_extraction() → analyze + reset to HOME
```

## Mission Lifecycle

### 1. Creation (at HOME)
```python
mission.create(
  name="Complete Auth Feature",
  session_sequence=[
    {project_path: "/proj1", flight_config: "flight1.json"},
    {project_path: "/proj2", flight_config: "flight2.json"}
  ]
)
```

### 2. Activation
```python
mission.start(mission_id="auth_feature")
# Sets: mission_active=true, mission_step=0
# Forces: waypoint.start() for first session
```

### 3. Execution
```
For each step in session_sequence:
  1. OMNISANC enforces: must start this specific session
  2. waypoint.start(flight_config, project_path)
  3. check → orient → start_starlog (waypoint enforcement)
  4. Work in session
  5. end_starlog()
  6. mission_step++ (advance)
  7. Repeat for next step
```

### 4. Step Injection
```python
mission.inject_step(
  before_step=3,
  project_path="/proj2",
  flight_config="new_step.json",
  notes="Discovered we need database migration first"
)
# Inserts new step, shifts remaining steps
# current_step stays same (now points to new injected step)
```

### 5. Completion or Extraction
```
Success: All steps completed
  → mission.status = "completed"
  → mission_active = false
  → Optionally save as template

Failure: abort() at some step
  → mission.request_extraction()
  → Generates failure report
  → Resets to HOME mode
  → Returns analysis
```

## Storage Structure

```
/tmp/heaven_data/missions/
├── active/
│   └── {mission_id}.json          # Currently active mission
├── completed/
│   └── {mission_id}.json          # Completed missions
├── aborted/
│   └── {mission_id}.json          # Failed missions
└── templates/
    └── {template_name}.json       # Reusable mission templates
```

## MCP Tools API

### mission.create()
- Creates new mission definition
- Stores in `/tmp/heaven_data/missions/active/`
- Available only in HOME mode

### mission.start(mission_id)
- Activates mission
- Updates OMNISANC course state
- Forces first session start

### mission.get_status()
- Returns current mission progress
- Shows completed/pending/current steps
- Available anytime

### mission.inject_step(before_step, project_path, flight_config, notes)
- Inserts new step before specified step
- Shifts remaining steps
- Updates current_step if needed

### mission.request_extraction()
- Analyzes mission failure
- Generates report
- Moves to aborted/
- Resets to HOME mode
- Returns analysis

### mission.list(status=None)
- Lists missions (all, active, completed, aborted)
- Filterable by domain, subdomain

### mission.save_as_template(mission_id, template_name)
- Saves completed mission as reusable template
- Stores in templates/

### mission.from_template(template_name, **overrides)
- Creates new mission from template
- Allows parameter overrides

## Reward Signal Integration

Missions track metrics for reward calculation:
- `conversations_count`: Across all sessions
- `sessions_completed`: Successfully finished sessions
- `current_step`: Progress tracking
- `status`: Overall outcome

These feed into HOME stats and reward scoring system.

## Evolution Path

```
Mission Execution
  ↓
Pattern Discovery (what worked/failed)
  ↓
Mission Template (save corrected version)
  ↓
Flowchain (formalized in OMNISANC Full)
  ↓
Auto-Enforcement (proven patterns become rules)
```

## Example Workflow

```
# At HOME
mission.create(name="Build Auth", session_sequence=[...])
mission.start("auth_feature")

# Journey enforces first session
waypoint.start("flight1.json", "/proj1")
# ... work ...
end_starlog()

# Mission enforces next session
waypoint.start("flight2.json", "/proj2")
# ... hit obstacle ...

# Inject new step
mission.inject_step(before_step=2, project_path="/proj2",
                   flight_config="migration.json",
                   notes="Need DB migration first")

# Continue with injected step
waypoint.start("migration.json", "/proj2")
# ... complete ...
end_starlog()

# Continue original sequence
# ... complete all steps ...

# Save corrected version
mission.save_as_template("auth_feature", "auth_build_with_migration")
```

## OMNISANC Core Enforcement Points

1. **After plot_course()**: Check if mission_active
2. **After end_starlog()**: Advance mission_step, enforce next session
3. **On abort()**: Update step status, preserve mission_step (ratcheting)
4. **Before any tool**: If mission_active && !at_correct_step, block

This creates unbreakable cross-session enforcement while maintaining flexibility through step injection.
