"""
Ingest tools from strata catalog into CartON as fully typed concepts.

Each tool becomes a concept with:
- is_a: Tool
- part_of: <Server_Name>
- belongs_to_domain: <domain>
- has_parameter: <Param_Name> (each param is also a concept)
- has_input_schema: description of inputs
- implements: <abstract patterns extracted from description>

This creates the typed ontology that enables feature-level RAG.
"""

import json
import re
import os
from pathlib import Path
from typing import Any

# CartON MCP interaction via gnosys_kit
# For now, we'll generate the concept batch and call via MCP


def serialize_toolgraph_sentence(tool_name: str, server_name: str, domain: str, pattern: str, params: list[str]) -> str:
    """
    Serialize a tool's subgraph into an ontological sentence for embedding.

    This is NOT prose - it's typed graph structure serialized to text.
    The sentence IS the ontology, addressable and rehydratable.
    """
    parts = [
        f"[TOOLGRAPH:{tool_name}]",
        f"is_a:Tool",
        f"part_of:{server_name}",
        f"instantiates:{pattern}",
        f"has_domain:{domain}",
    ]

    if params:
        param_str = ",".join(p.replace("Param_", "") for p in params[:5])
        parts.append(f"has_parameters:[{param_str}]")

    parts.append(f"[/TOOLGRAPH]")

    return " ".join(parts)


def normalize_name(name: str) -> str:
    """Convert to CartON-style Title_Case_With_Underscores."""
    # Handle snake_case and camelCase
    s = re.sub(r'[-.]', '_', name)
    s = re.sub(r'([a-z])([A-Z])', r'\1_\2', s)
    return '_'.join(word.capitalize() for word in s.split('_') if word)


def extract_concepts_from_description(desc: str) -> list[str]:
    """Extract potential concept names from description text."""
    # Simple extraction: capitalized words, technical terms
    concepts = []
    # Find capitalized words that might be concepts
    words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', desc)
    for w in words:
        if len(w) > 2 and w not in ['The', 'This', 'That', 'When', 'What', 'How']:
            concepts.append(normalize_name(w))
    return list(set(concepts))[:5]  # Limit to 5


def extract_params_from_schema(schema: dict) -> list[dict]:
    """Extract parameter info from inputSchema."""
    params = []
    props = schema.get('properties', {})
    required = schema.get('required', [])

    for name, info in props.items():
        param = {
            'name': normalize_name(name),
            'original_name': name,
            'type': info.get('type', 'any'),
            'description': info.get('description', '')[:200],
            'required': name in required
        }
        params.append(param)

    return params


def tool_to_carton_concepts(server_name: str, tool: dict) -> list[dict]:
    """
    Convert a single tool to a list of CartON concepts.

    Returns list of concept dicts ready for add_concept calls.
    """
    concepts = []

    tool_name = tool.get('name', '')
    tool_desc = tool.get('description', '')[:1000]
    input_schema = tool.get('inputSchema', {})

    # Normalize names
    tool_concept_name = f"Tool_{normalize_name(tool_name)}"
    server_concept_name = f"MCP_{normalize_name(server_name)}"

    # Infer domain from server name
    domain = infer_domain(server_name, tool_name, tool_desc)
    domain_concept = f"Domain_{normalize_name(domain)}"

    # Extract params
    params = extract_params_from_schema(input_schema)
    param_concept_names = [f"Param_{p['name']}" for p in params]

    # Extract abstract concepts from description
    abstract_concepts = extract_concepts_from_description(tool_desc)

    # Domain concept name (will have is_a: Domain)
    domain_name = normalize_name(domain)

    # Infer pattern from description (instantiates)
    pattern = infer_pattern(tool_name, tool_desc)

    # 1. Create the main tool concept with full UARL (4 dimensions)
    tool_relationships = [
        # is_a: category/type (taxonomy)
        {"relationship": "is_a", "related": ["Tool"]},
        # part_of: container (mereology)
        {"relationship": "part_of", "related": [server_concept_name]},
        # instantiates: pattern realization
        {"relationship": "instantiates", "related": [pattern]},
        # has_*: structure
        {"relationship": "has_domain", "related": [domain_name]},
    ]

    if param_concept_names:
        tool_relationships.append({
            "relationship": "has_parameter",
            "related": param_concept_names
        })

    # has_input_schema from the schema itself
    if input_schema:
        tool_relationships.append({
            "relationship": "has_input_schema",
            "related": [f"Schema_{tool_concept_name}"]
        })

    # has_assumption: what the tool assumes
    tool_relationships.append({
        "relationship": "has_assumption",
        "related": [f"Assumption_{normalize_name(server_name)}_Available"]
    })

    concepts.append({
        "concept_name": tool_concept_name,
        "concept": f"Tool: {tool_name}\nServer: {server_name}\n\n{tool_desc}",
        "relationships": tool_relationships
    })

    # 1b. Create the Toolgraph meta-concept
    # This represents "the semantic graph of this tool exists and is addressable"
    toolgraph_name = f"Toolgraph_{normalize_name(tool_name)}"

    # Collect all nodes in this tool's subgraph
    subgraph_nodes = [tool_concept_name, server_concept_name, domain_name, pattern]
    subgraph_nodes.extend(param_concept_names)
    subgraph_nodes.append(f"Assumption_{normalize_name(server_name)}_Available")
    if input_schema:
        subgraph_nodes.append(f"Schema_{tool_concept_name}")

    toolgraph_relationships = [
        {"relationship": "is_a", "related": ["Toolgraph"]},
        {"relationship": "part_of", "related": ["Toolgraph_Registry"]},
        {"relationship": "instantiates", "related": ["Semantic_Graph_Pattern"]},
        {"relationship": "has_root", "related": [tool_concept_name]},
        {"relationship": "has_node", "related": subgraph_nodes},
        {"relationship": "has_domain", "related": [domain_name]},
        {"relationship": "has_pattern", "related": [pattern]},
    ]

    concepts.append({
        "concept_name": toolgraph_name,
        "concept": serialize_toolgraph_sentence(tool_name, server_name, domain_name, pattern, param_concept_names),
        "relationships": toolgraph_relationships
    })

    # 2. Create parameter concepts
    for param in params:
        param_concept_name = f"Param_{param['name']}"
        param_type_concept = f"Type_{normalize_name(param['type'])}"

        param_relationships = [
            {"relationship": "is_a", "related": ["Parameter"]},
            {"relationship": "has_type", "related": [param_type_concept]},
            {"relationship": "parameter_of", "related": [tool_concept_name]},
        ]

        concepts.append({
            "concept_name": param_concept_name,
            "concept": f"Parameter: {param['original_name']}\nType: {param['type']}\nRequired: {param['required']}\n\n{param['description']}",
            "relationships": param_relationships
        })

    # 3. Ensure server concept exists
    concepts.append({
        "concept_name": server_concept_name,
        "concept": f"MCP Server: {server_name}",
        "relationships": [
            {"relationship": "is_a", "related": ["MCP_Server"]},
            {"relationship": "has_domain", "related": [domain_name]}
        ]
    })

    # 4. Ensure domain concept exists
    concepts.append({
        "concept_name": domain_name,
        "concept": f"Domain: {domain}",
        "relationships": [
            {"relationship": "is_a", "related": ["Domain"]}
        ]
    })

    return concepts


