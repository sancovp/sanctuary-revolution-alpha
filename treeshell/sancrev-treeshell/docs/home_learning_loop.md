# HOME Learning Loop - The Metabolic Center

## What HOME Actually Is

HOME is not just navigation/planning. HOME is the **metabolic center** where:
- Experience becomes wisdom
- Wisdom becomes rules
- Rules guide future work
- Future work feeds back into the system

---

## The Three Functions of HOME

### 1. LEARN

**Sources:**
- Past EpisodeArcs (individual session narratives)
- Past JourneyArcs (mission-level narratives)
- Project brain synthesis (combinatorial queries)

**Mechanisms:**
- NarrativeManager already produces structured learnings
- Brain-agent synthesizes across all project data
- Patterns emerge from hundreds of parallel contexts

**Query Examples:**
```python
query_brain(
    brain="project_brain",
    query="What obstacles keep recurring?"
)

query_brain(
    brain="project_brain",
    query="What patterns led to successful outcomes?"
)

query_brain(
    brain="project_brain",
    query="What internal flaws mirror what societal problems?"
)
```

### 2. CONFIGURE

**What gets configured:**
- Rules (`.claude/rules/`) - crystallized learnings become guidance
- HUDs - what TreeShell displays in each zone
- Personas - updated based on capability growth
- Skills - new skills from proven patterns

**The Rule Crystallization Pattern:**
```
Learning: "I keep forgetting to check dependencies before editing"
    ↓
Rule: dependency-reading.md
    ↓
Future sessions: Auto-injected guidance
```

### 3. DECIDE

Two paths from HOME:

**DO WORK:**
```
plot_course(project, description, domain)
    → SESSION begins
    → Actual work happens
    → JourneyLogs emitted
    → LANDING
    → giint.respond
    → Back to HOME with new experience
```

**IMAGINE:**
```
query_brain(brain, creative_query)
    → Synthesis across all neurons
    → New ideas emerge
    → Either crystallize as rule/skill
    → Or becomes next SESSION's goal
```

---

## The Compounding Cycle

```
        ┌─────────────────────────────────────────┐
        │                                         │
        v                                         │
     HOME                                         │
   (LEARN)                                        │
      │                                           │
      v                                           │
  Configure                                       │
   (rules)                                        │
      │                                           │
      v                                           │
   DECIDE                                         │
      │                                           │
   ┌──┴──┐                                        │
   │     │                                        │
   v     v                                        │
WORK   IMAGINE                                    │
   │     │                                        │
   │     └──→ (new ideas → rules or goals)        │
   │                                              │
   v                                              │
SESSION                                           │
   │                                              │
   v                                              │
JourneyLog (obstacle→pathway→overcome)            │
   │                                              │
   v                                              │
LANDING                                           │
   │                                              │
   v                                              │
giint.respond → NarrativeManager                  │
   │                                              │
   v                                              │
EpisodeArc created ───────────────────────────────┘
```

---

## Project Brain Setup

Each starlog project should have a brain:

```python
# Create brain for project
manage_brain(
    operation="add",
    brain_id="{project_name}_brain",
    name="{Project Name} Brain",
    neuron_source_type="directory",
    neuron_source="/path/to/starlog/project"
)
```

The brain cognizes:
- All session logs
- All debug diaries
- All generated docs
- All JourneyLog events
- All EpisodeArcs

This enables combinatorial synthesis - asking questions that span ALL project history.

---

## The "Hundreds of LLMs" Model

Each neuron in the brain is processed in parallel:
- Session 1 context → LLM analysis
- Session 2 context → LLM analysis
- Session 3 context → LLM analysis
- ...
- Session N context → LLM analysis
- → All results synthesized → Final insight

This is why the brain can find patterns humans miss - it's doing combinatorial analysis across everything simultaneously.

---

## Integration Points

**From NarrativeManager:**
- EpisodeArcs feed into brain neurons
- JourneyArcs provide milestone markers
- EpicArcs mark major transformations

**To Rules System:**
- Brain insights → crystallized rules
- Rules auto-inject into future sessions
- Sessions produce new data for brain

**To OPERA/Canopy:**
- Proven patterns → golden operadic flows
- Golden flows → schedulable work
- Scheduled work → queued in Canopy

---

## Key Insight

**HOME is where the system THINKS.**

SESSION is where work happens.
LANDING is where extraction happens.
HOME is where **synthesis** happens.

Without the learning loop, the system just does tasks.
With the learning loop, the system **evolves**.

---

*Session 18 (2026-01-11)*
