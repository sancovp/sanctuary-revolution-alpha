# GNOSYS Configuration Guide

GNOSYS uses a two-layer MCP configuration:

1. **Claude Code MCPs** (`claude.json`) - MCPs that Claude Code loads directly
2. **Strata MCPs** (`~/.config/strata/servers.json`) - MCPs that gnosys-treeshell orchestrates

## Why Two Layers?

```
Claude Code
    │
    ├── gnosys_kit (gnosys-treeshell)  ──────► Strata Config
    │                                              │
    │                                              ├── starlog
    │                                              ├── starship
    │                                              ├── waypoint
    │                                              ├── STARSYSTEM
    │                                              └── metastack
    │
    ├── skill_manager_treeshell
    │
    └── Context7 (optional)
```

**gnosys-treeshell** is a meta-MCP that provides JIT (just-in-time) access to many sub-MCPs. Instead of loading 20+ MCPs into Claude Code (which bloats the context), you load ONE TreeShell that connects to others on demand.

The sub-MCPs are configured in **Strata** (`~/.config/strata/servers.json`).

## Setup Steps

### Step 1: Install packages

```bash
pip install gnosys
```

This installs:
- gnosys-treeshell
- skill-manager-treeshell
- starlog-mcp, starship-mcp, waypoint-mcp, starsystem, metastack
- All dependencies

### Step 2: Set your HEAVEN_DATA_DIR

Choose where your GNOSYS data will live. Common choices:
- `~/.heaven_data` (home directory)
- `/tmp/heaven_data` (temporary, for testing)

### Step 3: Configure Strata

Copy `strata/servers.json` to `~/.config/strata/servers.json`:

```bash
mkdir -p ~/.config/strata
cp strata/servers.json ~/.config/strata/servers.json
```

Then edit `~/.config/strata/servers.json` and replace all `__FILL_IN_YOUR_PATH__` with your HEAVEN_DATA_DIR path.

### Step 4: Configure Claude Code

**DO NOT copy the file directly** - merge the `mcpServers` entries into your existing `claude.json`.

Open `claude_code_mcp_configs.json` and add each server entry to the `mcpServers` section of your `claude.json`.

Replace `__FILL_IN_YOUR_PATH__` with your HEAVEN_DATA_DIR path for each entry.

### Step 5: Run /gnosys:init

After configuration, run the init command in Claude Code:

```
/gnosys:init
```

This copies starter skills to your HEAVEN_DATA_DIR.

## File Reference

| File | Purpose | Location |
|------|---------|----------|
| `claude_code_mcp_configs.json` | MCPs for Claude Code to load directly | Merge into your `claude.json` |
| `strata/servers.json` | MCPs for gnosys-treeshell to orchestrate | Copy to `~/.config/strata/servers.json` |

## Troubleshooting

**"gnosys-treeshell can't find servers"**
- Check `~/.config/strata/servers.json` exists
- Verify JSON is valid (no trailing commas, etc.)

**"HEAVEN_DATA_DIR not set"**
- Make sure you replaced `__FILL_IN_YOUR_PATH__` in both config files
- Paths must be absolute (start with `/` or `~`)

**"Module not found" errors**
- Run `pip install gnosys` again
- Check you're using the right Python environment
