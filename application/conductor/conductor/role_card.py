"""Dynamic role card renderer for conductor.

Called by Heaven's dynamic_call prompt_suffix_block system.
Reads persona + user configs, formats role_card.template.md, returns rendered string.
"""

import json
from pathlib import Path

HEAVEN = Path("/tmp/heaven_data")
TEMPLATE_PATH = HEAVEN / "conductor_prompt_blocks" / "role_card.template.md"
PERSONA_CONFIG = HEAVEN / "conductor_persona_config.json"
USER_CONFIG = HEAVEN / "user_config.json"


def render_role_card() -> str:
    """Render role card from template + configs. Called by dynamic_call."""
    template = TEMPLATE_PATH.read_text() if TEMPLATE_PATH.exists() else ""

    persona = {}
    if PERSONA_CONFIG.exists():
        persona = json.loads(PERSONA_CONFIG.read_text())

    user = {}
    if USER_CONFIG.exists():
        user = json.loads(USER_CONFIG.read_text())

    return template.format(
        persona_name=persona.get("persona_name", "Conductor"),
        persona_description=persona.get("persona_description", "a compound intelligence copilot"),
        user_name=user.get("user_name", "User"),
    )
