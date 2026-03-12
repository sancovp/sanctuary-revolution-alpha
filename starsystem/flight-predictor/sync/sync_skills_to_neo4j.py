"""
Sync skills from skillmanager to Neo4j with graph relationships.

Schema:
- :Skill nodes with properties: name, domain, subdomain, category, description, what, when
- :Skillset nodes with properties: name, domain, subdomain, description
- :Domain nodes with properties: name
- Relationships:
  - (:Skill)-[:PART_OF]->(:Skillset)
  - (:Skillset)-[:PART_OF]->(:Domain)
  - (:Skill)-[:BELONGS_TO]->(:Domain)  # Direct domain relationship
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# Neo4j configuration - uses host.docker.internal for Docker compatibility
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://host.docker.internal:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


def get_neo4j_driver():
    """Get Neo4j driver instance."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def create_skill_schema(driver) -> dict:
    """
    Create the skill graph schema with constraints and indexes.

    Returns:
        dict: Schema creation results
    """
    queries = [
        # Constraints for uniqueness
        "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT skillset_name IF NOT EXISTS FOR (ss:Skillset) REQUIRE ss.name IS UNIQUE",
        "CREATE CONSTRAINT skill_domain_name IF NOT EXISTS FOR (d:SkillDomain) REQUIRE d.name IS UNIQUE",

        # Indexes for faster lookups
        "CREATE INDEX skill_domain_idx IF NOT EXISTS FOR (s:Skill) ON (s.domain)",
        "CREATE INDEX skill_category_idx IF NOT EXISTS FOR (s:Skill) ON (s.category)",
        "CREATE INDEX skillset_domain_idx IF NOT EXISTS FOR (ss:Skillset) ON (ss.domain)",
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


def sync_skill_to_neo4j(driver, skill_data: dict) -> dict:
    """
    Sync a single skill to Neo4j.

    Args:
        driver: Neo4j driver
        skill_data: Skill data dict with keys: name, domain, subdomain, category, description, what, when

    Returns:
        dict: Sync result
    """
    query = """
    MERGE (s:Skill {name: $name})
    SET s.domain = $domain,
        s.subdomain = $subdomain,
        s.category = $category,
        s.description = $description,
        s.what = $what,
        s.when = $when,
        s.synced_at = datetime()

    // Ensure domain node exists and link skill to it
    MERGE (d:SkillDomain {name: $domain})
    MERGE (s)-[:BELONGS_TO]->(d)

    RETURN s.name as skill_name, d.name as domain_name
    """

    with driver.session() as session:
        result = session.run(query, **skill_data)
        record = result.single()
        return {
            "skill": record["skill_name"],
            "domain": record["domain_name"],
            "status": "synced"
        }


def sync_skillset_to_neo4j(driver, skillset_data: dict) -> dict:
    """
    Sync a skillset to Neo4j with its member skills.

    Args:
        driver: Neo4j driver
        skillset_data: Skillset data dict with keys: name, domain, subdomain, description, skills (list)

    Returns:
        dict: Sync result
    """
    # Create skillset node and link to domain
    create_query = """
    MERGE (ss:Skillset {name: $name})
    SET ss.domain = $domain,
        ss.subdomain = $subdomain,
        ss.description = $description,
        ss.synced_at = datetime()

    MERGE (d:SkillDomain {name: $domain})
    MERGE (ss)-[:PART_OF]->(d)

    RETURN ss.name as skillset_name
    """

    # Link skills to skillset
    link_query = """
    MATCH (ss:Skillset {name: $skillset_name})
    MATCH (s:Skill {name: $skill_name})
    MERGE (s)-[:PART_OF]->(ss)
    RETURN s.name as skill_name, ss.name as skillset_name
    """

    with driver.session() as session:
        # Create skillset
        session.run(create_query,
                   name=skillset_data["name"],
                   domain=skillset_data["domain"],
                   subdomain=skillset_data.get("subdomain", ""),
                   description=skillset_data.get("description", ""))

        # Link member skills
        linked = []
        for skill_name in skillset_data.get("skills", []):
            try:
                result = session.run(link_query,
                                    skillset_name=skillset_data["name"],
                                    skill_name=skill_name)
                record = result.single()
                if record:
                    linked.append(record["skill_name"])
            except Exception as e:
                logger.warning(f"Could not link skill {skill_name}: {e}")

        return {
            "skillset": skillset_data["name"],
            "domain": skillset_data["domain"],
            "linked_skills": linked,
            "status": "synced"
        }


def load_skills_from_skillmanager(skills_dir: Optional[str] = None) -> list:
    """
    Load all skills from the skillmanager directory.

    Args:
        skills_dir: Path to skills directory. If None, uses HEAVEN_DATA_DIR/skills

    Returns:
        list: List of skill data dicts
    """
    heaven_data = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
    skills_path = Path(skills_dir or os.path.join(heaven_data, "skills"))

    if not skills_path.exists():
        logger.warning(f"Skills directory not found: {skills_path}")
        return []

    skills = []
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
            metadata_file = skill_dir / "_metadata.json"
            skill_md = skill_dir / "SKILL.md"

            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())

                    # Read description from SKILL.md if available
                    description = ""
                    if skill_md.exists():
                        content = skill_md.read_text()
                        if "description:" in content:
                            # Extract description from frontmatter
                            lines = content.split("\n")
                            in_desc = False
                            desc_lines = []
                            for line in lines:
                                if line.strip().startswith("description:"):
                                    in_desc = True
                                    rest = line.split(":", 1)[1].strip()
                                    if rest and not rest.startswith("|"):
                                        desc_lines.append(rest)
                                elif in_desc:
                                    if line.startswith("  "):
                                        desc_lines.append(line.strip())
                                    elif line.strip() and not line.startswith(" "):
                                        break
                            description = "\n".join(desc_lines)

                    skills.append({
                        "name": skill_dir.name,
                        "domain": metadata.get("domain", "general"),
                        "subdomain": metadata.get("subdomain", ""),
                        "category": metadata.get("category", ""),
                        "description": description or metadata.get("description", ""),
                        "what": metadata.get("what", ""),
                        "when": metadata.get("when", "")
                    })
                except Exception as e:
                    logger.warning(f"Could not load skill {skill_dir.name}: {e}")

    return skills


