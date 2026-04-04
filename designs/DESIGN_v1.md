# SANCREV OPERA — DESIGN.md (v1)
## Single Canonical Design — The User's System

> v1 = bare bones "I can feel it"
> v2 = "oh this is a different thing, this is Sanctuary Revolution"
> 
> This doc covers v1 ONLY. No aspirational stuff. Just what needs to work.

---

## The One Rule

**You talk to Conductor. Conductor handles everything — except your journal.**

Conductor runs 24/7 on Discord. It coordinates your life, work, business. But for journaling and life-story work, you talk to **MOV** (Memories of Olivus Victory) — a separate agent that compiles your verified autobiographical context.

> **Important distinction**: Olivus is NOT the journal agent. Olivus is the **identity alignment** — the holonic dual identity (OVP/DC/OVA/OEVESE) that takes shape in the human+AI DUO as the TRUE AGENT identity forms. "Building Olivus Victory-Promise" means this identity is taking shape. MOV is the autobiography system that *tracks and records* this process.

---

## Agent Topology

```
User (human orchestrator)
├── Conductor (coordinator) — Discord whisper + frontend modal
│   Tasks, social content, CAVE, TreeKanban, routing work
│   Skills: cave-social, treekanban, domain-knowledge, starsystem, etc.
│   MCPs: carton, sophia, sancrev_treeshell, compoctopus, observatory
│   (NOTE: sanctuary system MCP removed from Conductor → moved to Autobiographer)
│
├── Autobiographer (MOV) — bifurcated CentralChannel, three modes
│   Three channels, one carton substrate:
│   ├── CHAT mode: user adds memories, fills timeline (talk whenever)
│   ├── JOURNAL mode: structured daily capture (morning/evening routines)
│   └── NIGHT mode: contextualizes, deepens, connects → writes autobiography
│   Skills: journal-workflow, autobiographical-context
│   MCPs: sanctuary system, carton
│   THE MAIN COMPOUNDING ASSET — autobiography is the primitive.
│   Once you know who someone is, you project identity into anything.
│
├── Inner GNOSYS (coder) — terminal shell + frontend overlay
│   Builds things, makes PRs, autonomous coding
│   90% working, 30 tasks/hour (rate limited)
│
└── Observatory (researcher) — autonomous research swarm
    DUO pattern: Ariadne (researcher) + Poimandres (worker) + OVP (reviewer)
```

### Why Autobiographer is separate AND the most valuable agent:
- **Different purpose**: biographical coherence vs coordination
- **Different tools**: sanctuary MCP, not task management
- **Different context**: long-running life narrative, all on carton (no context engineering needed)
- **Three channels**: chat (add memories), journal (structured capture), night (contextualize + compile)
- **The compounding flywheel**: memories → autobiography → understanding → projections (books, content, decisions) → new memories → loop
- **Autobiography is the primitive**: identity is the root. Understanding × any domain = deliverables in that domain
- **Compiles once**: verified autobiographical context, updated incrementally

### The "skills not agents" rule still applies:
Everything WITHIN Conductor's domain = skills. Social content, CAVE, TreeKanban, starsystem — all skills on Conductor. No separate agents for those.

Separate agents ONLY when the purpose is fundamentally different:
- MOV = autobiography / records the Olivus identity formation (different purpose)
- Inner GNOSYS = autonomous coding (long-running)
- Observatory = autonomous research (long-running)

---

## Channel Architecture

```
#conductor-whisper    → Conductor (coordination, tasks, social review)
#journal              → MOV (morning/evening journals, autobiography)
#sanctum-noti         → Sanctum broadcasts (ritual reminders, completions, streaks)
                        Has its own mini CLI: "done <ritual>", "status", "skip <ritual>"
```

Sanctum notifications get their own channel with a CLI-like interaction, NOT inside the Conductor system. Conductor can look at the stuff on Carton from the other agents, and the other agents can look at the Conductor collection, but they have constrained tools for Carton observations — not the raw tool. Everything they observe into Carton is specifically bounded automatically.

