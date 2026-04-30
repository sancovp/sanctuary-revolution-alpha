#!/usr/bin/env python3
"""test_partials_status — verify the report exposes the soup/code distinction:
a freshly-stamped task has unnamed > 0 (SOUP)."""
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

r = post({"source": "test_status", "observations": [
    {"key": "task", "value": "status_target_proc_qqq", "type": "string_value"},
]})
f = parse_report(r["result"])
print(f"report: {f}", flush=True)

unnamed = int(f["unnamed"])
partials = int(f["partials"])
assert unnamed > 0, f"FAIL: fresh process should have unnamed partials, got {unnamed}"
assert partials >= unnamed, f"FAIL: partials ({partials}) should >= unnamed ({unnamed})"

# SOUP = has unnamed partials. Confirm by presence.
print(f"soup_status: concept has {unnamed} unnamed partials → SOUP", flush=True)
print("PASS: fresh process is at SOUP layer (has unnamed partials)", flush=True)
sys.exit(0)
