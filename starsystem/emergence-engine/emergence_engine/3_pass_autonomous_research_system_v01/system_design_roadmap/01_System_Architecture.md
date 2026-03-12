# Multi-Agent System Architecture for Self-Evolving System Design

## The Complete Architecture

We're building a multi-level system with three nested loops:

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESEARCH WORKFLOW (Outer Loop)                │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              UNDERSTANDING LOOP (Middle Loop)                ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │            3-PASS SYSTEM (Inner Loop)                   │││
│  │  │                                                          │││
│  │  │  Workflow Variable → Pass 1 → Pass 2 → Pass 3 → Output  │││
│  │  │                                                          │││
│  │  └─────────────────────────────────────────────────────────┘││
│  │                              ↓                               ││
│  │  Confusion → Correction → Understanding → Application       ││
│  │      ↑                                         ↓            ││
│  │      └── Meta-Reflection ← Documentation ← Reflection       ││
│  │                                                              ││
│  └──────────────────────────────────────────────────────────────┘│
│                                ↓                                  │
│     Measure Results → Evolve Workflow → Test New Variant         │
│              ↑                                    ↓               │
│              └────────────────────────────────────┘               │
└───────────────────────────────────────────────────────────────────┘
```

## The Agent System

### Core Agents

#### 1. Orchestrator Agent
- Manages the entire system
- Switches between research, understanding, and 3-pass modes
- Tracks state and progress
- Handles workflow variable injection

#### 2. Research Controller
- Generates workflow variations
- Measures fitness scores
- Manages evolution process
- Selects best performers

#### 3. Understanding Manager
- Detects confusion vs understanding states
- Routes to appropriate handlers
- Tracks learning progress
- Triggers meta-reflection

#### 4. Pass 1 Agent (Conceptualizer)
- Executes Pass 1 with current workflow
- Focuses on "What IS?"
- Prevents implementation thinking
- Outputs ontology

#### 5. Pass 2 Agent (System Builder)
- Executes Pass 2 with current workflow
- Focuses on "How MAKE?"
- Generates actual code
- Outputs generator system

#### 6. Pass 3 Agent (Instance Creator)
- Executes Pass 3 with current workflow
- Focuses on "Make THIS"
- Creates specific instances
- Outputs concrete result

#### 7. Reflection Agent
- Analyzes outputs from all passes
- Identifies patterns and insights
- Documents learnings
- Feeds back to Understanding Manager

#### 8. Evolution Agent
- Takes reflection outputs
- Generates new workflow mutations
- Combines successful patterns
- Feeds to Research Controller

## The Key Innovation

**The workflow structure is a VARIABLE that gets injected into the 3-pass system**

```python
class ThreePassSystem:
    def __init__(self, workflow_structure):
        self.workflow = workflow_structure  # This changes!
        self.pass1_agent = Pass1Agent(workflow)
        self.pass2_agent = Pass2Agent(workflow)
        self.pass3_agent = Pass3Agent(workflow)
    
    def execute(self, domain):
        # The SAME 3-pass process
        ontology = self.pass1_agent.conceptualize(domain)
        generator = self.pass2_agent.build_system(ontology)
        instance = self.pass3_agent.create_instance(generator)
        return ontology, generator, instance
```

## The Data Flow

```
1. Research Controller → Workflow Variant
2. Workflow → Three-Pass System
3. Three-Pass → Understanding Loop (if confusion)
4. Understanding Loop → Outputs
5. Outputs → Reflection Agent
6. Reflection → Evolution Agent
7. Evolution → New Workflow Variants
8. Loop back to 1
```

## What Makes This Powerful

1. **Self-Improving**: The system improves its own core prompts
2. **Learning-Aware**: It handles confusion and builds understanding
3. **Multi-Level**: Each level can optimize independently
4. **Emergent**: New patterns can emerge at any level
5. **Recursive**: The system can be applied to itself

## The Implementation Stack

```
┌─────────────────────────┐
│   Web Interface/CLI     │ ← User interaction
├─────────────────────────┤
│  Orchestrator Service   │ ← Main control loop
├─────────────────────────┤
│   Agent Pool:           │
│  - Research Controller  │
│  - Understanding Mgr    │ ← All agents
│  - Pass 1/2/3 Agents   │
│  - Reflection Agent     │
│  - Evolution Agent      │
├─────────────────────────┤
│   LLM Interface Layer   │ ← Claude/GPT API calls
├─────────────────────────┤
│   State Management      │ ← Track progress
├─────────────────────────┤
│   Data Storage          │ ← Results, variants, history
└─────────────────────────┘
```

## The Research Question

**Can a system that evolves its own system-building prompts discover fundamentally better ways to help LLMs design and build complex systems?**

We're about to find out.