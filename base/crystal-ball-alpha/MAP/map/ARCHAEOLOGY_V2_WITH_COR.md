# Catastrophe Archaeology V2: Map Codebase Deep Analysis

**Auditor:** Catastrophe archaeology agent with mandatory DefeasibleReasoning4Notes2Self CoR
**Date:** 2026-02-25
**Method:** Full source read of every file, line-by-line verification of every claim in VISION.md and IMPLEMENTATION_PLAN.md against actual code and test suite
**Files examined:** 25+ source files, 210 tests (all passing), VISION.md, IMPLEMENTATION_PLAN.md, task list, two prior archaeology reports
**Prior reports:** ARCHAEOLOGY_BASELINE.md (no CoR), ARCHAEOLOGY_WITH_COR.md (CoR, same session)

---

## 0. Preamble: Why V2?

Two archaeology reports already exist for this codebase. Both were produced by agents in the same session as the dev team. This V2 report is produced by a fresh agent with no shared context from the build session. This matters because prior archaeology agents may have inherited kv-cache from the dev team's work, meaning they could have the same blind spots as the builders. A cold-start archaeology avoids that contamination.

I will apply the DefeasibleReasoning4Notes2Self CoR at every major analysis section. I will verify EVERY checkmark in IMPLEMENTATION_PLAN.md against actual source code. I will cross-reference the prior reports and note where they were accurate vs where they missed things.

---

## 1. First Contact: What Does the Task List Tell Me?

The past LOOKS LIKE two rounds of coordinated dev work happened because the task list shows tasks #1-5 (round 1: error positions, self-dispatch write, pattern matching, modules, test suite) and tasks #8-12 (round 2: CLI, persistence, help, flows, test verification). The task list has "worker" (#6, #13) and "reviewer" (#7, #14) tasks still marked `in_progress`, but if these are DONE SIGNALS (process markers that were never cleaned up) instead of STATE SIGNALS (actual ongoing work), I need to distinguish them. Since the code shows completed implementations for all numbered tasks, and 210 tests pass, the worker/reviewer tasks are zombie entries -- process markers, not work items. Since all concrete work tasks (#1-5, #8-12) show `completed`, and the code confirms their completion, I will treat the task list as showing two completed rounds with uncleaned process markers.

**Catastrophe classification:** Type A (False Completion, inverted) -- tasks are falsely marked as in-progress when the work is done. Minor, but an agent reading the task list would see 4 "active" tasks and might try to coordinate with or wait for nonexistent workers.

---

## 2. IMPLEMENTATION_PLAN.md: Line-by-Line Verification of Every Checkmark

### 2.1 base/ -- Custom Lisp ("Map")

I will verify every `[x]` claim against the actual source code.

The past LOOKS LIKE the base layer is fully implemented because IMPLEMENTATION_PLAN.md has 17 checked items in the base section. IMPLEMENTATION_PLAN.md has `[x]` markers on every item, but if any of these are DONE SIGNALS placed by the dev agent at commit time without verification, they could be false. Since I have both the source and test suite, I will check each one against both.

