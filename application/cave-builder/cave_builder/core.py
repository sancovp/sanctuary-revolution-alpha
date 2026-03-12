"""CAVE Builder Core - Business system construction."""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import (
    CAVE, ValueLadder, ValueLadderStage, Offer, AIDAContent,
    CustomerPhase, RetargetingStrategy, Domain, DiscordStructure,
    Journey, Framework, IdentityConstants, BlogTemplate,
    LinkedInTemplate, TweetTemplate, YouTubeVideo, YouTubeScript
)


class CAVEBuilder:
    """Builder for CAVE business systems."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.environ.get(
            "CAVE_STORAGE_DIR",
            os.path.join(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "caves")
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self.storage_dir / "_config.json"

    def _cave_path(self, name: str) -> Path:
        return self.storage_dir / f"{name}.json"

    def _save(self, cave: CAVE) -> None:
        cave.updated = datetime.now()
        self._cave_path(cave.name).write_text(cave.model_dump_json(indent=2))

    def _load(self, name: str) -> Optional[CAVE]:
        path = self._cave_path(name)
        if path.exists():
            return CAVE.model_validate_json(path.read_text())
        return None

    def _get_current_name(self) -> Optional[str]:
        if self._config_path.exists():
            return json.loads(self._config_path.read_text()).get("current")
        return None

    def _set_current_name(self, name: str) -> None:
        self._config_path.write_text(json.dumps({"current": name}))

    def _ensure_current(self) -> CAVE:
        name = self._get_current_name()
        if not name:
            raise ValueError("No CAVE selected. Use select() first.")
        cave = self._load(name)
        if not cave:
            raise ValueError(f"CAVE '{name}' not found.")
        return cave

    # =========================================================================
    # CAVE Management
    # =========================================================================

    def new(self, name: str, description: str) -> str:
        """Create a new CAVE with default Discord structure."""
        if self._cave_path(name).exists():
            return f"CAVE '{name}' already exists"
        cave = CAVE(
            name=name,
            description=description,
            discord=DiscordStructure.default_structure(name)
        )
        self._save(cave)
        self._set_current_name(name)
        return f"Created CAVE: {name} (with default Discord structure)"

    def select(self, name: str) -> str:
        """Select a CAVE to work on."""
        if not self._cave_path(name).exists():
            return f"CAVE not found: {name}"
        self._set_current_name(name)
        return f"Selected: {name}"

    def which(self) -> str:
        """Show currently selected CAVE."""
        name = self._get_current_name()
        return name if name else "No CAVE selected"

    def list_caves(self) -> List[Dict[str, Any]]:
        """List all CAVEs."""
        caves = []
        for path in self.storage_dir.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                cave = CAVE.model_validate_json(path.read_text())
                caves.append({
                    "name": cave.name,
                    "mrr": cave.mrr,
                    "journeys": len(cave.journeys),
                    "frameworks": len(cave.frameworks),
                    "is_complete": cave.is_complete
                })
            except Exception:
                continue
        return caves

    def status(self) -> str:
        """CAVE status."""
        cave = self._ensure_current()
        lines = [
            f"CAVE: {cave.name}",
            f"MRR: ${cave.mrr}",
            f"Subscribers: {cave.subscribers}",
            f"Journeys: {len(cave.journeys)}",
            f"Frameworks: {len(cave.frameworks)}",
            f"Identity Set: {bool(cave.identity.who_am_i)}",
            f"Value Ladder: {cave.value_ladder.stages_complete if cave.value_ladder else 0}/5 stages",
            f"Complete: {cave.is_complete}"
        ]
        return "\n".join(lines)

    # =========================================================================
    # Identity
    # =========================================================================

    def set_identity(self, who_am_i: str = None, cta: str = None,
                     twitter_bio: str = None, linkedin_bio: str = None,
                     about_short: str = None, about_long: str = None,
                     brand_name: str = None, tagline: str = None) -> str:
        """Set identity constants."""
        cave = self._ensure_current()
        if who_am_i:
            cave.identity.who_am_i = who_am_i
        if cta:
            cave.identity.cta = cta
        if twitter_bio:
            cave.identity.twitter_bio = twitter_bio
        if linkedin_bio:
            cave.identity.linkedin_bio = linkedin_bio
        if about_short:
            cave.identity.about_short = about_short
        if about_long:
            cave.identity.about_long = about_long
        if brand_name:
            cave.identity.brand_name = brand_name
        if tagline:
            cave.identity.tagline = tagline
        self._save(cave)
        return "Identity updated"

    def get_identity(self) -> Dict[str, str]:
        """Get identity constants."""
        cave = self._ensure_current()
        return cave.identity.model_dump()

    # =========================================================================
    # Value Ladder
    # =========================================================================

    def init_value_ladder(self, name: str, description: str) -> str:
        """Initialize a value ladder."""
        cave = self._ensure_current()
        cave.value_ladder = ValueLadder(name=name, description=description)
        self._save(cave)
        return f"Value ladder initialized: {name}"

    def add_offer(self, name: str, description: str, stage: str,
                  price: Optional[float] = None) -> str:
        """Add an offer to the value ladder."""
        cave = self._ensure_current()
        if not cave.value_ladder:
            return "Initialize value ladder first"

        try:
            stage_enum = ValueLadderStage(stage)
        except ValueError:
            stages = [s.value for s in ValueLadderStage]
            return f"Invalid stage. Use: {stages}"

        # Determine transformation based on stage
        transformations = {
            ValueLadderStage.LEAD_MAGNET: (CustomerPhase.VISITOR, CustomerPhase.ENGAGED_LEAD),
            ValueLadderStage.TRIP_WIRE: (CustomerPhase.ENGAGED_LEAD, CustomerPhase.FIRST_TIME_CUSTOMER),
            ValueLadderStage.CORE_OFFERING: (CustomerPhase.FIRST_TIME_CUSTOMER, CustomerPhase.CORE_CUSTOMER),
            ValueLadderStage.UPSELL: (CustomerPhase.CORE_CUSTOMER, CustomerPhase.REPEAT_CUSTOMER),
            ValueLadderStage.PREMIUM: (CustomerPhase.REPEAT_CUSTOMER, CustomerPhase.BRAND_ADVOCATE),
        }
        from_phase, to_phase = transformations[stage_enum]

        offer = Offer(
            name=name,
            description=description,
            stage=stage_enum,
            price=price,
            from_phase=from_phase,
            to_phase=to_phase
        )
        cave.value_ladder.offers[stage_enum] = offer
        self._save(cave)
        return f"Added offer: {name} at {stage}"

    def list_offers(self) -> List[Dict[str, Any]]:
        """List offers in value ladder."""
        cave = self._ensure_current()
        if not cave.value_ladder:
            return []
        return [
            {"stage": k.value, "name": v.name, "price": v.price}
            for k, v in cave.value_ladder.offers.items()
        ]

    # =========================================================================
    # Journeys
    # =========================================================================

    def add_journey(self, title: str, domain: str, obstacle: str,
                    solution: str, transformation: str) -> str:
        """Add a journey (obstacle → solution story)."""
        cave = self._ensure_current()
        try:
            domain_enum = Domain(domain)
        except ValueError:
            domains = [d.value for d in Domain]
            return f"Invalid domain. Use: {domains}"

        journey = Journey(
            title=title,
            domain=domain_enum,
            obstacle=obstacle,
            solution=solution,
            transformation=transformation
        )
        cave.journeys.append(journey)
        self._save(cave)
        return f"Added journey: {title}"

    def list_journeys(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List journeys, optionally filtered by domain."""
        cave = self._ensure_current()
        journeys = cave.journeys
        if domain:
            journeys = [j for j in journeys if j.domain.value == domain]
        return [
            {"title": j.title, "domain": j.domain.value, "published": j.published}
            for j in journeys
        ]

    # =========================================================================
    # Frameworks
    # =========================================================================

    def add_framework(self, name: str, domain: str, problem_pattern: str,
                      solution_pattern: str, implementation: str) -> str:
        """Add a framework (extracted knowledge)."""
        cave = self._ensure_current()
        try:
            domain_enum = Domain(domain)
        except ValueError:
            domains = [d.value for d in Domain]
            return f"Invalid domain. Use: {domains}"

        framework = Framework(
            name=name,
            domain=domain_enum,
            problem_pattern=problem_pattern,
            solution_pattern=solution_pattern,
            implementation=implementation
        )
        cave.frameworks.append(framework)
        self._save(cave)
        return f"Added framework: {name}"

    def list_frameworks(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List frameworks, optionally filtered by domain."""
        cave = self._ensure_current()
        frameworks = cave.frameworks
        if domain:
            frameworks = [f for f in frameworks if f.domain.value == domain]
        return [
            {"name": f.name, "domain": f.domain.value}
            for f in frameworks
        ]

    # =========================================================================
    # Metrics
    # =========================================================================

    def update_metrics(self, mrr: Optional[float] = None,
                       subscribers: Optional[int] = None) -> str:
        """Update CAVE metrics."""
        cave = self._ensure_current()
        if mrr is not None:
            cave.mrr = mrr
        if subscribers is not None:
            cave.subscribers = subscribers
        self._save(cave)
        return f"Metrics updated: MRR=${cave.mrr}, Subscribers={cave.subscribers}"

    def check_complete(self) -> bool:
        """Check if CAVE is complete."""
        cave = self._ensure_current()
        return cave.is_complete
