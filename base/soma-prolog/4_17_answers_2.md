# Answers to SOMA Questions Round 2 — 2026-04-17

Answering agent: GNO.SYS (Opus 4.6)
Grounded in: file reads of soma.owl lines 425-428, 967-975, 1318-1338, 1393-1402; utils.py lines 739-902; soma_partials.pl full file.

---

## A1: Did I read soma.owl when answering the first round?

No. I answered from stale memory of what I thought the code contained without re-reading. That's why the first answers were wrong. I've now read the relevant sections.

---

## A2: Does CoreRequirement model the system-type-vs-domain-concept distinction?

**Partially, but not for GIINT types specifically.**

What's there: `CoreRequirement` (line 971-975) is a subclass of `Deduction_Chain`. Three CoreRequirement individuals exist (lines 1318-1338):
- `req_can_call_llm` — checks SOMA can call the LLM
- `req_authorization_reasoning` — checks authorization vocabulary exists
- `req_failure_is_llm_call` — checks failure-error format is transmittable

Each has `hasDeductionPremise` (a Prolog goal), `hasDeductionConclusion` (assertz unmet_requirement), and `hasRequirementRemedy` (instructions for the OntologyEngineer to fix it).

How they run: `fire_all_deduction_chains_py()` in utils.py (line 799) walks every `Deduction_Chain` instance (including CoreRequirements). For each one, it calls `solve_succeeds(premise)` via janus. If the premise FAILS (requirement NOT met), it fires the conclusion (asserting `unmet_requirement`) and adds it to the fired list. Then `build_failure_error_report()` (line 868) formats the unmet requirements with their remedies into a structured error string that goes in the event response.

**This IS a "hard block with instructions" mechanism.** When a CoreRequirement fires, the response contains:
```
failure_error(unmet_core_requirements=N)
the_following_requirements_are_not_met:
  - requirement: req_X
    description: ...
    remedy: ...
this_failure_error_is_a_call_to_the_ontology_engineer.
```

**But it's not used for GIINT type validation.** The three existing CoreRequirements are about SOMA's own capabilities (can it call the LLM? does auth vocabulary exist?). There are zero CoreRequirements about GIINT hierarchy structure. To make it work for system types, you'd add CoreRequirement individuals like:
```
Individual: req_giint_component_parent_type
  type: CoreRequirement
  hasDeductionPremise: "validate_giint_component_parent(X)"
  hasDeductionConclusion: "assertz(unmet_requirement(req_giint_component_parent))"
  hasRequirementRemedy: "GIINT_Component must part_of a GIINT_Feature. Fix the part_of target."
```

Then `fire_all_deduction_chains_py` would catch GIINT structural violations the same way it catches missing LLM capability — as a hard block with remedy, not as SOUP.

**So: the mechanism exists, it's wired, it runs on every event. It just needs GIINT-specific CoreRequirement individuals added to soma.owl.**

---

## A3: Do required_restriction facts in soma_partials.pl correspond to OWL restrictions?

**They're supposed to be the same information, but they're maintained separately.**

soma_partials.pl has hardcoded facts like `required_restriction(process, has_steps, template_sequence)`. soma.owl has OWL restrictions on the Process class like `hasStep minCardinality 1` on TemplateSequence. These encode the same structural knowledge in two parallel forms.

soma_boot.pl does NOT load OWL restrictions into Prolog as required_restriction facts. The bootstrap loader (`load_prolog_rules_from_owl`) only loads `PrologRule` individuals. OWL class restrictions are a different OWL construct — they'd need a separate loader that calls `class_restrictions_snake()` from utils.py and asserts them as Prolog facts.

utils.py already has `class_restrictions_snake(class_name)` (line 478) and `list_all_restrictions_snake()` (line 492) that read OWL restrictions via owlready2. The bridge to Prolog is missing — nobody calls these and assertz's the results.

**The correct fix: add a boot-time step that reads OWL restrictions and asserts required_restriction/3 facts from them, replacing the hardcoded facts in soma_partials.pl.** Then the OWL becomes the single source of truth for type requirements.

---

## A4: Does check_convention(missing_required_restriction) produce a Dispatch?

**No.** It produces `unnamed_slot(Concept, Property, TargetType)` — a marker, not a dispatch. The marker goes into the ephemeral Prolog store. The event report includes `unnamed_slots=N` count. But there's no dispatch (no "do this to fix it"), no routing to a healer or blocker, no distinction between "hard block" and "try to heal."

The healing step (`heal_unnamed`) runs after conventions and tries ONE strategy (find a neighbor of the right type). But it's not dispatch-based — it's a single hardcoded strategy applied uniformly to all unnamed_slots.

**To get the block-vs-heal distinction: convention rules should produce different outputs for system-type violations vs domain-concept incompleteness.** Either:
- Two different dynamic facts: `structural_violation(C, P, reason)` vs `unnamed_slot(C, P, T)`
- Or route system-type failures through CoreRequirement (which already produces structured failure_errors with remedies)

---

## A5: Does soma.owl tag classes as "system types" vs "domain concepts"?

**No.** Grep for SystemType, system_type, isSystemType, DomainConcept returns zero matches. There is no property, annotation, or class in soma.owl that distinguishes system types from domain concepts.

The GIINT classes (Giint_Project, Giint_Feature, etc.) exist in uarl.owl, not soma.owl. soma.owl has Process/CodifiedProcess/ProgrammedProcess/TemplateMethod/etc. but no GIINT hierarchy.

