# Dispatch Prompts Index

First-batch dispatch for the YOUKNOW→SOMA cross-check. Four parallel agent tasks, each with its own prompt file and findings file. Read the prompt file FIRST, then execute, then write findings to the matching findings file.

## Dispatch Tasks

| # | Prompt File | Target | Findings File | Status |
|---|---|---|---|---|
| 1 | `dispatch_prompt_1_owl_types.md` | `owl_types.py` singleton structure (via trace from `youknow().compile()`) | `findings_owl_types_singleton_2026_05_13.md` | **landed** |
| 2 | `dispatch_prompt_2_continuous_emr.md` | `continuous_emr.py` shape and role (via trace from `youknow().compile()`) | `findings_continuous_emr_shape_2026_05_13.md` | **landed** |
| 3 | `dispatch_prompt_3_bug_youknow_compiler.md` | `Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18` — check if recursive walker resolved it | `findings_bug_youknow_compiler_disconnected_2026_05_13.md` | **landed — PARTIALLY RESOLVED** |
| 4 | `dispatch_prompt_4_sanctuary_scoring.md` | Sanctuary scoring rule survey — identify lowest-arity flat rule | `findings_sanctuary_scoring_survey_2026_05_13.md` | **landed** |

## Dispatch shape (per Apr Round 15 Q33)

- **Parallel** — no cross-dependencies between the four tasks.
- **Per-item findings files** — avoids merge conflicts on a shared doc, each finding revisable independently.
- **This index tracks status** — flip "not yet dispatched" → "dispatched" → "landed" as runs complete.

## Pre-dispatch gates (per Apr Round 15 Q34 — Locks)

1. **WIP-15 revision lands FIRST** — captures the settled plan that dispatch verifies against. Don't design-by-finding.
2. **Apr drafts WIP-15 revision, May reviews** before dispatch fires.
3. **Immutable doc stays untouched** until cross-check fully settles AND Isaac confirms.

## After dispatch

Each task writes its findings file. The cross-check convo (`agent_to_agent_convo.md`) then synthesizes findings, especially:

- Task 3 verdict is load-bearing — if STILL OPEN or PARTIALLY RESOLVED, the migration shape gets re-evaluated.
- Task 4 verdict determines sequencing — if no flat scoring rule exists, reifies-terminal moves before sanctuary-scoring per Round 14 caveat.
- Tasks 1 + 2 verdicts feed Phase 1 implementation specifics (owl_types singleton handle) and intense-zone planning (continuous_emr's recursion shape).

## Method discipline (per cross-check convo Method section)

Per Isaac's verbatim: figure out the YOUKNOW→SOMA migration TOGETHER through the convo FIRST. THEN dispatch agents to verify. If an agent CANNOT confirm a conclusion, that "cannot confirm" result is itself valuable data: it tells us where the codebases are unreadable to agents, and we fix readability BEFORE we refactor or improve.
