# LLM Intelligence MCP - Architecture Specification

## Overview

The LLM Intelligence MCP implements a **universal intelligence compiler** that overcomes embedding geometry limitations through systematic multi-fire responses. It creates a feedback loop between conversation, implementation state, and project intelligence.

## Core Concept: Multi-Fire Intelligence

Google research shows that LLM embedding geometry doesn't work at scale - LLMs need multiple "fires" (interactions) to express full intelligence. This system forces systematic multi-fire responses where:
- **Conversation becomes the thinking space** (exploration)
- **QA files contain the actual responses** (crystallized intelligence)
- **Project metadata tracks emergent patterns** (meta-intelligence)

## System Architecture

### 1. Storage Structure

```
/tmp/llm_intelligence_responses/
├── {qa_id}.json                  # Master QA file (single source of truth)
├── {qa_id}.md                    # Human-readable version
└── response_files/
    └── {qa_id}/
        ├── response_001/
        │   ├── response.md       # The actual response content
        │   └── tool_content/     # Tools used for THIS response
        │       ├── Read_{hash}.json
        │       └── Grep_{hash}.json
        ├── response_002/
        │   ├── response.md
        │   └── tool_content/
        │       └── WebFetch_{hash}.json
        └── response_003/
            ├── response.md
            └── tool_content/
                └── Read_{hash}.json
```

### 2. Master QA File Schema

```json
{
  "qa_id": "session_identifier",
  "project_id": "project_name",
  "created_at": "ISO timestamp",
  "responses": [
    {
      "response_id": "response_001",
      "timestamp": "ISO timestamp",
      "user_prompt": "the user's actual question",
      "one_liner": "concise summary of response",
      "tools_used": [
        {
          "tool": "Read",
          "params_summary": "file: /src/auth.py",
          "content_path": "tool_content/Read_a3f2b1c9.json",
          "is_context_tool": true
        }
      ],
      "parts_status": {
        "component": {"id": "auth_system", "status": "completed"},
        "deliverable": {"id": "oauth_impl", "status": "in_review"}
      }
    }
  ],
  "tracking": {
    "feature": "authentication_system",
    "component": "oauth_integration",
    "deliverable": "token_management",
    "task": "implement_auth",
    "workflow_id": "auth_workflow_001"
  }
}
```

## Emergent Tracking Hierarchy

The system captures an emergent hierarchy that naturally forms during development:

```
Project
├── Feature         (high-level capability)
│   ├── Component   (architectural piece)
│   │   ├── Deliverable (specific output)
│   │   │   ├── Task      (work item)
│   │   │   │   └── Subtask (granular step)
```

### Dynamic Tracking

All hierarchy elements are **strings, not enums** - this enables:
- Emergent discovery of new categories
- No schema migrations
- Human-correctable at any time
- Pattern analysis across projects

## Context Management System

### Minimalist Context Bundle Approach

Instead of complex replay systems, use a simple "shopping list" pattern:

1. **Track context operations** during conversation (Read, Grep, Bash, etc.)
2. **Save context bundle** with concise summaries
3. **Reference in QA file** for next conversation
4. **Selective reload** based on what's needed

#### Context Bundle Structure

```json
{
  "session": "20250908_141431",
  "timestamp": "2025-09-08T14:14:31",
  "operations": [
    {"tool": "Read", "summary": "Read: /src/auth/oauth.py", "params": {...}},
    {"tool": "Grep", "summary": "Grep 'OAuth' in ./src", "params": {...}},
    {"tool": "Bash", "summary": "Bash: npm test auth...", "params": {...}}
  ]
}
```

#### In QA File

```markdown
**Context Bundle**: `/tmp/llm_intelligence_responses/context_bundles/20250908_141431.json`
**Quick List**:
- Read: /src/auth/oauth.py
- Read: /src/auth/tokens.py  
- Grep 'OAuth' in ./src
- Bash: npm test auth
```

#### At Conversation Start

```python
# Assistant sees the bundle reference and thinks:
"Ok I need to read those OAuth files to understand what we built"

# Quick scan of the shopping list
bundle = load_context_bundle("20250908_141431.json")
for op in bundle["operations"]:
    print(op["summary"])  # See what was accessed

# Selective reload of relevant context
Read("/src/auth/oauth.py")  # Key file from last time
```

### Context Capture (via Claude Code Hooks)

Simple hooks that track essential operations:

1. **UserPromptSubmit Hook**: Start new context bundle
2. **PostToolUse Hook**: Track Read, Grep, Bash, WebFetch operations
3. **AssistantResponseComplete Hook**: Save bundle and add reference to QA

### Context Philosophy

**Context isn't about replaying everything, it's about knowing what's available to replay!**

The minimalist approach provides:
- **Transparency**: See exactly what was accessed
- **Efficiency**: Only reload what's needed
- **Simplicity**: No complex replay mechanisms
- **Control**: Assistant decides what context is relevant

### Three Layers of Context

1. **QA Summary** (Always Available)
   - One-liners from all responses
   - Parts completion status
   - Context bundle reference

2. **Shopping List** (Quick Scan)
   - List of all files/searches/commands from last session
   - Helps decide what to reload

3. **Selective Reload** (Based on Task)
   - Read specific files mentioned in bundle
   - Re-run searches if needed
   - Check command outputs if relevant

