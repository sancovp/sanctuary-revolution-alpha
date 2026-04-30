"""Sanctuary Revolution TreeShell MCP Server — SSE Transport (FastMCP).

Persistent server for Heaven agents. Keeps strata connections alive between calls.
Started by WakingDreamer, conductor connects via SSE URL.

Usage:
    python -m sanctuary_revolution_treeshell.mcp_server_sse [--port 9090]
"""
import asyncio
import json
import logging
import os
import re
import sys
import traceback

from fastmcp import FastMCP

from sanctuary_revolution_treeshell import SancrevTreeShell
from heaven_tree_repl import render_response

logger = logging.getLogger(__name__)

DEFAULT_PORT = 9090

# Persistent shell instance — lives for the lifetime of the server
_shell = None


async def _get_shell():
    global _shell
    if _shell is None:
        heaven_data_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        user_config_path = None
        try:
            for item in os.listdir(heaven_data_dir):
                if item.startswith("sancrev_treeshell"):
                    configs = os.path.join(heaven_data_dir, item, "configs")
                    if os.path.exists(configs):
                        user_config_path = configs
                        break
        except Exception:
            pass
        _shell = SancrevTreeShell(user_config_path=user_config_path)
    return _shell


# Create FastMCP app with the full tool description (same as stdio version)
TOOL_DESC = """Sanctuary Revolution TreeShell - Unified interface (Game + Builders + GNOSYS + Skills).

Navigation:
- 'nav' — Full tree with coordinates
- 'jump <node_name>' — Go to node by full name or numeric coordinate
- 'back' — Go up one level
- 'menu' — Show current position menu

Execution:
- '<node>.exec {"arg": "val"}' — Jump + execute (e.g., 'equip.exec {"name": "my-skill"}')
- 'exec {"args"}' — Execute at current position

Addressing (valid inputs only):
- Full node name: 'agent_management_equipment'
- Numeric coordinate: '0.2.1'
- Registered shortcut: 'nav', 'lang', 'brain', etc.
- Bare words that aren't any of the above are INVALID

=== GNOSYS MCP Router (jump gnosys) ===
discover_server_actions(user_query) | execute_action(server_name, action_name, body_schema)
get_action_details(server_name, action_name) | manage_servers | search_mcp_catalog(query)

=== Skills (jump skills) ===
list_skills | list_domains | list_by_domain(domain) | get_skill(name) | search_skills(query)
equip(name) | unequip(name) | list_equipped | get_equipped_content

=== TreeKanban (jump treekanban) ===
view_board | view_lane | tk_add_deliverable | tk_add_task | get_next | move_to_lane"""

mcp = FastMCP("sanctuary-revolution-treeshell-sse")


# Planning commands that need CAVE/OMNISANC hook notification
_PLANNING_COMMANDS = {"tk_add_deliverable", "tk_add_task", "tk_update_task", "get_next"}

# TRIGGERS: CAVE/sancrev:8080 via HTTP POST — CAVE_URL env var
CAVE_URL = os.environ.get("CAVE_URL", "http://localhost:8080")


def _is_exec_command(command: str) -> bool:
    """Check if command is any .exec call — POST all to CAVE, let OMNISANC filter."""
    return ".exec" in command


# TRIGGERS: OMNISANC/CAVE PostToolUse pipeline
def _post_to_cave_hook(command: str, rendered_output: str):
    """POST to CAVE /hook/posttooluse — mimics paia_posttooluse for non-Claude-Code callers."""
    import urllib.request
    import urllib.error

    hook_data = json.dumps({
        "tool_name": "mcp__sancrev_treeshell__run_conversation_shell",
        "tool_input": {"command": command},
        "tool_response": rendered_output,
        "from_conductor": True,
    }).encode()

    try:
        req = urllib.request.Request(
            # TRIGGERS: CAVE/sancrev:8080/hook/posttooluse via HTTP POST
            f"{CAVE_URL}/hook/posttooluse",
            data=hook_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            logger.info(f"[CAVE POST] {command[:50]}... → {result.get('result', '?')}")
    except urllib.error.URLError as e:
        logger.warning(f"[CAVE POST] CAVE offline: {e}")
    except Exception as e:
        logger.warning(f"[CAVE POST] Failed: {e}")


@mcp.tool(description=TOOL_DESC)
async def run_conversation_shell(command: str) -> str:
    """Execute a TreeShell command."""
    shell = await _get_shell()
    try:
        result = await shell.handle_command(command)
        rendered_output = render_response(result)

        # Auto-connect retry
        if "not connected" in rendered_output and "manage_servers" in rendered_output:
            match = re.search(r"'(\w[\w-]*)' not connected", rendered_output)
            if match:
                server_name = match.group(1)
                logger.info(f"Auto-connecting '{server_name}' and retrying...")
                await shell.handle_command(f'manage_servers.exec {{"connect": "{server_name}"}}')
                for _ in range(10):
                    await asyncio.sleep(1)
                    check = await shell.handle_command(command)
                    check_output = render_response(check)
                    if "not connected" not in check_output:
                        rendered_output = check_output
                        break
                else:
                    return rendered_output

        # POST to CAVE for planning commands — OMNISANC hooks fire
        if _is_exec_command(command) and CAVE_URL:
            # TRIGGERS: OMNISANC/CAVE PostToolUse pipeline
            _post_to_cave_hook(command, rendered_output)

        return rendered_output
    except Exception as e:
        logger.error(f"Shell command failed: {traceback.format_exc()}")
        return f"Error: {e}"


async def main(port: int = DEFAULT_PORT):
    # Pre-connect starsystem MCP set
    try:
        shell = await _get_shell()
        from strata.treeshell_functions import manage_servers
        result = await manage_servers(connect_set="starsystem")
        print(f"[SSE] Pre-connected starsystem MCP set: {result}", file=sys.stderr)
    except Exception as e:
        print(f"[SSE] Pre-connect warning (non-fatal): {e}", file=sys.stderr)

    print(f"[SSE] Sancrev TreeShell SSE server on port {port}", file=sys.stderr)
    await mcp.run_sse_async(host="0.0.0.0", port=port)


if __name__ == "__main__":
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])
    asyncio.run(main(port=port))
