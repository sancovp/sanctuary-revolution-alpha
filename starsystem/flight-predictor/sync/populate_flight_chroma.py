"""Populate flight ChromaDB from generated Flightgraph concepts for RAG queries."""

import json
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def populate_flight_chroma():
    """Embed Flightgraph ontological sentences into ChromaDB."""

    concepts_path = Path("/tmp/rag_tool_discovery/data/flight_concepts.json")
    if not concepts_path.exists():
        print(f"Flight concepts not found at {concepts_path}")
        print("Run ingest_flights_to_carton.py first")
        return

    concepts = json.loads(concepts_path.read_text())

    # Filter for Flightgraph concepts only
    flightgraphs = [c for c in concepts if c['concept_name'].startswith('Flightgraph_')]
    print(f"Found {len(flightgraphs)} Flightgraph concepts")

    client = chromadb.PersistentClient(
        path=os.path.join(HEAVEN_DATA_DIR, "flight_chroma"),
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_or_create_collection(
        name="flightgraphs",
        metadata={"hnsw:space": "cosine"}
    )

    # Clear existing
    existing = collection.count()
    if existing > 0:
        print(f"Clearing {existing} existing flightgraphs")
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

    ids = []
    documents = []
    metadatas = []

    for fg in flightgraphs:
        name = fg['concept_name']
        sentence = fg['concept']

        rels = {r['relationship']: r['related'] for r in fg.get('relationships', [])}

        domain = rels.get('has_domain', ['unknown'])[0]
        root = rels.get('has_root', [''])[0] if rels.get('has_root') else ''
        slots = rels.get('has_capability_slot', []) if rels.get('has_capability_slot') else []

        ids.append(f"flightgraph:{name}")
        documents.append(sentence)
        metadatas.append({
            "type": "flightgraph",
            "name": name,
            "flight": root,
            "domain": domain,
            "slot_count": len(slots)
        })

    # Batch add
    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Done! Collection has {collection.count()} flightgraphs")

    # Test query
    print("\n=== Test Query: 'build MCP server' ===")
    results = collection.query(query_texts=["build MCP server"], n_results=3)
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        print(f"  {i+1}. {meta['name']} (domain: {meta['domain']}, dist: {dist:.3f})")

    print("\n=== Test Query: 'play sanctuary game' ===")
    results = collection.query(query_texts=["play sanctuary game"], n_results=3)
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        print(f"  {i+1}. {meta['name']} (domain: {meta['domain']}, dist: {dist:.3f})")


if __name__ == "__main__":
    populate_flight_chroma()
