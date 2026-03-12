# Quick Reference Guide

## The Workflow at a Glance

```
(0)[AbstractGoal]→
(1)[SystemsDesign]→
(2)[SystemsArchitecture]→
(3)[DSL]→
(4)[Topology]→
(5)[EngineeredSystem]→
(6)[FeedbackLoop]→
loop→(0)
```

## Three Passes

| Pass | Question | Output |
|------|----------|--------|
| **1: CONCEPTUALIZE** | What IS this thing? | Ontological understanding |
| **2: GENERALLY REIFY** | How do we MAKE these? | System/generator |
| **3: SPECIFICALLY REIFY** | How do we make THIS one? | Concrete instance |

## Phase Purposes

| Phase | Core Purpose |
|-------|--------------|
| **0: Abstract Goal** | Define what we're trying to achieve |
| **1: Systems Design** | Understand requirements and constraints |
| **2: Architecture** | Design component structure and interactions |
| **3: DSL** | Define domain vocabulary and rules |
| **4: Topology** | Map network of connections and flows |
| **5: Engineered System** | Build and deploy the actual system |
| **6: Feedback Loop** | Learn and improve continuously |

## Key Principles

### 1. **Ontology First**
Understand WHAT before HOW

### 2. **Pass Separation**
Don't mix conceptual with implementation

### 3. **Systematic Coverage**
Every substep serves a purpose

### 4. **Iterative Refinement**
Loop back with deeper understanding

### 5. **Domain Focus**
Technology serves the domain

## Quick Checks

### Starting a New Design?
1. What domain are you designing for?
2. Which pass are you on? (1, 2, or 3)
3. Have you completed earlier passes?
4. Are you thinking at the right level of abstraction?

### Stuck on a Phase?
1. Re-read the phase purpose
2. Check examples from your domain
3. Consider skipping and returning later
4. Ask: "What would this mean in my domain?"

### Common Corrections

| If you're... | You should... |
|--------------|---------------|
| Writing code in Pass 1 | Stop and focus on concepts |
| Creating syntax for DSL | Define vocabulary instead |
| Stuck in analysis | Time-box and move forward |
| Missing user needs | Return to stakeholder goals |
| Building features randomly | Check against ontology |

## Phase 1 Substeps Quick Reference

- **(1a) Purpose**: Why does this exist?
- **(1b) Context**: What's the environment?
- **(1c) Stakeholders**: Who cares?
- **(1d) Success**: How measure good?
- **(1e) Constraints**: What limits us?
- **(1f) Resources**: What's available?
- **(1g) Regulatory**: What rules apply?
- **(1h) Risks**: What could go wrong?
- **(1i) Concepts**: Core ideas?
- **(1j) Ontology**: Full concept map?
- **(1k) Boundaries**: In/out of scope?
- **(1l) Brief**: Synthesis

## Red Flags

🚩 **Jumping to implementation**
🚩 **No clear ontology**
🚩 **Mixing passes**
🚩 **Ignoring feedback loops**
🚩 **Technology-first thinking**
🚩 **No stakeholder consideration**
🚩 **Analysis paralysis**
🚩 **Skipping "obvious" steps**

## Green Flags

✅ **Clear domain understanding**
✅ **Separated concerns by pass**
✅ **Stakeholder needs addressed**
✅ **Ontology guides decisions**
✅ **Planning for iteration**
✅ **Balance theory/practice**
✅ **Human-centered design**
✅ **Systematic progress**

## The Core Loop

```
Understand Domain (Pass 1)
         ↓
Build Generator (Pass 2)  
         ↓
Create Instance (Pass 3)
         ↓
Learn & Improve (Phase 6)
         ↓
Deeper Understanding ←──┘
```

## Remember

- The workflow is a **guide**, not a straightjacket
- **Adapt** to your domain and context
- **Document** your decisions and why
- **Iterate** rather than perfect
- Focus on **understanding** before building
- Keep the **human element** central
- **Learn** from each loop

## Success Pattern

1. **Read** the complete workflow
2. **Understand** the three-pass approach
3. **Start** with Pass 1, Phase 0
4. **Work** systematically through phases
5. **Complete** all three passes
6. **Loop** back with learnings
7. **Improve** continuously

---

*"The beginning of wisdom is the definition of terms."* - Socrates

*"In order to build systems, we must first understand what we're building."* - Systems Design Wisdom
