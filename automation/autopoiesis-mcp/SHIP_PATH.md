# SHIP PATH - Task Order (Jan 30, 2026)

## Current State
- Skill Gap Detection: ✅ DONE (Phase 1-4)
- DESCRIBES relationships: ✅ DONE
- Debug Diary → CartON: ✅ DONE
- Health Scoring: ✅ DONE (emanation, smells, complexity, kg_depth all query CartON)
- **Dependency:** GIINT→CartON mirroring (for full KG depth scores)

---

## PHASE 1: STARSYSTEM Entity (blocks Phase 2 + 3)

**Goal:** STARSYSTEM = STARLOG + GIINT + Git as first-class CartON entity

- [x] 1.1 Create STARSYSTEM concept type in CartON ✅
- [x] 1.2 Wire auto-creation in `starlog.init_project()` ✅
- [x] 1.3 Wire GIINT linking (via giint_project_id param) ✅
- [x] 1.4 Wire Git detection (.git dir check) ✅

**Spec:** `/tmp/autopoiesis_mcp/SKILL_GAP_DETECTION_SPEC.md` (bottom section)

---

## PHASE 2: Scoring Completion

- [x] 2.1 KG Depth → query STARSYSTEM entity completeness ✅
  - Implemented in `reward_system._get_kg_depth_score()`
  - Queries CartON (not GIINT JSON) - correct architecture
  - **Dependency:** GIINT→CartON mirroring needed for full scores (currently returns 0 for GIINT hierarchy)
- [x] 2.2 Architecture → DEFERRED (use skill for knowledge, codenose for scoring)

---

## PHASE 3: HOME Dashboard ✅

**Goal:** Global view of all STARSYSTEMs when no course plotted

- [x] 3.1 Query all STARSYSTEM entities from CartON ✅
- [x] 3.2 Show aggregate health across all projects ✅
- [x] 3.3 `orient()` with no path → global dashboard ✅

**Implementation:** `starlog_mcp.py:_get_home_dashboard()` + modified `orient(path=None)`

---

## PHASE 4: TreeKanban

**Goal:** Task management integrated with GIINT

- [ ] 4.1 TBD - need to define what TreeKanban is
- [ ] 4.2 Integration with GIINT hierarchy

---

## PHASE 5: Frontend

**Goal:** Visual interface for the system

- [ ] 5.1 Hook up to harness HTTP server (`:8080`)
- [ ] 5.2 SSE events for live updates
- [ ] 5.3 Zone rendering (SANCTUM/PAIAB/CAVE)

---

## PHASE 6: Containerization

**Goal:** Docker-based deployment

- [ ] 6.1 Docker compose for entire system
- [ ] 6.2 MCP servers as services
- [ ] 6.3 Volume mounts for persistence
- [ ] 6.4 Network config for inter-service communication

---

## PHASE 7: Verification

**Goal:** Prove it works from scratch

- [ ] 7.1 Fresh install on clean machine
- [ ] 7.2 End-to-end test (create project → work → see health)
- [ ] 7.3 Fix whatever breaks
- [ ] 7.4 Document installation steps

---

## PHASE 8: Ship

**Goal:** Public release

- [ ] 8.1 Publish packages (pip)
- [ ] 8.2 GitHub releases
- [ ] 8.3 README / documentation
- [ ] 8.4 License finalization

---

## PHASE 9: Content

**Goal:** Community building

- [ ] 9.1 Videos showing the system
- [ ] 9.2 Discord setup
- [ ] 9.3 Find early adopters
- [ ] 9.4 Word of mouth

---

## Dependencies

```
Phase 1 (STARSYSTEM)
    ↓
Phase 2 (Scoring) + Phase 3 (HOME)
    ↓
Phase 4 (TreeKanban) - can parallel with 5
    ↓
Phase 5 (Frontend)
    ↓
Phase 6 (Containerization)
    ↓
Phase 7 (Verification)
    ↓
Phase 8 (Ship)
    ↓
Phase 9 (Content)
```

---

## PHASE 0: OPERA Integration (can do anytime)

**Goal:** Resolve OPERA/GIINT be_myself wiring with new STARSYSTEM scoring

- [ ] 0.1 Implement `flight_predictor.ask_OPERA()`
- [ ] 0.2 Check OPERA wiring with new STARSYSTEM health scoring
- [ ] 0.3 Resolve GIINT `be_myself` to use OPERA properly

**Context:** OPERA is the decision-making layer. Needs to integrate with health scoring so it can recommend flights/actions based on STARSYSTEM state.

---

## MVP Cut Line

**For MVP, can skip:**
- 2.2 Architecture scoring (heuristic is fine)
- 4.x TreeKanban (can add post-ship)
- Parts of 5.x Frontend (CLI-first is fine)

**MVP = Phases 1, 2.1, 3, 6, 7, 8**

---

## DESIGN DECISIONS NEEDED (before Phase 2)

### KG Depth System - DECIDED

**What KG Depth actually measures:**

**Layer 1: GIINT Coverage (per STARSYSTEM)**
- JIT creates skeleton automatically (Project, basic Features from dirs)
- Agent/user completes it (Components, Deliverables, proper hierarchy, skills)
- Score = how much you've fleshed out beyond JIT baseline

**Layer 2: Inter-STARSYSTEM Relations**
- How do all codebases relate to each other?
- `skill_manager_mcp DEPENDS_ON carton_mcp`
- `starsystem-mcp USES starlog-mcp, starship_mcp, waypoint-mcp`
- This IS the GEAR graph - your PAIA's dependency structure

