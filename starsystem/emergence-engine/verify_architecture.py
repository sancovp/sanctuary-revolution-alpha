#!/usr/bin/env python3
"""
Verify clean architecture refactor
"""

import sys
import traceback
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_business_logic_in_library():
    """Verify business logic moved to library"""
    logger.info("Testing business logic in library")
    from emergence_engine import get_contextual_prompt
    prompt = get_contextual_prompt(1, 0, 'Test')
    assert len(prompt) > 50, f'Prompt too short: {len(prompt)}'
    assert 'Abstract Goal - Pass 1' in prompt, 'Missing expected content'
    logger.info(f"Business logic verification passed: {len(prompt)} chars")
    print(f"✅ Business logic in library: {len(prompt)} chars")

def verify_mcp_clean_import():
    """Verify MCP has no business logic"""
    logger.info("Testing MCP clean import")
    import mcp_server
    assert not hasattr(mcp_server, 'PhasePrompts'), 'PhasePrompts still in MCP!'
    logger.info("MCP clean import verification passed")
    print("✅ MCP is clean wrapper")

def verify_functionality():
    """Verify functionality still works"""
    logger.info("Testing functionality preservation")
    from emergence_engine import start_journey, complete_journey
    start_journey('Architecture Test', '/tmp/verify_test')
    result = complete_journey('/tmp/verify_test')
    assert 'completed and cleaned up' in result, f'Unexpected result: {result}'
    logger.info("Functionality verification passed")
    print("✅ Functionality preserved")

if __name__ == "__main__":
    try:
        verify_business_logic_in_library()
        verify_mcp_clean_import()
        verify_functionality()
        print("\n🎯 Clean architecture verification completed")
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)