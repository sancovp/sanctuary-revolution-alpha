"""Core skill management logic with three-tier architecture: global/equipped/sets."""

import json
import yaml
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings

from .models import Skill, Skillset, Persona

logger = logging.getLogger(__name__)

# Claude Code's native skills directory - we mirror equipped skills here
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"


class SkillManager:
    """Manages skills with global catalog, agent-scoped equipped state, and skillsets."""

    def __init__(self, skills_dir: Optional[str] = None, chroma_dir: Optional[str] = None,
                 agent_id: Optional[str] = None):
        # Use HEAVEN_DATA_DIR env var, fallback to ~/.heaven_data
        heaven_data = os.environ.get("HEAVEN_DATA_DIR", os.path.expanduser("~/.heaven_data"))
        self.skills_dir = Path(skills_dir or os.path.join(heaven_data, "skills"))
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.agent_id = agent_id  # None = legacy shared behavior
        logger.info(f"Skills directory: {self.skills_dir} (agent_id={agent_id})")

        # Skillsets and personas config
        self.skillsets_file = self.skills_dir / "_skillsets.json"
        self.personas_file = self.skills_dir / "_personas.json"

        # Defaults and quarantine
        self.defaults_file = self.skills_dir / "_defaults.json"
        self.quarantine_dir = self.skills_dir / "_quarantine"

        # Equipped state — scoped per agent_id
        if agent_id:
            self.equipped_file = self.skills_dir / f"_equipped_{agent_id}.json"
        else:
            self.equipped_file = self.skills_dir / "_equipped.json"
        self.equipped: dict[str, Skill] = {}
        self.active_persona: Optional[Persona] = None
        self._persona_file = self.skills_dir / "_active_persona.json"
        self._load_persona_state()

        # ChromaDB for RAG
        chroma_path = chroma_dir or os.path.join(heaven_data, "skill_chroma")
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="skills",
            metadata={"hnsw:space": "cosine"}
        )

        # Sync on startup
        self.sync_on_startup()

    # === File paths ===

    def _skill_path(self, name: str) -> Path:
        return self.skills_dir / name

    def _skill_md_path(self, name: str) -> Path:
        return self._skill_path(name) / "SKILL.md"

    def _metadata_path(self, name: str) -> Path:
        return self._skill_path(name) / "_metadata.json"

    # === Skill CRUD ===

    def _parse_skill_md(self, content: str) -> dict:
        """Parse SKILL.md YAML frontmatter via yaml.safe_load. Returns dict with Claude's fields + body.

        Claude's official frontmatter fields:
        name, description, allowed-tools, model, context, agent,
        hooks, user-invocable, disable-model-invocation, argument-hint
        """
        lines = content.strip().split("\n")
        if lines[0] != "---":
            return {"name": "", "description": "", "body": content}

        end_idx = None
        for i, line in enumerate(lines[1:], 1):
            if line == "---":
                end_idx = i
                break

        if not end_idx:
            return {"name": "", "description": "", "body": content}

        frontmatter_str = "\n".join(lines[1:end_idx])
        body = "\n".join(lines[end_idx + 1:]).strip()

        try:
            fm = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError:
            fm = {}

        # Normalize hyphenated YAML keys to underscored Python keys
        return {
            "name": fm.get("name", ""),
            "description": fm.get("description", "").strip() if fm.get("description") else "",
            "allowed_tools": fm.get("allowed-tools"),
            "model": fm.get("model"),
            "context": fm.get("context"),
            "agent": fm.get("agent"),
            "hooks": fm.get("hooks"),
            "user_invocable": fm.get("user-invocable"),
            "disable_model_invocation": fm.get("disable-model-invocation"),
            "argument_hint": fm.get("argument-hint"),
            "body": body,
        }

    def _build_description(self, what: str, when: str) -> str:
        """Build Claude's description string from typed fields."""
        return f"WHAT: {what}\nWHEN: {when}"

    def create_skill(self, name: str, domain: str, content: str,
                     what: str, when: str,
                     subdomain: Optional[str] = None,
                     category: Optional[str] = None,
                     allowed_tools: Optional[str] = None,
                     model: Optional[str] = None,
                     context: Optional[str] = None,
                     agent: Optional[str] = None,
                     hooks: Optional[dict] = None,
                     user_invocable: Optional[bool] = None,
                     disable_model_invocation: Optional[bool] = None,
                     argument_hint: Optional[str] = None,
                     describes_component: Optional[str] = None,
                     starsystem: Optional[str] = None) -> dict:
        """Create a new skill in global catalog with full resource structure.

        Args:
            what: What this skill does
            when: When to use it (trigger condition)
            category: One of 'understand', 'preflight', 'single_turn_process'
            allowed_tools: Claude's allowed-tools field (comma-separated)
            model: Claude's model field
            context: "fork" to run in subagent
            agent: Subagent type when context=fork (e.g. "Explore", "Plan")
            hooks: PreToolUse/PostToolUse scoped to this skill
            user_invocable: Show in / menu (default true)
            disable_model_invocation: Prevent auto-invoke (default false)
            argument_hint: Autocomplete hint e.g. "[issue-number]"
            describes_component: GIINT component path
        """
        logger.info(f"Creating skill: {name} in {domain}::{subdomain or ''} (category={category})")

        # Validate native Claude field constraints
        if context == "fork" and not agent:
            return {"error": f"Skill '{name}': context='fork' requires 'agent' to be set (e.g. 'Explore', 'Plan', 'general-purpose')"}
        if agent and context != "fork":
            return {"error": f"Skill '{name}': 'agent' requires context='fork' to be set"}

        skill_dir = self._skill_path(name)
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Create resource directories
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "templates").mkdir(exist_ok=True)

        # Build description from typed fields
        description = self._build_description(what, when)

        # Build frontmatter dict with only non-None fields
        fm = {"name": name, "description": description}
        if allowed_tools: fm["allowed-tools"] = allowed_tools
        if model: fm["model"] = model
        if context: fm["context"] = context
        if agent: fm["agent"] = agent
        if hooks: fm["hooks"] = hooks
        if user_invocable is not None: fm["user-invocable"] = user_invocable
        if disable_model_invocation is not None: fm["disable-model-invocation"] = disable_model_invocation
        if argument_hint: fm["argument-hint"] = argument_hint

        # Write SKILL.md with proper YAML frontmatter
        frontmatter_str = yaml.dump(fm, default_flow_style=False, sort_keys=False).strip()
        skill_md = f"---\n{frontmatter_str}\n---\n\n# {name.replace('-', ' ').replace('_', ' ').title()}\n\n{content}\n"
        (skill_dir / "SKILL.md").write_text(skill_md)

        # Write empty reference.md
        (skill_dir / "reference.md").write_text(f"# {name} Reference\n\nAdd extended documentation here.\n")

        # Write GNOSYS extensions to _metadata.json
        metadata = {
            "domain": domain,
            "subdomain": subdomain,
            "category": category,
            "what": what,
            "when": when,
            "describes_component": describes_component
        }
        self._metadata_path(name).write_text(json.dumps(metadata, indent=2))

        # Index in ChromaDB
        self._index_skill(name, domain, subdomain, description, content, category)

        skill = Skill(name=name, domain=domain, subdomain=subdomain,
                      content=content, description=description,
                      what=what, when=when,
                      category=category, allowed_tools=allowed_tools, model=model,
                      describes_component=describes_component, starsystem=starsystem)

        # Scan resources for CartON sync
        resources = self._scan_resources(skill_dir)

        # Sync to CartON with FULL ontology matching Skill_Template
        self._sync_skill_to_carton(name, domain, category, description,
                                    describes_component=describes_component, starsystem=starsystem,
                                    what=what, when=when, subdomain=subdomain,
                                    content=content, resources=resources,
                                    context=context, agent=agent, hooks=hooks,
                                    user_invocable=user_invocable, disable_model_invocation=disable_model_invocation,
                                    argument_hint=argument_hint, allowed_tools=allowed_tools,
                                    model=model)

        return {
            "skill": skill,
            "path": str(skill_dir),
            "structure": {
                "SKILL.md": "main content (body is HOW for preflight)",
                "scripts/": "add executable scripts here",
                "templates/": "add reusable templates here",
                "reference.md": "add extended documentation here"
            }
        }

    def _index_skill(self, name: str, domain: str, subdomain: Optional[str],
                     description: str, content: str, category: Optional[str] = None):
        """Add skill to RAG index with separate short/long embeddings."""
        # Short embedding: name + domain + category (high signal for exact/near matches)
        short_text = f"{name} {domain} {subdomain or ''} {category or ''} {description[:200]}"
        self.collection.upsert(
            ids=[f"skill:{name}"],
            documents=[short_text],
            metadatas=[{"name": name, "domain": domain, "subdomain": subdomain or "",
                        "type": "skill", "category": category or "",
                        "description": description[:500]}]
        )
        # Long embedding: full content (for semantic discovery of concepts within skill)
        if content and len(content) > 100:
            self.collection.upsert(
                ids=[f"skill-content:{name}"],
                documents=[content[:2000]],
                metadatas=[{"name": name, "domain": domain, "subdomain": subdomain or "",
                            "type": "skill-content", "category": category or ""}]
            )

    def _sync_skill_to_carton(self, name: str, domain: str, category: Optional[str],
                               description: str, describes_component: Optional[str] = None,
                               starsystem: Optional[str] = None,
                               what: Optional[str] = None, when: Optional[str] = None,
                               subdomain: Optional[str] = None,
                               content: Optional[str] = None,
                               context: Optional[str] = None, agent: Optional[str] = None,
                               hooks: Optional[dict] = None, user_invocable: Optional[bool] = None,
                               disable_model_invocation: Optional[bool] = None,
                               argument_hint: Optional[str] = None,
                               allowed_tools: Optional[str] = None,
                               model: Optional[str] = None,
                               requires: Optional[list] = None,
                               resources: Optional[dict] = None):
        """Sync skill to CartON knowledge graph with FULL ontology matching Skill_Template.

        Writes relationships matching the Has_* ontology types from bootstrap_ontology_types().
        """
        try:
            from carton_mcp.add_concept_tool import add_concept_tool_func

            # Determine category and domain concepts
            domain_concept = (domain or "PAIAB").replace("-", "_").replace(" ", "_").title()
            category_str = category or "understand"
            category_concept = f"Skill_Category_{category_str.replace('-', '_').title()}"

            relationships = [
                {"relationship": "is_a", "related": ["Skill"]},
                {"relationship": "instantiates", "related": [f"Skill_{category_str.replace('-', '_').title()}_Pattern"]},
                {"relationship": "part_of", "related": [domain_concept]},
                {"relationship": "has_category", "related": [category_concept]},
                {"relationship": "has_personal_domain", "related": ["paiab"]},
                {"relationship": "has_domain", "related": [domain_concept]},
            ]

            # SkillSpec fields: what, when, subdomain
            if what:
                what_concept = f"What_{name.replace('-', '_').title()}"
                relationships.append({"relationship": "has_what", "related": [what_concept]})
            if when:
                when_concept = f"When_{name.replace('-', '_').title()}"
                relationships.append({"relationship": "has_when", "related": [when_concept]})
            if subdomain:
                subdomain_concept = subdomain.replace("-", "_").replace(" ", "_").title()
                relationships.append({"relationship": "has_subdomain", "related": [subdomain_concept]})

            # Content + file structure
            if content:
                import hashlib
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
                relationships.append({"relationship": "has_content", "related": [f"Content_{content_hash}"]})

            if resources:
                if resources.get("reference") and resources["reference"] != "empty":
                    relationships.append({"relationship": "has_reference", "related": [f"Reference_{name.replace('-', '_').title()}"]})
                if resources.get("scripts"):
                    for script in resources["scripts"]:
                        script_concept = f"Script_{script.replace('.', '_').replace('-', '_').title()}"
                        relationships.append({"relationship": "has_scripts", "related": [script_concept]})
                if resources.get("templates"):
                    for tmpl in resources["templates"]:
                        tmpl_concept = f"Template_{tmpl.replace('.', '_').replace('-', '_').title()}"
                        relationships.append({"relationship": "has_templates", "related": [tmpl_concept]})

            # GIINT component link
            if describes_component:
                parts = describes_component.split("/")
                if len(parts) >= 3:
                    component_concept = f"GIINT_Component_{parts[0]}_{parts[1]}_{parts[2]}"
                else:
                    component_concept = f"GIINT_Component_{describes_component.replace('/', '_')}"
                relationships.append({"relationship": "has_describes_component", "related": [component_concept]})

            # Starsystem link
            if starsystem:
                if starsystem.startswith("/"):
                    starsystem_name = f"Starsystem_{starsystem.strip('/').replace('/', '_').replace('-', '_').title()}"
                else:
                    starsystem_name = starsystem
                relationships.append({"relationship": "has_starsystem", "related": [starsystem_name]})
                # Override part_of to starsystem (more specific container)
                relationships = [r for r in relationships if not (r["relationship"] == "part_of" and r["related"] == [domain_concept])]
                relationships.append({"relationship": "part_of", "related": [starsystem_name]})

            # Skill dependencies
            if requires:
                for req in requires:
                    req_concept = f"Skill_{req.replace('-', '_').title()}"
                    relationships.append({"relationship": "has_requires", "related": [req_concept]})

            # Claude Code integration fields as typed relationships
            if allowed_tools:
                relationships.append({"relationship": "has_allowed_tools", "related": [f"Tools_{allowed_tools.replace(', ', '_').replace(' ', '_')}"]})
            if model:
                relationships.append({"relationship": "has_model", "related": [f"Model_{model.replace('-', '_').title()}"]})
            if context:
                relationships.append({"relationship": "has_context_mode", "related": [f"Context_Mode_{context.title()}"]})
            if agent:
                relationships.append({"relationship": "has_agent_type", "related": [f"Agent_Type_{agent.replace('-', '_').title()}"]})
            if hooks:
                for hook_type in hooks:
                    relationships.append({"relationship": "has_hook", "related": [f"Hook_Type_{hook_type}"]})
            if user_invocable is False:
                relationships.append({"relationship": "has_user_invocable", "related": ["User_Invocable_False"]})
            if disable_model_invocation is True:
                relationships.append({"relationship": "has_disable_model_invocation", "related": ["Disable_Model_Invocation_True"]})
            if argument_hint:
                relationships.append({"relationship": "has_argument_hint", "related": [f"Argument_Hint_{argument_hint.strip('[]').replace(' ', '_').title()}"]})

            concept_name = f"Skill_{name.replace('-', '_').title()}"
            concept_desc = f"Skill: {name}\n\n{description}"
            if what:
                concept_desc += f"\n\nWHAT: {what}"
            if when:
                concept_desc += f"\nWHEN: {when}"

            add_concept_tool_func(concept_name, concept_desc, relationships, hide_youknow=False)
            logger.info(f"Synced skill {name} to CartON" + (f" with DESCRIBES {describes_component}" if describes_component else ""))

        except Exception as e:
            logger.warning(f"Could not sync skill {name} to CartON: {e}")

    def _scan_resources(self, skill_dir: Path) -> dict:
        """Scan skill directory for resources."""
        resources = {
            "scripts": [],
            "templates": [],
            "reference": None
        }

        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            resources["scripts"] = [f.name for f in scripts_dir.iterdir() if f.is_file()]

        templates_dir = skill_dir / "templates"
        if templates_dir.exists():
            resources["templates"] = [f.name for f in templates_dir.iterdir() if f.is_file()]

        reference_path = skill_dir / "reference.md"
        if reference_path.exists():
            size = reference_path.stat().st_size
            resources["reference"] = f"{size} bytes" if size > 50 else "empty"

        return resources

    def get_skill(self, name: str) -> Optional[dict]:
        """Get a skill from global catalog with resource info."""
        skill_md_path = self._skill_md_path(name)
        if not skill_md_path.exists():
            return None

        content = skill_md_path.read_text()
        parsed = self._parse_skill_md(content)

        # Defaults
        domain, subdomain, category = "unknown", None, None
        what, when = "", ""
        describes_component = None
        requires = None

        # Load GNOSYS extensions from _metadata.json
        if self._metadata_path(name).exists():
            meta = json.loads(self._metadata_path(name).read_text())
            domain = meta.get("domain", "unknown")
            subdomain = meta.get("subdomain")
            category = meta.get("category")
            what = meta.get("what", "")
            when = meta.get("when", "")
            describes_component = meta.get("describes_component")
            requires = meta.get("requires")

        skill = Skill(
            name=parsed["name"] or name,
            description=parsed["description"],
            allowed_tools=parsed.get("allowed_tools"),
            model=parsed.get("model"),
            context=parsed.get("context"),
            agent=parsed.get("agent"),
            hooks=parsed.get("hooks"),
            user_invocable=parsed.get("user_invocable"),
            disable_model_invocation=parsed.get("disable_model_invocation"),
            argument_hint=parsed.get("argument_hint"),
            domain=domain,
            subdomain=subdomain,
            category=category,
            what=what,
            when=when,
            requires=requires,
            describes_component=describes_component,
            content=parsed["body"]
        )

        skill_dir = self._skill_path(name)
        resources = self._scan_resources(skill_dir)

        return {
            "skill": skill,
            "path": str(skill_dir),
            "resources": resources
        }

    def list_skills(self) -> list[dict]:
        """List all skills in global catalog."""
        skills = []
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                result = self.get_skill(skill_dir.name)
                if result:
                    skill = result["skill"]
                    skills.append({
                        "name": skill.name,
                        "domain": skill.domain,
                        "subdomain": skill.subdomain,
                        "description": skill.description,
                        "category": skill.category
                    })
        return skills

    def list_domains(self) -> list[str]:
        """List all available domains."""
        skills = self.list_skills()
        skillsets = self.list_skillsets()
        domains = set(s["domain"] for s in skills)
        domains.update(ss["domain"] for ss in skillsets)
        return sorted(domains)

    def list_by_domain(self, domain: str) -> dict:
        """List all skills and skillsets in a domain."""
        skills = [s for s in self.list_skills() if s["domain"] == domain]
        skillsets = [ss for ss in self.list_skillsets() if ss["domain"] == domain]
        return {"domain": domain, "skills": skills, "skillsets": skillsets}

    # === Claude skills directory mirroring ===

    # Agents whose equipped skills should be mirrored to ~/.claude/skills/
    CLAUDE_MIRROR_AGENTS = {None, "gnosys", "claude"}

    def _mirror_to_claude(self, name: str):
        """Copy skill to Claude's native skills dir for hot-reload pickup.

        Only mirrors for Claude Code (agent_id=None) or agents 'gnosys'/'claude'.
        Other agents don't use Claude's native skill dir.
        """
        if self.agent_id not in self.CLAUDE_MIRROR_AGENTS:
            return
        src = self._skill_path(name)
        dst = CLAUDE_SKILLS_DIR / name
        if src.exists():
            CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            logger.info(f"Mirrored skill to Claude: {dst}")

    def _remove_from_claude(self, name: str):
        """Remove skill from Claude's native skills dir."""
        dst = CLAUDE_SKILLS_DIR / name
        if dst.exists():
            shutil.rmtree(dst)
            logger.info(f"Removed skill from Claude: {dst}")

    # === Defaults and sync ===

    def _load_defaults(self) -> list[str]:
        """Load default skill names from config."""
        if not self.defaults_file.exists():
            return []
        try:
            data = json.loads(self.defaults_file.read_text())
            return data.get("defaults", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def _load_equipped_state(self) -> list[str]:
        """Load persisted equipped skill names."""
        if not self.equipped_file.exists():
            return []
        try:
            data = json.loads(self.equipped_file.read_text())
            return data.get("equipped", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_equipped_state(self):
        """Persist current equipped skill names to file."""
        data = {"equipped": list(self.equipped.keys())}
        self.equipped_file.write_text(json.dumps(data, indent=2))

    def _load_persona_state(self):
        """Load persisted active persona on startup."""
        if not self._persona_file.exists():
            return
        try:
            data = json.loads(self._persona_file.read_text())
            name = data.get("name")
            if name:
                persona = self.get_persona(name)
                if persona:
                    self.active_persona = persona
                    self._try_equip_skillset_for_persona(persona, {
                        "missing": [], "equipped_skills": []
                    })
                    logger.info(f"Restored persisted persona: {name}")
        except (json.JSONDecodeError, KeyError):
            pass

    def _save_persona_state(self):
        """Persist active persona name to file."""
        if self.active_persona:
            self._persona_file.write_text(json.dumps(
                {"name": self.active_persona.name}, indent=2
            ))
        elif self._persona_file.exists():
            self._persona_file.unlink()

    def _quarantine_skill(self, name: str, source: str, reason: str = "duplicate"):
        """Move skill to quarantine with metadata."""
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_path = self.quarantine_dir / f"{name}_{timestamp}"

        # Determine source path
        if source == "claude":
            src = CLAUDE_SKILLS_DIR / name
        else:
            src = self.skills_dir / name

        if not src.exists():
            logger.warning(f"Cannot quarantine {name}: source {src} does not exist")
            return

        # Copy to quarantine
        shutil.copytree(src, quarantine_path)

        # Write metadata
        metadata = {
            "source": source,
            "original_name": name,
            "reason": reason,
            "timestamp": timestamp,
            "original_path": str(src)
        }
        (quarantine_path / "_quarantine_metadata.json").write_text(json.dumps(metadata, indent=2))
        logger.info(f"Quarantined skill: {name} from {source} -> {quarantine_path}")

    def list_quarantine(self) -> list[dict]:
        """List all quarantined skills."""
        if not self.quarantine_dir.exists():
            return []

        quarantined = []
        for p in self.quarantine_dir.iterdir():
            if p.is_dir():
                meta_path = p / "_quarantine_metadata.json"
                if meta_path.exists():
                    try:
                        metadata = json.loads(meta_path.read_text())
                        quarantined.append({
                            "path": str(p),
                            "metadata": metadata
                        })
                    except json.JSONDecodeError:
                        quarantined.append({
                            "path": str(p),
                            "metadata": {"error": "invalid metadata"}
                        })
        return quarantined

    def reindex_all(self) -> dict:
        """Re-index ALL skills with current dual-embed format. Call after RAG schema changes."""
        count = 0
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            try:
                skill = self.get_skill(skill_dir.name)
                if skill:
                    self._index_skill(
                        skill.get("name", skill_dir.name),
                        skill.get("domain", "unknown"),
                        skill.get("subdomain", ""),
                        skill.get("description", ""),
                        skill.get("content", ""),
                        category=skill.get("category", "")
                    )
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to reindex {skill_dir.name}: {e}")
        return {"reindexed": count}

    def sync_on_startup(self):
        """Sync equipped state on startup.

        For agent-scoped instances (agent_id set): only load agent's own equipped file.
        For Claude Code (no agent_id): full sync with ~/.claude/skills/ dir.
        """
        if self.agent_id:
            # Agent-scoped: just load this agent's equipped state, no Claude dir sync
            persisted = set(self._load_equipped_state())
            for skill_name in persisted:
                if skill_name not in self.equipped:
                    result = self.get_skill(skill_name)
                    if result:
                        self.equipped[skill_name] = result["skill"]
            logger.info(f"Agent {self.agent_id}: equipped {len(self.equipped)} skills from persisted state")
            return

        # Claude Code path: full sync with ~/.claude/skills/
        CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        claude_skills = set(
            d.name for d in CLAUDE_SKILLS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ) if CLAUDE_SKILLS_DIR.exists() else set()

        heaven_skills = set(
            d.name for d in self.skills_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

        defaults = set(self._load_defaults())

        logger.info(f"Sync on startup: claude={len(claude_skills)}, heaven={len(heaven_skills)}, defaults={len(defaults)}")

        for skill in claude_skills:
            if skill not in heaven_skills:
                src = CLAUDE_SKILLS_DIR / skill
                dst = self.skills_dir / skill
                shutil.copytree(src, dst)
                logger.info(f"Synced new skill from claude to heaven: {skill}")
                self._try_index_skill(skill)
            elif skill not in defaults:
                self._quarantine_skill(skill, source="claude", reason="duplicate")

        for skill in claude_skills:
            if skill not in defaults:
                skill_path = CLAUDE_SKILLS_DIR / skill
                if skill_path.is_symlink():
                    skill_path.unlink()
                    logger.info(f"Removed symlink skill from claude: {skill}")
                elif skill_path.exists():
                    shutil.rmtree(skill_path)
                    logger.info(f"Removed non-default skill from claude: {skill}")

        for skill in defaults:
            if skill in heaven_skills:
                self._mirror_to_claude(skill)

        persisted = set(self._load_equipped_state())
        all_to_equip = defaults | persisted
        for skill_name in all_to_equip:
            if skill_name not in self.equipped:
                result = self.get_skill(skill_name)
                if result:
                    self.equipped[skill_name] = result["skill"]
        self._save_equipped_state()
        logger.info(f"Equipped {len(self.equipped)} skills on startup")

    def _try_index_skill(self, name: str):
        """Try to index a skill that was synced from claude."""
        result = self.get_skill(name)
        if result:
            skill = result["skill"]
            self._index_skill(
                name, skill.domain, skill.subdomain,
                skill.description, skill.content, skill.category
            )

    # === Equipped state ===

    def equip(self, name: str, _resolving: set = None) -> dict:
        """Equip a skill or skillset. Auto-resolves understand skill dependencies."""
        if _resolving is None:
            _resolving = set()

        if name in _resolving:
            return {"skipped": name, "reason": "circular dependency"}
        _resolving.add(name)

        # Try as skillset first
        skillset = self.get_skillset(name)
        if skillset:
            return self.equip_skillset(name)

        # Try as skill
        result = self.get_skill(name)
        if result:
            skill = result["skill"]

            # Auto-resolve dependencies first
            deps_equipped = []
            if skill.requires:
                for dep in skill.requires:
                    if dep not in self.equipped:
                        dep_result = self.equip(dep, _resolving)
                        if "equipped" in dep_result:
                            deps_equipped.append(dep)
                        elif "error" in dep_result:
                            logger.warning(f"Dependency '{dep}' for '{name}' not found")

            self.equipped[name] = skill
            self._mirror_to_claude(name)
            self._save_equipped_state()
            logger.info(f"Equipped skill: {name}")
            result_dict = {"equipped": name, "type": "skill", "domain": skill.domain}
            if deps_equipped:
                result_dict["deps_equipped"] = deps_equipped
            return result_dict

        return {"error": f"'{name}' not found as skill or skillset"}

    def equip_skillset(self, name: str) -> dict:
        """Equip all skills in a skillset."""
        skillset = self.get_skillset(name)
        if not skillset:
            return {"error": f"Skillset '{name}' not found"}

        equipped_names = []
        for skill_name in skillset.skills:
            result = self.get_skill(skill_name)
            if result:
                self.equipped[skill_name] = result["skill"]
                self._mirror_to_claude(skill_name)
                equipped_names.append(skill_name)

        self._save_equipped_state()
        logger.info(f"Equipped skillset: {name} ({len(equipped_names)} skills)")
        return {
            "equipped": name,
            "type": "skillset",
            "domain": skillset.domain,
            "skills": equipped_names
        }

    def unequip(self, name: str) -> dict:
        """Unequip a skill."""
        if name in self.equipped:
            del self.equipped[name]
            self._remove_from_claude(name)
            self._save_equipped_state()
            return {"unequipped": name}
        return {"error": f"'{name}' not equipped"}

    def unequip_all(self) -> dict:
        """Clear all equipped skills."""
        count = len(self.equipped)
        for name in list(self.equipped.keys()):
            self._remove_from_claude(name)
        self.equipped.clear()
        self._save_equipped_state()
        return {"unequipped_count": count}

    def list_equipped(self) -> list[dict]:
        """List currently equipped skills."""
        return [
            {
                "name": s.name,
                "domain": s.domain,
                "subdomain": s.subdomain,
                "description": s.description
            }
            for s in self.equipped.values()
        ]

    def get_equipped_content(self) -> str:
        """Get full content of all equipped skills."""
        if not self.equipped:
            return "No skills equipped."

        lines = []
        for skill in self.equipped.values():
            lines.append(f"## {skill.name} ({skill.domain}::{skill.subdomain or ''})")
            lines.append(skill.content)
            lines.append("")
        return "\n".join(lines)

    # === RAG search ===

    def search_skills(self, query: str, n_results: int = 5,
                      category: Optional[str] = None) -> list[dict]:
        """Multi-strategy skill search: exact name → metadata-filtered semantic → broad."""
        seen = {}  # name → match dict (dedup, keep highest score)

        def _add_matches(results, score_boost=0.0):
            if not (results["ids"] and results["ids"][0]):
                return
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 1.0
                score = (1 - dist) + score_boost
                if score < 0.2:
                    continue  # threshold: skip garbage
                name = meta.get("name", doc_id.split(":", 1)[-1])
                if name not in seen or score > seen[name]["score"]:
                    seen[name] = {
                        "name": name, "domain": meta.get("domain", "unknown"),
                        "subdomain": meta.get("subdomain", ""),
                        "type": meta.get("type", "skill"),
                        "category": meta.get("category", ""), "score": round(score, 2)
                    }

        where_filter = {"category": category} if category else None
        query_lower = query.lower().strip()

        # L0: Exact name match (check if query IS a skill name)
        try:
            exact = self.collection.get(ids=[f"skill:{query_lower}"])
            if exact["ids"]:
                meta = exact["metadatas"][0] if exact["metadatas"] else {}
                seen[query_lower] = {
                    "name": meta.get("name", query_lower), "domain": meta.get("domain", "unknown"),
                    "subdomain": meta.get("subdomain", ""), "type": "skill",
                    "category": meta.get("category", ""), "score": 1.0
                }
        except Exception:
            pass

        # L1: Semantic search on short embeddings (name+domain+category)
        _add_matches(self.collection.query(
            query_texts=[query], n_results=n_results,
            where={"type": "skill", **({"category": category} if category else {})}
        ), score_boost=0.05)

        # L2: Semantic search on content embeddings (broader discovery)
        if len(seen) < n_results:
            _add_matches(self.collection.query(
                query_texts=[query], n_results=n_results,
                where={"type": "skill-content", **({"category": category} if category else {})}
            ))

        return sorted(seen.values(), key=lambda m: m["score"], reverse=True)[:n_results]

    def browse_skills(self, category: Optional[str] = None,
                      domain: Optional[str] = None,
                      subdomain: Optional[str] = None,
                      query: Optional[str] = None,
                      page: int = 1,
                      page_size: int = 10) -> dict:
        """Faceted skill navigation — progressive drill-down with optional semantic refinement.

        Call with no args to see categories. Add category to see domains. Add domain to see
        subdomains. Add subdomain to see the full paginated skill list. Add query at any
        drill-down level to get semantic matches scoped to that level.

        The key insight: LLMs are better at reading categories and making routing decisions
        than small embedding models are at matching task descriptions to skill metadata.
        Progressive disclosure lets the LLM narrow the search space before semantic search
        fires in a small, specific corpus where it can actually work.
        """
        all_skills = self.list_skills()

        # --- Level 0: Show categories with counts ---
        if category is None and domain is None and subdomain is None and query is None:
            cats = {}
            for s in all_skills:
                cat = s.get("category") or "uncategorized"
                if cat not in cats:
                    cats[cat] = {"count": 0, "domains": set()}
                cats[cat]["count"] += 1
                cats[cat]["domains"].add(s.get("domain", "unknown"))

            return {
                "level": "categories",
                "hint": "Pick a category to see its domains. Categories: understand (knowledge), preflight (pre-checks), single_turn_process (procedures).",
                "categories": {
                    cat: {"skill_count": info["count"], "domain_count": len(info["domains"])}
                    for cat, info in sorted(cats.items())
                },
                "total_skills": len(all_skills)
            }

        # Filter by category if given
        if category:
            all_skills = [s for s in all_skills if (s.get("category") or "uncategorized") == category]

        # --- Level 1: Show domains within the filtered set ---
        if domain is None and subdomain is None and query is None:
            domains = {}
            for s in all_skills:
                d = s.get("domain", "unknown")
                if d not in domains:
                    domains[d] = {"count": 0, "subdomains": set()}
                domains[d]["count"] += 1
                sd = s.get("subdomain")
                if sd:
                    domains[d]["subdomains"].add(sd)

            return {
                "level": "domains",
                "category": category,
                "hint": "Pick a domain to see its subdomains and skills.",
                "domains": {
                    d: {"skill_count": info["count"],
                        "subdomains": sorted(info["subdomains"]) if info["subdomains"] else []}
                    for d, info in sorted(domains.items())
                },
                "total_in_category": len(all_skills)
            }

        # Filter by domain if given
        if domain:
            all_skills = [s for s in all_skills if s.get("domain") == domain]

        # --- Level 2: Show subdomains within domain ---
        if subdomain is None and query is None:
            subs = {}
            no_sub = []
            for s in all_skills:
                sd = s.get("subdomain")
                if sd:
                    if sd not in subs:
                        subs[sd] = []
                    subs[sd].append(s["name"])
                else:
                    no_sub.append(s["name"])

            return {
                "level": "subdomains",
                "category": category,
                "domain": domain,
                "hint": "Pick a subdomain to see all skills, or add a query for semantic search within this domain.",
                "subdomains": {
                    sd: {"skill_count": len(names), "skills": sorted(names)}
                    for sd, names in sorted(subs.items())
                },
                "no_subdomain": sorted(no_sub) if no_sub else [],
                "total_in_domain": len(all_skills)
            }

        # Filter by subdomain if given
        if subdomain:
            all_skills = [s for s in all_skills if s.get("subdomain") == subdomain]

        # --- Level 3: Paginated skill list + optional semantic search ---

        # Semantic search results (scoped to current filters)
        recommended = []
        if query:
            # Build where filter for ChromaDB scoped to current drill-down
            where_parts = {"type": "skill"}
            if category:
                where_parts["category"] = category
            if domain:
                where_parts["domain"] = domain
            if subdomain:
                where_parts["subdomain"] = subdomain

            # Use $and for multi-field filter if needed
            if len(where_parts) > 1:
                where_filter = {"$and": [{k: v} for k, v in where_parts.items()]}
            else:
                where_filter = where_parts

            try:
                results = self.collection.query(
                    query_texts=[query], n_results=5,
                    where=where_filter
                )
                if results["ids"] and results["ids"][0]:
                    for i, doc_id in enumerate(results["ids"][0]):
                        meta = results["metadatas"][0][i] if results["metadatas"] else {}
                        dist = results["distances"][0][i] if results["distances"] else 1.0
                        score = round(1 - dist, 2)
                        if score >= 0.2:
                            recommended.append({
                                "name": meta.get("name", doc_id.split(":", 1)[-1]),
                                "score": score,
                                "domain": meta.get("domain", ""),
                                "subdomain": meta.get("subdomain", ""),
                                "category": meta.get("category", "")
                            })
            except Exception as e:
                logger.warning(f"Browse semantic search failed: {e}")

        # Paginate the full list at this level
        total = len(all_skills)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = start + page_size
        page_skills = all_skills[start:end]

        # Enrich page_skills with what/when from description
        enriched = []
        for s in page_skills:
            entry = {"name": s["name"], "domain": s.get("domain", ""),
                     "subdomain": s.get("subdomain", ""), "category": s.get("category", "")}
            desc = s.get("description", "")
            if desc:
                # Parse WHAT/WHEN from description
                for line in desc.split("\n"):
                    if line.startswith("WHAT:"):
                        entry["what"] = line[5:].strip()
                    elif line.startswith("WHEN:"):
                        entry["when"] = line[5:].strip()
                if "what" not in entry:
                    entry["what"] = desc[:100]
            enriched.append(entry)

        result = {
            "level": "skills",
            "category": category,
            "domain": domain,
            "subdomain": subdomain,
            "query": query,
            "total_skills": total,
            "page": page,
            "total_pages": total_pages,
            "skills": enriched,
        }

        if recommended:
            result["recommended"] = recommended
            result["hint"] = "★ = semantic match. Full list below. Use equip(name) to load a skill."
        else:
            result["hint"] = "All skills at this level. Use equip(name) to load a skill."

        return result

    def _parse_skilllog_prediction(self, prediction: str) -> dict:
        """Parse SkillLog prediction into components."""
        parts = prediction.split("::")
        return {
            "domain": parts[0] if parts else "",
            "subdomain": parts[1] if len(parts) > 1 else "",
            "specific": parts[2] if len(parts) > 2 else ""
        }

    def match_skilllog(self, prediction: str) -> dict:
        """Match a SkillLog prediction against catalog."""
        logger.info(f"Matching SkillLog: {prediction}")
        parsed = self._parse_skilllog_prediction(prediction)
        query = f"{parsed['domain']} {parsed['subdomain']} {parsed['specific']}".strip()

        matches = self.search_skills(query, n_results=5)
        exact_domain = [m for m in matches if m["domain"] == parsed["domain"]]

        return {
            "prediction": prediction,
            "parsed": parsed,
            "matches": matches,
            "exact_domain_matches": exact_domain,
            "available_domains": self.list_domains(),
            "has_match": len(matches) > 0 and matches[0]["score"] > 0.5
        }

    # === Skillset management ===

    def _load_skillsets(self) -> dict[str, Skillset]:
        if not self.skillsets_file.exists():
            return {}
        data = json.loads(self.skillsets_file.read_text())
        return {name: Skillset(**ss) for name, ss in data.items()}

    def _save_skillsets(self, skillsets: dict[str, Skillset]):
        data = {name: ss.model_dump() for name, ss in skillsets.items()}
        self.skillsets_file.write_text(json.dumps(data, indent=2))

    def create_skillset(self, name: str, domain: str, description: str,
                        skills: list[str], subdomain: Optional[str] = None) -> Skillset:
        """Create a skillset with domain and index with aggregated member domains."""
        logger.info(f"Creating skillset: {name} in {domain}::{subdomain or ''}")

        skillsets = self._load_skillsets()
        ss = Skillset(name=name, domain=domain, subdomain=subdomain,
                      description=description, skills=skills)
        skillsets[name] = ss
        self._save_skillsets(skillsets)

        # Index with aggregated domains from member skills
        self._index_skillset(ss)

        return ss

    def _index_skillset(self, ss: Skillset):
        """Index skillset with its own domain + all member skill domains."""
        # Start with skillset's own domain
        search_parts = [ss.domain, ss.subdomain or "", ss.name, ss.description]

        # Add all member skill domains
        for skill_name in ss.skills:
            result = self.get_skill(skill_name)
            if result:
                skill = result["skill"]
                search_parts.extend([skill.domain, skill.subdomain or "", skill.name])

        search_text = " ".join(search_parts)
        doc_id = f"skillset:{ss.name}"

        self.collection.upsert(
            ids=[doc_id],
            documents=[search_text],
            metadatas=[{"name": ss.name, "domain": ss.domain,
                        "subdomain": ss.subdomain or "", "type": "skillset"}]
        )

    def get_skillset(self, name: str) -> Optional[Skillset]:
        skillsets = self._load_skillsets()
        return skillsets.get(name)

    def list_skillsets(self) -> list[dict]:
        skillsets = self._load_skillsets()
        return [
            {
                "name": ss.name,
                "domain": ss.domain,
                "subdomain": ss.subdomain,
                "description": ss.description,
                "skill_count": len(ss.skills)
            }
            for ss in skillsets.values()
        ]

    def add_to_skillset(self, skillset_name: str, skill_name: str) -> dict:
        """Add a skill to a skillset and reindex."""
        skillsets = self._load_skillsets()
        if skillset_name not in skillsets:
            return {"error": f"Skillset '{skillset_name}' not found"}

        ss = skillsets[skillset_name]
        if skill_name not in ss.skills:
            ss.skills.append(skill_name)
            self._save_skillsets(skillsets)
            self._index_skillset(ss)  # Reindex with new skill

        return {"success": True, "skillset": skillset_name, "skills": ss.skills}

    # === Persona management ===

    def _load_personas(self) -> dict[str, Persona]:
        if not self.personas_file.exists():
            return {}
        data = json.loads(self.personas_file.read_text())
        return {name: Persona(**p) for name, p in data.items()}

    def _save_personas(self, personas: dict[str, Persona]):
        data = {name: p.model_dump() for name, p in personas.items()}
        self.personas_file.write_text(json.dumps(data, indent=2))

    def create_persona(self, name: str, domain: str, description: str, frame: str,
                       mcp_set: Optional[str] = None, skillset: Optional[str] = None,
                       carton_identity: Optional[str] = None,
                       subdomain: Optional[str] = None) -> Persona:
        """Create a persona with aspirational MCP set, skillset, and identity."""
        logger.info(f"Creating persona: {name} in {domain}::{subdomain or ''}")

        personas = self._load_personas()
        persona = Persona(
            name=name, domain=domain, subdomain=subdomain,
            description=description, frame=frame,
            mcp_set=mcp_set, skillset=skillset,
            carton_identity=carton_identity or name
        )
        personas[name] = persona
        self._save_personas(personas)

        # Index persona in RAG
        self._index_persona(persona)

        return persona

    def _index_persona(self, p: Persona):
        """Index persona for RAG search."""
        search_text = f"persona {p.domain} {p.subdomain or ''} {p.name} {p.description} {p.frame}"
        doc_id = f"persona:{p.name}"
        self.collection.upsert(
            ids=[doc_id],
            documents=[search_text],
            metadatas=[{"name": p.name, "domain": p.domain,
                        "subdomain": p.subdomain or "", "type": "persona"}]
        )

    def get_persona(self, name: str) -> Optional[Persona]:
        personas = self._load_personas()
        return personas.get(name)

    def list_personas(self) -> list[dict]:
        personas = self._load_personas()
        return [
            {
                "name": p.name,
                "domain": p.domain,
                "subdomain": p.subdomain,
                "description": p.description,
                "mcp_set": p.mcp_set,
                "skillset": p.skillset,
                "carton_identity": p.carton_identity
            }
            for p in personas.values()
        ]

    def _try_equip_skillset_for_persona(self, persona: Persona, report: dict):
        """Attempt to equip persona's skillset, update report with status."""
        if not persona.skillset:
            return
        skillset = self.get_skillset(persona.skillset)
        if skillset:
            equip_result = self.equip_skillset(persona.skillset)
            report["skillset"] = "equipped"
            report["equipped_skills"] = equip_result.get("skills", [])
        else:
            report["missing"].append({
                "type": "skillset",
                "name": persona.skillset,
                "suggestion": f"Create skillset '{persona.skillset}' with create_skillset()"
            })

    def _build_mcp_set_status(self, persona: Persona) -> Optional[dict]:
        """Build MCP set status for persona report."""
        if not persona.mcp_set:
            return None
        return {
            "name": persona.mcp_set,
            "status": "requires_strata",
            "action": f"Use strata: connect_set('{persona.mcp_set}')"
        }

    def equip_persona(self, name: str) -> dict:
        """Equip a persona - activate frame, attempt MCP set and skillset."""
        persona = self.get_persona(name)
        if not persona:
            return {"error": f"Persona '{name}' not found"}

        logger.info(f"Equipping persona: {name}")

        report = {
            "persona": name,
            "frame": "loaded",
            "frame_content": persona.frame,
            "mcp_set": None,
            "skillset": None,
            "carton_identity": persona.carton_identity,
            "missing": [],
            "equipped_skills": []
        }

        self._try_equip_skillset_for_persona(persona, report)
        report["mcp_set"] = self._build_mcp_set_status(persona)

        self.active_persona = persona
        self._save_persona_state()
        return report

    def get_active_persona(self) -> Optional[dict]:
        """Get the currently active persona."""
        if not self.active_persona:
            return None
        return {
            "name": self.active_persona.name,
            "domain": self.active_persona.domain,
            "frame": self.active_persona.frame,
            "mcp_set": self.active_persona.mcp_set,
            "skillset": self.active_persona.skillset,
            "carton_identity": self.active_persona.carton_identity
        }

    def deactivate_persona(self) -> dict:
        """Deactivate current persona and unequip all skills."""
        if not self.active_persona:
            return {"status": "no active persona"}

        name = self.active_persona.name
        self.active_persona = None
        self._save_persona_state()
        self.unequip_all()
        return {"deactivated": name, "skills_unequipped": True}
