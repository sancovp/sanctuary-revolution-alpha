"""Main STARLOG singleton class combining all functionality."""

import os
import json
import logging
import traceback
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Import Heaven registry system
try:
    # PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
    from heaven_base.tools.registry_tool import registry_util_func
    from heaven_base.registry.registry_service import RegistryService
except ImportError:
    # Fallback for development
    logger.warning(f"Heaven registry not available, using fallback: {traceback.format_exc()}")
    def registry_util_func(*args, **kwargs):
        return "Heaven registry not available - using fallback"

from .debug_diary import DebugDiaryMixin
from .starlog_sessions import StarlogSessionsMixin
from .rules import RulesMixin
from .hpi_system import HpiSystemMixin
from .models import RulesEntry, DebugDiaryEntry, StarlogEntry, FlightConfig

logger = logging.getLogger(__name__)

# Import CartON for mirroring (optional - degrades gracefully)
try:
    from carton_mcp.add_concept_tool import add_concept_tool_func
    CARTON_AVAILABLE = True
except ImportError:
    CARTON_AVAILABLE = False
    logger.info("CartON not available - starlog will not mirror to knowledge graph")


class Starlog(DebugDiaryMixin, StarlogSessionsMixin, RulesMixin, HpiSystemMixin):
    """Main STARLOG singleton class combining all functionality."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Auto-populate STARSHIP flight configs if registry doesn't exist or is empty
        self._ensure_flight_configs_with_defaults()
        
        logger.info("Initialized STARLOG singleton with HEAVEN registry system")

    @staticmethod
    def _normalize_concept_name(name: str) -> str:
        """Normalize to Title_Case_With_Underscores. No hyphens, no paths, no dots."""
        # Strip leading path separators and replace path/hyphen/dot with underscore
        name = name.strip("/").replace("/", "_").replace("-", "_").replace(".", "_")
        # Title case each segment
        return "_".join(seg.title() if seg.islower() else seg for seg in name.split("_"))

    def _ensure_starlog_project_linked(self, starlog_project_name: str, starsystem_path: str = None) -> None:
        """Ensure a Starlog_Project_ concept exists and is linked to its Starsystem_."""
        if not starsystem_path:
            return
        try:
            path_slug = starsystem_path.strip("/").replace("/", "_").replace("-", "_").title()
            starsystem_name = f"Starsystem_{path_slug}"
            add_concept_tool_func(
                concept_name=starlog_project_name,
                description=f"Starlog project for {starsystem_path}",
                relationships=[
                    {"relationship": "is_a", "related": ["Starlog_Project"]},
                    {"relationship": "part_of", "related": [starsystem_name]},
                    {"relationship": "instantiates", "related": ["Project_Tracking_Instance"]},
                ],
                hide_youknow=False,
                desc_update_mode="append",
            )
        except Exception as e:
            logger.debug(f"Starlog project link ensure failed (non-fatal): {e}")

    def mirror_to_carton(self, concept_name: str, description: str, relationships: list, project_name: str = None, starsystem_path: str = None, shared_connection=None) -> str:
        """Mirror starlog data to CartON knowledge graph. Fails silently if CartON unavailable."""
        if not CARTON_AVAILABLE:
            return "CartON not available"
        try:
            concept_name = self._normalize_concept_name(concept_name)

            if project_name:
                normalized_project = self._normalize_concept_name(project_name)
                starlog_project_name = f"Starlog_Project_{normalized_project}"
                relationships.append({"relationship": "part_of", "related": [starlog_project_name]})
                # Ensure the starlog project is linked to its starsystem
                self._ensure_starlog_project_linked(starlog_project_name, starsystem_path)

            result = add_concept_tool_func(
                concept_name=concept_name,
                description=description,
                relationships=relationships,
                hide_youknow=False
            )
            logger.debug(f"Mirrored to CartON: {concept_name}")
            return str(result)
        except Exception as e:
            logger.warning(f"CartON mirror failed (non-fatal): {e}")
            return f"CartON mirror failed: {e}"

    def _create_starsystem_entity(self, path: str, name: str, description: str = "", giint_project_id: str = None) -> str:
        """Create STARSYSTEM entity in CartON with Starlog_Project as PART_OF.

        Uses observation batch pattern for full ontology.

        Hierarchy:
            Starsystem_{path_slug}
                └── Starlog_Project_{name} PART_OF Starsystem_{path_slug}
                        └── (sessions will be PART_OF Starlog_Project via mirror_to_carton)
        """
        if not CARTON_AVAILABLE:
            return "CartON not available"

        try:
            # Use add_concept_tool_func for each concept (no observation wrapper)

            # Create path slug with .title() for consistency
            path_slug = path.strip("/").replace("/", "_").replace("-", "_").title()
            starsystem_name = f"Starsystem_{path_slug}"

            # Check for .git directory
            has_git = os.path.exists(os.path.join(path, ".git"))

            # Build ALL concepts for batch
            concepts = []

            # 1. STARSYSTEM entity with HAS_PROJECT
            starsystem_desc = f"STARSYSTEM for {path}. {description}"
            if has_git:
                starsystem_desc += " [Git repo detected]"

            project_concept_name = f"Starlog_Project_{self._normalize_concept_name(name)}"
            starsystem_relationships = [
                {"relationship": "is_a", "related": ["STARSYSTEM"]},
                {"relationship": "part_of", "related": ["Seed_Ship_Starsystems"]},
                {"relationship": "instantiates", "related": ["Starsystem_Instance"]},
                {"relationship": "has_project", "related": [project_concept_name]},
            ]

            concepts.append({
                "name": starsystem_name,
                "description": starsystem_desc,
                "relationships": starsystem_relationships
            })

            # 2. Starlog_Project entity with PART_OF STARSYSTEM
            project_relationships = [
                {"relationship": "is_a", "related": ["Starlog_Project"]},
                {"relationship": "part_of", "related": [starsystem_name]},
                {"relationship": "instantiates", "related": ["Project_Tracking_Instance"]},
            ]

            concepts.append({
                "name": project_concept_name,
                "description": f"STARLOG project '{name}' at {path}. {description}",
                "relationships": project_relationships
            })

            # 3. If GIINT project provided, link it to STARSYSTEM
            if giint_project_id:
                giint_concept_name = f"GIINT_Project_{giint_project_id}"
                concepts.append({
                    "name": giint_concept_name,
                    "description": f"GIINT project '{giint_project_id}' linked to {starsystem_name}",
                    "relationships": [
                        {"relationship": "is_a", "related": ["GIINT_Project"]},
                        {"relationship": "part_of", "related": [starsystem_name]},
                        {"relationship": "instantiates", "related": ["Giint_Project_Instance"]},
                    ]
                })
                # Also add HAS_GIINT_PROJECT to starsystem
                starsystem_relationships.append({
                    "relationship": "has_giint_project", "related": [giint_concept_name]
                })

            # Submit all concepts (each with raw_concept=True, no observation wrapper)
            for concept in concepts:
                add_concept_tool_func(
                    concept_name=concept["name"],
                    description=concept["description"],
                    relationships=concept["relationships"],
                    hide_youknow=False
                )
            logger.info(f"Created STARSYSTEM entity: {starsystem_name} with {len(concepts)} concepts")

            return starsystem_name

        except Exception as e:
            logger.warning(f"STARSYSTEM entity creation failed (non-fatal): {e}")
            return f"STARSYSTEM creation failed: {e}"

    def _ensure_flight_configs_with_defaults(self) -> None:
        """Ensure starlog_flight_configs registry exists and populate with STARSHIP defaults if empty."""
        try:
            # Check if registry exists and has configs
            current_data = self._get_flight_configs_registry_data()
            if current_data:
                # Registry already has configs, don't auto-populate
                logger.debug("Flight configs registry already populated")
                return
            
            # Registry is empty or doesn't exist - auto-populate STARSHIP defaults
            try:
                from starship_mcp.auto_populate import auto_populate_defaults
                status = auto_populate_defaults()
                logger.info(f"Auto-populated STARSHIP flight configs: {status}")
            except ImportError:
                logger.debug("STARSHIP MCP not available for auto-population")
            except Exception as e:
                logger.warning(f"Failed to auto-populate STARSHIP defaults: {e}", exc_info=True)
                
        except Exception as e:
            logger.warning(f"Error ensuring flight configs registry: {e}", exc_info=True)
    
    _PLACEHOLDER_COMMENTS = {
        ".py": '"""{content}"""',
        ".js": "/* {content} */",
        ".ts": "/* {content} */",
        ".sh": "# {content}",
        ".md": "{content}",
        ".yaml": "# {content}",
        ".yml": "# {content}",
        ".json": "{}",
        ".html": "<!-- {content} -->",
        ".css": "/* {content} */",
    }

    def _create_placeholder_file(self, filepath: str, component_name: str, desc: str) -> bool:
        """Create a placeholder file with component description. Returns True if created, False if exists."""
        if os.path.exists(filepath):
            return False
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        ext = os.path.splitext(filepath)[1].lower()
        content = f"AUTO-GENERATED PLACEHOLDER — Starsystem Terraform\nComponent: {component_name}\nDescription: {desc}\n\nReplace this content to implement the component."
        template = self._PLACEHOLDER_COMMENTS.get(ext, "# {content}")
        if template == "{}":
            file_content = "{}"
        else:
            file_content = template.format(content=content)
        with open(filepath, 'w') as f:
            f.write(file_content + "\n")
        return True

    # TRIGGERS: CAVE/sancrev:8080/hook/posttooluse via HTTP POST — triggers OMNISANC/CAVE PostToolUse pipeline
    def _post_to_omnisanc(self, tool_name: str, tool_input: dict, tool_response: str = '{"success": true}'):
        """POST to CAVE /hook/posttooluse — triggers OMNISANC directly for internal calls.

        When code calls GIINT functions internally (Python import), Claude Code hooks
        don't fire. This mimics the PostToolUse event so OMNISANC creates TK cards.
        Same pattern as mcp_server_sse.py _post_to_cave_hook().
        """
        import urllib.request
        import urllib.error
        # TRIGGERS: CAVE/sancrev:8080/hook/posttooluse via HTTP POST
        cave_url = os.environ.get("CAVE_URL", "http://localhost:8080")
        hook_data = json.dumps({
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_response": tool_response,
        }).encode()
        try:
            req = urllib.request.Request(
                f"{cave_url}/hook/posttooluse",
                data=hook_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as e:
            logger.warning(f"OMNISANC POST failed (non-fatal): {e}")

    # TRIGGERS: OMNISANC/CAVE PostToolUse pipeline via _post_to_omnisanc() for each GIINT planning call
    def _build_architecture(self, path: str, giint_project_id: str, architecture: list) -> list:
        """Create placeholder files + GIINT features/components from validated architecture tree.

        Calls GIINT planning functions directly, then POSTs to CAVE /hook/posttooluse
        to trigger OMNISANC TK card creation (internal calls don't fire Claude Code hooks).
        """
        from starlog_mcp.models import ArchitectureTree
        msgs = []

        # OMNISANC REQUIRED — TK card creation depends on OMNISANC processing the POSTs
        omnisanc_disabled = os.path.join(
            os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"),
            "omnisanc_core", ".omnisanc_disabled"
        )
        if os.path.exists(omnisanc_disabled):
            return ["ERROR: OMNISANC must be ON for architecture build. TK cards require OMNISANC. Toggle OMNISANC on first."]

        # Validate through Pydantic — fails loud on empty descriptions
        tree = ArchitectureTree.from_list(architecture)

        try:
            from llm_intelligence.projects import (
                add_feature_to_project, add_component_to_feature, add_deliverable_to_component
            )
        except ImportError:
            return ["llm_intelligence not available — architecture skipped"]

        for feat in tree.features:
            add_feature_to_project(giint_project_id, feat.feature, path=path)
            self._post_to_omnisanc(
                "mcp__giint-llm-intelligence__planning__add_feature_to_project",
                {"project_id": giint_project_id, "feature_name": feat.feature, "path": path}
            )
            msgs.append(f"  Feature: {feat.feature} — {feat.feature_description[:60]}")

            for filepath, comp_desc in feat.files.items():
                full_path = os.path.join(path, filepath)
                created = self._create_placeholder_file(full_path, feat.feature, comp_desc)
                file_msg = "created" if created else "exists"
                component_name = os.path.splitext(os.path.basename(filepath))[0].replace("-", "_").replace(" ", "_").title()
                add_component_to_feature(giint_project_id, feat.feature, component_name, path=full_path)
                self._post_to_omnisanc(
                    "mcp__giint-llm-intelligence__planning__add_component_to_feature",
                    {"project_id": giint_project_id, "feature_name": feat.feature, "component_name": component_name, "path": full_path}
                )
                deliverable_name = f"Implement_{component_name}"
                add_deliverable_to_component(giint_project_id, feat.feature, component_name, deliverable_name)
                self._post_to_omnisanc(
                    "mcp__giint-llm-intelligence__planning__add_deliverable_to_component",
                    {"project_id": giint_project_id, "feature_name": feat.feature, "component_name": component_name, "deliverable_name": deliverable_name}
                )
                msgs.append(f"    {filepath} [{file_msg}] -> {component_name} -> {deliverable_name}: {comp_desc[:50]}")

        return msgs

    def init_project(self, path: str, name: str, description: str = "", giint_project_id: str = None, architecture: list = None) -> str:
        """Create new STARSYSTEM project with .claude/ scaffold, registries, starlog.hpi, GIINT project, and optional architecture.

        A STARSYSTEM is: directory + starlog project + GIINT project + .claude/ (rules + skills).

        Args:
            architecture: Optional list of {filepath: {feature_name: description}} dicts.
                Creates placeholder files + GIINT features/components. Existing files kept.
        """
        try:
            # Create project directory if it doesn't exist
            os.makedirs(path, exist_ok=True)

            # Auto-create GIINT project if not provided
            if not giint_project_id:
                try:
                    from llm_intelligence.projects import create_project as create_giint_project
                    giint_id = name.lower().replace(" ", "-").replace("/", "-")
                    hpi_path_for_giint = os.path.join(path, "starlog.hpi")
                    result = create_giint_project(
                        project_id=giint_id,
                        project_dir=path,
                        starlog_path=hpi_path_for_giint
                    )
                    if result.get("success"):
                        giint_project_id = giint_id
                        logger.info(f"Auto-created GIINT project '{giint_id}' for STARSYSTEM '{name}'")
                    elif "already exists" in str(result.get("error", "")):
                        giint_project_id = giint_id
                        logger.info(f"GIINT project '{giint_id}' already exists, linking to it")
                    else:
                        logger.warning(f"Failed to auto-create GIINT project: {result.get('error', 'unknown')}")
                except ImportError:
                    logger.warning("llm_intelligence not available — GIINT project not created")
                except Exception as e:
                    logger.warning(f"GIINT auto-creation failed (non-fatal): {e}")

            # Create project registries
            self._create_project_registry(name, "debug_diary")
            self._create_project_registry(name, "starlog")

            # Create starlog.hpi file with GIINT project mapping
            hpi_path = os.path.join(path, "starlog.hpi")
            hpi_content = self._create_default_hpi_content(name, description, giint_project_id)

            with open(hpi_path, 'w') as f:
                json.dump(hpi_content, f, indent=2)

            # Create .claude/ scaffold
            self._create_claude_scaffold(path, name)

            # Parse codebase into Neo4j (context-alignment)
            parse_status = self._parse_codebase_to_neo4j(path)

            # Create STARSYSTEM entity in CartON
            starsystem_name = self._create_starsystem_entity(path, name, description, giint_project_id)

            # Auto-generate architecture from CA if code exists in Neo4j and no manual architecture provided
            if not architecture and parse_status in ("parsed", "already_parsed") and giint_project_id:
                architecture = self._auto_architecture_from_ca(path)
                if architecture:
                    logger.info(f"Auto-generated architecture from CA: {len(architecture)} features")

            # Build architecture if available (creates files + GIINT features/components)
            arch_msgs = []
            if architecture and giint_project_id:
                arch_msgs = self._build_architecture(path, giint_project_id, architecture)
                if arch_msgs:
                    logger.info(f"Built architecture: {len(arch_msgs)} entries")

            giint_msg = f" (GIINT: '{giint_project_id}')" if giint_project_id else " (⚠️ no GIINT — K1 not achievable)"
            parse_msg = f" [code parsed]" if parse_status == "parsed" else ""
            arch_msg = f"\nArchitecture ({len(arch_msgs)} files):\n" + "\n".join(arch_msgs) if arch_msgs else ""
            logger.info(f"Initialized STARSYSTEM '{name}' at {path}{giint_msg}")
            return f"✅ Initialized STARSYSTEM '{name}' with .claude/ scaffold, starlog.hpi, and GIINT project{giint_msg}{parse_msg}" + \
                   f" [STARSYSTEM: {starsystem_name}] [Persona: starship-pilot-{name}]{arch_msg}"

        except Exception as e:
            logger.error(f"Failed to initialize project: {traceback.format_exc()}")
            return f"❌ Failed to initialize project: {str(e)}"

    def upgrade_starsystem(self, path: str) -> str:
        """Upgrade existing STARSYSTEM: add missing GIINT project and .claude/ scaffold without touching existing data."""
        try:
            hpi_path = os.path.join(path, "starlog.hpi")
            if not os.path.exists(hpi_path):
                return f"❌ Not a STARLOG project: {path}"

            with open(hpi_path, 'r') as f:
                hpi = json.load(f)

            name = hpi.get("metadata", {}).get("project_name", os.path.basename(path))
            giint_id = hpi.get("metadata", {}).get("giint_project_id")
            upgraded = []

            # Add GIINT project if missing
            if not giint_id:
                try:
                    from llm_intelligence.projects import create_project as create_giint_project
                    giint_id = name.lower().replace(" ", "-").replace("/", "-")
                    result = create_giint_project(project_id=giint_id, project_dir=path, starlog_path=hpi_path)
                    if result.get("success") or "already exists" in str(result.get("error", "")):
                        hpi.setdefault("metadata", {})["giint_project_id"] = giint_id
                        with open(hpi_path, 'w') as f:
                            json.dump(hpi, f, indent=2)
                        upgraded.append(f"GIINT '{giint_id}'")
                except Exception as e:
                    logger.warning(f"GIINT upgrade failed: {e}")

            # Ensure .claude/ scaffold exists
            claude_dir = os.path.join(path, ".claude")
            for subdir in ["rules", "skills", "agents"]:
                os.makedirs(os.path.join(claude_dir, subdir), exist_ok=True)
            rule_path = os.path.join(claude_dir, "rules", "starsystem.md")
            if not os.path.exists(rule_path):
                persona_name = f"starship-pilot-{name}"
                with open(rule_path, 'w') as f:
                    f.write(f"# STARSYSTEM\n\nThis repo is a STARSYSTEM. Equip persona `{persona_name}`.\n")
                upgraded.append(".claude/ scaffold")

            # Parse codebase if not already in Neo4j
            parse_status = self._parse_codebase_to_neo4j(path)
            if parse_status == "parsed":
                upgraded.append("code parsed")

            if upgraded:
                return f"✅ Upgraded STARSYSTEM '{name}': added {', '.join(upgraded)}"
            return f"ℹ️ STARSYSTEM '{name}' already fully equipped (GIINT: {giint_id})"
        except Exception as e:
            return f"❌ Upgrade failed: {e}"

    @staticmethod
    def _neo4j_creds():
        """Return (uri, user, password) from env."""
        return (
            os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687"),
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "password"),
        )

    def _parse_codebase_to_neo4j(self, path: str) -> str:
        """Parse codebase into Neo4j via context-alignment's DirectNeo4jExtractor. Non-fatal."""
        try:
            import sys
            sys.path.insert(0, "/home/GOD/gnosys-plugin-v2/knowledge/context-alignment/neo4j_codebase_mcp")
            from parsers.parse_repo_into_neo4j import DirectNeo4jExtractor
            import asyncio

            neo4j_uri, neo4j_user, neo4j_password = self._neo4j_creds()

            repo_name = os.path.basename(os.path.normpath(path))

            # Check if already parsed in Neo4j
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with driver.session() as session:
                result = session.run(
                    "MATCH (r:Repository {name: $name}) RETURN count(r) AS c",
                    name=repo_name
                )
                if result.single()["c"] > 0:
                    driver.close()
                    return "already_parsed"
            driver.close()

            extractor = DirectNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)

            async def _run():
                await extractor.initialize()
                result = await extractor.analyze_local_directory(path, repo_name)
                await extractor.close()
                return result

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(asyncio.run, _run()).result(timeout=120)
                else:
                    result = asyncio.run(_run())
            except RuntimeError:
                result = asyncio.run(_run())

            logger.info(f"Parsed codebase '{path}' into Neo4j")
            return "parsed"
        except ImportError:
            logger.debug("context-alignment parser not available — skipping codebase parse")
            return "unavailable"
        except Exception as e:
            logger.warning(f"Codebase parse failed (non-fatal): {e}")
            return f"failed: {e}"

    def _auto_architecture_from_ca(self, path: str) -> list:
        """Query CA Neo4j graph for parsed repo structure, return architecture list.

        Groups files by parent directory (module→feature). Each file's classes/functions
        become its component description. Returns [] if no code files or CA unavailable.
        """
        try:
            from neo4j import GraphDatabase
            neo4j_uri, neo4j_user, neo4j_password = self._neo4j_creds()
            repo_name = os.path.basename(os.path.normpath(path))

            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            with driver.session() as session:
                # Get all files with their classes and functions
                records = session.run(
                    "MATCH (r:Repository {name: $repo})-[:CONTAINS]->(f:File) "
                    "OPTIONAL MATCH (f)-[:DEFINES]->(c:Class) "
                    "OPTIONAL MATCH (f)-[:DEFINES]->(fn:Function) "
                    "RETURN f.path AS path, "
                    "collect(DISTINCT c.name) AS classes, "
                    "collect(DISTINCT fn.name) AS functions",
                    repo=repo_name
                ).data()
            driver.close()

            if not records:
                return []

            # Group files by parent directory (module = feature)
            modules = {}
            for rec in records:
                fpath = rec["path"]
                if not fpath or not fpath.endswith(".py"):
                    continue
                parent = os.path.dirname(fpath) or repo_name
                modules.setdefault(parent, []).append(rec)

            architecture = []
            for module_path, files in sorted(modules.items()):
                mod_name = module_path.replace("/", "_").replace("-", "_")
                mod_name = "_".join(w.capitalize() for w in mod_name.split("_") if w)
                file_map = {}
                for rec in files:
                    parts = []
                    if rec["classes"]:
                        parts.append(f"Classes: {', '.join(rec['classes'][:5])}")
                    if rec["functions"]:
                        parts.append(f"Functions: {', '.join(rec['functions'][:5])}")
                    desc = "; ".join(parts) if parts else "Python module"
                    file_map[rec["path"]] = desc

                if file_map:
                    architecture.append({
                        "feature": mod_name,
                        "feature_description": f"Module {module_path} ({len(file_map)} files)",
                        "files": file_map,
                    })

            return architecture
        except Exception as e:
            logger.debug(f"Auto-architecture from CA failed (non-fatal): {e}")
            return []

    def _create_claude_scaffold(self, path: str, name: str):
        """Create .claude/ directory with STARSYSTEM scaffold."""
        claude_dir = os.path.join(path, ".claude")
        rules_dir = os.path.join(claude_dir, "rules")
        agents_dir = os.path.join(claude_dir, "agents")
        skills_dir = os.path.join(claude_dir, "skills")

        os.makedirs(rules_dir, exist_ok=True)
        os.makedirs(agents_dir, exist_ok=True)
        os.makedirs(skills_dir, exist_ok=True)

        persona_name = f"starship-pilot-{name}"

        # Write CLAUDE.md
        claude_md_path = os.path.join(claude_dir, "CLAUDE.md")
        if not os.path.exists(claude_md_path):
            with open(claude_md_path, 'w') as f:
                f.write(f"# CLAUDE.md\n\nEquip persona `{persona_name}` before working in this repo.\n")

        # Write starsystem rule
        rule_path = os.path.join(rules_dir, "starsystem.md")
        if not os.path.exists(rule_path):
            with open(rule_path, 'w') as f:
                f.write(f"# STARSYSTEM\n\n"
                        f"This repo is a STARSYSTEM. Before working:\n\n"
                        f"1. Equip persona `{persona_name}`\n"
                        f"2. `orient()` to check project status\n"
                        f"3. `start_starlog()` to begin a session\n"
                        f"4. `fly()` to browse available flight configs\n"
                        f"5. Log insights/bugs/decisions to debug diary as you work\n"
                        f"6. `end_starlog()` when session is done\n")
    
    def _get_registry_status(self, project_name: str) -> Dict[str, int]:
        """Get registry status for all project registries."""
        rules_data = self._get_registry_data(project_name, "rules")
        diary_data = self._get_registry_data(project_name, "debug_diary") 
        starlog_data = self._get_registry_data(project_name, "starlog")
        
        return {
            "rules": len(rules_data),
            "debug_diary": len(diary_data),
            "starlog": len(starlog_data)
        }
    
    def _build_project_status(self, project_name: str) -> Dict[str, Any]:
        """Build project status info for valid STARLOG projects."""
        registry_status = self._get_registry_status(project_name)
        
        return {
            "is_starlog_project": True,
            "project_name": project_name,
            "hpi_file_exists": True,
            "registries": registry_status
        }
    
    def check(self, path: str) -> Dict[str, Any]:
        """Check if directory is a STARLOG project."""
        try:
            hpi_path = os.path.join(path, "starlog.hpi")
            is_starlog_project = os.path.exists(hpi_path)
            
            if is_starlog_project:
                project_name = self._get_project_name_from_path(path)
                return self._build_project_status(project_name)
            else:
                return {
                    "is_starlog_project": False,
                    "hpi_file_exists": False
                }
                
        except Exception as e:
            logger.error(f"Error checking project: {traceback.format_exc()}")
            return {
                "is_starlog_project": False,
                "error": str(e)
            }
    
    # Heaven registry utilities for all mixins
    def _create_project_registry(self, project_name: str, registry_type: str) -> str:
        """Create registry for project using Heaven registry system."""
        registry_name = f"{project_name}_{registry_type}"
        result = registry_util_func("create_registry", registry_name=registry_name)
        logger.debug(f"Created registry {registry_name}: {result}")
        return result
    
    def _get_registry_data(self, project_name: str, registry_type: str) -> Dict[str, Any]:
        """Get all data from registry using Heaven registry system."""
        registry_name = f"{project_name}_{registry_type}"
        
        try:
            # Use RegistryService directly instead of parsing display strings
            service = RegistryService()
            data = service.get_all(registry_name)
            return data if data is not None else {}
        except Exception:
            logger.warning(f"Failed to get registry data for {registry_name}: {traceback.format_exc()}")
            return {}
    
    def _add_to_registry(self, project_name: str, registry_type: str, key: str, value: Any) -> str:
        """Add item to registry using Heaven registry system."""
        registry_name = f"{project_name}_{registry_type}"
        
        # Check if this is the first item being added to a rules registry
        is_first_rule = (registry_type == "rules" and 
                        self._is_registry_empty(registry_name))
        
        if isinstance(value, dict):
            result = registry_util_func("add", registry_name=registry_name, key=key, value_dict=value)
        else:
            result = registry_util_func("add", registry_name=registry_name, key=key, value_str=str(value))
        
        # Auto-create brain when first rule is added
        if is_first_rule and "added to registry" in result:
            self._auto_create_rules_brain(project_name, registry_name)
        
        logger.debug(f"Added {key} to {registry_name}: {result}")
        return result
    
    def _is_registry_empty(self, registry_name: str) -> bool:
        """Check if registry is empty or doesn't exist."""
        try:
            result = registry_util_func("get_all", registry_name=registry_name)
            return "{}" in result or "not found" in result or not result.strip()
        except:
            return True
    
    def _auto_create_rules_brain(self, project_name: str, registry_name: str) -> None:
        """Auto-create brain-agent brain when rules registry is created."""
        try:
            from brain_agent.manager_tools import brain_manager_func
            
            brain_id = f"{project_name}_rules_brain"
            result = brain_manager_func(
                operation="add",
                brain_id=brain_id,
                name=f"{project_name} Rules Brain",
                neuron_source_type="registry_keys",
                neuron_source=registry_name,
                chunk_max=30000
            )
            
            if "added to registry" in result:
                logger.info(f"✅ Auto-created rules brain '{brain_id}' for project '{project_name}'")
            else:
                logger.warning(f"Failed to auto-create rules brain: {result}")
                
        except ImportError:
            logger.info("brain-agent not available - skipping auto brain creation")
        except Exception as e:
            logger.warning(f"Failed to auto-create rules brain: {e}")
    
    def _update_registry_item(self, project_name: str, registry_type: str, key: str, value: Any) -> str:
        """Update item in registry using Heaven registry system."""
        registry_name = f"{project_name}_{registry_type}"
        
        if isinstance(value, dict):
            result = registry_util_func("update", registry_name=registry_name, key=key, value_dict=value)
        else:
            result = registry_util_func("update", registry_name=registry_name, key=key, value_str=str(value))
        
        logger.debug(f"Updated {key} in {registry_name}: {result}")
        return result
    
    def _get_from_registry(self, project_name: str, registry_type: str, key: str) -> Any:
        """Get specific item from registry using Heaven registry system."""
        registry_name = f"{project_name}_{registry_type}"
        result = registry_util_func("get", registry_name=registry_name, key=key)
        
        # Parse the result string to extract the actual data
        if f"Item '{key}' in registry" in result:
            try:
                start_idx = result.find(": ") + 2
                if start_idx > 1:
                    data_str = result[start_idx:]
                    if data_str.startswith(('{', '[')):
                        # Handle Python literals (None, True, False) in the registry data
                        data_str = data_str.replace("None", "null").replace("True", "true").replace("False", "false")
                        return json.loads(data_str.replace("'", '"'))
                    else:
                        return data_str
            except Exception:
                logger.warning(f"Failed to parse registry item: {traceback.format_exc()}")
        
        return None
    
    def _get_project_name_from_path(self, path: str) -> str:
        """Extract project name from path - checks for starlog.hpi file."""
        hpi_path = os.path.join(path, "starlog.hpi")
        if os.path.exists(hpi_path):
            return self._get_project_name_from_hpi(hpi_path)
        else:
            # Default to directory name
            return os.path.basename(os.path.abspath(path))
    
    def _get_project_name_from_hpi(self, hpi_path: str) -> str:
        """Extract project name from .hpi file content."""
        try:
            with open(hpi_path, 'r') as f:
                hpi_data = json.load(f)
                return hpi_data.get('project_name', os.path.basename(os.path.dirname(hpi_path)))
        except:
            return os.path.basename(os.path.dirname(hpi_path))
    
    def retrieve_starlog(self, project: str, session_id: str = None, 
                        date_range: str = None, paths: bool = False) -> str:
        """Generic starlog retrieval with filtering options."""
        try:
            project_name = project
            starlog_data = self._get_registry_data(project_name, "starlog")
            diary_data = self._get_registry_data(project_name, "debug_diary")
            
            if paths:
                # Return registry file paths
                import os
                heaven_data_dir = os.environ["HEAVEN_DATA_DIR"]
                context = f"# STARLOG Registry Paths\n\n"
                context += f"**Starlog Registry**: {heaven_data_dir}/registry/{project_name}_starlog_registry.json\n"
                context += f"**Debug Diary Registry**: {heaven_data_dir}/registry/{project_name}_debug_diary_registry.json\n"
                context += f"**Rules Registry**: {heaven_data_dir}/registry/{project_name}_rules_registry.json\n"
                return context
            
            # Filter sessions
            filtered_sessions = starlog_data
            if session_id:
                # Get specific session
                if session_id in starlog_data:
                    filtered_sessions = {session_id: starlog_data[session_id]}
                else:
                    return f"❌ Session '{session_id}' not found in project '{project}'"
            elif date_range:
                # TODO: Implement date range filtering
                pass
            
            # Format results
            if not filtered_sessions:
                return f"📋 No STARLOG sessions found for project '{project}'"
            
            context = f"# STARLOG History for {project}\n\n"
            
            # Sort sessions by timestamp 
            sorted_sessions = sorted(filtered_sessions.items(), 
                                   key=lambda x: x[1].get("timestamp", ""), 
                                   reverse=True)
            
            for session_id, session_data in sorted_sessions:
                context += f"## Session: {session_data.get('session_title', session_id)}\n"
                context += f"**Date**: {session_data.get('date', 'Unknown')}\n"
                context += f"**ID**: {session_id}\n"
                context += f"**Goals**: {', '.join(session_data.get('session_goals', []))}\n\n"
                context += f"**START**: {session_data.get('start_content', 'No start content')}\n\n"
                
                if session_data.get('end_content'):
                    context += f"**END**: {session_data.get('end_content')}\n\n"
                else:
                    context += f"**Status**: Session in progress\n\n"
                
                context += "---\n\n"
            
            # Add debug diary if no specific session requested
            if not session_id and diary_data:
                context += "## Recent Debug Diary Entries\n\n"
                # Sort by timestamp and get recent entries
                entries = list(diary_data.items())
                entries.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
                
                for entry_id, entry_data in entries[:5]:  # Last 5 entries
                    timestamp = entry_data.get("timestamp", "").split("T")[0] 
                    content = entry_data.get("content", "")
                    context += f"**{timestamp}**: {content}\n"
                context += "\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to retrieve starlog: {traceback.format_exc()}")
            return f"❌ Error retrieving starlog: {str(e)}"
    
    # Model-registry operations
    def _save_rules_entry(self, project_name: str, rule: RulesEntry) -> str:
        """Save RulesEntry to registry."""
        try:
            result = self._add_to_registry(project_name, "rules", rule.id, rule.model_dump(mode='json'))
            logger.debug(f"Saved rule {rule.id} to {project_name}_rules")
            return result
        except Exception as e:
            logger.error(f"Failed to save rule: {traceback.format_exc()}")
            raise e
    
    def _load_rules_entry(self, project_name: str, rule_id: str) -> Optional[RulesEntry]:
        """Load RulesEntry from registry."""
        try:
            rule_data = self._get_from_registry(project_name, "rules", rule_id)
            if rule_data:
                return RulesEntry(**rule_data)
            return None
        except Exception as e:
            logger.error(f"Failed to load rule {rule_id}: {traceback.format_exc()}")
            return None
    
    def _save_debug_diary_entry(self, project_name: str, entry: DebugDiaryEntry) -> str:
        """Save DebugDiaryEntry to registry."""
        try:
            result = self._add_to_registry(project_name, "debug_diary", entry.id, entry.model_dump(mode='json'))
            logger.debug(f"Saved debug diary entry {entry.id} to {project_name}_debug_diary")
            return result
        except Exception as e:
            logger.error(f"Failed to save debug diary entry: {traceback.format_exc()}")
            raise e
    
    def _load_debug_diary_entry(self, project_name: str, entry_id: str) -> Optional[DebugDiaryEntry]:
        """Load DebugDiaryEntry from registry."""
        try:
            entry_data = self._get_from_registry(project_name, "debug_diary", entry_id)
            if entry_data:
                return DebugDiaryEntry(**entry_data)
            return None
        except Exception as e:
            logger.error(f"Failed to load debug diary entry {entry_id}: {traceback.format_exc()}")
            return None
    
    def _save_starlog_entry(self, project_name: str, session: StarlogEntry) -> str:
        """Save StarlogEntry to registry."""
        try:
            result = self._add_to_registry(project_name, "starlog", session.id, session.model_dump(mode='json'))
            logger.debug(f"Saved starlog session {session.id} to {project_name}_starlog")
            return result
        except Exception as e:
            logger.error(f"Failed to save starlog session: {traceback.format_exc()}")
            raise e
    
    def _load_starlog_entry(self, project_name: str, session_id: str) -> Optional[StarlogEntry]:
        """Load StarlogEntry from registry."""
        try:
            session_data = self._get_from_registry(project_name, "starlog", session_id)
            if session_data:
                return StarlogEntry(**session_data)
            return None
        except Exception as e:
            logger.error(f"Failed to load starlog session {session_id}: {traceback.format_exc()}")
            return None
    
    def _save_flight_config(self, flight_config: FlightConfig) -> str:
        """Save FlightConfig to global registry."""
        try:
            result = registry_util_func("add", "starlog_flight_configs", flight_config.id, flight_config.model_dump(mode='json'))
            logger.debug(f"Saved flight config {flight_config.id} to starlog_flight_configs")
            return result
        except Exception as e:
            logger.error(f"Failed to save flight config: {traceback.format_exc()}")
            raise e
    
    def _load_flight_config(self, flight_id: str) -> Optional[FlightConfig]:
        """Load FlightConfig from global registry."""
        try:
            flight_data = registry_util_func("get", "starlog_flight_configs", flight_id)
            if flight_data:
                return FlightConfig(**flight_data)
            return None
        except Exception as e:
            logger.error(f"Failed to load flight config {flight_id}: {traceback.format_exc()}")
            return None
    
    def _get_flight_configs_registry_data(self) -> Dict[str, Any]:
        """Get all flight configs from registry."""
        try:
            result = registry_util_func("get_all", registry_name="starlog_flight_configs")
            
            # Parse the result string to extract the actual data
            if "Items in registry" in result:
                try:
                    start_idx = result.find("{") 
                    if start_idx != -1:
                        dict_str = result[start_idx:]
                        # Handle Python literals (None, True, False) in the registry data
                        dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                        return json.loads(dict_str.replace("'", '"'))
                except Exception:
                    logger.warning(f"Failed to parse flight configs registry result: {traceback.format_exc()}")
            
            return {}
        except Exception as e:
            logger.error(f"Failed to get flight configs: {traceback.format_exc()}")
            return {}