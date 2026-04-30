#!/usr/bin/env python3
"""
Reward System - STARSYSTEM Health + Legacy Event Scoring

NEW (State-based): get_starsystem_health()
  - Measures CURRENT project health, not accumulated events
  - Formula: emanation×0.25 + smells×0.20 + arch×0.15 + complexity×0.15 + kg_depth×0.10 + consistency×0.15

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
        health = emanation×0.25 + smells×0.20 + arch×0.15 + complexity×0.15 + kg_depth×0.10 + consistency×0.15

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
    emanation_result = _get_emanation_score(path)
    components["emanation"] = emanation_result["score"]
    components["emanation_details"] = emanation_result

    # 2. SMELL CLEANLINESS (0.25 weight)
    components["smells"] = _get_smell_score(path)

    # 3. ARCHITECTURE COMPLIANCE (0.20 weight)
    components["architecture"] = _get_architecture_score(path)

    # 4. COMPLEXITY LEVEL (0.15 weight) - L0=0, L6=1.0
    complexity_result = _get_complexity_score(path)
    components["complexity"] = complexity_result["score"]
    components["complexity_details"] = complexity_result

    # 5. KNOWLEDGE GRAPH DEPTH (0.10 weight) — how complete is the GIINT hierarchy (Unnamed count)
    components["kg_depth"] = _get_kg_depth_score(path, components["complexity"])

    # 6. CONSISTENCY (0.15 weight) — GIINT filled out + skills mirrored + rules exist
    consistency = check_graph_filesystem_consistency(path)
    # Use coverage ratio directly (0.0-1.0) — penalize for unmirrored skills and missing GIINT
    giint_penalty = 0.0 if consistency.get("giint_complete", False) else 0.3
    components["consistency"] = max(0.0, consistency.get("coverage", 1.0) - giint_penalty)

    # Calculate weighted health
    health = (
        components["emanation"] * 0.25 +
        components["smells"] * 0.20 +
        components["architecture"] * 0.15 +
        components["complexity"] * 0.15 +
        components["kg_depth"] * 0.10 +
        components["consistency"] * 0.15
    )

    return {
        "health": round(health, 3),
        "health_percent": round(health * 100, 1),
        "path": str(path),
        "components": components,
        "weights": {
            "emanation": 0.25,
            "smells": 0.20,
            "architecture": 0.15,
            "complexity": 0.15,
            "kg_depth": 0.10,
            "consistency": 0.15
        }
    }


# OLD EMANATION - REPLACED BY YOUKNOW VERSION BELOW
# def _get_emanation_score(path: Path) -> float:
    # """Graph-only emanation score. Queries the FULL required graph shape from CartON.

    # Traces starsystem → GIINT hierarchy + AI integrations (skills, flights, rules).
    # Then scans filesystem for anything that exists on disk but not in the graph.
    # Score = completeness of the required graph shape.
    # """
    # try:
        # # Derive starsystem concept name (same slug as get_fleet_health uses)
        # path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        # ss_name = f"Starsystem_{path_slug}"

        # # Query the ENTIRE graph shape in one shot
        # shape_query = """
        # OPTIONAL MATCH (ss:Wiki {n: $ss_name})
        # WITH ss

        # OPTIONAL MATCH (proj:Wiki)-[:PART_OF]->(ss)
        # WHERE proj.n STARTS WITH 'Giint_Project_'
        # WITH ss, collect(DISTINCT proj.n) as projects

        # OPTIONAL MATCH (feat:Wiki)-[:PART_OF]->(:Wiki)-[:PART_OF]->(ss:Wiki {n: $ss_name})
        # WHERE feat.n STARTS WITH 'Giint_Feature_'
        # WITH ss, projects, collect(DISTINCT feat.n) as features

        # OPTIONAL MATCH (comp:Wiki)-[:PART_OF*1..3]->(ss:Wiki {n: $ss_name})
        # WHERE comp.n STARTS WITH 'Giint_Component_'
        # WITH ss, projects, features, collect(DISTINCT comp.n) as components

        # OPTIONAL MATCH (skill:Wiki)-[:HAS_STARSYSTEM]->(ss:Wiki {n: $ss_name})
        # WHERE skill.n STARTS WITH 'Skill_'
        # WITH ss, projects, features, components, collect(DISTINCT skill.n) as skills

        # OPTIONAL MATCH (flight:Wiki)-[:PART_OF]->(ss:Wiki {n: $ss_name})
        # WHERE flight.n STARTS WITH 'Flight_Config_'
        # WITH ss, projects, features, components, skills, collect(DISTINCT flight.n) as flights

        # OPTIONAL MATCH (rule:Wiki)-[:HAS_STARSYSTEM]->(ss:Wiki {n: $ss_name})
        # WHERE rule.n STARTS WITH 'Claude_Code_Rule_'
        # WITH ss, projects, features, components, skills, flights, collect(DISTINCT rule.n) as rules

        # OPTIONAL MATCH (deliv:Wiki)-[:PART_OF*1..4]->(ss:Wiki {n: $ss_name})
        # WHERE deliv.n STARTS WITH 'Giint_Deliverable_'
        # WITH projects, features, components, skills, flights, rules, collect(DISTINCT deliv.n) as deliverables

        # OPTIONAL MATCH (task:Wiki)-[:PART_OF*1..5]->(ss:Wiki {n: $ss_name})
        # WHERE task.n STARTS WITH 'Giint_Task_'

        # RETURN projects, features, components, deliverables,
               # collect(DISTINCT task.n) as tasks,
               # skills, flights, rules
        # """

        # result = _carton_query(shape_query, {"ss_name": ss_name})
        # if not result.get("success") or not result.get("data"):
            # return 0.0

        # d = result["data"][0]
        # projects = d.get("projects") or []
        # features = d.get("features") or []
        # components = d.get("components") or []
        # deliverables = d.get("deliverables") or []
        # tasks = d.get("tasks") or []
        # skills = d.get("skills") or []
        # flights = d.get("flights") or []
        # rules = d.get("rules") or []

        # # Score: completeness of the required graph shape
        # # Each partial is 0-1, weighted equally
        # n_comp = max(len(components), 1)
        # partials = [
            # 1.0 if projects else 0.0,                          # Has GIINT project
            # 1.0 if features else 0.0,                          # Has features defined
            # 1.0 if components else 0.0,                        # Has components defined
            # min(len(deliverables) / n_comp, 1.0),              # Deliverable coverage
            # min(len(tasks) / n_comp, 1.0),                     # Task coverage
            # min(len(skills) / n_comp, 1.0),                    # Skill coverage per component
            # min(len(flights) / 3.0, 1.0) if flights else 0.0,  # Flight coverage (3+ = full)
            # min(len(rules) / 3.0, 1.0) if rules else 0.0,     # Rule coverage (3+ = full)
        # ]
        # score = sum(partials) / len(partials)

        # # Scan filesystem for untracked items (skills/rules that exist on disk but not in graph)
        # _heal_emanation_gaps(path, ss_name, skills, rules)

        # return round(score, 3)

    # except Exception as e:
        # logger.warning(f"Could not get emanation score for {path}: {e}")
        # return 0.0


