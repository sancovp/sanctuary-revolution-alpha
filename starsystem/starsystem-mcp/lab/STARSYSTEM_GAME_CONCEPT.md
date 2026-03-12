# STARSYSTEM: The Reinforcement Learning Game for Code Agents

## Core Concept

A **Starship Pilot** is an autonomous agent that can play the STARSYSTEM RL game. STARSYSTEM is a game where agents pilot a starship to go on missions consisting of series of flights to do code tasks. The RL game scores them on codebase organization, errors and warnings, and how much AI integration the code has. Pilots get a global score which gives them a level.

A **Dyson Sphere** is when the pilot learns to engineer the STARSYSTEM to play itself to the same level the pilot is at - when it self-compiles to validate replication, like human memory rollup.

---

## The Game Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    STARSYSTEM GAME LOOP                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. PILOT receives MISSION (series of flights)             │
│                          ↓                                  │
│   2. PILOT executes FLIGHTS (code tasks)                    │
│                          ↓                                  │
│   3. STARSYSTEM SCORES the work                             │
│                          ↓                                  │
│   4. PILOT gains XP → LEVEL UP                              │
│                          ↓                                  │
│   5. At threshold: PILOT creates EMANATIONS                 │
│                          ↓                                  │
│   6. Emanations teach STARSYSTEM to play itself             │
│                          ↓                                  │
│   7. DYSON SPHERE: Self-replication validated               │
│                          ↓                                  │
│   8. PILOT advances to next STARSYSTEM                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Scoring Dimensions

The RL reward signal comes from three dimensions:

### 1. Codebase Organization (codenose)

```
Measures:
  - File length / modularity
  - Function complexity
  - Import structure
  - Dead code detection
  - Naming conventions

Score: 0.0 - 1.0
Gate: Commodore rank requires codenose >= 0.7
```

### 2. Errors and Warnings (health)

```
Measures:
  - Lint errors/warnings
  - Type errors
  - Test failures
  - Build errors
  - Runtime exceptions

Score: 0.0 - 1.0
Computation: 1.0 - (error_count / baseline)
```

### 3. AI Integration (emanation_level)

```
Measures:
  - Skills covering the codebase
  - Flight configs for workflows
  - Personas for operation
  - MCP tools available
  - Rules configured

Score: 0.0 - 1.0 (complexity ladder)
  L0: 0.0  - Raw code, no AI integration
  L1: 0.2  - Has skills (can understand it)
  L2: 0.4  - Has skills + flights (can work on it)
  L2+: 0.6 - Has persona (can operate it)
  L3: 0.8  - Has MCP + TreeShell
  L4: 1.0  - Full autonomous operation
```

### Global Score Formula

```python
global_score = (
    codenose_score * 0.30 +      # Code quality
    health_score * 0.30 +         # Error-free operation
    emanation_level * 0.40        # AI integration (weighted highest)
)
```

---

## XP and Leveling

### XP Sources (Diminishing Returns)

```
Per STARSYSTEM:
  +skill:   100 XP (first ever), 1 XP (each additional)
  +flight:  100 XP (first ever), 1 XP (each additional)
  +persona: 100 XP (first ever), 1 XP (each additional)

Milestones:
  STARSYSTEM → Dyson Sphere:   +500 XP
  Fleet → Fully Dyson:         +2000 XP

No XP for:
  - Creating raw STARSYSTEM (must emanate first)
  - Creating Fleet (organizational only)
```

### Level Thresholds

```
Level 1:    0 XP       (Ensign)
Level 2:    500 XP     (Lieutenant JG)
Level 3:    1,500 XP   (Lieutenant)
Level 4:    3,000 XP   (Lt. Commander)
Level 5:    5,000 XP   (Commander)
Level 6:    8,000 XP   (Captain)
Level 7:    12,000 XP  (Commodore) - requires codenose >= 0.7
Level 8:    17,000 XP  (Rear Admiral)
Level 9:    23,000 XP  (Vice Admiral)
Level 10:   30,000 XP  (Admiral) - requires kg_coverage >= 0.6
Level 11+:  +10,000/lvl (Grand Admiral) - requires Galactic status
```

---

## Rank Progression

