"""Project structure operations."""

from pathlib import Path
from typing import Optional

from ..models import PAIA, ComponentBase, GoldenStatus
from .constants import COMPONENT_TYPES


def init_project_structure(project_dir: Path, name: str, description: str) -> None:
    """Initialize full project structure for PAIA construction."""
    for comp_type in COMPONENT_TYPES:
        (project_dir / "construction_docs" / "01_components" / comp_type).mkdir(parents=True, exist_ok=True)
    (project_dir / "src").mkdir(parents=True, exist_ok=True)

    overview = f"# {name}\n\n> {description}\n\n## Status\n\n[VEHICLE] Hull under construction. Subsystems pending.\n"
    (project_dir / "construction_docs" / "00_overview.md").write_text(overview)
    (project_dir / "construction_docs" / "02_gear_status.md").write_text("# GEAR Status\n\n[VEHICLE] No subsystems installed.\n")
    (project_dir / "construction_docs" / "03_changelog.md").write_text(f"# Changelog\n\n## v0.1.0\n- [VEHICLE] Hull commissioned: {name}\n")

    claude_md = f"# {name} PAIA\n\n> {description}\n\n<!-- [VEHICLE] Nav computer builds as hull progresses -->\n"
    (project_dir / "CLAUDE.md").write_text(claude_md)


def generate_component_doc(comp: ComponentBase, comp_type: str) -> str:
    """Generate markdown doc for a single component."""
    tier_emoji = {"none": "⬜", "common": "🟢", "uncommon": "🔵", "rare": "🟣", "epic": "🟠", "legendary": "🟡"}
    gold_emoji = {"quarantine": "🔴", "crystal": "💎", "golden": "⭐"}

    lines = [
        f"# {comp.name}",
        f"> {comp.description}",
        "",
        f"**Tier:** {tier_emoji.get(comp.tier.value, '⬜')} {comp.tier.value.upper()} ({comp.points} pts)",
        f"**Status:** {gold_emoji.get(comp.golden.value, '🔴')} {comp.golden.value.upper()}",
        "",
    ]

    if comp_type == "skills" and hasattr(comp, "domain"):
        lines.append(f"**Domain:** {comp.domain}")
        if hasattr(comp, "category"):
            lines.append(f"**Category:** {comp.category.value}")
    elif comp_type == "mcps" and hasattr(comp, "command"):
        if comp.command:
            lines.append(f"**Command:** `{comp.command}`")
        if comp.tools:
            lines.append(f"**Tools:** {', '.join(comp.tools)}")

    if comp.notes:
        lines.extend(["", "## History", ""])
        for note in comp.notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def generate_claude_md(paia: PAIA) -> str:
    """Generate complete CLAUDE.md from main system prompt."""
    lines = [f"# {paia.name}", f"> {paia.description}", ""]

    main_prompt = None
    for p in paia.system_prompts:
        if p.prompt_type.value == "main":
            main_prompt = p
            break

    if main_prompt and main_prompt.sections:
        sorted_sections = sorted(main_prompt.sections, key=lambda s: s.order)
        for section in sorted_sections:
            lines.append(f"<{section.tag_name}>")
            lines.append(section.content)
            lines.append(f"</{section.tag_name}>")
            lines.append("")
    else:
        lines.append("<!-- [VEHICLE] Nav computer not configured - no main system prompt -->")

    return "\n".join(lines)
