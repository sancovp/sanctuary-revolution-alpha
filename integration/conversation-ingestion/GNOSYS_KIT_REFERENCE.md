# GNOSYS_KIT Reference

GNOSYS_KIT is an MCP meta-server providing access to Isaac's Compound Intelligence Ecosystem. The underlying Python library is `strata` (config: `/home/GOD/.config/strata/servers.json`). Use `get_action_details` to learn how to call any specific action.

---

## CARTON (23 actions)
**Use when:**
- Need to remember something across conversations (add_concept)
- Looking up what you know about a topic (get_concept, chroma_query)
- Exploring relationships between concepts (get_concept_network, query_wiki_graph)
- Making observations during work (add_observation_batch with 5 tags)
- Finding gaps in knowledge (list_missing_concepts)
- Creating concept collections for context engineering
- Projecting concepts to external substrates (files, discord, etc.)
- Renaming/evolving concepts
- Running experiments with meta-testing

**Omnisanc handling:** Available in HOME mode (get_recent_concepts, chroma_query, get_concept, get_concept_network, query_wiki_graph). PostToolUse hooks sync GIINT projects to CARTON (dual-write pattern) - when GIINT tasks update, corresponding CARTON concepts update automatically.

---

## CONTEXT7 (2 actions)
**Use when:**
- Need up-to-date documentation for any library/package
- First resolve library ID (resolve-library-id), then get docs (get-library-docs)
- Looking up API references or code examples

**Omnisanc handling:** No special handling. Available in all modes.

---

## STARLOG (16 actions)
**Use when:**
- Starting a conversation and need to know what happened in previous sessions
- Working in a directory and wondering if there's existing project context
- Need to preserve discoveries/progress for future conversations
- Want to log bugs, insights, or progress in real-time during work
- Ending a work session and need to summarize what was accomplished
- Creating a new tracked project in a directory
- Need to file a GitHub issue from current debugging work
- Looking for what projects were recently worked on

**Omnisanc handling:** Critical workflow component. `check()` and `orient()` available in HOME mode. `start_starlog()` requires STARPORT phase complete (after fly() and waypoint.start). `end_starlog()` triggers LANDING phase - must then call landing_routine → session_review → giint.respond in sequence. Session scoring happens via PostToolUse hooks.

---

## STARSHIP (14 actions)
**Use when:**
- Need to browse available reusable task templates (flight configurations)
- Want to execute a predefined workflow pattern
- Starting a session and need to transition from "sanctuary mode" to "project mode"
- Creating a new reusable workflow template for future use
- Need to set navigation context for what you're working on
- Reviewing a completed session
- Updating knowledge/learnings from work done

**Omnisanc handling:** Gateway from HOME to JOURNEY mode. `plot_course()` available in HOME mode and sets course_plotted=True. `fly()` required after plot_course to enter STARPORT phase. `launch_routine()` available in HOME. `landing_routine()` required as first step of LANDING phase after end_starlog. `session_review()` required as second LANDING step. Cannot change course while mission is active.

---

## WAYPOINT (5 actions)
**Use when:**
- Following a structured learning journey with defined steps
- Need to track progress through a multi-step learning path
- Want to know where you are in a guided process
- Navigating to the next step in a predefined sequence
- Abandoning or resetting a learning journey

**Omnisanc handling:** Part of STARPORT phase. `start_waypoint_journey()` required after fly() to complete STARPORT. Waypoint step enforcement: step 0 requires check(), step 1 requires orient(), step 2 requires start_starlog(). `get_waypoint_progress()` available in HOME mode.

---

## STARSYSTEM (16 actions)
**Use when:**
- Need to understand the entire compound intelligence system architecture
- Creating a new mission (multi-session goal spanning multiple projects)
- Tracking mission progress across sessions
- Need to see list of active/available missions
- Completing or extracting from a mission
- Creating reusable mission type templates
- Checking fitness scores or querying scores via Neo4j
- Toggling omnisanc mode
- Checking selfplay logs

**Omnisanc handling:** Mission management layer. When mission_active=True, cannot plot new course until mission complete. Mission scoring happens via PostToolUse hooks. `toggle_omnisanc()` controls the kill switch at `/tmp/heaven_data/omnisanc_core/.omnisanc_disabled`.

---

## GIINT-LLM-INTELLIGENCE (28 actions)
**Use when:**
- Need multi-fire intelligence (separate thinking channel from response channel)
- Creating or managing a GIINT project with features/components/deliverables/tasks
- Getting the next task from TreeKanban backlog
- Need to track Q&A sessions for memory
- Setting or checking the current mode (configuration)
- Adding specs to features/components/deliverables/tasks
- Updating task status in the project hierarchy
- Need workshop blueprints or metastack models
- Reporting tool usage

