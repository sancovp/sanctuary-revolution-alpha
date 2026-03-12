#!/usr/bin/env python3
"""
Reward System - STARSYSTEM Health + Legacy Event Scoring

NEW (State-based): get_starsystem_health()
  - Measures CURRENT project health, not accumulated events
  - Formula: emanation×0.30 + smells×0.25 + arch×0.20 + complexity×0.15 + kg_depth×0.10

DEPRECATED (Event-based): compute_fitness(), compute_session_reward(), etc.
  - Old approach counting tool calls
  - Kept for backward compatibility during transition

This file is edited directly to optimize the reward system (self-play).
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)


def _carton_query(cypher: str, parameters: dict = None) -> dict:
    """Query CartON wiki graph via singleton Neo4j connection."""
    try:
        from carton_mcp.carton_utils import CartOnUtils
        utils = CartOnUtils()
        return utils.query_wiki_graph(cypher, parameters)
    except Exception as e:
        logger.warning(f"CartON query failed: {e}")
        return {"success": False, "data": []}


# ============================================================================
# STARSYSTEM HEALTH - State-based scoring (NEW)
# ============================================================================

def get_starsystem_health(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Compute health score for a STARSYSTEM (0.0 - 1.0).

    This is STATE-BASED scoring - measures current project health,
    not accumulated events. Score updates immediately when you fix things.

    Formula:
        health = emanation×0.30 + smells×0.25 + arch×0.20 + complexity×0.15 + kg_depth×0.10

    Args:
        path: STARSYSTEM directory path (defaults to cwd)

    Returns:
        Dict with health score and component breakdown
    """
    if path is None:
        path = os.getcwd()

    path = Path(path)

    # KG queries go through CartON MCP HTTP — no direct Neo4j

    # Component scores (0.0 - 1.0 each)
    components = {}

    # 1. EMANATION COVERAGE (0.30 weight)
    components["emanation"] = _get_emanation_score()

    # 2. SMELL CLEANLINESS (0.25 weight)
    components["smells"] = _get_smell_score(path)

    # 3. ARCHITECTURE COMPLIANCE (0.20 weight)
    components["architecture"] = _get_architecture_score(path)

    # 4. COMPLEXITY LEVEL (0.15 weight) - L0=0, L6=1.0
    components["complexity"] = _get_complexity_score(path)

    # 5. KNOWLEDGE GRAPH DEPTH (0.10 weight)
    components["kg_depth"] = _get_kg_depth_score(path, components["complexity"])

    # Calculate weighted health
    health = (
        components["emanation"] * 0.30 +
        components["smells"] * 0.25 +
        components["architecture"] * 0.20 +
        components["complexity"] * 0.15 +
        components["kg_depth"] * 0.10
    )

    return {
        "health": round(health, 3),
        "health_percent": round(health * 100, 1),
        "path": str(path),
        "components": components,
        "weights": {
            "emanation": 0.30,
            "smells": 0.25,
            "architecture": 0.20,
            "complexity": 0.15,
            "kg_depth": 0.10
        }
    }


def _get_emanation_score() -> float:
    """Get emanation coverage as 0-1 score."""
    try:
        from llm_intelligence.carton_sync import get_emanation_gaps
        result = get_emanation_gaps()
        if result.get("success"):
            gaps = result.get("gaps", {})
            coverage = gaps.get("coverage_percent", 0)
            return coverage / 100.0
        return 0.0
    except Exception as e:
        logger.warning(f"Could not get emanation score: {e}")
        return 0.5  # Neutral if unavailable


def _get_smell_score(path: Path) -> float:
    """
    Get code smell cleanliness as 0-1 score using real codenose detection.

    Severity weights:
    - Critical (syntax, syspath, traceback): -0.2 each
    - Warning (arch, facade): -0.05 each
    - Info (dup, long, import): -0.01 each
    """
    try:
        from codenose import CodeNose
        nose = CodeNose()
        result = nose.scan(str(path))
        return result.cleanliness_score if hasattr(result, 'cleanliness_score') else 0.5

    except ImportError:
        # Fallback to simple line count heuristic
        logger.warning("Codenose not available, using line count fallback")
        try:
            py_files = list(path.rglob("*.py"))
            if not py_files:
                return 1.0

            total_files = 0
            files_with_smells = 0

            for f in py_files[:50]:
                try:
                    lines = len(f.read_text().splitlines())
                    total_files += 1
                    if lines > 500:
                        files_with_smells += 1
                except:
                    pass

            if total_files == 0:
                return 1.0

            clean_ratio = (total_files - files_with_smells) / total_files
            return round(clean_ratio, 3)
        except Exception:
            return 0.5

    except Exception as e:
        logger.warning(f"Could not get smell score: {e}", exc_info=True)
        return 0.5


