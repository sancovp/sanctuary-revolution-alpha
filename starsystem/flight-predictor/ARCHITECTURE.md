# RAG Tool Discovery Architecture

## The Core Insight: Programmable Cognition via Query Schemas over Typed Graph

This system enables **programmable cognition** - the ability to literally program how GNOSYS thinks by defining schemas over a unified typed graph (CartON).

## Graph Hierarchy

```
Toolgraph     = primitive capabilities (MCP tools)
Skillgraph    = knowledge/context bundles (skills)
Flightgraph   = assembled procedures (learned from execution)
Automations   = graph operations that create new *graphs
```

## The Four-Dimensional UARL Model

Every concept has four relationship dimensions:

1. **is_a** - category/type (taxonomy)
2. **part_of** - container (mereology)
3. **instantiates** - pattern realization
4. **has_*** - structure (parameters, assumptions, domains)

## Metagraph Concepts

### Toolgraph

A Toolgraph is a **meta-concept** representing "the semantic graph of this tool exists and is addressable."

```
Toolgraph_Add_Concept:
  is_a: Toolgraph
  part_of: Toolgraph_Registry
  instantiates: Semantic_Graph_Pattern
  has_root: Tool_Add_Concept
  has_node: [Tool_Add_Concept, MCP_Carton, Knowledge_Graph, Query_Pattern, Param_Concept_Name, ...]
  has_domain: Knowledge_Graph
  has_pattern: Query_Pattern
```

The **description** is an ontological sentence (NOT prose):
```
[TOOLGRAPH:add_concept] is_a:Tool part_of:carton instantiates:Query_Pattern has_domain:Knowledge_Graph has_parameters:[Concept_Name,Concept,Relationships] [/TOOLGRAPH]
```

### Skillgraph ✅

Skills are **packages** with resources, scripts, templates. Skillgraphs capture full package structure:

```
Skillgraph_Make_MCP:
  is_a: Skillgraph
  part_of: Skillgraph_Registry
  instantiates: Semantic_Graph_Pattern
  has_root: Skill_Make_MCP
  has_node: [Skill_Make_MCP, Domain_Paiab, Preflight_Skill_Pattern, Resource_*, ...]
  has_domain: Paiab
  has_pattern: Preflight_Skill_Pattern
  has_category: Category_Preflight
```

Ontological sentence includes resources for better RAG:
```
[SKILLGRAPH:make-mcp] is_a:Skill instantiates:Preflight_Skill_Pattern has_domain:Paiab has_subdomain:Mcp_Development has_resources:[Components,Checklist,Architecture_Patterns] what:Preflight for building MCPs when:Need to build a new MCP [/SKILLGRAPH]
```

### The Full *graph Hierarchy

```
OPERADICFLOWGRAPH (goldenized workflow - TOP LEVEL)
  ├── type: AI_Only | Human_Only | AI_Human
  └── goldenized: True (proven pattern)
      │
      ▼
CANOPYFLOWGRAPH (same structure, not goldenized yet)
      │
      ▼
MISSIONGRAPH (flights + course)
  ├── has_course: Course (goal, milestones, KPIs)
  ├── has_project: [Project_1, ...]
  └── has_flight: [Flightgraph_1, ...]
          │
          ▼
FLIGHTGRAPH (actual work session)
  ├── has_session: Starlog_Session
  ├── has_promise: Autopoiesis promise
  ├── has_loop: [brainhook, autopoiesis, guru]
  └── has_step: [Steps → capability_slots]
          │
          ▼
TOOLGRAPH / SKILLGRAPH (fill capability slots)
```

### Flightgraph (TODO)

```
Flightgraph_Build_MCP:
  is_a: Flightgraph
  part_of: Missiongraph_X
  instantiates: Procedure_Pattern
  has_session: Starlog_Session_X
  has_promise: Promise_Build_MCP
  has_loop: [Loop_Brainhook, Loop_Autopoiesis]
  has_step: [Step_1, Step_2, Step_3]
  has_capability_slot: [Slot_Research, Slot_Scaffold, Slot_Implement]
  has_filled_slot: [Toolgraph_Search_Docs, Skillgraph_Make_MCP]
  has_trace: Trace_XXXXX
```

### Missiongraph (TODO)

```
Missiongraph_Ship_PAIA:
  is_a: Missiongraph
  part_of: Canopyflowgraph_X
  has_course: Course_Ship_PAIA (goal, milestones, KPIs)
  has_project: [Project_SDNA, Project_Autopoiesis]
  has_flight: [Flightgraph_Build_MCP, Flightgraph_Test_MCP]
```

### Canopyflowgraph (TODO)

```
Canopyflowgraph_MCP_Development:
  is_a: Canopyflowgraph
  part_of: Operadicflowgraph_X (if goldenized)
  has_mission: [Missiongraph_Ship_PAIA, Missiongraph_Ship_Skillmanager]
  has_goldenized: False
```

### Operadicflowgraph (TODO)

