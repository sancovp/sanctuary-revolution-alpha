# Journey Integration Spec - Narrative System Connection

## New: JourneyLog

Alongside CogLog, SkillLog, DeliverableLog:

```
🗺️ obstacle::domain::what_blocked 🗺️
🗺️ pathway::domain::approach_taken 🗺️
🗺️ overcome::domain::resolution 🗺️
```

**Pattern:** obstacle → pathway → overcome = one transformation arc

## giint.respond Template

Structured learning format (not raw chat dump):

```markdown
## Session Learning Report

### What Was Attempted
- [goal/intent]

### Obstacles Encountered
- [from JourneyLog obstacle entries]

### Pathways Tried
- [from JourneyLog pathway entries]

### What Was Overcome
- [from JourneyLog overcome entries]

### The Learning (not just what was done)
- [extracted insight]
- [internal flaw revealed]
- [transformation that occurred]
```

## Narrative System Integration

**Input to NarrativeManager:**
- Structured learnings (from giint.respond template)
- JourneyLog events (obstacle→pathway→overcome arcs)
- Session metadata (domain, project, qa_id)

**Analysis performed:**
1. **Internal Hidden Flaws** - what was the real lesson?
2. **Psychotyping** - what character arc is this?
3. **Societal Mirror** - how does internal flaw reflect external wasteland?
4. **Medicine Extraction** - what's the boon for others?

## The Full Loop

```
SESSION work
    ↓ emit JourneyLogs (obstacle/pathway/overcome)
LANDING
    ↓ giint.respond (structured template)
NarrativeManager.create_episode_arc()
    ↓ analyzes for flaws/psychotypes
EpisodeArc created
    ↓ (multiple sessions in mission)
NarrativeManager.create_journey_arc()
    ↓ if proven golden
OperadicFlow (sanctuary journey)
    ↓ can be scheduled
Future SESSIONs
```

## The Medicine Model

```
Internal Flaw (personal)
    ↔ mirrors ↔
Societal Flaw (wasteland)
    ↓ overcome via journey
Boon emerges (medicine)
    ↓ applied
Wasteland → Sanctuary
```

The narrative system doesn't summarize - it **diagnoses the transformation** and extracts reusable medicine.

---

*Session 18 (2026-01-11)*
