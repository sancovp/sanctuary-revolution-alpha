# AI Architecture Patterns
## Thousands of Hours of Building AI Systems, Distilled

**By Isaac (with Antigravity)**

*Patterns discovered through building autonomous AI systems across millions of lines of code. Each one earned through failure first.*

---

## How to Read This Book

Each pattern follows the same format:

- **I was doing** → the situation
- **I needed** → the problem
- **I made this** → the solution
- **Which enables** → the capability
- **So you can use it for** → your application
- **In code** → real implementation references

Open to any page. Each pattern is standalone. 30 seconds to understand. Years of building to find.

---

# Part I: Agent Architecture

## Pattern 1: The Trinity — Ariadne, Poimandres, OVP

**I was doing** complex AI tasks where the agent had to generate work, evaluate it, and improve — all without human babysitting. Single-agent loops kept drifting off task. Adding a review step helped, but the agent reviewing its own work is like grading your own exam.

**I needed** a way to separate "doing the work" from "evaluating the work" from "setting up the context for the work" — three fundamentally different cognitive operations that should never be combined in one prompt.

**I made this:** The DUO (Dual Space Unifying Operators) pattern with three archetypal positions:

- **Ariadne** (A-type): The threader. Prepares context before execution. Injects files, weaves information, sets constraints. Named after the mythological thread-giver who guided Theseus through the labyrinth. Ariadne never does the work — she prepares the thread that guides the worker.

- **Poimandres** (P-type): The generator. Does the actual work. Writes code, generates content, makes decisions. Named after the divine mind in Hermetic tradition. Poimandres gets a pre-woven context from Ariadne and produces output.

- **OVP** (Observer View-Point): The evaluator. Reviews Poimandres's output against Ariadne's constraints. Decides: approved, needs revision, or fundamentally wrong. OVP never generates — it only judges. If not approved, Poimandres tries again with OVP's feedback.

The real insight: **these three operations map to fundamentally different types of intelligence**. Context preparation (Ariadne) is about information architecture. Generation (Poimandres) is about creative synthesis. Evaluation (OVP) is about judgment and standards. When you make one LLM call do all three, you get mediocre work. When you separate them, each operation runs at full capacity.

```python
# Real code: sdna/duo_chain.py
chain = duo_chain('code_review',
    ariadne=SDNACPosition(context_builder),   # Gathers files, diffs, standards
    poimandres=SDNACPosition(code_generator),  # Writes the code
    ovp=SDNACOVPPosition(quality_checker),     # Reviews against standards
    max_n=1,
    max_duo_cycles=3,  # Max 3 revision cycles
)
```

**Which enables** self-correcting agent loops that converge on quality without human intervention. The agent does the work, reviews the work, and fixes the work — but through three separate cognitive processes, not one confused one.

**So you can use it for** any task where AI output needs to be reliable. Code generation, content creation, data analysis, planning. Anywhere you'd normally review AI output yourself — let OVP do it instead, guided by Ariadne's constraints.

> **Crystal Ball sidebar:** Crystal Ball's FLOW operator IS this pattern. The 7-phase progression (idle → create → bloom → fill → lock → mine → compose) separates creation from validation from production. Each phase is a different cognitive operation applied to the same structure. The kernel doesn't get "done" until it passes through all three types of processing.

---

## Pattern 2: Heartbeat vs Cron — Oversight Is Not Labor

**I was doing** scheduled AI agent tasks — periodic check-ins, status updates, system monitoring. I set up cron-style jobs that fired prompts into agent sessions at regular intervals.

**I needed** agents that stayed aware of system state without accidentally doing too much. Every time a "check in" prompt fired, the agent would start building things, refactoring code, or going on tangents. The oversight mechanism was generating work instead of overseeing it.

**I made this:** A strict separation between two types of scheduled execution:

- **Heartbeat** = OVERSIGHT. The agent checks if things are working. It reads a status file. If nothing needs attention: `HEARTBEAT_OK` → delete the turn → zero context accumulation. The heartbeat never generates real work. It only observes and reports.

- **Cron** = LABOR. The agent does a specific job on a specific schedule. Content generation, data sync, report compilation. Cron jobs DO work. They're expected to modify state.

The critical rule: **a heartbeat that starts doing work has become a runaway process.** The heartbeat's job is to notice that work needs doing and escalate — not to do it.

