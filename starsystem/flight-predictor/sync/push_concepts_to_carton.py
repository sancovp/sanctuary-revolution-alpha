"""Push generated concepts to CartON via direct Neo4j (faster than MCP for bulk)."""

import json
import os
from pathlib import Path
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def push_concept(session, concept: dict):
    """Push a single concept to Neo4j with CartON structure."""
    name = concept['concept_name']
    desc = concept.get('concept', '')
    relationships = concept.get('relationships', [])

    # Create or merge the concept node
    session.run("""
        MERGE (c:Concept {name: $name})
        SET c.description = $desc,
            c.synced_at = datetime()
    """, name=name, desc=desc)

    # Create relationships
    for rel in relationships:
        rel_type = rel['relationship'].upper()
        for related in rel['related']:
            # Ensure related concept exists
            session.run("""
                MERGE (c:Concept {name: $name})
            """, name=related)

            # Create relationship
            session.run(f"""
                MATCH (a:Concept {{name: $from_name}})
                MATCH (b:Concept {{name: $to_name}})
                MERGE (a)-[:{rel_type}]->(b)
            """, from_name=name, to_name=related)


def push_all_concepts(concepts_file: str):
    """Push all concepts from JSON file to CartON."""
    concepts = json.loads(Path(concepts_file).read_text())
    driver = get_driver()

    try:
        with driver.session() as session:
            # Create indexes for performance
            session.run("CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.name)")

            total = len(concepts)
            for i, concept in enumerate(concepts):
                push_concept(session, concept)
                if (i + 1) % 100 == 0:
                    print(f"Pushed {i + 1}/{total} concepts")

            print(f"Done! Pushed {total} concepts to CartON")

            # Count results
            result = session.run("MATCH (c:Concept) RETURN count(c) as count")
            count = result.single()['count']
            print(f"Total concepts in graph: {count}")

    finally:
        driver.close()


if __name__ == "__main__":
    push_all_concepts("/tmp/rag_tool_discovery/data/tool_concepts.json")
