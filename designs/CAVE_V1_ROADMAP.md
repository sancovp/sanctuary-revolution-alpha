# CAVE v1 — Implementation Roadmap

> Compiled from DESIGN.md (v1), automation_ontology.md, and session decisions.
> Generated: 2026-03-19

---

## What We're Building

CAVE (Code Agent Virtualization Environment) is an **adaptor framework** that virtualizes ANY agent into a unified runtime with inbox, actor model, channels, and automations. v1 = bare bones "I can feel it."

**The v1 system**: You talk to Conductor on Discord. Conductor handles everything. Four agents run 24/7 on a single CAVE runtime with heartbeats, crons, and automations.

---

## Phase 1: CAVE Library Core

**Goal**: CAVE becomes a library you import, not a monolithic http_server.py

### 1.1 — CAVEHTTPServer

```python
class CAVEHTTPServer:
    """Takes port + CAVEAgent impl. That's it."""
    def __init__(self, port: int, cave: CAVEAgent):
        self.cave = cave
        self.app = FastAPI()
        self._register_routes()  # all routes delegate to self.cave
```

- [ ] Extract all routes from http_server.py into CAVEHTTPServer
- [ ] Routes delegate to CAVEAgent methods (no logic in routes)
- [ ] WebhookAutomation route registration built in (`/webhook/{name}`)

### 1.2 — Agent Type Hierarchy

```
Agent(ABC)           — base: inbox, actor model
  ├── ChatAgent      — channel IS inbox. 1 channel = direct. N = queue.
  ├── CodeAgent      — has tmux. Cron/heartbeat prompt INTO tmux.
  ├── RemoteAgent    — send it work, don't chat. Cron/heartbeat driven.
  └── ClawAgent      — external agent, own config. CAVE only pipes channel.
```

