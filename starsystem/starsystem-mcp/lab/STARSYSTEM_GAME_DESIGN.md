# STARSYSTEM Game Design (Jan 30-31, 2026)

Extracted from SHIP_PATH.md - the game mechanics and design decisions.

---

## USER THOUGHTS (Jan 30, 2026)

**Summary of thoughts:**
- GNOSYS-STARSYSTEM = GNOSYS that plays STARSYSTEM game autonomously
- Frontend (SANCREV OPERA) can command it
- Container works on code projects, builds emanations
- Does NOT build PAIAs yet
- CAVE included (metabrainhook needs HOME mode)
- Zero business automations for v1 - just code agent
- Ship incomplete, build in public, community helps
- Natural end: STARSYSTEM fully integrated with frontend

**Key insight:**
- STARSYSTEM = individual codebase scoring + global score + leveling system
- GEAR = scores PAIA intent vs current state
- PAIA Builder game = requirements like "must be level N STARSYSTEM pilot" to unlock GEAR equipment
- **Missing:** global score aggregation, leveling system in HOME dashboard

---

## DYSON SPHERE CONVERSATION (Jan 30, 2026)

**Dyson Sphere = the state where a STARSYSTEM becomes fully self-capturing:**
- 100% emanation coverage (every component crystallized)
- All complexity ladder levels maxed (L6 Deployed)
- Autonomous value generation - it produces without intervention
- Complete observability - nothing escapes unmeasured

**Shell progression:**
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

The Dyson Sphere is the **automation inflection point** - where you stop piloting and start manufacturing.

---

## HUMAN VALIDATION LOOP (Jan 30, 2026)

Agent self-assessment is NOT the final word. Human validates through daily sanctuary journal:

```
Agent works → Agent scores itself → Scores surface in HOME
    ↓
Human does daily sanctuary journal
    ↓
Human reviews agent claims
    ↓
Human confirms/rejects score accuracy
```

---

## STAR NAVY HIERARCHY (Jan 30, 2026)

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

### Dyson Sphere Checklist (ALL required)
```
□ Persona frame (.claude/CLAUDE.md or equivalent)
□ Understand skills covering the entire repo
□ Preflight skills for applicable workflows
□ Required MCPs for the repo (whatever it needs)
□ Repo rules (.claude/rules/)
□ Flight configs for key workflows

ALL CHECKED = Dyson Sphere ☀️
```

---

## KARDASHEV SCALE WITHIN STARSYSTEM (Jan 30, 2026)

### Progression
```
RAW          → No .claude/ (uninhabited star)
UNTERRAFORMED→ (same as RAW)
PLANETARY    → Has .claude/ with SDLC/CICD/intent (can land)
STELLAR      → Dyson Sphere (can operate) - emanation >= 0.6
GALACTIC     → CICD + deployment + self-propagating
```

### Type I (Planetary) - Simple Orientation
```
□ .claude/CLAUDE.md with:
  - SDLC explanation
  - CICD explanation
  - Design intent
```

### Type II (Stellar) - Dyson Sphere
```
□ All Type I requirements
□ Understand skills covering entire repo
□ Preflight skills for applicable workflows
□ Required MCPs
□ Repo rules (.claude/rules/)
□ Flight configs for key workflows
```

### Type III (Galactic) - Self-Deploying
```
□ All Type II requirements (Dyson)
□ CICD pipeline configured
□ Git actions / automation
□ Deployment scripts / infra
□ Release workflow (versioning, changelog)
```

---

## XP MECHANICS (Jan 30, 2026)

### XP Sources (Diminishing Returns Model)
```
Per STARSYSTEM:
  +skill:   100 XP (first ever), 1 XP (each additional)
  +flight:  100 XP (first ever), 1 XP (each additional)
  +persona: 100 XP (first ever), 1 XP (each additional)

Milestones:
  STARSYSTEM → Dyson Sphere:   +500 XP
  Fleet → Fully Dyson:         +2000 XP
```

### JSON Schema (UPDATED Jan 31)
```json
{
  "starships": {
    "my-project": {"path": "/path/to/starsystem"}
  },
  "squadrons": {
    "my-squadron": {
      "members": ["my-project"],
      "has_leader": false
    }
  },
  "fleets": {
    "my-fleet": {
      "squadrons": ["my-squadron"],
      "loose_starships": [],
      "has_admiral": false
    }
  },
  "xp": 0
}
```

**Note:** Kardashev level (Planetary/Stellar/Galactic) is COMPUTED from actual state, not stored in JSON.

---

## DESIGN DECISIONS LOCKED (Jan 30, 2026)

