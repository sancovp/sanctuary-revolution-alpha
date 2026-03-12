# substrate_projector.py
"""
Substrate Projector - Project Carton concepts to various substrates.

Carton as source of truth, project content anywhere on demand.
"""

from pydantic import BaseModel, Field
from typing import Literal, Union, List
from pathlib import Path
import os
import re
import json
import yaml
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Substrate Models - each with self-documenting Field descriptions
# ============================================================================

class FileSubstrate(BaseModel):
    """Project to file at line or marker"""
    type: Literal["file"] = "file"
    path: str = Field(..., description="Path to target file")
    inject_at_line: int | None = Field(None, description="Line number to inject content at (1-indexed)")
    inject_at_marker: str | None = Field(None, description="Marker string like <!-- INJECT:name --> to find and replace after")
    replace_marker: bool = Field(False, description="If True, replace the marker line itself; if False, inject after marker")


class DiscordSubstrate(BaseModel):
    """Project to Discord channel"""
    type: Literal["discord"] = "discord"
    channel_id: str = Field(..., description="Discord channel ID")
    message_id: str | None = Field(None, description="Message ID to edit, or None for new message")


class RegistrySubstrate(BaseModel):
    """Project to HEAVEN registry key-value"""
    type: Literal["registry"] = "registry"
    key: str = Field(..., description="Registry key to write to")


class EnvSubstrate(BaseModel):
    """Project to environment variable (current process only)"""
    type: Literal["env"] = "env"
    var_name: str = Field(..., description="Environment variable name")


class SkillSubstrate(BaseModel):
    """Project CartON concept to skill package directory + ChromaDB skillgraph entry"""
    type: Literal["skill"] = "skill"
    output_dir: str | None = Field(None, description="Override output dir. Defaults to HEAVEN_DATA_DIR/skills/{name}")
    write_to_chromadb: bool = Field(True, description="Write skillgraph entry to ChromaDB for Crystal Ball discovery")


# Union of all substrate types
Substrate = Union[FileSubstrate, DiscordSubstrate, RegistrySubstrate, EnvSubstrate, SkillSubstrate]

# Registry of all substrate classes for dynamic instruction building
SUBSTRATE_CLASSES: List[type] = [
    FileSubstrate,
    DiscordSubstrate,
    RegistrySubstrate,
    EnvSubstrate,
    SkillSubstrate,
]


# ============================================================================
# Projection Request Model
# ============================================================================

class SubstrateProjection(BaseModel):
    """Full projection request"""
    substrate: Substrate
    target: str = Field(..., description="Carton concept name to project from")
    description_only: bool = Field(True, description="If True, project only description; if False, include relationships")


# ============================================================================
# Instruction Builder
# ============================================================================

def build_instructions() -> str:
    """Dynamically build instructions from substrate Field descriptions"""
    lines = [
        "# Substrate Projector Instructions",
        "",
        "Project Carton concepts to various substrates (destinations).",
        "",
        "## Parameters",
        "- substrate: dict with 'type' and type-specific fields (see below)",
        "- target: Carton concept name to project from",
        "- description_only: True for just description, False to include relationships",
        "",
        "## Available Substrates",
        "",
    ]

    for substrate_cls in SUBSTRATE_CLASSES:
        lines.append(f"### {substrate_cls.__name__.replace('Substrate', '')}")
        lines.append(f"type: \"{substrate_cls.model_fields['type'].default}\"")
        if substrate_cls.__doc__:
            lines.append(f"  {substrate_cls.__doc__}")
        lines.append("")

        for name, field in substrate_cls.model_fields.items():
            if name == "type":
                continue
            required = "required" if field.is_required() else "optional"
            desc = field.description or "No description"
            lines.append(f"  - {name} ({required}): {desc}")

        lines.append("")

    lines.extend([
        "## Examples",
        "",
        "Project to file at line:",
        '  substrate={"type": "file", "path": "/path/to/file.md", "inject_at_line": 10}',
        '  target="My_Concept"',
        "",
        "Project to file at marker:",
        '  substrate={"type": "file", "path": "/path/to/file.md", "inject_at_marker": "<!-- INJECT:section -->"}',
        '  target="My_Concept"',
        "",
        "Project to Discord:",
        '  substrate={"type": "discord", "channel_id": "123456789"}',
        '  target="My_Concept"',
    ])

    return "\n".join(lines)


# ============================================================================
# Projection Logic
# ============================================================================

def get_concept_content(concept_name: str, description_only: bool) -> str:
    """Fetch concept content from Carton/Neo4j"""
    from carton_mcp.carton_utils import CartOnUtils

    utils = CartOnUtils()

    # Query concept directly from Neo4j
    cypher_query = """
    MATCH (c:Wiki) WHERE c.n = $concept_name AND c.d IS NOT NULL
    OPTIONAL MATCH (c)-[r]->(related:Wiki)
    RETURN c.n as name, c.d as description,
           collect({type: type(r), target: related.n}) as relationships
    """
    result = utils.query_wiki_graph(cypher_query, {"concept_name": concept_name})

    if not result.get("success") or not result.get("data"):
        raise ValueError(f"Concept '{concept_name}' not found")

    concept_data = result["data"][0]
    description = concept_data.get("description", "")

    if description_only:
        return description
    else:
        # Format with relationships
        lines = [description]

        relationships = [rel for rel in concept_data.get("relationships", []) if rel.get("type")]
        if relationships:
            lines.append("")
            lines.append("## Relationships")
            for rel in relationships:
                lines.append(f"- {rel['type']}: {rel['target']}")

        return "\n".join(lines)


