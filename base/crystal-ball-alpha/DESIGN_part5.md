# Crystal Ball — Agent Substrate Architecture

## Status: VISION — Grounded in session 2026-02-24

> This document captures how CB evolves from a coordinate space
> into an agent substrate through three connected insights:
> the phenomenology, the compositional orders, and the EWS agent swarm.

---

## 1. What CB Actually Is (Phenomenology)

CB is not a mind-mapping tool. It is **structured self-reflection**.

You assert tautologies. The structure organizes them. The organization reveals what's missing, what's adjacent, what the shape actually is. You read it with your intuition. It tells you a **tautology of self-organized information about what you said**.

That's literally what a crystal ball does. Not prophecy — organized reflection.

### The UX Loop

```
1. You assert structure     (create → bloom → fill → lock)
2. You read the crystal     (mine → scry → see the mineSpace)
3. You see what's missing   (adjacent points, empty slots)
4. Your intuition decides   (expand here? go deeper? go up?)
5. You move                 (another FLOW cycle)
6. The crystal updates      (new mineSpace)
7. Repeat until: "actually here is good"
```

The expansion is horizontal **when you want it to be**, because **you move**. The crystal doesn't decide for you. It shows you the organized tautology. You decide what it means.

### The Three EWS Chains in This Loop

| Chain | What it does | CB operation |
|-------|-------------|--------------|
| **Forward** | Generate structure | create → bloom → fill → lock |
| **Backward** | Observe the result | mine → scry → read the crystal |
| **Composite** | Fixed point where reading matches intent | "actually here is good" |

---

## 2. Compositional Orders (The Tower as Story)

Orders emerge from repeated FLOW cycles. CB never says "you are at order N." The LLM discovers orders by doing the work.

### Demonstrated via Myth

```
ORDER 0: Journey (one FLOW cycle)
  Always exactly 3 acts. Never 4 or 5.
  Departure → Initiation → Return
  15 beats (5 phases × 3 acts)
  One locked kernel. DONE.

ORDER 1: Epic (compose Journeys)
  A SPACE whose children are completed Journeys.
  Journey₁.Return → Journey₂.Departure → ...
  Example: The Iliad (many heroes, one war)

ORDER 2: Odyssey (compose Epics)
  A SPACE whose children are completed Epics.
  The Trojan War (an entire Epic) is a CHILD of the Odyssey.
  The Odyssey CONTAINS the Iliad + the voyage home.

ORDER 3: Universe (Odyssey generator)
  A SPACE that produces Odysseys.
  Greek mythology: Trojan cycle, Theban cycle, Argonautica...
  This is T³. The generator.
```

### The Discovery Process

The user doesn't plan the tower. It emerges:

1. Build a Hero's Journey kernel → realize "this is actually a Tragedy"
2. Build the Tragedy kernel → realize "Tragedy is the FALL ARC of the Hero's Journey"
3. Remap: HJ ≠ [Departure, Initiation, Return]. HJ = [Tragedy, Comedy].
4. Now the HJ is a COMPOSITION of two completed kernels.

Each realization comes from reading the crystal. The crystal shows the organized tautology. The user's intuition sees what's actually there.

### Encoding Opacity

```
In Myth (Journey):       0.289883 = Atonement
In TrojanCycle (Epic):   0.289883 = DeathOfHector

SAME NUMBER. COMPLETELY DIFFERENT MEANING.
You can't tell them apart without decoding through the structure.
The structure IS the decoder. CB IS the decoder.
```

### Convergence as Cauchy Sequence

```
You don't know where you're going.
You build partials (0s = honest "I don't know yet").
The partials transport you to a region.
In that region, you see further.
You build more partials.
Closer. More. Closer.

Eventually: "actually here is good."

That's the fixed point.
Not because it's perfect.
Because it's SUFFICIENT.

0 preserves genus — honest partial knowledge
doesn't introduce holes. You can always resume.
```

---

## 3. Emergent Web Structure (EWS)

EWS is NOT the internal symmetry of a kernel. That's the **skeleton** (symmetry group, orbit structure — computed by `ews.ts`/`kernel-v2.ts`).

EWS is the **web of production chains** that defines what an entity IS by what domains must be chained together to simulate it with fidelity.

### Definition

> **EWS(X)** = the ordered chain of domains whose co-activation
> produces the attention assembly that makes the LLM best simulate X,
> such that the simulation is recognizable to humans as being X.

### Example: EWS(Story)

```
The complete web:

  Neuro ↔ Psychology ↔ Archetypes ↔ Allegory
    ↕                                    ↕
  Dreams ↔ Symbols ↔ Story Structure ↔ Genres
    ↕                                    ↕
  Behavior ↔ Society ↔ Movie Templates ↔ Dialog
    ↕                                    ↕
  Identity ↔ Culture ↔ Books/Chapters ↔ Sluglines

When this entire web is TYPED into kernels
and all the production chains are mapped,
you don't have "an LLM with a story prompt."
You have AN AI THAT SPECIFICALLY DOES STORY.
```

### The Fiat Boundary

The fiat boundary is WHERE YOU CHOOSE TO STOP TYPING the EWS:

