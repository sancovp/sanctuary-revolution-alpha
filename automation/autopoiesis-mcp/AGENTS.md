# Project Operational Knowledge

Autopoiesis MCP - Self-maintaining work loop for Claude Code.

## Build Commands

```bash
# Install dependencies
pip install -q -e /tmp/autopoiesis_mcp

# Verify installation
python -c "from autopoiesis_mcp import be_autopoietic; print('OK')"
```

## Test Commands

```bash
# Test the MCP tool directly
cd /tmp/autopoiesis_mcp && python -c "
from autopoiesis_mcp.server import be_autopoietic
result = be_autopoietic('promise')
print(result)
"

# Test hook exists
ls -la /tmp/autopoiesis_mcp/hooks/

# After restart, test via MCP
# (requires Claude Code restart to pick up MCP)
```

## Validation Steps

Before committing, ensure:
1. `pip install -q -e .` succeeds
2. MCP server imports without error
3. Hook files are present and valid Python
4. After restart: `be_autopoietic("promise")` returns promise template path

## Project Structure

```
/tmp/autopoiesis_mcp/
├── autopoiesis_mcp/     # MCP server code
│   ├── server.py        # FastMCP server with be_autopoietic tool
│   └── ...
├── hooks/               # Claude Code hooks
│   └── autopoiesis_stop_hook.py
├── commands/            # Slash commands
├── skills/              # Related skills
├── docs/                # Philosophy, usage docs
└── specs/               # Requirements for Ralph
```

## The Loop Test

To verify the loop works:
1. Call `be_autopoietic("promise")` - should vendor promise template
2. Edit and activate promise
3. Try to exit - should be blocked
4. Either complete genuinely or call `be_autopoietic("blocked")`
5. Exit should now be allowed

## Conventions

- MCP changes require `pip install -q` then `self_restart`
- Hook changes require Claude Code restart
- Test in actual Claude Code session, not just Python imports
