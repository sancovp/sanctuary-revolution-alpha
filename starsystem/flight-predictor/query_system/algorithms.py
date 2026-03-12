"""
Standard algorithms for QuerySystem layers.

ScoreAlgorithm: Filter/rank hits by confidence
CartONAlgorithm: Enrich hits with graph context
"""

from typing import Callable
import logging

logger = logging.getLogger(__name__)


class ScoreAlgorithm:
    """Factory for score filtering/ranking algorithms."""

    @staticmethod
    def passthrough(hits: list[dict]) -> list[dict]:
        """Return hits unchanged."""
        return hits

    @staticmethod
    def sort_by_score(hits: list[dict]) -> list[dict]:
        """Sort hits by score descending."""
        return sorted(hits, key=lambda h: h.get('score', 0), reverse=True)

    @staticmethod
    def top_n(n: int) -> Callable[[list[dict]], list[dict]]:
        """Return only top N hits by score."""
        def _top_n(hits: list[dict]) -> list[dict]:
            sorted_hits = sorted(hits, key=lambda h: h.get('score', 0), reverse=True)
            return sorted_hits[:n]
        return _top_n

    @staticmethod
    def dedupe_concepts(hits: list[dict]) -> list[dict]:
        """Deduplicate by concept_name, keeping highest score."""
        seen = {}
        for hit in hits:
            name = hit.get('concept_name', '')
            if name not in seen or hit.get('score', 0) > seen[name].get('score', 0):
                seen[name] = hit
        return list(seen.values())

    @staticmethod
    def compose(*algorithms: Callable) -> Callable[[list[dict]], list[dict]]:
        """Compose multiple algorithms: algo1 -> algo2 -> algo3."""
        def _composed(hits: list[dict]) -> list[dict]:
            result = hits
            for algo in algorithms:
                result = algo(result)
            return result
        return _composed


class CartONAlgorithm:
    """Factory for CartON graph enrichment algorithms."""

    @staticmethod
    def passthrough(hits: list[dict]) -> list[dict]:
        """Return hits unchanged (no enrichment)."""
        return hits

    @staticmethod
    def add_network(depth: int = 1) -> Callable[[list[dict]], list[dict]]:
        """Add concept network from Neo4j."""
        def _add_network(hits: list[dict]) -> list[dict]:
            try:
                from carton_mcp.carton_utils import CartOnUtils
                utils = CartOnUtils()

                for hit in hits:
                    concept_name = hit.get('concept_name', '')
                    if concept_name:
                        network = utils.get_concept_network_data(concept_name, depth)
                        hit['network'] = network
            except Exception as e:
                logger.warning(f"Network enrichment failed: {e}")

            return hits
        return _add_network

    @staticmethod
    def add_relationships() -> Callable[[list[dict]], list[dict]]:
        """Add direct relationships from Neo4j."""
        def _add_rels(hits: list[dict]) -> list[dict]:
            try:
                from carton_mcp.carton_utils import CartOnUtils
                utils = CartOnUtils()

                for hit in hits:
                    concept_name = hit.get('concept_name', '')
                    if concept_name:
                        concept_data = utils.get_concept_data(concept_name)
                        hit['relationships'] = concept_data.get('relationships', {})
            except Exception as e:
                logger.warning(f"Relationship enrichment failed: {e}")

            return hits
        return _add_rels

    @staticmethod
    def compose(*algorithms: Callable) -> Callable[[list[dict]], list[dict]]:
        """Compose multiple algorithms."""
        def _composed(hits: list[dict]) -> list[dict]:
            result = hits
            for algo in algorithms:
                result = algo(result)
            return result
        return _composed
