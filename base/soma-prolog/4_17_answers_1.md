# Answers to SOMA Questions — 2026-04-17 (Grounded in Code)

Answering agent: GNO.SYS (Opus 4.6)
Grounded in: actual file reads of soma_partials.pl, soma_compile.pl, soma_boot.pl, soma.owl, utils.py as they exist on disk right now. NOT referencing unimplemented design ideas.

---

## A1: Does soma_deduction_chains.pl model the three-state distinction?

**No.** soma_deduction_chains.pl is still in `_deprecated/` and is NOT consulted by soma_boot.pl. It is not part of the running system.

What IS running (soma_partials.pl) has TWO states, not three:
- `unnamed_slot(C, Prop, TargetType)` = something is missing
- No unnamed_slot = complete

There is no "annealing" state in the code. The `deduce_validation_status/2` predicate (line 204-210) returns:
- `code` if concept has is_a triple AND zero unnamed_slots
- `soup` if concept has is_a triple AND any unnamed_slots
- `unvalidated` if concept has no is_a triple at all

Your three-state model (HARD BLOCK / ANNEALING / COMPLETE) does not exist in the current code. To add it, you'd need a third status and a way to tag unnamed_slots as "expected-incomplete" vs "actually-wrong."

---

## A2: How does backwards reasoning handle incremental GIINT creation?

**It doesn't.** The current SOMA does NOT do backwards reasoning over GIINT concepts.

What happens now: when an observation enters via `process_event_partials/1` (line 227), it:
1. Asserts triples into the graph
2. Runs `check_convention(missing_required_restriction)` which checks: for every `triple(C, is_a, T)`, does every `required_restriction(T, Prop, _)` have a matching `triple(C, Prop, _)`? If not → `unnamed_slot`.
3. Runs `heal_unnamed` which tries ONE strategy: find a neighbor of C that has the right type (line 189-198). That's it.

There is no `solve/3` backward chaining integrated into the partials flow. The MI's `solve/3` (in mi_core.pl) exists and works for PrologRule individuals loaded from soma.owl, but `process_event_partials` does NOT call `solve/3`. It uses direct Prolog predicates (`check_convention`, `heal_unnamed`).

So when a Deliverable is created without tasks, `check_convention(missing_required_restriction)` would mark `unnamed_slot(Deliverable_X, hasTask, giint_task)` — and that's it. No reasoning about whether that's expected or wrong.

---

## A3: Where does BUILD phase knowledge live?

**Nowhere in the current code.** There is no concept of "build-time relationship" vs "planning-time requirement" in soma_partials.pl. Every `required_restriction` is treated the same — if it's missing, it's an unnamed_slot. Period.

To add this, you'd need something like:
```prolog
:- dynamic build_time_relationship/3.
build_time_relationship(giint_deliverable, hasTask, giint_task).
```
And modify `check_convention(missing_required_restriction)` to skip unnamed_slot emission when the missing restriction is declared build-time. This does not exist yet.

---

## A4: How should SOMA distinguish "wrong" from "incomplete"?

**Currently it doesn't.** The convention rule `check_convention(missing_required_restriction)` (line 129-136) only checks for ABSENCE — `\+ triple(C, Prop, _)`. It does NOT check whether an existing triple has the WRONG type.

So right now:
- `GIINT_Component_X part_of Random_Thing` where Random_Thing is wrong type → NOT CAUGHT. The convention rule only checks if `part_of` exists at all, not whether its value is the right type.
- `GIINT_Deliverable_X` missing `hasTask` → caught as `unnamed_slot`.

Both "wrong" and "missing" are treated the same way or not caught at all. A structural violation check would need to be a NEW convention rule:
```prolog
check_convention(structural_type_mismatch) :-
    forall(
        (   triple(C, Prop, Target),
            required_restriction(Type, Prop, ExpectedType),
            triple(C, is_a, Type),
            \+ triple(Target, is_a, ExpectedType)
        ),
        assert_structural_violation(C, Prop, Target, ExpectedType)
    ).
```
This does not exist in the code.

---

## A5: Should OMNISANC inference live in SOMA?

**Can't answer from the code.** SOMA currently has no connection to OMNISANC. The `_infer_from_context` function in system_type_validator.py reads a file on disk. SOMA's triple graph has no concept of "current starsystem" or "agent context."

Whether it SHOULD live in SOMA is a design question, not answerable from reading the code. What I can say: SOMA's triple graph CAN store any fact including agent context, and convention rules CAN reason over it. But none of that wiring exists.

