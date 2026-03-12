"""
Scoring Display Functions for SEED Home HUD

These functions are called via dynamic_call in home.hpi to display fitness scores
and other system metrics (OPERA quarantine count, etc.).
They read from registries without creating direct dependencies.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

try:
    from heaven_base.registry.registry_service import RegistryService
except ImportError as e:
    logger.error(f"Failed to import RegistryService: {e}")
    RegistryService = None

# Import starsystem_reward_system if available
try:
    import starsystem_reward_system as reward_system
except ImportError as e:
    logger.error(f"Failed to import starsystem_reward_system: {e}")
    reward_system = None


def get_opera_quarantine_count() -> str:
    """
    Read OPERA quarantine count from registry (no direct OPERA dependency).

    OPERA maintains quarantine_count in opera_metrics registry.
    SEED reads from registry to display count in HOME HUD.

    Returns:
        Formatted string showing quarantine count
    """
    if not RegistryService:
        return "0"

    try:
        registry_service = RegistryService()

        # Read quarantine count from opera_metrics registry
        result = registry_service.get("opera_metrics", "quarantine_count")

        if result and isinstance(result, dict):
            count = result.get("count", 0)
            return str(count)
        else:
            # Registry key doesn't exist yet (no patterns detected)
            return "0"

    except Exception as e:
        logger.error(f"Error reading OPERA quarantine count: {e}")
        return "0"


def get_latest_score_display() -> str:
    """
    Get the most recent fitness score (today's score).

    Returns:
        Formatted string showing today's fitness score
    """
    if not RegistryService or not reward_system:
        return "Score: N/A (dependencies missing)"

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        registry_service = RegistryService()

        fitness_data = reward_system.compute_fitness(registry_service, today)

        return f"Fitness: {fitness_data['fitness']:.2f} | Level: {fitness_data['level']} | XP: {fitness_data['xp']:.2f}"

    except Exception as e:
        logger.error(f"Error computing latest score: {e}")
        return f"Score: Error ({str(e)})"


def get_last_7_days_display() -> str:
    """
    Aggregate fitness scores for the last 7 days.

    Returns:
        Formatted string showing 7-day aggregated score
    """
    if not RegistryService or not reward_system:
        return "7-Day Score: N/A (dependencies missing)"

    try:
        registry_service = RegistryService()
        today = datetime.now()

        total_fitness = 0.0
        total_xp = 0.0
        days_with_data = 0

        for i in range(7):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                fitness_data = reward_system.compute_fitness(registry_service, date)
                total_fitness += fitness_data['fitness']
                total_xp += fitness_data['xp']
                days_with_data += 1
            except Exception:
                # No events for this date, skip
                continue

        avg_fitness = total_fitness / days_with_data if days_with_data > 0 else 0.0

        return f"7-Day: Fitness: {total_fitness:.2f} | Avg: {avg_fitness:.2f} | XP: {total_xp:.2f} | Days: {days_with_data}/7"

    except Exception as e:
        logger.error(f"Error computing 7-day score: {e}")
        return f"7-Day Score: Error ({str(e)})"


def get_last_30_days_display() -> str:
    """
    Aggregate fitness scores for the last 30 days.

    Returns:
        Formatted string showing 30-day aggregated score
    """
    if not RegistryService or not reward_system:
        return "30-Day Score: N/A (dependencies missing)"

    try:
        registry_service = RegistryService()
        today = datetime.now()

        total_fitness = 0.0
        total_xp = 0.0
        days_with_data = 0

        for i in range(30):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                fitness_data = reward_system.compute_fitness(registry_service, date)
                total_fitness += fitness_data['fitness']
                total_xp += fitness_data['xp']
                days_with_data += 1
            except Exception:
                # No events for this date, skip
                continue

        avg_fitness = total_fitness / days_with_data if days_with_data > 0 else 0.0

        return f"30-Day: Fitness: {total_fitness:.2f} | Avg: {avg_fitness:.2f} | XP: {total_xp:.2f} | Days: {days_with_data}/30"

    except Exception as e:
        logger.error(f"Error computing 30-day score: {e}")
        return f"30-Day Score: Error ({str(e)})"


def get_all_time_display() -> str:
    """
    Aggregate fitness scores for all time (all dates with event registries).

    Returns:
        Formatted string showing all-time aggregated score
    """
    if not RegistryService or not reward_system:
        return "All-Time Score: N/A (dependencies missing)"

    try:
        registry_service = RegistryService()

        # Get all registries and find event registries
        all_registries = registry_service.list_registries()

        # Find all date-based event registries
        event_dates = set()
        for registry_name in all_registries:
            for prefix in ["home_events_", "session_events_", "mission_events_"]:
                if registry_name.startswith(prefix):
                    # Extract date from registry name
                    date_str = registry_name.replace(prefix, "").replace("_registry", "")
                    event_dates.add(date_str)

        # Compute scores for all dates
        total_fitness = 0.0
        total_xp = 0.0
        total_days = 0

        for date in sorted(event_dates):
            try:
                fitness_data = reward_system.compute_fitness(registry_service, date)
                total_fitness += fitness_data['fitness']
                total_xp += fitness_data['xp']
                total_days += 1
            except Exception:
                # Skip dates with issues
                continue

        avg_fitness = total_fitness / total_days if total_days > 0 else 0.0
        overall_level = int(total_fitness)

        return f"All-Time: Fitness: {total_fitness:.2f} | Level: {overall_level} | XP: {total_xp:.2f} | Days: {total_days}"

    except Exception as e:
        logger.error(f"Error computing all-time score: {e}")
        return f"All-Time Score: Error ({str(e)})"
