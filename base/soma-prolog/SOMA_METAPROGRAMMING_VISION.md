# SOMA Metaprogramming Vision — CA Integration + Progressive Codegen

**Status**: Design document (2026-04-30)
**Extends**: SOMA_STANDALONE_VISION.md (2026-04-19)
**Context**: How SOMA integrates with CA (context-alignment), progressive code generation, and the metaprogramming endgame.

---

## What This Document Adds

SOMA_STANDALONE_VISION.md describes the product architecture (Observer Agent, Aligner Agent, workers, mobile app). This document describes the **mechanism** — how SOMA actually works as a prompt computer and code generator, how CA feeds it, and what the endgame looks like.

---

## Core Insight: SOMA Is A Prompt Computer

SOMA's primary output is NOT generated code. It is the **exact prompt** for an LLM.

SOMA walks rules + CA graph + automations + dependency chains and computes everything it CAN resolve with logic, then packages what it CANNOT resolve as a structured prompt (failure_error) returned to the LLM caller. The LLM fills what SOMA couldn't deduce.

- `compile_to_python` is one endpoint — when SOMA has enough to generate code directly (fully typed)
- `failure_error` is the more general output — structured prompt with all resolved context + specific instructions for what the LLM needs to provide
- Both are the same mechanism at different typing depths

The cascade: better typing → more specific prompts → better LLM outputs → more observations → better typing → even better prompts.

---

## Everything Starts As CODE

There is no SOUP→CODE binary switch. Everything has programming types from the moment it enters SOMA (string_value, int_value, float_value, bool_value, list_value, dict_value — these ARE the programming types). string_value IS a programming type — the most generic one.

A concept with all string_value fields IS already CODE at an arbitrary base level. It's a Pydantic model that an LLM can fill with text. That's already useful. That's already callable.

The progression is WITHIN code — a continuous spectrum of specificity:

1. **All strings** — Pydantic model, LLM fills with text, works for anything
2. **Some typed** — amount becomes int_value, date gets a type, model gets more specific
3. **Constrained** — deduction chains add cross-field constraints (if amount > threshold → requires_approval)
4. **Fully typed** — model is so specific that calling it IS running the code

---

## The Triple Chain Under Every Type

Under every type, there is a HUGE chain of triples that defines what something IS. It is a single statement composed of all the triples that compose all the restrictions and how they can be filled.

Example: `process` requires `has_steps` (which requires `has_step` entries, each requiring `has_method_name` + `has_method_body` + `has_method_parameters`), `has_roles`, `has_inputs`, `has_outputs`. That's already ~20 triples deep. Each level can have its own restrictions going deeper.

