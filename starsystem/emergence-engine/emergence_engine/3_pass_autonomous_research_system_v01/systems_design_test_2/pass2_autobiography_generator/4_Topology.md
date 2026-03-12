# Phase 4: Topology - Multi-Agent System Network

## 4a. Node Identify

### Agent Nodes:

**N1: Orchestrator Node**
- Function: Coordinate all agents, maintain state
- Capacity: Single instance
- State: Global generation state

**N2: Interview Agent Node**
- Function: Conduct memory elicitation
- Capacity: Multiple concurrent interviews
- State: Conversation history per session

**N3: Timeline Agent Node**
- Function: Organize chronologically
- Capacity: Batch processing
- State: Timeline structure

**N4: Theme Agent Node**
- Function: Extract patterns
- Capacity: CPU-intensive analysis
- State: Discovered themes

**N5: Voice Agent Node**
- Function: Analyze linguistic style
- Capacity: Sample processing
- State: Voice profile

**N6: Narrative Agent Node**
- Function: Generate prose
- Capacity: Chapter generation
- State: Writing context

**N7: Coherence Agent Node**
- Function: Verify consistency
- Capacity: Full text analysis
- State: Issue tracking

### Storage Nodes:

**S1: Memory Bank Node**
- Data: All collected memories
- Persistence: Session + long-term
- Indices: Time, person, theme

**S2: State Store Node**
- Data: Orchestrator state
- Persistence: Checkpoint-based
- Recovery: Resume capability

**S3: Output Buffer Node**
- Data: Generated chapters
- Persistence: Write-through
- Format: Markdown text

## 4b. Edge Mapping

### Control Edges (Orchestrator-driven):
```
E1: Orchestrator → Interview Agent
    - Type: Task assignment
    - Data: Phase to interview

E2: Orchestrator → Timeline Agent
    - Type: Analysis request
    - Data: Memory collection

E3: Orchestrator → Theme Agent
    - Type: Pattern extraction
    - Data: Memory collection

E4: Orchestrator → Voice Agent
    - Type: Style analysis
    - Data: Sample memories

E5: Orchestrator → Narrative Agent
    - Type: Generation request
    - Data: Phase + context

E6: Orchestrator → Coherence Agent
    - Type: Review request
    - Data: All chapters
```

### Data Flow Edges:
```
D1: Interview Agent → Memory Bank
    - Type: Storage
    - Data: New memories

D2: Memory Bank → All Agents
    - Type: Query
    - Data: Filtered memories

D3: Analysis Agents → State Store
    - Type: Results
    - Data: Themes, timeline, voice

D4: Narrative Agent → Output Buffer
    - Type: Chapter storage
    - Data: Generated text

D5: Coherence Agent → Orchestrator
    - Type: Feedback
    - Data: Issues found
```

### Tool Invocation Edges:
```
T1: Agent → Tool Function
    - Type: Synchronous call
    - Data: Pydantic model args

T2: Tool → Agent
    - Type: Return value
    - Data: Processed result
```

## 4c. Flow Weights

### Processing Time Weights:
- Interview: **Heavy** (5-10 min per phase)
- Timeline: **Light** (< 1 min)
- Theme Analysis: **Medium** (2-3 min)
- Voice Analysis: **Light** (< 1 min)
- Chapter Generation: **Heavy** (3-5 min per chapter)
- Coherence Check: **Medium** (2 min)

### Data Volume Weights:
- Memory Collection: **Medium** (50-200 memories)
- Theme Extraction: **Light** (5-15 themes)
- Voice Profile: **Light** (1 profile)
- Generated Text: **Heavy** (60k-120k words)

### LLM Call Weights:
- Interview: **Many** (20-50 calls per phase)
- Analysis: **Few** (5-10 calls per agent)
- Generation: **Many** (10-20 calls per chapter)
- Review: **Few** (5-10 calls total)

## 4d. Graph Build

