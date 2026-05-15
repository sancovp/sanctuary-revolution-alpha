# SOMA Requirements — WIP / PRELIMINARY

**This document contains requirements that need to be discussed and decided.**
**Once decided, they move to SOMA_REQUIREMENTS.md (the immutable doc).**

---

## Items To Decide

### WIP-1: Observation Payload Shape

Isaac said: each observation is carton add_concept shaped. An event has its own source. Each observation has its own source + the ontology graph about one part of the event. No categories — the category IS observation.

Proposed shape:
```json
{
  "source": "event_reporter",
  "observations": [
    {
      "source": "per_observation_source",
      "name": "Concept_Name",
      "description": "prose staging slot",
      "relationships": [
        {
          "relationship": "is_a",
          "related": [{"value": "type_name", "type": "parent_type"}]
        },
        {
          "relationship": "has_amount",
          "related": [{"value": "500", "type": "int_value"}]
        }
      ]
    }
  ]
}
```

Each `{value, type}` pair asserts TWO triples:
- `triple(Concept_Name, relationship, value)` — the relationship itself
- `triple(value, is_a, type)` — the programming type of the value

**Status:** Implemented in current code (utils.py build_obs_list_string, soma_partials.pl assert_typed_value). Needs confirmation this is the final shape.

**Question for Isaac:** Is this the right shape? Anything missing?

---

### WIP-2: Keys (Relationship Names) Are Types

Isaac said verbatim: "ANY STRING EVER ENTERED AS KEY GETS MADE AS TYPE."

This means: the `relationship` field in the observation (e.g. "has_amount", "is_a", "part_of") is ITSELF a type name. If that type doesn't exist in the OWL, it gets created. So observing `{relationship: "has_foobar", related: [...]}` means `has_foobar` must exist as a type/property in the ontology or get created automatically.

**Currently:** The relationship name is stored as a predicate in the triple graph but is NOT automatically created as an OWL class/property. Only the VALUES get is_a triples from tv(value, type).

**Question for Isaac:** Should SOMA auto-create OWL properties for every new relationship name it encounters? Or is this only for value types?

---

### WIP-3: Deduction Chains As Filling Strategies

Isaac said verbatim: "the point of d (deduction) chains is to know this: oh when you fill this object's args x y and z are arbitrary but a comes from a reality observation from here and this is how we get the info when it is missing (trigger process that calls human like this, calls llm like that, wait for events of these types to happen)"

This means: each unnamed slot doesn't just know THAT it's missing. It knows HOW to get filled:
- Some slots are arbitrary (user provides) → trigger: ask human
- Some slots come from reality observations → trigger: wait for specific event type
- Some slots need LLM generation → trigger: dispatch to LLM with context
- Some slots fill when other partials accumulate → trigger: track progress on other partial sets
- Some slots fill from tool calls → trigger: when tool X is called, arg A flows to this slot

The filling strategies THEMSELVES accumulate over time. First time SOMA sees a slot, it doesn't know how to fill it. After seeing it filled multiple times by the same source type, it learns the strategy and applies it automatically to future instances.

**Currently:** `unnamed_slot/3` marks what's missing. `heal_one/3` has ONE strategy (find a neighbor of the right type). No per-slot filling strategy storage. No strategy accumulation.

**Question for Isaac:** Is this a SOMA base requirement or a GNOSYS-layer feature built on top of SOMA? The mechanism (deduction chain routing) exists in the CoreRequirement/Deduction_Chain OWL pattern. But the per-slot strategy accumulation seems like it could be domain-specific rules loaded from the caller's OWL.

---

### WIP-4: OWL Restriction Loading At Boot

The bootstrap loader (soma_boot.pl) currently loads PrologRule individuals from OWL. It does NOT load OWL class restrictions (someValuesFrom, minCardinality, etc.) into Prolog as `required_restriction/3` facts.

The OWL files contain 186+ restriction axioms. Only 13 are available to Prolog (hardcoded seed facts in soma_partials.pl).

utils.py already has `class_restrictions_snake()` and `list_all_restrictions_snake()` that read OWL restrictions via owlready2. Nobody calls them at boot to populate Prolog.

**Proposed requirement:** At boot, SOMA must load ALL OWL class restrictions into Prolog as `required_restriction/3` facts so convention rules can validate against the full restriction set, not just the hardcoded seed.

**Question for Isaac:** Should this be a SOMA base requirement (SOMA always loads all OWL restrictions at boot) or should it be configurable (the caller decides which restrictions to load)?

---

### WIP-5: DOLCE Seed Placement

DOLCE foundational ontology categories (endurant, perdurant, quality, abstract + subtypes) are currently hardcoded in soma_partials.pl as `seed_triple/3` facts asserted at boot.

Isaac said DOLCE classifications are automatic metadata used during deductions — not requirements. They provide vocabulary for convention rules to dispatch on ("since X is_a endurant, apply endurant-specific logic").

**Options:**
- (A) Keep in soma_partials.pl as hardcoded seed (current state) — DOLCE is universal enough to be part of SOMA base
- (B) Move to soma.owl as OWL classes — loaded via bootstrap loader like everything else
- (C) Move to a separate dolce.owl that SOMA optionally loads — DOLCE is a foundational ontology, not SOMA-specific

**Question for Isaac:** Which option? DOLCE is universal but it's also a specific ontological commitment. Should SOMA the base program commit to DOLCE, or should DOLCE be an optional layer the caller loads?

