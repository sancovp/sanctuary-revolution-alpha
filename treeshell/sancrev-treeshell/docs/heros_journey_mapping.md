# Sanctuary Revolution: Hero's Journey Mapping

## OMNISANC Phases as Hero's Journey

The omnisanc_core.py state machine implements the Hero's Journey monomyth as a workflow structure.

---

## The Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                     ACT 1: ORDINARY WORLD                        │
│                                                                  │
│  HOME MODE                                                       │
│  - Limited tools (planning, navigation, identity)                │
│  - SEED system: who_am_i, what_do_i_do, how_do_i                │
│  - Strategic planning (missions, Canopy/OPERA)                  │
│  - This is where the 4 SANCREV zones live                       │
│                                                                  │
│  plot_course() = THE CALL TO ADVENTURE                          │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           v
┌─────────────────────────────────────────────────────────────────┐
│                   CROSSING THE THRESHOLD                         │
│                                                                  │
│  STARPORT PHASE                                                  │
│  - LAUNCH: starship.fly() - survey the special world             │
│  - FLIGHT SELECTION: waypoint.start() - commit to the journey   │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           v
┌─────────────────────────────────────────────────────────────────┐
│                    ACT 2: SPECIAL WORLD                          │
│                                                                  │
│  SESSION PHASE                                                   │
│                                                                  │
│  Waypoint Steps 1-3: TESTS, ALLIES, APPROACH                    │
│  - starlog.check() - survey the territory                        │
│  - starlog.orient() - gather allies (load context)              │
│  - starlog.start_starlog() - approach the inmost cave           │
│                                                                  │
│  Waypoint Step 4+: THE ORDEAL                                   │
│  - All tools allowed                                             │
│  - The actual work happens here                                  │
│  - Events logged to session_events registry                      │
│                                                                  │
│  end_starlog() = SEIZING THE REWARD                             │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           v
┌─────────────────────────────────────────────────────────────────┐
│                    ACT 3: THE RETURN                             │
│                                                                  │
│  LANDING PHASE = THE ROAD BACK                                  │
│                                                                  │
│  Step 1: landing_routine()                                       │
│  - Facing death/transformation                                   │
│  - Learning what LANDING means                                   │
│                                                                  │
│  Step 2: session_review()                                        │
│  - The Resurrection moment                                       │
│  - Reviewing and crystallizing the experience                    │
│                                                                  │
│  Step 3: giint.respond()                                         │
│  - RETURN WITH THE ELIXIR/BOON                                  │
│  - JIT constructs GIINT hierarchy                                │
│  - Syncs to Carton (knowledge graph)                            │
│  - Syncs to TreeKanban (task board)                             │
│  - The crystallized intelligence IS the boon                     │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           v
┌─────────────────────────────────────────────────────────────────┐
│                   MASTER OF TWO WORLDS                           │
│                                                                  │
│  HOME MODE (return)                                              │
│  - Now enriched with the boon                                    │
│  - Can start new journey (repeat cycle)                          │
│  - Or extract mission (pause with gains)                         │
│  - Or complete mission (full mastery)                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Terms

| Omnisanc Term | Hero's Journey | Description |
|---------------|----------------|-------------|
| HOME | Ordinary World | Where you ARE (planning, identity) |
| JOURNEY | The Adventure | Everything outside HOME |
| STARPORT | Crossing Threshold | Committing to the quest |
| SESSION | Special World | Where work happens |
| LANDING | The Return | Coming back transformed |
| giint.respond() | The Boon/Elixir | Crystallized intelligence |

---

## MISSION as Repeating Cycle

A MISSION spans multiple Hero's Journeys:

```
MISSION = [session_1, session_2, session_3, ...]

Each session IS a complete Hero's Journey:
  HOME → STARPORT → SESSION → LANDING → HOME

The mission_id persists across journeys.
request_extraction() = pause between journeys
complete_mission() = full series complete
```

---

## SANCREV 4 Zones in This Model

The 4 zones (HOME/OMNISANC, PAIAB, SANCTUM, CAVE) map to:

**HOME/OMNISANC** = The hub between journeys
- Zone selection happens here
- Cross-zone summary HUD
- Strategic planning

**PAIAB/SANCTUM/CAVE** = Different "Special Worlds"
- Each zone is a different type of journey
- plot_course() with zone-specific projects
- Zone-specific SESSION work
- Zone-specific boons returned

---

## The Boon Structure

What giint.respond() produces:

```
BOON (crystallized intelligence)
├── GIINT Hierarchy (feature/component/deliverable/task)
├── Carton Knowledge Graph (persistent memory)
├── TreeKanban Cards (actionable tasks)
└── Session Score (reward computation)
```

The boon is not just knowledge - it's **structured, actionable, persistent**.

---

*Session 18 (2026-01-11)*
