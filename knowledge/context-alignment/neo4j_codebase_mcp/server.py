"""
Context Alignment MCP Server

Provides dependency graph analysis and context loading tools to prevent AI hallucination
by ensuring complete codebase context is available before making changes.
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from dependency_analyzer import analyze_dependencies
import json
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Initialize FastMCP server
mcp = FastMCP("context-alignment")

@mcp.tool()
async def parse_repository_to_neo4j(repo_url: str, keep_local: bool = True) -> str:
    """
    Parse a GitHub repository or local directory into Neo4j knowledge graph.
    
    Args:
        repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo.git') 
                 OR local directory path (e.g., '/path/to/local/project')
        keep_local: Whether to keep the cloned repository locally for dependency analysis (default: True)
    
    Returns:
        JSON string with parsing results and statistics
    """
    try:
        from parsers.parse_repo_into_neo4j import DirectNeo4jExtractor
        
        extractor = DirectNeo4jExtractor(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        await extractor.initialize()
        
        try:
            # Detect if input is local directory or GitHub URL
            import os
            is_local = os.path.exists(repo_url) and os.path.isdir(repo_url)
            
            if is_local:
                # Handle local directory
                repo_name = os.path.basename(os.path.abspath(repo_url))
                # Use local directory directly
                await extractor.analyze_local_directory(repo_url, repo_name)
                local_path = repo_url
                formatted_url = f"local:{repo_url}"
            else:
                # Handle GitHub URL
                await extractor.analyze_repository(repo_url, keep_local=keep_local)
                repo_name = repo_url.split('/')[-1].replace('.git', '')
                formatted_url = repo_url
                
                # If files are kept locally, include the directory path
                local_path = None
                if keep_local:
                    local_path = _find_latest_repo_dir(repo_name)
            
            return json.dumps({
                "status": "success",
                "repo_url": formatted_url,
                "repo_name": repo_name,
                "message": f"{'Local directory' if is_local else 'Repository'} {repo_name} successfully parsed into Neo4j",
                "files_kept_locally": keep_local if not is_local else True,
                "local_directory": local_path
            })
            
        finally:
            await extractor.close()
            
    except Exception:
        logger.error(f"Error parsing repository {repo_url}", exc_info=True)
        raise

@mcp.tool()
async def get_dependency_context(
    target_entity: str, 
    search_dirs: Optional[List[str]] = None
) -> str:
    """
    Get the complete dependency context needed to safely modify a code entity.
    
    This is the core anti-hallucination tool that tells you exactly what files
    to read before making any changes using Isaac's advanced AST dependency analyzer.
    
    Returns ONLY the dependency graph - not the actual code content.
    Use this to get the ordered list of files to read, then use Read tool on each file.
    
    Args:
        target_entity: Name of the class, function, or file you want to modify
        search_dirs: List of directories to search in (defaults to current working dir)
    
    Returns:
        Dependency graph with files and line ranges to read (no code content)
    """
    try:
        result = analyze_dependencies(
            target_name=target_entity,
            search_dirs=search_dirs,
            contextualizer=False,  # Always False - we want callgraph not code
            exclude_from_contextualizer=None,
            include_external_packages=True,
            external_depth=1,
        )
        return json.dumps(result, default=str)
    except Exception:
        logger.error(f"Error analyzing dependencies for {target_entity}", exc_info=True)
        raise

def _find_latest_repo_dir(repo_name: str, is_local: bool = False) -> Optional[str]:
    """Find the latest timestamped directory for a repository or return local path"""
    import glob
    
    # For local repositories, we need to handle them differently
    # Check if repo_name looks like a local path stored in metadata
    if is_local or repo_name.startswith('/'):
        # This is a local directory, return as-is if it exists
        if os.path.exists(repo_name):
            return repo_name
        return None
    
    script_dir = Path(__file__).parent
    repos_dir = script_dir / "parsers" / "repos"
    
    # Look for directories matching repo_name_YYYYMMDD_HHMMSS pattern
    pattern = str(repos_dir / f"{repo_name}_*")
    matching_dirs = glob.glob(pattern)
    
    if not matching_dirs:
        return None
        
    # Return the most recent (lexicographically last due to timestamp format)
    return sorted(matching_dirs)[-1]

async def _check_if_repo_is_local(repo_name: str) -> bool:
    """Check if a repository was ingested from a local directory by checking Neo4j metadata"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(
                "MATCH (r:Repository {name: $repo_name}) RETURN r.source_url as source_url",
                repo_name=repo_name
            ).single()
            
            if result and result["source_url"]:
                return result["source_url"].startswith("local:")
            return False
    except Exception:
        return False
    finally:
        if 'driver' in locals():
            driver.close()