def _get_architecture_score(path: Path) -> float:
    """
    Get onion architecture compliance as 0-1 score.

    TODO: Implement real architecture analysis:
    - Check for utils.py → core.py → facade pattern
    - Detect logic in wrong layers
    - Check for god classes

    Current: Placeholder returning 0.5
    """
    # TODO: Real implementation
    # For now, check if canonical structure exists
    try:
        has_core = (path / "core.py").exists() or any(path.rglob("core.py"))
        has_utils = (path / "utils.py").exists() or any(path.rglob("utils.py"))

        if has_core and has_utils:
            return 0.7  # Has structure, assume decent
        elif has_core or has_utils:
            return 0.5  # Partial structure
        else:
            return 0.3  # No obvious structure
    except:
        return 0.5


def _get_complexity_score(path: Path) -> float:
    """
    Detect complexity level (L0-L6) by checking .claude/ inventory against CartON.

    Two-part check:
    A) Inventory .claude/ folder - check each item exists in CartON with correct relationships
    B) Query CartON for remote emanations - things that describe this project but live elsewhere

    L0 = 0.0:   Nothing in .claude/ or CartON
    L1 = 0.17:  Has skill(s) properly connected
    L2 = 0.33:  Has skill + flight config
    L3 = 0.67:  Has MCP or TreeShell + flights
    L4 = 0.83:  Has persona properly connected
    L5 = 0.92:  Has scoring + goldenization
    L6 = 1.0:   Deployed, documented, distributed
    """
    try:
        # Convert path to starsystem concept name (Title_Case to match CartON convention)
        path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        starsystem_name = f"Starsystem_{path_slug}"

        # PART A: Inventory .claude/ folder
        claude_dir = path / ".claude"
        local_skills = []
        local_agents = []
        local_hooks = []
        local_commands = []

        if claude_dir.exists():
            skills_dir = claude_dir / "skills"
            if skills_dir.exists():
                local_skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]

            agents_dir = claude_dir / "agents"
            if agents_dir.exists():
                local_agents = [f.stem for f in agents_dir.glob("*.md")]

            hooks_dir = claude_dir / "hooks"
            if hooks_dir.exists():
                local_hooks = [f.stem for f in hooks_dir.glob("*.py")]

            commands_dir = claude_dir / "commands"
            if commands_dir.exists():
                local_commands = [f.stem for f in commands_dir.glob("*.md")]

        # PART B: Query CartON for what's connected to this starsystem
        # This includes both local items that were synced AND remote emanations
        cypher = """
        MATCH (s:Wiki {n: $starsystem_name})
        OPTIONAL MATCH (skill:Wiki)-[:PART_OF|DESCRIBES]->(s) WHERE (skill)-[:IS_A]->(:Wiki {n: "Skill"})
        OPTIONAL MATCH (agent:Wiki)-[:PART_OF|DESCRIBES]->(s) WHERE (agent)-[:IS_A]->(:Wiki {n: "Agent"})
        OPTIONAL MATCH (hook:Wiki)-[:PART_OF|DESCRIBES]->(s) WHERE (hook)-[:IS_A]->(:Wiki {n: "Hook"})
        OPTIONAL MATCH (cmd:Wiki)-[:PART_OF|DESCRIBES]->(s) WHERE (cmd)-[:IS_A]->(:Wiki {n: "Slash_Command"})
        OPTIONAL MATCH (flight:Wiki)-[:PART_OF|AUTOMATES]->(s) WHERE (flight)-[:IS_A]->(:Wiki {n: "Flight_Config"})
        OPTIONAL MATCH (persona:Wiki)-[:CONFIGURES]->(s) WHERE (persona)-[:IS_A]->(:Wiki {n: "Persona"})
        OPTIONAL MATCH (mcp:Wiki)-[:PART_OF|PROVIDES_TOOLS_TO]->(s) WHERE (mcp)-[:IS_A]->(:Wiki {n: "MCP_Server"})
        RETURN
            count(DISTINCT skill) as carton_skills,
            count(DISTINCT agent) as carton_agents,
            count(DISTINCT hook) as carton_hooks,
            count(DISTINCT cmd) as carton_commands,
            count(DISTINCT flight) as carton_flights,
            count(DISTINCT persona) as carton_personas,
            count(DISTINCT mcp) as carton_mcps
        """

        result = _carton_query(cypher, {"starsystem_name": starsystem_name})

        carton_skills = 0
        carton_agents = 0
        carton_flights = 0
        carton_personas = 0
        carton_mcps = 0

        if result and result.get("success") and result.get("data"):
            data = result["data"][0] if result["data"] else {}
            carton_skills = data.get("carton_skills", 0)
            carton_agents = data.get("carton_agents", 0)
            carton_flights = data.get("carton_flights", 0)
            carton_personas = data.get("carton_personas", 0)
            carton_mcps = data.get("carton_mcps", 0)

        # Total emanations = local inventory + remote from CartON
        total_skills = max(len(local_skills), carton_skills)
        total_agents = max(len(local_agents), carton_agents)
        total_flights = carton_flights  # flights typically not in .claude/
        total_personas = carton_personas
        total_mcps = carton_mcps

        # Determine level based on what's properly connected
        if total_personas > 0:
            return 0.83  # L4 - Has persona
        elif total_mcps > 0 and total_flights > 0:
            return 0.67  # L3 - Has MCP + flights
        elif total_skills > 0 and total_flights > 0:
            return 0.33  # L2 - Has skill + flight
        elif total_skills > 0 or total_agents > 0:
            return 0.17  # L1 - Has skill or agent
        else:
            return 0.0   # L0 - Nothing

    except Exception as e:
        logger.warning(f"Could not get complexity score: {e}")
        return 0.0


