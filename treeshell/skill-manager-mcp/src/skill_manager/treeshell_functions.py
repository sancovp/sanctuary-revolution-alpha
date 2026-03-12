"""Skill Manager functions for TreeShell crystallization."""

import logging
from typing import List, Dict, Any, Optional
from .core import SkillManager

logger = logging.getLogger(__name__)

# Global manager for Claude Code (no agent_id = shared _equipped.json)
manager = SkillManager()
logger.info("SkillManager singleton initialized for TreeShell")


def _get_manager(agent_id: str = "") -> SkillManager:
    """Get SkillManager — global for Claude Code, scoped for Heaven agents."""
    if agent_id:
        return SkillManager(agent_id=agent_id)
    return manager


# === Global catalog ===

def list_skills() -> str:
    """List all skills in global catalog by name."""
    skills = manager.list_skills()
    if not skills:
        return "No skills in catalog. Create with create_skill."
    return "\n".join(s['name'] for s in skills)


def list_domains() -> str:
    """List all available skill domains."""
    domains = manager.list_domains()
    if not domains:
        return "No domains. Create skills to populate."
    return "Domains: " + ", ".join(domains)


def list_by_domain(domain: str) -> str:
    """List all skills and skillsets in a domain."""
    result = manager.list_by_domain(domain)
    lines = [f"Domain: {domain}"]

    if result["skillsets"]:
        lines.append("\nSkillsets:")
        for ss in result["skillsets"]:
            lines.append(f"  {ss['name']}: {ss['description']} ({ss['skill_count']} skills)")

    if result["skills"]:
        lines.append("\nSkills:")
        for s in result["skills"]:
            lines.append(f"  {s['name']}: {s['description']}")

    if not result["skillsets"] and not result["skills"]:
        lines.append("(empty)")

    return "\n".join(lines)


def _format_resources(resources: dict) -> list[str]:
    """Format resource info as lines."""
    lines = []
    scripts = resources.get("scripts", [])
    templates = resources.get("templates", [])
    ref = resources.get("reference")

    lines.append(f"scripts/: {', '.join(scripts)}" if scripts else "scripts/: (empty)")
    lines.append(f"templates/: {', '.join(templates)}" if templates else "templates/: (empty)")
    lines.append(f"reference.md: {ref}" if ref else "reference.md: (not created)")
    return lines


def get_skill(name: str) -> str:
    """Get full content of a skill package.

    Returns SKILL.md content plus available resources (scripts/, templates/, reference.md).
    """
    result = manager.get_skill(name)
    if not result:
        return f"Skill '{name}' not found"

    skill = result["skill"]
    path = f"{skill.domain}::{skill.subdomain}" if skill.subdomain else skill.domain
    cat_line = f"Category: {skill.category}" if skill.category else "Category: (not set)"

    lines = [f"# {skill.name}", f"Domain: {path}", cat_line, f"Path: {result['path']}", "", skill.content, "", "## Resources"]
    lines.extend(_format_resources(result["resources"]))
    return "\n".join(lines)


