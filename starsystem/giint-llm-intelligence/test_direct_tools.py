#!/usr/bin/env python3
"""
Direct tool call test for LLM Intelligence MCP
Tests the tools without needing an LLM
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add the package to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_use import MCPClient


async def test_llm_intelligence_mcp():
    """Test LLM Intelligence MCP tools directly using mcp-use"""
    
    # Configure the MCP server
    config = {
        "mcpServers": {
            "llm-intelligence": {
                "command": "python",
                "args": ["-m", "mcp_server"],
                "env": {
                    "LLM_INTELLIGENCE_DIR": "/tmp/llm_intelligence_responses"
                },
                "cwd": str(Path(__file__).parent)
            }
        }
    }
    
    print("Starting LLM Intelligence MCP Direct Tool Call Test")
    print(f"Working directory: {Path(__file__).parent}")
    print(f"Response directory: /tmp/llm_intelligence_responses")
    
    client = MCPClient.from_dict(config)
    
    try:
        # Initialize the session
        await client.connect()
        print("Connected to LLM Intelligence MCP server")
        
        # Get available tools
        tools = await client.list_tools()
        print(f"\nFound {len(tools.tools)} tools:")
        for t in tools.tools:
            print(f"  - {t.name}")
        
        print("\n=== Testing LLM Intelligence MCP Tools ===\n")
        
        # Test 1: Create first response
        print("Test 1: Creating first response...")
        result = await client.call_tool("respond", {
            "qa_id": "test_embedding_geometry",
            "response_text": "The embedding geometry limitation means LLMs cannot express their full intelligence in a single response.\n\nKey points:\n- Embeddings at scale have geometric constraints\n- Multiple 'fires' allow better expression\n- Systematic tracking enables intelligence to compound",
            "one_liner": "Explaining embedding geometry limitations",
            "key_tags": ["embedding-geometry", "llm-intelligence", "multi-fire"],
            "involved_files": ["/tmp/llm_intelligence_mcp/mcp_server.py"]
        })
        print(f"Response 1 created: {result}")
        
        # Test 2: Add another response building on context
        print("\nTest 2: Adding second response...")
        result = await client.call_tool("respond", {
            "qa_id": "test_embedding_geometry",
            "response_text": "Building on the previous explanation, the solution is to create systematic response patterns.\n\nImplementation:\n1. Track responses with QA_IDs\n2. Enable context retrieval\n3. Support continuation across 'fires'\n4. Separate thinking (conversation) from output (QA files)",
            "one_liner": "Solution patterns for overcoming limitations",
            "key_tags": ["solution", "patterns", "qa-system"],
            "involved_files": None
        })
        print(f"Response 2 created: {result}")
        
        # Test 3: Get context from session
        print("\nTest 3: Getting QA context...")
        context = await client.call_tool("get_qa_context", {
            "qa_id": "test_embedding_geometry",
            "last_n": 2
        })
        print(f"Context retrieved: {json.dumps(context, indent=2)}")
        
        # Test 4: List sessions
        print("\nTest 4: Listing QA sessions...")
        sessions = await client.call_tool("list_qa_sessions", {
            "tag": None
        })
        print(f"Sessions: {json.dumps(sessions, indent=2)}")
        
        # Test 5: Read specific response
        print("\nTest 5: Reading specific response...")
        response = await client.call_tool("read_qa_response", {
            "qa_id": "test_embedding_geometry",
            "response_num": 1
        })
        print(f"Response content:\n{response['content']}")
        
        # Test 6: Complete the session
        print("\nTest 6: Completing QA session...")
        complete = await client.call_tool("complete_qa_session", {
            "qa_id": "test_embedding_geometry",
            "summary": "Successfully demonstrated the LLM Intelligence system for overcoming embedding geometry limitations through systematic multi-fire responses."
        })
        print(f"Session completed: {complete}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()
        print("\nDisconnected from MCP server")


if __name__ == "__main__":
    asyncio.run(test_llm_intelligence_mcp())