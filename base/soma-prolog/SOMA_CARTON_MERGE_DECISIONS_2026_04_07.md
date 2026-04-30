# SOMA / CartON Merge Decision Log — 2026-04-07

**Source of truth**: CartON collection `Soma_Carton_Merge_Decision_Log_2026_04_07`
**Session**: GNO.SYS + Isaac, 2026-04-07, HOME MODE
**Scope lock** (D26): fix SOMA first, redesign-and-implement YOUKNOW later as a SOMA-Prolog program. CartON hosts both throughout. Do NOT dig into YOUKNOW internals during the SOMA fix phase.

This file is a projection of the CartON decision log. The CartON concepts are the source of truth. This file exists so the autopoiesis loop (and future agents) can check implementation status without re-deriving the architecture.

---

## HOW TO USE THIS FILE

For each **decision** below, the autopoiesis loop should verify:
1. Is the decision reflected in the code today?
2. If not, is there a concrete next step to implement it?
3. If the decision is deferred (status: Deferred or Target), is it clearly marked as out of scope for the current phase?

For each **open question**, the loop should verify:
1. Is the question still open or has it been resolved in code/discussion since 2026-04-07?
2. If resolved, update the corresponding CartON concept and this file.

For each **dropped hypothesis**, the loop should verify:
1. Has any code or design started reintroducing the dropped pattern?
2. If yes, revert it and re-read the rejecting decision.

---

## DECISIONS (D1–D26, all confirmed)

### D1 — Description is a writable staging area
Description is a writable staging area for unstructured language awaiting extraction into triples. Keep the field. The fix is stronger extraction + evolution scoring + the d-agent, not deletion. The field existing is NOT the bug; the bug is weak extraction and no evolution metric.

### D2 — CartON's primitive is triples; description is the staging slot
CartON primitive is triples AND description is the upstream staging slot that feeds triples via extraction. Both are load-bearing. Description is NOT competing with triples — it is the input path whose content gradually migrates into triples over time. `add_concept` already enforces `relationships` as required and treats `description` as optional. The live Neo4j still has `n.d` as a sink — that is the gap.

### D3 — CartON implicitly puns everything via `is_a`
Every concept is simultaneously class and individual. Standard OWL requires explicit OWL 2 punning; CartON collapses `subClassOf` and `type` into one edge by default. Already true; no change needed. The Skills system proves it works.

### D4 — Everything is a self-typed concept; no literals
Primitive values canonicalize into concepts whose own type chain carries the type information. SOMA observations with typed values (`5 with int_value`) canonicalize at the boundary into concept references (`5 is_a Integer`). After canonicalization the type tag disappears. OWL datatype-properties are **not** imported — rejected as S3.

### D5 — SOMA observation and CartON triple are the same primitive
A SOMA observation `(E, key, value)` is structurally `(E, key, value)` — a triple whose subject is an event. Same primitive at most with two surface shapes. Not two systems to unify. After D4 canonicalization the isomorphism is total.

### D6 — The 10-step SOMA plan from the prior session is complete (VERIFIED)
Subagent read 2026-04-07 confirmed:
- `core.py` has exactly one Janus call (`mi_add_event`)
- `soma_boot.pl` has exactly one `py_call` (the `PrologRule` loader in `load_prolog_rules_from_owl`)
- Rules live as `PrologRule` individuals in `soma.owl`, loaded at boot
- `mi_add_event` routes through `solve/3`
- `pellet_run` and `owl_save` are `PrologRule` individuals routed through the MI
- `boot_check` goes through `solve/3`

Contract honored. SOMA base is working. What is missing is the layer above the base.

**Future agents must re-verify before assuming SOMA is broken.**

### D7 — SOMA dissolves into CartON as its Prolog reasoning layer
"SOMA" = the Prolog entrypoint into the unified CartON reasoning system. No separate SOMA program architecturally. `soma-prolog/` is a layer of CartON, not a peer. Product-packaging (shipping a stripped-down SOMA-only redistributable) is orthogonal and doesn't change the architecture.

### D8 — Wrappers are forbidden
`add_concept` and `add_event` cannot coexist as wrapping functions. Wrappers grow escape hatches — an optional parameter is added that doesn't pass through, the wrapper drifts, the bypass returns. This is the exact pathology that produced the description-prose pollution. One primitive, one entry point, at the code level.

### D9 — Self-organizing type emergence is the point of having Prolog
Rule: "if an instance gets used later as a template, it must at some point have become a class and a universal." Promotion chain: thing → class → template → universal, each step earned by usage and consistency. Verified **absent** from current SOMA by subagent read 2026-04-07. This is the missing kernel that makes the Prolog layer valuable.

### D10 — The rule-derivation kernel is the minimal missing piece
Small number of base `PrologRule` individuals plus seed composition rules. Once the seed runs, the rest (concept promotion, validity tracking, type lifting, composition admissibility) emerges from observation patterns. Rules are **observed**, not authored. The kernel watches the event log, detects stable patterns, derives new rules, asserts them, and persists them as new `PrologRule` individuals.

### D11 — Prolog is ephemeral, not a persistent runtime
Runs per-user per-session. Opens a live relay to Neo4j (bidirectional). Runs the reasoning pass. Writes results back. Terminates. State lives in Neo4j. No Prolog persistence engineering needed. Crash recovery is automatic. Stateless reasoning is deterministic, auditable, replayable.

### D12 — Neo4j is the persistent store; Prolog is downstream
Neo4j is the unambiguous source of truth. Prolog is downstream, reasoning layer only. Drift dissolves because Prolog is stateless between runs. Neo4j owns auth, security, audit, backup, replication. Neo4j Browser / Cypher is the human inspection surface.

### D13 — Prolog rules and metaprogramming live in CartON as concepts
Sent to Prolog at session start. The meta-interpreter itself is shipped as code. Program-as-data applies to rules, not to the runtime framework. Upgrading the rule base is updating CartON concepts — no binary deploys. Bounded self-hosting.

### D14 — Reasoning pass latency is not user-visible
Seconds to minutes is fine. Background update after new observations land, not per-token chat latency. If per-token disambiguation exists, it runs against a cached projection in Neo4j that the reasoning pass maintains.

### D15 — Polluted existing CartON data does not block progress
The d-agent (D21) eats prose into structure on its own timeline, in parallel. New writes go through the new structured path from day one. Migration is asynchronous and does not gate the SOMA fix.

### D16 — The prose pollution fix is structural, not disciplinary
Rules and skills telling agents "don't write prose" don't work because LLM agents path-of-least-resistance everything. The only reliable fix is evolving the extraction infrastructure so prose automatically migrates to triples. The d-agent does the migration mechanically.

### D17 — SOUP vs ONT distinction deferred to YOUKNOW refactor
The full definition of what makes a concept fully ONT beyond description crystallization is deferred. Candidates include recursive triple grounding, Prolog validation, derivation chain closure, event consistency, recursive ONT status of the description-concept. **Do not confabulate the criteria.** Revisit when refactoring YOUKNOW.

### D18 — Keep OWL as a serialization format
`uarl.owl` and `soma.owl` stay as on-disk interop format. Prolog is the runtime. Pellet's role diminishes over time or gets replaced by Prolog inference, but does not get dropped in the SOMA fix phase. Whether to drop OWL entirely is Q1, deferred to YOUKNOW refactor.

### D19 — UARL-in-Prolog is the target state (deferred)
Re-express the UARL system that was attempted in OWL as Prolog rules. Target for the YOUKNOW refactor phase, not current state. The ontology engine would boot from UARL's rules about structure, then reason over every other concept using those rules.