def project_to_file(substrate: FileSubstrate, content: str) -> str:
    """Project content to file"""
    path = Path(substrate.path)

    if not path.exists():
        # Create new file with content
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"Created {path} with content"

    # Read existing file
    lines = path.read_text().splitlines()

    if substrate.inject_at_line is not None:
        # Inject at specific line (1-indexed)
        line_idx = substrate.inject_at_line - 1
        content_lines = content.splitlines()
        new_lines = lines[:line_idx] + content_lines + lines[line_idx:]
        path.write_text("\n".join(new_lines))
        return f"Injected at line {substrate.inject_at_line} in {path}"

    elif substrate.inject_at_marker is not None:
        # Find marker and inject after (or replace)
        marker = substrate.inject_at_marker
        marker_idx = None

        for i, line in enumerate(lines):
            if marker in line:
                marker_idx = i
                break

        if marker_idx is None:
            raise ValueError(f"Marker '{marker}' not found in {path}")

        content_lines = content.splitlines()

        if substrate.replace_marker:
            new_lines = lines[:marker_idx] + content_lines + lines[marker_idx + 1:]
        else:
            new_lines = lines[:marker_idx + 1] + content_lines + lines[marker_idx + 1:]

        path.write_text("\n".join(new_lines))
        action = "Replaced marker" if substrate.replace_marker else "Injected after marker"
        return f"{action} in {path}"

    else:
        # Append to end
        existing = path.read_text()
        path.write_text(existing + "\n" + content)
        return f"Appended to {path}"


def project_to_discord(substrate: DiscordSubstrate, content: str) -> str:
    """Project content to Discord channel"""
    # Import discord MCP tools
    try:
        from carton_mcp.server_fastmcp import mcp__our_discord__send_message, mcp__our_discord__edit_message
    except ImportError:
        pass

    # Use the discord MCP directly
    if substrate.message_id:
        # Edit existing message
        # This would need the discord MCP integration
        return f"Would edit message {substrate.message_id} in channel {substrate.channel_id}"
    else:
        # Send new message
        return f"Would send to channel {substrate.channel_id}"


def project_to_registry(substrate: RegistrySubstrate, content: str) -> str:
    """Project content to HEAVEN registry"""
    # TODO: Integrate with HEAVEN registry
    return f"Would write to registry key '{substrate.key}'"


def project_to_env(substrate: EnvSubstrate, content: str) -> str:
    """Project content to environment variable"""
    os.environ[substrate.var_name] = content
    return f"Set env var {substrate.var_name}"