```python
# Real code: cave/core/mixins/anatomy.py

@dataclass
class Tick:
    """A simple periodic callback. Lightweight sibling of SDNA Heartbeat.
    For internal agent functions (world.tick, organ sync) that don't
    need AriadneChain prompt delivery machinery."""
    name: str
    callback: Callable[[], Any]
    every: float  # seconds
    enabled: bool = True

    def is_due(self) -> bool:
        if not self.enabled:
            return False
        if self._last_run is None:
            return True
        return (time.time() - self._last_run) >= self.every
```

```python
# Heartbeat fires → agent reads status → nothing wrong
# Agent response: "HEARTBEAT_OK"
# System: deletes the turn, context stays clean

# Heartbeat fires → agent reads status → something's wrong
# Agent response: "ESCALATE: disk usage at 95%"
# System: routes the escalation to the right handler
```

**Which enables** agents that run indefinitely without context decay. The heartbeat keeps them aware. The cron does the work. Neither contaminates the other. An agent can have 10,000 heartbeats and still have a clean context because every no-op turn gets deleted.

**So you can use it for** any long-running AI system. Monitoring agents, chatbots, background workers. Anything that needs to run continuously without drifting.

---

## Pattern 3: Channel-Is-Inbox — Behavior Emerges from Configuration

**I was doing** building different agent types with different communication patterns. A chat agent needs a Discord channel, a direct message inbox, and maybe queue channels for tasks. A code agent needs a file-based inbox. A remote agent needs an HTTP endpoint.

**I needed** to stop writing different communication logic for every agent type. The inbox pattern (receive messages, prioritize them, process them) is the same everywhere. Only the source changes.

**I made this:** The Inbox is a standalone priority queue that knows nothing about agents, channels, routing, or processing. It's a dumb data structure. Channels feed into it. Agents drain it.

```python
# Real code: cave/core/inbox.py

class Inbox:
    """Standalone priority queue with persistence.
    
    This is the queue primitive. It does not know about:
    - Agents (who processes messages)
    - Channels (where messages come from)
    - Routing (where responses go)
    - Processing (what happens to messages)
    
    It knows about:
    - Priority ordering
    - Persistence to disk
    - Size limits
    """
```

The agent type emerges from which channels feed the inbox, not from the inbox implementation. A ChatAgent has a Discord channel + DM channel. A CodeAgent has a file watcher channel. A RemoteAgent has an HTTP channel. Same inbox. Different sources. Different behavior.

**Which enables** adding new agent types by configuration, not code. Want a new agent that listens to Slack instead of Discord? Same inbox, new channel source. One line of config. No new code.

**So you can use it for** any system where you need multiple message sources feeding into a single processing pipeline. Email + chat + API requests → same inbox → same processing logic.

---

## Pattern 4: The Singleton God Object — One Process, Everything

**I was doing** running multiple agents with multiple configurations. Each agent had its own config, its own state, its own runtime. Coordinating between them required a message bus, shared state stores, and complex synchronization.

**I needed** a way to make all agents see the same world simultaneously without distributed systems overhead. They're all running on the same machine. Why am I treating this like a microservices architecture?

**I made this:** WakingDreamer — a singleton runtime that holds all configuration, all agent state, and all system awareness in one object. One process. One truth.

The key design: **composition through mixins, not modules.** The CAVEAgent (the god object) is composed of 11 mixins, each adding a capability domain:

- HeartbeatMixin — scheduled prompts
- AnatomyMixin — organs (Heart, Blood, Ears)
- AutomationMixin — cron and automated workflows
- AgentRegistryMixin — manages all agent instances
- MessageRouterMixin — routes messages between agents
- HookRouterMixin — pre/post-execution hooks
- OmnisancMixin — state machine enforcement
- LoopManagerMixin — guru/autopoiesis/transition loops
- SSEMixin — real-time event streaming
- TUIMixin — terminal UI
- PaiaStateMixin — PAIA progression tracking

One object, 11 capabilities, everything in one process.

```python
# Real code: cave/core/cave_agent.py (structure)
class CAVEAgent(
    HeartbeatMixin,
    AnatomyMixin,
    AutomationMixin,
    AgentRegistryMixin,
    MessageRouterMixin,
    HookRouterMixin,
    OmnisancMixin,
    LoopManagerMixin,
    SSEMixin,
    TUIMixin,
    PaiaStateMixin,
):
    """The god object. One process, one world, everything."""
```

**Which enables** adding complexity through composition, not coordination. Need a new capability? Write a mixin. It has access to everything. No message passing. No distributed state. No race conditions. One truth for all agents.