(For v1, the constraint is handled by sanctuary MCP's `journal_entry()` which already structures observations. MOV only calls `journal_entry()`, never raw Carton.)

---

## The 5 Surfaces

### 1. Conductor Chat (Discord + frontend modal)
- The universal interface for coordination, tasks, social, business.
- Has domain-specific **skills** equipped.
- Reads **dynamic status files** every turn.
- Does NOT handle journaling (that's MOV).
- Needs memory system updated to work like Inner GNOSYS copilot, keyed to USER's current task.
- Needs new prompt block: **agent awareness** — what Inner GNOSYS, MOV, Observatory are currently doing.

### 2. Sanctum Space (frontend)
- Visual ritual/life management. 6 domains, GEAR scores, ritual cards.
- "✓ Complete" button wired to harness → streaks update → Discord confirmation.
- Shows today's completion map (done/not done).
- ✅ WIRED TO REAL DATA

### 3. TreeKanban (frontend)
- Task management with PBML lanes (Plan → Build → Measure → Learn).
- Visual overlays distinguish task types:
  - 🕯️ **Human-only** (Sanctum rituals) — green leaf border, already implemented
  - 🤝 **AI-Human** (PAIAB) — needs overlay
  - 🤖 **AI-only** (Starsystem) — needs overlay

### 4. Inner GNOSYS Shell (frontend)
- Terminal overlay for AI work.
- **AI-Human**: User drops in, works collaboratively.
- **AI-only**: User watches AI work autonomously.
- Already works.

### 5. CAVE (frontend + backend)
- Social content queue: trending topics, draft posts, review queue.
- Business metrics (future).

### Cron Dashboard (sub-surface of ReactFlow canvas)
- Shows all cron jobs: name, schedule, last run, status.

---

## The Daily Loop

### 🌙 3:00 AM — Social Content Cron (AI-only)
- **Trigger**: Sancrev treeshell Automation family fires cron.
- **Who runs**: New Conductor instance with `cave-social-content` skill.
- Scans trending topics (web search MCP).
- Drafts 1-2 posts based on user's niche + voice preferences.
- Saves drafts to filesystem + Carton.
- Updates `conductor_dynamic/social_queue.txt`.

### 🌅 6:00 AM — Morning Journal (MOV)
- **Trigger**: Automation cron fires.
- **Who runs**: New **MOV** instance (NOT Conductor).
- **Channel**: Dedicated journal Discord channel.
- **Pre-flight (hidden from user)**:
  - Reads yesterday's journal from Carton/filesystem.
  - Reads current sanctum status (ritual completions, GEAR, domain scores).
  - Reads overnight results (Observatory, social cron).
  - Compiles verified autobiographical context — the "story so far."
  - All of this happens BEFORE the first message to user.
- **User sees**:
  ```
  MOV: ☀️🌏💗🌐 Good morning!
  
  Overnight: 2 social posts drafted, Observatory ran 1 research task.
  
  How are you feeling? Walk me through your 6 dimensions.
  ```
- User talks naturally about their state, life, plans.
- MOV extracts 6 dimension scores + journal text.
- Calls `journal_entry(entry_type="opening", ...)` via sanctuary MCP.
- Updates Carton with autobiographical observations.

### ☀️ 6:30 AM — Morning Briefing (Conductor)
- **After journal completes**, Conductor assembles briefing from dynamic files:
  ```
  📋 RITUALS: 11 daily (0/11 done)
  📱 SOCIAL: 2 posts ready for review → want to see them now?
  📋 TASKS: 3 in PLAN lane
  🎯 GOALS: ship-paia-system, maximize-compression-ratio
  ```
- Conductor acts as second pair of eyes on social drafts.
- Reviews against user preferences, flags issues, fixes style.
- Tells user "ready to post" or "come back later."

### ☀️ Daytime — User-Driven
- **Complete rituals**: Click "✓ Complete" in Sanctum Space OR "done standup" on Discord.
- **Review social drafts**: Conductor shows, reviews, user posts manually (v1).
- **Do work**: TreeKanban tasks with type overlays.
- **Ask Conductor** whatever: "What's left?" / "Queue research on X"

### 🌙 10:00 PM — Evening Journal (MOV)
- Same as morning but `entry_type="closing"`.
- Reviews the day: rituals, tasks, social, feelings.
- MOV updates life story context.
- Conductor gets notified → announces night mode.

### 🌙 Night Mode (automated)
- **Definition**: Night mode = heartbeats firing + user AFK + agent done with ALL day tasks
- Observatory runs queued research.
- AI-only tasks continue.
- Social content cron prepares for morning.
- Night mode output gets **reviewed during DAY** as a ritualized type of operadic flow.

### ⚠️ GAP: No ritualization system for AI-Human tasks
- Sanctum rituals = human-only. TreeKanban = tasks. But there's no **ritualized AI-human** workflow.
- This is a PAIAB type — ritualized human-AI collaborative tasks.
- Night mode review is the first example: system proposes, human reviews, becomes ritualized.
- **This needs to be built for v1.**

---

## Conductor's Architecture

### Skills (not agents — these stay on Conductor)
| Skill | Purpose |
|-------|---------|
| `use-treekanban` | Task management, PBML lanes, GIINT hierarchy |
| `cave-social-content` | Trending topics, post drafting, review queue |
| `mcp-skill-starsystem` | Call Inner GNOSYS, Observatory |
| `mcp-skill-opera` | Frontend control, notifications |
| `domain-knowledge` | User's domain expertise |
| `conductor-heartbeat-workflow` | Heartbeat/keepalive |

### MCPs on Conductor
carton, sophia, sancrev_treeshell, compoctopus, observatory
(sanctuary system MCP **removed** — now on Autobiographer only)

### MOV (Memories of Olivus Victory) Architecture
| Component | Detail |
|-----------|--------|
| MCPs | sanctuary system, carton |
| Skills | journal-workflow, autobiographical-context |
| Channel | Dedicated journal Discord channel |
| Context | Verified autobiographical context (compiled, compacted) |
| Trigger | Cron at 6AM + 10PM |
| Tracks | The Olivus identity alignment as it forms in the DUO |
| Premise | Every meaningful memory is a data point on the path from Wasteland to Sanctuary |

### Dynamic Status Files (Conductor reads every turn)
| File | Content | Updated by |
|------|---------|-----------|
| `sanctum_status.txt` | Today's ritual completions, GEAR, goals | Heartbeat / status script |
| `social_queue.txt` | Pending social drafts summary | Social cron |
| `agent_status.txt` | What each agent is currently doing | Heartbeat (NEW) |
| `tasks.txt` | Current TreeKanban state | Heartbeat |
| `status.txt` | System state (day/night, active research) | Heartbeat |
| `memory.txt` | Dynamic memory | Conductor self |
| `notepad.txt` | Scratch pad | Conductor self |
| `MEMORY.md` | Persistent memory | Conductor self |

### Cron System
- **Engine**: Sancrev treeshell Automation family (runs in sancrev proper).
- **Pattern**: Each cron spawns a new agent instance (Conductor OR MOV).
- **Results**: Saved to dynamic files / Carton.

---

## The Three Task Types

| Indicator | Type | Managed by | Where user completes |
|-----------|------|-----------|---------------------|
| 🕯️ | Human-only | Sanctum | Sanctum Space "✓ Complete" or Discord "done X" |
| 🤝 | AI-Human | PAIAB | Inner GNOSYS Shell (collaborative) |
| 🤖 | AI-only | Starsystem | Auto-completes |

---

## What's Invisible to the User

HEAVEN framework, SDNA chains, Hermes execution, Compoctopus compiler,
Observatory DUO pattern, MCP server wiring, auto-compaction, heartbeat loops,
CartON knowledge graph internals, SkillTool mechanics...

**4 agents (Conductor, Olivus, Inner GNOSYS, Observatory). 5 surfaces. 1 daily loop.**

---

## v1 Task List

### Already Done
- [x] Sanctum Space wired to real data (rituals, goals, completion, streaks)

### The Build (priority order)
1. [ ] **Dynamic sanctum_status.txt** — script reads sanctum JSON + canopy → writes status file. Hook into heartbeat.
2. [ ] **Cron system via Automation family** — verify sancrev treeshell can schedule + fire. Wire it up.
3. [ ] **Journal Discord channel** — create channel. Wire cron → new MOV instance → channel.
4. [ ] **Sanctum notification channel** — separate Discord channel with mini CLI (done/status/skip). Broadcasts ritual reminders, completions, streak milestones.
5. [ ] **MOV agent (Memories of Olivus Victory)** — new agent class. Pre-flight contextualization (hidden). Sanctuary MCP. Journal conversation skill. Extracts scores, calls `journal_entry()`. Tracks Olivus identity formation.
6. [ ] **Remove sanctuary MCP from Conductor** — move to MOV. If Conductor needs VEC/degree tools, put on new MCP.
7. [ ] **Agent awareness prompt block** — `agent_status.txt` dynamic file. Heartbeat writes what each agent is doing. Conductor reads every turn.
8. [ ] **Conductor memory system update** — update to work like Inner GNOSYS copilot pattern, keyed to user's current task.
9. [ ] **Social content skill** — add web search MCP (30 min). Skill: scan trends → draft → save to pending.
10. [ ] **Social queue dynamic file** — `social_queue.txt`. Cron updates. Conductor reads + reviews.
11. [ ] **Morning briefing** — Conductor assembles after journal: sanctum + social + tasks.
12. [ ] **TreeKanban overlays** — CSS for 🤝 ai-human and 🤖 ai-only card types.
13. [ ] **Cron dashboard** — ReactFlow node showing cron status, toggle.
14. [ ] **Notification system builder** — reusable backend tool: make a noti system for any module with CLI + channel attachment.
15. [ ] **ChromaRAG partition filtering** — semantic query needs options for which partitions to include (skills, flights, tools, just concepts, GIINT stuff only, etc). Currently returns mixed results that are hard to filter.
16. [ ] **Skills audit** — verify all equipped skills have actual content.
17. [ ] **PAIAB ritualization system** — ritualized AI-human tasks (the missing piece). Night mode output reviewed during day as operadic flow. PAIAB type for human-AI collaborative rituals. Build today.
18. [ ] **Heartbeat thread separation** — separate heartbeat conversations from normal conversations. Agent should know about heartbeats from a heartbeat thread. This changes how the system works.
19. [ ] **Slinky testing with MOV** — test Slinky context compression protocol with Autobiographer/MOV first.

---

## Compaction Architecture (Critical Distinction)

### MOV / Autobiographer
- Uses **hierarchical summarizer** (same as what Inner GNOSYS uses)
- Has a **complete timeline** of interactions
- This means the narrative system can compile the sanctuary myth DIRECTLY from convos with autobiographer
- **Slinky** (context compression protocol) will be tested here first

### Conductor
- Uses **hierarchical summarizer** but ONLY for convos the user is actually in
- During heartbeat, uses **simple compaction** → goes directly to **phase aggregation** (pipeline needs to be made/refined)

### Heartbeat Thread Separation
- Heartbeat conversations MUST be separated from normal conversations
- The agent should know about what happens in heartbeats from a **heartbeat thread**
- This is massively important because it changes how context gets built and maintained

### Slinky
- Context compression protocol
- Testing with MOV/Autobiographer first
- If this works → solves context decay at scale

---

## Heartbeat Transcript Management (BaseHEAVENAgent)

The heartbeat mechanism is dead simple: a timer injects "Read HEARTBEAT.md. Follow it. If nothing needs attention, reply HEARTBEAT_OK." The HEARTBEAT.md file IS the loop — the agent reads it, does work, updates it, and next heartbeat picks up where it left off.

**The transcript pruning logic lives in BaseHEAVENAgent as a default keyword search.** It is always running, expected behavior — the agent doesn't even need to know about it unless we want it to deliberately use the pattern.

### !heartbeat Command vs Heartbeat Timer

These are two different things:

- **`!heartbeat` command** → edits HEARTBEAT.md (change the standing orders). This is the user/Conductor WRITING what the agent should do.
- **Heartbeat timer** → fires automatically on schedule, injects "Read HEARTBEAT.md". This is the MECHANISM that reads and follows the orders.

`!heartbeat` = control surface (what). Timer = execution (when).

### User Commands (v1)

All commands are prefixed with `!` and intercepted by the channel before reaching the agent.

| Command | Effect |
|---------|--------|
| `!heartbeat` | Edit HEARTBEAT.md (change standing orders) |
| `!stop` | Abort the current agent run immediately. Marks `abortedLastRun` on session. Partial output discarded. |
| `!prune n` | Remove the last `n` iterations (user+assistant turn pairs) from conversation history. Use when agent goes off the rails, accumulates garbage context, or you want to undo a bad exchange. |
| `!new` | Reset conversation — clear history, start fresh session (keep system prompt + HEARTBEAT.md) |

**Queue behavior when agent is busy:**
- Default: process immediately when idle, queue when busy, drain queue in order when done
- `!stop` clears the queue too (fresh start)
- Messages sent while agent is processing are queued and drained in order after the current run finishes

### Flow

```
Heartbeat fires → inject prompt → agent reads HEARTBEAT.md
│
├── Agent says HEARTBEAT_OK
│   → append "HEARTBEAT_OK @ {timestamp}" to heartbeat_log.md
│   → DELETE the heartbeat turn from conversation history
│   → Context stays clean, zero accumulation
│
└── Agent does actual work (not HEARTBEAT_OK)
    → Let the agent complete its run
    → Inject follow-up: "Summarize what you just did in ```HEARTBEAT_SUMMARY\n\n...\n\n```"
    → Catch the HEARTBEAT_SUMMARY fence from output
    → Append summary to heartbeat_log.md
    → DELETE the summary turn from conversation history
    → DELETE the work turn from conversation history
    → Context stays clean, summaries accumulate in log only
```

### Daily Report (Cron Job)

Every 24 hours, a cron automation:
1. Reads heartbeat_log.md
2. Compiles entries into a daily report
3. Delivers report (to Discord, to user, to Carton)
4. Clears the log for next day

### Implementation Location

- **Keyword detection** (`HEARTBEAT_OK`, `` ```HEARTBEAT_SUMMARY ```) → `BaseHEAVENAgent` output watcher
- **Heartbeat config** → `/tmp/heaven_data/heartbeat_config.json` (Isaac controls, agent reads only)
- **Standing orders** → `HEARTBEAT.md` in workspace root (agent updates as it works)
- **Log accumulation** → `heartbeat_log.md` (append-only, cleared on daily report)
- **Daily report** → Cron automation in [AutomationRegistry](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation.py#336-381)

---

## Heartbeat vs Cron (Critical Distinction)

**Heartbeat = OVERSIGHT.** Checks that things are working. Doesn't DO work.  
**Cron = LABOR.** Does specific isolated jobs on a schedule.

```
HEARTBEAT (general oversight loop)
  "Is everything working? Report bugs. Feed next tasks. Cohere KG if idle.
   Ask user about complex/recursive/nested changes before doing them.
   Otherwise user is fine with whatever you do as long as it adds to
   the whole and doesn't directly change patterns already being used."
  → HEARTBEAT.md is the standing orders (user sets via !heartbeat or conversation)
  → Runs on timer, checks everything, lightweight
  → Does NOT do labor — just observes and orchestrates

CRON (specific isolated jobs)
  "Check OpenClaw's work. Write report. Save to /reports/YYYY-MM-DD/HH.md"
  → Each job does ONE thing on a schedule
  → Has its own prompt, delivery target, session target
  → Does actual work — produces output, delivers results
```

The MISTAKE is putting labor in the heartbeat. Heartbeat stays clean:
- Check inbox
- Check cron jobs are running
- Check for bugs/issues
- Feed next tasks
- Cohere KG when idle
- Flag complex changes for user approval

Everything else is a cron job:

```json
{
  "name": "openclaw_report",
  "schedule": "0 * * * *",
  "prompt": "Check OpenClaw queue. Read files on OpenClaw docker. Write worker report.",
  "deliver_to": "file",
  "target": "/reports/{date}/{hour}.md",
  "session_target": "isolated"
}
```

Heartbeat is one specific cron job with tmux self-delivery. Cron is the general system.

### Library Architecture (FIXED)

The cron and selfbot libraries are part of **SDNA** (base library layer). CAVE's automation system **uses** them. Every automation is a **live class instance** in CaveAgent's runtime — you look at the code, you see exactly what the system does.

```
LAYER 1: SDNA (base library — primitives)
  sdna/cron.py       → CronJob, CronScheduler, DeliveryTarget, DeliveryType, SessionTarget
  sdna/selfbot.py    → SelfBot (tmux agent control / self-prompting)

LAYER 2: CAVE (application — uses primitives)
  cave/core/automation.py   → imports sdna.cron + sdna.selfbot
                             → Automation(Link) wraps CronJob with chain ontology
                             → AutomationRegistry loads/stores live instances
                             → AutomationSchema serializes to/from JSON

LAYER 3: RUNTIME (CaveAgent — live instances)
  cave_agent.automation_registry.automations = {
      "heartbeat":     Automation(schedule="*/15 * * * *", delivery=tmux),
      "daily_tweet":   Automation(schedule="0 9 * * *",   delivery=discord),
      "client_work":   Automation(schedule="0 */6 * * *", delivery=agent://openclaw),
      "daily_report":  Automation(schedule="0 22 * * *",  delivery=file),
  }
  ↑ loaded from /tmp/heaven_data/automations/*.json (dynamic)
  ↑ OR hardcoded in CaveAgent.__init__
  ↑ every single one is a LIVE CLASS INSTANCE — reflective runtime
```

### DeliveryTarget Types

| Type | Target | Use Case |
|------|--------|----------|
| [tmux](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/agent.py#216-220) | session name | Self-prompting (heartbeat) |
| `discord` | channel_id | Post to Discord channel |
| [agent](file:///Users/isaacwr/.gemini/antigravity/scratch/openclaw-review/src/cron/isolated-agent) | agent_id | Route to registered agent (OpenClaw, etc.) |
| [file](file:///Users/isaacwr/.gemini/antigravity/scratch/openclaw-review/Dockerfile) | path | Write result to file |
| `webhook` | url | POST to external URL |
| [callback](file:///Users/isaacwr/.gemini/antigravity/scratch/agent-control-panel/backend/orchestrator/server.py#1380-1388) | Python callable | In-process delivery |

### SessionTarget

- [main](file:///Users/isaacwr/.gemini/antigravity/scratch/agent-control-panel/backend/orchestrator/server.py#1536-1544) — runs on the main agent session (heartbeat pattern)
- `isolated` — spawns a fresh sub-agent for the task (OpenClaw's subagent pattern)

### Cron JSON Example

```json
{
  "name": "agency_content",
  "description": "Generate social content for agency clients",
  "schedule": "0 9 * * 1-5",
  "session_target": "isolated",
  "prompt_template": "Generate this week's social content for $client_name based on their brand guide at $brand_path",
  "template_vars": {
    "client_name": "AcmeCorp",
    "brand_path": "/workspace/clients/acme/brand.md"
  },
  "delivery": {
    "type": "agent",
    "agent_id": "openclaw-worker"
  },
  "priority": 7,
  "tags": ["agency", "content"],
  "enabled": true
}
```

---

## CAVE = Code Agent Virtualization Environment (Critical Fix)

CAVE is an **adaptor framework** that virtualizes ANY agent — local, remote, any framework — into a unified runtime with inbox, actor model, and channels. Every agent looks the same from code, regardless of whether it's a local Claude Code in tmux, a remote OpenClaw on Discord, or an SDNA chain.

**You code with them as local objects in one runtime. Even though they're potentially all remote systems. That's the virtualization.**

### The Agent Type Hierarchy (Corrected)

```
Agent                — base, has inbox, actor model
  ├── CodeAgent      — has tmux. Cron/heartbeat prompt INTO the tmux. You chat with it.
  ├── ChatAgent      — channel IS the inbox. You chat with it, but not via tmux.
  │                    1 channel → direct conversation
  │                    N channels → automatic queue with hook
  ├── RemoteAgent    — send it work, don't chat. Runs on cron/heartbeat.
  └── PAIA           — CodeAgent DI + paia-builder + starsystem. Own container.

CAVEAgent            — DIs everything. SANCREV impl = TOOT.
```

Specific agents are created by extending these types and DI'ing a runtime:

```python
class Conductor(ChatAgent):
    """Conductor — DIs a Heaven/SDNA agent system. 1 Discord channel."""
    def __init__(self, config):
        super().__init__(channels=[DiscordChannel(config.channel_id)])
        self.heaven_agent = BaseHeavenAgent(config)  # DI the runtime

class InnerGNOSYS(CodeAgent):
    """Inner GNOSYS — DIs a Claude Code session."""
    def __init__(self, config):
        super().__init__()  # inbox, actor model, tmux — free
        self.session = ClaudeCodeSession(config)  # DI the runtime

class OpenClaw(RemoteAgent):
    """OpenClaw — DIs a remote Discord worker."""
    def __init__(self, config):
        super().__init__()  # inbox, actor model — free
        self.channel = DiscordChannel(config.channel_id)  # DI the channel
```

CAVE types give infrastructure (inbox, actor model, channels). The specific agent DIs whatever runtime it uses. That's the adapter pattern. That IS CAVE.

**ChatAgent key insight**: the inbox typing fix is INHERENT in the type. No separate DIRECT vs INBOX enum needed. If ChatAgent has 1 channel, messages go straight through. If it has N channels, it queues automatically. The behavior emerges from configuration.


### What's Broken Now

**Root cause: Nobody used CAVE as a library.** Agents kept building flat FastAPI files with module-level decorators and global state. 2500 lines of spaghetti. Pure context decay.

1. **No `CAVEHTTPServer` class.** CAVE should provide an HTTP server that REQUIRES a CAVEAgent impl. Instead, http_server.py IS the entire application — no separation.

2. **No `SANCREV(CAVEAgent)` class.** Sancrev should subclass CAVEAgent and plug into CAVEHTTPServer. Instead, everything is inlined in http_server.py.

3. **Conductor is not a CAVE agent type.** It's a raw Python class with inverted CAVEAgent ownership. Should be `Conductor(ChatAgent)`.

4. **CAVEAgent is a mixin soup.** Should manage agent instances, not try to be one.

5. **OpenClaw is not wrapped.** Should be `OpenClaw(RemoteAgent)`.

CAVE is a **LIBRARY**. You import it. You implement a CAVEAgent. You plug it in.

```python
# CAVE provides:
class CAVEHTTPServer:
    """Takes port + CAVEAgent impl. That's it."""
    def __init__(self, port: int, cave: CAVEAgent):
        self.cave = cave
        self.app = FastAPI()
        self._register_routes()  # all routes delegate to self.cave

# SANCREV provides:
class WakingDreamer(CAVEAgent):
    """Singleton. Loads config from file. Hot-reloads changes.
    
    The god object. Lucid inside the cave.
    Has Conductor, Engineers, everything.
    Agents edit config → WakingDreamer hot-reloads → behavior changes.
    The system modifies itself. That's the reflective part.
    
    OVP (Omniscient Viewer Perspective) is not a separate agent —
    it's the USER's oversight perspective encoded into how
    WakingDreamer operates. Building OVP = teaching the
    WakingDreamer how the user sees.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config = self._load_config()  # from file
        self._watch_config()  # hot reload on change
        self.agents = [
            Conductor(ChatAgent),
            InnerGNOSYS(CodeAgent),
            OpenClaw(RemoteAgent),
        ]

# start_sancrev.py:
wd = WakingDreamer()  # singleton, config from file
cave_sanctuary = CAVEHTTPServer(8080, wd)
uvicorn.run(cave_sanctuary.app)
```

Steps:
1. Create `CAVEHTTPServer(port, cave_agent)` in CAVE library — all standard routes delegate to cave_agent methods
2. Create `ChatAgent` type — channel IS inbox, broadcast or queue mode
3. Create `WakingDreamer(CAVEAgent)` — singleton god object, hot-reloads config, OVP encoded
4. Create `Conductor(ChatAgent)` DI'ing existing Heaven agent
5. Create `OpenClaw(RemoteAgent)` DI'ing remote Discord worker
6. Move all 2500 lines of http_server.py logic into proper classes
7. `start_sancrev.py` becomes ~5 lines

### The CAVE Agent Registry (Actual)

**Four** agents exist in CAVE, plus one external:

| Agent | CAVE Type | Purpose | What CAVE Manages | Channel |
|-------|-----------|---------|-------------------|---------|
| **Conductor** | `ChatAgent` | Coordinator, user-facing, keeps everything operating | Everything | Discord |
| **Inner GNOSYS** | [CodeAgent](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/agent.py#125-432) | Coder, meta-agent, builds automations/connectors | Everything | tmux |
| **Autobiographer** | `ChatAgent` | Olivus — commits MOV (autobiography), contextualizes user life/identity into Carton, has sanctuary system MCP, narrative compilation, Slinky testing | Everything | Discord (own channel) |
| **OpenClaw** | `ClawAgent` | General worker — websites, socials, client work | Just the channel pipe | Discord |

**ClawAgent** = external agent with its own config and lifecycle. CAVE does NOT manage its config, heartbeat, or internals. CAVE only knows the channel to pipe to (Discord channel ID).

```python
class ClawAgent(Agent):
    """External agent. Own config. We just pipe to it via a channel."""
    channel: DiscordChannel  # channel_id we send to
```

Everything else is NOT a separate CAVE agent:
- **Observatory** — MCP/tool Conductor uses for research (SDNA MiniMax)
- **Sophia** — MCP/tool Conductor uses (TBD, maybe DUO later)
- **Compoctopus** — MCP/tool Conductor uses for agent compilation (TBD)

These are capabilities Conductor invokes, not agents with their own channels/inboxes/runtimes.

### TOOT = The PLAN Lane in the Kanban

TOOT is not a framework to build. TOOT is the **PLAN lane in TreeKanban**, glossed as "the TOOT" because it's agentified:

```
PLAN lane cards = operadic flows (goldenized missions)
Card assignees  = starsystems (self-improving agent nodes)
Card order      = the track (logic flow)
A set of cards  = a train (isolated workflow)
The whole lane  = the TOOT
```

An agentified plan that, if made right, would compile. The PLAN lane IS a TOOT rendered visually — tasks flowing through agent-stations. Every card is a unit of work. Every station is a self-improving node. The flow IS the train on tracks.

No train library needed. The kanban IS the TOOT. **Do NOT rename PLAN to TOOT** — keep PLAN, the TOOT gloss is internal/epistemological. TOOT overlay styling can be added to the TreeKanban PLAN lane visually.

### Conductor vs GNOSYS vs Sophia — Clear Separation

| Agent | Role | Operates At | Mode |
|-------|------|-------------|------|
| **Conductor** | Orchestrate & approve | System level | Always user-facing |
| **Sophia** (Compoctopus) | Compose existing parts into flows | Type level | Autonomous only |
| **Inner GNOSYS** | Build new parts from scratch | Code level | Autonomous + Collaborative |

```
CONDUCTOR (ChatAgent)                GNOSYS / Inner GNOSYS (CodeAgent)
├── User-facing chat                 ├── Auto-agentic engineering agent
├── Orchestrates everything          ├── Codes, configures AI integrations
├── Approves Sophia proposals        ├── Runs STARSYSTEMs with scores
├── Keeps everything operating       ├── Builds bigger and better stuff
├── Heartbeat: coheres KG,           ├── Heartbeat: checks task queue,
│   works on system memory           │   picks next task or goes idle
└── NEVER codes                      └── Two modes (see below)

SOPHIA (via Compoctopus)
├── System-specific compiler
├── Knows CAVE types, SDNA chains, automation ontology
├── Composes existing pieces into running automations/flows
├── Observes TOOT → designs automations → proposes to Conductor
└── D:D→D — Compiler that compiles Compilers
```

### GNOSYS Two Modes

```
AUTONOMOUS MODE (default):
  Conductor queues task → GNOSYS codes it → sets up AI configs →
  runs as STARSYSTEM → scores itself → iterates → reports back
  User does NOT talk to GNOSYS directly

COLLABORATIVE MODE (kanban-gated):
  User's current PLAN card = "vibe code feature X"?
    → GNOSYS channel unlocked, user can talk directly
    → AI-Human pair programming (vibe coding)
    → Human-in-the-loop for architecture decisions
  
  User's current PLAN card = anything else?
    → GNOSYS stays autonomous, user talks to Conductor only
    → The kanban IS the access control
```

**The system manages the user's attention.** You don't randomly drop into coding — the TOOT tells you when it's time.

### Automation Creation Flow

| Need | Who Does It | How |
|------|------------|-----|
| Wire existing capabilities into automation | **Sophia** composes it | Assembles Links into Chains, writes JSON config, proposes to Conductor |
| New capability that doesn't exist yet | **GNOSYS** codes it | Creates new module, new Link type, new integration |
| Approve and load | **Conductor** reviews it | Approves proposal, CAVE hot-reloads |

Conductor's flow:
1. Conductor designs the automation (what data flows where)
2. Sophia composes it from existing types (OR queues to GNOSYS if new code needed)
3. GNOSYS builds new parts if needed, returns result
4. Conductor approves → JSON config written → CAVE hot-reloads
5. The TOOT (plan lane) grows — new card appears with the automation