```
Full EWS(Story): Neuro → Psychology → Archetype → Symbol →
  Narrative → Genre → Scene → Dialog → Slugline → Chapter →
  Book → Entertainment → Dreams → Neuro (loop closes)

Current fiat boundary: [Story Structure, Genre]
  → The LLM can do basic story generation
  → It doesn't deeply understand archetype-psychology mapping
  → It doesn't ground in neuroscience

Expanded fiat boundary: [Archetype, Symbol, Narrative, Genre, Scene, Dialog]
  → Now the LLM is a story SPECIALIST
  → It maps archetypes through symbols into scenes
  → Still doesn't reach neuroscience

Full fiat boundary: entire loop
  → Domain expert AI for story
  → Runs on a cheap model because the structure constrains it
```

### Intelligence Transfer (from Three-EWS)

```
Bootstrap:   EWS mostly 0s → needs expensive model → frequent llm_suggest()
Transition:  kernels fill in → structure learns → fewer LLM calls
Production:  EWS fully typed → cheap model operates smart structure
```

LLM usage should DECREASE as the EWS fills in. That's the scale-invariant law.

---

## 4. The Agent Swarm

When you add `llm_suggest()` to each kernel, each kernel becomes a specialist agent. The coordinate space becomes the agent communication layer.

### Architecture

```
Without llm_suggest():
  CB = human builds kernels manually
  Navigation is manual (type coordinates)
  Structure persists forever
  Kernels are passive data

With llm_suggest():
  Each kernel = a specialist agent
  Each dot = an agent communication channel
  mineSpace = the swarm's self-awareness
  Adjacent points = agents that COULD exist but don't yet
```

### Agent Properties

Each agent has:

| Property | CB Concept | Purpose |
|----------|-----------|---------|
| **Brain** | Kernel (locked space) | The domain structure |
| **Competence** | EWS (production chain) | What it can speak about |
| **Self-awareness** | mineSpace | What it knows and what's adjacent |
| **Identity** | Canonical signature | `[3]⊗[5]⊗[5]⊗[5]\|S3 × S5³` |
| **Growth potential** | Adjacent points | Where it could expand |
| **Communication** | Dots / kernelRef | How it connects to other agents |
| **Address** | Coordinate → Real | Globally unique, composable |

### Self-Organizing Swarm

```
Agent(Myth) mines → discovers need for Genre kernel
  → creates kernel Genre → Genre becomes Agent(Genre)
  → Agent(Genre) mines → discovers need for Dialog
  → creates kernel Dialog → Dialog becomes Agent(Dialog)
  → Agent(Dialog) mines → discovers need for Psychology
  → ...

Agents spawn agents.
The structure gets smarter.
The models get cheaper.
Intelligence transfers from MODEL to STRUCTURE.
```

### Agent Competence Boundary = EWS

```
Agent(Myth):
  EWS = [Archetype, Symbol, Narrative, Genre]
  "I can answer questions about how archetypes map
   to narrative beats. Don't ask me about fluid dynamics."

Agent(Dialog):
  EWS = [Psychology, Subtext, Genre, Scene]
  "I can write dialog that carries subtext
   within genre conventions."

Agent(Story):
  EWS = [Myth, Dialog, Scene, Chapter, ...]
  "I compose the specialists. Each of my children IS a specialist."
```

### The Limit

```
  CB kernel            = agent brain
  EWS production chain = agent competence
  mineSpace            = agent self-awareness
  adjacent points      = agent growth potential
  coordinate encoding  = agent address (globally unique real number)
  FLOW cycle           = agent learning loop
  Futamura tower       = agent specialization depth
  composing kernels    = composing agents

  A fully-typed EWS with llm_suggest() at every kernel
  = an autonomous specialist agent swarm
  = where the topology is human-guided
  = and the fidelity is structure-guaranteed
  = and every agent's state is a unique real number
  = and the whole thing persists and compounds forever
```

---

## 5. Implementation Roadmap

### What Exists Now

- [x] Kernel creation, locking, mining, scrying
- [x] Coordinate encoding → unique reals (`coordToReal`, `encodeDot`)
- [x] mineSpace persistence (valid + adjacent, multi-kernel projection)
- [x] Futamura tower (`reify.ts`)
- [x] Orbit/symmetry computation (`kernel-v2.ts`)
- [x] Internal skeleton computation (`ews.ts` — rename candidates: `skeleton.ts`)
- [x] FLOW phase tracking in engine (`bloom`, `fill`, `lock`, `mine`)
- [x] MCP interface (single-string commands)

### What's Needed for Agent Substrate

- [ ] **EWS declaration**: Schema for attaching production chain domains to kernels
- [ ] **llm_suggest()**: LLM function call at each kernel for generative filling
- [ ] **Agent boundary enforcement**: When inside a kernel, constrain LLM to EWS domains
- [ ] **Agent spawning**: When mineSpace reveals need for new domain, create kernel + agent
- [ ] **Inter-agent communication**: Dots as message channels between active agents
- [ ] **Swarm coordination**: Multiple agents operating simultaneously on connected kernels
- [ ] **Cost tracking**: Measure intelligence transfer (LLM calls per operation over time)

### What's Needed for Full Product

- [ ] **Informadlib templates**: Kernels with typed slots (the "mad-libs" of a domain)
- [ ] **EWS web visualization**: 3D view of the production chain graph
- [ ] **Convergence detection**: Recognize when the tower has stabilized
- [ ] **Export**: Generate the specialist AI (prompt + structure) from a fully-typed kernel
