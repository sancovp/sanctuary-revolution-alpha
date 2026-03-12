# STARLOG Improvements Needed

## 1. Rules Brain Directory Flexibility

**Current State:**
- `rules_brain_integration.py` has `create_rules_brain(project_path)`
- Hardcoded to look for starlog-specific rules
- Auto-creates brain when rules added to starlog project

**Problem:**
- Rules should be in `.claude/rules/` (Claude Code native location)
- Not locked to starlog's internal rules location
- Need to point brain-agent to ANY rules directory

**Files to Modify:**
- `/home/GOD/.pyenv/versions/3.11.6/lib/python3.11/site-packages/starlog_mcp/rules_brain_integration.py`
- `/home/GOD/.pyenv/versions/3.11.6/lib/python3.11/site-packages/starlog_mcp/starlog.py` (line 195: `_auto_create_rules_brain`)

**Required Changes:**
```python
# Current signature
def create_rules_brain(self, project_path: str) -> str:

# New signature
def create_rules_brain(
    self,
    project_path: str,
    rules_dir: Optional[str] = None
) -> str:
    """
    Create a brain-agent brain from rules.

    Args:
        project_path: Project for brain naming
        rules_dir: Directory containing rules. Defaults to:
                   1. {project_path}/.claude/rules/ if exists
                   2. ~/.claude/rules/ (global)
    """
    if rules_dir is None:
        # Check project-local first
        project_rules = Path(project_path) / ".claude" / "rules"
        if project_rules.exists():
            rules_dir = str(project_rules)
        else:
            # Fall back to global
            rules_dir = str(Path.home() / ".claude" / "rules")

    # ... rest of logic using rules_dir
```

**Separation of Concerns:**
```
~/.claude/rules/              → Global Claude Code rules
{project}/.claude/rules/      → Project-scoped rules
starlog project rules         → Should migrate to .claude/rules/project/
brain-agent                   → Just cognizes whatever dir you point it at
```

---

## 2. Global Projects View

**Current State:**
- `starlog.list_most_recent_projects()` exists
- Reads from `starlog_recent_projects` registry
- Returns paginated list of projects

**Problem:**
- Not automatically displayed in HOME mode
- No HUD renders this
- Agent doesn't know to use it

**Solution:**
- HOME HUD should call `list_most_recent_projects()` automatically
- Display zone domains alongside projects
- Show status (active, dormant, never_initialized)

---

## 3. Brain-Agent for Global Synthesis

**Current State:**
- `brain-agent` MCP exists at `/home/GOD/brain-agent/`
- Can create brains with `neuron_source_type='directory'`
- `query_brain()` synthesizes across all neurons

**Opportunity:**
- Create a "global_projects" brain pointing to `/tmp/heaven_data/starlog_projects/`
- Query: "What are all active projects, their domains, and status?"
- Brain synthesizes combinatorial view across ALL projects

**Implementation:**
```python
manage_brain(
    operation="add",
    brain_id="global_projects",
    name="Global Projects Brain",
    neuron_source_type="directory",
    neuron_source="/tmp/heaven_data/starlog_projects/"
)

# Then query
query_brain(
    brain="global_projects",
    query="List all projects with their domains, last activity, and current status"
)
```

---

*Session 18 (2026-01-11)*
