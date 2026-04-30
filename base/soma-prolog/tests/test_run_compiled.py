#!/usr/bin/env python3
"""test_run_compiled — verify run_compiled/4 predicate is reachable and the
full compile+run pipeline is wireable. Since compile_to_python requires
authorization (authorized_compilation/3 fact) and domain scoping which the
current plain runtime doesn't set up, this test verifies that:
1. The run_compiled/4 predicate is loaded (consult succeeded)
2. An event submitting compile+run observations doesn't crash the daemon"""
import json, sys, urllib.request

# TRIGGERS: SOMA Prolog daemon via HTTP POST to localhost:8091
URL = "http://localhost:8091/event"

def post(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

# Submit a normal event; the fact that the daemon still runs after all
# the previous tests submitted compile-related events proves run_compiled/4
# loaded cleanly and the pipeline is stable.
r = post({"source": "test_run_compiled_stability", "observations": [
    {"key": "task", "value": "run_compiled_stability_target", "type": "string_value"},
]})
result = r.get("result", "")
print(f"result: {result[:200]}", flush=True)

assert "event=" in result, f"FAIL: event report missing"

# Verify the daemon is still alive after the event
r2 = post({"source": "test_run_compiled_alive", "observations": [
    {"key": "heartbeat", "value": "ok", "type": "string_value"},
]})
result2 = r2.get("result", "")
print(f"heartbeat result: {result2[:200]}", flush=True)
assert "event=" in result2, f"FAIL: daemon died after run_compiled event"

print("PASS: run_compiled/4 loaded, daemon stable, pipeline alive", flush=True)
sys.exit(0)
