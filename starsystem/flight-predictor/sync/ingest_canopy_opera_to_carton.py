"""
Ingest Canopy and Opera flows into CartON as *flowgraph concepts.

CanopyFlowPatterns (quarantine) → Canopyflowgraph
OperadicFlows (golden) → Operadicflowgraph

Both have:
- pattern_id/operadic_flow_id, name, description
- sequence[] of steps with item_type (AI/Human/AI+Human)
- status (quarantine vs golden)
"""

import json
import os
import re
from pathlib import Path

REGISTRY_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "registry"


def normalize_name(name: str) -> str:
    """Convert to CartON-style Title_Case_With_Underscores."""
    s = re.sub(r'[-.]', '_', name)
    s = re.sub(r'([a-z])([A-Z])', r'\\1_\\2', s)
    return '_'.join(word.capitalize() for word in s.split('_') if word)


def serialize_flowgraph_sentence(
    flow_id: str, flow_type: str, name: str, description: str,
    sequence: list[dict], status: str
) -> str:
    """Serialize a flow into an ontological sentence for embedding."""
    parts = [
        f"[{flow_type.upper()}:{flow_id}]",
        f"is_a:{flow_type}",
        f"instantiates:Workflow_Pattern",
        f"has_status:{status}",
    ]

    if description:
        parts.append(f"what:{description[:80].replace(chr(10), ' ')}")

    # Extract step types
    step_types = [s.get('item_type', 'Unknown') for s in sequence]
    if step_types:
        parts.append(f"has_steps:[{','.join(step_types[:5])}]")

    # Execution types
    exec_types = list(set(s.get('execution_type', '') for s in sequence if s.get('execution_type')))
    if exec_types:
        parts.append(f"execution_types:[{','.join(exec_types[:3])}]")

    parts.append(f"[/{flow_type.upper()}]")
    return " ".join(parts)


def ingest_canopy_patterns() -> list[dict]:
    """Ingest CanopyFlowPatterns (quarantine) as Canopyflowgraph concepts."""
    concepts = []
    registry_path = REGISTRY_DIR / "opera_canopy_patterns_registry.json"

    if not registry_path.exists():
        print(f"Canopy patterns registry not found: {registry_path}")
        return []

    patterns = json.loads(registry_path.read_text())
    print(f"Found {len(patterns)} canopy patterns")

    for pattern_id, pattern in patterns.items():
        name = pattern.get('name', pattern_id)
        description = pattern.get('description', '')
        sequence = pattern.get('sequence', [])
        status = pattern.get('status', 'quarantine')

        concept_name = f"Canopyflowgraph_{normalize_name(pattern_id)}"

        relationships = [
            {"relationship": "is_a", "related": ["Canopyflowgraph"]},
            {"relationship": "part_of", "related": ["Canopyflowgraph_Registry"]},
            {"relationship": "instantiates", "related": ["Workflow_Pattern"]},
            {"relationship": "has_status", "related": [f"Status_{normalize_name(status)}"]},
        ]

        concepts.append({
            "concept_name": concept_name,
            "concept": serialize_flowgraph_sentence(
                pattern_id, "Canopyflowgraph", name, description, sequence, status
            ),
            "relationships": relationships
        })

    return concepts


def ingest_operadic_flows() -> list[dict]:
    """Ingest OperadicFlows (golden) as Operadicflowgraph concepts."""
    concepts = []
    registry_path = REGISTRY_DIR / "opera_operadic_flows_registry.json"

    if not registry_path.exists():
        print(f"Operadic flows registry not found: {registry_path}")
        return []

    flows = json.loads(registry_path.read_text())
    print(f"Found {len(flows)} operadic flows")

    for flow_id, flow in flows.items():
        name = flow.get('name', flow_id)
        description = flow.get('description', '')
        sequence = flow.get('sequence', [])
        status = flow.get('status', 'golden')
        verified_by = flow.get('verified_by', '')

        concept_name = f"Operadicflowgraph_{normalize_name(flow_id)}"

        relationships = [
            {"relationship": "is_a", "related": ["Operadicflowgraph"]},
            {"relationship": "part_of", "related": ["Operadicflowgraph_Registry"]},
            {"relationship": "instantiates", "related": ["Golden_Workflow_Pattern"]},
            {"relationship": "has_status", "related": ["Status_Golden"]},
        ]

        if verified_by:
            relationships.append({"relationship": "verified_by", "related": [f"Verifier_{normalize_name(verified_by)}"]})

        # Link to original canopy pattern if promoted
        original_id = flow.get('original_pattern_id') or flow.get('pattern_id')
        if original_id:
            relationships.append({"relationship": "promoted_from", "related": [f"Canopyflowgraph_{normalize_name(original_id)}"]})

        concepts.append({
            "concept_name": concept_name,
            "concept": serialize_flowgraph_sentence(
                flow_id, "Operadicflowgraph", name, description, sequence, status
            ),
            "relationships": relationships
        })

    return concepts


def generate_all_flow_concepts() -> list[dict]:
    """Generate CartON concepts for all canopy/operadic flows."""
    all_concepts = []

    all_concepts.extend(ingest_canopy_patterns())
    all_concepts.extend(ingest_operadic_flows())

    # Deduplicate
    seen = set()
    unique = []
    for c in all_concepts:
        if c['concept_name'] not in seen:
            seen.add(c['concept_name'])
            unique.append(c)

    return unique


if __name__ == "__main__":
    concepts = generate_all_flow_concepts()
    print(f"Generated {len(concepts)} concepts from canopy/operadic flows")

    output_path = Path("/tmp/rag_tool_discovery/data/flow_concepts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(concepts, indent=2))
    print(f"Saved to {output_path}")

    print("\n=== Sample Concepts ===")
    for c in concepts[:3]:
        print(f"\n{c['concept_name']}:")
        print(f"  sentence: {c['concept'][:150]}...")
