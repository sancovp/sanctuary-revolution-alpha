# CANOPY - Master Schedule Orchestration

CANOPY (Master Schedule) orchestrates work distribution between AI and Human in the STARSYSTEM compound intelligence ecosystem.

## Overview

CANOPY manages the master schedule of work items with three collaboration types:

- **AI+Human**: Work together on missions (both required)
- **AI-Only**: AI can complete autonomously
- **Human-Only**: Waiting for human completion

## Installation

```bash
pip install canopy-mcp
```

## MCP Tools

### add_to_schedule()
Add work item to master schedule

```python
add_to_schedule(
    item_type="AI+Human",  # or "AI-Only" or "Human-Only"
    description="Implement OAuth authentication feature",
    priority=8,  # 1-10, higher = more urgent
    mission_type="feature_dev_3session",  # optional
    mission_type_domain="feature_development",  # optional
    variables={"project_path": "/path/to/project", "feature_name": "OAuth"}  # optional
)
```

### get_next_item()
Get next pending item from schedule

```python
get_next_item()  # All types
get_next_item(item_type="AI+Human")  # Filter by type
```

### view_schedule()
View master schedule

```python
view_schedule()  # All items
view_schedule(status_filter="pending")  # Filter by status
```

### mark_complete()
Mark item as completed

```python
mark_complete(item_id="canopy_1_20251012_120000")
```

### update_item_status()
Update item status

```python
update_item_status(item_id="canopy_1_20251012_120000", status="in_progress")
```

## Integration with STARSYSTEM

CANOPY sits at the top of the STARSYSTEM hierarchy:

```
CANOPY (Master Schedule)
  ↓
Mission Types (Templates)
  ↓
Missions (Instances)
  ↓
Sessions (STARLOG)
  ↓
Flight Configs (Work patterns)
```

## Workflow

1. **At HOME**: Review schedule with `view_schedule()`
2. **Select work**: Get next item with `get_next_item()`
3. **For missions**: Use mission_type to create mission instance
4. **Execute**: Follow mission → session → flight config flow
5. **Complete**: Mark done with `mark_complete()`

## Storage

Uses HEAVEN registries (`canopy_master_schedule`) for persistence across sessions.
