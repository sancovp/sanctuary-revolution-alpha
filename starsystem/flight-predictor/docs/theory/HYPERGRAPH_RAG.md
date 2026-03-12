# Hypergraph RAG: Semantic Senses and Neighborhood Embeddings

## Beyond Flat Embedding Search

Traditional RAG: embed query, find similar documents, return top-K.

Hypergraph RAG: embed query against **semantic neighborhoods**, return a **typed hypergraph** of matches with precise confidence explanations.

## Semantic Senses (Neighborhood Embeddings)

Each capability (skill/tool) has a **neighborhood** - not its literal fields, but all the **semantic senses** through which you might approach it:

```
Skill "starlog" neighborhood:
├── "session tracking within projects"
├── "time management"
├── "observation of work patterns"
├── "analysis of workflows"
├── "development journaling"
├── "context persistence across conversations"
├── "work logging"
├── "project state management"
└── ...all ways you might THINK about needing this
```

Each sense is a different **angle of approach** to the same capability.

## Self-Referential Validation

A capability's name is valid because its subgraph is **coherent**:

- "starlog" has senses about tracking, persistence, logging
- These senses reinforce each other
- The name anchors a semantically consistent neighborhood
- The neighborhood validates the name

This is **self-referential bootstrapping**: the label emerges from the relationships that make a logic.

## Typed Fuzziness

When a query matches, we know:

1. **Which sense(s) activated** - "work logging" vs "time management"
2. **Match strength per sense** - confidence scores
3. **How the user is thinking** - entry point reveals mental model

Precision comes from knowing **WHERE in the typed neighborhood** the fuzziness lives.

```
Query: "I need to keep track of what I'm doing"
       │
       ▼
Matches "starlog" via:
  - "work logging" sense: 0.92
  - "session tracking" sense: 0.87
  - "observation" sense: 0.71

User approached via "logging" mental model, not "time management"
```

## The Hypergraph Structure

RAG doesn't return flat matches. It returns a **hypergraph**:

```
Root: "I should do {intent} {because}"
      │
      ├── starlog: 1.0
      │   ├── via "session tracking" sense
      │   └── via "context persistence" sense
      │
      ├── giint: 0.95
      │   └── via "self-awareness" sense
      │
      ├── make-flight: 0.90
      │   ├── via "workflow reuse" sense
      │   └── via "pattern capture" sense
      │
      └── [... more capabilities ...]
```

The root is the **semantic anchor**. The edges are **typed by sense**. The structure preserves relationships.

## Collapse via Emergent Morphisms

The LLM receives this hypergraph and **collapses** it:

```
starlog: 1.0 → "to {{track sessions across this multi-day build}}"
giint: 0.95  → "specifically be_myself because {{I need state awareness}}"
make-flight: 0.90 → "because {{this is a repeatable pattern}}"
```

The `{{...}}` are **emergent morphisms** - semantic bridges the LLM creates between:
- Abstract capability (what RAG found)
- Specific intent (why you need it HERE)

## Why This Matters

Flat RAG: "here are similar things"
Hypergraph RAG: "here is your solution space, structured, with entry points"

The structure lets the LLM reason about **relationships between capabilities**, not just individual matches. The senses let it understand **how the user is thinking**.

This is the foundation for the Planning AI's contribution to the two-AI architecture.
