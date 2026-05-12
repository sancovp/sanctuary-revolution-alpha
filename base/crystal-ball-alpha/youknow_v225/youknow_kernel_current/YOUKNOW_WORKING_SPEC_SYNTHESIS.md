# YOUKNOW Working Spec (Synthesis, Complete)

Status: Working specification for implementation
Version: 1.0 (compiled from current discussion)
Related file: `YOUKNOW_USER_EXPLANATIONS_VERBATIM.md`

## 1. Scope
This spec defines the intended behavior of the YOUKNOW compiler rollup (`youknow(statement)`), including:
- EMR progression
- ABCD grounding
- SES typed-depth measurement
- compression semantics (weak vs strong)
- SOUP -> ONT admission
- post-admission simulation/codegen witness behavior

This spec is implementation-facing. It preserves current outward error-return style.

## 2. Non-Negotiable Definitions
`youknow(statement)`
- The single public compiler rollup entrypoint.

`programs`
- Means strengthened/compiled state.
- Does not mean "text was generated".

`SES typed-depth`
- Measures constructor typing depth: how many constructor args are present and how deeply they are typed before arbitrary-string leaves appear.
- This is an arity/decomposition metric, not a generic confidence metric.

`strong compression`
- True iff both are true:
1. MSC exists for target entity/subgraph.
2. Every required relationship in the derivation chain has `justifies`.

`weak compression`
- Not strong compression.

`admission to ONT`
- Allowed only when:
1. strong compression is true,
2. CatOfCat superclass chain is declared bounded,
3. no blocking validator violations.

`SOUP`
- Valid holding state for unresolved structure; not discard.

## 3. System Objective
Allow an LLM-driven REPL flow where free-form statements are progressively strengthened into typed ontology structure, such that:
- missingness is explicit and iterable,
- closure is measurable,
- admission is deterministic,
- and admitted structures can optionally be simulated via codegen.

## 4. End-to-End Compile Phases
### Phase 0: Input Capture
Input: `statement` (string)
Output: `CompilePacket.source_statement`

Requirements:
- Preserve raw text.
- Preserve current parse failure output style.

### Phase 1: Parse and Canonicalize
Input: source statement
Output: canonical claim packet:
- subject
- predicate
- object
- additional relations
- normalized relation keys

Requirements:
- Normalize relation vocabulary to internal canonical forms.
- Keep original tokens for human-facing output.

### Phase 2: ABCD Grounding Trigger
Rule:
- If claim is underspecified/unknown in current typed state, enforce ABCD grounding path.

ABCD scaffold:
- A: intuition
- B: compareFrom
- C: mapsTo
- D: analogicalPattern

Output:
- ABCD completeness status
- explicit missing slots

Functional purpose:
- Convert vague unknown claims into concrete fill targets for LLM iteration.

### Phase 3: Isomorphism-Lifting Loop
Input:
- claim packet + ABCD state

Behavior:
- Build multi-perspective isomorphism stack (hologram).
- Repeatedly lift relation viewpoints.
- Treat perspectives as vector-like constraints.
- Collapse toward stable typed label/feature point.

Output:
- candidate derivation subgraph
- current typed feature hypotheses

### Phase 4: EMR Progression
Evaluate progression:
- embodies -> manifests -> reifies -> programs

Output:
- EMR state
- progression missingness

Rule:
- `programs` is a semantic strengthening state.

### Phase 5: Validation Stack
Run validation in one pass bundle:
- SHACL structural constraints
- OWL reasoner entailment/consistency
- derivation/hyperedge constraints

Output:
- unified diagnostics bundle
- preserve existing error text style (reasoner/SHACL feedback remains human-facing)

### Phase 6: SES Typed-Depth Computation
Compute SES typed-depth from constructor/subgraph:
- arg_count_total
- arg_count_typed
- max_recursive_typed_depth
- first_arbitrary_string_depth

Output:
- SES report

### Phase 7: Compression Evaluation
Compute:
- MSC presence
- required-relationship `justifies` coverage

Result:
- `compression = strong | weak`

### Phase 8: Promotion Gate
Promote SOUP -> ONT iff all true:
- EMR reached required threshold (`programs` in this spec)
- compression is strong
- CatOfCat chain declared bounded
- no blocking violations in diagnostics bundle

Else:
- remain SOUP with explicit missingness

### Phase 9: Persistence
If SOUP:
- persist partial subgraph snapshot
- persist missingness
- persist EMR state
- persist SES report
- persist unresolved `justifies` coverage

If ONT:
- persist promoted assertions
- persist MSC proof
- persist full `justifies` coverage proof
- persist bounded chain evidence
- persist SES-at-promotion

### Phase 10: Optional Codegen/Simulation Witness
Run only post-admission.

Purpose:
- Operational witness of admitted ontology structure.

Rule:
- Witness does not decide validity.
- Validity is already decided by Phase 8 gate.

## 5. `llm_suggest` Contract
Constraint from user intent:
- Keep current outward error-return style.

