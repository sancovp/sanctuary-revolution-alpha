"""Sanctuary Revolution Core - Game orchestrator across all mini-games."""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import (
    PlayerState, MiniGame, GamePhase, MINIGAME_TRANSITIONS, MINIGAME_NESTING,
    SanctuaryJourney, MVS, VEC, SANCREVTWILITELANGMAP
)

# Optional dependencies - each builder
try:
    from paia_builder import PAIABuilder
    PAIAB_AVAILABLE = True
except ImportError:
    PAIAB_AVAILABLE = False

try:
    from cave_builder import CAVEBuilder
    CAVE_AVAILABLE = True
except ImportError:
    CAVE_AVAILABLE = False

try:
    from sanctum_builder import SANCTUMBuilder
    SANCTUM_AVAILABLE = True
except ImportError:
    SANCTUM_AVAILABLE = False


class SanctuaryRevolution:
    """The full game - orchestrates PAIAB, CAVE, SANCTUM mini-games."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.environ.get(
            "SANCTUARY_STORAGE_DIR",
            os.path.join(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "sanctuary_revolution")
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self.storage_dir / "_config.json"

        # Initialize builders if available
        self.paia_builder = PAIABuilder() if PAIAB_AVAILABLE else None
        self.cave_builder = CAVEBuilder() if CAVE_AVAILABLE else None
        self.sanctum_builder = SANCTUMBuilder() if SANCTUM_AVAILABLE else None

    # Player Management

    def _player_path(self, name: str) -> Path:
        return self.storage_dir / f"{name}.json"

    def _save(self, player: PlayerState) -> None:
        player.updated = datetime.now()
        self._player_path(player.name).write_text(player.model_dump_json(indent=2))

    def _load(self, name: str) -> Optional[PlayerState]:
        path = self._player_path(name)
        if path.exists():
            return PlayerState.model_validate_json(path.read_text())
        return None

    def _get_current_name(self) -> Optional[str]:
        if self._config_path.exists():
            return json.loads(self._config_path.read_text()).get("current")
        return None

    def _set_current_name(self, name: str) -> None:
        self._config_path.write_text(json.dumps({"current": name}))

    def _ensure_current(self) -> PlayerState:
        name = self._get_current_name()
        if not name:
            raise ValueError("No player selected. Use select() first.")
        player = self._load(name)
        if not player:
            raise ValueError(f"Player '{name}' not found.")
        return player

    # Game Operations

    def new_game(self, player_name: str, sanctum_name: Optional[str] = None) -> str:
        """Start a new game - SANCTUM first (it's the container).

        The nested model: SANCTUM contains PAIAB and CAVE.
        CAVE emerges from living SANCTUM well - it's not built.
        """
        if self._player_path(player_name).exists():
            return f"Player '{player_name}' already exists"

        player = PlayerState(name=player_name)
        self._save(player)
        self._set_current_name(player_name)

        lines = [
            f"=== SANCTUARY REVOLUTION ===",
            f"Player: {player_name}",
            f"",
            f"NESTED MODEL (not sequential):",
            f"  SANCTUM = container (your whole life architecture)",
            f"  └── PAIAB = tool (AI that offloads work, frees time)",
            f"  └── CAVE = emerges from living SANCTUM well",
            f"",
            f"Start by creating your SANCTUM:",
            f"  Use sanctum-builder to define your life architecture.",
            f"  Then call activate_sanctum() to make it your container.",
        ]
        return "\n".join(lines)

    def select(self, player_name: str) -> str:
        """Select a player/game to continue."""
        if not self._player_path(player_name).exists():
            return f"Player not found: {player_name}"
        self._set_current_name(player_name)
        player = self._load(player_name)
        return f"Selected: {player_name}\nCurrent mini-game: {player.current_mini_game.value.upper()}"

    def status(self) -> str:
        """Full game status - NESTED model."""
        player = self._ensure_current()

        lines = [
            f"=== SANCTUARY REVOLUTION ===",
            f"Player: {player.name}",
            f"Phase: {player.phase.value.upper()}",
            f"",
            f"=== NESTED STRUCTURE ===",
            f"SANCTUM (container): {player.sanctum_name or '[NOT CREATED]'}",
            f"  Active: {'✓' if player.sanctum_active else '✗'}",
        ]

        if player.has_sanctum:
            lines.extend([
                f"  └── PAIAB (tool): {player.paia_name or '[NOT INTEGRATED]'}",
                f"      Integrated: {'✓' if player.paiab_integrated else '✗'}",
                f"  └── CAVE (emergence): {player.cave_name or '[NOT YET EMERGING]'}",
                f"      Gravity: {player.cave_gravity}%",
            ])

        lines.extend([
            f"",
            f"=== COMPOUND LOOP ===",
            f"{player.compound_loop_status}",
            f"",
            f"Revolutionary: {'YES - SELF-SUSTAINING' if player.is_revolutionary else 'Not yet'}",
            f"VECs Complete: {player.vec_count}",
            f"",
            f"Builders Available:",
            f"  sanctum-builder: {'YES' if SANCTUM_AVAILABLE else 'NO'}",
            f"  paia-builder:    {'YES' if PAIAB_AVAILABLE else 'NO'}",
            f"  cave-builder:    {'YES' if CAVE_AVAILABLE else 'NO'}",
        ])

        return "\n".join(lines)

    # === NESTED OPERATIONS ===

    def activate_sanctum(self, sanctum_name: str) -> str:
        """Activate a SANCTUM as the container for this game."""
        player = self._ensure_current()
        player.sanctum_name = sanctum_name
        player.sanctum_active = True
        player.phase = GamePhase.BUILDING
        self._save(player)
        return f"[SANCTUM] {sanctum_name} activated as your life container.\nNext: Integrate PAIAB to free up time."

    def integrate_paiab(self, paia_name: str) -> str:
        """Integrate a PAIA into your SANCTUM."""
        player = self._ensure_current()
        if not player.has_sanctum:
            return "[HIEL] Must activate SANCTUM first. It's the container."
        player.paia_name = paia_name
        player.paiab_integrated = True
        self._save(player)
        return f"[PAIAB] {paia_name} integrated into SANCTUM.\nAI now freeing time. Live well to trigger CAVE emergence."

    def update_cave_gravity(self, gravity: int, cave_name: Optional[str] = None) -> str:
        """Update CAVE gravity (0-100). CAVE emerges from living well."""
        player = self._ensure_current()
        if not player.has_sanctum:
            return "[HIEL] Must activate SANCTUM first."

        player.cave_gravity = min(100, max(0, gravity))
        if cave_name:
            player.cave_name = cave_name
        if gravity > 0:
            player.cave_emerging = True
            player.phase = GamePhase.MASTERY

        self._save(player)

        if player.is_revolutionary:
            return f"[REVOLUTION] CAVE gravity at {gravity}%. Compound effect compounding!"
        elif gravity >= 50:
            return f"[CAVE] Gravity well at {gravity}%. Approaching revolution threshold (50%)."
        else:
            return f"[CAVE] Gravity at {gravity}%. Keep living SANCTUM well."

    def complete_minigame(self) -> str:
        """Mark current mini-game as complete and prepare for transition."""
        player = self._ensure_current()

        # Mark current as complete
        if player.current_mini_game == MiniGame.PAIAB:
            player.paiab_complete = True
        elif player.current_mini_game == MiniGame.CAVE:
            player.cave_complete = True
        elif player.current_mini_game == MiniGame.SANCTUM:
            player.sanctum_complete = True

        player.phase = GamePhase.TRANSITION
        self._save(player)

        return f"{player.current_mini_game.value.upper()} marked complete!\nUse transition() to move to next mini-game."

    def transition(self) -> str:
        """Transition to next mini-game."""
        player = self._ensure_current()

        if player.phase != GamePhase.TRANSITION:
            return f"Not ready to transition. Complete current mini-game first."

        valid_next = MINIGAME_TRANSITIONS.get(player.current_mini_game, [])
        if not valid_next:
            if player.is_revolutionary:
                player.phase = GamePhase.REVOLUTION
                self._save(player)
                return "REVOLUTION ACHIEVED! All three mini-games complete. Full sovereignty unlocked."
            return "Already at final mini-game (SANCTUM). Complete it to achieve REVOLUTION."

        old = player.current_mini_game
        player.current_mini_game = valid_next[0]
        player.phase = GamePhase.BUILDING
        self._save(player)

        return f"Transitioned: {old.value.upper()} -> {player.current_mini_game.value.upper()}"

    def list_players(self) -> List[Dict[str, Any]]:
        """List all players/games."""
        players = []
        for path in self.storage_dir.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                player = PlayerState.model_validate_json(path.read_text())
                players.append({
                    "name": player.name,
                    "mini_game": player.current_mini_game.value,
                    "phase": player.phase.value,
                    "revolutionary": player.is_revolutionary
                })
            except Exception:
                continue
        return players

    # === VEC/MVS/SJ CREATION (The Mnemonics) ===

    def create_journey(
        self,
        name: str,
        description: str,
        origin_situation: str,
        revelation: str,
        stages: Optional[List[str]] = None
    ) -> str:
        """[JOURNEY] Create a SanctuaryJourney - the revelation of transformation."""
        player = self._ensure_current()
        if not player.has_sanctum:
            return "[HIEL] Must activate SANCTUM first."

        # Create langmap name from journey
        langmap_name = f"{name}_langmap"

        journey = SanctuaryJourney(
            name=name,
            description=description,
            langmap_name=langmap_name,
            origin_situation=origin_situation,
            revelation=revelation,
            stages=stages or [],
        )
        player.journeys.append(journey)
        self._save(player)

        return f"[JOURNEY] Created: {name}\nOrigin: {origin_situation}\nRevelation: {revelation}\nStages: {len(stages or [])}"

    def create_mvs(
        self,
        name: str,
        journey_name: str,
        description: str,
        rituals: Optional[List[str]] = None,
        boundaries: Optional[List[str]] = None,
        structures: Optional[List[str]] = None
    ) -> str:
        """[MVS] Create a Minimum Viable Sanctuary for a journey."""
        player = self._ensure_current()
        if not player.has_sanctum:
            return "[HIEL] Must activate SANCTUM first."

        # Verify journey exists
        journey_exists = any(j.name == journey_name for j in player.journeys)
        if not journey_exists:
            return f"[HIEL] Journey '{journey_name}' not found. Create it first."

        mvs = MVS(
            name=name,
            description=description,
            journey_name=journey_name,
            rituals=rituals or [],
            boundaries=boundaries or [],
            structures=structures or [],
        )
        player.mvs_systems.append(mvs)
        self._save(player)

        return f"[MVS] Created: {name}\nFor journey: {journey_name}\nRituals: {len(rituals or [])}, Boundaries: {len(boundaries or [])}, Structures: {len(structures or [])}"

    def create_vec(
        self,
        name: str,
        journey_name: str,
        mvs_name: str,
        agent_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """[VEC] Create a Victory-Everything Chain = Journey + MVS + Agent."""
        player = self._ensure_current()
        if not player.has_sanctum:
            return "[HIEL] Must activate SANCTUM first."

        # Verify journey exists
        journey = next((j for j in player.journeys if j.name == journey_name), None)
        if not journey:
            return f"[HIEL] Journey '{journey_name}' not found."

        # Verify MVS exists
        mvs = next((m for m in player.mvs_systems if m.name == mvs_name), None)
        if not mvs:
            return f"[HIEL] MVS '{mvs_name}' not found."

        vec = VEC(
            name=name,
            description=description or f"VEC for {journey_name}",
            journey_name=journey_name,
            mvs_name=mvs_name,
            agent_name=agent_name,
            journey_complete=journey.completed,
            mvs_viable=mvs.viable,
            agent_deployed=agent_name is not None,
        )
        player.vecs.append(vec)
        self._save(player)

        status = "COMPLETE" if vec.is_complete else "IN PROGRESS"
        return f"[VEC] Created: {name} ({status})\nJourney: {journey_name} ({'✓' if journey.completed else '○'})\nMVS: {mvs_name} ({'✓' if mvs.viable else '○'})\nAgent: {agent_name or 'None'} ({'✓' if agent_name else '○'})"

    def list_journeys(self) -> str:
        """List all journeys for current player."""
        player = self._ensure_current()
        if not player.journeys:
            return "[JOURNEY] No journeys yet. Use create_journey() to start one."
        lines = ["[JOURNEYS]"]
        for j in player.journeys:
            status = "✓" if j.completed else f"stage {j.current_stage}/{len(j.stages)}"
            lines.append(f"  - {j.name}: {status}")
        return "\n".join(lines)

    def list_mvs(self) -> str:
        """List all MVS systems for current player."""
        player = self._ensure_current()
        if not player.mvs_systems:
            return "[MVS] No MVS systems yet. Use create_mvs() after creating a journey."
        lines = ["[MVS SYSTEMS]"]
        for m in player.mvs_systems:
            status = "VIABLE ✓" if m.viable else "testing..."
            lines.append(f"  - {m.name} (for {m.journey_name}): {status}")
        return "\n".join(lines)

    def list_vecs(self) -> str:
        """List all VECs for current player."""
        player = self._ensure_current()
        if not player.vecs:
            return "[VEC] No VECs yet. Use create_vec() after journey + MVS ready."
        lines = ["[VICTORY-EVERYTHING CHAINS]"]
        for v in player.vecs:
            status = "COMPLETE ✓" if v.is_complete else "building..."
            lines.append(f"  - {v.name}: {status}")
        return "\n".join(lines)

    def complete_journey(self, journey_name: str) -> str:
        """Mark a journey as complete."""
        player = self._ensure_current()
        journey = next((j for j in player.journeys if j.name == journey_name), None)
        if not journey:
            return f"[HIEL] Journey '{journey_name}' not found."
        journey.completed = True
        # Update any VECs that reference this journey
        for vec in player.vecs:
            if vec.journey_name == journey_name:
                vec.journey_complete = True
        self._save(player)
        return f"[JOURNEY] {journey_name} marked COMPLETE"

    def mark_mvs_viable(self, mvs_name: str) -> str:
        """Mark an MVS as viable (tested and working)."""
        player = self._ensure_current()
        mvs = next((m for m in player.mvs_systems if m.name == mvs_name), None)
        if not mvs:
            return f"[HIEL] MVS '{mvs_name}' not found."
        mvs.viable = True
        mvs.tested = True
        # Update any VECs that reference this MVS
        for vec in player.vecs:
            if vec.mvs_name == mvs_name:
                vec.mvs_viable = True
        self._save(player)
        return f"[MVS] {mvs_name} marked VIABLE"

    def deploy_agent(self, vec_name: str, agent_name: str) -> str:
        """Deploy an agent to a VEC."""
        player = self._ensure_current()
        vec = next((v for v in player.vecs if v.name == vec_name), None)
        if not vec:
            return f"[HIEL] VEC '{vec_name}' not found."
        vec.agent_name = agent_name
        vec.agent_deployed = True
        self._save(player)
        if vec.is_complete:
            return f"[VEC] {vec_name} now COMPLETE! Agent {agent_name} deployed."
        return f"[VEC] Agent {agent_name} deployed to {vec_name}."
