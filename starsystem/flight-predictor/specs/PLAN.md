# Capability Reasoning System - Implementation Plan

## Vision
Build a meta-learning harness for capability prediction that:
- Predicts what skills/tools you need based on intent
- Tracks what you actually use
- Detects mismatch (learning signal)
- Improves predictions over time

## Phase 1: Rebuild RAG Functions (CartON-style)

### 1.1 Skill RAG Rebuild
**Current:** ChromaDB flat embedding search → top K matches
**Target:** RAG → Graph Traversal → Hierarchical Aggregation

```
Query "planning"
    ↓
ChromaDB finds: starlog, waypoint, flight-config (entry points)
    ↓
Neo4j traversal:
  - starlog PART_OF navigation_skillset
  - waypoint PART_OF navigation_skillset
  - flight-config PART_OF navigation_skillset
    ↓
Aggregation: Navigation domain (high confidence)
    ↓
Output: Hierarchical prediction with relationships
```

**Tasks:**
- [ ] Create skill graph schema in Neo4j (Skill, Skillset, Domain nodes)
- [ ] Sync existing skills to Neo4j with relationships
- [ ] Build `skill_rag_carton_style(query)` function
- [ ] Test independently

### 1.2 Tool RAG Rebuild
**Current:** BM25 keyword search → flat list
**Target:** RAG → Graph Traversal → Hierarchical Aggregation

```
Query "dependency analysis"
    ↓
BM25/embedding finds: get_dependency_context, parse_repo (entry points)
    ↓
Neo4j traversal:
  - get_dependency_context PART_OF context-alignment server
  - parse_repo PART_OF context-alignment server
    ↓
Aggregation: context-alignment MCP (high confidence)
    ↓
Output: Hierarchical prediction with relationships
```

**Tasks:**
- [ ] Create tool graph schema in Neo4j (Tool, Server, Domain nodes)
- [ ] Sync tool catalog to Neo4j with relationships
- [ ] Build `tool_rag_carton_style(query)` function
- [ ] Test independently

## Phase 2: Join into One Tool with Schema

### 2.1 Schema Design (like be_myself awareness)
```python
class PlanStep(BaseModel):
    step_number: int
    description: str  # Natural language intent

class CapabilityObservation(BaseModel):
    """What you submit to get predictions"""
    steps: List[PlanStep]
    context_domain: Optional[str]  # e.g., "PAIAB", "CAVE", "SANCTUM"

class StepPrediction(BaseModel):
    step_number: int
    description: str
    predicted_skills: List[dict]  # name, confidence, skillset, domain
    predicted_tools: List[dict]   # name, confidence, server, domain
    aggregated_domains: List[str] # Top domains for this step

class CapabilityPrediction(BaseModel):
    """What you get back"""
    steps: List[StepPrediction]
    overall_domains: List[str]
    recommendations: str
```

### 2.2 Single Tool
```python
@mcp.tool()
def predict_capabilities(observation: CapabilityObservation) -> CapabilityPrediction:
    """
    Input your plan, get predicted capabilities.
    """
    predictions = []
    for step in observation.steps:
        skill_hits = skill_rag_carton_style(step.description)
        tool_hits = tool_rag_carton_style(step.description)
        predictions.append(aggregate_and_format(step, skill_hits, tool_hits))
    return CapabilityPrediction(steps=predictions, ...)
```

**Tasks:**
- [ ] Define Pydantic schemas
- [ ] Implement `predict_capabilities()` joining both RAGs
- [ ] Create MCP server wrapper
- [ ] Test end-to-end

## Phase 3: Tuning System

### 3.1 Observation Recording
When you ACTUALLY USE a skill/tool, record it:
```python
class ActualUsage(BaseModel):
    session_id: str
    step_description: str
    predicted: List[str]  # What we predicted
    actual: List[str]     # What was actually used
    mismatch: List[str]   # Delta (missed predictions, false positives)
```

### 3.2 Rollup/Compilation
Aggregate observations to find patterns:
```
"plan" → [starlog: 95%, waypoint: 80%, flight-config: 60%]
"code" → [Write: 90%, Edit: 85%, context-alignment: 70%]
"test" → [Bash: 95%, testing-skill: 60%]
```

### 3.3 Mismatch Detection
- **False Negative:** Predicted nothing, used something → LEARN this mapping
- **False Positive:** Predicted something, didn't use it → REDUCE this weight
- **True Positive:** Predicted and used → REINFORCE this mapping

**Tasks:**
- [ ] Implement usage tracking hook (PostToolUse records actual usage)
- [ ] Build observation storage (JSON/Neo4j)
- [ ] Implement rollup aggregation
- [ ] Build mismatch detection and reporting

## Phase 4: Meta-Learning Harness

### 4.1 Feedback Loop
```
predict_capabilities(plan)
    ↓
Work (tools used are tracked)
    ↓
Compare predictions vs actuals
    ↓
Update weights/patterns
    ↓
Next prediction is better
```

### 4.2 Alias Clusters (Bootstrap)
Seed with known mappings:
```python
ALIASES = {
    "navigation": ["plan", "course", "waypoint", "flight", "starlog"],
    "building": ["code", "write", "implement", "create", "make"],
    "testing": ["test", "verify", "check", "validate"],
    "publishing": ["publish", "deploy", "ship", "release"],
}
```

These bootstrap initial predictions, then observations refine them.

**Tasks:**
- [ ] Implement feedback loop integration
- [ ] Seed alias clusters
- [ ] Build weight adjustment mechanism
- [ ] Create visualization of prediction accuracy over time

## File Structure
```
/tmp/rag_tool_discovery/
├── README.md                    # Overview
├── PLAN.md                      # This file
├── capability_predictor/
│   ├── __init__.py
│   ├── models.py                # Pydantic schemas
│   ├── skill_rag.py             # CartON-style skill RAG
│   ├── tool_rag.py              # CartON-style tool RAG
│   ├── predictor.py             # Joined prediction logic
│   ├── tracking.py              # Usage tracking + mismatch detection
│   ├── core.py                  # Library facade
│   └── mcp_server.py            # MCP wrapper (one tool)
├── sync/                        # Infrastructure (not LLM-facing)
│   ├── sync_skills_to_neo4j.py
│   └── sync_tools_to_neo4j.py
└── tests/
    ├── test_skill_rag.py
    ├── test_tool_rag.py
    └── test_predictor.py
```

## Dependencies
- chromadb (existing skill embeddings)
- neo4j (graph traversal)
- pydantic (schemas)
- mcp (server)
- Existing: skillmanager, gnosys_strata catalogs

## Success Criteria
1. **Phase 1:** Both RAG functions return hierarchical results with graph relationships
2. **Phase 2:** Single tool accepts plan, returns predictions
3. **Phase 3:** Mismatch detection shows prediction accuracy metrics
4. **Phase 4:** Prediction accuracy improves over time with usage

## Notes
- Sync is INFRASTRUCTURE, not LLM-facing
- LLM only calls `predict_capabilities()` - one tool, one MCP
- be_myself pattern: structured input → processing → guidance output
- CartON pattern: RAG → Graph Traversal → Hierarchical Aggregation
