# Archaeology Baseline — Code Review of Map Implementation

**Auditor:** Baseline agent (no CoR, no catastrophe framework)
**Date:** 2026-02-25
**Files reviewed:** 20+ source files, 210 tests, VISION.md, IMPLEMENTATION_PLAN.md

---

## Executive Summary

The implementation is **substantially complete and functional**. 210 tests pass. The three-layer architecture (base / meta / super) works. The CLI, persistence, flows, and help system are all implemented. However, there are meaningful gaps between the VISION spec, the IMPLEMENTATION_PLAN notes, and the actual code. Several items are marked "fixed" or "done" in the notes that are actually incomplete, and the VISION describes capabilities that don't exist.

---

## 1. Test Count Mismatch

**IMPLEMENTATION_PLAN claims:** 148 test methods
**Actual:** 210 test methods pass

The plan was never updated after the second dev round added CLI, persistence, flows, and help tests. The "148" number is stale. This isn't a bug, but it means the plan document is unreliable as a record of current state.

---

## 2. VISION vs Implementation — Missing Features

VISION.md section "What's missing" lists 7 items. The team addressed 1-4 but left 5-7 untouched:

### 2a. CLI Shell Interface — DONE (with naming discrepancy)

**VISION says:** `python3 -m map run/eval/list/inspect/compose`
**Actual:** `python3 -m introduction_to_cs run/eval/list/inspect/compose`

The module name is `introduction_to_cs`, not `map`. The VISION spec uses `map` throughout. No alias, symlink, or `map` package exists. An AI following the VISION's examples would get `ModuleNotFoundError`.

### 2b. Persistent Environment — DONE

Works correctly. Serializes to `.map-state/env.json`. The Morph environment patching on deserialize is sound.

### 2c. Progressive Disclosure Help — DONE

All 4 levels implemented. Level 0 (breadcrumb), Level 1 (command index), Level 2 (per-command help), Level 3 (special form help). Matches VISION spec.

### 2d. Attention Flow Storage — DONE

Save, list, inspect, compose, modify, delete, flow-run all implemented. Flows persist as `.map` files in `.map-flows/`.

### 2e. `super/` Ops That Modify META-EVAL — NOT DONE

**VISION says:** "super/ ops that modify META-EVAL — current ops only define base-level functions"
**Actual:** Still only base-level functions. The super ops (map, compose, match, reify) define Map functions that run in the meta-interpreter's environment, but none of them modify the meta-evaluator itself. No op rewrites META-EVAL dispatch, adds new special forms to the meta-evaluator, or alters the evaluation strategy.

The self-modification primitives (`self-rewrite`, `self-inspect`, `self-fork`, `self-dispatch`) can rewrite *operation files*, but they can't rewrite `meta_circular.map` or alter how META-EVAL dispatches. This is a fundamental gap between the VISION's Futamura tower concept and the actual implementation.

### 2f. Compilation Step (1st Futamura Projection) — NOT DONE

**VISION says:** "Map program -> specialized evaluator (1st projection)"
**Actual:** No compiler exists. No specialization. Everything is interpreted.

### 2g. Self-Application (2nd Futamura Projection) — NOT DONE

**VISION says:** "compiler applied to itself (2nd projection = generator)"
**Actual:** No compiler, so no self-application.

---

## 3. IMPLEMENTATION_PLAN Notes vs Actual Code

### 3a. "Known Bugs (Open)" Section Is Stale

Items 1 and 2 in "Known Bugs (Open)" are marked with strikethrough `~~FIXED~~`:
- `self-dispatch` write mode — claimed FIXED
- Error positions — claimed FIXED

But the section header still says "Open". This is confusing — are they open or fixed? The code confirms both are actually implemented.

### 3b. Stale Line Items in "What Would Make This Actually Good"

Items 9 and 10 are still listed as TODO:
- "Add line:col to error messages" — **Actually done.** `ParseError` now takes `line` and `col` parameters. `_offset_to_line_col()` exists. 4 tests verify this.
- "Complete `self-dispatch` write mode" — **Actually done.** Full implementation exists in `hot.py` lines 143-194.

