#!/usr/bin/env python3
"""Live HTTP E2E test — submits events through the actual HTTP daemon.

This tests the full user-surface path:
    curl POST /event → api.SOMAHandler.do_POST → core.ingest_event →
    janus.query_once(mi_add_event) → solve/3 → prolog_rule_add_event body →
    persist_event → kernel_derive → pellet_run → owl_save → report → HTTP 200

Assumes the daemon is already running on localhost:8091.
If not, start with: python3 -m soma_prolog.api --port 8091 &
"""
import json
import sys
import urllib.request
import urllib.error

PORT = 8091
# TRIGGERS: SOMA Prolog daemon via HTTP POST to localhost:8091
URL = f"http://localhost:{PORT}/event"

def post_event(source, observations, domain="default"):
    body = json.dumps({"source": source, "observations": observations, "domain": domain}).encode()
    req = urllib.request.Request(URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            code = resp.getcode()
            data = json.loads(resp.read().decode())
        return code, data
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return None, {"error": str(e)}

def check_404(path):
    """GET on non-/event should return 404."""
    try:
        with urllib.request.urlopen(f"http://localhost:{PORT}{path}", timeout=5) as resp:
            return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None

all_ok = True

print("=== Test 1: POST /event with non-matching observation ===", flush=True)
code, data = post_event("live_e2e", [{"key": "live_k1", "value": "live_v1", "type": "string_value"}])
print(f"  HTTP code: {code}", flush=True)
print(f"  result: {data.get('result', data)[:200]}", flush=True)
if code != 200 or "pellet=ok" not in str(data.get("result", "")):
    print("  FAIL", flush=True)
    all_ok = False
else:
    print("  PASS", flush=True)

print("\n=== Test 2: POST /event with int_value observation ===", flush=True)
code, data = post_event("live_e2e", [{"key": "live_k2", "value": 42, "type": "int_value"}])
print(f"  HTTP code: {code}", flush=True)
print(f"  result: {data.get('result', data)[:200]}", flush=True)
if code != 200 or "pellet=ok" not in str(data.get("result", "")):
    print("  FAIL", flush=True)
    all_ok = False
else:
    print("  PASS", flush=True)

print("\n=== Test 3: POST /event with multiple observations ===", flush=True)
code, data = post_event("live_e2e", [
    {"key": "multi_k1", "value": "multi_v1", "type": "string_value"},
    {"key": "multi_k2", "value": 99, "type": "int_value"},
    {"key": "multi_k3", "value": True, "type": "bool_value"},
])
print(f"  HTTP code: {code}", flush=True)
print(f"  result: {data.get('result', data)[:300]}", flush=True)
if code != 200 or "observations=3" not in str(data.get("result", "")):
    print("  FAIL — expected observations=3 in result", flush=True)
    all_ok = False
else:
    print("  PASS", flush=True)

print("\n=== Test 4: GET / should 404 ===", flush=True)
code = check_404("/")
print(f"  GET / code: {code}", flush=True)
if code != 404:
    print("  FAIL — SOMA contract violated: only POST /event should exist", flush=True)
    all_ok = False
else:
    print("  PASS", flush=True)

print("\n=== Test 5: POST /not_an_event should 404 ===", flush=True)
code, data = post_event.__self__ if False else None, None  # placeholder
import urllib.request
try:
    req = urllib.request.Request(f"http://localhost:{PORT}/not_an_event",
                                   data=b"{}", method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        code = resp.getcode()
except urllib.error.HTTPError as e:
    code = e.code
print(f"  POST /not_an_event code: {code}", flush=True)
if code != 404:
    print("  FAIL — SOMA contract violated: only POST /event should exist", flush=True)
    all_ok = False
else:
    print("  PASS", flush=True)

print("\n=== Test 6: POST /event with invalid JSON should 400 ===", flush=True)
try:
    req = urllib.request.Request(URL, data=b"this is not json", method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        code = resp.getcode()
except urllib.error.HTTPError as e:
    code = e.code
print(f"  POST /event (bad JSON) code: {code}", flush=True)
if code != 400:
    print("  FAIL — expected 400 for invalid JSON", flush=True)
    all_ok = False
else:
    print("  PASS", flush=True)

print(f"\n=== OVERALL: {'PASS' if all_ok else 'FAIL'} ===", flush=True)
sys.exit(0 if all_ok else 1)
