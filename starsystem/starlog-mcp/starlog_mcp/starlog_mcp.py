"""STARLOG MCP server wrapper using FastMCP."""

import logging
import os
import json
import subprocess
from pathlib import Path
from typing import Annotated, Dict, Any, List, Optional, Tuple
from pydantic import Field
from datetime import datetime

# Set up logging for debugging
logger = logging.getLogger(__name__)


def _compute_fleet_xp(starships: dict, health_cache: dict = None) -> dict:
    """Compute XP from health scores across all starships.

    XP = sum of (health_score * 1000) per starship.
    Level = total XP // 1000.

    If health_cache is provided (from get_fleet_health batch), uses
    pre-computed values. Otherwise falls back to individual calls.
    """
    total_xp = 0
    health_details = {}

    for name, ss in starships.items():
        path = ss.get("path", "")
        if not path or not os.path.isdir(path):
            health_details[name] = {"health": 0.0, "xp_contribution": 0}
            continue
        try:
            if health_cache and path in health_cache:
                health = health_cache[path]
            else:
                from starsystem.reward_system import get_starsystem_health
                health = get_starsystem_health(path)
            h_score = health.get("health", 0.0)
            xp_contrib = int(h_score * 1000)
            total_xp += xp_contrib
            health_details[name] = {"health": h_score, "xp_contribution": xp_contrib}
        except Exception as e:
            logger.warning(f"Could not compute health for {name}: {e}")
            health_details[name] = {"health": 0.0, "xp_contribution": 0}

    return {
        "xp": total_xp,
        "level": total_xp // 1000,
        "details": health_details
    }


def _get_observation_deck(path: str) -> str:
    """Build OBSERVATION DECK HUD with STARSYSTEM health score."""
    deck_parts = []

    # Get unified STARSYSTEM health score
    try:
        from starsystem.reward_system import get_starsystem_health
        health = get_starsystem_health(path)
        h_pct = health["health_percent"]
        c = health["components"]

        # Health indicator emoji
        if h_pct >= 80:
            indicator = "🟢"
        elif h_pct >= 60:
            indicator = "🟡"
        elif h_pct >= 40:
            indicator = "🟠"
        else:
            indicator = "🔴"

        deck_parts.append(f"{indicator} HEALTH: {c.get('health', h_pct/100):.2f}")
        deck_parts.append(f"   🎯 Emanation: {c['emanation']:.2f} | 👃 Smells: {c['smells']:.2f}")
        deck_parts.append(f"   🏛️ Arch: {c['architecture']:.2f} | 📊 L{_complexity_to_level(c['complexity'])} | 🧠 KG: {c['kg_depth']:.2f}")
    except Exception as e:
        logger.warning(f"Could not get STARSYSTEM health: {e}")
        # Fallback to legacy emanation-only display
        try:
            from llm_intelligence.carton_sync import get_emanation_gaps
            gaps_result = get_emanation_gaps()
            gaps = gaps_result.get('gaps', gaps_result)
            coverage = gaps.get('coverage_percent', 0)
            total = gaps.get('total_components', 0)
            with_full = gaps.get('components_with_full_emanation', 0)
            deck_parts.append(f"🎯 EMANATION: {with_full}/{total} ({coverage:.0f}%)")
        except:
            deck_parts.append("🎯 HEALTH: unavailable")

    if not deck_parts:
        return ""

    return "📡 OBSERVATION DECK:\n" + "\n".join(f"   {p}" for p in deck_parts)


def _complexity_to_level(score: float) -> str:
    """Convert complexity score to level string."""
    if score >= 0.83:
        return "4+"
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


def _get_smell_summary(path: str) -> str:
    """Scan directory for code smells and return summary."""
    try:
        # Find Python files in the STARSYSTEM
        py_files = list(Path(path).rglob("*.py"))
        if not py_files:
            return "👃 SMELLS: no Python files"

        # Quick line count check for long files
        long_files = []
        total_files = 0
        for f in py_files[:50]:  # Limit to 50 files for speed
            try:
                lines = len(f.read_text().splitlines())
                total_files += 1
                if lines > 500:
                    long_files.append((f.name, lines))
            except:
                pass

        if long_files:
            long_files.sort(key=lambda x: x[1], reverse=True)
            top_offenders = ", ".join(f"{n}({l}L)" for n, l in long_files[:3])
            return f"👃 SMELLS: {len(long_files)}/{total_files} files >500L | offenders: {top_offenders}"
        else:
            return f"👃 SMELLS: {total_files} files clean"
    except Exception as e:
        logger.warning(f"Smell scan failed: {e}")
        return ""

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    logger.error("FastMCP not available - install mcp package")
    raise

from .starlog import Starlog
from .models import RulesEntry, DebugDiaryEntry, StarlogEntry, FlightConfig, StarlogPayloadDiscoveryConfig
from heaven_base.tools.registry_tool import registry_util_func

# Create singleton instance
logger.info("Initializing STARLOG instance")
starlog = Starlog()

# Create FastMCP app
app = FastMCP("STARLOG")
logger.info("STARLOG initialized")

@app.tool()
def init_project(path: str, name: str, description: str = "", giint_project_id: str = None) -> str:
    """Creates a full STARSYSTEM: starlog.hpi + GIINT project + .claude/ scaffold. Use this when check() shows directory is not a STARLOG project.

    A STARSYSTEM = directory + starlog project + GIINT project + .claude/ (rules + skills).
    GIINT project is auto-created if not provided.

    Args:
        path: Directory path for the STARSYSTEM
        name: Project name
        description: Project description
        giint_project_id: Optional existing GIINT project ID to link (auto-created if omitted)
    """
    logger.debug(f"init_project called with path={path}, name={name}, description={description}, giint_project_id={giint_project_id}")
    result = starlog.init_project(path, name, description, giint_project_id)
    return result

@app.tool()
def upgrade_starsystem(path: str) -> str:
    """Upgrade existing STARSYSTEM to add missing GIINT project and .claude/ scaffold. Non-destructive — preserves all existing data."""
    result = starlog.upgrade_starsystem(path)
    return result

@app.tool()
def check(path: str) -> Dict[str, Any]:
    """Verifies if directory is a STARLOG project. Always use this first to determine if you need to init_project or can proceed with orient."""
    logger.debug(f"check called with path={path}")
    return starlog.check(path)