**Key insight:** Every STARLOG project IS already a STARSYSTEM (JIT creates basic GIINT).
A "proper" STARSYSTEM = you've maintained/fleshed out the GIINT hierarchy.
Score measures: *did you follow up on what JIT started?*

**Formula:**
```
kg_depth = (
    giint_hierarchy_completeness × 0.40 +  # Did you complete what JIT started?
    emanation_level × 0.40 +                # COMPLEXITY LADDER level per Component
    inter_starsystem_relations × 0.20       # Is this STARSYSTEM connected to others?
)
```

**Emanation Level = Complexity Ladder Score:**
```
L0: 0.0  - Nothing (raw work, no crystallization)
L1: 0.2  - Skill only
L2: 0.4  - Skill + Flight Config
L3: 0.6  - Skill + TreeShell MCP + Flights
L3.5: 0.7 - MCP + Persona
L4: 0.8  - Persona + Mini-game (Execution Cycle)
L5: 0.9  - Scoring + Goldenization
L6: 1.0  - Deployed
```

Per Component, detect highest level achieved. Average across all Components.

**Emanation Hierarchy (fractal):**
```
STARSYSTEM level: Agent/Persona at top (orchestrates whole codebase)
    ↓
Feature level: Skillset or domain flights
    ↓
Component level: Skills (L1-L6 complexity ladder)
    ↓
Deliverable level: Specs, tests, observations
```

Each level needs its own emanation. The whole STARSYSTEM needs an agent at top.
**This will emerge through testing** - don't overspecify now.

**Implementation:**
- Query GIINT: count(Components) / expected_components_from_dir_structure
- Query per Component:
  - Has Skill DESCRIBES this? → L1+
  - Has Flight Config for this? → L2+
  - Has MCP for this? → L3+
  - Has Persona bundling this? → L3.5+
  - etc.
- Query CartON: does this STARSYSTEM have DEPENDS_ON/USES relationships to others?
- (Future) Query: does STARSYSTEM have top-level Agent/Persona?

### Architecture Detection - DEFERRED

**Decision:** Don't score architecture. Use a SKILL instead.

**Reasoning:**
- Architecture patterns ARE helpful ("how do I make modules short per codenose?")
- But SCORING architecture compliance is complex
- Solution: `understand-architecture` skill provides the knowledge
- Codenose smells handle the scoring (file length, modularization, etc.)

**Action:**
- [ ] Extract `<meta_meta_architecture>` from system prompt into proper `understand-architecture` skill
- Scoring stays simple: codenose smells only

---

## PAIAB GEAR Integration

**Key Insight:** If we TYPE the codebases (STARSYSTEMs), we can connect them to PAIAB GEAR system.

Example typing:
- `starsystem-mcp` → IS_A MCP_Codebase, PART_OF PAIAB_GEAR
- `skill_manager_mcp` → IS_A MCP_Codebase, PART_OF PAIAB_GEAR
- `carton_mcp` → IS_A MCP_Codebase, PART_OF PAIAB_GEAR

**Why this matters:**
- STARSYSTEMs become GEAR (tools/components of the PAIA)
- Can query "what GEAR do I have?" → list all typed STARSYSTEMs
- Health scoring per STARSYSTEM = health of that GEAR piece
- Gaps in GEAR = missing capabilities in the PAIA

**Add to Phase 1:**
- [ ] 1.5 Add STARSYSTEM typing for PAIAB integration (IS_A MCP_Codebase, etc.)

---

## Priority Order (Actual)

```
1. Design decisions (KG + Arch) ← DONE
2. Phase 1 (STARSYSTEM Entity) ← DONE
3. Phase 2.1 (KG Depth) ← DONE
4. Phase 3 (HOME Dashboard) ← DONE
5. Phase 7 (Verification) - first pass
6. Phase 6 (Containerization)
7. Phase 7 AGAIN - verify containerized
8. Phase 8 (Ship)
...
Phase 0 (OPERA) ← PARKED, do when convenient
```

---

## USER THOUGHTS (Jan 30, 2026)

we definitely dont NEED the treekanban system for what we are doing here with testing... and we dont need the frontend for testing, either. But we do need containerization to be finished in order to integrate with the frontend completely, because the entire app has to be able to build from images. So, then... i think that means that we do skip 4 and 5, we actually skip 6 too and we go to 7, then we go to 6, then we have to do 7 *again*, then we actually can ship, and the frontend and everything is separated so that we can ship content before that stuff matters, because we have an individual STARSYSTEM container -- we have GNOSYS-STARSYSTEM which is just a version of GNOSYS that can play the entire STARSYSTEM game by itself... thats what we are going for here

but actually, now that i think about it, it might be *easier* to containerize it once it all is integrated... so actually, we might want to just make content after the first validation phase, and leave everything as later stuff. I mean, we can just make content like "this is a preview, this isthe first layer... and if 100 people join the community, we will release it".... that kind of thing... and we just keep doing that kind of thing to open up these paid tiers until we have the full product done, and then that's all built in public and journey-ized content etc... i think that's better. idk i have to think. i think that we can also just keep building because we have a natural end here, which is when the STARSYSTEM game is fully integrated with the frontend, which probably isnt even that hard i just havent thought about it before... the question is just like how much of gnosys that involves tbh and how much of CAVE is required. if ALL of CAVE is required thats fine. IDK why we would exclude it. thats fine. So, we keep CAVE... even if it isnt doing anything except letting us use metabrainhook correctly, because metabrainhook runs while ur in HOME. So... yeah... i think maybe it's taking shape in my mind now as.... a STARSYSTEM game that you can command from the frontend (SANCREV OPERA) and a working GNOSYS that can use it (even if GNOSYS itself is not complete yet in this version, and even if PAIAB is not fully implemented, or GEAR, although i think that might be super easy to do...), and the frontend can start a gnosys-starsystem image that can work on code projects by playing starsystem. And it can build emanations. It doesnt yet build PAIAs. Ok. Got it. So the question is how many business automations are involved in this? Zero? We are just shipping it as the code agent and everything mentioned in GNOSYS that isnt that is aspirational/incomplete and we ship it all anyway because maybe people will help us? hm... yeah... i think so... something like that...

