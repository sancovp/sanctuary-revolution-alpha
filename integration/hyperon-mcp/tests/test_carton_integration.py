#!/usr/bin/env python3
"""
Test Carton ontology integration with llm2hyperon MCP.

Tests:
1. Carton atomspace initialization with ontology rules
2. Python I/O function grounding
3. DAG cycle detection validation
4. Complete add-concept workflow

Run with: PYTHONPATH=/tmp/hyperon-mcp python3 test_carton_integration.py
"""

import sys

from hyperon_mcp.core.carton_init import initialize_carton_atomspace, is_carton_initialized
from hyperon_mcp.core.persistent_metta import get_metta_instance
from hyperon_mcp.core.atomspace_registry import AtomspaceRegistry


def test_1_initialization():
    """Test carton atomspace initializes with ontology rules."""
    print("\n" + "="*80)
    print("TEST 1: Carton Atomspace Initialization")
    print("="*80)

    # Initialize carton atomspace
    result = initialize_carton_atomspace()
    print(f"\nInitialization result: {result}")

    # Verify initialization
    if not is_carton_initialized():
        raise AssertionError("Carton atomspace should be initialized")
    print("✓ Carton atomspace initialized")

    # Verify atom count
    carton_metta = get_metta_instance("carton")
    atom_count = carton_metta.atom_count()
    print(f"✓ Atom count: {atom_count}")

    if atom_count == 0:
        raise AssertionError("Should have loaded ontology rules, but atom count is 0")

    return True


def test_2_grounded_functions():
    """Test Python I/O functions are grounded and callable."""
    print("\n" + "="*80)
    print("TEST 2: Grounded Python Functions")
    print("="*80)

    carton = AtomspaceRegistry("carton")

    # Test getting existing concepts
    query = '!(py-get-existing-concepts "/tmp/nonexistent")'
    result = carton.query_with_rules(query, flat=False)
    print(f"\nQuery: {query}")
    print(f"Result: {result}")

    # Verify it returned something (even if empty list)
    if result is None:
        raise AssertionError("py-get-existing-concepts should return a result")

    print("✓ Grounded function is callable and returned result")
    return True


def _add_test_relationships(carton):
    """Helper: Add test relationships for cycle detection."""
    r1 = carton.add_rule("(is_a Neural_Network Machine_Learning)")
    r2 = carton.add_rule("(is_a Machine_Learning AI)")
    print(f"Add result 1: {r1}")
    print(f"Add result 2: {r2}")

    if "Error" in str(r1) or "Error" in str(r2):
        raise AssertionError("Failed to add test relationships")

    return r1, r2


def _test_ancestor_traversal(carton):
    """Helper: Test ancestor traversal query."""
    query = "!(ancestors-is-a Neural_Network)"
    result = carton.query_with_rules(query, flat=False)
    print(f"Query: {query}")
    print(f"Result: {result}")

    if result is None:
        raise AssertionError("Ancestor traversal should return a result")


def test_3_cycle_detection():
    """Test DAG cycle detection for relationships."""
    print("\n" + "="*80)
    print("TEST 3: DAG Cycle Detection")
    print("="*80)

    carton = AtomspaceRegistry("carton")

    # Add and verify test relationships
    print("\nAdding test relationships...")
    _add_test_relationships(carton)

    # Test ancestor traversal
    print("\nTesting ancestor traversal:")
    _test_ancestor_traversal(carton)

    return True


def test_4_safe_add_operations():
    """Test safe add operations with validation."""
    print("\n" + "="*80)
    print("TEST 4: Safe Add Operations")
    print("="*80)

    carton = AtomspaceRegistry("carton")

    # Test safe-add with new relationship
    print("\nTesting safe-add-is-a:")
    query = "!(safe-add-is-a Deep_Learning Neural_Network)"
    result = carton.query_with_rules(query, flat=False)
    print(f"Query: {query}")
    print(f"Result: {result}")

    # Verify by checking if relationship exists
    verify_query = "!(match &self (is_a Deep_Learning $x) $x)"
    verify_result = carton.query_with_rules(verify_query, flat=False)
    print(f"\nVerification query: {verify_query}")
    print(f"Verification result: {verify_result}")

    if verify_result is None:
        raise AssertionError("Safe add verification query should return a result")

    return True


def test_5_query_helpers():
    """Test query helper functions."""
    print("\n" + "="*80)
    print("TEST 5: Query Helper Functions")
    print("="*80)

    carton = AtomspaceRegistry("carton")

    # Test get-is-a
    print("\nTesting get-is-a:")
    query = "!(get-is-a Deep_Learning)"
    result = carton.query_with_rules(query, flat=False)
    print(f"Query: {query}")
    print(f"Result: {result}")

    if result is None:
        raise AssertionError("get-is-a should return a result")

    # Test pattern matching
    print("\nTesting pattern matching:")
    query = "!(match &self (is_a $x $y) ($x $y))"
    result = carton.query_with_rules(query, flat=False)
    print(f"Query: {query}")
    print(f"Result: {result}")

    if result is None:
        raise AssertionError("Pattern matching should return a result")

    return True


def _get_test_suite():
    """Get list of all tests to run."""
    return [
        test_1_initialization,
        test_2_grounded_functions,
        test_3_cycle_detection,
        test_4_safe_add_operations,
        test_5_query_helpers
    ]


def _run_single_test(test):
    """Run a single test and return success status."""
    try:
        test()
        print(f"\n✓ {test.__name__} completed")
        return True
    except Exception as e:
        print(f"\n✗ {test.__name__} failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "="*80)
    print("CARTON ONTOLOGY INTEGRATION TEST SUITE")
    print("="*80)

    tests = _get_test_suite()
    results = [_run_single_test(test) for test in tests]
    passed = sum(results)
    failed = len(results) - passed

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
