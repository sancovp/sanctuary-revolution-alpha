"""CartON compilation loop — compile parsed concepts to knowledge graph."""

import json
import logging
import os
import traceback
from pathlib import Path

from dragonbones.constants import ACTIVE_HC_FILE
from dragonbones.giint_types import inject_giint_types, GIINT_EC_SHAPES
from dragonbones.logs import get_add_concept_func

logger = logging.getLogger("dragonbones")

COURSE_STATE_PATH = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "omnisanc_core" / ".course_state"


def _get_active_starsystem_name() -> str | None:
    """Get the current starsystem collection name from Neo4j.

    Queries for the actual Starsystem_Collection entity rather than
    constructing a name from the path (which doesn't match real entities).
    Falls back to path-based construction if Neo4j unavailable.
    """
    try:
        if not COURSE_STATE_PATH.exists():
            return None
        state = json.loads(COURSE_STATE_PATH.read_text())
        project_path = state.get("last_oriented") or (state.get("projects", [None])[0])
        if not project_path:
            return None

        # Try Neo4j first — get the ACTUAL collection entity
        try:
            from neo4j import GraphDatabase
            uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
            user = os.environ.get("NEO4J_USER", "neo4j")
            password = os.environ.get("NEO4J_PASSWORD", "password")
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                # Find Starsystem_Collection whose description mentions this path
                result = session.run(
                    "MATCH (ss:Wiki)-[:IS_A]->(:Wiki {n: 'Starsystem_Collection'}) "
                    "WHERE ss.d CONTAINS $path "
                    "RETURN ss.n AS name LIMIT 1",
                    path=project_path,
                )
                record = result.single()
                if record:
                    driver.close()
                    return record["name"]
            driver.close()
        except Exception:
            pass

        # Fallback: construct from path (may not match real entity)
        slug = project_path.strip("/").replace("/", "_").replace("-", "_").title()
        return f"Starsystem_{slug}"
    except Exception:
        return None


def batch_check_descs_in_carton(concept_names: list[str]) -> dict[str, str]:
    """Batch check which concepts already have descriptions in CartON (Neo4j)."""
    if not concept_names:
        return {}
    try:
        from neo4j import GraphDatabase
        uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run(
                "MATCH (c:Wiki) WHERE c.n IN $names AND c.d IS NOT NULL AND c.d <> '' "
                "RETURN c.n AS name, c.d AS desc",
                names=concept_names,
            )
            found = {record["name"]: record["desc"] for record in result}
        driver.close()
        return found
    except Exception:
        logger.exception("Neo4j batch desc lookup failed")
        return {}


def _is_giint_project(name: str) -> bool:
    """Check if name is a GIINT_Project_ concept (case-insensitive prefix)."""
    return name.lower().startswith("giint_project_")


def _walk_hierarchy(concept: dict, concepts_by_name: dict) -> list[str]:
    """Walk part_of chain from concept up to GIINT_Project_, return hierarchy top-down.

    Uses in-memory concept dicts (same compilation batch) to walk the chain.
    Falls back to CartON query for parents not in the current batch.
    Stops at GIINT_Project_ level (does not walk past it).
    Returns list like ['Giint_Project_Omnisanc', 'Giint_Feature_X', ...].
    """
    chain = [concept["concept_name"]]
    current = concept
    seen = {concept["concept_name"]}

    for _ in range(5):  # Max 5 levels: Task→Deliverable→Component→Feature→Project
        # Stop if we already reached a GIINT_Project_
        if _is_giint_project(current.get("concept_name", "")):
            break

        partof_targets = []
        for r in current.get("relationships", []):
            if r["relationship"] == "part_of":
                partof_targets = r["related"]
                break
        if not partof_targets:
            break

        parent_name = partof_targets[0]
        if parent_name in seen:
            break
        seen.add(parent_name)
        chain.append(parent_name)

        # Stop walking if parent IS a GIINT_Project_
        if _is_giint_project(parent_name):
            break

        if parent_name in concepts_by_name:
            current = concepts_by_name[parent_name]
        else:
            # Parent not in batch — query CartON for its part_of
            try:
                from neo4j import GraphDatabase
                uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
                user = os.environ.get("NEO4J_USER", "neo4j")
                pw = os.environ.get("NEO4J_PASSWORD", "password")
                driver = GraphDatabase.driver(uri, auth=(user, pw))
                normalized = parent_name.replace("-", "_").replace("_", " ").title().replace(" ", "_")
                with driver.session() as session:
                    result = session.run(
                        "MATCH (c:Wiki {n: $name})-[:PART_OF]->(p:Wiki) "
                        "RETURN p.n AS parent LIMIT 1",
                        name=normalized,
                    )
                    record = result.single()
                    if record:
                        current = {"concept_name": parent_name,
                                   "relationships": [{"relationship": "part_of",
                                                      "related": [record["parent"]]}]}
                    else:
                        current = {"concept_name": parent_name, "relationships": []}
                driver.close()
            except Exception:
                logger.exception("CartON lookup failed for parent %s", parent_name)
                break

    chain.reverse()  # Top-down: Project > Feature > Component > Deliverable
    return chain