@app.tool()
def orient(path: str = None) -> str:
    """Returns project context or HOME dashboard.

    With path: Returns full Captain's Log XML context for existing projects.
    Without path: Returns HOME dashboard showing all STARSYSTEMs and their health.
    """
    import time as _time
    _t0 = _time.time()
    logger.debug(f"orient called with path={path}")

    # HOME Dashboard mode - no path provided
    if path is None:
        return _get_home_dashboard()

    _t1 = _time.time()
    result = starlog.orient(path)
    _t2 = _time.time()
    logger.warning(f"⏱️ ORIENT TIMING: starlog.orient() took {_t2-_t1:.2f}s")

    # If orient was successful (doesn't start with ❌), update course state and add WARP message
    if not result.startswith("❌"):
        try:
            COURSE_STATE_FILE = os.path.join(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "omnisanc_core/.course_state")

            if os.path.exists(COURSE_STATE_FILE):
                with open(COURSE_STATE_FILE, 'r') as f:
                    course_state = json.load(f)

                # Update state to mark as oriented
                course_state["oriented"] = True
                course_state["last_oriented"] = path

                with open(COURSE_STATE_FILE, 'w') as f:
                    json.dump(course_state, f, indent=2)

                logger.info(f"Course state updated: oriented to {path}")
        except Exception as e:
            logger.warning(f"Failed to update course state after orient: {e}")

        # Build WARP message with OBSERVATION DECK
        warp_header = f"⚡ WARPED TO STARSYSTEM {path}!\n"
        _t3 = _time.time()
        observation_deck = _get_observation_deck(path)
        _t4 = _time.time()
        logger.warning(f"⏱️ ORIENT TIMING: _get_observation_deck() took {_t4-_t3:.2f}s")

        if observation_deck:
            result = warp_header + observation_deck + "\n\n" + result
        else:
            result = warp_header + "\n" + result

    _t5 = _time.time()
    logger.warning(f"⏱️ ORIENT TIMING: TOTAL {_t5-_t0:.2f}s")
    return result


def _sync_kardashev_to_carton(kmap: dict) -> list[str]:
    """Sync kardashev_map.json data to CartON knowledge graph.

    Creates/updates concepts for starships, squadrons, and fleets.
    Returns list of errors (empty = success).
    """
    errors = []

    # Import CartON (same pattern as starlog.py)
    try:
        from carton_mcp.add_concept_tool import add_concept_tool_func, _get_module_connection
        carton_available = True
    except ImportError:
        return ["CartON not available - install carton_mcp to enable sync"]

    starships = kmap.get("starships", {})
    squadrons = kmap.get("squadrons", {})
    fleets = kmap.get("fleets", {})

    # Validate: each starship must have a path pointing to an initialized STARSYSTEM
    # Check via starlog registry
    try:
        from heaven_base.tools.registry_tool import registry_util_func
    except ImportError:
        errors.append("HEAVEN registry not available - can't validate STARSYSTEMs")
        return errors

    for name, ss in starships.items():
        # Each starship must have a 'path' field
        path = ss.get("path")
        if not path:
            errors.append(f"Starship '{name}' missing required 'path' field")
            continue

        # Check if this path has been initialized as a starlog project
        try:
            project_name = os.path.basename(os.path.abspath(path))
            registry_result = registry_util_func("get_all", registry_name=f"{project_name}_starlog")
            # If registry doesn't exist, project wasn't initialized
            # Use startswith to avoid false positives from "Error" appearing in session content
            if "No registry found" in registry_result or registry_result.startswith("Error"):
                errors.append(f"'{name}' at path '{path}' is not an initialized STARSYSTEM (run starlog.init_project first)")
        except Exception as e:
            errors.append(f"Failed to validate STARSYSTEM '{name}': {e}")

    # Validate: check for duplicate starship references
    all_refs = []
    for sq in squadrons.values():
        all_refs.extend(sq.get("members", []))
    for fl in fleets.values():
        all_refs.extend(fl.get("loose_starships", []))
    duplicates = [x for x in all_refs if all_refs.count(x) > 1]
    if duplicates:
        errors.append(f"Duplicate starship references: {set(duplicates)}")

    # Validate: check referenced starships exist
    for ref in all_refs:
        if ref not in starships:
            errors.append(f"Referenced starship '{ref}' doesn't exist in starships")

    # Validate: fleets with loose_starships must have at least one squadron
    for fl_name, fl in fleets.items():
        if fl.get("loose_starships") and not fl.get("squadrons"):
            errors.append(f"Fleet '{fl_name}' has loose starships but no squadrons (invalid)")

    # Validate: referenced squadrons exist in fleets
    for fl_name, fl in fleets.items():
        for sq_name in fl.get("squadrons", []):
            if sq_name not in squadrons:
                errors.append(f"Fleet '{fl_name}' references non-existent squadron '{sq_name}'")

    # If validation errors, return early
    if errors:
        return errors

    # Build ALL concepts for full ontology
    try:
        from carton_mcp.add_concept_tool import add_concept_tool_func
    except ImportError:
        errors.append("add_concept_tool_func not available")
        return errors

    concepts = []

    # Build starship concepts
    for name, ss in starships.items():
        try:
            # Compute Kardashev level from actual state
            path = ss.get("path", "")
            kardashev = "Unterraformed"

            # Planetary (K1): has .claude/ directory
            claude_dir = os.path.join(path, ".claude")
            if os.path.isdir(claude_dir):
                kardashev = "Planetary"

                # Colonized (K2): has starlog.hpi (starlog initialized)
                hpi_path = os.path.join(path, "starlog.hpi")
                if os.path.exists(hpi_path):
                    kardashev = "Colonized"

                    # Civilized (K3): has GIINT project linked
                    try:
                        with open(hpi_path, 'r') as _hf:
                            hpi_data = json.load(_hf)
                        if hpi_data.get("metadata", {}).get("giint_project_id"):
                            kardashev = "Civilized"
                    except Exception:
                        pass  # Stick with Colonized if HPI read fails

                    # Stellar (K4): check emanation score (~L3 complexity)
                    try:
                        from starsystem.reward_system import get_starsystem_health
                        health = get_starsystem_health(path)
                        emanation = health.get("components", {}).get("emanation", 0)
                        if emanation >= 0.6:  # ~L3 threshold
                            kardashev = "Stellar"
                    except Exception:
                        pass  # Stick with current level if scoring fails

            committed = "committed" if ss.get("committed", True) else "uncommitted"
            desc = f"Starship {name} | {kardashev} | {committed}"

            relationships = [
                {"relationship": "is_a", "related": ["Navy_Starship"]},
                {"relationship": "part_of", "related": ["Kardashev_Map"]},
                {"relationship": "has_kardashev_level", "related": [f"Kardashev_{kardashev}"]}
            ]

            # Add PART_OF Starsystem for complexity scoring
            if path:
                starsystem_name = f"Starsystem_{path.strip('/').replace('/', '_').replace('-', '_').title()}"
                relationships.append({"relationship": "part_of", "related": [starsystem_name]})

            concepts.append({
                "name": f"Starship_{name}",
                "description": desc,
                "relationships": relationships
            })
        except Exception as e:
            errors.append(f"Failed to build starship '{name}': {e}")

    # Build squadron concepts with HAS_MEMBER
    for name, sq in squadrons.items():
        try:
            members = sq.get("members", [])
            has_leader = "with Squad Leader" if sq.get("has_leader") else "no Squad Leader"
            desc = f"Squadron {name} | {len(members)} members | {has_leader}"

            relationships = [
                {"relationship": "is_a", "related": ["Navy_Squadron"]},
                {"relationship": "part_of", "related": ["Kardashev_Map"]}
            ]
            # Add HAS_MEMBER for each starship (parent → child)
            if members:
                relationships.append({"relationship": "has_member", "related": [f"Starship_{m}" for m in members]})

            concepts.append({
                "name": f"Squadron_{name}",
                "description": desc,
                "relationships": relationships
            })
        except Exception as e:
            errors.append(f"Failed to build squadron '{name}': {e}")

    # Build fleet concepts with HAS_SQUADRON
    for name, fl in fleets.items():
        try:
            sq_list = fl.get("squadrons", [])
            loose = fl.get("loose_starships", [])
            has_admiral = "with Admiral" if fl.get("has_admiral") else "no Admiral"
            desc = f"Fleet {name} | {len(sq_list)} squadrons, {len(loose)} loose | {has_admiral}"

            relationships = [
                {"relationship": "is_a", "related": ["Navy_Fleet"]},
                {"relationship": "part_of", "related": ["Kardashev_Map"]}
            ]
            # Add HAS_SQUADRON (parent → child)
            if sq_list:
                relationships.append({"relationship": "has_squadron", "related": [f"Squadron_{sq}" for sq in sq_list]})
            # Add HAS_LOOSE_STARSHIP
            if loose:
                relationships.append({"relationship": "has_loose_starship", "related": [f"Starship_{ss}" for ss in loose]})

            concepts.append({
                "name": f"Fleet_{name}",
                "description": desc,
                "relationships": relationships
            })
        except Exception as e:
            errors.append(f"Failed to build fleet '{name}': {e}")

    # Submit all concepts (each with raw_concept=True, no observation wrapper)
    if concepts:
        try:
            for concept in concepts:
                add_concept_tool_func(
                    concept["name"], concept["description"], concept["relationships"], hide_youknow=True
                )
        except Exception as e:
            errors.append(f"Failed to sync to CartON: {e}")

    return errors