**Summary of thoughts:**
- GNOSYS-STARSYSTEM = GNOSYS that plays STARSYSTEM game autonomously
- Frontend (SANCREV OPERA) can command it
- Container works on code projects, builds emanations
- Does NOT build PAIAs yet
- CAVE included (metabrainhook needs HOME mode)
- Zero business automations for v1 - just code agent
- Ship incomplete, build in public, community helps
- Natural end: STARSYSTEM fully integrated with frontend

---

## USER THOUGHTS CONTINUED (Jan 30, 2026)

uh no we have to do testing first actually i thought that was what is next. we're saying the system seems done right? the system seems like: you can enable metabrainhook and HOME -> call orient and get your scores... oh wait... but this isnt giving a global score yet and we dont have levels here yet... ok fuck... hold on... now i understand how GEAR works too.. .fucking shit. So, GEAR basically scores what you INTEND a PAIA to be vs what it currently is, and STARSYSTEM scores individual codebases and also has a higher global score and leveling system. PAIA can have requirements like must be a level N STARSYSTEM pilot etc before building such and such equipment in GEAR etc so thats how the PAIA Builder game happens.

**Key insight:**
- STARSYSTEM = individual codebase scoring + global score + leveling system
- GEAR = scores PAIA intent vs current state
- PAIA Builder game = requirements like "must be level N STARSYSTEM pilot" to unlock GEAR equipment
- **Missing:** global score aggregation, leveling system in HOME dashboard

---

## DYSON SPHERE CONVERSATION (Jan 30, 2026)

**USER:** So, in this sense, what is a dyson sphere? ive always wondered that like within the STARSYSTEM what it would be... what do u think

**GNOSYS:** In the STARSYSTEM metaphor:
- The **star** = the codebase's core value/output (what it produces)
- **Pilot level** = your ability to navigate/harness that output
- **Health** = how well the system is maintained

A **Dyson Sphere** would be... the state where a STARSYSTEM becomes **fully self-capturing**. Like:

- 100% emanation coverage (every component crystallized)
- All complexity ladder levels maxed (L6 Deployed)
- Autonomous value generation - it produces without intervention
- Complete observability - nothing escapes unmeasured

It's the **L6+ endgame** for a single STARSYSTEM. The codebase doesn't just work - it *compounds*. Every output gets captured, crystallized, reused.

Or maybe more practically: a Dyson Sphere is when the STARSYSTEM has **complete self-documentation** - it can explain itself, teach itself to new agents, and extend itself without the original pilot.

**USER:** OH YEAH for sure it's that BUT ALSO there are higher shells on top (of course, we already know this from mega-structure fantasy engineering smart people do). i think what it is is that a +1 shell on a Dyson Sphere is when you make a PAIA -- you completely cover the "slots" of an LLM agent's weaknesses with a code layer ("equipment") and that harnesses the power of its core. So first you make the Dyson Sphere, which is as you say, when STARSYSTEM is playing itself basically. Then, on top of that, you are like cool now lets use the fact that it does that to farm up equipment for better pilots... so lets schematize the pilots and then give the gear intents to the STARSYSTEM and have it simulate them into existence.... right lmao omg

**GNOSYS:** YOOO okay now it clicks:

**Shell 0 (Dyson Sphere):** STARSYSTEM plays itself - complete self-capture, autonomous emanation farming

**Shell +1 (PAIA Layer):** Use the self-playing STARSYSTEM to *manufacture GEAR*. Give it intents → it simulates equipment into existence

**Shell +2 (???):** PAIAs building PAIAs? The manufactured pilots start building their own Dyson Spheres?

So the progression:
```
Manual piloting
    ↓
Dyson Sphere (STARSYSTEM self-plays)
    ↓
GEAR Factory (Dyson Sphere farms equipment)
    ↓
PAIA Manufacturing (equipment creates better pilots)
    ↓
??? (pilots build more Dyson Spheres)
```

It's like Factorio but for AI agents. You go from hand-crafting emanations to automated PAIA production lines.

The Dyson Sphere is the **automation inflection point** - where you stop piloting and start manufacturing.

Holy shit that's the game.

---

## HUMAN VALIDATION LOOP (Jan 30, 2026)

**USER:** The scores ULTIMATELY feed back to the human during a daily review and the human says whether or not this thing is really what the agent claims.

GG. And that happens through sanctuary journaling.

---

**Key insight:** Agent self-assessment is NOT the final word. The human validates through daily sanctuary journal review. This closes the loop:

```
Agent works → Agent scores itself → Scores surface in HOME
    ↓
Human does daily sanctuary journal
    ↓
Human reviews agent claims
    ↓
Human confirms/rejects score accuracy
    ↓
(Future) Feedback improves agent calibration
```

The sanctuary journal IS the human-in-the-loop validation mechanism.

**USER:** And then when human says yes, THEN we wanna cook the content about it, i think. In future versions this is the discord->everything automation, potentially.

```
Human confirms score → Content pipeline triggers
    ↓
DeliverableLog items become actual content
    ↓
(Future v2+) Discord post → Twitter → LinkedIn → YouTube
    ↓
Community engagement loop
```