def infer_pattern(tool_name: str, description: str) -> str:
    """Infer what pattern this tool instantiates from its name/description."""
    text = f"{tool_name} {description}".lower()

    patterns = {
        "Query_Pattern": ["query", "search", "find", "get", "list", "fetch", "retrieve"],
        "Create_Pattern": ["create", "add", "insert", "new", "generate", "make"],
        "Update_Pattern": ["update", "edit", "modify", "change", "set"],
        "Delete_Pattern": ["delete", "remove", "clear", "drop"],
        "Execute_Pattern": ["run", "execute", "invoke", "call", "trigger"],
        "Navigate_Pattern": ["navigate", "jump", "go", "move", "traverse"],
        "Transform_Pattern": ["transform", "convert", "parse", "format", "process"],
        "Connect_Pattern": ["connect", "establish", "init", "start", "open"],
        "Disconnect_Pattern": ["disconnect", "close", "end", "stop", "terminate"],
        "Validate_Pattern": ["validate", "check", "verify", "test", "assert"],
    }

    for pattern, keywords in patterns.items():
        if any(kw in text for kw in keywords):
            return pattern

    return "Generic_Tool_Pattern"


def infer_domain(server_name: str, tool_name: str, description: str) -> str:
    """Infer domain from server/tool/description."""
    text = f"{server_name} {tool_name} {description}".lower()

    patterns = {
        "navigation": ["starlog", "starship", "waypoint", "course", "flight", "session", "journey"],
        "knowledge_graph": ["carton", "concept", "graph", "knowledge", "ontology", "relationship"],
        "mcp_development": ["mcpify", "mcp", "protocol", "server development"],
        "orchestration": ["gnosys", "strata", "orchestrate", "manage servers"],
        "reasoning": ["sophia", "hyperon", "reason", "wisdom", "rule", "atom"],
        "skill_management": ["skill", "equip", "skillset", "persona"],
        "code_analysis": ["parse", "dependency", "codebase", "repository", "analyze"],
    }

    for domain, keywords in patterns.items():
        if any(kw in text for kw in keywords):
            return domain

    return "general"


def load_strata_catalog() -> dict:
    """Load tool catalog from strata cache."""
    from platformdirs import user_cache_dir
    catalog_path = Path(user_cache_dir("strata")) / "tool_catalog.json"
    if not catalog_path.exists():
        return {}
    return json.loads(catalog_path.read_text())


def generate_all_tool_concepts() -> list[dict]:
    """Generate CartON concepts for all tools in strata catalog."""
    catalog = load_strata_catalog()
    all_concepts = []

    for server_name, tools in catalog.items():
        for tool in tools:
            concepts = tool_to_carton_concepts(server_name, tool)
            all_concepts.extend(concepts)

    # Deduplicate by concept_name (keep first occurrence)
    seen = set()
    unique_concepts = []
    for c in all_concepts:
        if c['concept_name'] not in seen:
            seen.add(c['concept_name'])
            unique_concepts.append(c)

    return unique_concepts


if __name__ == "__main__":
    concepts = generate_all_tool_concepts()
    print(f"Generated {len(concepts)} concepts from tools")

    # Save to file for inspection
    output_path = Path("/tmp/rag_tool_discovery/data/tool_concepts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(concepts, indent=2))
    print(f"Saved to {output_path}")

    # Show sample
    print("\n=== Sample concepts ===")
    for c in concepts[:3]:
        print(f"\n{c['concept_name']}:")
        print(f"  relationships: {[r['relationship'] for r in c['relationships']]}")