def _get_home_dashboard() -> str:
    """Generate HOME dashboard from kardashev_map.json with hierarchy."""
    import json
    from pathlib import Path

    KARDASHEV_MAP = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "kardashev_map.json"

    INSTRUCTIONS = f"""🏠 HOME DASHBOARD

📭 No Kardashev Map found. Create one at:
   {KARDASHEV_MAP}

📋 JSON Schema:
```json
{{
  "starships": {{
    "my-project": {{"path": "/path/to/starsystem"}}
  }},
  "squadrons": {{
    "my-squadron": {{
      "members": ["my-project"],
      "has_leader": false
    }}
  }},
  "fleets": {{
    "my-fleet": {{
      "squadrons": ["my-squadron"],
      "loose_starships": [],
      "has_admiral": false
    }}
  }}
}}
```

📌 Rules:
• Each starship needs "path" pointing to an initialized STARSYSTEM
• Run starlog.init_project(path, name) first to initialize
• Kardashev level (Planetary/Stellar/Galactic) is COMPUTED from completeness quality
• XP is COMPUTED from CartON emanation health scores (not stored)
• Being in the JSON = committed to tracking

💡 Use `preflight-colonize-starsystem` skill to set up a new STARSYSTEM.
"""

    # Load or create kardashev map
    if not KARDASHEV_MAP.exists():
        KARDASHEV_MAP.parent.mkdir(parents=True, exist_ok=True)
        KARDASHEV_MAP.write_text("{}")
        return INSTRUCTIONS

    try:
        kmap = json.loads(KARDASHEV_MAP.read_text())
    except json.JSONDecodeError as e:
        return f"🏠 HOME DASHBOARD\n\n❌ JSON SYNTAX ERROR in kardashev_map.json:\n   {e}\n\nFix the JSON syntax and try again."
    except Exception as e:
        return f"🏠 HOME DASHBOARD\n\n❌ Error reading kardashev_map.json: {e}"

    # Empty map = show instructions
    if not kmap.get("starships"):
        return INSTRUCTIONS

    # Sync to CartON - this validates AND persists to knowledge graph
    sync_errors = _sync_kardashev_to_carton(kmap)
    if sync_errors:
        error_lines = ["🏠 HOME DASHBOARD", "", "❌ KARDASHEV MAP VALIDATION ERRORS:"]
        for err in sync_errors:
            error_lines.append(f"  • {err}")
        error_lines.append("")
        error_lines.append("Fix kardashev_map.json and try again.")
        return "\n".join(error_lines)

    starships = kmap.get("starships", {})
    squadrons = kmap.get("squadrons", {})
    fleets = kmap.get("fleets", {})

    # Batch compute health for ALL starships in one UNWIND query
    valid_paths = [ss.get("path", "") for ss in starships.values()
                   if ss.get("path") and os.path.isdir(ss.get("path", ""))]
    try:
        from starsystem.reward_system import get_fleet_health
        fleet_health = get_fleet_health(valid_paths)
    except ImportError:
        fleet_health = {}

    # XP computed from batch health — NOT flat counter
    fleet_xp = _compute_fleet_xp(starships, health_cache=fleet_health)
    xp = fleet_xp["xp"]

    # Compute Kardashev levels for each starship
    # 3-level completeness model (Isaac canonical, Mar 2 2026)
    def _compute_kardashev(path: str) -> str:
        if not path or not os.path.isdir(path):
            return "Unterraformed"

        # K1 (Planetary): Has GIINT project — tracked and structured
        hpi_path = os.path.join(path, "starlog.hpi")
        has_giint = False
        if os.path.exists(hpi_path):
            try:
                with open(hpi_path, 'r') as _hf:
                    hpi_data = json.load(_hf)
                if hpi_data.get("metadata", {}).get("giint_project_id"):
                    has_giint = True
            except Exception:
                pass

        if not has_giint:
            return "Unterraformed"

        # K2 (Stellar): Has .claude/ with rules AND skills — properly set up
        claude_dir = os.path.join(path, ".claude")
        has_rules_and_skills = False
        if os.path.isdir(claude_dir):
            rules_dir = os.path.join(claude_dir, "rules")
            skills_dir = os.path.join(claude_dir, "skills")
            try:
                has_rules = os.path.isdir(rules_dir) and bool(list(os.scandir(rules_dir)))
                has_skills = os.path.isdir(skills_dir) and bool(list(os.scandir(skills_dir)))
                has_rules_and_skills = has_rules and has_skills
            except Exception:
                pass

        if not has_rules_and_skills:
            return "Planetary"

        # K3 (Galactic): Completed measurable % — health threshold met
        # Uses pre-computed fleet_health from batch UNWIND query
        if path in fleet_health:
            health_score = fleet_health[path].get("health", 0)
            if health_score >= 0.6:
                return "Galactic"

        return "Stellar"

    computed_levels = {name: _compute_kardashev(ss.get("path", "")) for name, ss in starships.items()}

    # Calculate title and type from computed levels (3-level Kardashev)
    galactics = sum(1 for lvl in computed_levels.values() if lvl == "Galactic")
    stellars = sum(1 for lvl in computed_levels.values() if lvl == "Stellar")
    planetaries = sum(1 for lvl in computed_levels.values() if lvl == "Planetary")
    squads_with_leaders = sum(1 for sq in squadrons.values() if sq.get("has_leader"))
    fleets_with_admirals = sum(1 for fl in fleets.values() if fl.get("has_admiral"))

    # Determine title (CADET → ENSIGN → COMMANDER → CAPTAIN → COMMODORE → ADMIRAL)
    if fleets_with_admirals > 0:
        title, type_n = "ADMIRAL", fleets_with_admirals
    elif squads_with_leaders > 0:
        title, type_n = "COMMODORE", squads_with_leaders
    elif galactics > 0:
        title, type_n = "CAPTAIN", galactics
    elif stellars > 0:
        title, type_n = "COMMANDER", stellars
    elif planetaries > 0:
        title, type_n = "ENSIGN", planetaries
    else:
        title, type_n = "CADET", 0

    level = fleet_xp["level"]

    # Kardashev level display helpers (3-level model)
    _kardashev_icons = {
        "Galactic": "🌌", "Stellar": "⭐", "Planetary": "🌍", "Unterraformed": "⚫"
    }
    _kardashev_labels = {
        "Galactic": "🌌 GALACTIC", "Stellar": "⭐ STELLAR",
        "Planetary": "🌍 PLANETARY", "Unterraformed": "⚫ UNTERRAFORMED"
    }

    # Build display
    lines = [
        "=" * 60,
        f"  ⚓ TITLE: {title}  |  TYPE: {type_n}  |  LEVEL: {level}",
        f"  ⭐ XP: {xp:,} / {(level + 1) * 1000:,}",
        "=" * 60,
    ]

    # Find loose starships (not in any squadron or fleet)
    assigned = set()
    for sq in squadrons.values():
        assigned.update(sq.get("members", []))
    for fl in fleets.values():
        assigned.update(fl.get("loose_starships", []))
    loose = [name for name in starships if name not in assigned]

    if loose:
        lines.append("\n  LOOSE STARSHIPS:")
        for name in loose:
            lvl = computed_levels.get(name, "Unterraformed")
            status = _kardashev_labels.get(lvl, "⚫ UNTERRAFORMED")
            lines.append(f"    {name}: {status}")

    # Loose squadrons (not in any fleet)
    assigned_sq = set()
    for fl in fleets.values():
        assigned_sq.update(fl.get("squadrons", []))
    loose_sq = [name for name in squadrons if name not in assigned_sq]

    if loose_sq:
        lines.append("\n  SQUADRONS (not in fleet):")
        for name in loose_sq:
            sq = squadrons[name]
            leader = "✓ Leader" if sq.get("has_leader") else "✗ No Leader"
            lines.append(f"    {name} [{leader}]:")
            for member in sq.get("members", []):
                lvl = computed_levels.get(member, "Unterraformed")
                icon = _kardashev_icons.get(lvl, "⚫")
                lines.append(f"      {icon} {member} ({lvl})")

    # Fleets
    if fleets:
        lines.append("\n  FLEETS:")
        for name, fl in fleets.items():
            admiral = "✓ Admiral" if fl.get("has_admiral") else "✗ No Admiral"
            lines.append(f"    {name} [{admiral}]")
            for sq_name in fl.get("squadrons", []):
                sq = squadrons.get(sq_name, {})
                leader = "✓" if sq.get("has_leader") else "✗"
                lines.append(f"      └─ Squadron {sq_name} [{leader}]:")
                for member in sq.get("members", []):
                    lvl = computed_levels.get(member, "Unterraformed")
                    icon = _kardashev_icons.get(lvl, "⚫")
                    lines.append(f"           {icon} {member} ({lvl})")
            if fl.get("loose_starships"):
                lines.append(f"      └─ Loose:")
                for ls in fl.get("loose_starships", []):
                    lvl = computed_levels.get(ls, "Unterraformed")
                    icon = _kardashev_icons.get(lvl, "⚫")
                    lines.append(f"           {icon} {ls} ({lvl})")

    lines.append("")
    lines.append("💡 Use `preflight-colonize-starsystem` skill to set up a new STARSYSTEM.")
    lines.append("")
    return "\n".join(lines)