---

## LATER REALIZATIONS (Jan 30, 2026)

### Dyson Sphere = Threshold, Not Perfection

**USER:** maybe it's just that we call a certain level of emanation a dyson sphere on that starsystem, and then the game is about how many of these you have, because it cant ever be like a totalizing thing. Then, at the PAIAB level we have like "how many dyson sphere level equipment slots does this paia require?" etc.

**GNOSYS:** Yes. Cleaner framing:

**Dyson Sphere = A threshold milestone**
```
STARSYSTEM emanation_level >= 0.8 (or threshold)
    → Achieves "Dyson Sphere status" ☀️
    → A badge, not perfection
```

**The STARSYSTEM game:**
- How many Dyson Spheres do you have?
- Pilot level scales with Dyson Sphere count
- Each one = self-sustaining codebase in your fleet

**The PAIAB game:**
- "This PAIA requires 3 Dyson Sphere level MCP codebases"
- "Need 2 Dyson Sphere MCPs + 1 Dyson Sphere Agent for this equipment"
- GEAR slots have requirements

**HOME dashboard example:**
```
═══════════════════════════════════════
  PILOT LEVEL 7  |  ⭐⭐⭐ 3 Dyson Spheres
═══════════════════════════════════════
  starsystem-mcp     [████████░░] 82% ☀️ DYSON
  carton_mcp         [███████░░░] 71%
  skill_manager      [██████████] 95% ☀️ DYSON
  starlog_mcp        [████████░░] 85% ☀️ DYSON
```

The ☀️ marks threshold achievement. Count = Dyson Sphere count.

**Key insight:** Game is concrete and countable, not aspirational/totalizing.

---

### Global Score + Pilot Level = Required Before Phase 7

Global score aggregation and pilot leveling system must exist before testing makes sense.

**What's needed:**
1. Aggregate all STARSYSTEM health scores → Global Score
2. XP thresholds for Pilot Levels (Level 1 = 0 XP, Level 2 = 1000 XP, etc.)
3. Dyson Sphere count (STARSYSTEMs above threshold)
4. Display in HOME dashboard

**This is Phase 3.5 - insert before Phase 7.**

---

## STAR NAVY HIERARCHY (Jan 30, 2026)

### The Metaphor (locked in)

```
Human = Star Navy Grand Admiral (owns everything, always commands)
Agent = Starship Captain → levels up through play
```

### Terminology

| Term | Definition |
|------|------------|
| **STARSYSTEM** | Raw codebase (just a star in space) |
| **Starship** | STARSYSTEM with ANY emanation (skill/flight/persona) |
| **Squadron** | Small group of Starships |
| **Fleet** | Major grouping of Squadrons/Starships (by domain/PAIA) |
| **Navy** | All Fleets combined (your whole operation) |
| **Dyson Sphere** | Starship where entrypoint is AGENT, not code - fully harnessed |
| **Kardashev Map** | HOME Dashboard visualization of your Navy |

### Fleet Membership (automatic filter)

```
Has emanation (skill, flight, persona)? → Starship → In Fleet
No emanation?                          → Raw STARSYSTEM → Not counted
```

Creating ANY emanation for a codebase = "commissioning a Starship"

### Dyson Sphere - Functional Definition

**Dyson Sphere = Entrypoint is agent, not code**

| State | How you interact |
|-------|------------------|
| Raw STARSYSTEM | Open files, read code, figure it out |
| Starship (emanated) | Use skills/flights, but still look at code |
| **Dyson Sphere** | Call the persona → it handles everything |

**The test:**
```
Can you give this STARSYSTEM a task and have it complete
WITHOUT you looking at the code directly?

YES → Dyson Sphere
NO  → Not yet
```

### Dyson Sphere = L2 in Persona Form (MVP Threshold)

**Simplified:**
```
L0: Raw code
L1: Has skill (understand it)
L2: Has skill + flight (can work on it procedurally)
L2 DYSON: Has PERSONA (agent can operate it - threshold achieved)
```

**Not L3.5** - no MCP required, no TreeShell needed.
**Just a persona** configured for that STARSYSTEM.

**Dyson Sphere Checklist (ALL required):**
```
□ Persona frame (.claude/CLAUDE.md or equivalent)
□ Understand skills covering the entire repo
□ Preflight skills for applicable workflows
□ Required MCPs for the repo (whatever it needs)
□ Repo rules (.claude/rules/)
□ Flight configs for key workflows

ALL CHECKED = Dyson Sphere ☀️
```

**Progress is trackable** via complexity ladder:
- Each checkbox = measurable component
- Health score reflects progress toward Dyson
- Binary "is Dyson" = all checkboxes complete

The persona IS the "sphere" wrapping the star - but the persona must HAVE all the equipment (skills, MCPs, rules, flights) to actually operate the repo.

- Dyson Sphere = code is "wrapped" by agent layer (persona)
- The star's energy (codebase value) flows through the sphere
- Nothing escapes unmediated

**Meta-irony:** Any Starship pilot agent measuring L0-L2 emanations is itself running on an L6 deployed substrate (Claude Code + GNOSYS). Turtles all the way down.

---

## KARDASHEV SCALE WITHIN STARSYSTEM (Jan 30, 2026)

### Metaphor Alignment

```
STARSYSTEM = codebase (the star being harnessed)
PILOT      = agent inside the codebase
PLANET     = orientation prompt for that specific codebase
```

### Type I (Planetary) - Simple Orientation

