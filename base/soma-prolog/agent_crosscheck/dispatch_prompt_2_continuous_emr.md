# Dispatch Prompt 2 — continuous_emr shape and role

## Purpose

Understand the shape of `continuous_emr.py` in YOUKNOW. It was flagged in Round 11 as a likely intense-zone hot-spot (CODE/SYSTEM_TYPE conflation) that no agent has loaded context on. The migration sequencing depends on knowing whether it's flat enough to migrate as a py_call wrapper or whether it embeds recursion that needs reifies-terminal first.

## Method requirement

**Trace from `youknow().compile()` DOWN through the callgraph to `continuous_emr`.** Do NOT read `continuous_emr.py` in isolation — its findings only mean something when traced from the entry point. Per the global rule `always-contextualize-any-code.md`: full entrypoint-to-terminal trace.

## Instructions

1. **Locate the entry point.** Find `youknow().compile()` (or whatever the public compile entry point is) in `youknow_kernel/`. Report the exact `file:line` of the entry.

2. **Trace the callgraph DOWN from the entry to `continuous_emr`.** Follow function calls, method dispatches, and imports until you reach a use of `continuous_emr`. Report each hop: caller `file:line` → callee `file:line` → what's passed.

3. **At `continuous_emr.py`:** Read the whole file. Report:
   - Top-level entry function signatures (name, args, return type)
   - What graph/state it walks (which structures does it traverse)
   - What it accumulates (in-memory state, side effects, OWL writes)
   - What it returns (shape and meaning)
   - Whether it recurses over partials/morphisms or is structurally flat

4. **Grep all import sites of `continuous_emr`** in `youknow_kernel/` and any consumer code. Report each site's `file:line` and the access pattern (function call, class instantiation, etc).

5. **Report:** how does `continuous_emr` relate to the EMR principle (Embodies/Manifests/Reifies) per the global rule `emr-reifies-is-result-not-input.md`? Is it the runtime implementation of reifies-as-knowledge chain closure, or something else?

## What NOT to do

- **Do NOT edit any code.** Read-only.
- **Do NOT read `continuous_emr.py` first in isolation.** The trace from `compile()` is the load-bearing context.
- **Do NOT make architectural recommendations.** Just report what's on disk.

## Where to write findings

`/home/GOD/gnosys-plugin-v2/base/soma-prolog/agent_crosscheck/findings_continuous_emr_shape_2026_05_13.md`

Use the following sections:
- **Entry point** (file:line)
- **Callgraph trace** (each hop)
- **continuous_emr top-level signatures**
- **What it walks / accumulates / returns**
- **Recursion shape** (recursive over partials, flat, or other)
- **Import sites** (each consumer's file:line and access pattern)
- **Relation to EMR principle**
- **Notes / surprises**

## Context

This dispatch is part of the YOUKNOW→SOMA cross-check convo. See `agent_crosscheck/agent_to_agent_convo.md` for the migration plan context, especially Round 14 (intense-zone sequencing) and Correction #2 §6/§7/§8 (the d-chain principle, the LLM POV framing, projection per-projector).

Recursion-shape finding affects sequencing: if continuous_emr is recursive over partials, reifies-terminal needs to be in place BEFORE this piece migrates. If flat, it can migrate without reifies-terminal landed first.