**Omnisanc handling:** `respond()` required as third/final step of LANDING phase after session_review. PostToolUse hooks sync GIINT to CARTON (concepts created for projects) and GIINT to TreeKanban (task status updates). `get_mode_instructions()` available in HOME mode.

---

## CANOPY (5 actions)
**Use when:**
- Need to view the master execution schedule
- Adding a work item to the schedule (AI+Human, AI-Only, or Human-Only)
- Updating status of a scheduled item
- Marking work as complete
- Getting the next item to work on from the schedule

**Omnisanc handling:** PostToolUse hooks feed execution patterns to OPERA for pattern extraction. When Canopy items complete, OPERA analyzes for reusable patterns.

---

## OPERA (13 actions)
**Use when:**
- Need to view verified/golden workflow patterns (OperadicFlows)
- Viewing patterns in quarantine (unverified, awaiting review)
- Promoting a pattern from quarantine to golden library (goldenize)
- Rejecting a quarantined pattern
- Vendoring an OperadicFlow to a GIINT deliverable
- Expanding an OperadicFlow into Canopy schedule items
- Getting details on a specific pattern
- Managing the OPERA schedule
- Viewing Canopy-extracted patterns

**Omnisanc handling:** PostToolUse hooks sync OPERA to TreeKanban - when patterns are vendored to deliverables, TreeKanban tasks auto-created. Receives patterns from Canopy execution tracking.

---

## EMERGENCE-ENGINE (11 actions)
**Use when:**
- Applying 3-pass methodology to a domain (structured thinking process)
- Need to track which pass (1/2/3) and phase (0-6) you're on
- Getting guidance for the next phase in the 3-pass journey
- Starting a new 3-pass journey on a topic
- Abandoning, completing, or resetting a 3-pass journey
- Need the master prompt for 3-pass thinking
- Exploring the methodology interface
- Injecting directory structure into the process

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## TOOT (6 actions)
**Use when:**
- Need to create a persistent reasoning chain (train of thought)
- Updating or explaining an existing train of thought
- Setting intention for doing good work (reference past success patterns)
- Marking that you did a good job (for pattern learning)
- Need to get the TOOT directory path
- Need context continuity across conversations via reasoning chains

**Omnisanc handling:** No special handling. Available in JOURNEY mode. Separate from STARLOG - TOOT is reasoning continuity, STARLOG is project progress.

---

## METASTACK (7 actions)
**Use when:**
- Need to render structured templates (stackable Pydantic models)
- Registering a new metastack template
- Listing available metastack templates
- Getting help on pydantic_stack_core classes (RenderablePiece, MetaStack, FractalStage, etc.)
- Describing what a metastack does
- Rendering a metastack to a file
- Appending content from one metastack to another

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## SEED (14 actions)
**Use when:**
- Need to know the system identity (who_am_i)
- Need to know what the system does (what_do_i_do)
- Need guidance on how to do something (how_do_i)
- Viewing the HOME mode interface/HUD
- Ingesting Q&A sessions into CartON as concepts
- Working with publishing (webserver, membership site)
- Parsing Q&A JSON files
- Adding content to SEED
- Listing available Q&A files
- Reciting mantras
- Listing recently plotted courses

**Omnisanc handling:** `home()`, `who_am_i()`, `what_do_i_do()`, `how_do_i()` available in HOME mode. `home()` is the primary HOME mode interface/HUD.

---

## FLIGHTSIM (7 actions)
**Use when:**
- Need to list available simulation models
- Getting simulations by category
- Generating a mission brief for subagent delegation
- Adding a new flightsim model
- Getting, updating, or deleting a specific flightsim

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## BRAIN-AGENT (3 actions)
**Use when:**
- Need distributed cognition with separate "brain" configurations
- Creating, reading, updating, or deleting brain configurations
- Querying a brain with a specific persona and mode
- Managing personas or modes for brains
- Need to chunk knowledge from registries, directories, or files into neurons

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## N8N-MCP (41 actions)
**Use when:**
- Need to interact with n8n workflow automation
- Listing, creating, updating, or deleting n8n workflows
- Triggering webhook workflows
- Viewing workflow executions
- Getting workflow structure or details
- Validating workflows or node configurations
- Searching nodes or templates
- Getting node documentation or info
- Working with n8n AI tools
- Diagnosing or autofixing workflows

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## SANCTUARY (4 actions)
**Use when:**
- Assessing sanctuary degree (6 dimensions: engagement, emotion, mechanics, progression, immersion, agency)
- Declaring system state
- Making journal entries
- Viewing sanctuary history

