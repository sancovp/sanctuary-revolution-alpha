"""
Sync tools from gnosys_strata catalog to Neo4j with graph relationships.

Schema:
- :Tool nodes with properties: name, description, server
- :ToolServer nodes with properties: name
- :ToolDomain nodes with properties: name
- Relationships:
  - (:Tool)-[:PART_OF]->(:ToolServer)
  - (:ToolServer)-[:BELONGS_TO]->(:ToolDomain)
  - (:Tool)-[:BELONGS_TO]->(:ToolDomain)  # Direct domain relationship

Domain inference is based on server name patterns and tool description analysis.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# Neo4j configuration - uses host.docker.internal for Docker compatibility
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


# Domain inference patterns - maps server names and keywords to domains
# Order matters - more specific patterns should be checked first via keyword matching
DOMAIN_PATTERNS = {
    "code_analysis": {
        "servers": [],  # context-alignment handled via keywords
        "keywords": ["parse", "dependency", "codebase", "repository", "analyze"]
    },
    "knowledge_graph": {
        "servers": ["carton", "context-alignment"],
        "keywords": ["concept", "graph", "knowledge", "ontology", "relationship"]
    },
    "navigation": {
        "servers": ["starlog", "starship", "waypoint", "STARSYSTEM"],
        "keywords": ["navigate", "course", "flight", "session", "journey", "mission"]
    },
    "mcp_development": {
        "servers": ["mcpify"],
        "keywords": ["mcp", "protocol", "server", "api"]
    },
    "conversation": {
        "servers": ["conversation-ingestion"],
        "keywords": ["conversation", "pair", "tag", "publish"]
    },
    "reasoning": {
        "servers": ["SOPHIA_SDNA_Router", "llm2hyperon"],
        "keywords": ["reason", "wisdom", "construct", "rule", "atom"]
    },
    "skill_management": {
        "servers": ["skill_manager_treeshell"],
        "keywords": ["skill", "equip", "skillset", "persona"]
    },
    "orchestration": {
        "servers": ["gnosys_kit", "autopoiesis"],
        "keywords": ["orchestrate", "server", "action", "execute", "manage"]
    }
}


def get_neo4j_driver():
    """Get Neo4j driver instance."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def infer_domain(server_name: str, tool_name: str, description: str) -> str:
    """
    Infer domain from server name, tool name, and description.

    Uses pattern matching to categorize tools into domains.
    Checks keywords first (more specific), then server name (fallback).
    """
    text = f"{server_name} {tool_name} {description}".lower()

    # Check keyword-based domain assignment first (more specific)
    for domain, patterns in DOMAIN_PATTERNS.items():
        for keyword in patterns["keywords"]:
            if keyword in text:
                return domain

    # Fall back to server-based domain assignment
    for domain, patterns in DOMAIN_PATTERNS.items():
        if server_name in patterns["servers"]:
            return domain

    return "general"


def create_tool_schema(driver) -> dict:
    """
    Create the tool graph schema with constraints and indexes.

    Returns:
        dict: Schema creation results
    """
    queries = [
        # Constraints for uniqueness (tool name + server combo must be unique)
        "CREATE CONSTRAINT tool_name_server IF NOT EXISTS FOR (t:Tool) REQUIRE (t.name, t.server) IS UNIQUE",
        "CREATE CONSTRAINT tool_server_name IF NOT EXISTS FOR (ts:ToolServer) REQUIRE ts.name IS UNIQUE",
        "CREATE CONSTRAINT tool_domain_name IF NOT EXISTS FOR (d:ToolDomain) REQUIRE d.name IS UNIQUE",

        # Indexes for faster lookups
        "CREATE INDEX tool_name_idx IF NOT EXISTS FOR (t:Tool) ON (t.name)",
        "CREATE INDEX tool_server_idx IF NOT EXISTS FOR (t:Tool) ON (t.server)",
        "CREATE INDEX tool_domain_idx IF NOT EXISTS FOR (t:Tool) ON (t.domain)",
    ]

    results = []
    with driver.session() as session:
        for query in queries:
            try:
                session.run(query)
                results.append({"query": query, "status": "success"})
            except Exception as e:
                results.append({"query": query, "status": "error", "error": str(e)})

    return {"schema_created": True, "results": results}