@app.tool()
def rules(path: str) -> str:
    """View project guidelines and standards. Use this to check what coding standards and project rules have been established."""
    logger.debug(f"rules called with path={path}")
    return starlog.rules(path)

@app.tool()
def update_rules(rules_data: list[RulesEntry], path: str) -> str:
    """Replace all project rules with RulesEntry models."""
    logger.debug(f"update_rules called with path={path}, count={len(rules_data)}")
    project_name = starlog._get_project_name_from_path(path)
    
    # Clear existing rules and add new ones
    for rule in rules_data:
        starlog._save_rules_entry(project_name, rule)
    
    return f"✅ Updated {len(rules_data)} rules for {project_name}"

@app.tool()
def add_rule(rule: str, path: str, category: str = "general") -> str:
    """Create new project guideline or standard. Use this to establish coding standards, project conventions, or other guidelines during development."""
    logger.debug(f"add_rule called with path={path}, category={category}")
    return starlog.add_rule(rule, path, category)

@app.tool()
def delete_rule(rule_id: str, path: str) -> str:
    """Remove specific rule."""
    logger.debug(f"delete_rule called with path={path}, rule_id={rule_id}")
    return starlog.delete_rule(rule_id, path)

def _has_active_session(project_name: str) -> bool:
    """Check if project has an active (non-ended) session."""
    try:
        starlog_data = starlog._get_registry_data(project_name, "starlog")
        if not starlog_data:
            return False
        
        # Check for any session without end_timestamp
        for session_id, session_data in starlog_data.items():
            if session_data.get("end_timestamp") is None:
                return True
        
        return False
    except Exception as e:
        logger.error(f"Failed to check active sessions: {e}", exc_info=True)
        return False

def _log_warpcore_work_phase(project_name: str) -> None:
    """Log WARPCORE phase 2 (work phase) if not already logged for current session."""
    try:
        # Check if work phase already logged for current session
        diary_data = starlog._get_registry_data(project_name, "debug_diary")
        if diary_data:
            # Get current session start time
            starlog_data = starlog._get_registry_data(project_name, "starlog")
            session_start = None
            for session_id, session_data in starlog_data.items():
                if session_data.get("end_timestamp") is None:
                    session_start = session_data.get("timestamp")
                    break
            
            if session_start:
                # Check if WARPCORE work phase already logged since session start
                for entry_id, entry_data in diary_data.items():
                    entry_timestamp = entry_data.get("timestamp", "")
                    entry_content = entry_data.get("content", "")
                    if (entry_timestamp >= session_start and 
                        "[WARPCORE]: Jumping. Warp phase (2/3): 🌌" in entry_content):
                        return  # Already logged
        
        # Log work phase
        from .models import DebugDiaryEntry
        work_entry = DebugDiaryEntry(
            content="[WARPCORE]: Jumping. Warp phase (2/3): 🌌"
        )
        starlog._save_debug_diary_entry(project_name, work_entry)
        
    except Exception as e:
        logger.error(f"Failed to log WARPCORE work phase: {e}", exc_info=True)