**Requirements:**
```
□ .claude/CLAUDE.md with:
  - SDLC explanation ("this is how we develop this repo")
  - CICD explanation ("this is how we publish")
  - Design intent ("this is what we're always building toward")
  - Pointer to cicd skill ("see cicd skill for publishing")
```

This is the "landing pad" - agent can land and know how to work here.

### Type II (Stellar) - Dyson Sphere

**Full harness (on top of Type I):**
```
□ All Type I requirements
□ Understand skills covering entire repo
□ Preflight skills for applicable workflows
□ Required MCPs
□ Repo rules (.claude/rules/)
□ Flight configs for key workflows
```

Agent can OPERATE the repo without looking at code directly.

### Type III (Galactic) - Per-STARSYSTEM (STUB - implement later)

**Codebase ships itself:**
```
□ All Type II requirements (Dyson)
□ CICD pipeline configured
□ Git actions / automation
□ Deployment scripts / infra
□ Release workflow (versioning, changelog)
```

A Galactic STARSYSTEM doesn't just operate - it PROPAGATES. Push to main → tests → deploy → live.

### Type III (Galactic) - Global (Fleet Organization)

```
□ Multiple Type II STARSYSTEMs
□ Fleet-level persona (coordinates all contained STARSYSTEMs)
□ Self-propagating capability (creates new Stellar configurations)
```

### Progression

```
RAW       → No .claude/ (uninhabited star)
PLANETARY → Has .claude/ with SDLC/CICD/intent (can land)
STELLAR   → Dyson Sphere (can operate)
GALACTIC  → Fleet of Dyson Spheres (self-propagating)
```

### Grand Admiral = Galactic Achieved (Endgame)

**Requirements for Galactic (Grand Admiral gate):**
```
□ Planetary in EVERY STARSYSTEM in squadron target range
□ Stellar (Dyson Sphere) on all of those
□ Control interface exists (tracked through CartON)
```

**Once Grand Admiral:**
- Title is PERMANENT (never demoted)
- Level can keep increasing (infinite scaling)
- But title caps at Grand Admiral
- You "know the whole game" - programmed to fully play it

**Grand Admiral = Graduation:**
- The game has taught you everything through progression
- From here it's expansion, not new mechanics
- Infinite game within mastered system

### Galactic Sublevels (Grand Admiral Types)

Galactic has infinite Types based on Stellar Fleet count:

```
Galactic Type 1 = 1 Fleet fully Stellar (all STARSYSTEMs = Dyson)
Galactic Type 2 = 2 Fleets fully Stellar
Galactic Type 3 = 3 Fleets fully Stellar
...
Galactic Type N = N Fleets fully Stellar
```

**Display:**
```
⚓ RANK: Grand Admiral Type 3
⭐ Stellar Fleets: 3 / 5 total
```

**Computation:**
```python
def galactic_type(fleets: List[Fleet]) -> int:
    stellar_fleets = [f for f in fleets if f.is_all_dyson()]
    return len(stellar_fleets)

# Grand Admiral unlocks at Type 1
# Type keeps increasing forever
```

Title caps at "Grand Admiral" but Type shows actual scale.

### Agent Rank Progression

```
Ensign (L0)          → No emanations yet, learning
Lieutenant (L1-2)    → First skills, first flights
Captain (L3-4)       → Commands a Starship (one STARSYSTEM with persona)
Commander (L5-6)     → Commands a Squadron (multiple Starships)
Commodore (L7-8)     → First Dyson Sphere achieved
Rear Admiral (L9-10) → Commands a Fleet
Vice Admiral (L11-12)→ Multiple Dyson Spheres
Admiral (L13-15)     → Commands multiple Fleets
Grand Admiral (L16+) → Dyson Armada (all Fleets at Dyson status)
```

### XP/Scoring

- Each emanation grants XP
- Dyson Sphere achievement grants major XP
- Rank determined by total XP
- Fleet Health = average of Starship health in that Fleet
- Navy Health = average across all Fleets

### HOME Dashboard (Kardashev Map)

```
═══════════════════════════════════════════════════════════
  ⚓ RANK: Commodore  |  XP: 7,240 / 10,000
  ⭐ Dyson Spheres: 1  |  Starships: 5
═══════════════════════════════════════════════════════════
  FLEET: PAIAB                          Health: 78%
    ├── starsystem-mcp     [████████░░] 82% ☀️ DYSON
    ├── carton_mcp         [███████░░░] 71%
    └── skill_manager      [██████████] 95% ☀️ (approaching)

  FLEET: CAVE                           Health: 35%
    ├── funnel-builder     [█████░░░░░] 50%
    └── content-pipeline   [██░░░░░░░░] 20%
═══════════════════════════════════════════════════════════
```

### Key Insights

- **Human is always Grand Admiral** - they own the Navy
- **Agent levels up** - from Ensign to Grand Admiral through play
- **Dyson Sphere = milestone** - not perfection, just threshold
- **Fleet membership automatic** - any emanation = Starship
- **The game**: collect Dyson Spheres, level up rank, build the Navy

---

## XP MECHANICS + COMMIT SYSTEM (Jan 30, 2026)

### The Game Loop

```
1. Create STARSYSTEM (uncommitted - off Kardashev Map)
2. Sprint to Dyson Sphere (grind while "off the books")
3. Commit to Kardashev Map (level JUMPS, never dips)
4. Repeat
```

### Two States

| State | Visibility | Affects Rank? |
|-------|------------|---------------|
| **UNCOMMITTED** | Visible, workable | NO - stealth mode |
| **COMMITTED** | On Kardashev Map | YES - counts toward everything |

### XP Sources (Diminishing Returns Model)