1. **Fleet Definition**: Manual only - user edits JSON
2. **XP Scope**: Per STARSYSTEM (first skill = 100 XP each codebase)
3. **Dyson Detection**: Automatic via scoring (emanation >= 0.6)
4. **Quality Gates**: codenose_score, kg_coverage
5. **Commit UX**: Being in the JSON = committed
6. **Fleet Exclusivity**: STARSYSTEM can only be in ONE Fleet
7. **Demotion**: XP kept forever, rank never drops
8. **Galactic Type**: ALL STARSYSTEMs in Fleet must be Dyson

---

## THREE-AXIS PROGRESSION MODEL (Jan 30, 2026)

### AXIS 1: LEVEL (XP Accumulation)
```
Level N = N × 1,000 XP
```

### AXIS 2: TITLE (Rule-Based Gates)
```
Cadet:        Nothing yet
Ensign:       1+ Planetary STARSYSTEM
Captain:      1+ Stellar STARSYSTEM
Commodore:    1+ Squadron with Squad Leader agent
Admiral:      1+ Fleet with Admiral agent
Grand Admiral: All Fleets Stellar
Emperor:      Network of Grand Admirals (autonomous STARSYSTEM games)
```

Titles are PERMANENT once earned.

### AXIS 3: TYPE (Count at Title)
```
Captain Type 5    = 5 Stellar STARSYSTEMs
Commodore Type 2  = 2 Squadrons with Squad Leaders
Admiral Type 3    = 3 Fleets with Admirals
```

### Display Format
```
⚓ TITLE: Admiral  |  TYPE: 2  |  LEVEL: 47
⭐ XP: 47,240 / 48,000
```

---

## HIERARCHY = EMANATIONS (Major Insight)

**The ranks are not player levels - they're EMANATIONS you build.**

```
STARSHIP     = STARSYSTEM + Persona (single codebase agent)
     ↓
SQUADRON     = Starships + Squad Leader Persona
     ↓
FLEET        = Squadrons + Admiral Persona
     ↓
NAVY         = Fleets + Grand Admiral
```

| Title | What You've Built |
|-------|-------------------|
| Ensign | Learning, no emanations yet |
| Captain | Have a Starship (STARSYSTEM + Persona) |
| Commodore | Have a Squadron with Squad Leader agent |
| Admiral | Have a Fleet with Admiral agent |
| Grand Admiral | All Fleets have Admirals |

---

## DYSONED TITLES: Configs vs Autonomous (Jan 30, 2026)

| Concept | What it is |
|---------|------------|
| **Agent Config** | Persona + skills + flights + MCPs + rules. EQUIPMENT. Ready to use. |
| **Autonomous Agent** | Running process using a config. Actually executing. |

```
TITLE (config)              DYSONED TITLE (autonomous)
─────────────────────────────────────────────────────
Captain                     Dysoned Captain = autonomous Starship agent
Commodore                   Dysoned Commodore = autonomous Squad Leader
Admiral                     Dysoned Admiral = autonomous Fleet Admiral
Grand Admiral               Dysoned Grand Admiral = EMPEROR
```

**Emperor = Galactic Grand Admiral:**
- Dockerized image
- Deployable anywhere
- Can be cloned/propagated
- The Navy runs AND deploys itself

---

## GROUPING HIERARCHY: Starship → Squadron → Fleet

**Rules:**
1. First group = Squadron. Fleet comes when you have multiple Squadrons.
2. Fleet can contain loose Starships IF it has at least one Squadron.
3. No duplicates - Starship appears ONCE on the map.
4. Can't be in a Squadron AND loose in the same Fleet.

### Quality Gates
```
Ensign → Commander:     Emanations only
Commander → Commodore:  + codenose_score >= 0.7
Commodore → Admiral:    + kg_coverage >= 0.6
Admiral → Grand Admiral: + Galactic achieved
```

---

## IMPLEMENTATION STATUS (Jan 31, 2026)

### ✅ DONE
- JSON → CartON sync (`_sync_kardashev_to_carton()`)
- Computed Kardashev (Planetary/Stellar from actual state)
- STARSYSTEM validation (must be init'd via starlog)
- Basic title/type calculation
- HOME dashboard with hierarchy display
- Empty JSON → full instructions

### ❌ NOT IMPLEMENTED
- XP tracking/awarding system
- Diminishing returns (100 XP first, 1 XP after)
- Milestone XP (+500 Dyson, +2000 Fleet Dyson)
- Galactic detection (CICD check)
- Emperor tier
- Loop stacks (Daily/Weekly/Seasonal)
