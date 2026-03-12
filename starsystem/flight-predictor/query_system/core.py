"""
Core QuerySystem classes - the composable semantic query framework.

Architecture:
    QuerySystem = [Layer, Layer, Layer, ...]
    Layer = EmbeddingSource + ScoreAlgorithm + CartONAlgorithm
    EmbeddingSource = ChromaDB collection from CartON scope
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingSource:
    """
    Bridge from CartON scope to ChromaDB collection.

    Defines which concepts to embed and where to store/query them.
    """
    name: str  # Identifier for this source
    collection_name: str  # ChromaDB collection name
    cypher_filter: Optional[str] = None  # Neo4j filter for which concepts

    # Connection state (lazy initialized)
    _collection: Any = field(default=None, repr=False)

    @classmethod
    def from_collection(cls, collection_name: str) -> "EmbeddingSource":
        """Create source from CartON collection like 'Skillgraph_'."""
        return cls(
            name=collection_name,
            collection_name=collection_name,
            cypher_filter=f"MATCH (c)-[:PART_OF]->(:Wiki {{n: '{collection_name}'}})"
        )

    @classmethod
    def from_domain(cls, domain: str) -> "EmbeddingSource":
        """Create source from domain like 'PAIAB', 'CAVE', 'SANCTUM'."""
        return cls(
            name=f"{domain}_domain",
            collection_name=f"{domain}_embeddings",
            cypher_filter=f"MATCH (c)-[:HAS_DOMAIN]->(:Wiki {{n: '{domain}'}})"
        )

    @classmethod
    def from_scope(cls, name: str, collection_name: str, cypher: str) -> "EmbeddingSource":
        """Create source from arbitrary Cypher scope."""
        return cls(name=name, collection_name=collection_name, cypher_filter=cypher)

    def get_collection(self):
        """Get or create ChromaDB collection connection."""
        if self._collection is None:
            # Lazy import to avoid startup issues
            import chromadb
            import os

            heaven_data = os.getenv('HEAVEN_DATA_DIR', '/tmp/heaven_data')
            client = chromadb.PersistentClient(path=f"{heaven_data}/chroma_db")

            try:
                self._collection = client.get_collection(self.collection_name)
            except Exception:
                logger.warning(f"Collection {self.collection_name} not found")
                self._collection = None

        return self._collection

    def search(self, query: str, n_results: int = 10) -> list[dict]:
        """
        Search this embedding source.

        Returns list of {concept_name, score, content, metadata}
        """
        collection = self.get_collection()
        if collection is None:
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            # Convert to standard format
            hits = []
            if results and results.get('ids') and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    score = 1.0 - distance  # Convert distance to similarity

                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    content = results['documents'][0][i] if results.get('documents') else ""

                    hits.append({
                        'concept_name': metadata.get('concept_name', doc_id),
                        'score': score,
                        'content': content,
                        'metadata': metadata,
                    })

            return hits

        except Exception as e:
            logger.warning(f"Search failed on {self.collection_name}: {e}")
            return []


@dataclass
class LayerResult:
    """Result from a single layer's query."""
    layer_name: str
    hits: list[dict]  # [{concept_name, score, content, enrichment}]
    best_score: float
    triggered_fallback: bool = False

    @property
    def is_empty(self) -> bool:
        return len(self.hits) == 0


@dataclass
class QueryResult:
    """Aggregated result from all layers."""
    query: str
    layer_results: dict[str, LayerResult]  # layer_name -> LayerResult
    overall_best_score: float
    highest_abstraction: Optional[str] = None  # Layer name of highest match
    suppressed: dict = field(default_factory=dict)  # layer -> [suppressed concepts]

    def get_layer(self, name: str) -> Optional[LayerResult]:
        return self.layer_results.get(name)

    def all_concepts(self) -> list[str]:
        """Get all concept names across all layers."""
        concepts = []
        for lr in self.layer_results.values():
            for hit in lr.hits:
                if hit['concept_name'] not in concepts:
                    concepts.append(hit['concept_name'])
        return concepts

    def highest_layer_concepts(self) -> list[str]:
        """Get concepts only from the highest abstraction layer."""
        if self.highest_abstraction and self.highest_abstraction in self.layer_results:
            return [h['concept_name'] for h in self.layer_results[self.highest_abstraction].hits]
        return self.all_concepts()


