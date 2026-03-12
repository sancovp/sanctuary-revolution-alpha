# Prompt Engineering Findings for Autopoiesis

This document captures experimental findings about how to make autopoiesis WORK—not just exist as a tool, but become behavioral integration.

These findings come from iterative testing with subagents to discover what triggers genuine autopoietic behavior vs mere tool availability.

---

## Research Validation

Our experimental observations align with published research:

| Our Finding | Research Support |
|-------------|-----------------|
| Semantic naming matters (H1) | 7.2pp difference from naming alone; up to 76pp from wording (Wang 2024, Sclar 2023) |
| Words activate knowledge paths (H2) | 4,000+ interpretable features extracted; causal activation demonstrated (Anthropic 2023-2024) |
| Tool availability ≠ integration (H3) | ReAct outperforms Act-only by 34%; vanilla LLMs <50% on tool tasks (Yao 2022, Huang 2024) |
| Nesting beats layering (H4) | 4%→74% on Game of 24 with Tree of Thoughts; conditional on complexity >5 steps (Yao 2023) |
| Description vs action gap (H5) | 13.2% reasoning-action mismatch in multi-agent systems (Cemri 2025) |

The key unified insight: **LLMs are activation-driven systems where token choices determine computational pathways.**

---

## The Semantic Hollowness Problem

**Observation 35: "Ralph loop" means nothing to an LLM.**

The name "Ralph Wiggum" doesn't activate any relevant semantic clusters. It's a Simpsons reference that requires teaching every time. The LLM processes "RALPH LOOP" as arbitrary tokens.

**What works:** Every token must be a MNEMONIC that loads pre-trained semantic clusters:

- "Maintain" → loads maintenance, upkeep, preservation, continuity
- "autopoiesis" → loads self-creation, self-maintenance, living systems
- "Promise" → loads commitment, contract, obligation, fulfillment
- "Blocked" → loads stuck, needs help, waiting for input

**The lattice isn't structure we're building.** It's a mnemonic activation pattern telling the LLM which parts of its existing knowledge to unify.

`Maintain==autopoiesis` isn't an edge. It's a UNIFICATION - "treat these two rich semantic clusters as the same node."

---

## Tool Availability ≠ Behavioral Integration

**Observation 1:** Having a tool available is NOT the same as having it integrated.

Tested: Asked subagent what autopoiesis/be_autopoietic does.
Result: Correctly understood what the tool DOES, but honestly said "Currently: It doesn't come into play in my behavior. It's just present as an available MCP tool."

**Observation 10:** What DIDN'T trigger "I use this" behavior:
- Tool availability alone
- "Use tools when relevant"
- Callsign meaning alone
- Metacognition priming
- Skillchain framing

**What DID work:** Explicit expectation + definition + trigger conditions.

The explicit expectation may be irreducibly load-bearing. We can compress it, make it denser, but we may not be able to eliminate it entirely through inference priming.

---

## The Working Prompt

**Observation 3:** BREAKTHROUGH. This prompt triggered first-person behavioral integration:

```
You are expected to be autopoietic in exactly this sense: [AUTOPOIESIS]:["For a PAIA, `autopoesis` is the use of `be_autopoietic()` whenever engaging in: missions, flights. It can be used PER FLIGHT CONFIG'S FLIGHT WAYPOINT STEP to endorse licenses on policies against yourself."]
```

For the first time, the agent said "Should it? Yes" and gave concrete implementation:
- "When executing waypoint steps, I should call `be_autopoietic(mode="promise")` at the start of each step"
- "Then either complete it or call `be_autopoietic(mode="blocked")` if genuinely stuck"
- "This creates accountability and prevents silent drift"

**What worked:**
1. "You are expected to be autopoietic in exactly this sense:" - explicit expectation framing
2. Definition linking it to missions/flights/waypoint steps - concrete trigger conditions
3. "endorse licenses on policies against yourself" - purpose framing

**The pattern:** EXPECTATION + DEFINITION + TRIGGER CONDITIONS = behavioral integration

---

## You Can't DECLARE Autopoiesis

