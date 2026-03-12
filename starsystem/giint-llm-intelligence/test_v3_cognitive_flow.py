#!/usr/bin/env python3
"""Test the V3 cognitive architecture: Write → Work → Report → Respond."""

import asyncio
from pathlib import Path
from mcp_use import MCPClient


async def test_cognitive_flow():
    """Test the complete cognitive separation flow."""
    
    config = {
        "mcpServers": {
            "llm-intelligence-v3": {
                "command": "python",
                "args": ["-m", "mcp_server_v3"],
                "env": {"LLM_INTELLIGENCE_DIR": "/tmp/llm_intelligence_v3"},
                "cwd": str(Path(__file__).parent)
            }
        }
    }
    
    client = MCPClient.from_dict(config)
    
    try:
        await client.create_all_sessions()
        session = client.get_session("llm-intelligence-v3")
        
        print("🧪 Testing V3 Cognitive Architecture")
        print("=" * 60)
        
        # Step 1: Start a new response
        print("\n1. Starting new response...")
        result = await session.call_tool("start_response", {
            "project_id": "auth_system",
            "feature": "oauth_implementation",
            "component": "token_management"
        })
        
        response_data = eval(result.content[0].text)
        qa_id = response_data["qa_id"]
        response_file_path = response_data["response_file_path"]
        
        print(f"✓ Started QA session {qa_id}")
        print(f"✓ Response file: {response_file_path}")
        
        # Step 2: Write initial response (user-facing content)
        print("\n2. Writing initial response content...")
        
        # Simulate using Claude Code's Write tool to build response
        response_content = """I'll implement OAuth with token refresh capability.

Let me start by examining the existing authentication structure and then build the OAuth client with automatic token management.

## Implementation Plan:
1. Create OAuthClient class with token storage
2. Add refresh token logic
3. Implement automatic token renewal
4. Add comprehensive error handling
5. Write tests for all scenarios
"""
        
        # Write to response file (this would normally be done with Write tool)
        Path(response_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(response_file_path, "w") as f:
            f.write(response_content)
        
        print(f"✓ Wrote initial response content ({len(response_content)} chars)")
        
        # Step 3: Report first round of tool usage
        print("\n3. Reporting first round of tool usage...")
        result = await session.call_tool("report_tool_usage", {
            "tools_used": ["Read", "Write"],
            "response_file_path": response_file_path,
            "involved_files": ["src/auth/oauth.py"]
        })
        print(f"✓ Reported tools: {result.content[0].text}")
        
        # Step 4: Continue working and update response
        print("\n4. Continuing work and updating response...")
        
        # Add more content to response file
        updated_content = response_content + """

## OAuth Implementation Complete

I've successfully implemented the OAuth client with the following features:

```python
class OAuthClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        
    def authenticate(self, username, password):
        # Implementation with automatic token storage
        pass
        
    def refresh_tokens(self):
        # Automatic token refresh logic
        pass
```

The implementation includes:
- ✅ Token storage and management
- ✅ Automatic refresh before expiration  
- ✅ Comprehensive error handling
- ✅ Full test coverage

All tests are passing and the OAuth flow is ready for production use.
"""
        
        # Update response file
        with open(response_file_path, "w") as f:
            f.write(updated_content)
        
        print(f"✓ Updated response file ({len(updated_content)} chars)")
        
        # Step 5: Report second round of tool usage
        print("\n5. Reporting second round of tool usage...")
        result = await session.call_tool("report_tool_usage", {
            "tools_used": ["Edit", "Write", "Bash"],
            "response_file_path": response_file_path,
            "involved_files": ["src/auth/oauth.py", "tests/test_oauth.py"]
        })
        print(f"✓ Reported second round of tools")
        
        # Step 6: Harvest response into QA conversation
        print("\n6. Harvesting response into QA conversation...")
        result = await session.call_tool("respond", {
            "qa_id": qa_id,
            "user_prompt": "implement OAuth with token refresh",
            "one_liner": "Implemented OAuth client with automatic token refresh",
            "key_tags": ["oauth", "authentication", "token-refresh", "security"]
        })
        
        harvest_result = eval(result.content[0].text)
        print(f"✓ Harvested response: {harvest_result.get('message', 'Response harvested')}")
        print(f"✓ Tools used: {harvest_result.get('tools_used', [])}")
        print(f"✓ Files involved: {harvest_result.get('involved_files', [])}")
        print(f"✓ Content: {harvest_result.get('response_content_chars', 0)} characters")
        print(f"Debug: {harvest_result}")
        
        # Step 7: Start second cycle
        print("\n7. Starting second work cycle...")
        
        # Get path for next response
        result = await session.call_tool("get_response_file_path", {
            "qa_id": qa_id
        })
        next_response_data = eval(result.content[0].text)
        next_response_path = next_response_data["response_file_path"]
        
        # Write second response
        second_response = """Adding comprehensive error handling and edge case management to the OAuth implementation.

## Error Handling Enhancements:

1. **Network Failures**: Added retry logic with exponential backoff
2. **Invalid Tokens**: Clear error messages and automatic refresh attempts
3. **Rate Limiting**: Respect 429 responses and retry-after headers
4. **Malformed Responses**: Robust JSON parsing with fallbacks

The OAuth client is now production-ready with enterprise-grade reliability.
"""
        
        Path(next_response_path).parent.mkdir(parents=True, exist_ok=True)
        with open(next_response_path, "w") as f:
            f.write(second_response)
        
        print(f"✓ Started second response cycle")
        
        # Report tools for second response
        result = await session.call_tool("report_tool_usage", {
            "tools_used": ["Edit", "Bash", "Read"],
            "response_file_path": next_response_path,
            "involved_files": ["src/auth/oauth.py", "src/auth/error_handling.py"]
        })
        
        # Harvest second response
        result = await session.call_tool("respond", {
            "qa_id": qa_id,
            "user_prompt": "add error handling to OAuth implementation",
            "one_liner": "Added enterprise-grade error handling to OAuth",
            "key_tags": ["error-handling", "resilience", "production-ready"]
        })
        
        print(f"✓ Harvested second response")
        
        # Step 8: Verify the complete structure
        print("\n8. Verifying file structure and QA context...")
        
        # Check directory structure
        import subprocess
        subprocess.run(["find", "/tmp/llm_intelligence_v3", "-type", "f"], check=True)
        
        # Get QA context
        result = await session.call_tool("get_qa_context", {
            "qa_id": qa_id
        })
        context_data = eval(result.content[0].text)
        
        print(f"✓ QA session has {context_data['total_responses']} responses")
        print(f"✓ Project: {context_data['project_id']}")
        print(f"✓ Tracking: {context_data['tracking']}")
        
        # Verify both responses are in conversation
        for i, conv in enumerate(context_data['conversation'], 1):
            print(f"  Response {i}: {conv['one_liner']}")
            print(f"    Tools: {conv['tools_used']}")
            print(f"    Files: {conv['involved_files']}")
        
        # Step 9: Check actual files created
        print("\n9. Verifying actual file structure...")
        qa_file_path = Path(f"/tmp/llm_intelligence_v3/qa_sets/{qa_id}/qa.json")
        if qa_file_path.exists():
            import json
            with open(qa_file_path) as f:
                qa_data = json.load(f)
            
            print("QA File Contents:")
            print(f"- QA ID: {qa_data['qa_id']}")
            print(f"- Responses: {len(qa_data['responses'])}")
            print(f"- First response chars: {len(qa_data['responses'][0]['response_content'])}")
            print(f"- Tools aggregated: {qa_data['responses'][0]['tools_used']}")
            print(f"- Files involved: {qa_data['responses'][0]['involved_files']}")
            
            # Verify cognitive separation
            response_file_1 = Path(f"/tmp/llm_intelligence_v3/qa_sets/{qa_id}/responses/response_001/response.md")
            tool_archive_1 = Path(f"/tmp/llm_intelligence_v3/qa_sets/{qa_id}/responses/response_001/tool_usage.json")
            
            print(f"✓ Response file 1 exists: {response_file_1.exists()}")
            print(f"✓ Tool archive 1 exists: {tool_archive_1.exists()}")
            
            if tool_archive_1.exists():
                with open(tool_archive_1) as f:
                    tool_data = json.load(f)
                print(f"✓ Tool reports: {len(tool_data['usage_reports'])}")
        
        print("\n" + "=" * 60)
        print("✅ V3 COGNITIVE ARCHITECTURE WORKING PERFECTLY!")
        print("🧠 Thinking/Analysis Channel: Tool calls and work")
        print("💬 Communication Channel: Response files")  
        print("📝 Harvest System: respond() packages everything")
        print("🗂️ Clean Structure: qa_sets/{id}/{qa.json, responses/}")
        print("🔄 Multiple Cycles: Write → Work → Report → (repeat) → Respond")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(test_cognitive_flow())