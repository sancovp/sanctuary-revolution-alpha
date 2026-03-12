"""
Ingest skills from skillmanager into CartON as fully typed concepts.

Skills are PACKAGES with:
- SKILL.md - main content
- _metadata.json - structured metadata
- reference.md - TOC
- resources/ - content files (can be nested dirs)
- scripts/ - executable scripts
- templates/ - template files

Each skill becomes concepts with full UARL + package structure:
- is_a: Skill
- part_of: <Skillset_Name> or Skill_Catalog
- instantiates: <Skill_Category_Pattern>
- has_domain, has_subdomain, has_category
- has_resource: [Resource_*]
- has_script: [Script_*]
- has_template: [Template_*]

Plus a Skillgraph meta-concept for RAG embedding.
"""

import json
import re
import os
from pathlib import Path


SKILLS_DIR = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")) / "skills"


def normalize_name(name: str) -> str:
    """Convert to CartON-style Title_Case_With_Underscores."""
    s = re.sub(r'[-.]', '_', name)
    s = re.sub(r'([a-z])([A-Z])', r'\\1_\\2', s)
    return '_'.join(word.capitalize() for word in s.split('_') if word)


def scan_directory_recursive(dir_path: Path, prefix: str = "") -> list[str]:
    """Recursively scan directory and return normalized resource names."""
    resources = []
    if not dir_path.exists():
        return resources

    for item in dir_path.iterdir():
        if item.name.startswith('_') or item.name.startswith('.'):
            continue

        rel_name = f"{prefix}_{item.stem}" if prefix else item.stem
        normalized = normalize_name(rel_name)

        if item.is_file():
            resources.append(normalized)
        elif item.is_dir():
            # Add dir as container + recurse
            resources.append(normalized)
            resources.extend(scan_directory_recursive(item, rel_name))

    return resources


def serialize_skillgraph_sentence(
    skill_name: str,
    domain: str,
    subdomain: str,
    category: str,
    resources: list[str],
    scripts: list[str],
    templates: list[str],
    what: str = "",
    when: str = ""
) -> str:
    """
    Serialize a skill's subgraph into an ontological sentence for embedding.

    Includes resources/scripts/templates for better RAG matching.
    """
    parts = [
        f"[SKILLGRAPH:{skill_name}]",
        f"is_a:Skill",
        f"instantiates:{category.capitalize()}_Skill_Pattern" if category else "instantiates:Generic_Skill_Pattern",
        f"has_domain:{domain}",
    ]

    if subdomain:
        parts.append(f"has_subdomain:{subdomain}")

    if resources:
        res_str = ",".join(resources[:8])  # Limit for embedding size
        parts.append(f"has_resources:[{res_str}]")

    if scripts:
        script_str = ",".join(scripts[:5])
        parts.append(f"has_scripts:[{script_str}]")

    if templates:
        tmpl_str = ",".join(templates[:5])
        parts.append(f"has_templates:[{tmpl_str}]")

    # Include WHAT/WHEN for semantic matching
    if what:
        parts.append(f"what:{what[:100]}")
    if when:
        parts.append(f"when:{when[:100]}")

    parts.append(f"[/SKILLGRAPH]")

    return " ".join(parts)


def infer_skill_pattern(category: str) -> str:
    """Map category to pattern."""
    patterns = {
        "understand": "Understand_Skill_Pattern",
        "preflight": "Preflight_Skill_Pattern",
        "single_turn_process": "Single_Turn_Process_Pattern"
    }
    return patterns.get(category, "Generic_Skill_Pattern")


def load_skill_from_directory(skill_dir: Path) -> dict | None:
    """Load skill data from directory structure."""
    if not skill_dir.is_dir():
        return None

    # Skip internal dirs
    if skill_dir.name.startswith('_'):
        return None

    skill = {"name": skill_dir.name}

    # Load _metadata.json (preferred)
    metadata_path = skill_dir / "_metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text())
            skill.update(metadata)
        except:
            pass

    # Load SKILL.md for description if not in metadata
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists() and 'description' not in skill:
        content = skill_md.read_text()
        # Extract first paragraph after frontmatter as description
        if '---' in content:
            parts = content.split('---', 2)
            if len(parts) >= 3:
                body = parts[2].strip()
                # First non-empty paragraph
                for para in body.split('\n\n'):
                    para = para.strip()
                    if para and not para.startswith('#'):
                        skill['description'] = para[:500]
                        break

    # Scan resources
    skill['resources'] = scan_directory_recursive(skill_dir / "resources")
    skill['scripts'] = scan_directory_recursive(skill_dir / "scripts")
    skill['templates'] = scan_directory_recursive(skill_dir / "templates")

    # Check for reference.md
    if (skill_dir / "reference.md").exists():
        skill['has_reference'] = True

    return skill