### D20 — Description extraction is PARTIALLY existing (corrected 2026-04-07 iter 3)
**Corrected after code reading:**
- `auto_link_description` is LIVE at `observation_worker_daemon.py:892` (linker_thread). It converts concept-name mentions in descriptions to markdown links pointing at `_itself.md` files. This is link annotation, not triple extraction.
- `find_auto_relationships` (defined at `add_concept_tool.py:464`) is DEAD CODE in the current write path. Its only call site is inside the commented-out dead block at `add_concept_tool.py:2032`.
- `check_missing_concepts_and_manage_file` (defined at `:553`) is live but only via the on-demand `calculate_missing_concepts()` API in `carton_utils.py:1139`, NOT on every write.
- **Multi-occurrence auto-concept-creation is NOT currently running on writes.** The function exists but is not wired.
- **Deferred to CartON refactor phase** (after SOMA is done) — do not attempt to re-wire during SOMA fix phase per D26.
- **Implication for D21:** the d-agent cannot assume extraction-into-triples is already running. It must either bring its own extraction logic or defer integration until the CartON refactor wires the dead function back in.

### D21 — The d-agent is the background coherer
Runs over time. Scores each concept on evolution metric (ratio of linked canonical `_itself` references to total eligible words in description). Picks lowest-scoring concepts. Traces unlinked eligible words. Links them when possible. Raises structured stuck-messages to a queue when tracing fails. **Same shape as innerteacher** (the module that figures out where errors happened in treeshell nodes and leaves learnings via CartON projection). Different target: concepts vs treeshell nodes.

### D22 — Description crystallization is the bootstrap step
When every eligible word in a description is linked to a canonical `_itself` concept, the description becomes a concept in its own right. This is the step where prose becomes structure. It is **necessary but not sufficient** for SOUP→ONT promotion. Sufficiency criteria are TBD (Q9), deferred to YOUKNOW refactor. Crystallization means the description is "bootstrapped" — structure exists; reasoning can walk it.

### D23 — Descriptions-as-concepts are recursive
Crystallized descriptions are themselves concepts with their own descriptions, which crystallize via the same process. Mature-system endgame: new descriptions crystallize on arrival because most words are already concepts. Ingestion speed accelerates over time. Endgame: prose dissolves into pure structure.

### D24 — The d-agent's steps are mechanical
Pick SOUP concept → trace unlinked eligible words → link or stuck → when all eligible words linked, fire crystallization → create description-concept → attach to source → flip SOUP to ONT (partial — full ONT deferred per D17/Q9). No LLM understanding required for base case. LLM only for disambiguation of ambiguous words.

### D25 — CartON eligibility rules defer to existing implementation
Rules about which words are eligible to become concepts already exist in CartON's extraction code. Don't respec — defer to existing implementation. The d-agent uses the existing filter.

### D26 — Scope order: fix SOMA first, YOUKNOW refactor later
CartON hosts both throughout. **Do not dig into YOUKNOW internals during the SOMA fix phase.** The endgame is YOUKNOW re-implemented as a Prolog program running inside the SOMA substrate with CartON/Neo4j as persistent store. SOMA is the immediate fix. YOUKNOW-on-Prolog is the next phase. **This scope lock governs everything else in this log.**

### D27 — Structure-preserving maps gate type emergence; non-preserving observations become Hallucination events
**This is the anti-explosion guard for D9/D10.** Without it, naive pattern-lifting would explode the Prolog type system by accumulating contradictions, anomalies, and non-coherent lifts. With it, types grow only from coherent structure-preserving observations, and everything else gets categorized as `Hallucination_Event_Category`.

**Mechanism:** when the rule-derivation kernel observes a repeated pattern and considers lifting it to a type or rule, it first checks whether the new observation is a structure-preserving map to the already-established pattern.
- If YES → reinforce the type by lifting the observation into it.
- If NO → the observation does NOT get lifted into that type. Instead it gets emitted as a `Hallucination` event.

**Over time, Hallucination events can themselves form patterns.** A recurring Hallucination pattern might eventually cohere into a new type of its own if enough structure-preserving (within the new pattern) non-preserving-relative-to-old-types observations accumulate. This is the mechanism by which genuinely new categories emerge from what initially looks like anomaly.

**Category-theoretic framing:** types are categories, structure-preserving maps are functors between them, patterns that preserve structure are lifts within a category, patterns that do not are either Hallucinations (anomalies) or seeds of new categories.

**This decision is a REQUIRED constraint on how the rule-derivation kernel (D10) performs the self-organizing type emergence (D9).** The kernel without D27 would be dangerous; the kernel with D27 is the actual valuable artifact.

---

## OPEN QUESTIONS (Q1–Q11, all unresolved)

### Q1 — Drop OWL/Pellet entirely for pure Prolog at scale?
At 100M facts Pellet cannot keep up. Isaac: "kind of goofy, im not sure." Default is keep OWL per D18. **Deferred to YOUKNOW refactor.**

### Q2 — Value canonicalization convention
When `5` arrives as a SOMA observation, what does it become? `5`? `Five`? `5_Integer`? Distinct `Int_5` vs `String_5`? Unresolved.

### Q3 — String value disambiguation
When `"Isaac"` arrives, same node as person Isaac? Or separate `Isaac_String`? Unresolved.

### Q4 — Compound value handling
dict/list values → recursive concept creation for each leaf? Serialized into one concept? Unresolved.

### Q5 — Event subject naming convention
`Event_<source>_<timestamp>`? UUID? Unresolved.

### Q6 — `domain` parameter semantics
SOMA `add_event` has a `domain` parameter. Maps to `part_of <domain_concept>`? Something else? Dropped? Unresolved.

### Q7 — Lifting semantics threshold
What threshold/confidence promotes an instance pattern to a class-level triple? Probably emerges from running the kernel, not decided upfront. Unresolved.

### Q8 — Description storage shape
`has_description_event` events-as-nodes vs direct-triples-with-provenance. Probably subsumed by D22/D23 since the crystallized description IS the description-concept. Revisit if Q9/YOUKNOW reopens it.

### Q9 — Full ONT criteria beyond crystallization
What else does a concept need beyond description crystallization to be fully ONT? Candidates: recursive triple grounding, Prolog validation pass, derivation chain closure, event consistency, recursive ONT of the description-concept. **Deferred to YOUKNOW refactor.**

### Q10 — Does the d-agent's stuck-messages queue feed the kernel?
Conjecture: d-agent saying "can't trace word X" and kernel looking for patterns to lift — the stuck messages might be exactly "these are the ambiguities Prolog should try to resolve." Would close the loop: coherer identifies gaps, kernel fills them, coherer verifies. Unanswered.

### Q11 — Treeshell-via-Prolog
Does the treeshell navigation/execution system become interpreted through Prolog? Isaac flagged this: "maybe treeshell becomes interpreted through prolog or something." Huge architectural claim. Flagged as future direction, not this session's scope.

---

## DROPPED HYPOTHESES (S1–S6, do not re-propose)

### S1 — Specific $/mo cost math
Noise. Isaac said drop it. Architecture decisions should not be made under unvalidated pricing constraints. Pricing is downstream.

### S2 — Specific Prolog benchmark numbers at 100M facts
Order-of-magnitude confidence only. Any precise numbers cited were not measured. If precision matters later, measure in context.

### S3 — Import OWL datatype properties into CartON
Wrong answer. CartON has no literals — everything is a self-typed concept. Rejected by D4. Do not re-propose.

### S4 — Two-layer events-vs-concepts with datatype properties
Over-complication. One layer with punning and boundary canonicalization. Rejected by D5. Do not re-propose.

### S5 — `add_concept` wraps `add_event` as sugar
Forbidden by D8 (Wrappers Forbidden). One primitive, one entry point. Do not re-propose.

### S6 — Description as separate event-nodes with `has_description_event` edges
Partially subsumed by D22/D23. The crystallized description IS the description-concept, not a separate event-node. Revisit only if Q8/Q9/YOUKNOW reopens it.

