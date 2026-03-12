"""
Ingest missions into CartON as Missiongraph concepts.

Missions are JSON files with:
- mission_id, name, description
- domain, subdomain
- session_sequence[] = list of {project_path, flight_config, status}
- metrics

Each mission becomes concepts with full UARL:
- is_a: Mission
- part_of: Mission_Catalog
- has_domain, has_subdomain
- has_flight: [Flightgraph refs from session_sequence]
- has_project: [project paths]

Plus a Missiongraph meta-concept for RAG embedding.
"""

import json
import os
import re
from pathlib import Path


MISSIONS_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "missions"


def normalize_name(name: str) -> str:
    """Convert to CartON-style Title_Case_With_Underscores."""
    s = re.sub(r'[-.]', '_', name)
    s = re.sub(r'([a-z])([A-Z])', r'\\1_\\2', s)
    return '_'.join(word.capitalize() for word in s.split('_') if word)


def serialize_missiongraph_sentence(
    mission_name: str,
    domain: str,
    subdomain: str,
    description: str,
    flights: list[str],
    projects: list[str],
    session_count: int
) -> str:
    """Serialize a mission's subgraph into an ontological sentence for embedding."""
    parts = [
        f"[MISSIONGRAPH:{mission_name}]",
        f"is_a:Mission",
        f"instantiates:Multi_Session_Pattern",
        f"has_domain:{domain}",
    ]

    if subdomain:
        parts.append(f"has_subdomain:{subdomain}")

    if description:
        desc_clean = description[:100].replace('\n', ' ')
        parts.append(f"what:{desc_clean}")

    if flights:
        flight_str = ",".join(flights[:5])
        parts.append(f"has_flights:[{flight_str}]")

    if projects:
        proj_str = ",".join(normalize_name(p.split('/')[-1]) for p in projects[:3])
        parts.append(f"has_projects:[{proj_str}]")

    parts.append(f"session_count:{session_count}")
    parts.append(f"[/MISSIONGRAPH]")

    return " ".join(parts)


def load_mission(mission_path: Path) -> dict | None:
    """Load mission from JSON file."""
    try:
        return json.loads(mission_path.read_text())
    except Exception as e:
        print(f"Error loading {mission_path}: {e}")
        return None


def mission_to_carton_concepts(mission: dict) -> list[dict]:
    """Convert a mission to CartON concepts."""
    concepts = []

    mission_id = mission.get('mission_id', 'unknown')
    name = mission.get('name', mission_id)
    description = mission.get('description', '')
    domain = mission.get('domain', 'unknown')
    subdomain = mission.get('subdomain', '')
    sessions = mission.get('session_sequence', [])
    status = mission.get('status', 'pending')

    # Normalize names
    mission_concept_name = f"Mission_{normalize_name(mission_id)}"
    domain_name = normalize_name(domain) if domain else "General"
    subdomain_name = normalize_name(subdomain) if subdomain else None

    # Extract flights and projects from session_sequence
    flights = []
    projects = []
    for sess in sessions:
        fc = sess.get('flight_config', '')
        if fc:
            flight_name = normalize_name(fc.replace('.json', '').replace('_flight_config', ''))
            flights.append(f"Flightgraph_{flight_name}")

        proj = sess.get('project_path', '')
        if proj and proj not in projects:
            projects.append(proj)

    # 1. Main mission concept with full UARL
    mission_relationships = [
        {"relationship": "is_a", "related": ["Mission"]},
        {"relationship": "part_of", "related": ["Mission_Catalog"]},
        {"relationship": "instantiates", "related": ["Multi_Session_Pattern"]},
        {"relationship": "has_domain", "related": [domain_name]},
        {"relationship": "has_status", "related": [f"Status_{normalize_name(status)}"]},
    ]

    if subdomain_name:
        mission_relationships.append({"relationship": "has_subdomain", "related": [subdomain_name]})

    if flights:
        mission_relationships.append({"relationship": "has_flight", "related": list(set(flights))})

    if projects:
        proj_concepts = [f"Project_{normalize_name(p.split('/')[-1])}" for p in projects]
        mission_relationships.append({"relationship": "has_project", "related": proj_concepts})

    concepts.append({
        "concept_name": mission_concept_name,
        "concept": f"Mission: {name}\nDomain: {domain}\nDescription: {description[:200]}\nSessions: {len(sessions)}",
        "relationships": mission_relationships
    })

    # 2. Missiongraph meta-concept
    missiongraph_name = f"Missiongraph_{normalize_name(mission_id)}"

    subgraph_nodes = [mission_concept_name, domain_name]
    subgraph_nodes.extend(list(set(flights))[:10])

    missiongraph_relationships = [
        {"relationship": "is_a", "related": ["Missiongraph"]},
        {"relationship": "part_of", "related": ["Missiongraph_Registry"]},
        {"relationship": "instantiates", "related": ["Semantic_Graph_Pattern"]},
        {"relationship": "has_root", "related": [mission_concept_name]},
        {"relationship": "has_node", "related": subgraph_nodes},
        {"relationship": "has_domain", "related": [domain_name]},
    ]

    concepts.append({
        "concept_name": missiongraph_name,
        "concept": serialize_missiongraph_sentence(
            mission_id, domain_name, subdomain_name or "", description,
            list(set(flights)), projects, len(sessions)
        ),
        "relationships": missiongraph_relationships
    })

    # 3. Domain concept
    concepts.append({
        "concept_name": domain_name,
        "concept": f"Domain: {domain}",
        "relationships": [{"relationship": "is_a", "related": ["Domain"]}]
    })

    return concepts


def generate_all_mission_concepts() -> list[dict]:
    """Generate CartON concepts for all missions."""
    all_concepts = []

    if not MISSIONS_DIR.exists():
        print(f"Missions directory not found: {MISSIONS_DIR}")
        return []

    mission_files = list(MISSIONS_DIR.glob("*.json"))
    print(f"Found {len(mission_files)} mission files")

    for mission_path in mission_files:
        mission = load_mission(mission_path)
        if mission:
            concepts = mission_to_carton_concepts(mission)
            all_concepts.extend(concepts)

    # Deduplicate
    seen = set()
    unique = []
    for c in all_concepts:
        if c['concept_name'] not in seen:
            seen.add(c['concept_name'])
            unique.append(c)

    return unique


if __name__ == "__main__":
    concepts = generate_all_mission_concepts()
    print(f"Generated {len(concepts)} concepts from missions")

    output_path = Path("/tmp/rag_tool_discovery/data/mission_concepts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(concepts, indent=2))
    print(f"Saved to {output_path}")

    # Show sample Missiongraph
    print("\n=== Sample Missiongraph ===")
    for c in concepts:
        if c['concept_name'].startswith('Missiongraph_') and 'compound' in c['concept_name'].lower():
            print(f"\n{c['concept_name']}:")
            print(f"  sentence: {c['concept'][:200]}...")
            break

    # Show flight references
    print("\n=== Flight References Found ===")
    flight_refs = set()
    for c in concepts:
        for rel in c.get('relationships', []):
            if rel['relationship'] == 'has_flight':
                flight_refs.update(rel['related'])
    print(f"  Total unique flight refs: {len(flight_refs)}")
    for f in list(flight_refs)[:10]:
        print(f"    - {f}")