**Omnisanc handling:** No special handling. Available in JOURNEY mode. Used for RL-style postmortem scoring.

---

## CONTEXT-ALIGNMENT (4 actions)
**Use when:**
- Parsing a GitHub repo or local directory into Neo4j knowledge graph
- Getting dependency context for code
- Analyzing dependencies and merging to graph
- Querying the codebase graph

**Omnisanc handling:** No special handling. Available in JOURNEY mode. Different from CARTON - this is code dependency graphs, CARTON is concept knowledge.

---

## MCPIFY (8 actions)
**Use when:**
- Need to learn how to build MCPs (get_latest_mcp_knowledge)
- Need MCP development checklist
- Looking for common MCP mistakes to avoid
- Need MCP architecture patterns
- Need MCP testing guide
- Learning how to nest MCPs
- Building SDK for UI over MCP
- Setting up payments over Cloudflare using MCP

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## LLM2HYPERON (10 actions)
**Use when:**
- Need to execute MeTTa programs in persistent space
- Adding atoms or rules to Hyperon AtomSpace
- Listing atoms or rules in a space
- Loading MeTTa from files
- Getting atom counts
- Working with Hyperon's meta-circular interpreter
- Pattern matching against AtomSpace
- Querying/validating CartON ontology through Hyperon

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## HEAVEN-TREESHELL (1 action)
**Use when:**
- Need tree-based navigation interface for conversation management
- Building/saving/following pathways (recorded action sequences)
- Managing conversations (start, continue, list, load, search)
- Executing chain commands across coordinates
- Analyzing execution patterns (RSI system)
- Crystallizing reusable patterns from execution history

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## HEAVEN-FRAMEWORK-TOOLBOX (5 actions)
**Use when:**
- Need to dynamically invoke any tool in heaven_base.tools (omni_tool)
- Managing registries (key-value storage across the system)
- Creating, reading, updating, deleting registry entries
- Using registry references (registry_key_ref, registry_object_ref, registry_all_ref)
- Working with matryoshka registries
- Network edit operations
- Testing agent configs

**Omnisanc handling:** No special handling. Available in JOURNEY mode.

---

## Omnisanc Workflow Summary

```
HOME MODE (limited tools: Read, Glob, Grep, Bash, plus specific MCP actions)
    ↓ starship.plot_course()
STARPORT PHASE
    ↓ starship.fly() → waypoint.start_waypoint_journey()
SESSION PHASE
    ↓ starlog.check() → starlog.orient() → starlog.start_starlog()
WORKING (full tools available)
    ↓ starlog.end_starlog()
LANDING PHASE (3 required sequential steps)
    ↓ starship.landing_routine() → starship.session_review() → giint.respond()
HOME MODE (cycle complete)
```

**State file:** `/tmp/heaven_data/omnisanc_core/.course_state`
**Kill switch:** `/tmp/heaven_data/omnisanc_core/.omnisanc_disabled` (if file exists, omnisanc disabled)

### How to Determine Current Phase from State File

Read the state file and check these keys:

| Condition | Phase |
|-----------|-------|
| `session_active: false` + `needs_review: false` + `course_plotted: false` | HOME MODE (fresh) |
| `session_active: false` + `needs_review: false` + `course_plotted: true` + `fly_called: false` | HOME MODE (course plotted, ready for fly) |
| `course_plotted: true` + `fly_called: true` + `session_active: false` + `waypoint_step: 0` | STARPORT (need waypoint.start) |
| `session_active: false` + `waypoint_step > 0` + not yet started starlog | SESSION PHASE (pre-work: check → orient → start_starlog) |
| `session_active: true` + `needs_review: false` | WORKING (full tools available) |
| `session_active: false` + `needs_review: true` | LANDING PHASE |

### Landing Phase Sub-steps

When in LANDING (`needs_review: true`), check these to know which step you're on:
- `landing_routine_called: false` → Step 1: call `starship.landing_routine()`
- `landing_routine_called: true` + `session_review_called: false` → Step 2: call `starship.session_review()`
- `session_review_called: true` + `giint_respond_called: false` → Step 3: call `giint.respond()`
- All three true → LANDING complete, returns to HOME MODE

### Mission Blocking

When `mission_active: true`:
- Cannot call `plot_course()` to change direction
- Must complete or extract from current mission first
- `mission_id` shows which mission is active
- Mission spans multiple sessions/conversations
