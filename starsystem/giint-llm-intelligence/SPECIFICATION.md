# LLM Intelligence System Specification

## Core Problem & Solution

### The Problem
Google's research shows that embedding geometry doesn't work at scale - LLMs need multiple "fires" to express full intelligence. Current LLM interactions are single-fire, limiting cognitive capacity.

### The Solution
Create systematic multi-fire intelligence through cognitive separation:
- **Conversation Channel**: AI's thinking space (tool calls, analysis, exploration)
- **Response Channel**: AI's deliberate communication (curated response files)

## System Architecture

### Core Principle: Cognitive Separation
1. AI writes to response files (what the user should see)
2. AI does actual work (Read, Edit, Bash, analysis) - the thinking process
3. AI reports tool usage (optional archiving)
4. AI harvests response into conversation with context

### File Structure
```
qa_sets/{qa_id}/
├── qa.json                           # Master conversation file
├── responses/
│   ├── response_001/
│   │   ├── response.md              # AI's curated response content
│   │   └── tool_content.json        # Archived tool details
│   ├── response_002/
│   │   ├── response.md
│   │   └── tool_content.json
│   └── ...
```

### QA File Format
```json
{
  "qa_id": "abc123",
  "created_at": "2025-09-08T22:45:00Z",
  "project_id": "auth_system",
  "tracking": {
    "feature": "oauth_implementation",
    "component": "auth_middleware", 
    "deliverable": "oauth_flow",
    "subtask": "token_validation",
    "task": "implement_jwt_verify",
    "workflow_id": "auth_sprint_1",
    "is_from_waypoint": false
  },
  "responses": [
    {
      "response_id": 1,
      "timestamp": "2025-09-08T22:45:00Z",
      "response_content": "I implemented OAuth by...",
      "one_liner": "OAuth implementation with JWT validation",
      "tools_used": ["Read", "Edit", "Bash"],
      "involved_files": ["auth.py", "oauth_middleware.py"],
      "tags": ["oauth", "authentication", "jwt"],
      "response_file": "responses/response_001/response.md",
      "tool_archive": "responses/response_001/tool_content.json"
    }
  ]
}
```

## API Specification

### Core Tools (MCP Interface)

#### 1. respond()
**Purpose**: Harvest response file into QA conversation with full context
**Signature**:
```python
respond(
    qa_id: str,
    response_file_path: str,
    one_liner: str,
    key_tags: List[str],
    involved_files: List[str],
    project_id: str,
    feature: str,
    component: str,
    deliverable: str,
    subtask: str,
    task: str,
    workflow_id: str,
    is_from_waypoint: bool = False
) -> Dict[str, Any]
```

**Behavior**:
1. Read response file content from LLM-specified path (can be anywhere)
2. Copy content to organized structure: `qa_sets/{qa_id}/responses/response_XXX/response.md`
3. Delete original response file (cleanup)
4. Create/update QA conversation with full emergent tracking
5. Log to STARLOG debug diary (see STARLOG Integration section)
6. Return success confirmation

#### 2. report_tool_usage()
**Purpose**: Archive tool usage details during work
**Signature**:
```python
report_tool_usage(
    tools_used: List[str],
    response_file_path: str,
    involved_files: List[str]
) -> Dict[str, Any]
```

#### 3. get_qa_context()
**Purpose**: Load conversation context from previous sessions
**Signature**:
```python
get_qa_context(
    qa_id: str,
    last_n: int = 3
) -> Dict[str, Any]
```

#### 4. list_qa_sessions()
**Purpose**: List available QA sessions with filtering
**Signature**:
```python
list_qa_sessions(
    project_id: Optional[str] = None
) -> Dict[str, Any]
```

### Management Tools

#### 5. query_project_sessions()
**Purpose**: Find all sessions for emergent tracking queries
**Signature**:
```python
query_project_sessions(
    project_id: Optional[str] = None,
    feature: Optional[str] = None,
    component: Optional[str] = None,
    deliverable: Optional[str] = None,
    subtask: Optional[str] = None,
    task: Optional[str] = None,
    workflow_id: Optional[str] = None
) -> Dict[str, Any]
```

## STARLOG Integration

### Core Principle
STARLOG is the single source of truth for projects. LLM Intelligence adds conversation intelligence ON TOP OF existing STARLOG projects.

