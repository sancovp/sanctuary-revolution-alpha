# Catastrophe Archaeology Report: Map Codebase

**Date:** 2025-02-25
**Method:** Chain-of-Reasoning catastrophe archaeology with mandatory CoR at each analysis step
**Artifacts examined:** VISION.md, IMPLEMENTATION_PLAN.md, all source files, test suite (210 tests), task list

---

## 1. Overall Framing: Spec vs Plan vs Code vs Tests

The past LOOKS LIKE a successful two-round dev team effort because IMPLEMENTATION_PLAN.md shows all checkboxes ticked, 210 tests pass, and the "Known Bugs (Open)" section has all items struck through as fixed. IMPLEMENTATION_PLAN.md has extensive completion markers (`[x]`), but if any of these are DONE SIGNALS instead of STATE SIGNALS, I need to perform a ROLLUP. The plan claims "148 test methods, all passing" while the actual suite has 210 -- this is a DONE SIGNAL frozen from an earlier state, not a live STATE SIGNAL. Since the analysis shows the plan document was written at one point in time and then partially updated by subsequent dev rounds, I should investigate each claim chain until I understand how it got into my perception now (ie ROLLUP process), or proceed with making the next layer. However, if I am not absolutely sure from the morphological state about how these priors (plan claims, test counts, "known bugs" statuses) got HERE NOW, I need to ROLLUP. Since plan claims <-> actual code state shows both agreement AND drift, I will ROLLUP the specific discrepancies before proceeding.

### Verdict: The implementation is REMARKABLY GOOD overall.

This is not a catastrophe-rich site. The dev team did genuinely competent work across two rounds. The catastrophes I found are subtle -- mostly Type A (False Completion) and Type D (Narrative Overwrite) in the documentation layer, not in the code.

---

## 2. The Test Count Discrepancy (Type D: Narrative Overwrite)

The past LOOKS LIKE the test suite was written once with 148 tests because IMPLEMENTATION_PLAN.md says "148 test methods" in multiple places (line 35: "Regression tests -- tests/test_map.py with 148 test methods", line 100: "tests/test_map.py -- pytest suite with 148 test methods"). IMPLEMENTATION_PLAN.md has "148 test methods" frozen in text, but the actual count is 210. If this is a DONE SIGNAL (the count at the time the plan was last edited) instead of a STATE SIGNAL (the current count), I need to trace the delta. Since the task list shows TWO rounds of work (tasks 1-5 = round 1, tasks 6-14 = round 2), and round 2 added CLI, persistence, flows, and help system tests, the 62-test delta (210-148) maps cleanly to those new test classes. Since the 148 figure is a snapshot from the end of round 1 and was never updated by round 2, I will mark this as Type D (Narrative Overwrite) -- the round 2 team ADDED tests but never updated the plan's claim about test count.

**Specific locations:**
- Line 35 of IMPLEMENTATION_PLAN.md: "148 test methods across all layers, all passing" -- actually 210
- Line 100: "148 test methods, all passing" -- same stale count
- Line 127 of VISION.md: "148 passing tests" -- same stale count

**Severity: Low.** The actual count is HIGHER than claimed, so this is benign narrative drift. But it's still a Type D -- a later summary erased causal detail (which tests were added when).

---

## 3. VISION.md "What's Missing" vs Actual State (Type A: False Completion via omission)

The past LOOKS LIKE the vision was written before the dev team started because it lists 7 "missing" items. But VISION.md was actually UPDATED mid-flight (the "Current State" section mentions "148 passing tests" and specific features). VISION.md's "What's missing" section has 7 items, but if some are now implemented, this list is a DONE SIGNAL from when the vision was last edited, not the actual gap. Since the dev team actually implemented several of these "missing" items, I should check each one.

