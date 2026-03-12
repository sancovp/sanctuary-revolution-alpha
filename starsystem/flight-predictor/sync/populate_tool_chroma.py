"""Populate tool ChromaDB from strata catalog for RAG queries."""

import json
import os
import re
from pathlib import Path

import chromadb
from chromadb.config import Settings

HEAVEN_DATA_DIR = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")


def parse_toolgraph_sentence(structured: str) -> dict:
    """
    Parse structured toolgraph syntax into components.

    Input: [TOOLGRAPH:[abort](../path)_[waypoint](../path)] [is_a](../path):[Tool](../path) ...
    Output: {"name": "abort waypoint", "is_a": "tool", "part_of": "waypoint", ...}
    """
    if not structured:
        return {}

    # Strip markdown links: [text](../path) → text
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', structured)

    # Remove [TOOLGRAPH: prefix and /TOOLGRAPH] suffix
    clean = re.sub(r'\[/?TOOLGRAPH:?\]?', '', clean)
    clean = clean.strip()

    result = {}

    # Extract the tool name (first part before is_a)
    name_match = re.match(r'^([a-z0-9_]+)', clean, re.IGNORECASE)
    if name_match:
        result["name"] = name_match.group(1).replace("_", " ").lower()

    # Extract is_a
    is_a_match = re.search(r'is_a:(\w+)', clean, re.IGNORECASE)
    if is_a_match:
        result["is_a"] = is_a_match.group(1).replace("_", " ").lower()

    # Extract part_of
    part_of_match = re.search(r'part_of:([a-z0-9_-]+)', clean, re.IGNORECASE)
    if part_of_match:
        result["part_of"] = part_of_match.group(1).replace("_", " ").replace("-", " ").lower()

    # Extract instantiates
    inst_match = re.search(r'instantiates:([a-z0-9_]+)', clean, re.IGNORECASE)
    if inst_match:
        result["instantiates"] = inst_match.group(1).replace("_", " ").lower()

    # Extract has_domain
    domain_match = re.search(r'has_domain:([a-z0-9_]+)', clean, re.IGNORECASE)
    if domain_match:
        result["domain"] = domain_match.group(1).replace("_", " ").lower()

    # Extract has_parameters
    params_match = re.search(r'has_parameters:\[([^\]]+)\]', clean, re.IGNORECASE)
    if params_match:
        params = params_match.group(1).replace("_", " ").lower()
        result["parameters"] = params

    return result


def to_natural_sentence(parsed: dict, concept_name: str) -> str:
    """
    Convert parsed components to natural language sentence.

    "the toolgraph of abort waypoint journey is a tool that is part of waypoint,
     instantiates delete pattern, has domain navigation, and has parameters starlog path"
    """
    # Use readable name from concept: Toolgraph_Abort_Waypoint → "abort waypoint"
    readable = concept_name.replace("Toolgraph_", "").replace("_", " ").lower()

    parts = [f"the toolgraph of {readable}"]

    if parsed.get("is_a"):
        parts.append(f"is a {parsed['is_a']}")

    if parsed.get("part_of"):
        parts.append(f"that is part of {parsed['part_of']}")

    if parsed.get("instantiates"):
        parts.append(f"instantiates {parsed['instantiates']}")

    if parsed.get("domain"):
        parts.append(f"has domain {parsed['domain']}")

    if parsed.get("parameters"):
        parts.append(f"and has parameters {parsed['parameters']}")

    return " ".join(parts)


def get_strata_catalog():
    """Load tool catalog from strata cache."""
    from platformdirs import user_cache_dir
    catalog_path = Path(user_cache_dir("strata")) / "tool_catalog.json"
    if not catalog_path.exists():
        return {}
    return json.loads(catalog_path.read_text())


def get_plugin_mcp_tools():
    """Scan Claude plugin settings for MCP servers and their tools."""
    claude_dir = Path.home() / ".claude"
    plugins_dir = claude_dir / "plugins"
    tools = []

    if not plugins_dir.exists():
        return tools

    # Find all settings.json in plugins
    for settings_file in plugins_dir.glob("**/settings.json"):
        try:
            data = json.loads(settings_file.read_text())
            mcp_servers = data.get("mcpServers", {})

            for server_name, server_config in mcp_servers.items():
                # Create a tool entry for the MCP server itself
                tools.append({
                    "name": f"Toolgraph_{server_name.replace('-', '_').title()}",
                    "server": server_name,
                    "domain": "plugin",
                    "source": "plugin",
                    "sentence": f"the toolgraph of {server_name} is a tool that is part of {server_name} plugin"
                })
        except (json.JSONDecodeError, IOError):
            continue

    return tools


