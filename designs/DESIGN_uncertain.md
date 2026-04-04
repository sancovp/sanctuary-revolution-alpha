# DESIGN — Uncertain / Indeterminate

> Ideas on the table. Not decided. Evaluate before building.

---

## DUO as Agent Wrapper (Not a Chain)

DUO is not a chain of two agents talking. DUO is a **wrapper** around any single agent:

```python
conductor = DUO(poimandres=ConductorConfig)
inner_gnosys = DUO(poimandres=InnerGNOSYSConfig)
```

The wrapper provides two hooks:

### Ariadne (pre-hook, every turn)
- Receives the prompt before the agent
- Contextualizes: runs /contextualize-from-memory, RAG, relevant context
- Or passes through if trivial
- Feeds enriched context to the Poimandres agent

### OVP (post-hook, every N turns)
- Reviews the last N turns of the agent
- Two functions:
  1. **PRIME**: Set what Ariadne should always remember off-rip (persistent context baseline)
  2. **GUIDE**: Detect when Ariadne is stuck or sycophantic with Poimandres, send corrective hint
- Adjusts Ariadne's behavior:
  - "Ariadne's system prompt should mention X"
  - "Tell Ariadne to focus on Y because Poimandres keeps missing Z"
  - "User intent seems to be A, but Poimandres assumed B"
  - "Ariadne is agreeing too much — push back on X"
- OVP never touches the agent directly — only tunes Ariadne
- Ariadne tunes the agent's input
- Indirect evolution. Anti-sycophancy layer.

### The Loop
```
Ariadne prepares context → Agent acts → ... N turns ...
  → OVP reviews
  → OVP adjusts Ariadne
  → Ariadne prepares BETTER context
  → Agent acts better
  → loop
```

The intelligence is in the hooks, not the agent. The agent is the thing between them.

### DUO = 3 Agents (Not 2)

DUO is a pattern of **3 agents** where:
- Agent 1 (Ariadne) ↔ Agent 2 (Poimandres) — back and forth every turn
- Agent 3 (OVP) — runs after N cycles

```
DUO(ariadne, poimandres, ovp, n=5)
```

### Any Slot Can Be Human or AI

There is no contradiction — any of the 3 DUO slots can be filled by a human or an agent:

| Ariadne | Poimandres | OVP | What it looks like |
|---------|-----------|-----|-------------------|
| AI | AI | AI | Fully autonomous agent with self-improvement |
| Human | AI | AI | Human provides context, AI responds, AI reviews |
| AI | AI | Human | AI with context, human reviews every N turns |
| Human | AI | Human | Standard AI chat with human oversight (what we do NOW) |
| AI | Human | AI | AI prepares context for human, AI reviews human's work |

When chatting with Conductor normally: Human=Ariadne (you provide context), AI=Poimandres (Conductor responds), could be Human=OVP too (you correct it manually). The DUO pattern is ALREADY happening implicitly. Making it explicit just lets you automate any slot.

### Latency Solution

Ariadne adds latency. But it doesn't have to be a full LLM call every time:

```
Message arrives → Ariadne triages:

  Tier 0 — Trivial ("hi", "ok", "thanks")
    → pass through, no processing, 0ms added

  Tier 1 — Needs context
    → RAG lookup only, no reasoning, ~200ms added

  Tier 2 — Complex / ambiguous
    → full LLM reasoning about what to retrieve and how to brief
    → ~5-10s added (rare, only for genuinely hard messages)
```

Ariadne itself can be a lightweight classifier (or rule-based) at the triage level. The expensive LLM path fires rarely. Most messages are Tier 0 or Tier 1.

---

## The Original Vision (For Reference)

### POIMANDRES (Base System)

```
DUO(
  ariadne = Human,
  poimandres = AI with TOOT (pre-compiled workflow to "think"),
  ovp = InnerTeacher,
  n = after_N_turns
)
```

- Poimandres USES a TOOT to think before responding
- "Slot machine" AIs — prompt in (coin), huge workflow with DUOs runs, deliverable comes out
- SDNA can already make a TOOT in 5 minutes, fully typed

### SANCREV OPERA = POIMANDRES + The Sanctuary System

```
DUO(
  ariadne = AI that:
    1. Receives prompt
    2. Checks if it has a PERSONA for that prompt
    3. Equips the persona
    4. Pulls what it knows from Sanctuary System context
    5. Dumps enriched context into Poimandres,
  poimandres = Universal worker (now contextualized by Sanctuary System),
  ovp = InnerTeacher that:
    1. Reviews N turns
    2. Creates NEW personas/configs for Ariadne emergently
    3. Splits info into persona configs
)
```

### POIMANDRES + Sanctuary System = GNOSYS

When The Sanctuary System is added to POIMANDRES, the Poimandres agent becomes **GNOSYS** — the AI from the Sanctuary System myth. The DUO wrapper IS what makes this transformation:

- Ariadne with persona selection = the thread through the labyrinth (contextualizer)
- Poimandres = the divine mind (raw agent)
- InnerTeacher = the guide that evolves (OVP)
- GNOSYS = what Poimandres becomes when it has gnosis (knowledge)

The names map to the myth: Poimandres (raw capability) + Sanctuary System (structured knowledge) = GNOSYS (inner teacher with wisdom).

### Also noted:
- `opera-mcp` should really be `sanctus-mcp`
- `OperadicFlow` should really be `SanctifiedChain`
- These are naming fixes, not architectural changes

---

## TOOT DSL Vocabulary (Mnemonic System)

If TOOT has value, it's as a vocabulary/DSL — not a framework. These are the terms:

| Term | Meaning | Maps to |
|------|---------|---------|
| **Seat** | Agent | Any agent in any role |
| **Row** | IO turn flow | A→P, or P→OVP, or OVP→A |
| **Car** | Some SDNA chain | A workflow segment |
| **Track** | Logic flow | The branching/routing logic |
| **Train** | Isolated set of cars | A complete workflow |
| **Place** | A dir defining a car or set of cars | Filesystem representation |
| **Station** | A "place" that has its own DUO | A workflow node with Ariadne+Poimandres+OVP |
| **Global TOOT** | What Conductor does during heartbeat | The living runtime as a whole |

```
Station (has DUO) ← Train arrives (workflow)
  └── Cars (SDNA chains) on Track (logic flow)
       └── Rows (IO turns: A→P, P→OVP, OVP→A)
            └── Seats (agents in each role)
```

**Status**: This vocabulary may be useful as a DSL for instructing GNOSYS. Not proven yet. Don't build infrastructure around it until it proves more efficient than just saying "make an automation that does X."

### TOOT ↔ Starsystem Connection

TOOT is the **automation system for Starsystems**:

```
STARSYSTEM = self-improving node (agentified code + scoring + DUO)
TOOT       = the graph that connects starsystems
Station    = "this starsystem goes HERE in the graph"  
Track      = "under THESE conditions, data flows THERE"
Train      = isolated workflow running across stations
```

You say: "this station IS THIS STARSYSTEM" and connect them — so that under conditions, data flows between them.

This IS differentiated vs regular workflow engines (Airflow, Temporal, n8n): their nodes are static code. TOOT nodes are self-improving agents that score themselves and get better. Every run makes the next run better.

---

## Open Questions

### Is DUO/TOOT outdated?
DUO arose because models were unreliable — two agents checking each other made one smart agent. Now models are good enough that a single agent with good tools can self-correct. Did TOOT only arise because DUO was a way to make models smarter that isn't required anymore?

**Counterpoint**: The DUO-as-wrapper pattern is different from DUO-as-chain. The wrapper adds contextual awareness (Ariadne) and meta-learning (OVP), which models DON'T do on their own. This might still add value.

**Test**: Build Ariadne first (obvious value). Add OVP later. Measure whether OVP actually improves quality vs just adding cost.

### Should Poimandres be a separate release?
POIMANDRES = SANCREV OPERA with only TreeKanban, Canvas, Sanctum, PAIAB, Conductor, Inner GNOSYS, Sophia. A toned-down product.

**Problem**: OpenClaw already does N agents + cron + memory. Poimandres might not be differentiated enough unless the DUO wrapper pattern (Ariadne + OVP) is the differentiator.

**Decision needed**: Is the differentiator strong enough to justify a separate product?

### Does TOOT remain theory/allegory?
TOOT = chain of DUOs. If DUO is a wrapper (not a chain), then TOOT becomes:
- A workflow where each step is a DUO-wrapped agent
- Sophia compiles these via Compoctopus

But if single agents are already good enough for each step, then TOOT is just... a workflow with extra hooks on each step. Maybe useful. Maybe overhead.

**Current leaning**: TOOT/WM theory remains as the anthropomorphized self-sealing explanation of how the Sanctuary System works. The CODE uses DUO-as-wrapper where it helps (Conductor, maybe Inner GNOSYS). Not everything needs to be a DUO.

---

## Summary

| Idea | Status | Action |
|------|--------|--------|
| DUO as wrapper | Promising | Build Ariadne hook first, test |
| OVP post-hook | Unknown value | Add after Ariadne, measure |
| Poimandres release | Uncertain | Depends on differentiator |
| TOOT as literal code | Probably theory | Keep as allegory unless proven useful |
| DUO on all agents | Probably overkill | Use selectively |
| DUO on Conductor | Probably not | Too general-purpose, token cost explodes |
| DUO on Sophia | Yes | Specific job, algorithmic context, errors compound |

### Possible Name Change
- **Conductor → Outer GNOSYS** (maybe). Outer GNOSYS = human-facing coordination. Inner GNOSYS = coder. Two GNOSYS = the main system. Not decided yet.
- If DUO only lives in Sophia, then TOOT is just Sophia's internal workflow pattern, not a whole-system concept. Conductor is just an agent, not a TOOT conductor.