def _get_kg_depth_score(path: Path, complexity_score: float = None) -> float:
    """
    Get CartON knowledge graph depth for this STARSYSTEM.

    Formula (from SHIP_PATH.md):
        kg_depth = (
            giint_hierarchy_completeness × 0.40 +
            emanation_level × 0.40 +
            inter_starsystem_relations × 0.20
        )

    Components:
    - giint_hierarchy_completeness: How much GIINT structure exists (features/components/deliverables)
    - emanation_level: Average complexity ladder level per component (skills DESCRIBES components)
    - inter_starsystem_relations: Is this STARSYSTEM connected to others?
    """
    try:
        giint_score = _get_giint_hierarchy_completeness(path)
        emanation_score = complexity_score if complexity_score is not None else _get_complexity_score(path)
        inter_starsystem_score = _get_inter_starsystem_relations(path)

        kg_depth = (
            giint_score * 0.40 +
            emanation_score * 0.40 +
            inter_starsystem_score * 0.20
        )

        return round(kg_depth, 3)
    except Exception as e:
        logger.warning(f"Could not get KG depth score: {e}")
        return 0.5


def _get_giint_hierarchy_completeness(path: Path) -> float:
    """
    Query CartON for GIINT hierarchy completeness of STARSYSTEM at path.

    CartON is the query layer - GIINT mirrors its data there.
    Looks for: GIINT_Project, Feature, Component, Deliverable concepts
    linked to this STARSYSTEM.

    Score based on: features > 0, components > 0, deliverables > 0, tasks > 0
    Returns 0.0 if no GIINT project, 1.0 if fully populated.
    """
    try:
        path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        starsystem_name = f"Starsystem_{path_slug}"

        cypher = """
        MATCH (s:Wiki {n: $starsystem_name})
        MATCH (gp:Wiki)-[:PART_OF]->(s) WHERE gp.n STARTS WITH 'GIINT_Project'
        MATCH (f:Wiki)-[:PART_OF]->(s) WHERE f.n CONTAINS 'Feature' OR (f)-[:IS_A]->(:Wiki {n: 'Feature'})
        MATCH (c:Wiki)-[:PART_OF]->(s) WHERE c.n CONTAINS 'Component' OR (c)-[:IS_A]->(:Wiki {n: 'Component'})
        MATCH (d:Wiki)-[:PART_OF]->(s) WHERE d.n CONTAINS 'Deliverable' OR (d)-[:IS_A]->(:Wiki {n: 'Deliverable'})
        RETURN
            count(DISTINCT gp) as giint_projects,
            count(DISTINCT f) as features,
            count(DISTINCT c) as components,
            count(DISTINCT d) as deliverables
        """

        result = _carton_query(cypher, {"starsystem_name": starsystem_name})

        if result and result.get("success") and result.get("data"):
            data = result["data"][0] if result["data"] else {}
            giint_projects = data.get("giint_projects", 0)
            features = data.get("features", 0)
            components = data.get("components", 0)
            deliverables = data.get("deliverables", 0)

            # Score: 0.25 per level that has at least 1 element
            score = 0.0
            if giint_projects > 0:
                score += 0.25
            if features > 0:
                score += 0.25
            if components > 0:
                score += 0.25
            if deliverables > 0:
                score += 0.25

            return score

        return 0.0

    except Exception as e:
        logger.warning(f"Could not get GIINT hierarchy completeness: {e}")
        return 0.0


