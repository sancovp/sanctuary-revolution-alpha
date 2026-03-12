#!/usr/bin/env python3
"""
LLM Intelligence MCP Server V2 - Proper QA File Structure

QA files now contain the FULL conversation content inline, with tool details archived separately.
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

def get_qa_file_path(qa_id: str) -> Path:
    """Get path for the main QA file."""
    return RESPONSE_DIR / f"{qa_id}.json"

def get_qa_markdown_path(qa_id: str) -> Path:
    """Get path for the human-readable QA file."""
    return RESPONSE_DIR / f"{qa_id}.md"

def get_tool_content_path(qa_id: str, response_num: int) -> Path:
    """Get path for tool content archive."""
    tool_dir = RESPONSE_DIR / "response_files" / qa_id / f"response_{response_num:03d}"
    tool_dir.mkdir(parents=True, exist_ok=True)
    return tool_dir / "tool_content.json"

def load_qa_file(qa_id: str) -> Optional[Dict[str, Any]]:
    """Load the main QA file."""
    qa_path = get_qa_file_path(qa_id)
    if qa_path.exists():
        with open(qa_path, "r") as f:
            return json.load(f)
    return None

def save_qa_json(qa_id: str, qa_data: Dict[str, Any]):
    """Save the JSON QA file."""
    qa_path = get_qa_file_path(qa_id)
    with open(qa_path, "w") as f:
        json.dump(qa_data, f, indent=2)
    return qa_path

def save_qa_markdown(qa_id: str, qa_data: Dict[str, Any]):
    """Save the markdown QA file."""
    md_path = get_qa_markdown_path(qa_id)
    with open(md_path, "w") as f:
        f.write(f"# QA Session: {qa_id}\n\n")
        f.write(f"**Project**: {qa_data.get('project_id', 'N/A')}\n")
        f.write(f"**Created**: {qa_data['created_at']}\n")
        f.write(f"**Status**: {qa_data.get('status', 'active')}\n\n")
        
        if qa_data.get("tracking"):
            f.write("## Tracking\n")
            for key, value in qa_data["tracking"].items():
                if value:
                    f.write(f"- **{key.title()}**: {value}\n")
            f.write("\n")
        
        f.write("## Conversation\n\n")
        for i, response in enumerate(qa_data.get("responses", []), 1):
            f.write(f"### Exchange {i}\n\n")
            f.write(f"**User**: {response.get('user_prompt', 'N/A')}\n\n")
            f.write(f"**One-liner**: {response.get('one_liner', 'N/A')}\n\n")
            if response.get("tools_used"):
                f.write(f"**Tools Used**: {', '.join(response['tools_used'])}\n\n")
            f.write("**Response**:\n\n")
            f.write(response.get("response_content", ""))
            f.write("\n\n---\n\n")
    return md_path

def save_qa_file(qa_id: str, qa_data: Dict[str, Any]):
    """Save both JSON and markdown versions of QA file."""
    qa_path = save_qa_json(qa_id, qa_data)
    md_path = save_qa_markdown(qa_id, qa_data)
    logger.info(f"Saved QA file: {qa_path} and {md_path}")

@mcp.tool()
async def respond(
    ctx: Context, 
    qa_id: str,
    user_prompt: str,
    response_text: str, 
    one_liner: str,
    key_tags: List[str],
    tools_used: Optional[List[str]] = None,
    tool_content_path: Optional[str] = None,
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
    Add a response to the QA file with FULL CONTENT inline.
    
    Args:
        qa_id: The QA session ID
        user_prompt: The user's actual prompt that triggered this response
        response_text: The FULL response content (not a summary!)
        one_liner: One-line summary of this response
        key_tags: Key tags/concepts in this response
        tools_used: List of tool NAMES used (not full details)
        tool_content_path: Path to detailed tool content if archived
        project_id: Project this response belongs to
        feature: Feature within project (emergent)
        component: Component within feature (emergent)
        deliverable: Deliverable within component (emergent)
        subtask: Contextual subtask (defined per situation)
        task: Main task (always exists)
        workflow_id: Workflow/waypoint ID if applicable
        is_from_waypoint: Whether this comes from waypoint system
        
    Returns:
        Response metadata
    """
    # Load or create QA file
    qa_data = load_qa_file(qa_id)
    
    if not qa_data:
        # New QA session
        qa_data = {
            "qa_id": qa_id,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "project_id": project_id,
            "tracking": {
                "feature": feature,
                "component": component,
                "deliverable": deliverable,
                "task": task,
                "workflow_id": workflow_id,
                "is_from_waypoint": is_from_waypoint
            },
            "tags": [],
            "responses": []
        }
        logger.info(f"Created new QA session: {qa_id}")
    
    # Update tracking if provided
    if feature:
        qa_data["tracking"]["feature"] = feature
    if component:
        qa_data["tracking"]["component"] = component
    if deliverable:
        qa_data["tracking"]["deliverable"] = deliverable
    if task:
        qa_data["tracking"]["task"] = task
    if workflow_id:
        qa_data["tracking"]["workflow_id"] = workflow_id
    if is_from_waypoint is not None:
        qa_data["tracking"]["is_from_waypoint"] = is_from_waypoint
    
    # Add new response with FULL CONTENT
    response_num = len(qa_data["responses"]) + 1
    new_response = {
        "response_num": response_num,
        "timestamp": datetime.now().isoformat(),
        "user_prompt": user_prompt,
        "response_content": response_text,  # FULL CONTENT HERE!
        "one_liner": one_liner,
        "tools_used": tools_used or [],
        "tool_bundle": tool_content_path,
        "tags": key_tags
    }
    
    # Add part status if tracking progress
    if subtask:
        new_response["subtask"] = subtask
    
    qa_data["responses"].append(new_response)
    qa_data["last_updated"] = datetime.now().isoformat()
    
    # Update tags
    qa_data["tags"] = list(set(qa_data.get("tags", []) + key_tags))
    
    # Save QA file
    save_qa_file(qa_id, qa_data)
    
    logger.info(f"Added response {response_num} to QA session {qa_id}")
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "message": f"Response {response_num} added to QA file",
        "one_liner": one_liner,
        "project_id": project_id,
        "tracking": qa_data["tracking"]
    }