### System Topology:
```
┌─────────────────────────────────────────────┐
│             Orchestrator                     │
│  ┌────────────────────────────────────┐     │
│  │         State Store                 │     │
│  └────────────────────────────────────┘     │
└──────┬──────┬──────┬──────┬──────┬─────────┘
       │      │      │      │      │
       ↓      ↓      ↓      ↓      ↓
┌──────────┐ ┌──────────┐ ┌──────────┐
│Interview │ │Timeline  │ │Theme     │
│Agent     │ │Agent     │ │Agent     │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     ↓            ↓            ↓
┌─────────────────────────────────────┐
│          Memory Bank                 │
│  - Chronological Index              │
│  - Person Index                     │
│  - Theme Index                      │
└─────────────────────────────────────┘
     ↑            ↑            ↑
     │            │            │
┌──────────┐ ┌──────────┐ ┌──────────┐
│Voice     │ │Narrative │ │Coherence │
│Agent     │ │Agent     │ │Agent     │
└──────────┘ └────┬─────┘ └──────────┘
                  │
                  ↓
            ┌──────────┐
            │Output    │
            │Buffer    │
            └──────────┘
```

## 4e. Simulation

### Load Simulation - Single User:
```
Time    Action                          Active Agents
0:00    Start                          Orchestrator
0:01    Introduction                   Interview
0:05    Childhood memories             Interview
0:15    Adolescence memories           Interview
0:25    Young adult memories           Interview
0:35    Career memories                Interview
0:45    Recent memories                Interview
0:50    Timeline analysis              Timeline
0:52    Theme extraction               Theme
0:55    Voice analysis                 Voice
0:56    Gap detection                  Timeline
1:00    Gap filling                    Interview
1:10    Chapter 1 generation           Narrative
1:15    Chapter 2 generation           Narrative
1:20    Chapter 3 generation           Narrative
1:35    All chapters complete          -
1:37    Coherence review               Coherence
1:40    Final assembly                 Orchestrator
1:42    Complete                       -
```

### Concurrent User Simulation:
```
Users   Interview   Analysis   Generation   Total Time
1       50 min      7 min      35 min       1h 42m
5       250 min     35 min     175 min      2h 30m*
10      500 min     70 min     350 min      4h 00m*

* With parallel processing
```

## 4f. Load Balance

### Agent Scaling Strategy:

**Interview Agents**: 
- Scale horizontally (multiple instances)
- Each handles different life phase
- Session affinity for continuity

**Analysis Agents**:
- Single instance each (stateful)
- Queue requests if needed
- Cache results for reuse

**Narrative Agent**:
- Scale by chapter
- Parallel generation possible
- Merge results at end

### Resource Allocation:
```python
resource_allocation = {
    'orchestrator': {'instances': 1, 'memory': '1GB'},
    'interview_agent': {'instances': 3, 'memory': '2GB'},
    'timeline_agent': {'instances': 1, 'memory': '1GB'},
    'theme_agent': {'instances': 1, 'memory': '2GB'},
    'voice_agent': {'instances': 1, 'memory': '1GB'},
    'narrative_agent': {'instances': 2, 'memory': '4GB'},
    'coherence_agent': {'instances': 1, 'memory': '2GB'},
    'memory_bank': {'instances': 1, 'memory': '4GB'}
}
```

### Bottleneck Mitigation:
1. **Interview Phase**: Parallelize by life period
2. **Generation Phase**: Generate chapters concurrently
3. **Memory Access**: Implement caching layer
4. **LLM Calls**: Batch where possible

## 4g. Topology Map

### Final System Topology:

**Architecture Pattern**: Hub-and-spoke with central orchestration
**Data Pattern**: Shared memory bank with indexed access
**Scaling Pattern**: Horizontal for interviews, vertical for analysis

**Critical Paths**:
1. Interview → Memory Bank → Analysis
2. Analysis → State Store → Generation
3. Generation → Output → Review

**Performance Characteristics**:
- Latency: 1.5-2 hours end-to-end
- Throughput: 5-10 concurrent users
- Memory: 15-20GB total system
- LLM calls: 200-400 per autobiography

**Monitoring Points**:
- Agent response times
- Memory bank size
- Queue depths
- Error rates
- Generation progress

**Failure Recovery**:
- Checkpoint after each phase
- Resumable from any point
- Partial output on failure
- Graceful degradation

This topology ensures efficient autobiography generation while maintaining quality and allowing for scale.
