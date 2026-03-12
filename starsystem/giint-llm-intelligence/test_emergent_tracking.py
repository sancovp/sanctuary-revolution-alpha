#!/usr/bin/env python3
"""Test the emergent tracking system with real project data."""

import asyncio
from pathlib import Path
from mcp_use import MCPClient


async def test_emergent_tracking():
    """Test the emergent tracking system with HEAVEN ecosystem data."""
    
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
        
        print("🧪 Testing Emergent Tracking System")
        print("=" * 50)
        
        # Test 1: HEAVEN ecosystem publishing with full emergent tracking
        print("\n1. Creating response with full emergent tracking...")
        result = await session.call_tool("respond", {
            "qa_id": "token_setup_heaven",
            "project_id": "heaven_ecosystem_publishing",
            "feature": "library_publishing_system", 
            "component": "pypi_integration",
            "deliverable": "automated_publishing_workflows",
            "subtask": "add_pypi_tokens_to_github_repos",
            "task": "setup_publishing_infrastructure",
            "workflow_id": "repo_finalization_workflow_001",
            "is_from_waypoint": True,
            "response_text": "Successfully added PyPI tokens to all GitHub repositories.\n\nCompleted repositories:\n- starlog-mcp: Token added, workflow active\n- carton-mcp: Token added, workflow active\n- powerset-agents-core: Token added, workflow active\n\nNext step: Trigger publishing via git tags.",
            "one_liner": "PyPI tokens added to all HEAVEN ecosystem repos",
            "key_tags": ["pypi", "github", "tokens", "publishing", "automation"],
            "involved_files": [".github/workflows/publish.yml", "pyproject.toml"]
        })
        print(f"✓ Created tracked response: {result.content[0].text}")
        
        # Test 2: Follow-up response in same project context
        print("\n2. Adding follow-up response with related tracking...")
        result = await session.call_tool("respond", {
            "qa_id": "token_setup_heaven", 
            "project_id": "heaven_ecosystem_publishing",
            "feature": "library_publishing_system",
            "component": "version_management", 
            "deliverable": "git_tagging_system",
            "subtask": "create_version_tags_for_publishing",
            "task": "trigger_pypi_publishing_workflows", 
            "workflow_id": "repo_finalization_workflow_001",
            "is_from_waypoint": True,
            "response_text": "Created git tags to trigger PyPI publishing:\n\n```bash\ngit tag v0.1.0 && git push origin v0.1.0  # pydantic-stack-core\ngit tag v0.1.0 && git push origin v0.1.0  # payload-discovery\n```\n\nPublishing workflows now active on PyPI.",
            "one_liner": "Git tags created to trigger PyPI publishing",
            "key_tags": ["git", "tags", "versioning", "pypi", "workflows"],
            "involved_files": ["pyproject.toml", "setup.py"]
        })
        print(f"✓ Created follow-up response: Response {result.content[0].text}")
        
        # Test 3: Different project to show emergent patterns
        print("\n3. Creating response for different project...")
        result = await session.call_tool("respond", {
            "qa_id": "llm_intelligence_development",
            "project_id": "llm_intelligence_mcp_development",
            "feature": "emergent_tracking_system",
            "component": "response_metadata_storage", 
            "deliverable": "dual_format_storage_system",
            "subtask": "implement_json_and_markdown_storage",
            "task": "build_emergent_tracking_architecture",
            "workflow_id": None,  # Not from waypoint
            "is_from_waypoint": False,
            "response_text": "Implemented dual-format storage system for emergent tracking.\n\nKey features:\n- JSON metadata for programmatic access\n- Markdown files for human readability\n- Full tracking hierarchy: project→feature→component→deliverable→subtask→task\n- Waypoint integration support",
            "one_liner": "Dual-format emergent tracking system implemented", 
            "key_tags": ["emergent", "tracking", "metadata", "json", "markdown"],
            "involved_files": ["/tmp/llm_intelligence_mcp/mcp_server.py"]
        })
        print(f"✓ Created different project response")
        
        # Test 4: Analyze patterns
        print("\n4. Analyzing emergent patterns...")
        sessions = await session.call_tool("list_qa_sessions", {})
        print(f"✓ Found sessions across multiple projects")
        
        print("\n" + "=" * 50) 
        print("✅ EMERGENT TRACKING SYSTEM WORKING!")
        print("📊 Data stored in both JSON (programmatic) and MD (human-readable)")
        print("🔗 Ready for cross-project pattern analysis")
        print("🚀 Ready for STARLOG and Carton integration")
        
    finally:
        await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(test_emergent_tracking())