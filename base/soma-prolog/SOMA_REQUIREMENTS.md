# SOMA Requirements — IMMUTABLE

**DO NOT CHANGE THIS DOCUMENT. EVER.**

Written: 2026-04-18. Source: Isaac's verbatim direction across Apr 7-18 sessions.

---

## What SOMA Is

SOMA is a standalone installable base program. It is a meta-interpreter shell that accumulates an ontology from observations. It is its own daemon. It contains ZERO domain-specific content (no GIINT, no GNOSYS, no Skills, no Starsystem). Domain content enters through the caller's OWL file which SOMA loads at boot.

## The One Purpose

SOMA takes observations and progressively types them from arbitrary strings into formalized ontology. The accumulated ontology emits literal running code when a concept reaches CODE, and has full recursive deduction chains when a concept reaches ONT.

## The Three Stores

| Store | What it holds | Rule |
|---|---|---|
| OWL | CODE + ONT concepts only. Universals. Type restrictions. Rules. | NEVER holds SOUP. |
| Neo4j | EVERYTHING. Every event, every observation, every SOUP concept, every status. Particulars + history. | Reflects promotions from SOUP→CODE→ONT when they happen. |
| Prolog | Ephemeral working memory. Rules loaded from OWL at boot. Reasoning state during event processing. | Dies when process dies. Not a persistence layer. |

## The Lifecycle of a Concept

1. Observation enters. Stored in Neo4j as SOUP.
2. SOMA reads OWL: "what type is this? what does that type require?" Gets the universal structure.
3. OWL's restrictions tell SOMA what to check in Neo4j: "this type requires has_X — does this particular have it?"
4. SOMA queries Neo4j for the particular's accumulated state.
5. SOMA reasons over the combined result (universal from OWL + particular from Neo4j).
6. If observation doesn't match OWL requirements → classified as HALLUCINATION. Stays SOUP in Neo4j. Does NOT enter OWL. Does NOT get projected (no skill file, no rule file, nothing).
7. If observation matches at CODE level (all values typed, structure-preserving map admits) → OWL admits it. Neo4j updated from SOUP to CODE. Concept gets projected (skill file, rule file, whatever the type produces).
8. If observation further satisfies ONT (recursive core sentence, every subclaim verified) → OWL admits at ONT. Neo4j updated to ONT.
9. If a SOUP concept later gets more observations that complete it → SOMA re-evaluates. If it passes now → OWL admits, Neo4j evolves SOUP→CODE/ONT. Values change because it evolved.

## SOUP / CODE / ONT

- **SOUP**: The value's type is `string_value`. It is an arbitrary unverified string. SOUP exists in Neo4j ONLY. OWL rejects it. The system knows it has this thing but cannot formalize it.
- **CODE**: Every value on the concept is typed as a real type (not string_value). All required restrictions from the OWL are satisfied with correctly-typed values. The structure admits a structure-preserving map to a programming language. CODE exists in BOTH OWL and Neo4j. CODE concepts emit literal running code.
- **ONT**: CODE plus the recursive core sentence is satisfied. Every subclaim of the concept is itself ONT (recursively). Every single thing about it is atomized with full deduction chains behind it. ONT exists in BOTH OWL and Neo4j.

## Progressive Typing

Every single thing gets annealed from SOUP to CODE to ONT. If the type is `string_value`, it IS SOUP by construction. The entire system is designed on this. Each observation with a `{value, type}` pair where type is NOT string_value moves the concept closer to CODE. When no string_value remains and all restrictions are satisfied, it's CODE.

## The Core Sentence (ONT Admission)

From uarl.owl:

```
from Reality and is(Reality):
primitive_is_a IS a type of is_a → is_a embodies part_of →
part_of (as triple) entails instantiates → instantiates necessitates
produces → part_of manifests produces → produces reifies as
pattern_of_is_a → pattern_of_is_a produces programs →
programs instantiates part_of Reality
```

Every label X claims to exist by having a subgraph of triples. Every triple must be a valid primitive claim. Every primitive claim must ITSELF have a subgraph that instantiates the complete core sentence for ITS label. If ANY subclaim is SOUP, X is SOUP too. X is ONT only when every subclaim recursively has the complete core sentence shape.

## SOMA's Prolog Role

Prolog is the orchestrator. It reads OWL for universals (what should exist), queries Neo4j for particulars (what actually exists), reasons over the combined result, determines status, and emits instructions:

- "Store this in Neo4j as SOUP" → caller writes to Neo4j
- "This is CODE — admit to OWL and update Neo4j" → caller writes to OWL + Neo4j
- "This is wrong — blocked" → caller gets structured error with remedy
- "I need more info about X" → caller queries Neo4j and calls SOMA back
- "I can't deduce Y — ask an LLM/human" → caller dispatches to LLM/human

SOMA never imports CartON or Neo4j directly. They communicate via HTTP. SOMA's response tells the caller what to do. The caller has the connections and executes.

## OWL File Hierarchy

```
soma.owl (base program — universal SOMA machinery only)
  ↑ imported by
uarl.owl (YOUKNOW ontology — core sentence, derivation rules)
  ↑ imported by
starsystem.owl (GIINT hierarchy, Skills, Navy, Starsystem types)
  ↑ imported by
gnosys_foundation.owl (ships as "the program" — combines all above)
  ↑ imported by
user_domain.owl (per-user domain content)
```

SOMA loads whatever OWL file the caller points it at. It doesn't know or care which file. The PrologRule individuals, CoreRequirement individuals, class restrictions — all come from the loaded OWL. SOMA just processes them.

