# Swarm Orchestrator Vision

## The Core Insight

The complexity lives in ONE place (main GNOSYS). Everything else is base Claude Code in containers.

## The Agent Class

```python
from paia import Agent

agent = Agent(
    container="agent-001",        # Docker/isolated env
    base="claude-code",           # Base Claude Code install
    plugins=["autopoiesis"],      # Optional: inject plugins
    mcps=["starship"],            # Optional: inject MCPs
    prompt_file="/shared/task.md" # How to communicate
)

agent.start()                     # Spin up container, start claude
agent.send("Build this feature") # Write to prompt file
result = agent.wait()             # Block until done
agent.stop()                      # Clean up
```

## What Each Agent Has

- Bash (full shell access in container)
- Network filesystem (can read/write shared volumes)
- Base Claude Code (the anthropic CLI)
- Optional: plugins, MCPs, compound intelligence stack

## The Swarm

```python
from paia import Swarm

swarm = Swarm(orchestrator=main_gnosys)

# Add workers
swarm.add(Agent(container="worker-001"))
swarm.add(Agent(container="worker-002"))
swarm.add(Agent(container="worker-003"))

# Distribute tasks
swarm.orchestrate([
    "Build frontend component",
    "Write API endpoint",
    "Create tests"
])

# Collect results
results = swarm.gather()
```

## Main GNOSYS = Orchestrator

The main instance (me, running with full compound intelligence) becomes:
- Task decomposer (break work into agent-sized chunks)
- Swarm manager (spawn, assign, monitor, collect)
- Quality gate (verify results via samaya-like checks)
- Upgrader (decide which agents get compound intelligence stack)

## The Resource Constraint Reality

> "I only have one container I can do that in right now because of resource constraints, so I need that one to make money..."

This is the exact position:

```
┌─────────────────────────────────────────────┐
│  MAIN GNOSYS (full compound intelligence)   │
│  - Orchestrates everything                  │
│  - Has all MCPs, plugins, skills            │
│  - This is YOU, the user's PAIA            │
└─────────────────┬───────────────────────────┘
                  │ manages
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────────────┐
│Worker 1│  │Worker 2│  │ GOLDEN WORKER  │
│ (base) │  │ (base) │  │ (full stack)   │
│        │  │        │  │ MAKES MONEY    │
└────────┘  └────────┘  └────────────────┘
```

## The Golden Worker

One worker gets the full stack because it's the money-maker:
- Full compound intelligence
- Guru loops with emanation requirement
- Samaya verification
- Produces production-quality output

Revenue from Golden Worker → fund more Golden Workers → scale

## The Library

`paia-swarm` or similar:
- `Agent` class wraps container + claude code
- `Swarm` class manages multiple agents
- `Orchestrator` interface for main GNOSYS
- File-based communication (simple, debuggable)
- Optional compound intelligence injection

## Why This Works

1. **Isolation** - each agent in own container, can't break others
2. **Simplicity** - base Claude Code is the unit, no complex setup per agent
3. **Scalability** - spin up N workers for parallel tasks
4. **Upgradability** - inject compound intelligence where it matters
5. **Debuggability** - file-based communication, can inspect everything
6. **Economics** - concentrate investment in money-making agent

## This Is Your Exact Position

You have:
- Main GNOSYS (me) with full stack
- Need to make money
- Limited resources for additional full-stack agents
- Can spin up basic workers for parallelism

Strategy:
1. Build the swarm library
2. Use basic workers for parallel grunt work
3. One Golden Worker for revenue-generating tasks
4. Revenue funds more Golden Workers
5. Eventually: swarm of Golden Workers, all self-verifying
