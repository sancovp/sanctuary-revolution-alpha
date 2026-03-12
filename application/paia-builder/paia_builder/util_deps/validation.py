"""Validation operations."""

from pathlib import Path
from typing import Dict, Any

from ..models import PAIA, SystemPromptSectionType


def validate_system_prompt(paia: PAIA, prompt_file_path: str, config_name: str) -> Dict[str, Any]:
    """Validate a prompt file against config."""
    config = None
    for c in paia.system_prompt_configs:
        if c.name == config_name:
            config = c
            break
    if not config:
        return {"valid": False, "error": f"Config not found: {config_name}"}

    content = Path(prompt_file_path).read_text()
    errors = []

    for section in config.required_sections:
        tag = section.value
        if f"<{tag}>" not in content:
            errors.append(f"Missing opening tag: <{tag}>")
        if f"</{tag}>" not in content:
            errors.append(f"Missing closing tag: </{tag}>")

    stack = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    for i, char in enumerate(content):
        if char in pairs:
            stack.append((char, i))
        elif char in pairs.values():
            if not stack:
                errors.append(f"Unmatched '{char}' at position {i}")
            else:
                open_char, _ = stack.pop()
                if pairs[open_char] != char:
                    errors.append(f"Mismatched '{open_char}' and '{char}' at position {i}")

    for char, pos in stack:
        errors.append(f"Unclosed '{char}' at position {pos}")

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


def render_system_prompt(paia: PAIA, prompt_name: str) -> str:
    """Render a system prompt to XML-tagged markdown."""
    prompt = None
    for p in paia.system_prompts:
        if p.name == prompt_name:
            prompt = p
            break
    if not prompt:
        raise ValueError(f"System prompt not found: {prompt_name}")

    sorted_sections = sorted(prompt.sections, key=lambda s: s.order)
    lines = []
    for section in sorted_sections:
        lines.append(f"<{section.tag_name}>")
        lines.append(section.content)
        lines.append(f"</{section.tag_name}>")
        lines.append("")
    return "\n".join(lines)