def _mirror_to_canopy(concept_name: str, hierarchy_str: str, assignee: str, concept: dict) -> None:
    """Mirror a GIINT_Deliverable to Canopy schedule. Best-effort, never fails loudly."""
    try:
        from canopy.schedule import add_to_schedule

        # Map assignee to Canopy item_type format
        canopy_type_map = {
            "ai-only": "AI-Only",
            "ai-human": "AI+Human",
            "human-only": "Human-Only",
        }
        item_type = canopy_type_map.get(assignee, "AI-Only")

        # Get operadic flow IDs from concept relationships if present
        operadic_flow_id = None
        for r in concept.get("relationships", []):
            if r["relationship"] == "has_operadic_flow":
                operadic_flow_id = r["related"][0] if r["related"] else None
                break

        add_to_schedule(
            item_type=item_type,
            description=f"{concept_name} | {hierarchy_str}",
            execution_type="mission",
            execution_type_decision_explanation=f"Auto-mirrored from Dragonbones GIINT_Deliverable compilation. Assignee: {assignee}.",
            priority=5,
            mission_type="bml_default",
            mission_type_domain="odyssey",
            source_type="opera" if operadic_flow_id else "freestyle",
            source_operadic_flow_id=operadic_flow_id,
        )
        logger.info("Mirrored %s to Canopy schedule (assignee=%s)", concept_name, assignee)
    except Exception:
        logger.exception("Canopy mirror failed for %s (non-critical)", concept_name)


