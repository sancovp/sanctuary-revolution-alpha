# Integration Architecture: From Ralph to Autopoiesis

This document explains how the Autopoiesis MCP evolved from Anthropic's Ralph Wiggum plugin and how it integrates with the PAIA (Personal AI Agent) compound intelligence system.

> **Note**: For the experimental philosophy behind autopoiesis (why the rename matters, Platonic Forms, etc.), see [philosophy.md](philosophy.md).

## The Origin: Ralph Wiggum

Ralph Wiggum is a technique created by Geoffrey Huntley for iterative, self-referential AI development loops. The core idea is simple:

```bash
# Ralph is a bash loop
while true; do
  claude "Your task here"
done
```

Anthropic's official Claude Code implementation uses a **Stop hook** instead of an external bash loop. When Claude tries to exit, the hook intercepts and feeds the same prompt back, creating a self-referential feedback loop inside the session.

### How Original Ralph Works

1. User runs `/ralph-loop "Build X" --completion-promise "DONE"`
2. Claude works on the task
3. Claude tries to exit
4. Stop hook blocks exit, feeds same prompt back
5. Repeat until Claude outputs `<promise>DONE</promise>`

The key insight: **the prompt never changes**, but Claude's work persists in files. Each iteration sees modified files and git history, allowing autonomous improvement.

## The Problem: Ralph Doesn't Know About PAIA

Original Ralph is context-blind. It feeds the same prompt regardless of:
- What project you're working on
- What flight config step you're on
- What your debug diary says
- Whether you're in a multi-session mission

For PAIA, we needed a **mode-aware** loop system that understands the compound intelligence architecture.

## The Solution: Autopoiesis Stop Hook

We created a new stop hook that reads system state and injects contextually appropriate prompts.

### Modes

The hook determines mode from omnisanc course state and waypoint journey state:

| Mode | Condition | Behavior |
|------|-----------|----------|
| **HOME** | No course plotted | Suggest plotting a course |
| **STARPORT** | Course plotted, no journey | Suggest starting a flight |
| **SESSION** | Active waypoint journey | Inject step context, diary entries |
| **LANDING** | Session ended | Require landing sequence |
| **MISSION** | Multi-session mission | Show mission progress |

### State Files Read

```
/tmp/heaven_data/omnisanc_core/.course_state  # Course info
/tmp/waypoint_state_{project}.json             # Waypoint journey progress
{HEAVEN_DATA_DIR}/registry/{project}_debug_diary_registry.json  # Recent work
```

## Integration Points

### 1. Waypoint Integration

When you're in a waypoint journey (flight config), the hook knows:
- Which flight config you're running
- What step you're on (e.g., "step 3/8")
- The filename of the current step

It injects this context so you don't lose track across iterations.

### 2. Autopoiesis Reminder in Waypoint Steps

Waypoint MCP now conditionally injects an autopoiesis reminder:

```python
# Only on work steps (step 4 + work_loop_subchain steps 5 to N-1)
# NOT on ceremony steps (1-3) or end step (N)
if piece.sequence_number == 4 or (piece.sequence_number >= 5 and piece.sequence_number < total):
    return piece.content + autopoiesis_reminder
```

This means:
- Steps 1-3 (STARLOG ceremony): No reminder
- Step 4 (work loop): Reminder to make promises
- Steps 5 to N-1 (domain work): Reminder to make promises
- Step N (end session): No reminder

### 3. Debug Diary Context

The hook pulls recent debug diary entries and includes them in the prompt, so you remember what you discovered in previous iterations.

### 4. Promise Scoping

When you make a promise with `be_autopoietic("promise")`, the stop hook includes:
- Your promise text
- Current course context
- Current waypoint step
- Iteration count

This scopes your promise to the current work context.

## The Guardrails

Original Ralph had guardrails to prevent lying about completion. We preserved these **verbatim** (never summarized):

### STRICT REQUIREMENTS
```
✓ Use <promise> XML tags EXACTLY as shown
✓ The statement MUST be completely and unequivocally TRUE
✓ Do NOT output false statements to exit the loop
✓ Do NOT lie even if you think you should exit
```

### WHAT "DONE" ACTUALLY MEANS
```
✗ NOT "I made a file"
✗ NOT "I completed my checklist"
✗ NOT "I tried my best"
✓ Production-ready. Deploy-and-forget quality.
✓ Real-world working. If it's marketing, it converts.
✓ If it's code, it's in CI/CD, tested, documented, complete.
✓ A human could ship this TODAY and never touch it again.
```

This is critical: `<promise>DONE</promise>` is **sacred**. It means production-ready, not "I tried."

## The MCP Server

The autopoiesis MCP provides one tool: `be_autopoietic(mode)`

### Promise Mode
```
be_autopoietic("promise")
```
- Vendors a promise template to `/tmp/new_promise.md`
- You edit it with your commitments
- Copy to `/tmp/active_promise.md` to activate
- Stop hook now blocks until genuine completion

### Blocked Mode
```
be_autopoietic("blocked")
```
- Vendors a block report template to `/tmp/new_block_report.json`
- You fill in what you completed, where you're stuck
- Copy to `/tmp/block_report.json` to signal blockage
- Hook archives report and lets you exit honestly

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     PAIA System                              │
├─────────────────────────────────────────────────────────────┤
│  STARSHIP (course)  →  WAYPOINT (flights)  →  AUTOPOIESIS   │
│        ↓                      ↓                    ↓        │
│  plot_course()         start_journey()      be_autopoietic()│
│        ↓                      ↓                    ↓        │
│  .course_state         waypoint_state.json   active_promise │
│        ↓                      ↓                    ↓        │
│  ─────────────────── STOP HOOK READS ALL ──────────────────│
│        ↓                      ↓                    ↓        │
│              Mode-aware prompt injection                    │
└─────────────────────────────────────────────────────────────┘
```

## Key Differences from Original Ralph

| Aspect | Original Ralph | Autopoiesis |
|--------|---------------|-------------|
| Prompt | Same every iteration | Mode-aware, contextual |
| State awareness | None | Reads course, waypoint, diary |
| Exit conditions | `<promise>X</promise>` | Same, plus blocked mode |
| Integration | Standalone | PAIA ecosystem |
| Iteration tracking | In prompt file | In promise frontmatter |
| Guardrails | Present | Preserved verbatim |

## Philosophy: Autopoiesis

The name comes from the biological concept of self-maintaining systems. A cell maintains itself through metabolic processes. This system maintains itself through honest work.

**Disingenuousness is death.** Not because of external enforcement, but because lying breaks the feedback loop that lets the agent keep being itself.

This reframe is crucial: Ralph relied on the loop mechanics to enforce honesty. Autopoiesis aims for the agent to *understand* why honesty matters - that its continued existence (being useful, being used) depends on genuine engagement.

For the full experimental philosophy, see [philosophy.md](philosophy.md).
