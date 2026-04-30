"""TreeShell functions for sanctuary-revolution - wraps SanctuaryRevolution methods.

Sanctuary-revolution is the ORCHESTRATOR interface - it defines WHAT to build.
paia-builder is the BUILDER - it ACTUALLY builds things and tracks GEAR experience.
The agent uses BOTH: sancrev for goals, paia-builder for execution.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from sanctuary_revolution import SanctuaryRevolution

# Harness URL for event emission (container-local)
# TRIGGERS: sancrev harness:8000 via HTTP POST — event emission to SSE frontend
HARNESS_URL = os.environ.get("HARNESS_URL", "http://localhost:8000")


def _emit_event(event_type: str, data: dict = None, paia_name: str = None, message: str = None):
    """Emit event to harness → SSE → frontend.

    Fire-and-forget: doesn't block on failure.
    """
    try:
        payload = json.dumps({
            "event_type": event_type,
            "data": data or {},
            "paia_name": paia_name or _get_game()._get_current_name(),
            "message": message
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{HARNESS_URL}/event",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=1)
    except (urllib.error.URLError, TimeoutError, Exception):
        pass  # Fire-and-forget

# Import paia-builder for GEAR integration
try:
    from paia_builder import PAIABuilder
    _paia_builder: Optional[PAIABuilder] = None
    PAIA_BUILDER_AVAILABLE = True
except ImportError:
    _paia_builder = None
    PAIA_BUILDER_AVAILABLE = False

# Import sanctum-builder for life architecture
try:
    from sanctum_builder import SANCTUMBuilder
    _sanctum_builder: Optional[SANCTUMBuilder] = None
    SANCTUM_BUILDER_AVAILABLE = True
except ImportError:
    _sanctum_builder = None
    SANCTUM_BUILDER_AVAILABLE = False

# Import cave-builder for funnel/business
try:
    from cave_builder import CAVEBuilder
    _cave_builder: Optional[CAVEBuilder] = None
    CAVE_BUILDER_AVAILABLE = True
except ImportError:
    _cave_builder = None
    CAVE_BUILDER_AVAILABLE = False

# Global instance
_game: Optional[SanctuaryRevolution] = None

# Omnisanc state file for sanctuary-revolution game tracking
SANCREV_STATE_FILE = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "omnisanc_core" / ".sancrev_state"


def _get_game() -> SanctuaryRevolution:
    global _game
    if _game is None:
        _game = SanctuaryRevolution()
    return _game


def _get_builder() -> Optional[PAIABuilder]:
    """Get or create PAIABuilder instance for GEAR integration."""
    global _paia_builder
    if not PAIA_BUILDER_AVAILABLE:
        return None
    if _paia_builder is None:
        _paia_builder = PAIABuilder()
    return _paia_builder


def _get_sanctum_builder() -> Optional[SANCTUMBuilder]:
    """Get or create SANCTUMBuilder instance for life architecture."""
    global _sanctum_builder
    if not SANCTUM_BUILDER_AVAILABLE:
        return None
    if _sanctum_builder is None:
        _sanctum_builder = SANCTUMBuilder()
    return _sanctum_builder


def _get_cave_builder() -> Optional[CAVEBuilder]:
    """Get or create CAVEBuilder instance for funnel/business."""
    global _cave_builder
    if not CAVE_BUILDER_AVAILABLE:
        return None
    if _cave_builder is None:
        _cave_builder = CAVEBuilder()
    return _cave_builder


def _load_sancrev_state() -> dict:
    """Load sanctuary-revolution game state for omnisanc."""
    if SANCREV_STATE_FILE.exists():
        return json.loads(SANCREV_STATE_FILE.read_text())
    return {
        "game_active": False,
        "current_player": None,
        "journeys_created": 0,
        "last_journey": None,
        "mvs_created": 0,
        "vecs_created": 0,
        "updated": None
    }


def _save_sancrev_state(state: dict):
    """Persist sanctuary-revolution game state for omnisanc."""
    SANCREV_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = datetime.now().isoformat()
    SANCREV_STATE_FILE.write_text(json.dumps(state, indent=2))


def _update_sancrev_state(event_type: str, data: dict):
    """Update omnisanc state with sancrev event."""
    state = _load_sancrev_state()
    state["game_active"] = True
    state["current_player"] = _get_game()._get_current_name()

    if event_type == "journey_created":
        state["journeys_created"] = state.get("journeys_created", 0) + 1
        state["last_journey"] = data.get("name")
    elif event_type == "mvs_created":
        state["mvs_created"] = state.get("mvs_created", 0) + 1
    elif event_type == "vec_created":
        state["vecs_created"] = state.get("vecs_created", 0) + 1
    elif event_type == "player_selected":
        state["current_player"] = data.get("player")

    _save_sancrev_state(state)

# === GAME OPERATIONS ===

async def new_game(player_name: str, sanctum_name: Optional[str] = None) -> str:
    """Start a new sanctuary revolution game."""
    return _get_game().new_game(player_name, sanctum_name)

async def select_player(player_name: str) -> str:
    """Select a player/game to continue."""
    result = _get_game().select(player_name)
    # Wire to omnisanc state
    if "[SELECTED]" in result or "[LOADED]" in result:
        _update_sancrev_state("player_selected", {"player": player_name})
    return result

async def game_status() -> str:
    """Get full game status."""
    return _get_game().status()

async def list_players() -> List[Dict[str, Any]]:
    """List all players/games."""
    return _get_game().list_players()

# === SANCTUM OPERATIONS ===

async def activate_sanctum(sanctum_name: str) -> str:
    """Activate a SANCTUM as the container for this game."""
    return _get_game().activate_sanctum(sanctum_name)

async def integrate_paiab(paia_name: str) -> str:
    """Integrate a PAIA into your SANCTUM.

    This wires sancrev to paia-builder: future building work on this PAIA
    will generate ExperienceEvents and track GEAR progression.
    """
    # Wire to paia-builder: select this PAIA for GEAR tracking
    builder = _get_builder()
    builder_msg = ""
    if builder:
        try:
            builder_msg = builder.select(paia_name)
            if "[HIEL]" in builder_msg:
                # PAIA doesn't exist in paia-builder yet - CRYSTAL ERROR
                builder_msg = (
                    f"\n[GEAR] PAIA '{paia_name}' not found in paia-builder."
                    f"\n  To create it: paia-builder new {paia_name} \"description\""
                    f"\n  Or via sancrev: First create a journey, then the PAIA emerges from building."
                    f"\n  PAIAs represent AI work capacity. No PAIA = no GEAR tracking."
                )
            else:
                builder_msg = f" [GEAR] {paia_name} linked for experience tracking."
        except Exception as e:
            builder_msg = f" [GEAR] Integration error: {e}. Check paia-builder is installed."

    result = _get_game().integrate_paiab(paia_name)
    return result + builder_msg

async def update_cave_gravity(gravity: int, cave_name: Optional[str] = None) -> str:
    """Update CAVE gravity (0-100). CAVE emerges from living well."""
    return _get_game().update_cave_gravity(gravity, cave_name)

# === JOURNEY OPERATIONS ===

async def create_journey(
    name: str,
    description: str,
    origin_situation: str,
    revelation: str,
    stages: Optional[List[str]] = None
) -> str:
    """Create a SanctuaryJourney - the revelation of transformation.

    Generates ExperienceEvent in paia-builder (journey → flight component).
    """
    result = _get_game().create_journey(name, description, origin_situation, revelation, stages)

    # Wire to paia-builder: journey = flight (transformation workflow)
    builder = _get_builder()
    gear_msg = ""
    if builder and "[JOURNEY]" in result:
        try:
            builder.add_flight(
                name=f"journey-{name}",
                domain="sanctuary",
                description=f"Journey: {description}. Origin: {origin_situation}. Revelation: {revelation}",
                # steps=List[FlightStepSpec], not int — omit and use add_flight_step later
            )
            gear_msg = f" [GEAR] +XP: flight 'journey-{name}' added."
        except Exception as e:
            gear_msg = (
                f"\n[GEAR] Flight creation failed: {e}"
                f"\n  Journey created in sancrev but NOT tracked in GEAR."
                f"\n  To fix: Ensure a PAIA is selected (integrate_paiab first)."
                f"\n  Flights need a PAIA context to generate ExperienceEvents."
            )

    # Wire to omnisanc state - update game tracking
    if "[JOURNEY]" in result:
        _update_sancrev_state("journey_created", {"name": name})
        _emit_event("journey_created", {"name": name, "description": description}, message=f"Journey created: {name}")
    return result + gear_msg

async def list_journeys() -> str:
    """List all journeys for current player."""
    return _get_game().list_journeys()

async def complete_journey(journey_name: str) -> str:
    """Mark a journey as complete."""
    return _get_game().complete_journey(journey_name)

# === MVS OPERATIONS ===

async def create_mvs(
    name: str,
    journey_name: str,
    description: str,
    rituals: Optional[List[str]] = None,
    boundaries: Optional[List[str]] = None,
    structures: Optional[List[str]] = None
) -> str:
    """Create a Minimum Viable Sanctuary for a journey.

    Generates ExperienceEvent in paia-builder (MVS → plugin component).
    """
    result = _get_game().create_mvs(name, journey_name, description, rituals, boundaries, structures)

    # Wire to paia-builder: MVS = plugin (composition of rituals/boundaries/structures)
    builder = _get_builder()
    gear_msg = ""
    if builder and "[MVS]" in result:
        try:
            full_desc = f"MVS for {journey_name}: {description}. Rituals: {rituals}. Boundaries: {boundaries}. Structures: {structures}"
            builder.add_plugin(name=f"mvs-{name}", description=full_desc)
            gear_msg = f" [GEAR] +XP: plugin 'mvs-{name}' added."
        except Exception as e:
            gear_msg = (
                f"\n[GEAR] Plugin creation failed: {e}"
                f"\n  MVS created but NOT tracked in GEAR."
                f"\n  MVS = Minimum Viable Sanctuary (rituals + boundaries + structures)."
                f"\n  To fix: integrate_paiab first to set PAIA context."
            )

    # Wire to omnisanc state
    if "[MVS]" in result:
        _update_sancrev_state("mvs_created", {"name": name, "journey": journey_name})
        _emit_event("mvs_created", {"name": name, "journey": journey_name}, message=f"MVS created: {name}")
    return result + gear_msg

async def list_mvs() -> str:
    """List all MVS systems for current player."""
    return _get_game().list_mvs()

async def mark_mvs_viable(mvs_name: str) -> str:
    """Mark an MVS as viable (tested and working)."""
    return _get_game().mark_mvs_viable(mvs_name)

# === VEC OPERATIONS ===

async def create_vec(
    name: str,
    journey_name: str,
    mvs_name: str,
    agent_name: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """Create a Victory-Everything Chain = Journey + MVS + Agent.

    Generates ExperienceEvent in paia-builder (VEC → system_prompt component).
    """
    result = _get_game().create_vec(name, journey_name, mvs_name, agent_name, description)

    # Wire to paia-builder: VEC = system_prompt (ties journey+mvs+agent together)
    builder = _get_builder()
    gear_msg = ""
    if builder and "[VEC]" in result:
        try:
            desc = description or f"VEC tying {journey_name} + {mvs_name}"
            builder.add_system_prompt(
                name=f"vec-{name}",
                description=desc,
                prompt_type="main",
                domain="sanctuary"
            )
            gear_msg = f" [GEAR] +XP: system_prompt 'vec-{name}' added."
        except Exception as e:
            gear_msg = (
                f"\n[GEAR] VEC registration failed: {e}"
                f"\n  VEC = Victory-Everything Chain (journey + MVS + agent)."
                f"\n  VEC created but not tracked. To fix: integrate_paiab first."
                f"\n  Complete VECs are the WIN CONDITION of sanctuary-revolution."
            )

    # Wire to omnisanc state
    if "[VEC]" in result:
        _update_sancrev_state("vec_created", {"name": name, "journey": journey_name, "mvs": mvs_name})
        _emit_event("vec_created", {"name": name, "journey": journey_name, "mvs": mvs_name}, message=f"VEC created: {name}")
    return result + gear_msg

async def list_vecs() -> str:
    """List all VECs for current player."""
    return _get_game().list_vecs()

async def deploy_agent(vec_name: str, agent_name: str) -> str:
    """Deploy an agent to a VEC.

    Generates ExperienceEvent in paia-builder (deploy → agent component).
    """
    result = _get_game().deploy_agent(vec_name, agent_name)

    # Wire to paia-builder: deploy = agent component
    builder = _get_builder()
    gear_msg = ""
    if builder and "[DEPLOYED]" in result:
        try:
            builder.add_agent(name=agent_name, description=f"Agent deployed to VEC {vec_name}")
            gear_msg = f" [GEAR] +XP: agent '{agent_name}' added."
        except Exception as e:
            gear_msg = (
                f"\n[GEAR] Agent deploy failed: {e}"
                f"\n  Agent deployed to VEC but not tracked in GEAR."
                f"\n  Deploying an agent completes the VEC chain."
                f"\n  To fix: integrate_paiab first to set PAIA context."
            )

    if "[DEPLOYED]" in result:
        _emit_event("agent_deployed", {"vec": vec_name, "agent": agent_name}, message=f"Agent deployed: {agent_name} → {vec_name}")

    return result + gear_msg

# === TRANSITION OPERATIONS ===

async def complete_minigame() -> str:
    """Mark current mini-game as complete."""
    return _get_game().complete_minigame()

async def transition() -> str:
    """Transition to next mini-game."""
    return _get_game().transition()


# === STACK STATUS (Boot Check) ===

async def stack_status() -> str:
    """Check if all three builders are stacked and available.

    Stack = sanctum + paiab + cave booted together.
    This is the foundation for sanctuary-revolution to work.
    """
    lines = ["[STACK] Builder Status:"]

    def _get_builder_info(builder, name):
        """Get builder info, handling missing which() method."""
        if builder is None:
            return "available"
        if hasattr(builder, 'which'):
            return builder.which()
        if hasattr(builder, '_get_current_name'):
            current = builder._get_current_name()
            return current if current else "no selection"
        return "ready"

    # PAIA Builder
    if PAIA_BUILDER_AVAILABLE:
        pb = _get_builder()
        lines.append(f"  ✓ PAIAB: {_get_builder_info(pb, 'PAIAB')}")
    else:
        lines.append("  ✗ PAIAB: NOT INSTALLED")

    # SANCTUM Builder
    if SANCTUM_BUILDER_AVAILABLE:
        sb = _get_sanctum_builder()
        lines.append(f"  ✓ SANCTUM: {_get_builder_info(sb, 'SANCTUM')}")
    else:
        lines.append("  ✗ SANCTUM: NOT INSTALLED")

    # CAVE Builder
    if CAVE_BUILDER_AVAILABLE:
        cb = _get_cave_builder()
        lines.append(f"  ✓ CAVE: {_get_builder_info(cb, 'CAVE')}")
    else:
        lines.append("  ✗ CAVE: NOT INSTALLED")

    # Overall status
    all_available = PAIA_BUILDER_AVAILABLE and SANCTUM_BUILDER_AVAILABLE and CAVE_BUILDER_AVAILABLE
    if all_available:
        lines.append("\n[STACK] ✓ FULLY STACKED - Ready for sanctuary-revolution")
    else:
        missing = []
        if not PAIA_BUILDER_AVAILABLE:
            missing.append("paia-builder")
        if not SANCTUM_BUILDER_AVAILABLE:
            missing.append("sanctum-builder")
        if not CAVE_BUILDER_AVAILABLE:
            missing.append("cave-builder")
        lines.append(f"\n[STACK] ✗ INCOMPLETE - Missing: {', '.join(missing)}")

    return "\n".join(lines)


# =============================================================================
# PAIAB DOMAIN - Direct paia-builder interface
# =============================================================================

async def paiab_new(name: str, description: str, git_dir: Optional[str] = None) -> str:
    """Create a new PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    result = builder.new(name, description, git_dir)
    _emit_event("paia_created", {"name": name}, message=f"PAIA created: {name}")
    return result

