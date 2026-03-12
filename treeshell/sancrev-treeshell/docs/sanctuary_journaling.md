# Sanctuary Journaling - Daily Rhythm

## The 2x Daily Journal

Journaling happens at day/night transitions:

```
MORNING (Opening)
├── User wakes up
├── journal_entry(entry_type="opening")
│   ├── Standup with treekanban
│   ├── Review night work completed
│   └── Set intentions for day
└── Day mode begins

EVENING (Closing)
├── journal_entry(entry_type="closing")
│   ├── Reflect on day's work
│   ├── Note learnings
│   └── Prepare night work queue
├── User leaves
└── Night mode begins
```

---

## Current Implementation

**MCP:** `sanctuary-system-mcp`

**Location:** `/home/GOD/.pyenv/versions/3.11.6/lib/python3.11/site-packages/sanctuary_system/mcp_server.py`

**Tool:** `journal_entry()`
```python
journal_entry(
    entry_text: str,
    entry_type: Literal["opening", "closing"],
    engagement: int,      # 1-10
    emotion: int,         # 1-10
    mechanics: int,       # 1-10
    progression: int,     # 1-10
    immersion: int,       # 1-10
    agency: int,          # 1-10
    user_explicitly_authorized: bool = False,
    entry_file_path: Optional[str] = None
)
```

**6 Dimensions (Sanctuary Score):**
- Engagement - How engaged/present
- Emotion - Emotional quality
- Mechanics - Technical execution
- Progression - Forward movement
- Immersion - Depth of focus/flow
- Agency - Sense of control/autonomy

**Output:**
- Creates Carton observation (if SANCTUARY_CARTON_ENABLED=true)
- Writes marker file to `/tmp/heaven_data/sanctuary/journals/`
- Classification: "Sanctuary" (>=0.75) or "Wasteland" (<0.75)

---

## Integration Points

**With Day/Night Cycle:**
- Opening journal triggers day mode
- Closing journal triggers night mode

**With Treekanban:**
- Morning standup reviews kanban
- What's in progress? What's blocked?

**With Carton:**
- Journal entries become knowledge graph concepts
- Sanctuary degrees tracked over time
- Historical pattern analysis

**With Hooks:**
- `sanctuary_journal_hook.py` reminds if journal missed
- Config at `/tmp/heaven_data/sanctuary/journal_config.json`

---

## AUDIT NEEDED

**Issue:** System was designed to be "arbitrary string" but became complex 6-dimension scoring.

**Problems:**
1. 6 dimensions may be overkill for daily journaling
2. Scoring friction could reduce compliance
3. Mapping to paiab/sanctum libraries incomplete

**Potential Simplification:**
```python
# Original vision - arbitrary string
journal_entry(
    entry_text: str,
    entry_type: Literal["opening", "closing"]
)

# Current - complex scoring
journal_entry(
    entry_text: str,
    entry_type: ...,
    engagement: int,
    emotion: int,
    mechanics: int,
    progression: int,
    immersion: int,
    agency: int
)
```

**Options:**
1. Make dimensions optional with defaults
2. Derive scores from entry_text via LLM
3. Simplify to single "sanctuary_degree" estimate
4. Keep complex but provide presets

**Needs:**
- Audit of sanctuary-system lib
- Mapping to paiab library (PAIA progression)
- Mapping to sanctum library (life architecture)
- Improved scoring model

---

## Morning Standup Flow

```
1. journal_entry(entry_type="opening")
2. treekanban review:
   - What's in progress?
   - What blocked?
   - What completed overnight?
3. Review dream insights (from night mode)
4. Set day's focus
5. Begin day mode
```

## Evening Wind-down Flow

```
1. Review day's work
2. journal_entry(entry_type="closing")
3. Queue night work:
   - Ingestion tasks
   - Content generation
   - Cave work
4. Trigger night mode
```

---

## Config File

Location: `/tmp/heaven_data/sanctuary/journal_config.json`

Controls:
- Morning reminder time
- Evening reminder time
- Hook behavior

---

*Session 18 (2026-01-11)*

**TODO:**
- [ ] Audit sanctuary-system lib complexity
- [ ] Map to paiab library
- [ ] Map to sanctum library
- [ ] Simplify scoring or make optional
