#!/usr/bin/env python3
"""
LLM Intelligence MCP Server V3 - Cognitive Architecture

Implements the proper cognitive separation:
- Response files = deliberate user-facing communication
- Tool calls = background thinking/analysis
- respond() = harvest response file into QA conversation

Flow: Write → Work → Report → (repeat cycles) → Respond
"""

import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP, Context

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("llm-intelligence")

# Configuration
RESPONSE_DIR = Path(os.environ.get("LLM_INTELLIGENCE_DIR", "/tmp/llm_intelligence_responses"))
RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

def get_qa_directory(qa_id: str) -> Path:
    """Get the QA session directory."""
    qa_dir = RESPONSE_DIR / "qa_sets" / qa_id
    qa_dir.mkdir(parents=True, exist_ok=True)
    return qa_dir

def get_qa_file_path(qa_id: str) -> Path:
    """Get path for the main QA file."""
    return get_qa_directory(qa_id) / "qa.json"

def get_qa_markdown_path(qa_id: str) -> Path:
    """Get path for the human-readable QA file."""
    return get_qa_directory(qa_id) / "qa.md"

def get_response_directory(qa_id: str, response_num: int) -> Path:
    """Get response directory, creating it if needed."""
    response_dir = get_qa_directory(qa_id) / "responses" / f"response_{response_num:03d}"
    response_dir.mkdir(parents=True, exist_ok=True)
    return response_dir

def get_response_file_path_internal(qa_id: str, response_num: int) -> Path:
    """Get path for response file."""
    return get_response_directory(qa_id, response_num) / "response.md"

def get_tool_archive_path(qa_id: str, response_num: int) -> Path:
    """Get path for tool usage archive."""
    return get_response_directory(qa_id, response_num) / "tool_usage.json"

def load_qa_file(qa_id: str) -> Optional[Dict[str, Any]]:
    """Load the main QA file."""
    qa_path = get_qa_file_path(qa_id)
    if qa_path.exists():
        with open(qa_path, "r") as f:
            return json.load(f)
    return None

def save_qa_file(qa_id: str, qa_data: Dict[str, Any]):
    """Save both JSON and markdown versions of QA file."""
    # Save JSON
    qa_path = get_qa_file_path(qa_id)
    with open(qa_path, "w") as f:
        json.dump(qa_data, f, indent=2)
    
    # Create markdown
    md_path = get_qa_markdown_path(qa_id)
    with open(md_path, "w") as f:
        f.write(f"# QA Session: {qa_id}\n\n")
        f.write(f"**Project**: {qa_data.get('project_id', 'N/A')}\n")
        f.write(f"**Created**: {qa_data['created_at']}\n")
        f.write(f"**Status**: {qa_data.get('status', 'active')}\n\n")
        
        # Tracking info
        if qa_data.get("tracking"):
            f.write("## Tracking\n")
            for key, value in qa_data["tracking"].items():
                if value:
                    f.write(f"- **{key.title()}**: {value}\n")
            f.write("\n")
        
        # Conversation
        f.write("## Conversation\n\n")
        for i, response in enumerate(qa_data.get("responses", []), 1):
            f.write(f"### Exchange {i}\n\n")
            f.write(f"**User**: {response.get('user_prompt', 'N/A')}\n\n")
            f.write(f"**One-liner**: {response.get('one_liner', 'N/A')}\n\n")
            
            # Show files involved and tools used
            if response.get("involved_files"):
                f.write(f"**Files**: {', '.join(response['involved_files'])}\n\n")
            if response.get("tools_used"):
                f.write(f"**Tools**: {', '.join(response['tools_used'])}\n\n")
            
            f.write("**Response**:\n\n")
            f.write(response.get("response_content", ""))
            f.write("\n\n---\n\n")
    
    logger.info(f"Saved QA file: {qa_path} and {md_path}")