@dataclass
class Layer:
    """
    One query layer in a QuerySystem.

    Combines:
    - EmbeddingSource: where to search
    - score_algorithm: how to filter/rank results
    - carton_algorithm: how to enrich with graph context
    """
    name: str
    source: EmbeddingSource
    score_algorithm: Callable[[list[dict]], list[dict]]  # Filter/rank hits
    carton_algorithm: Callable[[list[dict]], list[dict]]  # Enrich with graph
    threshold: float = 0.5  # Minimum score to include

    def query(self, query_text: str, n_results: int = 10) -> LayerResult:
        """
        Execute this layer's query pipeline.

        1. Search embedding source
        2. Apply score algorithm (filter/rank)
        3. Apply carton algorithm (enrich)
        4. Return LayerResult
        """
        logger.info(f"Layer[{self.name}] querying: {query_text[:50]}...")

        # Step 1: Search embeddings
        raw_hits = self.source.search(query_text, n_results)

        if not raw_hits:
            logger.info(f"Layer[{self.name}] no hits from embedding search")
            return LayerResult(
                layer_name=self.name,
                hits=[],
                best_score=0.0,
                triggered_fallback=True,
            )

        # Step 2: Apply score algorithm
        scored_hits = self.score_algorithm(raw_hits)

        # Filter by threshold
        filtered_hits = [h for h in scored_hits if h['score'] >= self.threshold]

        if not filtered_hits:
            best_raw = max(h['score'] for h in raw_hits) if raw_hits else 0.0
            logger.info(f"Layer[{self.name}] all hits below threshold {self.threshold} (best: {best_raw:.2f})")
            return LayerResult(
                layer_name=self.name,
                hits=[],
                best_score=best_raw,
                triggered_fallback=True,
            )

        # Step 3: Apply carton algorithm (enrich with graph)
        enriched_hits = self.carton_algorithm(filtered_hits)

        best_score = max(h['score'] for h in enriched_hits) if enriched_hits else 0.0
        logger.info(f"Layer[{self.name}] returning {len(enriched_hits)} hits (best: {best_score:.2f})")

        return LayerResult(
            layer_name=self.name,
            hits=enriched_hits,
            best_score=best_score,
            triggered_fallback=False,
        )


class QuerySystem:
    """
    Composable semantic query system.

    Stack layers to create emergent intelligence:
        OPERA = QuerySystem([
            Layer("skill", ...),
            Layer("tool", ...),
            Layer("flight", ...),
        ])
        result = OPERA.query("I need to build an MCP")
    """

    def __init__(self, layers: list[Layer], name: str = "QuerySystem"):
        self.name = name
        self.layers = layers
        self._layer_map = {layer.name: layer for layer in layers}

    def query(self, query_text: str, n_results: int = 10) -> QueryResult:
        """
        Run query through all layers, then suppress lower layers if higher contains them.

        Layers are ordered low→high abstraction. If flight found, suppress its skills/tools.
        """
        logger.info(f"{self.name} processing query: {query_text[:50]}...")

        layer_results = {}
        overall_best = 0.0

        # Query all layers
        for layer in self.layers:
            result = layer.query(query_text, n_results)
            layer_results[layer.name] = result
            overall_best = max(overall_best, result.best_score)

        # Apply suppression: higher layers suppress components in lower layers
        suppressed = self._apply_suppression(layer_results)
        highest = self._find_highest_abstraction(layer_results)

        return QueryResult(
            query=query_text,
            layer_results=layer_results,
            overall_best_score=overall_best,
            highest_abstraction=highest,
            suppressed=suppressed,
        )

    def _find_highest_abstraction(self, layer_results: dict) -> Optional[str]:
        """Find the highest layer with non-empty results."""
        # Layers are ordered low→high, so iterate in reverse
        for layer in reversed(self.layers):
            lr = layer_results.get(layer.name)
            if lr and not lr.is_empty:
                return layer.name
        return None

    def _apply_suppression(self, layer_results: dict) -> dict:
        """
        Suppress lower layer concepts that are contained in higher layer concepts.

        Uses CartON HAS_COMPONENT/PART_OF relationships to detect containment.
        """
        suppressed = {}
        # For now, mark for suppression but don't modify results
        # Full implementation would query CartON for containment relationships
        # e.g., Flight_Make_Mcp --HAS_STEP--> uses Skill_Make_Mcp
        return suppressed

    def get_layer(self, name: str) -> Optional[Layer]:
        return self._layer_map.get(name)

    def add_layer(self, layer: Layer) -> None:
        """Add a layer dynamically."""
        self.layers.append(layer)
        self._layer_map[layer.name] = layer

    def __repr__(self) -> str:
        layer_names = [l.name for l in self.layers]
        return f"QuerySystem({self.name}, layers={layer_names})"
