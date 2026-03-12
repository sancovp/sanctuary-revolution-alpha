"""Golden chain store — high-reward configurations for fast reuse.

When the bandit has enough evidence that a compilation config works well,
it gets "graduated" to a golden chain. Future similar tasks can then
Select the golden chain instead of Constructing a new pipeline.

From DESIGN.md:
    "A high-reward configuration is eventually 'graduated' to a permanent
     Selection candidate, reducing the need for costly Construction passes."
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional

from compoctopus.types import CompiledAgent, FeatureType, GoldenChainEntry

logger = logging.getLogger(__name__)

# Default max chains before LRU eviction kicks in
DEFAULT_MAX_CHAINS = 500
# Default TTL in seconds (30 days)
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60


class GoldenChainStore:
    """Stores and retrieves graduated high-reward configurations.

    Features:
        - Thread-safe (RLock)
        - LRU eviction when max_chains exceeded
        - TTL-based expiry (lazy eviction on access)
        - Persistence hooks (sync_to_carton / sync_from_carton)

    Backed by an in-memory dict for now; can be persisted to Carton later.
    """

    def __init__(
        self,
        max_chains: int = DEFAULT_MAX_CHAINS,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ):
        self._chains: Dict[str, GoldenChainEntry] = {}
        self._access_times: Dict[str, float] = {}   # config_hash → last access
        self._created_times: Dict[str, float] = {}   # config_hash → creation time
        self._lock = threading.RLock()
        self._max_chains = max_chains
        self._ttl_seconds = ttl_seconds

    def store(self, entry: GoldenChainEntry) -> None:
        """Store a golden chain entry."""
        with self._lock:
            now = time.time()
            self._chains[entry.config_hash] = entry
            self._access_times[entry.config_hash] = now
            self._created_times[entry.config_hash] = now
            self._evict_if_needed()
            logger.info(
                "GoldenChainStore: stored chain %s (domain=%s, reward=%.3f)",
                entry.config_hash[:8], entry.domain, entry.reward_mean,
            )

    def get(self, config_hash: str) -> Optional[GoldenChainEntry]:
        """Get a golden chain by config hash. Returns None if expired."""
        with self._lock:
            if config_hash not in self._chains:
                return None
            if self._is_expired(config_hash):
                self._remove(config_hash)
                return None
            self._access_times[config_hash] = time.time()
            return self._chains[config_hash]

    def find_for_task(
        self,
        domain: str,
        feature_type: FeatureType,
        min_reward: float = 0.8,
    ) -> Optional[GoldenChainEntry]:
        """Find the best golden chain for a task context.

        Searches by domain + feature_type and returns the highest
        reward chain that meets the minimum threshold.
        """
        with self._lock:
            self._evict_expired()
            candidates = [
                c for c in self._chains.values()
                if c.domain == domain
                and c.feature_type == feature_type
                and c.reward_mean >= min_reward
            ]
            if not candidates:
                return None
            best = max(candidates, key=lambda c: c.reward_mean)
            self._access_times[best.config_hash] = time.time()
            logger.debug(
                "GoldenChainStore: found chain %s for %s/%s (reward=%.3f)",
                best.config_hash[:8], domain, feature_type.value, best.reward_mean,
            )
            return best

    def graduate(
        self,
        compiled_agent: CompiledAgent,
        reward_mean: float,
        reward_count: int,
        domain: str,
    ) -> GoldenChainEntry:
        """Graduate a successful config to a golden chain.

        Creates a GoldenChainEntry and stores it for future Select decisions.
        """
        config_hash = compiled_agent.compile_id or str(hash(
            str(compiled_agent.system_prompt) + str(compiled_agent.tool_manifest)
        ))
        entry = GoldenChainEntry(
            config_hash=config_hash,
            reward_mean=reward_mean,
            reward_count=reward_count,
            domain=domain,
            feature_type=compiled_agent.task_spec.feature_type,
            compiled_agent=compiled_agent,
        )
        self.store(entry)
        logger.info(
            "GoldenChainStore: graduated %s (domain=%s, reward=%.3f, count=%d)",
            config_hash[:8], domain, reward_mean, reward_count,
        )
        return entry

    def list_chains(self, domain: Optional[str] = None) -> List[GoldenChainEntry]:
        """List all golden chains, optionally filtered by domain."""
        with self._lock:
            self._evict_expired()
            if domain:
                return [c for c in self._chains.values() if c.domain == domain]
            return list(self._chains.values())

    @property
    def size(self) -> int:
        """Current number of stored chains."""
        with self._lock:
            return len(self._chains)

    # ---- Eviction ----

    def _is_expired(self, config_hash: str) -> bool:
        """Check if a chain has exceeded its TTL."""
        created = self._created_times.get(config_hash, 0)
        return (time.time() - created) > self._ttl_seconds

    def _evict_expired(self) -> None:
        """Remove all expired chains (must hold lock)."""
        expired = [h for h in self._chains if self._is_expired(h)]
        for h in expired:
            self._remove(h)
        if expired:
            logger.debug("GoldenChainStore: evicted %d expired chains", len(expired))

    def _evict_if_needed(self) -> None:
        """LRU eviction when over max_chains (must hold lock)."""
        while len(self._chains) > self._max_chains:
            lru_hash = min(self._access_times, key=self._access_times.get)
            logger.debug(
                "GoldenChainStore: LRU evicting %s (size=%d > max=%d)",
                lru_hash[:8], len(self._chains), self._max_chains,
            )
            self._remove(lru_hash)

    def _remove(self, config_hash: str) -> None:
        """Remove a chain and its metadata (must hold lock)."""
        self._chains.pop(config_hash, None)
        self._access_times.pop(config_hash, None)
        self._created_times.pop(config_hash, None)

    # ---- Persistence ----

    def sync_to_carton(self) -> None:
        """Persist golden chains to Carton KG."""
        raise NotImplementedError(
            "sync_to_carton is not yet implemented. "
            "When implemented, will use carton observe_from_identity_pov to persist "
            "each chain as a Golden_Chain concept in the knowledge graph. "
            "Fix: implement Carton integration in golden_chains.py."
        )

    def sync_from_carton(self) -> None:
        """Load golden chains from Carton KG."""
        raise NotImplementedError(
            "sync_from_carton is not yet implemented. "
            "When implemented, will query carton for IS_A Golden_Chain concepts "
            "and hydrate entries from their stored descriptions. "
            "Fix: implement Carton integration in golden_chains.py."
        )
