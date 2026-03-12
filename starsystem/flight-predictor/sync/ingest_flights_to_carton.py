"""
Ingest flight configs into CartON as Flightgraph concepts.

Flight configs are JSON files with:
- domain, version, description
- root_files[] = steps with sequence_number, title, content, dependencies
- entry_point

Each flight becomes concepts with full UARL:
- is_a: Flight
- part_of: <Domain>_Flights or Flight_Catalog
- instantiates: <Pattern>
- has_domain, has_step, has_dependency
- has_capability_slot: [extracted from step content]

Plus a Flightgraph meta-concept for RAG embedding.
"""

import json
import os
import re
from pathlib import Path


FLIGHT_CONFIGS_DIRS = [
    Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "starship" / "flight_configs",
    Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "default_flight_configs",
]


def normalize_name(name: str) -> str:
    """Convert to CartON-style Title_Case_With_Underscores."""
    s = re.sub(r'[-.]', '_', name)
    s = re.sub(r'([a-z])([A-Z])', r'\\1_\\2', s)
    return '_'.join(word.capitalize() for word in s.split('_') if word)


def extract_capability_slots(content: str) -> list[dict]:
    """
    Extract capability references from step content.

    Looks for:
    - MCP tool calls: gnosys_kit, mcp__, .exec {
    - Skill references: equip, skill names
    - Tool patterns: @mcp.tool, starlog., starship.
    """
    slots = []

    # MCP tool patterns
    mcp_patterns = [
        r'gnosys_kit\s*[→.]\s*(\w+)',  # gnosys_kit → action or gnosys_kit.action
        r'mcp__(\w+)__(\w+)',  # mcp__server__tool
        r'(\w+)\.exec\s*\{',  # action.exec {
        r'(starlog|starship|waypoint)\.(\w+)',  # starlog.orient
    ]

    for pattern in mcp_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, tuple):
                slot_name = '_'.join(match)
            else:
                slot_name = match
            slots.append({
                "type": "tool",
                "name": normalize_name(slot_name),
                "raw": slot_name
            })

    # Skill patterns
    skill_patterns = [
        r'equip\s*["\']([^"\']+)["\']',  # equip "skill-name"
        r'skill[:\s]+["\']?([a-z][a-z0-9_-]+)["\']?',  # skill: name or skill "name"
    ]

    for pattern in skill_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            slots.append({
                "type": "skill",
                "name": f"Skill_{normalize_name(match)}",
                "raw": match
            })

    # Deduplicate by name
    seen = set()
    unique = []
    for slot in slots:
        if slot["name"] not in seen:
            seen.add(slot["name"])
            unique.append(slot)

    return unique


def serialize_flightgraph_sentence(
    flight_name: str,
    domain: str,
    description: str,
    steps: list[dict],
    capability_slots: list[str]
) -> str:
    """
    Serialize a flight's subgraph into an ontological sentence for embedding.
    """
    parts = [
        f"[FLIGHTGRAPH:{flight_name}]",
        f"is_a:Flight",
        f"instantiates:Procedure_Pattern",
        f"has_domain:{domain}",
    ]

    if description:
        # Truncate for embedding
        desc_clean = description[:100].replace('\n', ' ')
        parts.append(f"what:{desc_clean}")

    if steps:
        step_names = [s.get("title", f"Step_{s.get('sequence_number', 0)}") for s in steps[:5]]
        step_str = ",".join(normalize_name(s) for s in step_names)
        parts.append(f"has_steps:[{step_str}]")

    if capability_slots:
        slot_str = ",".join(capability_slots[:8])
        parts.append(f"has_capability_slots:[{slot_str}]")

    parts.append(f"[/FLIGHTGRAPH]")

    return " ".join(parts)


def load_flight_config(config_path: Path) -> dict | None:
    """Load flight config from JSON file."""
    try:
        data = json.loads(config_path.read_text())
        # Extract name from filename
        name = config_path.stem
        if name.endswith('_pd'):
            name = name[:-3]  # Remove _pd suffix
        data['config_name'] = name
        data['config_path'] = str(config_path)
        return data
    except Exception as e:
        print(f"Error loading {config_path}: {e}")
        return None


