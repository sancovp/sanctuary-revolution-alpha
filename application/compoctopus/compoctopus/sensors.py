"""Reward signal sensors for the Construct vs Select bandit.

Sensors collect execution outcome metrics that feed the bandit's
decision of whether to Construct a new pipeline or Select a golden chain.

From the DESIGN.md:
    "To solve the bandit problem, the Compoctopus requires Sensors.
     These are metrics derived from execution outcomes:
     - Success rates (GOAL ACCOMPLISHED vs. Block)
     - Iteration efficiency (turns taken)
     - Human feedback (User validation/correction)"
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from compoctopus.types import SensorReading

logger = logging.getLogger(__name__)


class SensorStore:
    """Stores and queries execution outcome sensors.

    Each CompiledAgent execution produces a SensorReading.
    The SensorStore aggregates these by config hash to produce
    reward signals for the bandit.

    Thread-safe: all mutations are guarded by a reentrant lock.
    """

    def __init__(self, max_readings_per_hash: int = 100):
        self._readings: Dict[str, List[SensorReading]] = {}
        self._lock = threading.RLock()
        self._max_readings_per_hash = max_readings_per_hash

    def record(self, reading: SensorReading) -> None:
        """Record a sensor reading from an execution."""
        with self._lock:
            if reading.config_hash not in self._readings:
                self._readings[reading.config_hash] = []
            bucket = self._readings[reading.config_hash]
            bucket.append(reading)
            # Evict oldest if over limit
            if len(bucket) > self._max_readings_per_hash:
                evicted = len(bucket) - self._max_readings_per_hash
                del bucket[:evicted]
                logger.debug(
                    "SensorStore: evicted %d old readings for hash %s",
                    evicted, reading.config_hash[:8],
                )

    def get_reward(self, config_hash: str) -> Optional[float]:
        """Get the mean reward for a config hash.

        Reward function:
            reward = success_rate * 0.4 + efficiency * 0.3 + human_feedback * 0.3
        where:
            success_rate = goal_accomplished / total_runs
            efficiency = 1.0 - (avg_turns / max_possible_turns)
            human_feedback = avg(human_feedback scores)
        """
        readings = self.get_readings(config_hash)
        if not readings:
            return None

        success_rate = sum(1 for r in readings if r.success) / len(readings)
        avg_turns = sum(r.turns_taken for r in readings) / len(readings)
        max_turns = 25  # from SDNA max_turns default
        efficiency = max(0.0, 1.0 - (avg_turns / max_turns))

        # Human feedback: if available, average it; else default 0.5
        feedback_scores = [
            r.human_feedback for r in readings if r.human_feedback is not None
        ]
        human_feedback = (
            sum(feedback_scores) / len(feedback_scores)
            if feedback_scores else 0.5
        )

        reward = success_rate * 0.4 + efficiency * 0.3 + human_feedback * 0.3
        logger.debug(
            "SensorStore: reward for %s = %.3f (success=%.2f, eff=%.2f, human=%.2f)",
            config_hash[:8], reward, success_rate, efficiency, human_feedback,
        )
        return reward

    def get_readings(self, config_hash: str) -> List[SensorReading]:
        """Get all readings for a config hash (snapshot, thread-safe)."""
        with self._lock:
            return list(self._readings.get(config_hash, []))

    def get_count(self, config_hash: str) -> int:
        """Get the number of readings for a config hash."""
        with self._lock:
            return len(self._readings.get(config_hash, []))

    def meets_graduation_threshold(
        self,
        config_hash: str,
        min_count: int = 5,
        min_reward: float = 0.8,
    ) -> bool:
        """Check if a config should be graduated to a golden chain.

        A config graduates when it has enough runs with high enough
        mean reward to be considered reliable.
        """
        count = self.get_count(config_hash)
        if count < min_count:
            return False
        reward = self.get_reward(config_hash)
        if reward is None:
            return False
        graduated = reward >= min_reward
        if graduated:
            logger.info(
                "SensorStore: hash %s meets graduation (count=%d, reward=%.3f)",
                config_hash[:8], count, reward,
            )
        return graduated
