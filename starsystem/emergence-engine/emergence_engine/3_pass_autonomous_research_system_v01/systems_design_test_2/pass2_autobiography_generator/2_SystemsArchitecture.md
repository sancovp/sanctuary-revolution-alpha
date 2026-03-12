# Phase 2: Systems Architecture - Multi-Agent Autobiography Generator

## 2a. Function Decomposition

### Core System Functions:

**F1: Memory Elicitation**
- Input: Life phase, existing memories
- Process: Conversational interview via agent.run()
- Output: Structured Memory objects

**F2: Memory Storage**
- Input: Memory objects
- Process: Index by time, person, theme
- Output: Searchable memory bank

**F3: Timeline Construction**
- Input: All memories
- Process: Chronological ordering, phase detection
- Output: LifePhase objects, gap identification

**F4: Theme Extraction**
- Input: Memory collection
- Process: Pattern recognition via LLM
- Output: Theme objects with evolution

**F5: Voice Analysis**
- Input: Memory text samples
- Process: Linguistic feature extraction
- Output: Voice profile dictionary

**F6: Narrative Generation**
- Input: Phase, memories, themes, voice
- Process: Scene creation, transitions
- Output: Chapter text

**F7: Coherence Verification**
- Input: All chapters
- Process: Consistency checking
- Output: Issues and fixes

**F8: Final Assembly**
- Input: All components
- Process: Ordering, formatting
- Output: Complete autobiography

## 2b. Module Grouping

### Module 1: Interview System
- InterviewAgent
- Memory elicitation tools
- Conversation state management

### Module 2: Storage System
- MemoryBank class
- Indexing mechanisms
- Query interfaces

### Module 3: Analysis System
- TimelineAgent
- ThemeAgent  
- VoiceAgent
- Pattern recognition tools

### Module 4: Generation System
- NarrativeAgent
- Scene creation tools
- Voice application

### Module 5: Quality System
- CoherenceAgent
- Verification tools
- Fix application

### Module 6: Orchestration System
- AutobiographyOrchestrator
- State management
- Progress tracking

## 2c. Interface Definition

### Agent Interfaces:
```python
class Agent:
    def run(prompt: str) -> Dict:
        # Returns: {history_id, history, error}
        
    tools: List[callable]  # Available tools
```

### Tool Interfaces:
```python
# All tools use Pydantic models for args
tool(args: PydanticModel) -> ReturnType
```

### Inter-Module Interfaces:
```
Interview → Storage: Memory objects
Storage → Analysis: Memory queries
Analysis → Generation: Themes, timeline, voice
Generation → Quality: Chapter text
Quality → Generation: Fix requests
Orchestration → All: Coordination
```

## 2d. Layer Stack

```
Layer 5: User Interface Layer
- Progress updates
- Configuration input  
- Final output

Layer 4: Orchestration Layer
- AutobiographyOrchestrator
- State management
- Error handling

Layer 3: Processing Layer
- Specialized agents
- LLM interactions
- Tool executions

Layer 2: Data Layer
- MemoryBank
- Theme storage
- Voice profiles

Layer 1: Infrastructure Layer
- Agent base class
- Tool registration
- Message handling
```

## 2e. Control Flow

```
Start → User Configuration
           ↓
    Introduction Interview
           ↓
    ┌─ Memory Collection Loop ←─┐
    │      ↓                    │
    │  Interview by Phase       │
    │      ↓                    │
    │  Store Memories          │
    │      ↓                    │
    └─ More Phases? ────Yes────┘
           │ No
           ↓
    Structure Analysis
    (Timeline + Themes)
           ↓
    Voice Analysis
           ↓
    Gap Detection
           ↓
    Fill Gaps? ──Yes──→ Targeted Interviews
        │ No                    │
        ↓←──────────────────────┘
    Generate Chapters
           ↓
    Coherence Check
           ↓
    Apply Fixes? ──Yes──→ Revise Chapters
        │ No                    │
        ↓←──────────────────────┘
    Final Assembly
           ↓
        Output
```

## 2f. Data Flow

```
User Intent → Interview Prompts → Raw Conversations
                                        ↓
                              Structured Memories
                    ↓               ↓            ↓
            Timeline/Phases    Themes      Voice Profile
                    ↓               ↓            ↓
                    └───────────────┴────────────┘
                                   ↓
                            Chapter Outlines
                                   ↓
                           Generated Prose
                                   ↓
                          Coherence Checks
                                   ↓
                       Final Autobiography
```

## 2g. Redundancy Plan

- **Memory Redundancy**: Related memories cross-referenced
- **Theme Redundancy**: Multiple extraction passes
- **Voice Redundancy**: Sampled across all phases
- **Generation Redundancy**: Multiple drafts if needed
- **Save State**: Can resume from any phase

## 2h. Architecture Specification

### Key Decisions:

1. **Agent Specialization**: Each agent masters one aspect
2. **Central Memory Store**: Single source of truth
3. **Tool-Based Operations**: Typed, testable functions
4. **State Machine**: Clear phases with checkpoints
5. **Graceful Degradation**: Partial output on failure

### Quality Attributes:
- **Reliability**: Checkpoint after each phase
- **Scalability**: Can handle 50-500 memories
- **Maintainability**: Clear module boundaries
- **Extensibility**: Easy to add new agents/tools
- **Testability**: Each component independently testable