```
Operadicflowgraph_Build_And_Ship:
  is_a: Operadicflowgraph
  instantiates: AI_Human_Pattern
  has_goldenized: True
  has_canopy: [Canopyflowgraph_MCP_Development, ...]
```

### OMNISANC State Machine

```
HOME ──(plot course)──► JOURNEY
                          ├── STARPORT (between flights)
                          ├── SESSION (starlog active, in flight)
                          └── ... cycle until land HOME

metabrainhook survives when everything else shuts off at HOME
```

### Loop Stack (during flights)

```
metabrainhook (TOP - separate process, survives shutdown)
    ↓
guru (bodhisattva vow)
    ↓
autopoiesis (self-maintaining promises)
    ↓
brainhook (recursion)
```

## The RAG Flow

### 1. Embedding (Offline)

```
CartON Toolgraph → Ontological Sentence → ChromaDB Embedding
```

The embedding content IS the ontology serialized:
```
[TOOLGRAPH:X] is_a:Tool part_of:Y instantiates:Z has_domain:A has_parameters:[B,C,D] [/TOOLGRAPH]
```

### 2. Query (Online)

```
Natural Language Query → ChromaDB RAG → Toolgraph Node Refs
```

RAG returns exact node references like `Toolgraph_Add_Concept`.

### 3. Rehydration

```
Toolgraph Node Ref → CartON Query → Full Typed Subgraph
```

The semantics come back **typed and structured**, not lossy string matches.

## Flights as Capability-Slot Programs

Flight configs become programs with **capability slots**:

```yaml
Flight_Build_MCP:
  steps:
    - name: Research existing patterns
      capability_slot: research_pattern
      # RAG fills: Toolgraph_Search_Docs

    - name: Scaffold project structure
      capability_slot: scaffold_pattern
      # RAG fills: Toolgraph_Create_Project

    - name: Implement MCP server
      capability_slot: implement_pattern
      # RAG fills: Skillgraph_Make_MCP
```

## Emergent Flight Assembly

### The Self-Improving Loop

```
1. Plan arrives: "I need to build an MCP"

2. Search for existing Flightgraph_Build_MCP
   └── If found: Use it (slots pre-filled, reasoning trace available)

3. If not found: Create flight skeleton with capability slots

4. RAG fills slots from Toolgraphs/Skillgraphs
   └── Query: "scaffold pattern" → Toolgraph_Create_Project

5. Execute flight, capturing reasoning trace

6. Add results back to CartON:
   └── Create Flightgraph_Build_MCP
   └── Link to filled slots
   └── Store reasoning trace

7. Next time: Flight exists with full semantics
```

## Changing What *graphs "Have" = Programming Cognition

By changing what a Toolgraph/Skillgraph/Flightgraph `has_*`, we change:
- What gets serialized to ontological sentences
- What gets embedded
- What RAG can match on
- **How GNOSYS thinks**

This is the "input schema" for the cognitive system. The Python code defines the schema, the schema defines the embeddings, the embeddings define the cognitive modes.

## Chunk Management

Once you have:
- Typed graphs → Serialized sentences → Embeddings

You can do:
- Different sections and markers
- Different addressing schemes
- Different chunk sizes for different semantic resolution

**It all just depends on managing chunk sizes correctly.**

## Files

### Ingestion
- `sync/ingest_tools_to_carton.py` - Creates Tool + Toolgraph concepts with full UARL
- `sync/ingest_skills_to_carton.py` - Creates Skill + Skillgraph concepts with package structure
- `sync/ingest_flights_to_carton.py` - Creates Flight + Flightgraph concepts with capability slots
- `sync/ingest_missions_to_carton.py` - Creates Mission + Missiongraph concepts with flight refs
- `sync/push_concepts_to_carton.py` - Pushes to CartON (DEPRECATED - use daemon)
- `sync/populate_tool_chroma.py` - Embeds Toolgraph sentences into ChromaDB
- `sync/populate_skill_chroma.py` - Embeds Skillgraph sentences into ChromaDB
- `sync/populate_flight_chroma.py` - Embeds Flightgraph sentences into ChromaDB
- `sync/populate_mission_chroma.py` - Embeds Missiongraph sentences into ChromaDB

### RAG
- `capability_predictor/tool_rag.py` - CartON-style tool RAG with graph traversal
- `capability_predictor/skill_rag.py` - Skillgraph RAG with domain/category aggregation
- `capability_predictor/flight_rag.py` - Flightgraph RAG for procedure discovery
- `capability_predictor/mission_rag.py` - Missiongraph RAG for multi-session workflows

### Fixed Bugs
- `/home/GOD/carton_mcp/observation_worker_daemon.py` - Was re-queuing instead of writing to Neo4j. Fixed to use `batch_create_concepts_neo4j`.

## Current State

