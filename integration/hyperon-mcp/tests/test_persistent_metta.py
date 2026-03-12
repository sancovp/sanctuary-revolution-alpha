"""Test persistent MeTTa functionality"""

import pytest
from hyperon_mcp.core.persistent_metta import PersistentMeTTa, get_metta_instance
from hyperon_mcp.core.atomspace_registry import AtomspaceRegistry


def test_persistent_metta_basic():
    """Test basic persistent MeTTa operations"""
    metta = PersistentMeTTa("test1")

    # Add atoms
    result = metta.add_atom_from_string("(isa dog mammal)")
    assert "Total atoms: 1" in result

    result = metta.add_atom_from_string("(isa cat mammal)")
    assert "Total atoms: 2" in result

    # Check count
    assert metta.atom_count() == 2

    # Clear
    metta.clear()


def test_persistent_across_queries():
    """Test that atomspace persists across queries"""
    metta = PersistentMeTTa("test2")

    # Add rules
    metta.add_atom_from_string("(isa dog mammal)")
    metta.add_atom_from_string("(isa cat mammal)")
    metta.add_atom_from_string("(isa mammal animal)")

    # First query
    result1 = metta.query("!(match &self (isa $x mammal) $x)")
    print(f"Query 1 result: {result1}")

    # Add more atoms
    metta.add_atom_from_string("(isa bird animal)")

    # Second query should see ALL atoms
    result2 = metta.query("!(match &self (isa $x animal) $x)")
    print(f"Query 2 result: {result2}")

    assert "mammal" in result2
    assert "bird" in result2

    # Clear
    metta.clear()


def test_singleton_instances():
    """Test that get_metta_instance returns same instance"""
    instance1 = get_metta_instance("test3")
    instance2 = get_metta_instance("test3")

    assert instance1 is instance2

    instance1.add_atom_from_string("(isa dog mammal)")
    assert instance2.atom_count() == 1

    # Clear
    instance1.clear()


def test_atomspace_registry():
    """Test atomspace registry functionality"""
    registry = AtomspaceRegistry("test4")

    # Add rule
    result = registry.add_rule("(isa dog mammal)")
    assert "added" in result.lower()

    # Add batch
    rules = [
        "(isa cat mammal)",
        "(isa mammal animal)"
    ]
    result = registry.add_rules_batch(rules)
    assert "3" in result  # Should have 3 total now

    # Query
    result = registry.query_with_rules("!(match &self (isa dog $x) $x)")
    assert "mammal" in result.lower()

    # List
    all_rules = registry.get_all_rules()
    assert len(all_rules) == 3

    # Clear
    registry.clear_all_rules()


def test_multiple_registries():
    """Test isolated registry instances"""
    registry1 = AtomspaceRegistry("test5")
    registry2 = AtomspaceRegistry("test6")

    # Add to registry1
    registry1.add_rule("(isa dog mammal)")

    # Registry2 should be empty
    assert registry2.rule_count() == 0

    # Registry1 should have 1
    assert registry1.rule_count() == 1

    # Clear both
    registry1.clear_all_rules()
    registry2.clear_all_rules()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
