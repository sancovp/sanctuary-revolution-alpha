"""Populate mission ChromaDB from generated Missiongraph concepts for RAG queries."""

import json
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def populate_mission_chroma():
    """Embed Missiongraph ontological sentences into ChromaDB."""

    concepts_path = Path("/tmp/rag_tool_discovery/data/mission_concepts.json")
    if not concepts_path.exists():
        print(f"Mission concepts not found at {concepts_path}")
        print("Run ingest_missions_to_carton.py first")
        return

    concepts = json.loads(concepts_path.read_text())

    missiongraphs = [c for c in concepts if c['concept_name'].startswith('Missiongraph_')]
    print(f"Found {len(missiongraphs)} Missiongraph concepts")

    client = chromadb.PersistentClient(
        path=os.path.join(HEAVEN_DATA_DIR, "mission_chroma"),
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_or_create_collection(
        name="missiongraphs",
        metadata={"hnsw:space": "cosine"}
    )

    existing = collection.count()
    if existing > 0:
        print(f"Clearing {existing} existing missiongraphs")
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

    ids = []
    documents = []
    metadatas = []

    for mg in missiongraphs:
        name = mg['concept_name']
        sentence = mg['concept']

        rels = {r['relationship']: r['related'] for r in mg.get('relationships', [])}

        domain = rels.get('has_domain', ['unknown'])[0]
        root = rels.get('has_root', [''])[0] if rels.get('has_root') else ''
        flights = rels.get('has_flight', []) if rels.get('has_flight') else []

        ids.append(f"missiongraph:{name}")
        documents.append(sentence)
        metadatas.append({
            "type": "missiongraph",
            "name": name,
            "mission": root,
            "domain": domain,
            "flight_count": len(flights)
        })

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Done! Collection has {collection.count()} missiongraphs")

    print("\n=== Test Query: 'compound intelligence' ===")
    results = collection.query(query_texts=["compound intelligence"], n_results=3)
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        print(f"  {i+1}. {meta['name']} (domain: {meta['domain']}, dist: {dist:.3f})")

    print("\n=== Test Query: 'authentication feature' ===")
    results = collection.query(query_texts=["authentication feature"], n_results=3)
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        print(f"  {i+1}. {meta['name']} (domain: {meta['domain']}, dist: {dist:.3f})")


if __name__ == "__main__":
    populate_mission_chroma()