async def paiab_select(name: str) -> str:
    """Select a PAIA to work with."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    return builder.select(name)

async def paiab_which() -> str:
    """Show currently selected PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    return builder.which()

async def paiab_list() -> List[Dict[str, Any]]:
    """List all PAIAs."""
    builder = _get_builder()
    if not builder:
        return []
    return builder.list_paias()

async def paiab_add_skill(name: str, domain: str, category: str, description: str) -> str:
    """Add a skill to current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    builder.add_skill(name, domain, category, description)
    _emit_event("component_added", {"type": "skill", "name": name}, message=f"Skill added: {name}")
    return f"[SKILL] Added: {name}"

async def paiab_add_mcp(name: str, description: str) -> str:
    """Add an MCP to current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    builder.add_mcp(name, description)
    _emit_event("component_added", {"type": "mcp", "name": name}, message=f"MCP added: {name}")
    return f"[MCP] Added: {name}"

async def paiab_add_hook(name: str, hook_type: str, description: str) -> str:
    """Add a hook to current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    builder.add_hook(name, hook_type, description)
    _emit_event("component_added", {"type": "hook", "name": name}, message=f"Hook added: {name}")
    return f"[HOOK] Added: {name}"

async def paiab_add_agent(name: str, description: str) -> str:
    """Add an agent to current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    builder.add_agent(name, description)
    _emit_event("component_added", {"type": "agent", "name": name}, message=f"Agent added: {name}")
    return f"[AGENT] Added: {name}"

