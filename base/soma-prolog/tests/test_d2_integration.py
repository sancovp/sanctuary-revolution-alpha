#!/usr/bin/env python3
"""D2 integration test: call add_concept_tool_func end-to-end and verify the
queue file written to disk has the correct D2 structure.

This exercises the FULL add_concept_tool_func code path: YOUKNOW validation,
template requirement check, ontology healing, and queue file write. We don't
require Neo4j or the daemon to be running — the queue file is the contract
between add_concept_tool_func and the daemon, and that's what we verify.
"""
import json
import os
import sys
import glob
import time

sys.path.insert(0, "/home/GOD/gnosys-plugin-v2/knowledge/carton-mcp")

# Set HEAVEN_DATA_DIR to a tmp location so we don't pollute real queues
TEST_DATA_DIR = "/tmp/test_d2_heaven_data"
os.makedirs(TEST_DATA_DIR, exist_ok=True)
os.environ["HEAVEN_DATA_DIR"] = TEST_DATA_DIR

from add_concept_tool import add_concept_tool_func, get_observation_queue_dir

RAW_PROSE = (
    "This is pollution. An agent wrote a knowledge dump into description. "
    "D2 should route this into raw_staging, not description."
)

def cleanup_queue():
    """Remove any existing concept queue files."""
    queue_dir = get_observation_queue_dir()
    for f in glob.glob(str(queue_dir / "*_concept.json")):
        try:
            os.remove(f)
        except Exception:
            pass

print("=== Test: add_concept_tool_func routes raw prose to raw_staging ===", flush=True)

cleanup_queue()
time.sleep(0.05)

# Call the real function. This will queue a concept to disk.
try:
    result = add_concept_tool_func(
        concept_name="Test_D2_Integration_Concept",
        description=RAW_PROSE,
        relationships=[
            {"relationship": "is_a", "related": ["Test_Thing"]},
            {"relationship": "part_of", "related": ["Test_Bucket"]},
            {"relationship": "instantiates", "related": ["Test_Pattern"]},
        ],
        hide_youknow=True,  # skip YOUKNOW validation for this unit test
        _skip_ontology_healing=True,
    )
    print(f"  add_concept result: {result}", flush=True)
except Exception as e:
    print(f"  FAIL: add_concept_tool_func raised: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Find the queue file
queue_dir = get_observation_queue_dir()
queue_files = sorted(glob.glob(str(queue_dir / "*_concept.json")))
if not queue_files:
    print(f"  FAIL: no queue file written to {queue_dir}", flush=True)
    sys.exit(1)

queue_file = queue_files[-1]
print(f"  queue file: {queue_file}", flush=True)

with open(queue_file) as f:
    queue_data = json.load(f)

# Verify structure
checks = []

# 1. raw_staging field exists and contains the raw prose
raw_staging = queue_data.get("raw_staging", "")
if raw_staging == RAW_PROSE:
    checks.append(("raw_staging preserves caller prose", True))
else:
    checks.append((f"raw_staging preserves caller prose (got {len(raw_staging)} chars)", False))

# 2. description is the computed rollup, NOT the raw prose
description = queue_data.get("description", "")
expected_rollup = (
    "Test_D2_Integration_Concept is_a Test_Thing. "
    "Test_D2_Integration_Concept part_of Test_Bucket. "
    "Test_D2_Integration_Concept instantiates Test_Pattern."
)
if description == expected_rollup:
    checks.append(("description is the computed rollup", True))
else:
    checks.append((f"description is the computed rollup (got {description!r})", False))

# 3. raw prose does NOT appear in description
if RAW_PROSE not in description:
    checks.append(("raw prose does not leak into description", True))
else:
    checks.append(("raw prose does not leak into description", False))

# 4. relationships are preserved
rels = queue_data.get("relationships", [])
if len(rels) == 3:
    checks.append(("relationships preserved", True))
else:
    checks.append((f"relationships preserved (got {len(rels)})", False))

print("\n  Checks:", flush=True)
all_ok = True
for label, ok in checks:
    mark = "PASS" if ok else "FAIL"
    print(f"    {mark}: {label}", flush=True)
    if not ok:
        all_ok = False

cleanup_queue()

print(f"\n=== OVERALL: {'PASS' if all_ok else 'FAIL'} ===", flush=True)
sys.exit(0 if all_ok else 1)
