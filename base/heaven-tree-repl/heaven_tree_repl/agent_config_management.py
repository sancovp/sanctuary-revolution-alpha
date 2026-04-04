"""
Agent Config Management - Equipment system for building HeavenAgentConfig

Simple wrapper functions for TreeShell nodes that use existing HEAVEN framework utilities.
Saves/loads configs as JSON for portability and proper round-tripping.

DYNAMIC CONFIG PERSISTENCE:
The _dynamic_config is now persisted to /tmp/heaven_data/agent_dynamic_config.json
and loaded on module import. This ensures config persists across TreeShell invocations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Global dynamic config storage
_dynamic_config = {}

# Persistence file path
DYNAMIC_CONFIG_PATH = "/tmp/heaven_data/agent_dynamic_config.json"

# ---------------------------------------------------------------------------
# Dynamic Config Persistence (NEW)
# ---------------------------------------------------------------------------

def _load_dynamic_config():
    """Load dynamic config from persistence file on module import."""
    global _dynamic_config
    if os.path.exists(DYNAMIC_CONFIG_PATH):
        try:
            with open(DYNAMIC_CONFIG_PATH, 'r') as f:
                loaded = json.load(f)
                _dynamic_config = loaded
                logger.info(f"Loaded dynamic config from {DYNAMIC_CONFIG_PATH}")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load dynamic config: {e}")
            _dynamic_config = {}
    else:
        _dynamic_config = {}


def _save_dynamic_config():
    """Save dynamic config to persistence file."""
    try:
        os.makedirs(os.path.dirname(DYNAMIC_CONFIG_PATH), exist_ok=True)
        with open(DYNAMIC_CONFIG_PATH, 'w') as f:
            json.dump(_dynamic_config, f, indent=2)
        logger.debug(f"Saved dynamic config to {DYNAMIC_CONFIG_PATH}")
    except IOError as e:
        logger.warning(f"Failed to save dynamic config: {e}")


def _set_and_save(key: str, value: Any):
    """Helper: set a key and persist."""
    _dynamic_config[key] = value
    _save_dynamic_config()


def _del_and_save(key: str):
    """Helper: delete a key and persist."""
    if key in _dynamic_config:
        del _dynamic_config[key]
        _save_dynamic_config()


# Load on module import
_load_dynamic_config()

# ---------------------------------------------------------------------------
# Config access
# ---------------------------------------------------------------------------

def get_dynamic_config() -> Dict[str, Any]:
    """Get the current dynamic agent config."""
    return _dynamic_config.copy()

def reset_dynamic_config():
    """Reset the dynamic config to empty state."""
    global _dynamic_config
    _dynamic_config = {}
    _save_dynamic_config()

# ---------------------------------------------------------------------------
# System Prompt management
# ---------------------------------------------------------------------------

def equip_system_prompt(prompt: str):
    """Equip a system prompt to the dynamic config."""
    _set_and_save('system_prompt', prompt)
    return f"Equipped system prompt ({len(prompt)} chars)", True

def unequip_system_prompt() -> Dict[str, Any]:
    """Remove system prompt from dynamic config."""
    if 'system_prompt' in _dynamic_config:
        _del_and_save('system_prompt')
        return {"success": True, "message": "Unequipped system prompt"}
    return {"success": False, "message": "No system prompt equipped"}

def list_system_prompts() -> Dict[str, Any]:
    """List current system prompt."""
    current = _dynamic_config.get('system_prompt')
    if current:
        preview = current[:100] + "..." if len(current) > 100 else current
        return {"success": True, "current": preview, "message": f"Current: {len(current)} chars"}
    return {"success": True, "current": None, "message": "No system prompt equipped"}

# ---------------------------------------------------------------------------
# Tools management
# ---------------------------------------------------------------------------

def equip_tool(tool_name: str):
    """Equip a tool to the dynamic config."""
    try:
        from heaven_base.utils.agent_and_tool_lists import get_tool_class
        tool_class = get_tool_class(tool_name)

        tools = _dynamic_config.get('tools', [])
        tool_names = [getattr(t, '__name__', str(t)) for t in tools]
        if tool_name not in tool_names:
            tools.append(tool_class)
            _set_and_save('tools', tools)
            return f"Equipped tool: {tool_name}", True
        return f"Tool {tool_name} already equipped", False
    except Exception as e:
        logger.exception("Failed to equip tool %s", tool_name)
        return f"Failed to equip tool {tool_name}: {str(e)}", False

def unequip_tool(tool_name: str) -> Dict[str, Any]:
    """Remove a tool from dynamic config."""
    tools = _dynamic_config.get('tools', [])
    for i, t in enumerate(tools):
        if getattr(t, '__name__', str(t)) == tool_name:
            tools.pop(i)
            _set_and_save('tools', tools)
            return {"success": True, "message": f"Unequipped tool: {tool_name}"}
    return {"success": False, "message": f"Tool {tool_name} not equipped"}

def list_tools() -> Dict[str, Any]:
    """List available and equipped tools."""
    from heaven_base.utils.agent_and_tool_lists import get_tool_modules
    available = get_tool_modules().split(", ")
    equipped = [getattr(t, '__name__', str(t)) for t in _dynamic_config.get('tools', [])]
    return {
        "success": True,
        "available": available[:10],
        "equipped": equipped,
        "message": f"Available: {len(available)}, Equipped: {len(equipped)}"
    }

# ---------------------------------------------------------------------------
# Provider management
# ---------------------------------------------------------------------------

VALID_PROVIDERS = ['anthropic']

def equip_provider(provider: str) -> Dict[str, Any]:
    """Equip an AI provider. MiniMax uses anthropic provider with MiniMax model names."""
    if provider.lower() not in VALID_PROVIDERS:
        return {"success": False, "message": f"Invalid provider. Must be one of: {VALID_PROVIDERS}. MiniMax uses 'anthropic' provider with MiniMax-* model names."}
    _set_and_save('provider', provider.lower())
    return {"success": True, "message": f"Equipped provider: {provider}"}

def unequip_provider() -> Dict[str, Any]:
    """Remove provider from dynamic config."""
    if 'provider' in _dynamic_config:
        _del_and_save('provider')
        return {"success": True, "message": "Unequipped provider"}
    return {"success": False, "message": "No provider equipped"}

def list_providers() -> Dict[str, Any]:
    """List available providers."""
    current = _dynamic_config.get('provider')
    return {"success": True, "available": VALID_PROVIDERS, "current": current, "note": "MiniMax uses 'anthropic' provider with MiniMax-* model names"}

# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------

MODELS_BY_PROVIDER = {
    'anthropic': [
        'MiniMax-M2.5-highspeed',
        'MiniMax-M2.5',
        'claude-sonnet-4-5-20250514',
        'claude-sonnet-4-20250514',
    ],
}

DEFAULT_MODEL = 'MiniMax-M2.5-highspeed'

def equip_model(model: str) -> Dict[str, Any]:
    """Equip a model to the dynamic config."""
    _set_and_save('model', model)
    return {"success": True, "message": f"Equipped model: {model}"}

def unequip_model() -> Dict[str, Any]:
    """Remove model from dynamic config."""
    if 'model' in _dynamic_config:
        _del_and_save('model')
        return {"success": True, "message": "Unequipped model"}
    return {"success": False, "message": "No model equipped"}

def list_models() -> Dict[str, Any]:
    """List available models for current provider."""
    current_provider = _dynamic_config.get('provider', 'minimax')
    available = MODELS_BY_PROVIDER.get(current_provider, [])
    current = _dynamic_config.get('model')
    return {
        "success": True,
        "available": available,
        "current": current,
        "default": DEFAULT_MODEL,
        "provider": current_provider,
    }

# ---------------------------------------------------------------------------
# Temperature management
# ---------------------------------------------------------------------------

def equip_temperature(temperature: float) -> Dict[str, Any]:
    """Equip temperature setting."""
    if not 0.0 <= temperature <= 1.0:
        return {"success": False, "message": "Temperature must be between 0.0 and 1.0"}
    _set_and_save('temperature', temperature)
    return {"success": True, "message": f"Equipped temperature: {temperature}"}

def unequip_temperature() -> Dict[str, Any]:
    """Remove temperature from dynamic config."""
    if 'temperature' in _dynamic_config:
        _del_and_save('temperature')
        return {"success": True, "message": "Unequipped temperature"}
    return {"success": False, "message": "No temperature equipped"}

def list_temperature() -> Dict[str, Any]:
    """Show current temperature."""
    current = _dynamic_config.get('temperature')
    return {"success": True, "current": current, "default": 0.7}

# ---------------------------------------------------------------------------
# Max tokens management
# ---------------------------------------------------------------------------

def equip_max_tokens(max_tokens: int) -> Dict[str, Any]:
    """Equip max_tokens setting."""
    if max_tokens <= 0:
        return {"success": False, "message": "max_tokens must be positive"}
    _set_and_save('max_tokens', max_tokens)
    return {"success": True, "message": f"Equipped max_tokens: {max_tokens}"}

def unequip_max_tokens() -> Dict[str, Any]:
    """Remove max_tokens from dynamic config."""
    if 'max_tokens' in _dynamic_config:
        _del_and_save('max_tokens')
        return {"success": True, "message": "Unequipped max_tokens"}
    return {"success": False, "message": "No max_tokens equipped"}

def list_max_tokens() -> Dict[str, Any]:
    """Show current max_tokens."""
    current = _dynamic_config.get('max_tokens')
    return {"success": True, "current": current, "default": 8000}

# ---------------------------------------------------------------------------
# Name management
# ---------------------------------------------------------------------------

def equip_name(name: str) -> Dict[str, Any]:
    """Equip agent name."""
    if not name or not name.strip():
        return {"success": False, "message": "Agent name cannot be empty"}
    _set_and_save('name', name.strip())
    return {"success": True, "message": f"Equipped name: {name}"}

def unequip_name() -> Dict[str, Any]:
    """Remove name from dynamic config."""
    if 'name' in _dynamic_config:
        _del_and_save('name')
        return {"success": True, "message": "Unequipped name"}
    return {"success": False, "message": "No name equipped"}

def list_names() -> Dict[str, Any]:
    """Show current name."""
    current = _dynamic_config.get('name')
    return {"success": True, "current": current}

# ---------------------------------------------------------------------------
# Prompt blocks management
# ---------------------------------------------------------------------------

def equip_prompt_block(block_name: str) -> Dict[str, Any]:
    """Equip a prompt suffix block."""
    blocks = _dynamic_config.get('prompt_suffix_blocks', [])
    if block_name not in blocks:
        blocks.append(block_name)
        _set_and_save('prompt_suffix_blocks', blocks)
        return {"success": True, "message": f"Equipped prompt block: {block_name}"}
    return {"success": False, "message": f"Prompt block {block_name} already equipped"}

def unequip_prompt_block(block_name: str) -> Dict[str, Any]:
    """Remove a prompt suffix block."""
    blocks = _dynamic_config.get('prompt_suffix_blocks', [])
    if block_name in blocks:
        blocks.remove(block_name)
        _set_and_save('prompt_suffix_blocks', blocks)
        return {"success": True, "message": f"Unequipped prompt block: {block_name}"}
    return {"success": False, "message": f"Prompt block {block_name} not equipped"}

def list_prompt_blocks() -> Dict[str, Any]:
    """List prompt suffix blocks."""
    equipped = _dynamic_config.get('prompt_suffix_blocks', [])
    available = ["switchboard", "extraction", "thinking", "debug"]
    return {"success": True, "available": available, "equipped": equipped}

# ---------------------------------------------------------------------------
# Thinking budget management
# ---------------------------------------------------------------------------

def equip_thinking_budget(budget: int) -> Dict[str, Any]:
    """Equip thinking budget (extended thinking tokens for Claude 3.7+)."""
    if budget <= 0:
        return {"success": False, "message": "thinking_budget must be positive"}
    _set_and_save('thinking_budget', budget)
    return {"success": True, "message": f"Equipped thinking_budget: {budget}"}

def unequip_thinking_budget() -> Dict[str, Any]:
    """Remove thinking budget from dynamic config."""
    if 'thinking_budget' in _dynamic_config:
        _del_and_save('thinking_budget')
        return {"success": True, "message": "Unequipped thinking_budget"}
    return {"success": False, "message": "No thinking_budget equipped"}

def list_thinking_budget() -> Dict[str, Any]:
    """Show current thinking budget."""
    current = _dynamic_config.get('thinking_budget')
    return {"success": True, "current": current, "default": None}

# ---------------------------------------------------------------------------
# MCP servers management
# ---------------------------------------------------------------------------

def equip_mcp_server(server_name: str, command: str, args: str = "[]", env: str = "{}") -> Dict[str, Any]:
    """Equip an MCP server config."""
    try:
        parsed_args = json.loads(args) if isinstance(args, str) else args
        parsed_env = json.loads(env) if isinstance(env, str) else env
    except json.JSONDecodeError as e:
        return {"success": False, "message": f"Invalid JSON: {e}"}

    servers = _dynamic_config.get('mcp_servers', {})
    servers[server_name] = {
        "command": command,
        "args": parsed_args,
        "env": parsed_env,
    }
    _set_and_save('mcp_servers', servers)
    return {"success": True, "message": f"Equipped MCP server: {server_name}"}

def unequip_mcp_server(server_name: str) -> Dict[str, Any]:
    """Remove an MCP server from dynamic config."""
    servers = _dynamic_config.get('mcp_servers', {})
    if server_name in servers:
        del servers[server_name]
        _set_and_save('mcp_servers', servers)
        return {"success": True, "message": f"Unequipped MCP server: {server_name}"}
    return {"success": False, "message": f"MCP server {server_name} not equipped"}

def list_mcp_servers() -> Dict[str, Any]:
    """List equipped MCP servers."""
    servers = _dynamic_config.get('mcp_servers', {})
    summary = {name: cfg.get('command', '?') for name, cfg in servers.items()}
    return {"success": True, "equipped": summary, "count": len(servers)}

# ---------------------------------------------------------------------------
# MCP set management
# ---------------------------------------------------------------------------

def equip_mcp_set(set_name: str) -> Dict[str, Any]:
    """Equip a strata MCP set by name (resolved at agent startup)."""
    _set_and_save('mcp_set', set_name)
    return {"success": True, "message": f"Equipped mcp_set: {set_name}"}

def unequip_mcp_set() -> Dict[str, Any]:
    """Remove MCP set from dynamic config."""
    if 'mcp_set' in _dynamic_config:
        _del_and_save('mcp_set')
        return {"success": True, "message": "Unequipped mcp_set"}
    return {"success": False, "message": "No mcp_set equipped"}

def list_mcp_set() -> Dict[str, Any]:
    """Show current MCP set."""
    current = _dynamic_config.get('mcp_set')
    return {"success": True, "current": current}

# ---------------------------------------------------------------------------
# Persona management
# ---------------------------------------------------------------------------

def equip_persona(persona_name: str) -> Dict[str, Any]:
    """Equip a persona (resolves frame, skillset, mcp_set, carton_identity)."""
    _set_and_save('persona', persona_name)
    return {"success": True, "message": f"Equipped persona: {persona_name}"}

def unequip_persona() -> Dict[str, Any]:
    """Remove persona from dynamic config."""
    if 'persona' in _dynamic_config:
        _del_and_save('persona')
        return {"success": True, "message": "Unequipped persona"}
    return {"success": False, "message": "No persona equipped"}

def list_persona() -> Dict[str, Any]:
    """Show current persona."""
    current = _dynamic_config.get('persona')
    return {"success": True, "current": current}

# ---------------------------------------------------------------------------
# Skillset management
# ---------------------------------------------------------------------------

def equip_skillset(skillset_name: str) -> Dict[str, Any]:
    """Equip a skillset for per-agent skill injection."""
    _set_and_save('skillset', skillset_name)
    return {"success": True, "message": f"Equipped skillset: {skillset_name}"}

def unequip_skillset() -> Dict[str, Any]:
    """Remove skillset from dynamic config."""
    if 'skillset' in _dynamic_config:
        _del_and_save('skillset')
        return {"success": True, "message": "Unequipped skillset"}
    return {"success": False, "message": "No skillset equipped"}

def list_skillset() -> Dict[str, Any]:
    """Show current skillset."""
    current = _dynamic_config.get('skillset')
    return {"success": True, "current": current}

# ---------------------------------------------------------------------------
# CartON identity management
# ---------------------------------------------------------------------------

def equip_carton_identity(identity_name: str) -> Dict[str, Any]:
    """Equip a CartON identity for observations."""
    _set_and_save('carton_identity', identity_name)
    return {"success": True, "message": f"Equipped carton_identity: {identity_name}"}

def unequip_carton_identity() -> Dict[str, Any]:
    """Remove CartON identity from dynamic config."""
    if 'carton_identity' in _dynamic_config:
        _del_and_save('carton_identity')
        return {"success": True, "message": "Unequipped carton_identity"}
    return {"success": False, "message": "No carton_identity equipped"}

def list_carton_identity() -> Dict[str, Any]:
    """Show current CartON identity."""
    current = _dynamic_config.get('carton_identity')
    return {"success": True, "current": current}

# ---------------------------------------------------------------------------
# Config file management (save/load as JSON)
# ---------------------------------------------------------------------------

def _get_agents_dir() -> Optional[Path]:
    """Get the agents config directory."""
    heaven_data_dir = os.getenv('HEAVEN_DATA_DIR')
    if not heaven_data_dir:
        return None
    return Path(heaven_data_dir) / 'agents'

def _serializable_config() -> Dict[str, Any]:
    """Get a JSON-serializable version of the dynamic config."""
    config = _dynamic_config.copy()
    if 'tools' in config:
        config['tools'] = [getattr(t, '__name__', str(t)) for t in config['tools']]
    return config

def save_config_as(name: str) -> Dict[str, Any]:
    """Save current dynamic config as JSON."""
    if not name or not name.strip():
        return {"success": False, "message": "Config name cannot be empty"}

    name = name.strip()

    if 'name' not in _dynamic_config:
        _dynamic_config['name'] = name

    agents_dir = _get_agents_dir()
    if not agents_dir:
        return {"success": False, "message": "HEAVEN_DATA_DIR environment variable not set"}

    agent_dir = agents_dir / name
    config_file = agent_dir / f"{name}_config.json"

    if config_file.exists():
        return {"success": False, "message": f"Config '{name}' already exists. Use copy_existing to load it."}

    agent_dir.mkdir(parents=True, exist_ok=True)

    serializable = _serializable_config()
    config_file.write_text(json.dumps(serializable, indent=2))

    return {"success": True, "message": f"Saved config '{name}' to {config_file}"}

def copy_existing(name: str) -> Dict[str, Any]:
    """Load an existing config into the dynamic config."""
    if not name or not name.strip():
        return {"success": False, "message": "Config name cannot be empty"}

    name = name.strip()
    agents_dir = _get_agents_dir()
    if not agents_dir:
        return {"success": False, "message": "HEAVEN_DATA_DIR environment variable not set"}

    config_file = agents_dir / name / f"{name}_config.json"
    if not config_file.exists():
        legacy_file = agents_dir / name / f"{name}_config.py"
        if legacy_file.exists():
            _dynamic_config.clear()
            _dynamic_config['name'] = name
            _save_dynamic_config()
            return {"success": True, "message": f"Loaded legacy config '{name}' (name only - re-equip fields)"}
        return {"success": False, "message": f"Config '{name}' not found"}

    try:
        data = json.loads(config_file.read_text())
        _dynamic_config.clear()

        tool_names = data.pop('tools', [])
        if tool_names:
            resolved_tools = []
            from heaven_base.utils.agent_and_tool_lists import get_tool_class
            for tool_name in tool_names:
                try:
                    resolved_tools.append(get_tool_class(tool_name))
                except ImportError:
                    pass
            data['tools'] = resolved_tools

        _dynamic_config.update(data)
        _save_dynamic_config()
        return {"success": True, "message": f"Loaded config '{name}' ({len(data)} fields)"}
    except Exception as e:
        logger.exception("Failed to load config %s", name)
        return {"success": False, "message": f"Failed to load config: {str(e)}"}

def overwrite_config(name: str) -> Dict[str, Any]:
    """Overwrite an existing saved config with current dynamic config."""
    if not name or not name.strip():
        return {"success": False, "message": "Config name cannot be empty"}

    name = name.strip()
    agents_dir = _get_agents_dir()
    if not agents_dir:
        return {"success": False, "message": "HEAVEN_DATA_DIR environment variable not set"}

    agent_dir = agents_dir / name
    config_file = agent_dir / f"{name}_config.json"

    if not config_file.exists():
        return {"success": False, "message": f"Config '{name}' does not exist. Use save_config_as to create."}

    if 'name' not in _dynamic_config:
        _dynamic_config['name'] = name

    serializable = _serializable_config()
    config_file.write_text(json.dumps(serializable, indent=2))
    return {"success": True, "message": f"Overwrote config '{name}'"}

def delete_config(name: str) -> Dict[str, Any]:
    """Delete a saved agent config."""
    if not name or not name.strip():
        return {"success": False, "message": "Config name cannot be empty"}

    name = name.strip()
    agents_dir = _get_agents_dir()
    if not agents_dir:
        return {"success": False, "message": "HEAVEN_DATA_DIR environment variable not set"}

    agent_dir = agents_dir / name
    if not agent_dir.exists():
        return {"success": False, "message": f"Config '{name}' not found"}

    import shutil
    shutil.rmtree(agent_dir)
    return {"success": True, "message": f"Deleted config '{name}'"}

def list_saved_configs() -> Dict[str, Any]:
    """List all saved agent configs."""
    agents_dir = _get_agents_dir()
    if not agents_dir:
        return {"success": False, "message": "HEAVEN_DATA_DIR environment variable not set"}

    if not agents_dir.exists():
        return {"success": True, "configs": [], "message": "No saved configs found"}

    configs = []
    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir():
            json_file = agent_dir / f"{agent_dir.name}_config.json"
            py_file = agent_dir / f"{agent_dir.name}_config.py"
            if json_file.exists():
                configs.append({"name": agent_dir.name, "format": "json"})
            elif py_file.exists():
                configs.append({"name": agent_dir.name, "format": "legacy_py"})

    return {"success": True, "configs": configs, "message": f"Found {len(configs)} saved configs"}

def preview_dynamic_config() -> Dict[str, Any]:
    """Show current state of dynamic config."""
    config = get_dynamic_config()
    if 'tools' in config:
        config['tools'] = [getattr(t, '__name__', str(t)) for t in config['tools']]
    required_fields = ['name', 'system_prompt']
    missing = [field for field in required_fields if field not in config or not config[field]]
    complete = len(missing) == 0

    return {
        "success": True,
        "config": config,
        "complete": complete,
        "missing": missing,
        "message": f"Config {'complete' if complete else 'incomplete'}"
    }