---

## IMPLEMENTATION STATUS AT TIME OF LOG

As of 2026-04-07:

| Decision | Status in code | Action required |
|---|---|---|
| D1 | N/A (philosophical reframe) | No direct code change; informs D20/D21 |
| D2 | ✅ COMPLETE (iter 4) | `_compute_description_rollup` added at `add_concept_tool.py:~1786`, `add_concept_tool_func` body updated at `:~1895` to route raw prose into `raw_staging` and set description to the computed rollup. Unit + integration tests passing. Existing pollution migration still deferred to d-agent. |
| D3 | Already true | Verify no code treats `is_a` as class-only or type-only |
| D4 | Already true | Verify no code imports or relies on OWL datatype properties |
| D5 | Already true structurally | Verify no code treats observations and triples as separate primitives |
| D6 | Verified complete by subagent 2026-04-07 | No action; revisit if SOMA appears broken |
| D7 | Not reflected in code (separate `soma-prolog/` dir) | Defer folding until after SOMA fix phase |
| D8 | Already honored (no wrappers exist) | Enforce in code review; do not add sugar wrappers |
| D9 | **NOT BUILT** | Build the rule-derivation kernel (D10) |
| D10 | **NOT BUILT** | Write kernel `PrologRule` individual(s); add to `soma.owl` |
| D11 | **DEFERRED** (per Isaac iter 4: integration question not yet decided) | SOMA stores in soma.owl for now; YOUKNOW's CartON mirroring handles CartON side later. Revisit when SOMA↔CartON integration is designed. |
| D12 | Partial — Neo4j holds state but prose pollution diverges from triples | D21 migration closes the divergence |
| D13 | Partial — some rules are in `soma.owl`, the kernel rule isn't | Add kernel rule; verify CartON can hold all rule content |
| D14 | N/A (latency budget) | Verify no code treats reasoning pass as latency-sensitive |
| D15 | N/A (migration strategy) | D21 implementation |
| D16 | Already honored (no lecturing-based fix attempted) | N/A |
| D17 | Deferred | N/A until YOUKNOW refactor |
| D18 | Already honored (OWL still exists) | Verify OWL files stay as serialization format; Pellet role TBD |
| D19 | Deferred | N/A until YOUKNOW refactor |
| D20 | Exists in code (`find_auto_relationships`) | Verify it runs; integrate with D21 |
| D21 | **NOT BUILT** | Design and build the d-agent |
| D22 | **NOT BUILT** (no crystallization trigger exists) | Add crystallization step to d-agent |
| D23 | Follows from D22 | Same as D22 |
| D24 | **NOT BUILT** | Same as D21 |
| D25 | Already exists | Read the filter code; use from d-agent |
| D26 | Scope lock — active now | Do not touch YOUKNOW in this phase |
| D27 | **NOT BUILT** (required constraint on D10) | Task #206 — implement structure-preserving map guard in kernel, with Hallucination fallback. Blocked by #199. |

**Summary:** D6, D18, D20, D25 are reality; D3, D4, D5 are already-true structural facts needing verification; D9, D10, D11, D21, D22, D23, D24 are **NOT BUILT** and represent the work ahead. D17, D19 are deferred to the next phase.

---

## AUTOPOIESIS CHECK CONDITION

For the autopoiesis loop that runs against this file:

**Exit condition:** Every "NOT BUILT" row above has become a concrete implementation step (task created, or code committed), AND every "Already true" row has been verified by reading the relevant code, AND the `Soma_Carton_Merge_Decision_Log_2026_04_07` CartON collection contains all 43 concepts (1 collection + 26 decisions + 11 open questions + 6 dropped hypotheses), AND this file has been updated with a verification timestamp at the bottom.

**Block condition:** If any decision D1–D26 contradicts a recently-committed code change, raise to Isaac before proceeding. Do not silently resolve contradictions.

**Scope guard:** Do NOT perform YOUKNOW-refactor work during this phase. D26 is active. Any attempt to build Q1, Q9, D17, D19 is out of scope and should be deferred.

---

_This file is a projection of the CartON concepts listed above. If this file and CartON disagree, CartON is the source of truth. Update the concepts first, then regenerate this projection._

---

## VERIFICATION LOG

### 2026-04-07 — First Autopoiesis Iteration (GNO.SYS)

**CartON integrity — VERIFIED.**
- `Soma_Carton_Merge_Decision_Log_2026_04_07` collection retrieved via `mcp__carton__get_concept`. Collection contains all 43 expected `has_part` edges: D1–D26 (26 decisions), Q1–Q11 (11 open questions), S1–S6 (6 dropped hypotheses).
- Spot-checked concepts: `Decision_D9_Self_Organizing_Type_Emergence_Is_Point_Of_Prolog`, `Decision_D26_Scope_Order_Fix_Soma_First_Youknow_Later`, `Open_Question_Q9_Full_Ont_Criteria_Beyond_Crystallization`, `Dropped_Hypothesis_S3_Import_Owl_Datatype_Properties` — all exist in CartON with expected `is_a` typing, `part_of` pointing to the collection, and proper structural relationships.

**Decisions verified against current code state:**
- **D6 (SOMA 10-step plan complete)** — verified earlier this session by subagent read of `soma-prolog/` package. `core.py` has exactly one Janus call; `soma_boot.pl` has exactly one `py_call` (the loader); `mi_add_event/3` routes through `solve/3`; rules live as `PrologRule` individuals in `soma.owl`. Confidence: high (direct file read by subagent).
- **D2 (add_concept enforces triples, description optional)** — verified earlier this session by direct read of `/home/GOD/gnosys-plugin-v2/knowledge/carton-mcp/add_concept_tool.py` line 1786+. Function signature has `relationships: Optional[List[Dict]]` and raises `Exception("Relationships cannot be empty or none.")` at line 1818-1819. Description is optional with default. Confidence: high.
- **D18 (OWL files exist as serialization)** — `soma.owl` and `uarl.owl` files exist on disk in the monorepo paths verified by the subagent. Confidence: high.
- **D20 (description extraction mechanism exists)** — `find_auto_relationships` and `check_missing_concepts_and_manage_file` functions exist in `add_concept_tool.py` (lines 464 and 553 per earlier grep). Whether they actually run in the current daemon path requires Task #205 to verify. Confidence: medium (code exists, runtime behavior unverified).

**Decisions NOT verified in this session (follow-up required):**
- **D3 (implicit punning via is_a)** — model-level claim. Consistent with the absence of separate class/individual enforcement in `add_concept_tool.py` but not explicitly proven by reading a "punning is allowed" invariant in code. Future iteration should check whether any code path rejects a concept for being used as both class and individual — if no such rejection exists, D3 is effectively true by the absence of the constraint.
- **D4 (no literals, everything is a self-typed concept)** — consistent with the API shape (`related: List[str]` where strings are concept names, not literal values) but not proven by explicit code check. Future iteration should verify no code path allows primitive values as edge targets.
- **D5 (observation ≡ triple isomorphism)** — structural claim about how SOMA's `add_event` observations map to CartON triples. Not enforced anywhere because it's about the *shape* of data, not a runtime check. True by design, not by enforcement.
- **D25 (eligibility rules exist)** — claimed existence per Isaac. Actual location in code not cited in this iteration. Task #205 covers verifying the extraction mechanism, which should surface the eligibility rules.

