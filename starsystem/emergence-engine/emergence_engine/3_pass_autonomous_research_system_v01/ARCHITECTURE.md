# 3-Pass Autonomous Research System Architecture

## Overview

This document describes a self-improving research system that studies how different prompting styles affect AI system design quality, while simultaneously building a knowledge base about effective AI system design patterns.

## High-Level Design (HLD)

### Core Concept

The system uses AI to study AI - it runs experiments on how different prompt styles affect the output of a sophisticated system design workflow, learning general principles about effective prompting and system design.

### Three Layers of Functionality

#### 1. Base Layer - The 3-Pass Workflow Engine
- **Purpose**: Consistent experimental apparatus
- **Input**: Domain (e.g., "task manager") + Style (e.g., "focus on simplicity")
- **Process**: Executes the complete 3-pass workflow with 6 phases each
- **Output**: Complete system designs (conceptual model, code, instance)

#### 2. Research Layer - Scientific Method Implementation
- **Purpose**: Systematic experimentation and learning
- **Process**:
  - Forms hypotheses about what the workflow will produce
  - Runs experiments using different styles
  - Analyzes discrepancies between hypothesis and reality
  - Stores findings in knowledge graphs
- **Output**: Validated insights about prompt effectiveness

#### 3. Meta Layer - Self-Improvement System
- **Purpose**: Accumulate and apply cross-domain knowledge
- **Features**:
  - Two-tier knowledge system (Domain-specific vs Self-knowledge)
  - Cross-pollination between domains
  - Knowledge promotion from specific to general
  - Self-restart with accumulated knowledge

### Architectural Genius

The system simultaneously achieves:
1. **Prompt Engineering Research**: Discovers how to better communicate with AI
2. **System Design Research**: Learns what makes good architecture
3. **Meta-Research**: Improves its own research methodology

All three happen in every experiment through the interaction of hypothesis, execution, and analysis.

## Low-Level Design (LLD)

### Implementation Architecture - The Power of Callables

The system uses a layered callable architecture that provides sensible defaults while allowing infinite flexibility:

#### Layer 1: Workflow Execution
```python
run_six_phase_workflow(domain: str, style: str = "") -> Result
```
- Loads MASTER_PROMPT.md
- Appends domain and style
- Gives to ONE agent as its goal via hermes_step
- Agent follows the master prompt to completion
- No orchestration needed - all intelligence is in the prompt

#### Layer 2: Experimental Framework
```python
run_three_pass_system(
    domain: str, 
    style: str = "",
    workflow_callable: Callable = run_six_phase_workflow
) -> Result
```
- By default uses the 3-pass workflow
- Can accept ANY callable for testing different workflows
- Provides the experimental framework

#### Layer 3: Research Orchestration
```python
RunExperimentTool(
    domain: str,
    style: str = "",
    experiment_callable: Callable = run_three_pass_system
) -> Result
```
- By default uses the 3-pass system
- Can accept ANY callable for testing different frameworks
- Called by ResearchAgent

#### Layer 4: Research Agent
- Forms hypotheses
- Calls RunExperimentTool
- Analyzes results
- Manages knowledge

### This Creates Three Systems From One Architecture

1. **Prompt Engineering Research System** (all defaults)
   - ResearchAgent → RunExperimentTool → run_three_pass_system → run_six_phase_workflow
   - Studies how different styles affect the 3-pass workflow

2. **3-Pass Research System** (swap the workflow)
   - ResearchAgent → RunExperimentTool → run_three_pass_system → custom_workflow_function
   - Can test the 3-pass approach with different workflows

3. **General Research System** (swap the framework)
   - ResearchAgent → RunExperimentTool → custom_experiment_function
   - Can test ANY experimental framework

### Agent Specifications

#### ResearchAgent

**Purpose**: Implements the scientific method for studying AI systems

**Tools Required**:

1. **Core Research Tools** (all store results in Neo4j):
   - `FormHypothesisTool` - Creates hypotheses with expected outcomes
   - `DesignExperimentTool` - Designs controlled experiments  
   - `AnalyzeResultsTool` - Compares hypothesis vs reality
   - `DrawConclusionsTool` - Extracts insights and patterns
   - `RunExperimentTool` - Executes experiments (calls run_three_pass_system)

