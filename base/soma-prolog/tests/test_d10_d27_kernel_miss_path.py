#!/usr/bin/env python3
"""Test the SOMA rule-derivation kernel (D10 + D27).

Tests:
1. SOMA boots with the new kernel rules loaded from soma.owl
2. Submitting an event with observations triggers kernel_derive
3. First observation becomes a Hallucination (no matching rule exists yet)
4. Check that kernel_hallucination/3 was asserted in the Prolog runtime

This is a unit test for the kernel wiring. It does NOT test the reinforcement
path yet because there are no matching rules for the kernel to reinforce against
on a fresh boot.
"""
import json
import sys
import traceback

def test_boot_and_ingest():
    """Submit an event and verify the kernel fires."""
    print("=== Test 1: Boot SOMA and submit an event ===", flush=True)

    try:
        from soma_prolog import core
    except Exception as e:
        print(f"FAIL: Could not import soma_prolog.core: {e}", flush=True)
        traceback.print_exc()
        return False

    try:
        result = core.ingest_event(
            source="test_kernel_d10",
            observations=[
                {"key": "test_key_alpha", "value": "test_value_alpha", "type": "string_value"},
                {"key": "test_key_beta", "value": 42, "type": "int_value"},
            ],
            domain="default",
        )
    except Exception as e:
        print(f"FAIL: ingest_event raised: {e}", flush=True)
        traceback.print_exc()
        return False

    print(f"ingest_event result: {result}", flush=True)

    # If the kernel crashed, the add_event rule would fail and the result
    # would contain an error or be empty. If it succeeded, we see the
    # standard report format.
    if result is None or result == "":
        print("FAIL: empty result from ingest_event", flush=True)
        return False

    result_str = str(result)
    if "event=" in result_str and "pellet=ok" in result_str:
        print("PASS: add_event returned the expected report format", flush=True)
        print("      -> this means persist_event + kernel_derive + pellet_run all succeeded", flush=True)
        return True
    else:
        print(f"FAIL: result does not match expected format. Got: {result_str}", flush=True)
        return False


def test_query_kernel_state():
    """Query the Prolog runtime directly to check if kernel_hallucination was asserted."""
    print("=== Test 2: Query kernel state via Janus ===", flush=True)

    try:
        import janus_swi as janus
    except Exception as e:
        print(f"FAIL: could not import janus_swi: {e}", flush=True)
        return False

    # Count hallucinations asserted — use aggregate_all which handles empty lists
    try:
        n = 0
        for _ in janus.query("kernel_hallucination(_, _, _)"):
            n += 1
    except Exception as e:
        print(f"FAIL: janus count query raised: {e}", flush=True)
        traceback.print_exc()
        return False

    print(f"kernel_hallucination/3 entries: {n}", flush=True)

    if n > 0:
        print(f"PASS: kernel_hallucination fired — kernel_derive ran and hit the miss path", flush=True)
        return True
    else:
        # Check reinforcement as fallback
        try:
            results2 = list(janus.query("findall(X, kernel_reinforcement(_EId, X), L), length(L, N)"))
            n2 = results2[0].get("N", 0) if results2 else 0
            print(f"kernel_reinforcement/2 entries: {n2}", flush=True)
            if n2 > 0:
                print(f"PASS: kernel_reinforce fired — kernel_derive ran and hit the match path", flush=True)
                return True
        except Exception:
            pass
        print("FAIL: neither kernel_hallucination nor kernel_reinforcement was asserted", flush=True)
        return False


def main():
    print("SOMA kernel D10+D27 unit test", flush=True)
    print("=" * 60, flush=True)

    t1 = test_boot_and_ingest()
    print("", flush=True)
    t2 = test_query_kernel_state()
    print("", flush=True)

    print("=" * 60, flush=True)
    print(f"Test 1 (boot + ingest):     {'PASS' if t1 else 'FAIL'}", flush=True)
    print(f"Test 2 (kernel fired):      {'PASS' if t2 else 'FAIL'}", flush=True)
    all_pass = t1 and t2
    print(f"OVERALL:                    {'PASS' if all_pass else 'FAIL'}", flush=True)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
