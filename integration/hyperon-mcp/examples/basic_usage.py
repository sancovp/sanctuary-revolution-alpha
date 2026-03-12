#!/usr/bin/env python3
"""
Basic usage example for hyperon-mcp

Demonstrates persistent atomspace accumulation and querying.
"""

from hyperon_mcp import PersistentMeTTa, AtomspaceRegistry


def example_persistent_metta():
    """Example using PersistentMeTTa directly"""
    print("=" * 60)
    print("Example 1: Persistent MeTTa Basic Usage")
    print("=" * 60)

    metta = PersistentMeTTa("demo")

    # Add knowledge incrementally
    print("\n1. Adding facts...")
    metta.add_atom_from_string("(isa dog mammal)")
    metta.add_atom_from_string("(isa cat mammal)")
    metta.add_atom_from_string("(isa mammal animal)")

    print(f"   Atoms in space: {metta.atom_count()}")

    # Query
    print("\n2. Query: What are mammals?")
    result = metta.query("!(match &self (isa $x mammal) $x)")
    print(f"   Result: {result}")

    # Add more knowledge - persists!
    print("\n3. Adding more facts...")
    metta.add_atom_from_string("(isa bird animal)")

    # New query sees everything
    print("\n4. Query: What are animals?")
    result = metta.query("!(match &self (isa $x animal) $x)")
    print(f"   Result: {result}")

    # List all
    print("\n5. All atoms in atomspace:")
    for atom in metta.get_all_atoms():
        print(f"   - {atom}")

    # Cleanup
    metta.clear()
    print("\n✅ Atomspace cleared")


def example_registry():
    """Example using AtomspaceRegistry"""
    print("\n" + "=" * 60)
    print("Example 2: Atomspace Registry with Rules")
    print("=" * 60)

    registry = AtomspaceRegistry("rules_demo")

    # Add taxonomy
    print("\n1. Building taxonomy...")
    rules = [
        "(isa dog mammal)",
        "(isa cat mammal)",
        "(isa mammal animal)",
        "(isa bird animal)"
    ]
    result = registry.add_rules_batch(rules)
    print(f"   {result}")

    # Add inference rules
    print("\n2. Adding inference rule...")
    registry.add_rule(
        "(= (ancestor $x $z) "
        "(or (isa $x $z) "
        "(and (isa $x $y) (ancestor $y $z))))"
    )

    # Query with inference
    print("\n3. Query with inference: Is dog an animal?")
    result = registry.query_with_rules(
        "!(match &self (ancestor dog animal) True)"
    )
    print(f"   Result: {result}")

    # List all rules
    print("\n4. All rules in registry:")
    print(f"   Count: {registry.rule_count()}")

    # Cleanup
    registry.clear_all_rules()
    print("\n✅ Registry cleared")


def example_multiple_instances():
    """Example with multiple isolated instances"""
    print("\n" + "=" * 60)
    print("Example 3: Multiple Isolated Instances")
    print("=" * 60)

    # Create two separate knowledge bases
    animals = AtomspaceRegistry("animals")
    programming = AtomspaceRegistry("programming")

    # Populate animals
    print("\n1. Animals knowledge base...")
    animals.add_rules_batch([
        "(isa dog mammal)",
        "(isa cat mammal)"
    ])
    print(f"   Animals atoms: {animals.rule_count()}")

    # Populate programming
    print("\n2. Programming knowledge base...")
    programming.add_rules_batch([
        "(isa python language)",
        "(isa rust language)"
    ])
    print(f"   Programming atoms: {programming.rule_count()}")

    # Query each independently
    print("\n3. Query animals for mammals:")
    result = animals.query_with_rules("!(match &self (isa $x mammal) $x)")
    print(f"   Result: {result}")

    print("\n4. Query programming for languages:")
    result = programming.query_with_rules("!(match &self (isa $x language) $x)")
    print(f"   Result: {result}")

    # Cleanup
    animals.clear_all_rules()
    programming.clear_all_rules()
    print("\n✅ Both registries cleared")


if __name__ == "__main__":
    example_persistent_metta()
    example_registry()
    example_multiple_instances()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