def project_to_skill(substrate: SkillSubstrate, concept_name: str) -> str:
    """Project CartON concept to skill package + optional ChromaDB skillgraph entry.

    Fetches structured concept data (description + relationships) from Neo4j,
    maps relationships to GnosysSkillMetadata fields, writes skill package dir.

    Args:
        substrate: SkillSubstrate with output config
        concept_name: CartON concept name (NOT content string — skill fetches its own data)
    """
    from carton_mcp.carton_utils import CartOnUtils

    utils = CartOnUtils()

    # Fetch structured concept data
    cypher = """
    MATCH (c:Wiki) WHERE c.n = $name AND c.d IS NOT NULL
    OPTIONAL MATCH (c)-[r]->(related:Wiki)
    RETURN c.n as name, c.d as description,
           collect({type: type(r), target: related.n}) as relationships
    """
    result = utils.query_wiki_graph(cypher, {"name": concept_name})

    if not result.get("success") or not result.get("data"):
        raise ValueError(f"Concept '{concept_name}' not found")

    data = result["data"][0]
    # Strip CartON wiki-links: [word](../Path/Path_itself.md) → word
    description = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', data.get("description", ""))
    rels = data.get("relationships", [])

    # Helpers for relationship extraction
    def rel_targets(rel_type):
        return [r["target"] for r in rels if r.get("type") == rel_type]

    def first_rel(rel_type):
        targets = rel_targets(rel_type)
        return targets[0] if targets else None

    # Map relationships to GnosysSkillMetadata fields
    domain = (first_rel("HAS_DOMAIN") or first_rel("HAS_PERSONAL_DOMAIN")
              or first_rel("HAS_ACTUAL_DOMAIN") or "PAIAB")
    subdomain = first_rel("HAS_SUBDOMAIN")
    raw_category = first_rel("HAS_CATEGORY") or "understand"
    # Strip Skill_Category_ prefix: "Skill_Category_Preflight" → "preflight"
    category = re.sub(r'^Skill_Category_', '', raw_category).lower()

    # Resolve what/when: try concept description first, fall back to readable name
    def _resolve_concept_text(rel_type):
        """Get target concept's description, or convert concept name to readable text."""
        name = first_rel(rel_type)
        if not name:
            return None
        # Try fetching description from Neo4j
        desc_result = utils.query_wiki_graph(
            "MATCH (c:Wiki {n: $name}) RETURN c.d as desc", {"name": name}
        )
        if desc_result.get("success") and desc_result.get("data"):
            desc = desc_result["data"][0].get("desc", "")
            if desc and len(desc) > 3:
                # Strip wiki-links from resolved description too
                return re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', desc).split("\n")[0][:200]
        # Fall back: convert concept name to readable text
        return name.replace("_", " ")

    what_text = _resolve_concept_text("HAS_WHAT")
    when_text = _resolve_concept_text("HAS_WHEN")
    produces = first_rel("HAS_PRODUCES") or first_rel("PRODUCES")
    requires = rel_targets("REQUIRES") or None

    # Bidirectional sync: if Neo4j has no REQUIRES but _metadata.json does, backfill
    if not requires:
        heaven_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        _meta_path = Path(heaven_dir) / "skills" / concept_name.lower().replace("_", "-") / "_metadata.json"
        if _meta_path.exists():
            try:
                _existing_meta = json.loads(_meta_path.read_text())
                _fs_requires = _existing_meta.get("requires", [])
                if _fs_requires:
                    # Create REQUIRES edges in Neo4j
                    for req_skill in _fs_requires:
                        req_concept = "Skill_" + req_skill.replace("-", "_").title().replace(" ", "_")
                        backfill_cypher = (
                            "MATCH (s:Wiki {n: $src}), (t:Wiki {n: $tgt}) "
                            "MERGE (s)-[:REQUIRES]->(t)"
                        )
                        utils.query_wiki_graph(backfill_cypher, {"src": concept_name, "tgt": req_concept})
                    requires = [
                        "Skill_" + r.replace("-", "_").title().replace(" ", "_")
                        for r in _fs_requires
                    ]
                    logger.info(f"Backfilled REQUIRES edges from _metadata.json: {requires}")
            except Exception:
                pass  # Non-critical — projection continues without backfill

    describes = first_rel("DESCRIBES_COMPONENT")
    starsystem = first_rel("HAS_STARSYSTEM")

    # Extract native Claude Code skill fields from typed relationships
    # These were stored by skillmanager._sync_skill_to_carton()
    context_mode = first_rel("HAS_CONTEXT_MODE")
    if context_mode and context_mode.startswith("Skill_Context_"):
        context_mode = context_mode.replace("Skill_Context_", "").lower()
    else:
        context_mode = None

    agent_type = first_rel("SPAWNS_AGENT")
    if agent_type and agent_type.startswith("Agent_Type_"):
        agent_type = agent_type.replace("Agent_Type_", "").replace("_", " ").strip()
    else:
        agent_type = None

    # Known Claude Code hook types — CartON title-cases them (PreToolUse → Pretooluse)
    _HOOK_CASING = {
        "pretooluse": "PreToolUse", "posttooluse": "PostToolUse",
        "notification": "Notification", "stop": "Stop",
        "userpromptsubmit": "UserPromptSubmit",
    }
    hook_targets = rel_targets("HAS_HOOK")
    hooks_list = []
    for ht in hook_targets:
        hook_name = ht.replace("Hook_Type_", "") if ht.startswith("Hook_Type_") else ht
        hook_name = _HOOK_CASING.get(hook_name.lower(), hook_name)
        hooks_list.append(hook_name)

    flag_targets = rel_targets("HAS_FLAG")
    not_user_invocable = "Skill_Flag_Not_User_Invocable" in flag_targets
    model_invocation_disabled = "Skill_Flag_Disable_Model_Invocation" in flag_targets

    argument_hint = first_rel("HAS_ARGUMENT_HINT")
    if argument_hint and argument_hint.startswith("Argument_Hint_"):
        argument_hint = f"[{argument_hint.replace('Argument_Hint_', '')}]"
    else:
        argument_hint = None

    # Derive skill name from concept name
    skill_name = concept_name.lower().replace("_", "-")
    for suffix in ["-feb8", "-feb7", "-feb6", "-feb5", "-feb4", "-feb2026"]:
        if skill_name.endswith(suffix):
            skill_name = skill_name[:len(skill_name) - len(suffix)]
            break

    # Determine output directory
    if substrate.output_dir:
        skill_dir = Path(substrate.output_dir)
    else:
        heaven_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        skill_dir = Path(heaven_dir) / "skills" / skill_name

    skill_dir.mkdir(parents=True, exist_ok=True)

    # Build SKILL.md with YAML frontmatter (yaml.dump for correctness + all fields)
    what_line = what_text or description[:100].replace("\n", " ")
    when_line = when_text or "Context matches domain"

    frontmatter = {
        "name": skill_name,
        "description": f"WHAT: {what_line}\nWHEN: {when_line}",
    }

    # Native Claude Code fields (only include when present)
    if context_mode:
        frontmatter["context"] = context_mode
    if agent_type:
        frontmatter["agent"] = agent_type
    if hooks_list:
        frontmatter["hooks"] = {h: {} for h in hooks_list}
    if not_user_invocable:
        frontmatter["user-invocable"] = False
    if model_invocation_disabled:
        frontmatter["disable-model-invocation"] = True
    if argument_hint:
        frontmatter["argument-hint"] = argument_hint

    skill_md = "---\n" + yaml.dump(frontmatter, default_flow_style=False, sort_keys=False) + "---\n\n" + description + "\n"
    (skill_dir / "SKILL.md").write_text(skill_md)

    # Build _metadata.json
    metadata = {
        "domain": domain,
        "subdomain": subdomain,
        "category": category,
        "what": what_text,
        "when": when_text,
        "produces": produces,
        "requires": requires,
        "describes_component": describes,
        "starsystem": starsystem,
    }
    metadata = {k: v for k, v in metadata.items() if v is not None}
    (skill_dir / "_metadata.json").write_text(json.dumps(metadata, indent=2))

    # Build reference.md and create child files routed by IS_A type
    children = rel_targets("HAS_PART")

    # Query each child's description and IS_A types in one shot
    child_entries = []  # list of (name, desc, dir_name, filename)
    for child_name in children:
        child_result = utils.query_wiki_graph(
            "MATCH (c:Wiki {n: $name}) "
            "OPTIONAL MATCH (c)-[:IS_A]->(t:Wiki) "
            "RETURN c.d as description, collect(t.n) as types",
            {"name": child_name}
        )
        if not (child_result.get("success") and child_result.get("data")):
            continue
        row = child_result["data"][0]
        raw_desc = row.get("description", "")
        # Strip wiki-links from child content
        child_desc = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', raw_desc)
        types = [t.lower() for t in row.get("types", [])]

        # Route by IS_A type → directory + extension
        if any("script" in t for t in types):
            dir_name = "scripts"
            base = child_name.lower().replace("_", "-")
            # Detect language from shebang or default to .py
            ext = ".py" if child_desc.lstrip().startswith("#!") or "import " in child_desc else ".sh"
            filename = base + ext
        elif any("template" in t for t in types):
            dir_name = "templates"
            filename = child_name.lower().replace("_", "-") + ".md"
        else:
            dir_name = "resources"
            filename = child_name.lower().replace("_", "-") + ".md"

        child_entries.append((child_name, child_desc, dir_name, filename))

    # Write reference.md
    ref_lines = [f"# {skill_name} Reference", ""]
    if child_entries:
        # Group by directory
        for section in ["scripts", "resources", "templates"]:
            items = [(n, fn) for n, _, d, fn in child_entries if d == section]
            if items:
                ref_lines.append(f"## {section.title()}")
                ref_lines.append("")
                for name, fn in items:
                    ref_lines.append(f"- **{name}**: See `{section}/{fn}`")
                ref_lines.append("")
    else:
        ref_lines.append("No additional resources.")
    (skill_dir / "reference.md").write_text("\n".join(ref_lines))

    # Create directories and write child files
    for child_name, child_desc, dir_name, filename in child_entries:
        target_dir = skill_dir / dir_name
        target_dir.mkdir(exist_ok=True)
        if dir_name == "scripts":
            # Scripts: write content verbatim (it's code)
            (target_dir / filename).write_text(child_desc)
        else:
            # Resources/templates: add header
            (target_dir / filename).write_text(f"# {child_name}\n\n{child_desc}")

    # Write to ChromaDB skillgraphs collection
    chromadb_msg = ""
    if substrate.write_to_chromadb:
        try:
            import chromadb
            chroma_path = os.path.join(
                os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "skill_chroma"
            )
            client = chromadb.PersistentClient(path=chroma_path)
            collection = client.get_or_create_collection(
                name="skillgraphs",
                metadata={"hnsw:space": "cosine"}
            )

            # Skillgraph naming convention: Skillgraph_{Title_Case}
            sg_name = "Skillgraph_" + concept_name.replace("-", "_")
            # Ontological sentence — typed fields, NOT bag-of-words
            parts = [f"[SKILLGRAPH:{skill_name}]"]
            parts.append(f"is_a:Skill")
            parts.append(f"has_domain:{domain}")
            if subdomain:
                parts.append(f"has_subdomain:{subdomain}")
            if category:
                parts.append(f"has_category:{category}")
            if what_text:
                parts.append(f"what:{what_text}")
            if when_text:
                parts.append(f"when:{when_text}")
            if produces:
                parts.append(f"produces:{produces}")
            if requires:
                parts.append(f"requires:[{','.join(requires)}]")
            if context_mode:
                parts.append(f"context:{context_mode}")
            if agent_type:
                parts.append(f"agent:{agent_type}")
            if hooks_list:
                parts.append(f"hooks:[{','.join(hooks_list)}]")
            if not_user_invocable:
                parts.append("user_invocable:false")
            if model_invocation_disabled:
                parts.append("disable_model_invocation:true")
            parts.append("[/SKILLGRAPH]")
            doc_text = " ".join(parts)

            meta = {
                "name": sg_name,
                "skill": skill_name,
                "domain": domain,
                "category": category,
                "concept_name": concept_name,
                "type": "skillgraph",
            }
            if produces:
                meta["produces"] = produces
            if subdomain:
                meta["subdomain"] = subdomain
            if context_mode:
                meta["context"] = context_mode
            if agent_type:
                meta["agent"] = agent_type

            collection.upsert(
                ids=[f"skillgraph:{skill_name}"],
                documents=[doc_text],
                metadatas=[meta]
            )
            chromadb_msg = " + ChromaDB skillgraph written"
        except Exception as e:
            chromadb_msg = f" (ChromaDB failed: {e})"

    return f"Skill '{skill_name}' projected to {skill_dir}{chromadb_msg}"