def get_claude_config_mcp_tools():
    """Scan Claude settings for directly configured MCP servers."""
    claude_dir = Path.home() / ".claude"
    tools = []

    # Check both settings.json and settings.local.json
    for settings_name in ["settings.json", "settings.local.json"]:
        settings_file = claude_dir / settings_name
        if settings_file.exists():
            try:
                data = json.loads(settings_file.read_text())
                mcp_servers = data.get("mcpServers", {})

                for server_name, server_config in mcp_servers.items():
                    tools.append({
                        "name": f"Toolgraph_{server_name.replace('-', '_').title()}",
                        "server": server_name,
                        "domain": "claude_config",
                        "source": "claude_config",
                        "sentence": f"the toolgraph of {server_name} is a tool that is part of {server_name}"
                    })
            except (json.JSONDecodeError, IOError):
                continue

    return tools


def populate_tool_chroma():
    """Embed Toolgraph ontological sentences into ChromaDB."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password"))
    )

    client = chromadb.PersistentClient(
        path=os.path.join(HEAVEN_DATA_DIR, "tool_chroma"),
        settings=Settings(anonymized_telemetry=False)
    )

    # Get or create collection for Toolgraphs
    collection = client.get_or_create_collection(
        name="toolgraphs",
        metadata={"hnsw:space": "cosine"}
    )

    # Clear existing
    existing = collection.count()
    if existing > 0:
        print(f"Clearing {existing} existing toolgraphs")
        collection.delete(where={"type": "toolgraph"})

    # Query Neo4j for Toolgraph concepts - simple query, just get the concept and description
    ids = []
    documents = []
    metadatas = []

    with driver.session() as session:
        result = session.run("""
            MATCH (tg:Wiki)
            WHERE tg.n STARTS WITH 'Toolgraph_'
            RETURN tg.n as name, tg.d as sentence
        """)

        for rec in result:
            name = rec["name"]
            sentence = rec["sentence"] or ""

            # Parse the structured syntax into components
            parsed = parse_toolgraph_sentence(sentence)

            # Convert to natural language
            natural_sentence = to_natural_sentence(parsed, name)

            ids.append(f"toolgraph:{name}")
            documents.append(natural_sentence)
            metadatas.append({
                "type": "toolgraph",
                "name": name,
                "part_of": parsed.get("part_of", "unknown"),
                "domain": parsed.get("domain", "general"),
                "instantiates": parsed.get("instantiates", ""),
            })

    # Add tools from strata cache (covers most MCPs)
    strata_catalog = get_strata_catalog()
    strata_count = 0
    existing_names = {m["name"] for m in metadatas}
    for server_name, tools in strata_catalog.items():
        for tool in tools:
            tool_name = tool.get("name", "")
            concept_name = f"Toolgraph_{tool_name.replace('-', '_').replace(' ', '_').title()}"
            if concept_name not in existing_names:
                ids.append(f"toolgraph:{concept_name}")
                documents.append(f"the tool {tool_name} is part of {server_name}")
                metadatas.append({
                    "type": "toolgraph",
                    "name": concept_name,
                    "part_of": server_name,
                    "domain": "strata",
                })
                existing_names.add(concept_name)
                strata_count += 1
    print(f"Added {strata_count} tools from strata cache")

    # Add plugin MCP tools
    plugin_tools = get_plugin_mcp_tools()
    print(f"Found {len(plugin_tools)} plugin MCP tools")
    for tool in plugin_tools:
        if tool["name"] not in [m["name"] for m in metadatas]:  # Avoid duplicates
            ids.append(f"toolgraph:{tool['name']}")
            documents.append(tool["sentence"])
            metadatas.append({
                "type": "toolgraph",
                "name": tool["name"],
                "part_of": tool["server"],
                "domain": tool["domain"],
                "source": tool["source"],
            })

    # Add Claude config MCP tools
    config_tools = get_claude_config_mcp_tools()
    print(f"Found {len(config_tools)} Claude config MCP tools")
    for tool in config_tools:
        if tool["name"] not in [m["name"] for m in metadatas]:
            ids.append(f"toolgraph:{tool['name']}")
            documents.append(tool["sentence"])
            metadatas.append({
                "type": "toolgraph",
                "name": tool["name"],
                "part_of": tool["server"],
                "domain": tool["domain"],
                "source": tool["source"],
            })

    # Batch add
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )
        print(f"Added {min(i+batch_size, len(ids))}/{len(ids)} toolgraphs")

    driver.close()
    print(f"Done! Collection now has {collection.count()} toolgraphs")


if __name__ == "__main__":
    populate_tool_chroma()