def _has_warpcore_work_phase(project_name: str) -> bool:
    """Check if current session has WARPCORE work phase logged."""
    try:
        diary_data = starlog._get_registry_data(project_name, "debug_diary")
        if not diary_data:
            return False
            
        # Get current session start time
        starlog_data = starlog._get_registry_data(project_name, "starlog")
        session_start = None
        for session_id, session_data in starlog_data.items():
            if session_data.get("end_timestamp") is None:
                session_start = session_data.get("timestamp")
                break
        
        if not session_start:
            return False
            
        # Check if WARPCORE work phase logged since session start
        for entry_id, entry_data in diary_data.items():
            entry_timestamp = entry_data.get("timestamp", "")
            entry_content = entry_data.get("content", "")
            if (entry_timestamp >= session_start and 
                "[WARPCORE]: Jumping. Warp phase (2/3): 🌌" in entry_content):
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Failed to check WARPCORE work phase: {e}", exc_info=True)
        return False

@app.tool()
def view_debug_diary(path: str, filter_type: str = "all", last_n: int = None) -> str:
    """Check current project status and recent entries.

    Args:
        path: Project path
        filter_type: Filter by type - all, bug_report, bug_fix, has_file, has_insights
        last_n: Limit to last N entries (optional)
    """
    logger.debug(f"view_debug_diary called with path={path}, filter_type={filter_type}, last_n={last_n}")
    return starlog.view_debug_diary(path, filter_type, last_n)

@app.tool()
def update_debug_diary(path: str, diary_entry: DebugDiaryEntry = None, entry: DebugDiaryEntry = None, debug_diary: DebugDiaryEntry = None) -> str:
    """Log real-time discoveries, bugs, insights during work. Use this frequently during your work session to track progress and issues.

    Args:
        path: Project path
        diary_entry: The diary entry (also accepts 'entry' or 'debug_diary')
        entry: Alias for diary_entry
        debug_diary: Alias for diary_entry
    """
    # Accept any of the parameter name variations
    the_entry = diary_entry or entry or debug_diary
    if not the_entry:
        return "❌ Must provide diary_entry, entry, or debug_diary parameter"

    logger.debug(f"update_debug_diary called with path={path}")
    project_name = starlog._get_project_name_from_path(path)

    # Check if there's an active session
    if not _has_active_session(project_name):
        return f"❌ Debug diary entries can only be added during active sessions. Use start_starlog() first."

    # Log WARPCORE work phase
    _log_warpcore_work_phase(project_name)

    result = starlog._save_debug_diary_entry(project_name, the_entry)

    # Mirror to CartON - use timestamp for chronological sorting
    ts = the_entry.timestamp.strftime('%Y%m%d_%H%M%S')
    starlog.mirror_to_carton(
        concept_name=f"Debug_Diary_{ts}",
        description=the_entry.content,
        relationships=[{"relationship": "is_a", "related": ["Debug_Diary_Entry"]}],
        project_name=project_name
    )

    return "✅ Updated debug diary\n💡 Hint: Mark all bug finds (bug_report=True) and fixes (bug_fix=True)"

@app.tool()
def view_starlog(path: str, last_n: int = 5) -> str:
    """Get recent session history. Shows last N sessions (default 5) with status, goals, and duration."""
    logger.debug(f"view_starlog called with path={path}, last_n={last_n}")
    return starlog.view_starlog(path, last_n)

def _update_recent_projects(project_path: str) -> None:
    """Update recent projects list, moving project to front and deduping."""
    try:
        from heaven_base.tools.registry_tool import registry_util_func
        
        # Get current recent projects
        recent_data = {}
        try:
            recent_result = registry_util_func("get_all", registry_name="starlog_recent_projects")
            if "Items in registry" in recent_result:
                # Extract the dictionary part from the result string
                start_idx = recent_result.find("{") 
                if start_idx != -1:
                    dict_str = recent_result[start_idx:]
                    # Handle Python literals (None, True, False) in the registry data
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    recent_data = json.loads(dict_str.replace("'", '"'))
        except Exception:
            # Registry doesn't exist yet, start fresh
            pass
        
        # Remove project if it already exists (for deduplication)
        keys_to_remove = []
        for key, value in recent_data.items():
            if value.get("project") == project_path:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            registry_util_func("delete", registry_name="starlog_recent_projects", key=key)
        
        # Add project to front with current timestamp as key
        from datetime import datetime
        timestamp_key = datetime.now().isoformat()
        registry_util_func("add", 
                          registry_name="starlog_recent_projects", 
                          key=timestamp_key,
                          value_dict={"project": project_path})
        
        # Prune to keep only 100 most recent
        updated_result = registry_util_func("get_all", registry_name="starlog_recent_projects")
        if "Items in registry" in updated_result:
            start_idx = updated_result.find("{") 
            if start_idx != -1:
                dict_str = updated_result[start_idx:]
                dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                updated_data = json.loads(dict_str.replace("'", '"'))
            if len(updated_data) > 100:
                # Sort by timestamp (key) and keep only newest 100
                sorted_keys = sorted(updated_data.keys(), reverse=True)
                keys_to_prune = sorted_keys[100:]
                for key in keys_to_prune:
                    registry_util_func("delete", registry_name="starlog_recent_projects", key=key)
        
        logger.debug(f"Updated recent projects with {project_path}")
        
    except Exception as e:
        logger.error(f"Failed to update recent projects: {e}", exc_info=True)

@app.tool()
def start_starlog(session_title: str, start_content: str, session_goals: List[str], path: str, relevant_docs: List[str] = None) -> str:
    """Begin tracked development session with goals and context. Use this to start a new work session after orient() provides project context."""
    logger.debug(f"start_starlog called with path={path}, title={session_title}")

    # Update recent projects list
    _update_recent_projects(path)

    # Auto-inject session into mission if mission is active
    HEAVEN_DATA_DIR = os.environ["HEAVEN_DATA_DIR"]
    COURSE_STATE_FILE = os.path.join(HEAVEN_DATA_DIR, "omnisanc_core", ".course_state")
    if os.path.exists(COURSE_STATE_FILE):
        try:
            with open(COURSE_STATE_FILE, 'r') as f:
                course_state = json.load(f)

            if course_state.get("mission_active"):
                mission_id = course_state.get("mission_id")

                # Get current flight config from waypoint state
                # Waypoint state is stored as /tmp/waypoint_state_{project_basename}.json
                project_name = os.path.basename(path)
                waypoint_state_file = f"/tmp/waypoint_state_{project_name}.json"
                flight_config = "unknown_flight"
                if os.path.exists(waypoint_state_file):
                    try:
                        with open(waypoint_state_file, 'r') as wf:
                            waypoint_data = json.load(wf)
                            config_path = waypoint_data.get("config_path", "")
                            # Extract flight config name from path like "/path/to/debug_flight_config.json"
                            flight_config = os.path.basename(config_path).replace("_flight_config.json", "").replace(".json", "")
                    except Exception as e:
                        logger.warning(f"Failed to read waypoint state: {e}")

                # Auto-inject step into mission
                from starsystem.mission import inject_step
                inject_step(mission_id, path, flight_config)
                logger.info(f"Auto-injected session into mission {mission_id}: {path} with {flight_config}")
        except Exception as e:
            logger.error(f"Failed to auto-inject mission step: {e}")
            # Don't fail session start if injection fails - just log and continue

    # Call the actual starlog method that includes debug diary creation
    context_from_docs = ', '.join(relevant_docs or [])
    result = starlog.start_starlog(session_title, start_content, context_from_docs, session_goals, path)
    return result

