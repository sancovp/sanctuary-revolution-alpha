# YOUKNOW Architecture — Clean Design

## Three Tier System

### SOUP (Hallucination)
- Concept entered but missing OWL restrictions
- `is_a Hallucination` in domain.owl
- Auto-healer creates `_Unnamed` partials for missing required targets
- Progressive typing fills fields over time
- Arbitrary claims from LLM live here until verified

### CODE (Verified Executable)
- All OWL restrictions satisfied (SHACL passes)
- `codeness_gen` produces executable Python class
- Simulation runs (methods from relationships, LLM for untyped parts)
- Skills crystallize → mirror to `.claude/skills/` → rule created
- Flight_Configs become executable via waypoint
- Prolog_Rules become live in runtime
- **This is where things SHIP. Most work never needs to go beyond CODE.**

### ONT (Provably True)
- Derivation chain closes to Cat_of_Cat
- All relationship targets are also CODE or ONT
- Fractal EMR complete (EMR:[E[EMR]→M[EMR]→R[EMR]])
- Strong compression — full subgraph recursively typed
- Simulation runs WITHOUT LLM calls — fully self-sufficient
- Export pipeline: Prolog verifies → Pellet consistent → Crystal Ball math views → LEAN4 formal proof
- Each ONT admission tells Prolog "this pattern is proven, propagate everywhere"

## Layer Responsibilities

### OWL (uarl.owl + starsystem.owl + domain.owl → one World)
- **Type definitions**: what types exist, what relationships they have
- **Restrictions**: what fields MUST be present (structural truth)
- **Class hierarchy**: subClassOf, equivalentClass
- **Property definitions**: domain, range, transitive, sub-properties
- **NOT logic/rules/decisions** — those go to Prolog

### Pellet (via owlready2 sync_reasoner)
- **Consistency checking**: is the OWL model internally consistent?
- **Classification**: automatic subtype detection (anonymous classes)
- **Transitive closure**: is_a chain traces to Cat_of_Cat
- **Entailment**: what NEW facts can be derived from existing ones?
- **ONT determination**: does this concept satisfy the full derivation chain?

### SHACL (uarl_shapes.ttl)
- **Restriction checking**: does this concept have all required fields?
- **CODE determination**: SHACL passes = CODE tier
- **Explainable errors**: which restrictions are missing and why

### Prolog (PrologRuntime, rules.pl, Prolog_Rule_ concepts in domain.owl)
- **Logic/rules/decisions**: backward chaining "Y when X"
- **Deduction chains**: "since X entered, what else must be true?"
- **Composability detection**: "these 3 skills + this component = a plugin"
- **New type detection**: "Pellet found anonymous class, should we name it?"
- **Scoring/emanation queries**: "does this component have all 6 AI integration types?"
- **State machines**: replaces Python Griess constructor, OMNISANC zones, EMR progression
- **Dispatch**: "this needs CA check" → calls Python foreign function → gets result
- **Rules persist in ontology**: Prolog_Rule_ concepts load on init, live forever

### Python (compiler.py, add_concept_tool.py, substrate_projector.py, etc.)
- **IO**: read/write files, OWL loading, Neo4j queries, network calls
- **Thin router**: parse input → call Prolog → return result
- **OWL management**: owlready2 world creation, ontology saving
- **Foreign functions**: registered in Prolog for IO-bound operations
- **Daemon**: queue processing, skill crystallization, mirroring
- **NOT logic/rules/decisions** — those go to Prolog

## The Compile Path (Clean)

```
Input: "Skill_X is_a Skill, has_domain Paiab, ..."
                    │
                    ▼
    ┌─── PrologRuntime.validate() ───┐
    │                                 │
    │  1. Parse statement              │
    │  2. Assert facts into Prolog     │
    │  3. Check: is this a system      │
    │     type? (Skill_, Flight_,      │
    │     Prolog_Rule_)                │
    │     YES → Dragonbones shape      │
    │           gate already passed    │
    │     NO  → arbitrary claim        │
    │                                  │
    │  4. Call SHACL: restrictions?    │
    │     ALL MET → CODE tier          │
    │     MISSING → SOUP tier          │
    │                                  │
    │  5. If CODE: call Pellet         │
    │     Traces to Cat_of_Cat?        │
    │     YES → ONT tier               │
    │     NO  → stays CODE             │
    │                                  │
    │  6. Run deduction chains         │
    │     (SEPARATE from tier check)   │
    │     "What else is implied?"      │
    │     "New type detected?"         │
    │     "Emanation score?"           │
    │     These are Prolog queries     │
    │     that fire based on type      │
    │                                  │
    │  7. If Prolog_Rule_:             │
    │     assert rule body into        │
    │     live Prolog runtime          │
    │                                  │
    │  8. Return result:               │
    │     SOUP + what's missing        │
    │     CODE + deduction results     │
    │     ONT + proof status           │
    └─────────────────────────────────┘
                    │
                    ▼
    Persist to domain.owl (SOUP as Hallucination, CODE/ONT as entity)
    Persist to CartON queue (daemon processes)
```

