# Context Alignment MCP

Hybrid codebase analysis system that extends crawl4ai's Neo4j repository parsing with Isaac's deep AST dependency analyzer to prevent AI hallucination through complete context understanding.

## Overview

Context Alignment MCP builds on top of crawl4ai-rag's knowledge graph functionality to create an anti-hallucination system. It combines:

- **Structural Analysis** (from crawl4ai): Repository parsing into Neo4j knowledge graphs
- **Deep Dependency Analysis** (new): Isaac's advanced AST analyzer for precise callgraph extraction  
- **Hybrid Integration** (new): Merges both analyses into unified context recommendations

## Attribution

This project extends the knowledge graph functionality from [crawl4ai-rag](https://github.com/coleam00/mcp-crawl4ai-rag) by coleam00, specifically:
- The `parse_repository_to_neo4j` tool is adapted from crawl4ai's repository parsing
- The Neo4j schema and structural analysis approach builds on crawl4ai's implementation

The new contributions in Context Alignment MCP are:
- Deep AST-based dependency analysis (`dependency_analyzer.py`)
- Hybrid graph merging (`analyze_dependencies_and_merge_to_graph`)
- Context-aware file/line range recommendations (`get_dependency_context`)

## Key Features

- 🔍 **Repository Parsing** (via crawl4ai): Ingest GitHub repos or local directories into Neo4j
- 🧠 **Dependency Context**: Get exact files/line ranges to read before modifying code
- 🔄 **Hybrid Analysis**: Merge structural + dependency graphs for complete understanding
- 📊 **Graph Queries**: Execute Cypher queries on the unified knowledge graph

## Quick Start

### Prerequisites

- Python 3.11+
- Neo4j Database (local or cloud)
- Required for full functionality from crawl4ai

### Installation

```bash
# Clone the repository
git clone https://github.com/sancovp/context-alignment-mcp
cd context-alignment-mcp

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Neo4j credentials
```

### Environment Setup

Create a `.env` file with:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### Usage

Start the MCP server:

```bash
python -m neo4j_codebase_mcp.server
```

## MCP Tools Available

### 1. `parse_repository_to_neo4j` (adapted from crawl4ai)
Ingest a repository into Neo4j knowledge graph using crawl4ai's parsing approach.

```python
# GitHub repository
parse_repository_to_neo4j("https://github.com/user/repo.git")

# Local directory  
parse_repository_to_neo4j("/path/to/local/project")
```

### 2. `get_dependency_context` (new)
Get precise files and line ranges to read before modifying code using Isaac's AST analyzer.

```python
get_dependency_context("BaseHeavenAgent", ["/path/to/codebase"])
# Returns: {"dependencies": [...], "file_dependencies": [...]}
```

### 3. `analyze_dependencies_and_merge_to_graph` (new)
Core hybrid tool that enriches crawl4ai's structural graph with deep dependency analysis.

```python
analyze_dependencies_and_merge_to_graph("my_repo", "SpecificClass")
# Adds DEEP_DEPENDS_ON relationships to existing Neo4j graph
```

### 4. `query_codebase_graph`
Execute Cypher queries on the unified knowledge graph.

```python
query_codebase_graph("MATCH (c:Class)-[:DEEP_DEPENDS_ON]->(d) RETURN c.name, d.name")
```

## Architecture

The system enhances crawl4ai's approach with dependency analysis:

1. **Structural Foundation** (crawl4ai): Parse repository into Neo4j for broad coverage
2. **Dependency Enhancement** (new): Analyze specific entities with AST for deep understanding
3. **Graph Merging** (new): Combine both analyses with DEEP_DEPENDS_ON relationships
4. **Context Extraction** (new): Provide exact context needed for safe code modifications

## Neo4j Schema

Extends crawl4ai's schema with new relationship types:

**Base Schema (from crawl4ai):**
- Nodes: `Repository`, `File`, `Class`, `Method`, `Function`
- Relationships: `CONTAINS`, `DEFINES`, `HAS_METHOD`

**Extended Schema (new):**
- Additional Relationships: 
  - `DEEP_DEPENDS_ON`: Deep dependency from AST analysis
  - `DEPENDS_ON_FILE`: File resource dependencies
- Additional Properties:
  - `deep_analyzed`: Boolean flag for analyzed entities
  - `line_range_start/end`: Precise code locations

## Development

This is a vendored package - clone and run directly:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Start development server
python -m neo4j_codebase_mcp.server
```

## Related Projects

- [crawl4ai-rag](https://github.com/coleam00/mcp-crawl4ai-rag) - The foundation for Neo4j repository parsing
- [HEAVEN Framework](https://github.com/sancovp/heaven-framework) - The ecosystem this MCP is part of

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Special thanks to:
- coleam00 for crawl4ai-rag and the Neo4j repository parsing implementation
- The HEAVEN ecosystem team for the integration framework