# Dispatch table
PROJECTORS = {
    "file": project_to_file,
    "discord": project_to_discord,
    "registry": project_to_registry,
    "env": project_to_env,
    "skill": project_to_skill,
}


def render_through_template(concept_name: str, template_name: str) -> str:
    """
    Render concept through a metastack template.

    Args:
        concept_name: Carton concept name
        template_name: Registered metastack template name (e.g., 'reference_document')

    Returns:
        Rendered content from template
    """
    from carton_mcp.carton_utils import CartOnUtils

    utils = CartOnUtils()

    # Get full concept data
    cypher_query = """
    MATCH (c:Wiki) WHERE c.n = $concept_name AND c.d IS NOT NULL
    OPTIONAL MATCH (c)-[r]->(related:Wiki)
    RETURN c.n as name, c.d as description,
           collect({type: type(r), target: related.n}) as relationships
    """
    result = utils.query_wiki_graph(cypher_query, {"concept_name": concept_name})

    if not result.get("success") or not result.get("data"):
        raise ValueError(f"Concept '{concept_name}' not found")

    concept_data = result["data"][0]

    # Build template content from concept data
    # Parse description for taxonomy/source if present
    description = concept_data.get("description", "")

    # Extract taxonomy and source from description if formatted
    taxonomy = None
    source = None
    essence = description

    if "**Taxonomy:**" in description:
        parts = description.split("**Taxonomy:**")
        essence = parts[0].strip()
        meta_part = parts[1]
        if "**Source:**" in meta_part:
            tax_source = meta_part.split("**Source:**")
            taxonomy = tax_source[0].strip()
            source = tax_source[1].strip()
        else:
            taxonomy = meta_part.strip()

    # Build relationships list for template
    relationships = []
    for rel in concept_data.get("relationships", []):
        if rel.get("type") and rel.get("target"):
            relationships.append({"type": rel["type"], "related": rel["target"]})

    # Split essence into paragraph and sentence
    essence_lines = essence.split("\n\n")
    essence_paragraph = essence_lines[0] if essence_lines else essence
    essence_sentence = essence_lines[1] if len(essence_lines) > 1 else essence_paragraph[:200]

    # Build template content
    template_content = {
        "name": concept_data.get("name", concept_name),
        "essence_paragraph": essence_paragraph,
        "essence_sentence": essence_sentence,
        "relationships": relationships if relationships else None,
    }

    if taxonomy:
        template_content["taxonomy"] = taxonomy
    if source:
        template_content["source"] = source

    # Call metastack to render
    try:
        from heaven_base.registry import RegistryService

        registry_dir = os.getenv("HEAVEN_DATA_DIR")
        if not registry_dir:
            raise RuntimeError("HEAVEN_DATA_DIR not set")

        registry = RegistryService(registry_dir)
        meta_info = registry.get("metastacks", template_name)

        if not meta_info:
            raise ValueError(f"Template '{template_name}' not found in registry")

        class_path = meta_info.get("class_path")
        defaults = meta_info.get("defaults", {})

        # Import and instantiate template class
        import sys
        templates_dir = os.path.join(registry_dir, "metastack_templates")
        if templates_dir not in sys.path:
            sys.path.insert(0, templates_dir)

        from importlib import import_module
        module_name, class_name = class_path.rsplit(".", 1)
        module = import_module(module_name)
        template_class = getattr(module, class_name)

        # Merge defaults with content
        merged = {**defaults, **template_content}

        # Instantiate and render
        instance = template_class(**merged)
        return instance.render()

    except ImportError as e:
        raise RuntimeError(f"Failed to import template: {e}")