## What Moves From Python to Prolog

These are currently Python if/elif chains that should be Prolog rules:

1. **EMR state determination** (`_emr_state_from_derivation` in compiler.py)
   - Currently: Python checks `has_programs`, `has_reifies`, etc.
   - Prolog: `emr_state(X, programs) :- has_rel(X, "programs", _).`

2. **Derivation level** (derivation.py `DerivationValidator.validate`)
   - Currently: Python walks L0→L6 checking dict keys
   - Prolog: `at_level(X, 3) :- has_rel(X, "is_a", P), traces_to_root(P).`

3. **Y-strata check** (derivation.py `for_y_strata`)
   - Currently: Python scans cat.entities for instances/generators
   - Prolog: `y4(X) :- has_rel(Y, "is_a", X), Y \= X.`

4. **Emanation scoring** (carton_sync.py `get_emanation_gaps`)
   - Currently: Python scans .claude dirs + string matching
   - Prolog: `has_emanation(C, skill) :- has_rel(S, "has_describes_component", C), has_rel(S, "is_a", "Skill").`

5. **Task readiness** (projects.py `_has_ready_tasks`)
   - Currently: Python walks nested dicts
   - Prolog: `ready_task(T) :- has_rel(T, "is_a", "GIINT_Task"), has_rel(T, "has_status", "Task_Ready").`

6. **Griess constructor phases** (griess_constructor.py)
   - Currently: Python state machine
   - Prolog: `griess_phase(X, verify) :- at_level(X, 4), shacl_valid(X).`

## What Stays Python

1. **OWL file loading** — owlready2 API
2. **SHACL validation** — pyshacl API
3. **Neo4j queries** — neo4j driver
4. **File IO** — reading/writing skills, configs, queue files
5. **Daemon** — queue processing loop
6. **Statement parser** — regex parsing of input strings
7. **Foreign functions** — registered in Prolog for IO operations
8. **codeness_gen** — Python class generation (output is Python)

## What Stays OWL

1. **All type definitions** — every class, every restriction
2. **All property definitions** — domain, range, characteristics
3. **GIINT hierarchy structure** — Project→Feature→Component→Deliverable→Task
4. **Skill structure** — 22 required fields
5. **Emanation types** — Hook, Subagent, Plugin, Skill, Flight_Config, MCP_Server
6. **Bootstrap** — Cat_of_Cat, Reality, Entity, core sentence entities

## Prolog Meta-Interpreter + Self-Reasoning

### Why Meta-Interpreter
Prolog needs to reason about its own rules — not just execute them. The meta-interpreter
lets the system watch itself think: trace proofs, explain conclusions, detect when it
can't proceed and needs the LLM, and modify its own rules at runtime.

### The Orchestration Loop (Prolog as Conductor)
```
Prolog detects "something new or missing"
    → calls Pellet about specific thing (via Python foreign function)
    → Pellet classifies (OWA: what COULD be true)
    → Prolog closes it (CWA: what IS true given Pellet's answer)
    → if new subclass/type detected:
        → call LLM to name it + write Prolog rules for it
        → assert new rules into live runtime
        → backtrace: verify everything still consistent
        → test: run meta-interpreter over new rules
        → validate: Pellet still consistent
        → continue from new world state
    → if missing fact:
        → raise "need LLM" request with proof tree of what's missing and why
        → LLM responds → Dragonbones → youknow → Prolog updated
        → loop continues
```

