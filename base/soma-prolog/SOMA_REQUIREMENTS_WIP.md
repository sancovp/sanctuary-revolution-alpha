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
