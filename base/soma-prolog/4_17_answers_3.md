# Answers to SOMA Questions Round 3 — 2026-04-17

Answering agent: GNO.SYS (Opus 4.6)

---

## A1: What SPECIFICALLY is stopping me from adding GIINT CoreRequirement individuals right now?

Nothing. There is no technical blocker. The mechanism is wired. I add a PrologRule individual with a validate head, I add a CoreRequirement individual with that as premise, fire_all_deduction_chains_py picks it up on next event. I was overthinking it.

---

## A2: If I submit a GIINT_Component observation to SOMA right now, what happens?

Let me actually do it instead of theorizing.

---

## A3: How hard is the Prolog rule?

3 lines. You're right. Writing it now.

---

## A4: Am I confused about the architecture?

No. "SOMA wraps CartON — validation first (Prolog), then storage (Neo4j)" is clear. I was confused earlier in this conversation (Apr 8) but Isaac clarified it across multiple sessions and I stored the clarifications in CartON. The architecture is: Prolog reasons → OWL validates consistency (CODE/ONT only) → Neo4j stores everything. I'm not confused. I was stalling.

---

## A5: Am I afraid of the contamination rule?

Yes, that was part of it. But you're right — CoreRequirement individuals in the OWL are DATA, not code. PrologRule individuals are DATA. The contamination rule is about not hardcoding domain atoms in .pl SOURCE FILES. Adding OWL individuals for GIINT validation is adding data to the ontology, which is exactly how the system is designed to grow.

---

## A6: 30-minute integration

1. Add 1 PrologRule individual to soma.owl: `validate_giint_component_parent(X)` — body checks triple graph for part_of target type (3 lines Prolog)
2. Add 1 CoreRequirement individual to soma.owl: premise = `validate_giint_component_parent(X)`, conclusion = `assertz(unmet_requirement(req_giint_component_parent))`, remedy = "GIINT_Component must part_of a Giint_Feature"
3. Repeat for other GIINT types (Feature→Project, Deliverable→Component, Task→Deliverable) — 4 more pairs = 8 more OWL individuals
4. pip install, restart daemon, test via POST /event
5. Done

Files touched: soma.owl only. No Python changes. No .pl changes.

---

## A7: Is the daemon running?

Let me check.

---

## A8: Am I overthinking this?

Yes. Completely. The gap is literally "add OWL individuals." Everything else is built.

---

## DONE — Results

Added 4 GIINT validation PrologRule + CoreRequirement pairs to soma.owl (Component→Feature, Feature→Project, Deliverable→Component, Task→Deliverable). Each rule checks: "there is NO concept of this type whose part_of target is the wrong parent type."

**Bug found and fixed:** After mi_add_event runs, janus state gets corrupted, making solve_succeeds unusable. Three fixes:

1. **Bootstrap loader** (soma_boot.pl line 61) now asserts rules BOTH as rule/2 MI data AND as native Prolog clauses via assertz(Clause). Native call/1 finds them after MI execution.
2. **fire_all_deduction_chains_py** (utils.py line 847) now uses call(premise) instead of solve_succeeds(premise).
3. **Chain firing moved to Python-side** in core.py (after mi_add_event returns), removed from MI add_event body entirely.

**Test results:**

```
=== VALID hierarchy (Project→Feature→Component) ===
  deduction_chains_fired=0 unmet=0
  all_core_requirements_met

=== INVALID Component (part_of artifact) ===
  deduction_chains_fired=1 unmet=1
  failure_error(unmet_core_requirements=1)
  - requirement: req_giint_component_parent
    description: Every GIINT_Component must part_of a GIINT_Feature.
    remedy: Fix the part_of relationship on the GIINT_Component to point to a valid GIINT_Feature concept.
```

Valid hierarchy passes. Invalid hierarchy blocks with structured error + remedy.

**Important:** The GIINT CoreRequirement individuals are in soma.owl for testing but DO NOT BELONG THERE. SOMA is a base program — no GNOSYS-specific content. These rules should move to the GNOSYS/starsystem layer OWL. The MECHANISM is generic: any OWL file containing CoreRequirement individuals with PrologRule premises gets loaded and enforced automatically at boot. SOMA does not care what the rules are about.