A morphism (like CA's CONTAINS, DEFINES, IMPORTS) BECOMES a restricted set of UARL predicates (is_a, part_of, embodies, manifests, reifies, programs) that boot it. "UARL semantics completely entered" = all restrictions for all morphisms defined and decomposed into UARL predicates. The original morphism vocabulary is gone — replaced by universals.

---

## Python Checks Replace Logic For Simple Things

You do NOT need Prolog deduction chains for everything:

- "Does it have git?" → Python check (os.path.exists)
- "Does it have a starsystem?" → check the graph shape (query Neo4j)
- "Is this file part of a pattern?" → CA pattern_detector (already built)

Only use Prolog deduction chains for things that REQUIRE actual deduction/logic — cross-concept constraints, transitive reasoning, rule composition.

Mirror pattern: every time a Python check fires, you can update the graph. Then check the graph for semantics once you've ontologized how the graph stores it. The graph stays current with reality.

---

## SOMA Always Generates Code

SOMA does not wait for full typing before generating. It generates CONTINUOUSLY. The quality scales with how much you've typed:

- Partially typed = partial code (Pydantic model with string fields, LLM fills)
- More typed = more specific code (typed fields, some callable)
- Fully typed = complete code (all fields typed, constraints enforced, fully callable)

`compile_to_python` in soma_compile.pl currently handles the `process → has_steps → template_method` shape. This is just the FIRST implementation for ONE shape. The vision: ANY typed concept → callable Pydantic model → progressively refined.

---

## Each Callable IS An Agent

Every compiled callable is already a full-blown agent at whatever base degree you define (what tools it has by default, how it accumulates them).

As the callable gets used, SOMA emits rules about WHEN to call it. The automations accumulate about themselves — these ARE the deduction chains. The deduction chains make you better at generating complete webs, which give you MORE info to generate MORE cascading stuff.

The cascade:
```
observe → type → generate callable/agent → agent produces observations when called
→ those observations type MORE things → MORE agents → MORE deduction chains
→ CASCADING self-growth
```

---

## Recursive Depth: The Slack Example

Invoice_Processing reaches CODE → SOMA shows spec to LLM → LLM sees slack_channel as input → but Slack is an API → WHERE is the API info?

SOMA detects: messaging_source requires has_api_endpoint → unnamed_slot → that becomes a TASK in the vibe-coding process → agent gets the Slack API spec → enters it as events → SOMA now knows the endpoints → each endpoint has parameters → those get typed → deeper and deeper.

Each depth level creates more convention rules, more types, more deduction chains. Over time the system gets deeper — MORE things are typed, MORE things auto-resolve.

Eventually: hook ANY API by just speaking about it. "Some API exists at this URL, get the endpoints with this call" → system discovers endpoints, builds webs, generates agents automatically. Abstract meta-information connecting stuff makes logic naturally expand.

---

## Authorization Of Fills

Eventually you get rules for authorization: "this agent is able to fill this arg contextually, this arg must also come from this level of typed thing." Because typing is recursive, you can say "must satisfy all these constraints" — and those constraints are themselves typed concepts with their own restrictions.

---

## The Endgame: No More Subclasses

You no longer need to make subclasses literally in code. You just declare:

"This thing is_a that, and it is because [these triples], and if it is then you can code with it."

The declaration IS the class. SOMA generates the code. No manual subclassing. Programming collapses into typed declarations. Convention rules enforce what each declaration means. The LLM fills implementation. Authorization rules control who/what can fill which args.

---

## CA Integration Specifically

CA (context-alignment) observes code structure: files, classes, methods, imports, patterns, dependencies. These observations enter SOMA through events, same as everything else.

What was built (Apr 29-30 2026):
- `pattern_detector.py` / `pattern_fingerprint.py` — auto-discovers code patterns from shared base classes
- `check_onion_imports` in codenose — import direction enforcement on every edit
- Debounced CA refresh queue — codenose queues touched files, flush after 5min idle
- Pattern nodes + FOLLOWS_PATTERN edges in Neo4j (same database as CartON)

What needs to happen for CA→SOMA:
- CA morphisms (CONTAINS, DEFINES, IMPORTS, HAS_METHOD, FOLLOWS_PATTERN) enter SOMA as typed observations
- Convention rules for code types need to be DEVELOPED through events (not hardcoded — per foundation-vs-contamination rule)
- SOMA computes prompts about code: "You need to read file X and Y, and because Y has automation Z, also read Z, and here's the dependency chain"
- Progressive typing of CA relationships into UARL predicates (is_a, part_of, embodies, manifests, reifies, programs)

---

## The Universal

The universal that makes all of this work: **typed triple graph + convention rules + unnamed_slot detection + failure_error prompting**.

This mechanism works at ANY depth, for ANY type, forever. You keep adding convention rules as events and the system handles them. Nothing blocks because something is incomplete — SOUP/string_value is still usable, unnamed_slots are just tasks, you fill them whenever. Completely partial, forever.

The string_value type IS the universal base case. Everything starts there and refines. The system never needs to be "done."

---

## Pellet Note

The Pellet/OWL aspect from SOMA_STANDALONE_VISION.md was written before Pellet was replaced with YOUKNOW backtracking for runtime validation. Pellet's role is now reduced to periodic (e.g., daily) OWL model consistency checks, not inline validation.

---

## Reference

- SOMA_STANDALONE_VISION.md — product architecture (Observer, Aligner, mobile app)
- SOMA_CARTON_MERGE_DECISIONS_2026_04_07.md — D1-D27 architectural decisions
- Design_Ca_Soma_Uarl_Reflection_Layer — CartON concept with Isaac's verbatim quotes
- Design_Yo_Mesh_Unification_Apr29 — Y-strata + O-strata unified representation
- Aligning_Carton_Primitive_With_Soma_Primitive — CartON-as-ONE-interface architecture
- /tmp/heaven_data/design_carton_unified_interface_apr23.md — full design doc

---

## Why Prolog, Not Python (The Final Answer)

**SOMA is CartON supercharged.** Same triple graph mechanism, but WITH programming types, codegen, AND convention rules that DIRECT you through everything.

### The Base Architecture Is Complete

Seven mechanisms handle EVERYTHING:
1. `triple(S, P, O)` — one mechanism for all facts
2. `check_convention(Name)` — universal rule dispatcher
3. `required_restriction(Type, Prop, Target)` — one fact per constraint
4. `unnamed_slot(S, P, T)` — automatic gap detection
5. `heal_unnamed` — automatic deduction from neighbors
6. `deduce_validation_status(C, Status)` — automatic SOUP/CODE tracking
7. `compile_to_python(C, Code)` — automatic codegen when ready

Adding a new type = adding FACTS (required_restriction entries). No new code. The existing rules handle it. Adding type 501 is the same effort as adding type 1.

In Python, adding a new type = new class + validators + imports + factory registration + pipeline wiring + tests. For EVERY type. It never ends.

### Directives From Gaps

The fundamental difference:

- **Python produces errors from violations** — "field is None, crash"
- **Prolog produces directives from gaps** — "concept needs has_url, nearest typed neighbor is Slack API, observe Slack endpoints next"

Constructive vs destructive feedback. SOMA tells you what to DO. Python tells you what you did WRONG.

### Situational Prompting

SOMA can require observation every turn and respond with exactly what you should do — because it knows:
- The full graph state
- What's missing (unnamed_slots)
- What's nearby (healing/neighbor deduction)
- What conventions apply
- What typing depth everything is at

This is a continuous directing engine. Not "validate this input" but "given everything I know, here is exactly what the LLM should do next, with exactly the context it needs."

Python almost never develops this kind of system without calling a logic engine. Building "figure out what to do next from graph state" in Python IS building a logic engine — just a worse Prolog.

### Pydantic Stack Core Relationship

SOMA discovers WHAT the types should look like (fields, constraints, relationships — from observations + convention rules). Pydantic_stack_core IS the output format (RenderablePiece subclasses with typed fields + render() method). SOMA generates the schema; pydantic_stack_core is the schema framework.

### The Python Abstraction Problem

In Python, every abstraction creates structural complexity (files, imports, modules, circular deps). Even when there's no logical conflict, structural conflicts emerge.

In SOMA, Entity is a holon — same structure at every level. triple(S, P, O) is the ONE mechanism. No imports, no circular deps. Adding a triple adds capability with ZERO structural overhead. The pattern is fractal — connecting a Process to Steps uses the SAME mechanism as connecting a Step to Methods.

---

## GIINT-to-Code Progressive Deepening (Apr 30 2026)

### Four Paths for GIINT Hierarchy Creation

1. **starlog init_project** — scaffold + GIINT project. Should USE CA to auto-create components from code structure (currently requires manual `architecture` param for features/components).
2. **colonize.py** — computes module→feature, class→component mapping from AST but DOES NOT PERSIST (line 155: "GIINT persistence is GNOSYS's job"). Gap: should pass computed mapping as `architecture` param.
3. **colonize-repo agent** — full Dyson Sphere colonization via starsystem-colonizer agent + Dragonbones ECs.
4. **CA auto-updates** — debounced queue flushes, pattern detection runs. Can detect new code NOT in GIINT yet → score the gap. "Find shit you missed."

### Progressive Deepening Levels

```
Level 0: Component exists but _Unnamed (CA auto-created from code structure)
Level 1: Named and described (GNOSYS/agent filled it from reading code)
Level 2: Mapped to code pattern (FOLLOWS_PATTERN edge from pattern_detector)
Level 3: Has deliverables reflecting the pattern
Level 4: Code verified against pattern (code_reality check passes)
------- component-level deepening complete above this line -------
Level 5+: Meta-information — how this component relates to higher systems,
          cross-repo dependencies, architectural patterns spanning multiple
          components. This is where SOMA's cross-system convention rules
          become necessary.
```

### Scoring

Each level of depth is scored on orient(). Health score reflects:
- How many components are undescribed
- How many patterns are not reflected as deliverables
- KG depth ratio (filled vs unfilled at each level)

CA auto-updates detect drift — every edit, new code that isn't in GIINT shows up as a gap in the score.

### The Key Refactor

init_project should auto-use CA to create components. colonize.py should pass its computed GIINT mapping through instead of discarding it. Then GNOSYS enters planning for all _Unnamed/placeholder entries.

String descriptions aren't eliminated — they progressively get REPLACED by pattern mappings as KG deepens. Score shows how much of codebase is structurally mapped vs just described in text.
