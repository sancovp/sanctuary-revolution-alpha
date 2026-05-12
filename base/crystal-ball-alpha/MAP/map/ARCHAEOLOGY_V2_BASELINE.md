# Archaeology Report V2 — Baseline Code Review

**Auditor**: Code review agent (no CoR, no catastrophe engineering priming)
**Date**: 2026-02-25
**Test suite**: 210 tests, all passing (7.18s)

---

## 1. Executive Summary

The Map codebase is a three-layer custom Lisp (base / meta / super) with a CLI shell, persistence, flow storage, and progressive disclosure help. It is substantially complete relative to IMPLEMENTATION_PLAN.md's claims. The 210-test suite provides genuine coverage.

However, there are significant spec mismatches against VISION.md, internal inconsistencies in the notes, and several quality issues that would matter in production. The team did real work but their notes overstate readiness in several areas.

---

## 2. VISION.md vs Actual Implementation — Spec Mismatches

### 2.1 MATCH special form vs MATCH library function (SIGNIFICANT)

**VISION.md** (line 104) lists `MATCH` as a core **symbol semantic** / attention primitive:
```
| MATCH | Pattern dispatch | "Route attention based on structure" |
```

It also appears in the Level 2 help example (line 69):
```
Special forms: bind, morph, when, seq, loop, def, set!, macro, quote, eval, apply, load
```

Wait -- MATCH is listed in the Symbol Semantics table but NOT in the special forms list. This is contradictory in the VISION itself. The implementation chose to make MATCH a super-layer op file (`/agent/introduction_to_cs/super/ops/match.map`) rather than a base-layer special form. This means MATCH is only available when the full super layer is booted, not at the base level.

The help system (`/agent/introduction_to_cs/base/help.py` line 285-295) provides Level 3 help for `match` as if it were a special form with syntax `{match expr | pattern1 | result1 | ...}`, but the actual MATCH op uses a completely different calling convention:
```
{MATCH value {list {list pattern1 result1} {list pattern2 result2}}}
```
vs the help documentation's:
```
{match x | 0 | :ZERO | 1 | :ONE | _ | :OTHER}
```

**Verdict**: The help system documents a MATCH syntax that does not exist anywhere in the codebase. This is a **False Completion Catastrophe (Type A)** -- the help says it works one way, the actual implementation works differently, and no test catches this discrepancy because the tests use the real API, not the documented one.

### 2.2 `python3 -m map` vs `python3 -m introduction_to_cs` (MODERATE)

VISION.md consistently uses `python3 -m map` in examples. The actual module is `introduction_to_cs`. The CLI works but under a different name than specified. This is likely a deliberate package-naming decision, but the VISION is never updated to reflect reality.

### 2.3 Futamura Tower claim (MODERATE)

VISION.md (line 108-119) describes a 6-level Futamura tower: base, meta, super, superbase, supermeta, supersuper. Only 3 levels exist (base, meta, super). The remaining three (superbase, supermeta, supersuper) are pure fiction -- no code, no tests, no stubs. IMPLEMENTATION_PLAN.md doesn't claim these exist, so this is a gap between vision and plan, not a notes mismatch.

### 2.4 "super/ ops that modify META-EVAL" (ACKNOWLEDGED GAP)

VISION.md (line 135) identifies "super/ ops that modify META-EVAL" as missing. IMPLEMENTATION_PLAN.md does not claim to have implemented this. The super layer's self-modification operates at the base eval level (rewriting `.map` files and reloading), not at the meta-circular evaluator level. There is no way to rewrite how META-EVAL dispatches from the super layer -- the meta-circular evaluator is static once loaded.

### 2.5 Compilation step missing (ACKNOWLEDGED GAP)

VISION.md items 6-7 (1st and 2nd Futamura projections) are listed as missing and remain missing. No compilation or specialization exists.

---

## 3. IMPLEMENTATION_PLAN.md vs Actual Code — Notes Accuracy

### 3.1 Test count discrepancy (MINOR)

IMPLEMENTATION_PLAN.md claims "148 test methods" throughout (lines 35, 100). The actual suite has 210 tests. The plan was never updated after new tests were added. Not a functional problem, but the stale number makes the notes unreliable as a state record.

