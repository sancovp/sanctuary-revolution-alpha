"""
LLM Intelligence Package

Core business logic for the LLM Intelligence system with systematic multi-fire cognitive responses.
"""

from .core import (
    respond, 
    report_tool_usage, 
    get_qa_context, 
    list_qa_sessions,
    llms_must_use_this_to_be_intelligent,
    remind_me_what_giint_is
)
from .projects import (
    create_project,
    get_project,
    update_project,
    list_projects,
    delete_project,
    add_feature_to_project,
    add_component_to_feature,
    add_deliverable_to_component,
    add_task_to_deliverable,
    update_task_status,
    add_spec_to_feature,
    add_spec_to_component,
    add_spec_to_deliverable,
    add_spec_to_task
)

__version__ = "0.1.0"
__all__ = [
    "respond", 
    "report_tool_usage", 
    "get_qa_context", 
    "list_qa_sessions",
    "llms_must_use_this_to_be_intelligent",
    "remind_me_what_giint_is",
    "create_project",
    "get_project", 
    "update_project",
    "list_projects",
    "delete_project",
    "add_feature_to_project",
    "add_component_to_feature",
    "add_deliverable_to_component",
    "add_task_to_deliverable",
    "update_task_status",
    "add_spec_to_feature",
    "add_spec_to_component",
    "add_spec_to_deliverable",
    "add_spec_to_task"
]