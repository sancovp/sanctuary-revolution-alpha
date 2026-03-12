# LLM Intelligence MCP - Usage Example

The system is working! Here's how to use it:

## What We Built

1. **MCP Server**: `mcp_server.py` - FastMCP server with tools for systematic responses
2. **Core Functions**: File operations for QA session management
3. **Response Structure**: Organized responses with QA_IDs, tags, and context tracking

## How To Use

### 1. Run the MCP Server
```bash
cd /tmp/llm_intelligence_mcp
python -m mcp_server
```

### 2. Configure Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "llm-intelligence": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/tmp/llm_intelligence_mcp"
    }
  }
}
```

### 3. Use the Tools

The MCP provides these tools:
- `respond` - Create structured responses 
- `get_qa_context` - Retrieve previous responses
- `list_qa_sessions` - View all sessions
- `read_qa_response` - Read specific responses
- `complete_qa_session` - Mark sessions complete

## The Pattern

1. **Conversation = Your thinking space** (what we're doing now)
2. **QA Files = The actual responses** (structured output)
3. **Multi-fire intelligence** (build context across responses)

## File Structure

Responses are saved as:
```
/tmp/llm_intelligence_responses/
├── qa_session_id/
│   ├── metadata.json
│   ├── response_001.md
│   ├── response_002.md
│   └── SUMMARY.md (when complete)
```

## Next Steps

This system is ready to test with Claude Desktop! It solves the embedding geometry problem by:
- Separating thinking (conversation) from output (QA files)
- Enabling multi-fire responses that build on context
- Systematic tracking of all intelligence threads