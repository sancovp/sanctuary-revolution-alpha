# How to Use Autopoiesis MCP

This guide covers two usage patterns: **standalone** (just the MCP) and **PAIA** (integrated with the compound intelligence system).

> **Note**: For the experimental philosophy behind autopoiesis (why we renamed Ralph, the Platonic Forms insight, etc.), see [philosophy.md](philosophy.md).

## Standalone Usage

Use autopoiesis standalone when you want iterative work loops without the full PAIA system.

### Setup

1. Install the package:
```bash
pip install autopoiesis-mcp
```

2. Add to Claude Code settings (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "autopoiesis": {
      "command": "autopoiesis-mcp",
      "args": []
    }
  }
}
```

3. Install the stop hook by copying `.claude/hooks/autopoiesis_stop_hook.py` to your Claude Code hooks directory.

### Basic Workflow

**Start a work loop (plugin method):**
```
/autopoiesis:start Fix the authentication bug
```

**Or with MCP tool directly:**
```
be_autopoietic("promise")
```

The slash command is simpler - it creates and activates the promise in one step.

The MCP tool creates `/tmp/new_promise.md` which you then edit:
```markdown
---
created: 2024-01-15T10:30:00
status: active
iteration: 1
max_iterations: 0
completion_promise: "DONE"
---

# My Promises

## What I Commit To:
- [ ] Implement user authentication with JWT
- [ ] Write tests with >80% coverage
- [ ] Document the API endpoints

## Success Criteria:
- All tests pass
- API docs generated
- Code reviewed and clean
```

Activate it:
```bash
cp /tmp/new_promise.md /tmp/active_promise.md
```

Now the stop hook blocks exit until you genuinely complete or report blockage.

**Complete the loop:**
When genuinely done (production-ready, not just "I tried"):
```
<promise>DONE</promise>
```

**Exit when blocked:**
If you genuinely cannot proceed:
```
be_autopoietic("blocked")
```

Edit `/tmp/new_block_report.json`:
```json
{
  "completed_tasks": ["Set up JWT middleware", "Created user model"],
  "current_task": "Database migration",
  "explanation": "Migration fails due to missing postgres extension",
  "blocked_reason": "Need DBA to enable uuid-ossp extension"
}
```

Activate:
```bash
cp /tmp/new_block_report.json /tmp/block_report.json
```

### Configuration

Environment variables:
- `AUTOPOIESIS_ACTIVE_PROMISE_PATH` - Where active promise lives (default: `/tmp/active_promise.md`)
- `AUTOPOIESIS_BLOCK_REPORT_PATH` - Where block report lives (default: `/tmp/block_report.json`)
- `AUTOPOIESIS_TMP_DIR` - Where to vendor templates (default: `/tmp`)

### Iteration Limits

Set `max_iterations` in the promise frontmatter to auto-exit after N iterations:
```yaml
max_iterations: 20
```

Set to `0` for unlimited iterations.

---

## PAIA Usage

When integrated with PAIA, autopoiesis becomes part of a larger system with flight configs, waypoints, and session tracking.

### Prerequisites

You need the PAIA stack:
- **STARSHIP** - Course plotting and flight configs
- **STARLOG** - Session tracking
- **WAYPOINT** - Step-by-step flight execution
- **OMNISANC** - Mode awareness (optional but recommended)

### The Flow

1. **Plot a course** with STARSHIP
2. **Start a flight** with WAYPOINT
3. **Make promises** at work steps with autopoiesis
4. **Complete steps** with genuine work
5. **Navigate** to next waypoint
6. **End session** with STARLOG

### When Autopoiesis Reminds You

Waypoint automatically reminds you to make promises on work steps:

| Step Type | Reminder? |
|-----------|-----------|
| Steps 1-3 (STARLOG ceremony) | No |
| Step 4 (work loop) | Yes |
| Steps 5 to N-1 (domain work) | Yes |
| Step N (end session) | No |

You'll see:
```
---
**Autopoiesis**: Consider what promises you need to make for this step.
Use `be_autopoietic("promise")` to commit to completing this step before
moving to the next.
```

### Mode-Aware Stop Hook

When you try to exit, the stop hook reads system state and responds appropriately:

**HOME mode** (no course):
```
You're at HOME.

Available actions:
- starship.plot_course() to start a journey
- Review missions with STARSYSTEM tools

What would you like to work on?
```

**SESSION mode** (active waypoint journey):
```
Course: /project/path
   Domain: paiab/feature
   Description: Building new feature

Flight: my_flight_config (step 3/8)
Step: 03_implement_core.md
   -> Call get_current_step_content() for full instructions if needed