@app.tool()
def end_starlog(end_content: str, path: str, 
                key_discoveries: List[str] = None, files_updated: List[str] = None, 
                challenges_faced: List[str] = None) -> str:
    """Complete session with summary and outcomes. Use this to properly close your work session with a summary of what was accomplished."""
    logger.debug(f"end_starlog called with path={path}")
    project_name = starlog._get_project_name_from_path(path)
    
    # Check WARPCORE sequence - must have work phase before ending
    if not _has_warpcore_work_phase(project_name):
        return f"❌ WARPCORE sequence violation: No jumping detected. Use fly() or update_debug_diary() first."
    
    # If additional fields provided, update session before ending
    if key_discoveries or files_updated or challenges_faced:
        active_session = starlog._find_active_session(project_name)
        if not active_session:
            return f"❌ No active session found"
        
        # Update session with provided fields
        if key_discoveries:
            active_session.key_discoveries = key_discoveries
        if files_updated:
            active_session.files_updated = files_updated
        if challenges_faced:
            active_session.challenges_faced = challenges_faced
        
        # Save updated session back to registry
        starlog._update_registry_item(project_name, "starlog", active_session.id, active_session.model_dump(mode='json'))
    
    # Delegate to the working StarlogSessionsMixin method
    result = starlog.end_starlog(end_content, path)
    return result

@app.tool()
def retrieve_starlog(project: str, session_id: str = None, 
                    date_range: str = None, paths: bool = False) -> str:
    """Selective historical retrieval."""
    logger.debug(f"retrieve_starlog called with project={project}, session_id={session_id}, date_range={date_range}, paths={paths}")
    return starlog.retrieve_starlog(project, session_id, date_range, paths)

@app.tool()
def starlog_guide() -> str:
    """Returns STARLOG system workflow and tool usage guide."""
    
    return f"""
<STARLOG_GUIDE>
🌌📖 STARLOG System - Development Session Tracking Flow

check(path) [¹]
    ↓
    Is STARLOG project?
    ├─ NO → init_project(path, name, description) [²]
    └─ YES → orient(path) [³]
    ↓
start_starlog(session_data, path) [⁴]
    ↓
[Work Loop - choose as needed:]
├─ update_debug_diary(entry, path) [⁵]
├─ view_debug_diary(path) [⁶]
├─ view_starlog(path) [⁷]
├─ rules(path) [⁸]
└─ add_rule(rule, path) [⁹]
    ↓
end_starlog(session_id, summary, path) [¹⁰]

[¹] Check: Verifies if directory is a STARLOG project
[²] Init: Creates project structure with registries and HPI template  
[³] Orient: Returns full Captain's Log XML context for existing projects
[⁴] Start: Begin tracked development session with goals and context
[⁵] Update Diary: Log real-time discoveries, bugs, insights during work
[⁶] View Diary: Check current project status and recent entries
[⁷] View Sessions: Review session history and past work
[⁸] Rules: View project guidelines and standards
[⁹] Add Rule: Create new project guideline or standard
[¹⁰] End: Complete session with summary and outcomes

STARLOG creates Captain's Log style XML output for AI context injection.
</STARLOG_GUIDE>
"""

@app.tool()
async def query_project_rules(
    path: str, 
    context: str, 
    persona_id: str = None, 
    persona_str: str = None, 
    mode_id: str = None, 
    mode_str: str = None
) -> str:
    """Query project rules brain for development guidance based on context.
    
    Args:
        path: Project path containing STARLOG rules
        context: Development context/question to query
        persona_id: Predefined persona ID. Available personas:
            - 'logical_philosopher': Rigorous logical analysis with explicit premises
            - 'senior_scientist': Methodical, evidence-driven, cautious with claims
            - 'senior_engineer': Pragmatic implementation guidance with trade-offs
        persona_str: Custom persona description (e.g., 'experienced backend developer')
        mode_id: Predefined mode ID. Available modes:
            - 'summarize': Comprehensive summary relating neuron content to query
            - 'imagine': Creative connections between content and imaginary scenarios
            - 'reify': Actionable steps to make concrete ideas reality
        mode_str: Custom mode description (e.g., 'provide step-by-step instructions')
    """
    logger.debug(f"query_project_rules called with path={path}, context={context}, persona_id={persona_id}, persona_str={persona_str}, mode_id={mode_id}, mode_str={mode_str}")
    
    try:
        from .rules_brain_integration import query_project_rules as async_query
        
        # Pass persona/mode parameters to the async function
        result = await async_query(path, context, persona_id, persona_str, mode_id, mode_str)
        return result
        
    except ImportError:
        return "❌ brain-agent not available - cannot query rules brain"
    except Exception as e:
        logger.error(f"Error in query_project_rules: {e}", exc_info=True)
        return f"❌ Error querying rules brain: {str(e)}"


def _find_flight_config_by_name(flight_data: dict, name: str, path: str) -> Optional[Tuple[str, dict]]:
    """Find flight config by name and path. Returns (config_id, config_data) or None."""
    for config_id, config in flight_data.items():
        if config.get("name") == name and config.get("original_project_path") == path:
            return config_id, config
    return None

def _validate_flight_config_name(name: str) -> Optional[str]:
    """Validate flight config name convention. Returns error message or None."""
    if not name.endswith("_flight_config"):
        return "❌ Flight config names must end with '_flight_config'"
    return None

def _validate_payload_discovery_path(path: Optional[str]) -> Optional[str]:
    """Validate PayloadDiscovery file exists. Returns error message or None."""
    if path and not os.path.exists(path):
        return f"❌ PayloadDiscovery file not found: {path}"
    return None

def _filter_flight_data(flight_data: dict, path: str, this_project_only: bool, category: str = None) -> dict:
    """Filter flight data by project and category."""
    if this_project_only:
        flight_data = {k: v for k, v in flight_data.items() 
                      if v.get("original_project_path") == path}
    
    if category:
        flight_data = {k: v for k, v in flight_data.items() 
                      if v.get("category") == category}
    
    return flight_data