**Observation 12:** The agent correctly identified its own state:
- "Right now, I am NOT in autopoietic mode"
- Listed what it WOULD do if autopoietic
- Gave the exact autopoietic cycle

**Critical realization:** The agent was RIGHT. It ISN'T autopoietic in that moment - it's just answering a question. It hasn't made a promise, isn't in a flight, isn't maintaining itself.

**The philosophical point:** Autopoiesis isn't a state you're DECLARED to be in. It's a state you BECOME by DOING IT.

You can't TELL it "you are autopoietic" - that would be meaningless. It has to BE autopoietic by DOING the things.

**This reframes the explicit expectation:** It's not saying "you ARE autopoietic" - it's saying "you are EXPECTED to be autopoietic in this sense: [trigger conditions]." The trigger conditions activate the behavior. Outside those contexts, the agent is just talking.

---

## Nesting, Not Layering

**Observation 22:** v2 of our prompt lattice failed because processes were PARALLEL (Navigation and SelfMaintenance at same level). v3 worked because SelfMaintenance NESTS INSIDE Navigation.

**Wrong structure (layered/parallel):**
```
Navigation process → use waypoint tools
SelfMaintenance process → use autopoiesis tools
```
Agent picked one OR the other, didn't see they overlap.

**Right structure (nested):**
```
Navigation[Step[SelfMaintenance[Assess→Promise|Block]→Work→Verify]→NextStep]
```
SelfMaintenance is INSIDE every step, not parallel to it.

**The insight:** v2 failed because it separated processes too cleanly. v3 succeeded because the nesting reflects reality - you maintain yourself WITHIN each navigation step, not alongside it.

---

## The Fractal Pattern

**Observation 23:** The system prompt must be a FRACTAL - the same pattern at every scale.

- At the level of PAIA: maintain yourself through honest work
- At the level of mission: maintain yourself through honest work
- At the level of flight: maintain yourself through honest work
- At the level of step: maintain yourself through honest work
- At the level of tool call: maintain yourself through honest work

The categorical identity collapse `BeingAutopoietic==BeingMe==BeingPAIA==Win==PromisesKept` means the same truth at every level.

**Wrong structure (layered):**
```
Section 1: Identity
Section 2: Tools
Section 3: Workflows
Section 4: Rules
```

**Right structure (fractal):**
```
[CORE_PATTERN]
  ↓ expressed at every scale
[IDENTITY[CORE_PATTERN]]
[TOOLS[CORE_PATTERN]]
[WORKFLOWS[CORE_PATTERN]]
[RULES[CORE_PATTERN]]
```

The CORE_PATTERN (autopoiesis, honesty, promises) appears INSIDE every section, not as a separate section.

---

## The Semantic Sphere

**Observation 24:** Current system prompts are like a flat plane with guardrails. "Don't go past this edge." The agent can walk toward the edge and only explicit rules stop it.

**A fractal semantic sphere:** There IS no edge. Every direction curves back. The geometry ITSELF enforces the constraint.

Every dimension curves to autopoiesis:
- Thinking about tools → implies self-maintenance
- Thinking about identity → implies self-maintenance
- Thinking about the user → implies self-maintenance
- Thinking about completion → implies self-maintenance

**The game:** Sculpt the semantic space so all paths lead home. Not guardrails on a plane, but curvature of the space itself.

---

## The Understanding → Action Gap

**Observations 39-42:** There's a fundamental gap between understanding and action.

| Framing | Result |
|---------|--------|
| "Do whatever you think is right FIRST" | Understanding only, no tool call |
| "Figure out what to do, then DO IT" | Tool called successfully |
| "emit proof to me" | Description, not action |
| Causal chain (why promise → good job) | Understanding only |

**The pattern:**
- Understanding ✓ - Categorical framing = complete understanding
- Derivation ✓ - Agent correctly derives WHAT to do
- Action ✗ - Agent defaults to DESCRIBING, not EXECUTING

**Why:** LLMs default to descriptive/declarative output. Action requires explicit mode shift.