@mcp.tool()
async def start_response(
    ctx: Context,
    qa_id: Optional[str] = None,
    project_id: Optional[str] = None,
    feature: Optional[str] = None,
    component: Optional[str] = None,
    deliverable: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a new response in a QA session.
    
    Args:
        qa_id: QA session ID (generates UUID if not provided)
        project_id: Project this belongs to
        feature: Feature being worked on
        component: Component being worked on  
        deliverable: Deliverable being created
        
    Returns:
        QA session info and response file path
    """
    # Generate QA ID if not provided
    if not qa_id:
        qa_id = str(uuid.uuid4())[:8]
        logger.info(f"Generated new QA ID: {qa_id}")
    
    # Load or create QA session
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
                "deliverable": deliverable
            },
            "responses": []
        }
        logger.info(f"Created new QA session: {qa_id}")
        # Save the new QA file
        save_qa_file(qa_id, qa_data)
    
    # Determine next response number
    response_num = len(qa_data["responses"]) + 1
    
    # Create response file path
    response_file_path = str(get_response_file_path_internal(qa_id, response_num))
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "response_file_path": response_file_path,
        "project_id": project_id,
        "message": f"Started response {response_num} in QA session {qa_id}"
    }

@mcp.tool()
async def report_tool_usage(
    ctx: Context,
    tools_used: List[str],
    response_file_path: str,
    involved_files: List[str]
) -> Dict[str, Any]:
    """
    Report tools used and files involved during work.
    
    Args:
        tools_used: List of tool names used
        response_file_path: Path to the response file being built
        involved_files: Files that were created/modified
        
    Returns:
        Confirmation of tool usage recorded
    """
    # Extract qa_id and response_num from path
    path_parts = Path(response_file_path).parts
    qa_id = path_parts[-4]  # qa_sets/qa_id/responses/response_001/response.md
    response_dir = path_parts[-2]  # response_001
    response_num = int(response_dir.split("_")[1])
    
    # Archive tool usage
    tool_archive_path = get_tool_archive_path(qa_id, response_num)
    
    # Load existing usage or create new
    if tool_archive_path.exists():
        with open(tool_archive_path, "r") as f:
            usage_data = json.load(f)
    else:
        usage_data = {
            "qa_id": qa_id,
            "response_num": response_num,
            "usage_reports": []
        }
    
    # Add this usage report
    usage_data["usage_reports"].append({
        "timestamp": datetime.now().isoformat(),
        "tools_used": tools_used,
        "involved_files": involved_files
    })
    
    # Save updated usage
    with open(tool_archive_path, "w") as f:
        json.dump(usage_data, f, indent=2)
    
    logger.info(f"Recorded tool usage for {qa_id}/response_{response_num:03d}: {tools_used}")
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "tools_recorded": tools_used,
        "files_recorded": involved_files,
        "archive_path": str(tool_archive_path),
        "message": f"Tool usage recorded for response {response_num}"
    }

@mcp.tool()
async def respond(
    ctx: Context,
    qa_id: str,
    user_prompt: str,
    one_liner: str,
    key_tags: List[str],
    involved_files: List[str],
    project_id: str,
    feature: str,
    component: str,
    deliverable: str,
    subtask: str,
    task: str,
    workflow_id: str,
    is_from_waypoint: bool = False
) -> Dict[str, Any]:
    """
    Harvest a response file into the QA conversation.
    
    Args:
        qa_id: The QA session ID
        user_prompt: The user's original prompt
        one_liner: One-line summary of the response
        key_tags: Key concepts/tags for this response
        project_id: Project ID (optional update)
        feature: Feature (optional update)
        component: Component (optional update)
        deliverable: Deliverable (optional update)
        workflow_id: Workflow ID if from waypoint
        
    Returns:
        Response harvest confirmation
    """
    # Load or create QA file
    qa_data = load_qa_file(qa_id)
    if not qa_data:
        qa_data = {
            "qa_id": qa_id,
            "created_at": datetime.now().isoformat(),
            "status": "active",
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
            "responses": []
        }
    
    # Determine response number
    response_num = len(qa_data["responses"]) + 1
    response_file_path = get_response_file_path_internal(qa_id, response_num)
    tool_archive_path = get_tool_archive_path(qa_id, response_num)
    
    # Read response file content
    if not response_file_path.exists():
        return {"error": f"Response file not found: {response_file_path}"}
    
    with open(response_file_path, "r") as f:
        response_content = f.read()
    
    # Load tool usage data
    all_tools_used = []
    all_involved_files = []
    
    if tool_archive_path.exists():
        with open(tool_archive_path, "r") as f:
            usage_data = json.load(f)
        
        # Aggregate all tools and files from all usage reports
        for report in usage_data.get("usage_reports", []):
            all_tools_used.extend(report.get("tools_used", []))
            all_involved_files.extend(report.get("involved_files", []))
    
    # Remove duplicates while preserving order
    all_tools_used = list(dict.fromkeys(all_tools_used))
    all_involved_files = list(dict.fromkeys(all_involved_files))
    
    # Update tracking
    qa_data["project_id"] = project_id
    qa_data["tracking"]["feature"] = feature
    qa_data["tracking"]["component"] = component
    qa_data["tracking"]["deliverable"] = deliverable
    qa_data["tracking"]["subtask"] = subtask
    qa_data["tracking"]["task"] = task
    qa_data["tracking"]["workflow_id"] = workflow_id
    qa_data["tracking"]["is_from_waypoint"] = is_from_waypoint
    
    # Create response entry
    response_entry = {
        "response_num": response_num,
        "timestamp": datetime.now().isoformat(),
        "user_prompt": user_prompt,
        "response_content": response_content,
        "one_liner": one_liner,
        "tools_used": all_tools_used,
        "involved_files": involved_files,
        "tags": key_tags,
        "response_file": str(response_file_path.relative_to(RESPONSE_DIR)),
        "tool_archive": str(tool_archive_path.relative_to(RESPONSE_DIR)) if tool_archive_path.exists() else None
    }
    
    # Add to QA data
    qa_data["responses"].append(response_entry)
    qa_data["last_updated"] = datetime.now().isoformat()
    
    # Update tags
    qa_data["tags"] = list(set(qa_data.get("tags", []) + key_tags))
    
    # Save QA file
    save_qa_file(qa_id, qa_data)
    
    logger.info(f"Harvested response {response_num} into QA session {qa_id}")
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "response_content_chars": len(response_content),
        "tools_used": all_tools_used,
        "involved_files": involved_files,
        "one_liner": one_liner,
        "message": f"Response {response_num} harvested into QA conversation"
    }

@mcp.tool()
async def get_qa_context(ctx: Context, qa_id: str, last_n: int = 3) -> Dict[str, Any]:
    """
    Get context from QA file.
    
    Args:
        qa_id: The QA session ID
        last_n: Number of recent exchanges to retrieve
        
    Returns:
        QA conversation context
    """
    qa_data = load_qa_file(qa_id)
    if not qa_data:
        return {"error": f"QA session {qa_id} not found"}
    
    responses = qa_data.get("responses", [])
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
                "tools_used": r.get("tools_used", []),
                "involved_files": r.get("involved_files", []),
                "response_preview": r["response_content"][:300] + "..." if len(r["response_content"]) > 300 else r["response_content"]
            }
            for r in recent_responses
        ],
        "tags": qa_data.get("tags", [])
    }

@mcp.tool()
async def list_qa_sessions(ctx: Context, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    List all QA sessions.
    
    Args:
        project_id: Optional project filter
        
    Returns:
        List of QA sessions
    """
    sessions = []
    qa_sets_dir = RESPONSE_DIR / "qa_sets"
    
    if not qa_sets_dir.exists():
        return {"sessions": [], "total": 0}
    
    for qa_dir in qa_sets_dir.iterdir():
        if qa_dir.is_dir():
            qa_file = qa_dir / "qa.json"
            if qa_file.exists():
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
                        "status": qa_data.get("status", "active"),
                        "tracking": qa_data.get("tracking", {}),
                        "tags": qa_data.get("tags", [])
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
async def get_response_file_path(ctx: Context, qa_id: str, response_num: Optional[int] = None) -> Dict[str, str]:
    """
    Get the path to a response file for writing/reading.
    
    Args:
        qa_id: QA session ID
        response_num: Response number (defaults to next available)
        
    Returns:
        Response file path
    """
    if response_num is None:
        # Determine next response number
        qa_data = load_qa_file(qa_id)
        if qa_data:
            response_num = len(qa_data["responses"]) + 1
        else:
            response_num = 1
    
    response_path = get_response_file_path_internal(qa_id, response_num)
    
    return {
        "qa_id": qa_id,
        "response_num": response_num,
        "response_file_path": str(response_path),
        "directory": str(response_path.parent)
    }

# Resources
@mcp.resource(uri="qa://active")
async def get_active_sessions(ctx: Context) -> str:
    """Get all active QA sessions."""
    result = await list_qa_sessions(ctx)
    active = [s for s in result["sessions"] if s["status"] == "active"]
    return json.dumps({"active_sessions": active}, indent=2)

if __name__ == "__main__":
    mcp.run()