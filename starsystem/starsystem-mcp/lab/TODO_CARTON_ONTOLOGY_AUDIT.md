# CartON Ontology Audit - CRITICAL

## Problem

When adding concepts to CartON, we only add immediate relationships. We do NOT:
1. Ensure parent entities exist before creating PART_OF relationships
2. Ensure type entities exist (IS_A targets)
3. Use consistent naming conventions (`.title()` for path slugs)

This breaks graph traversal and scoring queries.

---

## Entry Point Audit

### 1. llm_intelligence/carton_sync.py ✅ DONE
**Location**: `/tmp/llm_intelligence_mcp/llm_intelligence_package/llm_intelligence/carton_sync.py`

**Fixed 2026-02-03:**
- All sync functions now build FULL ontology subgraph
- `sync_project_to_carton` walks entire tree (Project → Features → Components → Deliverables → Tasks)
- Bidirectional relationships: PART_OF (child→parent) AND HAS_* (parent→child)
- All concepts submitted as ONE observation batch
- Individual sync functions also build their full subgraphs

| Function | Status |
|----------|--------|
| `sync_project_to_carton` | ✅ Full subgraph |
| `sync_feature_to_carton` | ✅ Full subgraph |
| `sync_component_to_carton` | ✅ Full subgraph |
| `sync_deliverable_to_carton` | ✅ Full subgraph |
| `sync_task_to_carton` | ✅ Leaf node |
| `update_task_in_carton` | ✅ Updated |

**Priority: HIGH** - This is GIINT emanation scoring - **COMPLETE**

---

### 2. starlog_mcp/starlog_mcp.py - Kardashev Sync
**Location**: `/home/GOD/starlog_mcp/starlog_mcp/starlog_mcp.py` (L190-358)

| Function | Issues |
|----------|--------|
| `_sync_kardashev_to_carton` | References `Kardashev_Map`, `Navy_Starship`, `Navy_Squadron`, `Navy_Fleet`, `Kardashev_{level}` without ensuring they exist |

**Missing Root Concepts:**
- `Kardashev_Map IS_A Carton_Collection` (or appropriate type)
- `Navy_Starship IS_A Starship_Type`
- `Navy_Squadron IS_A Squadron_Type`
- `Navy_Fleet IS_A Fleet_Type`
- `Kardashev_Unterraformed`, `Kardashev_Planetary`, `Kardashev_Stellar`, `Kardashev_Galactic` IS_A Kardashev_Level

**Priority: MEDIUM** - Used for HOME dashboard

---

### 3. starlog_mcp/starlog.py - Session Mirroring
**Location**: `/home/GOD/starlog_mcp/starlog_mcp/starlog.py` (L59-146)

Need to audit `mirror_to_carton()` function for same pattern.

**Priority: MEDIUM**

---

### 4. skill_manager/core.py - Skill Sync
**Location**: `/home/GOD/skill_manager_mcp/src/skill_manager/core.py` (~L209)

Fixed in previous session:
- Added `.title()` for case consistency
- Added PART_OF Starsystem relationship
- Added DESCRIBES Component relationship

**STILL NEEDS:**
- Ensure Starsystem exists with IS_A Starsystem before PART_OF
- Ensure Component exists if describes_component is set

**Priority: HIGH** - This affects complexity scoring

---

## The Fix Pattern

Every `add_concept` call must:

```python
def _ensure_parent_graph(starsystem_path: str, component_path: Optional[str] = None):
    """Ensure all parent entities exist before adding child."""

    # 1. Ensure Starsystem exists
    path_slug = starsystem_path.strip("/").replace("/", "_").replace("-", "_").title()
    starsystem_name = f"Starsystem_{path_slug}"

    _ensure_concept_exists(
        name=starsystem_name,
        relationships=[{"relationship": "is_a", "related": ["Starsystem"]}]
    )

    # 2. If component path, ensure GIINT hierarchy exists
    if component_path:
        # Parse: project/feature/component
        parts = component_path.split("/")
        # Ensure each level exists with proper PART_OF...

def _ensure_concept_exists(name: str, relationships: list):
    """Query CartON, create if not exists."""
    query = f"MATCH (c:Wiki {{n: '{name}'}}) RETURN c.n"
    result = query_wiki_graph(query)
    if not result.get("data"):
        add_concept_tool_func(name, "Auto-created parent entity", relationships, hide_youknow=True)
```

---

## Execution Order

1. **Fix llm_intelligence/carton_sync.py** - Add `.title()` to path_slug (line 123)
2. **Create root type concepts** - One-time setup for Starsystem, GIINT types, Kardashev types
3. **Add _ensure_parent_graph helper** - Reusable across all entry points
4. **Wire helper into each sync function** - Call before add_concept

---

## Session Context

Date: 2026-02-02 → 2026-02-03
Found while testing skill→starsystem tagging for complexity scoring.

Key insight: The skill was added but emanation stayed 0 because:
1. Starsystem didn't have IS_A Starsystem
2. GIINT hierarchy wasn't connected
3. Scoring queries couldn't traverse the graph
