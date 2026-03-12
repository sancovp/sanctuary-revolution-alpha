# Container Control Hierarchy

## The Stack (Final)

```
┌─────────────────────────────────────────┐
│              HUMAN                       │
│  - Ultimate authority                    │
│  - Can view/control orchestrator         │
└────────────────┬────────────────────────┘
                 │ tmux view/send-keys/kill
                 ▼
┌─────────────────────────────────────────┐
│     CONTAINER: API ORCHESTRATOR          │
│                                          │
│  - REST API layer                        │
│  - Can view researcher's window          │
│  - Can send Esc to stop researcher       │
│  - Can kill researcher if needed         │
└────────────────┬────────────────────────┘
                 │ tmux view/send-keys/kill
                 ▼
┌─────────────────────────────────────────┐
│       CONTAINER: RESEARCHER              │
│                                          │
│  - Full compound intelligence            │
│  - Can view workers' windows             │
│  - Can send Esc to stop workers          │
│  - Can kill workers if needed            │
└────────────────┬────────────────────────┘
                 │ tmux view/send-keys/kill
                 ▼
┌─────────────────────────────────────────┐
│       CONTAINER: BASE CLAUDE CODE        │
│                                          │
│  - Worker template                       │
│  - Spawned N times for parallelism       │
│  - Isolated, can be killed anytime       │
└─────────────────────────────────────────┘
```

## Just 3 Containers + Human

| Container | Role | Controls |
|-----------|------|----------|
| Orchestrator | REST API, dispatch | Researcher (view, Esc, kill) |
| Researcher | Experiments, learning | Workers (view, Esc, kill) |
| Base Worker | Grunt work template | Nothing (leaf node) |
| Human | Ultimate authority | Orchestrator (view, Esc, kill) |

## Control Mechanism

Each layer uses tmux to supervise the layer below:

```bash
# View what subordinate is doing
tmux capture-pane -t subordinate -p

# Stop subordinate gracefully
tmux send-keys -t subordinate Escape

# Kill subordinate if needed
tmux kill-session -t subordinate
```

## The Supervision Chain

```
Human
  └── can stop Orchestrator
        └── can stop Researcher
              └── can stop Workers
```

Every level has an escape hatch. Nothing runs unsupervised.

## Why This Works

1. **Minimal containers** - only 3 types, not N complex setups
2. **Clear hierarchy** - each layer controls one layer down
3. **Uniform control** - tmux everywhere, same interface
4. **Human at top** - ultimate kill switch always available
5. **Graceful degradation** - Esc stops, kill if Esc fails