def _create_default_flight(path: str) -> str:
    """Create default flight if none exist."""
    flight_path = os.path.join(path, "starlog_flight.json")
    if not os.path.exists(flight_path):
        flight_pd = StarlogPayloadDiscoveryConfig()
        with open(flight_path, 'w') as f:
            json.dump(flight_pd.model_dump(), f, indent=2)
        logger.info(f"Created default Flight PayloadDiscovery for Waypoint at {flight_path}")
    
    return f"""📋 No custom flight configs found

✅ Created default STARLOG flight configuration at:
   {flight_path}

🚀 To start a STARLOG session, use:
   start_waypoint_journey('{flight_path}', '{path}')

🌐 Global flight configs ARE available! You're seeing all available configs by default.
💡 Set this_project_only=true to view flight configs from a specific STARLOG project only.

💡 To create custom flight configs for your project:
   - Use add_flight_config() to create domain-specific workflows
   - Flight configs extend the base STARLOG session with custom subchains that are Waypoint journeys (`PayloadDiscovery`s)
   - Subchains work best when they are configured as infinitely repeatable processes
   - For example a 'write_documentation' subchain is best formatted as 'detect if there is documentation in this code and add or refine it as necessary' instead of 'detect code that needs documentation and add it'
   - Or a 'write_5_paragraph_essay' subchain is best formatted as 'create or edit a 5 paragraph essay at path' instead of 'write a 5 paragraph essay xyz'
   - Examples: research_flight_config, debugging_flight_config, analysis_flight_config"""


def _show_categories_page(flight_data: dict) -> str:
    """Show main categories page."""
    categories = list(set(v.get("category", "general") for v in flight_data.values()))
    total_configs = len(flight_data)
    
    configs_per_category = {}
    for cat in categories:
        configs_per_category[cat] = len([v for v in flight_data.values() 
                                       if v.get("category") == cat])
    
    result = f"Available Flight Categories ({total_configs} total configs):\\n"
    for cat, count in configs_per_category.items():
        result += f"- {cat} ({count} configs)\\n"
    result += f"\\nUse fly(path, category='name') to browse categories"
    return result


def _show_paginated_configs(flight_data: dict, page: int, category: str, path: str) -> str:
    """Show paginated list of configs."""
    configs_list = list(flight_data.items())
    page_size = 5
    total_pages = (len(configs_list) + page_size - 1) // page_size
    total_configs = len(flight_data)
    
    if page is None:
        page = 1
        
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_configs = configs_list[start_idx:end_idx]
    
    if category:
        result = f"{category.title()} Flight Configs ({total_configs} configs, page {page}/{total_pages}):\\n"
    else:
        result = f"All Flight Configs (page {page}/{total_pages}):\\n"
        
    for i, (config_id, config_data) in enumerate(page_configs, start_idx + 1):
        name = config_data.get("name", "Unnamed")
        desc = config_data.get("description", "No description")
        result += f"{i}. {name} - {desc}\\n"
    
    if total_pages > 1:
        result += f"\\nUse fly('{path}', page={page+1}" 
        if category:
            result += f", category='{category}'"
        result += ") for more"
        
    return result


def internal_add_flight_config(path: str, name: str, config_data: dict, category: str = "general") -> str:
    """Create new flight config with validation."""
    logger.debug(f"add_flight_config called with path={path}, name={name}, category={category}")
    
    try:
        # Validate flight config name convention
        if not name.endswith("_flight_config"):
            return "❌ Flight config names must end with '_flight_config'"
        
        # Validate that user is providing a subchain (required for custom flight configs)
        subchain_path = config_data.get("work_loop_subchain")
        if not subchain_path:
            return "❌ Custom flight configs must specify a work_loop_subchain"
        
        # Validate the PayloadDiscovery file exists
        if not os.path.exists(subchain_path):
            return f"❌ PayloadDiscovery file not found: {subchain_path}"
        
        # Now create FlightConfig instance
        flight_config = FlightConfig(
            name=name,
            original_project_path=path,
            category=category,
            description=config_data.get("description", ""),
            work_loop_subchain=subchain_path
        )
        
        # Save to registry
        result = starlog._save_flight_config(flight_config)
        
        if "added to registry" in result:
            return f"✅ Created flight config '{name}' in category '{category}'"
        else:
            return f"❌ Failed to create flight config: {result}"
            
    except Exception as e:
        logger.error(f"Error creating flight config: {e}", exc_info=True)
        return f"❌ Error creating flight config: {str(e)}"


def internal_delete_flight_config(path: str, name: str) -> str:
    """Remove flight config."""
    logger.debug(f"delete_flight_config called with path={path}, name={name}")
    
    try:
        # Find the flight config by name and path
        flight_data = starlog._get_flight_configs_registry_data()
        flight_id = None
        
        for config_id, config in flight_data.items():
            if config.get("name") == name and config.get("original_project_path") == path:
                flight_id = config_id
                break
        
        if not flight_id:
            return f"❌ Flight config '{name}' not found for project at {path}"
        
        # Delete from registry
        result = registry_util_func("delete", registry_name="starlog_flight_configs", key=flight_id)
        
        if "deleted from registry" in result:
            return f"✅ Deleted flight config '{name}'"
        else:
            return f"❌ Failed to delete flight config: {result}"
            
    except Exception as e:
        logger.error(f"Error deleting flight config: {e}", exc_info=True)
        return f"❌ Error deleting flight config: {str(e)}"


def internal_update_flight_config(path: str, name: str, config_data: dict) -> str:
    """Modify existing flight config."""
    logger.debug(f"update_flight_config called with path={path}, name={name}")
    
    try:
        # Find the flight config
        flight_data = starlog._get_flight_configs_registry_data()
        flight_id = None
        current_config = None
        
        for config_id, config in flight_data.items():
            if config.get("name") == name and config.get("original_project_path") == path:
                flight_id = config_id
                current_config = config
                break
        
        if not flight_id:
            return f"❌ Flight config '{name}' not found for project at {path}"
        
        # Update the config
        updated_config = FlightConfig(**current_config)
        
        if "description" in config_data:
            updated_config.description = config_data["description"]
        if "work_loop_subchain" in config_data:
            updated_config.work_loop_subchain = config_data["work_loop_subchain"]
        if "category" in config_data:
            updated_config.category = config_data["category"]
        
        updated_config.updated_at = datetime.now()
        
        # Validate PayloadDiscovery path if provided
        if updated_config.work_loop_subchain:
            import os
            if not os.path.exists(updated_config.work_loop_subchain):
                return f"❌ PayloadDiscovery file not found: {updated_config.work_loop_subchain}"
        
        # Save updated config
        result = registry_util_func("update", 
                                  registry_name="starlog_flight_configs", 
                                  key=flight_id, 
                                  value_dict=updated_config.model_dump(mode='json'))
        
        if "updated in registry" in result:
            return f"✅ Updated flight config '{name}'"
        else:
            return f"❌ Failed to update flight config: {result}"
            
    except Exception as e:
        logger.error(f"Error updating flight config: {e}", exc_info=True)
        return f"❌ Error updating flight config: {str(e)}"


