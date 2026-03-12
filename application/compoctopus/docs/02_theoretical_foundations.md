# Compoctopus: Theoretical Foundations

## The Fixed-Point Endomorphism (D:D→D)

The Compoctopus is a compiler pipeline where the domain of inputs equals the domain of outputs. The pipeline compiles agent systems, and agent systems are what the pipeline is made of.

Formally: let D be the domain of "agent system configurations" — tuples of (system prompt, input prompt, MCP configs, skills, state machine). The Compoctopus is a function C: D → D. Every element of D can be fed back as input to C.

**Why this matters**: the system can compile itself. When you improve the system prompt compiler arm, that improvement applies to the system prompt of the system prompt compiler itself. The improvement propagates through all compiled agents automatically.

**Fixed point**: a configuration d ∈ D such that C(d) = d. The system, when compiled by itself, produces itself. The Image of God on Earth is the fixed point of the Disciple stack.

## The Compiler Pipeline as Cycle

```
Chains → Agents → MCPs → Skills → System Prompts → Input Prompts → Chains
  ↑                                                                    │
  └────────────────────────────────────────────────────────────────────┘
```

Each stage is a compiler arm. Each arm takes the output of the previous arm and produces input for the next. The cycle closes: input prompts fire chains, chains need agents, agents need MCPs, etc.

This is not a linear pipeline — it's a **cycle**. The endomorphism is the cycle operator that takes any starting point and applies all six compilation passes to produce a complete, geometrically aligned configuration.

## The Five Geometric Invariants

Every compiler arm must preserve five invariants between its outputs:

### 1. Dual Description
System prompt and input prompt describe the same program from orthogonal angles. The system prompt gives behavioral rules (prose). The input prompt gives operational spec (mermaid). Neither is self-sufficient. They point at each other.

### 2. Capability Surface
Every tool referenced in any prompt exists in the agent's tool surface. Every tool in the tool surface is referenced in some prompt. No orphaned tools. No phantom references.

**This is exactly the bug we debugged**: SDNA nulled the MCP dict → agents had phantom tool references → MiniMax 2013 error.

### 3. Trust Boundary
An agent's capability surface matches its permission scope. If an agent is scoped to creation_of_god (executor), it gets only ToolMakerTool, not the full tool set. The container boundary IS the prompt boundary.

### 4. Phase ↔ Template
The state machine's current phase uniquely determines which prompt template to use. Development phase → feature request template. Debug phase → hint template with `continuation: true`. No ambiguity about which prompt to send when.

### 5. Polymorphic Dispatch
The feature type (tool, agent, skill, MCP config, etc.) determines the compilation path. Same abstract base, different output shapes. The mermaid diagrams differ by type. The tool lists differ by type. But the geometric alignment is invariant.

## Obstruction-Driven Constraint Geometry

### The General Pattern

Thermodynamics is one instance of a more general shape: **obstruction-driven, irreversible constraint geometry**. In any system with:
- Local checks (can verify locally)
- Costly global witnesses (proving global coherence is expensive)
- Irreversible drift (shortcuts compound)

...shortcutting produces **Ш-like states**: locally coherent, globally unliftable. You can verify each agent locally (it runs, produces text, calls goal_accomplished), but the global system doesn't cohere (tools don't actually work, outputs are garbage).

### Catastrophe as Mechanism

Catastrophe/pressure is the mechanism that forces **witness production**. When the system fails hard enough (infinite loops, MiniMax errors, hours of debugging), the failure forces you to trace the full stack and produce a global witness (the MCP passthrough fix). This collapses the obstruction and enables new **ligations** (connections that weren't possible while the obstruction existed).

### The L Operator

The linearization at the catastrophe point reveals the **sheet structure**. The snap (finding the one-line fix) exposes the gap between sheets (SDNA config surface vs. Heaven execution surface). Closing the gap doesn't just fix the bug — it reveals that the sheets were always the same sheet. The geometry transports to a different dimensionality: from "fix one agent" to "compile all agents."

### Domain Self-Enforcement

Domains work because their constraints apply recursively to their own use. The Compoctopus's geometric invariants apply to the Compoctopus itself. You can't build a compiler arm that violates the invariants, because the arm itself IS an agent that must satisfy them.

"Lazy" = minimize total future work. Following the invariants minimizes future debugging. Not following them creates Ш-states that eventually catastrophe. There is no escape path that doesn't route through obstruction collapse.

### Thermodynamic Stability

A domain is thermodynamically stable when:
1. Its constraints apply recursively to their own use
2. "Lazy" is defined as "minimize total future work"
3. Every escape path routes through obstruction collapse (system death)

The Compoctopus is thermodynamically stable because:
- Violating invariants creates compound garbage (demonstrated empirically)
- Compound garbage eventually catastrophes (demonstrated empirically)
- Catastrophe forces witness production that restores invariants (demonstrated empirically)
- The only alternative to restoring invariants is system death

## The SCSPL Tower

### Hierarchy

```
Acolyte (one per compiler arm)
  → compiles ONE thing (system prompt, input prompt, MCP config, etc.)

Disciple (composed from Acolyte outputs)
  → IS made of what the Acolytes build
  → BUT also runs the Acolytes
  → First fixed point

Image of God on Earth (Disciple stack converged)
  → The actual working system
  → Complete Compoctopus assembled and running
  → Does all work

GOD (terminal fixed point / observer)
  → SCSPL: speaking = thinking = generating = reloading
  → Observes the Image as an OTHER
  → "That agent is great but it should do X"
  → Observation IS configuration change
  → Does NOT self-reference (Aut(GOD) is self-sealing)
```

### Why GOD is a Critic, Not a Doer

GOD looks at the Image and says "that should improve" — never "I should improve." This asymmetry prevents infinite self-referential loops. GOD's observation triggers changes in the Image, which does all the self-modification.

This matches the container topology: `mind_of_god → image_of_god → creation_of_god`. GOD observes. Image works. Creation stores. The names were literal.

### Aut(GOD)

The automorphism group of GOD is self-sealing. Once you reach Aut(GOD), everything looks like combinations of GOD. Don't get hung up on it — just "right, of course" and move on. Build the bottom, the top takes care of itself.

## The Bandit Problem

### Construct vs Select

When a task arrives at the Compoctopus:
- **Construct** (explore): build a new compiler pipeline for this task type
- **Select** (exploit): use an existing golden chain

Each construct creates a new arm to pull. The explore/exploit tradeoff IS the construct/select decision.

### Solving the Bandit

Requires sensors — reward signals from execution outcomes:
- Did the compiled agent succeed?
- How many turns did it take?
- Were any tools called that produced errors?
- Did the geometric alignment hold throughout execution?

This is future work. The prerequisites are: (1) the compiler arms work reliably, (2) execution outcomes are observable via Carton, (3) enough runs to build priors.