def _create_skill_typed(name: str, domain: str, content: str,
                        what: str, when: str, category: str,
                        subdomain: str = "",
                        describes_component: str = "",
                        starsystem: str = "",
                        **kwargs) -> str:
    """Internal: create a skill with a specific category, then apply type-appropriate scaffolding.

    After core.create_skill writes the generic structure, this overwrites
    reference.md and creates resources/ layout matching the type pattern docs.
    Extra kwargs forwarded to core.create_skill (context, agent, hooks, etc).
    """
    from pathlib import Path

    if not name:
        return "ERROR: name is required"
    if not domain:
        return "ERROR: domain is required"
    if not what:
        return "ERROR: what is required (what does this skill do?)"
    if not when:
        return "ERROR: when is required (when should this skill be used?)"

    result = manager.create_skill(
        name=name, domain=domain, content=content,
        what=what, when=when,
        subdomain=subdomain or None,
        category=category,
        describes_component=describes_component or None,
        starsystem=starsystem or None,
        **kwargs
    )

    # Post-creation: write type-appropriate reference.md and resources/
    skill_dir = Path(result["path"])
    title = name.replace('-', ' ').replace('_', ' ').title()

    if category == "understand":
        # Understand: reference.md = TOC, resources/ = where knowledge goes
        (skill_dir / "resources").mkdir(exist_ok=True)
        ref = f"""# {title} Reference

## Resources

### `resources/`
**When to use:** Contains the actual knowledge for this domain.

Add resource files here with descriptive names. Each resource should have
a "When to use" entry in this TOC so agents know which file to read.

<!-- Example entry:
### `resources/core_concepts.md`
**When to use:** When you need to understand the fundamental concepts of {title}.
-->
"""
        (skill_dir / "reference.md").write_text(ref)

    elif category == "single_turn_process":
        # Single turn: reference.md only if supporting resources exist
        ref = f"""# {title} Reference

## Resources

Add rubrics, criteria, examples, or templates here if the atomic action
needs supporting files. Otherwise this file can stay minimal.

## Templates

Add output format templates to `templates/` if the action produces structured output.
"""
        (skill_dir / "reference.md").write_text(ref)

    elif category == "preflight":
        # Preflight: reference.md = available flights + decision criteria
        ref = f"""# {title} Reference

## Available Flights

<!-- List flight configs this preflight points to:
### `flight_config_name`
**When to use:** [criteria]
**Phases:** Step1 → Step2 → Step3
-->

## Related Skills

<!-- List understand skills that should be equipped first:
### `understand-X`
**Type:** understand
**When to use:** Before starting any flight in this domain.
-->
"""
        (skill_dir / "reference.md").write_text(ref)

    skill = result["skill"]
    path = f"{skill.domain}::{skill.subdomain}" if skill.subdomain else skill.domain
    describes_info = f"\nDESCRIBES: {describes_component}" if describes_component else ""
    starsystem_info = f"\nPART_OF: {starsystem}" if starsystem else ""
    return f"Created '{skill.name}' in {path} [{category}]\nPath: {result['path']}{describes_info}{starsystem_info}"


def create_understand(name: str, domain: str, content: str,
                      what: str, when: str,
                      subdomain: str = "",
                      describes_component: str = "",
                      starsystem: str = "",
                      **kwargs) -> str:
    """Create an UNDERSTAND skill — pure context for discussion/recall.

    Understand skills are for TALKING. They remind you of key concepts when you
    need to discuss or remember a domain. No flight config, no action — just knowledge.

    Examples: 'understand quantum mechanics', 'understand MCP architecture'

    Args:
        name: Skill name (kebab-case, e.g. 'understand-neo4j')
        domain: Primary domain (PAIAB, SANCTUM, CAVE, etc.)
        content: The knowledge content — concepts, patterns, how things work
        what: What this skill teaches (e.g. 'Neo4j query patterns and schema')
        when: When to use it (e.g. 'Need to query or understand the graph database')
        subdomain: Optional subdomain
        describes_component: GIINT component path
        starsystem: Project path
    """
    return _create_skill_typed(name, domain, content, what, when, "understand",
                               subdomain, describes_component, starsystem, **kwargs)


def create_single_turn(name: str, domain: str, content: str,
                       what: str, when: str,
                       subdomain: str = "",
                       describes_component: str = "",
                       starsystem: str = "",
                       **kwargs) -> str:
    """Create a SINGLE_TURN_PROCESS skill — context + immediate action in one turn.

    Single turn skills are for DOING something right now. Read the skill,
    do the thing immediately, done before context is lost. No flight needed.

    Examples: 'judge AI output', 'format a changelog', 'validate a schema'

    Args:
        name: Skill name (kebab-case, e.g. 'judge-ai-output')
        domain: Primary domain (PAIAB, SANCTUM, CAVE, etc.)
        content: Context + action instructions — what to know AND what to do
        what: What this skill does (e.g. 'Evaluate AI response quality')
        when: When to use it (e.g. 'Need to assess quality of AI-generated content')
        subdomain: Optional subdomain
        describes_component: GIINT component path
        starsystem: Project path
    """
    return _create_skill_typed(name, domain, content, what, when, "single_turn_process",
                               subdomain, describes_component, starsystem, **kwargs)