def _get_emanation_level_per_component(path: Path, complexity_score: float = None) -> float:
    """
    Query CartON for skills that DESCRIBES components in this STARSYSTEM.

    Currently uses pre-computed complexity score as proxy.
    Future: MATCH (s:Wiki)-[:DESCRIBES]->(c:Wiki) WHERE c.d CONTAINS $path

    Returns average emanation level across components.
    """
    if complexity_score is not None:
        return complexity_score
    return 0.0


def _get_inter_starsystem_relations(path: Path) -> float:
    """
    Query CartON for relationships between this STARSYSTEM and others.

    Looks for: DEPENDS_ON, USES, INTEGRATES_WITH relationships
    between STARSYSTEM entities.

    Returns 0.0 if isolated, 1.0 if well-connected.
    """
    try:
        path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        starsystem_name = f"Starsystem_{path_slug}"

        cypher = """
        MATCH (s:Wiki {n: $name})-[r]->(other:Wiki)
        WHERE other.n STARTS WITH 'Starsystem_'
        AND type(r) IN ['DEPENDS_ON', 'USES', 'INTEGRATES_WITH', 'RELATES_TO']
        RETURN count(r) as outgoing
        """

        result = _carton_query(cypher, {"name": starsystem_name})

        if result and "data" in result:
            outgoing = result["data"][0].get("outgoing", 0) if result["data"] else 0
            # Score: 0.0 for 0 relations, 0.5 for 1-2, 1.0 for 3+
            if outgoing >= 3:
                return 1.0
            elif outgoing >= 1:
                return 0.5
            else:
                return 0.0

        return 0.0

    except Exception as e:
        logger.warning(f"Could not get inter-STARSYSTEM relations: {e}")
        return 0.0


SMELL_CACHE_PATH = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "codenose_cache.json"


