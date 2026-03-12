# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Self-Claude Commands

Utilities for Claude to manage its own tmux session - restart, compact, etc.

## Key Files
- README.md - Architecture and flow docs
- scripts/ - Bash scripts (to be created)
- mcp/ - self-compact-mcp (to be created)

## Next Steps
1. ~~Create scripts/self_restart (orchestrator)~~ DONE
2. ~~Create scripts/claude_restart_handler (detached poller)~~ DONE
3. Test restart flow
4. Create mcp/self_compact_mcp.py
5. Add subagent blocking logic