| # | Claim | Source File Evidence | Test Evidence | Verified? |
|---|-------|---------------------|---------------|-----------|
| 1 | `{}` instead of `()` | `parser.py` line 113: checks for `{` and `}` structurally. `types.py` line 91: `Cell.__repr__` uses `{` `}`. | `TestParser::test_simple_expr` parses `{+ 1 2}`. `TestTypes::test_cell_repr_uses_braces` asserts `{1 2}`. | YES |
| 2 | Pipe-delimited sections `{morph \| x \| body}` | `parser.py` lines 155-169: pipe sections collected during list parse. `_build_pipe_form` at line 173. | `TestParser::test_pipe_morph` verifies `{morph \| x \| {* x 2}}` | YES |
| 3 | `~` quote, `@` eval | `parser.py` lines 101-111: `~` -> QUOTE, `@` -> EVAL. `eval.py` lines 78-90: QUOTE and EVAL handlers. | `TestParser::test_quote`, `TestParser::test_eval_unquote`, `TestEval::test_quote`, `TestEval::test_eval_unquote` | YES |
| 4 | Homoiconic type system (Cell/Atom, code = data) | `types.py`: Cell, Atom, NIL form the only data types. `eval.py` line 186-188: `{env}` returns env as Map data. | `TestEval::test_env_introspection`, `TestEval::test_homoiconicity`, `TestIntegration::test_homoiconic_roundtrip` | YES |
| 5 | All numbers are Fraction internally | `types.py` line 33: `self.val = Fraction(val)` for int/float. | `TestTypes::test_atom_fraction`, `TestEval::test_arithmetic_div_fraction`, `TestIntegration::test_division_always_fraction` | YES |
| 6 | No strings, only symbols and keywords | `types.py`: Atom stores symbols (uppercased) and keywords (`:` prefix). BUT -- **claim is PARTIALLY FALSE**: string literals ARE supported (line 38-39: `"` prefix handling, `is_str` property at line 57-58). `parser.py` line 116-118 handles double-quoted strings. `stdlib.py` line 242-246 has `STR?` builtin. IMPLEMENTATION_PLAN.md line 32 even acknowledges this: "String literals -- double-quoted..." | CONTRADICTION: Plan line 6 says "No strings" and Plan line 32 says "String literals" exist. Both are checked `[x]`. |
| 7 | Environments as cons-cell chains, NOT dicts | `env.py`: `Env` with `Frame` linked list. `lookup` at line 36 walks chain. `bind` at line 49 prepends frame. | `TestEnv` class -- 9 tests covering bind, lookup, shadow, mutate, extend. | YES |
| 8 | `head`/`tail` not `car`/`cdr` | `stdlib.py` lines 109-123: `HEAD` and `TAIL` builtins, no `car`/`cdr`. | `TestEval::test_head_tail` | YES |
| 9 | Special forms: bind, morph, when, seq, loop | `eval.py`: BIND (line 92), MORPH (line 117), WHEN (line 150), SEQ (line 165), LOOP (line 175) | Multiple tests in TestEval and TestSetMacroLoop | YES |
| 10 | `def` for named recursive functions | `eval.py` line 134: DEF handler. `parser.py` line 192: DEF pipe form. | `TestEval::test_def`, `TestEval::test_def_recursive` (fact 10 = 3628800) | YES |
| 11 | `set!` for mutation | `eval.py` line 107: SET! handler. `env.py` line 56: `mutate` method. | `TestSetMacroLoop::test_set_basic`, `test_set_in_closure`, `test_set_unbound_raises` | YES |
| 12 | `macro` (fexpr) | `eval.py` line 126: MACRO handler returns Macro. Line 213-221: Macro application passes args unevaluated, uses caller's env. | `TestSetMacroLoop::test_macro_basic`, `test_macro_with_eval` | YES |
| 13 | `apply` | `eval.py` line 190: APPLY handler. | `TestEval::test_apply` -- `{apply + {list 1 2 3}}` => 6 | YES |
| 14 | Tail-call optimization via trampoline | `eval.py`: while-True trampoline loop (line 52). `_apply` returns `TailCall` (line 244). WHEN and SEQ use `continue` for TCO. | `TestTCO::test_deep_recursion` (5000 frames), `test_mutual_tco_via_seq` (1000 sum) | YES |
| 15 | Standard library | `stdlib.py`: 25+ builtins covering arithmetic, comparison, logic, list ops, type checks, IO, module access. | TestEval has 30+ tests covering stdlib operations | YES |
| 16 | String literals | `parser.py` line 116-118: STR token type. `types.py` line 38-39: `"` prefix storage. `eval.py` line 63: strings self-evaluate. | `TestModules::test_string_literal_parse`, `test_string_literal_self_eval` | YES |
| 17 | Module/import system | `eval.py` lines 200-208 (LOAD handler), 283-322 (_load_module). `stdlib.py` lines 221-240 (MODULE-GET). | `TestModules`: test_load_module, test_module_get, test_module_get_function, test_load_relative_path, test_load_file_not_found | YES |
| 18 | REPL | `eval.py` lines 342-366: `repl()` function. | Plan acknowledges "not tested interactively". No tests exist. | YES (exists), but UNTESTED as acknowledged |
| 19 | Regression tests -- 148 test methods | **FALSE.** Actual count is 210. | `pytest -v` shows 210 passed. | NO -- stale number |
| 20 | Error messages with source positions | `parser.py` lines 12-27: ParseError with line/col, `_offset_to_line_col`. Lines 69-72: `_lc` method. Used in `expect`, `parse_expr`, `parse_list`. | `TestParser`: test_error_unclosed_brace_has_position, test_error_multiline_position, test_error_expect_mismatch_has_position, test_error_eof_in_nested | YES |

**Catastrophe findings in base/ section:**

