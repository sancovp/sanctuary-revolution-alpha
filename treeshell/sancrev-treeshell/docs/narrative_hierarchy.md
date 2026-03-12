# Narrative Hierarchy - Sanctuary Journeys

## The Stack

```
ODYSSEY (top level)
├── Stack of EPICs
│
EPIC
├── Stack of HERO'S JOURNEYs
│
HERO'S JOURNEY (HJ)
├── Stack of SCENEs
├── About: solving internal flaw that mirrors societal flaw
├── Produces: BOON (societal medicine)
├── Transforms: wasteland → sanctuary
```

## Mapping to OMNISANC

**OMNISANC Journey** = accumulating journeys in service of a **Sanctuary Journey**

But not every step is part of the sanctuary journey.

**Sanctuary Journey** = the GOLDEN journey = the **Operadic Flow**

```
omnisanc SESSION (one HJ instance)
    ↓ accumulates into
omnisanc MISSION (multiple HJs = one EPIC?)
    ↓ accumulates into
SANCTUARY JOURNEY (golden/operadic = ODYSSEY?)
```

## The Cycle

1. Do omnisanc journeys → accumulate experience
2. Pattern emerges → goes to OPERA quarantine
3. Pattern validated → CRYSTAL
4. Pattern battle-tested → GOLDEN (operadic)
5. **Operadic flow IS the sanctuary journey**
6. Can now be scheduled, repeated, taught

## Key Insight

The sanctuary journey is BY DEFINITION the golden journey.
- Not every journey becomes golden
- Only patterns that prove themselves
- The operadic flow is the crystallized wisdom

## SOURCE MODULE FOUND

**Location:** `/home/GOD/core/computer_use_demo/codebase_analyzer_system/narrative_system.py`

**Models:**
```python
class NarrativeLevel(str, Enum):
    EPISODE = "episode"   # Single work unit
    JOURNEY = "journey"   # Component milestone (stack of episodes)
    EPIC = "epic"         # Module milestone (stack of journeys)
    PROJECT = "project"   # Top level

class EpisodeArc(BaseModel):
    episode_id, title, summary
    histories: List[str]        # Source history IDs
    sections: Dict[str, str]    # Narrative sections
    dialogs: List[Dialog]       # Extracted dialogs
    concepts: List[str]
    outcome: NarrativeOutcome

class JourneyArc(BaseModel):
    journey_id, title, component_name
    episodes: List[str]         # Episode IDs
    summary, key_learnings, concepts, outcome

class EpicArc(BaseModel):
    epic_id, title, module_name
    journeys: List[str]         # Journey IDs
    summary, key_learnings, concepts, outcome
```

**NarrativeManager:** Orchestrates creation at all levels
- `create_episode_arc()` - from histories
- `create_journey_arc()` - from episodes
- `create_epic_arc()` - from journeys
- Uses LLM agents for narrative generation
- Stores to registries: `narrative_episodes_{project}`, etc.

**Integration Point:** This is what should connect to SANCREV
- omnisanc SESSIONs → EpisodeArcs
- omnisanc MISSIONs → JourneyArcs
- Sanctuary Journeys (golden operadic flows) → EpicArcs

---

*Session 18 (2026-01-11)*