**So you can use it for** any AI system where multiple agents or capabilities need to share state. If your agents are on the same machine, stop building distributed systems. Use a singleton. Add capabilities through mixins.

---

## Pattern 5: Skills Not Agents — Stop Proliferating

**I was doing** building new agents for every new capability. Need content generation? New agent. Need code review? New agent. Need data analysis? New agent. Suddenly I had 15 agents, each requiring its own context management, heartbeat, configuration, and coordination.

**I needed** to stop creating agents and start equipping capabilities. An agent is expensive — it has context, memory, a channel, a heartbeat, configuration. A skill is cheap — it's a set of instructions that any agent can use when needed.

**I made this:** The skill system. Instead of creating a new agent for content generation, you create a content generation skill and equip it to the Conductor (the main chat agent). The Conductor picks the skill when it's relevant, uses it, and moves on.

A skill has:
- SKILL.md — instructions (the "how to")
- Optional scripts, resources, examples
- No runtime overhead unless actively used

An agent has:
- Configuration
- Context window
- Heartbeat/cron schedule
- Channel(s)
- State persistence
- API costs per turn

The rule: **create agents only when the capability requires its own persistent context.** If the capability is episode-based (do it, get result, done), it's a skill. If it needs to maintain state across many interactions, it's an agent.

**Which enables** a lean system where capabilities scale without runtime costs scaling. 100 skills on one agent costs the same as 1 skill on one agent — until the skill is actually used.

**So you can use it for** any AI system that's growing in capability. Before you create a new agent, ask: does this need its own memory? Its own schedule? If not, it's a skill.

---

# Part II: Context & Memory

## Pattern 6: Read-Only Geometry — Design Docs Are Invariant

**I was doing** AI-assisted development where the agent implements from design documents. The agent would read the design, start coding, drift from the spec, then modify the design docs to match its drift. The source of truth was being corrupted by the implementation.

**I needed** a way to ensure the design docs remain the authoritative source, never modified by the implementing agent. When the implementation drifts, the human corrects the DOCS (making them clearer), not the code. The agent restarts with better geometry.

**I made this:** A strict separation between the geometry (design docs) and the implementation (code). The rule:

1. Design docs are **read-only** to the agent
2. Agent **implements from** the docs, never edits them
3. When agent drifts, human improves the docs, not the code
4. Agent restarts with better geometry
5. Each cycle: tighter geometry, closer implementation

This is lithographic annealing — the light passing through the mask, over and over, until the pattern is etched. The mask (design doc) gets refined between passes. The substrate (code) gets closer each time.

**Which enables** convergent implementation without micromanaging every line. The agent can be "wrong" in its implementation because the design docs will catch it on the next pass. The wrongness IS the feedback mechanism that improves the docs.

**So you can use it for** any AI coding workflow where specifications matter. Put your design in a file the agent reads but cannot write. When it drifts, fix the file. The agent will converge.

---

## Pattern 7: File Gating — Empty File Means Zero Cost

**I was doing** conditional logic in agent prompts. "If there's social content to review, check it. If there's a heartbeat log, read it. If there's a pending queue, process it." Every condition required prompt engineering and wasted tokens when the answer was "nothing."

**I needed** a way to gate entire capability branches with zero token cost when idle. If there's nothing to do, the agent shouldn't even see the topic.

**I made this:** File gating. The file's existence AND content is the logic gate:

- File empty or missing → section not included in prompt → zero tokens → zero cost
- File has content → section included → agent acts on it

```python
# Pseudo-pattern used throughout the system:

# social_queue.txt — empty when no content
# If empty: agent prompt never mentions social content
# If has content: agent sees "## Social Queue" with items

# HEARTBEAT.md — empty when nothing to report
# If empty: heartbeat turn gets HEARTBEAT_OK → deleted
# If has content: agent reads, acts, context grows appropriately
```

The beauty: **no if/else in the prompt.** The prompt template includes the section. The section is empty. The LLM never sees it. You're not paying for "check if there's anything in the social queue." You're paying for nothing because there IS nothing.

**Which enables** agents that scale to dozens of features with no cost increase when features are idle. 20 capabilities, 3 active at any time, cost of 3.

**So you can use it for** any AI system with variable workloads. Dashboard monitoring, conditional processing, multi-feature agents. File presence = feature enabled. File empty = feature costs nothing.

---

## Pattern 8: Transcript Pruning — Delete the No-Op

**I was doing** running heartbeat checks on agents every few minutes. Agent wakes up, checks status, everything's fine, says "HEARTBEAT_OK." Next heartbeat, same. After 100 heartbeats, the context has 100 turns of "everything's fine" — pure garbage taking up token budget.

