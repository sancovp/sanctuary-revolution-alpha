#!/usr/bin/env python3
"""
CORRECTED: Direct tool call test for LLM Intelligence MCP using mcp-use
Tests all tools without needing an LLM
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp_use import MCPClient


async def test_llm_intelligence_mcp():
    """Test LLM Intelligence MCP tools directly using mcp-use"""
    
    # Configure the LLM Intelligence MCP server  
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
        # Initialize sessions
        await client.create_all_sessions()
        print("✓ Connected to LLM Intelligence MCP server")
        
        # Get the session
        session = client.get_session("llm-intelligence")
        
        # Get available tools
        tools = await session.list_tools()
        print(f"✓ Found {len(tools)} tools: {[t.name for t in tools]}")
        
        print("\n=== Testing LLM Intelligence MCP Tools ===")
        
        # Test 1: Create first response
        print("\n1. Testing respond tool...")
        result = await session.call_tool("respond", {
            "qa_id": "embedding_test",
            "response_text": "This demonstrates the LLM Intelligence system working through MCP.\n\nKey benefits:\n- Overcomes embedding geometry limits\n- Systematic multi-fire responses\n- Separates thinking from output",
            "one_liner": "Demo of LLM Intelligence via MCP",
            "key_tags": ["mcp", "embedding-geometry", "multi-fire"],
            "involved_files": ["/tmp/llm_intelligence_mcp/mcp_server.py"]
        })
        print(f"✓ Response created: {result.content}")
        
        # Test 2: Add second response
        print("\n2. Testing second response...")
        result = await session.call_tool("respond", {
            "qa_id": "embedding_test", 
            "response_text": "Building on the previous response:\n\nImplementation works by:\n1. FastMCP provides the server framework\n2. mcp-use provides the testing client\n3. QA files store actual responses\n4. Conversation remains the thinking space",
            "one_liner": "Technical implementation details",
            "key_tags": ["implementation", "fastmcp", "mcp-use"],
            "involved_files": None
        })
        print(f"✓ Second response created: {result.content}")
        
        # Test 3: Get context
        print("\n3. Testing get_qa_context...")
        context = await session.call_tool("get_qa_context", {
            "qa_id": "embedding_test",
            "last_n": 2
        })
        print(f"✓ Context retrieved: {context.content}")
        
        # Test 4: List sessions
        print("\n4. Testing list_qa_sessions...")
        sessions = await session.call_tool("list_qa_sessions", {})
        print(f"✓ Sessions listed: {sessions.content}")
        
        # Test 5: Read specific response  
        print("\n5. Testing read_qa_response...")
        response = await session.call_tool("read_qa_response", {
            "qa_id": "embedding_test",
            "response_num": 1
        })
        print(f"✓ Response read: First 100 chars: {str(response.content)[:100]}...")
        
        # Test 6: Complete session
        print("\n6. Testing complete_qa_session...")
        complete = await session.call_tool("complete_qa_session", {
            "qa_id": "embedding_test",
            "summary": "Successfully tested LLM Intelligence MCP with all tools working correctly"
        })
        print(f"✓ Session completed: {complete.content}")
        
        print("\n" + "="*50)
        print("✅ ALL MCP TOOLS WORKING CORRECTLY!")
        print("The LLM Intelligence MCP is ready for use!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await client.close_all_sessions()
        print("✓ Disconnected from MCP server")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_llm_intelligence_mcp())
    sys.exit(0 if success else 1)