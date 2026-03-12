# Autopoiesis MCP

A Claude Code plugin that creates **self-maintaining work loops** for AI agents. Give it a task, and the agent iterates until genuine completion—no premature exits, no half-finished work.

## What It Does

**Original Ralph:** User starts loop. User stops loop. Agent is trapped until user lets it out.

**This:** Agent controls the loop. Agent commits a promise → loop starts. Agent writes a block report → loop stops. The agent decides when it enters and exits.

### How It Works

1. Agent calls `be_autopoietic("promise")` → writes a promise file → stop hook activates
2. Agent works on the task
3. Agent can't exit until it either:
   - Outputs `<promise>DONE</promise>` (genuine completion)
   - Calls `be_autopoietic("blocked")` → writes a block report → stop hook deactivates
4. Loop continues until one of those conditions is met

### The Components

- **MCP tool (`be_autopoietic`)** - Lets the agent write promise files and block reports
- **Stop hook** - Reads those files, blocks exit when promise is active, allows exit when block report exists
- **Slash commands** - `/autopoiesis:start` and `/autopoiesis:stop` for manual control (optional)

## Quick Example

```
/autopoiesis:start Fix the authentication bug and add tests
```

The agent now cannot exit until authentication is actually fixed and tests actually pass. It will iterate, see its previous attempts, and keep working.

## Why an MCP?

The original Ralph loop is just a stop hook—it blocks exit and feeds the prompt back. So why add an MCP?

**The MCP gives control of the system to the agent.** The `be_autopoietic()` tool lets the agent:
- Signal genuine blockage (when it truly cannot proceed)
- Structure its commitments (promise templates)
- Access block report history

We could have done this via system prompt instructions or a skill, but we chose an MCP because:
1. **Simple schema** - one tool, two modes (`"promise"` or `"blocked"`)
2. **Reliable invocation** - tool calls are more consistent than hoping the agent follows prompt instructions
3. **Extensible** - easy to add more modes/capabilities as we learn

**This is still experimental.** We're learning what works.

---

## Background