| # | Missing Item (per VISION.md) | Actual Status | Catastrophe? |
|---|---|---|---|
| 1 | CLI shell interface `python3 -m map run/eval/list/inspect/compose` | **IMPLEMENTED** in `__main__.py`. Commands: run, eval, save, list, inspect, compose, modify, delete, flow-run, meta, super, clear, help. Actually exceeds spec. | No -- but VISION.md was never updated to reflect this. Type D. |
| 2 | Persistent environment (serialize/deserialize) | **IMPLEMENTED** in `base/persistence.py`. JSON serialization of Atom, Cell, Morph. `load_env`/`save_env`/`clear_env`. CLI integrates it. | No -- VISION.md still lists as missing. Type D. |
| 3 | Progressive disclosure help system | **IMPLEMENTED** in `base/help.py`. 4 levels: breadcrumb, command index, per-command help, special form docs. | No -- VISION.md still lists as missing. Type D. |
| 4 | Attention flow storage | **IMPLEMENTED** in `base/flows.py`. Named flows stored as .map files with JSON metadata. Save, list, inspect, run, delete, compose. | No -- VISION.md still lists as missing. Type D. |
| 5 | super/ ops that modify META-EVAL | **NOT IMPLEMENTED.** The super layer only defines base-level functions (MAP, FILTER, etc). No operation in `super/ops/` modifies the meta-circular evaluator. The registry can hot-reload operations and self-modify, but nothing actually rewrites META-EVAL. | **This is genuine.** The claim is correctly still listed as missing. |
| 6 | Compilation step (1st Futamura projection) | **NOT IMPLEMENTED.** No compiler, no specializer. | Genuine gap. |
| 7 | Self-application (2nd Futamura projection) | **NOT IMPLEMENTED.** No self-application. | Genuine gap. |

**The catastrophe here:** VISION.md's "What's missing" section is stale. 4 of 7 items were implemented but the list was never updated. This means any agent or human reading VISION.md will perceive a much larger gap than actually exists. This is a Type D (Narrative Overwrite by omission) -- the implementation happened but the spec document still reads as if it didn't.

---

## 4. IMPLEMENTATION_PLAN.md "Known Bugs (Open)" Section (Type A: False Completion)

The past LOOKS LIKE all known bugs are fixed because the "Known Bugs (Open)" section at lines 129-132 shows both items struck through with "FIXED" annotations. IMPLEMENTATION_PLAN.md has `~~strikethrough~~` and "FIXED" on both open bugs, but if these are DONE SIGNALS placed by the fixing agent, I need to verify the fixes actually exist. Since I can check the code directly, I will verify both.

### Bug 1: `self-dispatch` write mode -- MARKED FIXED

**Claim:** "Write mode accepts list of {NAME SOURCE} pairs, replaces/registers ops, removes stale ones."

**Actual state:** Looking at `super/hot.py` lines 143-194, `self_dispatch` with 1 arg does indeed:
- Parse a list of `{NAME SOURCE}` pairs
- Remove ops not in the new list
- Register/update each op

**Verdict: LEGITIMATELY FIXED.** The code matches the claim.

### Bug 2: Error positions -- MARKED FIXED

**Claim:** "ParseError now includes line:col (1-based)"

**Actual state:** Looking at `base/parser.py`:
- `ParseError.__init__` accepts `line` and `col` parameters (line 12-18)
- `_offset_to_line_col` converts byte offsets (line 22-26)
- `_lc` method on Parser uses it (line 69-72)
- Used in `expect()`, `parse_expr()`, and `parse_list()` for error generation

**Verdict: LEGITIMATELY FIXED.** The code matches the claim.

However, I notice a CONTRADICTION: The "What Would Make This Actually Good" section (lines 136-148) still lists items 9 and 10 as:
- Line 146: "9. Add line:col to error messages" -- NOT marked done (but the bug fix says it IS done)
- Line 147: "10. Complete `self-dispatch` write mode" -- NOT marked done (but the bug fix says it IS done)

This is a **Type C (Binding Drift)**: the same features are tracked in two places ("Known Bugs" and "What Would Make This Good"), and one place says fixed while the other still says TODO. An agent reading only the TODO section would believe these are still open work.

