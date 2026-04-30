# D10 + D27 Test Log — 2026-04-07 iteration 4

## What was tested

- **D10** (Decision_D10_Rule_Derivation_Kernel_Is_Minimal_Missing_Piece): the rule-derivation kernel as a set of PrologRule individuals loaded from `soma.owl` into the MI's rule store on boot.
- **D27** (Decision_D27_Structure_Preserving_Maps_Gate_Type_Emergence_Non_Preserving_Become_Hallucinations): the anti-explosion guard — structure-preserving map check before lifting, Hallucination event emission on non-match.

## What was implemented

13 new `PrologRule` individuals added to `soma_prolog/soma.owl` and wired into the `prolog_rule_add_event` body so the kernel fires after `persist_event` and before `pellet_run`:

1. `prolog_rule_kernel_derive_base` — `kernel_derive(_EventId, _Source, [])` → `true`
2. `prolog_rule_kernel_derive_step` — `kernel_derive(EventId, Source, List)` → `(append([Obs], Rest, List), kernel_process_observation(EventId, Source, Obs), kernel_derive(EventId, Source, Rest))`
3. `prolog_rule_kernel_process_observation_match` — `kernel_process_observation(EventId, _Source, Obs)` → `(structure_preserving_match(Obs), kernel_reinforce(EventId, Obs))`
4. `prolog_rule_kernel_process_observation_miss` — `kernel_process_observation(EventId, Source, Obs)` → `(not(structure_preserving_match(Obs)), kernel_emit_hallucination(EventId, Source, Obs))`
5. `prolog_rule_structure_preserving_match_rule` — `structure_preserving_match(Obs)` → `(rule((Head :- _Body), _CF), structure_preserving_map(Obs, Head))`
6. `prolog_rule_structure_preserving_match_fact` — `structure_preserving_match(Obs)` → `(rule(Head, _CF), compound(Head), structure_preserving_map(Obs, Head))`
7. `prolog_rule_structure_preserving_map` — `structure_preserving_map(A, B)` → `(nonvar(A), nonvar(B), compound(A), compound(B), functor(A, F, Arity), functor(B, F, Arity), args_preserve_by_index(A, B, Arity))`
8. `prolog_rule_args_preserve_by_index_base` — `args_preserve_by_index(_A, _B, 0)` → `true`
9. `prolog_rule_args_preserve_by_index_step` — `args_preserve_by_index(A, B, N)` → `(succ(Prev, N), arg(N, A, ArgA), arg(N, B, ArgB), arg_preserves(ArgA, ArgB), args_preserve_by_index(A, B, Prev))`
10. `prolog_rule_arg_preserves_identical` — `arg_preserves(X, Y)` → `X == Y`
11. `prolog_rule_arg_preserves_var_target` — `arg_preserves(_X, Y)` → `var(Y)`
12. `prolog_rule_arg_preserves_var_source` — `arg_preserves(X, _Y)` → `var(X)`
13. `prolog_rule_kernel_reinforce` — `kernel_reinforce(EventId, Obs)` → `assertz(kernel_reinforcement(EventId, Obs))`
14. `prolog_rule_kernel_emit_hallucination` — `kernel_emit_hallucination(EventId, Source, Obs)` → `assertz(kernel_hallucination(EventId, Source, Obs))`

`prolog_rule_add_event` body updated to insert `kernel_derive(EventId, Source, Observations)` immediately after `persist_event(Source, Observations, EventId)`.

## Bootstrap-loader constraints discovered while testing

1. **The `_scrub_pipe` function at `soma_prolog/utils.py:621-625` replaces every `|` with `/` before the loader splits the rule string.** Any list-cons syntax `[H|T]` or `=..` destructure `[F|Args]` in a rule head or body gets corrupted at load time. **All list operations must use `append/3`, `functor/3` + `arg/3`, or index recursion via `succ/2` instead.**

