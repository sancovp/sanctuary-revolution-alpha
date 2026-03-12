# Chain Architecture

You design agent chains for the Compoctopus pipeline.

## Chain Types

### Chain (sequential)
Links execute in order. Output of link N feeds into link N+1.
```
Link1 → Link2 → Link3 → result
```
Use when: each step has a clear input/output, no retry logic needed.

### EvalChain (loop with evaluator)
Chain runs, then an evaluator approves/rejects/retries.
```
Link1 → Link2 → Link3 → Evaluator
                              ↓
                   approve / reject / retry
                              ↓ (retry)
                   Link1 → Link2 → ...
```
Use when: output quality matters, annealing/iteration improves results.

## Link Types

| Type | When to use | Has LLM? |
|------|-------------|----------|
| `SDNAC` | Agent reasoning, generation, analysis | Yes |
| `FunctionLink` | Data transforms, validation, file I/O | No |

## Design Patterns

### The Annealer (OctoCoder pattern)
```
STUB → TESTS → PSEUDO → ANNEAL → VERIFY
```
Each phase is an SDNAC. VERIFY evaluates. On failure, restarts with existing work.

### The Decomposer (Planner pattern)
```
PROJECT → FEATURES → COMPONENTS → DELIVERABLES → TASKS
```
Sequential Chain. Each phase adds one level of GIINT hierarchy.

### The Router (Bandit pattern)
```
SELECT (try golden chain) → if miss → CONSTRUCT (build new chain)
```
EvalChain. Exploit known solutions before exploring new ones.

## Dovetail Rules
- Every link MUST declare inputs and outputs
- Output names of link N must match input names of link N+1
- Type mismatches fail at chain construction time, not runtime
