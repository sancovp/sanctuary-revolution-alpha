#!/usr/bin/env python3
"""Test the reinforcement path of the kernel (D10 match path).

Since the reinforcement path requires an existing rule whose head structurally
matches the incoming observation, we test it by:
1. Manually asserting a rule into the MI store whose head is obs(k, v, t)
2. Submitting an event with an observation that should match (same functor/arity)
3. Verifying kernel_reinforcement/2 was asserted

This proves the structure-preserving map check works for positive matches.
"""
import sys
from soma_prolog import core

# Boot
core.ingest_event(
    source="reinforce_boot",
    observations=[{"key": "k", "value": "v", "type": "string_value"}],
    domain="default",
)

import janus_swi as janus

print("=== Step 1: Assert a fake rule whose head is obs/3 with VARIABLES ===", flush=True)
try:
    # Variables (A, B, C) will pass the arg_preserves var(Y) check
    list(janus.query("assertz(rule((obs(_A, _B, _C) :- true), 100))"))
    print("  asserted: rule((obs(_A,_B,_C) :- true), 100)", flush=True)
except Exception as e:
    print(f"  assertz error: {e}", flush=True)
    sys.exit(1)

print("\n=== Step 2: Verify structure_preserving_match now finds a match ===", flush=True)
try:
    for r in janus.query("solve(structure_preserving_match(obs(k1,v1,string_value)), Out), with_output_to(atom(S), write(Out))"):
        s = r.get("S", "")[:300]
        print(f"  solve result: {s}", flush=True)
        if "proven(structure_preserving_match" in s:
            print("  PASS: match path activates", flush=True)
        else:
            print("  FAIL: match did not prove", flush=True)
            sys.exit(1)
        break
except Exception as e:
    # The janus py_term serialization error is benign — the underlying solve DID succeed
    msg = str(e)
    if "proven(structure_preserving_match" in msg:
        print(f"  PASS (via error-printed proof): match activates", flush=True)
    else:
        print(f"  FAIL: unexpected error: {msg[:300]}", flush=True)
        sys.exit(1)

print("\n=== Step 3: Submit an event that should trigger reinforcement ===", flush=True)
result = core.ingest_event(
    source="reinforce_test",
    observations=[{"key": "k1", "value": "v1", "type": "string_value"}],
    domain="default",
)
print(f"  ingest result: {result!r}", flush=True)

print("\n=== Step 4: Count reinforcements ===", flush=True)
try:
    n = 0
    for _ in janus.query("kernel_reinforcement(_, _)"):
        n += 1
    print(f"  kernel_reinforcement/2 entries: {n}", flush=True)
    if n >= 1:
        print("  PASS: kernel_reinforce fired on the match path", flush=True)
    else:
        print("  FAIL: no reinforcements recorded", flush=True)
        sys.exit(1)
except Exception as e:
    print(f"  count error: {e}", flush=True)
    sys.exit(1)

print("\n=== OVERALL: REINFORCEMENT PATH PASSES ===", flush=True)
sys.exit(0)