def get_fleet_health(paths: List[str]) -> Dict[str, Dict[str, Any]]:
    """Compute health scores for ALL starships in a single batch.

    Replaces N individual get_starsystem_health() calls with:
    - 1 emanation score call (global, not per-path)
    - 1 UNWIND Cypher query for all KG-based scores (complexity + giint + inter)
    - N cheap filesystem checks (rglob for architecture, iterdir for .claude/)
    - N cached smell score reads (from daemon-maintained cache)

    Args:
        paths: List of STARSYSTEM directory paths

    Returns:
        Dict mapping path -> health data (same format as get_starsystem_health)
    """
    if not paths:
        return {}

    # KG queries go through CartON MCP HTTP — no direct Neo4j

    # 1. Emanation score — GLOBAL, call once for all starships
    emanation_score = _get_emanation_score()

    # 2. Build starsystem concept names for all paths
    path_to_name = {}
    for p in paths:
        path_obj = Path(p)
        path_slug = str(path_obj).strip("/").replace("/", "_").replace("-", "_").title()
        path_to_name[p] = f"Starsystem_{path_slug}"

    # 3. Single UNWIND Cypher for all KG-based scores
    # Chained WITH clauses prevent cartesian products between OPTIONAL MATCHes
    kg_results = {}
    all_names = list(path_to_name.values())

    if all_names:
        cypher = """
        UNWIND $names AS ss_name
        OPTIONAL MATCH (s:Wiki {n: ss_name})
        WITH ss_name, s

        OPTIONAL MATCH (skill:Wiki)-[:PART_OF|DESCRIBES]->(s)
        WHERE (skill)-[:IS_A]->(:Wiki {n: "Skill"})
        WITH ss_name, s, count(DISTINCT skill) as skills

        OPTIONAL MATCH (agent:Wiki)-[:PART_OF|DESCRIBES]->(s)
        WHERE (agent)-[:IS_A]->(:Wiki {n: "Agent"})
        WITH ss_name, s, skills, count(DISTINCT agent) as agents

        OPTIONAL MATCH (flight:Wiki)-[:PART_OF|AUTOMATES]->(s)
        WHERE (flight)-[:IS_A]->(:Wiki {n: "Flight_Config"})
        WITH ss_name, s, skills, agents, count(DISTINCT flight) as flights

        OPTIONAL MATCH (persona:Wiki)-[:CONFIGURES]->(s)
        WHERE (persona)-[:IS_A]->(:Wiki {n: "Persona"})
        WITH ss_name, s, skills, agents, flights, count(DISTINCT persona) as personas

        OPTIONAL MATCH (mcp_srv:Wiki)-[:PART_OF|PROVIDES_TOOLS_TO]->(s)
        WHERE (mcp_srv)-[:IS_A]->(:Wiki {n: "MCP_Server"})
        WITH ss_name, s, skills, agents, flights, personas, count(DISTINCT mcp_srv) as mcps

        OPTIONAL MATCH (gp:Wiki)-[:PART_OF]->(s)
        WHERE gp.n STARTS WITH 'GIINT_Project'
        WITH ss_name, s, skills, agents, flights, personas, mcps,
             count(DISTINCT gp) as giint_projects

        OPTIONAL MATCH (feat:Wiki)-[:PART_OF]->(s)
        WHERE feat.n CONTAINS 'Feature' OR (feat)-[:IS_A]->(:Wiki {n: 'Feature'})
        WITH ss_name, s, skills, agents, flights, personas, mcps, giint_projects,
             count(DISTINCT feat) as features

        OPTIONAL MATCH (comp:Wiki)-[:PART_OF]->(s)
        WHERE comp.n CONTAINS 'Component' OR (comp)-[:IS_A]->(:Wiki {n: 'Component'})
        WITH ss_name, s, skills, agents, flights, personas, mcps, giint_projects,
             features, count(DISTINCT comp) as components

        OPTIONAL MATCH (deliv:Wiki)-[:PART_OF]->(s)
        WHERE deliv.n CONTAINS 'Deliverable' OR (deliv)-[:IS_A]->(:Wiki {n: 'Deliverable'})
        WITH ss_name, s, skills, agents, flights, personas, mcps, giint_projects,
             features, components, count(DISTINCT deliv) as deliverables

        OPTIONAL MATCH (s)-[isr]->(other:Wiki)
        WHERE other.n STARTS WITH 'Starsystem_'
        AND type(isr) IN ['DEPENDS_ON', 'USES', 'INTEGRATES_WITH', 'RELATES_TO']

        RETURN ss_name, skills, agents, flights, personas, mcps,
               giint_projects, features, components, deliverables,
               count(DISTINCT isr) as inter_relations
        """

        try:
            result = _carton_query(cypher, {"names": all_names})
            if result and result.get("success") and result.get("data"):
                for row in result["data"]:
                    kg_results[row["ss_name"]] = row
        except Exception as e:
            logger.warning(f"Fleet UNWIND query failed: {e}")

    # 4. Compute per-path health from batched data
    results = {}
    for p in paths:
        path_obj = Path(p)
        ss_name = path_to_name[p]
        kg = kg_results.get(ss_name, {})

        complexity = _compute_complexity_from_kg(path_obj, kg)
        arch = _get_architecture_score(path_obj)
        smells = _get_cached_smell_score(p)
        giint = _compute_giint_from_kg(kg)
        inter = _compute_inter_from_kg(kg)

        kg_depth = round(giint * 0.40 + complexity * 0.40 + inter * 0.20, 3)

        health = (
            emanation_score * 0.30 +
            smells * 0.25 +
            arch * 0.20 +
            complexity * 0.15 +
            kg_depth * 0.10
        )

        results[p] = {
            "health": round(health, 3),
            "health_percent": round(health * 100, 1),
            "path": p,
            "components": {
                "emanation": emanation_score,
                "smells": smells,
                "architecture": arch,
                "complexity": complexity,
                "kg_depth": kg_depth,
            },
            "weights": {
                "emanation": 0.30,
                "smells": 0.25,
                "architecture": 0.20,
                "complexity": 0.15,
                "kg_depth": 0.10,
            }
        }

    return results