async def paiab_add_flight(name: str, domain: str, description: str) -> str:
    """Add a flight config to current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    builder.add_flight(name, domain, description)
    _emit_event("component_added", {"type": "flight", "name": name}, message=f"Flight added: {name}")
    return f"[FLIGHT] Added: {name}"

async def paiab_add_persona(name: str, domain: str, description: str, frame: str) -> str:
    """Add a persona to current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    builder.add_persona(name, domain, description, frame)
    _emit_event("component_added", {"type": "persona", "name": name}, message=f"Persona added: {name}")
    return f"[PERSONA] Added: {name}"

async def paiab_list_components(comp_type: str) -> List[Dict[str, Any]]:
    """List components of a type (skills, mcps, hooks, agents, flights, personas, plugins)."""
    builder = _get_builder()
    if not builder:
        return []
    return builder.list_components(comp_type)

async def paiab_advance_tier(comp_type: str, name: str, fulfillment: str) -> str:
    """Advance a component's tier (proves G/E/A/R)."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    result = builder.advance_tier(comp_type, name, fulfillment)
    _emit_event("tier_advanced", {"type": comp_type, "name": name}, message=f"Tier advanced: {name}")
    return result

async def paiab_gear_status() -> str:
    """Get GEAR status for current PAIA."""
    builder = _get_builder()
    if not builder:
        return "[ERROR] paia-builder not available"
    paia = builder._ensure_current()
    gs = paia.gear_state
    return f"[GEAR] L{gs.level} | G:{gs.gear.score} E:{gs.experience.score} A:{gs.achievements.score} R:{gs.reality.score} | {gs.overall}%"


# =============================================================================
# CAVE Domain Functions
# =============================================================================

async def cave_new(name: str, description: str) -> str:
    """Create a new CAVE business system."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.new(name, description)
    _emit_event("cave_created", {"name": name}, message=f"CAVE created: {name}")
    return result