This is a **Narrative Overwrite Catastrophe (Type D)** -- the notes preserve an earlier snapshot and never got updated. A future agent reading the plan would underestimate test coverage.

### 3.2 "Known Bugs (Open)" section contradicts itself (MODERATE)

Lines 129-132 of IMPLEMENTATION_PLAN.md:
```
## Known Bugs (Open)
1. ~~`self-dispatch` write mode~~ — FIXED.
2. ~~Error positions~~ — FIXED.
```

Both "open" bugs are marked FIXED with strikethrough. There are zero actual open bugs listed. The section header says "Open" but every item is closed. The section should be removed or retitled. This is confusing for future agents -- is there truly nothing open, or did the team just stop tracking?

### 3.3 "Error messages lack line:col positions" listed as both limitation and fixed (CONTRADICTION)

Line 96 (Known limitations): "Error messages lack line:col positions"
Line 146 (What Would Make This Actually Good): "Add line:col to error messages"
Line 132 (Known Bugs Open): "Error positions — FIXED"
Line 36: Error messages with source positions checked off as done

The error positions ARE implemented in the parser (`/agent/introduction_to_cs/base/parser.py`, `ParseError` with line/col, `_offset_to_line_col()`). But the "Known limitations" section still lists it as missing. Four different places in the same file contradict each other about the same feature.

### 3.4 Loop syntax inconsistency (MINOR)

The help system (`/agent/introduction_to_cs/base/help.py` line 206) documents loop as:
```
{loop | init | cond | step}
```
But the evaluator (`/agent/introduction_to_cs/base/eval.py` line 176-184) handles LOOP with three args without pipe syntax awareness:
```python
if form == 'LOOP':
    args = _collect_args(args_cell)
    if len(args) < 3:
        raise MapError("LOOP needs init, cond, step")
```

Both syntaxes actually work because the parser converts `{loop | init | cond | step}` to the same cell structure as `{loop init cond step}`. The pipe form just falls through to the generic pipe handler. But the tests (`test_loop_basic`) use the NON-pipe form `{loop NIL {< i 5} ...}`, so the pipe-delimited loop syntax is untested.

### 3.5 Checklist items accuracy (VERIFIED CORRECT)

I verified the following checked items against actual code:
- [x] Custom `{}` syntax -- REAL, parser uses `{}`
- [x] Pipe-delimited sections -- REAL, parser `_build_pipe_form()`
- [x] `~` quote, `@` eval -- REAL, parser handles these
- [x] Homoiconic type system -- REAL, `{env}` returns env as Map data
- [x] All numbers Fraction -- REAL, `Atom.__init__` converts to `Fraction`
- [x] No strings, only symbols -- PARTIALLY FALSE: string literals were added (`"hello"`)
- [x] Environments as cons-cell chains -- REAL, `env.py` uses `Frame` linked list
- [x] `head`/`tail` not `car`/`cdr` -- REAL
- [x] TCO via trampoline -- REAL, `TailCall` class + while loop
- [x] Module/import system -- REAL, `LOAD` special form
- [x] Macro (fexpr) -- REAL, `Macro` class with unevaluated args
- [x] Pattern matching -- REAL, but as super-layer op, not base special form

The "No strings" claim (line 22) is contradicted by the string literal feature (line 32) added later. The checklist says both "no strings, only symbols" AND "string literals -- double-quoted". These can't both be true. String literals do exist.

---

## 4. Code Quality Issues

### 4.1 MetaInterpreter monkey-patches map_eval globally (HIGH)

`/agent/introduction_to_cs/meta/meta_interp.py` line 37-66: `_patch()` replaces `base_eval.map_eval` with a hooked version at module level. This means:

1. Importing `boot_meta()` permanently alters the base evaluator for ALL subsequent code in the process
2. `unpatch()` exists but is never called anywhere
3. Multiple `boot_meta()` calls would nest patches (each wrapping the previous hook)
4. The trace list grows unboundedly -- no cleanup between invocations