### OWL vs Prolog Boundary (Resolved)
- **OWL**: structural types, restrictions, property definitions. Knows Prolog_Rule_
  exists as a type, knows what each rule operates_on and produces_type. Does NOT
  encode operational logic.
- **Prolog**: ALL operational logic. When to call Pellet, when to call LLM, how to
  backtrace, how to test. Rules about rules. The meta-interpreter is itself a
  Prolog_Rule_ concept in the ontology — the system knows about its own
  orchestration as a typed entity.
- **Pellet**: classification + consistency. Called BY Prolog when Prolog detects
  something that needs OWA reasoning. Pellet never initiates — Prolog orchestrates.

### Everything Is Ontologized
The Prolog layer IS code in the overall program. It gets ontologized like everything
else. The meta-interpreter is a CODE tier entity. The rules it reasons about are CODE
tier entities. OWL knows about all of them. Nothing sits outside the ontology.

## Implementation Strategy: Fork, Don't Edit

### DO NOT refactor youknow directly.

Build a NEW standalone Prolog + blank OWL bootstrap system:
1. Start with a high-grade self-interpreting Prolog meta-interpreter
2. Blank OWL ontology (not uarl.owl — fresh start)
3. Test it works on its own as a toy
4. THEN figure out how to integrate/replace youknow pieces
5. Reference uarl.owl and existing youknow code for what we need
6. Everything discussed about youknow changes still stands — but we validate
   the architecture standalone before touching the production system

### Why Fork
- Youknow has 2260 lines of jumbled Python logic
- Editing it risks breaking what works (GIINT hierarchy, auto-healing, skill pipeline)
- A standalone system proves the architecture before we commit
- We can A/B test: new system vs youknow on same concepts

## For SOMA Specifically (Business Ontology Bootstrap)

The SOMA (business event/observation) ontology is the FIRST thing to build on the
new Prolog + OWL bootstrap system. This is where we start:

### Why SOMA First
- Clean domain with clear types (events, observations, metrics, content)
- No legacy code to work around
- Business value: the content pipeline, funnel analytics, user journey tracking
- Proves the architecture works before touching the AI infrastructure ontology

### SOMA Bootstrap Plan
1. Blank OWL with SOMA event types (Purchase, Signup, ContentView, JourneyStep, etc.)
2. Prolog meta-interpreter loaded
3. Prolog rules for: "when event X happens, what observations accumulate?"
4. Events enter → facts asserted → Prolog deduces observations → observations
   accumulate into typed concepts → concepts reach CODE tier → codeness generates
   simulation classes for business entities
5. The Prolog→Pellet→LLM loop fires when new event patterns are detected
   that don't match existing types

### SOMA → YOUKNOW Integration Path
Once SOMA works standalone:
- Import SOMA types into uarl.owl (or starsystem.owl)
- Prolog rules from SOMA become Prolog_Rule_ concepts in the shared ontology
- The meta-interpreter pattern proven in SOMA gets applied to the AI infrastructure
  ontology (skills, GIINT, starsystems, etc.)
- Gradually replace youknow Python logic with Prolog rules, one piece at a time

## Open Questions (Partially Resolved)

1. ~~Which Prolog meta-interpreter?~~ **RESOLVED**: SWI-Prolog composed stack. See MI Selection below.

2. How does domain.owl scale? Currently 108KB + SOUP concepts. At 1M concepts ~500MB.

3. ~~codeness_gen interaction with tiers?~~ **RESOLVED**: See y_mesh section below.

4. How does Prolog interact with CartON (Neo4j)? Currently Prolog loads from OWL
   and in-memory facts. Should it also query Neo4j directly for large-scale graph
   operations?

5. ~~SOMA event types?~~ **RESOLVED**: See SOMA MVP below.

---

## Three Ontology Layers (TWILITELANG / SOMA / UARL)

Three layers, separate but aligned:

### TWILITELANG (Parent Abstraction — OPEN, publish it)
- The meta-compilation ontology. "What it is and how it goes."
- Defines: compilation stages, evolution walks, rollup patterns, inclusion maps
  as Aut constraints on futures, transformational wisdom intent
- Required by SOMA. SOMA cannot exist without TWI abstractions.
- This is the THEORY — how compilation through partials works, how strata of
  orders relate, how history compiles and serves itself
- From Isaac: "Self-Invented Super-Reification Language of the Crystal Ball that
  is the Wisdom Maverick's Mind."

