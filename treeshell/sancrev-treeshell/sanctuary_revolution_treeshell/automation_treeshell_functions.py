"""TreeShell functions for Automations — wraps CAVE AutomationRegistry.

These are the callable functions that automations_family.json nodes point to.
They import cave.core.automation directly — no MCP, no strata, no execute_action.

Automations are trigger+process pairs stored as JSON in /tmp/heaven_data/automations/.
The process is a code_pointer (module.func) that runs any Python — SDNA agents, scripts, whatever.
"""

import json
import os
from pathlib import Path
from typing import Optional

from cave.core.automation import AutomationSchema, AutomationRegistry


AUTOMATIONS_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "automations"


def _registry() -> AutomationRegistry:
    return AutomationRegistry(automations_dir=AUTOMATIONS_DIR)


def list_automations() -> str:
    """List all automations with their schedules and processes."""
    registry = _registry()
    registry.load_all()
    names = registry.list_all()
    if not names:
        return "No automations found. Use create_automation to add one."
    lines = [f"Automations ({len(names)}):"]
    for name in sorted(names):
        auto = registry.get(name)
        schedule = auto.schema.schedule or "no schedule"
        process = auto.schema.code_pointer or "prompt only"
        enabled = "ON" if auto.schema.enabled else "OFF"
        lines.append(f"  [{enabled}] {name} — {schedule} — {process}")
    return "\n".join(lines)


def view_automation(name: str = "") -> str:
    """View full details of an automation."""
    if not name:
        return "ERROR: name is required."
    registry = _registry()
    registry.load_all()
    auto = registry.get(name)
    if not auto:
        return f"Automation '{name}' not found."
    schema = auto.schema
    lines = [
        f"Automation: {schema.name}",
        f"  Description: {schema.description or '(none)'}",
        f"  Schedule:    {schema.schedule or '(none)'}",
        f"  Process:     {schema.code_pointer or '(none)'}",
        f"  Args:        {json.dumps(schema.code_args) if schema.code_args else '(none)'}",
        f"  Prompt:      {schema.prompt_template[:80] + '...' if schema.prompt_template and len(schema.prompt_template) > 80 else schema.prompt_template or '(none)'}",
        f"  Priority:    {schema.priority}",
        f"  Tags:        {', '.join(schema.tags) if schema.tags else '(none)'}",
        f"  Enabled:     {schema.enabled}",
    ]
    return "\n".join(lines)


def create_automation(name: str = "", description: str = "",
                      schedule: str = "", code_pointer: str = "",
                      code_args: str = "{}", prompt_template: str = "",
                      priority: int = 5, tags: str = "[]") -> str:
    """Create an automation. Writes JSON to automations dir.

    name: required — unique identifier
    schedule: cron expression (e.g. '0 */4 * * *') or empty for manual-only
    code_pointer: 'module.function' to import and call (e.g. 'my_scripts.nightly.run')
    code_args: JSON string of args to pass to the function
    prompt_template: prompt string with $variable substitution (alternative to code_pointer)
    tags: JSON array string for categorization
    """
    if not name:
        return "ERROR: name is required."
    if not code_pointer and not prompt_template:
        return "ERROR: either code_pointer or prompt_template is required."

    try:
        parsed_args = json.loads(code_args) if isinstance(code_args, str) else code_args
    except json.JSONDecodeError:
        return f"ERROR: invalid JSON for code_args: {code_args}"

    try:
        parsed_tags = json.loads(tags) if isinstance(tags, str) else tags
    except json.JSONDecodeError:
        parsed_tags = []

    schema = AutomationSchema(
        name=name,
        description=description,
        schedule=schedule or None,
        code_pointer=code_pointer or None,
        code_args=parsed_args,
        prompt_template=prompt_template or None,
        priority=priority,
        tags=parsed_tags,
    )

    registry = _registry()
    path = registry.save_schema(schema)
    return f"Created automation '{name}' at {path}"


def delete_automation(name: str = "") -> str:
    """Delete an automation JSON."""
    if not name:
        return "ERROR: name is required."
    path = AUTOMATIONS_DIR / f"{name}.json"
    if not path.exists():
        return f"Automation '{name}' not found."
    path.unlink()
    return f"Deleted automation '{name}'."


def enable_automation(name: str = "") -> str:
    """Enable a disabled automation."""
    return _set_enabled(name, True)


def disable_automation(name: str = "") -> str:
    """Disable an automation without deleting it."""
    return _set_enabled(name, False)


def _set_enabled(name: str, enabled: bool) -> str:
    if not name:
        return "ERROR: name is required."
    path = AUTOMATIONS_DIR / f"{name}.json"
    if not path.exists():
        return f"Automation '{name}' not found."
    data = json.loads(path.read_text())
    data["enabled"] = enabled
    path.write_text(json.dumps(data, indent=2))
    state = "enabled" if enabled else "disabled"
    return f"Automation '{name}' {state}."


def fire_automation(name: str = "") -> str:
    """Execute an automation immediately (ignore schedule)."""
    if not name:
        return "ERROR: name is required."
    registry = _registry()
    registry.load_all()
    auto = registry.get(name)
    if not auto:
        return f"Automation '{name}' not found."
    result = auto.fire()
    return f"Fired '{name}': {json.dumps(result, indent=2, default=str)}"


def export_agent_as_automation(agent_name: str = "", schedule: str = "",
                                prompt: str = "", automation_name: str = "") -> str:
    """Create an automation from a saved agent config.

    agent_name: name of saved agent config in /tmp/heaven_data/agents/
    schedule: cron expression
    prompt: the prompt to give the agent each run
    automation_name: name for the automation (defaults to agent_name)
    """
    if not agent_name:
        return "ERROR: agent_name is required."

    agent_path = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "agents" / f"{agent_name}.json"
    if not agent_path.exists():
        return f"Agent config '{agent_name}' not found at {agent_path}."

    auto_name = automation_name or agent_name
    schema = AutomationSchema(
        name=auto_name,
        description=f"Automation from agent config '{agent_name}'",
        schedule=schedule or None,
        code_pointer="sanctuary_revolution_treeshell.automation_treeshell_functions._run_agent",
        code_args={"agent_config_path": str(agent_path), "prompt": prompt},
    )

    registry = _registry()
    path = registry.save_schema(schema)
    return f"Created automation '{auto_name}' from agent '{agent_name}' at {path}"


def _run_agent(agent_config_path: str = "", prompt: str = "") -> str:
    """Run a saved agent config via SDNA. Used as code_pointer target."""
    from pathlib import Path
    import json

    config_path = Path(agent_config_path)
    if not config_path.exists():
        return f"Agent config not found: {agent_config_path}"

    config_data = json.loads(config_path.read_text())

    # Import SDNA and run
    try:
        from sdna import sdnac, ariadne, human
        from sdna.context_engineering import claude_code_session

        session_name = config_data.get("name", "automation_agent")
        result = claude_code_session(
            session=session_name,
            prompt=prompt or "Execute your configured task.",
        )
        return f"Agent '{session_name}' executed: {result}"
    except ImportError:
        return "ERROR: SDNA not available. Install sdna package."
    except Exception as e:
        return f"ERROR: Agent execution failed: {e}"
