#!/usr/bin/env python3
"""
Strata Unwrap Utilities

Helper functions for hooks to work with Strata-wrapped and TreeShell-wrapped MCP calls.

When MCPs are behind Strata router, all tool calls become:
  tool_name: "mcp__strata__execute_action"
  tool_input: {
    "server_name": "carton",
    "action_name": "add_concept",
    "body_schema": "{...}"
  }

When MCPs are behind TreeShell (gnosys_kit or skill_manager_treeshell), calls become:
  tool_name: "mcp__gnosys_kit__run_conversation_shell"
  tool_input: {
    "command": "execute_action.exec {\"server_name\": \"starlog\", \"action_name\": \"orient\", ...}"
  }

These utilities unwrap both patterns to get the real tool info.
"""

import json
import re
import glob
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


# TreeShell tool names that wrap other MCPs
TREESHELL_TOOLS = [
    'mcp__gnosys_kit__run_conversation_shell',
    'mcp__skill_manager_treeshell__run_conversation_shell',
    'mcp__sancrev_treeshell__run_conversation_shell',
]

# Cache for coordinate -> node_name mapping (from nav_config.json)
_COORD_CACHE: Optional[Dict[str, str]] = None

def _resolve_coordinate_to_name(coordinate: str) -> Optional[str]:
    """Resolve a numeric coordinate (e.g. '0.2.1.18') to a node name (e.g. 'tk_add_deliverable')."""
    global _COORD_CACHE
    if _COORD_CACHE is None:
        _COORD_CACHE = {}
        nav_paths = [
            # CONNECTS_TO: nav_config.json (read) — maintained by sancrev-treeshell package
            "/tmp/sanctuary-revolution-treeshell/sanctuary_revolution_treeshell/configs/nav_config.json",
        ]
        for nav_path in nav_paths:
            try:
                with open(nav_path) as f:
                    nav = json.load(f)
                for coord, name in nav.items():
                    _COORD_CACHE[coord] = name
            except (json.JSONDecodeError, OSError):
                continue
    return _COORD_CACHE.get(coordinate)


# Cache for family node -> (server_name, action_name) mapping
_FAMILY_NODE_CACHE: Optional[Dict[str, Tuple[str, str]]] = None

def _load_family_node_map() -> Dict[str, Tuple[str, str]]:
    """Load all family configs and build node_name -> (server_name, action_name) map.

    Scans all treeshell family config JSON files for nodes that wrap execute_action
    and have default_args with server_name and action_name.

    Cached after first load.
    """
    global _FAMILY_NODE_CACHE
    if _FAMILY_NODE_CACHE is not None:
        return _FAMILY_NODE_CACHE

    _FAMILY_NODE_CACHE = {}

    # Scan known family config directories
    family_dirs = [
        "/tmp/sanctuary-revolution-treeshell/sanctuary_revolution_treeshell/configs/families/",
        # Add more treeshell family dirs here as needed
    ]

    for family_dir in family_dirs:
        for config_path in glob.glob(f"{family_dir}*.json"):
            try:
                with open(config_path) as f:
                    config = json.load(f)

                # Family configs have nodes inside a "nodes" key
                nodes = config.get("nodes", config)
                for node_name, node_def in nodes.items():
                    if not isinstance(node_def, dict):
                        continue
                    # Look for nodes that wrap execute_action with default_args
                    if node_def.get("function_name") == "execute_action":
                        default_args = node_def.get("default_args", {})
                        server = default_args.get("server_name", "")
                        action = default_args.get("action_name", "")
                        if server and action:
                            _FAMILY_NODE_CACHE[node_name] = (server, action)
            except (json.JSONDecodeError, OSError):
                continue

    return _FAMILY_NODE_CACHE


