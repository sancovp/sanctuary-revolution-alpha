#!/usr/bin/env python3
"""Simple test of the LLM Intelligence MCP functionality."""

import asyncio
import json
from pathlib import Path
from datetime import datetime

# Test the core functions directly
async def test_core_functionality():
    """Test core functionality without MCP transport."""
    
    # Mock context
    class MockContext:
        pass
    
    ctx = MockContext()
    
    # Import the functions directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from mcp_server import (
        respond, get_qa_context, list_qa_sessions, 
        complete_qa_session, read_qa_response
    )
    
    print("Testing LLM Intelligence Core Functionality\n")
    print("=" * 50)
    
    # Test 1: Create first response and verify file creation
    print("\n1. Creating first response...")
    result = await respond(
        ctx=ctx,
        qa_id="test_session",
        response_text="This demonstrates how the LLM Intelligence system works.\n\nKey insights:\n- Conversations are thinking space\n- QA files are actual responses\n- Multi-fire enables full intelligence",
        one_liner="Introduction to LLM Intelligence system",
        key_tags=["llm-intelligence", "multi-fire", "system-design"],
        involved_files=["/tmp/llm_intelligence_mcp/mcp_server.py"]
    )
    
    # Verify the response file was created
    response_file = Path(result['file'])
    assert response_file.exists(), f"Response file not created: {result['file']}"
    assert result['response_num'] == 1, f"Expected response_num 1, got {result['response_num']}"
    print(f"✓ Response file created: {response_file}")
    
    # Verify file contains expected content
    content = response_file.read_text()
    assert "Introduction to LLM Intelligence system" in content, "One-liner not in file"
    assert "llm-intelligence" in content, "Tags not in file"
    assert "This demonstrates how the LLM Intelligence system works" in content, "Response text not in file"
    print(f"✓ Response file contains expected content")
    
    # Test 2: Add second response and verify incremental response numbering
    print("\n2. Adding second response...")
    result = await respond(
        ctx=ctx,
        qa_id="test_session",
        response_text="Building on the previous explanation:\n\nImplementation details:\n1. QA_IDs track conversation threads\n2. Tags enable cross-cutting retrieval\n3. File tracking shows code involvement\n4. Context retrieval enables continuation",
        one_liner="Implementation details of the system",
        key_tags=["implementation", "tracking", "context"],
        involved_files=None
    )
    
    # Verify second response
    assert result['response_num'] == 2, f"Expected response_num 2, got {result['response_num']}"
    response_file_2 = Path(result['file'])
    assert response_file_2.exists(), f"Second response file not created: {result['file']}"
    print(f"✓ Second response file created: {response_file_2}")
    
    # Test 3: Get context and verify it returns both responses
    print("\n3. Retrieving context...")
    context = await get_qa_context(ctx, "test_session", last_n=2)
    assert context['retrieved'] == 2, f"Expected 2 responses, got {context['retrieved']}"
    assert len(context['responses']) == 2, f"Expected 2 response objects, got {len(context['responses'])}"
    assert "llm-intelligence" in context['tags'], "Expected tag not in context"
    print(f"✓ Context retrieval working correctly")
    
    # Test 4: List sessions and verify our session appears
    print("\n4. Listing sessions...")
    sessions = await list_qa_sessions(ctx)
    assert sessions['total'] >= 1, f"Expected at least 1 session, got {sessions['total']}"
    session_ids = [s['qa_id'] for s in sessions['sessions']]
    assert "test_session" in session_ids, f"test_session not found in {session_ids}"
    print(f"✓ Session listing working correctly")
    
    # Test 5: Read specific response and verify content
    print("\n5. Reading specific response...")
    response = await read_qa_response(ctx, "test_session", 1)
    assert response['response_num'] == 1, f"Expected response_num 1, got {response['response_num']}"
    assert "Introduction to LLM Intelligence system" in response['content'], "One-liner not in response"
    print(f"✓ Response reading working correctly")
    
    # Test 6: Complete session and verify summary file
    print("\n6. Completing session...")
    result = await complete_qa_session(
        ctx=ctx,
        qa_id="test_session",
        summary="Successfully tested the LLM Intelligence system core functionality"
    )
    summary_file = Path(result['summary_file'])
    assert summary_file.exists(), f"Summary file not created: {result['summary_file']}"
    summary_content = summary_file.read_text()
    assert "Successfully tested" in summary_content, "Summary content not found"
    print(f"✓ Session completion and summary file creation working")
    
    print("\n" + "=" * 50)
    print("✅ All assertions passed - LLM Intelligence system is working correctly!")
    print(f"Responses saved in: {Path('/tmp/llm_intelligence_responses/test_session/')}")

if __name__ == "__main__":
    asyncio.run(test_core_functionality())