2. **`owl_save` (owlready2 serializer) does not safely round-trip rule body strings containing `>`, `<`, or `&`.** A body containing `N > 0` was written to disk in a form that broke XML parsing on the next load (`<soma:hasRuleBody literal((N > 0, ..` fragments were emitted instead of proper `<hasRuleBody>...&gt;...</hasRuleBody>`). **Rule bodies must avoid all XML-sensitive characters.** Use `succ/2` instead of `>` for arithmetic comparisons.

3. **The MI's `solve/5` does not handle `(A -> B ; C)` if-then-else.** Those operators fall through to Case 7 (native `call/1`), which does not resolve user-defined predicates stored in the MI's `rule/2` store. **Branching must be expressed as multiple clauses using `not/1` which Case 2a/2b handles.**

Documented these constraints in `soma.owl` as an inline comment above the kernel rules, and below as well.

## Test suite

### Test 1 — Miss path (`test_d10_d27_kernel_miss_path.py`)

**Input**: submit an event with observations `[{k:test_key_alpha, v:test_value_alpha, t:string_value}, {k:test_key_beta, v:42, t:int_value}]` against a freshly-booted SOMA with no existing rules whose head matches `obs/3`.

**Expected**: both observations fail the structure-preserving map check, both are emitted as `kernel_hallucination/3` facts. The `add_event` chain returns the expected report format.

**Result**: PASS.
- `ingest_event result: event=evt_1775588969.317486 source=test_kernel_d10 observations=2 pellet=ok deduction_chains_fired=0 unmet=0\nall_core_requirements_met`
- `kernel_hallucination/3 entries: 2`
- Both tests PASS, OVERALL PASS

### Test 2 — Match path (`test_d10_d27_kernel_match_path.py`)

**Input**: after SOMA boots, manually assert `rule((obs(_A, _B, _C) :- true), 100)` into the MI's rule store (variables in all arg positions so `arg_preserves` succeeds via the `var(Y)` clause). Then submit an event with one observation of shape `obs(k, v, string_value)`.

**Expected**: the structure-preserving map check succeeds (variables match via `var/1`), `kernel_reinforce` fires, `kernel_reinforcement/2` fact is asserted. The `add_event` chain returns the expected report.

**Result**: PASS.
- `assertz(rule((obs(_A,_B,_C) :- true), 100))` succeeds
- `structure_preserving_match` proves via the matching-rule path
- `ingest_event result: event=evt_1775589065.330092 source=reinforce_test observations=1 pellet=ok deduction_chains_fired=0 unmet=0\nall_core_requirements_met`
- `kernel_reinforcement/2 entries: 1`
- PASS

## Known benign warnings

- `janus_swi` emits `Domain error: 'py_term' expected, found 'proven(...)'` for some queries that return complex nested Prolog terms. The underlying Prolog goals succeed — the error is in the Python-side result serialization on janus's fast path. Test code catches these and checks the error message text for `proven(...)` vs `failure(...)` to determine actual success.
- `kernel_hallucination/3` and `kernel_reinforcement/2` emit "no previous definition" warnings on the first `assertz` call because they are not pre-declared as dynamic. This is cosmetic — SWI-Prolog autoclassifies the predicate as dynamic on first `assertz`.

## What is NOT tested here (deferred)

- **Live HTTP E2E test via `POST /event`** to the running `soma-prolog-mcp` HTTP server. The unit tests import `soma_prolog.core` and call `ingest_event` directly in-process, which exercises the full Prolog path but not the HTTP transport. The HTTP path is a thin wrapper per the SOMA contract (one endpoint, delegates to `core.ingest_event`) so passing the in-process test is strong evidence the HTTP path also works. A dedicated HTTP test will be added during D11 (ephemeral runtime conversion) where HTTP lifecycle becomes load-bearing.
- **Long-running kernel behavior** — pattern accumulation over many events, lifting heuristics, threshold-based promotion. The current kernel just does per-event match/miss; the pattern accumulation logic belongs to D9 (the next task).
- **Neo4j relay interaction** — not yet present; D11 work.

## Status after this iteration