def create_preflight(name: str, domain: str, content: str,
                     what: str, when: str,
                     subdomain: str = "",
                     describes_component: str = "",
                     starsystem: str = "",
                     **kwargs) -> str:
    """Create a PREFLIGHT skill — primes for work, points to flight config.

    Preflight skills are for WORKING on multi-step tasks. They prime you with
    concepts, then point to a flight config for step-by-step execution.
    The content IS the HOW — it tells you what flight to use.

    Examples: 'make-skill', 'make-mcp', 'make-hook'

    Args:
        name: Skill name (kebab-case, e.g. 'make-skill')
        domain: Primary domain (PAIAB, SANCTUM, CAVE, etc.)
        content: Priming context + pointer to flight config
        what: What this skill primes for (e.g. 'Create properly structured skills')
        when: When to use it (e.g. 'Need to build a new skill')
        subdomain: Optional subdomain
        describes_component: GIINT component path
        starsystem: Project path
    """
    return _create_skill_typed(name, domain, content, what, when, "preflight",
                               subdomain, describes_component, starsystem, **kwargs)


def search_skills(query: str, n_results: int = 5, category: str = "") -> str:
    """Search skills using RAG, optionally filtered by category (understand|preflight|single_turn_process)."""
    matches = manager.search_skills(query, n_results, category or None)
    if not matches:
        return "No matches"

    lines = []
    for m in matches:
        path = f"{m['domain']}::{m['subdomain']}" if m['subdomain'] else m['domain']
        cat = f" [{m['category']}]" if m.get('category') else ""
        lines.append(f"[{m['score']:.2f}] {m['name']} ({m['type']}){cat} - {path}")
    return "\n".join(lines)


def browse_skills(category: str = "", domain: str = "", subdomain: str = "",
                  query: str = "", page: int = 1) -> str:
    """Browse skills by progressive drill-down. START HERE for skill discovery.

    Navigate the hierarchy step by step:
    1. No args → see categories (understand, preflight, single_turn_process)
    2. category → see domains within that category
    3. category + domain → see subdomains + skill names
    4. category + domain + subdomain → see paginated skill list with details
    5. Add query at any level for scoped semantic search

    Args:
        category: Filter by skill category (understand, preflight, single_turn_process)
        domain: Filter by domain within category
        subdomain: Filter by subdomain within domain
        query: Optional semantic search query, scoped to current drill-down level
        page: Page number for paginated results (default: 1)
    """
    result = manager.browse_skills(
        category=category or None,
        domain=domain or None,
        subdomain=subdomain or None,
        query=query or None,
        page=page
    )

    level = result.get("level", "unknown")
    lines = []

    if level == "categories":
        lines.append(f"📂 Skill Catalog ({result['total_skills']} skills)")
        lines.append(result.get("hint", ""))
        lines.append("")
        for cat, info in result.get("categories", {}).items():
            lines.append(f"  {cat}: {info['skill_count']} skills across {info['domain_count']} domains")
        lines.append("")
        lines.append('→ Next: browse_skills(category="...")')

    elif level == "domains":
        cat = result.get("category", "?")
        lines.append(f"📂 {cat} ({result.get('total_in_category', 0)} skills)")
        lines.append(result.get("hint", ""))
        lines.append("")
        for dom, info in result.get("domains", {}).items():
            subs = info.get("subdomains", [])
            sub_str = f" [{', '.join(subs)}]" if subs else ""
            lines.append(f"  {dom}: {info['skill_count']} skills{sub_str}")
        lines.append("")
        lines.append(f'→ Next: browse_skills(category="{cat}", domain="...")')

    elif level == "subdomains":
        cat = result.get("category")
        dom = result.get("domain", "?")
        cat_display = cat or "all"
        lines.append(f"📂 {cat_display} → {dom} ({result.get('total_in_domain', 0)} skills)")
        lines.append(result.get("hint", ""))
        lines.append("")
        for sub, info in result.get("subdomains", {}).items():
            lines.append(f"  {sub}: {info['skill_count']} skills — {', '.join(info['skills'])}")
        no_sub = result.get("no_subdomain", [])
        if no_sub:
            lines.append(f"  (no subdomain): {', '.join(no_sub)}")
        lines.append("")
        hint_parts = []
        if cat:
            hint_parts.append(f'category="{cat}"')
        hint_parts.append(f'domain="{dom}"')
        params = ", ".join(hint_parts)
        lines.append(f'→ Next: browse_skills({params}, subdomain="...")')
        lines.append(f'→ Or search: browse_skills({params}, query="...")')

    elif level == "skills":
        parts = []
        if result.get("category"): parts.append(result["category"])
        if result.get("domain"): parts.append(result["domain"])
        if result.get("subdomain"): parts.append(result["subdomain"])
        breadcrumb = " → ".join(parts) if parts else "all"

        lines.append(f"📋 Skills: {breadcrumb}")
        if result.get("query"):
            lines.append(f'🔍 Query: "{result["query"]}"')
        lines.append(result.get("hint", ""))
        lines.append("")

        recommended = result.get("recommended", [])
        if recommended:
            lines.append("★ Recommended:")
            for r in recommended:
                path = f"{r['domain']}::{r['subdomain']}" if r.get('subdomain') else r.get('domain', '')
                lines.append(f"  ★ [{r['score']:.2f}] {r['name']} ({path})")
            lines.append("")

        total = result.get("total_skills", 0)
        page_num = result.get("page", 1)
        total_pages = result.get("total_pages", 1)
        lines.append(f"All ({total} skills, page {page_num}/{total_pages}):")
        for s in result.get("skills", []):
            what = s.get("what", "")
            what_str = f" — {what}" if what else ""
            lines.append(f"  • {s['name']}{what_str}")

        if page_num < total_pages:
            lines.append(f"\n→ More: browse_skills(..., page={page_num + 1})")
        lines.append('\n→ Load: equip("skill-name")')

    return "\n".join(lines)


