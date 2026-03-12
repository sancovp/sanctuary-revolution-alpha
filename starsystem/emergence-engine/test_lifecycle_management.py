#!/usr/bin/env python3
"""
Test the lifecycle management functionality
"""

import sys
import traceback
from emergence_engine import (
    start_journey,
    get_current_state,
    get_status,
    complete_journey,
    abandon_journey
)

def test_completion_workflow(test_path):
    """Test journey completion and cleanup"""
    print("\n1. Starting journey...")
    result = start_journey("Test Domain", test_path)
    print(f"   {result}")
    
    print("\n2. Checking initial state...")
    state = get_current_state(test_path)
    print(f"   State: {state}")
    
    print("\n3. Completing journey...")
    complete_result = complete_journey(test_path)
    print(f"   {complete_result}")
    
    print("\n4. Verifying cleanup...")
    state_after = get_current_state(test_path)
    print(f"   State after cleanup: {state_after}")

def test_abandon_workflow(test_path):
    """Test journey abandonment and cleanup"""
    print("\n5. Testing abandon workflow...")
    print("   Starting new journey...")
    start_journey("Another Test Domain", test_path)
    
    print("   Abandoning journey...")
    abandon_result = abandon_journey(test_path)
    print(f"   {abandon_result}")
    
    print("\n6. Verifying abandon cleanup...")
    state_after_abandon = get_current_state(test_path)
    print(f"   State after abandon: {state_after_abandon}")

def test_lifecycle_management():
    """Test complete/abandon lifecycle management"""
    test_path = "/tmp/test_lifecycle"
    
    print("🧪 Testing 3-Pass Lifecycle Management")
    print("=" * 50)
    
    try:
        test_completion_workflow(test_path)
        test_abandon_workflow(test_path)
        print("\n✅ All lifecycle tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_lifecycle_management()
    sys.exit(0 if success else 1)