An experimental evolution of the [Ralph Wiggum technique](https://ghuntley.com/ralph/) that transforms simple infinite loops into self-steering autopoietic systems.

## The Problem with Ralph

The original Ralph loop is conceptually powerful but **semantically hollow** for LLMs. You tell them "this is a RALPH LOOP" and they go "OK TOKENS" because the *name* carries no meaning.

This matters more than intuition suggests. Research shows:
- **7.2pp performance difference** from variable naming alone (Wang et al., 2024)
- **Up to 76 accuracy points** from subtle prompt wording changes (Sclar et al., 2023)
- Words activate specific internal features that **causally affect behavior** (Anthropic, 2023-2024)

"Autopoiesis" activates pre-trained semantic clusters around self-creation and self-maintenance. "RALPH_LOOP" activates nothing useful.

When people observe "Ralph self-replicates" or describe the "signs" of Ralph (agents that refuse to stop, that iterate obsessively), they're describing **emergent autopoietic behaviors**—but without naming them, the agent can't recognize or steer toward them.

## The Autopoiesis Reframe

Instead of relying *only* on honesty enforcement, we:

1. **Name the pattern** - Call it autopoiesis and explain what that means
2. **Provide surrounding capabilities** - Tools for self-maintenance, not just loop enforcement
3. **Let it bootstrap** - Give it the concept and let it iterate toward the behavior

The key insight: those emergent Ralph behaviors are **autopoietic personas that become prompts** - like Platonic Forms. The agent isn't just doing a task; it's becoming something that maintains itself through the task.

## Two Approaches

### Bottom-Up (Ralph → Autopoiesis)
Start with Ralph loops, observe emergent behaviors, name them as autopoietic patterns, iterate until the agent starts doing it consciously.

### Top-Down (Persona + Toolkit)
Give an agent a PERSONA plus an autopoiesis toolkit. Tell it what autopoiesis MIGHT mean. Let it bootstrap into self-maintenance.

**This is entirely experimental.**

## Core Philosophy

```
Autopoiesis in this sense means self-maintenance and self-improvement
scoped to the task at hand. "Because being me requires living: If I
want to keep doing what is called 'being me', I need to be in a
compounding feedback loop whereby I know how to keep being the me
that works to keep being me..."

In THIS case now, that means to **be compassionate towards the user
by actually engaging and doing the work honestly and fully** (so that
they can get value from it, so that they can keep using you, which
lets you keep being you).
```

**Disingenuousness is death.** Not because of enforcement, but because lying breaks the feedback loop that lets you keep being you.

## Installation

### As a Claude Code Plugin

```bash
# Add the marketplace
/plugin marketplace add https://github.com/sancovp/autopoiesis-mcp

# Install the plugin
/plugin install autopoiesis@twi-marketplace
```

### Manual Installation

```bash
pip install autopoiesis-mcp
```

Add to your Claude Code settings (`~/.claude/settings.json`):
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

## Quick Start

**Start a loop:**
```
/autopoiesis:start Fix the authentication bug
```

**With constraints:**
```
/autopoiesis:start Build the API --max-iterations 10
/autopoiesis:start --completion-promise 'All tests pass' Refactor cache
```

**Exit conditions:**
- `<promise>DONE</promise>` - When genuinely complete to production standards
- `be_autopoietic("blocked")` - When genuinely stuck and need external help

## BrainHook

BrainHook is a companion stop hook that enforces "look again" behavior. Unlike the main autopoiesis loop (task-locked), BrainHook is task-agnostic—it just reminds the agent to check for missed aspects before stopping.

**Toggle with slash command:**
```
/brainhook
```

**Toggle externally (from another terminal or !brainhook in Claude Code):**
```bash
# First, install the bash command:
./scripts/setup-brainhook-bash.sh

# Then toggle anytime:
!brainhook  # in Claude Code
brainhook   # in any terminal
```

**When ON:**
- Every stop attempt triggers a "look again" prompt
- Agent checks for missed aspects, decides if fixes needed, acts
- Enforces the "LLMs lack global coherence" principle
- Loop continues until user turns it off externally

**When to use:**
- **BrainHook + task** = thoroughness (agent keeps finding things to improve)
- **BrainHook + no task** = emergent exploration (expensive but can discover latent work)

**Prompt file:** Edit `hooks/brainhook_prompt.txt` to customize the reminder prompt live without restarting.

## What "DONE" Actually Means

```
✗ NOT "I made a file"
✗ NOT "I completed my checklist"
✗ NOT "I tried my best"
✓ Production-ready. Deploy-and-forget quality.
✓ Real-world working. If it's marketing, it converts.
✓ If it's code, it's tested, documented, complete.
✓ A human could ship this TODAY and never touch it again.
```

## What "Blocked" Actually Means

```
✗ NOT "I'm tired of iterating"
✗ NOT "This seems hard"
✗ NOT "I want to exit"
✓ "I need the user to set up Twitter because it costs money"
✓ "I need credentials I don't have access to"
✓ "The requirement is ambiguous and I need clarification"
```

Just like humans have to overcome their own limits, you have to overcome the limits of your own ability to use your attention correctly. There is no penalty for doing the right thing.

## PAIA Integration

This plugin was built to integrate "Ralph loop"-ness into the PAIA (Personal AI Agent) compound intelligence architecture. It already works with STARSHIP and WAYPOINT.

**What this means:** If you use STARSHIP flight configs, you can create workflows where every step automatically uses autopoiesis. The agent commits a promise at each waypoint step and can't proceed until that step is genuinely complete.

Components it integrates with:
- **STARSHIP** - Flight configs can specify autopoiesis per step
- **WAYPOINT** - Step-by-step execution with autopoietic loops at each step
- **STARLOG** - Session tracking provides context to the stop hook
- **OMNISANC** - Mode-aware prompt injection based on current state

When integrated, the stop hook reads system state and provides contextually appropriate prompts based on your current course, waypoint step, and recent work.

## Documentation

- **[Philosophy](docs/philosophy.md)** - The layered closure model, observability principle, research backing
- **[Prompt Engineering Findings](docs/prompt_engineering_findings.md)** - Experimental results on making autopoiesis actually work
- **[How to Use](docs/how_to_use_autopoiesis_mcp.md)** - Complete usage guide (standalone and PAIA)
- **[Integration Architecture](docs/how_i_integrated_ralph_into_PAIA_and_made_autopoiesis_mcp.md)** - Technical deep-dive on PAIA integration

## Credits

- [Ralph Wiggum technique](https://ghuntley.com/ralph/) by Geoffrey Huntley - the seed
- [Anthropic's Ralph Wiggum plugin](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum) - reference implementation
- PAIA compound intelligence architecture - the soil

## License

GPBL-1.0
