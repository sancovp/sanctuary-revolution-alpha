"""Dragonbones MCP tools — lightweight interface for agents to create PAIA artifacts.

Assembles EC text from structured args, runs through the SAME Dragonbones pipeline
(extract_from_blocks → compile_concepts) that the stop hook uses.

Tools:
    add_skill_to_target_starsystem — create a Skill_ concept
    add_rule_to_target_starsystem — create a Claude_Code_Rule_ concept
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _run_ec_through_dragonbones(ec_text: str, silenced: bool = True) -> dict:
    """Run EC text through the Dragonbones pipeline.

    Same functions the stop hook calls:
    1. extract_from_blocks(text) — parse EC text into concept dicts
    2. compile_concepts(concepts, silenced) — GIINT injection, HC validation,
       CartON write, starlog diary flush, TreeKanban sync
    """
    from dragonbones.parser import extract_from_blocks
    from dragonbones.compiler import compile_concepts

    concepts, stubs, help_requested, blocks_found = extract_from_blocks(ec_text)

    if not concepts:
        return {
            "success": False,
            "error": f"No valid ECs parsed from text. Stubs: {stubs}",
            "compiled": 0,
        }

    results, compiled_count, warning_count = compile_concepts(concepts, silenced)

    return {
        "success": compiled_count > 0,
        "compiled": compiled_count,
        "warnings": warning_count,
        "results": results,
    }


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
    subdomain: Optional[str] = None,
    requires: Optional[str] = None,
) -> dict:
    """Create a Skill_ concept via Dragonbones pipeline.

    Assembles the full 🌟⛓️ EC text with all required Skill fields,
    then runs through extract_from_blocks → compile_concepts.

    Args:
        name: Skill name without Skill_ prefix (e.g., "Understand_Foo_Bar")
        content: The skill description/content (becomes desc=)
        starsystem: Target starsystem name (e.g., "Starsystem_Screenwriting_Copilot")
        domain: Domain name (e.g., "Screenwriting")
        what: What this skill teaches/does
        when: When to use this skill
        category: Skill category (default: Skill_Category_Understand)
        produces: What this skill produces
        personal_domain: Personal domain enum (default: paiab)
        subdomain: Subdomain within the domain
        requires: Prerequisite skill name
    """
    # Sanitize content for EC format — escape triple quotes
    safe_content = content.replace("'''", "' ' '")

    subdomain_val = subdomain or domain
    requires_val = requires or "none"

    ec_text = (
        f"🌟⛓️ Skill_{name} {{is_a=Skill, desc='''{safe_content}'''}}\n"
        f"+{{instantiates=Skill_Understand_Pattern, desc='''Replayable skill pattern'''}}\n"
        f"+{{part_of={starsystem}, desc='''Target starsystem'''}}\n"
        f"+{{has_category={category}, desc='''Skill category'''}}\n"
        f"+{{has_personal_domain={personal_domain}, desc='''Personal domain'''}}\n"
        f"+{{has_domain={domain}, desc='''Domain'''}}\n"
        f"+{{has_subdomain={subdomain_val}, desc='''Subdomain'''}}\n"
        f"+{{has_what={what}, desc='''What this skill teaches'''}}\n"
        f"+{{has_when={when}, desc='''When to use this skill'''}}\n"
        f"+{{has_produces={produces}, desc='''What this skill produces'''}}\n"
        f"+{{has_content='''{safe_content[:200]}'''}}\n"
        f"+{{has_requires=[{requires_val}], desc='''Dependencies'''}}\n"
    )

    return _run_ec_through_dragonbones(ec_text)


def add_rule_to_target_starsystem(
    name: str,
    content: str,
    starsystem: str,
    scope: str = "project",
) -> dict:
    """Create a Claude_Code_Rule_ concept via Dragonbones pipeline.

    Assembles the full 🛡️⛓️ EC text with required Claude_Code_Rule fields,
    then runs through extract_from_blocks → compile_concepts.

    Args:
        name: Rule name without Claude_Code_Rule_ prefix (e.g., "Never_Foo")
        content: The rule body text (becomes the .md file content via daemon projection)
        starsystem: Target starsystem name (e.g., "Starsystem_Screenwriting_Copilot")
        scope: "global" or "project" (default: project)
    """
    safe_content = content.replace("'''", "' ' '")

    ec_text = (
        f"🛡️⛓️ Claude_Code_Rule_{name} {{is_a=Claude_Code_Rule, desc='''{safe_content}'''}}\n"
        f"+{{has_scope={scope}}}\n"
        f"+{{has_starsystem={starsystem}}}\n"
    )

    return _run_ec_through_dragonbones(ec_text)