def compile_memory_tier(tier_num: int = 0, shared_connection=None, active_hypercluster: str = None) -> str:
    """
    Compile a memory tier file from CartON Hypercluster graph.

    MEMORY.md is never manually edited — it's a compilation target.
    CartON graph = source code, this function = compiler, MEMORY.md = object code.

    3-Tier Design (Idea_Three_Tier_Memory_Architecture_Mar11):
    - Tier 0 (MEMORY.md): UltraMap (HC names + why) + ONE expanded active hypercluster
    - Tier 1 (rules): Starsystem HC collection list with hierarchy
    - Tier 2+ (faint): Compressed indices

    Args:
        tier_num: Which memory tier to compile (0=MEMORY.md, 1=rules L0, 2=L1, 3=L2)
        shared_connection: Optional shared Neo4j connection
        active_hypercluster: Name of the active hypercluster to expand (optional).
                            If not provided, checks /tmp/active_hypercluster.txt

    Returns:
        Result message with file path and stats
    """
    from carton_mcp.carton_utils import CartOnUtils

    utils = CartOnUtils(shared_connection=shared_connection)
    tier_name = f"Memory_Tier_{tier_num}"

    # Tier file paths
    tier_paths = {
        0: os.path.expanduser("~/.claude/projects/-home-GOD/memory/MEMORY.md"),
        1: os.path.expanduser("~/.claude/rules/hyperclusters-archive.md"),
        2: os.path.expanduser("~/.claude/rules/faint-memories-L1.md"),
        3: os.path.expanduser("~/.claude/rules/faintest-memories-L2.md"),
    }

    if tier_num not in tier_paths:
        return f"Unknown tier: {tier_num}"

    # Query all Hyperclusters at this tier with their relationships
    query = """
    MATCH (h:Wiki)-[:IS_A]->(ht:Wiki {n: "Hypercluster"})
    MATCH (h)-[:PART_OF]->(tier:Wiki {n: $tier_name})
    OPTIONAL MATCH (h)-[:HAS_STATUS]->(status:Wiki)
    OPTIONAL MATCH (h)-[:HAS_GIINT_PROJECT]->(giint:Wiki)
    OPTIONAL MATCH (h)-[:HAS_PART]->(part:Wiki)
    RETURN h.n as name, h.d as description,
           status.n as status,
           giint.n as giint_project,
           collect(DISTINCT part.n) as parts
    ORDER BY h.n
    """
    result = utils.query_wiki_graph(query, {"tier_name": tier_name})

    if not result.get("success"):
        return f"Query failed: {result}"

    hyperclusters = result.get("data", [])

    # Group by status
    active = []
    protected = []
    blocked = []
    for hc in hyperclusters:
        status = hc.get("status", "Active")
        if status == "Protected":
            protected.append(hc)
        elif status == "Blocked":
            blocked.append(hc)
        else:
            active.append(hc)

    # Query UltraMaps
    ultramap_query = """
    MATCH (u:Wiki)-[:IS_A]->(ut:Wiki {n: "Ultramap"})
    RETURN u.n as name, u.d as description
    ORDER BY u.n
    """
    ultramap_result = utils.query_wiki_graph(ultramap_query, {})
    ultramaps = ultramap_result.get("data", []) if ultramap_result.get("success") else []

    # Query Done collections for archived section
    done_query = """
    MATCH (c:Wiki)-[:IS_A]->(ct:Wiki {n: "Carton_Collection"})
    WHERE c.n STARTS WITH "Done_"
    OPTIONAL MATCH (c)-[:HAS_PART]->(member:Wiki)
    RETURN c.n as name, count(member) as member_count
    ORDER BY c.n
    """
    done_result = utils.query_wiki_graph(done_query, {})
    done_collections = done_result.get("data", []) if done_result.get("success") else []

    # === COMPILE THE FILE ===
    def _clean_why(text):
        """Strip wiki-links and migration prefix from description."""
        # Strip complete wiki-links: [word](../Path/Path_itself.md) → word
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Strip truncated/partial wiki-links: [word](../partial... → word
        text = re.sub(r'\[([^\]]+)\]\([^)]*$', r'\1', text)
        # Strip orphan link targets: (../Path/Path_itself.md) with no preceding []
        text = re.sub(r'\(\.\./[^)]*\)', '', text)
        # Strip truncated orphan targets: (../partial...
        text = re.sub(r'\(\.\./[^)]*$', '', text)
        # Strip truncated opening brackets: [word without closing ]
        text = re.sub(r'\[[^\]]*$', '', text)
        # Strip leftover '''[ or similar artifacts
        text = re.sub(r"'{2,}\[?", '', text)
        # Strip migration prefix: "HyperCluster tracking GIINT_Project_X. Why: "
        text = re.sub(r'^HyperCluster tracking \S+\.\s*Why:\s*', '', text)
        # Clean up double spaces and trailing punctuation artifacts
        text = re.sub(r'  +', ' ', text)
        return text.strip()

    # Resolve active hypercluster from parameter or state file
    if not active_hypercluster:
        active_hc_file = Path("/tmp/active_hypercluster.txt")
        if active_hc_file.exists():
            active_hypercluster = active_hc_file.read_text().strip()

    lines = []

    if tier_num == 0:
        # === SECTION 1: UltraMap (HC-to-HC morphisms) ===
        # UltraMap = relationships BETWEEN sibling hyperclusters
        # (DEPENDS_ON, BLOCKED_BY, FAILED_BECAUSE, RETRY_AS, etc.)
        morphism_query = """
        MATCH (h1:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
        MATCH (h2:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
        WHERE h1 <> h2
        MATCH (h1)-[r]->(h2)
        RETURN h1.n as source, type(r) as rel_type, h2.n as target
        ORDER BY h1.n, type(r)
        """
        morphism_result = utils.query_wiki_graph(morphism_query, {})
        morphisms = morphism_result.get("data", []) if morphism_result.get("success") else []

        lines.extend([
            "# MEMORY - GNO.SYS",
            "",
            "## UltraMap (HC-to-HC morphisms)",
            "",
        ])

        if morphisms:
            # Group morphisms by source HC
            from collections import defaultdict
            morph_by_source = defaultdict(list)
            for m in morphisms:
                src = m["source"].replace("Hypercluster_", "").replace("_", " ")
                tgt = m["target"].replace("Hypercluster_", "").replace("_", " ")
                morph_by_source[src].append(f"{m['rel_type'].lower()} → {tgt}")

            for src_name, rels in sorted(morph_by_source.items()):
                lines.append(f"- **{src_name}**: {'; '.join(rels)}")
        else:
            lines.append("*(No HC-to-HC morphisms yet — add DEPENDS_ON/BLOCKED_BY between Hyperclusters)*")

        # Compact HC listing with status tags (for HCs not in morphism graph)
        lines.extend(["", "### All Hyperclusters", ""])

        all_hcs_sorted = sorted(active + blocked + protected, key=lambda h: h["name"])
        for hc in all_hcs_sorted:
            display_name = hc["name"].replace("Hypercluster_", "").replace("_", " ")
            status = hc.get("status", "Active")
            tag = ""
            if status == "Blocked":
                tag = " (BLOCKED)"
            elif status == "Protected":
                tag = " (PROTECTED)"
            why = _clean_why(hc.get("description", "No description"))
            lines.append(f"- **{display_name}**{tag}: {why}")

        # Done collections (compact)
        if done_collections:
            lines.append("")
            for coll in done_collections:
                count = coll.get("member_count", 0)
                lines.append(f"- ~~{coll['name']}~~ ({count} concepts, archived)")

        # === SECTION 2: Active Hypercluster (FULLY EXPANDED) ===
        # Show EVERY concept PART_OF the active HC's GIINT project
        lines.extend(["", "---", ""])

        expanded_hc = None
        expanded_giint = None
        if active_hypercluster:
            all_hcs = active + blocked + protected
            for hc in all_hcs:
                if hc["name"] == active_hypercluster or hc["name"].replace("Hypercluster_", "") == active_hypercluster:
                    expanded_hc = hc
                    expanded_giint = hc.get("giint_project")
                    break

        if expanded_hc:
            display_name = expanded_hc["name"].replace("Hypercluster_", "").replace("_", " ")
            why = _clean_why(expanded_hc.get("description", "No description"))

            lines.extend([
                f"## Active Task: {display_name}",
                f"Why: {why}",
                "",
            ])

            # Query ALL concepts PART_OF the GIINT project (full expansion)
            if expanded_giint:
                expand_query = """
                MATCH (c:Wiki)-[:PART_OF]->(g:Wiki {n: $giint_name})
                RETURN c.n as name, substring(c.d, 0, 100) as snippet
                ORDER BY c.n
                """
                expand_result = utils.query_wiki_graph(expand_query, {"giint_name": expanded_giint})
                expand_data = expand_result.get("data", []) if expand_result.get("success") else []

                if expand_data:
                    lines.append(f"### Concepts ({len(expand_data)}):")
                    for concept in expand_data:
                        name = concept["name"]
                        snippet = _clean_why(concept.get("snippet", "").strip())
                        if snippet:
                            lines.append(f"- **{name}**: {snippet}")
                        else:
                            lines.append(f"- **{name}**")
                else:
                    lines.append("*(No concepts PART_OF this GIINT project yet)*")
            else:
                # Fallback: show HAS_PART from the HC itself
                parts = [p for p in expanded_hc.get("parts", []) if p]
                if parts:
                    lines.append(f"### Concepts ({len(parts)}):")
                    for p in parts:
                        lines.append(f"- {p}")
                else:
                    lines.append("*(No concepts in this hypercluster yet)*")
        else:
            lines.extend([
                "## Active Task: None",
                "No active hypercluster set. Write hypercluster name to /tmp/active_hypercluster.txt",
            ])

    elif tier_num == 1:
        # Tier 1: Completed GIINT Projects with hierarchy
        tier1_query = """
        MATCH (h:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
        MATCH (h)-[:PART_OF]->(:Wiki {n: $tier_name})
        MATCH (h)-[:HAS_GIINT_PROJECT]->(giint:Wiki)
        OPTIONAL MATCH (giint)-[:HAS_FEATURE]->(f:Wiki)
        OPTIONAL MATCH (f)-[:HAS_COMPONENT]->(c:Wiki)
        OPTIONAL MATCH (c)-[:HAS_DELIVERABLE]->(d:Wiki)
        OPTIONAL MATCH (d)-[:HAS_TASK]->(t:Wiki)
        OPTIONAL MATCH (giint)-[:HAS_PART]->(im:Wiki)
        WHERE im.n STARTS WITH 'Inclusion_Map_'
        RETURN h.n as name, h.d as description, giint.n as giint_project,
               collect(DISTINCT f.n) as features,
               collect(DISTINCT c.n) as components,
               collect(DISTINCT d.n) as deliverables,
               collect(DISTINCT t.n) as tasks,
               collect(DISTINCT im.n) as inclusion_maps
        ORDER BY h.n
        """
        tier1_result = utils.query_wiki_graph(tier1_query, {"tier_name": tier_name})
        tier1_data = tier1_result.get("data", []) if tier1_result.get("success") else []

        lines.extend([
            "# Hyperclusters Archive - Completed GIINT Projects",
            "",
            "<!-- Auto-compiled by compile_memory_tier(1) -->",
            "<!-- Done hyperclusters with complete GIINT hierarchies -->",
            "",
        ])

        for entry in tier1_data:
            giint_name = entry.get("giint_project", "Unknown")
            collection_name = f"Done_{giint_name}_Collection"
            features = [x for x in entry.get("features", []) if x]
            components = [x for x in entry.get("components", []) if x]
            deliverables = [x for x in entry.get("deliverables", []) if x]
            tasks = [x for x in entry.get("tasks", []) if x]
            inclusion_maps = [x for x in entry.get("inclusion_maps", []) if x]

            lines.append(f"## {giint_name}")
            lines.append(f"Collection: {collection_name}")
            lines.append("Hierarchy:")
            lines.append(f"  - Features: {', '.join(features) if features else 'None'}")
            lines.append(f"  - Components: {', '.join(components) if components else 'None'}")
            lines.append(f"  - Deliverables: {', '.join(deliverables) if deliverables else 'None'}")
            lines.append(f"  - Tasks: {', '.join(tasks) if tasks else 'None'}")
            lines.append(f"  - Inclusion_Maps: {', '.join(inclusion_maps) if inclusion_maps else 'None'}")
            lines.append("")

    # Write the compiled file
    output_path = tier_paths[tier_num]
    if output_path is None:
        return f"Tier {tier_num} has dynamic path — not yet supported"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines) + "\n")

    stats = f"{len(active)} active, {len(blocked)} blocked, {len(protected)} protected, {len(ultramaps)} ultramaps, {len(done_collections)} archived"
    logger.info(f"[MemoryCompiler] Tier {tier_num} compiled: {stats} -> {output_path}")
    return f"Compiled Tier {tier_num}: {stats} -> {output_path}"


