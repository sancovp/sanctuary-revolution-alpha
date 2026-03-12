#!/usr/bin/env python3
"""Test the LLM Intelligence MCP server."""

import asyncio
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import (
    respond, get_qa_context, list_qa_sessions, 
    complete_qa_session, read_qa_response
)

class MockContext:
    """Mock context for testing."""
    pass

async def test_llm_intelligence():
    """Test the LLM Intelligence workflow."""
    ctx = MockContext()
    
    # Test creating a new QA session with response
    print("Creating first response...")
    result = await respond(
        ctx=ctx,
        qa_id="test_session_001",
        response_text="This is the actual response content that would be shown to the user.\n\nIt contains the structured, final answer.",
        one_liner="Test response demonstrating QA system",
        key_tags=["test", "llm-intelligence", "embedding-geometry"],
        involved_files=["/tmp/llm_intelligence_mcp/mcp_server.py"]
    )
    print(f"Response 1: {result}\n")
    
    # Add another response to same session
    print("Adding second response...")
    result = await respond(
        ctx=ctx,
        qa_id="test_session_001",
        response_text="This is a follow-up response building on the previous context.\n\nIt demonstrates multi-fire intelligence.",
        one_liner="Follow-up response with context",
        key_tags=["multi-fire", "context-building"],
        involved_files=None
    )
    print(f"Response 2: {result}\n")
    
    # Get context from session
    print("Getting QA context...")
    context = await get_qa_context(ctx, "test_session_001", last_n=2)
    print(f"Context: {context}\n")
    
    # List sessions
    print("Listing QA sessions...")
    sessions = await list_qa_sessions(ctx)
    print(f"Sessions: {sessions}\n")
    
    # Complete the session
    print("Completing QA session...")
    complete = await complete_qa_session(
        ctx=ctx,
        qa_id="test_session_001",
        summary="Demonstrated the LLM Intelligence system for overcoming embedding geometry limitations through multi-fire responses."
    )
    print(f"Completed: {complete}\n")
    
    # Read a specific response
    print("Reading specific response...")
    response = await read_qa_response(ctx, "test_session_001", 1)
    print(f"Response content:\n{response['content']}\n")
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_llm_intelligence())