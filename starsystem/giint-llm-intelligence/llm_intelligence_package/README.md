# LLM Intelligence

A systematic multi-fire cognitive response system that separates AI thinking from communication through response files and organized conversation tracking.

## Overview

Based on Google's research showing embedding geometry doesn't work at scale, this system enables LLMs to use multiple "fires" for full intelligence expression through cognitive separation:

- **Conversation Channel**: AI's thinking space (tool calls, analysis, exploration)  
- **Response Channel**: AI's deliberate communication (curated response files)

## Key Features

- **Arbitrary Response Files**: LLM writes response files anywhere, system organizes automatically
- **Emergent Tracking**: Free-form project hierarchy (project → feature → component → deliverable → subtask → task → workflow)
- **STARLOG Integration**: Logs to debug diary with structured format
- **Cognitive Separation**: Clean separation between thinking and communication
- **JSON Safety**: All content properly escaped through json module

## Installation

```bash
pip install llm-intelligence
```

## Usage

### As MCP Server

```bash
llm-intelligence-server
```

### Direct API Usage

```python
from llm_intelligence import respond

# LLM writes response file anywhere
with open("/tmp/my_response.md", "w") as f:
    f.write("I implemented OAuth authentication...")

# System organizes everything automatically  
result = respond(
    qa_id="abc123",
    response_file_path="/tmp/my_response.md",  # Any path
    one_liner="OAuth implementation complete",
    key_tags=["oauth", "auth"],
    involved_files=["auth.py", "oauth.py"],
    project_id="auth_system",
    feature="oauth",
    component="middleware", 
    deliverable="auth_flow",
    subtask="jwt_validation",
    task="implement_verify",
    workflow_id="sprint_1"
)
```

## Architecture

- **Core Module**: `llm_intelligence.core` - All business logic
- **MCP Server**: `llm_intelligence.mcp_server` - Thin wrapper for MCP integration
- **Organized Storage**: `qa_sets/{qa_id}/responses/response_XXX/response.md`
- **JSON Tracking**: Full conversation history with emergent metadata

## Cognitive Flow

1. **Fire 1**: LLM writes curated response file
2. **Fire 2**: LLM does actual work (Read, Edit, Bash) 
3. **Fire 3**: LLM reports tool usage (optional)
4. **Fire 4**: LLM harvests everything with `respond()`

System handles all organization, cleanup, and tracking automatically.