def prune_memory_tier(tier_num: int = 0, dry_run: bool = False, compress_all: bool = False, shared_connection=None) -> str:
    """
    Prune completed hyperclusters from a memory tier to the next tier.

    Pruning is a graph mutation:
    1. Find Hyperclusters with Done Collections (or all if compress_all=True)
    2. Move PART_OF from Memory_Tier_N to Memory_Tier_{N+1}
    3. Recompile both tier files
    4. Auto-cascade if next tier exceeds 100 lines

    Args:
        tier_num: Which tier to prune from (default: 0)
        dry_run: If True, show what would be done without doing it
        compress_all: If True, move ALL hyperclusters (for cascade compression)
        shared_connection: Optional shared Neo4j connection for reads
    """
    from carton_mcp.carton_utils import CartOnUtils

    utils = CartOnUtils(shared_connection=shared_connection)
    tier_name = f"Memory_Tier_{tier_num}"
    next_tier = tier_num + 1
    next_tier_name = f"Memory_Tier_{next_tier}"

    if next_tier > 3:
        return f"Cannot prune beyond Tier 3"

    # Find candidates to move
    if compress_all:
        find_query = """
        MATCH (h:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
        MATCH (h)-[:PART_OF]->(:Wiki {n: $tier_name})
        RETURN h.n as hypercluster
        """
        result = utils.query_wiki_graph(find_query, {"tier_name": tier_name})
    else:
        find_query = """
        MATCH (h:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
        MATCH (h)-[:PART_OF]->(:Wiki {n: $tier_name})
        MATCH (h)-[:HAS_GIINT_PROJECT]->(giint:Wiki)
        MATCH (done:Wiki)-[:IS_A]->(:Wiki {n: "Carton_Collection"})
        WHERE done.n = "Done_" + giint.n + "_Collection"
        RETURN h.n as hypercluster, giint.n as giint_project
        """
        result = utils.query_wiki_graph(find_query, {"tier_name": tier_name})

    if not result.get("success"):
        return f"Query failed: {result}"

    candidates = result.get("data", [])
    if not candidates:
        action = "compress" if compress_all else "prune"
        return f"No hyperclusters to {action} at {tier_name}"

    names = [c["hypercluster"] for c in candidates]

    if dry_run:
        action = "compress" if compress_all else "prune"
        return f"[DRY RUN] Would {action} {len(names)} from {tier_name} to {next_tier_name}:\n" + \
               "\n".join(f"  - {n}" for n in names)

    # Move PART_OF edges in Neo4j (write operation — needs direct driver)
    from neo4j import GraphDatabase
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        with driver.session() as session:
            session.run("""
                MATCH (new_tier:Wiki {n: $new_tier})
                WITH new_tier
                UNWIND $names AS hc_name
                MATCH (h:Wiki {n: hc_name})-[r:PART_OF]->(:Wiki {n: $old_tier})
                DELETE r
                WITH h, new_tier
                MERGE (h)-[:PART_OF]->(new_tier)
            """, names=names, old_tier=tier_name, new_tier=next_tier_name)
    finally:
        driver.close()

    # Recompile both tiers
    old_result = compile_memory_tier(tier_num, shared_connection=shared_connection)
    new_result = compile_memory_tier(next_tier, shared_connection=shared_connection)

    # Auto-cascade if next tier exceeds 100 lines
    tier_paths = {
        0: os.path.expanduser("~/.claude/projects/-home-GOD/memory/MEMORY.md"),
        1: os.path.expanduser("~/.claude/rules/hyperclusters-archive.md"),
        2: os.path.expanduser("~/.claude/rules/faint-memories-L1.md"),
        3: os.path.expanduser("~/.claude/rules/faintest-memories-L2.md"),
    }
    cascade_msg = ""
    next_path = tier_paths.get(next_tier)
    if next_path and next_tier < 3 and Path(next_path).exists():
        line_count = len(Path(next_path).read_text().split("\n"))
        if line_count > 100:
            cascade_msg = f"\n  Tier {next_tier} at {line_count} lines — cascading compression..."
            cascade_result = prune_memory_tier(next_tier, compress_all=True, shared_connection=shared_connection)
            cascade_msg += f"\n  {cascade_result}"

    action = "Compressed" if compress_all else "Pruned"
    return (
        f"{action} {len(names)} hyperclusters: {tier_name} -> {next_tier_name}\n"
        f"  {old_result}\n"
        f"  {new_result}"
        f"{cascade_msg}"
    )