def flight_to_carton_concepts(flight: dict) -> list[dict]:
    """Convert a flight config to CartON concepts."""
    concepts = []

    name = flight.get('config_name', 'unknown')
    domain = flight.get('domain', 'unknown')
    description = flight.get('description', '')
    version = flight.get('version', '1.0.0')
    steps = flight.get('root_files', [])
    entry_point = flight.get('entry_point', '')

    # Normalize names
    flight_concept_name = f"Flight_{normalize_name(name)}"
    domain_name = normalize_name(domain) if domain else "General"

    # Extract all capability slots from all steps
    all_slots = []
    step_concepts = []

    for step in steps:
        title = step.get('title') or f"Step_{step.get('sequence_number', 0)}"
        step_name = f"Step_{normalize_name(title)}"
        step_concepts.append(step_name)

        content = step.get('content', '')
        slots = extract_capability_slots(content)
        all_slots.extend(slots)

    # Deduplicate slots
    slot_names = list(set(s['name'] for s in all_slots))

    # 1. Main flight concept with full UARL
    flight_relationships = [
        {"relationship": "is_a", "related": ["Flight"]},
        {"relationship": "part_of", "related": ["Flight_Catalog"]},
        {"relationship": "instantiates", "related": ["Procedure_Pattern"]},
        {"relationship": "has_domain", "related": [domain_name]},
    ]

    if step_concepts:
        flight_relationships.append({"relationship": "has_step", "related": step_concepts})

    if slot_names:
        # Map to Toolgraph/Skillgraph references
        capability_refs = []
        for slot in all_slots:
            if slot['type'] == 'tool':
                capability_refs.append(f"Toolgraph_{slot['name']}")
            else:
                capability_refs.append(f"Skillgraph_{slot['name']}")
        capability_refs = list(set(capability_refs))
        flight_relationships.append({"relationship": "has_capability_slot", "related": capability_refs})

    concepts.append({
        "concept_name": flight_concept_name,
        "concept": f"Flight: {name}\nDomain: {domain}\nDescription: {description}\nSteps: {len(steps)}",
        "relationships": flight_relationships
    })

    # 2. Flightgraph meta-concept
    flightgraph_name = f"Flightgraph_{normalize_name(name)}"

    subgraph_nodes = [flight_concept_name, domain_name]
    subgraph_nodes.extend(step_concepts[:10])
    subgraph_nodes.extend(slot_names[:10])

    flightgraph_relationships = [
        {"relationship": "is_a", "related": ["Flightgraph"]},
        {"relationship": "part_of", "related": ["Flightgraph_Registry"]},
        {"relationship": "instantiates", "related": ["Semantic_Graph_Pattern"]},
        {"relationship": "has_root", "related": [flight_concept_name]},
        {"relationship": "has_node", "related": subgraph_nodes},
        {"relationship": "has_domain", "related": [domain_name]},
    ]

    concepts.append({
        "concept_name": flightgraph_name,
        "concept": serialize_flightgraph_sentence(name, domain_name, description, steps, slot_names),
        "relationships": flightgraph_relationships
    })

    # 3. Step concepts
    for step in steps:
        seq = step.get('sequence_number', 0)
        title = step.get('title', f'Step {seq}')
        step_name = f"Step_{normalize_name(title)}"
        deps = step.get('dependencies', [])

        step_rels = [
            {"relationship": "is_a", "related": ["Flight_Step"]},
            {"relationship": "part_of", "related": [flight_concept_name]},
            {"relationship": "has_sequence", "related": [f"Sequence_{seq}"]},
        ]

        if deps:
            dep_refs = [f"Step_{normalize_name(steps[d-1].get('title', f'Step_{d}'))}"
                       for d in deps if d <= len(steps)]
            if dep_refs:
                step_rels.append({"relationship": "depends_on", "related": dep_refs})

        concepts.append({
            "concept_name": step_name,
            "concept": f"Flight Step: {title}\nSequence: {seq}\nPart of: {name}",
            "relationships": step_rels
        })

    # 4. Domain concept
    concepts.append({
        "concept_name": domain_name,
        "concept": f"Domain: {domain}",
        "relationships": [{"relationship": "is_a", "related": ["Domain"]}]
    })

    return concepts


def scan_flight_configs() -> list[dict]:
    """Scan all flight config directories for JSON files."""
    configs = []

    for base_dir in FLIGHT_CONFIGS_DIRS:
        if not base_dir.exists():
            continue

        # Scan recursively for JSON files
        for json_file in base_dir.rglob("*.json"):
            config = load_flight_config(json_file)
            if config:
                configs.append(config)

    return configs


def generate_all_flight_concepts() -> list[dict]:
    """Generate CartON concepts for all flight configs."""
    all_concepts = []

    configs = scan_flight_configs()
    print(f"Found {len(configs)} flight configs")

    for config in configs:
        concepts = flight_to_carton_concepts(config)
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
    concepts = generate_all_flight_concepts()
    print(f"Generated {len(concepts)} concepts from flights")

    output_path = Path("/tmp/rag_tool_discovery/data/flight_concepts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(concepts, indent=2))
    print(f"Saved to {output_path}")

    # Show sample Flightgraph
    print("\n=== Sample Flightgraph ===")
    for c in concepts:
        if c['concept_name'].startswith('Flightgraph_'):
            print(f"\n{c['concept_name']}:")
            print(f"  sentence: {c['concept'][:200]}...")
            break

    # Show capability slots found
    print("\n=== Capability Slots Found ===")
    slot_count = 0
    for c in concepts:
        for rel in c.get('relationships', []):
            if rel['relationship'] == 'has_capability_slot':
                slot_count += len(rel['related'])
                print(f"  {c['concept_name']}: {rel['related'][:5]}")
    print(f"\nTotal capability slot references: {slot_count}")