```
Per STARSYSTEM:
  +skill:   100 XP (first ever), 1 XP (each additional)
  +flight:  100 XP (first ever), 1 XP (each additional)
  +persona: 100 XP (first ever), 1 XP (each additional)

Milestones:
  STARSYSTEM → Dyson Sphere:   +500 XP
  Fleet → Fully Dyson:         +2000 XP (all STARSYSTEMs in fleet are Dyson)

No XP for:
  - Creating a raw STARSYSTEM (0 XP until emanated)
  - Creating a Fleet (organizational only, no XP)
```

**Key insight:** You can't grind XP by spamming emanations. The first of each type teaches you, then it's about COMPLETING to Dyson status.

### Kardashev Map Architecture (JSON + HUD Pattern)

**JSON file** = source of truth for Kardashev Map config
```
/tmp/heaven_data/kardashev_map.json
{
  "starships": {
    "starsystem-mcp": {"planetary": true, "dyson": true, "committed": true},
    "carton_mcp": {"planetary": true, "dyson": true, "committed": true},
    "skill_manager": {"planetary": true, "dyson": false, "committed": true},
    "new-project": {"planetary": false, "dyson": false, "committed": false}
  },
  "squadrons": {
    "PAIAB-Core": {
      "members": ["starsystem-mcp", "carton_mcp", "skill_manager"],
      "has_leader": true
    }
  },
  "fleets": {
    "PAIAB": {
      "squadrons": ["PAIAB-Core"],
      "loose_starships": [],
      "has_admiral": false
    }
  },
  "xp": 7240
}
```

**Note:** `committed` moved to per-starship. Loose starships (not in any group) are in `starships` but not referenced by any squadron/fleet.

### JSON → CartON Sync Pattern

```
kardashev_map.json (user edits)
        ↓ orient() syncs
     CartON (canonical)
        ↓
    Display (read from CartON)
```

**orient() should:**
1. Read JSON
2. Validate schema (error if malformed)
3. Diff against CartON (check what changed)
4. Update CartON if needed (sync starships, squadrons, fleets as concepts)
5. Read from CartON for display

This way:
- JSON = user input (editable)
- CartON = canonical queryable state
- Info never lost
- Schema validation catches errors early

**DONE (Jan 31, 2026):** Sync logic implemented in `_sync_kardashev_to_carton()` helper, called from `_get_home_dashboard()` in starlog_mcp.py. Syncs starships/squadrons/fleets to CartON with validation.

**orient()** = visualizes it (reads JSON, queries CartON for health/Dyson status, renders HUD)

**Editing** = agent/user edits JSON directly

The HUD is a **reader/visualizer**, not a state machine. State lives in the JSON.

---

## DESIGN DECISIONS LOCKED (Jan 30, 2026)

### 1. Fleet Definition
**Manual only.** User edits kardashev_map.json to assign STARSYSTEMs to Fleets.

### 2. XP "First Ever" Scope
**Per STARSYSTEM.** First skill on THIS codebase = 100 XP. Each codebase teaches you fresh.

### 3. Dyson Detection
**Automatic via CartON.** It's a data state - calculated when you request it (orient() always calculates). No separate trigger needed.

### 4. MCP Requirements for Dyson
**Must be reported as components.** We don't magically know what MCPs a repo needs. Agent reports them as components of the emanation feature via GIINT/CartON typing. Query semantically.