@mcp.tool()
async def analyze_dependencies_and_merge_to_graph(repo_name: str, target_entity: str, search_dirs: Optional[List[str]] = None) -> str:
    """
    THE CORE HYBRID TOOL: Analyze deep dependencies using Isaac's AST analyzer 
    and merge the callgraph data into the existing Neo4j structural graph.
    
    This combines broad Neo4j coverage with deep dependency analysis where needed.
    
    Args:
        repo_name: Name of the repository (must already exist in Neo4j from parse_github_repository)
        target_entity: Name of the class/function to deeply analyze
        search_dirs: Directories to search in for the dependency analysis
    
    Returns:
        JSON string with merge results and enhanced graph statistics
    """
    try:
        # If no search_dirs provided, try to find the latest local repo directory
        if search_dirs is None:
            # Check if this might be a local directory by looking in Neo4j metadata
            is_local = await _check_if_repo_is_local(repo_name)
            latest_repo_dir = _find_latest_repo_dir(repo_name, is_local)
            if latest_repo_dir:
                search_dirs = [latest_repo_dir]
                logger.info(f"Using {'local' if is_local else 'cloned'} repo directory: {latest_repo_dir}")
            else:
                return json.dumps({
                    "status": "error",
                    "message": f"No local repository found for '{repo_name}'. Please run parse_repository_to_neo4j first."
                })
        
        # Step 1: Run Isaac's deep dependency analysis
        dep_result = analyze_dependencies(
            target_name=target_entity,
            search_dirs=search_dirs,
            contextualizer=False,
            exclude_from_contextualizer=None,
            include_external_packages=True,
            external_depth=1,
        )
        
        if dep_result["status"] != "found":
            return json.dumps({
                "status": "error", 
                "message": f"Target entity '{target_entity}' not found",
                "details": dep_result
            })
        
        # Step 2: Connect to Neo4j and merge the callgraph data
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            find_target_query = """
            MATCH (repo:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(target)
            WHERE target.name = $target_entity
            RETURN target, labels(target)[0] as target_type
            """
            target_result = session.run(
                find_target_query,
                repo_name=repo_name,
                target_entity=target_entity,
            ).single()

            if not target_result:
                driver.close()
                return json.dumps(
                    {
                        "status": "error",
                        "message": (
                            f"Target entity '{target_entity}' exists in dependency analysis "
                            f"but was not found in Neo4j repository '{repo_name}'"
                        ),
                    }
                )

            # Create deep dependency relationships in the graph.
            dependencies_created = 0
            for dep in dep_result.get("dependencies", []):
                dep_label = "Function" if dep["type"] in ["function", "reference"] else "Class"

                merge_dep_query = f"""
                MERGE (dep_entity:{dep_label} {{
                    name: $dep_name,
                    file: $dep_file,
                    dependency_type: $dep_type,
                    symbol_origin: $symbol_origin
                }})
                WITH dep_entity
                MATCH (repo:Repository {{name: $repo_name}})-[:CONTAINS]->(f:File)-[:DEFINES]->(target)
                WHERE target.name = $target_entity
                MERGE (target)-[:DEEP_DEPENDS_ON {{
                    analyzed_at: datetime(),
                    line_range_start: $line_start,
                    line_range_end: $line_end,
                    dependency_type: $dep_type,
                    confidence: $confidence,
                    why: $why,
                    resolution: $resolution,
                    source_line: $source_line,
                    symbol_origin: $symbol_origin
                }}]->(dep_entity)
                """

                session.run(
                    merge_dep_query,
                    repo_name=repo_name,
                    target_entity=target_entity,
                    dep_name=dep["name"],
                    dep_file=dep["file"],
                    dep_type=dep["type"],
                    line_start=dep["line_range"][0],
                    line_end=dep["line_range"][1],
                    confidence=dep.get("confidence", 1.0),
                    why=dep.get("why", ""),
                    resolution=dep.get("resolution", "name_match"),
                    source_line=dep.get("source_line", 0),
                    symbol_origin=dep.get("symbol_origin", "internal"),
                )
                dependencies_created += 1

            # Create file dependency relationships in the graph.
            file_deps_created = 0
            for file_dep in dep_result.get("file_dependencies", []):
                merge_file_dep_query = """
                MERGE (file_resource:FileResource {
                    path: $file_path,
                    operation: $operation,
                    pattern: $pattern
                })
                WITH file_resource
                MATCH (repo:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(target)
                WHERE target.name = $target_entity
                MERGE (target)-[:DEPENDS_ON_FILE {
                    analyzed_at: datetime(),
                    line: $line,
                    operation: $operation,
                    pattern: $pattern,
                    confidence: $confidence,
                    why: $why
                }]->(file_resource)
                """

                session.run(
                    merge_file_dep_query,
                    repo_name=repo_name,
                    target_entity=target_entity,
                    file_path=file_dep["path"],
                    operation=file_dep["operation"],
                    pattern=file_dep["pattern"],
                    line=file_dep.get("line", 0),
                    confidence=file_dep.get("confidence", 0.8),
                    why=file_dep.get("why", ""),
                )
                file_deps_created += 1

            # Merge inferred callgraph lineage for unresolved/dynamic targets.
            inferred_deps_created = 0
            for inferred in dep_result.get("inferred_dependencies", []):
                merge_inferred_query = """
                MERGE (inferred:InferredDependency {
                    source_file: $source_file,
                    expression: $expression,
                    line: $line
                })
                SET inferred.name = $name,
                    inferred.kind = $kind,
                    inferred.confidence = $confidence,
                    inferred.why = $why,
                    inferred.candidates = $candidates,
                    inferred.updated_at = datetime()
                WITH inferred
                MATCH (repo:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(target)
                WHERE target.name = $target_entity
                MERGE (target)-[:INFERRED_DEPENDS_ON {
                    analyzed_at: datetime(),
                    kind: $kind,
                    line: $line,
                    confidence: $confidence,
                    why: $why
                }]->(inferred)
                """

                session.run(
                    merge_inferred_query,
                    repo_name=repo_name,
                    target_entity=target_entity,
                    source_file=inferred.get("source_file", dep_result.get("file")),
                    expression=inferred.get("expression", inferred.get("name", "<unknown>")),
                    line=inferred.get("line", 0),
                    name=inferred.get("name", "<unknown>"),
                    kind=inferred.get("kind", "unresolved_call"),
                    confidence=inferred.get("confidence", 0.5),
                    why=inferred.get("why", ""),
                    candidates=json.dumps(inferred.get("candidates", []), default=str),
                )
                inferred_deps_created += 1

            # Merge config lineage signals.
            config_lineage_created = 0
            for cfg in dep_result.get("config_lineage", []):
                merge_config_query = """
                MERGE (config_signal:ConfigSignal {
                    variable: $variable,
                    key_path: $key_path,
                    kind: $kind,
                    source_file: $source_file,
                    line: $line
                })
                SET config_signal.source = $source,
                    config_signal.confidence = $confidence,
                    config_signal.why = $why,
                    config_signal.updated_at = datetime()
                WITH config_signal
                MATCH (repo:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(target)
                WHERE target.name = $target_entity
                MERGE (target)-[:CONFIG_INFLUENCES {
                    analyzed_at: datetime(),
                    line: $line,
                    kind: $kind,
                    confidence: $confidence,
                    why: $why
                }]->(config_signal)
                """

                session.run(
                    merge_config_query,
                    repo_name=repo_name,
                    target_entity=target_entity,
                    variable=cfg.get("variable", "<unknown>"),
                    key_path=cfg.get("key_path", "<dynamic>"),
                    kind=cfg.get("kind", "key_access"),
                    source_file=dep_result.get("file"),
                    line=cfg.get("line", 0),
                    source=cfg.get("source"),
                    confidence=cfg.get("confidence", 0.6),
                    why=cfg.get("why", ""),
                )
                config_lineage_created += 1

            # Mark this entity as deeply analyzed.
            mark_analyzed_query = """
            MATCH (target) WHERE target.name = $target_entity
            SET target.deep_analyzed = true, target.deep_analyzed_at = datetime()
            """
            session.run(mark_analyzed_query, target_entity=target_entity)
            
        driver.close()
        
        return json.dumps({
            "status": "success",
            "repo": repo_name,
            "target": target_entity,
            "dependencies_merged": dependencies_created,
            "file_dependencies_merged": file_deps_created,
            "inferred_dependencies_merged": inferred_deps_created,
            "config_lineage_merged": config_lineage_created,
            "target_file": dep_result.get("file"),
            "target_line_range": dep_result.get("line_range")
        })
        
    except Exception:
        logger.error(f"Error merging dependencies for {target_entity} in {repo_name}", exc_info=True)
        raise

@mcp.tool()
async def query_codebase_graph(cypher_query: str) -> str:
    """
    Execute a Cypher query against the codebase knowledge graph.
    
    Args:
        cypher_query: Cypher query to execute
    
    Returns:
        JSON string with query results
    """
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            result = session.run(cypher_query)
            records = [dict(record) for record in result]
            
        driver.close()
        return json.dumps(records, default=str)
        
    except Exception:
        logger.error(f"Error executing Cypher query: {cypher_query}", exc_info=True)
        raise

async def main():
    """Run the MCP server"""
    logger.info("Starting Context Alignment MCP Server...")
    transport = os.getenv("TRANSPORT", "sse")
    
    if transport == "sse":
        await mcp.run_sse_async()
    else:
        await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main())
