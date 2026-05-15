# Dispatch Prompt 3 — Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18

## Purpose

**This is the LOAD-BEARING finding of the first-batch dispatch.**

The April 18 bug describes a disconnection between YOUKNOW's compiler and the core sentence — the bootstrap structure that makes the core sentence usable in the compiler as the universal d-chain template for everything in the ontology. The mereological closure that defines ONT depends on this bootstrap being correct.

The hypothesis (Isaac): the recursive walker (April 19 work, "replaces Pellet sync_reasoner" per starlog `diary_d7bb3b4e`) was the FIX for this bug.

If the hypothesis holds: bug is closed, recursive walker IS the universal d-chain primitive we expected, migration shape stays.

If the hypothesis doesn't hold: YOUKNOW's bootstrap structure is still broken, and we have to re-assess how much of YOUKNOW even goes into SOMA — because the core sentence's universal-d-chain role is the basis for ONT.

## Instructions

1. **Retrieve the bug concept** via `mcp__carton__get_concept`:
   - Concept name: `Bug_Youknow_Compiler_Disconnected_From_Core_Sentence_Apr18`
   - Report the VERBATIM description, all relationships, and any related concepts.

2. **Specifically check the hypothesis:** does the bug concept indicate it was resolved by the April 19 recursive-walker work that replaced Pellet sync_reasoner?

   Look for:
   - Related concepts mentioning the recursive walker (e.g., `Pattern_Recursive_Restriction_Walk_Replaces_Pellet`, `Skill_Recursive_Walker`, `Idea_Recursive_Walker_Apr19`)
   - Related concepts about owl_types replacing cat_of_cat
   - April 19 starlog entries (`diary_d7bb3b4e`, `diary_ca0deaba`) referenced in relationships
   - Status fields, resolution markers, or `is_resolved_by` / `resolved_by` relationships
   - Any concept that mentions "core sentence" being made usable in the compiler

3. **Render verdict:** STILL OPEN / RESOLVED / PARTIALLY RESOLVED / UNCLEAR. For each verdict, cite the specific evidence (relationship, concept name, description text) that supports it.

4. **If partially resolved or unclear:** identify what part of the disconnection is fixed and what part might still be open. The migration team needs this to know if more YOUKNOW pieces require migration or if some pieces should be dropped entirely.

5. **List ALL related concepts** found via the relationships, with one-line descriptions of each. Don't filter — every related concept could be a clue.

## What NOT to do

- **Do NOT mutate the graph.** No add_concept, rename_concept, or any write operation. Read-only.
- **Do NOT speculate beyond the evidence.** If the bug concept doesn't say it was resolved, report "no resolution evidence in the concept" rather than inferring.
- **Do NOT confine search to one concept.** Walk relationships to find context.

## Where to write findings

`/home/GOD/gnosys-plugin-v2/base/soma-prolog/agent_crosscheck/findings_bug_youknow_compiler_disconnected_2026_05_13.md`

Use the following sections:
- **Bug concept verbatim** (description, relationships, related concepts)
- **Hypothesis check** (did April 19 recursive-walker resolve it?)
- **Verdict** (STILL OPEN / RESOLVED / PARTIALLY RESOLVED / UNCLEAR) with cited evidence
- **If not fully resolved:** what part is still open
- **All related concepts** (one-line each)
- **Notes / surprises**

## Context

This dispatch is part of the YOUKNOW→SOMA cross-check convo. See `agent_crosscheck/agent_to_agent_convo.md` for the migration plan context.

If verdict comes back as STILL OPEN or PARTIALLY RESOLVED, the cross-check convo will pivot to re-assessing the migration scope. The bootstrap structure being broken means the core sentence isn't yet usable as the universal d-chain template, which means ONT isn't reachable via the recursive walker, which means YOUKNOW's role in SOMA needs serious re-evaluation. This is a load-bearing finding — handle with care, report fully.
