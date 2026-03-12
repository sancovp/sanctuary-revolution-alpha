#!/usr/bin/env python3
"""
Integration test for Conversation Ingestion MCP V2

Tests full e2e workflow: Phases 1-6
Phases 7-8 (document writing, posting) skipped until 1-6 verified.
"""

import json
import os
import sys

# Add package to path
sys.path.insert(0, '/tmp/conversation_ingestion_mcp_v2')

from conversation_ingestion_mcp import core
from conversation_ingestion_mcp import utils
from conversation_ingestion_mcp.models import Registry

# Test directories
CONV_DIR = "/tmp/conversation_ingestion_openai_paiab"
STATE_FILE = f"{CONV_DIR}/state.json"
REGISTRY_FILE = f"{CONV_DIR}/canonical_registry.json"

def reset_state():
    """Reset to fresh V2 state for testing."""
    state = utils.get_empty_state_v2()
    utils.save_state(state)
    print("✓ Reset state to fresh V2 format")

def setup_registry():
    """Ensure registry has test frameworks."""
    registry = utils.load_registry()

    # Add test canonical if not exists
    if not registry.get_canonical("Test_Canonical"):
        result = core.add_canonical_framework("paiab", "reference", "Test_Canonical", "actual")
        print(f"  {result}")
    else:
        print("  Test_Canonical already in registry")

    print("✓ Registry setup complete")

def create_test_conversation():
    """Create a minimal test conversation file if needed."""
    test_conv_path = f"{CONV_DIR}/test_conversation.json"

    if not os.path.exists(test_conv_path):
        # Minimal OpenAI conversation format
        test_conv = {
            "mapping": {
                "root": {
                    "parent": None,
                    "children": ["user1"]
                },
                "user1": {
                    "parent": "root",
                    "children": ["asst1"],
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["This is test user message 1 about AI agents."]}
                    }
                },
                "asst1": {
                    "parent": "user1",
                    "children": ["user2"],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["This is test assistant response 1."]}
                    }
                },
                "user2": {
                    "parent": "asst1",
                    "children": ["asst2"],
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Test message 2 with definition logic."]}
                    }
                },
                "asst2": {
                    "parent": "user2",
                    "children": [],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Test response 2 with more content."]}
                    }
                }
            }
        }
        with open(test_conv_path, 'w') as f:
            json.dump(test_conv, f, indent=2)
        print("✓ Created test_conversation.json")
    else:
        print("✓ test_conversation.json exists")

def test_phase_1_2_3():
    """Test tagging: strata, evolving, definition, concepts."""
    print("\n" + "="*60)
    print("PHASE 1-3: Tagging")
    print("="*60)

    # Set conversation
    result = core.set_conversation("test_conversation")
    print(f"  {result}")

    # Tag pair 0: strata + evolving + definition + concept
    print("\n  Tagging pair 0 with full chain...")

    # Strata first
    result = core.tag_pair(0, "strata", "paiab")
    print(f"    strata: {result}")

    # Evolving
    result = core.tag_pair(0, "evolving")
    print(f"    evolving: {result}")

    # Definition
    result = core.tag_pair(0, "definition")
    print(f"    definition: {result}")

    # Concept tag
    result = core.add_tag(["test_concept_1", "ai_agents"])
    print(f"    add_tag: {result}")

    result = core.tag_pair(0, "concept", "test_concept_1")
    print(f"    concept: {result}")

    # Tag pair 1: just strata + evolving (no definition)
    print("\n  Tagging pair 1 with strata + evolving only...")
    result = core.tag_pair(1, "strata", "paiab")
    print(f"    strata: {result}")
    result = core.tag_pair(1, "evolving")
    print(f"    evolving: {result}")

    # Try to add concept without definition - should BLOCK
    print("\n  Testing ratcheting block (concept without definition)...")
    result = core.tag_pair(1, "concept", "should_fail")
    if "BLOCKED" in result:
        print(f"    ✓ Correctly blocked: {result[:80]}...")
    else:
        print(f"    ✗ Should have blocked! Got: {result}")
        return False

    # Check status
    print("\n  Status check:")
    result = core.status()
    for line in result.split('\n'):
        print(f"    {line}")

    return True