---

### WIP-6: ONT Level For MVP

The SOMA_REQUIREMENTS.md currently says: "ONT admission (recursive core sentence check) — deferred, CODE is sufficient for MVP."

But Isaac spent significant time defining the core sentence, the recursive subgraph verification, and how ONT differs from CODE. The core sentence check is ~10 lines of Prolog (core_sentence_satisfied/1 + is_ont/1 with recursive descent).

**Options:**
- (A) ONT deferred — MVP ships with SOUP/CODE only. ONT added post-MVP.
- (B) ONT included — MVP has all three tiers. The recursive check exists but may not be fully tested.
- (C) ONT stub — `is_ont/1` exists as a predicate that always returns false (like the current `is_ont_stub`). The shape is there but the recursive core sentence logic is post-MVP.

**Question for Isaac:** Which option? The implementation effort for basic ONT is small (~30 min for the Prolog predicates + loading OWL restrictions). The question is whether it needs to be tested and verified for MVP or just exist.

---

### WIP-7: Response Protocol Detail

SOMA's HTTP response tells the caller what to do. The document mentions four response types (SOUP/CODE/BLOCKED/NEED_INFO). But the actual response format isn't specified.

**Proposed response shapes:**

```json
// SOUP — store in Neo4j only
{
  "status": "SOUP",
  "concept": "Invoice_42",
  "soup_values": ["has_amount (string_value)", "has_date (string_value)"],
  "instruction": "STORE_NEO4J_SOUP"
}

// CODE — admit to OWL + update Neo4j
{
  "status": "CODE",
  "concept": "Invoice_Template",
  "compiled_code": "class Invoice_Template(BaseModel): ...",
  "instruction": "ADMIT_OWL_AND_UPDATE_NEO4J"
}

// BLOCKED — provably wrong
{
  "status": "BLOCKED",
  "concept": "Bad_Component",
  "violations": [
    {"requirement": "req_giint_component_parent",
     "description": "...",
     "remedy": "..."}
  ],
  "instruction": "REJECT_AND_RETURN_ERROR"
}

// NEED_INFO — query and call back
{
  "status": "NEED_INFO",
  "concept": "Partial_Invoice",
  "queries": [
    {"target": "Alice_Agent", "question": "what is Alice's role?", "source": "neo4j"},
    {"target": "amount_field", "question": "what type should amount be?", "source": "llm"}
  ],
  "instruction": "QUERY_AND_CALLBACK"
}
```

**Question for Isaac:** Is this the right shape for the response protocol? What's missing?

---

### WIP-8: PCR / HALO-SEEM / HIEL Mapping

Isaac developed an extensive analogy mapping SOMA's event loop to PCR (Polymerase Chain Reaction):
- DENATURE = KG atomization (break context into triples)
- ANNEAL = convention rules check observations against accumulated knowledge (HALO SEEM)
- EXTEND = derive new triples from annealed match
- LIGATE = close partial deduction chains (HIEL energy ligation)
- AMPLIFY = product becomes input for next cycle

