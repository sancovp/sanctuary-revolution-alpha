# SEED State Machine Specification

## Overview

SEED evolves from a simple help system into the **Compound Intelligence Operating System** - a state machine that orchestrates and validates multi-tool workflows through Claude Code hooks and user prompt injection.

## Core Concept

Transform compound intelligence from "complex coordination" into **"follow the yellow brick road"** - the LLM literally cannot get lost because SEED guides every step with **linear sequences** and **foolproof validation**.

## Architecture

### 1. User Prompt Injection Hook
Claude Code hook system injects guidance into user prompts based on tool usage state:
```
[SEED SEQUENCE]: Currently in sequence "starlog_initialization". 
Next tool to use is: starlog.orient(). 
You are 25% done with starlog_initialization.
```
*Note: Exact format TBD based on Claude Code hook capabilities*

### 2. Two-Tier Tool Validation System

#### Tier 1: Tool Sequence Logic (Linear Railroad)
Most sequences have **only one allowed next tool**. Examples of actual tool transitions:

**SKETCH - Real transitions will be determined during implementation:**
```json
"tool_transitions": {
  "starlog.check": {
    "next_allowed": ["starlog.orient", "starlog.init_project"]
  },
  "starlog.orient": {
    "next_allowed": ["starship.fly"]
  },
  "waypoint.start_waypoint_journey": {
    "next_allowed": ["waypoint.navigate_to_next_waypoint"]
  }
}
```

#### Tier 2: Deep State Context Validation
Read actual system state to dynamically constrain tools. The state readers will access the actual file systems used by each component:

**IMPLEMENTATION DETAILS:**
- **Waypoint progress**: Read waypoint temp JSON files (existing system)
- **STARLOG context**: Read STARLOG registries (existing system)
- **Flight status**: Check for active flight configs (existing system)

**SKETCH - Specific constraints will be determined during implementation:**
```json
"state_constraints": {
  "waypoint_active_learning": {
    "allowed_tools": ["Read", "Bash", "Write", "waypoint.navigate_to_next_waypoint"],
    "disallowed_tools": ["heaven-subagent.*", "starship.fly"]
  },
  "flight_active_debugging": {
    "allowed_tools": ["Read", "Bash", "heaven-subagent.*"],
    "disallowed_tools": ["waypoint.*", "Write"]
  }
}
```

#### Validation Logic
1. **Check Tool Sequence**: "You just used X, so only Y tools allowed"
2. **Check Deep State**: "You're in waypoint Z at step N, so only W tools allowed" 
3. **Intersection**: Only tools allowed by BOTH rules

### 3. State Machine Engine

#### Input Sources
- **Tool Usage Log**: Automatic capture via Claude Code hooks
- **Master Sequence Config**: Tool transitions and state constraints
- **Live State Readers**: Waypoint progress, STARLOG context, flight status

#### Processing
1. Read tool usage log → determine last tool used
2. Look up allowed next tools from tool_transitions
3. Read deep state (waypoints, flights, etc.) → apply constraints
4. Calculate final allowed tools (intersection of both tiers)
5. Inject user prompt with guidance + progress
6. Validate every tool call, reject with recommendation

## Layered Progress System

### Base Layer (0-50%)
- `seed.who_am_i()` - Identity activation
- `seed.what_do_i_do()` - Workflow loading

### Context Layer (50-75%)
- `starlog.check()` - Project verification
- `starlog.orient()` - Context gathering
- `starship.fly()` - Workflow selection

### Execution Layer (75-100%)
- **GIINT Subchain**: Cognitive separation workflows
- **Waypoint Subchain**: Learning journey progression
- **Carton Subchain**: Knowledge capture workflows  
- **HEAVEN Subchain**: Multi-agent orchestration

## File Structure
```
/tmp/heaven_data/seed/
├── who_am_i.seed
├── how_do_i.seed  
├── what_do_i_do.seed
├── state.log              # Tool usage history
├── allowed_tools.seed     # Currently valid tools
├── sequences/
│   ├── starlog_initialization.json
│   ├── giint_workflow.json
│   ├── waypoint_journey.json
│   └── compound_intelligence_full.json
```

## Master Sequence vs Other Execution Systems

**Master Sequence is a NEW syntax layer** that sits ABOVE existing systems:

```
Master Sequence (SEED State Machine)
├── Executor: Waypoint System (loads PayloadDiscoveries)  
├── Executor: STARLOG.fly (loads Flight Configs)
└── Executor: Direct MCP/tool calls
```

