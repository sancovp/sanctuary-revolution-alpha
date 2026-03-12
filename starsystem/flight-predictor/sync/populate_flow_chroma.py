"""Populate Canopyflowgraph + Operadicflowgraph into ChromaDB."""

import json
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")

def populate_flow_chroma():
    concepts_path = Path("/tmp/rag_tool_discovery/data/flow_concepts.json")
    if not concepts_path.exists():
        print("Run ingest_canopy_opera_to_carton.py first")
        return

    concepts = json.loads(concepts_path.read_text())
    print(f"Found {len(concepts)} flow concepts")

    client = chromadb.PersistentClient(
        path=os.path.join(HEAVEN_DATA_DIR, "flow_chroma"),
        settings=Settings(anonymized_telemetry=False)
    )

    collection = client.get_or_create_collection(name="flowgraphs", metadata={"hnsw:space": "cosine"})

    existing = collection.count()
    if existing > 0:
        collection.delete(ids=collection.get()["ids"])

    ids, documents, metadatas = [], [], []
    for c in concepts:
        name = c['concept_name']
        flow_type = "canopy" if "Canopyflowgraph" in name else "operadic"
        ids.append(f"flowgraph:{name}")
        documents.append(c['concept'])
        metadatas.append({"type": flow_type, "name": name})

    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"Done! Collection has {collection.count()} flowgraphs")

    print("\n=== Test: 'golden workflow' ===")
    results = collection.query(query_texts=["golden workflow"], n_results=3)
    for i, doc_id in enumerate(results["ids"][0]):
        print(f"  {i+1}. {results['metadatas'][0][i]['name']} (dist: {results['distances'][0][i]:.3f})")

if __name__ == "__main__":
    populate_flow_chroma()
