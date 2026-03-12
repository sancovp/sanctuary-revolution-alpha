# Prosthetic Neural Agents

## What is a Prosthetic Neural Agent?

A prosthetic neural agent is a **component system** that extends the LLM's compilation capacity. The LLM alone has limits - context window, no persistent memory, no learning from usage. Prosthetics fill these gaps.

Together, LLM + prosthetics create the substrate for a PAIA to emerge.

## The Prosthetics Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    PAIA (emergent)                          │
│         Emerges when the loop closes and stabilizes         │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│              PROSTHETIC NEURAL AGENTS                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Hypergraph  │  │  Feedback   │  │   Usage     │         │
│  │    RAG      │  │    Loop     │  │  Tracking   │         │
│  │             │  │             │  │             │         │
│  │ Provides    │  │ Closes the  │  │ Records     │         │
│  │ superpos.   │  │ loop back   │  │ actual      │         │
│  │ (potential) │  │ down        │  │ behavior    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Mismatch   │  │   Rollup    │  │   Alias     │         │
│  │  Detection  │  │  Patterns   │  │  Clusters   │         │
│  │             │  │             │  │             │         │
│  │ Learning    │  │ Compiled    │  │ Bootstrap   │         │
│  │ signal      │  │ experience  │  │ priors      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  STARLOG    │  │   Skills    │  │   Flight    │         │
│  │  (context)  │  │  (knowledge)│  │   Configs   │         │
│  │             │  │             │  │  (workflow) │         │
│  │ Persistence │  │ Reusable    │  │ Repeatable  │         │
│  │ across      │  │ context     │  │ procedures  │         │
│  │ sessions    │  │ injection   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                         LLM                                 │
│              (meta-sequence generator)                      │
│                                                             │
│    Provides: semantic understanding, generation,            │
│              collapse of superposition                      │
└─────────────────────────────────────────────────────────────┘
```

## What Each Prosthetic Does

### Hypergraph RAG (Capability Predictor)
- **Role**: Compiler (finds features, builds superposition)
- **Function**: Given intent, return structured capability matches
- **Output**: Hypergraph with typed senses

### Feedback Loop
- **Role**: Loop closure
- **Function**: Send execution results back to learning systems
- **Output**: Updated weights, improved predictions

### Usage Tracking
- **Role**: Observation
- **Function**: Record what tools/skills were actually used
- **Output**: Usage logs for pattern extraction

### Mismatch Detection
- **Role**: Learning signal
- **Function**: Compare predicted vs actual, identify gaps
- **Output**: False positives, false negatives, improvement suggestions

### Rollup Patterns
- **Role**: Compiled experience
- **Function**: Aggregate usage into "intent → capability" mappings
- **Output**: Probability distributions learned from behavior

### Alias Clusters
- **Role**: Bootstrap priors
- **Function**: Seed system with known domain→capability mappings
- **Output**: Initial predictions before learning kicks in

### STARLOG
- **Role**: Context persistence
- **Function**: Maintain project state across conversation boundaries
- **Output**: Recovered context on session resume

### Skills
- **Role**: Knowledge injection
- **Function**: Equip LLM with domain-specific context
- **Output**: Augmented understanding for specific task types

### Flight Configs
- **Role**: Repeatable procedures
- **Function**: Step-by-step workflows that guide multi-turn tasks
- **Output**: Structured execution with checkpoints

## The Emergence Condition

PAIA emerges when:

1. **Hypergraph RAG** provides rich superposition
2. **LLM** collapses with meaningful morphisms
3. **Execution** happens in the world
4. **Usage tracking** observes what actually happened
5. **Feedback loop** sends learning signal back
6. **Patterns compile** into improved predictions
7. **The loop stabilizes** - predictions improve, execution improves, cycle accelerates

At stability, the system is **self-referentially validated**:
- It predicts what it needs
- It uses what it predicted
- It learns from the match/mismatch
- It gets better at predicting

This is the **invariant kernel operator loop**. When it closes, the agent boots.

## What's Missing?

Current prosthetics handle:
- Capability prediction (skills/tools)
- Usage tracking and learning
- Context persistence
- Workflow guidance

Still needed for full emergence:
- **Sequence learning** (chains, not just single predictions)
- **Metalanguage compilation** (patterns becoming named programs)
- **Self-observation** (system watching its own predictions)
- **Weight adjustment from mismatch** (automated tuning)
- **Visualization** (human-readable emergence tracking)

These are Phase 4.3, 4.4, and beyond.