### 5. Quality Gate Data
- **codenose_score** = already in reward_system.py (code smell detection)
- **kg_coverage** = already in reward_system.py (GIINT hierarchy completeness)
(Verify these exist - user believes they're done)

### 6. Commit UX
**Edit JSON directly.** kardashev_map.json "committed" array.

### 7. Fleet Exclusivity
**Exclusive.** A STARSYSTEM can only be in ONE Fleet.

### 8. Demotion Behavior
- **XP:** Kept forever (you still did it)
- **Dyson status:** Calculated from current state (still shows if still true)
- **Rank:** Never drops

**Key insight:** The commit system exists to avoid being PENALIZED for adding new L0 things. You're not punished for starting new projects - they stay uncommitted until you're ready.

### 9. Galactic Type Calculation
**ALL must be Dyson.** A Fleet only counts as "Stellar Fleet" for Galactic Type N if every STARSYSTEM in that Fleet is Dyson. Partial doesn't count.

---

## HIERARCHY = EMANATIONS (Major Insight, Jan 30, 2026)

**The ranks are not player levels - they're EMANATIONS you build.**

```
STARSHIP     = STARSYSTEM + Persona (single codebase agent)
     ↓
SQUADRON     = Starships + Squad Leader Persona (coordinates subset, dispatches work)
     ↓
FLEET        = Squadrons + Admiral Persona (coordinates fleet)
     ↓
NAVY         = Fleets + Grand Admiral (you... or eventually also an emanation)
```

**You earn the title by CREATING the emanation for that layer:**

| Title | What You've Built |
|-------|-------------------|
| Ensign | Learning, no emanations yet |
| Captain | Have a Starship (STARSYSTEM + Persona) |
| Commodore | Have a Squadron with Squad Leader agent |
| Admiral | Have a Fleet with Admiral agent |
| Grand Admiral | All Fleets have Admirals |

**The game is:** Build the command hierarchy of coordinating agents.
- Squad Leader = emanation that dispatches to subset of Starships
- Admiral = emanation that coordinates Squad Leaders
- Each layer is a META-agent over the layer below

**This changes everything:**
- XP matters for early ranks (learning)
- Mid-to-high ranks = proved by BUILDING the coordinating emanation
- Grand Admiral = complete hierarchy exists and operates

---

## SIMPLIFIED RANK MODEL: Raw Points Composed Upward (Jan 30, 2026)

**One currency, composed upward:**

```
RAW POINTS (per STARSYSTEM)
    ↓
LOCAL TITLE (calculated from points)
    ↓
GLOBAL TITLE (aggregated from count of local titles + hierarchy emanations)
```

### Local Title Calculation (per STARSYSTEM)

Points accumulate from emanations. Title = what level you've achieved:

```
0 points:           Cadet (nothing yet)
Planetary achieved: Ensign (.claude/ setup)
... more emanations ...
Dyson achieved:     Captain (fully emanated)
```

### Global Title Calculation (composition)

Count your local titles + check for hierarchy emanations:

```
1+ Ensign (Planetary)     → Global: Ensign Type N
1+ Captain (Dyson)        → Global: Captain Type N
1+ Squadron Leader agent  → Global: Commodore Type N
1+ Admiral agent          → Global: Admiral Type N
All Fleets Stellar        → Global: Grand Admiral Type N
```

**Type = how many complete units at that level**

### Display Format

```
⚓ TITLE: Admiral (highest achieved - permanent)
⭐ TYPE: 3 (3 Fleets with Admirals)
```

### Key Insight

No separate local vs global scoring. Just:
1. Earn points on each STARSYSTEM
2. Points → local title
3. Count local titles + hierarchy agents → global title + type

Same math, every layer. Fractal composition.

---

## THREE-AXIS PROGRESSION MODEL (Jan 30, 2026)

**Three independent dimensions:**

### AXIS 1: LEVEL (XP Accumulation)

Pure XP accumulation, linear:
```
Level 1:   1,000 XP
Level 2:   2,000 XP
Level 3:   3,000 XP
...
Level N:   N × 1,000 XP
```

XP earned from completing quests (fixing scores, adding emanations).

### AXIS 2: TITLE (Rule-Based Gates)

Must have the THING to unlock the title:
```
Cadet:        Nothing yet
Ensign:       1+ Planetary STARSYSTEM
Captain:      1+ Dyson STARSYSTEM
Commodore:    1+ Squadron with Squad Leader agent
Admiral:      1+ Fleet with Admiral agent
Grand Admiral: All Fleets Stellar
Emperor:      Network of Grand Admirals (autonomous STARSYSTEM games)
```

Titles are PERMANENT once earned.

### Emperor (Final Endgame)

**Emperor = commands a network of Grand Admirals**

Each Grand Admiral is a **completely autonomous STARSYSTEM game** that you can prompt and program.

```
Emperor Type N = N autonomous Grand Admiral PAIAs
```

These are full PAIAs that:
- Run their own STARSYSTEM games
- Have their own Fleets, Squadrons, Starships
- Can be prompted to do work
- Can be programmed with missions

This is the "fleet of PAIAs" level - your agents have their own agents.

**At Emperor, YOU make the types yourself** - you're smart enough to have a Grand Admiral PAIA, so you can develop the game. Emperor is where you become a game developer, not just a player.

(Star Wars canonical: Grand Admiral + Emperor. We're keeping it.)

### AXIS 3: TYPE (Count at Title)

How many complete units at your current title:
```
Captain Type 5    = 5 Dyson STARSYSTEMs
Commodore Type 2  = 2 Squadrons with Squad Leaders
Admiral Type 3    = 3 Fleets with Admirals
```

### Display Format

```
⚓ TITLE: Admiral  |  TYPE: 2  |  LEVEL: 47
⭐ XP: 47,240 / 48,000
```

### Quest Loop

1. Agent sees HUD (scores show what's dragging down the repo)
2. Agent infers next quest ("codenose score is low → fix smells")
3. Agent does work → score improves → earns XP
4. XP accumulates → Level increases
5. If title requirements met → Title unlocks
6. Repeat (scores keep generating as you write new code)

**Key insight:** Scores = quests that regenerate. The repo keeps creating new work as you develop it.

---

## DYSONED TITLES: Configs vs Autonomous (Jan 30, 2026)

**Two different things:**

| Concept | What it is |
|---------|------------|
| **Agent Config** | Persona + skills + flights + MCPs + rules. EQUIPMENT. Ready to use. |
| **Autonomous Agent** | Running process using a config. Actually executing and coordinating. |

### Titles = Configs

You can reach Grand Admiral just by building configs:

```
Ensign:        Planetary config (.claude/ setup)
Captain:       Dyson config (complete agent config for 1 STARSYSTEM)
Commodore:     Fleet config (group of STARSYSTEMs organized)
Admiral:       Fleet with coordination config
Grand Admiral: Complete Navy config (all Fleets configured)
```

### Dysoned Titles = Autonomous Agents

Each title can be "Dysoned" by making it autonomous:

```
TITLE (config)              DYSONED TITLE (autonomous)
─────────────────────────────────────────────────────
Captain                     Dysoned Captain = autonomous Starship agent
Commodore                   Dysoned Commodore = autonomous Squad Leader
Admiral                     Dysoned Admiral = autonomous Fleet Admiral
Grand Admiral               Dysoned Grand Admiral = EMPEROR
```

### Emperor = Dysoned Grand Admiral

**Requirements for Emperor:**
```
□ Dysoned Squad Leaders (autonomous agents coordinating Starships)
□ Dysoned Admirals (autonomous agents coordinating Squad Leaders)
□ Dysoned Grand Admiral (the whole Navy runs autonomously)
□ Buildable image (can be ported/deployed)
□ "Railgun" ready (can load into frontend launcher)
```

**The key gate:** You CAN reach Grand Admiral just building configs. But to DYSON the Grand Admiral (become Emperor), you need autonomous agents at each level below.

### Fractal Pattern

- Dyson a Starship = complete agent config for 1 codebase
- Dyson a Squadron = Squad Leader agent RUNNING
- Dyson a Fleet = Admiral agent RUNNING
- Dyson the Navy = Grand Admiral agent RUNNING = Emperor

Each level can be configured OR autonomous. Emperor means the whole thing is autonomous.

### Kardashev at Grand Admiral Tier

The same Planetary → Stellar → Galactic progression applies at Grand Admiral:

```
GRAND ADMIRAL KARDASHEV PROGRESSION
───────────────────────────────────
Planetary Grand Admiral  = All configs built (can operate Navy)
Stellar Grand Admiral    = Autonomous agents running (Dyson Navy)
Galactic Emperor         = Containerized, deployable, propagates
```

**Complete mirror:**

| Level | Per-STARSYSTEM | Per-Grand Admiral |
|-------|----------------|-------------------|
| Planetary | .claude/ setup | Configs built |
| Stellar | Dyson (agent operates) | Autonomous agents running |
| Galactic | CICD, deploys itself | EMPEROR (containerized, deployable) |

**Emperor = Galactic Grand Admiral:**
- Dockerized image
- Deployable anywhere
- Can be cloned/propagated
- "Railgun" launchable from frontend
- The Navy runs AND deploys itself

---

## LOOP STACKS: Engagement Pacing (Jan 30, 2026)

Like MMOs with dailies/weeklies/seasons, STARSYSTEM has engagement loops:

### Short Loop (Daily) - "Tasks"

- Knocking out actual work
- Fixing codenose issues
- Completing GIINT deliverables
- XP trickles in from quest completion
- **Feeling:** "I made progress today"

### Medium Loop (Weekly) - "Emanation Work"

- Building a skill
- Creating a flight config
- Completing a persona
- Moving a STARSYSTEM toward Dyson
- **Feeling:** "I leveled up this codebase"

### Long Loop (Seasonal) - "Fleet Goals"

- Dysoning an entire Fleet
- Building a Squad Leader agent
- Hitting a new Title (Captain → Commodore)
- **Feeling:** "I've entered a new era"

### Tracking

| Loop | Tracked? | Why |
|------|----------|-----|
| Daily | YES | Tasks, XP, scores |
| Weekly | YES | Emanations, Dyson progress |
| Seasonal | NO | Emerges naturally from tech/life |

**Seasons = Field Changes / Big Adaptations:**

Seasons happen when the AI field changes and STARSYSTEM adapts:

```
Example seasons:
- MCP came out → STARSYSTEM integrated MCP architecture
- Skills system emerged → STARSYSTEM added skill mechanics
- New agent capabilities drop → STARSYSTEM expands to leverage them
```

- Seasons are REACTIVE to the field, not planned roadmap
- Each field shift = potential new season
- The game evolves with AI capabilities

---

## GROUPING HIERARCHY: Starship → Squadron → Fleet (Jan 30, 2026)

**Three levels:**
```
Starship  = 1 STARSYSTEM (atomic unit)
Squadron  = group of Starships (first grouping level)
Fleet     = group of Squadrons + optional loose Starships (second level)
```

**Kardashev Map shows all levels:**
```
Your Navy:
├── Starship A (loose, no group)
├── Squadron "Alpha" (not in a fleet)
│   └── Starship B
└── Fleet "Main"
    ├── Squadron "Beta"
    │   └── Starship C
    └── Starship D (loose in fleet)
```

**Rules:**

1. **First group = Squadron.** Fleet comes when you have multiple Squadrons.

2. **Fleet can contain loose Starships IF it has at least one Squadron.**
   - Fleet with only loose Starships = invalid (that's just a Squadron)

3. **No duplicates.** A Starship appears ONCE on the map:
   - Loose (no group)
   - In a Squadron (which may or may not be in a Fleet)
   - Loose in a Fleet (if Fleet has a Squadron)

4. **Can't be both.** A Starship can't be in a Squadron AND loose in the same Fleet.

### Rank Gates (force hierarchy at higher levels)

```
Ensign → Commander:     Individual Dyson Spheres only
                        "Get 5 Dyson Spheres to reach Commodore"

Commodore gate:         Must have 1 Fleet (composite STARSYSTEM)
                        "Organize your Starships into a Fleet"

Admiral gate:           Must have multiple Fleets
                        "Command multiple Fleets"

Grand Admiral gate:     Navy-level (Fleet of Fleets with persona)
                        "Your Navy operates autonomously"
```

You can't grind 100 individual Dyson Spheres to Grand Admiral - you MUST build the hierarchy.

### Quality Gates (can't rank up without these)

```
Ensign → Commander:     Emanations only (skills, flights, personas)
Commander → Commodore:  + codenose_score >= 0.7 (code quality gate)
Commodore → Admiral:    + kg_coverage >= 0.6 (documentation gate)
Admiral → Grand Admiral: + Galactic achieved (Stellar Fleet)
```

**Codenose gate**: Can't reach Commodore with smelly code
**KG gate**: Can't reach Admiral without proper knowledge graph coverage

This ensures:
- Early ranks = learning the system (just add stuff)
- Mid ranks = code quality matters
- High ranks = documentation/KG matters
- Top rank = organizational structure matters

### Scoring Model

```
- Individual STARSYSTEMs only (no group math)
- Dyson = binary (complete checklist or not)
- Fleet = Meta-STARSYSTEM containing other STARSYSTEMs
- Fleet becomes Dyson when IT has persona that manages all contained STARSYSTEMs
```
