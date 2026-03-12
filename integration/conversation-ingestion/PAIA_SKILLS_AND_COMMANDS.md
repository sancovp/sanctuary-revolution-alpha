# PAIA Skills and Slash Commands

## Slash Commands (UX Flows)

Slash commands ARE UX flows - they can only be fully defined once full PAIA flows are known.

### Planned Commands:
- `/paia_init_day` - Initialize DAY mode, coglog priming
- `/paia_init_night` - Initialize NIGHT mode, coglog priming
- `/omnisanc_toggle` - Toggle Omnisanc enforcement on/off
- `/flag_conversation` - Mark current conversation for ingestion (wraps the tool)

---

## Skills

### Phase 1: Core PAIA Pipeline (Ship First)

These power the DAY→NIGHT→Discord→Funnel pipeline.

| Skill | Purpose |
|-------|---------|
| NIGHT_conversation-ingestion | The full ingestion workflow |
| NIGHT_framework-synthesis | Synthesizing canonical frameworks from ingested content |
| NIGHT_discord-publishing | Publishing canonical frameworks to Discord |
| funnel-architecture | Landing page structure (hero → problem → solution → CTA) |

### Phase 2: Flight Config System

Once flight configs are actively used.

| Skill | Purpose |
|-------|---------|
| flight-config-maker | How to make flight configs |
| flight-config-search | How to find/browse flight configs |

### Phase 3: Meta Skills (-maker)

For building/extending PAIA parts autonomously.

| Skill | Purpose |
|-------|---------|
| skill-maker | How to make skills |
| mcp-maker | How to make MCPs |
| slash-command-maker | How to make slash commands |
| hook-maker | How to make Claude Code hooks |
| harness-maker | Composite skill for full harness setup |
| plugin-maker | How to make Claude Code plugins |
| library-maker | How to make libraries (pip packages) |

### Phase 4: Domain Skills

Load when doing specific types of work.

| Skill | Purpose |
|-------|---------|
| harness-engineering | Converting MCPs to agent harnesses using state machines + typed models + rejection signals |
| business-logic-invariants | MAKE vs GET modes, decision trees, atomicity rules |
| vue-patterns | Vue.js component patterns |
| react-patterns | React component patterns |
| styling | CSS architecture (BEM, Tailwind, design systems) |

### Phase 5: Infrastructure

Deployment and CI/CD.

| Skill | Purpose |
|-------|---------|
| github-cicd | Deployment process (metapackage, plugin, or standalone docker+MCP HTTP) |

---

## Skill Details

### flight-config-search

How to use `starship.fly()` to find flight configs:

1. **Browse categories**: `fly(path)` - shows available categories and total config count
2. **Browse category**: `fly(path, category="category_name")` - shows configs in that category
3. **Pagination**: `fly(path, category="x", page=N)` - paginated results
4. **Filter to project**: `fly(path, this_project_only=True)` - only current project's configs
5. **Start a flight**: `starship.fly(flight_config_name="config_name")` - actually start the config

---

## Future: Sanctuary MCP Day/Night Cycles

Logged in CartON as `Sanctuary_Mcp_Day_Night_Cycles`.

Full human/agent day-night cycle tracking with Sanctuary journal is deferred. Initial PAIA uses simple DAY/NIGHT mode (agent-level per conversation) without the complex cycle mapping.

---

## Notes

- Phase 1 skills are the priority - ship these first
- Later phases build on Phase 1 foundation
- Skills are context injection - just .md files with the right info
