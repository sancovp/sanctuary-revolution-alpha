#!/usr/bin/env python3
"""
LLM Intelligence Projects Module

Project management with Pydantic validation and JSON registry.
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator

# Setup logging
logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enum - exactly as specified by user."""
    READY = "ready"
    IN_PROGRESS = "in_progress" 
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class AssigneeType(str, Enum):
    """Assignee type enum."""
    HUMAN = "HUMAN"
    AI = "AI"


class ProjectType(str, Enum):
    """Project type enum."""
    SINGLE = "single"  # Standard GIINT project with features/components/deliverables
    COMPOSITE = "composite"  # Container project that holds multiple single projects


class Task(BaseModel):
    """Task model with status tracking."""
    task_id: str = Field(..., description="Task identifier")
    spec: Optional["TaskSpec"] = Field(None, description="Task rollup specification")
    status: TaskStatus = Field(TaskStatus.READY, description="Current task status")
    is_blocked: bool = Field(False, description="Whether task is blocked")
    blocked_description: Optional[str] = Field(None, description="Why task is blocked")
    is_ready: bool = Field(True, description="Whether task is ready to work on")
    assignee: AssigneeType = Field(..., description="Who is assigned to this task")
    agent_id: Optional[str] = Field(None, description="Agent ID if assignee is AI")
    human_name: Optional[str] = Field(None, description="Human name if assignee is HUMAN")
    github_issue_id: Optional[str] = Field(None, description="GitHub issue ID if created")
    github_issue_url: Optional[str] = Field(None, description="GitHub issue URL for reference")
    claude_task_id: Optional[str] = Field(None, description="Claude Code task ID for bridging native task system")
    # Context metadata fields for contextualization protocol
    files_touched: Optional[List[str]] = Field(None, description="Files touched while completing this task")
    lines_that_matter: Optional[str] = Field(None, description="Line ranges that are relevant (e.g., '42-87')")
    context_deps: Optional[List[str]] = Field(None, description="Context dependencies - files that were read to understand this task")
    key_insight: Optional[str] = Field(None, description="Key insight or pattern discovered while completing task")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @validator('agent_id')
    def validate_agent_id(cls, v, values):
        assignee = values.get('assignee')
        if assignee == AssigneeType.AI and not v:
            raise ValueError('agent_id is required when assignee is AI')
        if assignee == AssigneeType.HUMAN and v:
            raise ValueError('agent_id should not be set when assignee is HUMAN')
        return v
    
    @validator('human_name')
    def validate_human_name(cls, v, values):
        assignee = values.get('assignee')
        if assignee == AssigneeType.HUMAN and not v:
            raise ValueError('human_name is required when assignee is HUMAN')
        if assignee == AssigneeType.AI and v:
            raise ValueError('human_name should not be set when assignee is AI')
        return v


class FeatureSpec(BaseModel):
    """Feature specification."""
    spec_file_path: str = Field(..., description="Path to feature spec JSON file")
    status: str = Field("draft", description="draft|review|approved")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ComponentSpec(BaseModel):
    """Component specification."""
    spec_file_path: str = Field(..., description="Path to component spec JSON file")
    status: str = Field("draft", description="draft|review|approved")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class DeliverableSpec(BaseModel):
    """Deliverable specification."""
    spec_file_path: str = Field(..., description="Path to deliverable spec JSON file")
    status: str = Field("draft", description="draft|review|approved")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskSpec(BaseModel):
    """Task rollup specification containing all parent specs."""
    spec_file_path: str = Field(..., description="Path to task rollup spec JSON file")
    status: str = Field("draft", description="draft|review|approved")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Deliverable(BaseModel):
    """Deliverable containing tasks that produce it."""
    deliverable_name: str = Field(..., description="Deliverable name")
    spec: Optional[DeliverableSpec] = Field(None, description="Deliverable specification")
    tasks: Dict[str, Task] = Field(default_factory=dict, description="Tasks that produce this deliverable")
    operadic_flow_ids: List[str] = Field(default_factory=list, description="OperadicFlow IDs vendored to this deliverable")
    covers_component: Optional[str] = Field(None, description="Component path this deliverable covers (for AI integrations)")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Component(BaseModel):
    """Component containing deliverables."""
    component_name: str = Field(..., description="Component name")
    spec: Optional[ComponentSpec] = Field(None, description="Component specification")
    deliverables: Dict[str, Deliverable] = Field(default_factory=dict, description="Deliverables in this component")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Feature(BaseModel):
    """Feature containing components."""
    feature_name: str = Field(..., description="Feature name")
    spec: Optional[FeatureSpec] = Field(None, description="Feature specification")
    components: Dict[str, Component] = Field(default_factory=dict, description="Components in this feature")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Project(BaseModel):
    """Pydantic model for project data validation."""

    project_id: str = Field(..., description="Unique project identifier")
    project_type: ProjectType = Field(ProjectType.SINGLE, description="Project type: single or composite")
    project_dir: str = Field(..., description="Path to project directory")
    mode: str = Field("planning", description="Current project mode: planning|execution")
    starlog_path: Optional[str] = Field(None, description="Optional path to STARLOG project")
    github_repo_url: Optional[str] = Field(None, description="Optional GitHub repository URL for issue integration")
    features: Dict[str, Feature] = Field(default_factory=dict, description="Features in this project (SINGLE type only)")
    sub_projects: List[str] = Field(default_factory=list, description="Sub-project IDs (COMPOSITE type only)")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @validator('project_id')
    def validate_project_id(cls, v):
        if not v.strip():
            raise ValueError('project_id cannot be empty')
        return v.strip()
    
    @validator('project_dir')
    def validate_project_dir(cls, v):
        if not v.strip():
            raise ValueError('project_dir cannot be empty')
        return v.strip()
    
    @validator('starlog_path')
    def validate_starlog_path(cls, v):
        if v is not None and not v.strip():
            raise ValueError('starlog_path cannot be empty string, use None instead')
        return v.strip() if v else None


