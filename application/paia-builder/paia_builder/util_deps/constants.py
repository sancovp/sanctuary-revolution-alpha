"""Constants for paia-builder."""

COMPONENT_TYPES = [
    "skills", "mcps", "hooks", "commands", "agents", "personas", "plugins", "flights",
    "metastacks", "giint_blueprints", "operadic_flows", "frontend_integrations", "automations",
    "agent_gans", "agent_duos", "system_prompts"
]

TIER_NAMES = ["common", "uncommon", "rare", "epic", "legendary"]

COMPONENT_TYPE_MAP = {
    "skills": "skill",
    "mcps": "mcp",
    "hooks": "hook",
    "commands": "slash_command",
    "agents": "agent",
    "personas": "persona",
    "plugins": "plugin",
    "flights": "flight",
    "metastacks": "metastack",
    "giint_blueprints": "giint_blueprint",
    "operadic_flows": "operadic_flow",
    "frontend_integrations": "frontend_integration",
    "automations": "automation",
    "agent_gans": "agent_gan",
    "agent_duos": "agent_duo",
    "system_prompts": "system_prompt",
}