2. **Knowledge Management Tools**:
   - `CypherQueryDomainSpecificKnowledgeTool` - Query domain findings
   - `CypherQuerySelfStoredKnowledgeTool` - Query general principles
   - `PromoteKnowledgeTool` - Elevate domain findings to self-knowledge

3. **Analysis Tools**:
   - `NetworkFileViewerTool` - Read experiment outputs
   - `ViewHistoryTool` - Review experiment conversation histories

4. **Meta Tools**:
   - `RestartWithContextTool` - Reinitialize with accumulated knowledge

**Location**: `/agents/research/`

#### WorkflowAgent

**Purpose**: Executes the 3-pass system design workflow

**Tools Required**:
- `NetworkEditTool` - Create/edit files anywhere in Docker network
- `BashTool` - Execute commands, run code, manage containers

**Process**:
1. Receives master prompt + domain + style
2. Follows the 3-pass workflow autonomously
3. Writes all outputs to files
4. Completes all 18 steps (3 passes × 6 phases) in one execution

**Location**: `/agents/workflow/`

### Knowledge Graph Structure

#### Domain-Specific Knowledge
```cypher
(:Experiment {
    id: string,
    domain: string,
    style: string,
    hypothesis: string,
    conclusions: string,
    timestamp: datetime
})-[:TESTED_DOMAIN]->(:Domain {name: string})

(:Experiment)-[:PRODUCED]->(:Insight {
    id: string,
    description: string,
    confidence: float
})
```

#### Self-Knowledge (Promoted Insights)
```cypher
(:SelfKnowledge {
    id: string,
    description: string,
    confidence: float,
    validation_count: int,
    promoted_from: string,
    rationale: string
})-[:APPLIES_TO]->(:Concept)

(:SelfKnowledge)-[:DERIVED_FROM]->(:Insight)
```

#### Cross-Domain Relationships
```cypher
(:Domain)-[:SIMILAR_TO {similarity: float}]->(:Domain)
(:Experiment)-[:CONTRADICTS]->(:Experiment)
(:Insight)-[:SUPPORTS]->(:Insight)
```

### Research Workflow

1. **Check Existing Knowledge**
   - Query self-knowledge for general principles
   - Query domain knowledge for specific insights
   - Identify knowledge gaps

2. **Form Hypothesis**
   - Based on existing knowledge + gaps
   - Include expected outcomes
   - Design controlled variables

3. **Run Experiment**
   - Call RunExperimentTool with domain + style
   - Workflow executes completely
   - Outputs saved to files

4. **Analyze Results**
   - Compare hypothesis to actual outputs
   - Identify unexpected patterns
   - Extract insights

5. **Store Knowledge**
   - Save experiment + conclusions to Neo4j
   - Create relationships to other experiments
   - Promote significant insights to self-knowledge

6. **Cross-Pollinate** (when applicable)
   - Find adjacent domains
   - Test insight transfer
   - Discover meta-patterns

### File Structure

```
/agents/
├── research/
│   ├── research_agent.py
│   └── research_test.py
└── workflow/
    ├── workflow_agent.py
    └── workflow_test.py

/workspace/
└── experiments/
    └── {domain}_{timestamp}/
        ├── pass1/
        │   ├── abstract_goal.md
        │   ├── systems_design.md
        │   └── ... (other phases)
        ├── pass2/
        └── pass3/
```

### Key Design Decisions

1. **One Agent, One Goal**: The workflow agent receives the complete master prompt and executes autonomously

2. **File-Based State**: No complex context management - files naturally preserve state between phases

3. **Callable Architecture**: Every layer can be swapped out for different experiments

4. **Knowledge Hierarchy**: Domain-specific findings can be promoted to general principles

5. **Cypher for Analysis**: The research agent writes custom queries instead of using pre-built comparison tools

### Success Metrics

- Number of validated insights promoted to self-knowledge
- Consistency of findings across domains
- Improvement in hypothesis accuracy over time
- Discovery of non-obvious cross-domain patterns

## Summary

This architecture creates a research system that can:
- Study any domain using any workflow
- Learn general principles from specific experiments
- Apply knowledge across domains
- Improve its own research methodology
- Generate actual working systems as a byproduct of research

The genius lies in its simplicity: one agent following a sophisticated prompt, wrapped in a scientific method framework, accumulating knowledge over time.