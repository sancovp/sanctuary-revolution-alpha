#!/usr/bin/env python3
"""test_partials_process_event — single event with task + steps + roles +
inputs + outputs observations should trigger full process_event_partials
flow: create concept, fill all 4 primary partials, trigger template cascade."""
import json, sys, urllib.request

# TRIGGERS: SOMA Prolog daemon via HTTP POST to localhost:8091
URL = "http://localhost:8091/event"

def post(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_report(s):
    out = {}
    for tok in s.split("\n", 1)[0].split():
        if "=" in tok:
            k, v = tok.split("=", 1); out[k] = v
    return out

# Capture baseline
r0 = post({"source": "test_pep_baseline", "observations": [
    {"key": "noop", "value": "x", "type": "string_value"},
]})
f0 = parse_report(r0["result"])
baseline_partials = int(f0["partials"])
baseline_concepts = int(f0["concepts"])

# Now submit full event
r1 = post({"source": "test_pep_full", "observations": [
    {"key": "task", "value": "full_proc_target_zzz", "type": "string_value"},
    {"key": "steps", "value": "step_one,step_two", "type": "string_value"},
    {"key": "roles", "value": "worker", "type": "string_value"},
    {"key": "inputs", "value": "x,y", "type": "string_value"},
    {"key": "outputs", "value": "z", "type": "string_value"},
]})
f1 = parse_report(r1["result"])
print(f"after full event: {f1}", flush=True)

concepts_after = int(f1["concepts"])
partials_after = int(f1["partials"])
unnamed_after = int(f1["unnamed"])

# Should have at least +1 concept (the process) AND +some partials stamped
# Template cascade creates step partials (TemplateMethod ones) too, so partials grow more than 4
assert concepts_after > baseline_concepts, \
    f"FAIL: no new concept created (baseline={baseline_concepts} after={concepts_after})"
assert partials_after >= baseline_partials + 4, \
    f"FAIL: expected at least +4 partials, got +{partials_after - baseline_partials}"

print(f"concepts: {baseline_concepts} -> {concepts_after}", flush=True)
print(f"partials: {baseline_partials} -> {partials_after}", flush=True)
print("PASS: process_event_partials stamped and filled partials", flush=True)
sys.exit(0)
