# Questions for SOMA Agent — 2026-04-17

## Context

Today we discovered that YOUKNOW's `system_type_validator.py` was commented out on 2026-03-29 with a false claim that the reasoner replaced it. It didn't. The result: Dragonbones entity chains can claim ANY starsystem, ANY GIINT hierarchy, with ZERO validation. Concepts get created in CartON regardless of whether the hierarchy exists or the starsystem is correct.

We uncommented `system_type_validator.py` and wired it into `youknow()` as a fast path. It now blocks on STRUCTURAL violations (wrong parent type prefix). But we hit a problem with COMPLETENESS checks:

GIINT hierarchy is built INCREMENTALLY by `_ensure_giint_hierarchy_in_carton` in `mcp_server.py`. A Deliverable is created WITHOUT tasks. A Component is created WITHOUT hasPath. Tasks are added later during BUILD. If the system_type_validator treats missing-but-expected relationships as errors, it blocks incremental creation.

This means we need THREE states, not two:
1. **HARD BLOCK** — wrong parent type, wrong starsystem. Provably wrong. System has complete knowledge.
2. **ANNEALING** — known incomplete state. Deliverable without tasks, Component without hasPath. The system KNOWS what's missing and KNOWS it will come during BUILD. Not SOUP (unknown incomplete). Not error. Tracked intermediate state.
3. **COMPLETE** — all restrictions satisfied. ONT.

## Questions

### Q1: Does SOMA's deduction chain routing (soma_deduction_chains.pl) already model this three-state distinction?
The deprecated `soma_deduction_chains.pl` routes unnamed partials into `from_context`, `from_llm`, `from_human`. Is "annealing" equivalent to a partial that `can_fill_from_context` but hasn't been filled yet? Or is it a different concept?

### Q2: How does SOMA's backwards reasoning handle incremental GIINT creation?
The HANDOFF says SOMA does "backwards reasoning over GIINT" — given a goal like "GIINT_Project_X is currently valid", walk rules backward to find which premises must hold. When a Deliverable is created without tasks, what does the backwards query return? Is it `failure(missing_premise(hasTask))` or something more nuanced that says "this will be filled during BUILD phase"?

### Q3: Where does the BUILD phase knowledge live?
The system knows that tasks are created DURING BUILD, not at planning time. Where should this temporal knowledge be encoded? As a Prolog rule? As an OWL axiom? As a property on the GIINT type that says "hasTask is a BUILD-time relationship, not a PLANNING-time requirement"?

### Q4: How should SOMA distinguish "wrong" from "incomplete"?
Wrong = part_of target doesn't match expected parent type (GIINT_Component part_of Random_Thing instead of Giint_Feature). The system can PROVE this is wrong.
Incomplete = missing hasTask on a new Deliverable. The system knows this is expected at this stage.
Both involve missing/wrong relationships. What's the SOMA-native way to distinguish them?

### Q5: The `_infer_from_context` function in system_type_validator.py reads OMNISANC course state to deduce starsystem. Should this inference logic live in SOMA instead?
The Python function reads `/tmp/heaven_data/omnisanc_core/.course_state` to get `last_oriented` and derives the starsystem. Should SOMA have this as observations (events about which starsystem the agent is working in) so that Prolog rules can reason about it?

### Q6: What is the relationship between SOMA's `solve/3` backward chaining and the system_type_validator's OWL restriction checking?
system_type_validator parses OWL restrictions (someValuesFrom, minCardinality) and checks relationships against them. SOMA's MI has `solve/3` for backward chaining over Prolog rules loaded from OWL. Are these doing the same thing differently? Should system_type_validator be replaced by SOMA queries once SOMA is wired?

### Q7: The deduction chain file is in `_deprecated/`. Was it deprecated because it was wrong, or because SOMA wasn't ready to use it?
soma_deduction_chains.pl has working Prolog logic for routing partials. The y-mesh labels were wrong (commented out with explanation), but the deduction_chain_step/deduction_chain_run logic looks correct. Was the whole file deprecated, or just the y-mesh parts?

### Q8: What's the minimum SOMA MVP needed to replace system_type_validator?
Right now system_type_validator.py is a Python fast-path that blocks structural violations. What would SOMA need to have working to replace this with `solve(validate_system_type(Concept, Rels), Result)` through the MI? Is it just the 10-step plan from HANDOFF, or does it need additional rules?

### Q9: How should the annealing state be persisted?
When a Deliverable is created without tasks, that's an annealing state. Should SOMA track this as an observation? As a Prolog fact? As a CartON relationship (REQUIRES_EVOLUTION)? The current system has `is_soup` flag in the CartON queue — is annealing a different flag?

### Q10: Can SOMA precompute whether a Dragonbones EC emission is valid BEFORE it reaches CartON?
The ideal flow: agent emits EC in text → Dragonbones hook parses it → SOMA validates (is this structurally valid? is this the right starsystem? is the parent real?) → if valid, compile to CartON. If not, BLOCK with explanation. This would prevent the garbage ECs from ever reaching CartON. Is this feasible with SOMA's current architecture?