### STARLOG Debug Diary Format
Every `respond()` call logs to STARLOG debug diary with exact format:
```
{{DATETIME}}.{{QA_ID}}.{{RESPONSE_ID}}.{{PROJECT}}.{{FEATURE}}.{{COMPONENT}}.{{DELIVERABLE}}.{{SUBTASK}}.{{TASK}}.{{WORKFLOW}}.{{IS_FROM_WAYPOINT}}: {{one_liner}}
```

Example:
```
20250908_224500.abc123.1.auth_system.oauth_implementation.auth_middleware.oauth_flow.token_validation.implement_jwt_verify.auth_sprint_1.false: OAuth implementation with JWT validation
```

### Integration Flow
1. **Project Discovery**: Use `mcp__starlog__check()` and `mcp__starlog__orient()` to get project context
2. **Session Logging**: Each `respond()` call logs to STARLOG debug diary
3. **Context Continuity**: `orient()` lifts LLM Intelligence entries into STARLOG reports
4. **Project Queries**: Query debug diary for pattern `*.*.*.PROJECT.*.*.*.*.*.*.*:*`

### Two Base Waypoints
1. **starlog + LLM intelligence build flow**
   - Start STARLOG session
   - Use LLM Intelligence for implementation work
   - End STARLOG session with summary

2. **starlog + LLM intelligence review flow**
   - Load existing STARLOG project
   - Use LLM Intelligence for code review
   - Update STARLOG with review findings

## Cognitive Flow

### The Multi-Fire Pattern
1. **Fire 1**: Write curated response for user
2. **Fire 2**: Do actual analysis/implementation work
3. **Fire 3**: Report tool usage (archive thinking process)
4. **Fire 4**: Harvest everything with context

### Example Session
```python
# AI writes what user should see (ANYWHERE - LLM chooses path)
Write("/tmp/oauth_implementation_response.md", """
I'm implementing OAuth authentication with JWT validation.

The approach:
1. Create middleware for token validation
2. Implement JWT verification logic
3. Add error handling for expired tokens

This will integrate with your existing auth system...
""")

# AI does the actual work (thinking process)
Read("auth.py")
Edit("oauth_middleware.py", old="...", new="...")
Bash("npm test auth")

# AI archives tool usage (optional)
report_tool_usage(
    tools_used=["Read", "Edit", "Bash"],
    response_file_path="/tmp/oauth_implementation_response.md",
    involved_files=["auth.py", "oauth_middleware.py"]
)

# AI harvests everything - respond() organizes it automatically
respond(
    qa_id="abc123",
    response_file_path="/tmp/oauth_implementation_response.md",  # LLM's arbitrary path
    one_liner="OAuth implementation with JWT validation",
    key_tags=["oauth", "authentication", "jwt"],
    involved_files=["auth.py", "oauth_middleware.py"],
    project_id="auth_system",
    feature="oauth_implementation",
    component="auth_middleware",
    deliverable="oauth_flow",
    subtask="token_validation", 
    task="implement_jwt_verify",
    workflow_id="auth_sprint_1",
    is_from_waypoint=False
)

# respond() internally:
# 1. Reads content from /tmp/oauth_implementation_response.md
# 2. Copies to qa_sets/abc123/responses/response_001/response.md
# 3. Deletes /tmp/oauth_implementation_response.md (cleanup)
# 4. Updates qa_sets/abc123/qa.json with organized structure
```

## Emergent Tracking System

### Hierarchy
```
project_id → feature → component → deliverable → subtask → task → workflow_id
```

### Characteristics
- All elements are strings (not enums) for emergent discovery
- New categories can emerge naturally
- Queryable at any hierarchy level
- Enables project intelligence over time

### Example Hierarchy
```
project_id: "auth_system"
├── feature: "oauth_implementation"
│   ├── component: "auth_middleware"
│   │   ├── deliverable: "oauth_flow"
│   │   │   ├── subtask: "token_validation"
│   │   │   │   └── task: "implement_jwt_verify"
│   │   │   └── subtask: "refresh_token_handling"
│   │   └── deliverable: "oauth_endpoints"
│   └── component: "user_management"
└── feature: "session_handling"
```

## Context Continuity System

### Problem
Conversations reset, losing context of what was previously accessed.

### Solution: Context Bundles
Simple hooks track tool usage → create "shopping list" for next conversation.

### Hook Implementation
Track these operations:
- `Read(file_path)` → files accessed
- `Grep(pattern, path)` → search patterns used
- `Bash(command)` → commands executed

### Context Bundle Format
```json
{
  "session_id": "abc123",
  "accessed_files": ["auth.py", "oauth_middleware.py", "test_auth.py"],
  "search_patterns": ["oauth", "jwt", "token"],
  "commands_run": ["npm test auth", "git status"],
  "qa_sessions": ["abc123", "def456"]
}
```

