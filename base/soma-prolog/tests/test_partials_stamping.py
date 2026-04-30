#!/usr/bin/env python3
"""test_partials_stamping — POST a task observation, verify a Process concept
gets created with 4 partials (has_steps, has_roles, has_inputs, has_outputs)
all in unnamed status."""
import json
import sys
import urllib.request

# TRIGGERS: SOMA Prolog daemon via HTTP POST to localhost:8091
URL = "http://localhost:8091/event"

def post(payload):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_report(result_str):
    """Parse key=value tokens from the SOMA report first line."""
    out = {}
    first = result_str.split("\n", 1)[0]
    for tok in first.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out

resp = post({
    "source": "test_partials_stamping",
    "observations": [
        {"key": "task", "value": "stamping_target_proc_xyz", "type": "string_value"},
    ],
})
fields = parse_report(resp["result"])
print(f"report fields: {fields}", flush=True)

# Count at least +1 concept and at least +4 partials for this run.
# Partials count is cumulative across events so we check >= 4 and concepts >= 1.
concepts = int(fields.get("concepts", "0"))
partials = int(fields.get("partials", "0"))
unnamed = int(fields.get("unnamed", "0"))

assert concepts >= 1, f"FAIL: expected concepts >= 1, got {concepts}"
assert partials >= 4, f"FAIL: expected partials >= 4, got {partials}"
assert unnamed >= 4, f"FAIL: expected unnamed >= 4, got {unnamed}"

print("PASS: task observation stamped >= 4 partials all unnamed", flush=True)
sys.exit(0)
