# YOUKNOW Compiler / Meta-Compiler Audit (read-only investigation)

Date: 2026-02-16
Source inspected: `mind_of_god:/tmp/youknow_kernel_current` copied to local workspace as `youknow_kernel_current/`
Scope: compiler correctness and meta-compiler stack viability

## Executive Assessment

Current state is **architecturally inconsistent** and **functionally regressed** for compiler behavior.

- The active `youknow_kernel/compiler.py` is mostly a response formatter around regex parsing + ontology lookups, not a robust compiler pipeline.
- The codebase contains components named as if they are compiler phases (parser/derivation/hyperedge/Y-mesh/codegen), but they are not wired into a coherent staged compiler with stable IR boundaries.
- Test expectations (`SOUP:` behavior + hallucination persistence) match an older backup implementation, not the current active compiler.
- For known-root chains, there is a concrete chain-construction bug that can incorrectly mark complete foundational chains as broken.

Severity for compiler goal: **high**.

---

## Concrete Findings (with file evidence)

### 1) Current compiler regressed against intended SOUP contract

Evidence:
- `tests/test_soup_wiring.py` expects:
  - unknown targets return `SOUP:`
  - hallucination metadata files are written to `$HEAVEN_DATA_DIR/soup/*_hallucination.json`
- Active compiler (`youknow_kernel/compiler.py`) no longer includes `_persist_to_soup` or `_build_soup_response`; only returns `You said ... Wrong because ...` and `_persist()` is a TODO `pass`.

Key lines:
- `youknow_kernel/compiler.py:226` (`youknow()` entry)
- `youknow_kernel/compiler.py:445` (`_persist` TODO + `pass`)
- `youknow_kernel/compiler.py.backup_all_changes_feb6:636` (`_persist_to_soup` exists)
- `youknow_kernel/compiler.py.backup_all_changes_feb6:734` (`_build_soup_response` exists)

Runtime verification (`python3 -m pytest -q`):
- 5 tests failing, 3 passing.
- Fails exactly on missing `SOUP:` behavior and missing soup file persistence.

### 2) Root-chain bug: known complete chain can be marked incomplete

For input like `Entity is_a Cat_of_Cat`, chain should close at root.

Bug mechanics:
- `_get_chain("Cat_of_Cat")` returns `[("Cat_of_Cat", "?")]` because the method converts a single-node trace into unknown placeholder.
- This causes false breakage even for foundational root.

Key lines:
- `youknow_kernel/compiler.py:376` (`_get_chain`)
- `youknow_kernel/compiler.py:405` (`return pairs if pairs else [(entity, "?")]`)

Observed output confirms false break:
- `Cat_of_Cat is_a ? (unknown)`

### 3) “Compiler” is mostly parser + validator adapters, no real compile phases

Current architecture lacks canonical compiler boundaries:
- No explicit lexical phase (only regex / token splitting)
- No typed semantic IR distinct from syntax and ontology entity records
- No lowering pipeline (AST -> normalized semantic graph -> executable/artifact IR)
- No backend abstraction (only direct string template emission)

Evidence:
- `youknow_kernel/compiler.py:174` regex triple parser
- `youknow_kernel/lang.py` parser is token-stream for tiny DSL, not integrated as front-end for `youknow()`
- `youknow_kernel/codeness_gen.py` emits templates directly, no intermediate code IR or verifier pass

### 4) Meta-compiler claims exceed implementation

Files claim a metacircular stack (observe -> ontology -> codegen -> runtime), but critical pieces are missing/partial:
- `codeness.py` itself flags parts as broken/TODO.
- `derivation.py` has placeholder checks (`pass`) in reification requirements.
- multiple modules include TODO/placeholder behavior in core paths.

Evidence:
- `youknow_kernel/codeness.py:346` (“BROKEN - Uses old API”)
- `youknow_kernel/derivation.py:121` placeholder `pass`
- `youknow_kernel/compiler.py` has TODOs in key pipeline points and no persistence implementation.

### 5) Test/runtime mismatch indicates branch drift or partial revert

`compiler.py.backup_all_changes_feb6` includes SOUP logic, reasoner hook, richer spiral metadata, and persistence.
Current `compiler.py` appears to be a simplified/rolled-back variant with removed features but unchanged tests.

Likely outcome:
- agents merged/replaced compiler file without reconciling tests and invariants.

---

## Why this is not yet a proper compiler stack

A real compiler/meta-compiler stack needs stable phase contracts:

1) Front-end grammar + parser
- Deterministic grammar
- AST with source spans and error recovery

2) Semantic analysis
- Symbol table
- Type/kind checks (ontology types, relationship arity/constraints)
- Normalization to semantic IR

3) Middle-end
- Canonical IR for transformations and proofs
- Pass manager (validation, closure checks, derivation progression)

4) Backend(s)
- OWL backend
- runtime/code backend (Python artifacts)
- persistence backend (SOUP/Carton)

5) Bootstrap/meta layer
- self-hosted transformations should operate on IR, not ad hoc dicts and regex strings
- round-trip tests should enforce: parse -> IR -> emit -> reparse consistency

Current code jumps between dicts/strings/templates and ontology objects without hard IR boundaries, so it cannot be reasoned about like a real compiler.

---

## Suggested recovery direction (architecture only)

1) Define one canonical semantic IR
- `ConceptDecl`, `RelationEdge`, `Evidence`, `DerivationState`, `Diagnostic`
- All phases consume/produce this IR.

2) Split `youknow()` into explicit passes
- parse -> normalize -> validate(hyperedge/derivation/uarl) -> classify(OK/SOUP) -> persist -> render response

3) Reinstate SOUP contract intentionally
- If chain incomplete: emit deterministic `SOUP:` envelope + persist hallucination metadata
- Keep human-readable response as secondary rendering from the same diagnostics.

4) Fix root-chain invariant first
- `Cat_of_Cat` closure must be terminal success, never `?`.

5) Align tests to one contract
- Either keep `SOUP:` protocol and enforce it, or change tests and all consuming integrations.
- Right now tests and compiler disagree on API contract.

6) Separate meta-compiler from template engine
- Template generation can remain a backend, but not be called “compiler core.”
- The compiler core should be IR-driven and backend-agnostic.

---

## Quick truth table of current behavior

- Unknown target statement: returns verbose `Wrong` text (not `SOUP:`)
- Known root chain (`Entity is_a Cat_of_Cat`): incorrectly breaks at root due chain bug
- SOUP file persistence: not implemented in active compiler
- OWL/Carton persistence in active compiler path: TODO/stub

---

## Bottom Line

The agents did not fully destroy everything, but the current active compiler path is **not a coherent compiler stack** and appears **regressed from an intended SOUP-aware contract**. The highest-impact immediate issues are:

1) API contract mismatch (tests/integrations expect `SOUP:`)
2) root-chain closure bug
3) missing persistence and phase boundaries

