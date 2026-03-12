#!/usr/bin/env python3
"""
LLM Intelligence MCP Server

Forces systematic multi-fire LLM responses to overcome embedding geometry limitations.
The conversation becomes the thinking space, QA files contain the actual responses.
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from fastmcp import FastMCP, Context

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("llm-intelligence")

# Configuration
RESPONSE_DIR = Path(os.environ.get("LLM_INTELLIGENCE_DIR", "/tmp/llm_intelligence_responses"))
RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

def get_qa_path(qa_id: str) -> Path:
    """Get directory path for a QA session."""
    return RESPONSE_DIR / qa_id

def get_response_file(qa_id: str, response_num: int) -> Path:
    """Get path for a specific response file."""
    qa_path = get_qa_path(qa_id)
    return qa_path / f"response_{response_num:03d}.md"

def load_qa_metadata(qa_id: str) -> Optional[Dict[str, Any]]:
    """Load metadata for a QA session."""
    metadata_path = get_qa_path(qa_id) / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            return json.load(f)
    return None

def save_qa_metadata(qa_id: str, metadata: Dict[str, Any]):
    """Save metadata for a QA session."""
    metadata_path = get_qa_path(qa_id) / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

def get_all_sessions(filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[Dict[str, Any]]:
    """
    Get all QA sessions with optional filtering.
    
    Args:
        filter_fn: Optional function to filter sessions
        
    Returns:
        List of session metadata matching the filter
    """
    sessions = []
    
    for qa_dir in RESPONSE_DIR.iterdir():
        if qa_dir.is_dir():
            metadata = load_qa_metadata(qa_dir.name)
            if metadata and (filter_fn is None or filter_fn(metadata)):
                sessions.append(metadata)
    
    logger.info(f"Found {len(sessions)} sessions" + (f" (filtered)" if filter_fn else ""))
    return sessions

def get_sessions_by_project(project_id: str) -> List[Dict[str, Any]]:
    """Get all sessions for a specific project."""
    return get_all_sessions(lambda m: m.get("project_id") == project_id)

def get_sessions_by_tag(tag: str) -> List[Dict[str, Any]]:
    """Get all sessions containing a specific tag."""
    return get_all_sessions(lambda m: tag in m.get("tags", []))

def get_sessions_by_tracking_field(field: str, value: str) -> List[Dict[str, Any]]:
    """Get all sessions with a specific tracking field value."""
    return get_all_sessions(lambda m: m.get("tracking", {}).get(field) == value)

@mcp.tool()
async def respond(
    ctx: Context, 
    qa_id: str, 
    response_text: str, 
    one_liner: str,
    key_tags: List[str],
    involved_files: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    feature: Optional[str] = None,
    component: Optional[str] = None,
    deliverable: Optional[str] = None,
    subtask: Optional[str] = None,
    task: Optional[str] = None,
    workflow_id: Optional[str] = None,
    is_from_waypoint: bool = False
) -> Dict[str, Any]:
    """
    Create the actual response in the QA system with emergent tracking data.
    
    Args:
        qa_id: The QA session ID (create new if doesn't exist)
        response_text: The actual response content
        one_liner: One-line summary of this response
        key_tags: Key tags/concepts in this response
        involved_files: Files involved in this response
        project_id: Project this response belongs to
        feature: Feature within project (emergent)
        component: Component within feature (emergent)
        deliverable: Deliverable within component (emergent)
        subtask: Contextual subtask (defined per situation)
        task: Main task (always exists)
        workflow_id: Workflow/waypoint ID if applicable
        is_from_waypoint: Whether this comes from waypoint system
        
    Returns:
        Response metadata and file location
    """
    qa_path = get_qa_path(qa_id)
    
    # Initialize session if new
    if not qa_path.exists():
        qa_path.mkdir(parents=True, exist_ok=True)
        metadata = {
            "qa_id": qa_id,
            "created_at": datetime.now().isoformat(),
            "response_count": 0,
            "status": "active",
            "tags": [],
            "files": [],
            "project_id": project_id,
            "tracking": {
                "feature": feature,
                "component": component,
                "deliverable": deliverable,
                "task": task,
                "workflow_id": workflow_id,
                "is_from_waypoint": is_from_waypoint
            }
        }
    else:
        metadata = load_qa_metadata(qa_id)
    
    # Increment response count
    response_num = metadata["response_count"] + 1
    metadata["response_count"] = response_num
    metadata["last_updated"] = datetime.now().isoformat()
    
    # Update tags and files
    metadata["tags"] = list(set(metadata.get("tags", []) + key_tags))
    if involved_files:
        metadata["files"] = list(set(metadata.get("files", []) + involved_files))
    
    # Create response file with structured format including emergent tracking
    response_file = get_response_file(qa_id, response_num)
    with open(response_file, "w") as f:
        f.write(f"# Response {response_num}: {one_liner}\n\n")
        f.write(f"**QA_ID**: `{qa_id}`\n")
        f.write(f"**Timestamp**: {datetime.now().isoformat()}\n")
        f.write(f"**Tags**: {', '.join(key_tags)}\n")
        if involved_files:
            f.write(f"**Files**: {', '.join(involved_files)}\n")
        
        # Emergent tracking data
        if project_id:
            f.write(f"**Project**: {project_id}\n")
        if feature:
            f.write(f"**Feature**: {feature}\n")
        if component:
            f.write(f"**Component**: {component}\n")
        if deliverable:
            f.write(f"**Deliverable**: {deliverable}\n")
        if subtask:
            f.write(f"**Subtask**: {subtask}\n")
        if task:
            f.write(f"**Task**: {task}\n")
        if workflow_id:
            f.write(f"**Workflow**: {workflow_id}\n")
        if is_from_waypoint:
            f.write(f"**From Waypoint**: Yes\n")
            
        f.write("\n---\n\n")
        f.write(response_text)
    
    # Save updated metadata
    save_qa_metadata(qa_id, metadata)
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "file": str(response_file),
        "one_liner": one_liner,
        "tags": key_tags,
        "project_id": project_id,
        "tracking": {
            "feature": feature,
            "component": component,
            "deliverable": deliverable,
            "subtask": subtask,
            "task": task,
            "workflow_id": workflow_id,
            "is_from_waypoint": is_from_waypoint
        },
        "message": f"Response {response_num} saved to {qa_id}"
    }

@mcp.tool()
async def get_qa_context(ctx: Context, qa_id: str, last_n: int = 3) -> Dict[str, Any]:
    """
    Get context from previous responses in this QA session.
    
    Args:
        qa_id: The QA session ID
        last_n: Number of recent responses to retrieve
        
    Returns:
        Previous responses for context
    """
    metadata = load_qa_metadata(qa_id)
    if not metadata:
        return {"error": f"QA session {qa_id} not found"}
    
    response_count = metadata["response_count"]
    responses = []
    
    start = max(1, response_count - last_n + 1)
    for i in range(start, response_count + 1):
        response_file = get_response_file(qa_id, i)
        if response_file.exists():
            with open(response_file, "r") as f:
                content = f.read()
            responses.append({
                "response_num": i,
                "content": content
            })
    
    return {
        "qa_id": qa_id,
        "total_responses": response_count,
        "retrieved": len(responses),
        "responses": responses,
        "tags": metadata.get("tags", []),
        "files": metadata.get("files", [])
    }

@mcp.tool()
async def list_qa_sessions(ctx: Context, tag: Optional[str] = None) -> Dict[str, Any]:
    """
    List all QA sessions, optionally filtered by tag.
    
    Args:
        tag: Optional tag to filter by
        
    Returns:
        List of QA sessions
    """
    logger.info(f"Listing QA sessions" + (f" filtered by tag: {tag}" if tag else ""))
    
    # Use helper function with optional tag filter
    all_sessions = get_sessions_by_tag(tag) if tag else get_all_sessions()
    
    sessions = []
    for metadata in all_sessions:
        sessions.append({
            "qa_id": metadata["qa_id"],
            "created": metadata["created_at"],
            "updated": metadata.get("last_updated"),
            "responses": metadata["response_count"],
            "status": metadata.get("status", "unknown"),
            "tags": metadata.get("tags", []),
            "files": len(metadata.get("files", []))
        })
    
    # Sort by last updated
    sessions.sort(key=lambda x: x.get("updated") or x["created"], reverse=True)
    
    logger.info(f"Returned {len(sessions)} sessions")
    return {
        "sessions": sessions,
        "total": len(sessions),
        "filtered_by": tag
    }

@mcp.tool()
async def complete_qa_session(ctx: Context, qa_id: str, summary: str) -> Dict[str, str]:
    """
    Mark a QA session as complete with a summary.
    
    Args:
        qa_id: The QA session ID
        summary: Summary of the QA session
        
    Returns:
        Completion status
    """
    metadata = load_qa_metadata(qa_id)
    if not metadata:
        return {"error": f"QA session {qa_id} not found"}
    
    metadata["status"] = "complete"
    metadata["completed_at"] = datetime.now().isoformat()
    metadata["summary"] = summary
    
    save_qa_metadata(qa_id, metadata)
    
    # Create summary file
    summary_file = get_qa_path(qa_id) / "SUMMARY.md"
    with open(summary_file, "w") as f:
        f.write(f"# QA Session Summary: {qa_id}\n\n")
        f.write(f"**Total Responses**: {metadata['response_count']}\n")
        f.write(f"**Created**: {metadata['created_at']}\n")
        f.write(f"**Completed**: {metadata['completed_at']}\n")
        f.write(f"**Tags**: {', '.join(metadata.get('tags', []))}\n")
        f.write(f"**Files Involved**: {len(metadata.get('files', []))}\n\n")
        f.write("## Summary\n\n")
        f.write(summary)
    
    return {
        "qa_id": qa_id,
        "summary_file": str(summary_file),
        "message": f"QA session {qa_id} completed"
    }

@mcp.tool()
async def read_qa_response(ctx: Context, qa_id: str, response_num: int) -> Dict[str, Any]:
    """
    Read a specific response from a QA session.
    
    Args:
        qa_id: The QA session ID
        response_num: The response number
        
    Returns:
        The response content
    """
    response_file = get_response_file(qa_id, response_num)
    if not response_file.exists():
        return {"error": f"Response {response_num} not found in QA session {qa_id}"}
    
    with open(response_file, "r") as f:
        content = f.read()
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "content": content
    }

# Project Management Query Tools
@mcp.tool()
async def list_projects(ctx: Context) -> Dict[str, Any]:
    """
    List all projects with their metadata and statistics.
    
    Returns:
        All projects with metadata, QA counts, and recent activity
    """
    logger.info("Listing all projects with statistics")
    
    # Get all sessions that have project_id
    sessions_with_projects = get_all_sessions(lambda m: m.get("project_id") is not None)
    
    projects = {}
    
    for metadata in sessions_with_projects:
        project_id = metadata["project_id"]
        
        if project_id not in projects:
            projects[project_id] = {
                "project_id": project_id,
                "qa_sessions": [],
                "total_responses": 0,
                "features": set(),
                "components": set(),
                "deliverables": set(),
                "tasks": set(),
                "workflows": set(),
                "tags": set(),
                "first_created": None,
                "last_updated": None,
                "waypoint_sessions": 0
            }
        
        # Add session info
        projects[project_id]["qa_sessions"].append({
            "qa_id": metadata["qa_id"],
            "responses": metadata["response_count"],
            "created": metadata["created_at"],
            "updated": metadata.get("last_updated"),
            "status": metadata.get("status", "unknown")
        })
        
        projects[project_id]["total_responses"] += metadata["response_count"]
        projects[project_id]["tags"].update(metadata.get("tags", []))
        
        # Track emergent hierarchy
        tracking = metadata.get("tracking", {})
        if tracking.get("feature"):
            projects[project_id]["features"].add(tracking["feature"])
        if tracking.get("component"):
            projects[project_id]["components"].add(tracking["component"])
        if tracking.get("deliverable"):
            projects[project_id]["deliverables"].add(tracking["deliverable"])
        if tracking.get("task"):
            projects[project_id]["tasks"].add(tracking["task"])
        if tracking.get("workflow_id"):
            projects[project_id]["workflows"].add(tracking["workflow_id"])
        if tracking.get("is_from_waypoint"):
            projects[project_id]["waypoint_sessions"] += 1
        
        # Track dates
        created = metadata["created_at"]
        updated = metadata.get("last_updated", created)
        
        if not projects[project_id]["first_created"] or created < projects[project_id]["first_created"]:
            projects[project_id]["first_created"] = created
        if not projects[project_id]["last_updated"] or updated > projects[project_id]["last_updated"]:
            projects[project_id]["last_updated"] = updated
    
    # Convert sets to lists for JSON serialization
    for project in projects.values():
        project["features"] = list(project["features"])
        project["components"] = list(project["components"])
        project["deliverables"] = list(project["deliverables"])
        project["tasks"] = list(project["tasks"])
        project["workflows"] = list(project["workflows"])
        project["tags"] = list(project["tags"])
    
    # Sort projects by last activity
    sorted_projects = sorted(projects.values(), key=lambda x: x["last_updated"] or x["first_created"], reverse=True)
    
    logger.info(f"Found {len(projects)} projects with {sum(len(p['qa_sessions']) for p in projects.values())} total sessions")
    
    return {
        "projects": sorted_projects,
        "total_projects": len(projects),
        "total_qa_sessions": sum(len(p["qa_sessions"]) for p in projects.values()),
        "total_responses": sum(p["total_responses"] for p in projects.values())
    }

@mcp.tool()
async def get_project_overview(ctx: Context, project_id: str) -> Dict[str, Any]:
    """
    Get detailed overview of a specific project.
    
    Args:
        project_id: The project ID to get overview for
        
    Returns:
        Detailed project information including hierarchy and patterns
    """
    logger.info(f"Getting overview for project: {project_id}")
    
    project_sessions = get_sessions_by_project(project_id)
    
    if not project_sessions:
        logger.warning(f"Project {project_id} not found")
        return {"error": f"Project {project_id} not found"}
    
    # Aggregate project data
    total_responses = sum(s["response_count"] for s in project_sessions)
    all_tags = set()
    all_files = set()
    features = {}
    components = {}
    deliverables = {}
    tasks = {}
    workflows = set()
    waypoint_count = 0
    
    earliest = None
    latest = None
    
    for session in project_sessions:
        # Basic stats
        all_tags.update(session.get("tags", []))
        all_files.update(session.get("files", []))
        
        created = session["created_at"]
        updated = session.get("last_updated", created)
        
        if not earliest or created < earliest:
            earliest = created
        if not latest or updated > latest:
            latest = updated
        
        # Emergent tracking analysis
        tracking = session.get("tracking", {})
        
        if tracking.get("feature"):
            feature = tracking["feature"]
            if feature not in features:
                features[feature] = {"qa_sessions": [], "components": set(), "deliverables": set()}
            features[feature]["qa_sessions"].append(session["qa_id"])
            
            if tracking.get("component"):
                component = tracking["component"]
                features[feature]["components"].add(component)
                
                if component not in components:
                    components[component] = {"qa_sessions": [], "features": set(), "deliverables": set()}
                components[component]["qa_sessions"].append(session["qa_id"])
                components[component]["features"].add(feature)
                
                if tracking.get("deliverable"):
                    deliverable = tracking["deliverable"]
                    features[feature]["deliverables"].add(deliverable)
                    components[component]["deliverables"].add(deliverable)
                    
                    if deliverable not in deliverables:
                        deliverables[deliverable] = {"qa_sessions": [], "features": set(), "components": set()}
                    deliverables[deliverable]["qa_sessions"].append(session["qa_id"])
                    deliverables[deliverable]["features"].add(feature)
                    deliverables[deliverable]["components"].add(component)
        
        if tracking.get("task"):
            task = tracking["task"]
            if task not in tasks:
                tasks[task] = {"qa_sessions": [], "subtasks": set()}
            tasks[task]["qa_sessions"].append(session["qa_id"])
            if tracking.get("subtask"):
                tasks[task]["subtasks"].add(tracking["subtask"])
        
        if tracking.get("workflow_id"):
            workflows.add(tracking["workflow_id"])
        
        if tracking.get("is_from_waypoint"):
            waypoint_count += 1
    
    # Convert sets to lists
    for feature_data in features.values():
        feature_data["components"] = list(feature_data["components"])
        feature_data["deliverables"] = list(feature_data["deliverables"])
    
    for component_data in components.values():
        component_data["features"] = list(component_data["features"])
        component_data["deliverables"] = list(component_data["deliverables"])
    
    for deliverable_data in deliverables.values():
        deliverable_data["features"] = list(deliverable_data["features"])
        deliverable_data["components"] = list(deliverable_data["components"])
    
    for task_data in tasks.values():
        task_data["subtasks"] = list(task_data["subtasks"])
    
    return {
        "project_id": project_id,
        "summary": {
            "qa_sessions": len(project_sessions),
            "total_responses": total_responses,
            "unique_tags": len(all_tags),
            "involved_files": len(all_files),
            "waypoint_sessions": waypoint_count,
            "created": earliest,
            "last_updated": latest
        },
        "emergent_hierarchy": {
            "features": features,
            "components": components,
            "deliverables": deliverables,
            "tasks": tasks,
            "workflows": list(workflows)
        },
        "tags": list(all_tags),
        "files": list(all_files),
        "qa_sessions": [s["qa_id"] for s in project_sessions]
    }

@mcp.tool()
async def query_by_feature(ctx: Context, feature_name: str) -> Dict[str, Any]:
    """
    Find all QA sessions and responses related to a specific feature.
    
    Args:
        feature_name: The feature name to search for
        
    Returns:
        All QA sessions and responses related to the feature
    """
    logger.info(f"Querying sessions by feature: {feature_name}")
    
    # Use helper function to get sessions with matching feature
    feature_sessions = get_sessions_by_tracking_field("feature", feature_name)
    
    matching_sessions = []
    for metadata in feature_sessions:
        tracking = metadata.get("tracking", {})
        matching_sessions.append({
            "qa_id": metadata["qa_id"],
            "project_id": metadata.get("project_id"),
            "responses": metadata["response_count"],
            "component": tracking.get("component"),
            "deliverable": tracking.get("deliverable"),
            "task": tracking.get("task"),
            "workflow_id": tracking.get("workflow_id"),
            "tags": metadata.get("tags", []),
            "created": metadata["created_at"],
            "updated": metadata.get("last_updated")
        })
    
    logger.info(f"Found {len(matching_sessions)} sessions for feature '{feature_name}'")
    
    return {
        "feature": feature_name,
        "matching_sessions": matching_sessions,
        "total_sessions": len(matching_sessions),
        "total_responses": sum(s["responses"] for s in matching_sessions),
        "projects": list(set(s["project_id"] for s in matching_sessions if s["project_id"])),
        "components": list(set(s["component"] for s in matching_sessions if s["component"])),
        "deliverables": list(set(s["deliverable"] for s in matching_sessions if s["deliverable"]))
    }

@mcp.tool()
async def query_by_component(ctx: Context, component_name: str) -> Dict[str, Any]:
    """
    Find all QA sessions and responses related to a specific component.
    
    Args:
        component_name: The component name to search for
        
    Returns:
        All QA sessions and responses related to the component
    """
    logger.info(f"Querying sessions by component: {component_name}")
    
    # Use helper function to get sessions with matching component
    component_sessions = get_sessions_by_tracking_field("component", component_name)
    
    matching_sessions = []
    for metadata in component_sessions:
        tracking = metadata.get("tracking", {})
        matching_sessions.append({
            "qa_id": metadata["qa_id"],
            "project_id": metadata.get("project_id"),
            "responses": metadata["response_count"],
            "feature": tracking.get("feature"),
            "deliverable": tracking.get("deliverable"),
            "task": tracking.get("task"),
            "workflow_id": tracking.get("workflow_id"),
            "tags": metadata.get("tags", []),
            "created": metadata["created_at"],
            "updated": metadata.get("last_updated")
        })
    
    logger.info(f"Found {len(matching_sessions)} sessions for component '{component_name}'")
    
    return {
        "component": component_name,
        "matching_sessions": matching_sessions,
        "total_sessions": len(matching_sessions),
        "total_responses": sum(s["responses"] for s in matching_sessions),
        "projects": list(set(s["project_id"] for s in matching_sessions if s["project_id"])),
        "features": list(set(s["feature"] for s in matching_sessions if s["feature"])),
        "deliverables": list(set(s["deliverable"] for s in matching_sessions if s["deliverable"]))
    }

@mcp.tool()
async def analyze_project_patterns(ctx: Context, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze emergent patterns across projects or within a specific project.
    
    Args:
        project_id: Optional project ID to limit analysis to
        
    Returns:
        Pattern analysis including most common hierarchies, workflows, and trends
    """
    logger.info(f"Analyzing patterns" + (f" for project: {project_id}" if project_id else " across all projects"))
    
    # Use helper functions to get sessions
    if project_id:
        sessions_to_analyze = get_sessions_by_project(project_id)
    else:
        sessions_to_analyze = get_all_sessions()
    
    if not sessions_to_analyze:
        logger.warning(f"No sessions found{' for project ' + project_id if project_id else ''}")
        return {"error": f"No sessions found{' for project ' + project_id if project_id else ''}"}
    
    # Pattern analysis
    feature_frequency = {}
    component_frequency = {}
    deliverable_frequency = {}
    task_frequency = {}
    workflow_frequency = {}
    tag_frequency = {}
    
    feature_component_pairs = {}
    component_deliverable_pairs = {}
    waypoint_patterns = []
    
    project_activity = {}
    
    for session in sessions_to_analyze:
        tracking = session.get("tracking", {})
        
        # Count frequencies
        if tracking.get("feature"):
            feature = tracking["feature"]
            feature_frequency[feature] = feature_frequency.get(feature, 0) + 1
        
        if tracking.get("component"):
            component = tracking["component"]
            component_frequency[component] = component_frequency.get(component, 0) + 1
        
        if tracking.get("deliverable"):
            deliverable = tracking["deliverable"]
            deliverable_frequency[deliverable] = deliverable_frequency.get(deliverable, 0) + 1
        
        if tracking.get("task"):
            task = tracking["task"]
            task_frequency[task] = task_frequency.get(task, 0) + 1
        
        if tracking.get("workflow_id"):
            workflow = tracking["workflow_id"]
            workflow_frequency[workflow] = workflow_frequency.get(workflow, 0) + 1
        
        # Tag analysis
        for tag in session.get("tags", []):
            tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
        
        # Relationship patterns
        if tracking.get("feature") and tracking.get("component"):
            pair = f"{tracking['feature']} → {tracking['component']}"
            feature_component_pairs[pair] = feature_component_pairs.get(pair, 0) + 1
        
        if tracking.get("component") and tracking.get("deliverable"):
            pair = f"{tracking['component']} → {tracking['deliverable']}"
            component_deliverable_pairs[pair] = component_deliverable_pairs.get(pair, 0) + 1
        
        # Waypoint patterns
        if tracking.get("is_from_waypoint"):
            waypoint_patterns.append({
                "workflow_id": tracking.get("workflow_id"),
                "feature": tracking.get("feature"),
                "component": tracking.get("component"),
                "task": tracking.get("task")
            })
        
        # Project activity
        proj_id = session.get("project_id")
        if proj_id:
            if proj_id not in project_activity:
                project_activity[proj_id] = {"sessions": 0, "responses": 0}
            project_activity[proj_id]["sessions"] += 1
            project_activity[proj_id]["responses"] += session["response_count"]
    
    # Sort patterns by frequency
    def sort_dict_by_value(d, limit=10):
        return dict(sorted(d.items(), key=lambda x: x[1], reverse=True)[:limit])
    
    result = {
        "scope": f"project '{project_id}'" if project_id else "all projects",
        "total_sessions": len(sessions_to_analyze),
        "total_responses": sum(s["response_count"] for s in sessions_to_analyze),
        "patterns": {
            "most_common_features": sort_dict_by_value(feature_frequency),
            "most_common_components": sort_dict_by_value(component_frequency),
            "most_common_deliverables": sort_dict_by_value(deliverable_frequency),
            "most_common_tasks": sort_dict_by_value(task_frequency),
            "most_active_workflows": sort_dict_by_value(workflow_frequency),
            "most_frequent_tags": sort_dict_by_value(tag_frequency)
        },
        "relationships": {
            "feature_component_pairs": sort_dict_by_value(feature_component_pairs),
            "component_deliverable_pairs": sort_dict_by_value(component_deliverable_pairs)
        },
        "waypoint_analysis": {
            "total_waypoint_sessions": len(waypoint_patterns),
            "waypoint_percentage": round(len(waypoint_patterns) / len(sessions_to_analyze) * 100, 1),
            "common_waypoint_patterns": waypoint_patterns[:10]
        },
        "project_activity": project_activity
    }
    
    logger.info(f"Pattern analysis complete: {result['total_sessions']} sessions, {result['total_responses']} responses")
    return result

# Resources
@mcp.resource(uri="qa://active")
async def get_active_sessions(ctx: Context) -> str:
    """Get all active QA sessions."""
    result = await list_qa_sessions(ctx)
    active = [s for s in result["sessions"] if s["status"] == "active"]
    return json.dumps({"active_sessions": active}, indent=2)

@mcp.resource(uri="qa://recent")
async def get_recent_sessions(ctx: Context) -> str:
    """Get the 5 most recent QA sessions."""
    result = await list_qa_sessions(ctx)
    recent = result["sessions"][:5]
    return json.dumps({"recent_sessions": recent}, indent=2)

if __name__ == "__main__":
    mcp.run()