---

## 5. IMPLEMENTATION_PLAN.md "Known Limitations" vs Reality (Type A: False Completion / Mixed)

The plan lists 3 "Known limitations" at lines 95-97:

1. "Interactive REPLs (base and super) not tested in automated suite" -- **STILL TRUE.** No REPL integration tests exist. The REPL in `base/eval.py` (`repl()`) and the super REPL in `super/main.py` are not tested. This is accurately reported.

2. "Error messages lack line:col positions" -- **CONTRADICTED** by the very next section ("Known Bugs (Fixed)") which says error positions were fixed. This limitation was written before the fix but never removed.

3. "`self-dispatch` write mode is a stub" -- **CONTRADICTED** by the bug fix section. Same issue.

**Type C (Binding Drift):** The "Known Limitations" section contains stale claims that contradict the "Known Bugs (Fixed)" section in the same document. Items 2 and 3 are listed as both "known limitation" and "fixed bug" simultaneously.

---

## 6. The Module/Import System: `MATCH` in VISION.md vs Reality

The past LOOKS LIKE `MATCH` is a supported special form because VISION.md lists it in the symbol semantics table (line 104: "MATCH | Pattern dispatch"). The help system includes a `match` entry in FORM_HELP (help.py line 285-295). `inspect_flow` lists MATCH in its `special_forms` set. But if MATCH is claimed as a language feature, I need to verify it exists in the evaluator.

**Actual state in eval.py:** There is NO `MATCH` special form handler in `map_eval()`. The function handles: QUOTE, EVAL, BIND, SET!, MORPH, MACRO, DEF, WHEN, SEQ, LOOP, ENV, APPLY, LOAD. No MATCH.

There IS a `match.map` file in `super/ops/` -- so pattern matching exists as a super-layer operation, not as a base-level special form.