def load_skillsets_from_skillmanager(skills_dir: Optional[str] = None) -> list:
    """
    Load all skillsets from the skillmanager directory.

    Args:
        skills_dir: Path to skills directory. If None, uses HEAVEN_DATA_DIR/skills

    Returns:
        list: List of skillset data dicts
    """
    heaven_data = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
    skills_path = Path(skills_dir or os.path.join(heaven_data, "skills"))
    skillsets_file = skills_path / "_skillsets.json"

    if not skillsets_file.exists():
        logger.warning(f"Skillsets file not found: {skillsets_file}")
        return []

    try:
        data = json.loads(skillsets_file.read_text())
        skillsets = []
        for name, ss_data in data.items():
            skillsets.append({
                "name": name,
                "domain": ss_data.get("domain", "general"),
                "subdomain": ss_data.get("subdomain", ""),
                "description": ss_data.get("description", ""),
                "skills": ss_data.get("skills", [])
            })
        return skillsets
    except Exception as e:
        logger.error(f"Could not load skillsets: {e}")
        return []


def sync_all_skills(skills_dir: Optional[str] = None) -> dict:
    """
    Sync all skills and skillsets from skillmanager to Neo4j.

    Args:
        skills_dir: Optional path to skills directory

    Returns:
        dict: Summary of sync operation
    """
    driver = get_neo4j_driver()

    try:
        # Create schema
        schema_result = create_skill_schema(driver)

        # Load and sync skills
        skills = load_skills_from_skillmanager(skills_dir)
        skill_results = []
        for skill in skills:
            try:
                result = sync_skill_to_neo4j(driver, skill)
                skill_results.append(result)
            except Exception as e:
                skill_results.append({"skill": skill["name"], "status": "error", "error": str(e)})

        # Load and sync skillsets
        skillsets = load_skillsets_from_skillmanager(skills_dir)
        skillset_results = []
        for skillset in skillsets:
            try:
                result = sync_skillset_to_neo4j(driver, skillset)
                skillset_results.append(result)
            except Exception as e:
                skillset_results.append({"skillset": skillset["name"], "status": "error", "error": str(e)})

        return {
            "schema": schema_result,
            "skills_synced": len([r for r in skill_results if r.get("status") == "synced"]),
            "skills_total": len(skills),
            "skillsets_synced": len([r for r in skillset_results if r.get("status") == "synced"]),
            "skillsets_total": len(skillsets),
            "skill_results": skill_results,
            "skillset_results": skillset_results
        }
    finally:
        driver.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = sync_all_skills()
    print(json.dumps(result, indent=2))
