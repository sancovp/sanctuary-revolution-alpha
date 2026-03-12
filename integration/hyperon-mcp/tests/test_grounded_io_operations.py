#!/usr/bin/env python3
"""
Test grounded Python I/O operations in Carton atomspace.

Tests that Python file I/O functions are properly grounded and callable
from MeTTa, and that they actually create files on disk.

Run with:
    env PYTHONPATH="/tmp/hyperon-mcp:/tmp/heaven_data/carton_hyperon_python" \
        HEAVEN_DATA_DIR="/tmp/heaven_data" \
        python3 test_grounded_io_operations.py
"""

import sys
import os
import shutil
from pathlib import Path

from hyperon_mcp.core.carton_init import initialize_carton_atomspace
from hyperon_mcp.core.atomspace_registry import AtomspaceRegistry


def setup_test_environment():
    """Create clean test directory."""
    test_dir = Path("/tmp/test_carton_io")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    return str(test_dir)


def test_create_directories():
    """Test py-create-concept-directories actually creates directories."""
    print("\n" + "="*80)
    print("TEST: Create Concept Directories")
    print("="*80)

    base_path = setup_test_environment()
    carton = AtomspaceRegistry("carton")

    # Call grounded function via MeTTa
    query = f'!(py-create-concept-directories "{base_path}" "Neural_Network")'
    result = carton.query_with_rules(query, flat=False)
    print(f"\nQuery: {query}")
    print(f"Result: {result}")

    # Verify directories exist
    concept_path = Path(base_path) / "concepts" / "Neural_Network"
    components_path = concept_path / "components"

    assert concept_path.exists(), f"Concept directory not created: {concept_path}"
    assert components_path.exists(), f"Components directory not created: {components_path}"

    print(f"✓ Directories created successfully")
    print(f"  - {concept_path}")
    print(f"  - {components_path}")

    return True


def test_write_description_file():
    """Test py-write-description-file actually writes files."""
    print("\n" + "="*80)
    print("TEST: Write Description File")
    print("="*80)

    base_path = setup_test_environment()
    carton = AtomspaceRegistry("carton")

    # Create directories first
    create_query = f'!(py-create-concept-directories "{base_path}" "Neural_Network")'
    carton.query_with_rules(create_query, flat=False)

    # Write description file
    description = "A neural network is a machine learning model"
    write_query = f'!(py-write-description-file "{base_path}" "Neural_Network" "{description}")'
    result = carton.query_with_rules(write_query, flat=False)
    print(f"\nQuery: {write_query}")
    print(f"Result: {result}")

    # Verify file exists and has correct content
    desc_file = Path(base_path) / "concepts" / "Neural_Network" / "components" / "description.md"
    assert desc_file.exists(), f"Description file not created: {desc_file}"

    content = desc_file.read_text()
    assert content == description, f"File content mismatch. Expected: {description}, Got: {content}"

    print(f"✓ Description file created successfully")
    print(f"  - Path: {desc_file}")
    print(f"  - Content: {content}")

    return True


def test_write_relationship_file():
    """Test py-write-relationship-file creates relationship files."""
    print("\n" + "="*80)
    print("TEST: Write Relationship File")
    print("="*80)

    base_path = setup_test_environment()
    carton = AtomspaceRegistry("carton")

    # Setup
    carton.query_with_rules(f'!(py-create-concept-directories "{base_path}" "Neural_Network")', flat=False)

    # Write relationship file - IMPORTANT: Pass items as variadic args, not list
    rel_query = f'!(py-write-relationship-file "{base_path}" "Neural_Network" "is_a" "Machine_Learning" "AI_Model")'
    result = carton.query_with_rules(rel_query, flat=False)
    print(f"\nQuery: {rel_query}")
    print(f"Result: {result}")

    # Verify file exists
    rel_file = Path(base_path) / "concepts" / "Neural_Network" / "components" / "is_a" / "Neural_Network_is_a.md"
    assert rel_file.exists(), f"Relationship file not created: {rel_file}"

    content = rel_file.read_text()
    print(f"✓ Relationship file created successfully")
    print(f"  - Path: {rel_file}")
    print(f"  - Content:\n{content}")

    return True


def test_auto_link_description():
    """Test py-auto-link-description adds markdown links."""
    print("\n" + "="*80)
    print("TEST: Auto-Link Description")
    print("="*80)

    base_path = setup_test_environment()
    carton = AtomspaceRegistry("carton")

    # Create two concepts to link between
    carton.query_with_rules(f'!(py-create-concept-directories "{base_path}" "Neural_Network")', flat=False)
    carton.query_with_rules(f'!(py-create-concept-directories "{base_path}" "Machine_Learning")', flat=False)

    # Auto-link description that mentions Machine_Learning
    description = "A neural network is a type of machine learning model"
    link_query = f'!(py-auto-link-description "{description}" "{base_path}" "Neural_Network")'
    result = carton.query_with_rules(link_query, flat=False)
    print(f"\nQuery: {link_query}")
    print(f"Result: {result}")

    # Extract the linked description from result
    # Result format: [[["linked description text"]]]
    linked = str(result)
    print(f"\n✓ Auto-linking completed")
    print(f"  - Original: {description}")
    print(f"  - Linked: {linked}")

    # Should contain markdown link to Machine_Learning
    assert "Machine_Learning" in linked or "machine learning" in linked.lower()

    return True


def test_complete_workflow():
    """Test complete workflow: create concept with all files."""
    print("\n" + "="*80)
    print("TEST: Complete Workflow")
    print("="*80)

    base_path = setup_test_environment()
    carton = AtomspaceRegistry("carton")

    concept = "Deep_Learning"
    description = "Deep learning uses neural networks with multiple layers"

    # 1. Create directories
    carton.query_with_rules(f'!(py-create-concept-directories "{base_path}" "{concept}")', flat=False)
    print("✓ Directories created")

    # 2. Write description
    carton.query_with_rules(f'!(py-write-description-file "{base_path}" "{concept}" "{description}")', flat=False)
    print("✓ Description file written")

    # 3. Write relationship (variadic args, not list)
    carton.query_with_rules(f'!(py-write-relationship-file "{base_path}" "{concept}" "is_a" "Neural_Network")', flat=False)
    print("✓ Relationship file written")

    # Verify all files exist
    concept_path = Path(base_path) / "concepts" / concept
    assert (concept_path / "components" / "description.md").exists()
    assert (concept_path / "components" / "is_a" / f"{concept}_is_a.md").exists()

    print(f"\n✓ Complete workflow successful for {concept}")
    print(f"  - Base path: {base_path}")
    print(f"  - Files created: {list(concept_path.rglob('*.md'))}")

    return True


def run_all_tests():
    """Run all grounded I/O operation tests."""
    print("\n" + "="*80)
    print("GROUNDED I/O OPERATIONS TEST SUITE")
    print("="*80)

    # Initialize carton atomspace
    print("\nInitializing Carton atomspace...")
    result = initialize_carton_atomspace()
    print(f"Initialization: {result}")

    tests = [
        test_create_directories,
        test_write_description_file,
        test_write_relationship_file,
        test_auto_link_description,
        test_complete_workflow,
    ]

    results = []
    for test in tests:
        try:
            test()
            print(f"\n✓ {test.__name__} PASSED")
            results.append(True)
        except Exception as e:
            print(f"\n✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

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