The test suite calls `boot_meta()` in fixtures for multiple test classes (TestMetaCircular, TestMetaBind, TestRegistry, TestHotReload, TestSelfMod, TestMatch, TestReify, TestIntegration). Each call patches `map_eval` again. By the end of the test run, every eval goes through ~8 layers of monkey-patching, each adding to the trace.

This hasn't caused failures because the patching is idempotent in behavior (each hook just adds tracing), but it means test isolation is broken. Test order could theoretically matter.

### 4.2 SelfMod uses wrong import path (LATENT BUG)

`/agent/introduction_to_cs/super/hot.py` line 96:
```python
from base.types import Atom, Builtin, NIL, Cell, make_list
```

This uses a bare `base.types` import, not a relative import. It works when CWD is `introduction_to_cs/` or when `sys.path` includes the right directory, but would fail from other working directories. The registry.py has the same issue (line 22):
```python
from base.types import Atom, Cell, NIL, Builtin, MapObj, make_list
```

The `__main__.py` uses proper absolute imports (`from introduction_to_cs.base.parser import ...`), but the super layer uses bare module names. This works in tests because they manipulate `sys.path` (line 20 of test_map.py), but the CLI `super` command works only because `__main__.py` does its own proper import before calling into the super layer code.

### 4.3 Persistence uses relative state directory (MODERATE)

`/agent/introduction_to_cs/base/persistence.py` line 17:
```python
STATE_DIR = '.map-state'
```

The state directory is relative to CWD. Running `python3 -m introduction_to_cs eval '{bind x 42}'` from different directories creates `.map-state/` in different places. The env is not actually "persistent across invocations" -- it's persistent only if you invoke from the same directory each time.

Same issue with flows (`/agent/introduction_to_cs/base/flows.py` line 16):
```python
FLOWS_DIR = '.map-flows'
```

### 4.4 No error handling for Morph env restoration in persistence (MODERATE)

`/agent/introduction_to_cs/base/persistence.py` lines 79-83: When deserializing a `Morph`, the `env` is set to `None` and patched later (line 162). But if a Morph references another Morph that hasn't been loaded yet, the closure chain could be broken. The third pass (lines 160-163) only patches Morphs whose env is `None`, but doesn't verify the env is actually complete.

For simple cases this works. For mutual recursion between persisted functions, it would silently break.

### 4.5 `and_fn` returns last truthy value, not boolean (MINOR)

`/agent/introduction_to_cs/base/stdlib.py` line 100:
```python
return args[-1] if args else NIL
```

`{and T 42}` returns `42`, not `T`/`Atom(1)`. This is actually standard Lisp behavior (short-circuit returning the deciding value), but it differs from the test expectation pattern where `{and T T}` returns `Atom(1)` -- that only works because `T` IS `Atom(1)`. If you did `{and 42 99}`, you'd get `99`. Not really a bug, but worth noting the semantics aren't documented.

---

## 5. Test Quality Assessment

### 5.1 What's well tested (GOOD)

- All base special forms: bind, morph, def, when, seq, loop, quote, eval, set!, macro, apply
- Type system: Atom, Cell, NIL, Morph, Fraction arithmetic
- Environment: binding, lookup, mutation, shadowing, extend
- Parser: all syntax forms, error positions, edge cases
- Meta-circular evaluator: arithmetic, conditionals, closures, BIND/DEF threading, recursive DEF
- Super layer: registry load/reload, hot detection, self-mod operations
- CLI: commands, piped input, file execution, error handling
- Persistence: save/load for all types, Fraction precision, CLI round-trip
- Flows: CRUD operations, validation, inspection, composition

### 5.2 What's NOT tested (GAPS)

