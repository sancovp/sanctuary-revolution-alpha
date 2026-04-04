#!/usr/bin/env python3
"""
GIINT Carton Synchronization Module

Dual-write pattern: GIINT entities are mirrored to Carton knowledge graph.
- JSON = fast operational cache
- Carton = queryable knowledge graph for cross-system integration
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA DESIGN - Concept Naming Conventions
# ============================================================================

def get_project_concept_name(project_id: str) -> str:
    """Get Carton concept name for GIINT project."""
    return f"GIINT_Project_{project_id}"


def get_feature_concept_name(project_id: str, feature_name: str) -> str:
    """Get Carton concept name for GIINT feature."""
    return f"GIINT_Feature_{project_id}_{feature_name}"


def get_component_concept_name(project_id: str, feature_name: str, component_name: str) -> str:
    """Get Carton concept name for GIINT component."""
    return f"GIINT_Component_{project_id}_{feature_name}_{component_name}"


def get_deliverable_concept_name(project_id: str, feature_name: str, component_name: str, deliverable_name: str) -> str:
    """Get Carton concept name for GIINT deliverable."""
    return f"GIINT_Deliverable_{project_id}_{feature_name}_{component_name}_{deliverable_name}"


def get_task_concept_name(project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str) -> str:
    """Get Carton concept name for GIINT task."""
    return f"GIINT_Task_{project_id}_{feature_name}_{component_name}_{deliverable_name}_{task_id}"


# ============================================================================
# CONCEPT CONVERSION - Pydantic Models to Carton Concepts
# ============================================================================

def project_to_concept(project: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GIINT Project to Carton concept format. All model fields → typed relationships."""
    concept_name = get_project_concept_name(project["project_id"])
    concept = f"GIINT Project: {project['project_id']}. Location: {project['project_dir']}."

    features = project.get('features', {})
    sub_projects = project.get('sub_projects', [])

    relationships = [
        {"relationship": "is_a", "related": ["GIINT_Project"]},
        {"relationship": "has_project_type", "related": [project.get('project_type', 'single')]},
        {"relationship": "has_mode", "related": [project.get('mode', 'planning')]},
        {"relationship": "has_path", "related": [project['project_dir']]},
    ]

    # Sub-projects
    for sub_id in sub_projects:
        relationships.append({"relationship": "has_sub_project", "related": [get_project_concept_name(sub_id)]})

    # Starlog project link
    if project.get('starlog_path'):
        _raw = os.path.basename(project['starlog_path'].rstrip("/"))
        _norm = _raw.replace("-", "_").replace(".", "_")
        _norm = "_".join(s.title() if s.islower() else s for s in _norm.split("_"))
        relationships.append({"relationship": "has_starlog_project", "related": [f"Starlog_Project_{_norm}"]})

    # GitHub repo
    if project.get('github_repo_url'):
        relationships.append({"relationship": "has_github_repo", "related": [project['github_repo_url']]})

    # Starsystem
    project_dir = project.get('project_dir', '')
    if project_dir:
        path_slug = project_dir.strip("/").replace("/", "_").replace("-", "_").title()
        relationships.append({"relationship": "part_of", "related": [f"Starsystem_{path_slug}"]})

    return {"concept_name": concept_name, "concept": concept, "relationships": relationships}


