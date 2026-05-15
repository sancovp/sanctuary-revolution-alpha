# Dispatch Prompt 4 — Sanctuary scoring rule survey

## Purpose

Sanctuary scoring rules are concrete examples of "primitive/parallel/quasi" d-chain work already active in the codebase — written today as hand-written Cypher / Python without an ontology layer. They are:

1. **Reference for what we're migrating TO d-chain form.** Each existing scoring rule is a structural cousin of what a SOMA d-chain looks like.
2. **The second migration target after HAS_CONTENT** in the intense-zone sequence. Per Round 13 — sanctuary-scoring extends polymorphism coverage from string (HAS_CONTENT) to int, surfaces XML char constraint from operator side (`>` comparisons), tests janus int serialization, and demonstrates the typed-strings-vs-logic thesis in production code.

This dispatch surveys what's there and identifies the simplest first migration candidate.

## Instructions

1. **Survey sanctuary scoring code.** Likely paths:
   - `/home/GOD/gnosys-plugin-v2/starsystem/reward-system/`
   - `/home/GOD/gnosys-plugin-v2/application/sanctum-builder/`
   - Plus any other paths that surface via grep for "score" / "scoring" / "reward" in `gnosys-plugin-v2/`

2. **Catalog each scoring rule found.** For each rule report:
   - File:line of the rule definition
   - Function/method signature (name, args, return type)
   - What it computes (formula, aggregation pattern)
   - Dependencies (what other data/functions it reads)
   - Whether it's **flat** (no recursion over partials) or **recursive** (computes by descending into sub-structures)
   - Whether it uses raw Cypher, Python expressions, or some other shape

3. **Identify the LOWEST-ARITY FLAT rule** as the first migration candidate. Criteria:
   - Flat (no recursion) — so reifies-terminal isn't a prerequisite
   - Fewest input arguments (minimum dependencies → minimum surface area for first migration)
   - Self-contained (doesn't require auxiliary scoring rules to fire first)

4. **Report verdict on migration candidacy:**
   - If a flat lowest-arity rule exists: name it, give its full code, describe the shape we'd migrate it to as a d-chain.
   - If NO flat rule exists: report explicitly (sequence will need reorder per Round 14 caveat — reifies-terminal before sanctuary-scoring).

## What NOT to do

- **Do NOT edit any code.** Read-only.
- **Do NOT propose architectural changes to the scoring system.** Just report what's there.
- **Do NOT skip recursive rules in the catalog.** Even if not the first migration candidate, they're useful for understanding the d-chain-like patterns already in production.

## Where to write findings

`/home/GOD/gnosys-plugin-v2/base/soma-prolog/agent_crosscheck/findings_sanctuary_scoring_survey_2026_05_13.md`

Use the following sections:
- **Survey scope** (paths searched)
- **Scoring rules catalog** (one entry per rule with the fields above)
- **First migration candidate** (the lowest-arity flat rule, or "none found" with reasoning)
- **Notes / surprises** (e.g., d-chain-like patterns spotted, common shapes across rules)

## Context

This dispatch is part of the YOUKNOW→SOMA cross-check convo. See `agent_crosscheck/agent_to_agent_convo.md` for the migration plan context, especially Round 13 (sanctuary-scoring as second pick after HAS_CONTENT) and Round 14 caveat (flat rule preferred to avoid needing reifies-terminal first).

The migration pattern target: take the simplest scoring rule, encode it as a SOMA Deduction_Chain / Prolog_Rule OWL individual whose body computes the score over the concept's partials. Surfaces janus int serialization + the XML-char constraint (`>` comparisons need `succ/2` workaround) + the polymorphic return shape. Successful migration of one scoring rule proves the unification thesis (logic via d-chains, not raw Cypher) on real code.