class ProjectRegistry:
    """Manages projects registry with JSON persistence."""
    
    def __init__(self, registry_path: Optional[str] = None):
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            base_dir = Path(os.environ.get("LLM_INTELLIGENCE_DIR", "/tmp/llm_intelligence_responses"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.registry_path = base_dir / "projects.json"
    
    def _load_projects(self) -> Dict[str, Project]:
        """Load projects from JSON file."""
        if not self.registry_path.exists():
            return {}
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to Project objects with Pydantic validation
            projects = {}
            for project_id, project_data in data.items():
                try:
                    projects[project_id] = Project(**project_data)
                except Exception as e:
                    logger.error(f"Invalid project data for {project_id}: {e}")
                    continue
            
            return projects
        except Exception as e:
            logger.error(f"Failed to load projects registry: {e}", exc_info=True)
            return {}
    
    def _save_projects(self, projects: Dict[str, Project]) -> None:
        """Save projects to JSON file."""
        try:
            # Convert Project objects to dict for JSON serialization
            data = {project_id: project.dict() for project_id, project in projects.items()}
            
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved projects registry: {self.registry_path}")
        except Exception as e:
            logger.error(f"Failed to save projects registry: {e}", exc_info=True)
            raise
    
    def create_project(
        self,
        project_id: str,
        project_dir: str,
        starlog_path: Optional[str] = None,
        github_repo_url: Optional[str] = None,
        project_type: ProjectType = ProjectType.SINGLE
    ) -> Dict[str, Any]:
        """Create a new project with validation."""
        try:
            # Validate through Pydantic
            project = Project(
                project_id=project_id,
                project_type=project_type,
                project_dir=project_dir,
                starlog_path=starlog_path,
                github_repo_url=github_repo_url
            )
            
            # Load existing projects
            projects = self._load_projects()
            
            # Check if project already exists
            if project_id in projects:
                return {"error": f"Project {project_id} already exists"}
            
            # Add new project
            projects[project_id] = project
            
            # Save to file
            self._save_projects(projects)

            # Sync to CartON knowledge graph
            try:
                from .carton_sync import sync_project_to_carton
                sync_project_to_carton(project.dict())
            except Exception as e:
                logger.warning(f"CartON sync failed (non-fatal): {e}")

            logger.info(f"Created project: {project_id}")
            return {
                "success": True,
                "project": project.dict(),
                "message": f"Project {project_id} created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create project {project_id}: {e}", exc_info=True)
            return {"error": f"Failed to create project: {e}"}
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project by ID."""
        try:
            projects = self._load_projects()

            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}

            return {
                "success": True,
                "project": projects[project_id].dict()
            }

        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
            return {"error": f"Failed to get project: {e}"}

    def get_project_by_dir(self, project_dir: str) -> Dict[str, Any]:
        """Get project by project_dir (STARSYSTEM path). One STARSYSTEM = one GIINT project."""
        try:
            projects = self._load_projects()
            normalized = os.path.normpath(project_dir)

            for pid, project in projects.items():
                if os.path.normpath(project.project_dir) == normalized:
                    return {
                        "success": True,
                        "project": project.dict(),
                        "project_id": pid
                    }

            return {"error": f"No GIINT project found for directory {project_dir}"}

        except Exception as e:
            logger.error(f"Failed to get project by dir {project_dir}: {e}", exc_info=True)
            return {"error": f"Failed to get project by dir: {e}"}
    
    def update_project(
        self,
        project_id: str,
        project_dir: Optional[str] = None,
        starlog_path: Optional[str] = None,
        github_repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update existing project."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
            
            # Get current project
            current_project = projects[project_id]
            
            # Update fields if provided
            updated_data = current_project.dict()
            if project_dir is not None:
                updated_data["project_dir"] = project_dir
            if starlog_path is not None:
                updated_data["starlog_path"] = starlog_path
            if github_repo_url is not None:
                updated_data["github_repo_url"] = github_repo_url
            updated_data["updated_at"] = datetime.now().isoformat()
            
            # Validate updated project
            updated_project = Project(**updated_data)
            
            # Save updated project
            projects[project_id] = updated_project
            self._save_projects(projects)
            
            logger.info(f"Updated project: {project_id}")
            return {
                "success": True,
                "project": updated_project.dict(),
                "message": f"Project {project_id} updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}", exc_info=True)
            return {"error": f"Failed to update project: {e}"}
    
    def list_projects(self) -> Dict[str, Any]:
        """List all projects as lightweight summaries.

        Returns name, path, type, mode, last modified, and feature count only.
        To see full project hierarchy, use get_project(project_id) on a specific project.

        IMPORTANT for agents: Projects are hierarchical (Project → Feature → Component →
        Deliverable → Task). Read them one at a time with get_project(), not all at once.
        """
        try:
            projects = self._load_projects()

            project_list = []
            for project in projects.values():
                feature_names = list(project.features.keys()) if project.features else []
                sub_project_ids = project.sub_projects if project.sub_projects else []
                project_list.append({
                    "project_id": project.project_id,
                    "project_dir": project.project_dir,
                    "project_type": project.project_type.value,
                    "mode": project.mode,
                    "feature_count": len(feature_names),
                    "feature_names": feature_names,
                    "sub_projects": sub_project_ids,
                    "starlog_path": project.starlog_path,
                    "github_repo_url": project.github_repo_url,
                    "created_at": project.created_at,
                    "updated_at": project.updated_at,
                })

            # Sort by updated_at (most recently touched first)
            project_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

            return {
                "success": True,
                "projects": project_list,
                "total": len(project_list),
                "hint": "Projects are hierarchical: Project → Feature → Component → Deliverable → Task. Use get_project(project_id) to see full hierarchy for ONE project at a time."
            }

        except Exception as e:
            logger.error(f"Failed to list projects: {e}", exc_info=True)
            return {"error": f"Failed to list projects: {e}"}
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete project by ID."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
            
            # Remove project
            del projects[project_id]
            
            # Save updated registry
            self._save_projects(projects)
            
            logger.info(f"Deleted project: {project_id}")
            return {
                "success": True,
                "message": f"Project {project_id} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
            return {"error": f"Failed to delete project: {e}"}

    def add_sub_project(self, composite_project_id: str, sub_project_id: str) -> Dict[str, Any]:
        """Add a sub-project to a composite project."""
        try:
            projects = self._load_projects()

            # Validate composite project exists
            if composite_project_id not in projects:
                return {"error": f"Composite project {composite_project_id} not found"}

            composite_project = projects[composite_project_id]

            # Validate it's a composite project
            if composite_project.project_type != ProjectType.COMPOSITE:
                return {"error": f"Project {composite_project_id} is not a composite project (type: {composite_project.project_type})"}

            # Validate sub-project exists
            if sub_project_id not in projects:
                return {"error": f"Sub-project {sub_project_id} not found"}

            sub_project = projects[sub_project_id]

            # Validate it's a single project
            if sub_project.project_type != ProjectType.SINGLE:
                return {"error": f"Sub-project {sub_project_id} must be a single project (type: {sub_project.project_type})"}

            # Check if already added
            if sub_project_id in composite_project.sub_projects:
                return {"error": f"Sub-project {sub_project_id} already exists in composite project {composite_project_id}"}

            # Add sub-project reference
            composite_project.sub_projects.append(sub_project_id)
            composite_project.updated_at = datetime.now().isoformat()

            # Save updated registry
            self._save_projects(projects)

            logger.info(f"Added sub-project {sub_project_id} to composite project {composite_project_id}")
            return {
                "success": True,
                "message": f"Sub-project {sub_project_id} added to composite project {composite_project_id}"
            }

        except Exception as e:
            logger.error(f"Failed to add sub-project: {e}", exc_info=True)
            return {"error": f"Failed to add sub-project: {e}"}

    def add_feature_to_project(self, project_id: str, feature_name: str) -> Dict[str, Any]:
        """Add feature to project."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
            
            if feature_name in projects[project_id].features:
                return {"error": f"Feature {feature_name} already exists in project {project_id}"}
            
            # Add feature
            projects[project_id].features[feature_name] = Feature(feature_name=feature_name)
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Added feature {feature_name} to project {project_id}")
            return {"success": True, "message": f"Feature {feature_name} added to project {project_id}"}
            
        except Exception as e:
            logger.error(f"Failed to add feature {feature_name} to project {project_id}: {e}", exc_info=True)
            return {"error": f"Failed to add feature: {e}"}
    
    def add_component_to_feature(self, project_id: str, feature_name: str, component_name: str) -> Dict[str, Any]:
        """Add component to feature."""
        try:
            projects = self._load_projects()

            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}

            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}

            if component_name in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} already exists in feature {feature_name}"}

            # Add component
            component = Component(component_name=component_name)
            projects[project_id].features[feature_name].components[component_name] = component
            projects[project_id].updated_at = datetime.now().isoformat()

            # Save
            self._save_projects(projects)

            # Sync to CartON (dual-write pattern)
            try:
                from .carton_sync import sync_component_to_carton
                sync_result = sync_component_to_carton(project_id, feature_name, component_name, component.dict())
                logger.info(f"Component {component_name} synced to CartON: {sync_result}")
            except Exception as carton_err:
                logger.warning(f"CartON sync failed for component {component_name}: {carton_err}")

            logger.info(f"Added component {component_name} to feature {feature_name} in project {project_id}")
            return {"success": True, "message": f"Component {component_name} added to feature {feature_name}"}
            
        except Exception as e:
            logger.error(f"Failed to add component {component_name} to feature {feature_name}: {e}", exc_info=True)
            return {"error": f"Failed to add component: {e}"}
    
    def add_deliverable_to_component(self, project_id: str, feature_name: str, component_name: str, deliverable_name: str) -> Dict[str, Any]:
        """Add deliverable to component."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
                
            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}
            
            if component_name not in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} not found in feature {feature_name}"}
            
            if deliverable_name in projects[project_id].features[feature_name].components[component_name].deliverables:
                return {"error": f"Deliverable {deliverable_name} already exists in component {component_name}"}
            
            # Add deliverable
            projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name] = Deliverable(
                deliverable_name=deliverable_name
            )
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Added deliverable {deliverable_name} to component {component_name}")
            return {"success": True, "message": f"Deliverable {deliverable_name} added to component {component_name}"}
            
        except Exception as e:
            logger.error(f"Failed to add deliverable {deliverable_name} to component {component_name}: {e}", exc_info=True)
            return {"error": f"Failed to add deliverable: {e}"}

    def add_task_to_deliverable(self, project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, is_human_only_task: bool, agent_id: Optional[str] = None, human_name: Optional[str] = None, claude_task_id: Optional[str] = None) -> Dict[str, Any]:
        """Add task to deliverable."""
        try:
            projects = self._load_projects()

            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}

            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}

            if component_name not in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} not found in feature {feature_name}"}

            if deliverable_name not in projects[project_id].features[feature_name].components[component_name].deliverables:
                return {"error": f"Deliverable {deliverable_name} not found in component {component_name}"}

            if task_id in projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks:
                return {"error": f"Task {task_id} already exists in deliverable {deliverable_name}"}

            # Determine assignee based on is_human_only_task
            if is_human_only_task:
                assignee = AssigneeType.HUMAN
                if not human_name:
                    return {"error": "human_name is required for human-only tasks"}
            else:
                assignee = AssigneeType.AI
                if not agent_id:
                    return {"error": "agent_id is required for AI tasks"}

            # Add task
            projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks[task_id] = Task(
                task_id=task_id,
                assignee=assignee,
                agent_id=agent_id,
                human_name=human_name,
                claude_task_id=claude_task_id
            )
            projects[project_id].updated_at = datetime.now().isoformat()

            # Save
            self._save_projects(projects)

            logger.info(f"Added task {task_id} to deliverable {deliverable_name}")
            return {"success": True, "message": f"Task {task_id} added to deliverable {deliverable_name}"}
            
        except Exception as e:
            logger.error(f"Failed to add task {task_id} to deliverable {deliverable_name}: {e}", exc_info=True)
            return {"error": f"Failed to add task: {e}"}
    
    def add_spec_to_feature(self, project_id: str, feature_name: str, spec_file_path: str) -> Dict[str, Any]:
        """Add spec to feature."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
                
            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}
            
            # Add feature spec
            projects[project_id].features[feature_name].spec = FeatureSpec(spec_file_path=spec_file_path)
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Added spec to feature {feature_name}")
            return {"success": True, "message": f"Spec added to feature {feature_name}"}
            
        except Exception as e:
            logger.error(f"Failed to add spec to feature {feature_name}: {e}", exc_info=True)
            return {"error": f"Failed to add spec: {e}"}
    
    def add_spec_to_component(self, project_id: str, feature_name: str, component_name: str, spec_file_path: str) -> Dict[str, Any]:
        """Add spec to component."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
                
            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}
            
            if component_name not in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} not found in feature {feature_name}"}
            
            # Add component spec
            projects[project_id].features[feature_name].components[component_name].spec = ComponentSpec(spec_file_path=spec_file_path)
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Added spec to component {component_name}")
            return {"success": True, "message": f"Spec added to component {component_name}"}
            
        except Exception as e:
            logger.error(f"Failed to add spec to component {component_name}: {e}", exc_info=True)
            return {"error": f"Failed to add spec: {e}"}
    
    def add_spec_to_deliverable(self, project_id: str, feature_name: str, component_name: str, deliverable_name: str, spec_file_path: str) -> Dict[str, Any]:
        """Add spec to deliverable."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
                
            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}
            
            if component_name not in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} not found in feature {feature_name}"}
            
            if deliverable_name not in projects[project_id].features[feature_name].components[component_name].deliverables:
                return {"error": f"Deliverable {deliverable_name} not found in component {component_name}"}
            
            # Add deliverable spec
            projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].spec = DeliverableSpec(spec_file_path=spec_file_path)
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Added spec to deliverable {deliverable_name}")
            return {"success": True, "message": f"Spec added to deliverable {deliverable_name}"}
            
        except Exception as e:
            logger.error(f"Failed to add spec to deliverable {deliverable_name}: {e}", exc_info=True)
            return {"error": f"Failed to add spec: {e}"}
    
    def add_spec_to_task(self, project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, spec_file_path: str) -> Dict[str, Any]:
        """Add rollup spec to task."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
                
            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}
            
            if component_name not in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} not found in feature {feature_name}"}
            
            if deliverable_name not in projects[project_id].features[feature_name].components[component_name].deliverables:
                return {"error": f"Deliverable {deliverable_name} not found in component {component_name}"}
            
            if task_id not in projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks:
                return {"error": f"Task {task_id} not found in deliverable {deliverable_name}"}
            
            # Add task rollup spec
            projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks[task_id].spec = TaskSpec(spec_file_path=spec_file_path)
            
            # Check if task now has complete specs and mark as ready if so
            if self._task_has_complete_specs(projects[project_id], feature_name, component_name, deliverable_name, task_id):
                projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks[task_id].is_ready = True
                logger.info(f"Task {task_id} now has complete specs and is marked ready")
            
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Added rollup spec to task {task_id}")
            return {"success": True, "message": f"Rollup spec added to task {task_id}"}
            
        except Exception as e:
            logger.error(f"Failed to add spec to task {task_id}: {e}", exc_info=True)
            return {"error": f"Failed to add spec: {e}"}
    
    def update_project_mode(self, project_id: str, mode: str) -> Dict[str, Any]:
        """Update project mode and save to JSON."""
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
            
            # Update mode
            projects[project_id].mode = mode
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Updated project {project_id} mode to {mode}")
            return {"success": True, "message": f"Project {project_id} mode updated to {mode}"}
            
        except Exception as e:
            logger.error(f"Failed to update project {project_id} mode: {e}", exc_info=True)
            return {"error": f"Failed to update project mode: {e}"}
    
    def _task_has_complete_specs(self, project: Project, feature_name: str, component_name: str, deliverable_name: str, task_id: str) -> bool:
        """Check if task has complete spec hierarchy (feature, component, deliverable, task specs)."""
        try:
            feature = project.features.get(feature_name)
            if not feature or not feature.spec:
                return False
            
            component = feature.components.get(component_name) 
            if not component or not component.spec:
                return False
                
            deliverable = component.deliverables.get(deliverable_name)
            if not deliverable or not deliverable.spec:
                return False
                
            task = deliverable.tasks.get(task_id)
            if not task or not task.spec:
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking task specs: {e}")
            return False
    
    def update_task_status(
        self,
        project_id: str,
        feature_name: str,
        component_name: str,
        deliverable_name: str,
        task_id: str,
        is_done: bool,
        is_blocked: bool,
        blocked_description: Optional[str],
        is_ready: bool,
        is_measured: bool = False,
        # Context metadata fields for contextualization protocol
        files_touched: Optional[List[str]] = None,
        lines_that_matter: Optional[str] = None,
        context_deps: Optional[List[str]] = None,
        key_insight: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update task status.

        is_done: Mark work complete (→ IN_REVIEW → measure lane)
        is_measured: Mark measurement complete (→ DONE → learn lane)

        Context metadata (optional):
        - files_touched: Files modified while completing this task
        - lines_that_matter: Relevant line ranges (e.g., '42-87')
        - context_deps: Files read to understand this task
        - key_insight: Key pattern or insight discovered
        """
        try:
            projects = self._load_projects()
            
            if project_id not in projects:
                return {"error": f"Project {project_id} not found"}
                
            if feature_name not in projects[project_id].features:
                return {"error": f"Feature {feature_name} not found in project {project_id}"}
            
            if component_name not in projects[project_id].features[feature_name].components:
                return {"error": f"Component {component_name} not found in feature {feature_name}"}
            
            if deliverable_name not in projects[project_id].features[feature_name].components[component_name].deliverables:
                return {"error": f"Deliverable {deliverable_name} not found in component {component_name}"}
            
            if task_id not in projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks:
                return {"error": f"Task {task_id} not found in deliverable {deliverable_name}"}
            
            # Get task
            task = projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name].tasks[task_id]
            
            # Update status based on parameters
            if is_blocked:
                task.status = TaskStatus.BLOCKED
                task.blocked_description = blocked_description
            elif is_measured:
                task.status = TaskStatus.DONE  # Measurement complete → learn lane
            elif is_done:
                task.status = TaskStatus.IN_REVIEW  # Work complete → measure lane
            elif task.status == TaskStatus.READY and is_ready:
                task.status = TaskStatus.IN_PROGRESS
            
            # Validate specs before allowing is_ready=True
            if is_ready and not self._task_has_complete_specs(projects[project_id], feature_name, component_name, deliverable_name, task_id):
                return {"error": f"Task {task_id} cannot be ready - missing required specs (feature, component, deliverable, and task specs must all exist)"}
            
            task.is_blocked = is_blocked
            task.is_ready = is_ready
            task.updated_at = datetime.now().isoformat()

            # Update context metadata if provided
            if files_touched is not None:
                task.files_touched = files_touched
            if lines_that_matter is not None:
                task.lines_that_matter = lines_that_matter
            if context_deps is not None:
                task.context_deps = context_deps
            if key_insight is not None:
                task.key_insight = key_insight

            # Check if deliverable is complete (all sibling tasks at same completion level)
            deliverable_complete = False
            if is_done or is_measured:
                deliverable = projects[project_id].features[feature_name].components[component_name].deliverables[deliverable_name]

                # If marking task as done, check if all tasks are in_review
                if is_done:
                    all_tasks_done = all(t.status == TaskStatus.IN_REVIEW for t in deliverable.tasks.values())
                    if all_tasks_done:
                        deliverable_complete = True
                        logger.info(f"Deliverable {deliverable_name} work complete - all tasks in review")

                # If marking task as measured, check if all tasks are done
                elif is_measured:
                    all_tasks_measured = all(t.status == TaskStatus.DONE for t in deliverable.tasks.values())
                    if all_tasks_measured:
                        deliverable_complete = True
                        logger.info(f"Deliverable {deliverable_name} measurement complete - all tasks done")

            # TreeKanban integration: Sync status changes
            treekanban_result = self._sync_to_treekanban(
                project_id, feature_name, component_name, deliverable_name, task_id, task, deliverable_complete
            )

            # GitHub integration: Create issue when task becomes ready
            if is_ready and not task.github_issue_id and projects[project_id].github_repo_url:
                github_result = self._create_github_issue(
                    projects[project_id], feature_name, component_name, deliverable_name, task
                )
                if github_result.get("success"):
                    task.github_issue_id = github_result["issue_id"]
                    task.github_issue_url = github_result["issue_url"]
                    logger.info(f"Created GitHub issue {task.github_issue_id} for task {task_id}")
                else:
                    logger.warning(f"Failed to create GitHub issue for task {task_id}: {github_result.get('error')}")
            
            # GitHub integration: Update issue status when task status changes
            if task.github_issue_id and projects[project_id].github_repo_url:
                github_status = task.status.value if hasattr(task.status, 'value') else str(task.status)
                github_result = self._update_github_issue_status(
                    projects[project_id], task.github_issue_id, github_status
                )
                if not github_result.get("success"):
                    logger.warning(f"Failed to update GitHub issue {task.github_issue_id}: {github_result.get('error')}")
            
            projects[project_id].updated_at = datetime.now().isoformat()
            
            # Save
            self._save_projects(projects)
            
            logger.info(f"Updated task {task_id} status to {task.status}")

            result = {
                "success": True,
                "task": task.dict(),
                "message": f"Task {task_id} status updated to {task.status}",
                "treekanban_sync": treekanban_result
            }

            # Add deliverable completion info if applicable
            if deliverable_complete:
                result["deliverable_complete"] = True
                result["deliverable_completion_message"] = (
                    f"Deliverable {deliverable_name} is complete! All tasks done. "
                    f"Next: Call flightsim with config='giint_measurement' and metadata: "
                    f"project_id={project_id}, feature={feature_name}, component={component_name}, "
                    f"deliverable={deliverable_name}, task_id={task_id}"
                )

            return result
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id} status: {e}", exc_info=True)
            return {"error": f"Failed to update task status: {e}"}

    def _sync_to_treekanban(
        self,
        project_id: str,
        feature_name: str,
        component_name: str,
        deliverable_name: str,
        task_id: str,
        task: Task,
        deliverable_complete: bool = False
    ) -> Dict[str, Any]:
        """Sync GIINT task status to TreeKanban card.

        If deliverable_complete=True, also moves the deliverable card to measure.
        """
        try:
            from heaven_bml_sqlite.heaven_bml_sqlite_client import HeavenBMLSQLiteClient
        except ImportError as e:
            logger.warning(f"TreeKanban client not available: {e}")
            return {"success": False, "message": "TreeKanban not available"}

        try:
            client = HeavenBMLSQLiteClient()
            board_name = os.getenv("GIINT_TREEKANBAN_BOARD")
            if not board_name:
                return {"success": False, "message": "GIINT_TREEKANBAN_BOARD environment variable not set"}

            # Find card by GIINT tags
            all_cards = client.get_all_cards(board_name)

            matching_card = None
            for card in all_cards:
                card_tags = card.get("tags", [])
                if isinstance(card_tags, str):
                    import json
                    card_tags = json.loads(card_tags) if card_tags.startswith('[') else [card_tags]

                # Check if card has all required tags
                if (project_id in card_tags and
                    deliverable_name in card_tags and
                    task_id in card_tags and
                    "task" in card_tags):
                    matching_card = card
                    break

            if not matching_card:
                logger.warning(f"No TreeKanban card found for GIINT task {task_id}")
                return {"success": False, "message": f"No card found for task {task_id}"}

            card_id = matching_card["id"]
            updates = {}

            # Determine new status based on task state
            if task.is_blocked:
                # Move to blocked lane and update description
                updates["status"] = "blocked"
                current_desc = matching_card.get("description", "")
                # Add blocked description if not already there
                if task.blocked_description and task.blocked_description not in current_desc:
                    updates["description"] = f"{current_desc}\n\n**BLOCKED**: {task.blocked_description}"
                logger.info(f"Moving card {card_id} to blocked lane")

            elif task.status == TaskStatus.IN_REVIEW:
                # Task work is done - move to measure lane with completion metadata
                updates["status"] = "measure"
                meta_parts = []
                if task.files_touched:
                    meta_parts.append(f"**Files touched**: {', '.join(task.files_touched)}")
                if task.key_insight:
                    meta_parts.append(f"**Key insight**: {task.key_insight}")
                if task.context_deps:
                    meta_parts.append(f"**Context deps**: {', '.join(task.context_deps)}")
                if task.lines_that_matter:
                    meta_parts.append(f"**Lines**: {task.lines_that_matter}")
                if meta_parts:
                    current_desc = matching_card.get("description", "")
                    updates["description"] = f"{current_desc}\n\n---\n**COMPLETION METADATA**\n" + "\n".join(meta_parts)
                logger.info(f"Moving task card {card_id} to measure lane")

            elif task.status == TaskStatus.DONE:
                # Measurement complete - move to learn lane with digest
                updates["status"] = "learn"
                learn_parts = []
                if task.files_touched:
                    learn_parts.append(f"**Files**: {', '.join(task.files_touched)}")
                if task.key_insight:
                    learn_parts.append(f"**Insight**: {task.key_insight}")
                if task.context_deps:
                    learn_parts.append(f"**Context deps**: {', '.join(task.context_deps)}")
                if learn_parts:
                    current_desc = matching_card.get("description", "")
                    updates["description"] = f"{current_desc}\n\n---\n**LEARN DIGEST**\n" + "\n".join(learn_parts)
                logger.info(f"Moving task card {card_id} to learn lane with digest")

            # Apply updates if any
            if updates:
                updates["board"] = board_name
                result = client._make_request("PUT", f"/api/sqlite/cards/{card_id}", updates)
                if not result:
                    return {"success": False, "message": f"Failed to update TreeKanban card {card_id}"}
                logger.info(f"Successfully moved task card {card_id}")

            # If deliverable is complete, also move the deliverable card to measure
            if deliverable_complete:
                logger.info(f"Deliverable {deliverable_name} complete - searching for deliverable card")

                # Find deliverable card (has deliverable_name in tags, no "task" tag)
                deliverable_card = None
                for card in all_cards:
                    card_tags = card.get("tags", [])
                    if isinstance(card_tags, str):
                        import json
                        card_tags = json.loads(card_tags) if card_tags.startswith('[') else [card_tags]

                    # Check if this is the deliverable card (has deliverable tag but not task tag)
                    if (deliverable_name in card_tags and
                        "deliverable" in card_tags and
                        "task" not in card_tags):
                        deliverable_card = card
                        break

                if deliverable_card:
                    deliverable_id = deliverable_card["id"]

                    # Determine target lane: learn if all tasks DONE, measure if all tasks IN_REVIEW
                    target_lane = "learn" if task.status == TaskStatus.DONE else "measure"
                    deliverable_updates = {"board": board_name, "status": target_lane}
                    deliverable_result = client._make_request("PUT", f"/api/sqlite/cards/{deliverable_id}", deliverable_updates)

                    if deliverable_result:
                        logger.info(f"✅ Moved deliverable card {deliverable_id} ({deliverable_name}) to {target_lane} lane")

                        # If moving to learn, also move all child tasks
                        if target_lane == "learn":
                            logger.info(f"Moving all child tasks of {deliverable_name} to learn lane")
                            for card in all_cards:
                                card_tags = card.get("tags", [])
                                if isinstance(card_tags, str):
                                    import json
                                    card_tags = json.loads(card_tags) if card_tags.startswith('[') else [card_tags]

                                # Check if this is a task card for this deliverable
                                if (deliverable_name in card_tags and
                                    "task" in card_tags and
                                    project_id in card_tags):
                                    task_card_id = card["id"]
                                    task_updates = {"board": board_name, "status": "learn"}
                                    task_result = client._make_request("PUT", f"/api/sqlite/cards/{task_card_id}", task_updates)
                                    if task_result:
                                        logger.info(f"✅ Moved task card {task_card_id} to learn lane with deliverable")
                    else:
                        logger.warning(f"Failed to move deliverable card {deliverable_id} to {target_lane}")
                else:
                    logger.warning(f"Could not find deliverable card for {deliverable_name}")

            return {"success": True, "message": f"Synced task {task_id} to TreeKanban" + (" and deliverable" if deliverable_complete else "")}

        except Exception as e:
            logger.error(f"Failed to sync to TreeKanban: {e}", exc_info=True)
            return {"success": False, "message": f"TreeKanban sync error: {str(e)}"}

    def _get_github_pat(self) -> Optional[str]:
        """Get GitHub PAT from environment variable."""
        return os.getenv('GH_PAT')
    
    def _create_github_issue(self, project: Project, feature_name: str, component_name: str, deliverable_name: str, task: Task) -> Dict[str, Any]:
        """Create GitHub issue for task when marked ready."""
        if not project.github_repo_url:
            return {"success": False, "error": "No GitHub repo URL configured for project"}
        
        gh_pat = self._get_github_pat()
        if not gh_pat:
            return {"success": False, "error": "GH_PAT environment variable not set"}
        
        try:
            # Parse repo URL to get owner/repo
            repo_parts = project.github_repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
            if len(repo_parts) != 2:
                return {"success": False, "error": "Invalid GitHub repo URL format"}
            
            owner, repo = repo_parts
            
            # Create issue title and body
            title = f"[{feature_name}.{component_name}.{deliverable_name}] {task.task_id}"
            body = f"""**GIINT Task**: {task.task_id}
**Project**: {project.project_id}
**Feature**: {feature_name}
**Component**: {component_name}  
**Deliverable**: {deliverable_name}
**Assignee**: {task.assignee.value}

**Task Spec**: {task.spec.spec_file_path if task.spec else 'No spec file'}

This issue was automatically created by GIINT when the task was marked ready.
"""
            
            # Use gh CLI to create issue
            cmd = [
                'gh', 'issue', 'create',
                '--repo', f"{owner}/{repo}",
                '--title', title,
                '--body', body,
                '--label', 'giint-task,ready',
                '--label', f'feature:{feature_name}'
            ]
            
            env = os.environ.copy()
            env['GH_TOKEN'] = gh_pat
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                logger.error(f"GitHub issue creation failed: {result.stderr}")
                return {"success": False, "error": f"gh command failed: {result.stderr}"}
            
            # Parse issue URL from output
            issue_url = result.stdout.strip()
            issue_id = issue_url.split('/')[-1]
            
            logger.info(f"Created GitHub issue {issue_id} for task {task.task_id}")
            return {
                "success": True,
                "issue_id": issue_id,
                "issue_url": issue_url
            }
            
        except Exception as e:
            logger.error(f"Failed to create GitHub issue: {e}")
            return {"success": False, "error": f"Failed to create GitHub issue: {str(e)}"}
    
    def _update_github_issue_status(self, project: Project, issue_id: str, status: str) -> Dict[str, Any]:
        """Update GitHub issue status (ready -> in-progress -> in-review)."""
        if not project.github_repo_url:
            return {"success": False, "error": "No GitHub repo URL configured"}
        
        gh_pat = self._get_github_pat()
        if not gh_pat:
            return {"success": False, "error": "GH_PAT environment variable not set"}
        
        try:
            repo_parts = project.github_repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
            if len(repo_parts) != 2:
                return {"success": False, "error": "Invalid GitHub repo URL format"}
            
            owner, repo = repo_parts
            
            # Map GIINT status to GitHub labels
            status_labels = {
                "ready": ["ready"],
                "in_progress": ["in-progress"], 
                "in_review": ["in-review"],
                "done": ["done"]
            }
            
            if status not in status_labels:
                return {"success": False, "error": f"Unknown status: {status}"}
            
            # Remove old status labels and add new one
            old_labels = ["ready", "in-progress", "in-review", "done"]
            for old_label in old_labels:
                subprocess.run([
                    'gh', 'issue', 'edit', issue_id,
                    '--repo', f"{owner}/{repo}",
                    '--remove-label', old_label
                ], env={'GH_TOKEN': gh_pat}, capture_output=True)
            
            # Add new status label
            cmd = [
                'gh', 'issue', 'edit', issue_id,
                '--repo', f"{owner}/{repo}",
                '--add-label', status_labels[status][0]
            ]
            
            env = os.environ.copy()
            env['GH_TOKEN'] = gh_pat
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                logger.error(f"GitHub issue update failed: {result.stderr}")
                return {"success": False, "error": f"gh command failed: {result.stderr}"}
            
            logger.info(f"Updated GitHub issue {issue_id} status to {status}")
            return {"success": True, "message": f"Issue {issue_id} updated to {status}"}
            
        except Exception as e:
            logger.error(f"Failed to update GitHub issue: {e}")
            return {"success": False, "error": f"Failed to update GitHub issue: {str(e)}"}


