# The Agent Framework Stub Pattern

## Why Stubbing Matters

When designing complex systems, implementation details can obscure conceptual clarity. By stubbing the agent framework, we separated WHAT agents do from HOW they do it, enabling clear architectural thinking.

## The Stub Pattern We Used

### Core Interface
```python
class Agent:
    def __init__(self, role: str, tools: List[callable] = None):
        self.role = role
        self.tools = tools or []
    
    def run(self, prompt: str) -> Dict:
        """
        Stub for LLM call
        Returns: {
            'history_id': str,
            'history': History object with .history_id and .messages,
            'error': Optional[str]
        }
        """
        pass  # Implementation hidden
```

### Why This Works

1. **Hides Complexity**: We don't worry about LLM APIs, token limits, retry logic
2. **Focuses on Architecture**: We can design agent interactions clearly
3. **Enables Testing**: Can mock responses for testing system behavior
4. **Postpones Decisions**: LLM provider choice can come later

## The Tool Pattern

```python
@tool
def extract_memory(text: str) -> Memory:
    """Tool with Pydantic model for type safety"""
    pass  # Implementation hidden
```

Tools are:
- Functions with typed inputs (Pydantic models)
- Clear responsibilities
- Testable in isolation
- Composable by agents

## How Stubbing Enabled Our Design

### 1. **Clear Agent Responsibilities**
Because we didn't get lost in implementation, we could clearly define:
- InterviewAgent: Elicits memories
- ThemeAgent: Finds patterns
- NarrativeAgent: Generates prose

### 2. **Clean Data Flow**
```python
# We could focus on WHAT flows, not HOW
result = agent.run(prompt)  # Simple interface
memory = tool(result)       # Clear transformation
bank.store(memory)          # Obvious storage
```

### 3. **Architectural Flexibility**
The stub pattern meant we could:
- Swap LLM providers
- Change prompt strategies
- Modify tool implementations
- All without changing architecture

## The Conceptual Clarity

By stubbing, we achieved:

```
Conceptual Level (What):
    Agent asks questions → Gets responses → Extracts memories

Implementation Level (How):
    HTTP call to OpenAI → Parse JSON → Validate with Pydantic
```

We stayed at the conceptual level throughout Pass 2 design!

## Stubbing Best Practices

### 1. **Define Clear Contracts**
```python
# Clear input/output types
def run(self, prompt: str) -> Dict[str, Any]:
    # Always returns same structure
    return {
        'history_id': str,
        'history': History,
        'error': Optional[str]
    }
```

### 2. **Hide Implementation Details**
```python
# Don't expose:
# - API keys
# - Retry logic  
# - Token counting
# - Provider-specific details
```

### 3. **Focus on Domain Logic**
```python
# Good: Domain-focused
interview_agent.conduct_interview(life_phase)

# Bad: Implementation-focused
interview_agent.call_openai_with_retry(prompt, max_tokens=2000)
```

## The Power of Abstraction

This stubbing approach is itself an application of the three-pass system:

1. **Pass 1**: What IS an agent? (Something that processes prompts and returns responses)
2. **Pass 2**: How do we MAKE agents? (Create the stub interface)
3. **Pass 3**: How do we make THIS agent? (Implement specific behavior)

## Practical Benefits

### During Design:
- Faster iteration on architecture
- Clearer team communication
- Focus on business logic
- Testable designs

### During Implementation:
- Clear interfaces to implement
- Parallel development possible
- Easy to swap implementations
- Natural test boundaries

## Example: Evolution of Understanding

```python
# First thought (too specific):
class OpenAIAgent:
    def __init__(self, api_key, model="gpt-4"):
        self.client = OpenAI(api_key)
        
# Better (but still coupled):
class LLMAgent:
    def __init__(self, provider):
        self.provider = provider
        
# Best (fully abstracted):
class Agent:
    def run(self, prompt: str) -> Dict:
        pass  # Pure interface
```

## Key Insight

By stubbing the agent framework, we could think about the autobiography generation system at the right level of abstraction. We designed a multi-agent choreography without getting tangled in API details, token limits, or retry logic.

This is the power of proper abstraction: it lets you solve the right problems at the right time.

## Applying This Pattern

When designing your own systems:

1. **Start with stubs** for any complex external dependencies
2. **Define clear interfaces** based on domain needs
3. **Focus on interactions** not implementations
4. **Defer implementation details** until architecture is solid
5. **Keep stubs even after implementing** for testing

Remember: The goal is conceptual clarity first, implementation excellence second. Stubbing helps maintain this priority.