def _create_tk_card_for_deliverable(concept: dict, concepts_by_name: dict) -> str | None:
    """Create a TK card on backlog when a GIINT_Deliverable is compiled.

    Walks part_of chain from declared relationships to build hierarchy string
    and derive starsystem tag. Posts to TreeKanban API. Best-effort.
    """
    import json as _json
    import urllib.request

    concept_name = concept["concept_name"]
    tk_url = os.environ.get("TREEKANBAN_API_URL", "http://host.docker.internal:5051")
    board = os.environ.get("GIINT_TREEKANBAN_BOARD", "poimandres_v2")

    hierarchy = _walk_hierarchy(concept, concepts_by_name)

    # Derive starsystem tag from GIINT_Project_ in the chain (case-insensitive)
    starsystem_tag = None
    for name in hierarchy:
        if _is_giint_project(name):
            # Strip prefix case-insensitively
            starsystem_tag = name[len("Giint_Project_"):].lower().replace("_", "-")
            break
    tags = [f"starsystem:{starsystem_tag}", "giint_deliverable"] if starsystem_tag else ["giint_deliverable"]

    if not starsystem_tag:
        logger.warning("No GIINT_Project_ in hierarchy for %s — card will lack starsystem tag", concept_name)

    # Auto-classify assignee using risk logic:
    #   - If concept has "human" or "manual" or "isaac" in desc → human-only
    #   - Default for code deliverables → ai-only (agent builds, human reviews PRs)
    #   - Complex/risky keywords → ai-human
    desc_lower = concept.get("description", "").lower()
    if any(kw in desc_lower for kw in ["human-only", "manual", "isaac must", "requires isaac", "requires human"]):
        assignee = "human-only"
    elif any(kw in desc_lower for kw in ["risky", "dangerous", "breaking change", "migration", "security", "credentials"]):
        assignee = "ai-human"
    else:
        assignee = "ai-only"
    tags.append(f"assignee:{assignee}")

    # Build GIINT hierarchy string for description (format: GIINT: project/feature/component/deliverable)
    # Strip GIINT type prefixes (case-insensitive) to get short segment names
    giint_prefixes_lower = ["giint_project_", "giint_feature_", "giint_component_",
                            "giint_deliverable_", "giint_task_"]
    segments = []
    for name in hierarchy:
        short = name
        name_lower = name.lower()
        for prefix in giint_prefixes_lower:
            if name_lower.startswith(prefix):
                short = name[len(prefix):]
                break
        segments.append(short)
    hierarchy_str = "GIINT: " + "/".join(segments)

    card_data = _json.dumps({
        "board": board,
        "title": concept_name,
        "description": hierarchy_str,
        "status": "backlog",
        "priority": "NA",
        "tags": _json.dumps(tags),
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"{tk_url}/api/sqlite/cards",
            data=card_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = _json.loads(resp.read())
            tk_msg = f"📋 TK card #{result.get('id', '?')} [{concept_name}] → backlog (tags: {tags})"

        # Mirror to Canopy schedule
        _mirror_to_canopy(concept_name, hierarchy_str, assignee, concept)

        return tk_msg
    except Exception:
        logger.exception("Failed to create TK card for %s", concept_name)
        return None


def _get_active_hc_projects() -> set[str]:
    """Get GIINT_Project_ names that are part_of the active hypercluster.

    Reads HC name from ACTIVE_HC_FILE, queries Neo4j for GIINT_Project_ children.
    Returns empty set on any failure (file missing, Neo4j down, etc.).
    """
    try:
        with open(ACTIVE_HC_FILE) as f:
            hc_name = f.read().strip()
        if not hc_name:
            return set()

        from neo4j import GraphDatabase
        uri = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # Normalize HC name to title case for Neo4j lookup
        normalized = hc_name.replace("-", "_").replace("_", " ").title().replace(" ", "_")

        with driver.session() as session:
            result = session.run(
                "MATCH (p:Wiki)-[:PART_OF]->(hc:Wiki {n: $hc_name}) "
                "WHERE p.n STARTS WITH 'Giint_Project_' "
                "RETURN p.n AS name",
                hc_name=normalized,
            )
            projects = {record["name"] for record in result}
        driver.close()
        logger.info("Active HC '%s' has projects: %s", normalized, projects)
        return projects
    except FileNotFoundError:
        logger.info("No active HC file at %s", ACTIVE_HC_FILE)
        return set()
    except Exception:
        logger.exception("Failed to get active HC projects")
        return set()


def _validate_hc_connection(concept: dict, concepts_by_name: dict,
                            active_projects: set[str]) -> list[str]:
    """Validate that a GIINT-typed concept connects to the active HC.

    Walks part_of chain up to GIINT_Project_ level and checks if that project
    is in the active HC. Returns error messages if disconnected.

    Exempt concepts (no validation needed):
    - Skill_, Pattern_ (standalone, no hierarchy)
    - GIINT_Project_ itself (validates directly against HC)
    - Concepts not matching any GIINT shape
    """
    name = concept["concept_name"]
    errors = []

    if not active_projects:
        return errors  # No HC set — can't validate

    # Find matching GIINT shape (case-insensitive prefix match)
    matched_shape = None
    matched_prefix = None
    name_lower = name.lower()
    for prefix, shape in GIINT_EC_SHAPES.items():
        if name_lower.startswith(prefix.lower()):
            matched_shape = shape
            matched_prefix = prefix
            break

    if matched_shape is None:
        return errors  # Not a GIINT-typed concept

    # Exempt standalone types (no parent_hint and no hierarchy requirement)
    if matched_prefix in ("Skill_", "Pattern_"):
        return errors

    # Normalize active_projects to lowercase for case-insensitive comparison
    # (CartON stores Title_Case, but emitted ECs may use UPPER_CASE)
    active_lower = {p.lower() for p in active_projects}

    # GIINT_Project_ itself: check if it's one of the active projects
    if _is_giint_project(name):
        if name.lower() not in active_lower:
            errors.append(
                f"❌ ERROR [{name}] is a GIINT_Project_ but NOT part_of active HC. "
                f"Active projects: {', '.join(sorted(active_projects))}. "
                f"Add part_of relationship to the active Hypercluster."
            )
        return errors

    # All other GIINT types: walk hierarchy up to GIINT_Project_
    hierarchy = _walk_hierarchy(concept, concepts_by_name)
    if not hierarchy:
        errors.append(
            f"❌ ERROR [{name}] has no part_of chain. "
            f"Every GIINT concept MUST connect to active HC via part_of."
        )
        return errors

    # Check if top of hierarchy is an active project
    top = hierarchy[0]
    if _is_giint_project(top):
        if top.lower() not in active_lower:
            errors.append(
                f"❌ ERROR [{name}] hierarchy reaches {top} which is NOT in active HC. "
                f"Active projects: {', '.join(sorted(active_projects))}. "
                f"Fix part_of to connect to active HC hierarchy."
            )
    else:
        errors.append(
            f"❌ ERROR [{name}] part_of chain does not reach any GIINT_Project_. "
            f"Chain: {' → '.join(hierarchy)}. Floating concept — will NOT appear in MEMORY.md."
        )

    return errors


def compile_concepts(concepts: list[dict], silenced: bool) -> tuple[list[str], int, int]:
    """Compile parsed concepts to CartON.

    Returns (results, compiled_count, warning_count).
    """
    results = []
    compiled_count = 0
    warning_count = 0

    # Batch Neo4j lookup for target descriptions
    all_targets = set()
    for concept in concepts:
        all_targets.update(concept.get("all_targets", []))
    existing_descs = batch_check_descs_in_carton(list(all_targets))

    add_concept = get_add_concept_func()

    # Index concepts by name for hierarchy walking
    concepts_by_name = {c["concept_name"]: c for c in concepts}

    # Get active HC projects for hierarchy validation
    active_projects = _get_active_hc_projects()
    # Also include any GIINT_Project_ in the current batch (being created now)
    for c in concepts:
        if _is_giint_project(c["concept_name"]):
            active_projects.add(c["concept_name"])

    # Get active starsystem for auto-linking
    active_starsystem = _get_active_starsystem_name()

    # Get active starlog session + project for temporal linking
    active_session_id = None
    active_starlog_project = None
    try:
        if COURSE_STATE_PATH.exists():
            cs = json.loads(COURSE_STATE_PATH.read_text())
            active_session_id = cs.get("active_starlog_session_id")
            # Resolve starlog project: explicit > derived from last_oriented
            proj = cs.get("active_starlog_project")
            if proj:
                # Normalize: no hyphens, Title_Case
                proj = proj.strip("/").replace("/", "_").replace("-", "_").replace(".", "_")
                proj = "_".join(s.title() if s.islower() else s for s in proj.split("_"))
                active_starlog_project = f"Starlog_Project_{proj}"
            elif cs.get("last_oriented"):
                # Derive from last_oriented path basename
                base = os.path.basename(cs["last_oriented"].rstrip("/"))
                base = base.replace("-", "_").replace(".", "_")
                base = "_".join(s.title() if s.islower() else s for s in base.split("_"))
                active_starlog_project = f"Starlog_Project_{base}"
    except Exception:
        pass

    for concept in concepts:
        # Inject GIINT types based on naming conventions
        concept, giint_errors = inject_giint_types(concept)
        if giint_errors:
            results.extend(giint_errors)
            warning_count += len(giint_errors)

        # Auto-inject part_of starsystem for Skill_ and GIINT_Project_ concepts
        # Skills need starsystem for mirroring. GIINT_Projects need it because
        # OWL requires partOf → Starsystem_Collection — without injection,
        # healing creates Starsystem_Unnamed instead of using the active one.
        if active_starsystem and (
            concept["concept_name"].startswith("Skill_")
            or _is_giint_project(concept["concept_name"])
        ):
            # Check if already has part_of pointing to a Starsystem_
            has_ss_partof = False
            for r in concept["relationships"]:
                if r["relationship"] == "part_of":
                    if any(t.startswith("Starsystem_") for t in r.get("related", [])):
                        has_ss_partof = True
                        break
            if not has_ss_partof:
                # Add starsystem to existing part_of or create new one
                for r in concept["relationships"]:
                    if r["relationship"] == "part_of":
                        r["related"].append(active_starsystem)
                        has_ss_partof = True
                        break
                if not has_ss_partof:
                    concept["relationships"].append({
                        "relationship": "part_of",
                        "related": [active_starsystem],
                    })
                logger.info("Auto-injected part_of %s on %s", active_starsystem, concept["concept_name"])

        # Auto-inject part_of starlog project (ALWAYS — observations always belong to a starlog)
        if active_starlog_project:
            has_slp = False
            for r in concept["relationships"]:
                if r["relationship"] == "part_of":
                    if not any(t.startswith("Starlog_Project_") for t in r.get("related", [])):
                        r["related"].append(active_starlog_project)
                    has_slp = True
                    break
            if not has_slp:
                concept["relationships"].append({
                    "relationship": "part_of",
                    "related": [active_starlog_project],
                })

        # Auto-inject part_of active starlog session (OPTIONAL — richer annotation when session is open)
        if active_session_id:
            session_concept = f"Starlog_Session_{active_session_id}"
            has_session_partof = False
            for r in concept["relationships"]:
                if r["relationship"] == "part_of":
                    if not any(t.startswith("Starlog_Session_") for t in r.get("related", [])):
                        r["related"].append(session_concept)
                    has_session_partof = True
                    break
            if not has_session_partof:
                concept["relationships"].append({
                    "relationship": "part_of",
                    "related": [session_concept],
                })

        # Validate HC connection for GIINT-typed concepts
        hc_errors = _validate_hc_connection(concept, concepts_by_name, active_projects)
        if hc_errors:
            results.extend(hc_errors)
            warning_count += len(hc_errors)

        # ALWAYS compile to CartON
        # Known GIINT/structural types MUST be validated by YOUKNOW (never hidden)
        name_lower = concept["concept_name"].lower()
        is_typed_ec = any(name_lower.startswith(p.lower()) for p in GIINT_EC_SHAPES)
        try:
            result = add_concept(
                concept_name=concept["concept_name"],
                description=concept["description"],
                relationships=concept["relationships"],
                desc_update_mode="append",
                hide_youknow=silenced and not is_typed_ec,
            )
            if not silenced:
                results.append(f"✅ [{concept['concept_name']}] {result}")
            compiled_count += 1
            logger.info("Compiled %s (silenced=%s)", concept["concept_name"], silenced)

# Sync GIINT typed concepts to GIINT JSON registry (keeps registry + CartON in sync)
            giint_level, _ = _strip_giint_prefix(concept["concept_name"])
            if giint_level and not silenced:
                hierarchy = _walk_hierarchy(concept, concepts_by_name)
                giint_sync_msg = _sync_to_giint_registry(concept, hierarchy)
                if giint_sync_msg:
                    results.append(f"📋 [GIINT] {concept['concept_name']}: {giint_sync_msg}")

# Extract is_a for downstream checks (flight step detection, TK card creation)
            concept_isa = []
            for r in concept["relationships"]:
                if r["relationship"] == "is_a":
                    concept_isa = r["related"]
                    break

# DEAD CODE — Commented out 2026-03-29. Python dict check for 5 SkillSpec fields duplicates SHACL SkillShape in uarl_shapes.ttl. The reasoner checks this via youknow() at compiler.py line 498-553.
            # if "Skill" in concept_isa and not silenced:
                # provided_rels = {r["relationship"].lower() for r in concept["relationships"]}
                # skillspec_required = {"has_domain", "has_category", "has_what", "has_when", "has_produces"}
                # missing = skillspec_required - provided_rels
                # if not missing:
                    # results.append(f"🔮 Skill queued: {concept['concept_name']}")
                # else:
                    # results.append(f"⏳ Skill incomplete [{concept['concept_name']}]: missing {', '.join(missing)}")

            # Detect flight step skills — skill with has_flight_step + part_of Flight_Config_*
            if "Skill" in concept_isa:
                flight_step_num = None
                flight_config_name = None
                for r in concept["relationships"]:
                    if r["relationship"] == "has_flight_step":
                        flight_step_num = r["related"][0] if r.get("related") else None
                    if r["relationship"] == "part_of":
                        for t in r.get("related", []):
                            if t.startswith("Flight_Config_"):
                                flight_config_name = t
                if flight_step_num and flight_config_name:
                    if not silenced:
                        results.append(
                            f"🛫 Flight step: {concept['concept_name']} → "
                            f"step {flight_step_num} of {flight_config_name}")
                    logger.info("Flight step detected: %s → step %s of %s",
                                concept["concept_name"], flight_step_num, flight_config_name)
                    # CartON compilation IS the registration — has_flight_step + part_of Flight_Config_X
                    # are persisted as relationships. CartON automations handle the rest.

            # TK card creation + Canopy mirror now handled by GIINT library
            # via _sync_to_giint_registry → add_deliverable_to_component → _create_tk_card_for_deliverable
        except Exception:
            logger.exception("Error compiling %s", concept["concept_name"])
            results.append(f"❌ [{concept['concept_name']}] ERROR: {traceback.format_exc()}")

        # Rule #6: Write claim descs to target concepts
        for target_name, target_desc in concept.get("target_descs", {}).items():
            try:
                add_concept(
                    concept_name=target_name,
                    description=target_desc,
                    relationships=[{"relationship": "relates_to",
                                    "related": [concept["concept_name"]]}],
                    desc_update_mode="append",
                    hide_youknow=True,
                )
                logger.info("Rule#6 enriched %s from %s", target_name, concept["concept_name"])
            except Exception:
                logger.exception("Failed to enrich target %s", target_name)

        # Warnings only shown when UNSILENCED
        if not silenced:
            if concept["description"].startswith("[NO DESC]"):
                results.append(
                    f"❌ ERROR [{concept['concept_name']}] HAS NO DESCRIPTION. "
                    f"FIX NOW: add desc='''...''' to at least one claim.")
                warning_count += 1

            missing = concept.get("missing_descs", [])
            if missing:
                actually_missing = []
                for m in missing:
                    target = m.split("=", 1)[1] if "=" in m else m
                    if target not in existing_descs:
                        actually_missing.append(m)
                if actually_missing:
                    results.append(
                        f"❌ [{concept['concept_name']}] Claims WITHOUT desc: "
                        f"{', '.join(actually_missing)}. ADD DESC NOW.")
                    warning_count += 1

            invalid = concept.get("invalid_rels", [])
            if invalid:
                results.append(
                    f"❌ [{concept['concept_name']}] Non-UARL dropped: "
                    f"{', '.join(invalid)}")
                warning_count += 1

            undescribed = [t for t in concept.get("all_targets", [])
                           if t not in existing_descs]
            if undescribed:
                results.append(
                    f"❌ [{concept['concept_name']}] Targets needing desc: "
                    f"{', '.join(sorted(set(undescribed)))}")
                warning_count += 1

    # Side effect: flush all compiled concepts to starlog layer as debug diary entries
    _flush_to_starlog_diary(concepts, active_starlog_project)

    return results, compiled_count, warning_count


GIINT_PREFIXES = {
    "GIINT_Project_": "project",
    "GIINT_Feature_": "feature",
    "GIINT_Component_": "component",
    "GIINT_Deliverable_": "deliverable",
    "GIINT_Task_": "task",
}


def _strip_giint_prefix(name: str) -> tuple[str | None, str]:
    """Strip GIINT prefix, return (level, stripped_name)."""
    name_lower = name.lower()
    for prefix, level in GIINT_PREFIXES.items():
        if name_lower.startswith(prefix.lower()):
            return level, name[len(prefix):]
    return None, name


def _sync_to_giint_registry(concept: dict, hierarchy: list[str]) -> str | None:
    """Sync a GIINT typed concept to the GIINT JSON registry via library functions.

    Extracts project_id/feature/component/deliverable/task from the hierarchy chain.
    Returns status message or None on failure.
    """
    try:
        from llm_intelligence.projects import (
            create_project, add_feature_to_project, add_component_to_feature,
            add_deliverable_to_component, add_task_to_deliverable,
            get_project_by_dir,
        )
    except ImportError:
        logger.warning("llm_intelligence not available — skipping GIINT registry sync")
        return None

    # Build hierarchy params from chain (top-down: Project > Feature > Component > Deliverable > Task)
    params = {}
    for name in hierarchy:
        level, stripped = _strip_giint_prefix(name)
        if level:
            params[level] = stripped

    if "project" not in params:
        return None  # Can't sync without a project

    concept_level, _ = _strip_giint_prefix(concept["concept_name"])
    if not concept_level:
        return None

    try:
        project_id = params["project"]

        # Resolve project_dir from .course_state
        project_dir = ""
        try:
            if COURSE_STATE_PATH.exists():
                cs = json.loads(COURSE_STATE_PATH.read_text())
                project_dir = cs.get("last_oriented", "")
        except Exception:
            pass

        if concept_level == "project":
            result = create_project(project_id=project_id, project_dir=project_dir or "/tmp")
        elif concept_level == "feature" and "feature" in params:
            result = add_feature_to_project(project_id, params["feature"])
        elif concept_level == "component" and "feature" in params and "component" in params:
            result = add_component_to_feature(project_id, params["feature"], params["component"])
        elif concept_level == "deliverable" and all(k in params for k in ("feature", "component", "deliverable")):
            result = add_deliverable_to_component(project_id, params["feature"], params["component"], params["deliverable"])
        elif concept_level == "task" and all(k in params for k in ("feature", "component", "deliverable", "task")):
            result = add_task_to_deliverable(
                project_id, params["feature"], params["component"], params["deliverable"],
                params["task"], assignee="AI-Only", agent_id="gnosys"
            )
        else:
            return None

        success = result.get("success", False)
        msg = result.get("message", result.get("error", ""))
        if success:
            logger.info("GIINT registry synced: %s → %s", concept["concept_name"], msg)
        else:
            logger.info("GIINT registry sync skipped: %s → %s", concept["concept_name"], msg)
        return msg

    except Exception as e:
        logger.warning("GIINT registry sync failed for %s: %s", concept["concept_name"], e)
        return None


def _flush_to_starlog_diary(concepts: list[dict], active_starlog_project: str | None) -> None:
    """After compilation, create debug diary entries for each entity chain.

    Each entry captures: what was compiled, what side effects occurred, file paths mentioned.
    Routes through starlog's existing starsystem detection for JIT joint starlog resolution.
    """
    if not concepts:
        return
    try:
        from starlog_mcp.starlog import Starlog
        from starlog_mcp.models import DebugDiaryEntry
        from starlog_mcp.starlog_sessions import (
            detect_starsystems_for_entry, get_joint_starlog_name,
        )
        from datetime import datetime

        sl = Starlog()
        stardate = sl._generate_stardate()

        for concept in concepts:
            name = concept["concept_name"]
            desc = concept.get("description", "")[:200]

            # Detect entry type and side effects from is_a
            concept_isa = []
            for r in concept.get("relationships", []):
                if r["relationship"] == "is_a":
                    concept_isa = r.get("related", [])

            # Map is_a to entry_type
            type_map = {
                "Bug": "bug", "Potential_Solution": "potential_solution",
                "Skill": "skill", "GIINT_Deliverable": "deliverable",
                "GIINT_Task": "task", "Design": "design",
                "Idea": "idea", "Inclusion_Map": "inclusion_map",
            }
            entry_type = "observation"
            for isa_type, etype in type_map.items():
                if isa_type in concept_isa:
                    entry_type = etype
                    break

            side_effects = []
            if "Skill" in concept_isa:
                side_effects.append("skill_compiled")
            if "GIINT_Deliverable" in concept_isa:
                side_effects.append("tk_card_created")

            effects_str = f" Effects: [{', '.join(side_effects)}]." if side_effects else ""

            entry_content = (
                f"Captain's Log, stardate {stardate}: "
                f"[{entry_type}] Dragonbones compiled {name}.{effects_str} "
                f"{desc}"
            )

            # Detect starsystems from file paths in description
            detected = detect_starsystems_for_entry(desc, None)

            if len(detected) > 1:
                # Multi-starsystem — route to joint starlog project
                joint_name = get_joint_starlog_name(list(detected.keys()))
                try:
                    from heaven_base.tools.registry_tool import registry_util_func
                    registry_util_func("create_registry", registry_name=f"{joint_name}_debug_diary")
                except Exception:
                    pass
                project_name = joint_name
            elif detected:
                project_name = list(detected.keys())[0]
            elif active_starlog_project:
                # Strip Starlog_Project_ prefix to get registry project name
                project_name = active_starlog_project.replace("Starlog_Project_", "")
            else:
                continue  # No starsystem context, skip

            entry = DebugDiaryEntry(
                content=entry_content,
                entry_type=entry_type,
                source="dragonbones",
                concept_ref=name,
                bug_report=(entry_type == "bug"),
            )
            sl._save_debug_diary_entry(project_name, entry)

    except Exception as e:
        logger.warning(f"Starlog diary flush failed (non-fatal): {e}")