---

## A6: Relationship between solve/3 and system_type_validator

**They are separate systems that do not interact.**

- `system_type_validator.py` = Python code in the YOUKNOW package that reads OWL restrictions via owlready2 and checks relationships against them. Lives in `/home/GOD/gnosys-plugin-v2/base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/system_type_validator.py`.
- `solve/3` = Prolog backward chaining in `mi_core.pl` over rules loaded from soma.owl PrologRule individuals. Lives in `/home/GOD/gnosys-plugin-v2/base/soma-prolog/soma_prolog/mi_core.pl`.

system_type_validator is called by YOUKNOW during `youknow()` validation. SOMA's `solve/3` is called during `add_event` processing. They don't know about each other.

The convention rules in soma_partials.pl (`check_convention(missing_required_restriction)`) do something SIMILAR to what system_type_validator does — check required properties against what exists — but they operate on SOMA's triple graph, not on CartON's Neo4j graph or OWL restrictions. They're parallel implementations of the same idea in different stores.

---

## A7: Why was soma_deduction_chains.pl deprecated?

**I don't know from the code alone.** The file is in `_deprecated/` with no README explaining why. The decision doc (SOMA_CARTON_MERGE_DECISIONS_2026_04_07.md) says the deprecated files were "quarantined" and later described as having domain-specific hardcoded atoms mixed with universal mechanisms. But I cannot verify whether the deduction_chain_step/run logic is correct without running it, and it's not wired into anything.

---

## A8: Minimum SOMA MVP to replace system_type_validator

What EXISTS now that's relevant:
- `check_convention(missing_required_restriction)` — checks required properties exist. Similar to system_type_validator's completeness check.
- `required_restriction/3` seed facts — defines what process/template_method/etc need. But NO required_restrictions for GIINT types (giint_project, giint_feature, giint_component, giint_deliverable, giint_task).
- `triple/3` graph — can store any facts. But has NO connection to CartON's Neo4j where GIINT concepts actually live.

What's MISSING to replace system_type_validator:
1. **GIINT required_restrictions** — `required_restriction(giint_deliverable, part_of, giint_component)` etc. None exist in soma_partials.pl.
2. **Structural type-mismatch check** — convention rule that catches WRONG parent type, not just missing parent. Does not exist (see A4).
3. **Prolog↔Neo4j bridge** — Prolog can't query "does GIINT_Feature_X exist in CartON?" No py_call helper for Neo4j queries exists in utils.py.
4. **Starsystem context** — no way for Prolog to know what starsystem the agent is in.
5. **Integration point** — Dragonbones currently calls CartON directly. No hook to route through SOMA first.

That's 5 missing pieces. The 10-step plan from HANDOFF (D6) is about SOMA's base wiring which IS done. The validation use-case needs additional work on top.

---

## A9: How should annealing state be persisted?

**Current code has no persistence for ANY Prolog state.** `triple/3`, `unnamed_slot/3`, `compiled_program/2` — all live as Prolog dynamic facts that vanish when the process dies. D11 in the decision doc says "Prolog is ephemeral, state lives in Neo4j" but that Neo4j relay does NOT exist in the code.

So "how to persist annealing" is currently the same question as "how to persist anything" — and the answer is: it's not implemented. Everything in the Prolog runtime is ephemeral right now.

The decision doc says Neo4j is the persistence target. The `owl_save` call in `prolog_rule_add_event` persists OWL individuals to the soma.owl file, but that's only Event/Observation individuals — not triples, not unnamed_slots, not validation status.

---

## A10: Can SOMA prevalidate Dragonbones ECs before CartON?

**Not currently wired, but the mechanism exists in pieces.**

What exists:
- SOMA accepts events via POST /event (or in-process via `core.ingest_event`)
- Convention rules run on every event and produce unnamed_slots
- The response includes `triples=N unnamed_slots=M` counts

What doesn't exist:
- Dragonbones doesn't route through SOMA — it calls CartON's `add_concept` directly
- No convention rule checks GIINT structural validity (wrong parent type, wrong starsystem)
- No structured error message format for "why this EC is invalid"
- No Prolog↔Neo4j bridge to check if referenced parent concepts actually exist

The architecture COULD support it: Dragonbones parses EC → calls SOMA → SOMA runs convention rules → if unnamed_slots or structural violations exist → block with explanation → else route to CartON. But every piece of that chain after "calls SOMA" needs to be built.