@mcp.tool()
async def archive_tool_content(
    ctx: Context,
    qa_id: str,
    response_num: int,
    tools: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Archive tool details separately from the QA file.
    
    Args:
        qa_id: The QA session ID
        response_num: The response number
        tools: List of tool usage details (name, params, results)
        
    Returns:
        Path to the archived tool content
    """
    tool_path = get_tool_content_path(qa_id, response_num)
    
    # Archive the tool details
    with open(tool_path, "w") as f:
        json.dump({
            "qa_id": qa_id,
            "response_num": response_num,
            "timestamp": datetime.now().isoformat(),
            "tools": tools
        }, f, indent=2)
    
    logger.info(f"Archived {len(tools)} tools to {tool_path}")
    
    return {
        "tool_content_path": str(tool_path.relative_to(RESPONSE_DIR)),
        "tools_archived": len(tools)
    }

@mcp.tool()
async def get_qa_context(ctx: Context, qa_id: str, last_n: int = 3) -> Dict[str, Any]:
    """
    Get context from QA file - now returns FULL conversation content.
    
    Args:
        qa_id: The QA session ID
        last_n: Number of recent exchanges to retrieve
        
    Returns:
        Full conversation context
    """
    qa_data = load_qa_file(qa_id)
    if not qa_data:
        return {"error": f"QA session {qa_id} not found"}
    
    responses = qa_data.get("responses", [])
    
    # Get last N responses
    recent_responses = responses[-last_n:] if len(responses) > last_n else responses
    
    return {
        "qa_id": qa_id,
        "project_id": qa_data.get("project_id"),
        "tracking": qa_data.get("tracking", {}),
        "total_responses": len(responses),
        "retrieved": len(recent_responses),
        "conversation": [
            {
                "response_num": r["response_num"],
                "user_prompt": r["user_prompt"],
                "one_liner": r["one_liner"],
                "response_content": r["response_content"][:500] + "..." if len(r["response_content"]) > 500 else r["response_content"],
                "tools_used": r.get("tools_used", [])
            }
            for r in recent_responses
        ],
        "tags": qa_data.get("tags", [])
    }

@mcp.tool()
async def list_qa_sessions(ctx: Context, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    List all QA sessions, optionally filtered by project.
    
    Args:
        project_id: Optional project ID to filter by
        
    Returns:
        List of QA sessions
    """
    sessions = []
    
    for qa_file in RESPONSE_DIR.glob("*.json"):
        # Skip response_files directory
        if "response_files" in str(qa_file):
            continue
            
        try:
            with open(qa_file) as f:
                qa_data = json.load(f)
            
            # Filter by project if specified
            if project_id and qa_data.get("project_id") != project_id:
                continue
            
            sessions.append({
                "qa_id": qa_data["qa_id"],
                "project_id": qa_data.get("project_id"),
                "created": qa_data["created_at"],
                "updated": qa_data.get("last_updated"),
                "responses": len(qa_data.get("responses", [])),
                "status": qa_data.get("status", "unknown"),
                "tags": qa_data.get("tags", []),
                "tracking": qa_data.get("tracking", {}),
                "last_exchange": {
                    "user": qa_data["responses"][-1]["user_prompt"][:100] if qa_data.get("responses") else None,
                    "one_liner": qa_data["responses"][-1]["one_liner"] if qa_data.get("responses") else None
                }
            })
        except Exception as e:
            logger.warning(f"Failed to load {qa_file}: {e}", exc_info=True)
            continue
    
    # Sort by last updated
    sessions.sort(key=lambda x: x.get("updated") or x["created"], reverse=True)
    
    return {
        "sessions": sessions,
        "total": len(sessions),
        "filtered_by_project": project_id
    }

@mcp.tool()
async def update_part_status(
    ctx: Context,
    qa_id: str,
    response_num: int,
    part_type: str,
    part_id: str,
    status: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the status of a part (feature/component/deliverable) in a response.
    
    Args:
        qa_id: The QA session ID
        response_num: The response number where this part was worked on
        part_type: Type of part (feature, component, deliverable, task, subtask)
        part_id: The ID/name of the part
        status: Status (started, in_progress, blocked, completed, in_review, shipped)
        notes: Optional notes about the status change
        
    Returns:
        Updated status info
    """
    qa_data = load_qa_file(qa_id)
    if not qa_data:
        return {"error": f"QA session {qa_id} not found"}
    
    # Find the response
    if response_num > len(qa_data["responses"]):
        return {"error": f"Response {response_num} not found"}
    
    response = qa_data["responses"][response_num - 1]
    
    # Initialize parts_status if not exists
    if "parts_status" not in response:
        response["parts_status"] = {}
    
    # Update the part status
    response["parts_status"][part_type] = {
        "id": part_id,
        "status": status,
        "updated_at": datetime.now().isoformat(),
        "notes": notes
    }
    
    # Save updated QA file
    save_qa_file(qa_id, qa_data)
    
    logger.info(f"Updated {part_type} '{part_id}' to status '{status}' in {qa_id}/response_{response_num}")
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "part_type": part_type,
        "part_id": part_id,
        "status": status,
        "message": f"Status updated for {part_type} '{part_id}'"
    }

@mcp.tool()
async def get_project_status(ctx: Context, project_id: str) -> Dict[str, Any]:
    """
    Get the current status of all parts in a project.
    
    Args:
        project_id: The project ID
        
    Returns:
        Status of all parts in the project
    """
    parts_status = {
        "features": {},
        "components": {},
        "deliverables": {},
        "tasks": {},
        "subtasks": {}
    }
    
    # Scan all QA files for this project
    for qa_file in RESPONSE_DIR.glob("*.json"):
        if "response_files" in str(qa_file):
            continue
            
        try:
            with open(qa_file) as f:
                qa_data = json.load(f)
            
            if qa_data.get("project_id") != project_id:
                continue
            
            # Extract status from each response
            for response in qa_data.get("responses", []):
                if "parts_status" in response:
                    for part_type, part_info in response["parts_status"].items():
                        part_id = part_info["id"]
                        
                        # Keep the most recent status for each part
                        if part_type in parts_status:
                            if part_id not in parts_status[part_type] or \
                               part_info.get("updated_at", "") > parts_status[part_type].get(part_id, {}).get("updated_at", ""):
                                parts_status[part_type][part_id] = {
                                    "status": part_info["status"],
                                    "updated_at": part_info.get("updated_at"),
                                    "qa_id": qa_data["qa_id"],
                                    "response_num": response["response_num"],
                                    "notes": part_info.get("notes")
                                }
        except Exception as e:
            logger.warning(f"Failed to process {qa_file}: {e}", exc_info=True)
            continue
    
    # Count statuses
    status_summary = {}
    for part_type, parts in parts_status.items():
        status_counts = {}
        for part_id, info in parts.items():
            status = info["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        status_summary[part_type] = status_counts
    
    return {
        "project_id": project_id,
        "parts_status": parts_status,
        "summary": status_summary,
        "total_parts": sum(len(parts) for parts in parts_status.values())
    }

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