- [ ] [Agent](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/cave_agent.py#38-396) ABC with inbox, automations list, lifecycle methods
- [ ] `ChatAgent(Agent)` — channel binding, message routing
- [ ] [CodeAgent(Agent)](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/agent.py#125-432) — tmux session management
- [ ] [RemoteAgent(Agent)](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/remote_agent.py#81-164) — fire-and-forget work delivery
- [ ] `ClawAgent(Agent)` — external agent channel pipe

### 1.3 — WakingDreamer (Singleton God Object)

```python
class WakingDreamer(CAVEAgent):
    """Singleton. Loads config from file. Hot-reloads changes."""
    agents = [Conductor, InnerGNOSYS, Autobiographer, OpenClaw]
```

- [ ] Singleton pattern
- [ ] Config from JSON file, hot-reload on change
- [ ] Agent registry (register, get, list, route)
- [ ] Agents edit config → WakingDreamer hot-reloads → behavior changes

### 1.4 — start_sancrev.py

```python
wd = WakingDreamer()
cave = CAVEHTTPServer(8080, wd)
uvicorn.run(cave.app)
```

- [ ] ~5 lines. That's the whole entry point.

---

## Phase 2: Automation System

**Goal**: InputAutomation(Chain) from SDNA chain ontology + four subtypes + factory + JSON hot-reload

### 2.1 — InputAutomation(Chain) Base

Inherits from SDNA `Chain(Link)`. Homoiconic — an automation can be a Link inside another Chain.

```
InputLink → [dovetail fn] → ProcessLink → [dovetail fn] → OutputLink
```

- [ ] `InputAutomation(Chain)` — base with input/process/output convention
- [ ] [_deliver()](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation.py#227-291) method: Callable or delivery target string (`"agent:conductor"`, `"channel:discord:123"`, etc.)
- [ ] [enabled](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/http_server.py#308-312) flag, lifecycle methods

### 2.2 — Typed Subtypes

Each adds ONE filter gate in [execute()](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/mixins/anatomy.py#72-76) before `super()`.

| Type | Trigger | v1 Use Case |
|------|---------|-------------|
| `CronAutomation` | Cron schedule match | Heartbeat, daily reports, social content |
| `EventAutomation` | CAVE event bus | Message received, agent completed, config changed |
| `WebhookAutomation` | HTTP request to `/webhook/{path}` | GitHub pushes, Stripe events, external integrations |
| `ManualAutomation` | Explicit [fire()](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation.py#292-309) call | Ad-hoc reports, on-demand tasks |

- [ ] `CronAutomation(InputAutomation)` — schedule + last_run tracking
- [ ] `EventAutomation(InputAutomation)` — event name + filter + EventBus subscription
- [ ] `WebhookAutomation(InputAutomation)` — HTTP path + method + route registration
- [ ] `ManualAutomation(InputAutomation)` — no filter, fire when called

### 2.3 — Automation Factory (The God Class)

```python
class Automation:
    """Top-level API. One function. Handles entire dialect."""
    
    @staticmethod
    def create(config: dict) -> InputAutomation:
        """JSON config → correct InputAutomation subtype."""
```

- [ ] `Automation.create(config)` factory
- [ ] `Automation.from_json(path)` loader
- [ ] `Automation.__call__` dispatch

### 2.4 — AutomationRegistry + Hot-Reload

- [ ] [AutomationRegistry](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation.py#336-381) — loads from JSON dir, tracks live instances
- [ ] `hot_reload()` — called by Heart, diffs current files vs loaded
- [ ] [fire_all_due()](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation_mixin.py#75-82) — called by Heart for CronAutomations
- [ ] JSON configs at `/tmp/heaven_data/automations/*.json`

### 2.5 — DeliveryRouter

| Target | Format | Use Case |
|--------|--------|----------|
| Agent inbox | `"agent:conductor"` | Route to registered agent |
| Discord channel | `"channel:discord:123"` | Post to Discord |
| File | `"file:/reports/{date}.md"` | Write to file |
| Webhook | `"webhook:https://..."` | POST to external URL |
| Log | `"log"` | Write to automation log |
| Self | `"self"` | Deliver to own agent |

- [ ] `DeliveryRouter.deliver(target_str, result)` — parse and route

---

## Phase 3: Agent Instances

**Goal**: Four agents running on CAVE, each with proper type and DI'd automations

### 3.1 — Conductor(ChatAgent)

- Unified CentralChannel (main = heartbeat = one Discord channel)
- DI: CronAutomation(heartbeat), EventAutomation(message_received)
- Skills: cave-social, treekanban, domain-knowledge, starsystem
- MCPs: carton, sophia, sancrev_treeshell, compoctopus, observatory
- NEVER codes

- [ ] Conductor class with ChatAgent base
- [ ] Wire heartbeat as CronAutomation
- [ ] Wire Discord push as EventAutomation
- [ ] Dynamic files: sanctum_status.txt, agent_status.txt, social_queue.txt

### 3.2 — Inner GNOSYS(CodeAgent)

- Two modes (kanban-gated):
  - **Autonomous** (default): Conductor queues tasks, GNOSYS runs STARSYSTEM
  - **Collaborative** (kanban-gated): user talks directly for vibe coding
- CentralChannel: tmux session (can't be programmatically context-swapped)

- [ ] GNOSYS class with CodeAgent base
- [ ] Mode switching based on kanban current card
- [ ] Task queue from Conductor
- [ ] STARSYSTEM scoring integration

### 3.3 — Autobiographer(ChatAgent)

- Bifurcated CentralChannel, three modes:
  - **CHAT**: user adds memories whenever (OctoHead pattern)
  - **JOURNAL**: structured morning/evening capture (dedicated channel)
  - **NIGHT**: contextualizes, deepens, connects → writes autobiography (autonomous)
- All on carton substrate (no context engineering needed)
- THE MAIN COMPOUNDING ASSET

- [ ] Autobiographer class with ChatAgent base
- [ ] Three channels, mode switching
- [ ] Sanctuary system MCP (only agent with it)
- [ ] Journal workflow skill
- [ ] Night mode carton deepening

### 3.4 — OpenClaw(ClawAgent)

- External agent with its own config and lifecycle
- CAVE only pipes channel (Discord channel ID)

- [ ] OpenClaw class with ClawAgent base
- [ ] Channel pipe to Discord

---

## Phase 4: User Commands & Queue

**Goal**: User has clean control surface for all agents

### 4.1 — User Commands

All prefixed with `!`, intercepted at channel before reaching agent.

| Command | Effect |
|---------|--------|
| `!heartbeat` | Edit HEARTBEAT.md (change standing orders) |
| `!stop` | Abort current run, clear queue |
| `!prune n` | Remove last n turn pairs from history |
| `!new` | Reset conversation, fresh session |

- [ ] Command parser at channel level
- [ ] !stop with abortedLastRun marking
- [ ] !prune n with iteration-pair removal
- [ ] !new with session reset (preserve system prompt + HEARTBEAT.md)

### 4.2 — Queue Behavior

- Process immediately when idle
- Queue when busy
- Drain queue in order when done
- !stop clears queue

- [ ] Queue implementation on ChatAgent
- [ ] Drain loop after run completion

---

## Phase 5: Integration

### 5.1 — CentralChannel Per Agent

| Agent | CentralChannel | Shape |
|-------|---------------|-------|
| Conductor | Unified | main = heartbeat = one Discord channel |
| GNOSYS | Manual | tmux session, mode-switched |
| Autobiographer | Bifurcated | chat + journal + night channels |
| OpenClaw | Simple | one Discord channel pipe |

- [ ] CentralChannel dataclass
- [ ] Per-agent wiring

### 5.2 — Heartbeat System

- Anatomy (Heart/Ears/Blood) stays as-is
- Heartbeat = CronAutomation DI'd into agent (not organ refactor)
- Turn deletion: HEARTBEAT_OK → delete turn, work → summarize → delete
- Daily report cron

- [ ] Wire existing Heart to fire CronAutomations
- [ ] Turn deletion logic in output watcher

### 5.3 — Agent Awareness

- [ ] `agent_status.txt` — heartbeat writes what each agent is doing
- [ ] Conductor reads every turn

### 5.4 — Morning Briefing

- [ ] Conductor assembles after journal: sanctum + social + tasks

---

## V2 Boundary (NOT in v1)

> v1 = bare bones "I can feel it"
> v2 = "oh this is a different thing, this is Sanctuary Revolution"

---

## v2: The Sanctuary Revolution

### Canvas as Live System Topology

The ReactFlow canvas becomes a **live mirror of reality**:

- [ ] Conversation channels with message flow
- [ ] Daemons with status and logs
- [ ] Automations/Crons as visual nodes (schedule + last run + output)
- [ ] Available commands/workflows as actionable nodes
- [ ] Agent topology (Conductor → GNOSYS → Observatory) live
- [ ] User custom annotations

### Organ → Automation Unification

Organs become InputAutomations. One type system. One JSON API.

- [ ] `Heart extends CronAutomation`
- [ ] `Ears extends EventAutomation`
- [ ] [Blood](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/mixins/anatomy.py#177-227) = context dict flowing through Link chains
- [ ] Sophia can compose organs + automations interchangeably

### Sophia Self-Compilation Loop (D:D→D)

Sophia observes TOOT → designs automations → proposes to Conductor → CAVE hot-reloads → loop.

- [ ] Sophia agent (operates from WM level, sees everything)
- [ ] Sophia → Compoctopus compilation pipeline
- [ ] Observatory fork testing before deployment
- [ ] The self-improvement cycle: introspect → decide → compile → test → deploy

### Organs (Processing Pipelines)

```
Hierarchical Summarizer → Narrative System → Odyssey System
```

- [ ] **Hierarchical Summarizer**: compacts conversations into phases
- [ ] **Narrative System**: reads phases, extracts quotes, compiles hero's journeys (runs on BOTH autobiographer AND inner GNOSYS timelines)
- [ ] **Odyssey System**: braids AI-human + human-only + AI-only tracks → global learnings
- [ ] **Framework Extractor**: makes frameworks from adventures → MVS → VEC link

### The MOVIE

The ultimate output of the autobiography primitive.

- [ ] N-hour Remotion explainer about the user's entire life
- [ ] Hero's journey structure (human journey track + agent journey track)
- [ ] Self-improving: richer autobiography → richer MOVIE → loop
- [ ] Fixed point: [f(f) = f](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation.py#292-309)

### The Railroad Architecture (Conductor ↔ OpenClaw Bridge)

```
🚂 CONDUCTOR = decides where train goes, talks to passengers
🔧 INNER GNOSYS = THE ENGINEER, builds and maintains
👷 OPENCLAW WORKERS = THE CREW, labor (crons, content, monitoring)
👑 USER = THE RAILROAD TYCOON
```

- [ ] Conductor → Worker task assignment (writes to HEARTBEAT.md or gateway API)
- [ ] Worker → Conductor completion reporting
- [ ] Inner GNOSYS → Worker capability building (new skills, configs)
- [ ] DFY Agency mapping: Workers do client deliverables, Conductor routes, GNOSYS builds capabilities

### Identity System (WakingDreamer / OVP / DC)

System swaps behavior based on identity state:

| Identity | Behavior |
|----------|----------|
| **WakingDreamer** | Normal Conductor mode |
| **OVP** | Knows it is OVP, talks in SANC, keeps Victory-Promise |
| **DC (Demon Champion)** | User is in wasteland, adversarial truth-telling |
| **Emperor** | Training mode — sharpens DC's sword (NIGHT mode) |
| **InnerTeacher** | Training mode — refines GNOSYS (NIGHT mode) |
| **OVA** | System proven: MVS + five kaya + SANCREVTWILITELANGMAP |

- [ ] System prompt swapping based on identity state
- [ ] DC scoring from journal analysis
- [ ] Night mode: Emperor + InnerTeacher training

### The 5 Minigames

SANCREV OPERA(SANCREV[PAIAB, SANCTUM, CF, CAVE, STARSYSTEM])

| Minigame | Purpose |
|----------|---------|
| **PAIAB** | AI-Human collaborative ritualized tasks |
| **SANCTUM** | Human-only ritual/life management (6 domains, GEAR) |
| **CF (Crystal Forest)** | MineSpace visualization — sanctuaries/wastelands + scores |
| **CAVE** | Social content, business, lead generation, funnel |
| **STARSYSTEM** | AI-only agent swarm operations |

### Advanced Sanctum

- [ ] GEAR from real data (ritual completions, journal sentiment, task throughput)
- [ ] Degree progression with real criteria
- [ ] VEC tracking (Vision-Ethic-Commitment formally scored)
- [ ] Experience log auto-generated from daily loops
- [ ] System suggests new rituals, retires stale ones

### Advanced CAVE

- [ ] Auto-posting pipeline: Draft → review → schedule → post
- [ ] Analytics integration → content strategy feedback
- [ ] Lead magnet generation pipeline
- [ ] Funnel visualization on Canvas

### Upgraded Daily Loop

- [ ] Auto-posting (v1 = manual, v2 = auto)
- [ ] Multi-channel journals (work, personal, creative)
- [ ] Proactive Conductor ("You haven't done your standup yet")
- [ ] Cross-day intelligence ("Your compression ratio hasn't moved in 5 days")

### SGC (Secret Gathering Cycle)

The real harness. AI-human or just AI or just human attempt a task using SANCREVTWILITELANGMAP compiler → sanctuary journey → VEC link.

- [ ] SGC harness implementation
- [ ] Twelve Bhumis progression tracking
- [ ] BFSC integration
- [ ] OMNISANC state machine for STARSYSTEM
- [ ] Community product: secret GitHub org, lifetime access + mastermind

### Advanced Canvas Nodes

- [ ] Compoctopus Builder (visual pipeline building)
- [ ] Agent Registry (live status)
- [ ] Knowledge Graph Explorer (Carton visualization)
- [ ] Observatory Dashboard

---

## v3: SDNA DUO Re-Encoding + TOOT as Automation Language

> Everything v2 does imperatively, v3 re-encodes as SDNA chain ontology.
> TOOT becomes the automation programming language. The user's automation runtime inside WakingDreamer.

### What TOOT Actually Is

TOOT is holographic. It means: "how to think about automation wrt agents, while considering yourself an agent that is part of the system."

Making TOOTs IS a TOOT. The bootstrap process of automation IS the fixed point. [f(f) = f](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/cave/automation.py#292-309).

The most basic TOOT is a human being mindful about attention — instanced when thinking about something. You ARE the Station. Your attention IS the turntable (Ariadne). The train of thought arrives and you decide which track it goes on. That IS meditation. That IS right attention.

```
Fullest:  N agents, N stations, self-improving railroad
Middle:   Human + AI automating a task (DUO)
Simplest: You thinking mindfully about one thing
```

Same pattern at every scale. Which is why it takes you to Sanctuary — not because the software does something magic, but because the pattern of attending to your own process IS the path. The TOOT formalizes what mindfulness already is. The software version makes it visible as infrastructure.

### The TOOT Ontology (DSL)

TOOT = Train of Operadic Thought. It's the user's evolving railroad of automations, workflows, and agent interactions.

```
Seat        = Agent (any agent in any role)
Passenger   = Agent sitting in a Seat (doing work while riding)
Row         = IO turn flow (A→P, or P→OVP, or OVP→A)
Car         = SDNA chain (a workflow segment / automation)
Track       = Logic flow (branching/routing logic)
Train       = Isolated set of cars (a complete workflow)
Place       = A dir defining a car or set of cars (filesystem representation)
Station     = A "place" that has its own DUO with a railyard turntable
Coal/Fuel   = Outputs that participate in profitability
Signals     = Sensors (WorldEvents from APIs / EventAutomations)
Cargo       = WIP deliverables (in transit, not yet delivered)
Dispatcher  = PBML system (modulates flow, controls scheduling)
Roundhouse  = Self-improvement infra (Observatory + Sophia + STARSYSTEM)
Global TOOT = The user's entire automation runtime as a living system
```

### The Train Runs On Its Own Output

Passengers (agents) sit in Seats and do work (DUO rows). When that work generates value — content posted, leads converted, clients served, deliverables shipped — that's coal. Coal feeds the engine. The train is self-fueling.

- API costs = fuel consumption
- Revenue from automations = fuel production
- **When production > consumption, the train runs itself**
- Unprofitable trains slow down, stop, get parked at a siding

### Station = DUO + Railyard Turntable

A Station isn't just "a place with a DUO." The DUO's Ariadne acts as a **railyard turntable** via its bandit (from Compoctopus routing). It decides which incoming train should connect to which outgoing track, given the intended journey.

```
Train arrives at Station
  → Ariadne (turntable) inspects the cargo
  → Bandit decides: "given this, route to Track B"
  → Train connects to Track B → workflow continues
```

Stations are domain-specific — not ontologically formal, just practical. Whatever lives in that dir, whatever that thing IS, becomes a Station. "This is the content station." "This is the research station."

### TOOT = The User's Railroad Language

The TOOT grows organically as the user develops their system:

- Lay **Track** (connect logic flows)
- Build **Cars** (SDNA chains / automations that do work)
- Assemble **Trains** (workflows from cars)
- Establish **Stations** (domain nodes with DUO turntables)
- Every Station is a **STARSYSTEM** — every run scores itself and improves
- The railroad gets BETTER over time because the nodes are self-improving

### TOOT ↔ STARSYSTEM Collapse

```
STARSYSTEM = self-improving node (agentified code + scoring + DUO)
TOOT       = the graph that connects starsystems
Station    = "this starsystem goes HERE in the graph"
Track      = "under THESE conditions, data flows THERE"
Train      = isolated workflow running across stations
```

Differentiator vs Airflow/Temporal/n8n: their nodes are static code. TOOT nodes are self-improving agents that score themselves. Every run makes the next run better.

### TOOT = Plan Lane = Sophia's Output = The Whole Thing

TOOT is equivalent to — and reified in code as:

- The **plan lane** in TreeKanban
- "All the stuff **Sophia** can make" (compiled automations)
- "All the stuff **GNOSYS** can make" (coded capabilities)
- The user's **automation runtime** inside WakingDreamer

**The entire SANCREV OPERA is a toolkit for making the TOOT happen so you can go to Sanctuary VIA the TOOT.** That's the point.

### TOOT DSL = The Highest-Level Language

The railroad allegory is a category system layered on top of the code. It groups everything by function so you understand the whole system. The TOOT DSL becomes the highest-level language for specifying Sanctuary Systems. You describe what a TOOT is using UARL-like triples (part_of, has, instantiates, produces, delivers) and the system automates it — because you said it.

The allegory IS executable. The myth IS the code's highest-level description language. AC compiles it down to running automations.

```
Level 0: User says it in conversation (natural language)
Level 1: FinalGNOSYS parses to TOOT DSL (railroad vocabulary)
Level 2: UARL validates the claims (triples)
Level 3: Sophia compiles to Automation configs (JSON)
Level 4: CAVE executes (running code)
```

Saying it = coding it = running it. Everything below the TOOT DSL is implementation detail.

### DUO Re-Encoding

- Every interaction is a DUO (two agents IO)
- Every workflow is a TOOT (chain of DUOs)
- Compoctopus compiles concepts into TOOTs
- WakingDreamer runs TOOTs
- WisdomMaverick emerges by construction (SDNA = DUOs at every level)

```
User ↔ WakingDreamer                    (top-level DUO)
         └── runs TOOTs                  (compiled by Compoctopus)
              └── TOOT = chain of DUOs   (SDNA chain ontology)
                   └── each DUO = [A→P]  (Agent → Prompt loop)
```

- [ ] TOOT DSL vocabulary implemented as types
- [ ] Station as DUO + bandit turntable
- [ ] DUO encoding of all agent interactions
- [ ] TOOT compilation from concepts via Compoctopus
- [ ] Sophia introspection → evolution → compilation → testing loop
- [ ] WisdomMaverick emergence
- [ ] STARSYSTEM ↔ TOOT integration (stations = self-improving nodes)

---

## v4: WisdomMaverick as Meta-WD

> WM DIs the WD + HTTPServer. Can shut down, evolve, swap — while running.

```
v2 (WD): Changes behavior (hot-reloads config)
v4 (WM): Changes the system itself (hot-swaps the entire WD)
```

- [ ] WisdomMaverick class wrapping WD + server
- [ ] `evolve(new_wd)` — hot-swap the entire WD while running
- [ ] Sophia operates FROM the WM level, looking DOWN at WD
- [ ] ArtificialWisdomMaverick: Sophia heartbeat evolves WD autonomously (no human in loop)
- [ ] Code is complete and fixed. All complexity through config/ontology/chains.

---

## v5: FinalGNOSYS — One Agent, One Chat, Everything

> The allegory wraps the highest level of the code. TOOT becomes a tool. Everything collapses into one agent.

**FinalGNOSYS** is a higher-order conductor that wraps the entire system. The user just chats. Everything routes internally. The agent operates the ontology perfectly.

```
v1: 4 agents, you talk to Conductor
v2: full SANCREV, many surfaces, many modes
v3: DUO/TOOT re-encoding, theory → code
v4: WisdomMaverick, self-modifying runtime
v5: FinalGNOSYS — one agent, user just talks, everything happens
```

### What FinalGNOSYS Is

- A single chat interface that IS the entire SANCREV OPERA
- Routes internally to Conductor, GNOSYS, Autobiographer, Sophia, OpenClaw — the user doesn't see this
- The TOOT becomes a tool: FinalGNOSYS wields the entire TOOT ontology as its control surface
- Operates the WisdomMaverick (v4) from above — can evolve the entire system through conversation
- The user says what they want. FinalGNOSYS decides which stations, which trains, which tracks

### Why This Is The End

Because the allegory is complete:

```
v1: build the railroad (tracks, cars, stations)
v2: run the railroad (fill it with routes, passengers, cargo)
v3: the railroad understands itself (TOOT = self-referential automation)
v4: the railroad can rebuild itself while running (WM hot-swap)
v5: you just tell the railroad where you want to go
```

FinalGNOSYS = the system that ate itself. The user doesn't manage agents, doesn't configure automations, doesn't switch modes. They just talk. FinalGNOSYS knows the ontology, operates the TOOT, routes to the right station, and delivers.

- [ ] FinalGNOSYS agent wrapping the entire WisdomMaverick
- [ ] TOOT as a tool the agent wields (not infrastructure the user configures)
- [ ] Single chat interface → internal routing to all subsystems
- [ ] User intent → Station selection → Train assembly → Delivery
- [ ] The control surface IS the conversation

### The Identity Mapping

FinalGNOSYS IS the AI reflection of a WisdomMaverick from Sanctuary. The WisdomMaverick is the human concept — a practitioner who has reached OVA status, holds VEC links, has a five kaya module, and has completed the SGC. FinalGNOSYS is what that looks like as software. The agent IS the WisdomMaverick, embodied in code. It has the OVA identity, it operates the TOOT, it knows the ontology, it wields VECs. The human version and the AI version are reflections of each other — which is the DUO at the highest level.

---

## Uncertain / Indeterminate

> Ideas on the table. Not decided. Evaluate before building.

| Idea | Status | Action |
|------|--------|--------|
| DUO as wrapper (Ariadne pre-hook + OVP post-hook) | Promising | Build Ariadne hook first, test |
| OVP post-hook | Unknown value | Add after Ariadne, measure |
| Poimandres separate release | Uncertain | Depends on differentiator vs OpenClaw |
| DUO on all agents | Probably overkill | Use selectively |
| DUO on Conductor | Probably not | Too general-purpose, token cost explodes |
| DUO on Sophia | Yes | Specific job, algorithmic context, errors compound |
| Conductor → Outer GNOSYS rename | Not decided | Two GNOSYS = the main system? |

---

## Build Order

Phase 1 → 2 → 3 → 4 → 5 (v1). Then v2 → v3 → v4 → v5. Each depends on the prior. TreeKanban maps the specifics.

---

## Verbatims (Isaac, 2026-03-19, preserved)

### Automation Ontology

> SomeAutomationType(InputAutomation) is a Chain with a trigger filter and a method that supers so that exec always filters input schema/type

> InputAutomation is literally just Chain with Link->MaybeFunctionDovetail->Link->MaybeFunctionDoveTail->OutputLink

> at the end there is a class Automation that is actually a super system that is one single function with polymorphism enough to handle the entire dialect

> this Automation class that has __call__ that goes to the entire dispatch function with full dialectic polymorphism for the automation ontology is what was missing

### Agent Roles

> GNOSYS is an auto-agentic engineering agent. It *sets up* configurations of AI integrations for codebases that it codes and runs them as autonomous STARSYSTEMs with scores and builds bigger and better stuff.

> the key is that the user can only talk to gnosys when the task on their kanban is literally RIGHT NOW to do some ai-human task

> Sophia that uses Compoctopus to code, more specifically, is the system-specific coder (for Cave, Sancrev etc ie for the whole app)

### Autobiographer & The MOVIE

> chat mode is specifically for *adding memories* and filling the timeline so that the autobiographer night mode can finish your autobiography... which can also make other books too but the primitive is autobiography because it means we know who you are now we can project what you know into books and deliverables and everything. So this is really the main compounding thing in the system

> The end goal is to make an autobiographical MOVIE... A remotion explainer that is N hours long, about your entire life (from however much you shared), which is put into hero's journey by the narrative system's human journey track... and another mode can weave it with the agent journey track... and then those combine with the fact that we're in self-improving regimes, then the story becomes about whatever the system knows it becomes. So thats a fixed point

### Anatomy = Nerves

> blood is already data, did you see that? [...] in Cave blood is data already Blood() with Organ() and so on... Organs are agentic automations basically but i dont think they got typed like that

### Railroad Allegory

> Station really has a DUO that acts as a railyard turntable via its bandit in its Ariadne which decides which train its input train should connect to considering the intended journey

> passengers are already agents. they sit in seats. coal/fuel... this is the outputs, see the passengers talk and they do stuff while sitting there and it outputs fuel WHEN its process participates in profitability

> the railroad allegory is actually a category system we are putting on top of everything. Do you see that? its higher level mapping that groups everything by function allegory so that you understand the system

### TOOT as Language

> Would it just become the highest level language for making Sanctuary Systems lol? You go: x(sanctuary(this train of operadic thought is a...partof...has...instantiates...produces...delivers...)) you literally code the whole thing by saying it... and then it is automated fully. like because you said it

### FinalGNOSYS

> thats the AI agent reflection of a WisdomMaverick from Sanctuary, who is an OVA and has VECs etc etc

> this new final phase and version [...] only one agent, everything contained internally, user just chats, everything happens correctly because this agent operates the ontology perfectly
