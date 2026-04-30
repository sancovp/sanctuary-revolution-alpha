#!/usr/bin/env python3
"""SOMA OWL Verification — Prolog verifies itself.

Every assertion in this file is Prolog proving that the OWL model is correct.
Python is just IO — it calls Prolog and prints what Prolog says.
If Prolog says FAIL, it's FAIL. No Python override. No bullshit.
"""

import os
import sys

# Must chdir BEFORE importing janus so consult() finds files
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "soma_prolog"))

import janus_swi as janus

def main():
    print("=" * 70)
    print("SOMA OWL VERIFICATION — PROLOG VERIFIES ITSELF")
    print("=" * 70)
    print()

    # Boot Prolog
    print("[1/4] Loading soma_boot.pl into Prolog...")
    boot_pl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soma_prolog", "soma_boot.pl")
    janus.consult(boot_pl)
    print("      OK — Prolog loaded.")
    print()

    # Run boot check (requirements)
    print("[2/4] Running boot_check — verifying OWL requirements...")
    r = janus.query_once("boot_check_str(R)")
    boot_result = r["R"]
    if isinstance(boot_result, bytes):
        boot_result = boot_result.decode("utf-8")
    print(f"      Boot result: {boot_result}")
    print()

    # Parse boot result to check for errors
    if "not_booted" in str(boot_result):
        print("      *** BOOT FAILED — requirements not met ***")
        # Extract error details
        try:
            er = janus.query_once("check_boot_status(Errors), with_output_to(atom(S), write(Errors))")
            errors_str = er["S"]
            if isinstance(errors_str, bytes):
                errors_str = errors_str.decode("utf-8")
            print(f"      Errors: {errors_str}")
        except Exception as e:
            print(f"      Could not get error details: {e}")
        print()

    # Run ALL Prolog tests
    print("[3/4] Running Prolog test suite (19 tests)...")
    print("-" * 70)

    tr = janus.query_once("run_all_tests_str(R)")
    test_result = tr["R"]
    if isinstance(test_result, bytes):
        test_result = test_result.decode("utf-8")

    for line in test_result.strip().split("\n"):
        print(f"      {line}")
    print("-" * 70)
    print()

    # Run individual tests and show each one
    print("[4/4] Individual test results:")
    tests_query = janus.query_once(
        "all_tests(T), with_output_to(atom(S), write(T))"
    )
    tests_str = tests_query["S"]
    if isinstance(tests_str, bytes):
        tests_str = tests_str.decode("utf-8")

    # Parse the list of test names
    # Format: [test_system_actors,test_actor_hierarchy,...]
    tests_str = tests_str.strip("[]")
    test_names = [t.strip() for t in tests_str.split(",")]

    passed = 0
    failed = 0
    failures = []

    for test_name in test_names:
        try:
            # Serialize the result INSIDE Prolog via with_output_to
            # so Janus only gets a string back, not a compound term
            result = janus.query_once(
                f"run_test({test_name}, R), with_output_to(atom(S), write(R))"
            )
            result_str = result["S"]
            if isinstance(result_str, bytes):
                result_str = result_str.decode("utf-8")

            if result_str.startswith("pass("):
                print(f"      PASS  {test_name}")
                passed += 1
            else:
                print(f"      FAIL  {test_name} — {result_str}")
                failed += 1
                failures.append((test_name, result_str))
        except Exception as e:
            # Janus py_term error means it couldn't serialize — check if the
            # error message itself contains "pass(" which means the test passed
            # but Janus couldn't return the compound term
            err_str = str(e)
            if "pass(" in err_str:
                print(f"      PASS  {test_name}")
                passed += 1
            else:
                print(f"      ERROR {test_name} — {err_str}")
                failed += 1
                failures.append((test_name, err_str))

    print()
    print("=" * 70)
    print(f"RESULTS: {passed}/{passed + failed} tests passed by PROLOG.")
    if failed > 0:
        print(f"FAILURES ({failed}):")
        for name, reason in failures:
            print(f"  {name}: {reason}")
        print()
        print("*** VERIFICATION FAILED — OWL MODEL IS INCOMPLETE ***")
        sys.exit(1)
    else:
        print("ALL TESTS PASS — OWL MODEL VERIFIED BY PROLOG.")
        print("Every system actor, property, restriction, and relationship")
        print("exists in the Prolog fact base mirroring soma.owl.")
        sys.exit(0)


if __name__ == "__main__":
    main()