### SOMA (Child Product — requires TWI)
- Self-Organizing Meta-Architecture
- The EVENT and OBSERVATION system specifically
- EventPrimitive → Observation → Process → CodifiedProcess → ProgrammedProcess
- Programming typology restrictions (str, int, float, bool, list, dict)
- THIS is what clients interact with. This is the product surface.

### UARL (Secret Extension — our internal moat)
- PIO entities, ABCD isomorphism, Futamura projections, bootstrap axioms
- Extends TWI with the full metaphysical machinery
- Clients NEVER see this. It's what gives US superpowers over the system.
- YOUKNOW validates against UARL. The product validates against SOMA.

**Hierarchy**: UARL extends TWI. SOMA requires TWI.
**Client sees**: SOMA (events/observations) displayed through Crystal Ball.
**We see**: UARL (full machinery) operating through YOUKNOW.
**Both share**: TWI (the abstraction layer that makes compilation work).

---

## SOMA: The Any→Code Compilation Pipeline

### Typed Observations (The Foundation)

SOMA observations take TYPED primitives, not arbitrary semantic strings.
The primitive types are: `str`, `float`, `int`, `bool`, `list`, `dict`.
When something enters as `str`, that IS its type — not "unknown."
`Any` means the PROGRAMMING `Any` — a union type, not a semantic wildcard.
The agent DECLARES the type at observation time.

```
observe(user_42, purchased, product_x, amount=49.99)
                                        ^^^^^ float — KNOWN at entry
```

### The Three Compilation Stages

```
Stage 1: Process (SOUP)
  - Semantic description from accumulated typed observations
  - "What does this pattern of events mean?"
  - Triggered by: accumulation threshold of typed observations

Stage 2: CodifiedProcess (TYPED)
  - Agent reads semantic description
  - Outputs: Pydantic data models, step sequence, I/O types, validation rules
  - Triggered by: Process exists + requires ai_evolution
  - These ARE Automation logic rules → go to Prolog

Stage 3: ProgrammedProcess (CODE)
  - Human approves (authorization gate)
  - Agent outputs actual Python that renders at runtime
  - Triggered by: CodifiedProcess + authorized by human
  - Wrap in SDNAC to agentify
```

Each stage is an OWL class. Each arrow is an agent run. Human authorization
gate between Codified and Programmed.

### Runtime Codegen

OWL Process-kind classes become methods on generated Pydantic models.
Data-kind become fields. The model IS the typed SOP IS the automation target.

---

## Prolog Is THOUGHT, CartON Is MEMORY

CartON stores concepts. Prolog propagates implications across all partials.
Right now we have memory without thought — concepts enter CartON and nothing
else happens.

### The Propagation Problem (Current)

```
Agent emits Design_X
  → Dragonbones compiles to CartON
  → ... NOTHING ELSE HAPPENS
  → 193 pending tasks sit there unchanged
  → Nobody checked if Design_X unblocks any of them
```

### The Propagation Solution (Target)

```
Agent emits Design_X
  → Dragonbones compiles to CartON
  → Prolog receives: new_concept(Design_X, is_a=Design, part_of=Project_Y)
  → Prolog checks ALL partials across ALL goals:
      - Task_A: RELEVANT — this design constrains it → update
      - Task_B: RELEVANT — dependency resolved → UNBLOCK
      - Concept_C: RELEVANT — gap filled → advance toward CODE
      - 12 more concepts relate...
  → Each partial that CAN'T advance produces:
      failure(Partial_Z, missing(has_implementation))
  → When that missing thing arrives later → auto-fires
```

Every Dragonbones entity chain emission IS a SOMA observation that should
propagate. Current: emit → compile → store → stop.
Target: emit → compile → store → Prolog sweep → advance partials →
dispatch actions → new observations → loop.

---

## The SOMA→Prolog→CAVE Closed Loop

