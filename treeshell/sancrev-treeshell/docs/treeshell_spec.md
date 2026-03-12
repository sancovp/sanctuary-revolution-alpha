# Sanctuary Revolution TreeShell Spec

## The Simple Flow

```
1. Call with ""     → HUD shows recent activity
2. See what's up    → "Oh yeah, I was doing X"
3. Load context     → Back to where you were
4. Continue         → Not complicated
```

---

## TreeShell Structure

```
sanctuary-revolution
├── crystal_forest (HOME)
│   ├── hud          → Show recent activity, current state
│   ├── basins       → List all context basins (projects)
│   ├── enter        → Enter a basin (load context)
│   └── status       → Full memory palace status
│
├── starport (NAVIGATION)
│   ├── flights      → List available flights for current basin
│   ├── launch       → Start a flight (waypoint journey)
│   └── missions     → Active/recent missions
│
├── session (WORK)
│   ├── current      → What am I doing right now?
│   ├── log          → Log a JourneyLog event
│   └── checkpoint   → Save progress mid-session
│
├── landing (EXTRACTION)
│   ├── extract      → Pull learnings from session
│   ├── crystallize  → Turn learning into skill/rule
│   └── complete     → End session, return home
│
└── night (AUTONOMOUS)
    ├── queue        → Night work queue
    ├── dreams       → Dream insights from last night
    └── schedule     → Schedule night flights
```

*Numeric coordinates emerge from tree structure at runtime.*

---

## Commands

### Root: `""`
Shows HUD with:
- Current state (where you are in the game)
- Recent activity (last 3-5 things)
- Active mission (if any)
- Quick actions

```
╔══════════════════════════════════════════════════════════════╗
║  SANCTUARY REVOLUTION                                        ║
╠══════════════════════════════════════════════════════════════╣
║  State: CRYSTAL_FOREST                                       ║
║  Basin: sanctuary-revolution (last active)                   ║
║  Mission: None active                                        ║
╠══════════════════════════════════════════════════════════════╣
║  Recent:                                                     ║
║  • 2m ago: Documented groundhogs_day_game.md                ║
║  • 15m ago: Updated creation_processes.md                   ║
║  • 1h ago: Created soseeh_paia_mapping.md                   ║
╠══════════════════════════════════════════════════════════════╣
║  Quick: [enter] Resume basin  [flights] See flights          ║
╚══════════════════════════════════════════════════════════════╝
```

### `nav`
Shows full tree structure (standard TreeShell)

### `jump <coord>`
Navigate to any node

### `<coord>.exec {args}`
Execute action at coordinate

---

## Key Actions

### `hud` - The Essential First Call
```python
def hud():
    """Show current state and recent activity."""
    return {
        "state": get_omnisanc_state(),
        "basin": get_current_basin(),
        "mission": get_active_mission(),
        "recent": get_recent_activity(limit=5),
        "quick_actions": get_contextual_actions()
    }
```

### `enter` - Load Context
```python
def enter(basin: str):
    """Enter a context basin (load its context)."""
    # 1. Orient STARLOG to this project
    starlog.orient(basin)
    # 2. Equip relevant skills
    equip_basin_skills(basin)
    # 3. Load CartON identity
    load_carton_context(basin)
    # 4. Update omnisanc state
    omnisanc.transition("STARPORT")
    return f"Entered {basin}. Context loaded. Ready for flight select."
```

### `launch` - Start Flight
```python
def launch(flight: str):
    """Launch a flight (start waypoint journey)."""
    # 1. Start waypoint journey
    waypoint.start_journey(flight, starlog_path=current_basin)
    # 2. Update omnisanc state
    omnisanc.transition("SESSION")
    return f"Launched {flight}. First waypoint ready."
```

### `extract` - Pull Learnings
```python
def extract():
    """Extract learnings from current session."""
    # 1. Review JourneyLogs from this session
    logs = get_session_journey_logs()
    # 2. Identify patterns/learnings
    learnings = analyze_logs(logs)
    # 3. Suggest crystallizations
    suggestions = suggest_crystallizations(learnings)
    return {
        "logs": logs,
        "learnings": learnings,
        "suggestions": suggestions
    }
```

---

## State Machine (Omnisanc Integration)

```
ZONE_IN (default)
    │
    ├── Call "" or hud → Show HUD
    │
    └── enter(basin) → STARPORT
                           │
                           ├── flights → List flights
                           │
                           └── launch(flight) → SESSION
                                                   │
                                                   ├── Work happens
                                                   ├── log() → Record JourneyLog
                                                   │
                                                   └── checkpoint/complete → LANDING
                                                                               │
                                                                               ├── extract → Pull learnings
                                                                               ├── crystallize → Make skill/rule
                                                                               │
                                                                               └── complete → CRYSTAL_FOREST
```

---

## Persistence

State persists to:
```
/tmp/heaven_data/sancrev/
├── state.json           # Current omnisanc state
├── current_basin.json   # Which basin is active
├── recent_activity.json # Last N actions
├── hud_config.json      # HUD customization
└── night_queue.json     # Queued night work
```

---

## The Simplicity

**Zone in flow:**
```
1. sancrev ""           → HUD shows recent stuff
2. "Oh I was doing X"   → sancrev enter X
3. Context loaded       → sancrev flights (or resume)
4. Choose flight        → sancrev launch Y
5. Work                 → Session with waypoints
6. Done                 → sancrev complete
```

**That's it.** Not complicated. Just making explicit what you'd do anyway, with persistence so you don't lose context.

---

## Implementation Notes

This wraps existing MCPs:
- STARLOG for project tracking
- STARSHIP for flights
- WAYPOINT for step execution
- CartON for memory
- Omnisanc for state enforcement

Sancrev TreeShell is the **game interface** over these systems.

---

*Session 18 (2026-01-11)*
