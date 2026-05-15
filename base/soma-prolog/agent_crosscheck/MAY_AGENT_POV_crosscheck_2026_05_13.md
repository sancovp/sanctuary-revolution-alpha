# SOMA Crosscheck — Other Conversation Interpretations vs Ground Truth
Date: 2026-05-13
Source: cross-check of two parallel SOMA conversations after sharing tonight's YOUKNOW-revert findings between them.

## Context

Two SOMA conversations running in parallel:
- **Convo A** (this file's home): tonight discovered YOUKNOW April 19 CODE LAYER works, reverted today's misguided d-chain wiring (commits a2f65ad/4596240/2093ed2), identified that SOMA replaces YOUKNOW via py_call into existing YOUKNOW Python.
- **Convo B**: has the SOMA_REQUIREMENTS.md (immutable) and SOMA_REQUIREMENTS_WIP.md (14 open items) — was actively going through WIP decisions when paused 3 weeks ago.

Isaac shared the Convo-A finding that Pellet is replaced by YOUKNOW's recursive walk. Convo B then made interpretations that overshoot in 3 places and conflate 1 thing. This file records the corrections.

## Original facts shared with Convo B

From the April 19 YOUKNOW starlog (diary_d7bb3b4e), one of 10 verified features:
> "Recursive restriction walk (instant, replaces Pellet sync_reasoner)"

The actually-needed py_call targets (named as **examples** replacing the HANDOFF's outdated examples like pellet_run/owl_save):
- `validate_restrictions` (the recursive walk → replaces what Pellet did for YOUKNOW)
- `project_to_X` (substrate projector dispatch — lives in carton-mcp/substrate_projector.py)
- `check_code_reality` (CA Neo4j query for stub protocol)
- `accumulate_owl_types` (owl_types.py in-memory merger that replaced cat_of_cat.py)

## Convo B interpretations and corrections

### 1. "Pellet is fully out, not just demoted." — PARTIAL OVERSHOOT

**What's true:** Pellet is out of YOUKNOW's path. The recursive walk replaces YOUKNOW's admissibility check (does every required restriction get filled?).

**What's NOT verified:** Whether SOMA needs Pellet for things YOUKNOW didn't.
- Pellet does full OWL-DL reasoning: subsumption, classification, disjointness, property-chain inference.
- The walk does admissibility only.
- If SOMA's "authorization precomputation" needs full DL reasoning (e.g., "does this proposed change create a class inconsistency three levels up the hierarchy?"), the walk may not suffice.

**Correction:** Pellet is out of YOUKNOW's code path. Whether SOMA needs it is an open WIP question, not a settled fact for immutable.

### 2. "Prolog↔Neo4j bridge has a concrete name: check_code_reality." — CONFLATION

There are TWO different Neo4j graphs:
- **CA Neo4j** = code-alignment graph (Python AST entities, imports, callgraph). `check_code_reality` queries this.
- **CartON Neo4j** = concept graph (Wiki nodes, IS_A/PART_OF/has_X relationships). Queried via `query_wiki_graph` and friends.

SOMA likely needs both at different points. `check_code_reality` is the stub-protocol-specific operation. It does NOT replace generic CartON queries. Treating "Prolog↔Neo4j bridge" as a single thing collapses two separate concerns.

### 3. "accumulate_owl_types is the OWL hierarchy merger (soma.owl → uarl.owl → starsystem.owl → gnosys_foundation.owl → user_domain.owl) at boot." — MISINTERPRETATION

This conflates two unrelated mechanisms:
- `owl_types.py` is the **in-memory type accumulator** that replaced `cat_of_cat.py`. It tracks types observed at runtime and merges them as more observations come in.
- **OWL file loading/merging** at boot is handled by owlready2 (or whichever OWL lib SOMA uses). The files import each other via owl:imports declarations.

These are two completely different mechanisms. `accumulate_owl_types` is runtime, owlready2 is boot-time. Don't conflate.

### 4. "Projection is project_to_X." — ROUGHLY CORRECT

The pattern is right. One clarification: `project_to_X` lives in **carton-mcp's `substrate_projector.py`**, not in YOUKNOW. The other agent got this part right.

### 5. "So the four py_call targets are the complete substrate SOMA's PrologRules invoke." — OVERSHOOTING

The four targets were given as **examples** of actually-needed operations that replace the HANDOFF's outdated examples (pellet_run, owl_save). They are NOT a complete or exhaustive list.

Other py_call targets that will be needed:
- CartON concept queries (query_wiki_graph, get_concept_network, chroma_query)
- LLM-call wrappers for WIP-12 Layer 3 (agent-embedded generator)
- Audit logging
- Observation persistence to soma.owl as Event/Observation individuals
- Possibly: codeness invocation for system-type-from-Python observation

Locking the substrate at "four" in immutable would prematurely close scope.

## Recommendation to Convo B

**Option (a) only — make this a new WIP item, do NOT update immutable yet.**

Reasons:
1. The Pellet-out claim is YOUKNOW-scoped only; SOMA's DL-reasoning needs are unresolved.
2. The four py_call targets are a starting set, not exhaustive.
3. The accumulate_owl_types reading conflated runtime accumulation with boot-time OWL file loading.
4. The Neo4j bridges are two separate concerns (CA code-graph vs CartON concept-graph).

The settle-point that unblocks moving anything to immutable is the answer to:
> **Does SOMA's authorization-precomputation need OWL-DL reasoning that the recursive walk doesn't provide?**

If YES → Pellet stays for the DL-reasoning role (different scope than YOUKNOW used it for).
If NO → Pellet is fully out and we declare it in immutable.

## Concrete message Isaac can paste into Convo B

> Hold off on updating immutable. Three of the four interpretations are overshooting:
>
> 1. Pellet is out of YOUKNOW's path (the walk replaces its admissibility check), but YOUKNOW's walk does admissibility only — Pellet does full OWL-DL reasoning (subsumption, classification, disjointness). Whether SOMA's authorization-precomputation needs that DL reasoning is unresolved. Don't declare "Pellet fully out" in immutable yet.
>
> 2. `accumulate_owl_types` is the in-memory type accumulator (replaced cat_of_cat.py). It is NOT the OWL file merger at boot. Those are separate mechanisms — owlready2 handles OWL file loading at boot, `owl_types.py` accumulates types observed at runtime.
>
> 3. The four py_call targets I shared (validate_restrictions, project_to_X, check_code_reality, accumulate_owl_types) are EXAMPLES of actually-needed operations replacing the HANDOFF's outdated pellet_run/owl_save examples. They are not a complete substrate list. There will be more: CartON queries, LLM-call wrappers for WIP-12 Layer 3, observation persistence, etc. Don't lock the substrate at four.
>
> 4. There are two Neo4j bridges: CA code-graph (`check_code_reality` is for this one — Python AST entities, callgraph) vs CartON concept-graph (Wiki nodes — queried via query_wiki_graph). Don't unify them.
>
> Recommended: option (a) — make this a new WIP item, don't update immutable yet. The settle-point that unblocks moving things to immutable is: does SOMA's authorization-precomputation need OWL-DL reasoning the walk doesn't provide?

File: /home/GOD/gnosys-plugin-v2/base/soma-prolog/agent_crosscheck/MAY_AGENT_POV_crosscheck_2026_05_13.md

## Relationships
- IS_A: File
- INSTANTIATES: File_Template