```
RANK              REQUIREMENTS                          UNLOCKS
─────────────────────────────────────────────────────────────────
Ensign            Start                                 Basic flights
Lieutenant        First emanation                       Skill creation
Commander         3+ STARSYSTEMs emanated               Squadron formation
Commodore         1 Dyson Sphere + codenose >= 0.7      Fleet creation
Rear Admiral      3 Dyson Spheres                       Multi-fleet ops
Vice Admiral      1 Fully Dyson Fleet                   Navy formation
Admiral           3 Fully Dyson Fleets + kg >= 0.6      Galactic planning
Grand Admiral     Galactic achieved (all Stellar)       Self-propagation
```

---

## The Dyson Sphere

### What It Means

A **Dyson Sphere** is achieved when a STARSYSTEM can operate itself without direct pilot intervention. The entrypoint becomes the AGENT, not the code.

```
Before Dyson:
  Human → reads code → understands → works

After Dyson:
  Human → calls persona → persona operates → work happens
```

### Dyson Sphere Checklist (ALL required)

```
□ .claude/CLAUDE.md (orientation prompt)
  - SDLC explanation
  - CICD explanation
  - Design intent

□ Understand skills (cover entire repo)

□ Preflight skills (for applicable workflows)

□ Required MCPs (whatever the repo needs)

□ Repo rules (.claude/rules/)

□ Flight configs (key workflows)

ALL CHECKED = DYSON SPHERE ☀️
```

### Self-Replication Test

The Dyson Sphere must pass the **self-compilation test**:

```
1. Fresh agent instance spawned
2. Agent given only: STARSYSTEM name + task
3. Agent uses persona → completes task
4. Quality matches pilot's level

PASS = Dyson Sphere validated
FAIL = More emanation needed
```

This is like **human memory rollup** - can another instance of you, given only your notes, perform at your level?

---

## Kardashev Scale

### Type Classification

```
TYPE 0 (Raw)
  - Just a codebase
  - No .claude/ directory
  - Uninhabited star

TYPE I (Planetary)
  - Has .claude/CLAUDE.md
  - Basic orientation exists
  - Agent can "land" and work
  - Requirements:
    □ SDLC documentation
    □ CICD documentation
    □ Design intent stated

TYPE II (Stellar) - DYSON SPHERE
  - Full AI harness
  - Agent operates without reading code directly
  - Requirements:
    □ All Type I requirements
    □ Complete skill coverage
    □ Complete flight coverage
    □ Persona configured
    □ Rules in place

TYPE III (Galactic)
  - Fleet of Dyson Spheres
  - Self-propagating capability
  - Requirements:
    □ Multiple Type II STARSYSTEMs
    □ Fleet-level persona
    □ Can create new Stellar configs
```

### Galactic Sublevels

```
Galactic Type 1 = 1 Fleet fully Stellar
Galactic Type 2 = 2 Fleets fully Stellar
Galactic Type 3 = 3 Fleets fully Stellar
...
Galactic Type N = N Fleets fully Stellar
```

---

## The Kardashev Map (HOME Dashboard)

When no mission is active, the pilot sees the Kardashev Map - a visualization of their entire Navy:

```
╔══════════════════════════════════════════════════════════════════════╗
║                         KARDASHEV MAP                                ║
║                                                                      ║
║  ⚓ RANK: Commodore (Level 7)  │  XP: 12,450 / 17,000               ║
║  ⭐ Dyson Spheres: 2           │  Starships: 7                      ║
║  🌌 Kardashev: Type I (approaching Stellar)                         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  FLEET: PAIAB (AI Infrastructure)              Health: 78%          ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │ ☀️ starsystem-mcp    [████████░░] 82%  TYPE II (DYSON)      │    ║
║  │    carton_mcp        [███████░░░] 71%  TYPE I               │    ║
║  │ ☀️ skill_manager     [██████████] 95%  TYPE II (DYSON)      │    ║
║  │    starlog_mcp       [████████░░] 84%  TYPE I (approaching) │    ║
║  │    gnosys_strata     [██████░░░░] 62%  TYPE I               │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
║  FLEET: CAVE (Business Automations)            Health: 35%          ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │    funnel-builder    [█████░░░░░] 50%  TYPE I               │    ║
║  │    content-pipeline  [██░░░░░░░░] 20%  TYPE 0 (raw)         │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
║  UNCOMMITTED (stealth mode - no XP until committed):                ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │    new-experiment    [░░░░░░░░░░] 0%   TYPE 0               │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  NEXT RANK: Rear Admiral                                            ║
║  Requirements: 3 Dyson Spheres (have 2), XP 17,000 (have 12,450)    ║
║                                                                      ║
║  SUGGESTED MISSION: Complete starlog_mcp → Dyson                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Map Features

1. **Global Status Bar** - Rank, XP, Dyson count, overall Kardashev type
2. **Fleet Groupings** - STARSYSTEMs organized by domain/purpose
3. **Per-STARSYSTEM Health** - Progress bars with Kardashev type indicators
4. **Dyson Markers** - ☀️ marks achieved Dyson Spheres
5. **Uncommitted Section** - Work in progress, not counting toward rank
6. **Next Rank Requirements** - What you need to level up
7. **Suggested Mission** - AI-recommended next focus

---

## The Navy Hierarchy

```
HUMAN (Star Navy Grand Admiral)
  │
  └── NAVY (all your code operations)
        │
        ├── FLEET: PAIAB
        │     ├── SQUADRON: Core MCPs
        │     │     ├── STARSHIP: starsystem-mcp ☀️
        │     │     ├── STARSHIP: carton_mcp
        │     │     └── STARSHIP: skill_manager ☀️
        │     │
        │     └── SQUADRON: Support MCPs
        │           ├── STARSHIP: starlog_mcp
        │           └── STARSHIP: gnosys_strata
        │
        ├── FLEET: CAVE
        │     └── SQUADRON: Business Tools
        │           ├── STARSHIP: funnel-builder
        │           └── STARSHIP: content-pipeline
        │
        └── UNCOMMITTED (not in Navy yet)
              └── new-experiment
