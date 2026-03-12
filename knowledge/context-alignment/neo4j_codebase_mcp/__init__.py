"""
Context Alignment MCP - Anti-hallucination system for AI code understanding

Extends crawl4ai's Neo4j repository parsing with deep AST dependency analysis.
"""

__version__ = "0.1.0"
__author__ = "HEAVEN Team"

from .server import (
    parse_repository_to_neo4j,
    get_dependency_context,
    analyze_dependencies_and_merge_to_graph,
    query_codebase_graph
)