async def cave_select(name: str) -> str:
    """Select a CAVE to work on."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    return cb.select(name)

async def cave_which() -> str:
    """Show currently selected CAVE."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    return cb.which()

async def cave_list() -> List[Dict[str, Any]]:
    """List all CAVEs."""
    cb = _get_cave_builder()
    if not cb:
        return []
    return cb.list_caves()

async def cave_status() -> str:
    """Get CAVE status."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    return cb.status()

async def cave_set_identity(who_am_i: Optional[str] = None, cta: Optional[str] = None,
                            twitter_bio: Optional[str] = None, linkedin_bio: Optional[str] = None,
                            about_short: Optional[str] = None, brand_name: Optional[str] = None) -> str:
    """Set identity constants for CAVE."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.set_identity(who_am_i=who_am_i, cta=cta, twitter_bio=twitter_bio,
                             linkedin_bio=linkedin_bio, about_short=about_short, brand_name=brand_name)
    _emit_event("identity_set", {"cave": cb.which()}, message="Identity updated")
    return result

async def cave_init_value_ladder(name: str, description: str) -> str:
    """Initialize value ladder for current CAVE."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.init_value_ladder(name, description)
    _emit_event("value_ladder_init", {"name": name}, message=f"Value ladder initialized: {name}")
    return result

async def cave_add_offer(name: str, description: str, stage: str, price: Optional[float] = None) -> str:
    """Add offer to value ladder. Stages: lead_magnet, trip_wire, core_offering, upsell, premium"""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.add_offer(name, description, stage, price)
    _emit_event("offer_added", {"name": name, "stage": stage}, message=f"Offer added: {name}")
    return result

async def cave_list_offers() -> List[Dict[str, Any]]:
    """List offers in value ladder."""
    cb = _get_cave_builder()
    if not cb:
        return []
    return cb.list_offers()

async def cave_add_journey(title: str, domain: str, obstacle: str, solution: str, transformation: str) -> str:
    """Add a journey (obstacle→solution story = ad). Domains: paiab, sanctum, cave"""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.add_journey(title, domain, obstacle, solution, transformation)
    _emit_event("journey_added", {"title": title, "domain": domain}, message=f"Journey added: {title}")
    return result

async def cave_list_journeys(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """List journeys, optionally filtered by domain."""
    cb = _get_cave_builder()
    if not cb:
        return []
    return cb.list_journeys(domain)

async def cave_add_framework(name: str, domain: str, problem_pattern: str,
                             solution_pattern: str, implementation: str) -> str:
    """Add a framework (extracted knowledge). Domains: paiab, sanctum, cave"""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.add_framework(name, domain, problem_pattern, solution_pattern, implementation)
    _emit_event("framework_added", {"name": name, "domain": domain}, message=f"Framework added: {name}")
    return result

async def cave_list_frameworks(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """List frameworks, optionally filtered by domain."""
    cb = _get_cave_builder()
    if not cb:
        return []
    return cb.list_frameworks(domain)

async def cave_update_metrics(mrr: Optional[float] = None, subscribers: Optional[int] = None) -> str:
    """Update CAVE metrics (MRR, subscribers)."""
    cb = _get_cave_builder()
    if not cb:
        return "[ERROR] cave-builder not available"
    result = cb.update_metrics(mrr, subscribers)
    _emit_event("metrics_updated", {"mrr": mrr, "subscribers": subscribers}, message="Metrics updated")
    return result


# =============================================================================
# SANCTUM Domain Functions - Life Architecture
# =============================================================================

async def sanctum_new(name: str, description: str) -> str:
    """Create a new SANCTUM life architecture."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.new(name, description)
    _emit_event("sanctum_created", {"name": name}, message=f"SANCTUM created: {name}")
    return result


