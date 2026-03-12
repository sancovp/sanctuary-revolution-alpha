# SOSEEH → PAIA-builder Mapping

## What is SOSEEH?

**SOSEEH** = System-of-Systems Extreme Environment Handling

A 2-minute coordination decomposition lens with four components:
- **Pilot** - The human controller (OVP = Victory-Promise, OVA = Victory-Actual)
- **Vehicle** - The AI system being constructed
- **Mission Control** - The coordination/monitoring layer
- **Interaction Loops** - The operational patterns

---

## Implementation Status in paia_builder

### 1. PILOT ✅ Fully Implemented

**Location:** `paia_builder/models.py` → `Player` class (line 562)

```python
class Player(BaseModel):
    """[PILOT] Player - the one constructing Vehicles.

    In SOSEEH: Pilot = Player = OVP (Victory-Promise).
    The Pilot builds and commands multiple Vehicles (PAIAs).
    """
    name: str
    paias: List[PAIA]  # G = Gear = PAIAs (the pilot's fleet)
    gear_state: GEAR   # Player-level progression
```

**Frontend terminology:** "Pilot" (the user building their AI system)

**States:**
- OVP (Victory-Promise): `overall < 50%` - "Promise declared, building Vehicle"
- OVA (Victory-Actual): `overall >= 50%` - "Capability manifest"

---

### 2. VEHICLE ✅ Fully Implemented

**Location:** `paia_builder/models.py` → `PAIA` class (line 647)

```python
class PAIA(BaseModel):
    """[VEHICLE] Personal AI Agent - the hull you are constructing.

    PAIA = Vehicle in SOSEEH. You (Pilot) build this Vehicle.
    """
    # 16 subsystem types:
    skills, mcps, hooks, commands, agents, personas, plugins, flights,
    metastacks, giint_blueprints, operadic_flows, frontend_integrations,
    automations, agent_gans, agent_duos, system_prompts
```

**Frontend terminology:** "Vehicle" (the Docker image / PAIA container)

**Construction tracked via:**
- GEAR state: G (subsystems), E (experience), A (achievements), R (reality)
- Tier progression: none → common → uncommon → rare → epic → legendary
- Goldenization: quarantine → crystal → golden

---

### 3. MISSION CONTROL ⚠️ Partial

**Location:** `paia_builder/models.py` → `FrontendIntegrationSpec` (line 293)

```python
class FrontendIntegrationSpec(ComponentBase):
    """Frontend integration - UI tools like TreeKanban."""
    integration_type: str  # e.g., "treekanban", "dashboard"
```

**Status check in core.py:**
```python
mc_state = "[MISSION CONTROL] " + ("Online" if paia.frontend_integrations else "Not established")
```

**What's missing:**
- No dedicated Mission Control class
- No real-time monitoring models
- No operator dashboard spec
- No alert/notification system

**Frontend (heaven_chat):** The Electron app IS Mission Control, but not modeled in paia_builder yet.

---

### 4. INTERACTION LOOPS ⚠️ Implemented But Not Modeled in paia_builder

**Current state in paia_builder:**
```python
loop_state = "[LOOPS] Default chat loop active"
```
Always shows "Default chat loop" - no tracking of which loop is active.

**Actually Implemented Loops:**

| Loop | Implementation | What It Does |
|------|---------------|--------------|
| **autopoiesis** | `autopoiesis_mcp` | Self-maintaining work loop. Promise mode (commit to work) or Blocked mode (need help). "Disingenuousness is death." |
| **brainhook** | `brainhook.py` hook | Toggle state that reminds agent to use compound intelligence systems |
| **guru loop** | `/autopoiesis:guru` skill | Bodhisattva vow - must create emanation (skill/flight) before exit |
| **ralph (Ralph Wiggum)** | `/ralph-wiggum:ralph-loop` skill | Specific technique for handling certain interaction patterns |

**Loop Lifecycle:**
```
Default Chat Loop
    ↓ (user triggers loop)
Specific Loop Active (autopoiesis, guru, ralph, etc.)
    ↓ (promise → work → completion OR blocked)
Back to Default
```

**What's Missing in paia_builder:**
- No `InteractionLoopSpec` model to define loop types
- No tracking of which loop is active
- No loop state machine (transitions, exit conditions)
- Loops exist as skills/hooks but not as first-class data

---

## Frontend (heaven_chat) Mapping

| SOSEEH | Backend (paia_builder) | Frontend (heaven_chat) |
|--------|------------------------|------------------------|
| Pilot | Player class | User profile / Login |
| Vehicle | PAIA class | Docker container / "Vehicle" image |
| Mission Control | frontend_integrations | Electron app dashboard |
| Interaction Loops | (not modeled) | ReactFlow boards / Space buttons |

---

## Gaps to Fill

### Priority 1: Mission Control Model
```python
class MissionControlSpec(ComponentBase):
    """Mission Control - monitoring and coordination."""
    dashboard_type: str  # "treekanban", "hud", "monitor"
    data_sources: List[str]  # What this monitors
    alerts: List[str]  # Alert conditions
    operator_actions: List[str]  # What operator can do
```

### Priority 2: Interaction Loop Registry
```python
class InteractionLoopSpec(ComponentBase):
    """Interaction Loop - a named operational pattern for running the PAIA."""
    loop_type: str  # "autopoiesis", "guru", "ralph", "brainhook", "gan", "duo"
    implementation: str  # "mcp", "hook", "skill" - how it's implemented
    implementation_ref: str  # e.g., "autopoiesis_mcp", "brainhook.py"
    triggers: List[str]  # What activates this loop (slash command, hook, etc.)
    exit_conditions: List[str]  # "DONE", "blocked", "emanation_created"
    state_file: Optional[str]  # Where state persists (e.g., /tmp/active_promise.md)
```

### Priority 3: Loop State Tracking
Track which loop is active per PAIA:
```python
class LoopState(BaseModel):
    """Current loop state for a PAIA."""
    active_loop: Optional[str]  # Name of active InteractionLoopSpec
    started_at: datetime
    iteration: int
    promise_file: Optional[str]
    block_report: Optional[str]
```

---

## Key Insight

**SOSEEH is the lens, PAIA-builder is the implementation.**

- Pilot/Vehicle mapping is complete and working
- Mission Control exists conceptually but needs richer modeling
- Interaction Loops are the biggest gap - we have loop types (GAN, DUO, operadic) but no unified loop tracking

The Electron frontend (heaven_chat) IS Mission Control in practice, but the backend doesn't model it properly yet.

---

*Session 18 (2026-01-11)*
