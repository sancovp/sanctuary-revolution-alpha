# OMNISANC CORE STATE MACHINES - COMPLETE ARCHITECTURAL DOCUMENTATION

## Executive Summary

OMNISANC Core (`/home/GOD/.claude/hooks/omnisanc_core.py`) is a PreToolUse/PostToolUse hook system enforcing a structured workflow model with two major modes (HOME and JOURNEY) and multiple nested state machines. It orchestrates transitions between organizing (HOME), flight planning (STARPORT), active work (SESSION), post-work review (LANDING), and multi-session missions (MISSION).

---

## 1. CORE PHASES AND MODES

### Phase 0: HOME Mode
**When Active:** `course_plotted == False`

- Limited tool access (read-only + navigation + planning)
- No active project work
- Strategic planning space (missions, Canopy/OPERA scheduling)
- SEED identity system available

**Transitions:**
- → JOURNEY Mode: `starship.plot_course()` or `mission_start()`

---

### Phase 1: STARPORT (Journey Mode Pre-Flight)
**When Active:** `course_plotted == True` AND `flight_selected == False`

**Sub-Phases:**
1. **LAUNCH** (`fly_called == False`): Must call `starship.fly()`
2. **FLIGHT SELECTION** (`fly_called == True`): Must call `waypoint.start_waypoint_journey()`

**Transitions:**
- → SESSION Phase: `waypoint.start_waypoint_journey()` sets `flight_selected=True`

---

### Phase 2: SESSION (Waypoint Journey Active)
**When Active:** `flight_selected == True`

**Waypoint Steps:**
1. `starlog.check()` - Project check
2. `starlog.orient()` or `init_project()` - Load/create project
3. `starlog.start_starlog()` - Activate session (`session_active=True`)
4. Work session - All tools allowed

**Transitions:**
- → LANDING Phase: `starlog.end_starlog()` sets `needs_review=True`

---

### Phase 3: LANDING (Session Post-Processing)
**When Active:** `needs_review == True`

**3-Step Sequential Enforcement:**
1. `starship.landing_routine()` → `landing_routine_called=True`
2. `starship.session_review()` → `session_review_called=True`
3. `giint.respond()` → JIT GIINT + syncs → `needs_review=False`

**Transitions:**
- → STARPORT (if mission_active) or HOME

---

### Phase 4: MISSION (Multi-Session Orchestration)
**When Active:** `mission_active == True`

- Spans multiple sessions
- Each session is a waypoint journey
- `mission.request_extraction()` → pauses (keeps mission_id)
- `mission.complete_mission()` → clears all state

---

## 2. IMPLICIT STATE MACHINES

### SM1: Course Compaction Recovery
- `was_compacted=True` → Must call `continue_course()` then `starlog.orient()`

### SM2: Session End Shield
- After compaction, first `end_starlog()` blocked (shield countdown)
- Second call allowed

### SM3: Waypoint Sequence Enforcement
- Steps 1-3 must be done in order before step 4+ work

### SM4: MISSION Enforcement Lock
- Cannot create/start missions while on course
- Cannot extract while session_active

### SM5: OPERA Schedule Lock
- Prevents freestyle Canopy additions when OPERA has work queued

### SM6: JIT GIINT Project Construction
- Auto-creates feature/component/deliverable/task on giint.respond()

---

## 3. STATE TRACKING & PERSISTENCE

### Primary State File
**Location:** `/tmp/heaven_data/omnisanc_core/.course_state`

```json
{
  "course_plotted": bool,
  "projects": [str],
  "flight_selected": bool,
  "waypoint_step": int,
  "session_active": bool,
  "mission_active": bool,
  "mission_id": str | null,
  "mission_step": int,
  "needs_review": bool,
  "landing_routine_called": bool,
  "session_review_called": bool,
  "giint_respond_called": bool,
  "was_compacted": bool,
  "continue_course_called": bool,
  "fly_called": bool,
  "session_end_shield_count": int,
  "session_shielded": bool,
  "qa_id": str | null
}
```