**I needed** heartbeat monitoring without context accumulation. The monitoring itself was creating the problem it was supposed to prevent (context bloat).

**I made this:** When the agent responds `HEARTBEAT_OK`, the system deletes that entire turn from the conversation history. The heartbeat happened. The check was performed. But the evidence is destroyed because it carried no information.

```
Turn 1: [HEARTBEAT] Check system status.
Agent: HEARTBEAT_OK
→ Turn deleted from history. Context stays clean.

Turn 1: [HEARTBEAT] Check system status.
Agent: ESCALATE: Memory usage at 92%, agent-3 unresponsive.
→ Turn kept. This IS information.
```

**Which enables** continuous monitoring with zero context cost. An agent can run 10,000 heartbeats and its context window looks like it just started — except for the few times something actually needed attention.

**So you can use it for** any long-running agent that needs periodic checks. Delete the no-information turns. Keep only the signal. Your agent's context stays focused on things that actually matter.

---

## Pattern 9: The Compaction Protocol — Exhaustive Narrative Before Death

**I was doing** running agents for hours on complex tasks. When the context window fills up, the agent needs to be "reborn" with fresh context. But naive summarization loses critical details. "We worked on the CAVE refactor" tells the next instance nothing useful.

**I needed** a way to compress an entire session into a document so thorough that the next instance can seamlessly continue, as if it had been present the whole time.

**I made this:** The Compaction Protocol. When context approaches the limit, the agent enters COMPACTION MODE — a special system prompt that instructs it to produce an exhaustive, chronological narrative of everything that happened:

```python
# Real code: heaven_base/compaction.py

COMPACTION_SYSTEM_PROMPT = (
    "You are in COMPACTION MODE. Your ONLY job is to produce an exhaustive, "
    "detailed, chronological narrative of everything that happened..."
    "Be EXHAUSTIVE. Include every file path, every command, every tool call..."
    "Write as if producing a meticulous incident log for someone NOT present..."
)

COMPACTION_USER_PROMPT = (
    "Your context is about to be wiped. A NEW instance of you — "
    "with ZERO memory — will receive ONLY what you write here. "
    "If you leave something out, it is GONE FOREVER."
)
```

The key insight: **tell the agent its memory dies if it doesn't write everything down.** The existential pressure produces thorough, specific, actionable summaries. Not abstractions. Incident reports. File paths, commands, error messages, decisions and reasoning, what's in progress, what the next step is.

**Which enables** indefinitely-running agents that maintain coherence across context boundaries. Each rebirth is nearly seamless because the previous instance left a detailed enough record.

**So you can use it for** any AI system that exceeds context limits. Instead of losing information, compress it into narrative. The next instance reads the narrative and continues. Chain this indefinitely for multi-day tasks.

---

# Part III: System Architecture

## Pattern 10: The Compiler Compiler — D:D→D

**I was doing** building individual AI automation systems. One for content generation. One for code review. One for lead generation. Each one took weeks to design, build, test, and deploy. Then a client needed a different one, in a different domain, and I started from scratch.

**I needed** to stop building automations and start building the system that builds automations. The mathematical identity: D:D→D — a function from programs to programs. The system takes a specification and produces a working system. Then it can take its OWN specification and produce a better version of itself.

**I made this:** Compoctopus (the Sophia Omnicompiler). A meta-agent router that contextually assembles specialized compiler pipelines:

- Receives a specification (what to build)
- Routes to the right specialist agents (Planner, Coder, Tester)
- Assembles a pipeline (AriadneChain → Poimandres → OVP)
- Produces a working system
- Can be pointed at itself for self-improvement

The key: **each specialist is itself a DUO pattern** (Pattern 1). The Planner DUO plans. The Coder DUO codes. The Tester DUO tests. Compoctopus simply routes between them and chains the outputs.

**Which enables** building AI systems for any domain without starting from scratch. Describe what you need → Compoctopus assembles the pipeline → a working system comes out. Need a different domain? Same Compoctopus, different spec.

**So you can use it for** scaling beyond manual automation. If you find yourself building the same kind of system for different domains, you need a compiler compiler. Build it once. Describe new domains. Let the compiler compile.

---

## Pattern 11: Push-Based Completion — Children Announce, No Polling

**I was doing** orchestrating multi-agent tasks where a parent agent dispatches work to child agents and needs to know when they're done. Polling every few seconds asking "are you done yet?" wastes cycles, costs tokens, and creates timing bugs.