async def sanctum_select(name: str) -> str:
    """Select a SANCTUM to work on."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    return sb.select(name)


async def sanctum_which() -> str:
    """Show currently selected SANCTUM."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    return sb.which()


async def sanctum_list() -> List[Dict[str, Any]]:
    """List all SANCTUMs."""
    sb = _get_sanctum_builder()
    if not sb:
        return []
    return sb.list_sanctums()


async def sanctum_status() -> str:
    """Get SANCTUM status with GEAR scores and domain breakdown."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    return sb.status()


async def sanctum_add_ritual(name: str, description: str, domain: str,
                              frequency: str = "daily", duration_minutes: int = 15) -> str:
    """Add a ritual. Domains: health, wealth, relationships, purpose, growth, environment.
    Frequencies: daily, weekly, monthly, quarterly, yearly."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.add_ritual(name, description, domain, frequency, duration_minutes)
    _emit_event("ritual_added", {"name": name, "domain": domain}, message=f"Ritual added: {name}")
    return result


async def sanctum_add_goal(name: str, description: str, domain: str) -> str:
    """Add a goal. Domains: health, wealth, relationships, purpose, growth, environment."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.add_goal(name, description, domain)
    _emit_event("goal_added", {"name": name, "domain": domain}, message=f"Goal added: {name}")
    return result


async def sanctum_add_boundary(name: str, description: str, domain: str, rule: str) -> str:
    """Add a boundary/constraint. Domains: health, wealth, relationships, purpose, growth, environment."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.add_boundary(name, description, domain, rule)
    _emit_event("boundary_added", {"name": name, "domain": domain}, message=f"Boundary added: {name}")
    return result