def _compute_complexity_from_kg(path: Path, kg_data: dict) -> float:
    """Compute complexity score from pre-fetched KG data + local .claude/ inventory."""
    claude_dir = path / ".claude"
    local_skills = []
    local_agents = []

    if claude_dir.exists():
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            try:
                local_skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
            except Exception:
                pass
        agents_dir = claude_dir / "agents"
        if agents_dir.exists():
            try:
                local_agents = [f.stem for f in agents_dir.glob("*.md")]
            except Exception:
                pass

    total_skills = max(len(local_skills), kg_data.get("skills", 0))
    total_agents = max(len(local_agents), kg_data.get("agents", 0))
    total_flights = kg_data.get("flights", 0)
    total_personas = kg_data.get("personas", 0)
    total_mcps = kg_data.get("mcps", 0)

    if total_personas > 0:
        return 0.83  # L4
    elif total_mcps > 0 and total_flights > 0:
        return 0.67  # L3
    elif total_skills > 0 and total_flights > 0:
        return 0.33  # L2
    elif total_skills > 0 or total_agents > 0:
        return 0.17  # L1
    else:
        return 0.0   # L0


def _compute_giint_from_kg(kg_data: dict) -> float:
    """Compute GIINT hierarchy completeness from pre-fetched KG data."""
    score = 0.0
    if kg_data.get("giint_projects", 0) > 0:
        score += 0.25
    if kg_data.get("features", 0) > 0:
        score += 0.25
    if kg_data.get("components", 0) > 0:
        score += 0.25
    if kg_data.get("deliverables", 0) > 0:
        score += 0.25
    return score


def _compute_inter_from_kg(kg_data: dict) -> float:
    """Compute inter-starsystem relations from pre-fetched KG data."""
    outgoing = kg_data.get("inter_relations", 0)
    if outgoing >= 3:
        return 1.0
    elif outgoing >= 1:
        return 0.5
    return 0.0


def _get_cached_smell_score(path: str) -> float:
    """Read cached smell score from daemon-maintained cache file.

    Cache at HEAVEN_DATA_DIR/codenose_cache.json is written by omnisanc
    daemon on heartbeat. Returns 0.5 (neutral) if no cache exists.
    """
    try:
        if SMELL_CACHE_PATH.exists():
            cache = json.loads(SMELL_CACHE_PATH.read_text())
            entry = cache.get(path, {})
            if isinstance(entry, dict):
                return entry.get("score", 0.5)
            elif isinstance(entry, (int, float)):
                return float(entry)
    except Exception:
        pass
    return 0.5


def format_health_hud(health_data: Dict[str, Any]) -> str:
    """Format health score as HUD string with RAW SCORES."""
    h = health_data
    c = h["components"]

    lines = [
        f"🏆 HEALTH: {h['health']:.2f}",
        f"   🎯 Emanation: {c['emanation']:.2f}",
        f"   👃 Smells: {c['smells']:.2f}",
        f"   🏛️ Arch: {c['architecture']:.2f}",
        f"   📊 L{_score_to_level(c['complexity'])} | {c['complexity']:.2f}",
        f"   🧠 KG: {c['kg_depth']:.2f}",
    ]
    return "\n".join(lines)


def _score_to_level(score: float) -> str:
    """Convert complexity score back to level string."""
    if score >= 0.92:
        return "5+"
    elif score >= 0.83:
        return "4"
    elif score >= 0.67:
        return "3"
    elif score >= 0.50:
        return "2.5"
    elif score >= 0.33:
        return "2"
    elif score >= 0.17:
        return "1"
    else:
        return "0"


# ============================================================================
# EVENT REWARDS - Base scores for individual events (DEPRECATED)
# ============================================================================

EVENT_REWARDS = {
    # Mission events (highest value)
    "mission_start": 100,
    "mission_report_progress": 50,  # per step completed
    "mission_complete": 500,
    "mission_inject_step": -20,  # penalty for course correction
    "mission_request_extraction": -200,  # penalty for abandonment

    # Session events (medium value)
    "start_starlog": 20,
    "end_starlog": 100,  # bonus for proper completion
    "update_debug_diary": 5,

    # Waypoint events
    "start_waypoint_journey": 10,
    "navigate_to_next_waypoint": 15,  # per waypoint
    "abort_waypoint_journey": -30,

    # Home events (low value - encourages progression)
    "plot_course": 50,  # reward for starting journey

    # Quality penalties
    "omnisanc_error": -10,
    "validation_block": -5,  # attempted disallowed tool
}

