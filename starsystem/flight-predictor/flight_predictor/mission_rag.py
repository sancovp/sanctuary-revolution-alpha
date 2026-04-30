"""
CartON-style Mission RAG: ChromaDB Missiongraphs → Multi-session workflow discovery

Pattern:
1. RAG query → Get Missiongraph hits from ChromaDB
2. Extract flight references → Link to Flightgraphs
3. Return structured results for mission selection
"""

import logging
import os
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


@dataclass
class MissiongraphHit:
    """Individual Missiongraph match from RAG."""
    name: str
    mission_name: str
    domain: str
    flight_count: int
    score: float
    sentence: str


@dataclass
class MissionRAGResult:
    """Result from Missiongraph RAG."""
    query: str
    hits: list[MissiongraphHit] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "missions": [
                {
                    "missiongraph": h.name,
                    "mission": h.mission_name,
                    "domain": h.domain,
                    "flight_count": h.flight_count,
                    "score": h.score
                }
                for h in self.hits
            ]
        }


def get_chroma_client() -> chromadb.ClientAPI:
    """Get ChromaDB client — connects to shared HTTP server started by observation_worker_daemon."""
    return chromadb.HttpClient(host="localhost", port=8101)


def mission_rag_query(query: str, n_results: int = 5) -> MissionRAGResult:
    """Query Missiongraphs for matching multi-session workflows."""
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name="missiongraphs",
            metadata={"hnsw:space": "cosine"}
        )

        results = collection.query(query_texts=[query], n_results=n_results)

        hits = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                document = results["documents"][0][i] if results["documents"] else ""

                hits.append(MissiongraphHit(
                    name=metadata.get("name", doc_id.split(":", 1)[-1]),
                    mission_name=metadata.get("mission", ""),
                    domain=metadata.get("domain", "unknown"),
                    flight_count=metadata.get("flight_count", 0),
                    score=1 - distance,
                    sentence=document
                ))

        return MissionRAGResult(query=query, hits=hits)
    except Exception as e:
        logger.error(f"Mission RAG query failed: {e}")
        return MissionRAGResult(query=query)


def format_mission_rag_result(result: MissionRAGResult) -> str:
    """Format MissionRAGResult as human-readable output."""
    lines = [f"🎯 Mission RAG Results for: '{result.query}'"]
    lines.append("=" * 60)

    if not result.hits:
        lines.append("\n⚠️ No mission predictions found")
        return "\n".join(lines)

    for i, hit in enumerate(result.hits, 1):
        mission_display = hit.mission_name.replace("Mission_", "").replace("_", " ")
        lines.append(f"\n{i}. {mission_display}")
        lines.append(f"   Domain: {hit.domain}")
        lines.append(f"   Flights: {hit.flight_count}")
        lines.append(f"   Score: {hit.score:.2f}")

    return "\n".join(lines)


def test_mission_rag():
    """Test mission RAG with sample queries."""
    queries = [
        "compound intelligence",
        "authentication feature",
        "sanctuary game",
    ]

    for q in queries:
        result = mission_rag_query(q, n_results=3)
        print(format_mission_rag_result(result))
        print("\n")


if __name__ == "__main__":
    test_mission_rag()
