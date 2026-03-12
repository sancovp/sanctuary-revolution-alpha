# Project Operational Knowledge

## Build Commands

```bash
# Install dependencies
pip install -q -e /tmp/rag_tool_discovery

# Install related packages (needed for imports)
pip install -q chromadb neo4j pydantic mcp

# Type checking
mypy capability_predictor/
```

## Test Commands

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_skill_rag.py -v

# Test MCP server locally
python -c "from capability_predictor.core import predict_capabilities; print('Import OK')"
```

## Validation Steps

Before committing:
1. All tests pass
2. MCP server starts without error
3. Can query both skill and tool RAG functions

## Project Structure

```
/tmp/rag_tool_discovery/
├── capability_predictor/
│   ├── __init__.py
│   ├── models.py          # Pydantic schemas
│   ├── skill_rag.py       # CartON-style skill RAG
│   ├── tool_rag.py        # CartON-style tool RAG
│   ├── predictor.py       # Joined prediction logic
│   ├── core.py            # Library facade
│   └── mcp_server.py      # MCP wrapper
├── sync/                  # Infrastructure scripts
├── tests/
├── specs/                 # Requirements
└── pyproject.toml
```

## Dependencies

- chromadb (skill embeddings)
- neo4j (graph traversal)
- pydantic (schemas)
- mcp (server)
- Imports from: skillmanager, gnosys_strata, carton_mcp

## Key Files to Reference

- `/home/GOD/skill_manager_mcp/src/skill_manager/core.py` - existing skill RAG
- `/home/GOD/gnosys_strata/src/strata/utils/catalog.py` - existing tool RAG
- `/home/GOD/carton_mcp/carton_utils.py` - CartON scan_carton pattern to follow