def test_phase_4():
    """Test emergent framework assignment."""
    print("\n" + "="*60)
    print("PHASE 4: Emergent Framework Assignment")
    print("="*60)

    # Try to assign emergent before authorization - should BLOCK
    print("\n  Testing phase gate (emergent without Phase 4 auth)...")
    result = core.tag_pair(0, "emergent_framework", "Test_Emergent")
    if "BLOCKED" in result:
        print(f"    ✓ Correctly blocked: {result[:80]}...")
    else:
        print(f"    ✗ Should have blocked! Got: {result}")
        return False

    # Create emergent framework first
    print("\n  Creating emergent framework...")
    result = core.add_or_update_emergent_framework("Test_Emergent", "paiab")
    print(f"    {result}")

    # Authorize Phase 4
    print("\n  Authorizing Phase 4...")
    result = core.authorize_next_phase("test_conversation")
    print(f"    {result}")

    # Now assign emergent to pair
    print("\n  Assigning emergent framework to pair 0...")
    result = core.tag_pair(0, "emergent_framework", "Test_Emergent")
    print(f"    {result}")

    if "BLOCKED" in result:
        print(f"    ✗ Unexpected block: {result}")
        return False

    return True

def test_phase_5():
    """Test canonical assignment to emergent."""
    print("\n" + "="*60)
    print("PHASE 5: Canonical Assignment")
    print("="*60)

    # Try to assign canonical before authorization - should BLOCK
    print("\n  Testing phase gate (canonical without Phase 5 auth)...")
    result = core.assign_canonical_to_emergent("Test_Emergent", "Test_Canonical")
    if "BLOCKED" in result:
        print(f"    ✓ Correctly blocked: {result[:80]}...")
    else:
        print(f"    ✗ Should have blocked! Got: {result}")
        return False

    # Authorize Phase 5
    print("\n  Authorizing Phase 5...")
    result = core.authorize_next_phase("test_conversation")
    print(f"    {result}")

    # Now assign canonical
    print("\n  Assigning canonical to emergent...")
    result = core.assign_canonical_to_emergent("Test_Emergent", "Test_Canonical")
    print(f"    {result}")

    if "BLOCKED" in result:
        print(f"    ✗ Unexpected block: {result}")
        return False

    # Get phase status
    print("\n  Phase status:")
    result = core.get_phase_status("test_conversation")
    for line in result.split('\n'):
        print(f"    {line}")

    return True

def test_phase_6():
    """Test publishing set and journey metadata."""
    print("\n" + "="*60)
    print("PHASE 6: Publishing Set & Journey Metadata")
    print("="*60)

    # Create publishing set
    print("\n  Creating publishing set...")
    result = core.create_publishing_set("test_publishing_set", ["test_conversation"])
    print(f"    {result}")

    # Get publishing set status
    print("\n  Publishing set status:")
    result = core.get_publishing_set_status("test_publishing_set")
    for line in result.split('\n'):
        print(f"    {line}")

    # Authorize Phase 6
    print("\n  Authorizing Phase 6...")
    result = core.authorize_publishing_set_phase("test_publishing_set")
    print(f"    {result}")

    # Set journey metadata
    print("\n  Setting journey metadata...")
    result = core.set_journey_metadata(
        "Test_Canonical",
        "The obstacle is complexity",
        "We overcome by simplifying",
        "The dream is clarity"
    )
    print(f"    {result}")

    # Get journey metadata
    print("\n  Getting journey metadata:")
    result = core.get_journey_metadata("Test_Canonical")
    for line in result.split('\n'):
        print(f"    {line}")

    return True

def test_batch_operations():
    """Test batch tag operations with coherence."""
    print("\n" + "="*60)
    print("BONUS: Batch Operations Test")
    print("="*60)

    # Reset pair 1 by adding definition + concept in coherent batch
    print("\n  Testing coherent batch [definition, concept] on pair 1...")

    # First need to add definition to pair 1
    result = core.tag_pair(1, "definition")
    print(f"    Added definition: {result}")

    # Now batch add concepts
    result = core.batch_tag_operations([
        {"action": "tag_pair", "index": 1, "tag_type": "concept", "value": "batch_concept_1"},
        {"action": "tag_pair", "index": 1, "tag_type": "concept", "value": "batch_concept_2"}
    ])
    print(f"    Batch result: {result}")

    return True

def main():
    print("="*60)
    print("CONVERSATION INGESTION MCP V2 - INTEGRATION TEST")
    print("="*60)

    # Setup
    print("\n--- SETUP ---")
    reset_state()
    setup_registry()
    create_test_conversation()

    # Run tests
    tests = [
        ("Phase 1-3 (Tagging)", test_phase_1_2_3),
        ("Phase 4 (Emergent)", test_phase_4),
        ("Phase 5 (Canonical)", test_phase_5),
        ("Phase 6 (Publishing/Journey)", test_phase_6),
        ("Batch Operations", test_batch_operations),
    ]

    results = []
    for name, test_fn in tests:
        try:
            passed = test_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  ✗ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("="*60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