def _parse_treeshell_command(command: str) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Parse a TreeShell command to extract server_name, action_name, and args.

    Command formats:
    - "execute_action.exec {\"server_name\": \"starlog\", \"action_name\": \"orient\", ...}"
    - "tk_add_task.exec {\"project_id\": \"...\", ...}" (family node with default_args)
    - "nav" (navigation, no action)
    - "jump execute_action" (navigation, no action)

    Returns:
        Tuple of (server_name, action_name, body_schema) or (None, None, {}) if not an execute
    """
    if not command:
        return None, None, {}

    # Check for execute_action.exec pattern (explicit server/action in args)
    exec_match = re.match(r'execute_action\.exec\s+(.+)', command, re.DOTALL)
    if exec_match:
        try:
            args = json.loads(exec_match.group(1))
            server_name = args.get('server_name', '')
            action_name = args.get('action_name', '')
            body_schema = args.get('body_schema', {})

            # body_schema might be a string that needs parsing
            if isinstance(body_schema, str):
                try:
                    body_schema = json.loads(body_schema)
                except (json.JSONDecodeError, TypeError):
                    body_schema = {}

            return server_name, action_name, body_schema
        except (json.JSONDecodeError, TypeError):
            pass

    # Check for family_node.exec pattern (server/action from default_args in config)
    # Matches both named (tk_add_deliverable.exec) and coordinate (0.2.1.18.exec) syntax
    family_exec_match = re.match(r'([\w.]+)\.exec(?:\s+(.+))?', command, re.DOTALL)
    if family_exec_match:
        node_name = family_exec_match.group(1)
        args_str = family_exec_match.group(2)

        # Resolve coordinate to node name if needed (e.g. "0.2.1.18" → "tk_add_deliverable")
        if re.match(r'^\d[\d.]*$', node_name):
            node_name = _resolve_coordinate_to_name(node_name)

        family_map = _load_family_node_map()
        if node_name and node_name in family_map:
            server_name, action_name = family_map[node_name]
            body_schema = {}
            if args_str:
                try:
                    body_schema = json.loads(args_str)
                except (json.JSONDecodeError, TypeError):
                    body_schema = {}
            return server_name, action_name, body_schema

    # All other commands (nav, manage_servers.exec, discover_server_actions.exec, etc.)
    # are gnosys-kit internal operations - don't unwrap them
    return None, None, {}


def get_actual_tool_name(request: Dict[str, Any]) -> str:
    """
    Extract real tool name from direct, Strata-wrapped, or TreeShell-wrapped call.

    Args:
        request: Hook request dict with 'tool_name' and 'tool_input'

    Returns:
        Actual tool name in format:
        - Direct call: "mcp__carton__add_concept"
        - Strata call: "mcp__carton__add_concept" (unwrapped)
        - TreeShell call: "mcp__starlog__orient" (unwrapped from command)
        - Non-MCP: "Read", "Write", etc.

    Example:
        >>> request = {
        ...     'tool_name': 'mcp__strata__execute_action',
        ...     'tool_input': {
        ...         'server_name': 'carton',
        ...         'action_name': 'add_concept'
        ...     }
        ... }
        >>> get_actual_tool_name(request)
        'mcp__carton__add_concept'

        >>> request = {
        ...     'tool_name': 'mcp__gnosys_kit__run_conversation_shell',
        ...     'tool_input': {
        ...         'command': 'execute_action.exec {"server_name": "starlog", "action_name": "orient"}'
        ...     }
        ... }
        >>> get_actual_tool_name(request)
        'mcp__starlog__orient'
    """
    tool_name = request.get('tool_name', '')
    tool_input = request.get('tool_input', {})

    # Check if this is a Strata-wrapped call
    if tool_name == 'mcp__strata__execute_action':
        server_name = tool_input.get('server_name', '')
        action_name = tool_input.get('action_name', '')

        if server_name and action_name:
            return f"mcp__{server_name}__{action_name}"

    # Check if this is a TreeShell-wrapped call
    if tool_name in TREESHELL_TOOLS:
        command = tool_input.get('command', '')
        server_name, action_name, _ = _parse_treeshell_command(command)

        # Only unwrap if we have BOTH server and action (execute_action pattern)
        # All other commands stay as run_conversation_shell (whitelisted)
        if server_name and action_name:
            return f"mcp__{server_name}__{action_name}"

    return tool_name


def get_actual_tool_input(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract real tool input from direct, Strata-wrapped, or TreeShell-wrapped call.

    Args:
        request: Hook request dict with 'tool_name' and 'tool_input'

    Returns:
        Actual tool parameters:
        - Direct call: Returns tool_input as-is
        - Strata call: Parses body_schema JSON string to get real params
        - TreeShell call: Parses command to extract body_schema
    """
    tool_name = request.get('tool_name', '')
    tool_input = request.get('tool_input', {})

    # Check if this is a Strata-wrapped call
    if tool_name == 'mcp__strata__execute_action':
        body_schema = tool_input.get('body_schema', '{}')
        try:
            return json.loads(body_schema) if isinstance(body_schema, str) else body_schema
        except (json.JSONDecodeError, TypeError):
            return {}

    # Check if this is a TreeShell-wrapped call
    if tool_name in TREESHELL_TOOLS:
        command = tool_input.get('command', '')
        _, _, body_schema = _parse_treeshell_command(command)
        return body_schema

    return tool_input


