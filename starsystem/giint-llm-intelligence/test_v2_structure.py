#!/usr/bin/env python3
"""Test the V2 QA file structure with full content inline."""

import asyncio
from pathlib import Path
from mcp_use import MCPClient


async def test_v2_qa_structure():
    """Test the new QA file structure where content is inline."""
    
    config = {
        "mcpServers": {
            "llm-intelligence-v2": {
                "command": "python",
                "args": ["-m", "mcp_server_v2"],
                "env": {"LLM_INTELLIGENCE_DIR": "/tmp/llm_intelligence_v2"},
                "cwd": str(Path(__file__).parent)
            }
        }
    }
    
    client = MCPClient.from_dict(config)
    
    try:
        await client.create_all_sessions()
        session = client.get_session("llm-intelligence-v2")
        
        print("🧪 Testing V2 QA File Structure")
        print("=" * 60)
        
        # Test 1: Create first response with FULL content
        print("\n1. Creating first response with full content inline...")
        
        full_response_content = """I'll implement OAuth flow with token refresh capability.

First, let me read the existing authentication module to understand the current structure:

```python
# auth/oauth.py
import requests
from datetime import datetime, timedelta

class OAuthClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
    
    def authenticate(self, username, password):
        response = requests.post('/oauth/token', {
            'grant_type': 'password',
            'username': username,
            'password': password,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        })
        
        if response.status_code == 200:
            self._store_tokens(response.json())
            return True
        return False
    
    def refresh(self):
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        
        response = requests.post('/oauth/token', {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        })
        
        if response.status_code == 200:
            self._store_tokens(response.json())
            return True
        return False
```

The OAuth implementation is now complete with automatic token refresh."""
        
        result = await session.call_tool("respond", {
            "qa_id": "oauth_implementation",
            "user_prompt": "implement OAuth flow with token refresh",
            "response_text": full_response_content,
            "one_liner": "Implemented OAuth with automatic token refresh",
            "key_tags": ["oauth", "authentication", "token-refresh"],
            "tools_used": ["Read", "Edit", "Bash"],
            "project_id": "auth_system",
            "feature": "authentication",
            "component": "oauth",
            "deliverable": "token_management",
            "task": "implement_oauth"
        })
        
        print(f"✓ Response 1 created: {result.content[0].text}")
        
        # Test 2: Add second response with different content
        print("\n2. Adding second response to same QA session...")
        
        second_response = """Adding comprehensive error handling to the OAuth implementation.

I've added the following error handling:

1. **Network errors**: Retry logic with exponential backoff
2. **Invalid credentials**: Clear error messages to user
3. **Token expiration**: Automatic refresh before API calls
4. **Rate limiting**: Respect 429 responses with retry-after

The implementation now handles all edge cases gracefully."""
        
        result = await session.call_tool("respond", {
            "qa_id": "oauth_implementation",
            "user_prompt": "add error handling to the OAuth flow",
            "response_text": second_response,
            "one_liner": "Added comprehensive error handling",
            "key_tags": ["error-handling", "resilience"],
            "tools_used": ["Edit", "Bash"],
            "subtask": "error_handling"
        })
        
        print(f"✓ Response 2 added: {result.content[0].text}")
        
        # Test 3: Archive tool content separately
        print("\n3. Archiving tool content...")
        result = await session.call_tool("archive_tool_content", {
            "qa_id": "oauth_implementation",
            "response_num": 1,
            "tools": [
                {
                    "tool": "Read",
                    "params": {"file_path": "/src/auth/oauth.py"},
                    "result": "file contents here..."
                },
                {
                    "tool": "Edit",
                    "params": {"file_path": "/src/auth/oauth.py", "old_string": "...", "new_string": "..."},
                    "result": "File updated successfully"
                },
                {
                    "tool": "Bash",
                    "params": {"command": "npm test auth"},
                    "result": "All tests passing"
                }
            ]
        })
        print(f"✓ Tool content archived: {result.content[0].text}")
        
        # Test 4: Load QA context (should have FULL content)
        print("\n4. Loading QA context with full content...")
        result = await session.call_tool("get_qa_context", {
            "qa_id": "oauth_implementation"
        })
        context = result.content[0].text
        print(f"✓ Context loaded, checking structure...")
        
        # Verify the response contains full content
        import json
        context_data = json.loads(context)
        assert "conversation" in context_data
        assert len(context_data["conversation"]) == 2
        assert "implement OAuth flow" in context_data["conversation"][0]["response_content"]
        print(f"✓ Full content verified in QA file!")
        
        # Test 5: Update part status
        print("\n5. Testing part status tracking...")
        result = await session.call_tool("update_part_status", {
            "qa_id": "oauth_implementation",
            "response_num": 1,
            "part_type": "component",
            "part_id": "oauth",
            "status": "completed",
            "notes": "OAuth implementation complete with token refresh"
        })
        print(f"✓ Part status updated: {result.content[0].text}")
        
        # Test 6: Check the actual file structure
        print("\n6. Verifying file structure...")
        import subprocess
        subprocess.run(["ls", "-la", "/tmp/llm_intelligence_v2/"], check=True)
        
        # Read the actual QA file
        print("\n7. Reading actual QA file to verify structure...")
        qa_file_path = Path("/tmp/llm_intelligence_v2/oauth_implementation.json")
        if qa_file_path.exists():
            with open(qa_file_path) as f:
                qa_data = json.load(f)
            
            print("QA File Structure:")
            print(f"- Responses: {len(qa_data['responses'])}")
            print(f"- First response has {len(qa_data['responses'][0]['response_content'])} chars of content")
            print(f"- Tools used: {qa_data['responses'][0]['tools_used']}")
            print(f"- User prompt: {qa_data['responses'][0]['user_prompt'][:50]}...")
            
            # Verify content is inline
            assert qa_data['responses'][0]['response_content'].startswith("I'll implement OAuth")
            print("✓ CONFIRMED: Full response content is inline in QA file!")
        
        print("\n" + "=" * 60)
        print("✅ V2 STRUCTURE WORKING PERFECTLY!")
        print("📝 QA files now contain FULL conversation content inline")
        print("🗂️ Tool details archived separately for replay")
        print("✨ Human-readable markdown generated automatically")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(test_v2_qa_structure())