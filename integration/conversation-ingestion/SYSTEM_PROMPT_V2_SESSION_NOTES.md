# System Prompt V2 - Final Status & Roadmap

## Current Status: SYSTEM PROMPT COMPLETE

The system prompt at `/tmp/conversation_ingestion_mcp_v2/SYSTEM_PROMPT_V2_DRAFT.md` is complete (838 lines).

### What's In It
- `<COMPOUND_INTELLIGENCE_SYSTEM_PROMPT>` wrapper
- `<FRAME>` with Architecture Preface + Persona Preface (configurable placeholders)
- `<PAIA>` with all operational content:
  - Persona (GNO.SYS identity)
  - Definitions (environment, phases, strata)
  - Rules (hard constraints)
  - Meta Architecture (target vision, gestalt model, MCP list)
  - Architecture (Omnisanc workflow, STARLOG, DAY/NIGHT, CartON, flight configs)
  - Warnings (edge cases, gotchas)
  - Reinforcement (key points)
  - WorkingWithIsaacOnTWI (conversation ingestion workflow)
  - Omnisanc Logic (Prolog-style spec)
  - Code Architecture (Isaac's canonical pattern)
  - Skills (list of skills to create)

### Configurable Placeholders
User replaces these in the system prompt:
- `{{USER_NAME}}`
- `{{CAVE_PROJECT_NAME}}`
- `{{USER_MISSION}}`
- `{{STRATA_LIST}}`
- `{{DISCORD_SERVER_NAME}}`
- `{{FUNNEL_GOAL}}`

No configurator needed - just document in README.

---

## Complete Roadmap

### Phase 1: System Prompt ✅ DONE
- Structure complete
- All sections written
- Placeholders documented

### Phase 2: Skills (NEXT)
Build Claude Code skills:

**Meta Skills (-maker)**:
- skill-maker
- mcp-maker
- slash-command-maker
- flight-config-maker
- hook-maker
- harness-maker (composite)
- plugin-maker
- library-maker

**PAIA System Skills**:
- NIGHT_discord-publishing
- NIGHT_framework-synthesis
- NIGHT_conversation-ingestion
- flight-config-search

**Infrastructure Skills**:
- github-cicd

### Phase 3: Slash Commands
- `/paia_init_day` - DAY mode init, coglog priming
- `/paia_init_night` - NIGHT mode init, coglog priming
- `/omnisanc_toggle` - toggle enforcement on/off
- `/flag_conversation` - mark conversation for ingestion

### Phase 4: Test
- Put system prompt in CLAUDE.md
- Test full DAY/NIGHT cycle
- Test skills trigger correctly
- Test slash commands work
- Iterate based on real usage

### Phase 5: GitHub
- Update/release carton_mcp
- Update/release starship_mcp
- Update/release starlog_mcp
- Update/release other ecosystem repos
- Tag versions, update READMEs

### Phase 6: Discord
- Set up TWI Discord structure (strata categories + subcategories)
- Create overview/journeys/frameworks channels per category
- Set up automations for broadcasting
- Start using it for real canonical framework publishing

### Phase 7: Blogs/Socials
- Set up broadcast projections
- Twitter automation from Discord
- YouTube content pipeline
- Blog setup
- Connect everything to the funnel

---

## Key Files

| File | Purpose |
|------|---------|
| `/tmp/conversation_ingestion_mcp_v2/SYSTEM_PROMPT_V2_DRAFT.md` | The complete system prompt |
| `/tmp/conversation_ingestion_mcp_v2/PAIA_SKILLS_AND_COMMANDS.md` | Skills and slash commands spec |
| `/tmp/conversation_ingestion_mcp_v2/omnisanc_todo.md` | Future Omnisanc enhancements |
| `/home/GOD/carton_mcp/` | CartON MCP (personal domain enum updated) |

---

## Key Decisions Made

### Personal Domain Enum (Simplified)
Changed from 7 arbitrary domains to 5 strata-aligned:
- `paiab` - building AI/agents
- `sanctum` - philosophy/life architecture
- `cave` - business/funnels
- `misc` - doesn't fit a strata yet
- `personal` - non-work life

### No Configurator Needed
Just document the placeholders in README. User finds and replaces.

### Sanctuary Journal Deferred
Logged to CartON as `Sanctuary_Mcp_Day_Night_Cycles` for future. Initial PAIA uses simple DAY/NIGHT mode without complex human/agent cycle mapping.

### Flight Configs Explain Themselves
No need to over-document in system prompt. They create step-by-step state machines when activated. One flight active at a time.

---

## Core Insights

**Observations are retrieval seeds**: The way you observe NOW determines what you can find LATER.

**Personal domains are temporal vectors**: Not "what is this about?" but "where is this going?"

**Discord is canonical source**: Only frameworks + journey metadata. Everything else is broadcast projection.

**Subcategories = bonuses**: Each adds value to the mega-offer of joining a strata community.

**DAY creates, NIGHT extracts**: DAY work (coding, explaining, building) becomes framework material during NIGHT ingestion.
