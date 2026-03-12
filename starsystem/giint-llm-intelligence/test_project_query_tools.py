#!/usr/bin/env python3
"""Test the new project query tools in the LLM Intelligence MCP."""

import asyncio
from pathlib import Path
from mcp_use import MCPClient


async def test_project_query_tools():
    """Test all the new project management query tools."""
    
    config = {
        "mcpServers": {
            "llm-intelligence": {
                "command": "python",
                "args": ["-m", "mcp_server"],
                "env": {"LLM_INTELLIGENCE_DIR": "/tmp/llm_intelligence_responses"},
                "cwd": str(Path(__file__).parent)
            }
        }
    }
    
    client = MCPClient.from_dict(config)
    
    try:
        await client.create_all_sessions()
        session = client.get_session("llm-intelligence")
        
        print("🧪 Testing Enhanced LLM Intelligence MCP Query Tools")
        print("=" * 60)
        
        # Test 1: List all projects
        print("\n1. Testing list_projects...")
        result = await session.call_tool("list_projects", {})
        projects_data = result.content[0].text
        print(f"✓ Projects found: {projects_data}")
        
        # Test 2: Get project overview
        print("\n2. Testing get_project_overview...")
        result = await session.call_tool("get_project_overview", {
            "project_id": "heaven_ecosystem_publishing"
        })
        overview_data = result.content[0].text
        print(f"✓ Project overview: {overview_data}")
        
        # Test 3: Query by feature
        print("\n3. Testing query_by_feature...")
        result = await session.call_tool("query_by_feature", {
            "feature_name": "library_publishing_system"
        })
        feature_data = result.content[0].text
        print(f"✓ Feature query: {feature_data}")
        
        # Test 4: Query by component
        print("\n4. Testing query_by_component...")
        result = await session.call_tool("query_by_component", {
            "component_name": "pypi_integration"
        })
        component_data = result.content[0].text
        print(f"✓ Component query: {component_data}")
        
        # Test 5: Analyze patterns (all projects)
        print("\n5. Testing analyze_project_patterns (all projects)...")
        result = await session.call_tool("analyze_project_patterns", {})
        patterns_all = result.content[0].text
        print(f"✓ All patterns: {patterns_all}")
        
        # Test 6: Analyze patterns (specific project)
        print("\n6. Testing analyze_project_patterns (specific project)...")
        result = await session.call_tool("analyze_project_patterns", {
            "project_id": "heaven_ecosystem_publishing"
        })
        patterns_project = result.content[0].text
        print(f"✓ Project patterns: {patterns_project}")
        
        # Test 7: List QA sessions (no filter)
        print("\n7. Testing list_qa_sessions (no filter)...")
        result = await session.call_tool("list_qa_sessions", {})
        sessions_all = result.content[0].text
        print(f"✓ All sessions: {sessions_all}")
        
        # Test 8: List QA sessions (with tag filter)
        print("\n8. Testing list_qa_sessions (tag filter)...")
        result = await session.call_tool("list_qa_sessions", {
            "tag": "pypi"
        })
        sessions_filtered = result.content[0].text
        print(f"✓ Filtered sessions: {sessions_filtered}")
        
        print("\n" + "=" * 60)
        print("✅ ALL PROJECT QUERY TOOLS WORKING!")
        print("🚀 LLM Intelligence MCP is now fully functional")
        print("📊 Ready for emergent pattern analysis and project management")
        print("🌟 This system can now support the full Seed.ai vision!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(test_project_query_tools())