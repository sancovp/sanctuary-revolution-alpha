"""Pydantic models for skill manager."""

from typing import Optional, Literal
from pydantic import BaseModel


# Skill categories determine how the agent should use the skill
SkillCategory = Literal["understand", "preflight", "single_turn_process"]


class ClaudeSkillFrontmatter(BaseModel):
    """Claude's official skill frontmatter fields (SKILL.md YAML).

    Field names use hyphens in YAML (e.g. allowed-tools, user-invocable)
    but underscores in Python (allowed_tools, user_invocable).
    """
    name: str  # max 64 chars, lowercase/numbers/hyphens only
    description: str  # max 1024 chars - THIS IS THE TRIGGER
    allowed_tools: Optional[str] = None  # comma-separated tool names, e.g. "Read, Grep, Bash(gh *)"
    model: Optional[str] = None  # e.g. claude-sonnet-4-20250514
    context: Optional[str] = None  # "fork" = run in subagent
    agent: Optional[str] = None  # subagent type when context=fork, e.g. "Explore", "Plan", custom agent name
    hooks: Optional[dict] = None  # PreToolUse/PostToolUse scoped to this skill
    user_invocable: Optional[bool] = None  # show in / menu (default true)
    disable_model_invocation: Optional[bool] = None  # prevent auto-invoke (default false)
    argument_hint: Optional[str] = None  # autocomplete hint e.g. "[issue-number]"


class GnosysSkillMetadata(BaseModel):
    """GNOSYS extensions stored in _metadata.json."""
    domain: str  # PAIAB, SANCTUM, CAVE
    subdomain: Optional[str] = None
    category: Optional[SkillCategory] = None
    # Typed description fields - concatenated into Claude's description
    what: Optional[str] = None  # What this skill does
    when: Optional[str] = None  # When to use it (trigger condition)
    # how is the skill body for preflight, not stored here
    # Dependencies - understand skills to auto-equip when this skill is equipped
    requires: Optional[list[str]] = None  # e.g. ["understand-mcp-architecture"]
    # DESCRIBES relationship - links skill to GIINT component
    describes_component: Optional[str] = None  # e.g. "project/feature/component"
    # PART_OF relationship - links skill to starsystem/project for complexity scoring
    starsystem: Optional[str] = None  # e.g. "/tmp/my_project" or "Starsystem_tmp_my_project"


class Skill(BaseModel):
    """A skill combining Claude's format + GNOSYS extensions."""
    # Claude's fields (all from ClaudeSkillFrontmatter)
    name: str
    description: str  # Built from WHAT/WHEN (and HOW for preflight is the body)
    allowed_tools: Optional[str] = None
    model: Optional[str] = None
    context: Optional[str] = None  # "fork" = run in subagent
    agent: Optional[str] = None  # subagent type when context=fork
    hooks: Optional[dict] = None  # PreToolUse/PostToolUse scoped to this skill
    user_invocable: Optional[bool] = None  # show in / menu
    disable_model_invocation: Optional[bool] = None  # prevent auto-invoke
    argument_hint: Optional[str] = None  # autocomplete hint
    # GNOSYS extensions
    domain: str
    subdomain: Optional[str] = None
    category: Optional[SkillCategory] = None
    what: Optional[str] = None
    when: Optional[str] = None
    requires: Optional[list[str]] = None  # understand skill dependencies to auto-equip
    describes_component: Optional[str] = None  # GIINT component path this skill describes
    starsystem: Optional[str] = None  # Project/starsystem this skill belongs to
    # Skill body content
    content: str


class Skillset(BaseModel):
    """A named group of skills with its own domain."""
    name: str
    domain: str
    subdomain: Optional[str] = None
    description: str
    skills: list[str]  # skill names


class Persona(BaseModel):
    """A composable persona bundling frame, MCP set, skillset, and identity."""
    name: str
    domain: str
    subdomain: Optional[str] = None
    description: str
    frame: str  # cognitive frame / prompt text
    mcp_set: Optional[str] = None  # strata set name (aspirational)
    skillset: Optional[str] = None  # skillset name (aspirational)
    carton_identity: Optional[str] = None  # CartON identity for observations
