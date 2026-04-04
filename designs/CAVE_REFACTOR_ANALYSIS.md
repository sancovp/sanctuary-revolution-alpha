# CAVE Library Refactor Analysis v2

> Updated after reading Conductor code. The root cause is clear now.

---

## The Root Problem

**CAVE has no ChatAgent type. So Conductor was built as a 500-line standalone hack that bypasses all CAVE infrastructure (channels, inbox, routing) and hardcodes Discord directly.**

To make Autobiographer, you'd have to copy-paste all 500 lines and change the prompt. That's the tax.

---

## What's Wrong — File by File

### 1. agent.py — Missing Types

**Has:** [CodeAgent(Actor)](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/agent.py#125-432) with inbox + tmux  
**Missing:** [Agent](file:///Users/isaacwr/.gemini/antigravity/scratch/agent-control-panel/src/services/harnessService.ts#736-742) base, `ChatAgent`, `ClawAgent`

The inbox (deque, enqueue, dequeue, priority) is on CodeAgent. Per design, inbox should be on ChatAgent, and CodeAgent should add tmux on top.

```
CURRENT:                        NEEDED:
CodeAgent(Actor)                Agent (base, inbox)
  └── ClaudeCodeAgent             ├── ChatAgent (channels)
                                  │     └── config: channel, heartbeat, etc.
RemoteAgent (standalone)          ├── CodeAgent(ChatAgent) (+ tmux)
                                  │     └── ClaudeCodeAgent
                                  └── ClawAgent (external, just pipe)
```

### 2. conductor.py — Should Not Exist As-Is

**Has:** 500 lines of hand-wired harness:
- Creates disposable `BaseHeavenAgent` per message
- Manages own history persistence
- Manages own compaction  
- Manages own context overflow
- Hardcodes [UserDiscordChannel()](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/channel.py#42-87) for notifications
- Hardcodes `_chunk_for_discord()`
- Has its own `DiscordEventForwarder` callback

**Should be:** A method on CAVEAgent, or better: the logic that ChatAgent provides.

The pattern in Conductor IS what ChatAgent should be:
- Take a message → create agent → run → get response → return
- History management
- Compaction
- Context overflow handling
- Event emission (NOT Discord-specific)

### 3. channel.py — Channels Not Connected To Agents

**Has:** Channel types (UserDiscord, AgentInbox, AgentTmux, SSE, Multi)  
**Problem:** Channels exist. Agents exist. They're not connected. 

No agent HAS channels. Channels are standalone objects. When Conductor needs Discord, it creates [UserDiscordChannel()](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/channel.py#42-87) directly instead of asking CAVE "send this through my configured channel."

### 4. http_server.py — Creates Its Own CAVEAgent

**Has:**
```python
cave: CAVEAgent = None  # global
@app.on_event("startup")
async def startup():
    global cave
    cave = CAVEAgent(CAVEConfig.load())  # inverted ownership
```

**Should be:** A FACADE. Every route calls one method on CAVEAgent.

```python
class CAVEHTTPServer:
    def __init__(self, port: int, cave_agent: CAVEAgent):
        self.cave = cave_agent  # passed IN, not created
```

### 5. remote_agent.py — One-Shot Wrapper, Not Configurable

**Has:** Fire-and-forget SDNA one-shot call
**Should be:** Configurable agent that exposes SDNA/Heaven patterns

### 6. config.py — Only Knows About ONE Agent

**Has:** `main_agent_config: MainAgentConfig` — singular  
**Missing:** `agents: List[AgentConfig]` — multiple agents with types

### 7. models.py — Agent Types Wrong

**Has:** `agent_type: Literal["paia", "worker", "ephemeral"]`  
**Should be:** `agent_type: Literal["chat", "code", "claw"]`

---

## Refactor Stages (Confirmed)

Each stage depends on the one before:

```
1. Inbox       → get the queue right (deque, priority, persist)
2. Channels    → bidirectional transport (add receive()), feeds inbox
3. Agents      → ChatAgent, CodeAgent, ClawAgent built on inbox + channels
4. Automation  → trigger (cron/event/manual) + process (func/agent/SOPHIA) + delivery (channel)
5. CAVEAgent   → wires N agents from config, generic registry
6. HTTPServer  → facade, every route = one method
```

### Stage 1: Inbox
- Inbox is a real queue (deque with priority, persist to disk)
- Inbox exists independently — channels FEED into it
- `inbox.enqueue(message)` / `inbox.dequeue()` / `inbox.peek()`
- Already partially exists on CodeAgent — may need extraction to standalone

### Stage 2: Channels
- Add [receive()](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/agent.py#367-371) to Channel ABC (currently only has [deliver()](file:///Users/isaacwr/.gemini/antigravity/scratch/cave_review/channel.py#158-171))
- Channel becomes bidirectional transport — input AND output
- **Channel ≠ inbox.** Channel FEEDS the inbox:
  ```
  channel.receive() → inbox.enqueue(message)
  ```
- Channel handles adapter (Discord API → string, string → Discord send)
- Agent only sees strings in, strings out
- 1 channel → auto-serve (dequeue immediately, process, respond)
- N channels → messages queue, agent checks on hook/heartbeat/cron

### Stage 3: Agents
- Agent base (has inbox)
- ChatAgent(Agent) — bound to channel(s), channel feeds inbox
  - 1 channel: auto-serve (feels direct)
  - N channels: auto-queue
  - Extract Conductor's pattern (BaseHeavenAgent-per-message, history, compaction, context overflow)
- CodeAgent(ChatAgent) — adds tmux
- ClawAgent(Agent) — external pipe, own config

### Stage 4: Automation
- **Automation = Trigger + Process + Delivery** — the fundamental unit
- Cron is a TRIGGER TYPE, not a separate concept
- Current [DeliveryTarget](file:///Users/isaacwr/.gemini/antigravity/scratch/sdna-fix/sdna/cron.py#52-94) should become a Channel (no duplication)

**Trigger (WHEN):**
  - `CronTrigger` → scheduled (cron expression)
  - `EventTrigger` → on event X
  - `WebhookTrigger` → on HTTP call
  - `ManualTrigger` → invoked explicitly (by user, by SOPHIA, by another automation)

**Process (WHAT):**
  - `code_pointer` → a function (module.func importlib)
  - agent → route to a ChatAgent's inbox
  - **SOPHIA** → the universal intelligent Process. Just say "call SOPHIA" and the bandit picks the right pipeline.

**Delivery (WHERE):**
  - Channel → any configured channel (Discord, SSE, file, webhook)

**SOPHIA Connection:**
SOPHIA (Compoctopus omnicompiler) IS the intelligent Process for Automations.
- SOPHIA builds agent systems for Triggers in Automations
- ManualTrigger = SOPHIA invokes it when you ask
- You can chain automations: "call SOPHIA → call SOPHIA → call SOPHIA..."
- SOPHIA's bandit router picks the right agent/pipeline each time

**TOOT — What It Actually Is (THE BREAKTHROUGH):**

TOOT is NOT a metaphor for the PLAN lane. It is a **specific reified operational thing**:

> **TOOT = SOPHIA's goldenized automations on any given day/week/schedule.**

The PLAN lane shows TWO kinds of work:

| Type | Source | How it runs | Example |
|------|--------|-------------|---------|
| **TOOT items** | SOPHIA built them, goldenized | Cron/schedule triggers | "Weekly progress review" pipeline that SOPHIA proved works |
| **Agent tasks** | User queued them | Heartbeat system, agents pull off TreeKanban | "Fix the login bug" — regular work |

TOOT evolution:
1. ~~Nothing burger (just a word)~~
2. ~~Metaphor for the PLAN lane~~
3. **Reified operational thing** — SOPHIA's goldenized automations, reified onto the human's schedule

**The Full TOOT Lifecycle:**
1. "Call the TOOT for X" → SOPHIA gets amorphous prompt X
2. SOPHIA calls itself at each step to figure out the chain:
   `sophia() → sophia() → sophia()...`
3. Chain works? Score is golden → SAVE as CronTrigger Automations
4. The resulting chain of automations IS a schedule of `sophia()` / `sophia(x)` calls
5. This schedule autopopulates the TreeKanban PLAN lane each day
6. You don't control it — it feeds itself in
7. The PLAN lane shows TOOT items alongside your regular agent tasks
8. TOOT items run themselves. Agent tasks get pulled by heartbeat. Both show on PLAN lane.

The Train of Operadic Thought = the self-creating schedule of goldenized automations.
SOPHIA bootstraps. Golden chains crystallize. TOOT grows autonomously alongside regular work.

### Stage 5: CAVEAgent
- `agents: List[AgentConfig]` in config (not just `main_agent_config`)
- CAVEAgent.__init__ reads config, creates right agent type for each
- Generic registry, not hardcoded slots

### Stage 6: HTTPServer
- `CAVEHTTPServer(port, cave_agent)` — takes agent IN
- FACADE: every route calls one method on cave_agent
- No business logic in routes
- No global [cave](file:///Users/isaacwr/.gemini/antigravity/scratch/agent-control-panel/backend/orchestrator/server.py#784-919) variable

---

## Key Questions For User

1. **Does inbox stay on Agent base, or does it go on ChatAgent only?**
   - If Agent base: every agent type has an inbox
   - If ChatAgent only: CodeAgent gets inbox through ChatAgent inheritance, ClawAgent has no inbox

2. **Does the BaseHeavenAgent-per-message pattern stay?**
   - Creating a new agent per message is how Conductor works now
   - Is this the right pattern for ChatAgent, or should it be persistent?

3. **What happens with the existing Conductor code?**
   - Delete it and rebuild as ChatAgent(config)?
   - Or extract the pattern into ChatAgent and keep Conductor as thin config?

4. **Does CAVE need to handle Discord chunking (2000 char limit)?**
   - Or is chunking a Discord channel concern (Channel.deliver handles it)?

5. **Where does compaction logic live?**
   - On ChatAgent (every chat agent compacts)?
   - Or configurable per agent?

---

## What's Right (Don't Touch)

- ✅ Mixin onion pattern in CAVEAgent
- ✅ Heart rhythm system
- ✅ Hook router
- ✅ Automation/cron framework
- ✅ SSE events
- ✅ File-based inbox persistence
- ✅ HTTP route patterns (clean passthrough)
- ✅ Conductor's LOGIC (handle_message, compaction, context overflow) — just needs to be extracted