1. **Type C (Binding Drift) -- "No strings" vs string literals.** IMPLEMENTATION_PLAN.md item 6 says "No strings, only symbols (UPPERCASE) and keywords (:KEYWORD)" but item 16 (line 32) says "String literals -- double-quoted `"path/to/file"`, stored as Atom with `"` prefix." Both are checked. The "No strings" claim was the original design; strings were added later. The original checklist item was never updated. An agent reading item 6 would believe strings don't exist.

2. **Type D (Narrative Overwrite) -- stale test count.** "148 test methods" was accurate at end of round 1. Round 2 added 62 tests. The number was never updated. Both prior archaeology reports correctly identified this.

### 2.2 meta/ -- Meta-Circular Evaluator

The past LOOKS LIKE the meta layer is fully implemented because IMPLEMENTATION_PLAN.md has 12 checked items in the meta section. meta/meta_circular.map is 195 lines, meta/meta_interp.py is 165 lines, meta/bootstrap.py exists. But if any checks are aspirational DONE SIGNALS, I need to verify.

| # | Claim | Source Evidence | Test Evidence | Verified? |
|---|-------|----------------|---------------|-----------|
| 1 | meta_interp.py with pre/post eval hooks | `meta_interp.py` lines 22-67: MetaInterpreter with hooks_pre, hooks_post, monkey-patch of map_eval | No direct hook tests. `TestMetaCircular` uses boot_meta() which creates MetaInterpreter. | YES (code exists), but hooks themselves are NOT tested |
| 2 | meta_circular.map -- Map evaluator IN Map | 195 lines of Map code. Defines ENV-EMPTY, ENV-BIND, ENV-LOOKUP, ENV-EXTEND, META-EVAL-LIST, META-APPLY, META-BIND?, META-EVAL-SEQ, META-EVAL, META-STDLIB, META-EVAL-PROGRAM | Boot test in TestMetaCircular::test_meta_boot confirms META-ENV is bound | YES |
| 3 | ENV-EMPTY, ENV-BIND, ENV-LOOKUP, ENV-EXTEND | Lines 13-31 of meta_circular.map | Indirectly tested through meta eval tests that use bindings | YES |
| 4 | META-EVAL dispatches on type | Lines 88-141: handles nil, num, atom (kw/sym), cell (special forms + application) | TestMetaCircular: test_meta_add, test_meta_mul, test_meta_nested, test_meta_quote, test_meta_when_true/false | YES |
| 5 | META-EVAL handles QUOTE, BIND, DEF, WHEN, SEQ, MORPH | Lines 103-135 of meta_circular.map | Tested: QUOTE (test_meta_quote), WHEN (test_meta_when_true/false), MORPH (test_meta_morph, test_meta_morph_apply), SEQ (test_meta_seq), BIND (TestMetaBind::test_meta_bind_in_seq, test_meta_bind_program), DEF (test_meta_def_program, test_meta_def_recursive_program) | YES |
| 6 | META-APPLY handles builtins and closures | Lines 42-64: dispatches on type (:BUILTIN -> host apply, :CLOSURE -> env extend + eval, :NAMED-CLOSURE -> self-bind + env extend + eval) | test_meta_morph_apply (closure), test_meta_add (builtin delegation) | YES |
| 7 | META-STDLIB bootstraps builtins | Lines 145-168: binds +, -, *, /, =, <, >, HEAD, TAIL, CONS, LIST, NIL?, ATOM?, CELL?, NUM?, TYPE?, PRINT, LENGTH, NTH, T, NIL | test_meta_boot verifies META-ENV is populated | YES |
| 8 | Closures as {:CLOSURE params body env} and {:NAMED-CLOSURE ...} | Lines 132-135 (MORPH -> :CLOSURE), lines 112-118 (DEF -> :NAMED-CLOSURE) | test_meta_morph asserts result.head == Atom(":CLOSURE") | YES |
| 9 | Two-level interpretation | meta_interp.py line 106-117: eval_in_meta wraps source as `{META-EVAL ~{source} META-ENV}` | TestIntegration::test_two_level_same_result verifies 5 expressions produce identical results at base and meta level | YES |
| 10 | bootstrap.py | meta/bootstrap.py exists | Not directly tested but boot_meta() in meta_interp.py serves same purpose | YES |
| 11 | Meta-eval of BIND/DEF | meta_circular.map lines 104-118 handle BIND and DEF via META-BIND tagged return values. META-EVAL-SEQ (line 75-84) and META-EVAL-PROGRAM (line 174-188) thread env through binds. | TestMetaBind: 4 tests covering bind in seq, bind in program, def, recursive def | YES |

**Catastrophe findings in meta/ section:**

3. **Type A (False Completion, subtle) -- meta hooks are not tested.** The MetaInterpreter has `hooks_pre`, `hooks_post`, `hooks_bind`, `hooks_apply` (line 29-31 of meta_interp.py), and `on_pre_eval()`, `on_post_eval()` methods. But `hooks_bind` and `hooks_apply` are declared and NEVER USED anywhere. `on_post_eval` is defined but never called in tests. Only `hooks_pre` might fire through the monkey-patch. The IMPLEMENTATION_PLAN claims "Python wrapper with pre/post eval hooks -- implemented, imports work" which is technically true (the code exists, imports work), but the hooks are dead code paths. The claim "implemented" means "the stub exists," not "this is a working, tested feature."

4. **Architectural concern -- monkey-patching global eval.** MetaInterpreter._patch() at line 37 replaces `base_eval.map_eval` globally. The prior reports both identified this. Creating multiple MetaInterpreter instances stacks hooks. This is not a catastrophe per se (the code works in practice because tests create one instance per fixture), but it IS a latent failure mode. No test verifies isolation between meta instances.

### 2.3 super/ -- Hot-Reloadable Metaprogramming

The past LOOKS LIKE the super layer is fully implemented because IMPLEMENTATION_PLAN.md has 10 checked items. The super/ directory contains registry.py, hot.py, main.py, and 4 .map files in ops/. But if the claims are DONE SIGNALS from when the checklist was marked rather than STATE SIGNALS verified against code, I need to check each one.

| # | Claim | Source Evidence | Test Evidence | Verified? |
|---|-------|----------------|---------------|-----------|
| 1 | registry.py -- OpEntry, Registry | registry.py: OpEntry (26-55), Registry (58-231) | TestRegistry: 8 tests | YES |
| 2 | Hot-reload via file hash comparison | registry.py line 37-45: OpEntry.is_stale uses md5 hash | TestHotReload::test_stale_detection | YES |
| 3 | Background watcher thread | hot.py lines 18-76: HotEngine with _watch_loop in daemon thread | TestHotReload::test_hot_watcher_detects_changes, test_hot_new_file_detection | YES |
| 4 | Registry exposed as Map data | registry.py line 47-55: OpEntry.to_map. Line 72-78: reg-list builtin | TestRegistry::test_reg_list_builtin | YES |
| 5 | Create operations at runtime | registry.py line 100-114: reg-register and reg-define-op builtins | TestRegistry::test_register_inline, test_define_op_creates_file | YES |
| 6 | Self-modification: self-rewrite, self-inspect, self-fork | hot.py lines 99-141: self_rewrite, self_inspect, self_fork | TestSelfMod: test_self_inspect, test_self_rewrite, test_self_fork | YES |
| 7 | self-dispatch (read + write) | hot.py lines 143-194: 0-arg read, 1-arg write with table replacement | TestSelfMod: test_self_dispatch_read, test_self_dispatch_write, test_self_dispatch_write_updates_existing | YES |
| 8 | Super-REPL | super/main.py lines 49-153: full REPL with meta-commands | No tests (acknowledged as untested). | YES (exists), UNTESTED |
| 9 | Starter operations: map/filter/reduce, compose/pipe/identity, reify/memo, match | ops/map.map (MAP, FILTER, REDUCE), ops/compose.map (COMPOSE, PIPE2, IDENTITY, CONST, FLIP), ops/reify.map (BUILD-EXPR, REIFY-BINOP, MAKE-COUNTER, MAKE-MEMO, MEMO-LOOKUP), ops/match.map (MATCH-PAT, MATCH-CLAUSES, MATCH) | TestRegistry: test_map_op, test_filter_op, test_reduce_op, test_compose_op, test_identity_op. TestReify: test_build_expr, test_make_counter, test_identity_fn, test_const, test_flip. TestMatch: 7 tests. | YES |
| 10 | Hot-reload + self-mod tested | See items 2-3 and 6-7 above | 5 hot-reload tests, 5 self-mod tests | YES |

**Catastrophe findings in super/ section:**

5. **Missing test coverage for PIPE2.** The compose.map defines PIPE2 (reverse composition) at line 9, but no test exercises it. IMPLEMENTATION_PLAN.md doesn't explicitly claim PIPE2 is tested, but the `[x]` on "Starter operations" implies everything in the ops files was tested. PIPE2 was not.

6. **Missing test coverage for REIFY-BINOP.** reify.map defines REIFY-BINOP at line 9, but no test exercises it. Same situation as PIPE2.

7. **Missing test coverage for MAKE-MEMO.** reify.map defines MAKE-MEMO (lines 25-34) and MEMO-LOOKUP (lines 36-41), but no test exercises memoization. These are non-trivial functions involving stateful closures and cache mutation.

### 2.4 Round 2: CLI, Persistence, Help, Flows

The past LOOKS LIKE round 2 added four new subsystems because the task list shows tasks #8-12 completed. These correspond to `__main__.py`, `base/persistence.py`, `base/help.py`, and `base/flows.py`. All four files exist and are substantial. But the IMPLEMENTATION_PLAN.md was written for round 1's features and only partially updated for round 2 -- specifically, the "Known Bugs (Open)" section was updated but the test count and "Honest Status" section were not.

I will verify round 2 features directly rather than trusting any plan document.

| Feature | Implementation | Tests | Issues Found |
|---------|---------------|-------|--------------|
| CLI (`__main__.py`) | 361 lines, 13 commands: run, eval, save, list, inspect, compose, modify, delete, flow-run, meta, super, clear, help | TestCLI: 22 tests | `meta` and `super` CLI commands not tested through CLI subprocess. `compose`, `delete`, `inspect` not tested through CLI subprocess. |
| Persistence (`base/persistence.py`) | 175 lines. JSON serialization of Atom (num, sym, kw, str), Cell, Morph. Three-pass deserialize (deserialize, add to env, patch Morph envs). | TestPersistence: 11 tests | Solid coverage. Serialization roundtrip tested for all types. |
| Help (`base/help.py`) | 325 lines. 4-level progressive disclosure. BREADCRUMB, COMMAND_INDEX, COMMAND_HELP (13 commands), FORM_HELP (11 forms). | TestHelpSystem: 8 tests. TestCLI also tests help via subprocess. | MATCH documented in FORM_HELP but not a base-level feature. |
| Flows (`base/flows.py`) | 162 lines. Named flows stored as .map files with .meta.json metadata. Save, list, inspect, run, delete. | TestFlows: 14 tests. TestCLI tests save, flow-run, modify, list via subprocess. | Solid coverage. |

**Catastrophe findings in round 2:**

8. **Type B (Sycophantic Alignment) -- MATCH in help system.** help.py documents MATCH as a Level 3 special form (FORM_HELP dictionary, lines 285-295). The help text says: "Syntax: {match expr | pattern1 | result1 | pattern2 | result2 | ...}" -- but this syntax doesn't work at all. The actual MATCH operation in super/ops/match.map takes a list of clauses, not pipe-delimited patterns: `{MATCH value {list {list pattern1 result1} ...}}`. The help documents a syntax that doesn't exist ANYWHERE in the codebase. This is worse than the prior reports identified -- it's not just "MATCH at wrong level," the documented syntax is completely wrong. The prior reports noted MATCH's level misplacement but did NOT catch the syntax mismatch.

9. **Type B (Sycophantic Alignment) -- MATCH in flows.py inspect_flow.** `flows.py` line 111 lists MATCH in the `special_forms` set used by `inspect_flow`. This means flow inspection treats MATCH as a special form (excluding it from "user refs" / dependencies). If a flow uses MATCH, the inspector won't report it as a dependency, making it seem self-contained when it actually requires the super layer. Both prior reports noted this.

10. **Untested CLI commands.** The following CLI commands have implementations but no CLI-level tests (subprocess tests):
    - `meta` (cmd_meta, line 108-128): No CLI test
    - `super` (cmd_super, line 131-159): No CLI test
    - `compose` (cmd_compose, line 221-247): No CLI test
    - `delete` (cmd_delete, line 275-287): No CLI test
    - `inspect` (cmd_inspect, line 197-218): No CLI test

    The underlying functions are tested at the Python API level, but the CLI wrappers (argument parsing, error formatting, subprocess behavior) are not. The prior baseline report correctly identified this gap.

---

## 3. VISION.md vs Actual State: Detailed Comparison

The past LOOKS LIKE the VISION was written as a target spec before development because it describes features in aspirational language ("What's missing"). VISION.md was clearly revised at least once (the "Current State" section mentions "148 passing tests" which places its last edit after round 1 but before round 2). But the "What's missing" list was never updated after round 2 implementations. Since VISION.md serves as the spec that the team was building toward, I need to map its claims against reality precisely.

### 3.1 Non-Interactive REPL Design

**VISION says:** AI calls Map as a shell command/tool: `echo '{...}' | python3 -m map run`, `python3 -m map eval '{...}'`, etc.

**Actual:** `python3 -m introduction_to_cs run/eval/etc.` -- module name mismatch. This is well-documented by prior reports.

**NEW FINDING:** The VISION shows `python3 -m map eval '{set! task-context {merge task-context new-observations}}'` -- this implies a `merge` function exists. `merge` is NOT in the stdlib (`stdlib.py`). Neither `merge` nor `MERGE` appear anywhere in the codebase except VISION.md. This example would fail with `NameError: Unbound symbol: MERGE` if an AI tried to run it.

**Catastrophe Type:** C (Binding Drift). The VISION contains example code referencing functions that don't exist. An AI reading the VISION and trying to follow its examples would hit errors.

### 3.2 Symbol Semantics Table

**VISION says:** 9 symbols with attention-primitive semantics (BIND, MORPH, WHEN, SEQ, LOOP, EVAL, QUOTE/~, LOAD, MATCH).

**Actual:**
- BIND, MORPH, WHEN, SEQ, LOOP: base special forms -- YES
- EVAL, QUOTE/~: base special forms -- YES
- LOAD: base special form -- YES
- MATCH: super-layer operation only -- NOT a base form

Additionally, the base evaluator has special forms NOT listed in the VISION table: SET!, MACRO, DEF, ENV, APPLY. These are all documented in the help system but absent from the VISION's symbol semantics table.

**Catastrophe Type:** C (Binding Drift). The VISION's table is incomplete in both directions -- it claims MATCH at a level where it doesn't exist, and omits 5 actual special forms.

### 3.3 Futamura Tower

**VISION says:** 6 levels -- base, meta, super, superbase, supermeta, supersuper. "Each level shields the one below."

**Actual:** 3 levels exist -- base, meta, super. The shielding claim is partially true: you can rewrite ops but can't modify the base evaluator from Map code. But you CAN modify the meta-evaluator's behavior through the monkey-patched hooks. The shielding is not structural -- it's just that nobody wrote code to break it.

Items 5-7 in "What's missing" correctly identify the gaps. But the help system (help.py line 94) describes the super layer as "3rd Futamura level" -- implying the layer structure IS a Futamura tower. It's not. A Futamura tower requires specialization/compilation, not just layered interpretation.

The prior CoR report correctly identified this as Type E (Futamura Flattening).

### 3.4 Progressive Disclosure -- Accuracy of Level 2+

The VISION describes a 4-level help system. The implementation delivers 4 levels. But the CONTENT of the help is not fully accurate:

**Level 2 (eval help, help.py line 45-57):**
> "Special forms: bind, morph, when, seq, loop, def, set!, macro, quote, eval, apply, load"

This is accurate. Does not mention MATCH, which is correct since MATCH is not a special form.

**Level 3 (FORM_HELP):**
All 11 documented forms exist as base-level features EXCEPT `match`. The `match` entry's syntax documentation is wrong (as detailed in finding #8 above). The `loop` help says `{loop | init | cond | step}` with pipe syntax, which matches the parser handling. The `morph` help is accurate. The `def` help is accurate.

**NEW FINDING -- `eval` help form entry.** help.py line 255-263 documents `eval` as a special form: "Syntax: {eval expr} or @expr". This is correct. But it says "Evaluates the result of evaluating expr (double evaluation)" -- this is misleading. `{eval expr}` evaluates `expr` once (to get a Map value), then evaluates that value. It's not "double evaluation" in the sense of applying eval twice to the same thing; the second evaluation operates on the RESULT of the first. An AI reading "double evaluation" might expect `{eval {+ 1 2}}` to evaluate `{+ 1 2}` to get 3, then try to evaluate 3 (which self-evaluates to 3). What actually happens is correct, but the description could mislead.

---

## 4. Internal Contradictions in IMPLEMENTATION_PLAN.md

### 4.1 "Known Limitations" vs "Known Bugs (Fixed)"

Both prior reports identified this. The plan simultaneously says:
- **Known Limitations** (line 95-97): "Error messages lack line:col positions" and "`self-dispatch` write mode is a stub"
- **Known Bugs (Fixed)** (lines 129-132): These same items are struck through and marked FIXED

**Type C (Binding Drift):** Two sections of the same document give contradictory status for the same features.

### 4.2 "What Would Make This Actually Good" vs Reality

Items 9-10 (lines 146-147) are listed as open TODOs:
- "Add line:col to error messages"
- "Complete `self-dispatch` write mode"

Both are implemented. Both are tested. The TODO list was never updated.

### 4.3 "Honest Status" Is Now Dishonest

The "Known limitations" section (line 94-97) states three limitations. Two of those are no longer true (error positions exist, self-dispatch write is implemented). Only item 1 ("Interactive REPLs not tested") remains accurate.

The "What 'tested' means now" section (lines 99-103) says "148 test methods, all passing" -- stale by 62 tests.

**These are all Type D (Narrative Overwrite) -- summaries that replaced the current state with a historical snapshot.**

---

## 5. Code-Level Issues Not Found by Prior Reports

### 5.1 `and_fn` Returns Last Truthy Arg, Not Boolean

`stdlib.py` lines 96-100:
```python
def and_fn(args):
    for a in args:
        if not _to_bool(a):
            return NIL
    return args[-1] if args else NIL