## What SOMA Contains (the base program)

1. **Meta-interpreter** (mi_core.pl) — solve/3 backward chaining over rule/2 facts
2. **Bootstrap loader** (soma_boot.pl) — reads PrologRule individuals from OWL, asserts as native clauses + rule/2 facts
3. **Convention rules** (soma_partials.pl) — check_convention predicates that fire over the triple graph (missing_required_restriction, transitive_is_a, DOLCE classification, progressive typing check)
4. **Codegen** (soma_compile.pl) — compile_to_python emits Pydantic BaseModel quine when concept reaches CODE + authorized
5. **CoreRequirement mechanism** — Deduction_Chain/CoreRequirement OWL individuals whose premises get checked on every event; failures produce structured errors with remedies
6. **HTTP API** (api.py) — ONE endpoint: POST /event. Everything is an event.
7. **OWL bridge** (utils.py) — py_call helpers for reading/writing OWL via owlready2
8. **Event processing** (core.py) — receives event, routes to Prolog, fires deduction chains, returns combined report
9. **DOLCE seed** — foundational ontology categories (endurant/perdurant/quality/abstract) as seed triples for automatic classification
10. **Typed observations** — tv(value, type) pattern where each related value carries its programming type, asserting both the relationship triple AND the is_a type triple

## What SOMA Does NOT Contain

- No GIINT types or restrictions
- No Skill types or restrictions
- No Starsystem types
- No CartON integration code
- No Neo4j connection code
- No GNOSYS-specific anything
- No user-domain content
- No YOUKNOW compiler logic (that's in uarl.owl / youknow_kernel)

These enter through the caller's OWL file at boot.

## TWI Meta-Rules

All Prolog rules must accord with TWI (Transformational Wisdom Intent) rules. TWI rules are the meta-rules — the rules about what rules are ALLOWED. They are the highest-priority rules in the reasoning stack. You cannot add a Prolog rule that contradicts a TWI-level rule. The system is self-protecting at the intentional level.

## Communication Protocol

SOMA is a separate HTTP daemon. CartON calls SOMA via POST /event. SOMA returns a response containing:
- Validation result (accepted / blocked / needs more info)
- Structured errors with remedies (for blocked concepts)
- Instructions for the caller (store in Neo4j, admit to OWL, query and call back, dispatch to LLM)
- Status counts (triples, unnamed_slots, compiled, SOUP/CODE/ONT breakdown)

The caller executes the instructions. SOMA never directly touches Neo4j or the caller's systems.

## Authorization + Precomputation

(Source: CartON concept `Soma_True_Definition_Apr7`)

SOMA is NOT "a Prolog daemon that stores events." The distinguishing feature is the AUTHORIZATION+PRECOMPUTATION layer: the system computes the shape of any proposed change, decides validity given everything it has ever observed, and authorizes or rejects with context.

SOMA gating its own evolution and SOMA gating what can happen in any business it is pointed at are THE SAME OPERATION — only the input observations differ. The system precomputes whether a change makes sense before allowing it. It serves you the context to make the change if authorized, or explains why not if rejected.

This applies to everything: code changes, business process observations, new rules, new types. Nothing enters SOMA without being precomputed against the accumulated observation history.

## Braindead Bootstrap Loop

(Source: CartON concept `Design_Soma_Braindead_Bootstrap_Apr06`)

SOMA starts broken. It KNOWS it is broken because it has CoreRequirements it knows aren't met. It returns structured failure errors to the caller (LLM/human) saying exactly what is wrong and how to fix it. The caller fixes what SOMA told it to fix. SOMA checks again, finds the next problem. Loop until SOMA stops complaining.

"When it starts correcting you = booted."

This is NOT a setup procedure. This IS how SOMA operates at all times. Every event goes through the same loop: check requirements → if unmet, return structured error with remedy → caller fixes → resubmit → check again. The system is always bootstrapping itself to a more correct state. The CoreRequirement mechanism (Deduction_Chain/CoreRequirement OWL individuals) is the implementation of this loop.

## Pellet's Role

Pellet is a CONSISTENCY CHECKER only. Not a reasoner. Prolog does ALL reasoning. Pellet's one job: "is this OWL file internally consistent? yes/no." Pellet runs when something is being admitted to OWL (CODE or ONT promotion). If Pellet says the OWL would be inconsistent with this new concept, the admission is rejected. That is Pellet's only job.

## What "Done" Means for SOMA MVP

SOMA MVP is done when:
1. You can POST an observation event to the daemon
2. The observation gets validated against the loaded OWL's restrictions and rules
3. If the observation has string_value types → it's SOUP → response says "SOUP, store in Neo4j only"
4. If the observation has all real types and satisfies all restrictions → it's CODE → response says "CODE, admit to OWL, update Neo4j, project outputs"
5. If the observation is provably wrong → response says "BLOCKED" with structured error and remedy
6. If SOMA needs more info → response says "NEED_INFO" with what to query and call back with
7. The OWL accumulates over time as CODE/ONT concepts get admitted
8. CODE concepts emit literal running code (Pydantic BaseModel quine registered as callable)
9. The system works with ANY OWL file — no hardcoded domain content

## What Is NOT Required for MVP

- ONT admission (recursive core sentence check) — deferred, CODE is sufficient for MVP
- Neo4j integration — the CALLER handles Neo4j based on SOMA's response instructions
- Persistence across restarts — Prolog state is ephemeral per session, OWL file on disk IS the persistence
- GNOSYS integration — that's the caller's job, not SOMA's
- YOUKNOW replacement — gradual, not MVP