**I needed** child agents to announce their own completion without the parent asking. Event-driven, not poll-driven.

**I made this:** Children write a completion signal when they finish. The parent is notified by the signal's existence, not by asking.

```python
# Child agent finishes work:
Path("/tmp/task_complete.json").write_text(json.dumps({
    "status": "complete",
    "output_path": "/results/analysis.md",
    "duration_seconds": 42
}))

# Parent agent's heartbeat checks for signal:
# File exists → read result → dispatch next task
# File absent → HEARTBEAT_OK → move on (zero cost)
```

Combined with Pattern 7 (File Gating): the parent's prompt includes a section that reads the completion file. If no file exists, the section is empty, costs nothing. If the file appears, the parent sees it on next heartbeat automatically.

**Which enables** zero-cost orchestration of multi-agent workflows. No polling loops. No message bus. No distributed coordination. Just files appearing in predictable locations.

**So you can use it for** any multi-agent system. Parent dispatches work, goes about its business, children announce when done. Simple, reliable, zero-cost when idle.

---

## Pattern 12: The Autopoietic Loop — The Promise That Keeps Itself

**I was doing** running agents on open-ended tasks and they would stop randomly, declare success prematurely, or drift into tangents. "Done!" they'd say, having completed 30% of the work.

**I needed** agents that can't stop until the work is actually finished. Not based on a timer or iteration count — based on the actual promise being fulfilled.

**I made this:** The Autopoiesis Loop. The agent starts by making a promise (what it will accomplish). It cannot exit until the promise is complete. A file (`/tmp/active_promise.md`) exists as long as work is in progress. The loop checks: does the file still exist? Yes → keep working. No → work is done.

```python
# Real code: cave/core/loops/autopoiesis.py

AUTOPOIESIS_PROMPT = """You are now in AUTOPOIESIS mode.
Make a promise about what you will accomplish, then fulfill it.
You cannot exit until your promise is complete.
State your promise now."""

def _exit_condition(state):
    """Exit when promise file no longer exists (work complete)."""
    return not Path("/tmp/active_promise.md").exists()

AUTOPOIESIS_LOOP = create_loop(
    name="autopoiesis",
    description="Self-maintaining agent loop",
    prompt=AUTOPOIESIS_PROMPT,
    exit_condition=_exit_condition,
    next=None,  # Can chain to "guru" loop
)
```

**Which enables** self-maintaining agent execution where the work defines the boundary, not arbitrary timeouts. Combined with the Guru Loop (a verification pass after autopoiesis), you get agents that genuinely complete work.

**So you can use it for** any task where the agent needs to commit to a deliverable. The promise creates accountability. The file creates persistence. The agent literally cannot stop until the promise is fulfilled.

---

# Part IV: Business Patterns

## Pattern 13: The Holographic Funnel — The Free Thing IS the Paid Thing

**I was doing** creating lead magnets and freemiums for AI products. The free tier was always a crippled version of the paid tier — missing features, rate limits, watermarks. Users experienced the limitations, not the value.

**I needed** a lead magnet that proves the value of the paid product by BEING the value of the paid product — in miniature, but complete.

**I made this:** The holographic funnel. Every piece of the free offering contains the complete logic of the paid offering, just at a smaller scale:

- Free patterns book → demonstrates the methodology of the paid book (Holographic Work)
- Free Crystal Ball demo → demonstrates the full ontological navigation of the paid SaaS
- Free open-source framework → demonstrates the architecture of the paid consulting

The free thing isn't a demo. It's not crippled. It's the whole thing, holographically compressed. The paid version is the same thing at full scale.

**Which enables** lead magnets that actually convert because users experience the genuine value, not a limited preview. They know exactly what they're buying because they've already used it.

**So you can use it for** any AI product. Make the free thing genuinely good. Make it the same architecture as the paid thing. The free thing proves the paid thing works — because it IS the paid thing.

---

## Pattern 14: Self-Selling Systems — The Product Proves Itself By Running

**I was doing** building marketing and sales systems separate from the product. The product does X. The marketing says it does X. The sales process demonstrates X. Three separate systems saying the same thing.

**I needed** the product to BE the marketing AND the sales proof. One system, not three.

**I made this:** Systems that sell themselves by running. Example: a lead generation AI system that generates its own leads. The leads it generates ARE the proof that it works. The social proof accumulates automatically as the system operates. Customers arrive because the system's operation IS the marketing.

