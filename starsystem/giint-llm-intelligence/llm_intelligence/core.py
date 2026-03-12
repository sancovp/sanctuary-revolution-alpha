#!/usr/bin/env python3
"""
LLM Intelligence Core Module

Business logic for the LLM Intelligence system.
MCP server imports and wraps these functions.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


def respond(
    qa_id: str,
    response_file_path: str,
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
    Harvest response file into QA conversation with full emergent tracking.
    
    Args:
        qa_id: QA session identifier
        response_file_path: Path to LLM's response file (can be anywhere)
        one_liner: Brief summary of what was accomplished
        key_tags: Tags for categorization
        involved_files: Files that were created/modified
        project_id: Project identifier (free-form string)
        feature: Feature being worked on (free-form string)
        component: Component being worked on (free-form string)
        deliverable: Deliverable being created (free-form string)
        subtask: Subtask being handled (free-form string)
        task: Specific task (free-form string)
        workflow_id: Workflow identifier (free-form string)
        is_from_waypoint: Whether this is from a STARLOG waypoint
        
    Returns:
        Success confirmation with details
    """
    # Configuration
    base_dir = Path(os.environ.get("LLM_INTELLIGENCE_DIR", "/tmp/llm_intelligence_responses"))
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Read response file content from LLM's arbitrary path
    response_path = Path(response_file_path)
    if not response_path.exists():
        return {"error": f"Response file not found: {response_file_path}"}
    
    try:
        with open(response_path, 'r', encoding='utf-8') as f:
            response_content = f.read()
    except Exception as e:
        return {"error": f"Failed to read response file: {e}"}
    
    # 2. Set up organized structure
    qa_dir = base_dir / "qa_sets" / qa_id
    qa_dir.mkdir(parents=True, exist_ok=True)
    
    # Load or create QA file
    qa_file_path = qa_dir / "qa.json"
    if qa_file_path.exists():
        with open(qa_file_path, 'r') as f:
            qa_data = json.load(f)
    else:
        qa_data = {
            "qa_id": qa_id,
            "created_at": datetime.now().isoformat(),
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
    
    # Update tracking with latest info
    qa_data["project_id"] = project_id
    qa_data["tracking"].update({
        "feature": feature,
        "component": component,
        "deliverable": deliverable,
        "subtask": subtask,
        "task": task,
        "workflow_id": workflow_id,
        "is_from_waypoint": is_from_waypoint
    })
    qa_data["last_updated"] = datetime.now().isoformat()
    
    # Determine response number
    response_num = len(qa_data["responses"]) + 1
    
    # 3. Copy content to organized structure
    response_dir = qa_dir / "responses" / f"response_{response_num:03d}"
    response_dir.mkdir(parents=True, exist_ok=True)
    organized_response_path = response_dir / "response.md"
    
    try:
        shutil.copy2(response_path, organized_response_path)
    except Exception as e:
        return {"error": f"Failed to copy response file: {e}"}
    
    # 4. Delete original response file (cleanup)
    try:
        os.remove(response_path)
    except Exception as e:
        # Non-fatal - log but continue
        print(f"Warning: Failed to delete original response file {response_path}: {e}")
    
    # 5. Update QA conversation
    response_entry = {
        "response_id": response_num,
        "timestamp": datetime.now().isoformat(),
        "response_content": response_content,
        "one_liner": one_liner,
        "key_tags": key_tags,
        "involved_files": involved_files,
        "response_file": f"responses/response_{response_num:03d}/response.md"
    }
    
    qa_data["responses"].append(response_entry)
    
    # Save updated QA file
    with open(qa_file_path, 'w') as f:
        json.dump(qa_data, f, indent=2)
    
    # 6. Log to STARLOG debug diary
    try:
        log_to_starlog_debug_diary(
            qa_id=qa_id,
            response_id=response_num,
            project_id=project_id,
            feature=feature,
            component=component,
            deliverable=deliverable,
            subtask=subtask,
            task=task,
            workflow_id=workflow_id,
            is_from_waypoint=is_from_waypoint,
            one_liner=one_liner
        )
    except Exception as e:
        # Non-fatal - STARLOG integration might not be available
        print(f"Warning: STARLOG logging failed: {e}")
    
    return {
        "success": True,
        "qa_id": qa_id,
        "response_id": response_num,
        "organized_path": str(organized_response_path),
        "original_path_deleted": str(response_path),
        "one_liner": one_liner,
        "tracking": qa_data["tracking"]
    }


def report_tool_usage(
    tools_used: List[str],
    response_file_path: str,
    involved_files: List[str]
) -> Dict[str, Any]:
    """
    Archive tool usage details during work.
    
    Args:
        tools_used: List of tool names used
        response_file_path: Path to response file being built
        involved_files: Files that were created/modified
        
    Returns:
        Confirmation of tool usage archived
    """
    try:
        # For now, just return confirmation
        # Later we can implement actual archiving if needed
        return {
            "success": True,
            "tools_archived": tools_used,
            "files_tracked": involved_files,
            "response_file": response_file_path,
            "message": "Tool usage reported successfully"
        }
    except Exception as e:
        return {"error": f"Failed to report tool usage: {e}"}


def get_qa_context(qa_id: str, last_n: int = 3) -> Dict[str, Any]:
    """
    Get context from QA file.
    
    Args:
        qa_id: QA session identifier
        last_n: Number of recent responses to return
        
    Returns:
        QA context data
    """
    base_dir = Path(os.environ.get("LLM_INTELLIGENCE_DIR", "/tmp/llm_intelligence_responses"))
    qa_file_path = base_dir / "qa_sets" / qa_id / "qa.json"
    
    if not qa_file_path.exists():
        return {"error": f"QA session {qa_id} not found"}
    
    try:
        with open(qa_file_path, 'r') as f:
            qa_data = json.load(f)
        
        # Return last N responses
        recent_responses = qa_data["responses"][-last_n:] if qa_data["responses"] else []
        
        return {
            "qa_id": qa_data["qa_id"],
            "project_id": qa_data["project_id"],
            "tracking": qa_data["tracking"],
            "total_responses": len(qa_data["responses"]),
            "recent_responses": recent_responses,
            "created_at": qa_data["created_at"],
            "last_updated": qa_data.get("last_updated")
        }
    except Exception as e:
        return {"error": f"Failed to load QA context: {e}"}


def list_qa_sessions(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    List all QA sessions.
    
    Args:
        project_id: Optional project filter
        
    Returns:
        List of QA sessions
    """
    base_dir = Path(os.environ.get("LLM_INTELLIGENCE_DIR", "/tmp/llm_intelligence_responses"))
    qa_sets_dir = base_dir / "qa_sets"
    
    if not qa_sets_dir.exists():
        return {"sessions": [], "total": 0}
    
    sessions = []
    for qa_dir in qa_sets_dir.iterdir():
        if qa_dir.is_dir():
            qa_file = qa_dir / "qa.json"
            if qa_file.exists():
                try:
                    with open(qa_file, 'r') as f:
                        qa_data = json.load(f)
                    
                    # Filter by project if specified
                    if project_id and qa_data.get("project_id") != project_id:
                        continue
                    
                    sessions.append({
                        "qa_id": qa_data["qa_id"],
                        "project_id": qa_data.get("project_id"),
                        "created_at": qa_data["created_at"],
                        "last_updated": qa_data.get("last_updated"),
                        "responses": len(qa_data.get("responses", [])),
                        "tracking": qa_data.get("tracking", {}),
                        "one_liner": qa_data["responses"][-1]["one_liner"] if qa_data.get("responses") else None
                    })
                except Exception as e:
                    print(f"Warning: Failed to load {qa_file}: {e}")
                    continue
    
    # Sort by last updated
    sessions.sort(key=lambda x: x.get("last_updated") or x["created_at"], reverse=True)
    
    return {
        "sessions": sessions,
        "total": len(sessions),
        "filtered_by_project": project_id
    }


def log_to_starlog_debug_diary(
    qa_id: str,
    response_id: int,
    project_id: str,
    feature: str,
    component: str,
    deliverable: str,
    subtask: str,
    task: str,
    workflow_id: str,
    is_from_waypoint: bool,
    one_liner: str
) -> None:
    """
    Log to STARLOG debug diary with exact format specified.
    
    Format: {{DATETIME}}.{{QA_ID}}.{{RESPONSE_ID}}.{{PROJECT}}.{{FEATURE}}.{{COMPONENT}}.{{DELIVERABLE}}.{{SUBTASK}}.{{TASK}}.{{WORKFLOW}}.{{IS_FROM_WAYPOINT}}: {{one_liner}}
    """
    try:
        # This would call STARLOG MCP if available
        # For now, just print to show the format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        entry = f"{timestamp}.{qa_id}.{response_id}.{project_id}.{feature}.{component}.{deliverable}.{subtask}.{task}.{workflow_id}.{is_from_waypoint}: {one_liner}"
        
        print(f"STARLOG DEBUG DIARY: {entry}")
        
        # TODO: Implement actual STARLOG integration
        # update_debug_diary(content=entry)
        
    except Exception as e:
        print(f"STARLOG logging failed: {e}")