# def _heal_emanation_gaps(path: Path, ss_name: str, graph_skills: list, graph_rules: list):
    # """Check filesystem for skills/rules that exist on disk but aren't in the graph. Log gaps."""
    # try:
        # # Check .claude/skills/
        # skills_dir = path / ".claude" / "skills"
        # if skills_dir.is_dir():
            # disk_skills = [d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
            # graph_skill_names = {s.replace("Skill_", "").lower().replace("_", "-") for s in graph_skills}
            # for ds in disk_skills:
                # if ds.lower() not in graph_skill_names:
                    # logger.info(f"HEAL: skill '{ds}' exists at {skills_dir}/{ds} but not in graph for {ss_name}")

        # # Check .claude/rules/
        # rules_dir = path / ".claude" / "rules"
        # if rules_dir.is_dir():
            # disk_rules = [f.stem for f in rules_dir.glob("*.md")]
            # graph_rule_names = {r.replace("Claude_Code_Rule_", "").lower().replace("_", "-") for r in graph_rules}
            # for dr in disk_rules:
                # if dr.lower() not in graph_rule_names:
                    # logger.info(f"HEAL: rule '{dr}' exists at {rules_dir}/{dr}.md but not in graph for {ss_name}")
    # except Exception as e:
        # logger.debug(f"Heal check failed for {path}: {e}")


def _heal_emanation_gaps(gaps: list, repo_path: Path) -> int:
    """Auto-create CartON concepts for disk items we can fully deduce.

    For rules: we know name, content, scope, starsystem — everything.
    For skills/hooks/agents: same pattern.

    Returns number of concepts healed.
    """
    try:
        from carton_mcp.add_concept_tool import add_concept_tool_func
    except ImportError:
        logger.warning("Cannot import add_concept_tool — healing disabled")
        return 0

    repo_name = repo_path.name.replace("-", "_").title().replace(" ", "_")
    home_claude = Path.home() / ".claude"

    healed = 0
    for concept_name, item_type, disk_path in gaps:
        try:
            disk_p = Path(disk_path)

            if str(disk_p).startswith(str(home_claude)):
                scope = "global"
                part_of = ["Gnosys_Collection"]
            else:
                scope = "project"
                part_of = [f"Starsystem_{repo_name}"]

            if disk_p.is_dir():
                skill_md = disk_p / "SKILL.md"
                content = skill_md.read_text()[:2000] if skill_md.exists() else f"Skill at {disk_path}"
            elif disk_p.is_file():
                content = disk_p.read_text()[:2000]
            else:
                continue

            type_map = {
                "rule": "Claude_Code_Rule",
                "skill": "Skill",
                "hook": "Hook",
                "agent": "Agent",
            }
            owl_type = type_map.get(item_type, "Entity")

            rels = [
                {"relationship": "is_a", "related": [owl_type]},
                {"relationship": "part_of", "related": part_of},
                {"relationship": "instantiates", "related": [owl_type]},
            ]
            if item_type == "rule":
                rels.append({"relationship": "has_scope", "related": [scope]})

            add_concept_tool_func(
                concept_name=concept_name,
                description=content,
                relationships=rels,
                hide_youknow=False,
                source="emanation_healer",
            )
            healed += 1
            logger.info(f"HEALED: {concept_name} ({item_type}) — created in CartON")

        except Exception as e:
            logger.warning(f"Failed to heal {concept_name}: {e}")

    return healed