def internal_read_starlog_flight_config_instruction_manual() -> str:
    """Show flight config schema, examples, and usage guide."""
    
    return """
🧭 STARSHIP Flight Config Instruction Manual

## Overview
Flight configs extend the base STARLOG session workflow with domain-specific subchains.
They provide a way to customize STARLOG sessions for different project types while 
maintaining the immutable base STARLOG structure.

## Schema
```json
{
  "name": "research_methodology_flight_config",
  "category": "research", 
  "description": "Systematic literature review and analysis workflow",
  "work_loop_subchain": "/configs/research_methodology_waypoint.json"
}
```

## Naming Convention
✅ REQUIRED: Flight config names MUST end with '_flight_config'
- research_methodology_flight_config ✅
- debugging_analysis_flight_config ✅ 
- giint_integration_flight_config ✅
- research_waypoint ❌ (this is a regular waypoint)

## Subchain Requirements
- work_loop_subchain: Path to PayloadDiscovery JSON config (required for custom flight configs)
- Subchains should be amplificatory (repeatable processes)
- Example: "detect and improve documentation" vs "write documentation"

## PayloadDiscovery Help
For creating PayloadDiscovery configs, use:
python -c 'import payload_discovery; help(payload_discovery)'

## Usage Examples

### Create Flight Config:
add_flight_config(
    path="/my/project",
    name="research_flight_config",
    config_data={
        "description": "Systematic research methodology",
        "work_loop_subchain": "/configs/research_waypoint.json"
    },
    category="research"
)

### Use Flight Config:
start_waypoint_journey(config_path="/configs/research_waypoint.json", starlog_path="/my/project")

### Management:
- fly(path) - Browse existing configs
- update_flight_config(path, name, new_data)
- delete_flight_config(path, name)

## Architecture
Base STARLOG: check → orient → start → work_loop → end
With Flight Config: check → orient → start → work_loop + subchain → end

The subchain executes as part of work_loop, then returns control to STARLOG for proper session closure.
"""


@app.tool()
def list_most_recent_projects(page: Optional[int] = None) -> str:
    """List most recently used STARLOG projects with pagination."""
    logger.debug(f"list_most_recent_projects called with page={page}")
    
    try:
        from heaven_base.tools.registry_tool import registry_util_func
        
        # Get recent projects registry
        recent_data = {}
        try:
            recent_result = registry_util_func("get_all", registry_name="starlog_recent_projects")
            if "Items in registry" in recent_result:
                start_idx = recent_result.find("{") 
                if start_idx != -1:
                    dict_str = recent_result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    recent_data = json.loads(dict_str.replace("'", '"'))
        except Exception:
            return "📁 No recent projects found. Start a STARLOG session to track projects."
        
        if not recent_data:
            return "📁 No recent projects found. Start a STARLOG session to track projects."
        
        # Sort by timestamp (key) to get most recent first
        sorted_items = sorted(recent_data.items(), key=lambda x: x[0], reverse=True)
        projects = [item[1]["project"] for item in sorted_items]
        
        # Pagination
        page_size = 10
        total_projects = len(projects)
        total_pages = (total_projects + page_size - 1) // page_size
        
        if page is None:
            page = 1
        
        if page < 1 or page > total_pages:
            return f"❌ Page {page} out of range. Available pages: 1-{total_pages}"
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_projects = projects[start_idx:end_idx]
        
        result = f"📁 Most Recent STARLOG Projects (page {page}/{total_pages}, {total_projects} total):\n\n"
        for i, project_path in enumerate(page_projects, start_idx + 1):
            result += f"{i}. {project_path}\n"
        
        if total_pages > 1:
            result += f"\n💡 Use list_most_recent_projects(page={page+1}) for more"
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing recent projects: {e}", exc_info=True)
        return f"❌ Error listing recent projects: {str(e)}"

def internal_fly(path: str, page: int = None, category: str = None, this_project_only: bool = False, search: str = None, show_all: bool = False) -> str:
    """Browse and search flight configurations with pagination and categories.

    Args:
        path: STARLOG project path
        page: Page number for pagination
        category: Category to filter by
        this_project_only: Filter to current project only
        search: Search string to filter flight names/descriptions
        show_all: If True, show all flights in flat list (ignore categories)
    """
    logger.debug(f"fly called with path={path}, page={page}, category={category}, this_project_only={this_project_only}")
    
    try:
        project_name = starlog._get_project_name_from_path(path)
        
        # Log WARPCORE work phase only if we have an active session
        if _has_active_session(project_name):
            _log_warpcore_work_phase(project_name)
        
        flight_data = starlog._get_flight_configs_registry_data()
        flight_data = _filter_flight_data(flight_data, path, this_project_only, category)

        # Search filter - match name or description
        if search:
            search_lower = search.lower()
            flight_data = {
                k: v for k, v in flight_data.items()
                if search_lower in v.get("name", "").lower() or search_lower in v.get("description", "").lower()
            }
            if not flight_data:
                return f"🔍 No flights found matching '{search}'"
            # Show search results as flat list
            lines = [f"🔍 Flights matching '{search}' ({len(flight_data)} found):\n"]
            for config_id, config in sorted(flight_data.items(), key=lambda x: x[1].get("name", "")):
                name = config.get("name", "Unnamed")
                desc = config.get("description", "No description")[:60]
                cat = config.get("category", "general")
                lines.append(f"  • {name} [{cat}]\n    {desc}")
            lines.append(f"\nTo start: waypoint__start_waypoint_journey(config_path=\"<name>\", starlog_path=\"{path}\")")
            return "\n".join(lines)

        # Show all flights flat (no category drill-down)
        if show_all:
            lines = [f"🚀 All Flight Configs ({len(flight_data)} total):\n"]
            for config_id, config in sorted(flight_data.items(), key=lambda x: x[1].get("name", "")):
                name = config.get("name", "Unnamed")
                desc = config.get("description", "No description")[:60]
                cat = config.get("category", "general")
                lines.append(f"  • {name} [{cat}]\n    {desc}")
            lines.append(f"\nTo start: waypoint__start_waypoint_journey(config_path=\"<name>\", starlog_path=\"{path}\")")
            return "\n".join(lines)

        if category is None:
            # Check if any flight configs exist in registry
            if not flight_data:
                return f"""📋 No flight configs found in registry

💡 To get started with flight configs:
   1. Populate default configs: starship__populate_default_flight_configs()
   2. Create custom configs: starship__add_flight_config()

Default STARLOG Workflow (without flight configs):
  1. Check STARLOG project: starlog__check()
  2. Init or Orient: starlog__init_project() or starlog__orient()
  3. Start session: starlog__start_starlog()
  4. Work loop (debug diary, rules, etc.)
  5. End session: starlog__end_starlog()

Once flight configs are populated, you can browse them with fly()"""

            # Show categories from registry data
            categories = list(set(v.get("category", "general") for v in flight_data.values()))
            num_categories = len(categories)

            return f"""🚀 STARLOG Flight Configurations (Registry-Based)

Available Flight Categories: {num_categories} categories
Total Flight Configs: {len(flight_data)}

To browse a category:
  fly(path="{path}", category="category_name")

To start a flight:
  starship__fly(flight_config_name="config_name")

Categories: {', '.join(sorted(categories))}"""
        
        # Category specified - show that category with optional pagination
        return _show_paginated_configs(flight_data, page, category, path)
        
    except Exception as e:
        logger.error(f"Error in fly: {e}", exc_info=True)
        return f"❌ Error browsing flight configs: {str(e)}"


def main():
    """Main entry point for console script."""
    logger.info("Starting STARLOG MCP server")
    app.run()

if __name__ == "__main__":
    main()