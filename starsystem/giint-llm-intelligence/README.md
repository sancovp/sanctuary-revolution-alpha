# LLM Intelligence MCP

An MCP server that overcomes LLM embedding geometry limitations through systematic multi-fire responses.

## Background

Google's research shows that embedding geometry at scale prevents LLMs from expressing their full intelligence in single responses. This MCP provides tools to systematically build intelligence across multiple "fires".

## Installation

```bash
pip install fastmcp
```

## Usage

### As an MCP Server

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "llm-intelligence": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/llm_intelligence_mcp",
      "env": {
        "LLM_INTELLIGENCE_DIR": "/path/to/responses"
      }
    }
  }
}
```

## Tools

- **respond**: Create structured responses in QA system
- **get_qa_context**: Retrieve previous responses for context
- **list_qa_sessions**: View all QA sessions
- **read_qa_response**: Read specific responses
- **complete_qa_session**: Mark session complete with summary

## How It Works

1. **Conversation = Thinking Space**: Your conversation with the LLM is the working/thinking space
2. **QA Files = Actual Responses**: The QA files contain the structured, final responses
3. **Multi-Fire Intelligence**: Each response builds on previous context, overcoming embedding limitations
4. **Systematic Tracking**: All responses are tracked with QA_IDs, tags, and involved files

## Example

```python
# First response
await respond(
    qa_id="embedding_analysis",
    response_text="Core insight about embedding geometry...",
    one_liner="Embedding geometry analysis",
    key_tags=["embeddings", "geometry"],
    involved_files=["analysis.py"]
)

# Building on context
await respond(
    qa_id="embedding_analysis",
    response_text="Further analysis building on previous insights...",
    one_liner="Extended analysis",
    key_tags=["multi-fire", "context"],
    involved_files=None
)

# Retrieve context
context = await get_qa_context("embedding_analysis", last_n=2)
```

## Response Structure

Each response file contains:
- Response number and one-liner summary
- QA_ID for tracking
- Timestamp
- Tags for categorization
- Involved files
- The actual response content

## Benefits

- **Overcomes Embedding Limitations**: Multiple fires allow full intelligence expression
- **Systematic Tracking**: Every response is tracked and retrievable
- **Context Building**: Each response can build on previous ones
- **Clean Separation**: Thinking (conversation) vs Output (QA files)