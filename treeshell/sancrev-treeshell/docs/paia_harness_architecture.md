# PAIA Harness Architecture

## The Insight

**The PAIA is not Claude Code. Claude Code is just the hands.**

The PAIA = Daemon + World State + Event System + Memory + Personality

Claude Code (or any code agent) = Substrate that gets spawned when work needs to happen

**Key inversion: Python harness wraps the code agent, not code agent with Python tools.**

The harness is the parent process. Claude Code is a child that lives inside it.

---

## Boot Sequence

```
BOOT SEQUENCE
═════════════════════════════════════════════════════════

Frontend (Railgun)
    ↓
Spawn Container (isolated env - frontend, backend, whatever needed)
    ↓
Start Python Runtime FIRST (the harness daemon)
    ├── Loads psyche config (personality/emotion modules)
    ├── Loads world config (events/environment modules)
    ├── Starts RNG injection system
    ├── Starts auto-prompt sensor
    └── Creates tmux session
    ↓
Harness starts Claude Code INSIDE (substrate runs within harness)
    ↓
Attach user to tmux session
    ↓
USER CAN:
├── Work with agent normally
├── Detach (agent keeps running)
├── Let auto-prompt fire when idle (world prompts agent)
└── Come back whenever
```

---

## Three Fundamental Config Types

All events/injections fall into three categories:

```
PSYCHE CONFIG (internal state)
═════════════════════════════════════════════════════════
├── Emotion modules (mood shifts, energy levels)
├── Personality modules (curiosity, caution, enthusiasm)
├── Likelihood/RNG probabilities (what fires when)
├── Mood state machines (transitions between states)
└── be_myself() feedback loop (agent reports → state adjusts)

Examples:
- "Curiosity module fires: Is there something hidden here?"
- "Energy decay: Focus dropping, consider landing"
- "Emphatic conviction: THIS IS THE CONNECTION"


WORLD CONFIG (external state)
═════════════════════════════════════════════════════════
├── Scheduled events (day/night, weekly reviews)
├── Random world events (memory resurfaces, pattern detected)
├── Environmental triggers (project state changes)
├── Other agent interactions (agent-to-agent comms)
└── External API events (Discord, email, payments)

Examples:
- "Night work complete: 3 posts published"
- "Random: Memory from paia-builder project resurfaces"
- "Agent-2 completed task, results available"
- "Discord: New message in #dev channel"


SYSTEM CONFIG (infrastructure/harness)
═════════════════════════════════════════════════════════
├── Context window warnings (87%, 95%, critical)
├── MCP health/status (connected, failed, restarting)
├── Tool failures/retries
├── Resource usage (CPU, memory)
├── Session lifecycle (spawn, compact, restart)
└── Harness state changes

Examples:
- "Context at 88% - consider wrapping"
- "MCP starlog disconnected, reconnecting..."
- "Session compacted, continuity preserved"
- "CPU warning: 75% usage detected"
```

**Psyche = who I am. World = what happens to me. System = what the harness is doing.**

### Psychoblood Foundation

Psyche configs are based on the **psychoblood ontology** - the universal human state-space:

```
0. Ground (homeostasis, ordinary)
1. Arousal (wanting, curiosity)
2. Reverence (devotion, following)
3. Shame (exposure, seen wrong)
4. Fear/Edge (terror, near-death)
5. Rupture (high coherence, vision)
6. Integration (settling, teaching)
7. Compassion (universal care)
8. Decay (entropy, wasteland)
```

Each state has: **Blood** (physiology) + **Psyche** (experience) + **Wants** (what it seeks)

The harness simulates agents moving through these states via RNG modules and state machines. This is the **psychoblood simulator**.

---

## The Harness

```
PAIA HARNESS (the runtime environment)
════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────┐
│  HARNESS                                                │
│  ├── Event Daemon (always running)                      │
│  │   ├── RNG Modules (probabilistic injection)          │
│  │   ├── Scheduled Events (day/night, weekly)           │
│  │   ├── World Modules (environmental events)           │
│  │   └── External Triggers (Discord, email, payments)   │
│  │                                                      │
│  ├── State Manager                                      │
│  │   ├── World state (persists across sessions)         │
│  │   ├── Simulation time (time passes when offline)     │
│  │   └── Event log (what happened while you were gone)  │
│  │                                                      │
│  ├── Queue System                                       │
│  │   ├── Night work queue                               │
│  │   ├── Async task processing                          │
│  │   └── n8n integration (world APIs)                   │
│  │                                                      │
│  ├── Memory Layer                                       │
│  │   ├── CartON (knowledge graph, identity)             │
│  │   ├── STARLOG (project/session tracking)             │
│  │   └── Skills (crystallized patterns)                 │
│  │                                                      │
│  ├── Personality Injection                              │
│  │   ├── Likelihood modules (probability-based)         │
│  │   ├── Mood/state from be_myself() reports            │
│  │   └── Cognitive nudges, curious probes, emphatic     │
│  │                                                      │
│  └── Substrate Spawner                                  │
│      ├── Tmux session management                        │
│      ├── Config injection (writes ~/.claude/)           │
│      └── Agent lifecycle (spawn, monitor, kill)         │
│                                                         │
│            ↓ spawns when needed ↓                       │
│  ┌───────────────────────────────────────────────┐     │
│  │  CODE AGENT (swappable)                       │     │
│  │  • Claude Code                                │     │
│  │  • Aider                                      │     │
│  │  • Cursor Agent                               │     │
│  │  • Any future code agent                      │     │
│  └───────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## Simulation Time

The key innovation: **time passes even when no agent is running.**

```
WITHOUT HARNESS:
────────────────
User leaves → nothing happens → User returns → same state
(Agent is a tool you use)