def skill_to_carton_concepts(skill: dict) -> list[dict]:
    """Convert a skill package to CartON concepts."""
    concepts = []

    name = skill.get('name', '')
    domain = skill.get('domain', 'unknown')
    subdomain = skill.get('subdomain', '')
    category = skill.get('category', '')
    description = skill.get('description', '')[:500]
    what = skill.get('what', '')
    when = skill.get('when', '')
    resources = skill.get('resources', [])
    scripts = skill.get('scripts', [])
    templates = skill.get('templates', [])

    # Normalize names
    skill_concept_name = f"Skill_{normalize_name(name)}"
    domain_name = normalize_name(domain) if domain else "General"
    subdomain_name = normalize_name(subdomain) if subdomain else None
    pattern = infer_skill_pattern(category)

    # Resource concept names
    resource_concepts = [f"Resource_{r}" for r in resources]
    script_concepts = [f"Script_{s}" for s in scripts]
    template_concepts = [f"Template_{t}" for t in templates]

    # 1. Main skill concept with full UARL
    skill_relationships = [
        {"relationship": "is_a", "related": ["Skill"]},
        {"relationship": "part_of", "related": ["Skill_Catalog"]},
        {"relationship": "instantiates", "related": [pattern]},
        {"relationship": "has_domain", "related": [domain_name]},
    ]

    if subdomain_name:
        skill_relationships.append({"relationship": "has_subdomain", "related": [subdomain_name]})

    if category:
        skill_relationships.append({"relationship": "has_category", "related": [f"Category_{normalize_name(category)}"]})

    if resource_concepts:
        skill_relationships.append({"relationship": "has_resource", "related": resource_concepts})

    if script_concepts:
        skill_relationships.append({"relationship": "has_script", "related": script_concepts})

    if template_concepts:
        skill_relationships.append({"relationship": "has_template", "related": template_concepts})

    desc_parts = [f"Skill: {name}", f"Domain: {domain}"]
    if subdomain:
        desc_parts.append(f"Subdomain: {subdomain}")
    if category:
        desc_parts.append(f"Category: {category}")
    if what:
        desc_parts.append(f"WHAT: {what}")
    if when:
        desc_parts.append(f"WHEN: {when}")
    if description:
        desc_parts.append(f"\n{description}")

    concepts.append({
        "concept_name": skill_concept_name,
        "concept": "\n".join(desc_parts),
        "relationships": skill_relationships
    })

    # 2. Skillgraph meta-concept
    skillgraph_name = f"Skillgraph_{normalize_name(name)}"

    subgraph_nodes = [skill_concept_name, domain_name, pattern]
    subgraph_nodes.extend(resource_concepts[:10])  # Limit
    subgraph_nodes.extend(script_concepts[:5])
    subgraph_nodes.extend(template_concepts[:5])

    skillgraph_relationships = [
        {"relationship": "is_a", "related": ["Skillgraph"]},
        {"relationship": "part_of", "related": ["Skillgraph_Registry"]},
        {"relationship": "instantiates", "related": ["Semantic_Graph_Pattern"]},
        {"relationship": "has_root", "related": [skill_concept_name]},
        {"relationship": "has_node", "related": subgraph_nodes},
        {"relationship": "has_domain", "related": [domain_name]},
        {"relationship": "has_pattern", "related": [pattern]},
    ]

    if category:
        skillgraph_relationships.append({"relationship": "has_category", "related": [f"Category_{normalize_name(category)}"]})

    concepts.append({
        "concept_name": skillgraph_name,
        "concept": serialize_skillgraph_sentence(name, domain_name, subdomain_name or "", category, resources, scripts, templates, what, when),
        "relationships": skillgraph_relationships
    })

    # 3. Domain concept
    concepts.append({
        "concept_name": domain_name,
        "concept": f"Domain: {domain}",
        "relationships": [{"relationship": "is_a", "related": ["Domain"]}]
    })

    # 4. Resource concepts (brief, for graph structure)
    for res in resources[:15]:
        concepts.append({
            "concept_name": f"Resource_{res}",
            "concept": f"Skill Resource: {res}",
            "relationships": [
                {"relationship": "is_a", "related": ["Skill_Resource"]},
                {"relationship": "part_of", "related": [skill_concept_name]}
            ]
        })

    return concepts


def generate_all_skill_concepts() -> list[dict]:
    """Generate CartON concepts for all skills."""
    all_concepts = []

    if not SKILLS_DIR.exists():
        print(f"Skills directory not found: {SKILLS_DIR}")
        return []

    for skill_dir in SKILLS_DIR.iterdir():
        skill = load_skill_from_directory(skill_dir)
        if skill:
            concepts = skill_to_carton_concepts(skill)
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
    concepts = generate_all_skill_concepts()
    print(f"Generated {len(concepts)} concepts from skills")

    output_path = Path("/tmp/rag_tool_discovery/data/skill_concepts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(concepts, indent=2))
    print(f"Saved to {output_path}")

    # Show sample with resources
    print("\n=== Sample Skillgraph ===")
    for c in concepts:
        if c['concept_name'].startswith('Skillgraph_') and 'has_resource' in str(c.get('relationships', [])):
            print(f"\n{c['concept_name']}:")
            print(f"  sentence: {c['concept'][:200]}...")
            break