def reindex_all() -> str:
    """Re-index ALL skills with current dual-embed format. Run after RAG changes."""
    result = manager.reindex_all()
    return f"Re-indexed {result['reindexed']} skills"


# === Equipped state ===

def list_equipped(agent_id: str = "") -> str:
    """List currently equipped skills. Pass agent_id for agent-scoped state."""
    equipped = _get_manager(agent_id).list_equipped()
    if not equipped:
        return "No skills equipped. Use equip(name) to load skills."

    lines = ["Equipped skills:"]
    for s in equipped:
        path = f"{s['domain']}::{s['subdomain']}" if s['subdomain'] else s['domain']
        lines.append(f"  {s['name']}: {path}")
    return "\n".join(lines)


def get_equipped_content(agent_id: str = "") -> str:
    """Get full content of all equipped skills. Pass agent_id for agent-scoped state."""
    return _get_manager(agent_id).get_equipped_content()


def equip(name: str, agent_id: str = "") -> str:
    """Equip a skill or skillset. Pass agent_id for agent-scoped state.

    Args:
        name: Skill or skillset name to equip
        agent_id: Optional agent ID for scoped equipped state
    """
    result = _get_manager(agent_id).equip(name)
    if "error" in result:
        return result["error"]

    if result["type"] == "skillset":
        return f"Equipped skillset '{name}' ({result['domain']}): {', '.join(result['skills'])}"
    return f"Equipped skill '{name}' ({result['domain']})"


def unequip(name: str, agent_id: str = "") -> str:
    """Unequip a skill. Pass agent_id for agent-scoped state."""
    result = _get_manager(agent_id).unequip(name)
    if "error" in result:
        return result["error"]
    return f"Unequipped '{name}'"


def unequip_all(agent_id: str = "") -> str:
    """Clear all equipped skills. Pass agent_id for agent-scoped state."""
    result = _get_manager(agent_id).unequip_all()
    return f"Unequipped {result['unequipped_count']} skills"


# === Skillsets ===

def list_skillsets() -> str:
    """List all skillsets."""
    skillsets = manager.list_skillsets()
    if not skillsets:
        return "No skillsets. Create with create_skillset."

    lines = []
    for ss in skillsets:
        path = f"{ss['domain']}::{ss['subdomain']}" if ss['subdomain'] else ss['domain']
        lines.append(f"{ss['name']}: {path} - {ss['description']} ({ss['skill_count']} skills)")
    return "\n".join(lines)


def create_skillset(name: str, domain: str, description: str, skills: str, subdomain: str = "") -> str:
    """Create a skillset with domain.

    Args:
        name: Skillset name
        domain: Primary domain
        description: What this skillset is for
        skills: Comma-separated skill names
        subdomain: Optional subdomain
    """
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    ss = manager.create_skillset(name, domain, description, skill_list, subdomain or None)
    path = f"{ss.domain}::{ss.subdomain}" if ss.subdomain else ss.domain
    return f"Created skillset '{ss.name}' in {path} with {len(ss.skills)} skills"


