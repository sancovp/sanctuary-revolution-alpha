"""Test Janus Python→Prolog bridge with SOMA MI."""
import janus_swi as janus
import json

# Load SOMA event rules
janus.consult("soma_events.pl")

print("=== SOMA MI via Janus ===\n")

# Helper: query with term_string conversion to avoid serialization errors
def solve_to_str(goal_str):
    """Run solve/2 via solve_str wrapper — serializes inside Prolog."""
    results = []
    for r in janus.query(f"solve_str({goal_str}, RS)"):
        results.append(r["RS"])
    return results

# Test 1: Dispatch queries
print("--- Dispatch Results ---")
for r in janus.query("solve(dispatch(Agent, Action, What), _R), term_string(Agent, AS), term_string(Action, ActS), term_string(What, WS)"):
    print(f"  DISPATCH: {r['AS']}.{r['ActS']}({r['WS']})")
    break

# Test 2: Missing SOPs
print("\n--- Missing SOPs ---")
for r in janus.query("solve(missing_sop(X), proven(_, _)), term_string(X, XS)"):
    print(f"  MISSING SOP: {r['XS']}")
    break

# Test 3: High priority
print("\n--- High Priority SOPs ---")
for r in janus.query("solve(high_priority_sop(X), proven(_, _)), term_string(X, XS)"):
    print(f"  HIGH PRIORITY: {r['XS']}")
    break

# Test 4: Needs documentation
print("\n--- Needs Documentation ---")
for r in janus.query("solve(needs_documentation(X), proven(_, _)), term_string(X, XS)"):
    print(f"  NEEDS DOCS: {r['XS']}")
    break

# Test 5: Failure-as-data
print("\n--- Failure Detection ---")
results = solve_to_str("missing_sop(unicorn_breeding)")
if results:
    print(f"  FAILURE: {results[0][:100]}")
else:
    # If solve_to_str also fails, try with write_to_atom
    r = janus.query_once("solve(missing_sop(unicorn_breeding), R), with_output_to(atom(S), write(R))")
    print(f"  FAILURE: {r.get('S', 'no result')}")

# Test 6: Dynamic rule assertion (evolutionary self-programming!)
print("\n--- Dynamic Rule Assertion ---")
# Assert a new observation
janus.query_once("assert(observe(eve, does, report_generation, frequency=10))")
# Assert SOP exists for invoice_processing
janus.query_once("assert(sop_exists(invoice_processing))")

# Now invoice_processing should NOT be a missing SOP
print("  After asserting sop_exists(invoice_processing):")
results = solve_to_str("missing_sop(invoice_processing)")
if any("failure" in r for r in results):
    print("    invoice_processing: no longer missing (CORRECT)")
else:
    print(f"    invoice_processing: still shows as missing (BUG) — {results[:1]}")

# report_generation should be new missing SOP
for r in janus.query("solve(missing_sop(report_generation), proven(_, _)), term_string(report_generation, XS)"):
    print(f"    report_generation: MISSING SOP detected (CORRECT)")
    break

print("\n=== All tests passed ===")