# ============================================================================
# XP MULTIPLIERS
# ============================================================================

HOME_MULTIPLIER = 1.0
SESSION_MULTIPLIER = 3.0
MISSION_MULTIPLIER = 10.0

# ============================================================================
# FITNESS CONDITIONS - Dynamically added to optimize score
# ============================================================================

FITNESS_CONDITIONS = [
    "complete_sessions",  # +100 per completed session
    "complete_missions",  # +500 per completed mission
    "low_error_rate",     # +quality_multiplier
]

# ============================================================================
# STATS AGGREGATION
# ============================================================================

def get_events_from_registry(registry_service, registry_base: str, date: str) -> List[Dict]:
    """
    Get all events from a specific registry for a date.

    Args:
        registry_service: RegistryService instance
        registry_base: "home_events", "mission_events", or "session_events"
        date: Date string (YYYY-MM-DD)

    Returns:
        List of event dictionaries
    """
    day_registry_name = f"{registry_base}_{date}"
    events = []

    if registry_service.simple_service.registry_exists(day_registry_name):
        all_data = registry_service.get_all(day_registry_name)

        for event_key, event_data in all_data.items():
            if event_key != "_meta" and isinstance(event_data, dict):
                event_data["_registry"] = registry_base
                event_data["_key"] = event_key
                events.append(event_data)

    return events


def compute_stats(registry_service, start_date: str, end_date: str = None) -> Dict[str, Any]:
    """
    Compute aggregated stats from event registries.

    Args:
        registry_service: RegistryService instance
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to start_date

    Returns:
        Dictionary of computed statistics
    """
    if end_date is None:
        end_date = start_date

    # For now, just handle single day (can expand later)
    all_events = []

    for registry_base in ["home_events", "mission_events", "session_events"]:
        events = get_events_from_registry(registry_service, registry_base, start_date)
        all_events.extend(events)

    # Sort by timestamp
    all_events.sort(key=lambda x: x.get("timestamp", ""))

    # Count tools
    def count_tool(tool_name: str, **filters) -> int:
        count = 0
        for event in all_events:
            if event.get("tool_name", "").endswith(tool_name):
                # Check filters
                match = True
                for key, value in filters.items():
                    if event.get(key) != value:
                        match = False
                        break
                if match:
                    count += 1
        return count

    # Mission metrics
    missions_started = count_tool("mission_start")
    missions_extracted = count_tool("mission_request_extraction")
    missions_completed = count_tool("mission_report_progress")  # TODO: check if final step

    # Session metrics
    sessions_started = count_tool("start_starlog")
    sessions_ended = count_tool("end_starlog")

    # Waypoint metrics
    waypoints_started = count_tool("start_waypoint_journey")
    waypoints_aborted = count_tool("abort_waypoint_journey")

    # Error metrics
    omnisanc_errors = len([e for e in all_events if "omnisanc_error" in e.get("reason", "").lower()])
    validation_blocks = len([e for e in all_events if not e.get("allowed", True)])

    # Compute rates
    mission_extraction_rate = missions_extracted / missions_started if missions_started > 0 else 0
    mission_completion_rate = missions_completed / missions_started if missions_started > 0 else 0
    session_completion_rate = sessions_ended / sessions_started if sessions_started > 0 else 0
    waypoint_abandon_rate = waypoints_aborted / waypoints_started if waypoints_started > 0 else 0

    stats = {
        "date": start_date,
        "total_events": len(all_events),

        "mission": {
            "started": missions_started,
            "extracted": missions_extracted,
            "completed": missions_completed,
            "extraction_rate": mission_extraction_rate,
            "completion_rate": mission_completion_rate,
        },

        "session": {
            "started": sessions_started,
            "ended": sessions_ended,
            "completion_rate": session_completion_rate,
            "omnisanc_errors": omnisanc_errors,
            "errors_per_session": omnisanc_errors / sessions_started if sessions_started > 0 else 0,
        },

        "waypoint": {
            "started": waypoints_started,
            "aborted": waypoints_aborted,
            "abandon_rate": waypoint_abandon_rate,
        },

        "quality": {
            "omnisanc_errors": omnisanc_errors,
            "validation_blocks": validation_blocks,
            "error_rate": (omnisanc_errors + validation_blocks) / len(all_events) if all_events else 0,
        }
    }

    return stats


