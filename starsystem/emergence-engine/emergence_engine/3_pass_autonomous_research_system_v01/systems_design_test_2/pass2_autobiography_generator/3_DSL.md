# Phase 3: Domain Specific Language - Autobiography Generator System

## 3a. Concept Tokenize

### Agent Communication Concepts:
- **Prompt**: Instruction to agent with context
- **Response**: Agent output with potential tool calls
- **History**: Conversation state with messages
- **Tool Call**: Structured function invocation
- **Error State**: Failure modes and recovery

### Memory Management Concepts:
- **Memory Object**: Structured life experience
- **Memory Bank**: Indexed storage system
- **Timeline**: Chronological organization
- **Phase**: Life period grouping
- **Gap**: Missing temporal coverage

### Analysis Concepts:
- **Theme**: Recurring life pattern
- **Voice Profile**: Linguistic characteristics
- **Relationship Map**: Person connections
- **Evolution**: Change over time
- **Pattern**: Recurring elements

### Generation Concepts:
- **Scene**: Narrative rendering of memory
- **Transition**: Connection between scenes
- **Reflection**: Commentary on past
- **Chapter**: Complete life phase narrative
- **Coherence**: Consistency across elements

## 3b. Syntax Define

### Agent Communication Syntax:
```python
# Basic agent interaction
agent.run(prompt: str) -> {
    'history_id': str,
    'history': History(messages=[Message(content=str)]),
    'error': Optional[str]
}

# Tool definition
@tool
def function_name(args: PydanticModel) -> ReturnType:
    """Tool description"""
    pass

# Agent with tools
agent = Agent(role="role_name", tools=[tool1, tool2])
```

### Memory Structure Syntax:
```python
Memory(
    id=generated,
    content=text,
    memory_type=MemoryType.VALUE,
    year=Optional[int],
    people=List[str],
    emotions=List[str],
    significance=str
)
```

### Orchestration Syntax:
```python
orchestrator.phase_1() -> state_update
orchestrator.phase_2() -> state_update
...
orchestrator.final_assembly() -> autobiography
```

## 3c. Semantic Rules

### Agent Interaction Rules:
- Each agent has single responsibility
- Agents communicate through orchestrator
- Tools must have Pydantic models for args
- Responses must be parsed for tool calls
- Errors must be handled gracefully

### Memory Coherence Rules:
- Memories must have temporal anchor (year/age)
- Significance must explain importance
- Related memories must be bidirectional
- People mentioned must be indexed
- Emotions must be from valid set

### Generation Rules:
- Voice must be consistent across chapters
- Themes must appear multiple times
- Timeline must be logically consistent
- Reflections must feel authentic
- Transitions must be smooth

## 3d. Operator Set

### Memory Operators:
- **STORE**: Add memory to bank
- **QUERY**: Retrieve by criteria
- **LINK**: Connect related memories
- **INDEX**: Update search indices

### Analysis Operators:
- **EXTRACT**: Pull patterns from data
- **CLUSTER**: Group similar items
- **TRACE**: Follow evolution over time
- **COMPARE**: Find similarities/differences

### Generation Operators:
- **RENDER**: Transform memory to prose
- **WEAVE**: Integrate theme into narrative
- **VOICE**: Apply linguistic style
- **BRIDGE**: Create transitions

### Quality Operators:
- **VERIFY**: Check consistency
- **MEASURE**: Assess quality metrics
- **IDENTIFY**: Find issues
- **CORRECT**: Apply fixes

## 3e. Validation Tests

### System Validation:
```python
# Test: Agent responds correctly
agent = Agent(role="test")
result = agent.run("test prompt")
assert 'history_id' in result
assert 'history' in result
assert hasattr(result['history'], 'messages')

# Test: Tool calls work
@tool
def test_tool(arg: TestModel) -> str:
    return f"Processed {arg.value}"

agent = Agent(role="test", tools=[test_tool])
# Agent should be able to call tool

# Test: Memory storage
bank = MemoryBank()
memory = Memory(content="Test", significance="Test")
id = bank.store(memory)
assert bank.memories[id] == memory
```

### Content Validation:
```python
# Test: Timeline coherence
memories = bank.get_by_period(1980, 1990)
for i in range(len(memories)-1):
    assert memories[i].year <= memories[i+1].year

# Test: Theme extraction
themes = theme_agent.analyze_themes()
assert all(len(theme.related_memories) >= 3 for theme in themes)

# Test: Voice consistency
voice1 = voice_agent.analyze_voice(sample1)
voice2 = voice_agent.analyze_voice(sample2)
assert similarity(voice1, voice2) > 0.8
```

## 3f. DSL Specification

### Core Language Elements:

**Agent Protocol**:
- Agents initialized with role and tools
- Communicate via run(prompt) method
- Return structured responses
- Can invoke tools based on context

**Memory Protocol**:
- Memories are structured objects
- Must include content and significance
- Temporal anchoring preferred
- Indexed by multiple dimensions

**Generation Protocol**:
- Phases proceed sequentially
- State maintained across phases
- Each phase produces artifacts
- Final assembly combines all

### Composition Rules:
```
Autobiography = Introduction() 
              + CollectMemories()
              + AnalyzeStructure() 
              + AnalyzeVoice()
              + FillGaps()
              + GenerateChapters()
              + ReviewCoherence()
              + ApplyFixes()
              + FinalAssembly()
```

### Error Handling:
```
try:
    result = agent.run(prompt)
except AgentError:
    fallback_strategy()
    
if result['error']:
    handle_error(result['error'])
```

This DSL provides the conceptual framework for how agents, memories, and generation processes interact within the autobiography generator system.