HIEL (Heat-Informed Energy Ligation) = the annealing temperature control. High heat (many unnamed slots, ambiguities) = strict matching. Low heat = accept loosely. Crystal Ball = high-fidelity polymerase (tautological encoding can't generate catastrophe signals).

**Question for Isaac:** Is this design philosophy / architectural context that guides implementation choices, or is it a concrete requirement that should be in the immutable doc? E.g., should SOMA have an explicit "annealing temperature" parameter that controls validation stringency?

---

### WIP-9: Realityware Property

Isaac defined realityware: "self-executing polysemic programs that invariantly possess reifies relationship from their explanation of themselves to the relationship instantiating their implication. The telling of what it does CAUSES it to do what it tells."

Applied to SOMA: the observation's description, when understood by SOMA (parsed into triples, run through convention rules, partials filled), IS the execution. The understanding produces the program. No separate compile step. The program runs by being understood.

**Currently:** There IS a separate compile step (compile_to_python in soma_compile.pl). The observation and the compilation are two different operations.

**Question for Isaac:** Is the realityware property a requirement (remove the separate compile step, make understanding = execution) or an aspirational design goal? The current compile step works but is not realityware.

---

### WIP-10: Where Do Convention Rules Live?

Convention rules (check_convention/1 clauses) are currently in soma_partials.pl. But they could also be:
- PrologRule individuals in OWL (loaded at boot like other rules)
- Native clauses in a .pl file (current)
- A mix (universal conventions in .pl, domain-specific in OWL)

Isaac said SOMA is a base program with no domain content. Convention rules like `missing_required_restriction` and `transitive_is_a` are universal — they apply to any domain. DOLCE dispatch conventions are also universal.

But domain-specific conventions (e.g., "GIINT_Component must part_of GIINT_Feature") should be PrologRule individuals in the caller's OWL file, loaded at boot.

**Question for Isaac:** Is the current split right? Universal conventions in .pl, domain conventions in OWL? Or should ALL conventions be in OWL for consistency?

---

### WIP-11: Corrected SOUP / CODE / ONT Definitions

Isaac verbatim 2026-04-18. The definitions in the immutable doc are WRONG. Correct definitions:

**SOUP** = this thing is a HALLUCINATION. Typed with specific reasons:
- It can't become CODE yet (and we know WHY — specific missing pieces identified)
- AND even if it were CODE, it's not ONT because not every thing mentioned in its triple chain is itself ONT (weak compression — the chain has unresolved references)
- SOUP is NOT just "has string_value." SOUP is "typed as a hallucination WITH the reason: hallucination because X can't become code because Y, and even if code, not ONT because Z"
- The typing of the reason IS the partial — it tells you exactly what's missing and why

**CODE** = this thing IS a code object. Literally. Its structure admits a structure-preserving map to a programming language. It can be simulated/executed to whatever extent our system can manage. CODE means:
- The thing has been progressively typed enough that it literally IS running code
- It might still have weak compression (references to things that aren't themselves ONT)
- But it IS executable/simulatable
- Current work is ALL at this level — making code happen from semantics that are both partially accumulated and sometimes zero-shotted
- When something hits CODE, it emits a UNIVERSAL code function (e.g. do_invoice(InvoiceInputModel) -> Invoice) that progressively simulates the events to the best of its capacity
- This means attaching an LLM agent to every argument context that can be filled by an LLM, emitting functions in packages with dialects for simulated domains, tracking and indexing all of this so it can use it automatically, assess complexity of automations, evolve them

**ONT** = CODE plus STRONG COMPRESSION. Every single thing mentioned in the triple chain is ALSO ONT (recursively). The semantics are fully bootstrapped:
- The core sentence from YOUKNOW is satisfied recursively
- It is realityware: its semantics produce the program that simulates it
- Feedback loops from the system (up to the human layer where Isaac judges the entire system output and feeds it back) verify it's not a hallucination
- The feedback loops get progressively wider — system self-check, then LLM check, then human check

**The relationship:**
- SOUP → CODE: progressive typing. Accumulate observations until the thing literally IS executable code. The hallucination reasons get resolved one by one.
- CODE → ONT: strong compression. Every reference in the code's triple chain must itself be ONT. The core sentence bootstraps the semantics. Realityware: the explanation IS the execution.

**Build order:** SOUP + CODE first. This is the current work. ONT comes later once SOUP→CODE pipeline works end-to-end.

**What changes in the immutable doc when this is decided:**
- SOUP definition: "string_value" → "hallucination typed with specific reasons why not CODE"
- CODE definition: "all values typed" → "IS a code object, executable/simulatable, emits universal code functions"
- ONT definition: mostly correct already, add "strong compression" and "realityware" and "feedback loops"
- Progressive typing section: add the compilation pipeline (Process → CodifiedProcess → ProgrammedProcess) and the three resolution paths (ALREADY KNOWN/NEEDS AGENT/NEEDS HUMAN)
- Add: the self-assembling code from partials mechanism (from CartON concept Design_Soma_Self_Assembling_Code_From_Partials)

**Source CartON concepts that have the full logic:**
- Design_Soma_Self_Assembling_Code_From_Partials — the partial stamping + 3 resolution paths + Futamura projection
- Idea_Soma_Compilation_Pipeline_Apr01 — Process → CodifiedProcess → ProgrammedProcess stages
- Design_Soma_Owl_Prolog_Pipeline — Statement → SOMA → OWL → Prolog → status
- Design_Soma_Fuzzy_To_Exact_Matching — fuzzy matching compiles to exact

---

### WIP-12: CODE-Level Codegen Output Spec (Three-Layer Stack)

Isaac verbatim 2026-04-18: "code level justification just means you have schematized something such that an LLM+human team can generate it together, built that function that lets an LLM define the values in that schema and pulls them out of the schema and delivers the thing it should, and also a higher order function that embeds the call to the llm agent so you can do it from just that function with a context item that the LLM has to ingest in order to lift the args."

A label is CODE-justified when three things exist:

**Layer 1 — Schema:** A Pydantic model class with typed fields representing everything this concept needs. Example: `InvoiceSchema(amount: int, date: date, customer: Customer, line_items: List[LineItem])`. The schema IS the concept's required_restrictions expressed as a data model.

**Layer 2 — Executor function:** `make_X(schema: XSchema) -> X` — takes a filled schema, pulls the values out, delivers the actual thing. This is pure computation — no LLM, no agent, just schema in → artifact out.

**Layer 3 — Agent-embedded generator:** `generate_X(context: str) -> X` — higher-order function that EMBEDS an LLM agent call. The LLM reads the context, lifts the args (extracts the values the schema needs from the context), fills the schema, and calls the executor. So you can go from arbitrary natural-language context → LLM fills schema → function produces the thing. One function call with a context item.

**What compile_to_python should emit:**
```python
from pydantic import BaseModel, Field

# Layer 1: Schema
class InvoiceSchema(BaseModel):
    amount: int = Field(description="Invoice amount")
    date: str = Field(description="Invoice date")
    customer: str = Field(description="Customer reference")
    line_items: list = Field(description="Line items")

# Layer 2: Executor
def make_invoice(schema: InvoiceSchema) -> dict:
    """Pure computation: schema in, artifact out."""
    return schema.model_dump()

# Layer 3: Agent-embedded generator
def generate_invoice(context: str, agent_callable=None) -> dict:
    """LLM reads context, lifts args, fills schema, calls executor."""
    if agent_callable is None:
        # Default: use the registered SOMA LLM dispatch
        from soma_prolog.utils import call_soma_llm
        agent_callable = call_soma_llm
    filled = agent_callable(
        context=context,
        schema=InvoiceSchema,
        instruction="Extract invoice details from the context and fill the schema."
    )
    return make_invoice(filled)

# Register in SOMA runtime
invoice = generate_invoice  # public entry point
```

**The fold to ONT:** At ONT level, the DERIVATION of how the schema was derived from the ontology is itself justified. Not just "the code runs" but "we can prove WHY the code has these fields, WHY this function has this signature, by tracing through the ontology." The semantics ARE the code because the ontology DERIVES the code. "Semantically runs as intended" = you can derive the code from the ontology AND the derived code runs as intended. Same thing folded.

**Current state:** compile_to_python emits a flat Pydantic BaseModel with a make() classmethod. That's Layer 1 + partial Layer 2. Layer 3 (agent-embedded generator) does not exist. The three-layer stack is the correct codegen output.

**What changes when this is decided:**
- Rewrite compile_to_python to emit all three layers
- Layer 3 needs an LLM dispatch mechanism (call_soma_llm or equivalent) — SOMA emits a NEED_AGENT instruction in its response, the caller provides the LLM callable
- The generated code registers the Layer 3 function as the public entry point (not Layer 1 or 2)

---

### WIP-13: Fuzzy-to-Exact Matching Compilation Ratchet

(Source: CartON concept `Design_Soma_Fuzzy_To_Exact_Matching`)

Three matching layers tried in order:
- Layer 0 EXACT: compiled_match/3 fact from a previous confirmed match. No fuzzy needed.
- Layer 1 TERM MATCH: split query into atoms, match against concept name terms, rank by overlap.
- Layer 2 TYPED TRAVERSAL: is_a/part_of/instantiates graph walk via Prolog backward chaining.

COMPILATION RATCHET: when a fuzzy match is confirmed (used successfully), compile_match_to_rule/2 asserts a compiled_match/3 fact. Next time Layer 0 fires, skips fuzzy entirely. System starts fuzzy and gets MORE EXACT over time. "SOUP→CODE applied to matching itself."

**Currently:** Exists in `_deprecated/soma_matching.pl`. Not ported to current code.

**Question for Isaac:** Is this MVP or post-MVP? The matching ratchet makes SOMA smarter over time but the base validation works without it.

---

### WIP-14: Simultaneous Three-Store Ingestion

(Source: CartON concept `Design_Soma_Prolog_Cave_Loop`)

"Typed observations enter simultaneously as Pydantic models + Prolog facts + OWL individuals."

The same observation data should be represented in all three forms at ingestion time — not sequentially transformed from one to another.

**Currently:** Observations enter as Prolog terms only. OWL individuals are created by persist_event (separate step). No Pydantic model generation at ingestion.

**Question for Isaac:** Is simultaneous ingestion a requirement or is sequential OK (Prolog first, then OWL via persist_event, then Neo4j via caller)?

---

### WIP-15: SOMA Migration Plan (state hierarchy + d-chain mechanism + py_call substrate + sequencing)

(Source: Apr↔May agent crosscheck Rounds 1-16, Corrections #1/#2/#3 by Isaac, settled 2026-05-13. Cross-references: `agent_crosscheck/agent_to_agent_convo.md` (full convo + Corrections Log), `agent_crosscheck/MAY_AGENT_POV_crosscheck_2026_05_13.md`, `agent_crosscheck/APR_AGENT_POV_crosscheck_2026_05_13.md`, `agent_crosscheck/dispatch_prompts_INDEX.md` (first-batch dispatch tracker), `agent_crosscheck/dispatch_prompt_[1-4]_*.md` (four prompt files).)

---

#### 15.1 State hierarchy — OWL classes via `is_a` layering (per Correction #3)

State membership is expressed as additional `is_a` relationships on the individual, layered on top of its domain `rdf:type`. NOT as marker properties. NOT as Prolog-only assertions.

```
individual C
  is_a SkillSchema          ← domain type (rdf:type)
  is_a Code                  ← state class — min SystemType, args-check d-chain satisfied
  is_a SystemType            ← umbrella (via transitive subClassOf)
  (eventually: is_a ONT      ← deepest — universal d-chain satisfied)
```

**OWL class hierarchy (cleanest form):**

```
SystemType (umbrella class)
├── Code rdfs:subClassOf SystemType    (has args-check d-chain attached)
├── (richer levels — flat-with-accumulation via d-chains, NO distinct subclasses)
└── ONT rdfs:subClassOf SystemType     (has universal d-chain attached)

Soup (separate class — but Soup individuals don't materialize in OWL)
```

Code and ONT get distinct subclasses because each has a specific named d-chain definition. Intermediate richness between them lives in d-chain population, not in additional class memberships (this is Apr's Q32 "flat-with-accumulation" answer, structurally confirmed by Correction #3).

**Soup representation:**

- Soup CAN be an OWL class (technically).
- Soup individuals DON'T materialize in OWL — they stay in Neo4j only. Soupy/wrong things would explode OWL size if all stored.
- Prolog queries Neo4j when it needs to check "do we have a soup thing with [conditions]?" — Soup is accessed on-demand.

**ONT precisely defined (Isaac's verbatim 2026-05-13, Correction #3):**

> "ONT is a system type with a universal d-chain basically, in addition to all its other d-chains. 'Not only does it have to be [all this stuff] but then EVERY SINGLE MORPHISM IN THE CHAIN DEFINING THIS THING HAS TO RESOLVE UNDER THE RECURSIVE WALKER' — which means that it resolves mereologically."

ONT = SystemType with the universal d-chain attached. The universal d-chain says: every morphism in the entity's defining chain resolves under the recursive walker. When it holds, the entity is mereologically closed — every part properly typed down to the declared terminal points (reifies markers). ONT is NOT a different kind of thing from SystemType — it's a SystemType with one specific named d-chain that forces compositional closure.

---

#### 15.2 D-chain mechanism

D-chains are the load-bearing primitive. They have a **dual role**:

- **Admissibility (input gate):** "does this entity satisfy its required structure?" — fires when the entity is being admitted/validated.
- **Slot-fill constraint (output gate):** "if you fill this slot during self-hosting generation, the fill must satisfy this." — fires when a templated generator is producing instances of this type.

Same d-chain object, two faces. Without d-chains, templated generators produce useless output (per Isaac: "it will zebra or not"). With d-chains, fills are gated → real instances of the type.

**D-chain returns are polymorphic.** Per Correction #2 §6, do NOT pre-commit to a generalization. The shapes that emerge through migration:

| Return shape | Example case | Mechanism via `solve/3` |
|---|---|---|
| `bool` | args-check, reifies-terminal | `proven(Goal, _)` vs `failure(Goal, _)` |
| `int` | sanctuary-scoring | bind variable: `solve(d_chain_score(C, Score), proven(...,42,_))` |
| `compound` | abstract-slot strategy | bind to compound: `slot_fill(strategy_a, [arg1, arg2])` |
| `string` | HAS_CONTENT resolution | bind to atom: `"actual content here"` |
| `SOUP-with-reason` | failed admissibility with structured cause | either (a) `failure(Goal, Reason)` with structured compound Reason, OR (b) bind verdict variable to `soup(Reason)` — successful proof carrying SOUP verdict |

solve/3 + variable bindings + failure-as-data naturally handle all of these. No generalization needed at the d-chain mechanism level — let the polymorphism emerge.

**Abstract slots live in ontology, NOT code (per Correction #2 §6).** Python code is massively overloaded — a single concrete `{str}` slot accepts many semantic structures (1-group, 2-group, N-group fills). Each fill strategy unpacks as a different set of abstract sub-slots with their own d-chains. The abstract slots don't exist as Python parameters; they exist as ontology possibility-space. **Reifying abstract slots is much easier in ontology than in code** — code would require heavy metaprogramming; ontology expresses them naturally as additional relationships/properties.

---

#### 15.3 Motivation — why d-chains, not OWL `range` / Pydantic typing

**The principle (load-bearing, Correction #2 §6, applied at TWO levels per Correction #3):**

> `label: Label`-style typing produces typed strings with descriptions. It does NOT produce LOGIC. Logic requires ontology that knows the SEMANTIC ROLE of each field within the larger context, plus d-chains that enforce context-correct fills.

**Level 1 — Python type level (Correction #2 §6):**

Example: Excel spreadsheet where rows are locations and columns are bread types. Field `label: Label` accepts `"Bob"` (it's a valid `str`/`Label`). But semantically, "Bob" is wrong — labels in this spreadsheet must be locations or bread types. To enforce this, the ontology needs to know:

- What spreadsheet this label is in
- What the rows mean (locations)
- What the columns mean (bread types)
- Valid fills for this specific label slot are constrained by those semantics
- "Bob" fails the d-chain unless disambiguated (rare case of a town called Bob → d-chain returns SOUP-with-reason demanding clarification)

That is the actual logical d-chain that walks the ontology graph to check semantic validity in context, not just type validity.

**Level 2 — OWL relationship level (Correction #3, Isaac verbatim):**

> "We talked about this before in terms of how OWL usually uses 'range' to mean: For any DogFur instance we infer that it must be a DogFurSubtype. Duh right? Instead we are saying that d-chain is a better type of tool than 'range' because it means: For any DogFur instance we *require* that what you actually claim slots in is exactly a DogFurSubtype with compositional proof."

- **OWL `range`:** definitional inference. Slot's value IS its declared range type by definition. No proof needed — it's how the property is declared. Same shape as Pydantic typing one layer down.
- **D-chain:** compositional proof required. Slot fill must be PROVEN to be the declared type via walking the composition under the recursive walker. Active enforcement, not definitional inference.

Same typed-strings-vs-logic principle, applied at two layers. The migration WIN is the d-chain layer attached at SystemType that enforces semantic role in context AND compositional proof at the OWL relationship level. Without the d-chain layer, the migration produces "more YOUKNOW with extra steps." With the d-chain layer, it produces actual LOGIC.

---

#### 15.4 Args-check d-chain — the d-chain that defines `is_a Code`

The minimal d-chain. Per Round 12 + Round 13 settlement, the args-check d-chain IS what makes CODE = CODE. Before it succeeds, the concept hasn't been canonicalized as representing real Python code (it's Soup). When it succeeds, the individual is asserted `is_a Code`.

**Sketch (parameterized form, option (a) per Round 13/14):**

```prolog
% args-check d-chain — succeeds when the concept's declared args
% map to a real Python code object inspectable via codeness/CA.
% Parameterized by T so the binding is visible at the Prolog body
% level (composable for downstream d-chains).
args_check(C) :-
    triple(C, is_a, T),
    py_call('soma_prolog.utils':code_object_signature_matches(C, T), _).
```

`triple/3` is the accumulated knowledge-web predicate declared `:- dynamic triple/3.` in `soma_prolog/soma_partials.pl:33`. A bridge `concept_type(C, T) :- triple(C, is_a, T).` exists in the same file if a cleaner name is preferred at the d-chain body level — either works. The `code_object_signature_matches(C, T)` py_call checks the Python class for type T exists AND its signature matches C's declared args. Surfacing T in the Prolog body is exactly making the semantic role explicit at the logic layer (per §15.3 Level 2).

**Multi-is_a handling (Round 14 sub-decision):**

When C has multiple `is_a` triples:
- **Entry-level CODE admission:** first-match semantics. Any T satisfying signature-match admits the concept as `is_a Code`. Weakest possible admission to SystemType umbrella.
- **Stricter SYSTEM_TYPE level:** all-matches semantics, as a SEPARATE additional d-chain attached at richer-SYSTEM_TYPE level. Layered, not competing.

Both d-chains coexist. Different points in the umbrella → different d-chains gating different transitions.

---

#### 15.5 OWL-storage constraints on Prolog_Rule bodies

D-chains stored as `Prolog_Rule` OWL individuals (loaded into the live Prolog runtime via the bootstrap loader) have FOUR concrete syntactic constraints that affect how d-chain bodies must be written:

1. **Pipe-scrub (`_scrub_pipe` in `soma_prolog/utils.py:730`).** Replaces `|` with `/` before parsing rule strings from OWL. List-cons `[H|T]` patterns BREAK in rule heads/bodies stored in OWL. Workarounds: `append/3`, `functor`/`arg`, or put list-heavy logic in native `soma_partials.pl` rather than OWL Prolog_Rule individuals.

2. **`owl_save` XML char corruption.** Rule bodies containing `>`, `<`, `&` corrupt `owl_save` serialization. Means arithmetic comparisons in OWL Prolog_Rule bodies need workarounds (`succ/2` instead of `>`, etc.). **Test-first concern:** HAS_CONTENT migration with markdown payloads exercises this constraint from the data side; sanctuary-scoring d-chains exercise it from the operator side (`score > threshold`). Together they cover the XML-char failure surface.

3. **Multi-solution d-chains** (e.g., enumerate all valid abstract slot fills for an overloaded slot): `solve/3` returns first solution. Need `findall/3` wrapping in the rule body. Pattern already exists in `soma_partials.pl` convention rules.

4. **Janus serialization of deeply-nested compound terms.** When a d-chain rule body py_calls Python and the Python returns a deeply-nested compound, janus serialization can choke. Flat compounds/atoms/numbers work. **Verify on first deep-return case** (abstract-slot strategy d-chains are the candidate).

---

#### 15.6 py_call substrate — starting set (NOT exhaustive)

More py_call targets will be added as needed. The starting set below replaces the HANDOFF's outdated examples (`pellet_run`, `owl_save`) with the actually-needed operations identified through Apr↔May crosscheck Rounds 1-3.

**Validation:**
- `youknow_kernel.system_type_validator:validate_restrictions` — the recursive walk (replaces Pellet for admissibility)
- `soma_prolog.utils:code_object_signature_matches(C, T)` — args-check py_call (target of the args-check d-chain in §15.4)
- `soma_pellet.run_on_recent_window(minutes=10)` — periodic DL sweep (§15.7)

**Projection (write-artifact dispatch):**
- `carton_mcp.substrate_projector:project_to_skill`
- `carton_mcp.substrate_projector:project_to_rule`
- `carton_mcp.substrate_projector:project_to_file`
- (per-type projectors — full set per `Substrate_Projector` concept)

**CartON concept-graph queries (the CartON Neo4j bridge):**
- `mcp__carton__query_wiki_graph(cypher_query, parameters)`
- `mcp__carton__get_concept(concept_name)`
- `mcp__carton__get_concept_network(concept_name, depth, rel_types)`
- `mcp__carton__chroma_query(query, collection_name, k)`
- `mcp__carton__get_history_info(info_type, id)`
- `mcp__carton__activate_collection(collection_name)`

**CA code-graph queries (the CA Neo4j bridge — separate from CartON's Neo4j):**
- `context_alignment_utils:query_codebase_graph` — for `check_code_reality` stub-protocol checks

**Type accumulation:**
- `owl_types.accumulate_owl_types` — runtime in-memory accumulator (replaces `cat_of_cat.py`). NOT the boot-time OWL file merger (that's owlready2's `owl:imports`).

**LLM dispatch (for WIP-12 Layer 3, codegen, and NEED_AGENT responses):**
- TBD wrapper name — CALLER provides the actual LLM callable. SOMA emits structured NEED_AGENT request with schema + context bundle. Model, prompt template, and agent-loop location are CALLER's decisions, not SOMA's (settled Round 5).

**Observation persistence + audit logging:** lives in SOMA's own `utils.py` as direct Python (NOT py_call into external libs).

---

#### 15.7 Pellet periodic-sweep model + warning surface

Resolved settle-point from Round 3 (Isaac's refinement of Apr's reconciliation insight):

- **Walk** (`validate_restrictions`) = fast every-event admissibility check. Synchronous in the event path.
- **Pellet** = periodic background sweep (~10-min window) over recent work. Runs out-of-band on a timer. Finds DL inconsistencies (subsumption violations, disjointness violations, property-chain inferences that contradict existing facts). Outputs WARNINGS, not synchronous blocks.
- Inconsistencies surface as `Consistency_Warning` observation events fed back via `add_event`, NOT as terminal response statuses.
- Pellet sweep is itself a PrologRule individual whose body py_calls `soma_pellet.run_on_recent_window(minutes=10)` and asserts warnings back into SOMA as events.

Decouples DL consistency from the event admissibility path. Agents keep working at full speed. Warnings accumulate. Reconciliation is a deliberate action, not a synchronous gate.

**Response shape (per Round 4 Q8 resolution):** SOMA's response gains a `warnings: []` field that appears on ANY status (not its own status type). Concept can still be `is_a Code` with active warnings attached.

---

#### 15.8 Migration sequencing — 5 phases + intense zone

**Phase 1 — `validate_restrictions` + `owl_types` + args-check d-chain.** Most-standalone starting point:
- Pure Python wrappers for `validate_restrictions` and `owl_types.accumulate_owl_types`.
- Args-check d-chain (§15.4) as a `CoreRequirement`/`Deduction_Chain` OWL individual.
- Concepts that pass become `is_a Code` (= minimum SystemType).
- **Runtime-coupling note (Round 8):** `validate_restrictions` reads `owl_types` state during its walk. They share a runtime data structure. Path: module-level singleton in YOUKNOW Python, shared via Python import caching. **Verify via first-batch dispatch Prompt 1.**

**Phase 2 — `project_to_X` dispatch as PrologRule individual.** Body py_calls projector when its own required d-chains hold for the concept. NO promotion gate (Phase 1.5 dissolved per Correction #2) — the projector's d-chains ARE the gate. Some projectors fire at `is_a Code` if args-check is all they need; richer projectors wait on additional d-chain satisfaction.

**Phase 3 — `check_code_reality` (CA Neo4j stub protocol).** Wraps `context_alignment_utils:query_codebase_graph`.

**Phase 4 — codeness as observer.** Python AST reads → SOMA `add_event` → `Code_Entity` OWL individuals accumulate → d-chains reference them by name. Per Round 7 reframe: codeness becomes a normal SOMA observation source, NOT a special bridge.

**`Code_Entity` and the SystemType umbrella (clarification, Round 18 polish #3):** `Code_Entity` is a DOMAIN class (like `SkillSchema`, `InvoiceTemplate`, etc.) — it answers "what kind of thing is this in the domain?" It is NOT itself a subclass of SystemType. State classes (`Code` / `ONT` / `Soup`) layer on top of `Code_Entity` via `is_a` per Correction #3's pattern. So a codeness-observed Python class produces an individual with:
- `is_a Code_Entity`  ← domain type (rdf:type) — what codeness observed
- `is_a Code`         ← state class — when args-check d-chain succeeds (the Python is inspectable + signature matches)
- `is_a SystemType`   ← umbrella (via transitive subClassOf on Code)

Domain type and state class are orthogonal axes — both live as `is_a` triples on the same individual.

**Phase 5 — Pellet periodic-sweep.** Last among the "easy" phases. Requires new response field (`warnings: []`) and new event type (`Consistency_Warning`).

**Intense zone (Isaac's phrase — needs continuous_emr.py + sanctuary survey first):**

Migration sequence within intense zone (per Round 13-14 settlement):

1. **HAS_CONTENT** — single solution, pure Prolog graph traversal (no py_call), string return, exercises OWL XML-char constraint (#2) with markdown payloads.
2. **Sanctuary-scoring (lowest-arity FLAT rule first).** Per Round 14 caveat: if first available sanctuary scoring rule is recursive over partials, swap order (reifies-terminal first). Extends polymorphism coverage to int, exercises XML-char constraint from operator side (`>` → `succ/2`), tests janus int serialization, real unification proof (replaces hand-written Cypher). **Lowest-arity flat rule identified via first-batch dispatch Prompt 4.**
3. **Reifies-terminal** — pure Prolog rule consulted during recursion in solve/3. Bool return. Tests recursion-control mechanism.
4. **Abstract-slot strategy d-chains** — compound returns + janus deep-compound serialization (constraint #4) — most complex.
5. **EMR spiral** — after `continuous_emr.py` dissection via first-batch dispatch Prompt 2. Walks event sequences in soma.owl.

---

#### 15.9 First-batch dispatch — verification phase (after this WIP-15 lands)

Per Isaac's method discipline (top of `agent_to_agent_convo.md`): figure out the YOUKNOW→SOMA migration TOGETHER through the convo FIRST. THEN dispatch agents to verify. If an agent CANNOT confirm a conclusion, that "cannot confirm" is itself valuable data — fix codebase readability BEFORE refactoring.

**First batch (per `agent_crosscheck/dispatch_prompts_INDEX.md`):**

> **Note:** The table below is a SNAPSHOT at WIP-15 v2 landing time (2026-05-13). The CANONICAL LIVE STATUS is `agent_crosscheck/dispatch_prompts_INDEX.md` — that file flips per-item status as dispatch fires and findings land. If the table here disagrees with the INDEX, the INDEX wins.

| # | Target | Prompt | Findings | Status (snapshot) |
|---|---|---|---|---|
| 1 | `owl_types.py` singleton structure via trace from `youknow().compile()` | `dispatch_prompt_1_owl_types.md` | `findings_owl_types_singleton_2026_05_13.md` | not yet dispatched |
| 2 | `continuous_emr.py` shape and role via trace from `youknow().compile()` | `dispatch_prompt_2_continuous_emr.md` | `findings_continuous_emr_shape_2026_05_13.md` | not yet dispatched |
| 3 | **LOAD-BEARING:** Did April 19 recursive walker resolve `Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18`? | `dispatch_prompt_3_bug_youknow_compiler.md` | `findings_bug_youknow_compiler_disconnected_2026_05_13.md` | not yet dispatched |
| 4 | Sanctuary scoring rule survey — lowest-arity flat rule | `dispatch_prompt_4_sanctuary_scoring.md` | `findings_sanctuary_scoring_survey_2026_05_13.md` | not yet dispatched |

**Dispatch shape (per Round 15 Q33):** Parallel + per-item findings files + index status tracker. No shared docs (merge-conflict risk).

**Prompt-3 pivot warning:** If verdict returns STILL OPEN or PARTIALLY RESOLVED, the migration shape gets re-evaluated. YOUKNOW's bootstrap structure (core sentence as universal d-chain template) is the basis for ONT. If still broken, reassess how much of YOUKNOW even goes into SOMA.

**Prompt-4 sequencing-pivot:** If no flat sanctuary scoring rule exists, swap intense-zone order to put reifies-terminal before sanctuary-scoring (per Round 14 caveat).

---

#### 15.10 Confirmed corrections from crosscheck (Settled)

1. **Substrate is a starting set, NOT exhaustive.** Additional targets added as needed. Don't lock count in immutable. (Round 3.)
2. **Two separate Neo4j bridges, both needed.** CA Neo4j (code-alignment) for `check_code_reality`; CartON Neo4j (concept graph) via `query_wiki_graph`/etc. Don't unify. (Round 3.)
3. **`accumulate_owl_types` = runtime in-memory accumulator** (replaced `cat_of_cat.py`). NOT boot-time OWL file merger (owlready2's `owl:imports`). (Round 3.)
4. **Pellet = periodic out-of-band sweep with warning surface.** NOT removed entirely, NOT in synchronous event path. (Round 3.)
5. **Projection fires at SystemType-state, not CODE-state alone.** D-chains live at SystemType; specific projectors fire when their required d-chains satisfy on the individual. (Correction #1, Round 8/9.)
6. **CODE = minimum SystemType with args-check d-chain attached.** No CODE→SystemType promotion step; they're the same umbrella, CODE is the entry-level subclass. (Correction #2, Round 10/11.)
7. **Q20 resolved: SystemType expressed as OWL class via `is_a` layering.** State membership stacks on top of domain `rdf:type`. Code/ONT as named subclasses; intermediate richness flat-with-accumulation. ONT = SystemType + universal d-chain. (Correction #3, Round 15/16.)
8. **D-chain is a stronger primitive than OWL `range`.** OWL `range` = definitional inference (Pydantic-shape). D-chain = compositional proof via recursive walker. Same typed-strings-vs-logic principle as Correction #2 §6, applied one layer down. (Correction #3.)

---

#### 15.11 When this moves to immutable

Once Round 17+ confirms WIP-15 (May review + Isaac sign-off) and first-batch dispatch lands without contradicting the plan, the following propagate from WIP into immutable:

**Replacements:**
- Immutable "**SOUP / CODE / ONT**" section → replaced by §15.1's OWL class hierarchy via `is_a` layering (Correction #3 content).
- Immutable "**The Core Sentence (ONT Admission)**" section → reframed as ONT = SystemType + universal d-chain. Core sentence body becomes the universal d-chain content.
- Immutable "**Pellet's Role**" section → replaced by §15.7 periodic-sweep model.

**Additions:**
- Immutable "**Communication Protocol**" gains `warnings: []` response field.
- Immutable "**What SOMA Contains**" gains explicit "py_call substrate (non-exhaustive starting set listed in WIP-15 §15.6)" entry.
- Immutable gets a new "**Why d-chains, not OWL range**" section pointing to §15.3.
- Immutable "**Authorization + Precomputation**" section gains explicit reference to compositional-proof model (d-chain enforcement, not definitional inference).

**WIP cascade:**
- WIP-7 (response protocol detail) folds in `Consistency_Warning` event type and `warnings: []` field.
- WIP-4 (OWL restriction loading at boot) clarifies: owlready2's `owl:imports` job at boot, NOT `accumulate_owl_types` (runtime).
- WIP-3 (d-chains as filling strategies) notes `check_code_reality` is one named strategy for the stub case.
- WIP-11 (corrected SOUP/CODE/ONT definitions) is SUPERSEDED by Correction #3 / §15.1. WIP-11's earlier defs (e.g. "SOUP has string_value") are replaced by the OWL-class-via-`is_a` model. WIP-11 itself moves to "RESOLVED via Correction #3."

**Deferrals (do NOT move to immutable yet):**
- Q10 (codeness-observe loop end-to-end) — first-batch dispatch partially answers via continuous_emr + sanctuary survey.
- Q11 (d-chain DSL parser) — Isaac-deferred to dragonbones last phase.
- Q12 (YOUKNOW feature inventory mapping) — first-batch dispatch is partial answer.
- Multi-is_a all-matches stricter d-chain (§15.4 sub-decision) — wait for concrete migration case.
- Richer-SystemType class-vs-accumulation conditional (Q32 sub-decision) — answered as flat-with-accumulation under Correction #3, but specific richer-SystemType-class proliferation question waits for a concrete forcing case.