The plan was not updated after these were completed.

### 3c. "Honest Status" Section Is Dishonest (Stale)

The "Known limitations" section says:
- "Error messages lack line:col positions" — **False, they have positions now**
- "`self-dispatch` write mode is a stub" — **False, it's fully implemented**

These were fixed but the "honest status" was never updated.

---

## 4. Spec Violations and Semantic Issues

### 4a. `MATCH` Is Not a Special Form — It's Only a Super Op

VISION.md's Symbol Semantics table lists `MATCH` as an attention primitive:

> | `MATCH` | Pattern dispatch | "Route attention based on structure" |

The help system (help.py line 285-295) documents `match` as if it's a built-in special form. But `MATCH` is NOT in the base evaluator at all. It's only available as a super-layer operation (`super/ops/match.map`). Calling `{match ...}` in base eval raises `NameError: Unbound symbol: MATCH`.

This means:
1. The help system documents something that doesn't exist at the base level
2. An AI reading the help and trying `{match ...}` via `eval` will get an error
3. MATCH only works through `super` command or after loading the registry

### 4b. `Atom.is_sym` Returns True for Keywords and Strings

```python
Atom(':foo').is_sym  # True (also is_keyword)
Atom('"hello').is_sym  # True (also is_str)
```

The property `is_sym` means "val is a string" not "val is a symbol". Keywords and string literals pass `is_sym` checks. Code that does `if atom.is_sym` without also checking `not atom.is_keyword and not atom.is_str` will accidentally match keywords and strings. The type predicate naming is misleading.

### 4c. Persistence Uses Relative Paths (CWD-dependent)

```python
STATE_DIR = '.map-state'   # persistence.py
FLOWS_DIR = '.map-flows'   # flows.py
```

Both are relative to CWD, not to the project directory. If an AI invokes Map from different working directories, it will get different (or no) persistent state. The VISION describes persistent environment as a key feature, but persistence only works if you always run from the same directory.

### 4d. `compose` Is Concatenation, Not Functional Composition

The `compose` CLI command (line 237 of `__main__.py`) concatenates flow sources:

```python
composed = '\n'.join(sources)
```

This is string concatenation of Map programs, not functional composition. If flow A defines `{bind x 1}` and flow B defines `{bind x 2}`, "composing" them just runs both in sequence — the second `bind` shadows the first. There's no pipeline semantics, no output-of-A-becomes-input-of-B. The VISION says "combine flows into a pipeline" but the implementation is just sequential evaluation.

---

## 5. Architecture Issues

### 5a. MetaInterpreter Monkey-Patches Global State

`MetaInterpreter._patch()` replaces `base_eval.map_eval` with a hooked version. This is a global mutation — creating multiple MetaInterpreter instances causes hooks to stack (each new instance wraps the previous hooked version). There's no isolation between instances. Tests that create MetaInterpreter instances in sequence will accumulate trace depth and hooks.

```python
m1 = MetaInterpreter()  # patches global eval
m2 = MetaInterpreter()  # wraps m1's patched eval
# m2._original_eval is NOT the real original — it's m1's hooked version
```

### 5b. Persistence `Atom.__new__` Bypass Is Fragile

Deserialization creates Atoms via `Atom.__new__(Atom)` + direct `a.val = data['val']` to bypass `__init__`'s uppercasing. This works because saved values were already uppercased at creation time. But it bypasses all validation — if a serialized file is hand-edited with lowercase symbols, they'll load as lowercase and silently fail lookups.

### 5c. No `__init__.py` Exports

`/agent/introduction_to_cs/__init__.py` exists but was not examined for what it exports. The `__main__.py` imports from submodules directly, which works, but there's no public API surface.

---

## 6. Test Coverage Gaps

### 6a. No Tests for `meta` CLI Command

`cmd_meta()` is implemented but no test calls it through the CLI interface. The `TestCLI` class tests `eval`, `run`, `help`, `list`, `save`, `modify`, `clear`, `flow-run`, but not `meta` or `super`.