Operational behavior:
- `llm_suggest` acts as deterministic missingness emitter in an LLM-mediated loop.
- It may return formatted error guidance text exactly as current interface expects.
- No mandatory internal model call is required for this function in the compiler core.

## 6. Compiler Data Contracts (Internal)
Note: "IR" naming is optional; these are compile packet structures.

`CompilePacket`
- source_statement: str
- parsed_claim: dict
- normalized_relations: dict
- abcd_state: dict
- candidate_subgraph: dict
- emr_state: str
- ses_report: dict
- compression_report: dict
- diagnostics: dict
- decision: dict

`CompressionReport`
- has_msc: bool
- required_rel_count: int
- justified_rel_count: int
- all_required_justified: bool
- mode: "strong" | "weak"

`SESReport`
- constructor_name: str
- arg_count_total: int
- arg_count_typed: int
- max_typed_depth: int
- first_arbitrary_string_depth: int | null

`Decision`
- is_programs: bool
- is_strong_compression: bool
- is_catofcat_bounded: bool
- has_blocking_violations: bool
- admit_to_ont: bool
- stay_in_soup: bool

## 7. Invariants
1. Determinism:
- Same ontology state + same input = same decision.

2. No silent ONT admission:
- ONT admission without strong compression is forbidden.

3. Boundedness requirement:
- ONT admission without declared bounded CatOfCat chain is forbidden.

4. Programs semantics:
- `programs` cannot be set solely by template emission.

5. SES semantics:
- SES is computed from constructor arg typing depth, not prose heuristics.

6. Error surface stability:
- Existing human-facing error style is preserved.

## 8. Expected Code Changes (File-Level)
This section is the implementation map.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/compiler.py`
- Refactor `youknow()` into explicit phases (0..10 above).
- Add compile packet assembly and decision object.
- Replace ad hoc placeholder chain completion logic with compression + boundedness gate.
- Keep outward error return style intact.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/derivation.py`
- Ensure EMR progression status is exposed for gate usage.
- Align `programs` readiness with strengthening semantics.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/universal_pattern.py`
- Add explicit SES typed-depth calculator functions based on constructor args and recursive typedness.
- Keep storage and enum behavior compatible.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/hyperedge.py`
- Add/confirm relationship-level `justifies` coverage reporting for required derivation relationships.
- Expose data needed by compression report.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/cat_of_cat.py`
- Add declared boundedness API/check to support gate (`is_declared_bounded(name)` or equivalent).
- Fix root handling edge case in chain closure logic where needed.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/uarl_validator.py`
- Keep detailed SHACL/reasoner errors surfaced.
- Ensure diagnostics can be aggregated without changing outward style.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/owl_reasoner.py`
- Ensure reasoner checks provide bounded/closure-relevant facts for gate and diagnostics.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/y_mesh.py`
- Keep as controller/telemetry layer.
- Wire threshold events to compile packet state transitions (not as source-of-truth validity).

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/youknow_kernel/utils.py`
- Preserve `llm_suggest` outward behavior.
- Optionally add deterministic queue payload helper that does not alter returned message style.

### `/Users/isaacwr/Documents/New project/youknow_kernel_current/tests/`
- Add gate-focused tests:
1. Strong compression + bounded chain => ONT admission.
2. Missing `justifies` => stays SOUP.
3. No MSC => stays SOUP.
4. `programs` false => stays SOUP.
5. Unbounded CatOfCat => stays SOUP.
6. SES typed-depth computed from constructor arg drill-down.
7. Existing outward error text style remains stable.

## 9. Minimal Acceptance Criteria
1. For unresolved unknown claim:
- returns explicit missingness in current style,
- persists SOUP payload.

2. For fully strengthened claim:
- reaches `programs`,
- strong compression true,
- bounded chain true,
- admitted to ONT,
- returns `OK`.

3. For same repeated input + unchanged state:
- identical decision and output.

## 10. Milestone Plan
### Milestone A: Gate Correctness
- Implement compression + boundedness gate in compiler.
- Add tests for admission criteria.

### Milestone B: SES Correctness
- Implement constructor arg depth-based SES metric.
- Add SES tests.

### Milestone C: EMR + ABCD Wiring
- Ensure ABCD scaffold and EMR progression feed gate deterministically.

### Milestone D: YMesh/llm_suggest Operational Wiring
- Wire controller behavior without changing outward error style.

### Milestone E: Witness Layer
- Add optional post-admission codegen/simulation witness integration.

## 11. Deferred (Explicitly Not Required for This Spec Completion)
- Full self-hosting "do it twice" bootstrap proof.
- Broad ontology naming migration.
- API redesign of outward error strings.

## 12. Traceability to Verbatim Intent
This spec is grounded by exact user statements in:
- `YOUKNOW_USER_EXPLANATIONS_VERBATIM.md`

Any future edits to this spec should preserve those core meanings unless explicitly revised by user.
