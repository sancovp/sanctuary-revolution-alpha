"""Dragonbones MCP Server — exposes PAIA artifact creation to agents.

Two tools:
    add_skill_to_target_starsystem — create Skill_ via Dragonbones pipeline
    add_rule_to_target_starsystem — create Claude_Code_Rule_ via Dragonbones pipeline

Run: python3 -m dragonbones.server
"""

from mcp.server.fastmcp import FastMCP
from typing import Optional

mcp = FastMCP("dragonbones")


@mcp.tool()
def add_skill_to_target_starsystem(
    name: str,
    content: str,
    starsystem: str,
    domain: str,
    what: str,
    when: str,
    category: str = "Skill_Category_Understand",
    produces: str = "Context for developing this component",
    personal_domain: str = "paiab",
    subdomain: str = "",
    requires: str = "",
) -> str:
    """Add a skill to a starsystem. Creates the skill concept with proper typing.

    Args:
        name: Skill name without Skill_ prefix (e.g., Understand_Foo_Bar)
        content: What the skill teaches — full description an agent reads when equipped
        starsystem: Which starsystem this skill belongs to (e.g., Starsystem_Screenwriting_Copilot)
        domain: Knowledge domain (e.g., Screenwriting, Architecture, Testing)
        what: One-line summary of what this skill teaches
        when: When an agent should use this skill
        category: Skill_Category_Understand, Skill_Category_Preflight, or Skill_Category_Single_Turn_Process
        produces: What output this skill enables (e.g., Context for developing X)
        personal_domain: paiab, sanctum, cave, misc, or personal
        subdomain: More specific area within the domain
        requires: Name of a prerequisite skill (if any)
    """
    from dragonbones.mcp_tools import add_skill_to_target_starsystem as _impl
    result = _impl(
        name=name, content=content, starsystem=starsystem,
        domain=domain, what=what, when=when, category=category,
        produces=produces, personal_domain=personal_domain,
        subdomain=subdomain or None, requires=requires or None,
    )
    if result["success"]:
        return f"Skill_{name} compiled ({result['compiled']} concepts). {'; '.join(result.get('results', [])[:3])}"
    return f"FAILED: {result.get('error', 'Unknown error')}. Results: {result.get('results', [])}"


@mcp.tool()
def add_rule_to_target_starsystem(
    name: str,
    content: str,
    starsystem: str,
    scope: str = "project",
) -> str:
    """Add a rule to a starsystem. Creates the rule concept and the .md file.

    Args:
        name: Rule name (e.g., Never_Foo, Always_Use_Logging)
        content: The rule text — what the agent must follow when this rule is active
        starsystem: Which starsystem this rule belongs to (e.g., Starsystem_Screenwriting_Copilot)
        scope: global (applies everywhere) or project (applies only in this starsystem)
    """
    from dragonbones.mcp_tools import add_rule_to_target_starsystem as _impl
    result = _impl(name=name, content=content, starsystem=starsystem, scope=scope)
    if result["success"]:
        return f"Claude_Code_Rule_{name} compiled ({result['compiled']} concepts). {'; '.join(result.get('results', [])[:3])}"
    return f"FAILED: {result.get('error', 'Unknown error')}. Results: {result.get('results', [])}"


if __name__ == "__main__":
    mcp.run()