def _get_emanation_score(path: Path) -> float:
    """Emanation score via YOUKNOW validation.

    1. Scan .claude/skills/ and .claude/rules/ on disk — ground truth for what exists
    2. For each, derive CartON concept name and query its relationships
    3. Call youknow_validate() on the daemon — CODE = complete, SOUP = incomplete
    4. Score = fraction that pass YOUKNOW validation (CODE)
    5. Log gaps (missing from CartON) and SOUP reasons
    6. HEAL gaps where we can fully deduce the concept from disk
    """
    try:
        import urllib.request as _urllib_req

        try:
            # TRIGGERS: YOUKNOW daemon:8102/health via HTTP GET
            with _urllib_req.urlopen("http://localhost:8102/health", timeout=2) as r:
                if r.status != 200:
                    return 0.0
        except Exception:
            logger.warning("YOUKNOW daemon not running — emanation score unavailable")
            return 0.0

        disk_items = []

        skills_dir = path / ".claude" / "skills"
        if skills_dir.is_dir():
            for d in skills_dir.iterdir():
                if d.is_dir() and not d.name.startswith("_"):
                    # Strip "skill-" prefix if present to avoid double Skill_Skill_
                    name = d.name
                    if name.startswith("skill-"):
                        name = name[6:]
                    slug = name.replace("-", "_").title().replace(" ", "_")
                    disk_items.append((f"Skill_{slug}", "skill", str(d)))

        rules_dir = path / ".claude" / "rules"
        if rules_dir.is_dir():
            for f in rules_dir.glob("*.md"):
                slug = f.stem.replace("-", "_").title().replace(" ", "_")
                disk_items.append((f"Claude_Code_Rule_{slug}", "rule", str(f)))

        hooks_dir = path / ".claude" / "hooks"
        if hooks_dir.is_dir():
            for f in hooks_dir.glob("*.py"):
                slug = f.stem.replace("-", "_").title().replace(" ", "_")
                disk_items.append((f"Hook_{slug}", "hook", str(f)))

        agents_dir = path / ".claude" / "agents"
        if agents_dir.is_dir():
            for f in agents_dir.glob("*.md"):
                slug = f.stem.replace("-", "_").title().replace(" ", "_")
                disk_items.append((f"Agent_{slug}", "agent", str(f)))

        if not disk_items:
            return 0.0

        names = [item[0] for item in disk_items]
        rel_query = (
            "UNWIND $names AS name "
            "OPTIONAL MATCH (c:Wiki {n: name})-[r]->(t:Wiki) "
            "WHERE type(r) <> 'AUTO_RELATED_TO' "
            "RETURN name, collect(type(r) + ' ' + t.n) as rels"
        )
        rel_result = _carton_query(rel_query, {"names": names})
        rels_by_name = {}
        if rel_result.get("success"):
            for row in rel_result.get("data", []):
                rels_by_name[row["name"]] = row.get("rels", [])

        code_count = 0
        soup_items = []
        missing_items = []

        for concept, item_type, disk_path in disk_items:
            rels = rels_by_name.get(concept, [])
            if not rels:
                missing_items.append((concept, item_type, disk_path))
                continue

            statement = f"{concept} {', '.join(rels)}"
            try:
                body = json.dumps({"statement": statement}).encode()
                # TRIGGERS: YOUKNOW daemon:8102/validate via HTTP POST
                req = _urllib_req.Request(
                    "http://localhost:8102/validate",
                    data=body,
                    headers={"Content-Type": "application/json"}
                )
                with _urllib_req.urlopen(req, timeout=30) as resp:
                    yk_data = json.loads(resp.read())

                result_str = yk_data.get("result", "")
                if result_str.startswith("CODE:"):
                    code_count += 1
                else:
                    soup_items.append((concept, result_str[:150]))
            except Exception as e:
                soup_items.append((concept, f"validation error: {e}"))

        total = len(disk_items)
        missing_names = {m[0] for m in missing_items}
        soup_names = {s[0] for s in soup_items}
        failed = missing_names | soup_names

        def _count(typ):
            t = sum(1 for _, tt, _ in disk_items if tt == typ)
            c = sum(1 for cn, tt, _ in disk_items if tt == typ and cn not in failed)
            return c, t

        skill_code, skill_total = _count("skill")
        rule_code, rule_total = _count("rule")
        hook_code, hook_total = _count("hook")
        agent_code, agent_total = _count("agent")

        for concept, item_type, disk_path in missing_items:
            logger.info(f"EMANATION GAP: {item_type} '{concept}' at {disk_path} NOT in CartON")
        for concept, reason in soup_items:
            logger.info(f"EMANATION SOUP: {concept} — {reason}")

        # Heal gaps where we can fully deduce the concept from disk
        if missing_items:
            healed = _heal_emanation_gaps(missing_items, path)
            if healed > 0:
                logger.info(f"HEALED {healed} gaps — re-validating")
                # Re-query healed concepts and validate
                healed_names = [m[0] for m in missing_items]
                re_query = (
                    "UNWIND $names AS name "
                    "OPTIONAL MATCH (c:Wiki {n: name})-[r]->(t:Wiki) "
                    "WHERE type(r) <> 'AUTO_RELATED_TO' "
                    "RETURN name, collect(type(r) + ' ' + t.n) as rels"
                )
                re_result = _carton_query(re_query, {"names": healed_names})
                if re_result.get("success"):
                    for row in re_result.get("data", []):
                        rels = row.get("rels", [])
                        if not rels:
                            continue
                        statement = f"{row['name']} {', '.join(rels)}"
                        try:
                            body = json.dumps({"statement": statement}).encode()
                            # TRIGGERS: YOUKNOW daemon:8102/validate via HTTP POST
                            req = _urllib_req.Request(
                                "http://localhost:8102/validate",
                                data=body,
                                headers={"Content-Type": "application/json"}
                            )
                            with _urllib_req.urlopen(req, timeout=30) as resp:
                                yk_data = json.loads(resp.read())
                            if yk_data.get("result", "").startswith("CODE:"):
                                code_count += 1
                                failed.discard(row["name"])
                        except Exception:
                            pass
                # Recount after healing
                skill_code, skill_total = _count("skill")
                rule_code, rule_total = _count("rule")
                hook_code, hook_total = _count("hook")
                agent_code, agent_total = _count("agent")

        score = round(code_count / total, 3) if total > 0 else 0.0
        return {
            "score": score,
            "total": total,
            "code": code_count,
            "skills": f"{skill_code}/{skill_total}",
            "rules": f"{rule_code}/{rule_total}",
            "hooks": f"{hook_code}/{hook_total}",
            "agents": f"{agent_code}/{agent_total}",
            "gaps": [(c, t, p) for c, t, p in missing_items],
            "soup": [(c, r) for c, r in soup_items],
        }

    except Exception as e:
        logger.warning(f"Could not get emanation score for {path}: {e}")
        return {"score": 0.0, "total": 0, "code": 0, "skills": "0/0", "rules": "0/0", "hooks": "0/0", "agents": "0/0", "gaps": [], "soup": []}


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
    """Onion architecture compliance score. PLACEHOLDER — checks file existence only."""
    # TODO: Use context-alignment to analyze actual architecture layers
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