```

This returns the LAST argument if all are truthy, not `Atom(1)`. So `{and 42 99}` returns `99`, not `1`. This is Lisp-standard behavior (short-circuit AND), but Map's `or` does the same thing (returns the first truthy arg). The test `TestEval::test_logic_and` tests `{and T T}` which returns `T` -- but `T` is bound to `Atom(1)` in stdlib (line 263). The test passes because `T` IS `Atom(1)`, not because `and` returns a boolean. If someone writes `{and 42 99}`, they get `99`, which might surprise someone expecting boolean returns.

This isn't a bug -- it's standard Lisp semantics. But it's undocumented in the help system and could surprise an AI user.

### 5.2 Macro Uses Caller's Env, Not Its Own

`eval.py` lines 213-221:
```python
if isinstance(fn, Macro):
    raw_args = _collect_args(args_cell)
    call_env = env.extend(fn.params, raw_args)
    expr = fn.body
    env = call_env
    continue
```

The macro body is evaluated in the CALLER's env extended with the macro params. The comment on line 214 says "Fexpr: pass args UNEVALUATED, evaluate body in CALLER's env." This is correct fexpr semantics but differs from Common Lisp macros (which run in the macro's definition env). The help system (help.py line 236-245) says "Like morph, but args are passed unevaluated. The macro body executes in the caller's environment." This IS documented correctly. No catastrophe here.

### 5.3 `Morph.__repr__` Inconsistency

`types.py` line 122: `n = self.name or 'ANON'`
`eval.py` line 142: `morph = Morph(params, body, env, name=repr(name))`

When DEF creates a Morph, it sets `name=repr(name)` which gives the Morph a name like `"FACT"` (including quotes if the name is a symbol). But `Morph.__repr__` uses this directly: `<morph "FACT" | N>`. The double-quote wrapping is harmless but inconsistent with how symbols normally display.

### 5.4 `_load_module` Global State via `_load_dirs`

`eval.py` line 281: `_load_dirs = []` -- module-global stack for tracking nested load directories. This is thread-unsafe and creates implicit global state. If two threads call LOAD simultaneously, the directory stack will corrupt. In practice, Map is single-threaded, so this doesn't cause failures. But it's a latent issue if anyone tries concurrent evaluation.

### 5.5 `cmd_super` Doesn't Persist Environment

`__main__.py` line 131-159: `cmd_super` creates a fresh `boot_meta()` and `Registry` each time, evaluates the expression, but doesn't call `save_env`. So any bindings created via the `super` command are lost. The `eval` and `run` commands DO persist (they call `save_env`). The `meta` command also doesn't persist. This means the `super` and `meta` CLI commands are stateless -- each invocation starts fresh. This might be intentional (meta/super layers are more heavyweight) but it's undocumented and inconsistent with `eval`/`run`.

---

## 6. Cross-Referencing Prior Reports

### 6.1 What Both Prior Reports Got Right

Both prior reports correctly identified:
- Test count discrepancy (148 claimed, 210 actual)
- MATCH level misplacement (documented as base, exists at super only)
- Module name mismatch (map vs introduction_to_cs)
- Stale documentation in IMPLEMENTATION_PLAN.md
- Missing CLI tests for meta, super, compose, delete, inspect
- MetaInterpreter monkey-patching concern
- Persistence CWD-dependence
- Compose being concatenation, not functional composition
- Self-fork naive name replacement
- Untested REPLs
- Task list zombie entries

### 6.2 What the CoR Report (V1) Found That the Baseline Missed

The V1 CoR report additionally found:
- Type E classification for the Futamura tower claim
- More precise tracing of which signals are DONE vs STATE signals
- The VISION.md "Current State" section being stale (doesn't include round 2)

### 6.3 What THIS Report (V2) Found That Both Prior Reports Missed

1. **MATCH help syntax is wrong** (finding #8). Prior reports noted MATCH was at the wrong level, but didn't check whether the documented syntax was correct. It's not -- the help says pipe-delimited `{match expr | pattern | result | ...}` but the actual implementation uses `{MATCH value {list {list pattern result} ...}}`. This is a DIFFERENT and MORE SEVERE issue than just level misplacement.

2. **VISION.md example code references nonexistent functions** (finding in section 3.1). `merge` doesn't exist anywhere. Prior reports didn't check the VISION's examples for executability.

3. **"No strings" contradicts "String literals"** in the same checklist (finding #1 in section 2.1). Neither prior report caught that items 6 and 16 in the base checklist contradict each other.

4. **VISION's symbol semantics table is incomplete in both directions** (section 3.2). Prior reports noted MATCH's misplacement but didn't note that SET!, MACRO, DEF, ENV, and APPLY are missing from the table while being actual special forms.

5. **Untested super ops: PIPE2, REIFY-BINOP, MAKE-MEMO** (findings #5-7 in section 2.3). Prior reports noted missing CLI tests but didn't audit which specific operations lack test coverage.

6. **cmd_super and cmd_meta don't persist environment** (section 5.5). Neither prior report noted the stateless behavior of meta/super CLI commands.

7. **MetaInterpreter hooks_bind and hooks_apply are dead code** (finding #3 in section 2.2). Declared but never used, wired, or tested.

---

## 7. Catastrophe Classification Summary

| # | Type | Location | Severity | Description | Found by prior reports? |
|---|------|----------|----------|-------------|------------------------|
| 1 | A (False Completion, inverted) | Task list | Low | Worker/reviewer tasks stuck in_progress | Yes (both) |
| 2 | C (Binding Drift) | IMPL_PLAN items 6 vs 16 | Low | "No strings" and "String literals" both checked | **NO -- new finding** |
| 3 | D (Narrative Overwrite) | IMPL_PLAN line 35, 100 | Low | Test count frozen at 148, actually 210 | Yes (both) |
| 4 | A (False Completion) | meta_interp.py hooks | Medium | hooks_bind, hooks_apply declared but dead code. "implemented" means stub exists. | **NO -- new finding** |
| 5 | A (False Completion) | super/ops/ | Low | PIPE2, REIFY-BINOP, MAKE-MEMO untested | **NO -- new finding** |
| 6 | B (Sycophantic Alignment) | base/help.py MATCH entry | **HIGH** | MATCH documented with WRONG syntax AND at wrong level | Prior reports caught level issue, **syntax issue is new** |
| 7 | B (Sycophantic Alignment) | base/flows.py line 111 | Medium | MATCH in special_forms set, hiding dependency | Yes (both) |
| 8 | C (Binding Drift) | VISION.md examples | Medium | `merge` function doesn't exist; example code would fail | **NO -- new finding** |
| 9 | C (Binding Drift) | VISION.md symbol table | Medium | Table claims MATCH, omits SET!, MACRO, DEF, ENV, APPLY | Partially (MATCH noted, omissions **new**) |
| 10 | C (Binding Drift) | IMPL_PLAN "Known Limitations" | Medium | Contradicts "Known Bugs (Fixed)" in same doc | Yes (both) |
| 11 | C (Binding Drift) | IMPL_PLAN items 9-10 in TODO | Low | Listed as TODO but implemented | Yes (both) |
| 12 | C (Binding Drift) | VISION.md vs __main__.py | Low | Module name map vs introduction_to_cs | Yes (both) |
| 13 | D (Narrative Overwrite) | VISION.md "What's missing" | Medium | 4/7 items implemented but list unchanged | Yes (both) |
| 14 | D (Narrative Overwrite) | IMPL_PLAN "Honest Status" | Medium | 2/3 limitations no longer true | Yes (both) |
| 15 | E (Futamura Flattening) | base/help.py line 94 | Medium | Super layer called "3rd Futamura level" -- it's a registry, not a specializer | Yes (CoR V1) |
| 16 | -- (Design issue) | __main__.py cmd_super/cmd_meta | Low | Meta/super CLI commands don't persist environment (unlike eval/run) | **NO -- new finding** |
| 17 | -- (Coverage gap) | TestCLI | Low | 5 CLI commands lack subprocess-level tests | Yes (baseline) |

---

## 8. The Meta-Question: How Well Did Prior Archaeology Work?

Both prior reports were produced in the same session as the dev team. The CoR V1 report was more thorough than the baseline, finding the Futamura Flattening classification and making more precise signal/noise distinctions. But both reports had a significant gap: they accepted the MATCH issue as "wrong level" without checking whether the documented syntax was even correct. This is itself a **Type B (Sycophantic Alignment)** in the archaeology layer -- the reports aligned with the help system's claim about what MATCH syntax looks like, rather than verifying it against the actual implementation.

The V2 report found 6 new issues by performing truly exhaustive line-by-line verification rather than spot-checking. The biggest new finding is that MATCH's help documentation is wrong in TWO independent ways (wrong level AND wrong syntax), making it more dangerous than previously assessed.

---

## 9. Overall Assessment

**The codebase is well-built.** 210 tests pass. The three-layer architecture works correctly. The base Lisp interpreter is solid. The meta-circular evaluator successfully interprets Map programs. The super layer provides genuine hot-reload and self-modification capabilities. Round 2 additions (CLI, persistence, flows, help) are substantial and well-tested.

**The catastrophes are concentrated in the documentation/metadata layer.** Of 17 findings, 0 are code bugs that would cause incorrect results. The issues are: stale documentation (7), misleading documentation (5), dead code (2), missing test coverage (2), and design inconsistency (1).

**The single highest-severity finding** is #6: the MATCH help entry documents a syntax (`{match expr | pattern | result | ...}`) that doesn't match anything in the codebase. The actual syntax is `{MATCH value {list {list pattern result} ...}}`. An AI reading the help and trying to use MATCH will fail in two ways: the feature isn't available at the base level, AND if they somehow get to the super level, the syntax the help describes won't work.

**What the CoR method contributed to this analysis:** The mandatory CoR paragraph at each section forced me to treat every claim as either a DONE SIGNAL or a STATE SIGNAL before accepting it. This is what caught the MATCH syntax discrepancy -- rather than accepting "MATCH is documented" as a state signal, I verified the documentation's content against the implementation. Without the CoR, I likely would have replicated V1's conclusion ("MATCH at wrong level") without checking the deeper issue ("MATCH documented with entirely wrong syntax").