def memory_tier_stats(shared_connection=None) -> str:
    """
    Show memory tier system status from CartON graph.
    All data sourced from Neo4j — no text parsing.
    """
    from carton_mcp.carton_utils import CartOnUtils

    utils = CartOnUtils(shared_connection=shared_connection)

    tier_paths = {
        0: os.path.expanduser("~/.claude/projects/-home-GOD/memory/MEMORY.md"),
        1: os.path.expanduser("~/.claude/rules/hyperclusters-archive.md"),
        2: os.path.expanduser("~/.claude/rules/faint-memories-L1.md"),
        3: os.path.expanduser("~/.claude/rules/faintest-memories-L2.md"),
    }
    tier_labels = {0: "MEMORY.md", 1: "L0 Archive", 2: "L1 Faint", 3: "L2 Faintest"}

    lines = []
    lines.append("=" * 60)
    lines.append("MEMORY SYSTEM STATUS (CartON Graph-Driven)")
    lines.append("=" * 60)

    for tier_num in range(4):
        tier_name = f"Memory_Tier_{tier_num}"
        count_query = """
        MATCH (h:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
        MATCH (h)-[:PART_OF]->(:Wiki {n: $tier_name})
        RETURN count(h) as count
        """
        result = utils.query_wiki_graph(count_query, {"tier_name": tier_name})
        count = 0
        if result.get("success") and result.get("data"):
            count = result["data"][0].get("count", 0)

        path = tier_paths.get(tier_num)
        file_lines = 0
        if path and Path(path).exists():
            file_lines = len(Path(path).read_text().split("\n"))

        status = "NEEDS COMPRESSION" if file_lines > 100 else "ok"
        lines.append(f"\nTier {tier_num} ({tier_labels[tier_num]}): {count} hyperclusters, {file_lines} lines [{status}]")

    # Done collections count
    done_query = """
    MATCH (c:Wiki)-[:IS_A]->(:Wiki {n: "Carton_Collection"})
    WHERE c.n STARTS WITH "Done_"
    RETURN count(c) as count
    """
    done_result = utils.query_wiki_graph(done_query, {})
    done_count = 0
    if done_result.get("success") and done_result.get("data"):
        done_count = done_result["data"][0].get("count", 0)

    # Find prunable (done hyperclusters at Tier 0)
    prunable_query = """
    MATCH (h:Wiki)-[:IS_A]->(:Wiki {n: "Hypercluster"})
    MATCH (h)-[:PART_OF]->(:Wiki {n: "Memory_Tier_0"})
    MATCH (h)-[:HAS_GIINT_PROJECT]->(giint:Wiki)
    MATCH (done:Wiki)-[:IS_A]->(:Wiki {n: "Carton_Collection"})
    WHERE done.n = "Done_" + giint.n + "_Collection"
    RETURN h.n as name
    """
    prunable_result = utils.query_wiki_graph(prunable_query, {})
    prunable = prunable_result.get("data", []) if prunable_result.get("success") else []

    lines.append(f"\nDone Collections: {done_count}")
    lines.append(f"Prunable (done at Tier 0): {len(prunable)}")
    for p in prunable:
        lines.append(f"  - {p['name']}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def substrate_project(substrate: dict, target: str, description_only: bool = True, template: str = None) -> str:
    """
    Main projection function.

    Args:
        substrate: Dict with 'type' and type-specific fields
        target: Carton concept name
        description_only: Whether to include just description or relationships too
        template: Optional metastack template name (e.g., 'reference_document')
                  If provided, renders through template before projecting

    Returns:
        Result message
    """
    # Validate substrate
    substrate_type = substrate.get("type")
    if not substrate_type:
        raise ValueError("substrate must have 'type' field")

    if substrate_type not in PROJECTORS:
        raise ValueError(f"Unknown substrate type: {substrate_type}. Available: {list(PROJECTORS.keys())}")

    # Parse into appropriate model for validation
    substrate_classes = {
        "file": FileSubstrate,
        "discord": DiscordSubstrate,
        "registry": RegistrySubstrate,
        "env": EnvSubstrate,
        "skill": SkillSubstrate,
    }

    substrate_model = substrate_classes[substrate_type](**substrate)

    # Get content and project
    projector = PROJECTORS[substrate_type]
    if substrate_type == "skill":
        # Skill projector fetches its own structured data from Neo4j
        result = projector(substrate_model, target)
    elif template:
        content = render_through_template(target, template)
        result = projector(substrate_model, content)
    else:
        content = get_concept_content(target, description_only)
        result = projector(substrate_model, content)

    return result
