#!/usr/bin/env python3
"""
Test SEED MCP using mcp-use client
"""

import asyncio
from mcp_use import MCPClient

# Config for SEED MCP
config = {
    "mcpServers": {
        "seed": {
            "command": "python",
            "args": ["-m", "seed_mcp.seed_mcp"]
        }
    }
}

async def test_seed_mcp():
    client = MCPClient.from_dict(config)
    
    try:
        # Create sessions
        await client.create_all_sessions()
        
        # Get SEED session
        session = client.get_session("seed")
        
        # List available tools
        tools = await session.list_tools()
        tool_names = [t.name for t in tools]
        print(f"Available SEED tools: {tool_names}")
        
        # Test who_am_i with no context
        print("\n" + "="*50)
        print("Testing who_am_i() with no context:")
        print("="*50)
        result = await session.call_tool(name="who_am_i", arguments={})
        print(result.content[0].text)
        
        # Test who_am_i with context
        print("\n" + "="*50) 
        print("Testing who_am_i() with context:")
        print("="*50)
        result = await session.call_tool(name="who_am_i", arguments={"context": "analyzing new codebase"})
        print(result.content[0].text)
        
    finally:
        await client.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(test_seed_mcp())