# Loop Stack + OMNISANC Diagram

## The Two Axes

```
VERTICAL AXIS: Loop Depth (quality/completion enforcement)
HORIZONTAL AXIS: OMNISANC Zones (navigation/state)
```

## Full Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         METABRAINHOOK (TOP LEVEL)                           │
│  UserPromptSubmit hook - injects orchestration config every prompt          │
│  Config: /tmp/heaven_data/metabrainhook_config.json                         │
│  CANNOT BE DISABLED BY AGENT - only user can turn off                       │
│                                                                             │
│  Provides: allowed_dirs, info, goal, reminders, queue, guru_instructions    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ configures/spawns
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            GURU LOOP (L2)                                   │
│  Bodhisattva vow - must EMANATE before exit                                 │
│  "Work is not done until it's crystallized into reusable form"              │
│                                                                             │
│  Entry: /guru command                                                       │
│  Exit: samaya gate verification → emanation required                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ contains
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTOPOIESIS (L1)                                    │
│  Promise level - task completion enforcement                                │
│  "Did you actually finish what you promised?"                               │
│                                                                             │
│  MCP: autopoiesis.be_autopoietic(mode="promise"|"blocked")                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ contains
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BRAINHOOK (L0)                                     │
│  Reflection level - "look again" enforcement                                │
│  Blocks Stop hook until agent truly examines if done                        │
│                                                                             │
│  Toggle: /brainhook or `brainhook` bash command                             │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                    OMNISANC RUNS PARALLEL (HORIZONTAL AXIS)
═══════════════════════════════════════════════════════════════════════════════


┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│   HOME MODE    │────▶│ JOURNEY MODE   │────▶│   BACK HOME    │
│                │     │                │     │                │
│ No course      │     │ Course plotted │     │ Mission done   │
│ metabrainhook  │     │ Mission active │     │ metabrainhook  │
│ waiting        │     │                │     │ waiting        │
└────────────────┘     └────────────────┘     └────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      JOURNEY SUBSTATES        │
              │                               │
              │  STARPORT ──▶ LAUNCH          │
              │      │           │            │
              │      │           ▼            │
              │      │       SESSION ◀────┐   │
              │      │           │        │   │
              │      │           ▼        │   │
              │      │       LANDING      │   │
              │      │           │        │   │
              │      │           ▼        │   │
              │      └────── MISSION ─────┘   │
              │                               │
              └───────────────────────────────┘


## How They Interact

```
HOME MODE + metabrainhook active:
├── User edits metabrainhook_config.json (sets goal, queue, etc.)
├── Agent picks up config on next prompt
├── Agent can: plot_course → enters JOURNEY MODE
│
JOURNEY MODE + guru loop:
├── Mission started
├── Agent in SESSION zone
├── guru loop active (requires emanation to exit)
├── autopoiesis ensures promises kept
├── brainhook ensures reflection
│
SESSION complete:
├── LANDING zone (3-step review)
├── samaya gate checks emanation
├── If good → MISSION zone → next flight or HOME
├── If not → back to SESSION
```

## The Config Flow

```
/tmp/heaven_data/metabrainhook_config.json
         │
         │ read by metabrainhook.py on every prompt
         ▼
┌─────────────────────────────┐
│ ORCHESTRATION MODE ACTIVE   │
│ ════════════════════════    │
│ {raw JSON content}          │
│ ════════════════════════    │
│                             │
│ {brainhook_prompt.txt}      │
└─────────────────────────────┘
         │
         │ injected into prompt
         ▼
    Agent sees this every turn when metabrainhook ON
```

## State Files

| File | Purpose |
|------|---------|
| `/tmp/metabrainhook_state.txt` | on/off for metabrainhook |
| `/tmp/brainhook_state.txt` | on/off for brainhook |
| `/tmp/heaven_data/metabrainhook_config.json` | orchestration config |
| `/tmp/heaven_data/autopoiesis/promise_*.json` | promise tracking |
| `/tmp/heaven_data/omnisanc_core/.omnisanc_*` | OMNISANC state |

## Typical Flow

1. **User starts fresh** → HOME mode, metabrainhook can be on
2. **User sets config** → edits metabrainhook_config.json with goal
3. **User says "go"** → Agent plots course, enters JOURNEY
4. **Agent works** → guru loop active, autopoiesis tracks promises
5. **Agent thinks done** → brainhook says "look again"
6. **Agent really done** → samaya gate, must emanate
7. **Emanation created** → skill/flight/crystallized artifact
8. **Mission complete** → back to HOME, ready for next