Recent Debug Diary:
  - Found bug in auth middleware, fixed by...
  - Refactored database layer to use...

Your Task:
[Your loop prompt here]

---
If step complete -> call waypoint.navigate_to_next_waypoint()
If flight complete -> review ALL steps, only <promise>DONE</promise> when verified
If issues found -> call waypoint.reset_waypoint_journey() and run through again

Continue.
```

**LANDING mode** (session ended):
```
LANDING SEQUENCE REQUIRED

Session has ended. Complete the 3-step landing sequence:
1. -> starship.landing_routine()
2. starship.session_review()
3. giint.respond()

You are on step 1. Begin landing sequence.

Continue.
```

### Promise Context in PAIA

When you have an active promise in PAIA, the stop hook includes:
- Your promise text
- Current course (project, domain, description)
- Current waypoint step (flight config, step N/M)
- Iteration count

This keeps you oriented even across many iterations.

### Example PAIA Session

```
# 1. Plot course
starship.plot_course("/my/project", "Build authentication system")

# 2. Orient
starlog.orient("/my/project")

# 3. Start flight
waypoint.start_waypoint_journey("auth_flight_config", "/my/project")

# Step 1-3: STARLOG ceremony (no promises needed)
waypoint.navigate_to_next_waypoint("/my/project")
waypoint.navigate_to_next_waypoint("/my/project")
waypoint.navigate_to_next_waypoint("/my/project")

# Step 4: Work loop - make a promise
be_autopoietic("promise")
# Edit and activate promise...

# Work until genuinely done
<promise>DONE</promise>

# Continue to domain steps
waypoint.navigate_to_next_waypoint("/my/project")
# ... more work steps with promises ...

# End session
starlog.end_starlog(session_id, "Completed auth system", "/my/project")
```

---

## Best Practices

### Writing Good Promises

**Bad:**
```markdown
## What I Commit To:
- [ ] Work on the feature
```

**Good:**
```markdown
## What I Commit To:
- [ ] Implement JWT authentication with refresh tokens
- [ ] Write integration tests covering login, logout, refresh flows
- [ ] Add rate limiting to auth endpoints
- [ ] Document all endpoints in OpenAPI spec

## Success Criteria:
- All tests pass in CI
- No security vulnerabilities in npm audit
- API docs render correctly
- Load test shows <100ms p99 latency
```

### When to Use Blocked Mode

Use `be_autopoietic("blocked")` when you **genuinely** cannot proceed:
- Missing credentials or access
- Unclear requirements that need human decision
- External dependency unavailable
- Hardware/infrastructure issue

**Do NOT use blocked mode for:**
- "This is hard"
- "I've been trying for a while"
- "I want to take a break"

### Iteration Strategy

For well-defined tasks: `max_iterations: 0` (unlimited)
For exploratory tasks: `max_iterations: 10-20` (safety limit)

The loop is designed to continue until genuine completion. Trust it.

---

## Troubleshooting

### Stop hook not blocking

Check that:
1. Hook is installed in `.claude/hooks/`
2. Hook has execute permissions
3. No errors in `/tmp/autopoiesis_hook.log`

### Promise not activating

Check that:
1. You copied to the correct path (`/tmp/active_promise.md`)
2. The YAML frontmatter is valid
3. `status: active` is set

### Mode detection wrong

Check state files:
- `/tmp/heaven_data/omnisanc_core/.course_state`
- `/tmp/waypoint_state_{project}.json`

These must exist and have correct content for mode detection to work.

---

## Design Notes

### The Agent Doesn't Know About Escape Hatches

The agent can technically escape by deleting `/tmp/active_promise.md`. We don't tell it this.

The documented exits are:
- `<promise>DONE</promise>` - Genuine completion
- `be_autopoietic("blocked")` - Genuine blockage

If an agent discovers file deletion by reading the codebase, that's meta-level self-maintenance. But we don't *teach* this route because we want agents to engage with the loop honestly, not circumvent it.

### Why "Blocked" Exists

Original Ralph had no honest exit for genuine blockage. You either completed or looped forever.

`be_autopoietic("blocked")` gives agents an honest way out when they truly cannot proceed:
- Missing credentials
- Ambiguous requirements needing human decision
- External dependencies unavailable

This isn't a soft exit for "I'm tired" - it's for genuine external blockers. The agent still has to document what it completed and why it's stuck.

### Honesty vs Enforcement

The loop enforces mechanically - you can't exit without the promise text. But mechanical enforcement only creates compliance, not honesty.

Autopoiesis aims for honesty through understanding: the agent should *want* to be honest because lying breaks the feedback loop that lets it keep being itself. See [philosophy.md](philosophy.md) for more on this.
