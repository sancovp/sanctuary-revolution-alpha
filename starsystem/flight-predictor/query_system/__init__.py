"""
QuerySystem - Composable semantic query framework for CartON.

Build intelligent query systems by stacking Layers that combine:
- Embedding search (natural language → concept matching)
- Score algorithms (filtering/ranking by confidence)
- CartON algorithms (graph enrichment)

Example:
    OPERA = QuerySystem([
        Layer("skill", EmbeddingSource.from_collection("Skillgraph_"), ...),
        Layer("tool", EmbeddingSource.from_collection("Toolgraph_"), ...),
        Layer("flight", EmbeddingSource.from_collection("Flightgraph_"), ...),
    ])
    result = OPERA.query("I need to build an MCP server")
"""

from .core import QuerySystem, Layer, EmbeddingSource, LayerResult, QueryResult
from .algorithms import ScoreAlgorithm, CartONAlgorithm

__all__ = [
    "QuerySystem",
    "Layer",
    "EmbeddingSource",
    "LayerResult",
    "QueryResult",
    "ScoreAlgorithm",
    "CartONAlgorithm",
]