def sync_tool_to_neo4j(driver, tool_data: dict) -> dict:
    """
    Sync a single tool to Neo4j.

    Args:
        driver: Neo4j driver
        tool_data: Tool data dict with keys: name, description, server, domain

    Returns:
        dict: Sync result
    """
    query = """
    MERGE (t:Tool {name: $name, server: $server})
    SET t.description = $description,
        t.domain = $domain,
        t.synced_at = datetime()

    // Ensure server node exists and link tool to it
    MERGE (ts:ToolServer {name: $server})
    MERGE (t)-[:PART_OF]->(ts)

    // Ensure domain node exists and link tool to it
    MERGE (d:ToolDomain {name: $domain})
    MERGE (t)-[:BELONGS_TO]->(d)
    MERGE (ts)-[:BELONGS_TO]->(d)

    RETURN t.name as tool_name, ts.name as server_name, d.name as domain_name
    """

    with driver.session() as session:
        result = session.run(query, **tool_data)
        record = result.single()
        return {
            "tool": record["tool_name"],
            "server": record["server_name"],
            "domain": record["domain_name"],
            "status": "synced"
        }


def load_tools_from_catalog(catalog_path: Optional[str] = None) -> list:
    """
    Load all tools from the strata tool catalog.

    Args:
        catalog_path: Path to catalog file. If None, uses default ~/.cache/strata/tool_catalog.json

    Returns:
        list: List of tool data dicts
    """
    if catalog_path is None:
        from platformdirs import user_cache_dir
        cache_dir = user_cache_dir("strata")
        catalog_path = os.path.join(cache_dir, "tool_catalog.json")

    if not os.path.exists(catalog_path):
        logger.warning(f"Tool catalog not found: {catalog_path}")
        return []

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        tools = []
        for server_name, server_tools in catalog.items():
            for tool in server_tools:
                name = tool.get("name", "")
                description = tool.get("description", "")

                # Infer domain from server, tool name, and description
                domain = infer_domain(server_name, name, description)

                tools.append({
                    "name": name,
                    "description": description[:2000] if description else "",  # Truncate long descriptions
                    "server": server_name,
                    "domain": domain
                })

        return tools
    except Exception as e:
        logger.error(f"Could not load tool catalog: {e}")
        return []


def get_catalog_stats(catalog_path: Optional[str] = None) -> dict:
    """
    Get statistics about the tool catalog.

    Args:
        catalog_path: Path to catalog file

    Returns:
        dict: Statistics including server count, tool count, etc.
    """
    if catalog_path is None:
        from platformdirs import user_cache_dir
        cache_dir = user_cache_dir("strata")
        catalog_path = os.path.join(cache_dir, "tool_catalog.json")

    if not os.path.exists(catalog_path):
        return {"error": f"Catalog not found: {catalog_path}"}

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        servers = list(catalog.keys())
        total_tools = sum(len(tools) for tools in catalog.values())
        tools_per_server = {s: len(catalog[s]) for s in servers}

        return {
            "catalog_path": catalog_path,
            "server_count": len(servers),
            "total_tools": total_tools,
            "servers": servers,
            "tools_per_server": tools_per_server
        }
    except Exception as e:
        return {"error": str(e)}


def sync_all_tools(catalog_path: Optional[str] = None) -> dict:
    """
    Sync all tools from strata catalog to Neo4j.

    Args:
        catalog_path: Optional path to catalog file

    Returns:
        dict: Summary of sync operation
    """
    driver = get_neo4j_driver()

    try:
        # Create schema
        schema_result = create_tool_schema(driver)

        # Load and sync tools
        tools = load_tools_from_catalog(catalog_path)
        tool_results = []
        domains_seen = set()
        servers_seen = set()

        for tool in tools:
            try:
                result = sync_tool_to_neo4j(driver, tool)
                tool_results.append(result)
                domains_seen.add(tool["domain"])
                servers_seen.add(tool["server"])
            except Exception as e:
                tool_results.append({
                    "tool": tool["name"],
                    "server": tool["server"],
                    "status": "error",
                    "error": str(e)
                })

        return {
            "schema": schema_result,
            "tools_synced": len([r for r in tool_results if r.get("status") == "synced"]),
            "tools_total": len(tools),
            "servers_count": len(servers_seen),
            "domains_count": len(domains_seen),
            "domains": sorted(list(domains_seen)),
            "servers": sorted(list(servers_seen)),
            "tool_results": tool_results[:20]  # First 20 results for brevity
        }
    finally:
        driver.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Show catalog stats first
    print("=== Tool Catalog Stats ===")
    stats = get_catalog_stats()
    print(json.dumps(stats, indent=2))
    print()

    # Sync to Neo4j
    print("=== Syncing to Neo4j ===")
    result = sync_all_tools()
    print(json.dumps(result, indent=2))