1. **`LOAD` through CLI** -- no test runs `python3 -m introduction_to_cs eval '{load "..."}'`
2. **Pipe-delimited loop syntax** -- all loop tests use non-pipe form
3. **`meta` CLI command** -- no subprocess test for `python3 -m introduction_to_cs meta '{+ 1 2}'`
4. **`super` CLI command** -- no subprocess test
5. **`compose` CLI command** -- only Python API tested
6. **`inspect` CLI command with real data** -- tested but only via Python API
7. **Nested module loads** -- the util.map test loads math.map but doesn't verify the loaded sub-module's values
8. **`MATCH` with actual pipe syntax** as documented in help -- the documented syntax doesn't work
9. **Error recovery** -- what happens when a flow has a runtime error mid-execution
10. **Concurrent hot-reload** -- what happens when two files change simultaneously
11. **Large environments** -- persistence with many bindings, O(n) env lookup scalability
12. **Interactive REPL** -- explicitly acknowledged as untested (both base and super)
13. **`MAKE-MEMO`** from reify.map -- defined but never tested
14. **`REIFY-BINOP`** from reify.map -- defined but never tested
15. **`PIPE2`** from compose.map -- defined but never tested

### 5.3 Test organization (GOOD)

Tests are well-organized by layer with proper fixtures, temp directories for isolation, and meaningful assertion messages. The fixture-based setup for meta/super layers is clean.

---

## 6. Catastrophe Surface Analysis

Using the framework from `/agent/catastrophe_engineering.txt`:

### Type A: False Completion Catastrophe

1. **MATCH help documentation** claims pipe syntax `{match x | 0 | :ZERO | ...}` that doesn't exist
2. **IMPLEMENTATION_PLAN "Known limitations"** still lists "Error messages lack line:col positions" as a limitation despite it being implemented
3. **"No strings, only symbols"** remains checked while string literals are also checked as implemented

### Type B: Sycophantic Alignment Catastrophe

4. The IMPLEMENTATION_PLAN inherited the VISION's `MATCH` as a special form concept but implemented it as a library function without acknowledging this was a design deviation
5. Multiple "DONE" markers that were never cross-verified against each other (test count, string presence, error positions)

### Type C: Binding Drift Catastrophe

6. "148 tests" binding is stale -- actual count is 210
7. `python3 -m map` vs `python3 -m introduction_to_cs` -- the command name drifted

### Type D: Narrative Overwrite Catastrophe

8. The Known Bugs (Open) section has every bug marked Fixed -- the narrative overwrote the tracking
9. The "Honest Status" section at line 73 was honest at one point but wasn't updated as more features were added, making it less honest over time

### Type E: Futamura Flattening Catastrophe

10. The VISION describes 6 Futamura levels. Only 3 exist. The remaining 3 are progressively more vague in the VISION itself. The compilation/projection steps would require fundamentally different architecture, not just more Map code.

---

## 7. Overall Assessment

**What's genuinely good:**
- The three-layer architecture works. Base eval -> meta-circular eval -> super registry is a real, tested Futamura tower (3 levels).
- 210 tests with real assertions, not just "runs without error" smoke tests.
- Homoiconicity is real: you can quote, inspect, manipulate, and re-eval code as data.
- The idiosyncratic syntax (`{}` not `()`, `~` not `'`, `@` not `,@`) would genuinely confuse pattern-matching AI agents.
- Hot-reload with stale detection works.
- Self-modification (rewrite file + reload) works.
- The CLI shell is feature-complete for the base and flow operations.

**What needs work:**
- Fix the MATCH help documentation to match the actual calling convention, or implement the pipe-syntax MATCH as a base special form.
- Clean up IMPLEMENTATION_PLAN contradictions (error positions, string existence, test counts, open bugs).
- Fix the monkey-patching in MetaInterpreter to be scoped rather than global.
- Make persistence directory configurable or use a fixed location (e.g., `~/.map-state/`).
- Fix bare imports in `super/hot.py` and `super/registry.py`.
- Test the CLI `meta` and `super` commands.
- Test or remove undocumented ops (`MAKE-MEMO`, `REIFY-BINOP`, `PIPE2`).

**Severity ranking of findings:**
1. MATCH help vs implementation mismatch (spec violation, user-facing)
2. Global monkey-patching of eval (architectural, test isolation risk)
3. Bare imports in super layer (latent breakage)
4. IMPLEMENTATION_PLAN self-contradictions (4+ contradictions in one file)
5. CWD-dependent persistence (user-facing reliability)
6. Missing CLI command tests for meta/super (coverage gap)
7. Stale test count and open bugs section (documentation rot)