**Type B (Sycophantic Alignment):** The help system and VISION.md present MATCH as a core language feature alongside BIND, MORPH, WHEN, etc. But it's actually only available through the super layer's operation registry. The help system inherited the aspiration (VISION.md's table) and presented it as reality.

Specifically:
- `base/help.py` line 285: FORM_HELP has a `match` entry saying "Syntax: {match expr | pattern1 | result1 | ...}"
- `base/flows.py` line 113: `inspect_flow` lists MATCH in `special_forms`
- `base/eval.py`: No MATCH handler
- `super/ops/match.map`: Pattern matching as a registered operation

If an AI calls `help match` it gets detailed syntax docs for a feature that doesn't exist at the base language level. The help system promises something the evaluator can't deliver.

---

## 7. The CLI Module Name Discrepancy (Type C: Binding Drift)

VISION.md shows the CLI as:
```
python3 -m map run
python3 -m map eval
```

The actual implementation uses:
```
python3 -m introduction_to_cs run
python3 -m introduction_to_cs eval
```

This is a minor but systematic Type C. The VISION says `map`, the code says `introduction_to_cs`. The IMPLEMENTATION_PLAN never addresses this gap -- it was simply built with the project directory name as the module name.

---

## 8. Task List State (Type A: False Completion)

The past LOOKS LIKE there were two dev rounds because the task list has tasks #1-5 (round 1) and #6-14 (round 2). Tasks #6, #7, #13, #14 have status `in_progress` with roles "worker" and "reviewer". But these are agent IDENTITY tasks, not work tasks -- they represent the worker and reviewer agent processes themselves, not specific implementation items. If I interpret them as "work still being done" I get a wrong picture; they're zombie process markers that were never cleaned up.

**Type A (False Completion by inversion):** Tasks #6, #7, #13, #14 are NOT false completions -- they're false IN-PROGRESS markers. The work IS done but the task statuses were never resolved. An agent reading the task list would believe active work is happening.

---

## 9. The Futamura Tower Claim (Type E: Futamura Flattening -- ironically)

The past LOOKS LIKE the Futamura tower is partially implemented because VISION.md describes 6 levels (base, meta, super, superbase, supermeta, supersuper) and the codebase has base/, meta/, and super/ directories. But the VISION itself notes only base/meta/super exist (items 5-7 in "What's missing" confirm no compilation or self-application).

The help system (help.py line 94) describes `super` as "3rd Futamura level" -- this is a **Type E (Futamura Flattening)** claim. The super layer provides hot-reloadable operations and self-modification builtins, but this is NOT Futamura projection. Futamura projection is about specializing an interpreter with respect to a program to produce a compiled version. The super layer is just a registry with file watching. Calling it "3rd Futamura level" flattens the meaning of Futamura projection to "any layer that modifies lower layers."

---

## 10. Summary of Catastrophes Found

| # | Type | Location | Severity | Description |
|---|------|----------|----------|-------------|
| 1 | D (Narrative Overwrite) | IMPLEMENTATION_PLAN.md | Low | Test count frozen at 148, actually 210 |
| 2 | D (Narrative Overwrite) | VISION.md "What's missing" | Medium | 4/7 items implemented but list never updated |
| 3 | C (Binding Drift) | IMPLEMENTATION_PLAN.md | Medium | "Known Limitations" contradicts "Known Bugs (Fixed)" in same doc |
| 4 | C (Binding Drift) | IMPLEMENTATION_PLAN.md | Low | "What Would Make This Good" items 9-10 still listed as TODO but fixed |
| 5 | B (Sycophantic Alignment) | base/help.py, base/flows.py | High | MATCH documented as base-level special form but only exists in super/ops |
| 6 | C (Binding Drift) | VISION.md vs __main__.py | Low | Module name `map` vs `introduction_to_cs` |
| 7 | A (False Completion) | Task list | Low | Worker/reviewer tasks stuck in `in_progress` after work completed |
| 8 | E (Futamura Flattening) | base/help.py | Medium | Super layer described as "3rd Futamura level" -- it's a registry, not a specializer |
| 9 | D (Narrative Overwrite) | VISION.md "Current State" | Low | Lists features as "what exists" but doesn't include round 2 additions (CLI, persistence, flows, help) |

---

## 11. What the CoR Method Revealed

The mandatory CoR paragraph forced me to distinguish DONE SIGNALS from STATE SIGNALS at every step. This caught:

1. **The test count discrepancy** -- without CoR I might have accepted "148 tests" from the plan and not verified against the actual 210. The frozen number is a DONE SIGNAL from round 1.

2. **The MATCH special form phantom** -- without CoR I might have accepted the help system's documentation at face value. The CoR forced me to verify: "the help system says MATCH is a special form, but is this a STATE SIGNAL (it exists) or a DONE SIGNAL (it was planned/documented)?" It was neither -- it's an aspirational claim that was baked into the help system as if already true.

3. **The contradictory bug status** -- the same document says self-dispatch is both "a stub" (Known Limitations) and "FIXED" (Known Bugs). Without CoR I'd have picked one interpretation. The CoR forced: "these are two signals about the same referent -- which is the state signal and which is the done signal?" Answer: the limitation is the stale DONE SIGNAL from when it was written; the fix is the newer STATE SIGNAL.

---

## 12. Overall Assessment

**The codebase is genuinely well-built.** The base interpreter, meta-circular evaluator, and super layer all work correctly. 210 tests pass. The code quality is high -- proper error handling, clean abstractions, good separation of concerns. The round 2 additions (CLI, persistence, flows, help) are solid and well-tested.

**The catastrophes are in the narrative layer, not the code layer.** The documentation artifacts (VISION.md, IMPLEMENTATION_PLAN.md, task list) were not maintained to track the actual state of the code. This is the classic pattern: implementation outpaces documentation, and the documentation becomes a misleading historical snapshot rather than a reliable state signal.

**The one HIGH-severity finding** is the MATCH phantom (#5) -- because it's not just stale docs, it's actively misleading help text that will make any AI user believe MATCH is a base-level feature. This would cause real failures at runtime.