```
OBSERVE (typed primitives: str, float, int, bool, list, dict)
    → simultaneously: Pydantic model + Prolog facts + OWL individual

PROCESS (semantic description from accumulated observations)
    → "what does this pattern mean?"
    → agent answers → CodifiedProcess

CODIFIED PROCESS (typed I/O, step sequence, validation rules)
    → "how does this run?"
    → these ARE Automation logic rules
    → rules go to PROLOG

PROLOG (brain — dispatches decisions)
    → rules interact with each other
    → deductions fire
    → "since X AND Y, dispatch Z"
    → dispatches to...

CAVE AGENT (universe/runtime — WakingDreamer)
    → can call ANYTHING globally
    → Organs = specialized dispatchers
    → Automations = the crystallized processes

PROGRAMMED PROCESS (CODE — human-approved Python)
    → becomes an Automation in CAVE
    → Prolog rule controls when it fires
    → OWL knows it exists and what it does
    → execution produces NEW observations → loop closes
```

---

## y_mesh: Prolog's LLM Integration Layer

### What y_mesh Is

y_mesh = Yo_strata + LLM integration, living INSIDE Prolog. When Prolog
determines something needs to be generated, it doesn't just fail or
dispatch to the main agent. It calls an LLM INTERNALLY.

### How y_mesh Works

```
1. Prolog decides "I need X generated"
2. Queries OWL/Pellet: "what does X need? what's missing?"
   → OWL returns: Yo_strata (the consistency requirements)
3. y_mesh calls LLM via Janus Python bridge (NOT the main agent)
   with strata requirements as constraints
4. LLM generates the thing (codeness/codegen)
5. Result goes through YOUKNOW validation
6. If valid → assertz into Prolog + persist to OWL
   If invalid → retry with different constraints, or escalate
```

### Two Kinds of LLM Calls

1. **y_mesh internal calls** — Prolog decides, calls LLM, gets result,
   validates, asserts. Agent never sees this. System THINKING autonomously.

2. **Main agent dispatch** — Prolog decides this needs the full agent
   with tools. Dispatches to CAVEAgent/WakingDreamer. System ACTING.

### OWL Holds Yo_strata, Prolog Holds y_mesh

OWL/Pellet provides the consistency requirements (what shape must the
answer have). Prolog's y_mesh provides the orchestration (when to call
LLM, with what constraints, what to do with the result). This separation
means OWL stays declarative and Prolog stays procedural.

---

## Evolutionary Self-Programming

### The Core Insight

In any LLM-connected program, every output contains fragments that COULD
be inputs to other parts of the system. Right now we manually wire these
connections. Prolog doesn't hardcode lifts — it DISCOVERS them.

### How It Works

```
New fact arrives: observation(user_42, purchased, product_x, amount=49.99)

Prolog already has:
  needs_invoice(User) :- observation(User, purchased, _, amount=A), A > 0.

Automatically:
  needs_invoice(user_42) becomes TRUE → dispatch(billing_agent, ...)
```

Nobody programmed "when purchase → invoice." The rule existed. The fact
arrived. The conclusion FELL OUT.

### The Evolutionary Part

```
Prolog detects: observation(_, refund_requested, _, _) has no matching rule
  → failure-as-data: structured "what failed and why"
  → dispatch to y_mesh LLM: "what should happen on refund_requested?"
  → LLM generates: needs_refund_review(User) :- observation(User, refund_requested, _, _).
  → assertz into live Prolog runtime
  → NOW it fires automatically forever
```

The system programs itself by:
1. Observing what it does and fails to do
2. Asking LLM to fill gaps (via y_mesh)
3. Asserting fills as permanent rules
4. Proof trees from MI are THEMSELVES typed observations
5. Rules about rules emerge from meta-level observation

---

## Automations vs Simulations (SOMA MVP)

### Two Zones

**INSIDE the system = AUTOMATIONS**
- Touch the real world (send emails, update DBs, dispatch agents)
- GNOSYS must approve integration
- y_mesh CANNOT auto-generate without permission
- Permission = Prolog rule checking authorization

**OUTSIDE the system = SIMULATIONS**
- Generated standalone code
- y_mesh CAN auto-generate when Pellet infers completeness
- Published as standalone artifacts
- Nobody asked — it just fell out of the ontology

### Pellet Completeness Inference → Auto-Codegen Permission

```
1. User describes Dog in ontology (typed observations accumulate)
2. Pellet checks: are ALL partials complete for Dog?
   - All required relationships present?
   - All process descriptions typed?
   - All subtypes enumerated?
3. If COMPLETE → Prolog rule fires:
   can_auto_codegen(Dog) :- partials_complete(Dog),
                            not(is_automation(Dog)).
4. y_mesh generates Dog simulation (code, tests, docs)
5. Published as artifact — nobody asked

6. Later, user says "make Dog an automation":
   → GNOSYS reviews the simulation
   → Integrates into CAVE as Automation
   → Marks as is_automation(Dog)
   → Future changes require approval
```