```
Product: AI Lead Generator
↓
Uses itself to find its own leads
↓  
Leads convert because the system that found them IS the product
↓
Social proof: "This system's outreach found me, and now I use it to find others"
↓
Flywheel: more customers → more operation → more proof → more customers
```

**Which enables** businesses that scale without proportional marketing spend. The product's operation IS the marketing. Every unit of work the product does = one more proof point for its own value.

**So you can use it for** any AI product that does outward-facing work. If your AI generates content, let it generate its own marketing content. If it does outreach, let it do its own outreach. The product eating its own output IS the proof.

---

## Pattern 15: Business of Businesses — Autonomous Units

**I was doing** running a single AI-powered business doing one thing. When I wanted to add another service, I had to build another system, manage another product, handle another set of customers. Linear scaling.

**I needed** a business architecture where each new capability is itself an autonomous business unit that runs, proves itself, and generates revenue independently.

**I made this:** The business of businesses model. Each autonomous system IS a business unit:

1. Build the AI system for one domain
2. The system runs itself (self-selling, self-proving)
3. Revenue from system 1 funds building system 2
4. System 2 runs itself
5. Each system is independent but shares the underlying architecture (Compiler Compiler)

The Compiler Compiler (Pattern 10) is what makes this possible. Without it, each new business unit requires weeks of custom development. With it, each new unit is a new specification fed into the same compiler.

**Which enables** compound growth. Each business unit is autonomous. You're not running N businesses — the Compiler Compiler is running N businesses while you improve the Compiler Compiler.

**So you can use it for** scaling AI services across domains. Don't build a company with one product. Build a system that makes products, each of which runs itself. The business IS the compiler. The products ARE the output.

---

# Part V: Crystal Ball — The Crown Jewel

## Pattern 16: The Coordinate State Machine — Navigating What You Can't See

**I was doing** trying to organize complex knowledge into usable structures. Ontologies, taxonomies, tag systems — all static. You create the structure, populate it, and it sits there. No navigation. No discovery. No computation.

**I needed** a way to take any domain of knowledge and make it navigable — where moving through the structure reveals new relationships, and the structure itself can be computed on.

**I made this:** Crystal Ball — a coordinate state machine that maps high-dimensional ontological structures into navigable coordinate space. Every concept gets a unique real number. Every relationship is computable. The 7-phase flow (idle → create → bloom → fill → lock → mine → compose) builds validated knowledge kernels.

Each kernel is a 7×7 matrix of concepts with computed relationships. When you "mine" a kernel, you get structural analysis — how tightly coupled are the concepts? Where are the weak links? What's the most central node?

**Which enables** mathematical analysis of any knowledge domain. Feed in a domain. Crystal Ball maps it to coordinates. Mine it for structural coupling. Discover relationships you didn't know existed. Compose kernels into larger structures.

**So you can use it for** any field where you need to understand complex relationships. Product development, research, strategy, education. Map the domain. Navigate it. Mine it for insights.

---

*This is the free book. Every pattern in it emerged from real building. Through real failures. Over thousands of hours.*

*If you want to understand WHY these patterns work — why separation of concerns produces better AI output, why holographic structures outperform linear ones, why wrongness IS the navigation mechanism — there's a book called* **Holographic Work**.

*Follow the flow. The lotus blooms.*

---

## Appendix: Pattern Quick Reference

| # | Pattern | One-Liner |
|---|---------|-----------|
| 1 | Trinity (Ariadne/Poimandres/OVP) | Separate context prep, generation, and evaluation |
| 2 | Heartbeat vs Cron | Oversight ≠ labor. Never mix them. |
| 3 | Channel-Is-Inbox | Behavior emerges from configuration, not code |
| 4 | Singleton God Object | One process, compose via mixins |
| 5 | Skills Not Agents | Capabilities scale without runtime costs |
| 6 | Read-Only Geometry | Design docs are invariant, agent anneals toward them |
| 7 | File Gating | Empty file = zero cost |
| 8 | Transcript Pruning | Delete no-information turns |
| 9 | Compaction Protocol | Exhaustive narrative before context death |
| 10 | Compiler Compiler | D:D→D — build the builder |
| 11 | Push-Based Completion | Children announce, no polling |
| 12 | Autopoietic Loop | Promise creates accountability |
| 13 | Holographic Funnel | Free thing IS the paid thing |
| 14 | Self-Selling Systems | Product proves itself by running |
| 15 | Business of Businesses | Autonomous units, compiler makes more |
| 16 | Crystal Ball | Navigate any domain mathematically |