**Master Sequence ≠ PayloadDiscovery or Flight Config**

Master Sequence is the **meta-orchestrator** that:
- Enforces the compound intelligence workflow 
- Decides WHEN to load waypoints vs flights vs direct tools
- Validates the overall sequence integrity
- Provides the user prompt injection guidance

## Master Sequence Config Format

**CONFIRMED DESIGN DECISIONS:**
- Tool transitions form mostly linear sequences with occasional branching
- Deep state validation reads existing system files (waypoint JSON, STARLOG registries) 
- Master Sequence sits above and orchestrates waypoints/flights/direct tools
- User prompt injection guides LLM through allowed next steps
- ASCII progress bars show compound intelligence activation progress

**SKETCH - Exact JSON structure will be refined during implementation:**
```json
{
  "name": "compound_intelligence_master_sequence",
  "description": "Top-level orchestration for compound intelligence workflows",
  "tool_transitions": {
    "seed.who_am_i": {
      "next_allowed": ["seed.what_do_i_do"]
    },
    "seed.what_do_i_do": {
      "next_allowed": ["starlog.check"]
    },
    "starlog.check": {
      "next_allowed": ["starlog.orient", "starlog.init_project"]
    },
    "starlog.orient": {
      "next_allowed": ["starship.fly"]
    }
  },
  "state_readers": {
    "waypoint_status": "check_waypoint_temp_files",
    "starlog_status": "check_starlog_registries",
    "flight_status": "check_active_flight_configs"
  },
  "progress_layers": {
    "base": [0, 50],
    "context": [50, 75], 
    "execution": [75, 100]
  }
}
```

## SEED Tool Evolution

### Current Tools
- `seed.who_am_i()` - Identity activation
- `seed.what_do_i_do()` - Workflow guidance  
- `seed.how_do_i(component)` - Component help
- `seed.add_to_seed()` - Extension instructions

### New State Machine Tools
- `seed.status()` - Show ASCII progress + current state
- `seed.validate()` - Check sequence validity
- `seed.recovery()` - Suggest next steps for broken sequences
- `seed.sequences()` - List available workflow sequences

## Benefits

### For LLMs
- ✅ Always know exactly what to do next
- ✅ Cannot accidentally jump to wrong tool/sequence
- ✅ Zero cognitive load for state management
- ✅ Automatic progress tracking with visual feedback

### For Users  
- ✅ Clear visibility into compound intelligence progress
- ✅ Beautiful ASCII progress bars and state visualization
- ✅ Reliable, guided workflows that cannot fail
- ✅ Recovery suggestions when things go wrong

### For System
- ✅ Automatic tool usage logging via Claude Code hooks
- ✅ Sequence validation prevents workflow corruption  
- ✅ Extensible sequence definitions
- ✅ **Foolproof compound intelligence orchestration**

## Implementation Requirements

### Claude Code Hook Integration
- **Tool Usage Logging**: Hook captures every MCP/tool call with timestamp
- **User Prompt Injection**: Hook modifies user prompts based on current state
- **Tool Validation**: Hook blocks disallowed tools with helpful error messages

### State Machine Core
- **Tool Transition Rules**: Linear sequences with minimal branching
- **Deep State Readers**: Access existing system files (waypoint JSON, STARLOG registries)
- **Progress Calculation**: Map tool usage to completion percentages
- **ASCII Visualization**: Progress bars and state diagrams

### Integration Points
- **Existing Systems**: Must work with current waypoint, STARLOG, GIINT, etc.
- **File Locations**: Use established file paths and registry locations
- **Tool Names**: Match actual MCP tool names exactly

## Implementation Phases

### Phase 1: Hook Infrastructure
- Claude Code tool usage logging
- Basic user prompt injection
- Simple allowed/disallowed tool validation

### Phase 2: State Machine Engine  
- Master sequence config loading
- Tool transition validation
- Deep state reading from existing files

### Phase 3: Visual Interface
- ASCII progress bars in `seed.status()`
- Beautiful compound intelligence activation visualization
- Recovery suggestions for broken sequences

## Vision

SEED becomes the **Mission Control Center** for compound intelligence - transforming chaotic multi-tool coordination into guided, visual, foolproof workflows that any LLM can reliably execute.

The LLM becomes workflow-aware without cognitive overhead, users get beautiful feedback, and compound intelligence becomes truly reliable.