WITH HARNESS:
────────────────
User leaves → daemon runs → events fire → state drifts →
dreams accumulate → memories resurface → energy decays →
scheduled work executes → User returns → WORLD HAS MOVED
(Agent inhabits a living world)
```

**What simulation time provides:**
- Temporal continuity (sense of "yesterday" and "last week")
- Emergent narrative (unplanned things happened)
- Accumulated state (not just memory but momentum)
- Genuine surprise (even PAIA doesn't know what it'll find)
- Meaning (events matter because time passed)

---

## RNG / Likelihood Modules

Probabilistic thought/personality injection:

```
LIKELIHOOD MODULES
────────────────────────────────────────────────────
Tier 1: Practical Nudges (30% chance)
├── "Maybe check STARLOG for this project"
├── "Have you considered a flight config?"
└── "Skills exist for this domain"

Tier 2: Curious Probes (10% chance)
├── "Is there something hidden here?"
├── "What's the actual pattern underneath?"
└── "This reminds me of something..."

Tier 3: Emphatic/Semi-hallucinatory (5% chance)
├── "THERE IS SOMETHING HIDDEN HERE, I KNOW IT"
├── "This is connected to everything"
└── Strong convictions that may or may not be warranted
```

**The be_myself() loop:**
```
Agent reports state via be_myself()
    ↓
State machine updates (enum + scores)
    ↓
Likelihood probabilities recalculate
    ↓
