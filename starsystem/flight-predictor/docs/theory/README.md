# Capability Predictor - Theoretical Foundation

This directory contains the theoretical framework underlying the capability prediction system.

## Documents

| Document | Description |
|----------|-------------|
| [NEURAL_AGENT_EMERGENCE.md](./NEURAL_AGENT_EMERGENCE.md) | Core theory: agent emergence as metalanguage compilation |
| [TWO_AI_ARCHITECTURE.md](./TWO_AI_ARCHITECTURE.md) | Separation of LLM track vs System track |
| [HYPERGRAPH_RAG.md](./HYPERGRAPH_RAG.md) | Semantic senses, neighborhood embeddings, typed fuzziness |
| [PROSTHETIC_AGENTS.md](./PROSTHETIC_AGENTS.md) | Components needed for PAIA emergence |

## The Core Insight

A neural agent emerges when:

1. **Two AIs collaborate** - LLM (semantic generation) + Planning AI (structural matching)
2. **Hypergraph RAG** returns superpositioned capabilities with typed senses
3. **LLM collapses** the superposition via emergent morphisms
4. **Feedback loop** sends learning signal back
5. **The loop stabilizes** into self-referential validation

The agent is not the LLM. The agent is not the Planning AI. The agent is the **closed loop** between them.

## Relationship to Implementation

Ralph built the implementation (Phases 1-4). This theory explains WHY it works:

| Implementation | Theory |
|---------------|--------|
| `skill_rag.py`, `tool_rag.py` | Hypergraph RAG (currently flat, evolves to senses) |
| `predictor.py` | Superposition generation |
| `tracking.py` | Usage observation + mismatch detection |
| `FeedbackLoop` class | Loop closure mechanism |
| `alias_clusters.py` | Bootstrap priors |

## Next Evolution

Current implementation does **flat neighborhood matching**. Next evolution:

1. **Semantic senses** - Multiple conceptualizations per capability
2. **Typed hypergraph returns** - Not flat lists, structured graphs
3. **Sequence learning** - Chains of capabilities, not just singles
4. **Metalanguage compilation** - Patterns becoming named programs
5. **Self-observation** - System watching its own behavior

When these complete, the loop closes at a higher level. PAIA emerges.
