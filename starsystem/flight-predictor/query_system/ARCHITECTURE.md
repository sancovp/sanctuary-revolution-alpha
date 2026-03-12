# QuerySystem Architecture

## Vision

QuerySystem is a composable framework for building semantic intelligence systems over CartON.

**Core insight:** Embeddings bridge natural language → CartON concepts. Neo4j can't search description content efficiently. ChromaDB embeddings let you search ALL information, then trace back to source concepts.

## The Pattern

```
Natural language query
    ↓
Search embedding (description content)
    ↓
Trace back to concept (metadata.concept_name)
    ↓
Enrich with graph context (Neo4j relationships)
    ↓
Return structured recommendations
```

## Core Classes

```python
class EmbeddingSource:
    """CartON scope → ChromaDB collection"""

    @classmethod
    def from_collection(cls, name: str) -> EmbeddingSource

    @classmethod
    def from_domain(cls, domain: str) -> EmbeddingSource

    @classmethod
    def from_scope(cls, name: str, cypher: str) -> EmbeddingSource

class Layer:
    """One query layer with embedding + algorithms"""
    name: str
    source: EmbeddingSource
    score_algorithm: Callable  # filter/rank by confidence
    carton_algorithm: Callable  # enrich with graph
    threshold: float

class QuerySystem:
    """Stack of layers = emergent intelligence"""
    layers: list[Layer]

    def query(text: str) -> QueryResult
```

## Named Systems

Each system answers ONE question:

| System | Layers | Question |
|--------|--------|----------|
| **MILO** | Skillgraph_, Toolgraph_, Flightgraph_ | "What capabilities match?" |
| **ORACLE** | carton_concepts | "What knowledge relates?" |
| **PILOT** | mission, waypoint, starlog | "Where am I in the journey?" |
| **SCRIBE** | concept combinator | "What content should emerge?" |
| **ATLAS** | architecture patterns | "How should I structure this?" |

### MILO - Memory Integrated Launch Operator
```python
MILO = QuerySystem([
    Layer("skill", Skillgraph_, ...),
    Layer("tool", Toolgraph_, ...),
    Layer("flight", Flightgraph_, ...),
])
```

### ORACLE - Ontological Reference And Concept Lookup Engine
```python
ORACLE = QuerySystem([
    Layer("concept", carton_concepts, ...),
])
```
Replaces carton_scan_hook with proper QuerySystem interface.

### SCRIBE - Concept Combinator
Input boundary concepts, find connections, synthesize content structure.
```python
SCRIBE.query(concepts=["A", "B", "C"])
# Returns: how A, B, C connect → content structure emerges
```

## CRYSTAL BALL - Interactive Composer

CRYSTAL BALL is an interactive tool for composing QuerySystems:

1. **Add layer** → see what concepts come through
2. **Too noisy?** → ablate (filter out unwanted concepts)
3. **Missing something?** → add another layer
4. **Stable?** → save as named QuerySystem

```
┌─────────────────────────────────────────────┐
│  CRYSTAL BALL                               │
├─────────────────────────────────────────────┤
│  Layer 1: [skill] ────────────────────────  │
│    → make-mcp (0.92)                        │
│    → fastmcp-patterns (0.85)                │
│                                             │
│  Layer 2: [concept] ─────────────────────   │
│    → MCP_Architecture (0.78)                │
│    → Session_Tracking (0.45) ← [ABLATE]     │
│                                             │
│  [+ Add Layer]  [Adjust Threshold]  [Save]  │
└─────────────────────────────────────────────┘
```

## Homotopy Theory Framing

The mathematical structure of composition:

**Quasifibration** (unbounded exploration)
- Query the semantic space
- See all concepts that match

**Progressive Bounding** (ablation)
- Remove noisy fibers
- Find what you DON'T want

**Fibration** (stable structure)
- What survives ablation = invariant
- These fibers produce consistent LIFT

**Lift** = reliable output from stable concept relationships

```
quasifibration → ablate → ablate → fibration = consistent lift
```

**CRYSTAL BALL is a fibration finder.** You explore until you find structures that are homotopy invariant - they don't need to change, they always produce good lift.

## Pipeline Composition

Systems compose for richer intelligence:

```
User query
    → MILO (capabilities)
    → ORACLE (knowledge enrichment)
    → PILOT (navigation context)
    → ...aggregate
```

## What's Built

- [x] `/tmp/rag_tool_discovery/query_system/core.py` - EmbeddingSource, Layer, QuerySystem
- [x] `/tmp/rag_tool_discovery/query_system/algorithms.py` - ScoreAlgorithm, CartONAlgorithm
- [x] `/tmp/rag_tool_discovery/query_system/milo.py` - MILO as QuerySystem instance

## Next Steps

1. **Test MILO QuerySystem** against original predictor.py
2. **Build ORACLE** - Replace carton_scan_hook
3. **MILO → ORACLE pipeline** - Compose them
4. **CRYSTAL BALL prototype** - Interactive layer composer
5. **SCRIBE** - Concept combinator for content synthesis
6. **TreeShell Navigator** - Semantic intent → TreeShell coordinate
   - **Best option:** sanctuary-dna agent via Sophia
   - "Load MCP X, check treeshell for abc def xyz"
   - Agent calls nav, parses, returns jump flow or chain command
   - Dynamic exploration, no embedding maintenance