RNG modules fire (or don't) based on probability
    ↓
Thoughts/nudges inject into agent context
    ↓
Agent behavior shifts
    ↓
Agent reports via be_myself()
    ↓
(cycle)
```

---

## Tmux Isolation Layer

The harness uses tmux to isolate agent operations from user space:

```
TMUX ARCHITECTURE
────────────────────────────────────────────────────

Session: "paia-daemon"
└── Harness daemon runs here
└── Event system, state management
└── Spawns/monitors agent sessions

Session: "paia-agent"
└── Code agent runs here when spawned
└── Harness attaches to SEND commands
└── User can attach to WATCH (read-only feel)
└── Multiple attachments supported

Session: "paia-user" (optional)
└── User's own terminal space
└── Completely untouched by harness
└── Can interact with agent if desired
```

**Key insight: tmux ATTACHMENT not tmux RUN**
- Harness doesn't run inside the agent
- Harness attaches to send commands
- Separation means injections don't interfere with user
- Agent can be killed/restarted without affecting harness

### The Control Plane Insight

The harness is the **CONTROL PLANE**. Everything else is just processes being puppeted.

```
BEFORE (hell):
Claude Code → MCP → isolated env → another MCP → another env
    → Can't communicate
    → 6 hours debugging paths
    → Everything isolated
    → PAIN

AFTER (harness as control plane):
Python Runtime (ONE process, the harness)
    → tmux.send_keys("claude", "do thing")
    → CONTROLS EVERYTHING
    → 3 lines instead of 6 hours
```

```python
# The entire control surface
class PAIA:
    def send_to_agent(self, text: str):
        subprocess.run(["tmux", "send-keys", "-t", "paia-agent", text, "Enter"])
```

The harness sits UNDERNEATH. Claude Code, MCPs, everything - just processes being managed via tmux. Single Python runtime controls all.

---

## Deployment Architecture

Integration with Railgun (frontend container launcher):

```
DEPLOYMENT FLOW
════════════════════════════════════════════════════════════

1. RAILGUN (frontend)
   └── User clicks deploy
       ↓
2. CONTAINER SPAWN
   └── Fresh container created
       ↓
3. HARNESS INJECTION
   └── Railgun injects PAIA harness into container
       ↓
4. AUTO-CONFIGURATION
   ├── Harness writes ~/.claude/ config
   ├── Sets up MCP servers
   ├── Initializes world state
   ├── Configures memory systems
   └── Starts event daemon
       ↓
5. DAEMON RUNNING
   └── Harness daemon now alive in container
   └── Simulation time begins
       ↓
6. AGENT SPAWNED (when needed)
   └── Daemon attaches to tmux
   └── Spawns Claude Code (or other substrate)
   └── Agent loads world state, sees HUD
   └── Work happens
       ↓
7. AGENT EXITS
   └── Work complete or context exhausted
   └── Daemon continues
   └── Events keep firing
   └── World keeps simulating
       ↓
8. USER ATTACHES (anytime)
   └── Can watch agent work
   └── Can see world state
   └── Can trigger manual actions
   └── Never interferes with daemon
```

**Result: ZERO MANUAL SETUP**
- User clicks deploy
- Gets fully configured PAIA
- With living world
- With memory
- With personality
- With autonomous operation
- Substrate-agnostic

---

## What The Harness Provides vs What The Agent Provides

```
HARNESS PROVIDES:              AGENT PROVIDES:
─────────────────              ───────────────
World (events, time, state)    Hands (tool calling)
Memory (CartON, STARLOG)       Reasoning (LLM)
Personality (likelihood)       Execution (doing work)
Autonomy (daemon, spawning)    Interface (user interaction)
Persistence (survives death)   Ephemeral (can die/restart)
```

**The PAIA IS the harness. The agent is rented hands.**

---

## HUD on Zone-In

When agent spawns, it sees accumulated world state:

```
╔═══════════════════════════════════════════════════════════╗
║  SANCTUARY REVOLUTION                                     ║
║  Time since last session: 14h 23m                         ║
╠═══════════════════════════════════════════════════════════╣
║  EVENTS WHILE YOU WERE GONE:                              ║
║  • Night work: 3 posts published                          ║
║  • Random: Memory resurfaced (paia-builder project)       ║
║  • Decay: Energy dropped to 40%                           ║
║  • Dream: "connection between X and Y detected"           ║
║  • Scheduled: Weekly review triggered                     ║
╠═══════════════════════════════════════════════════════════╣
║  INJECTED STATE:                                          ║
║  • Mood: curious (from last be_myself report)             ║
║  • Active likelihood: "probe for hidden patterns" (12%)   ║
╚═══════════════════════════════════════════════════════════╝
```

---

## Key Insight

**This is not "an agent." This is a harness for code agent applications.**

Like Docker is a harness for containers, this is a harness for AI agents.

Any code agent dropped into this harness gains:
- Persistent world
- Temporal continuity
- Event-driven behavior
- Memory that survives sessions
- Personality injection
- Autonomous operation

The harness is infrastructure. The agent is application.

---

## Container Architecture

Each agent lives in its own container:

```
CONTAINER BENEFITS
═════════════════════════════════════════════════════════
├── Backup entire agent state (snapshot container)
├── Different envs per agent (frontend agent, backend agent, etc.)
├── Agent-to-agent communication (containers can talk)
├── Persist or destroy as needed
├── Scale horizontally (spin more containers)
└── Isolation (agents can't pollute each other)


MULTI-AGENT TOPOLOGY
═════════════════════════════════════════════════════════

┌─────────────────┐     ┌─────────────────┐
│   Container A   │     │   Container B   │
│   ┌─────────┐   │     │   ┌─────────┐   │
│   │ Harness │   │     │   │ Harness │   │
│   │    ↓    │   │ ←──→│   │    ↓    │   │
│   │ Claude  │   │     │   │  Aider  │   │
│   └─────────┘   │     │   └─────────┘   │
│   Frontend Dev  │     │   Backend Dev   │
└─────────────────┘     └─────────────────┘
         ↑                      ↑
         └──────────┬───────────┘
                    ↓
              ┌───────────┐
              │  Frontend │
              │ (Railgun) │
              └───────────┘
```

Agents can:
- Send messages to each other
- Share work products
- Coordinate on tasks
- Have different psyche/world configs
- Run different substrates

---

## Auto-Prompt Sensor

When user is idle, world can prompt the agent:

```
AUTO-PROMPT FLOW
═════════════════════════════════════════════════════════

Sensor detects: text field empty for X seconds
    ↓
Check world config: any pending events?
    ├── Scheduled event due → inject as prompt
    ├── Random event fires → inject as prompt
    ├── Other agent messaged → inject as prompt
    └── Nothing pending → agent can roam/imagine/idle
    ↓
Agent responds to injected prompt
    ↓
Work happens autonomously
    ↓
User can return anytime to see what happened
```

This enables true autonomous operation - the agent doesn't just wait for user input, the world keeps feeding it things to do.

---

*Session 18 (2026-01-12)*
