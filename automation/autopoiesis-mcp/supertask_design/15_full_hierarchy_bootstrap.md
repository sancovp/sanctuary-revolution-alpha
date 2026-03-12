# Full Hierarchy & Bootstrap Path

## The Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│         API ORCHESTRATOR GNOSYS (Top Level)             │
│                                                          │
│  - REST API control plane                               │
│  - Receives commands from all interfaces                │
│  - Dispatches to Researcher GNOSYS                      │
│  - The "brain" that never sleeps                        │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│            RESEARCHER GNOSYS (24/7 Research)            │
│                                                          │
│  - Full compound intelligence                           │
│  - Runs experiments on workers                          │
│  - Learns how to engineer PAIAs                         │
│  - Protected container (security boundary)              │
└─────────────────────────┬───────────────────────────────┘
                          │ manages
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ┌────────┐       ┌────────┐       ┌────────┐
   │Worker 1│       │Worker 2│       │Worker N│
   │ (base) │       │ (base) │       │ (base) │
   └────────┘       └────────┘       └────────┘
```

## The Bootstrap Path

```
Phase 1: LEARN
    │
    ├── Run experiments on base workers
    ├── Learn what makes them effective
    ├── Learn what compound intelligence adds
    ├── Learn what makes output valuable
    │
    ▼
Phase 2: ENGINEER
    │
    ├── Know how to engineer a PAIA that makes money
    ├── Specific configuration, plugins, MCPs
    ├── Specific prompting, skills, flights
    ├── Proven via experiments
    │
    ▼
Phase 3: DEPLOY
    │
    ├── Deploy the money-making PAIA
    ├── One Golden Worker
    ├── Produces revenue
    │
    ▼
Phase 4: REPLICATE
    │
    ├── Replicate to maintain it forever
    ├── Self-healing: if Golden Worker dies, respawn
    ├── Continuous: runs 24/7 without intervention
    │
    ▼
Phase 5: CONTROL PLANE
    │
    ├── Deploy the replicant once you have control plane
    ├── Full REST API + multi-interface access
    ├── Remote steering from anywhere
    │
    ▼
Phase 6: SCALE
    │
    ├── Continue...
    ├── Revenue → more Golden Workers
    ├── More workers → more experiments → better PAIAs
    └── Flywheel effect
```

## The Learning Loop

```
               ┌──────────────────┐
               │   Experiment     │
               │   (on workers)   │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   Learn          │
               │   (what works)   │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   Engineer       │
               │   (better PAIA)  │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   Deploy         │
               │   (make money)   │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   Replicate      │
               │   (maintain)     │
               └────────┬─────────┘
                        │
                        └──────────────► Scale → more experiments
```

## Current Position

We are at the START of Phase 1:
- Have: Researcher GNOSYS (compound intelligence, guru loop)
- Need: Worker container setup, experiment framework
- Goal: Learn what makes a money-making PAIA

## Next Immediate Step

Build the swarm library so we can spawn workers and run experiments.