def _get_hidden_deps_score(path: Path) -> float:
    """Hidden connections annotation score. 1.0 = all annotated, 0.0 = none."""
    try:
        import sys
        sys.path.insert(0, "/home/GOD/gnosys-plugin-v2/knowledge/context-alignment/neo4j_codebase_mcp")
        from hidden_connections import detect_hidden_connections
        result = detect_hidden_connections(str(path))
        return result.get("score", 0.5)
    except Exception:
        return 0.5


def _check_cicd(path: Path) -> bool:
    """Check if repo has CICD artifacts."""
    indicators = [
        path / ".github" / "workflows",
        path / "Dockerfile",
        path / "docker-compose.yml",
        path / "deploy",
    ]
    return any(p.exists() for p in indicators)


def _detect_complexity_level(
    total_skills: int, total_flights: int, total_mcps: int,
    total_personas: int, path: Path = None, emanation_score: float = None,
) -> dict:
    """Shared progressive level detection for complexity ladder.

    Returns dict with level (int 0-6), score (float 0.0-1.0),
    met (list of satisfied requirements), missing (list of next gaps).

    Levels (from guru loop _get_level_requirements, autopoiesis_stop_hook.py:318):
      L0: Nothing
      L1: 1+ skill + rules
      L2: L1 + flight config
      L3: L2 + MCP tool
      L4: L3 + persona (frame + skillset + MCP set)
      L5: K2 Stellar — starsystem auto-provides (emanation >= 0.6)
      L6: All L5 + CICD pipeline
    """
    met = []
    missing = []

    # L1: skills exist
    has_skills = total_skills > 0
    if has_skills:
        met.append("L1: skills")
    else:
        missing.append("L1: needs 1+ skill in .claude/skills/")

    # L2: L1 + flight config
    has_flights = total_flights > 0
    if has_skills and has_flights:
        met.append("L2: flights")
    elif has_skills:
        missing.append("L2: needs flight config in CartON")

    # L3: L2 + MCP
    has_mcps = total_mcps > 0
    if has_skills and has_flights and has_mcps:
        met.append("L3: MCPs")
    elif has_skills and has_flights:
        missing.append("L3: needs MCP tool")

    # L4: L3 + persona
    has_persona = total_personas > 0
    if has_skills and has_flights and has_mcps and has_persona:
        met.append("L4: persona")
    elif has_skills and has_flights and has_mcps:
        missing.append("L4: needs persona (frame + skillset + MCP set)")

    # L5: K2 Stellar (auto from emanation score)
    is_stellar = (emanation_score or 0) >= 0.6
    if is_stellar and has_persona:
        met.append("L5: K2 Stellar (auto)")
    elif has_persona:
        missing.append("L5: needs emanation >= 0.6 for K2 Stellar")

    # L6: CICD
    has_cicd = _check_cicd(path) if path else False
    if has_cicd and is_stellar:
        met.append("L6: CICD + deployment")
    elif is_stellar:
        missing.append("L6: needs CICD pipeline (.github/workflows/, Dockerfile)")

    level = len(met)
    score = round(level / 6.0, 3)
    return {"level": level, "score": score, "met": met, "missing": missing}