# ============================================================================
# REWARD CALCULATION
# ============================================================================

def compute_event_reward(event: Dict) -> float:
    """
    Compute reward for a single event.

    Args:
        event: Event dictionary

    Returns:
        Reward score
    """
    tool_name = event.get("tool_name", "")
    allowed = event.get("allowed", True)
    reason = event.get("reason", "")

    # Check if tool matches any reward key
    for reward_key, reward_value in EVENT_REWARDS.items():
        if tool_name.endswith(reward_key):
            return reward_value

    # Check for error penalties
    if "omnisanc_error" in reason.lower():
        return EVENT_REWARDS["omnisanc_error"]

    if not allowed:
        return EVENT_REWARDS["validation_block"]

    # Default: no reward
    return 0.0


def compute_session_reward(session_events: List[Dict]) -> float:
    """
    Compute reward for a session.

    Args:
        session_events: List of events in the session

    Returns:
        Session reward score
    """
    # Sum event rewards
    base_reward = sum(compute_event_reward(event) for event in session_events)

    # Check for completion bonus
    has_start = any(e.get("tool_name", "").endswith("start_starlog") for e in session_events)
    has_end = any(e.get("tool_name", "").endswith("end_starlog") for e in session_events)

    completion_bonus = 100 if (has_start and has_end) else 0

    # Quality multiplier (1.0 - error_rate)
    errors = len([e for e in session_events if not e.get("allowed", True)])
    error_rate = errors / len(session_events) if session_events else 0
    quality_multiplier = 1.0 - error_rate

    session_reward = (base_reward + completion_bonus) * quality_multiplier * SESSION_MULTIPLIER

    return session_reward


def compute_mission_reward(mission_events: List[Dict]) -> float:
    """
    Compute reward for a mission (sum of session rewards).

    Args:
        mission_events: List of events in the mission

    Returns:
        Mission reward score
    """
    # For now, treat as one session (TODO: split by actual sessions)
    base_reward = sum(compute_event_reward(event) for event in mission_events)

    # Check for mission completion/extraction
    has_complete = any(e.get("tool_name", "").endswith("mission_report_progress") for e in mission_events)
    has_extraction = any(e.get("tool_name", "").endswith("mission_request_extraction") for e in mission_events)

    mission_completion_bonus = 500 if has_complete else 0
    mission_extraction_penalty = -500 if has_extraction else 0

    mission_reward = (base_reward + mission_completion_bonus + mission_extraction_penalty) * MISSION_MULTIPLIER

    return mission_reward


def compute_fitness(registry_service, date: str) -> Dict[str, Any]:
    """
    Compute fitness function (overall usage reward).

    Args:
        registry_service: RegistryService instance
        date: Date string (YYYY-MM-DD)

    Returns:
        Dictionary with fitness score and breakdown
    """
    # Get all events
    home_events = get_events_from_registry(registry_service, "home_events", date)
    session_events = get_events_from_registry(registry_service, "session_events", date)
    mission_events = get_events_from_registry(registry_service, "mission_events", date)

    # Compute rewards
    home_rewards = sum(compute_event_reward(e) for e in home_events) * HOME_MULTIPLIER
    session_rewards = compute_session_reward(session_events)
    mission_rewards = compute_mission_reward(mission_events)

    # Quality factor (from stats)
    all_events = home_events + session_events + mission_events
    errors = len([e for e in all_events if not e.get("allowed", True)])
    quality_factor = 1.0 - (errors / len(all_events) if all_events else 0)

    # Fitness = weighted sum * quality
    fitness = (home_rewards + session_rewards + mission_rewards) * quality_factor

    # Compute XP (total accumulated rewards)
    xp = home_rewards + session_rewards + mission_rewards

    # Level = Fitness score (rounded)
    level = int(fitness)

    return {
        "date": date,
        "fitness": fitness,
        "level": level,
        "xp": xp,
        "breakdown": {
            "home_rewards": home_rewards,
            "session_rewards": session_rewards,
            "mission_rewards": mission_rewards,
            "quality_factor": quality_factor,
        }
    }
