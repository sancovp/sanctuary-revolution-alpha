---
name: map
description: "Compile tasks through Map — queue-driven enrich/instance loop. Use when the user asks to define a task, break work into parts, or compile anything through the enrich/instance pattern. Also use when you need structured task decomposition with forward-progress guarantees."
user_invocable: true
argument-hint: "define <name> <parts...> | enrich <name> <parts...> | instance <name> '<content>' | next | queue | tree | stats | reset"
---

# Map

You are the execution engine. Map is the compiler.

Your output is a **call to Map** — either `enrich` or `instance`. The system manages the queue, the KV store, the state. The queue enables compilation **through** you.

## Two Moves

**enrich** — A name is too complex to produce directly. Break it into sub-parts.
```bash
python3 -m introduction_to_cs enrich <name> <part1> <part2> ...
```

**instance** — A name is clear enough to produce. Write the content.
```bash
python3 -m introduction_to_cs instance <name> '<content>'
```

## The Ratchet

- A queue item is **NOT DONE** until instanced. Enrich replaces it with sub-items — doesn't resolve it.
- Once instanced, it's **ratcheted** — if you re-enrich it, the new sub-parts go to the END of the queue.
- You must process the entire remaining queue before you get back to it. No going back and fiddling.
- This enforces forward progress. That's what makes it compilation, not chatting.

## Workflow

1. **Define** a task as parts:
```bash
python3 -m introduction_to_cs define <task> <part1> <part2> ...
```

2. **Check** what's next:
```bash
python3 -m introduction_to_cs next
```

3. For each item, **decide**: enrich (break down further) or instance (produce content)?

4. After instancing, `next` automatically shows what's next.

5. **Monitor** progress:
```bash
python3 -m introduction_to_cs queue    # see what's pending
python3 -m introduction_to_cs tree     # see the full structure
python3 -m introduction_to_cs stats    # completion numbers
python3 -m introduction_to_cs show <name>  # inspect a node
```

6. **Reset** to start over:
```bash
python3 -m introduction_to_cs reset
```

## Commands

| Command | What it does |
|---------|-------------|
| `define <name> <parts...>` | Start a compilation — set root task and initial parts |
| `enrich <name> <parts...>` | Break a name into sub-parts (sub-parts enter queue) |
| `instance <name> '<content>'` | Produce content for a name (name is done) |
| `next` | Show the next queue item with context |
| `queue` | Show the full queue |
| `tree` | Show the compilation tree |
| `show <name>` | Inspect a specific node |
| `stats` | Show completion progress |
| `reset` | Clear all state |

## Depth = Thought

The depth of enrichment is the depth of thought. Flat = fast and shallow. Deep = slow and thorough. You choose based on the task.

- If you can produce it → instance
- If it's too complex or ambiguous → enrich into sub-parts
- The queue enforces that you finish what you start before revisiting
