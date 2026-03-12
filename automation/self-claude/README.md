# Self-Claude Commands

Bash utilities and MCP for Claude to manage its own session via tmux.

## Architecture

```
Claude (main agent)
  → calls orchestrator script (returns immediately)
      → spawns detached handler (nohup/disown)
          → polls for claude death
          → relaunches claude
```

## Components

### Scripts (in /usr/local/bin/)

1. **claude-debug** - Launch Claude in tmux with debug mode
2. **self_restart** - Orchestrator that schedules restart
3. **claude_restart_handler** - Detached handler that polls and relaunches
4. **self_compact** - Triggers /compact via tmux (existing)
5. **rules** - Manage Claude rule files

### MCP (self-compact-mcp)

Single tool: `use_self_compact(help: Optional[bool])`

- Returns instructions for using self_compact
- Checks if setup is complete
- NOT in gnosys_kit (main agent only)
- Auto-patches subagent configs to block itself

## Flow: self_restart

1. Claude calls `self_restart` bash command
2. Orchestrator spawns detached handler, returns immediately
3. Handler waits 5s for tool to return
4. Handler sends `/exit` to tmux
5. Handler polls until claude process dies
6. Handler sends `claude` to relaunch

## Flow: self_compact

1. Claude calls `self_compact` with run_in_background
2. Script sleeps 5s, sends `/compact`, sleeps 5s, sends Enter
3. /compact writes summary and truncates context

## Subagent Isolation

Problem: Subagents inherit MCPs and can see skills in ~/.claude/skills/

Solution:
- self-compact-mcp NOT in gnosys_kit
- MCP checks subagent configs before allowing use
- Auto-patches configs to block itself, triggers restart