def add_to_skillset(skillset_name: str, skill_name: str) -> str:
    """Add a skill to a skillset."""
    result = manager.add_to_skillset(skillset_name, skill_name)
    if "error" in result:
        return result["error"]
    return f"Added '{skill_name}' to '{skillset_name}'"


# === SkillLog matching ===

def match_skilllog(prediction: str) -> str:
    """Match a SkillLog prediction against catalog.

    Args:
        prediction: SkillLog like "domain::subdomain::specific"
    """
    result = manager.match_skilllog(prediction)

    lines = [f"SkillLog: {result['prediction']}"]

    if result['has_match']:
        lines.append("Matches:")
        for m in result['matches'][:3]:
            lines.append(f"  [{m['score']:.2f}] {m['name']} ({m['type']}, {m['domain']})")
    else:
        lines.append("No strong matches.")

    if result['available_domains']:
        lines.append(f"Domains: {', '.join(result['available_domains'])}")

    return "\n".join(lines)


# === Personas ===

def list_personas() -> str:
    """List all personas."""
    personas = manager.list_personas()
    if not personas:
        return "No personas. Create with create_persona."

    lines = []
    for p in personas:
        path = f"{p['domain']}::{p['subdomain']}" if p['subdomain'] else p['domain']
        lines.append(f"{p['name']}: {path} - {p['description']}")
        if p['mcp_set']:
            lines.append(f"  MCP set: {p['mcp_set']}")
        if p['skillset']:
            lines.append(f"  Skillset: {p['skillset']}")
    return "\n".join(lines)


def create_persona(name: str, domain: str, description: str, frame: str,
                   mcp_set: str = "", skillset: str = "",
                   carton_identity: str = "", subdomain: str = "") -> str:
    """Create a persona bundling frame, MCP set, skillset, and identity.

    Args:
        name: Persona name
        domain: Primary domain
        description: What this persona is for
        frame: Cognitive frame / prompt text (how to think)
        mcp_set: Strata MCP set name (aspirational - doesn't need to exist)
        skillset: Skillset name (aspirational - doesn't need to exist)
        carton_identity: CartON identity for observations (defaults to name)
        subdomain: Optional subdomain
    """
    p = manager.create_persona(
        name, domain, description, frame,
        mcp_set=mcp_set or None,
        skillset=skillset or None,
        carton_identity=carton_identity or None,
        subdomain=subdomain or None
    )
    path = f"{p.domain}::{p.subdomain}" if p.subdomain else p.domain
    return f"Created persona '{p.name}' in {path}"


def equip_persona(name: str, agent_id: str = "") -> str:
    """Equip a persona - loads frame, attempts skillset, reports MCP set needs.

    Missing components are aspirational - they signal what needs to be created.
    Use agent_id to equip for a specific agent (e.g. 'conductor').
    """
    mgr = _get_manager(agent_id)
    result = mgr.equip_persona(name)
    if "error" in result:
        return result["error"]

    lines = [f"Persona '{name}' equipped:"]
    lines.append(f"✓ Frame loaded")
    lines.append(f"✓ Identity: {result['carton_identity']}")

    if result['skillset'] == "equipped":
        lines.append(f"✓ Skillset equipped: {', '.join(result['equipped_skills'])}")

    if result['mcp_set']:
        lines.append(f"→ MCP set '{result['mcp_set']['name']}': {result['mcp_set']['action']}")

    if result['missing']:
        lines.append("\nMissing (aspirational):")
        for m in result['missing']:
            lines.append(f"  ✗ {m['type']}: {m['name']} - {m['suggestion']}")

    lines.append(f"\n--- Frame ---\n{result['frame_content']}")
    return "\n".join(lines)


def get_active_persona() -> str:
    """Get the currently active persona."""
    result = manager.get_active_persona()
    if not result:
        return "No active persona."
    return f"Active: {result['name']} ({result['domain']})"


def deactivate_persona() -> str:
    """Deactivate current persona and unequip all skills."""
    result = manager.deactivate_persona()
    if "status" in result:
        return result["status"]
    return f"Deactivated '{result['deactivated']}', skills unequipped"