### Recursive Bootstrap

Once Dog simulation works, the PROOF (test results, type completeness)
becomes an observation → enters Prolog → other partials that DEPENDED
on Dog existing now advance → maybe Cat was waiting on "animal agent
pattern proven" → Cat auto-codegen unlocks.

### SOMA MVP Definition (Scoped: BI + SOP Generation)

The MVP is NOT agentic code gen. The MVP is a BI tool.

**What it does**: Everyone in the business talks to Claude about what
happens in their work. These conversations are typed SOMA observations.
Events accumulate → system builds out BI (employees, processes,
relationships, requirements) → detects missing SOPs it KNOWS EXIST
from event patterns → generates SOPs as code (CodifiedProcess).

**The pitch**: "Get your BI up to 2026 and prepare for the next 100 years."

**Three-tier offering**:

1. **BASE ($1k/yr per user)**: Employees talk → SOMA events → BI built
   out → missing SOPs generated as code. This is the product.

2. **UPSELL (per-engagement)**: Individual SOP automation — "How far is
   SOP X from becoming an AI integration? Here's the quote." Check
   Pellet completeness of partials, quote the gap.

3. **ULTIMATE (agency model)**: Full autonomous AI integration — system
   auto-codegens simulations, integrates as automations, bootstraps
   recursively. The UNICORN: 1M users × $1k/yr.

The agentic codegen (Dog example, full simulations, recursive bootstrap)
is the ULTIMATE plan. The MVP is just: events → BI → SOPs → done.
AI automation is the UPSELL, not the base product.

---

## MI Selection: SWI-Prolog Composed Stack (RESOLVED)

### Decision

No single production MI meets all requirements out of the box. SWI-Prolog
provides composable pieces that together cover everything.

### Components

| Piece | Source | Status |
|-------|--------|--------|
| MI with proof trees | EXSHELL `build_proof/3` (Luger, UNM) or ACOMIP `mi_tree` (Neumerkel) | ~50 lines Prolog, textbook standard |
| CLP typed facts | SWI-Prolog CLP(FD) + CLP(R) + clpBNR pack | Built-in, Triska wrote CLP(FD) |
| Self-modification | Native `assertz/retract` | Just how Prolog works |
| Structured dispatch | Prolog terms → JSON via `library(http/json)` | Native |
| Failure-as-data | ~20-30 lines custom wrapper | Only custom piece needed |
| Python interop | Janus v1.5.2 (`pip install janus-swi`) | Official bridge, bi-directional |
| OWL export | Thea library for SWI-Prolog | Full OWL2 support |
| Foreign function mid-proof | Janus allows Prolog→Python→LLM mid-execution | For y_mesh LLM calls |

### MI Hard Requirements

1. **Typed facts / CLP** — observations carry float, int, str, not just atoms
2. **Proof tree export** — every derivation produces reifiable trace
3. **Self-modification** — assert new rules at runtime from LLM output
4. **Structured dispatch** — conclusions are dispatch(agent, action, params)
5. **Failure-as-data** — failed proofs produce structured "what's missing"
6. **Foreign function mid-proof** — call Python/LLM during proof execution

### What We Build (~30 lines custom)
- Failure-capture wrapper around MI
- Proof tree → OWL individual mapping
- Dispatch term format convention

### What We DON'T Build
MI itself, CLP solver, Python bridge, OWL serializer — all exist.

### Sources
- ACOMIP: https://www.complang.tuwien.ac.at/ulrich/prolog_misc/acomip.html
- EXSHELL: https://www.cs.unm.edu/~luger/ai-final/code/PROLOG.exshell_full
- Janus: https://pypi.org/project/janus-swi/
- Thea: https://github.com/vangelisv/thea
- clpBNR: https://www.swi-prolog.org/pack/list?p=clpBNR

### Disqualified Candidates
- Scryer Prolog: No Python interop
- SICStus: Commercial license
- miniKanren: Wrong paradigm (relational, not dispatch)
- FTCLP: Abandoned (2015)
- XSB: Tabling good but SWI imported it, weaker ecosystem