def feature_to_concept(project_id: str, feature_name: str, feature: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GIINT Feature to Carton concept format. All model fields → typed relationships."""
    concept_name = get_feature_concept_name(project_id, feature_name)
    concept = f"GIINT Feature: {feature_name} in project {project_id}."

    relationships = [
        {"relationship": "is_a", "related": ["GIINT_Feature"]},
        {"relationship": "part_of", "related": [get_project_concept_name(project_id)]},
    ]

    if feature.get('path'):
        relationships.append({"relationship": "has_path", "related": [feature['path']]})

    spec = feature.get('spec')
    if spec:
        relationships.append({"relationship": "has_spec", "related": [spec.get('spec_file_path', 'unknown')]})
        relationships.append({"relationship": "has_spec_status", "related": [spec.get('status', 'draft')]})

    return {"concept_name": concept_name, "concept": concept, "relationships": relationships}


def component_to_concept(project_id: str, feature_name: str, component_name: str, component: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GIINT Component to Carton concept format. All model fields → typed relationships."""
    concept_name = get_component_concept_name(project_id, feature_name, component_name)
    concept = f"GIINT Component: {component_name} in feature {feature_name}, project {project_id}."

    relationships = [
        {"relationship": "is_a", "related": ["GIINT_Component"]},
        {"relationship": "part_of", "related": [get_feature_concept_name(project_id, feature_name)]},
    ]

    if component.get('path'):
        relationships.append({"relationship": "has_path", "related": [component['path']]})
        # OWL requires hasCodeEntity — use path as code file reference
        relationships.append({"relationship": "has_code_entity", "related": [component['path']]})

    spec = component.get('spec')
    if spec:
        relationships.append({"relationship": "has_spec", "related": [spec.get('spec_file_path', 'unknown')]})
        relationships.append({"relationship": "has_spec_status", "related": [spec.get('status', 'draft')]})

    return {"concept_name": concept_name, "concept": concept, "relationships": relationships}


def deliverable_to_concept(project_id: str, feature_name: str, component_name: str, deliverable_name: str, deliverable: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GIINT Deliverable to Carton concept format. All model fields → typed relationships."""
    concept_name = get_deliverable_concept_name(project_id, feature_name, component_name, deliverable_name)
    concept = f"GIINT Deliverable: {deliverable_name} in component {component_name}, feature {feature_name}, project {project_id}."

    relationships = [
        {"relationship": "is_a", "related": ["GIINT_Deliverable"]},
        {"relationship": "part_of", "related": [get_component_concept_name(project_id, feature_name, component_name)]},
    ]

    spec = deliverable.get('spec')
    if spec:
        relationships.append({"relationship": "has_spec", "related": [spec.get('spec_file_path', 'unknown')]})
        relationships.append({"relationship": "has_spec_status", "related": [spec.get('status', 'draft')]})

    # Covers component link
    if deliverable.get('covers_component'):
        relationships.append({"relationship": "covers_component", "related": [deliverable['covers_component']]})

    # OperadicFlow links
    for flow_id in deliverable.get('operadic_flow_ids', []):
        relationships.append({"relationship": "has_operadic_flow", "related": [flow_id]})

    return {"concept_name": concept_name, "concept": concept, "relationships": relationships}


def task_to_concept(project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GIINT Task to Carton concept format. All model fields → typed relationships."""
    concept_name = get_task_concept_name(project_id, feature_name, component_name, deliverable_name, task_id)
    concept = f"GIINT Task: {task_id} in deliverable {deliverable_name}, component {component_name}."

    # Status mapping
    status_map = {
        'ready': 'Task_Ready', 'in_progress': 'Task_In_Progress',
        'in_review': 'Task_In_Review', 'done': 'Task_Done', 'blocked': 'Task_Blocked',
    }
    status = task.get('status', 'ready')

    relationships = [
        {"relationship": "is_a", "related": ["GIINT_Task"]},
        {"relationship": "part_of", "related": [get_deliverable_concept_name(project_id, feature_name, component_name, deliverable_name)]},
        {"relationship": "has_status", "related": [status_map.get(status, "Task_Ready")]},
        {"relationship": "has_assignee", "related": [task.get('assignee', 'UNKNOWN')]},
    ]

    # Agent/human identity
    if task.get('agent_id'):
        relationships.append({"relationship": "has_agent_id", "related": [task['agent_id']]})
    if task.get('human_name'):
        relationships.append({"relationship": "has_human_name", "related": [task['human_name']]})

    # Blocked info
    if task.get('is_blocked') and task.get('blocked_description'):
        relationships.append({"relationship": "has_blocked_reason", "related": [task['blocked_description']]})

    # Spec
    spec = task.get('spec')
    if spec:
        relationships.append({"relationship": "has_spec", "related": [spec.get('spec_file_path', 'unknown')]})
        relationships.append({"relationship": "has_spec_status", "related": [spec.get('status', 'draft')]})

    # GitHub integration
    if task.get('github_issue_id'):
        relationships.append({"relationship": "has_github_issue", "related": [task['github_issue_id']]})
    if task.get('github_issue_url'):
        relationships.append({"relationship": "has_github_issue_url", "related": [task['github_issue_url']]})

    # Claude Code bridge
    if task.get('claude_task_id'):
        relationships.append({"relationship": "has_claude_task_id", "related": [task['claude_task_id']]})

    # Context metadata
    if task.get('files_touched'):
        relationships.append({"relationship": "has_files_touched", "related": task['files_touched']})
    if task.get('lines_that_matter'):
        relationships.append({"relationship": "has_lines_that_matter", "related": [task['lines_that_matter']]})
    if task.get('context_deps'):
        relationships.append({"relationship": "has_context_deps", "related": task['context_deps']})
    if task.get('key_insight'):
        relationships.append({"relationship": "has_key_insight", "related": [task['key_insight']]})

    return {"concept_name": concept_name, "concept": concept, "relationships": relationships}


# ============================================================================
# SYNC FUNCTIONS - Write to Carton
# ============================================================================

def sync_project_to_carton(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync GIINT Project to Carton knowledge graph with FULL ontology.

    Builds the ENTIRE relational network in ONE observation batch:
    - Project with HAS_FEATURE → features
    - Feature with PART_OF → project, HAS_COMPONENT → components
    - Component with PART_OF → feature, HAS_DELIVERABLE → deliverables
    - Deliverable with PART_OF → component, HAS_TASK → tasks
    - Task with PART_OF → deliverable

    This enables full graph traversal and reasoning about the entire hierarchy.

    Args:
        project: Project dict from Pydantic model

    Returns:
        Sync result with success status and concept count
    """
    try:
        project_id = project["project_id"]
        logger.info(f"Starting Carton sync for project: {project_id}")

        # Collect ALL concepts from the entire hierarchy
        concepts = []

        # 1. Build project concept with HAS_FEATURE relationships
        project_concept = project_to_concept(project)
        features = project.get("features", {})

        # Add HAS_FEATURE relationships (parent → children)
        feature_concept_names = []
        for feature_name in features.keys():
            feature_concept_names.append(get_feature_concept_name(project_id, feature_name))

        if feature_concept_names:
            project_concept["relationships"].append({
                "relationship": "has_feature",
                "related": feature_concept_names
            })

        concepts.append({
            "name": project_concept["concept_name"],
            "description": project_concept["concept"],
            "relationships": project_concept["relationships"]
        })

        # 2. Walk features → components → deliverables → tasks
        for feature_name, feature_data in features.items():
            feature_concept = feature_to_concept(project_id, feature_name, feature_data)
            components = feature_data.get("components", {})

            # Add HAS_COMPONENT relationships
            component_concept_names = []
            for component_name in components.keys():
                component_concept_names.append(
                    get_component_concept_name(project_id, feature_name, component_name)
                )

            if component_concept_names:
                feature_concept["relationships"].append({
                    "relationship": "has_component",
                    "related": component_concept_names
                })

            concepts.append({
                "name": feature_concept["concept_name"],
                "description": feature_concept["concept"],
                "relationships": feature_concept["relationships"]
            })

            # 3. Walk components
            for component_name, component_data in components.items():
                component_concept = component_to_concept(
                    project_id, feature_name, component_name, component_data
                )
                deliverables = component_data.get("deliverables", {})

                # Add HAS_DELIVERABLE relationships
                deliverable_concept_names = []
                for deliverable_name in deliverables.keys():
                    deliverable_concept_names.append(
                        get_deliverable_concept_name(
                            project_id, feature_name, component_name, deliverable_name
                        )
                    )

                if deliverable_concept_names:
                    component_concept["relationships"].append({
                        "relationship": "has_deliverable",
                        "related": deliverable_concept_names
                    })

                concepts.append({
                    "name": component_concept["concept_name"],
                    "description": component_concept["concept"],
                    "relationships": component_concept["relationships"]
                })

                # 4. Walk deliverables
                for deliverable_name, deliverable_data in deliverables.items():
                    deliverable_concept = deliverable_to_concept(
                        project_id, feature_name, component_name, deliverable_name, deliverable_data
                    )
                    tasks = deliverable_data.get("tasks", {})

                    # Add HAS_TASK relationships
                    task_concept_names = []
                    for task_id in tasks.keys():
                        task_concept_names.append(
                            get_task_concept_name(
                                project_id, feature_name, component_name, deliverable_name, task_id
                            )
                        )

                    if task_concept_names:
                        deliverable_concept["relationships"].append({
                            "relationship": "has_task",
                            "related": task_concept_names
                        })

                    concepts.append({
                        "name": deliverable_concept["concept_name"],
                        "description": deliverable_concept["concept"],
                        "relationships": deliverable_concept["relationships"]
                    })

                    # 5. Walk tasks (leaf nodes)
                    for task_id, task_data in tasks.items():
                        task_concept = task_to_concept(
                            project_id, feature_name, component_name,
                            deliverable_name, task_id, task_data
                        )
                        concepts.append({
                            "name": task_concept["concept_name"],
                            "description": task_concept["concept"],
                            "relationships": task_concept["relationships"]
                        })

        # Submit ALL concepts (each queued with raw_concept=True, no observation wrapper)
        from carton_mcp.add_concept_tool import add_concept_tool_func

        for concept in concepts:
            add_concept_tool_func(
                concept_name=concept["name"],
                description=concept["description"],
                relationships=concept["relationships"],
                hide_youknow=False
            )

        logger.info(f"Successfully synced project {project_id} to Carton with {len(concepts)} concepts")
        return {
            "success": True,
            "project_id": project_id,
            "concepts_synced": len(concepts),
            "features": len(features)
        }

    except Exception as e:
        logger.error(f"Failed to sync project to Carton: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def sync_feature_to_carton(project_id: str, feature_name: str, feature: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync GIINT Feature to Carton with FULL subgraph ontology.

    Builds: Feature → Components → Deliverables → Tasks in one batch.
    """
    try:
        concepts = []

        # 1. Build feature concept with HAS_COMPONENT
        feature_concept = feature_to_concept(project_id, feature_name, feature)
        components = feature.get("components", {})

        component_concept_names = [
            get_component_concept_name(project_id, feature_name, cn)
            for cn in components.keys()
        ]
        if component_concept_names:
            feature_concept["relationships"].append({
                "relationship": "has_component",
                "related": component_concept_names
            })

        concepts.append({
            "name": feature_concept["concept_name"],
            "description": feature_concept["concept"],
            "relationships": feature_concept["relationships"]
        })

        # 2. Walk components → deliverables → tasks
        for component_name, component_data in components.items():
            component_concept = component_to_concept(
                project_id, feature_name, component_name, component_data
            )
            deliverables = component_data.get("deliverables", {})

            deliverable_concept_names = [
                get_deliverable_concept_name(project_id, feature_name, component_name, dn)
                for dn in deliverables.keys()
            ]
            if deliverable_concept_names:
                component_concept["relationships"].append({
                    "relationship": "has_deliverable",
                    "related": deliverable_concept_names
                })

            concepts.append({
                "name": component_concept["concept_name"],
                "description": component_concept["concept"],
                "relationships": component_concept["relationships"]
            })

            for deliverable_name, deliverable_data in deliverables.items():
                deliverable_concept = deliverable_to_concept(
                    project_id, feature_name, component_name, deliverable_name, deliverable_data
                )
                tasks = deliverable_data.get("tasks", {})

                task_concept_names = [
                    get_task_concept_name(project_id, feature_name, component_name, deliverable_name, tid)
                    for tid in tasks.keys()
                ]
                if task_concept_names:
                    deliverable_concept["relationships"].append({
                        "relationship": "has_task",
                        "related": task_concept_names
                    })

                concepts.append({
                    "name": deliverable_concept["concept_name"],
                    "description": deliverable_concept["concept"],
                    "relationships": deliverable_concept["relationships"]
                })

                for task_id, task_data in tasks.items():
                    task_concept = task_to_concept(
                        project_id, feature_name, component_name, deliverable_name, task_id, task_data
                    )
                    concepts.append({
                        "name": task_concept["concept_name"],
                        "description": task_concept["concept"],
                        "relationships": task_concept["relationships"]
                    })

        # Submit all concepts (each queued with raw_concept=True, no observation wrapper)
        from carton_mcp.add_concept_tool import add_concept_tool_func
        for concept in concepts:
            add_concept_tool_func(concept["name"], concept["description"], concept["relationships"], hide_youknow=False)

        return {"success": True, "feature_name": feature_name, "concepts_synced": len(concepts)}

    except Exception as e:
        logger.error(f"Failed to sync feature {feature_name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def sync_component_to_carton(project_id: str, feature_name: str, component_name: str, component: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync GIINT Component to Carton with FULL subgraph ontology.

    Builds: Component → Deliverables → Tasks in one batch.
    """
    try:
        concepts = []

        # 1. Build component concept with HAS_DELIVERABLE
        component_concept = component_to_concept(project_id, feature_name, component_name, component)
        deliverables = component.get("deliverables", {})

        deliverable_concept_names = [
            get_deliverable_concept_name(project_id, feature_name, component_name, dn)
            for dn in deliverables.keys()
        ]
        if deliverable_concept_names:
            component_concept["relationships"].append({
                "relationship": "has_deliverable",
                "related": deliverable_concept_names
            })

        concepts.append({
            "name": component_concept["concept_name"],
            "description": component_concept["concept"],
            "relationships": component_concept["relationships"]
        })

        # 2. Walk deliverables → tasks
        for deliverable_name, deliverable_data in deliverables.items():
            deliverable_concept = deliverable_to_concept(
                project_id, feature_name, component_name, deliverable_name, deliverable_data
            )
            tasks = deliverable_data.get("tasks", {})

            task_concept_names = [
                get_task_concept_name(project_id, feature_name, component_name, deliverable_name, tid)
                for tid in tasks.keys()
            ]
            if task_concept_names:
                deliverable_concept["relationships"].append({
                    "relationship": "has_task",
                    "related": task_concept_names
                })

            concepts.append({
                "name": deliverable_concept["concept_name"],
                "description": deliverable_concept["concept"],
                "relationships": deliverable_concept["relationships"]
            })

            for task_id, task_data in tasks.items():
                task_concept = task_to_concept(
                    project_id, feature_name, component_name, deliverable_name, task_id, task_data
                )
                concepts.append({
                    "name": task_concept["concept_name"],
                    "description": task_concept["concept"],
                    "relationships": task_concept["relationships"]
                })

        # Submit all concepts (each queued with raw_concept=True, no observation wrapper)
        from carton_mcp.add_concept_tool import add_concept_tool_func
        for concept in concepts:
            add_concept_tool_func(concept["name"], concept["description"], concept["relationships"], hide_youknow=False)

        return {"success": True, "component_name": component_name, "concepts_synced": len(concepts)}

    except Exception as e:
        logger.error(f"Failed to sync component {component_name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def sync_deliverable_to_carton(project_id: str, feature_name: str, component_name: str, deliverable_name: str, deliverable: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync GIINT Deliverable to Carton with FULL subgraph ontology.

    Builds: Deliverable → Tasks in one batch.
    """
    try:
        concepts = []

        # 1. Build deliverable concept with HAS_TASK
        deliverable_concept = deliverable_to_concept(
            project_id, feature_name, component_name, deliverable_name, deliverable
        )
        tasks = deliverable.get("tasks", {})

        task_concept_names = [
            get_task_concept_name(project_id, feature_name, component_name, deliverable_name, tid)
            for tid in tasks.keys()
        ]
        if task_concept_names:
            deliverable_concept["relationships"].append({
                "relationship": "has_task",
                "related": task_concept_names
            })

        concepts.append({
            "name": deliverable_concept["concept_name"],
            "description": deliverable_concept["concept"],
            "relationships": deliverable_concept["relationships"]
        })

        # 2. Build task concepts
        for task_id, task_data in tasks.items():
            task_concept = task_to_concept(
                project_id, feature_name, component_name, deliverable_name, task_id, task_data
            )
            concepts.append({
                "name": task_concept["concept_name"],
                "description": task_concept["concept"],
                "relationships": task_concept["relationships"]
            })

        # Submit all concepts (each queued with raw_concept=True, no observation wrapper)
        from carton_mcp.add_concept_tool import add_concept_tool_func
        for concept in concepts:
            add_concept_tool_func(concept["name"], concept["description"], concept["relationships"], hide_youknow=False)

        return {"success": True, "deliverable_name": deliverable_name, "concepts_synced": len(concepts)}

    except Exception as e:
        logger.error(f"Failed to sync deliverable {deliverable_name}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def sync_task_to_carton(project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync GIINT Task to Carton.

    Task is a leaf node - syncs single concept via observation batch.
    """
    try:
        task_concept = task_to_concept(
            project_id, feature_name, component_name, deliverable_name, task_id, task
        )

        from carton_mcp.add_concept_tool import add_concept_tool_func
        add_concept_tool_func(
            task_concept["concept_name"],
            task_concept["concept"],
            task_concept["relationships"],
            hide_youknow=False
        )

        return {"success": True, "task_id": task_id, "concepts_synced": 1}

    except Exception as e:
        logger.error(f"Failed to sync task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def update_task_in_carton(project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing task in Carton.

    Uses desc_update_mode="replace" to update the task concept with new status/metadata.
    """
    try:
        task_concept = task_to_concept(
            project_id, feature_name, component_name, deliverable_name, task_id, task
        )

        from carton_mcp.add_concept_tool import add_concept_tool_func
        add_concept_tool_func(
            task_concept["concept_name"],
            task_concept["concept"],
            task_concept["relationships"],
            desc_update_mode="replace",
            hide_youknow=False
        )

        logger.info(f"Updated task {task_id} in Carton")
        return {"success": True, "task_id": task_id}

    except Exception as e:
        logger.error(f"Failed to update task {task_id} in Carton: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ============================================================================
# GAP DETECTION - Find Components without Emanations
# ============================================================================

# AI Integration types for emanation scoring
AI_INTEGRATION_TYPES = ["Skill", "MCP", "Flight", "Hook", "Subagent", "Plugin"]


def get_emanation_gaps(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Find Components without emanation coverage across 6 AI integration types.

    AI Integration Types (full emanation = all 6):
    1. Skill - understand/preflight skills that cover the component
    2. MCP - MCP tools that interact with the component
    3. Flight - flight configs that build/modify the component
    4. Hook - hooks that monitor/react to the component
    5. Subagent - subagents that work on the component
    6. Plugin - plugins that package the component

    Checks AI_Integrations feature for deliverables with covers_component set,
    or falls back to naming convention matching.

    Args:
        project_id: Optional project to check (None = all projects)

    Returns:
        Gap analysis with coverage stats and missing items per type
    """
    try:
        from .projects import get_registry

        registry = get_registry()
        projects = registry._load_projects()

        if project_id and project_id not in projects:
            return {"error": f"Project {project_id} not found"}

        check_projects = {project_id: projects[project_id]} if project_id else projects

        gaps = {
            "total_components": 0,
            "components_with_full_emanation": 0,
            "coverage_percent": 0.0,
            "by_type": {t: {"covered": 0, "missing": []} for t in AI_INTEGRATION_TYPES},
            "by_project": {}
        }

        for pid, project in check_projects.items():
            # Build coverage map from AI_Integrations feature
            ai_coverage = _build_ai_coverage_map(project)

            project_gaps = {
                "missing_emanations": [],
                "components": 0,
                "with_full_emanation": 0,
                "coverage_by_type": {t: 0 for t in AI_INTEGRATION_TYPES}
            }

            for feature_name, feature in project.features.items():
                # Skip AI_Integrations feature itself
                if feature_name == "AI_Integrations":
                    continue

                for component_name, component in feature.components.items():
                    gaps["total_components"] += 1
                    project_gaps["components"] += 1
                    component_path = f"{pid}/{feature_name}/{component_name}"

                    # Check coverage for each AI integration type
                    missing_types = []
                    for ai_type in AI_INTEGRATION_TYPES:
                        has_coverage = _check_ai_coverage(
                            component_path, component_name, ai_type,
                            ai_coverage, component
                        )
                        if has_coverage:
                            gaps["by_type"][ai_type]["covered"] += 1
                            project_gaps["coverage_by_type"][ai_type] += 1
                        else:
                            missing_types.append(ai_type)
                            gaps["by_type"][ai_type]["missing"].append(component_path)

                    # Full emanation = all 6 types covered
                    if not missing_types:
                        gaps["components_with_full_emanation"] += 1
                        project_gaps["with_full_emanation"] += 1
                    else:
                        project_gaps["missing_emanations"].append({
                            "component": component_path,
                            "missing": missing_types
                        })

            gaps["by_project"][pid] = project_gaps

        # Calculate coverage
        if gaps["total_components"] > 0:
            gaps["coverage_percent"] = round(
                (gaps["components_with_full_emanation"] / gaps["total_components"]) * 100, 1
            )

        return {"success": True, "gaps": gaps}

    except Exception as e:
        logger.error(f"Failed to get emanation gaps: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def _scan_claude_folder(project_dir: str) -> Dict[str, List[str]]:
    """
    Scan project's .claude folder for AI integrations.

    Returns: {ai_type: [list of found items]}
    """
    from pathlib import Path

    claude_dir = Path(project_dir) / ".claude"
    found = {t: [] for t in AI_INTEGRATION_TYPES}

    if not claude_dir.exists():
        return found

    # Scan hooks/
    hooks_dir = claude_dir / "hooks"
    if hooks_dir.exists():
        for f in hooks_dir.glob("*.py"):
            found["Hook"].append(f.stem)

    # Scan skills/ (local project skills)
    skills_dir = claude_dir / "skills"
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                found["Skill"].append(d.name)

    # Scan agents/ or check settings.json for agentCommands
    agents_dir = claude_dir / "agents"
    if agents_dir.exists():
        for f in agents_dir.glob("*.md"):
            found["Subagent"].append(f.stem)

    # Check settings.json for subagents
    settings_file = claude_dir / "settings.json"
    if settings_file.exists():
        try:
            import json
            settings = json.loads(settings_file.read_text())
            agent_commands = settings.get("agentCommands", {})
            for agent_name in agent_commands.keys():
                if agent_name not in found["Subagent"]:
                    found["Subagent"].append(agent_name)
        except Exception:
            pass

    # Scan for flight configs (could be in various places)
    # Check commands/ for slash commands that might indicate flights
    commands_dir = claude_dir / "commands"
    if commands_dir.exists():
        for f in commands_dir.glob("*.md"):
            found["Flight"].append(f.stem)

    return found


def _build_ai_coverage_map(project) -> Dict[str, Dict[str, List[str]]]:
    """
    Build map of which components are covered by AI integrations.

    Combines:
    1. Filesystem scan of project's .claude folder
    2. AI_Integrations feature in GIINT project model

    Returns: {ai_type: {component_path: [deliverable_names]}}
    """
    coverage = {t: {} for t in AI_INTEGRATION_TYPES}

    # First: scan filesystem for actual AI integrations
    project_dir = getattr(project, 'project_dir', None)
    if project_dir:
        fs_items = _scan_claude_folder(project_dir)
        # Store as "_filesystem_" to indicate these exist but aren't mapped to specific components
        for ai_type, items in fs_items.items():
            if items:
                coverage[ai_type]["_filesystem_"] = items

    # Second: check AI_Integrations feature for explicit mappings
    ai_feature = project.features.get("AI_Integrations")
    if not ai_feature:
        return coverage

    for ai_type in AI_INTEGRATION_TYPES:
        type_component = ai_feature.components.get(ai_type)
        if not type_component:
            continue

        for deliv_name, deliverable in type_component.deliverables.items():
            # Use explicit covers_component if set
            if deliverable.covers_component:
                target = deliverable.covers_component
                if target not in coverage[ai_type]:
                    coverage[ai_type][target] = []
                coverage[ai_type][target].append(deliv_name)

    return coverage


def _check_ai_coverage(
    component_path: str,
    component_name: str,
    ai_type: str,
    ai_coverage: Dict[str, Dict[str, List[str]]],
    component
) -> bool:
    """
    Check if a component has coverage from a specific AI integration type.

    Checks:
    1. Filesystem scan found items in .claude folder (project has this type)
    2. Explicit coverage via covers_component field
    3. Legacy: component's own deliverables with type keywords
    """
    type_coverage = ai_coverage.get(ai_type, {})

    # Check if filesystem scan found ANY items of this type for the project
    # This means the project HAS this integration type available
    if "_filesystem_" in type_coverage and type_coverage["_filesystem_"]:
        return True

    # Check explicit coverage map (component-specific)
    if component_path in type_coverage or component_name in type_coverage:
        return True

    # Legacy fallback: check component's own deliverables for keywords
    deliverable_names = list(component.deliverables.keys())

    if ai_type == "Skill":
        return any(
            "understand" in d.lower() or "preflight" in d.lower() or "make-" in d.lower()
            for d in deliverable_names
        )
    elif ai_type == "MCP":
        return any("mcp" in d.lower() for d in deliverable_names)
    elif ai_type == "Flight":
        return any(
            "flight" in d.lower() or "_flight_config" in d.lower()
            for d in deliverable_names
        )
    elif ai_type == "Hook":
        return any("hook" in d.lower() for d in deliverable_names)
    elif ai_type == "Subagent":
        return any("subagent" in d.lower() or "agent" in d.lower() for d in deliverable_names)
    elif ai_type == "Plugin":
        return any("plugin" in d.lower() for d in deliverable_names)

    return False


def format_emanation_hud(gaps: Dict[str, Any]) -> str:
    """
    Format emanation gaps as HUD string for display.

    Args:
        gaps: Gap data from get_emanation_gaps()

    Returns:
        Formatted HUD string
    """
    if not gaps.get("success"):
        return f"⚠️ Gap detection error: {gaps.get('error', 'unknown')}"

    g = gaps["gaps"]
    total = g["total_components"]
    full = g["components_with_full_emanation"]
    pct = g["coverage_percent"]

    lines = [
        "┌─────────────────────────────────────────────────────────┐",
        "│ EMANATION COVERAGE (6 AI Integration Types)             │",
        "├─────────────────────────────────────────────────────────┤",
        f"│ Full Coverage: {full}/{total} components ({pct}%)",
        "│",
        "│ Coverage by Type:",
    ]

    # Show coverage per AI integration type
    by_type = g.get("by_type", {})
    for ai_type in AI_INTEGRATION_TYPES:
        type_data = by_type.get(ai_type, {"covered": 0, "missing": []})
        covered = type_data["covered"]
        type_pct = round((covered / total) * 100, 1) if total > 0 else 0
        icon = "✓" if type_pct == 100 else "○" if type_pct > 0 else "✗"
        lines.append(f"│   {icon} {ai_type}: {covered}/{total} ({type_pct}%)")

    # Show top 5 missing emanations
    all_missing = []
    for pid, pdata in g["by_project"].items():
        all_missing.extend(pdata.get("missing_emanations", []))

    if all_missing[:5]:
        lines.append("│")
        lines.append("│ Components needing coverage:")
        for item in all_missing[:5]:
            missing_str = ", ".join(item["missing"][:3])
            if len(item["missing"]) > 3:
                missing_str += f" +{len(item['missing']) - 3}"
            lines.append(f"│   • {item['component']}: {missing_str}")
        if len(all_missing) > 5:
            lines.append(f"│   ... and {len(all_missing) - 5} more")

    lines.append("└─────────────────────────────────────────────────────────┘")
    return "\n".join(lines)


def get_skills_without_describes() -> Dict[str, Any]:
    """
    Find Skills in CartON that don't have DESCRIBES relationships to Components.

    Queries CartON for:
    1. All concepts with IS_A Skill
    2. Filter those without DESCRIBES relationships

    Returns:
        Dict with orphan skills and coverage stats
    """
    try:
        from carton_mcp.carton_mcp import query_wiki_graph

        # Get all skills
        all_skills_query = """
        MATCH (s:Wiki)-[:IS_A]->(:Wiki {n: "Skill"})
        RETURN s.n as name, s.d as description
        """
        all_skills_result = query_wiki_graph(all_skills_query)

        # Get skills with DESCRIBES relationships
        skills_with_describes_query = """
        MATCH (s:Wiki)-[:IS_A]->(:Wiki {n: "Skill"})
        MATCH (s)-[:DESCRIBES]->(c:Wiki)
        RETURN DISTINCT s.n as name, c.n as component
        """
        describes_result = query_wiki_graph(skills_with_describes_query)

        # Parse results
        import json
        all_skills_data = json.loads(all_skills_result) if isinstance(all_skills_result, str) else all_skills_result
        describes_data = json.loads(describes_result) if isinstance(describes_result, str) else describes_result

        all_skill_names = set()
        if all_skills_data.get("success") and all_skills_data.get("data"):
            for row in all_skills_data["data"]:
                if row.get("name"):
                    all_skill_names.add(row["name"])

        skills_with_describes = set()
        skill_to_component = {}
        if describes_data.get("success") and describes_data.get("data"):
            for row in describes_data["data"]:
                if row.get("name"):
                    skills_with_describes.add(row["name"])
                    skill_to_component[row["name"]] = row.get("component", "unknown")

        orphan_skills = all_skill_names - skills_with_describes

        total = len(all_skill_names)
        with_describes = len(skills_with_describes)
        coverage = (with_describes / total * 100) if total > 0 else 0

        return {
            "success": True,
            "total_skills": total,
            "skills_with_describes": with_describes,
            "orphan_skills": list(orphan_skills),
            "coverage_percent": round(coverage, 1),
            "skill_to_component": skill_to_component
        }

    except Exception as e:
        logger.error(f"Failed to get skills without DESCRIBES: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