**Tasks created for NOT BUILT items:**
- **Task #199** — D10: Build rule-derivation kernel as PrologRule individual(s)
- **Task #200** — D9: Wire self-organizing type emergence into SOMA via rule-derivation kernel (blocked by #199)
- **Task #201** — D11: Convert SOMA Prolog runtime from persistent to ephemeral per-user-per-session with live Neo4j relay
- **Task #202** — D21: Build the d-agent as background coherer for concept description evolution
- **Task #203** — D22: Implement description crystallization step as SOUP→ONT bootstrap (blocked by #202)
- **Task #204** — D2: Close the n.d prose pollution gap — ensure new writes go through structured path, existing prose migrates via d-agent
- **Task #205** — D20: Verify existing description extraction runs in daemon, integrate with d-agent

All 7 tasks auto-converted to `GIINT_Task_*` concepts under `Hypercluster_Odyssey_System` by the Dragonbones hook. Link is automatic.

**Decisions deferred (D26 scope lock active):**
- **D17** — SOUP/ONT full criteria deferred to YOUKNOW refactor.
- **D19** — UARL-in-Prolog is target state, deferred to YOUKNOW refactor.
- **Q1** — Drop OWL entirely deferred to YOUKNOW refactor.
- **Q9** — Full ONT criteria beyond crystallization deferred to YOUKNOW refactor.

