# Visual Architecture: How Everything Connects

## The Three Nested Loops

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  RESEARCH LOOP: "What's the best workflow structure?"               │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                                                                 │ │
│  │  Workflow Variant A ──┐                                        │ │
│  │  Workflow Variant B ──┼── Test Each ──→ Measure ──→ Evolve    │ │
│  │  Workflow Variant C ──┘                                        │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                    │                                 │
│                          Each Test Runs:                             │
│                                    ↓                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                                                                 │ │
│  │  UNDERSTANDING LOOP: "Can the LLM use this workflow?"          │ │
│  │  ┌────────────────────────────────────────────────────────┐    │ │
│  │  │                                                         │    │ │
│  │  │  Start → Confused? → Correct → Try Again              │    │ │
│  │  │    ↓                              ↓                    │    │ │
│  │  │  Understanding → Apply Three-Pass System               │    │ │
│  │  │                                                         │    │ │
│  │  └────────────────────────────────────────────────────────┘    │ │
│  │                                ↓                                │ │
│  │                     Three-Pass Execution:                       │ │
│  │  ┌────────────────────────────────────────────────────────┐    │ │
│  │  │                                                         │    │ │
│  │  │  THREE-PASS: "Build the actual system"                 │    │ │
│  │  │                                                         │    │ │
│  │  │  [Workflow] → Pass 1: What IS it?                     │    │ │
│  │  │      ↓                                                 │    │ │
│  │  │  [Workflow] → Pass 2: How MAKE them?                  │    │ │
│  │  │      ↓                                                 │    │ │
│  │  │  [Workflow] → Pass 3: Make THIS one                   │    │ │
│  │  │      ↓                                                 │    │ │
│  │  │   Output: Working System                               │    │ │
│  │  │                                                         │    │ │
│  │  └────────────────────────────────────────────────────────┘    │ │
│  │                                                                 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## The Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR AGENT                            │
│                   "I manage the entire process"                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ RESEARCH AGENT  │  │ UNDERSTANDING    │  │ EVOLUTION AGENT │    │
│  │                 │  │ MANAGER          │  │                 │    │
│  │ "I test         │  │                  │  │ "I create new   │    │
│  │  workflows"     │  │ "I detect and    │  │  workflows"     │    │
│  │                 │  │  fix confusion"  │  │                 │    │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘    │
│           │                    │                     │              │
│           ↓                    ↓                     ↑              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    THREE-PASS AGENTS                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │   PASS 1    │  │   PASS 2    │  │   PASS 3    │         │   │
│  │  │             │  │             │  │             │         │   │
│  │  │ "What IS?"  │→ │ "How MAKE?" │→ │"Make THIS!" │         │   │
│  │  │             │  │             │  │             │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                            │                                        │
│                            ↓                                        │
│                   ┌─────────────────┐                              │
│                   │ REFLECTION AGENT │                              │
│                   │                  │                              │
│                   │ "What did we    │                              │
│                   │  learn?"         │                              │
│                   └─────────────────┘                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## The Workflow Evolution Process

```
Generation 0:
┌─────────────────────────────────────┐
│ (0)[Goal]→(1)[Design]→(2)[Build]    │ ← Original
└─────────────────────────────────────┘

Generation 1:                            Mutations:
┌─────────────────────────────────────┐  • Add phase
│ (0)[Goal]→(1)[Analyze]→(2)[Build]   │  • Change word
├─────────────────────────────────────┤  • Reorder
│ (0)[Goal]→(1)[Design]→(2)[Code]     │  • Remove phase
├─────────────────────────────────────┤  • Split phase
│ (0)[Why]→(1)[What]→(2)[How]         │  • Merge phases
└─────────────────────────────────────┘

Generation 2:                            Selection:
┌─────────────────────────────────────┐  ✓ Keep best
│ (0)[Why]→(1)[What]→(2)[How]→(3)[Do] │  ✗ Drop worst
└─────────────────────────────────────┘  ⚡ Combine good

Generation N:
┌─────────────────────────────────────────────┐
│ [Optimal workflow discovered through evolution] │
└─────────────────────────────────────────────┘
```

## Data Flow Through the System

```
1. RESEARCH AGENT
   └→ "Test workflow variant X"
   
2. ORCHESTRATOR
   └→ "Give variant X to Understanding Manager"
   
3. UNDERSTANDING MANAGER  
   └→ "LLM seems confused"
   └→ "Activate correction"
   └→ "Now understanding"
   
4. THREE-PASS AGENTS
   └→ Pass 1: "I understand what a task manager IS"
   └→ Pass 2: "Here's code for a task manager generator"
   └→ Pass 3: "Here's a specific task manager instance"
   
5. REFLECTION AGENT
   └→ "Quality score: 85/100"
   └→ "Interesting patterns found"
   └→ "Workflow handled domain well"
   
6. EVOLUTION AGENT
   └→ "Based on results, try adding 'Patterns' phase"
   
7. BACK TO RESEARCH AGENT
   └→ "Test new variant..."
```

## The Key Insight Visualized

```
Traditional Approach:
Human → Writes Prompt → Tests → Adjusts → Repeat
         (Slow, Limited)

Our Approach:
System → Generates Many Prompts → Tests All → Evolves Best → Repeat
         (Fast, Unlimited)

The Meta-Level:
System that Evolves → Systems that Build → Systems
                      ↑                      ↓
                      └──────Feedback────────┘
                        (Self-Improving!)
```

## Why This Architecture Works

### 1. Separation of Concerns
Each agent has ONE job:
- Research: Run experiments
- Understanding: Handle confusion
- Pass 1/2/3: Execute their pass
- Reflection: Analyze results
- Evolution: Create variations

### 2. The Workflow is a Variable
```python
# Not this:
def build_system():
    # Hardcoded steps
    
# But this:
def build_system(workflow):
    # workflow determines steps!
```

### 3. Learning is Built In
- Confusion → Correction
- Success → Reinforcement  
- Patterns → Evolution

### 4. It's Recursive
The system can be applied to itself:
- Use the system to improve the system
- Use improvements to improve the improver
- And so on...

## The End Goal

```
┌────────────────────────────────────────────┐
│   INPUT: "Build me an X system"            │
└──────────────────┬─────────────────────────┘
                   ↓
┌────────────────────────────────────────────┐
│   SYSTEM: Selects optimal workflow         │
│           Handles any confusion             │
│           Builds complete system            │
│           Learns from experience            │
└──────────────────┬─────────────────────────┘
                   ↓
┌────────────────────────────────────────────┐
│   OUTPUT: Working X system                 │
│           + Documentation                   │
│           + Insights for next time          │
└────────────────────────────────────────────┘
```

And it keeps getting better with each use.