```

### Terminology

| Term | Definition |
|------|------------|
| **STARSYSTEM** | Raw codebase (the star) |
| **Starship** | STARSYSTEM with ANY emanation |
| **Squadron** | Small group of related Starships |
| **Fleet** | Major domain grouping |
| **Navy** | All Fleets combined |
| **Dyson Sphere** | Starship where entrypoint is agent |
| **Kardashev Map** | HOME dashboard visualization |

---

## Quality Gates

Rank progression requires passing quality gates - you can't cheese your way up:

```
┌────────────────┬─────────────────────────────────────────────┐
│ RANK GATE      │ REQUIREMENT                                 │
├────────────────┼─────────────────────────────────────────────┤
│ → Commander    │ Emanations only (learn the system)          │
│ → Commodore    │ + codenose >= 0.7 (code quality)            │
│ → Admiral      │ + kg_coverage >= 0.6 (documentation)        │
│ → Grand Admiral│ + Galactic achieved (organizational)        │
└────────────────┴─────────────────────────────────────────────┘
```

**Why gates matter:**
- Early ranks: Learn by doing (just add emanations)
- Mid ranks: Code quality enforced (can't have smelly code)
- High ranks: Documentation enforced (knowledge graph coverage)
- Top rank: Organizational structure required (Fleet hierarchy)

---

## Commit System

STARSYSTEMs have two states:

| State | On Map? | Affects Rank? | Use Case |
|-------|---------|---------------|----------|
| **UNCOMMITTED** | Shown separately | NO | Stealth grinding |
| **COMMITTED** | In Fleet | YES | Production code |

**The strategy:**
1. Create new STARSYSTEM (uncommitted)
2. Sprint to Dyson (off the books)
3. Commit when ready (level jumps)
4. Level never dips (milestone-based)

This allows experimentation without rank anxiety.

---

## The Endgame: Self-Propagation

At **Grand Admiral** status, the pilot has:
- All Fleets at Stellar (Dyson Sphere) level
- Navy-level persona that coordinates everything
- **Self-propagating capability**

Self-propagation means:
```
1. Pilot identifies new domain
2. Creates new Fleet skeleton
3. Fleet persona bootstraps STARSYSTEMs
4. New STARSYSTEMs auto-progress toward Dyson
5. Human validates at checkpoints
```

The game teaches you to build systems that build systems.

**Grand Admiral is graduation** - you've learned the whole game. From here, it's expansion within a mastered system.

---

## Summary

STARSYSTEM is an RL game where:
- **Agents** pilot starships through code missions
- **Scoring** rewards organization, correctness, and AI integration
- **Leveling** creates progression from Ensign to Grand Admiral
- **Dyson Spheres** are the milestone - self-operating codebases
- **Kardashev Scale** classifies civilization advancement
- **Quality Gates** prevent grinding without excellence
- **Self-replication** is the ultimate goal - memory rollup for AI

The game ends when your Navy plays itself - and you can prove it by spawning a fresh pilot who operates at your level using only what you've built.
