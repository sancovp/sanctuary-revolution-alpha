# HOME MODE - Complete Map

## What HOME Is

HOME (Heuristic Ontological Maturation Experience) is:
- The **ordinary world** between journeys
- Where **strategic planning** happens
- Where the **4 zones are visible** as options
- Where you **cannot do work** (only plan it)

---

## The 4 Zones in HOME

```
HOME / OMNISANC (main HUD)
│
├── PAIAB Zone
│   └── PAIA construction + GEAR progression
│
├── SANCTUM Zone
│   └── Life architecture + personal development
│
└── CAVE Zone
    └── Funnel + business + monetization
```

Each zone is a **different type of journey** you can embark on.

---

## HOME Mode Allowed Tools

### Identity & Orientation (SEED)
- `seed.home` - HOME HUD display
- `seed.who_am_i` - Identity inquiry
- `seed.what_do_i_do` - Purpose inquiry
- `seed.how_do_i` - Methods inquiry

### Navigation & Discovery
- Skill Manager (equip, search, list)
- GNOSYS Kit (discover actions, navigate MCPs)
- Read tools (Read, Glob, Grep)

### Strategic Planning
- `starship.plot_course` - **Start a journey** (exit HOME)
- `starship.launch_routine` - Learn about STARSHIP
- `starship.fly` - Browse available flights

### Mission Management
- `mission_create` - Plan a multi-session mission
- `mission_start` - Begin a mission
- `mission_list` - View all missions
- `mission_get_status` - Check mission state
- `view_mission_config` - See mission details

### Work Queue (Canopy/OPERA)
- `canopy.view_schedule` - See queued work
- `canopy.get_next_item` - What's next?
- `opera.view_patterns` - See golden patterns
- `opera.view_flows` - See operadic flows

### Knowledge & Context
- Carton (knowledge graph queries)
- TOOT (train of thought context)
- Registry tools (read-only)

### Observability
- `check_selfplay_logs` - See what happened
- `get_fitness_score` - Performance metrics
- `toggle_omnisanc` - Emergency disable

### Escape Hatch
- `rm .course_state` - Reset to fresh HOME
- `network_edit_tool` - Edit omnisanc if locked

---

## HOME Mode BLOCKED Tools

- **All write/edit tools** (no work in HOME)
- **Bash execution** (except safe rm)
- **starlog tools** (those are for SESSION)
- **Any tool that modifies code**

---

## HOME HUD - What Should Be Displayed

```
╔══════════════════════════════════════════════════════════════════╗
║  🏠 HOME - OMNISANC Emergence Engineering Suite                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ZONES:                                                          ║
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                ║
║  │   PAIAB     │ │   SANCTUM   │ │    CAVE     │                ║
║  │  L5 / 13    │ │  L2 / 13    │ │  L1 / 13    │                ║
║  │  ████░░░░░  │ │  ██░░░░░░░  │ │  █░░░░░░░░  │                ║
║  │  38% GEAR   │ │  15% GEAR   │ │  8% GEAR    │                ║
║  └─────────────┘ └─────────────┘ └─────────────┘                ║
║                                                                  ║
║  WORK QUEUE (Canopy):                                           ║
║  → Next: "Implement PAIAB HUD wrapper function"                 ║
║  → 3 items in queue                                             ║
║                                                                  ║
║  MISSIONS:                                                       ║
║  → Active: base_mission_20260110 (step 0)                       ║
║  → Paused: none                                                  ║
║                                                                  ║
║  RECENT BOONS:                                                   ║
║  → Session 17: omnisanc_state_machines.md                       ║
║  → Session 16: sancrev_architecture_spec.md                     ║
║                                                                  ║
║  ACTIONS:                                                        ║
║  [1] plot_course → Start journey to a zone                      ║
║  [2] mission_start → Begin a mission                            ║
║  [3] canopy.get_next_item → See next queued work                ║
║  [4] seed.who_am_i → Identity check                             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Transitions OUT of HOME

### To PAIAB Zone
```
starship.plot_course(
    project_paths="/tmp/paia-builder",
    description="PAIAB work",
    domain="paiab"
)
```

### To SANCTUM Zone
```
starship.plot_course(
    project_paths="/tmp/sanctum-builder",
    description="SANCTUM work",
    domain="sanctum"
)
```

### To CAVE Zone
```
starship.plot_course(
    project_paths="/tmp/cave-builder",
    description="CAVE work",
    domain="cave"
)
```

---

## What Happens When You Return to HOME

After a journey (SESSION → LANDING → giint.respond):

1. **Boon is crystallized** - GIINT hierarchy created
2. **Knowledge persisted** - Carton updated
3. **Tasks created** - TreeKanban updated
4. **Score computed** - Session reward logged
5. **Back to HOME** - Ready for next journey

The HOME HUD should show:
- Updated zone progress (GEAR levels)
- New boons in "Recent Boons"
- Updated work queue
- Mission status (if in mission)

---

## HOME as the Integration Point

HOME is where everything comes together:

```
              ┌──────────────┐
              │     HOME     │
              │  (overview)  │
              └──────┬───────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         v           v           v
    ┌────────┐  ┌────────┐  ┌────────┐
    │ PAIAB  │  │SANCTUM │  │  CAVE  │
    │  zone  │  │  zone  │  │  zone  │
    └────────┘  └────────┘  └────────┘
         │           │           │
         └───────────┼───────────┘
                     │
                     v
              ┌──────────────┐
              │  Canopy/OPERA│
              │ (work queue) │
              └──────────────┘
                     │
                     v
              ┌──────────────┐
              │   Missions   │
              │(multi-session│
              │   journeys)  │
              └──────────────┘
```

---

## Key Insight

**HOME is not empty waiting.** HOME is:
- Active strategic planning
- Viewing overall progress
- Selecting next journey
- Managing work queues
- Reviewing past boons

The problem has been: **no HUD shows this**. The agent arrives at HOME blind, with no display of:
- Zone states
- Work queue
- Mission status
- Recent boons
- Available actions

**Building the HOME HUD is priority #1.**

---

*Session 18 (2026-01-11)*