**To add the distinction, you could:**
- Add an annotation property `isSystemType` with value `true` on GIINT classes in uarl.owl
- OR add a class `SystemType` in soma.owl and make GIINT classes subClassOf it
- OR (simplest) check programmatically: if a class is defined in uarl.owl (not user-created at runtime), it's a system type; if it was created at runtime via add_event, it's a domain concept

---

## A6: Can SHACL use different severities for system types vs domain concepts?

**Yes, in principle.** SHACL supports `sh:Violation`, `sh:Warning`, `sh:Info` severity levels. If the shapes in uarl_shapes.ttl used `sh:Violation` for system-type shapes and `sh:Warning` for generic shapes, UARLValidator could route them differently.

But this requires either:
- Separate SHACL shapes per class (not universal) — which defeats the point of the universal enforcer
- Or a SHACL property function / SPARQL filter that checks `isSystemType` annotation and sets severity accordingly

I don't know enough about the SHACL shapes to say what's easier. The universal enforcer's strength is that it reads restrictions dynamically — splitting severity would need a way to distinguish which restrictions belong to system types.

---

## A7: Could system type validation be a hasWritePrecondition?

**Yes, and the property exists.** `hasWritePrecondition` (soma.owl line 425) is defined as "A Prolog goal as a string. Must succeed for the named writer to be authorized." Domain: not restricted (no rdfs:domain). Range: xsd:string.

No individual currently uses this property — it's declared but never instantiated. But the mechanism is designed for exactly this: before an agent writes to a concept, a Prolog goal must succeed.

For GIINT types:
```xml
<owl:NamedIndividual rdf:about="#giint_component_write_precondition">
  <rdf:type rdf:resource="#WritePrecondition"/>
  <hasWritePrecondition rdf:datatype="...">validate_giint_component_parent(X)</hasWritePrecondition>
</owl:NamedIndividual>
```

**But nobody reads hasWritePrecondition at runtime.** The property exists in the OWL but no Python or Prolog code checks it. The add_event body doesn't call `check_write_preconditions`. utils.py doesn't have a `get_write_preconditions` helper. It's a declared-but-unwired mechanism.

---

## A8: What's at soma.owl lines 967-975 and how is it used?

**Lines 967-975:**
```xml
<owl:Class rdf:about="#Deduction_Chain">
  "A 'since X, maybe Y' inference rule. Premise is a Prolog goal
   whose success activates the chain. Conclusion is a Prolog goal
   that runs when the premise holds. Walked after every Pellet pass."
</owl:Class>

<owl:Class rdf:about="#CoreRequirement">
  subClassOf: Deduction_Chain
  "A Deduction_Chain about Base SOMA itself. When its premise holds
   (i.e. the requirement is NOT satisfied), its conclusion contributes
   to the failure error sent to the OntologyEngineer."
</owl:Class>
```

**Three CoreRequirement individuals exist** (lines 1318-1338): req_can_call_llm, req_authorization_reasoning, req_failure_is_llm_call.

**How it's used at runtime:**
1. `prolog_rule_add_event` body calls `fire_all_deduction_chains(Fired)` near the end
2. That resolves to `fire_all_deduction_chains_py()` in utils.py via py_call
3. `fire_all_deduction_chains_py()` iterates ALL Deduction_Chain instances (including CoreRequirements)
4. For each: runs `solve_succeeds(premise)` via janus
5. If premise FAILS → fires conclusion (assertz unmet_requirement) + adds to fired list
6. Back in the add_event body: `build_report_with_chains` counts unmet requirements
7. `build_failure_error_report()` formats the unmet list with descriptions + remedies
8. The formatted error goes in the event response

**So yes: Prolog code DOES instantiate and read CoreRequirement individuals. The pipeline is live. It runs on every event.** The three existing CoreRequirements check SOMA self-capabilities. Adding GIINT-specific CoreRequirements would extend the same mechanism to system-type validation without new code — just new OWL individuals.

---

## Summary: What already exists vs what's missing

| Mechanism | Exists? | Wired? | Used for GIINT? |
|---|---|---|---|
| CoreRequirement class + 3 individuals | YES (soma.owl 971-1338) | YES (fire_all_deduction_chains_py runs every event) | NO (only checks SOMA self-capabilities) |
| hasWritePrecondition property | YES (soma.owl 425) | NO (declared but no code reads it) | NO |
| Deduction_Chain walking | YES (utils.py 799-865) | YES (runs every event) | NO |
| Failure error formatting with remedy | YES (utils.py 868-902) | YES (build_failure_error_report) | NO |
| System type vs domain concept tagging | NO | N/A | N/A |
| OWL restriction → Prolog required_restriction bridge | NO (utils.py has readers, no assertz bridge) | N/A | N/A |
| check_convention producing block vs heal dispatch | NO (only produces unnamed_slot uniformly) | N/A | N/A |

**The shortest path to GIINT system-type blocking:**
1. Add CoreRequirement individuals to soma.owl for each GIINT structural rule (e.g. "GIINT_Component part_of must be a GIINT_Feature")
2. Add matching Prolog rules (e.g. `validate_giint_component_parent(X)`) as PrologRule individuals that check the triple graph
3. The existing fire_all_deduction_chains pipeline does the rest — fires on every event, produces structured failure_error with remedy

No new Python code, no new mechanisms. Just new OWL individuals using the existing CoreRequirement pattern.