# Global registry instance
_registry = None

def get_registry() -> ProjectRegistry:
    """Get or create global project registry."""
    global _registry
    if _registry is None:
        _registry = ProjectRegistry()
    return _registry


# Convenience functions
def create_project(project_id: str, project_dir: str, starlog_path: Optional[str] = None, github_repo_url: Optional[str] = None, project_type: ProjectType = ProjectType.SINGLE) -> Dict[str, Any]:
    """Create a new project."""
    return get_registry().create_project(project_id, project_dir, starlog_path, github_repo_url, project_type)

def get_project(project_id: str) -> Dict[str, Any]:
    """Get project by ID."""
    return get_registry().get_project(project_id)

def get_project_by_dir(project_dir: str) -> Dict[str, Any]:
    """Get project by STARSYSTEM directory path."""
    return get_registry().get_project_by_dir(project_dir)

def update_project(project_id: str, project_dir: Optional[str] = None, starlog_path: Optional[str] = None, github_repo_url: Optional[str] = None) -> Dict[str, Any]:
    """Update existing project."""
    return get_registry().update_project(project_id, project_dir, starlog_path, github_repo_url)

def list_projects() -> Dict[str, Any]:
    """List all projects."""
    return get_registry().list_projects()

def delete_project(project_id: str) -> Dict[str, Any]:
    """Delete project by ID."""
    return get_registry().delete_project(project_id)

