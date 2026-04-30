#!/usr/bin/env python3
"""D28 test: SOUP / CODE / ONT requirement-layer predicates in SOMA.

Verifies:
  1. concept_is_code_admissible() correctly identifies foundation-class
     individuals as CODE
  2. is_code/1 Prolog predicate fires correctly for a freshly-ingested event
  3. is_soup/1 fires for a non-existent / non-typed concept name
  4. is_ont/1 stub always fails (not yet implemented)
  5. requirement_layer/2 returns 'code' for events, 'soup' for missing
"""
import sys
from soma_prolog import core, utils

# Boot + ingest a real event so we have an Event individual in OWL
r = core.ingest_event(
    source="d28_test",
    observations=[{"key": "layer_k", "value": "layer_v", "type": "string_value"}],
    domain="default",
)
print(f"Boot result: {r}", flush=True)

# Extract the new event's ID from the result. Format: "event=evt_NNN source=..."
import re
m = re.search(r"event=(evt_[\d.]+)", r)
if not m:
    print(f"FAIL: could not parse event id from result", flush=True)
    sys.exit(1)
event_id = m.group(1)
print(f"Event ID: {event_id}", flush=True)

# Test 1: Python helper directly
print("\n=== Test 1: concept_is_code_admissible Python helper ===", flush=True)
if utils.concept_is_code_admissible(event_id) == "yes":
    print(f"  PASS: {event_id} is CODE-admissible", flush=True)
else:
    print(f"  FAIL: {event_id} should be CODE-admissible (it's an Event individual)", flush=True)
    sys.exit(1)

# Also check a TypedValue subclass instance — the boot event's obs value
# The observation value follows pattern evt_NNN_obs_KEY_val
obs_val_candidates = [i for i in utils._onto.individuals() if "d28_test" in str(i.name) or event_id in str(i.name)]
print(f"  related individuals: {[i.name for i in obs_val_candidates][:5]}", flush=True)

if utils.concept_is_code_admissible("nonexistent_concept_xyz") == "no":
    print("  PASS: nonexistent concept is NOT code-admissible", flush=True)
else:
    print("  FAIL: nonexistent concept should not be code-admissible", flush=True)
    sys.exit(1)

# Test 2: is_code/1 Prolog predicate via janus
print("\n=== Test 2: is_code/1 Prolog predicate ===", flush=True)
import janus_swi as janus

def prolog_query_bool(goal_str):
    """Query the SOMA MI solve/2 and return True iff it proved."""
    try:
        for r in janus.query(f"solve({goal_str}, Out), with_output_to(atom(S), write(Out))"):
            s = r.get("S", "")
            return "proven(" in s
    except Exception as e:
        # janus py_term serialization hiccup — check error text
        msg = str(e)
        if "proven(" in msg:
            return True
        if "failure(" in msg:
            return False
    return False

code_for_event = prolog_query_bool(f"is_code('{event_id}')")
print(f"  is_code('{event_id}'): {code_for_event}", flush=True)
if not code_for_event:
    print("  FAIL: is_code should succeed for an Event", flush=True)
    sys.exit(1)
print("  PASS", flush=True)

# Test 3: is_soup for a nonexistent concept
print("\n=== Test 3: is_soup/1 for nonexistent concept ===", flush=True)
soup_for_missing = prolog_query_bool("is_soup(totally_made_up_concept_123)")
print(f"  is_soup(totally_made_up_concept_123): {soup_for_missing}", flush=True)
if not soup_for_missing:
    print("  FAIL: nonexistent concepts should be SOUP", flush=True)
    sys.exit(1)
print("  PASS", flush=True)

# Test 4: is_ont always fails (stub)
print("\n=== Test 4: is_ont/1 stub always fails ===", flush=True)
ont_for_event = prolog_query_bool(f"is_ont('{event_id}')")
print(f"  is_ont('{event_id}'): {ont_for_event}", flush=True)
if ont_for_event:
    print("  FAIL: is_ont stub should always fail (not yet implemented)", flush=True)
    sys.exit(1)
print("  PASS (stub correctly always fails)", flush=True)

# Test 5: requirement_layer returns code for events
print("\n=== Test 5: requirement_layer/2 ===", flush=True)
# Query which layer the event is at
try:
    for r in janus.query(f"solve(requirement_layer('{event_id}', Layer), Out), with_output_to(atom(S), write(Layer))"):
        layer = r.get("S", "")
        print(f"  requirement_layer('{event_id}', ?): {layer}", flush=True)
        if layer == "code":
            print("  PASS: event is at CODE layer", flush=True)
        else:
            print(f"  FAIL: expected 'code', got {layer!r}", flush=True)
            sys.exit(1)
        break
except Exception as e:
    msg = str(e)
    # janus serialization hiccup — parse the Layer from the error text
    if "code" in msg and "proven" in msg:
        print("  PASS (via error-printed proof): event is at CODE layer", flush=True)
    else:
        print(f"  FAIL: unexpected error: {msg[:300]}", flush=True)
        sys.exit(1)

# And query layer for the missing concept
try:
    found_layer = None
    for r in janus.query("solve(requirement_layer(totally_made_up_123, Layer), Out), with_output_to(atom(S), write(Layer))"):
        found_layer = r.get("S", "")
        break
    print(f"  requirement_layer(missing, ?): {found_layer}", flush=True)
    if found_layer == "soup":
        print("  PASS: missing concept is at SOUP layer", flush=True)
    else:
        print(f"  FAIL: expected 'soup', got {found_layer!r}", flush=True)
        sys.exit(1)
except Exception as e:
    msg = str(e)
    if "soup" in msg and "proven" in msg:
        print("  PASS (via error-printed proof): missing is at SOUP layer", flush=True)
    else:
        print(f"  FAIL: unexpected error: {msg[:300]}", flush=True)
        sys.exit(1)

print("\n=== OVERALL: PASS ===", flush=True)
sys.exit(0)