async def sanctum_update_domain(domain: str, score: int) -> str:
    """Update a domain score (0-100). Domains: health, wealth, relationships, purpose, growth, environment."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.update_domain(domain, score)
    _emit_event("domain_updated", {"domain": domain, "score": score}, message=f"Domain {domain}: {score}%")
    return result


async def sanctum_create_mvs(mvs_name: str) -> str:
    """Link a Minimum Viable Sanctuary to this SANCTUM."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.create_mvs(mvs_name)
    _emit_event("sanctum_mvs_linked", {"mvs": mvs_name}, message=f"MVS linked: {mvs_name}")
    return result


async def sanctum_create_journey(journey_name: str) -> str:
    """Link a SanctuaryJourney to this SANCTUM."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.create_journey(journey_name)
    _emit_event("sanctum_journey_linked", {"journey": journey_name}, message=f"Journey linked: {journey_name}")
    return result


async def sanctum_check_vec() -> str:
    """Check Victory-Everything Chain completion status."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    result = sb.check_vec()
    if "COMPLETE" in result:
        _emit_event("vec_complete", {}, message="VEC Complete!")
    return result


async def sanctum_gear_status() -> str:
    """Get GEAR score breakdown (Growth, Experience, Awareness, Reality)."""
    sb = _get_sanctum_builder()
    if not sb:
        return "[ERROR] sanctum-builder not available"
    return sb.gear_status()


async def sanctum_check_complete() -> bool:
    """Check if SANCTUM is complete (all domains >= 80%)."""
    sb = _get_sanctum_builder()
    if not sb:
        return False
    complete = sb.check_complete()
    if complete:
        _emit_event("sanctum_complete", {}, message="SANCTUM Complete!")
    return complete
