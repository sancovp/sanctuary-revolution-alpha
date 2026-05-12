# Session Notes - PAIA Builder Pipeline

## What Was Built This Session

### 1. Container Infrastructure
- `paia/extended:latest` with control endpoints (`/exit`, `/force_exit`, `/kill_agent_process`)
- Fixed at `/tmp/sanctuary-system/game_wrapper/docker/`

### 2. Typed Spec Chain (paia-builder/models.py)

```
OnionArchSpec (reusable inner layers)
├── util_deps/
├── utils.py (ALL THE STUFF)
├── models.py
└── core.py (library facade)
        ↓
MCPSpec = OnionArchSpec + server layer + tools
        ↓
PluginSpec = composition of components
        ↓
ContainerSpec = plugin + runtime (base_image, mcp_deps)
        ↓
DeliverableSpec = callable compilation target
```

### 3. Compilation Pipeline (paia-builder/util_deps/compile.py)

```python
from paia_builder.core import compile_deliverable, commit_compilation, evolution_cycle

# Basic compilation
result = compile_deliverable("my-paia", "Build a CLI tool for X")
# result.port, result.container_name

# After manual testing passes:
commit_compilation(result.container_name, "paia/my-paia:v1")

# Full auto cycle (with test function):
result = evolution_cycle("my-paia", "instruction", test_fn=my_test)
```

### Key Insights
- OnionArchSpec = inner layers only (stops at core.py)
- Each spec type adds its unique server layer on top
- MCPToolSpec.core_function = which core function to wrap
- MCPToolSpec.ai_description = optional AI-facing docstring override
- Deliverable.__call__ = compile = build → start → auth → assemble → commit
- Green tests → trusted = True → can self-evolve

## Next Steps
1. Test compilation pipeline end-to-end
2. Wire DeliverableSpec to compile_deliverable()
3. YOUKNOW validation integration
4. Self-evolution via GitHub (after trust established)

## Key Files
- `/tmp/paia-builder/paia_builder/models.py` - all specs
- `/tmp/paia-builder/paia_builder/util_deps/compile.py` - compilation logic
- `/tmp/sanctuary-system/game_wrapper/docker/` - container infrastructure
