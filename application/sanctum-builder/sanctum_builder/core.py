"""SANCTUM Builder Core - Life architecture mini-game.

[SANCTUM] wraps life infrastructure with Sanctuary vocabulary.
Part of sanctuary-revolution game orchestrator.

Integrates:
- sanctuary-system myth layer (MVS, VEC, SanctuaryJourney)
- life_architecture_app infrastructure (LifePlan, DailyLog, schedules)
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date as dt_date

from .models import (
    SANCTUM, LifeDomain, RitualSpec, GoalSpec, BoundarySpec,
    RitualFrequency, SanctuaryDegree, GEARScore, ExperienceEntry,
    # Re-exported from life_app for convenience
    LifePlan, DailyLog, Experiment, DaySchedule, ScheduleItem,
)


class SANCTUMBuilder:
    """Builder for SANCTUM life architecture. STUB - to be implemented."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.environ.get(
            "SANCTUM_STORAGE_DIR",
            os.path.join(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"), "sanctums")
        ))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self.storage_dir / "_config.json"

    def _sanctum_path(self, name: str) -> Path:
        return self.storage_dir / f"{name}.json"

    def _save(self, sanctum: SANCTUM) -> None:
        sanctum.updated = datetime.now()
        self._sanctum_path(sanctum.name).write_text(sanctum.model_dump_json(indent=2))

    def _load(self, name: str) -> Optional[SANCTUM]:
        path = self._sanctum_path(name)
        if path.exists():
            return SANCTUM.model_validate_json(path.read_text())
        return None

    def _get_current_name(self) -> Optional[str]:
        if self._config_path.exists():
            return json.loads(self._config_path.read_text()).get("current")
        return None

    def _set_current_name(self, name: str) -> None:
        self._config_path.write_text(json.dumps({"current": name}))

    def _ensure_current(self) -> SANCTUM:
        name = self._get_current_name()
        if not name:
            raise ValueError("No SANCTUM selected. Use select() first.")
        sanctum = self._load(name)
        if not sanctum:
            raise ValueError(f"SANCTUM '{name}' not found.")
        return sanctum

    # STUB methods - to be implemented

    def new(self, name: str, description: str) -> str:
        """Create a new SANCTUM."""
        if self._sanctum_path(name).exists():
            return f"SANCTUM '{name}' already exists"
        sanctum = SANCTUM(name=name, description=description)
        self._save(sanctum)
        self._set_current_name(name)
        return f"Created SANCTUM: {name}"

    def select(self, name: str) -> str:
        """Select a SANCTUM to work on."""
        if not self._sanctum_path(name).exists():
            return f"SANCTUM not found: {name}"
        self._set_current_name(name)
        return f"Selected: {name}"

    def status(self) -> str:
        """[SANCTUM] Status display with SOSEEH thematization."""
        sanctum = self._ensure_current()

        # Determine pilot state
        degree = sanctum.sanctuary_degree
        if degree == SanctuaryDegree.OEVESE:
            pilot_status = "[PILOT] OEVESE - Victory-Everything manifest"
        elif degree == SanctuaryDegree.OVA:
            pilot_status = "[PILOT] OVA - Victory-Ability active"
        else:
            pilot_status = "[PILOT] OVP - Victory-Promise declared"

        lines = [
            f"=== [SANCTUM] {sanctum.name} ===",
            f"",
            pilot_status,
            f"",
            f"[MVS] Minimum Viable Sanctuary: {sanctum.mvs_name or 'Not configured'}",
            f"  Rituals: {len(sanctum.rituals)}",
            f"  Boundaries: {len(sanctum.boundaries)}",
            f"",
            f"[JOURNEY] SanctuaryJourney: {sanctum.journey_name or 'Not started'}",
            f"  Goals: {len(sanctum.goals)}",
            f"",
            f"[VEC] Victory-Everything Chain: {sanctum.vec_name or 'Not complete'}",
            f"  Complete: {sanctum.is_complete}",
            f"",
            f"Domain Scores (Overall: {sanctum.overall_score}%):"
        ]
        for domain, score in sanctum.domain_scores.items():
            bar = "█" * (score // 10) + "░" * (10 - score // 10)
            lines.append(f"  {domain}: [{bar}] {score}%")
        return "\n".join(lines)

    def add_ritual(self, name: str, description: str, domain: str,
                   frequency: str = "daily", duration_minutes: int = 15) -> str:
        """Add a ritual. STUB."""
        sanctum = self._ensure_current()
        ritual = RitualSpec(name=name, description=description,
                           domain=LifeDomain(domain),
                           frequency=RitualFrequency(frequency),
                           duration_minutes=duration_minutes)
        sanctum.rituals.append(ritual)
        self._save(sanctum)
        return f"Added ritual: {name}"

    def add_goal(self, name: str, description: str, domain: str) -> str:
        """Add a goal. STUB."""
        sanctum = self._ensure_current()
        goal = GoalSpec(name=name, description=description, domain=LifeDomain(domain))
        sanctum.goals.append(goal)
        self._save(sanctum)
        return f"Added goal: {name}"

    def add_boundary(self, name: str, description: str, domain: str, rule: str) -> str:
        """Add a boundary. STUB."""
        sanctum = self._ensure_current()
        boundary = BoundarySpec(name=name, description=description,
                               domain=LifeDomain(domain), rule=rule)
        sanctum.boundaries.append(boundary)
        self._save(sanctum)
        return f"Added boundary: {name}"

    def update_domain(self, domain: str, score: int) -> str:
        """Update a domain score."""
        sanctum = self._ensure_current()
        sanctum.domain_scores[domain] = min(100, max(0, score))
        self._save(sanctum)
        return f"{domain}: {sanctum.domain_scores[domain]}%"

    def list_sanctums(self) -> List[Dict[str, Any]]:
        """List all SANCTUMs."""
        sanctums = []
        for path in self.storage_dir.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                sanctum = SANCTUM.model_validate_json(path.read_text())
                sanctums.append({"name": sanctum.name, "overall": sanctum.overall_score})
            except Exception:
                continue
        return sanctums

    def check_complete(self) -> bool:
        """Check if SANCTUM is complete."""
        sanctum = self._ensure_current()
        return sanctum.is_complete

    # Sanctuary-system integration methods

    def create_mvs(self, mvs_name: str) -> str:
        """[MVS] Link a Minimum Viable Sanctuary to this SANCTUM."""
        sanctum = self._ensure_current()
        sanctum.mvs_name = mvs_name
        self._save(sanctum)
        return f"[MVS] Linked: {mvs_name}"

    def create_journey(self, journey_name: str) -> str:
        """[JOURNEY] Link a SanctuaryJourney to this SANCTUM."""
        sanctum = self._ensure_current()
        sanctum.journey_name = journey_name
        self._save(sanctum)
        return f"[JOURNEY] Started: {journey_name}"

    def check_vec(self) -> str:
        """[VEC] Check Victory-Everything Chain completion status."""
        sanctum = self._ensure_current()

        has_mvs = sanctum.mvs_name is not None
        has_journey = sanctum.journey_name is not None
        has_vec = sanctum.vec_name is not None
        domains_complete = sanctum.is_complete

        lines = [
            f"[VEC] Victory-Everything Chain Status:",
            f"  MVS linked: {'✓' if has_mvs else '✗'} ({sanctum.mvs_name or 'None'})",
            f"  Journey linked: {'✓' if has_journey else '✗'} ({sanctum.journey_name or 'None'})",
            f"  Domains complete: {'✓' if domains_complete else '✗'} ({sanctum.overall_score}%)",
            f"  VEC complete: {'✓' if has_vec else '✗'}",
        ]

        # Auto-complete VEC if all conditions met
        if has_mvs and has_journey and domains_complete and not has_vec:
            sanctum.vec_name = f"vec-{sanctum.name}"
            sanctum.sanctuary_degree = SanctuaryDegree.OVA
            self._save(sanctum)
            lines.append(f"")
            lines.append(f"[VEC] COMPLETE! {sanctum.vec_name} achieved.")
            lines.append(f"[PILOT] Advanced to OVA - Victory-Ability!")

        return "\n".join(lines)

    def which(self) -> str:
        """Which SANCTUM is currently selected."""
        name = self._get_current_name()
        if not name:
            return "[HIEL] No SANCTUM selected"
        return f"[SANCTUM] Current: {name}"

    # life_architecture_app integration methods

    def link_life_plan(self, user_id: str) -> str:
        """[LIFE] Link a LifePlan user to this SANCTUM.

        The LifePlan contains goals that map to MVS rituals/boundaries.
        """
        sanctum = self._ensure_current()
        sanctum.life_plan_user_id = user_id
        self._save(sanctum)
        return f"[LIFE] Linked LifePlan user: {user_id}"

    def import_from_life_plan(self, life_plan: LifePlan) -> str:
        """[LIFE] Import LifePlan goals as SANCTUM rituals.

        Maps LifePlan metrics to sanctuary vocabulary:
        - sleep_hours_goal → Health ritual
        - hydration_goal_ml → Health ritual
        - exercise_minutes_goal → Health ritual
        - steps_goal → Health ritual
        - work_sessions_goal → Purpose ritual
        - work_minutes_goal → Purpose ritual
        """
        sanctum = self._ensure_current()
        imported = []

        # Health domain rituals
        if life_plan.sleep_hours_goal > 0:
            sanctum.rituals.append(RitualSpec(
                name="Sleep Sanctuary",
                description=f"Get {life_plan.sleep_hours_goal} hours of sleep",
                domain=LifeDomain.HEALTH,
                frequency=RitualFrequency.DAILY,
                duration_minutes=int(life_plan.sleep_hours_goal * 60),
            ))
            imported.append("sleep")

        if life_plan.hydration_goal_ml > 0:
            sanctum.rituals.append(RitualSpec(
                name="Hydration Ritual",
                description=f"Drink {life_plan.hydration_goal_ml}ml water",
                domain=LifeDomain.HEALTH,
                frequency=RitualFrequency.DAILY,
                duration_minutes=5,
            ))
            imported.append("hydration")

        if life_plan.exercise_minutes_goal > 0:
            sanctum.rituals.append(RitualSpec(
                name="Movement Practice",
                description=f"Exercise for {life_plan.exercise_minutes_goal} minutes",
                domain=LifeDomain.HEALTH,
                frequency=RitualFrequency.DAILY,
                duration_minutes=life_plan.exercise_minutes_goal,
            ))
            imported.append("exercise")

        # Purpose domain rituals
        if life_plan.work_sessions_goal > 0:
            sanctum.rituals.append(RitualSpec(
                name="Deep Work Sessions",
                description=f"Complete {life_plan.work_sessions_goal} deep work sessions",
                domain=LifeDomain.PURPOSE,
                frequency=RitualFrequency.DAILY,
                duration_minutes=life_plan.work_minutes_goal or 90,
            ))
            imported.append("work")

        sanctum.life_plan_user_id = life_plan.user_id
        self._save(sanctum)
        return f"[LIFE] Imported {len(imported)} rituals from LifePlan: {', '.join(imported)}"

    def log_experience(self, daily_log: DailyLog, life_plan: Optional[LifePlan] = None) -> str:
        """[EXPERIENCE] Log daily experience from DailyLog and derive GEAR score.

        Compares DailyLog actuals against LifePlan goals to calculate:
        - E (Experience): % of goals met today
        - A (Awareness): Average of mood/energy/focus scores
        """
        sanctum = self._ensure_current()

        # Calculate Experience score (% of goals met)
        experience_score = 0
        if life_plan:
            metrics_met = 0
            metrics_total = 0

            if life_plan.sleep_hours_goal > 0 and daily_log.sleep_hours is not None:
                metrics_total += 1
                if daily_log.sleep_hours >= life_plan.sleep_hours_goal:
                    metrics_met += 1

            if life_plan.hydration_goal_ml > 0 and daily_log.hydration_ml is not None:
                metrics_total += 1
                if daily_log.hydration_ml >= life_plan.hydration_goal_ml:
                    metrics_met += 1

            if life_plan.exercise_minutes_goal > 0 and daily_log.exercise_minutes is not None:
                metrics_total += 1
                if daily_log.exercise_minutes >= life_plan.exercise_minutes_goal:
                    metrics_met += 1

            if life_plan.work_sessions_goal > 0 and daily_log.work_sessions is not None:
                metrics_total += 1
                if daily_log.work_sessions >= life_plan.work_sessions_goal:
                    metrics_met += 1

            if metrics_total > 0:
                experience_score = int((metrics_met / metrics_total) * 100)

        # Calculate Awareness score (average of subjective ratings)
        awareness_scores = []
        if daily_log.mood_score is not None:
            awareness_scores.append(daily_log.mood_score * 10)  # Scale 1-10 to 0-100
        if daily_log.energy_score is not None:
            awareness_scores.append(daily_log.energy_score * 10)
        if daily_log.focus_score is not None:
            awareness_scores.append(daily_log.focus_score * 10)

        awareness_score = int(sum(awareness_scores) / len(awareness_scores)) if awareness_scores else 0

        # Create GEAR score for this day
        gear = GEARScore(
            growth=sanctum.current_gear.growth,  # Preserve existing growth
            experience=experience_score,
            awareness=awareness_score,
            reality=sanctum.current_gear.reality,  # Preserve existing reality
        )

        # Create experience entry
        entry = ExperienceEntry(
            date=daily_log.date,
            daily_log_ref=f"{daily_log.user_id}:{daily_log.date.isoformat()}",
            gear=gear,
            notes=daily_log.notes,
        )

        sanctum.experience_log.append(entry)
        sanctum.current_gear = gear
        self._save(sanctum)

        return f"[EXPERIENCE] Logged {daily_log.date}: GEAR={gear.total}% (E={experience_score}%, A={awareness_score}%)"

    def gear_status(self) -> str:
        """[GEAR] Display current GEAR score breakdown."""
        sanctum = self._ensure_current()
        gear = sanctum.current_gear

        def bar(score: int) -> str:
            return "█" * (score // 10) + "░" * (10 - score // 10)

        lines = [
            f"[GEAR] Growth-Experience-Awareness-Reality Score",
            f"",
            f"  G (Growth):     [{bar(gear.growth)}] {gear.growth}%",
            f"  E (Experience): [{bar(gear.experience)}] {gear.experience}%",
            f"  A (Awareness):  [{bar(gear.awareness)}] {gear.awareness}%",
            f"  R (Reality):    [{bar(gear.reality)}] {gear.reality}%",
            f"",
            f"  Total GEAR: {gear.total}%",
            f"",
            f"  Experience Log: {len(sanctum.experience_log)} entries",
        ]
        return "\n".join(lines)

    def log_reality(self, day_schedule: DaySchedule, completed_items: List[str]) -> str:
        """[REALITY] Log schedule adherence for R score.

        Compares scheduled items against what was actually completed.
        R = (completed / scheduled) * 100

        Args:
            day_schedule: The DaySchedule for this day
            completed_items: List of item names that were completed
        """
        sanctum = self._ensure_current()

        scheduled_count = len(day_schedule.items)
        if scheduled_count == 0:
            reality_score = 100  # No schedule = perfect adherence
        else:
            # Match completed items against scheduled item names
            scheduled_names = {item.name.lower() for item in day_schedule.items}
            completed_names = {name.lower() for name in completed_items}
            matched = len(scheduled_names & completed_names)
            reality_score = int((matched / scheduled_count) * 100)

        # Update current GEAR with new R score
        sanctum.current_gear.reality = reality_score
        self._save(sanctum)

        return f"[REALITY] Schedule adherence: {reality_score}% ({len(completed_items)}/{scheduled_count} items)"

    def calculate_growth(self) -> str:
        """[GROWTH] Calculate G score from experience_log trend.

        G = improvement trend over time:
        - Compares recent average (last 7 days) to older average (prior 7 days)
        - Positive trend = growth, capped at 100
        - Uses E+A+R average as the metric to track
        """
        sanctum = self._ensure_current()

        if len(sanctum.experience_log) < 2:
            return "[GROWTH] Need at least 2 experience entries to calculate growth"

        # Sort by date
        sorted_log = sorted(sanctum.experience_log, key=lambda x: x.date)

        if len(sorted_log) <= 7:
            # Not enough for comparison - use simple average improvement
            first_total = sorted_log[0].gear.total
            last_total = sorted_log[-1].gear.total
            if first_total == 0:
                growth_score = min(100, last_total)
            else:
                improvement = ((last_total - first_total) / first_total) * 100
                growth_score = min(100, max(0, int(50 + improvement)))
        else:
            # Compare last 7 days to prior period
            recent = sorted_log[-7:]
            older = sorted_log[-14:-7] if len(sorted_log) >= 14 else sorted_log[:-7]

            recent_avg = sum(e.gear.total for e in recent) / len(recent)
            older_avg = sum(e.gear.total for e in older) / len(older)

            if older_avg == 0:
                growth_score = min(100, int(recent_avg))
            else:
                improvement = ((recent_avg - older_avg) / older_avg) * 100
                # Map: -100% = 0, 0% = 50, +100% = 100
                growth_score = min(100, max(0, int(50 + improvement / 2)))

        sanctum.current_gear.growth = growth_score
        self._save(sanctum)

        return f"[GROWTH] Trend score: {growth_score}% (based on {len(sorted_log)} entries)"

    def full_gear_update(self, daily_log: DailyLog, life_plan: Optional[LifePlan] = None,
                         day_schedule: Optional[DaySchedule] = None,
                         completed_items: Optional[List[str]] = None) -> str:
        """[GEAR] Full GEAR update with all four components.

        Combines:
        - G: Growth trend from history
        - E: Experience from daily_log vs life_plan
        - A: Awareness from mood/energy/focus
        - R: Reality from schedule adherence

        Args:
            daily_log: Today's DailyLog
            life_plan: LifePlan goals (for E calculation)
            day_schedule: DaySchedule for today (for R calculation)
            completed_items: Items completed today (for R calculation)
        """
        results = []

        # E and A from log_experience
        result_ea = self.log_experience(daily_log, life_plan)
        results.append(result_ea)

        # R from schedule adherence (if provided)
        if day_schedule and completed_items is not None:
            result_r = self.log_reality(day_schedule, completed_items)
            results.append(result_r)

        # G from trend calculation
        result_g = self.calculate_growth()
        results.append(result_g)

        # Final summary
        sanctum = self._ensure_current()
        gear = sanctum.current_gear
        results.append(f"\n[GEAR] Total: {gear.total}% (G={gear.growth}, E={gear.experience}, A={gear.awareness}, R={gear.reality})")

        return "\n".join(results)
