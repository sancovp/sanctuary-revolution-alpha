"""Populate skill ChromaDB from generated Skillgraph concepts for RAG queries."""

import json
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def populate_skill_chroma():
    """Embed Skillgraph ontological sentences into ChromaDB."""

    # Load skill concepts
    concepts_path = Path("/tmp/rag_tool_discovery/data/skill_concepts.json")
    if not concepts_path.exists():
        print(f"Skill concepts not found at {concepts_path}")
        print("Run ingest_skills_to_carton.py first")
        return

    concepts = json.loads(concepts_path.read_text())

    # Filter for Skillgraph concepts only
    skillgraphs = [c for c in concepts if c['concept_name'].startswith('Skillgraph_')]
    print(f"Found {len(skillgraphs)} Skillgraph concepts")

    client = chromadb.PersistentClient(
        path=os.path.join(HEAVEN_DATA_DIR, "skill_chroma"),
        settings=Settings(anonymized_telemetry=False)
    )

    # Get or create collection for Skillgraphs
    collection = client.get_or_create_collection(
        name="skillgraphs",
        metadata={"hnsw:space": "cosine"}
    )

    # Clear existing
    existing = collection.count()
    if existing > 0:
        print(f"Clearing {existing} existing skillgraphs")
        # Delete all by getting all IDs
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

    # Prepare data
    ids = []
    documents = []
    metadatas = []

    for sg in skillgraphs:
        name = sg['concept_name']
        sentence = sg['concept']  # The ontological sentence IS the embedding

        # Extract metadata from relationships
        rels = {r['relationship']: r['related'] for r in sg.get('relationships', [])}

        domain = rels.get('has_domain', ['unknown'])[0]
        pattern = rels.get('has_pattern', ['Generic_Skill_Pattern'])[0]
        category = rels.get('has_category', [''])[0] if rels.get('has_category') else ''
        root = rels.get('has_root', [''])[0] if rels.get('has_root') else ''

        ids.append(f"skillgraph:{name}")
        documents.append(sentence)
        metadatas.append({
            "type": "skillgraph",
            "name": name,
            "skill": root,
            "domain": domain,
            "pattern": pattern,
            "category": category
        })

    # Batch add
    batch_size = 50
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )
        print(f"Added {min(i+batch_size, len(ids))}/{len(ids)} skillgraphs")

    print(f"Done! Collection now has {collection.count()} skillgraphs")

    # Test query
    print("\n=== Test Query: 'build MCP server' ===")
    results = collection.query(
        query_texts=["build MCP server"],
        n_results=3
    )
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        print(f"  {i+1}. {meta['name']} (domain: {meta['domain']}, dist: {dist:.3f})")


if __name__ == "__main__":
    populate_skill_chroma()
