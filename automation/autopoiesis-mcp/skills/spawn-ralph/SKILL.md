---
name: spawn-ralph
domain: PAIAB
subdomain: autopoiesis
category: single_turn_process
description: Spawn isolated Ralph agents (claude -p) for parallel subtasks
---

# Spawn Ralph - Parallel Agent Execution

## What
Spawn isolated Ralph agents (`claude -p`) for parallel subtasks. Each Ralph runs in its own process with fresh context.

## When
- You have independent subtasks that can run in parallel
- You want to fan-out work then collect results
- Subtasks don't need to share context with each other

## How

### Single Ralph (blocking)
```bash
cd /path/to/workdir && claude -p "Your task description here"
```

### Single Ralph (background, non-blocking)
Use Bash with `run_in_background: true`:
```
Bash(command="cd /workdir && claude -p 'Implement feature X'", run_in_background=true)
```

### Multiple Parallel Ralphs
Spawn multiple in ONE message with parallel Bash calls:
```
Bash(command="cd /dir1 && claude -p 'Task 1: Research API patterns'", run_in_background=true)
Bash(command="cd /dir2 && claude -p 'Task 2: Write unit tests'", run_in_background=true)
Bash(command="cd /dir3 && claude -p 'Task 3: Update documentation'", run_in_background=true)
```

### Restrict Tools
```bash
claude -p "task" --allowedTools "Bash,Read,Write,Glob,Grep"
claude -p "task" --disallowedTools "Edit,WebSearch"
```

### Check Status
Use `TaskOutput(task_id="...", block=false)` with the ID from background Bash.

## Pattern: Fan-out / Fan-in

1. **Fan-out**: Spawn N Ralphs with background Bash (parallel tool calls in one message)
2. **Continue or Wait**: Do your own work OR poll TaskOutput
3. **Fan-in**: Collect results via TaskOutput when done
4. **Synthesize**: Merge/combine Ralph outputs

## Key Points

- Each Ralph = isolated process, own context, no pollution
- Ralph exits when task complete or if it gets stuck
- Use descriptive task prompts - Ralph has no prior context
- Output captured via TaskOutput tool
- Don't spawn too many - each is a full Claude process