- 164k+ Wiki nodes in CartON
- 790k+ relationships
- 334 Toolgraph meta-concepts (tools from all MCP servers)
- 43 Skillgraph meta-concepts (skills with resources/scripts/templates)
- 4 Flightgraph meta-concepts (flights with 23 capability slot references)
- 36 Missiongraph meta-concepts (missions with 17 unique flight references)
- 2 Canopyflowgraph meta-concepts (quarantine patterns)
- 2 Operadicflowgraph meta-concepts (golden workflows)
- ChromaDB: `toolgraphs` + `skillgraphs` + `flightgraphs` + `missiongraphs` + `flowgraphs` collections
- RAG returns exact node refs that rehydrate from CartON
- **FULL HIERARCHY COMPLETE**: Operadic → Canopy → Mission → Flight → Tool/Skill

## Next Steps

1. ~~**Skillgraph** - Create same pattern for skills~~ ✅ DONE
2. ~~**Flightgraph** - Ingest flight configs with capability slots~~ ✅ DONE
3. ~~**Missiongraph** - Model missions with courses, projects, flights~~ ✅ DONE
4. ~~**Canopyflowgraph** - Pre-goldenized workflow containers~~ ✅ DONE
5. ~~**Operadicflowgraph** - Goldenized workflows (AI/Human/AI+Human)~~ ✅ DONE
6. ~~**Unified RAG** - Combined query across all *graphs~~ ✅ DONE
7. ~~**CAVE Integration** - Wire RAG into hook system~~ ✅ DONE
8. **Instance Caching** - Freeze execution data into graph as cache
9. **Trace Capture** - Store reasoning traces back to CartON
10. **Evaluation Flights** - Flightgraphs that test other Flightgraphs
11. **Automations** - Graph ops that create new *graphs (PyTorch layers)

## Session Handoff (2026-01-23)

### Completed Session 1 (Skillgraphs)
- ✅ Skillgraph ingestion with full package structure (resources/scripts/templates)
- ✅ Skillgraph ChromaDB population (43 skillgraphs)
- ✅ skill_rag.py updated to use Skillgraph pattern
- ✅ Tested end-to-end: "build MCP" → make-mcp ✓

### Completed Session 2 (Flightgraphs)
- ✅ Flightgraph ingestion with capability slot extraction
- ✅ Flightgraph ChromaDB population (4 flightgraphs)
- ✅ flight_rag.py created for procedure discovery
- ✅ Tested end-to-end:
  - "build MCP server" → mcp-development-config ✓
  - "play sanctuary game" → play-sanctuary-revolution-config ✓
  - "create a flight config" → create-config-config ✓
- ✅ **23 capability slot references** extracted pointing to Toolgraph/Skillgraph

### Completed Session 3 (Missiongraphs)
- ✅ Missiongraph ingestion from `/tmp/heaven_data/missions/`
- ✅ Missiongraph ChromaDB population (36 missiongraphs)
- ✅ mission_rag.py created for multi-session workflow discovery
- ✅ Tested end-to-end:
  - "compound intelligence" → compound-intelligence-foundation ✓
  - "authentication feature" → test-mission-001 (feature_development) ✓
- ✅ **17 unique flight references** linking Mission → Flight → Tool/Skill

### Key Insights Captured
1. **PyTorch for Cognition** - *graphs are composable modules, RAG is forward pass, traces are backward
2. **Instance Caching** - Freeze execution data into graph, emergent synthesis replaces symbolic rules
3. **Make the Pond** - Substrate generates capability, teaching happens through usage
4. **Bootstrap is Business** - Build for self → content → audience → package what you used
5. **Capability Slots** - Flight steps contain tool/skill refs that can be auto-resolved via RAG

### Full Hierarchy Documented
```
Operadicflowgraph → Canopyflowgraph → Missiongraph → Flightgraph → Toolgraph/Skillgraph
```

### Completed Session 4 (Unified RAG + CAVE Integration)
- ✅ Created `unified_rag.py` - queries all *graph types (Tool, Skill, Flight, Mission)
- ✅ Created `capability_resolver.py` in CAVE - lazy-loads RAG module
- ✅ Wired into `HookRouterMixin.handle_hook()` - injects capability recommendations
- ✅ Tested end-to-end: "build MCP server" returns relevant skills, flights, tools
- ✅ RAG controllable via `rag_enabled` in hook state

### Architecture Summary
```
Query: "build MCP server"
         ↓
unified_rag.py (queries all ChromaDB collections)
         ↓
┌────────────────────────────────────────────────┐
│ 📋 MISSIONS: Mission_Base_Mission (0.22)       │
│ 🛫 FLIGHTS: Mcp_Development_Flight_Config (0.34)│
│ 📚 SKILLS: Make_Mcp (0.34), Understand_MCP... │
│ 🔧 TOOLS: mcpify [mcp_development_checklist]   │
└────────────────────────────────────────────────┘
         ↓
HookRouterMixin.handle_hook() → additionalContext
         ↓
Claude sees capability recommendations in context

### Next Session: Instance Caching + Trace Capture
1. Cache execution instances into graph
2. Capture reasoning traces back to CartON
3. Build feedback loop: execution → graph → better RAG
