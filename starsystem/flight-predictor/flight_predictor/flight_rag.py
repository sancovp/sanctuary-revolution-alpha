"""
CartON-style Flight RAG: ChromaDB Flightgraphs → Capability Slot Resolution

Pattern:
1. RAG query → Get Flightgraph hits from ChromaDB
2. Extract capability slots → Toolgraph/Skillgraph references
3. Return structured results for slot filling
"""

import logging
import os
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


@dataclass
class FlightgraphHit:
    """Individual Flightgraph match from RAG."""
    name: str
    flight_name: str
    domain: str
    slot_count: int
    score: float
    sentence: str


@dataclass
class FlightRAGResult:
    """Result from Flightgraph RAG."""
    query: str
    hits: list[FlightgraphHit] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "flights": [
                {
                    "flightgraph": h.name,
                    "flight": h.flight_name,
                    "domain": h.domain,
                    "slot_count": h.slot_count,
                    "score": h.score
                }
                for h in self.hits
            ]
        }


def get_chroma_client() -> chromadb.ClientAPI:
    """Get ChromaDB client for flight embeddings."""
    chroma_path = os.path.join(HEAVEN_DATA_DIR, "chroma_db")
    return chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False)
    )


def flight_rag_query(query: str, n_results: int = 5) -> FlightRAGResult:
    """
    Layer 0: EXACT TERM MATCH on Flightgraph concept names.

    Split query into words, find concepts where those exact words appear in the name.
    Rank by maximum overlap (most matching terms = highest rank).
    """
    # Split query into terms
    query_terms = set(query.lower().replace("-", " ").replace("_", " ").split())
    query_terms = {t for t in query_terms if len(t) > 1}  # Filter single chars

    if not query_terms:
        return FlightRAGResult(query=query)

    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name="flightgraphs",
            metadata={"hnsw:space": "cosine"}
        )

        # Get ALL concept names from ChromaDB
        all_items = collection.get(include=["metadatas", "documents"])

        matches = []
        for i, doc_id in enumerate(all_items["ids"]):
            metadata = all_items["metadatas"][i] if all_items["metadatas"] else {}
            document = all_items["documents"][i] if all_items["documents"] else ""

            flightgraph_name = metadata.get("name", doc_id.split(":", 1)[-1])

            # Convert concept name to terms: Flightgraph_Make_Mcp → {"make", "mcp"}
            concept_terms = set(flightgraph_name.lower().replace("flightgraph_", "").replace("_", " ").split())

            # Count how many query terms match
            overlap = query_terms & concept_terms
            if overlap:
                # Score = proportion of query terms matched
                score = len(overlap) / len(query_terms)

                matches.append(FlightgraphHit(
                    name=flightgraph_name,
                    flight_name=metadata.get("flight", flightgraph_name.replace("Flightgraph_", "Flight_")),
                    domain=metadata.get("domain", "unknown"),
                    slot_count=metadata.get("slot_count", 0),
                    score=score,
                    sentence=document
                ))

        # Sort by score (highest first)
        matches.sort(key=lambda x: x.score, reverse=True)

        return FlightRAGResult(query=query, hits=matches[:n_results])

    except Exception as e:
        logger.error(f"Flight RAG query failed: {e}")
        return FlightRAGResult(query=query)


def format_flight_rag_result(result: FlightRAGResult) -> str:
    """Format FlightRAGResult as human-readable output."""
    lines = [f"🛫 Flight RAG Results for: '{result.query}'"]
    lines.append("=" * 60)

    if not result.hits:
        lines.append("\n⚠️ No flight predictions found")
        return "\n".join(lines)

    for i, hit in enumerate(result.hits, 1):
        flight_display = hit.flight_name.replace("Flight_", "").replace("_", "-").lower()
        lines.append(f"\n{i}. {flight_display}")
        lines.append(f"   Domain: {hit.domain}")
        lines.append(f"   Capability Slots: {hit.slot_count}")
        lines.append(f"   Score: {hit.score:.2f}")

    return "\n".join(lines)


def test_flight_rag():
    """Test flight RAG with sample queries."""
    queries = [
        "build MCP server",
        "play sanctuary game",
        "create a flight config",
    ]

    for q in queries:
        result = flight_rag_query(q, n_results=3)
        print(format_flight_rag_result(result))
        print("\n")


if __name__ == "__main__":
    test_flight_rag()