def _get_complexity_score(path: Path) -> dict:
    """Detect complexity level L0-L6 by checking .claude/ inventory against CartON.

    Returns dict: {level: int, score: float, met: [...], missing: [...]}
    """
    try:
        path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        starsystem_name = f"Starsystem_{path_slug}"

        # PART A: Inventory .claude/ folder
        claude_dir = path / ".claude"
        local_skills = []
        local_agents = []

        if claude_dir.exists():
            skills_dir = claude_dir / "skills"
            if skills_dir.exists():
                local_skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
            agents_dir = claude_dir / "agents"
            if agents_dir.exists():
                local_agents = [f.stem for f in agents_dir.glob("*.md")]

        # PART B: Query CartON for connected emanations
        cypher = """
        MATCH (s:Wiki {n: $starsystem_name})
        OPTIONAL MATCH (skill:Wiki)-[:HAS_STARSYSTEM|PART_OF]->(s) WHERE (skill)-[:IS_A]->(:Wiki {n: "Skill"})
        OPTIONAL MATCH (flight:Wiki)-[:PART_OF]->(s) WHERE (flight)-[:IS_A]->(:Wiki {n: "Flight_Config"})
        OPTIONAL MATCH (persona:Wiki)-[:CONFIGURES]->(s) WHERE (persona)-[:IS_A]->(:Wiki {n: "Persona"})
        OPTIONAL MATCH (mcp:Wiki)-[:PART_OF]->(s) WHERE (mcp)-[:IS_A]->(:Wiki {n: "MCP_Server"})
        RETURN
            count(DISTINCT skill) as carton_skills,
            count(DISTINCT flight) as carton_flights,
            count(DISTINCT persona) as carton_personas,
            count(DISTINCT mcp) as carton_mcps
        """
        result = _carton_query(cypher, {"starsystem_name": starsystem_name})

        carton_skills = 0
        carton_flights = 0
        carton_personas = 0
        carton_mcps = 0

        if result and result.get("success") and result.get("data"):
            data = result["data"][0] if result["data"] else {}
            carton_skills = data.get("carton_skills", 0)
            carton_flights = data.get("carton_flights", 0)
            carton_personas = data.get("carton_personas", 0)
            carton_mcps = data.get("carton_mcps", 0)

        total_skills = max(len(local_skills), carton_skills)
        total_flights = carton_flights
        total_personas = carton_personas
        total_mcps = carton_mcps

        return _detect_complexity_level(
            total_skills, total_flights, total_mcps, total_personas, path
        )

    except Exception as e:
        logger.warning(f"Could not get complexity score: {e}")
        return {"level": 0, "score": 0.0, "met": [], "missing": []}


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

        # Walk the full hierarchy chain: Starsystem → Collection_Category → HC → Project → Feature → Component → Deliverable
        # Exclude _Unnamed concepts — they are incomplete placeholders that should NOT count toward completeness
        cypher = """
        MATCH (s:Wiki {n: $starsystem_name})
        OPTIONAL MATCH (gp:Wiki)-[:PART_OF*1..3]->(s)
            WHERE gp.n STARTS WITH 'Giint_Project_' AND NOT gp.n CONTAINS '_Unnamed'
        OPTIONAL MATCH (f:Wiki)-[:PART_OF*1..4]->(s)
            WHERE f.n STARTS WITH 'Giint_Feature_' AND NOT f.n CONTAINS '_Unnamed'
        OPTIONAL MATCH (c:Wiki)-[:PART_OF*1..5]->(s)
            WHERE c.n STARTS WITH 'Giint_Component_' AND NOT c.n CONTAINS '_Unnamed'
        OPTIONAL MATCH (d:Wiki)-[:PART_OF*1..6]->(s)
            WHERE d.n STARTS WITH 'Giint_Deliverable_' AND NOT d.n CONTAINS '_Unnamed'
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

            # Score: 0.25 per level that has at least 1 NON-Unnamed element
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


def _get_deepening_score(path: Path) -> dict:
    """Progressive deepening score (Design_Giint_Progressive_Deepening_Levels).
    L0=_Unnamed, L1=named, L3=has deliverables. Returns score + level counts."""
    try:
        path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        ss = f"Starsystem_{path_slug}"
        cypher = """
        MATCH (s:Wiki {n: $ss})
        OPTIONAL MATCH (c:Wiki)-[:PART_OF*1..5]->(s)
            WHERE c.n STARTS WITH 'Giint_Component_'
        WITH c WHERE c IS NOT NULL
        OPTIONAL MATCH (d:Wiki)-[:PART_OF]->(c)
            WHERE d.n STARTS WITH 'Giint_Deliverable_' AND NOT d.n CONTAINS '_Unnamed'
        RETURN c.n AS name, c.n CONTAINS '_Unnamed' AS is_unnamed, count(d) > 0 AS has_del
        """
        result = _carton_query(cypher, {"ss": ss})
        if not result or not result.get("success") or not result.get("data"):
            return {"score": 0.0, "levels": {0: 0, 1: 0, 3: 0}, "total": 0}
        levels = {0: 0, 1: 0, 3: 0}
        for row in result["data"]:
            if not row.get("name"): continue
            if row.get("is_unnamed"): levels[0] += 1
            elif row.get("has_del"): levels[3] += 1
            else: levels[1] += 1
        total = sum(levels.values())
        if total == 0: return {"score": 0.0, "levels": levels, "total": 0}
        avg = sum(lvl * cnt for lvl, cnt in levels.items()) / total
        return {"score": round(avg / 3.0, 3), "levels": levels, "total": total}
    except Exception as e:
        logger.warning(f"Deepening score failed: {e}")
        return {"score": 0.0, "levels": {0: 0, 1: 0, 3: 0}, "total": 0}


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


def check_graph_filesystem_consistency(path: Path, auto_repair: bool = True) -> Dict[str, Any]:
    """Check CartON graph matches filesystem for a STARSYSTEM.

    Three checks:
    1. GIINT hierarchy is filled out (Project→Feature→Component→Deliverable)
    2. Skills are mirrored INTO the starsystem (not just in heaven_data)
    3. Rules exist in .claude/rules/ for the starsystem's skills

    When auto_repair=True (default), automatically mirrors missing skills
    and generates rules before returning the final consistency score.

    Returns:
        {
            "consistent": bool,
            "coverage": float,  # 0.0-1.0 ratio of mirrored/total
            "giint_complete": bool,
            "skills_total": int,
            "skills_mirrored": int,
            "skills_with_rules": int,
            "issues": [{"category": str, "issue": str, "target": str}],
            "repairs_attempted": [{"action": str, "target": str, "result": str}]
        }
    """
    try:
        path = Path(path)
        path_slug = str(path).strip("/").replace("/", "_").replace("-", "_").title()
        starsystem_name = f"Starsystem_{path_slug}"

        issues = []
        repairs = []

        # --- CHECK 1: GIINT hierarchy completeness ---
        giint_cypher = """
        MATCH (s:Wiki {n: $ss_name})
        OPTIONAL MATCH (gp:Wiki)-[:PART_OF*1..2]->(s)
            WHERE gp.n STARTS WITH 'Giint_Project_' OR gp.n STARTS WITH 'GIINT_Project_'
        OPTIONAL MATCH (f:Wiki)-[:PART_OF*1..3]->(s)
            WHERE f.n STARTS WITH 'Giint_Feature_' OR f.n STARTS WITH 'GIINT_Feature_'
        OPTIONAL MATCH (c:Wiki)-[:PART_OF*1..4]->(s)
            WHERE c.n STARTS WITH 'Giint_Component_' OR c.n STARTS WITH 'GIINT_Component_'
        OPTIONAL MATCH (d:Wiki)-[:PART_OF*1..5]->(s)
            WHERE d.n STARTS WITH 'Giint_Deliverable_' OR d.n STARTS WITH 'GIINT_Deliverable_'
        RETURN
            count(DISTINCT gp) as projects,
            count(DISTINCT f) as features,
            count(DISTINCT c) as components,
            count(DISTINCT d) as deliverables
        """
        giint_result = _carton_query(giint_cypher, {"ss_name": starsystem_name})
        giint_data = {}
        giint_complete = False

        if giint_result.get("success") and giint_result.get("data"):
            giint_data = giint_result["data"][0] if giint_result["data"] else {}
            projects = giint_data.get("projects", 0)
            features = giint_data.get("features", 0)
            components = giint_data.get("components", 0)
            deliverables = giint_data.get("deliverables", 0)

            giint_complete = all([projects > 0, features > 0, components > 0, deliverables > 0])

            if projects == 0:
                issues.append({"category": "giint", "issue": "No GIINT_Project for this starsystem", "target": starsystem_name})
            if projects > 0 and features == 0:
                issues.append({"category": "giint", "issue": "GIINT_Project exists but has no Features", "target": starsystem_name})
            if features > 0 and components == 0:
                issues.append({"category": "giint", "issue": "Features exist but have no Components", "target": starsystem_name})
            if components > 0 and deliverables == 0:
                issues.append({"category": "giint", "issue": "Components exist but have no Deliverables", "target": starsystem_name})

        # --- CHECK 2: Skills mirrored into starsystem ---
        # Get skills that explicitly belong to THIS starsystem via:
        # a) skill -[:HAS_STARSYSTEM]-> this starsystem
        # b) skill -[:HAS_DESCRIBES_COMPONENT]-> component -[:PART_OF*1..4]-> this starsystem
        # c) skill -[:PART_OF]-> this starsystem directly
        skills_cypher = """
        MATCH (s:Wiki {n: $ss_name})
        OPTIONAL MATCH (skill1:Wiki)-[:HAS_STARSYSTEM]->(s) WHERE skill1.n STARTS WITH 'Skill_'
        OPTIONAL MATCH (skill2:Wiki)-[:PART_OF]->(s) WHERE skill2.n STARTS WITH 'Skill_'
        OPTIONAL MATCH (skill3:Wiki)-[:HAS_DESCRIBES_COMPONENT]->(comp:Wiki)-[:PART_OF*1..4]->(s)
            WHERE skill3.n STARTS WITH 'Skill_'
        WITH collect(DISTINCT skill1.n) + collect(DISTINCT skill2.n) + collect(DISTINCT skill3.n) as all_skills
        UNWIND all_skills as skill_name
        WITH skill_name WHERE skill_name IS NOT NULL
        RETURN DISTINCT skill_name
        """
        skills_result = _carton_query(skills_cypher, {"ss_name": starsystem_name})

        carton_skills = set()
        if skills_result.get("success") and skills_result.get("data"):
            for row in skills_result["data"]:
                sn = row.get("skill_name")
                if sn:
                    carton_skills.add(sn)

        # Also check heaven_data/skills/ for skills with matching starsystem in _metadata.json
        heaven_skills_dir = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "skills"
        if heaven_skills_dir.exists():
            for skill_dir in heaven_skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                meta_file = skill_dir / "_metadata.json"
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text())
                        skill_starsystem = meta.get("starsystem", "")
                        if skill_starsystem and str(path) in skill_starsystem:
                            # Normalize to CartON name
                            concept_name = "Skill_" + "_".join(
                                w.capitalize() for w in skill_dir.name.replace("-", "_").split("_")
                            )
                            carton_skills.add(concept_name)
                    except (json.JSONDecodeError, OSError):
                        pass

        # Check which skills are mirrored into the starsystem's .claude/skills/
        starsystem_skills_dir = path / ".claude" / "skills"
        starsystem_rules_dir = path / ".claude" / "rules"

        skills_total = len(carton_skills)
        skills_mirrored = 0
        skills_with_rules = 0

        for skill_concept in sorted(carton_skills):
            # Convert concept name to directory slug
            skill_slug = skill_concept.lower().replace("_", "-")
            if skill_slug.startswith("skill-"):
                skill_slug = skill_slug[6:]  # Remove "skill-" prefix for dir name

            # Check if mirrored into starsystem .claude/skills/
            mirrored = False
            if starsystem_skills_dir.exists():
                # Try multiple slug patterns
                for candidate in [skill_slug, f"skill-{skill_slug}", skill_concept.lower().replace("_", "-")]:
                    if (starsystem_skills_dir / candidate).exists():
                        mirrored = True
                        break

            if mirrored:
                skills_mirrored += 1
            else:
                issues.append({
                    "category": "skill_mirror",
                    "issue": f"Skill '{skill_concept}' belongs to this starsystem but not mirrored to {starsystem_skills_dir}",
                    "target": skill_concept
                })
                repairs.append({"action": "mirror_skill", "target": skill_concept})

            # Check if rule exists for this skill
            has_rule = False
            if starsystem_rules_dir.exists():
                for rule_file in starsystem_rules_dir.iterdir():
                    if rule_file.is_file() and rule_file.suffix == ".md":
                        # Check if rule name relates to skill
                        rule_stem = rule_file.stem.lower().replace("-", "_")
                        skill_lower = skill_slug.replace("-", "_")
                        if skill_lower in rule_stem or rule_stem in skill_lower:
                            has_rule = True
                            break

            if has_rule:
                skills_with_rules += 1

        # --- CHECK 3: Disk skills not in CartON ---
        if starsystem_skills_dir.exists():
            carton_slugs = set()
            for sc in carton_skills:
                slug = sc.lower().replace("_", "-")
                if slug.startswith("skill-"):
                    slug = slug[6:]
                carton_slugs.add(slug)

            for skill_dir in starsystem_skills_dir.iterdir():
                if skill_dir.is_dir():
                    disk_slug = skill_dir.name.lower().replace("-", "_").replace("skill_", "")
                    normalized = disk_slug.replace("_", "-")
                    if normalized not in carton_slugs and disk_slug not in carton_slugs:
                        issues.append({
                            "category": "skill_orphan",
                            "issue": f"Skill '{skill_dir.name}' on disk in starsystem but not tracked in CartON",
                            "target": skill_dir.name
                        })
                        repairs.append({"action": "sync_to_carton", "target": skill_dir.name})
                        skills_total += 1  # Count it in total

        # --- AUTO-REPAIR: mirror missing skills + generate rules ---
        repairs_attempted = []
        if auto_repair and repairs:
            import shutil
            heaven_skills = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "skills"
            starsystem_skills_dir.mkdir(parents=True, exist_ok=True)
            starsystem_rules_dir.mkdir(parents=True, exist_ok=True)

            for repair in repairs:
                action = repair.get("action", "")
                target = repair.get("target", "")

                if action == "mirror_skill":
                    skill_slug = target.lower().replace("_", "-")
                    if skill_slug.startswith("skill-"):
                        skill_slug = skill_slug[6:]

                    source = None
                    for candidate in [skill_slug, f"skill-{skill_slug}", target.lower().replace("_", "-")]:
                        candidate_path = heaven_skills / candidate
                        if candidate_path.exists():
                            source = candidate_path
                            break

                    if not source:
                        repairs_attempted.append({"action": action, "target": target, "result": "not_found"})
                        continue

                    dest = starsystem_skills_dir / source.name
                    try:
                        if dest.exists():
                            shutil.copytree(str(source), str(dest), dirs_exist_ok=True)
                        else:
                            shutil.copytree(str(source), str(dest))

                        # Generate rule from skill metadata
                        when_text = "working in this domain"
                        meta_file = source / "_metadata.json"
                        if meta_file.exists():
                            try:
                                meta = json.loads(meta_file.read_text())
                                when_text = meta.get("when", when_text) or when_text
                            except (json.JSONDecodeError, OSError):
                                pass

                        rule_content = f"# Use {source.name}\n\nUse the `{source.name}` skill when: {when_text}.\n"
                        (starsystem_rules_dir / f"use-{source.name}.md").write_text(rule_content)

                        skills_mirrored += 1
                        skills_with_rules += 1
                        issues = [i for i in issues if i.get("target") != target]
                        repairs_attempted.append({"action": action, "target": target, "result": "repaired"})
                    except Exception as e:
                        repairs_attempted.append({"action": action, "target": target, "result": f"failed: {e}"})

                elif action == "sync_to_carton":
                    repairs_attempted.append({"action": action, "target": target, "result": "skipped"})

        # Coverage ratio (recalculated after repair)
        total_artifacts = max(skills_total, 1)
        coverage = skills_mirrored / total_artifacts if total_artifacts > 0 else 1.0

        return {
            "consistent": len(issues) == 0,
            "coverage": round(coverage, 3),
            "giint_complete": giint_complete,
            "giint_levels": giint_data,
            "skills_total": skills_total,
            "skills_mirrored": skills_mirrored,
            "skills_with_rules": skills_with_rules,
            "issues": issues,
            "repairs_attempted": repairs_attempted,
        }

    except Exception as e:
        logger.warning(f"Graph-filesystem consistency check failed: {e}")
        return {
            "consistent": True, "coverage": 1.0, "giint_complete": False,
            "giint_levels": {}, "skills_total": 0, "skills_mirrored": 0,
            "skills_with_rules": 0, "issues": [], "repairs_attempted": [], "error": str(e)
        }


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

    # 1. Build starsystem concept names for all paths
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

        try:
            emanation_result = _get_emanation_score(path_obj)
            emanation_score = emanation_result["score"]
            complexity_result = _detect_complexity_level(
                max(len([d for d in (path_obj / ".claude" / "skills").iterdir() if d.is_dir()]) if (path_obj / ".claude" / "skills").is_dir() else 0, kg.get("skills", 0)),
                kg.get("flights", 0),
                kg.get("mcps", 0),
                kg.get("personas", 0),
                path_obj,
                emanation_score,
            )
            complexity = complexity_result["score"]
            arch = _get_architecture_score(path_obj)
            hidden_deps = _get_hidden_deps_score(path_obj)
            deepening = _get_deepening_score(path_obj)
            smells = _get_cached_smell_score(p)
            giint = _compute_giint_from_kg(kg)
            inter = _compute_inter_from_kg(kg)

            kg_depth = round(giint * 0.40 + complexity * 0.40 + inter * 0.20, 3)
            consistency = check_graph_filesystem_consistency(path_obj)
            giint_penalty = 0.0 if consistency.get("giint_complete", False) else 0.3
            consistency_score = max(0.0, consistency.get("coverage", 1.0) - giint_penalty)

            health = (
                emanation_score * 0.25 +
                smells * 0.20 +
                arch * 0.15 +
                complexity * 0.15 +
                kg_depth * 0.10 +
                consistency_score * 0.15
            )

            results[p] = {
                "health": round(health, 3),
                "health_percent": round(health * 100, 1),
                "path": p,
                "components": {
                    "emanation": emanation_score,
                    "emanation_details": emanation_result,
                    "smells": smells,
                    "architecture": arch,
                    "hidden_deps": hidden_deps,
                    "deepening": deepening,
                    "complexity": complexity,
                    "complexity_details": complexity_result,
                    "kg_depth": kg_depth,
                    "consistency": consistency_score,
                },
                "weights": {
                    "emanation": 0.25,
                    "smells": 0.20,
                    "architecture": 0.15,
                    "complexity": 0.15,
                    "kg_depth": 0.10,
                    "consistency": 0.15,
                }
            }
        except Exception as e:
            logger.warning(f"Fleet health failed for {p}: {e}")
            results[p] = {"health": 0.0, "health_percent": 0.0, "path": p, "components": {
                "emanation": 0.0, "smells": 0.5, "architecture": 0.0, "complexity": 0.0, "kg_depth": 0.0
            }, "weights": {}}

    return results


def _compute_complexity_from_kg(path: Path, kg_data: dict) -> float:
    """Compute complexity score from pre-fetched KG data + local .claude/ inventory."""
    claude_dir = path / ".claude"
    local_skills = []

    if claude_dir.exists():
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            try:
                local_skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
            except Exception:
                pass

    total_skills = max(len(local_skills), kg_data.get("skills", 0))
    total_flights = kg_data.get("flights", 0)
    total_personas = kg_data.get("personas", 0)
    total_mcps = kg_data.get("mcps", 0)

    result = _detect_complexity_level(
        total_skills, total_flights, total_mcps, total_personas, path
    )
    return result["score"]


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
        f"   🔗 Consistency: {c['consistency']:.2f}",
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
