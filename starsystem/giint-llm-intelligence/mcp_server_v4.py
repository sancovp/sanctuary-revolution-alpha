#!/usr/bin/env python3
"""
LLM Intelligence MCP Server

Thin wrapper that imports business logic from llm_intelligence.core module.
MCP servers should only contain wrapper functions.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP

# Add current directory to path so we can import llm_intelligence
sys.path.insert(0, str(Path(__file__).parent))

from llm_intelligence.core import (
    respond as core_respond,
    report_tool_usage as core_report_tool_usage,
    get_qa_context as core_get_qa_context,
    list_qa_sessions as core_list_qa_sessions
)

# Initialize MCP server
mcp = FastMCP("llm-intelligence")


@mcp.tool()
async def respond(
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
    
    This is a thin wrapper around the core business logic.
    """
    return core_respond(
        qa_id=qa_id,
        response_file_path=response_file_path,
        one_liner=one_liner,
        key_tags=key_tags,
        involved_files=involved_files,
        project_id=project_id,
        feature=feature,
        component=component,
        deliverable=deliverable,
        subtask=subtask,
        task=task,
        workflow_id=workflow_id,
        is_from_waypoint=is_from_waypoint
    )


@mcp.tool()
async def report_tool_usage(
    tools_used: List[str],
    response_file_path: str,
    involved_files: List[str]
) -> Dict[str, Any]:
    """
    Archive tool usage details during work.
    
    This is a thin wrapper around the core business logic.
    """
    return core_report_tool_usage(
        tools_used=tools_used,
        response_file_path=response_file_path,
        involved_files=involved_files
    )


@mcp.tool()
async def get_qa_context(
    qa_id: str,
    last_n: int = 3
) -> Dict[str, Any]:
    """
    Get context from QA file.
    
    This is a thin wrapper around the core business logic.
    """
    return core_get_qa_context(qa_id=qa_id, last_n=last_n)


@mcp.tool()
async def list_qa_sessions(
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all QA sessions.
    
    This is a thin wrapper around the core business logic.
    """
    return core_list_qa_sessions(project_id=project_id)


if __name__ == "__main__":
    mcp.run()