### Event Registries (Matryoshka)
- `home_events` / `home_events_{YYYY-MM-DD}`
- `session_events` / `session_events_{YYYY-MM-DD}`
- `mission_events` / `mission_events_{YYYY-MM-DD}`
- `session_scores`, `mission_scores`
- `last_activity_tracking`

---

## 4. REWARD COMPUTATION

### Session Reward
- Trigger: After `end_starlog()` success
- Formula: `sum(event_rewards) * SESSION_MULTIPLIER * quality_factor`
- Storage: `session_scores` registry

### Mission Reward
- Trigger: After `mission.request_extraction()`
- Formula: `sum(event_rewards) * MISSION_MULTIPLIER`
- Storage: `mission_scores` registry

---

## 5. SYNC INTEGRATIONS

### GIINT → Carton Sync
- After GIINT planning tools
- Syncs project/feature/component/deliverable/task to knowledge graph

### GIINT → TreeKanban Sync
- Pushes deliverables/tasks to TreeKanban board
- Creates pattern cards for vendored OperadicFlows
- Priority calculation: root cards get incrementing ints, sub-cards get `{parent}.{n}`

### Canopy → OPERA Pattern Detection
- After `canopy.mark_complete()`
- Triggers pattern detection and OPERA feeding

---

## 6. ERROR HANDLING

### Kill Switch
- File: `/tmp/heaven_data/omnisanc_core/.omnisanc_disabled`
- Effect: Disables all checks

### Escape Hatch
- `rm /tmp/heaven_data/omnisanc_core/.course_state`
- Returns to HOME

### Fail-Open Policy
- Any exception → allow tool (don't block)

---

## 7. STATE DIAGRAM

```
HOME MODE
  │
  │ plot_course() / mission_start()
  v
STARPORT (LAUNCH → FLIGHT_SELECTION)
  │
  │ waypoint.start_waypoint_journey()
  v
SESSION (STEP 1 → 2 → 3 → 4+ work)
  │
  │ starlog.end_starlog()
  v
LANDING (landing_routine → session_review → giint.respond)
  │
  ├─→ STARPORT (if mission_active, next session)
  ├─→ HOME + mission_id (extraction/pause)
  └─→ HOME fresh (mission complete)
```

---

## 8. PHASE TRANSITIONS TABLE

| From | To | Trigger | Key State Changes |
|------|----|---------|----|
| HOME | STARPORT | plot_course() | course_plotted=T, mission_id set |
| STARPORT | SESSION | waypoint.start() | flight_selected=T, waypoint_step=1 |
| SESSION | LANDING | end_starlog() | session_active=F, needs_review=T |
| LANDING | STARPORT/HOME | giint.respond() | needs_review=F |
| JOURNEY | HOME (pause) | request_extraction() | mission_active=F, keeps mission_id |
| JOURNEY | HOME (end) | complete_mission() | all state cleared |

---

## 9. KEY DESIGN PATTERNS

1. **State-Based Enforcement** - Check before every tool
2. **Sequential Gating** - LANDING 3 steps in order
3. **Waypoint-Driven Sessions** - Waypoint JSON is source of truth
4. **Mission as Atomic Loop** - Cannot start new while active
5. **Dual-Write Sync** - GIINT → Carton + TreeKanban
6. **Matryoshka Event Registry** - Day-based layers for temporal analysis
7. **Non-Critical Syncs** - Never block on sync failures
8. **JIT Construction** - Auto-create GIINT hierarchy on respond()

---

## 10. KNOWN ISSUES

### base_mission Auto-Activation Conflict
- STARSYSTEM auto-creates/activates base_mission
- omnisanc sees mission.status=="active" but course_state says HOME
- Invariant violated: HOME should have NO active missions

---

*Generated: Session 18 (2026-01-11)*
