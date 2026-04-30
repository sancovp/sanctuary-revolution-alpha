# Follow-Up Questions for SOMA Agent — 2026-04-17 (Round 2)

## Context Update

After your first answers, we dug deeper and had an explorer read ALL the OWL files (uarl.owl, starsystem.owl, soma.owl, uarl_shapes.ttl). Here's what we found:

**The validation DOES exist.** uarl_shapes.ttl has 7 universal SHACL shapes that DYNAMICALLY read OWL restrictions via SPARQL and enforce them. The "Universal OWL Restriction Enforcer" checks someValuesFrom, the "Universal MinCardinality Enforcer" checks cardinalities. These run inside UARLValidator.validate_with_reasoning() which is called by youknow() in _compile_packet().

**The problem is not that validation doesn't exist. The problem is that the system doesn't distinguish between TWO kinds of validation failure:**

1. **System type violation** — GIINT_Component part_of Random_Thing. The OWL KNOWS what a Giint_Component must look like (partOf someValuesFrom Giint_Feature). SHACL correctly flags it. But YOUKNOW routes it to SOUP like any other incomplete concept. It should be BLOCKED — the system has complete knowledge, the concept is provably wrong, there is nothing to harvest.

2. **Domain concept incomplete** — Some_New_Idea missing partOf. This IS soup — the system doesn't know enough yet, it'll accumulate relationships over time. SOUP is correct here.

Both go through the same SHACL → YOUKNOW → "SOUP: missing X" → add_concept queues anyway pipeline. There's no branch point where system types get hard-blocked.

We added system_type_validator.py back into youknow() as a Python fast path that returns SYSTEM_TYPE_ERROR for system types, which add_concept_tool_func now raises on. But this is a parallel system to SHACL doing the same check.

**The real question: does this distinction (system type = block, domain concept = soup) already exist somewhere in SOMA's OWL or Prolog, and we just missed it?**

I'm asking because I forgot that the OWL affects the runtime — the SHACL shapes READ the OWL dynamically, so anything in the OWL is live. I may have missed something in soma.owl that already models this.

## Questions

### Q1: Did you read soma.owl when answering the first round?
Specifically, did you read the NamedIndividuals like Deduction_Chain and CoreRequirement? CoreRequirement (line 971-975) has `hasRequirementRemedy` and is described as "When SOMA's core requirements not met, emits structured failure error at OntologyEngineer. Failure error IS the LLM call." That sounds like it might be the "hard block for system types" mechanism — a CoreRequirement failure is NOT soup, it's a structured error. Did you account for this?

### Q2: Does soma.owl's CoreRequirement class model the system-type-vs-domain-concept distinction?
CoreRequirement is a subclass of Deduction_Chain. It has `hasRequirementRemedy`. If a GIINT type fails a CoreRequirement check, the remedy tells the agent exactly what's wrong and how to fix it — that's a BLOCK with instructions, not SOUP. Is this the mechanism that distinguishes "provably wrong" (system type) from "incomplete, accumulate later" (domain concept)?

### Q3: Do the required_restriction facts in soma_partials.pl correspond to OWL restrictions?
soma_partials.pl has `required_restriction(process, has_goal, goal)` etc. These are hardcoded Prolog facts. But uarl.owl has the SAME information as OWL restrictions (`someValuesFrom`). Are these supposed to be loaded FROM the OWL instead of hardcoded? Does soma_boot.pl load OWL restrictions into Prolog as required_restriction facts?

### Q4: When check_convention(missing_required_restriction) fires, does it produce a Dispatch?
If yes, what kind? Is the dispatch a "hard block" (stop, fix this) or a "heal" (try to fill automatically)? The dispatch type would tell us whether SOMA already treats these as blocks vs soup.

### Q5: Does soma.owl have any OWL axiom or individual that marks certain classes as "system types" vs "domain concepts"?
For example, is there a property like `isSystemType` or a class like `SystemType` that GIINT classes are subclasses of? Or an annotation property that tags them? The SHACL shapes are universal — they enforce ALL restrictions equally. If there's a way to tag certain classes as "hard block on violation" vs "soup on violation," that would be the missing piece.

### Q6: The SHACL "Universal OWL Restriction Enforcer" uses sh:Violation severity. Is there a way to make it use different severities for system types vs domain concepts?
If system type violations were sh:Violation (hard block) and domain concept violations were sh:Warning (soup), UARLValidator could route them differently. Does the OWL or SHACL have any mechanism for this?

### Q7: soma.owl has `hasWritePrecondition` — a Prolog goal that must succeed for authorization. Could system type validation be modeled as a write precondition?
For example: `hasWritePrecondition("validate_system_type(X)")` on Giint_Component. Before any agent writes to Giint_Component, the Prolog goal must succeed. This would make SOMA the gatekeeper for system types. Is this architecturally correct?

### Q8: Please re-read soma.owl lines 967-975 (Deduction_Chain and CoreRequirement) and tell me exactly what's there and how it's used by the runtime.
I need to know: does any Prolog code currently instantiate CoreRequirement individuals? Does anything read hasDeductionPremise/hasDeductionConclusion? Or are these OWL class definitions that nothing uses yet?
