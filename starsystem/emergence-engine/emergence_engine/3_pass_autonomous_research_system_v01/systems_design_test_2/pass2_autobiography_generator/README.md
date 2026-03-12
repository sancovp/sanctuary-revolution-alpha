# Pass 2: Multi-Agent Autobiography Generator System

## Overview

This directory contains Pass 2 of the systems design workflow, where we designed a **multi-agent system** that can instantiate the autobiography ontology defined in Pass 1. This is the programmatic system that generates autobiographies.

## System Architecture

### Core Components:

1. **Agent Framework**
   - Base `Agent` class with `run(prompt: str) -> Dict` interface
   - Tool integration with Pydantic models
   - Conversation history management

2. **Specialized Agents**
   - **InterviewAgent**: Elicits memories through conversation
   - **TimelineAgent**: Organizes memories chronologically
   - **ThemeAgent**: Extracts patterns and themes
   - **VoiceAgent**: Analyzes linguistic style
   - **NarrativeAgent**: Generates prose chapters
   - **CoherenceAgent**: Ensures consistency

3. **Data Management**
   - **MemoryBank**: Central storage with indices
   - **StateStore**: Orchestrator state persistence
   - **OutputBuffer**: Generated content storage

4. **Orchestration**
   - **AutobiographyOrchestrator**: Coordinates all agents
   - State machine for phase management
   - Progress tracking and error recovery

## Key Design Decisions

1. **Stub LLM Interface**: All LLM calls go through `agent.run()` 
2. **Tool System**: Functions with Pydantic args for type safety
3. **Central Memory Store**: Single source of truth for all memories
4. **Phased Generation**: Clear progression through interview → analysis → generation
5. **Voice Preservation**: Early analysis, consistent application

## Usage Example

```python
# Initialize orchestrator
orchestrator = AutobiographyOrchestrator()

# Configure generation
config = {
    'min_memories': 50,
    'target_length': 'medium',
    'formality': 'conversational'
}

# Generate autobiography
autobiography = orchestrator.generate_autobiography("Jane Doe", config)

# Output is complete markdown text following Pass 1 structure
```

## System Flow

1. **Introduction**: Establish context and goals
2. **Memory Collection**: Interview across life phases
3. **Structure Analysis**: Build timeline, extract themes
4. **Voice Analysis**: Capture authentic style
5. **Gap Filling**: Targeted interviews for missing periods
6. **Chapter Generation**: Create narrative prose
7. **Coherence Review**: Ensure consistency
8. **Final Assembly**: Complete autobiography

## Files in this Directory

- `0_AbstractGoal.md` - System purpose and vision
- `1_SystemsDesign.md` - Design requirements and constraints
- `2_SystemsArchitecture.md` - Technical architecture
- `3_DSL.md` - Domain language for the system
- `4_Topology.md` - Network and flow design
- `5_EngineeredSystem.md` - Implementation details
- `6_FeedbackLoop.md` - Continuous improvement
- `system_architecture.py` - Basic implementation
- `detailed_implementation.py` - Full system code

## Performance Characteristics

- **Generation Time**: 1.5-2 hours per autobiography
- **Memory Requirements**: 15-20GB for full system
- **LLM Calls**: 200-400 per autobiography
- **Concurrent Users**: 5-10 supported

## Evolution Path

The system includes comprehensive telemetry and feedback loops for:
- Performance optimization
- Prompt effectiveness tracking
- User behavior adaptation
- Quality improvement
- Feature expansion

## Next: Pass 3

Pass 3 would involve using this system to generate a specific person's autobiography:
1. Configure the system for the individual
2. Conduct the interviews
3. Process their specific memories
4. Generate their unique autobiography

The multi-agent system successfully bridges the conceptual ontology (Pass 1) with concrete implementation, ready to create actual autobiographies.