def add_sub_project(composite_project_id: str, sub_project_id: str) -> Dict[str, Any]:
    """Add a sub-project to a composite project."""
    return get_registry().add_sub_project(composite_project_id, sub_project_id)

def add_feature_to_project(project_id: str, feature_name: str) -> Dict[str, Any]:
    """Add feature to project."""
    return get_registry().add_feature_to_project(project_id, feature_name)

def add_component_to_feature(project_id: str, feature_name: str, component_name: str) -> Dict[str, Any]:
    """Add component to feature."""
    return get_registry().add_component_to_feature(project_id, feature_name, component_name)

def add_deliverable_to_component(project_id: str, feature_name: str, component_name: str, deliverable_name: str) -> Dict[str, Any]:
    """Add deliverable to component."""
    return get_registry().add_deliverable_to_component(project_id, feature_name, component_name, deliverable_name)

def add_task_to_deliverable(project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, is_human_only_task: bool, agent_id: Optional[str] = None, human_name: Optional[str] = None, claude_task_id: Optional[str] = None) -> Dict[str, Any]:
    """Add task to deliverable."""
    return get_registry().add_task_to_deliverable(project_id, feature_name, component_name, deliverable_name, task_id, is_human_only_task, agent_id, human_name, claude_task_id)

def update_task_status(
    project_id: str,
    feature_name: str,
    component_name: str,
    deliverable_name: str,
    task_id: str,
    is_done: bool,
    is_blocked: bool,
    blocked_description: Optional[str],
    is_ready: bool,
    is_measured: bool = False,
    files_touched: Optional[List[str]] = None,
    lines_that_matter: Optional[str] = None,
    context_deps: Optional[List[str]] = None,
    key_insight: Optional[str] = None
) -> Dict[str, Any]:
    """Update task status with optional context metadata."""
    return get_registry().update_task_status(
        project_id, feature_name, component_name, deliverable_name, task_id,
        is_done, is_blocked, blocked_description, is_ready, is_measured,
        files_touched, lines_that_matter, context_deps, key_insight
    )

def add_spec_to_feature(project_id: str, feature_name: str, spec_file_path: str) -> Dict[str, Any]:
    """Add spec to feature."""
    return get_registry().add_spec_to_feature(project_id, feature_name, spec_file_path)

def add_spec_to_component(project_id: str, feature_name: str, component_name: str, spec_file_path: str) -> Dict[str, Any]:
    """Add spec to component."""
    return get_registry().add_spec_to_component(project_id, feature_name, component_name, spec_file_path)

def add_spec_to_deliverable(project_id: str, feature_name: str, component_name: str, deliverable_name: str, spec_file_path: str) -> Dict[str, Any]:
    """Add spec to deliverable."""
    return get_registry().add_spec_to_deliverable(project_id, feature_name, component_name, deliverable_name, spec_file_path)

def add_spec_to_task(project_id: str, feature_name: str, component_name: str, deliverable_name: str, task_id: str, spec_file_path: str) -> Dict[str, Any]:
    """Add rollup spec to task."""
    return get_registry().add_spec_to_task(project_id, feature_name, component_name, deliverable_name, task_id, spec_file_path)

def update_project_mode(project_id: str, mode: str) -> Dict[str, Any]:
    """Update project mode."""
    return get_registry().update_project_mode(project_id, mode)