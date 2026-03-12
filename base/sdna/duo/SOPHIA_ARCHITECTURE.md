# SOPHIA-MCP Architecture

## Overview

Sophia is the wisdom/routing layer between GNOSYS and Poimandres.
Sophia IS a DUOAgent - we (human) are its Ariadne.

```
GNOSYS (main PAIA)
    ↓ calls
SOPHIA-MCP (wisdom layer - DUOAgent)
    ↓ routes to
POIMANDRES (execution via SDNA)
```

## Key Insight: Token Savings

Moving complexity ladder + routing logic from system prompt → Sophia-MCP:
- Removes ~2-3k tokens from GNOSYS system prompt
- JIT context instead of always-loaded
- GNOSYS becomes leaner, better at thinking

## MCP Tools

```python
ask_sophia(context: str) -> SophiaResponse
    """Get wisdom/routing analysis. Returns resume_id for construct()."""
    # Returns: analysis, complexity_level (L0-L6), routing decision, resume_id

construct(prompt: str, resume_id: Optional[str] = None) -> ChainDesign
    """Plan/design mode. Creates new chain (quarantined until goldenized)."""
    # Can resume from ask_sophia context via resume_id
    # Returns: chain design, chain_id (quarantined)

golden_management(
    operation: Literal["add", "delete", "list", "search"],
    query_or_name: Optional[str] = None
) -> GoldenResult
    """Human-controlled goldenization. Agent proposes, human approves."""
    # add: promote quarantined chain to golden
    # delete: remove golden chain
    # list: show all golden chains
    # search: RAG search over golden chains
```

## Separation of Powers

- **Sophia CAN:** See golden chains, write NEW chains (quarantined)
- **Sophia CANNOT:** Goldenize chains (human approval required)
- **Human CAN:** Goldenize via `golden_management(operation="add")`

This keeps human in the loop for quality control.

## Flow Example

```python
# 1. Ask Sophia for routing
response = ask_sophia("I need to build an authentication system")
# response.complexity_level = "L2"
# response.routing = "needs_chain"
# response.resume_id = "sophia_123"

# 2. Construct a chain design
design = construct("build JWT auth with refresh tokens", resume_id="sophia_123")
# design.chain_id = "quarantined_456"
# design.chain = SDNAC(...)

# 3. Execute the chain
result = await design.chain.execute(context)

# 4. If it works, goldenize
golden_management("add", "auth_jwt_chain")  # Human approves
```

## Sophia as DUOAgent

```
WE (Human)           = Sophia's Ariadne (provide context/thread)
SOPHIA               = OVP (observer viewpoint, routes/plans)
POIMANDRES           = Executes chains designed by Sophia
```

Sophia has Construct/Execute modes:
- **Construct:** Planning, chain design (quarantined)
- **Execute:** Run existing golden chains

## Sanctus = Goldenization System

The `golden_management` tool IS Sanctus:
- Records successful chains
- Promotes proven patterns to golden status
- Makes SDNA self-improving via searchable chain library

## Next Steps

1. Implement DUOAgent class in SDNA
2. Build sophia-mcp with FastMCP
3. Implement goldenization storage (JSON? SQLite? Neo4j?)
4. RAG over golden chains for `search` operation
5. Migrate complexity ladder from CLAUDE.md → Sophia's knowledge base
