# Context Engineering Library - Loop Executor System

## The Problem

Interaction loops (autopoiesis, guru, ralph, brainhook) are implemented ad-hoc:
- autopoiesis = MCP + hook + state files
- brainhook = hook + state file
- guru = skill that wraps autopoiesis
- ralph = skill with its own pattern

No unified model. Can't list "what loops exist" or "which is active."

---

## The Solution: context-engineering Library

A library that formalizes loop types and provides unified execution.

### Core Concepts

**1. Loop Definition (YAML/JSON config)**
```yaml
name: autopoiesis
description: "Self-maintaining work loop. Disingenuousness is death."
implementation_type: mcp  # or hook, skill

# State machine
states:
  - idle
  - promise_active
  - blocked

initial_state: idle

transitions:
  - from: idle
    to: promise_active
    trigger: "be_autopoietic('promise')"

  - from: promise_active
    to: idle
    trigger: "<promise>DONE</promise>"
    exit_type: completion

  - from: promise_active
    to: blocked
    trigger: "be_autopoietic('blocked')"
    exit_type: blocked

# State persistence
state_file: /tmp/active_promise.md
block_report: /tmp/block_report.json

# Compact instruction (injected when loop active)
compact_instruction: |
  AUTOPOIESIS ACTIVE
  Promise: {promise_file}
  Exit: <promise>DONE</promise> or be_autopoietic("blocked")
  Rule: Disingenuousness is death.
```

**2. Loop Registry**
```python
class LoopRegistry:
    """Central registry of all loop types."""

    def register(self, loop_config: LoopConfig) -> None:
        """Add a loop type to registry."""

    def list_loops(self) -> List[str]:
        """List all registered loop types."""

    def get_active(self) -> Optional[str]:
        """Which loop is currently active (reads state files)."""

    def get_compact_instruction(self, loop_name: str) -> str:
        """Get the compact instruction for injection."""
```

**3. Loop Executor**
```python
class LoopExecutor:
    """Unified executor for any loop type."""

    def start(self, loop_name: str) -> str:
        """Start a loop (vendor template, set state)."""

    def status(self) -> LoopStatus:
        """Get current loop status."""

    def complete(self, output: str) -> str:
        """Complete the loop (validate exit condition)."""

    def block(self, reason: str) -> str:
        """Exit loop as blocked."""
```

---

## Execution Options

### Option A: Per-loop bash commands
```bash
# Each loop gets its own command
autopoiesis start
autopoiesis status
autopoiesis done

guru start
guru emanate  # must create emanation before exit
guru done

ralph start
ralph done
```

**Pros:** Simple, familiar
**Cons:** N commands for N loops, duplication

### Option B: Unified executor + configs (RECOMMENDED)
```bash
# One command, config specifies loop
loop start autopoiesis
loop start guru
loop start ralph

loop status          # Shows which is active
loop done            # Complete active loop
loop block "reason"  # Block active loop
```

**Pros:** Single binary, extensible, no code duplication
**Cons:** Slightly more abstract

---

## Config Location

```
~/.config/context-engineering/
├── loops/
│   ├── autopoiesis.yaml
│   ├── guru.yaml
│   ├── ralph.yaml
│   └── brainhook.yaml
├── registry.json          # Which loops are registered
└── state.json             # Current active loop
```

---

## Integration with paia_builder

Once this library exists, paia_builder can:

```python
class InteractionLoopSpec(ComponentBase):
    """Reference to a context-engineering loop config."""
    loop_name: str  # e.g., "autopoiesis"
    config_path: Optional[str]  # Path to custom config
    # Inherits tier, golden, status from ComponentBase
```

And PAIA can track:
```python
class PAIA:
    interaction_loops: List[InteractionLoopSpec]  # What loops this PAIA supports
    active_loop: Optional[str]  # Currently active (from context-engineering state)
```

---

## Compact Instructions

Each loop has a compact instruction - minimal text injected when loop is active.

**autopoiesis:**
```
🔄 AUTOPOIESIS | Promise: /tmp/active_promise.md | Exit: DONE or blocked
```

**guru:**
```
🧘 GURU | Emanation required before exit | Use /emanate when done
```

**ralph:**
```
🤡 RALPH | [specific ralph instruction]
```

These get injected by hooks when the loop's state file exists.

---

## Implementation Plan

1. **context-engineering package**
   - `LoopConfig` pydantic model
   - `LoopRegistry` for managing configs
   - `LoopExecutor` for unified execution
   - CLI: `loop start|status|done|block`

2. **Default configs**
   - autopoiesis.yaml (from current MCP)
   - guru.yaml (from current skill)
   - ralph.yaml (from current skill)
   - brainhook.yaml (from current hook)

3. **Hook integration**
   - Single hook reads active loop from registry
   - Injects appropriate compact instruction
   - Replaces per-loop hooks

4. **paia_builder integration**
   - Add `InteractionLoopSpec` model
   - Track active loop in PAIA status

---

## Key Insight

**Loops are reified interaction patterns.**

Currently they're scattered (MCP here, hook there, skill elsewhere).
context-engineering library makes them first-class:
- Defined in configs
- Registered in registry
- Executed uniformly
- Tracked in paia_builder

This is exactly what SOSEEH's "Interaction Loops" component needs.

---

*Session 18 (2026-01-11)*

📦 blog::PAIAB::Context Engineering - Making LLM Interaction Loops First-Class 📦