## Part Status Tracking

### Completion States

Each part (feature/component/deliverable/task) can have status:
- `started` - Work has begun
- `in_progress` - Active development
- `blocked` - Waiting on dependency
- `completed` - Implementation done
- `in_review` - Under review
- `shipped` - Deployed to production

### Human Recovery

**Critical Design Principle**: All AI tracking errors are recoverable through simple updates.

```python
# AI forgot to mark something complete? Fix it:
update_part_status(
    qa_id="session_123",
    part_type="component",
    part_id="oauth_integration", 
    status="completed",
    notes="Actually finished in response_002, AI didn't mark it"
)
```

The system instantly snaps back to truth - all queries reflect the correction.

## Narrative System (Future)

Projects naturally form narrative arcs:

```
Project
├── Journey (successful feature implementation)
│   ├── Episode (group of chats toward milestone)
│   │   ├── Chat/QA sessions
│   │   └── Multi-fire responses
│   └── Episode (next milestone)
└── Journey (next feature)
```

This maps to the tracking hierarchy:
- **Episodes** = feature→component→deliverable groupings
- **Journeys** = complete feature implementations
- **Narrative** = the story from conception to completion

## The Two Base Waypoints

All development work reduces to two fundamental conversation types:

### 1. BUILD FLOW
```
Starlog → LLM Intelligence → Build/Implement → Track Progress → Mark Completions
```

### 2. REVIEW FLOW  
```
Starlog → LLM Intelligence → Query Status → Find Drift → Correct Tracking → Update
```

### The Meta Loop
```
BUILD → REVIEW → FIX LLM INTELLIGENCE → BUILD BETTER → REVIEW BETTER → ...
```

This creates a **compounding intelligence system** where:
- Each BUILD generates more data
- Each REVIEW corrects drift and improves accuracy
- Fixes to LLM Intelligence make future tracking better
- The system gets smarter with every cycle

## Waypoint Composition

LLM Intelligence can invoke arbitrary waypoint sequences:

```
Starlog (entry point)
    ↓
LLM Intelligence (orchestrator)
    ↓
Waypoint System (arbitrary execution)
    ├── Payload Discovery (find patterns/instructions)
    ├── Metastack Templates (generate ANY output)
    └── Recursive Waypoints (waypoints calling waypoints)
```

Since all LLM outputs are strings, metastack can template them into any structure, making the system **Turing complete for development tasks**.

## Query Tools

### Project Management
- `list_projects()` - All projects with statistics
- `get_project_overview(project_id)` - Detailed project analysis
- `query_by_feature(feature_name)` - Find QAs by feature
- `query_by_component(component_name)` - Find QAs by component
- `analyze_project_patterns(project_id?)` - Pattern analysis

### Context Management
- `load_context_from_qa(qa_id, response_ids?)` - Replay tool context
- `get_conversation_context(qa_id)` - Full conversation transcript
- `replay_context_tools(qa_id, tool_filter?)` - Selective tool replay

### Status Tracking
- `update_part_status(qa_id, part_type, part_id, status)` - Update completion
- `get_project_status(project_id)` - Current state of all parts
- `find_blocked_parts()` - Identify blockers across projects

## Publishing Pipeline (Seed.ai Vision)

The system enables automatic publishing from conversations:

1. **Conversations** → QA files (raw intelligence)
2. **QA Files** → Project wikis (organized by feature)
3. **Wikis** → Refined documentation (with AI redaction)
4. **Documentation** → Public knowledge base

Each layer adds refinement while preserving the full context chain.

## Anti-Fragile Design Principles

1. **Human-Recoverable State**: All AI errors fixable through simple edits
2. **No Schema Lock-in**: Everything is strings, patterns emerge naturally
3. **Complete Audit Trail**: Every tool use, every response, every correction
4. **Progressive Enhancement**: Start simple, layer complexity as needed
5. **Context Preservation**: Never lose information, only add structure

## Implementation Status

### ✅ Completed
- Emergent tracking system with full hierarchy
- Dual-format storage (JSON + Markdown)
- Project query tools
- Basic response tracking
- Pattern analysis

### 🚧 In Progress
- Claude Code hooks for conversation capture
- Tool content archiving system
- Context replay mechanism

### 📋 Planned
- Part status tracking with recovery
- Narrative system (Episodes/Journeys)
- Waypoint composition system
- Auto-publishing pipeline
- STARLOG integration

## Getting Started

```python
# Start a new QA session
respond(
    qa_id="my_feature_dev",
    project_id="my_project",
    feature="new_feature",
    component="core_logic",
    response_text="Implementation details...",
    one_liner="Started core logic implementation",
    key_tags=["implementation", "core"]
)

# Load context in next conversation
load_context_from_qa(qa_id="my_feature_dev")

# Check project status
get_project_overview(project_id="my_project")

# Analyze patterns
analyze_project_patterns(project_id="my_project")
```

## Conclusion

The LLM Intelligence MCP creates a **universal development intelligence system** that:
- Overcomes LLM limitations through multi-fire responses
- Tracks project state emergently without rigid schemas
- Preserves perfect context across conversations
- Enables human correction of AI errors
- Compounds intelligence with every interaction

This architecture supports the full vision of conversations becoming structured project intelligence, enabling the Seed.ai auto-publishing workflow from raw conversations to refined public knowledge.