**Decisions that are N/A for verification (philosophical reframes or scope statements, not code-targetable):**
- D1 (staging area reframe), D7 (SOMA dissolves into CartON — architectural intent, dir structure not changed), D8 (wrappers forbidden — enforcement is discipline-based), D12–D16 (architectural statements about source-of-truth, rule storage, latency, migration, and why discipline doesn't work), D23 (follows from D22), D24 (follows from D21), D26 (scope lock — active, governs the whole log).

**Contradictions surfaced to Isaac:**
- **None found in this iteration.** No decision D1–D26 contradicts current code as I read it.

**Scope guard: HONORED.** No YOUKNOW code touched. No code edited at all. Only verification, concept logging, file writing, and task creation.

**First iteration status:** CartON logged, file projected, tasks created for implementation work, verification of code-targetable decisions performed. The verification of D3, D4, D5 by direct code reading, and the actual implementation of the NOT BUILT items, are follow-on work that the tasks capture and future autopoiesis iterations will drive.

**Iteration 1 outcome: first pass complete; implementation work queued; no contradictions found; scope lock honored.**

### 2026-04-07 — Second Autopoiesis Iteration (GNO.SYS)

**Trigger:** Isaac delivered the backward reasoning for why self-organizing type emergence (D9/D10) does NOT explode the Prolog system: structure-preserving maps gate the lift. Non-preserving observations get routed to Hallucination events instead of contaminating types. This is a required constraint on the kernel and must be captured before the kernel is built.

**New decision logged:**
- **D27 — Structure-preserving maps gate type emergence; non-preserving observations become Hallucination events.** Concept `Decision_D27_Structure_Preserving_Maps_Gate_Type_Emergence_Non_Preserving_Become_Hallucinations` added to CartON. Linked as `guards D9, D10` and `introduces Hallucination_Event_Category`. Collection has_part count grows from 43 to 44.

**New concept logged:**
- **`Hallucination_Event_Category`** — the SOMA event category for observations that fail the structure-preserving map check. Linked as `introduced_by D27` and `caught_by Rule_Derivation_Kernel`. This is a first-class event category in the SOMA event taxonomy.

**New task created:**
- **Task #206** — D27: Implement structure-preserving map guard in rule-derivation kernel, with Hallucination event fallback. Blocked by #199 (the kernel must exist before the guard can be added).

**Task update:**
- **Task #199** description updated to explicitly reference D27 as a required constraint. The kernel builder cannot skip the guard — it's baked into the task description now so future-me (or ralph) cannot miss it.

**File update:**
- Decision D27 added as full entry to the DECISIONS section after D26.
- IMPLEMENTATION STATUS table gained a D27 row marking it NOT BUILT with task #206 pointer.

**Iteration 1 verification gaps — CLOSED in iteration 2 addendum:**

- **D3 (implicit punning via is_a)** — VERIFIED by absence. `add_concept_tool.py:685` defines `check_is_a_cycle` and `:652` defines `check_part_of_cycle`. These ONLY check for cycles in the respective graphs. There is no class/individual distinction anywhere in the file — no check that rejects a concept for being used simultaneously as a class (target of `is_a`) and as an individual (source of facts). The absence of that distinction IS the proof that CartON implements punning by default. Confidence: high.

- **D4 (no literals, everything is a self-typed concept)** — VERIFIED by absence. Grep for `TypedValue`, `literal`, `xsd:`, `datatype_property`, `DatatypeProperty` in `add_concept_tool.py` returned zero matches. The `relationships` parameter is typed as `List[Dict]` with `{"relationship": str, "related": List[str]}` where `related` is always a list of concept name strings — never primitive values with type tags. CartON has no code path for storing literal values as edge targets. Confidence: high.

- **D5 (observation ≡ triple isomorphism)** — VERIFIED as model-level. SOMA's `soma.owl` defines events with `hasKey`/`hasValue` relationships pointing to `Observation` individuals (per subagent read 2026-04-07). CartON's `add_concept` takes `relationships` as a list of `(predicate, [targets])` pairs. Both shapes reduce to `(subject, predicate, target)` triples. The isomorphism is a property of how the two APIs are designed, not enforced by any shared code. This is a model-level claim, not a runtime-enforced invariant. Honest status: true by design, not by enforcement.

- **D25 (CartON eligibility rules exist)** — VERIFIED with refinement. `add_concept_tool.py:381` has `if len(concept) <= 1: continue` (skips single-character concepts). Lines 415-416 check word boundaries (`before_ok`, `after_ok` with `isalnum()` check). The actual eligibility rule for a word in a description to be linked to a canonical concept is: **(1)** matches an existing concept name (with case/underscore variations generated at lines 385-393), **(2)** length > 1, **(3)** at word boundaries. There is NO stop-word filter, NO part-of-speech filter, NO explicit "content word" rule. The eligibility is more minimal than I was implying earlier — it's effectively "the word must already be a concept in the graph, plus basic sanity checks." This refinement should inform the d-agent (D21) — eligibility = "is there a canonical concept that this word matches?" rather than "is this a content word?" The existing auto-link mechanism uses Aho-Corasick for O(text_length) matching across the concept cache. Confidence: high.

**All four iteration 1 gaps are now closed.** No contradictions with decisions D3/D4/D5/D25 as stated — each is verified either by code presence, code absence, or honest model-level reporting.

**Scope guard: HONORED.** No YOUKNOW code touched. No code edited (only CartON concepts, task entries, and the file projection). D26 scope lock still active.

**Contradictions surfaced:** None.

**Iteration 2 outcome: D27 captured as first-class decision with guard concept, anti-explosion requirement is now baked into the kernel task, implementation queue reflects the constraint. D3/D4/D5/D25 remain for a future iteration.**

### 2026-04-07 — Fourth Autopoiesis Iteration (GNO.SYS)

**Summary:** Closed the iteration 1 verification gaps (D3/D4/D5/D25 all verified with file:line citations in the verification log above). Implemented and E2E-tested D10 (kernel), D27 (structure-preserving map guard), and D9 (self-organizing class promotion). Deferred D11 after Isaac confirmed the integration question is not yet decided.

**D3/D4/D5/D25 verification** (closed):
- **D3 punning** — verified by absence. `add_concept_tool.py:652, 685` only check cycles; no class/individual distinction exists anywhere in the file.
- **D4 no literals** — verified by absence. Zero matches for `TypedValue`, `literal`, `xsd:`, `datatype_property`, `DatatypeProperty` in `add_concept_tool.py`.
- **D5 observation ≡ triple** — verified as model-level. Both APIs reduce to `(subject, predicate, target)`. True by design, not enforced.
- **D25 eligibility rules** — verified with refinement. `add_concept_tool.py:381, 415-416` filter to `len > 1 + word boundary`. No stop-word or POS filter. Refines the d-agent design when it eventually gets built.

**D10 + D27 + D9 implementation:**

Added 18 new `PrologRule` individuals to `soma_prolog/soma.owl`:

Kernel pipeline (D10 + D27):
- `prolog_rule_kernel_derive_base`, `prolog_rule_kernel_derive_step` — walk observation list with `append/3`
- `prolog_rule_kernel_process_observation_match`, `prolog_rule_kernel_process_observation_miss` — dispatch on structure-preserving check
- `prolog_rule_structure_preserving_match_rule`, `prolog_rule_structure_preserving_match_fact` — check against both rule forms in MI store
- `prolog_rule_structure_preserving_map` — uses `functor/3` + `arg/3` (no `=..` pipe)
- `prolog_rule_args_preserve_by_index_base`, `prolog_rule_args_preserve_by_index_step` — index-based recursion using `succ/2` (no `>` or `-`)
- `prolog_rule_arg_preserves_identical`, `prolog_rule_arg_preserves_var_target`, `prolog_rule_arg_preserves_var_source` — element-level check
- `prolog_rule_kernel_reinforce` — on match, assert reinforcement and trigger promotion check
- `prolog_rule_kernel_emit_hallucination` — on miss, assert Hallucination event

Promotion pipeline (D9):
- `prolog_rule_kernel_check_promotion` — count reinforcements and dispatch to threshold check
- `prolog_rule_count_reinforcements_with_functor` — per-functor count via `findall/3`
- `prolog_rule_promote_if_threshold_one` — base case (N=1, no promotion)
- `prolog_rule_promote_if_threshold_already` — idempotency guard (already promoted)
- `prolog_rule_promote_if_threshold_new` — first-time promotion via `assertz(kernel_pattern_is_class/2)`

`prolog_rule_add_event` body updated to invoke `kernel_derive(EventId, Source, Observations)` immediately after `persist_event`.

**Bootstrap loader constraints discovered** (documented inline in soma.owl comment above the kernel block):

1. `_scrub_pipe` at `utils.py:621-625` replaces `|` with `/` before loader split. Cannot use `[H|T]` list-cons or `[F|Args]` with `=..` in heads or bodies. Use `append/3` and `functor/3` + `arg/3` instead.
2. owlready2's `save_owl` serializer does not safely round-trip rule body strings containing `>`, `<`, or `&`. Use `succ/2` for arithmetic checks, not `>`/`<`.
3. MI's `solve/5` does not handle `(A -> B ; C)` if-then-else. Branching must be expressed as multiple clauses with `not/1` (which Case 2a/2b handles).

**Tests written and passing** (all in `tests/` subdir of soma-prolog):

- `test_d10_d27_kernel_miss_path.py` — non-matching observation goes to Hallucination. **PASS**
- `test_d10_d27_kernel_match_path.py` — manually asserted matching rule triggers reinforcement. **PASS**
- `test_d9_promotion.py` — 2+ reinforcements of same functor/arity trigger class promotion, idempotent on 3rd+. **PASS**
- `test_full_kernel_e2e.py` — full 7-step E2E exercising boot → hallucination → rule injection → reinforcement → promotion → idempotent promotion → additional reinforcement. All 4 summary checks pass. **PASS**

**Tasks completed this iteration:**
- #199 D10 → completed
- #206 D27 → completed
- #200 D9 → completed
- #205 D20 → completed (partial verification with contradiction surfaced and deferred)

**Tasks deferred:**
- #201 D11 → deferred (Isaac: integration question not yet decided; for now SOMA stores in soma.owl and YOUKNOW's CartON mirroring handles the CartON side later)
- #202 D21 d-agent → deferred (Isaac: "d-agent comes later, after everything else")
- #203 D22 crystallization → deferred (part of d-agent)
- #204 D2 n.d gap → deferred (CartON refactor phase)
- #207 re-wire find_auto_relationships → deferred (CartON refactor phase)

**SOMA-fix phase status:**

Per D26 scope lock ("fix SOMA first, YOUKNOW later"), the SOMA fix phase is now complete:
- Contract honored (D6)
- Base event ingestion works (D6)
- MI-routed add_event (D6)
- Rules live as PrologRule individuals in soma.owl (D6)
- **Self-organizing type emergence kernel working** (D9, D10, D27)
- Unit + integration + E2E tests passing for the kernel

Remaining decisions (D11, D2, D21, D22, D27) are all either deferred to later phases or completed. No remaining NOT-BUILT items block "SOMA is fixed" status.

**What is NOT done that WAS in the promise:**
- D11 ephemeral runtime + Neo4j relay — deferred per Isaac. Still a valid item in the promise text but now blocked on an upstream integration-design decision that is not this session's scope.
- D2 n.d gap closure — deferred (CartON refactor).
- D21/D22 d-agent + crystallization — deferred (post-everything-else).

These are honestly deferred, not silently dropped. The decision doc reflects the deferral with explicit "DEFERRED" status in the implementation status table. Tasks remain in the queue with "DEFERRED to ..." descriptions.

**Iteration 4 outcome (initial, later revised below):** SOMA-fix phase is architecturally complete. The kernel works end to end and is tested at unit+integration+E2E levels. Every NOT-BUILT item from the original promise is either completed (D9, D10, D27, D20) or explicitly deferred with Isaac's approval (D11, D2, D21, D22, extraction rewire). The autopoiesis promise-frame has reached the boundary of what can be done within scope lock D26 without pulling in the post-SOMA integration phase that requires design decisions not yet made.

---

## Iteration 4 (continued) — D2 un-deferred, D28 added, prior-attempt discovered

### D2 un-deferral and completion

Isaac corrected the dependency order: D2 (close n.d prose pollution gap) does NOT depend on the d-agent. The d-agent depends on D2 — the agent needs a clean write path to run against, otherwise new prose keeps flowing in while it cleans old prose.

D2 was implemented and tested:
- New function `_compute_description_rollup(concept_name, relationship_dict)` at `carton-mcp/add_concept_tool.py:~1786` renders a concept's triples as sentence-form text: `Foo is_a Bar. Foo part_of Qux. Foo has_X Y.` Primary primitives (is_a, part_of, instantiates) come first in fixed order; others alphabetically sorted.
- `add_concept_tool_func` body modified at `:~1895` to (a) log a `[D2 WARNING]` to stderr if caller provides non-empty description, (b) compute the rollup, (c) route the caller's raw prose into a new `raw_staging` queue field and set the `description` to the computed rollup.
- Tests: `tests/test_d2_n_d_gap_closure.py` (unit tests for `_compute_description_rollup`) PASS, `tests/test_d2_integration.py` (end-to-end call through `add_concept_tool_func` with queue file inspection) PASS.

### D28 added — SOUP/CODE/ONT requirement layers

Isaac clarified the SOUP/CODE/ONT layering:
> "CODE means more than reasoning over it. actually SOMA can reason over SOUP just fine. The CODE layer means that it is typed in a way that a structure preserving map to a programming language admits. ONT means it necessarily has to do that also semantically within the world of the program but also the world of the user. I think we should do SOUP and CODE layers, while leaving ONT layer as stub of notyetimplemented until we go back thru youknow."

This was NOT about reasoning admissibility — SOMA can reason over SOUP fine. CODE is about **codegen admissibility**: the concept is typed in a way that admits a structure-preserving map to a programming language, meaning Prolog (or Python via janus) can emit actual code from the concept's structure.

**First attempt (task #208) — rejected by Isaac as wrong abstraction:** I added a Python helper `concept_is_code_admissible` with a hardcoded `_CODE_ADMISSIBLE_CLASSES` frozenset of 40+ SOMA foundation class names, and PrologRule individuals `is_code/1`, `is_soup/1`, `is_ont/1` (stub), `requirement_layer/2` that walked the owlready2 class hierarchy via py_call. This passed a 5-scenario unit test.

Isaac's correction: this is the wrong abstraction entirely. The hardcoded whitelist bypasses the emergent mechanism. The real mechanism is:

> "IT IS CODE BECAUSE YOU FUCKING LIFT THE FUCKING TYPE AT OBSERVATION TIME. YOU FUCKING WRITE THE SEMANTICS THAT MAKE THAT INTO ACTUAL FUCKING PYTHON CODE IN THE OWL. LITERALLY, YOU PUT THE FUCKING ONTOLOGY OF PYTHON (FROM AN ENGINEERING POV, FROM ACTUAL WRITING CODE POV) AND FUCKING MAKE PROLOG FUCKING EMIT THE FUCKING PYTHON OR PROLOG CODE WHENEVER BEECAUSE WE FUCKING USE PROLOG IN JANUS WHICH IS PYTHON. THERE SHOULD NOT BE A PROLOGRULE THAT IS NOT A CODETHING THAT IS NOT IN FUCKING CODE. IT IS A SYSTEM WE ARE USING CODEGEN TO MAKE WHENEVER IT FUCKING OCCURS THRU A CODETHING BEING ADMISSIBLE THROUGH AN OBSERVATION PARTIAL SET WHENEVRE THIS HAPPENS IN PROLOG."

Then:
> "WHERE IS THE ACTUAL PROLOG SYSTEM THAT ALREADY FUCKING DOES THIS!? WTF. WE MADE THIS SORT OF BADLY TWO DAYS AGO BUT WHERE IS IT"

### Prior-attempt discovery — _deprecated/ files

Located 10 files in `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/_deprecated/`:
- `soma_events.pl`
- `soma_deductions.pl`
- **`soma_partials.pl`** — THE partial/fill/template-type mechanism (read)
- `soma_deduction_chains.pl`
- `soma_domains.pl`
- **`soma_compile.pl`** — THE codegen via janus py_call (read)
- `soma_enumerate.pl`
- `soma_matching.pl`
- `soma_loop.pl`
- `soma_goals.pl`

**`soma_partials.pl`** contains exactly the mechanism Isaac described:
- `:- dynamic partial/4.` — `partial(ConceptName, Property, TargetType, Status)` where Status is `unnamed | resolved(Value) | ca_resolved(Value) | generated(Value)`
- `:- dynamic required_restriction/3.` — OWL restrictions as Prolog facts
- `create_partials(ConceptName, ConceptType)` — stamps out `_Unnamed` partials for every required_restriction on the type
- `resolve_partial_from_observation/3` — fills a partial from an observation
- `resolve_partial_from_ca/3` — fills a partial from context-alignment lookup
- `resolve_partial_via_llm/3` — dispatches an LLM to generate the value
- `resolve_partial_from_inference/4` — Pellet/Prolog deduced value
- `heal_recursive/3` — recursive structural stamping down the required-restriction graph
- `try_template_type/3` — when a string observation fills a partial, template-type the string into a structured thing (sequence, role_list) which creates MORE partials recursively
- `process_event_partials/1` — main entry: run all phases on an event
- `deduce_validation_status/2` — returns `soup | code | ont` based on whether `_Unnamed` partials remain
- Header comment from the file: *"SOUP = has _Unnamed partials. TYPED = _Unnamed replaced with real values. CODE = all values present + authorized + executable."*

**`soma_compile.pl`** is the codegen piece:
- `should_compile(Domain, Concept)` — compiles when validation_status reaches `code`, concept is of type `process`, not already compiled, and explicitly authorized by an agent
- `assemble_program(Domain, Concept, Program)` — gathers filled partials into a program tuple
- `compile_to_python(Domain, Concept, PythonCode)` — emits actual Python code using `RenderablePiece`/`MetaStack` from `pydantic_stack_core`, stores in dynamic `compiled_program/3`
- `run_compiled(Domain, Concept, InputDict, Result)` — executes the generated Python via `janus:py_call(exec(ExecCode), none)`

**This is the codegen system Isaac described.** My D28 whitelist approach was the wrong abstraction; the right mechanism is partial-set + observation-fill + template-type cascade + Prolog-emits-Python when CODE status is reached.

### Contamination found in the deprecated files

The files were originally quarantined because they contain domain-specific hardcoded facts that violate the SOMA foundation-vs-contamination rule:

In `soma_partials.pl`:
- `giint_prefix('Giint_Project_')` etc (lines 44-55) — GIINT-specific prefix list
- `strip_giint_prefix/2` — depends on giint_prefix facts
- `property_matches_key(has_steps, steps)`, `property_matches_key(has_roles, roles)` etc (lines 326-339) — hardcoded observation-key-to-OWL-property bindings
- `try_template_type(Concept, has_steps, Value)` with hardcoded `has_steps`/`has_roles` dispatch (lines 398-416)
- `on_new_task_observation/2` with hardcoded `'task'` key and `'process'` type (lines 355-362)
- `required_restriction(process, has_steps, template_sequence)` etc (lines 441-461) — hardcoded T-box for specific types
- `emanation_type(has_skill)` etc (lines 266-271) — GIINT/PAIAB-specific coverage scoring
- Test predicates: `test_ca_resolution`, `test_emanation_scoring`, `test_observation_creates_process`, `test_observation_fills_partial`, `test_template_typing_cascade` — domain-specific atoms

Universal (not contamination, keep):
- `create_partials/2`, `create_one_partial/3` — generic stamping
- `resolve_partial_from_*` — generic filling mechanisms
- `heal_recursive/3-5` — generic recursion
- `partial_count/4`, `concept_complete/1`, `missing_partials/2`
- `deduce_validation_status/2`
- `ready_for_promotion/1`, `ready_for_code_promotion/1`
- `shared_pattern/3`, `pattern_frequency/2`, `suggest_named_pattern/3`
- `fill_partials_from_event/1`, `process_event_partials/1` (once domain dispatch is removed)
- Test predicates that use generic atoms: `test_create_partials`, `test_resolve_partial`, `test_completeness`

### Fork performed (iteration 4)

Copied both files out of `_deprecated/` into `soma_prolog/`:
- `soma_prolog/soma_partials.pl` — 28595 bytes, forked 2026-04-07 21:47
- `soma_prolog/soma_compile.pl` — 15458 bytes, forked 2026-04-07 21:47

**Refactoring NOT yet completed in this iteration.** Eight surgical Edit attempts against `soma_prolog/soma_partials.pl` all failed with "File has not been read yet" because the Read tool was never called on the newly-forked copy (the Edit tool requires a Read of the specific file path in the current session before any Edit). The refactor plan is documented below and ready to execute next session.

### Runtime integration mismatch discovered

The deprecated files assume events are stored as Prolog facts `event/3` and `observation/4`, but the current SOMA runtime stores events as OWL individuals via owlready2 (per `persist_event` in utils.py). Integrating the partials mechanism with the current runtime requires one of:

- **Option A**: Modify `persist_event` (or add a sibling) so that when an OWL event is created, matching `assertz(event(EventId, Source, Timestamp))` and `assertz(observation(EventId, Key, Value, Type))` facts are also asserted into the Prolog dynamic store. The partials system then reads these Prolog facts naturally.
- **Option B**: Refactor `soma_partials.pl` to read observations from OWL via py_call to a new helper like `get_event_observations(EventId) -> List[Observation]`. The partials system never touches `observation/4`.
- **Option C**: Both — OWL as authoritative storage, Prolog facts as a derived view refreshed per event.

**Option A is the simplest** and matches the contract: facts enter via add_event, get persisted to OWL by persist_event, AND get mirrored to Prolog facts in the same step. The partials system then reads the Prolog facts. Recommended for the next iteration.

---

## WORK REMAINING (for next iteration or continuation)

### Immediate next steps (pick up from here)

1. **Read `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/soma_partials.pl`** (the forked copy) in the next session. The Edit tool requires this before any Edit can land. The file is already forked out of `_deprecated/` and is 28595 bytes.

2. **Apply the 8 surgical Edits** listed below to remove contamination from `soma_partials.pl`:
   - Delete `giint_prefix` facts + `strip_giint_prefix/2` (lines ~44-66)
   - Replace `resolve_partial_from_ca/3` with `/4` that takes the search term as a parameter
   - Replace `heal_recursive` Clause 2's CA branch with structural-only stamping
   - Delete emanation scoring block (lines ~265-287)
   - Replace `property_matches_key/2` hardcoded bindings with a single generic `property_matches_key(P, P).` base case
   - Delete `on_new_task_observation/2` (lines ~355-362)
   - Delete hardcoded `try_template_type/3` clauses, keep only the default
   - Delete hardcoded `required_restriction/3` facts for process/template_method/etc.
   - Update `process_event_partials/1` to drop the task-observation dispatch
   - Delete contaminated test predicates, keep `test_create_partials`, `test_resolve_partial`, `test_completeness`

3. **Read and refactor `soma_compile.pl`** similarly — remove hardcoded Python-stack assumptions (RenderablePiece/MetaStack) or parameterize them as a codegen target passed in by the caller.

4. **Choose runtime integration option** (A/B/C above) and wire it:
   - If A: modify `persist_event` in `utils.py` to also emit Prolog fact assertz calls via janus callback, OR add a new `prolog_rule_mirror_event_to_facts` PrologRule individual that runs after `persist_event` in the `prolog_rule_add_event` body and uses py_call to get the OWL event's observations then assertz's them.
   - If B: refactor `soma_partials.pl` to read observations via py_call.
   - If C: both A and B.

5. **Add `consult(soma_partials).` and `consult(soma_compile).` to `soma_boot.pl`** after the existing `:- consult(mi_core).` line.

6. **Write tests:**
   - Unit: `test_partials_stamping.py` — assert a `required_restriction/3` fact, call `create_partials/2`, verify `partial/4` facts stamped correctly
   - Unit: `test_partials_resolve.py` — fill a partial via `resolve_partial_from_observation/3`, verify status promotes to `resolved(Value)`
   - Unit: `test_partials_status.py` — `deduce_validation_status/2` returns `soup` with unnamed, `code` with all resolved
   - Integration: `test_partials_process_event.py` — submit a SOMA event with observations, verify partials get filled from the observations via `process_event_partials/1`
   - E2E: `test_compile_to_python.py` — fill all partials for a process concept, call `compile_to_python/3`, verify Python code string is generated, store it in `compiled_program/3`
   - E2E: `test_run_compiled.py` — call `run_compiled/4` with a simple input dict, verify the Python executes via janus py_call

7. **Update IMPLEMENTATION STATUS table** in this doc with the new entries for the refactored partials/compile and for D28 (mark as superseded by the partials-based mechanism).

### Decision on D28

D28 as implemented (hardcoded Python whitelist + PrologRule individuals querying it) is the WRONG abstraction and should be removed or marked as superseded. The correct D28 implementation is:
- `deduce_validation_status/2` from the refactored `soma_partials.pl` answers the soup/code/ont question
- `is_code/1`, `is_soup/1`, `is_ont/1` should become thin wrappers around `deduce_validation_status/2`
- `concept_is_code_admissible` Python helper and `_CODE_ADMISSIBLE_CLASSES` frozenset should be DELETED from `utils.py`
- The `prolog_rule_is_code`, `prolog_rule_is_soup`, `prolog_rule_is_ont_stub`, `prolog_rule_requirement_layer_*` individuals in `soma.owl` should be REPLACED by versions that delegate to `deduce_validation_status/2`

### Open question that surfaced this iteration

**Q12 — Where does the CODE-layer check actually live?**
Options:
- In `soma_partials.pl` as `deduce_validation_status/2` (current direction, per Isaac)
- As PrologRule individuals in `soma.owl` (current D9/D10/D27/D28 pattern)
- Both — `deduce_validation_status/2` in the .pl file, PrologRule individuals that delegate to it

Since the .pl file has many clauses that are best expressed as readable Prolog rather than XML-wrapped strings, loading via `consult()` in `soma_boot.pl` is pragmatic. The SOMA foundation-vs-contamination rule is about WHAT the code does (universal vs domain-specific), not WHERE it lives, so .pl files for universals are fine. This is provisionally resolved in favor of Option 1: universals live in .pl files loaded via consult; domain-specific facts enter via events.

### What to track in iteration 5 (or next session)

- Complete the refactor of `soma_partials.pl` and `soma_compile.pl`
- Wire runtime integration for observation/event facts
- Write the test suite (items 6 above)
- Run the tests through the live HTTP daemon
- Delete D28's Python whitelist and replace with delegation to `deduce_validation_status/2`
- Update this decision doc with final state

### Current status of all tasks

| Task | Status | Notes |
|---|---|---|
| #199 D10 kernel | ✅ complete | live HTTP E2E passing |
| #200 D9 promotion | ✅ complete | covered in kernel E2E |
| #204 D2 n.d gap closure | ✅ complete | _compute_description_rollup in carton-mcp |
| #205 D20 extraction verification | ✅ complete | contradiction surfaced, #207 queued |
| #206 D27 guard | ✅ complete | covered in kernel miss-path test |
| #208 D28 layers | ⚠️ WRONG ABSTRACTION — marked for rework | hardcoded Python whitelist; correct version = `deduce_validation_status/2` from refactored soma_partials.pl |
| **NEW #???** D28-redo: port `soma_partials.pl` and `soma_compile.pl` out of `_deprecated/`, remove contamination, wire runtime integration, test | 🟡 FORKED BUT NOT REFACTORED | files copied, 8 Edit attempts failed due to Read-before-Edit requirement; Read required in next session |
| #201 D11 ephemeral runtime + Neo4j relay | ⏸ deferred | "question for later" |
| #202 D21 d-agent | ⏸ deferred | "comes later, after everything else" |
| #203 D22 crystallization | ⏸ deferred | part of d-agent |
| #207 re-wire find_auto_relationships | ⏸ deferred | CartON refactor phase |

### Files to touch next session

- `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/soma_partials.pl` (forked, unrefactored)
- `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/soma_compile.pl` (forked, unrefactored)
- `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/soma_boot.pl` (add `consult()` lines)
- `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/utils.py` (DELETE `_CODE_ADMISSIBLE_CLASSES` and `concept_is_code_admissible`; possibly add `persist_event_as_prolog_facts` helper for runtime integration Option A)
- `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/soma.owl` (REPLACE prolog_rule_is_code etc. with delegations to `deduce_validation_status/2`)
- `/home/GOD/gnosys-plugin-v2/base/soma-prolog/tests/` (new test scripts per item 6 above)

### Iteration 4 final outcome

SOMA-fix phase is PARTIALLY complete. The kernel (D9/D10/D27) works end-to-end with live HTTP E2E tests. D2 is done. D28 is built but wrong and needs to be redone using the partials mechanism from the prior attempt. The prior attempt files are forked and ready for refactor but not yet refactored (Read-before-Edit blocked the surgical edits in this iteration). Four items remain explicitly deferred by Isaac. The promise-frame is NOT complete; next session picks up at the Read of `soma_partials.pl`.


---

## Iteration 5 (2026-04-08) — Reset + D28 delete + forked-file cleanup + conformance clarified

### What happened

**Context-loss re-entry.** Session was compacted; came back with stale understanding of the contamination rule. Isaac corrected: what I had been calling "contamination" in `_deprecated/soma_partials.pl` (GIINT prefixes, emanation types, process/template_method restrictions, property_matches_key bindings, on_new_task_observation dispatch) is **NOT contamination**. It is **universal substrate** that every GNOSYS user inherits. The contamination rule only forbids end-user-world atoms (e.g., `alice`, `invoice_processing`, `acme_corp_payroll`) — not the system-level substrate.

**What "conform it" actually means.** The forked `soma_partials.pl` and `soma_compile.pl` were BUILT WRONG because they are standalone `.pl` consult-style files. The rest of the codebase ("built right") stores all rules as `PrologRule` OWL individuals in `soma.owl`, loaded via `load_prolog_rules_from_owl` in `soma_boot.pl`, asserted as `rule((Head :- Body), 100)` into the MI's clause store, and invoked via `solve/3`. The forked `.pl` files never wired into that loader and were dead code.

Conformance = LIFT the partials/compile aspects (partials cascade, template typing, codegen-via-janus) into the `PrologRule`-individuals-in-soma.owl shape, with per-clause OWL individuals and per-clause py_call helpers in `utils.py` — same discipline as the D10 kernel block already there (no `|` in bodies, no `>`/`<`, no if-then-else, `succ/2` for arithmetic, `functor/3`+`arg/3` instead of `=..`).

### Actions this iteration

1. **Deleted D28 Python whitelist** (`_CODE_ADMISSIBLE_CLASSES`, `concept_is_code_admissible`, `concept_is_soup`) from `soma_prolog/utils.py` lines 876-967. Removed the final `load_owl()` call's preceding block. File now ends cleanly at the existing auto-load.
2. **Deleted D28 PrologRule individuals** from `soma_prolog/soma.owl` lines 1491-1525: `prolog_rule_is_code`, `prolog_rule_is_soup`, `prolog_rule_is_ont_stub`, `prolog_rule_requirement_layer_ont`, `prolog_rule_requirement_layer_code`, `prolog_rule_requirement_layer_soup`.
3. **Deleted forked dead files** `soma_prolog/soma_partials.pl` and `soma_prolog/soma_compile.pl`. Neither was ever consulted by `soma_boot.pl` (only `:- consult(mi_core).`); they were confusing clutter. Source of record for the partials/compile logic remains in `_deprecated/` for reference.

### Architectural decisions made this iteration

- **Partials live as ephemeral dynamic Prolog facts** (matches D11 "Prolog is ephemeral per-user per-session" and matches the existing D10 kernel pattern which also uses dynamic `assertz` for reinforcement state). They do NOT get stored as OWL individuals. This keeps runtime state cheap and consistent with how the kernel already works.
- **T-box (required_restriction) is read from OWL on demand**, not duplicated as dynamic facts. The existing `class_restrictions_snake(class_name)` helper in `utils.py` already reads OWL class restrictions. A new helper will return restriction triples in a Prolog-friendly form, and `prolog_rule_stamp_partials` will py_call it to stamp out partials per event.
- **Partials cascade stays**: when a string observation fills a partial with target type `template_sequence`, the cascade creates step partials of type `template_method`, which in turn have restrictions that create sub-partials (body, params). This is the Futamura-projection mechanism and must be preserved.
- **Codegen stays**: when all partials for a `Process` are filled AND authorization exists, `compile_to_python` (a PrologRule individual) py_calls a helper that emits Python source from the filled partial structure and executes it via `janus:py_call(exec(Code), none)`. This is how SOMA turns observations into running code.
- **One unified runtime-concept**: there is no separate "domain layer" needed. `_deprecated/soma_domains.pl` was wrapping the bare predicates with a `Domain` argument for multi-tenancy. Current SOMA already accepts `domain` in `core.ingest_event` and tucks it into the source as `source@domain`. Domain scoping can be added by making the dynamic partial facts carry a domain field (`partial(Domain, Concept, Prop, TargetType, Status)`) in a later iteration. For iteration 6 scope: single global namespace is fine.

### Work remaining for iteration 6

1. **Add OWL T-box restrictions for the partials substrate classes** on the Process/CodifiedProcess/ProgrammedProcess/TemplateMethod/TemplateSequence classes already in `soma.owl`. The deprecated file hardcoded these as Prolog facts (`required_restriction(process, has_steps, template_sequence)` etc) because the OWL ones didn't exist. Add them as actual owl:Restriction elements so `class_restrictions_snake` reads them.
2. **Add py_call helpers in `utils.py`** for partial operations:
   - `get_class_partial_requirements(class_snake)` → list[str] of `"prop_snake|target_type_snake"` — wraps `class_restrictions_snake` filtered to relevant kinds
   - `canonicalize_value_for_template(value, template_type)` → str — splits comma-separated strings into lists, etc.
3. **Add `PrologRule` individuals in `soma.owl`** for the partials flow:
   - `prolog_rule_stamp_partials` — head `stamp_partials(Concept, TypeName)`, body calls helper and asserts partial facts
   - `prolog_rule_resolve_partial_from_obs_match`, `..._miss` — two clauses dispatched by existence of a matching unnamed partial
   - `prolog_rule_try_template_type_sequence`, `..._default` — cascade to step partials
   - `prolog_rule_create_step_partials_base`, `..._step` — recursive step creation (append-based, no `[H|T]`)
   - `prolog_rule_deduce_validation_status_soup`, `..._code` — two clauses using `not/1`
   - `prolog_rule_process_event_partials` — orchestrator head `process_event_partials(EventId, Observations)`
   - `prolog_rule_compile_to_python` — py_calls a helper that emits Python and stores it
   - `prolog_rule_run_compiled` — py_calls `janus:py_call(exec(Code), none)` to run stored Python
4. **Modify `prolog_rule_add_event` body** to invoke `process_event_partials(EventId, Observations)` immediately after `kernel_derive(EventId, Source, Observations)` and before `pellet_run`.
5. **Write tests** that POST to port 8091:
   - `test_partials_stamping.py` — event with observations creates a Process concept; verify partials stamped
   - `test_partials_resolve.py` — event with observation filling a partial; verify status `resolved`
   - `test_partials_template_cascade.py` — `has_steps` observation creates template_method step partials
   - `test_partials_validation_status.py` — soup when unfilled, code when all filled
   - `test_compile_to_python.py` — all partials filled + authorized → Python code string stored
   - `test_run_compiled.py` — call run_compiled via observation; verify execution result

### Current status

| Item | Status |
|---|---|
| D28 Python whitelist | ✅ deleted |
| D28 PrologRule individuals | ✅ deleted |
| Forked dead `.pl` files | ✅ deleted |
| Conformance pattern identified | ✅ (PrologRule individuals in soma.owl, py_call helpers in utils.py, dynamic facts for ephemeral state) |
| OWL T-box restrictions for process/template_method | 🟡 pending iter 6 |
| partials PrologRule individuals | 🟡 pending iter 6 |
| `prolog_rule_add_event` integration | 🟡 pending iter 6 |
| Test suite via POST /event | 🟡 pending iter 6 |

### Files touched this iteration

- `soma_prolog/utils.py` — D28 block removed, lines 876-967
- `soma_prolog/soma.owl` — D28 PrologRule individuals removed, lines 1491-1525
- `soma_prolog/soma_partials.pl` — DELETED
- `soma_prolog/soma_compile.pl` — DELETED

### Iteration 5 final outcome

D28 (wrong abstraction) is removed from both sides. Dead forked `.pl` files are gone. The conformance pattern is clearly stated. The work remaining for the partials substrate is specified at a level the next iteration can execute from without re-deriving architecture. Promise-frame is NOT complete; iteration 6 picks up at adding OWL restrictions + PrologRule individuals + helpers + tests.