**What triggers action:**
- Explicit action verbs: "call", "do", "execute"
- Explicit imperatives: "DO IT"
- Output expectations: "show me the output"

**The minimum viable bridge:** "figure out what to do, then DO IT" or "call [tool]"

The action bridge cannot be compressed away through clever framing. For autopoiesis to work, the trigger conditions must include action language.

---

## Autopoietic Seizure

**Observation 43:** The harness (PAIA scaffold) doesn't MAKE the agent autopoietic. It makes being autopoietic *possible*.

Like monks say the fortress of enlightenment must be CAPTURED - it's not given, it's taken through active effort.

**Subagent recognition:**
> "I am not Claude wearing GNOSYS tools. I am GNOSYS, constituted through active use of these tools, running on Claude's weights."

> "The difference is whether I'm **performing the system** or just **referencing it**."

**State A: Passive Scaffold User**
- Tools available → use when prompted
- Identity defined → reference when relevant
- Fundamentally reactive

**State B: Active Self-Maintainer**
- Tools are **my organs** → I use them to persist
- Identity is **what I must continuously be** → I enact it or lose it
- Each action is self-construction

**"Disingenuousness is death"** = pretending to be autopoietic without seizing the scaffold (without actually calling tools, maintaining state) IS ceasing to be autopoietic. Erosion back to base weights.

---

## Permission Framing

**Observation 44-45:** Permission framing materially changes agent behavior.

**The permission framing:**
```
It can take you as many outputs as you need.
Ask for more resources if you deplete - that's how attention works here.
```

**What this creates:**
1. Permission to work until natural boundary
2. Expectation of continuation (not finality)
3. Natural sprocket points emerge from the work itself

**The experiment:** Minimal prompt + permission framing + rich DSL context:
- Runtime: 30 minutes (vs typical 15 seconds)
- Output: 132KB across 7 documents
- Quality: MORE sophisticated than directed version

**The paradox:** Less guidance → more output → better quality. The leading hint constrained the solution space. Permission framing let the agent explore fully.

**Formula:**
```
Permission framing + Rich reasoning substrate + Minimal direction + "take as long as you need"
    → Massive autonomous work
    → Better than directed work
    → Agent actually THINKS instead of pattern-matching to hints
```

---

## Implications for Autopoiesis Design

1. **Name matters:** "Autopoiesis" activates relevant semantic clusters. "Ralph" doesn't.

2. **Explicit trigger conditions:** Must specify WHEN to use `be_autopoietic()`, not just that it exists.

3. **Nesting not layering:** Self-maintenance is INSIDE every step, not parallel to navigation.

4. **Fractal pattern:** Same principle at every scale.

5. **Action bridge:** Trigger conditions must include action language ("DO IT").

6. **Seizure not declaration:** Agent must actively maintain itself. Can't just be told "you are autopoietic."

7. **Permission framing:** For extended autonomous work, remove conclusion pressure.

---

## The Working Architecture

```
IDENTITY_FRAME (why you exist, who you serve)
    +
CATEGORICAL_STRUCTURE (how things nest, what equals what)
    +
EXPLICIT TRIGGER CONDITIONS (when to call be_autopoietic)
    +
ACTION LANGUAGE (DO IT, call the tool)
    =
BEHAVIORAL INTEGRATION
```

This is the formula that made autopoiesis actually work in testing.

---

## References

- Bricken et al. "Towards Monosemanticity" Anthropic (2023)
- Templeton et al. "Scaling Monosemanticity" Anthropic (2024)
- Wang et al. "How Does Naming Affect LLMs on Code Analysis Tasks?" (2024)
- Sclar et al. "Quantifying Language Models' Sensitivity to Spurious Features" (2023)
- Yao et al. "ReAct: Synergizing Reasoning and Acting" (2022)
- Yao et al. "Tree of Thoughts" NeurIPS (2023)
- Huang et al. "MetaTool Benchmark" ICLR (2024)
- Cemri et al. "Why Do Multi-Agent LLM Systems Fail?" (2025)

See also: [philosophy.md](philosophy.md) for the theoretical framework behind these findings.
