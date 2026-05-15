# Dispatch Prompt 1 — owl_types accumulator structure

## Purpose

Verify the structure of YOUKNOW's `owl_types` accumulator module. The Phase 1 migration plan (per WIP-15) assumes the accumulator is a module-level singleton that py_calls from SOMA can share via Python import caching. This dispatch confirms that assumption is true on disk OR identifies the actual shape so the plan adjusts.

## Method requirement

**Trace from `youknow().compile()` DOWN through the callgraph to `owl_types`.** Do NOT read `owl_types.py` in isolation — its findings only mean something in the context of how `compile()` reaches it. Per the global rule `always-contextualize-any-code.md`: full entrypoint-to-terminal trace.

## Instructions

1. **Locate the entry point.** Find `youknow().compile()` (or whatever the public compile entry point is) in `youknow_kernel/`. Likely paths: `youknow_kernel/compiler.py`, `youknow_kernel/__init__.py`. Report the exact `file:line` of the entry.

2. **Trace the callgraph DOWN from the entry to `owl_types`.** Follow function calls, method dispatches, and imports until you reach a use of the `owl_types` accumulator. Report each hop: caller `file:line` → callee `file:line` → what's passed.

3. **At `owl_types.py`:** Report the exact `file:line` of the accumulator's definition. Determine its declaration shape:
   - Module-level singleton (importable as e.g. `from owl_types import accumulator` / accessed via `owl_types.accumulator`)?
   - Class requiring instantiation (e.g. `OWLTypeRegistry()`)?
   - Some other pattern?

4. **Grep all import sites of `owl_types`** in `youknow_kernel/` and in any consumer code. Report each site's `file:line` and how it accesses the accumulator (direct import, instantiation, etc).

5. **Report:** does the accumulator look like it would be safely shared as a singleton across py_calls from SOMA (which would import youknow_kernel), or does it require explicit handle-passing?

## What NOT to do

- **Do NOT edit any code.** Read-only.
- **Do NOT read `owl_types.py` first in isolation.** The trace from `compile()` is the load-bearing context.
- **Do NOT make architectural recommendations.** Just report what's on disk.

## Where to write findings

`/home/GOD/gnosys-plugin-v2/base/soma-prolog/agent_crosscheck/findings_owl_types_singleton_2026_05_13.md`

Use the following sections:
- **Entry point** (file:line)
- **Callgraph trace** (each hop)
- **Accumulator definition** (file:line + declaration shape)
- **Import sites** (each consumer's file:line and access pattern)
- **Singleton vs instantiation verdict**
- **Notes / surprises**

## Context

This dispatch is part of the YOUKNOW→SOMA cross-check convo. See `agent_crosscheck/agent_to_agent_convo.md` for the migration plan context, especially Round 14 (Phase 1 sequencing) and Correction #2 (the corrected state ladder).