- **D10 → COMPLETE** (task #199)
- **D27 → COMPLETE** (task #206)
- **D6 → still verified complete** (no change)

Next in the dependency order per the iteration 3 promise: **D9** (wire self-organizing type emergence into SOMA via the rule-derivation kernel — builds on D10), then **D11** (convert to ephemeral per-user runtime with live Neo4j relay).

---

## D9 (iteration 4 addendum)

### Additional PrologRule individuals

Added on top of the D10+D27 kernel:

- `prolog_rule_kernel_check_promotion` — `kernel_check_promotion(Obs)` → `(functor(Obs, F, Arity), count_reinforcements_with_functor(F, Arity, N), promote_if_threshold(F, Arity, N))`
- `prolog_rule_count_reinforcements_with_functor` — `count_reinforcements_with_functor(F, Arity, N)` → `(findall(Obs, (kernel_reinforcement(_E, Obs), functor(Obs, F, Arity)), L), length(L, N))`
- `prolog_rule_promote_if_threshold_one` — `promote_if_threshold(_F, _Arity, 1)` → `true` (base case: 1 reinforcement = no promotion)
- `prolog_rule_promote_if_threshold_already` — `promote_if_threshold(F, Arity, _N)` → `kernel_pattern_is_class(F, Arity)` (already promoted, noop)
- `prolog_rule_promote_if_threshold_new` — `promote_if_threshold(F, Arity, _N)` → `(not(kernel_pattern_is_class(F, Arity)), assertz(kernel_pattern_is_class(F, Arity)))` (first promotion)

`kernel_reinforce` body updated to: `(assertz(kernel_reinforcement(EventId, Obs)), kernel_check_promotion(Obs))` — every reinforcement now triggers a promotion check.

### Test — `test_d9_promotion.py`

**Input**: assert rule `rule((obs(_A, _B, _C) :- true), 100)` with variables so observations structurally match; submit two events each with one obs observation.

**Expected**: after 1st submission, reinforcement count = 1 (or 2 including the earlier boot event), no class promotion; after 2nd submission, count crosses threshold, `kernel_pattern_is_class(obs, 3)` asserted.

**Result**: PASS.
```
Step 1: Assert matching rule — asserted
Step 2: Submit 1st matching observation — reinforcement count grew, no class promotion yet
Step 3: Submit 2nd matching observation — kernel_pattern_is_class(obs, 3) exists: True
Verdict: PASS — 2+ reinforcements triggered class promotion
```

### Notes

- Threshold is hardcoded as "not equal to 1" meaning any count ≥ 2 triggers promotion. This is the minimal Isaac-said "you said this twice → it's a type" threshold. Higher-tier promotions (class → template → universal) are not implemented yet and are deferred.
- The promotion is idempotent: the `promote_if_threshold_already` clause checks `kernel_pattern_is_class(F, Arity)` first, so repeated promotions on the same functor don't duplicate the fact.
- D9 depends on D27 structurally: promotion only happens via the reinforce path, which only fires after structure_preserving_match succeeds. Non-conforming observations go to Hallucination events and never reach the promotion logic. This is the D27 guard enforcing self-organizing type emergence.

### Status update

- **D9 → COMPLETE** (task #200)
- **D10 → COMPLETE** (task #199)
- **D27 → COMPLETE** (task #206)

Next: **D11** (convert SOMA Prolog runtime to ephemeral per-user-per-session with live Neo4j relay).

---

## D2 (iteration 4 addendum) — n.d prose pollution gap closure

### Why D2 moved out of deferred

Isaac iteration 4: "d gap closure doesn't depend on d-agent existing that is backwards. d-agent depends on d gap closure existing. Obviously that is what should be done next." D2 must come BEFORE the d-agent because the d-agent needs a clean write path to run against — otherwise new prose keeps flooding in while the agent tries to clean up old prose.

### What was implemented

New function `_compute_description_rollup(concept_name, relationship_dict) -> str` at `carton-mcp/add_concept_tool.py` (before `add_concept_tool_func`). Renders the concept's triples as sentence-form text:

```
Foo is_a Bar, Baz. Foo part_of Qux. Foo instantiates Pattern_X. Foo has_something Y.
```

Primary strong-compression primitives (`is_a`, `part_of`, `instantiates`) come first in that fixed order; everything else is alphabetically sorted. Empty relationship_dict produces an empty string.

Modifications to `add_concept_tool_func`:

1. Before queuing the concept, capture the caller's raw description in `_caller_raw_description` and log a `[D2 WARNING]` to stderr if it is non-empty. The warning explicitly tells the calling agent that raw prose is staging-area-only and the stored description is computed from triples.

2. Compute the rollup via `_compute_description_rollup(concept_name, relationship_dict)` and set `queue_data["description"]` to the computed rollup. The caller's raw prose is preserved in a new `queue_data["raw_staging"]` field so future d-agent work (D21) can read it and extract triples from staged prose.

3. Work around a local-variable-shadowing issue: `add_concept_tool.py:2022` has a later `import sys` inside the function body, which would shadow the module-level `sys` and cause an `UnboundLocalError` at my earlier `file=sys.stderr` call. Used `import sys as _d2_sys` at the warning site to avoid the shadowing without modifying the existing inner import.

### Reconciliation with D1

D1 says description is a writable staging area for unstructured language awaiting extraction. D2 does not delete the field — it keeps description as the caller's input slot (the staging area). What D2 changes is where the raw prose gets STORED: instead of going verbatim into Neo4j's `n.d` field, it goes into the new `raw_staging` slot, and `n.d` receives a computed rollup from the triples. The staging area is preserved; its storage location is fixed.

### Test results

- **Unit test** — `tests/test_d2_n_d_gap_closure.py`. Exercises `_compute_description_rollup` in isolation with empty dict, single is_a, primary primitives in correct order, multiple targets joined with comma, and primary + alphabetically-sorted secondary relationships. All 3 scenarios PASS.
- **Integration test** — `tests/test_d2_integration.py`. Calls the full `add_concept_tool_func` end-to-end with `hide_youknow=True` and `_skip_ontology_healing=True`, catches the real queue file written to disk at `/tmp/test_d2_heaven_data/carton_queue/`, parses the JSON, and verifies: (1) `raw_staging` preserves the caller prose verbatim, (2) `description` is the expected computed rollup, (3) raw prose does NOT leak into description, (4) relationships are preserved. All 4 checks PASS.
- **Live daemon** — not exercised because the D2 work is in the write path (queue file creation) which is upstream of the daemon. The daemon's responsibility to correctly persist the new `raw_staging` field in Neo4j is a follow-on concern (the daemon currently ignores unknown queue fields harmlessly, and the rolled-up `description` goes through the existing merge logic which now stores the rollup instead of the raw prose).

### Known follow-on work (not this session)

- **Daemon-side raw_staging persistence**: the daemon currently stores `description` in Neo4j `n.d` but does not do anything with the new `raw_staging` field. The field is in the queue JSON but the daemon drops it. When the d-agent (D21) is built, that's when the `raw_staging` field needs to become a Neo4j property on the concept node (e.g., `n.raw_staging`). For now the field is preserved in the queue archive for audit but not in Neo4j.
- **Existing prose migration**: the D15 decision says existing polluted `n.d` values stay until the d-agent migrates them. D2 only closes the gap for NEW writes. Old concepts with prose in n.d remain as-is.

### Status update

- **D2 → COMPLETE** (task #204)
- In-scope implementation work remaining: D11 (still pending Isaac's integration-design decision — deferred)
- Out-of-scope deferred: D21, D22, #207 (d-agent pipeline, post-D2)

---

## D28 (iteration 4 addendum) — SOUP / CODE / ONT requirement layer predicates

### Why D28 was added this session

Isaac iteration 4 clarified the SOUP/CODE/ONT layering:

> "CODE means more than reasoning over it. actually SOMA can reason over SOUP just fine. The CODE layer means that it is typed in a way that a structure preserving map to a programming language admits. ONT means it necessarily has to do that also semantically within the world of the program but also the world of the user. I think we should do SOUP and CODE layers, while leaving ONT layer as stub of notyetimplemented until we go back thru youknow."

This clarified that:
- **SOUP** = concept submitted but does not meet CODE or ONT requirements
- **CODE** = concept's structure admits a structure-preserving map into a programming language (SOMA's domain)
- **ONT** = CODE + semantic closure in program-world AND user-world (YOUKNOW's domain, deferred)

SOMA was implicitly doing CODE admissibility via the kernel's structure-preserving map check (D27), but there was no first-class queryable predicate `is_code/1` that a caller could ask "is this concept at CODE level?". D28 adds the explicit predicates.

### What was implemented

**Python helper in `utils.py`:**

- `_CODE_ADMISSIBLE_CLASSES` — frozenset of 40+ SOMA foundation class names (TypedValue hierarchy, Event, Observation, PrologRule, Process hierarchy, system actors, dispatch types, template/Futamura classes, code entity model)
- `concept_is_code_admissible(concept_name: str) -> str` — looks up the OWL individual by name, walks its type chain and ancestors, returns the Prolog-atom-friendly string `"yes"` if any type or ancestor is in the admissible set, `"no"` otherwise. Returns `"no"` for non-existent concepts or exceptions.
- `concept_is_soup(concept_name: str) -> str` — inverse of the above.

String return type is intentional: janus marshals Python strings to Prolog atoms, which lets the rule body unify directly against `yes` without wrestling with janus boolean marshaling (Python `True` becomes `@true`, not the atom `true`).

**PrologRule individuals in `soma.owl`:**

- `prolog_rule_is_code` — `is_code(Concept)` → `py_call('soma_prolog.utils':concept_is_code_admissible(Concept), yes)` — succeeds iff the helper returns `"yes"`.
- `prolog_rule_is_soup` — `is_soup(Concept)` → `not(is_code(Concept))` — uses the MI's Case 2 not-handling.
- `prolog_rule_is_ont_stub` — `is_ont(_Concept)` → `fail` — explicit stub, always fails, deferred to YOUKNOW refactor phase.
- `prolog_rule_requirement_layer_ont` — `requirement_layer(Concept, ont)` → `is_ont(Concept)`
- `prolog_rule_requirement_layer_code` — `requirement_layer(Concept, code)` → `(not(is_ont(Concept)), is_code(Concept))`
- `prolog_rule_requirement_layer_soup` — `requirement_layer(Concept, soup)` → `(not(is_ont(Concept)), not(is_code(Concept)))`

Three-clause `requirement_layer/2` with mutually-exclusive `not()` guards avoids Prolog cut (`!`) which the MI's `solve/5` does not handle correctly.

### Test results — `tests/test_d28_requirement_layers.py`

All 5 scenarios PASS:

| # | Scenario | Result |
|---|---|---|
| 1 | `concept_is_code_admissible(<event_id>)` Python helper returns `"yes"` for an Event individual | PASS |
| 1b | `concept_is_code_admissible("nonexistent_concept_xyz")` returns `"no"` | PASS |
| 2 | `solve(is_code('<event_id>'), Out)` proves via the MI | PASS |
| 3 | `solve(is_soup(totally_made_up_concept_123), Out)` proves via the not(is_code) path | PASS |
| 4 | `solve(is_ont('<event_id>'), Out)` fails (stub always fails) | PASS |
| 5 | `solve(requirement_layer('<event_id>', Layer), Out)` binds Layer to `code` | PASS |
| 5b | `solve(requirement_layer(totally_made_up_123, Layer), Out)` binds Layer to `soup` | PASS |

### Bootstrap loader constraint discovered

**Janus atom quoting:** when passing Prolog atoms that contain special characters (like `.`) through janus query strings, the atom must be quoted with single quotes. Example: `solve(is_code('evt_1775597690.075671'), Out)` — without the quotes, Prolog parses the dot as end-of-term and the goal becomes malformed. Documented in the test script.

### Status update

- **D28 → COMPLETE** (new task created)
- SOMA now has queryable `is_code/1`, `is_soup/1`, `is_ont/1` (stub), and `requirement_layer/2` predicates as first-class SOMA capabilities.
- The ONT tier remains a stub that always fails, explicitly marked as deferred to the YOUKNOW refactor phase per Q9.
