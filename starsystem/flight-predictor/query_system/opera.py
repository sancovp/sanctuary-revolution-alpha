"""
OPERA - Operadic Prediction and Exploratory Representation Algorithm.

Capability prediction system built on QuerySystem.

Hierarchy (low→high abstraction):
    skills+tools (atoms) → flights (molecules) → missions (organisms)
    → canopies (ecosystems) → operadics (meta-compositions)

Higher tiers suppress components in lower tiers.

OPERA = QuerySystem([
    Layer("skill", ...),    # Tier 0: atoms
    Layer("tool", ...),     # Tier 0: atoms (same level as skill)
    Layer("flight", ...),   # Tier 1: molecules
    Layer("mission", ...),  # Tier 2: organisms
    Layer("canopy", ...),   # Tier 3: ecosystems
    Layer("operadic", ...), # Tier 4: meta-compositions
])
"""

import os
from .core import QuerySystem, Layer, EmbeddingSource, QueryResult
from .algorithms import ScoreAlgorithm, CartONAlgorithm

HEAVEN_DATA = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def _chroma_source(name: str, chroma_subdir: str, collection: str) -> EmbeddingSource:
    """Create EmbeddingSource for specific ChromaDB location."""
    source = EmbeddingSource(
        name=name,
        collection_name=collection,
        cypher_filter=None,
    )
    # Override the collection getter to use correct path
    import chromadb
    from chromadb.config import Settings
    client = chromadb.PersistentClient(
        path=os.path.join(HEAVEN_DATA, chroma_subdir),
        settings=Settings(anonymized_telemetry=False)
    )
    try:
        source._collection = client.get_collection(collection)
    except Exception:
        source._collection = None
    return source


def build_opera() -> QuerySystem:
    """
    Build OPERA with layers ordered low→high abstraction.

    Returns highest abstraction that matches (suppresses lower layers).
    """
    # Score algorithm: dedupe, sort, top 10
    standard_score = ScoreAlgorithm.compose(
        ScoreAlgorithm.dedupe_concepts,
        ScoreAlgorithm.sort_by_score,
        ScoreAlgorithm.top_n(10),
    )

    # CartON algorithm: add relationships
    standard_carton = CartONAlgorithm.add_relationships()

    # Layers ordered LOW → HIGH abstraction
    layers = [
        # Skill layer - uses skill_chroma/skillgraphs
        Layer(
            name="skill",
            source=_chroma_source("skillgraphs", "skill_chroma", "skillgraphs"),
            score_algorithm=standard_score,
            carton_algorithm=standard_carton,
            threshold=0.4,
        ),
        # Tool layer - uses tool_chroma/toolgraphs
        Layer(
            name="tool",
            source=_chroma_source("toolgraphs", "tool_chroma", "toolgraphs"),
            score_algorithm=standard_score,
            carton_algorithm=standard_carton,
            threshold=0.4,
        ),
        # Flight layer - uses flight_chroma/flightgraphs
        Layer(
            name="flight",
            source=_chroma_source("flightgraphs", "flight_chroma", "flightgraphs"),
            score_algorithm=standard_score,
            carton_algorithm=standard_carton,
            threshold=0.4,
        ),
        # Mission layer - uses mission_chroma/missiongraphs (if exists)
        Layer(
            name="mission",
            source=_chroma_source("missiongraphs", "mission_chroma", "missiongraphs"),
            score_algorithm=standard_score,
            carton_algorithm=standard_carton,
            threshold=0.4,
        ),
        # Tier 3: Canopy - ecosystems
        Layer(
            name="canopy",
            source=_chroma_source("canopygraphs", "canopy_chroma", "canopygraphs"),
            score_algorithm=standard_score,
            carton_algorithm=standard_carton,
            threshold=0.4,
        ),
        # Tier 4: Operadic - meta-compositions
        Layer(
            name="operadic",
            source=_chroma_source("operadicgraphs", "operadic_chroma", "operadicgraphs"),
            score_algorithm=standard_score,
            carton_algorithm=standard_carton,
            threshold=0.4,
        ),
    ]

    # Define tier groupings for suppression logic
    opera = QuerySystem(layers, name="OPERA")
    opera.tier_map = {
        "skill": 0, "tool": 0,  # Atoms - same tier
        "flight": 1,             # Molecules
        "mission": 2,            # Organisms
        "canopy": 3,             # Ecosystems
        "operadic": 4,           # Meta-compositions
    }
    return opera


# Singleton instance
OPERA = None


def get_opera() -> QuerySystem:
    """Get or create OPERA instance."""
    global OPERA
    if OPERA is None:
        OPERA = build_opera()
    return OPERA


def format_opera_result(result: QueryResult) -> str:
    """Format OPERA QueryResult as readable output."""
    lines = [f"🎭 OPERA Query: {result.query[:50]}...", ""]

    for layer_name, layer_result in result.layer_results.items():
        icon = {"skill": "📚", "tool": "🔧", "flight": "✈️", "mission": "🎯", "canopy": "🌳", "operadic": "🎭"}.get(layer_name, "📦")

        if layer_result.is_empty:
            lines.append(f"{icon} {layer_name}: (no matches above threshold)")
        else:
            concepts = [h['concept_name'] for h in layer_result.hits[:5]]
            best = layer_result.best_score
            lines.append(f"{icon} {layer_name} (best: {best:.2f}): {', '.join(concepts)}")

    lines.append(f"\n📊 Overall best score: {result.overall_best_score:.2f}")
    lines.append(f"📋 All concepts: {', '.join(result.all_concepts()[:10])}")

    return "\n".join(lines)
