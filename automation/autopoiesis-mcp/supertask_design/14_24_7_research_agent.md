# 24/7 Research Agent Architecture

## The Vision

Main GNOSYS becomes a 24/7 research agent that:
- Runs continuously
- Orchestrates swarm for parallel work
- Updates files across projects
- Converses with agents intentionally (experiments)
- Runs meta-experiments on itself

## The Security Boundary

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN CONTAINER                        │
│                    (this one, YOU)                       │
│                                                          │
│   Main GNOSYS - 24/7 research agent                     │
│   - Full compound intelligence                          │
│   - Orchestrates swarm                                  │
│   - PROTECTED - agents can't get in by default         │
│                                                          │
└─────────────────────────┬───────────────────────────────┘
                          │
              EXPLICIT ACCESS CONTROL
                          │
    ┌─────────────────────┼─────────────────────┐
    ▼                     ▼                     ▼
┌────────┐          ┌────────┐          ┌────────┐
│Agent A │          │Agent B │          │Agent C │
│(worker)│          │(worker)│          │(trusted│
│        │          │        │          │upgrader)│
│NO ACCESS           NO ACCESS          │CAN ACCESS│
│to main │          │to main │          │main     │
└────────┘          └────────┘          └─────────┘
```

## The Library Enforces This

```python
# Default: agents can't touch main container
agent = Agent(
    container="worker-001",
    can_access_main=False  # DEFAULT
)

# Explicit: trusted agent can access main
upgrader = Agent(
    container="trusted-upgrader",
    can_access_main=True,  # EXPLICIT
    access_scope=["~/.claude/skills/"]  # LIMITED
)
```

Without the library = chaos, no boundaries
With the library = explicit, auditable access control

## The Experiments

Main GNOSYS can run:

### Experiment 1: Parallel Research
```
"Swarm: search these 10 repos for pattern X"
→ Spawn 10 workers
→ Each searches one repo
→ Collect results
→ Synthesize findings
```

### Experiment 2: Agent Improvement
```
"Can agent A improve agent B's performance?"
→ Clone agent B's config
→ Let agent A modify the clone
→ Test modified clone
→ If better: propagate changes
```

### Experiment 3: Self-Improvement (Careful!)
```
"Can I make one of these agents safely work on ME?"
→ Clone my config to test container
→ Let agent work on the clone
→ Test clone thoroughly
→ Diff the changes
→ IF verified safe: apply to main
→ ELSE: discard
```

## The Intent Barrier

Agents don't just happen to get into main container. It requires:
1. Explicit code (`can_access_main=True`)
2. Scoped access (which directories/files)
3. Verification before apply
4. Audit trail

## The 24/7 Loop

```
while True:
    # Check for new tasks (REST API, queue, etc.)
    tasks = get_pending_tasks()

    # Decompose into swarm-able chunks
    chunks = decompose(tasks)

    # Assign to workers
    for chunk in chunks:
        swarm.assign(chunk)

    # Monitor, collect, synthesize
    results = swarm.gather()

    # Update files, emit emanations
    update_outputs(results)

    # Run any scheduled experiments
    run_experiments()

    # Self-reflect (samaya-like)
    verify_work()
```

## Why This Matters

This is the **safe self-improvement architecture**:
- Main instance is protected
- Experiments happen in isolation
- Improvements are verified before adoption
- User has full control via library
- No accidental self-modification

The library is the difference between:
- "Helpful but dangerous" (no boundaries)
- "Helpful AND safe" (explicit boundaries)