### 6b. No Tests for `super` CLI Command

`cmd_super()` is implemented but not tested through CLI. The super layer IS tested through Python API in `TestSuper`, but the CLI entry point is uncovered.

### 6c. No Tests for `compose` CLI Command

The `compose` CLI command is not tested. The flows module's internal functions are tested, but not the CLI `compose` path which has its own logic for looking up flow sources and concatenating them.

### 6d. No Tests for `delete` CLI Command

CLI `delete` command is untested. The underlying `delete_flow()` is tested in `TestFlows`.

### 6e. No Tests for `inspect` CLI Command

CLI `inspect` command is untested through CLI, though `inspect_flow()` is tested directly.

### 6f. Interactive REPLs Not Tested (Acknowledged)

Both the base REPL (`base/eval.py:repl()`) and super REPL (`super/main.py:repl()`) are untested. This is acknowledged in the plan.

---

## 7. Minor Issues

### 7a. `self-fork` Name Replacement Is Naive

```python
source = source.replace(old, new)
```

This replaces ALL occurrences of the old name in the source, not just the function definition. If the name appears in a string, comment, or as a substring of another identifier, it will be incorrectly replaced.

### 7b. No Validation on Flow Names

`save_flow()` accepts any string as a flow name. Names with spaces, slashes, or other filesystem-unsafe characters will create problematic file paths. No sanitization.

### 7c. `_collect_symbols` in flows.py Doesn't Recurse Into Morph/Macro Bodies

The `_collect_symbols` function in `flows.py` collects symbols from `Atom` and `Cell` types, but doesn't handle `Morph` or `Macro` objects (which have `.body` and `.params` attributes). Since it operates on parsed AST (before eval), this is fine for parsed expressions, but the type check feels incomplete.

### 7d. Redundant `sys.path` Manipulation

Multiple files (`registry.py`, `meta_interp.py`, `super/main.py`) insert parent directories into `sys.path`. This is fragile and order-dependent. The `__main__.py` uses proper relative imports via the package structure.

---

## 8. Summary Table

| Feature | VISION Spec | PLAN Status | Actual Status |
|---------|-------------|-------------|---------------|
| Base Lisp interpreter | Required | Done | **Done, works** |
| Meta-circular evaluator | Required | Done | **Done, works** |
| Super layer (registry + hot) | Required | Done | **Done, works** |
| CLI shell interface | Missing item #1 | Done | **Done, wrong module name** |
| Persistent environment | Missing item #2 | Done | **Done, CWD-dependent** |
| Progressive disclosure help | Missing item #3 | Done | **Done, works** |
| Attention flow storage | Missing item #4 | Done | **Done, works** |
| Super ops modify meta-eval | Missing item #5 | Not mentioned | **Not done** |
| 1st Futamura projection | Missing item #6 | Not mentioned | **Not done** |
| 2nd Futamura projection | Missing item #7 | Not mentioned | **Not done** |
| MATCH special form | In symbol table | Not in plan | **Only super op, not base** |
| Test count | N/A | 148 claimed | **210 actual** |
| Error positions | In plan | FIXED | **Done, plan says "open"** |
| self-dispatch write | In plan | FIXED | **Done, plan says "open"** |

---

## 9. Verdict

The dev team delivered solid work on the concrete implementation tasks (CLI, persistence, flows, help, tests). The base language, meta-circular evaluator, and super layer all function correctly. The code quality is reasonable — clean separation of concerns, good test coverage for what's tested.

The gaps are:
1. **VISION drift** — The higher Futamura levels (items 5-7) were never attempted, and the plan doesn't mention them. The team built what was in front of them without checking whether the larger vision was being served.
2. **Stale documentation** — The IMPLEMENTATION_PLAN has multiple entries that contradict actual state. "Honest Status" is no longer honest.
3. **MATCH misrepresentation** — Documented as a base feature, only exists at super level.
4. **Module naming** — VISION says `map`, code says `introduction_to_cs`.

None of these are catastrophic. They're the normal entropy of a multi-round dev process where notes don't get updated and vision docs outpace implementation.
