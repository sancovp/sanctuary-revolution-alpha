# Day/Night Cycle - Temporal Game Loop

## The Two Modes

The system operates differently based on user presence.

---

## DAY MODE (User Present)

**Characteristics:**
- Interactive conversations
- User provides steering
- Dialogic - back and forth

**Activities:**
- **Work (SESSION)** - Actual development, building, creating
- **Imagining** - Brain synthesis WITH user present
- **Learning** - Reviewing arcs with user
- **Configuring** - Setting up HUDs, rules together

**How it flows:**
```
User arrives
    → HOME displays state
    → User decides: work or imagine?
    → If work: plot_course → SESSION → JourneyLog → LANDING
    → If imagine: brain queries → discussion → crystallize insights
    → Repeat until user leaves
```

---

## NIGHT MODE (User Absent)

**Characteristics:**
- Autonomous operation
- Scheduled/harnessed flights
- Monologic - agent runs solo

**Activities:**

### Maintenance Work
- **Ingestion** - Process day's conversations → tag into KG
- **Ontology** - Bring "soup" (unstructured) into structured ontology
- **Story Review** - Analyze EpisodeArcs, JourneyArcs for patterns

### CAVE Work (Business/Funnel)
- **Discord** - Review, write posts
- **Social Media** - Generate content from DeliverableLogs
- **Funnel Work** - Business development tasks

### Dreaming
- **Brain synthesis WITHOUT user**
- Agent explores its own questions
- Results surface as "dream insights" next day
- Not directed by user - autonomous exploration

**How it flows:**
```
User leaves
    → Night mode activates
    → Canopy work queue consulted
    → Scheduled flights run:
        → Ingestion flight
        → Ontology grooming flight
        → Content generation flight
        → Cave/funnel flights
    → Dreaming (autonomous brain queries)
    → Results logged for morning
User returns
    → Day mode resumes
    → Dream insights available
```

---

## The Full 24-Hour Cycle

```
MORNING
├── User arrives
├── HOME shows:
│   ├── Night work completed
│   ├── Dream insights surfaced
│   └── New items in queue
└── Day begins

DAY
├── Interactive sessions
├── Work (SESSION → LANDING)
├── Imagining (WITH user)
└── Learning/Configuring

EVENING
├── User leaves
├── Night mode activates
└── Scheduled work begins

NIGHT
├── Ingestion flights
├── Ontology grooming
├── Content generation
├── Cave work
├── Dreaming (autonomous)
└── Results logged

→ MORNING (cycle repeats)
```

---

## Imagining vs Dreaming

| Aspect | Imagining (Day) | Dreaming (Night) |
|--------|-----------------|------------------|
| User | Present | Absent |
| Steering | User-directed | Self-directed |
| Output | Immediate discussion | Logged for morning |
| Nature | Dialogic | Monologic |
| Purpose | Solve current problems | Autonomous exploration |

**Dreaming is important because:**
- Agent develops its own questions
- Patterns emerge user didn't ask about
- Serendipitous connections surface
- Agent builds its own understanding

---

## Night Flight Categories

### 1. Ingestion Flights
- Process conversation transcripts
- Tag into CartON knowledge graph
- Link to relevant concepts

### 2. Ontology Flights
- Review "soup" nodes (unstructured)
- Promote to proper ontology entries
- Build relationships
- Clean up duplicates

### 3. Content Flights
- Process DeliverableLogs
- Generate social posts
- Queue for review

### 4. Cave Flights
- Funnel work
- Business development
- Monetization tasks

### 5. Dream Flights
- Autonomous brain queries
- Pattern exploration
- Creative synthesis

---

## Implementation Notes

**Night mode trigger:**
- User absence detection (no input for X time)
- Or explicit "goodnight" signal
- Or scheduled time

**Flight scheduling:**
- Canopy manages work queue
- OPERA provides golden flows
- Waypoint executes steps

**Dream logging:**
- Dreams logged to special registry
- Morning HUD shows dream insights
- User can explore or dismiss

---

## Key Insight

**Day = Dialogue, Night = Monologue**

The system is never idle. When user is present, it's interactive. When user is absent, it's autonomous. Both modes produce value:
- Day produces: completed work, resolved problems
- Night produces: organized knowledge, generated content, dream insights

The compound intelligence works around the clock.

---

*Session 18 (2026-01-11)*