def unwrap_strata_call(request: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Unwrap Strata call to get both tool name and input.

    Args:
        request: Hook request dict with 'tool_name' and 'tool_input'

    Returns:
        Tuple of (actual_tool_name, actual_tool_input)

    Example:
        >>> request = {
        ...     'tool_name': 'mcp__strata__execute_action',
        ...     'tool_input': {
        ...         'server_name': 'carton',
        ...         'action_name': 'add_concept',
        ...         'body_schema': '{"concept_name": "Test"}'
        ...     }
        ... }
        >>> tool_name, tool_input = unwrap_strata_call(request)
        >>> tool_name
        'mcp__carton__add_concept'
        >>> tool_input
        {'concept_name': 'Test'}
    """
    return (
        get_actual_tool_name(request),
        get_actual_tool_input(request)
    )


def is_mcp_tool(tool_name: str, server_name: Optional[str] = None) -> bool:
    """
    Check if tool name is an MCP tool, optionally filtering by server.

    Args:
        tool_name: Tool name (already unwrapped)
        server_name: Optional server name to filter by

    Returns:
        True if this is an MCP tool (and matches server if specified)

    Example:
        >>> is_mcp_tool('mcp__carton__add_concept')
        True
        >>> is_mcp_tool('mcp__carton__add_concept', server_name='carton')
        True
        >>> is_mcp_tool('mcp__starlog__check', server_name='carton')
        False
        >>> is_mcp_tool('Read')
        False
    """
    if not tool_name.startswith('mcp__'):
        return False

    if server_name:
        # Extract server name from tool_name
        parts = tool_name.split('__')
        if len(parts) >= 2:
            actual_server = parts[1]
            return actual_server == server_name

    return True


def extract_server_name(tool_name: str) -> Optional[str]:
    """
    Extract server name from MCP tool name.

    Args:
        tool_name: Tool name (already unwrapped)

    Returns:
        Server name or None if not an MCP tool

    Example:
        >>> extract_server_name('mcp__carton__add_concept')
        'carton'
        >>> extract_server_name('Read')
        None
    """
    if not tool_name.startswith('mcp__'):
        return None

    parts = tool_name.split('__')
    if len(parts) >= 2:
        return parts[1]

    return None


def extract_action_name(tool_name: str) -> Optional[str]:
    """
    Extract action name from MCP tool name.

    Args:
        tool_name: Tool name (already unwrapped)

    Returns:
        Action name or None if not an MCP tool

    Example:
        >>> extract_action_name('mcp__carton__add_concept')
        'add_concept'
        >>> extract_action_name('Read')
        None
    """
    if not tool_name.startswith('mcp__'):
        return None

    parts = tool_name.split('__')
    if len(parts) >= 3:
        return '__'.join(parts[2:])  # Handle action names with underscores

    return None


if __name__ == "__main__":
    # Quick test
    test_request = {
        'tool_name': 'mcp__strata__execute_action',
        'tool_input': {
            'server_name': 'carton',
            'action_name': 'add_concept',
            'body_schema': '{"concept_name": "Test_Concept", "description": "A test"}'
        }
    }

    print("Test Strata Unwrap:")
    print(f"Actual tool name: {get_actual_tool_name(test_request)}")
    print(f"Actual tool input: {get_actual_tool_input(test_request)}")
    print(f"Is MCP tool: {is_mcp_tool(get_actual_tool_name(test_request))}")
    print(f"Server name: {extract_server_name(get_actual_tool_name(test_request))}")
    print(f"Action name: {extract_action_name(get_actual_tool_name(test_request))}")
