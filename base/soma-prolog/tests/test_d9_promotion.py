#!/usr/bin/env python3
"""Test D9: self-organizing type emergence — instance→class promotion.

Flow:
1. Boot SOMA and assert a matching rule so observations reinforce
2. Submit 1st matching observation → reinforcement count=1, no promotion
3. Submit 2nd matching observation → count=2, kernel_pattern_is_class asserted
4. Verify kernel_pattern_is_class(obs, 3) exists in the Prolog runtime
"""
import sys
from soma_prolog import core

# Boot
core.ingest_event(
    source="d9_boot",
    observations=[{"key": "k0", "value": "v0", "type": "string_value"}],
    domain="default",
)

import janus_swi as janus

print("=== Step 1: Assert matching rule (obs/3 with variables) ===", flush=True)
list(janus.query("assertz(rule((obs(_A, _B, _C) :- true), 100))"))
print("  asserted", flush=True)

print("\n=== Step 2: Submit 1st matching observation ===", flush=True)
core.ingest_event(
    source="d9_test_1",
    observations=[{"key": "kA", "value": "vA", "type": "string_value"}],
    domain="default",
)

# Count reinforcements for obs/3
n = 0
for _ in janus.query("kernel_reinforcement(_, _)"):
    n += 1
print(f"  kernel_reinforcement/2 total entries: {n}", flush=True)

# Check if promotion fact exists — should NOT yet. Use catch to handle undefined predicate.
promoted_count = 0
try:
    for _ in janus.query("catch(kernel_pattern_is_class(_, _), _, fail)"):
        promoted_count += 1
except Exception:
    pass
print(f"  kernel_pattern_is_class/2 entries after 1st: {promoted_count}", flush=True)

print("\n=== Step 3: Submit 2nd matching observation ===", flush=True)
core.ingest_event(
    source="d9_test_2",
    observations=[{"key": "kB", "value": "vB", "type": "string_value"}],
    domain="default",
)

n2 = 0
for _ in janus.query("kernel_reinforcement(_, _)"):
    n2 += 1
print(f"  kernel_reinforcement/2 total entries: {n2}", flush=True)

# Now promotion should have fired
promoted_count2 = 0
try:
    for _ in janus.query("catch(kernel_pattern_is_class(_, _), _, fail)"):
        promoted_count2 += 1
except Exception:
    pass
print(f"  kernel_pattern_is_class/2 entries after 2nd: {promoted_count2}", flush=True)

# Specifically check obs/3 got promoted
promoted_obs = 0
try:
    for _ in janus.query("catch(kernel_pattern_is_class(obs, 3), _, fail)"):
        promoted_obs += 1
except Exception:
    pass
print(f"  kernel_pattern_is_class(obs, 3) exists: {promoted_obs >= 1}", flush=True)

print("\n=== Verdict ===", flush=True)
if n2 >= 2 and promoted_obs >= 1:
    print("PASS: 2+ reinforcements triggered class promotion", flush=True)
    sys.exit(0)
else:
    print(f"FAIL: reinforcements={n2}, promoted_obs={promoted_obs}", flush=True)
    sys.exit(1)
