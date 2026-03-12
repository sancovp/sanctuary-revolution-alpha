# Hyperon MCP

Persistent Hyperon/MeTTa integration with MCP interface for LLM tool use.

## Overview

This package provides a **persistent atomspace** implementation for Hyperon/MeTTa, replacing the stateless Docker wrapper approach with true metagraph operations.

### Key Features

- ✅ **Persistent atomspace** - State accumulates across calls
- ✅ **Incremental rule addition** - No reparsing overhead
- ✅ **True metagraph queries** - Pattern matching on accumulated knowledge
- ✅ **MCP interface** - LLM-accessible via Model Context Protocol
- ✅ **HEAVEN-compatible** - BaseHeavenTool wrappers included
- ✅ **Thread-safe** - Multiple concurrent operations supported

### Comparison: Old vs New

#### Old Approach (Docker Wrapper)
```python
# Each call creates fresh container
docker run ... metta-repl  # Parse ALL rules from scratch
# Container dies after execution
# No persistent state
```

#### New Approach (Persistent Atomspace)
```python
from hyperon_mcp import get_metta_instance

metta = get_metta_instance()  # Persistent
metta.add_atom_from_string("(isa dog mammal)")  # Incremental
metta.query("!(match &self (isa dog $x) $x)")  # Uses accumulated state
```

## Installation

```bash
cd /tmp/hyperon-mcp
pip install -e .
```

## Usage

### As Python Library

```python
from hyperon_mcp import PersistentMeTTa, AtomspaceRegistry

# Create persistent instance
metta = PersistentMeTTa("my_knowledge")

# Add rules incrementally
metta.add_atom_from_string("(isa dog mammal)")
metta.add_atom_from_string("(isa cat mammal)")
metta.add_atom_from_string("(isa mammal animal)")

# Query with accumulated rules
result = metta.query("!(match &self (isa $x mammal) $x)")
print(result)  # [[dog, cat]]

# Add more rules - they persist
metta.add_atom_from_string("(isa bird animal)")

# New queries see ALL rules
result = metta.query("!(match &self (isa $x animal) $x)")
print(result)  # [[mammal, bird]]
```

### As MCP Server

```bash
# Run the MCP server
python -m hyperon_mcp.mcps.metta_server
```

Available MCP tools:
- `metta_query` - Query persistent atomspace
- `metta_add_rule` - Add rule to atomspace
- `metta_add_rules_batch` - Add multiple rules
- `metta_list_rules` - List all rules
- `metta_clear_rules` - Clear atomspace
- `metta_atom_count` - Get atom count

### With HEAVEN Framework

```python
from hyperon_mcp.tools import MeTTaQueryTool, MeTTaAddRuleTool

# Use as BaseHeavenTools
query_tool = MeTTaQueryTool()
add_tool = MeTTaAddRuleTool()
```

## Architecture

```
hyperon-mcp/
├── hyperon_mcp/
│   ├── core/
│   │   ├── persistent_metta.py      # Core persistent MeTTa instance
│   │   └── atomspace_registry.py    # Atomspace-based registry
│   ├── tools/
│   │   └── metta_tool.py           # HEAVEN-compatible tools
│   └── mcps/
│       └── metta_server.py         # MCP server interface
└── tests/
    └── test_persistent_metta.py    # Test suite
```

## Testing

```bash
pytest tests/ -v
```

## Use Cases

### Category Theory for MetaStack

```python
# Ground MetaStack compositions with category theory rules
registry = AtomspaceRegistry("metastack_rules")

# Add compositional axioms
registry.add_rules_batch([
    "(: compose (-> MetaStack MetaStack MetaStack))",
    "(: identity (-> Type MetaStack))",
    "(= (compose (identity $t) $m) $m)",  # Left identity
    "(= (compose $m (identity $t)) $m)",  # Right identity
])

# Validate compositions
result = registry.query_with_rules(
    "!(match &self (compose $a $b) (valid-composition $a $b))"
)
```

### Knowledge Graph Accumulation

```python
# Build knowledge incrementally
kg = AtomspaceRegistry("knowledge_graph")

# Session 1: Add taxonom
y
kg.add_rule("(isa dog mammal)")
kg.add_rule("(isa mammal animal)")

# Session 2: Add properties (rules still there!)
kg.add_rule("(has-property dog four-legs)")

# Session 3: Query sees everything
result = kg.query_with_rules("!(ancestor dog animal)")
```

## License

[Specify license]

## Contributing

[Contributing guidelines]