## Architecture Requirements

### MCP Server Pattern
```python
# mcp_server.py (WRAPPER ONLY)
from llm_intelligence.core import (
    respond as core_respond,
    report_tool_usage as core_report,
    get_qa_context as core_context,
    list_qa_sessions as core_list
)

@mcp.tool()
async def respond(qa_id: str, response_file_path: str, one_liner: str, key_tags: List[str], 
                 involved_files: List[str], project_id: str, feature: str, component: str, 
                 deliverable: str, subtask: str, task: str, workflow_id: str, 
                 is_from_waypoint: bool = False):
    return core_respond(qa_id, response_file_path, one_liner, key_tags, involved_files, 
                       project_id, feature, component, deliverable, 
                       subtask, task, workflow_id, is_from_waypoint)

@mcp.tool()
async def report_tool_usage(tools_used: List[str], response_file_path: str, involved_files: List[str]):
    return core_report(tools_used, response_file_path, involved_files)
```

### Core Module Structure
```python
# llm_intelligence/core.py (BUSINESS LOGIC)
def respond(qa_id, response_file_path, one_liner, key_tags, involved_files, 
           project_id, feature, component, deliverable, subtask, 
           task, workflow_id, is_from_waypoint):
    # 1. Read response file content from LLM's arbitrary path
    # 2. Copy content to organized structure: qa_sets/{qa_id}/responses/response_XXX/response.md
    # 3. Delete original response file (cleanup)
    # 4. Update QA conversation with organized paths
    # 5. Log to STARLOG debug diary
    # 6. Return confirmation

def report_tool_usage(tools_used, response_file_path, involved_files):
    # Archive tool details to tool_content.json

def get_qa_context(qa_id, last_n):
    # Load conversation context

def list_qa_sessions(project_id):
    # List sessions with filtering
```

## Success Criteria

### Cognitive Separation Working
- AI writes response files (deliberate communication)
- AI does work via tools (thinking process)
- Clear separation between thinking and communication channels

### STARLOG Integration Working
- Projects tracked in STARLOG, not LLM Intelligence
- Debug diary logs with exact specified format
- orient() lifts LLM Intelligence entries into reports
- Two waypoints functional

### Emergent Tracking Working
- Full hierarchy captured in respond() calls
- Queryable at any level
- New categories emerge naturally
- Project intelligence builds over time

### Context Continuity Working
- Hook system tracks tool usage
- Context bundles provide session continuity
- Next conversation can "pick up where left off"

## Non-Requirements

### What NOT to Build
- ❌ `start_response()` - unnecessary ceremony
- ❌ Complex path management - auto-discovery works
- ❌ Status tracking - not requested
- ❌ Standalone project system - use STARLOG
- ❌ Business logic in MCP files - separate core module

### Simplicity Principles
- respond() does everything important
- MCP = thin wrapper layer only  
- STARLOG handles projects
- Auto-discovery over manual configuration
- Emergent categories over rigid schemas

## Implementation Notes

### File Path Conventions
- Response files: `qa_sets/{qa_id}/responses/response_{num:03d}/response.md`
- Tool archives: `qa_sets/{qa_id}/responses/response_{num:03d}/tool_content.json`
- QA master: `qa_sets/{qa_id}/qa.json`

### Auto-Discovery Logic
```python
def find_latest_response_file(qa_id):
    response_dir = f"qa_sets/{qa_id}/responses"
    if not os.path.exists(response_dir):
        return None
    
    # Find highest numbered response_XXX directory
    response_dirs = [d for d in os.listdir(response_dir) if d.startswith("response_")]
    if not response_dirs:
        return None
        
    latest = max(response_dirs, key=lambda x: int(x.split("_")[1]))
    return f"{response_dir}/{latest}/response.md"
```

### STARLOG Integration Code
```python
def log_to_starlog(qa_id, response_id, project_id, feature, component, 
                  deliverable, subtask, task, workflow_id, is_from_waypoint, one_liner):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    entry = f"{timestamp}.{qa_id}.{response_id}.{project_id}.{feature}.{component}.{deliverable}.{subtask}.{task}.{workflow_id}.{is_from_waypoint}: {one_liner}"
    
    # This assumes STARLOG MCP is available
    update_debug_diary(content=entry)
```

This specification captures the complete system as requested, with proper STARLOG integration, emergent tracking, cognitive separation, and the correct MCP architecture pattern.