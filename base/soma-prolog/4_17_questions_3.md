# Questions for SOMA Agent Round 3 — 2026-04-17

## Context

We now know:
- CoreRequirement mechanism EXISTS, is WIRED, RUNS on every event
- system_type_validator.py has the Python logic for GIINT validation
- SHACL shapes dynamically read OWL restrictions
- CartON stores everything in Neo4j
- All the pieces exist separately

Isaac's question: why can't this be integrated in MINUTES? All the logic exists in Python. The mechanism exists in SOMA. Why is SOMA "not ready"? What is actually blocking the final wiring?

## Questions

### Q1: What SPECIFICALLY is stopping you from adding GIINT CoreRequirement individuals to soma.owl right now?
Not "what's the design." What is the actual technical blocker? Is it that SOMA's triple graph doesn't have GIINT concepts in it? Is it that the Prolog can't query Neo4j? Is it that the event format doesn't support it? What is the SPECIFIC thing that fails if you try to do it right now?

### Q2: If I submit an event to SOMA right now with observations about a GIINT_Component, what ACTUALLY happens?
Walk me through the exact code path. What does process_event_partials do? Does it create triples? Does it check restrictions? What's the output? Try it — actually call ingest_event with a test GIINT concept and show me the output.

### Q3: The CoreRequirement premise is a Prolog goal like "validate_giint_component_parent(X)". That Prolog rule doesn't exist. How hard is it to write it?
It checks: "for every triple(X, part_of, Y), Y must have triple(Y, is_a, giint_feature)." That's like 3 lines of Prolog. What's stopping you from writing those 3 lines as a PrologRule OWL individual and the CoreRequirement that uses it?

### Q4: Is the problem that you're confused about what Isaac wants the architecture to be?
Be honest. If you're unclear about how SOMA, YOUKNOW, and CartON are supposed to fit together, say so. Isaac said: "SOMA wraps CartON — validation happens first (SOMA/Prolog/OWL), then storage (CartON/Neo4j)." Is that clear enough to implement? If not, what's ambiguous?

### Q5: Is the problem that you're afraid of breaking the foundation-vs-contamination rule?
The rule says no domain-specific atoms in SOMA code. But CoreRequirement individuals in the OWL aren't code — they're data that enters the runtime. And the Prolog rules they reference can be PrologRule OWL individuals too. Is the contamination rule making you hesitate when you shouldn't be?

### Q6: What would a 30-minute integration look like?
Forget perfection. If you had 30 minutes to make SOMA validate GIINT hierarchy structure through CoreRequirements, what would you do? List the exact steps and files you'd touch. I want to see if this is actually simple or if there's a hidden complexity you haven't explained.

### Q7: Is the SOMA daemon actually running right now?
Can you POST to localhost:8090/event and get a response? If not, what's needed to start it? If the daemon isn't running, that's the first blocker — everything else is theoretical until the daemon is up.

### Q8: Are you overthinking this?
Seriously. We have Python code that validates GIINT types. We have SOMA that runs CoreRequirements on every event. The gap is: SOMA doesn't have GIINT CoreRequirements. Adding them is: write OWL individuals + write PrologRule individuals + done. Is there something I'm missing that makes this harder than it sounds, or are you just overthinking it?
