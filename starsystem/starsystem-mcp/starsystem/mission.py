#!/usr/bin/env python3
"""
Mission System - Cross-session sequence enforcement with step injection and ratcheting

Provides mission creation, execution tracking, step injection, and extraction capabilities.
Missions enforce ordered session sequences across multiple STARLOG projects with resilience.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Import mission_types for template rendering
from . import mission_types

logger = logging.getLogger(__name__)

# Mission storage directory
MISSION_DIR = Path("/tmp/heaven_data/missions")
MISSION_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MissionSession:
    """Represents a single session in a mission sequence"""
    project_path: str
    flight_config: str
    status: str = "pending"  # pending, in_progress, completed, aborted
    notes: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class MissionMetrics:
    """Mission execution metrics"""
    conversations_count: int = 0
    sessions_completed: int = 0
    sessions_aborted: int = 0
    total_duration_minutes: int = 0


@dataclass
class Mission:
    """Mission definition with session sequence"""
    mission_id: str
    name: str
    description: str
    domain: str
    subdomain: str
    session_sequence: List[MissionSession]
    current_step: int = 0
    status: str = "pending"  # pending, active, completed, extracted
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metrics: Optional[MissionMetrics] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Ensure metrics is included
        if self.metrics is None:
            data['metrics'] = asdict(MissionMetrics())
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mission':
        """Create Mission from dictionary"""
        # Convert session dicts to MissionSession objects
        data['session_sequence'] = [
            MissionSession(**s) if isinstance(s, dict) else s
            for s in data['session_sequence']
        ]
        # Convert metrics dict to MissionMetrics object
        if 'metrics' in data and isinstance(data['metrics'], dict):
            data['metrics'] = MissionMetrics(**data['metrics'])
        elif 'metrics' not in data:
            data['metrics'] = MissionMetrics()
        return cls(**data)


def save_mission(mission: Mission) -> None:
    """Save mission to storage"""
    mission_file = MISSION_DIR / f"{mission.mission_id}.json"
    with open(mission_file, 'w') as f:
        json.dump(mission.to_dict(), f, indent=2)
    logger.info(f"Saved mission: {mission.mission_id}")


def load_mission(mission_id: str) -> Optional[Mission]:
    """Load mission from storage"""
    mission_file = MISSION_DIR / f"{mission_id}.json"
    if not mission_file.exists():
        return None

    with open(mission_file, 'r') as f:
        data = json.load(f)

    return Mission.from_dict(data)


def create_mission(
    mission_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    domain: Optional[str] = None,
    subdomain: Optional[str] = None,
    session_sequence: Optional[List[Dict[str, str]]] = None,
    mission_type: Optional[str] = None,
    mission_type_domain: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a new mission definition

    Two modes:
    1. Manual: Provide name, description, domain, subdomain, session_sequence
    2. From template: Provide mission_type, mission_type_domain, variables

    Args:
        mission_id: Unique mission identifier
        name: Human-readable mission name (manual mode)
        description: Mission description (manual mode)
        domain: Mission domain (manual mode)
        subdomain: Mission subdomain (manual mode)
        session_sequence: List of session dicts with project_path and flight_config (manual mode)
        mission_type: Mission type template ID (template mode)
        mission_type_domain: Domain containing the mission type (template mode)
        variables: Variables to substitute in template (template mode)

    Returns:
        Mission creation result with mission_id
    """
    try:
        # Check if mission already exists
        if (MISSION_DIR / f"{mission_id}.json").exists():
            return {
                "success": False,
                "error": f"Mission '{mission_id}' already exists"
            }

        # Template mode - render mission type
        if mission_type:
            if not mission_type_domain:
                return {
                    "success": False,
                    "error": "mission_type_domain required when using mission_type"
                }
            if not variables:
                return {
                    "success": False,
                    "error": "variables required when using mission_type"
                }

            # Render mission type with variables
            render_result = mission_types.render_mission_type(
                mission_type_id=mission_type,
                domain=mission_type_domain,
                variables=variables
            )

            if not render_result.get("success"):
                return render_result

            # Extract rendered mission data
            rendered = render_result["rendered_mission"]
            name = rendered["name"]
            domain = rendered["domain"]
            subdomain = rendered["subdomain"]
            description = rendered["description"]
            session_sequence = rendered["session_sequence"]

        # Manual mode - validate required fields
        else:
            if not all([name, description, domain, subdomain, session_sequence]):
                return {
                    "success": False,
                    "error": "Manual mode requires: name, description, domain, subdomain, session_sequence"
                }

        # Create MissionSession objects
        sessions = [MissionSession(**s) for s in session_sequence]

        # Create mission
        mission = Mission(
            mission_id=mission_id,
            name=name,
            description=description,
            domain=domain,
            subdomain=subdomain,
            session_sequence=sessions,
            created_at=datetime.now().isoformat(),
            metrics=MissionMetrics()
        )

        # Save mission
        save_mission(mission)

        mode = "template" if mission_type else "manual"
        return {
            "success": True,
            "mission_id": mission_id,
            "message": f"Created mission: {name} (from {mission_type})" if mission_type else f"Created mission: {name}",
            "session_count": len(sessions),
            "mode": mode,
            "next_step": f"Start mission with: start_mission('{mission_id}')"
        }

    except Exception as e:
        logger.error(f"Error creating mission: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def start_mission(mission_id: str) -> Dict[str, Any]:
    """
    Activate a mission from HOME mode

    Args:
        mission_id: Mission to activate

    Returns:
        Mission activation result with first session details
    """
    try:
        mission = load_mission(mission_id)
        if not mission:
            return {
                "success": False,
                "error": f"Mission '{mission_id}' not found"
            }

        if mission.status == "active":
            # Re-inject course state for already-active mission (resume after go_home/compaction)
            current_step = mission.current_step or 0
            current_session = mission.session_sequence[current_step] if current_step < len(mission.session_sequence) else None
            projects = list(set(session.project_path for session in mission.session_sequence))
            return {
                "success": True,
                "mission_id": mission_id,
                "message": f"Resumed active mission: {mission.name}",
                "resumed": True,
                "current_step": current_step,
                "projects": projects,
                "next_session": {
                    "project_path": current_session.project_path if current_session else None,
                    "flight_config": current_session.flight_config if current_session else None
                } if current_session else None
            }

        # Activate mission
        mission.status = "active"
        mission.started_at = datetime.now().isoformat()
        mission.current_step = 0

        # Update first session status
        mission.session_sequence[0].status = "in_progress"
        mission.session_sequence[0].started_at = datetime.now().isoformat()

        save_mission(mission)

        # Get first session
        first_session = mission.session_sequence[0]

        # Extract unique project paths from entire session sequence
        projects = list(set(session.project_path for session in mission.session_sequence))

        return {
            "success": True,
            "mission_id": mission_id,
            "message": f"Activated mission: {mission.name}",
            "current_step": 0,
            "projects": projects,  # All unique projects in mission
            "next_session": {
                "project_path": first_session.project_path,
                "flight_config": first_session.flight_config
            }
        }

    except Exception as e:
        logger.error(f"Error starting mission: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_mission_status(mission_id: str) -> Dict[str, Any]:
    """
    Get current mission status and progress

    Args:
        mission_id: Mission to query

    Returns:
        Mission status with current step and session details
    """
    try:
        mission = load_mission(mission_id)
        if not mission:
            return {
                "success": False,
                "error": f"Mission '{mission_id}' not found"
            }

        current_session = mission.session_sequence[mission.current_step]

        return {
            "success": True,
            "mission_id": mission_id,
            "name": mission.name,
            "status": mission.status,
            "current_step": mission.current_step,
            "total_steps": len(mission.session_sequence),
            "current_session": {
                "project_path": current_session.project_path,
                "flight_config": current_session.flight_config,
                "status": current_session.status,
                "notes": current_session.notes
            },
            "metrics": asdict(mission.metrics),
            "progress": f"{mission.current_step + 1}/{len(mission.session_sequence)}"
        }

    except Exception as e:
        logger.error(f"Error getting mission status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def inject_mission_step(
    mission_id: str,
    project_path: str,
    flight_config: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Inject a new step BEFORE the current step in mission sequence

    Args:
        mission_id: Mission to modify
        project_path: Project path for new step
        flight_config: Flight config for new step
        notes: Optional notes about why step was injected

    Returns:
        Injection result with updated step index
    """
    try:
        mission = load_mission(mission_id)
        if not mission:
            return {
                "success": False,
                "error": f"Mission '{mission_id}' not found"
            }

        if mission.status != "active":
            return {
                "success": False,
                "error": f"Can only inject steps into active missions (status: {mission.status})"
            }

        # Create new session
        new_session = MissionSession(
            project_path=project_path,
            flight_config=flight_config,
            status="pending",
            notes=notes or "Injected step due to obstacle/requirement"
        )

        # Insert before current step
        mission.session_sequence.insert(mission.current_step, new_session)

        save_mission(mission)

        return {
            "success": True,
            "mission_id": mission_id,
            "message": f"Injected step at position {mission.current_step}",
            "total_steps": len(mission.session_sequence),
            "injected_session": {
                "project_path": project_path,
                "flight_config": flight_config
            }
        }

    except Exception as e:
        logger.error(f"Error injecting mission step: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def report_mission_progress(mission_id: str) -> Dict[str, Any]:
    """
    Report successful completion of current mission step and advance to next

    Marks current session as completed, increments step, checks if mission is complete.
    User calls this when they've successfully finished a mission step.

    Args:
        mission_id: Mission to update

    Returns:
        Progress report with next session or completion status
    """
    try:
        mission = load_mission(mission_id)
        if not mission:
            return {
                "success": False,
                "error": f"Mission '{mission_id}' not found"
            }

        if mission.status != "active":
            return {
                "success": False,
                "error": f"Cannot report progress on non-active mission (status: {mission.status})"
            }

        # Mark current session as completed
        current_session = mission.session_sequence[mission.current_step]
        current_session.status = "completed"
        current_session.completed_at = datetime.now().isoformat()
        mission.metrics.sessions_completed += 1

        # Increment to next step
        mission.current_step += 1

        # Check if mission is complete
        if mission.current_step >= len(mission.session_sequence):
            # Mission complete!
            mission.status = "completed"
            mission.completed_at = datetime.now().isoformat()
            save_mission(mission)

            return {
                "success": True,
                "mission_complete": True,
                "mission_id": mission_id,
                "message": f"🎉 Mission '{mission.name}' completed!",
                "total_sessions": len(mission.session_sequence),
                "completed_sessions": mission.metrics.sessions_completed,
                "return_to_home": True
            }
        else:
            # More sessions to go
            next_session = mission.session_sequence[mission.current_step]
            next_session.status = "in_progress"
            next_session.started_at = datetime.now().isoformat()
            save_mission(mission)

            return {
                "success": True,
                "mission_complete": False,
                "mission_id": mission_id,
                "message": f"Step {mission.current_step}/{len(mission.session_sequence)} - Advancing to next session",
                "current_step": mission.current_step,
                "total_steps": len(mission.session_sequence),
                "next_session": {
                    "project_path": next_session.project_path,
                    "flight_config": next_session.flight_config
                },
                "progress": f"{mission.current_step + 1}/{len(mission.session_sequence)}"
            }

    except Exception as e:
        logger.error(f"Error reporting mission progress: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def request_mission_extraction(mission_id: str) -> Dict[str, Any]:
    """
    Extract mission learnings and reset to HOME

    Analyzes mission execution, generates failure report, and resets system state

    Args:
        mission_id: Mission to extract

    Returns:
        Extraction report with learnings and reset confirmation
    """
    try:
        mission = load_mission(mission_id)
        if not mission:
            return {
                "success": False,
                "error": f"Mission '{mission_id}' not found"
            }

        # Analyze mission execution
        completed_steps = [
            s for s in mission.session_sequence
            if s.status == "completed"
        ]
        aborted_steps = [
            s for s in mission.session_sequence
            if s.status == "aborted"
        ]

        # Generate extraction report
        report = {
            "mission_id": mission_id,
            "mission_name": mission.name,
            "total_steps": len(mission.session_sequence),
            "completed_steps": len(completed_steps),
            "aborted_steps": len(aborted_steps),
            "current_step": mission.current_step,
            "execution_summary": {
                "status": mission.status,
                "started_at": mission.started_at,
                "metrics": asdict(mission.metrics)
            },
            "completed_sessions": [
                {
                    "project": s.project_path,
                    "flight": s.flight_config,
                    "completed_at": s.completed_at
                }
                for s in completed_steps
            ],
            "aborted_sessions": [
                {
                    "project": s.project_path,
                    "flight": s.flight_config,
                    "notes": s.notes
                }
                for s in aborted_steps
            ],
            "learnings": "Mission extracted - analyze aborted steps to refine mission template for next execution"
        }

        # Update mission status
        mission.status = "extracted"
        mission.completed_at = datetime.now().isoformat()
        save_mission(mission)

        return {
            "success": True,
            "message": f"Extracted mission: {mission.name}",
            "extraction_report": report,
            "reset_to_home": True
        }

    except Exception as e:
        logger.error(f"Error extracting mission: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def inject_step(
    mission_id: str,
    project_path: str,
    flight_config: str,
    notes: Optional[str] = None
) -> None:
    """
    Append a new session step to the mission sequence (for auto-injection)

    Used by starlog.start_starlog() to auto-inject sessions into base missions.
    Simply appends the session to session_sequence without changing current_step.

    Args:
        mission_id: Mission to update
        project_path: STARLOG project path
        flight_config: Flight config name
        notes: Optional notes
    """
    try:
        mission = load_mission(mission_id)
        if not mission:
            logger.warning(f"Auto-inject failed: Mission '{mission_id}' not found")
            return

        if mission.status != "active":
            logger.warning(f"Auto-inject skipped: Mission not active (status: {mission.status})")
            return

        # Create new session entry
        new_session = MissionSession(
            project_path=project_path,
            flight_config=flight_config,
            status="in_progress",
            notes=notes,
            started_at=datetime.now().isoformat()
        )

        # Append to session_sequence
        mission.session_sequence.append(new_session)

        # Save mission
        save_mission(mission)
        logger.info(f"Auto-injected session into {mission_id}: {project_path} with {flight_config}")

    except Exception as e:
        logger.error(f"Failed to auto-inject step into mission: {e}")


def list_missions(status_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    List all missions, optionally filtered by status

    Args:
        status_filter: Optional status to filter by (pending, active, completed, extracted)

    Returns:
        List of missions with basic info
    """
    try:
        missions = []
        for mission_file in MISSION_DIR.glob("*.json"):
            mission = load_mission(mission_file.stem)
            if mission:
                if status_filter is None or mission.status == status_filter:
                    missions.append({
                        "mission_id": mission.mission_id,
                        "name": mission.name,
                        "status": mission.status,
                        "domain": mission.domain,
                        "current_step": mission.current_step,
                        "total_steps": len(mission.session_sequence)
                    })

        return {
            "success": True,
            "missions": missions,
            "count": len(missions)
        }

    except Exception as e:
        logger.error(f"Error listing missions: {e}")
        return {
            "success": False,
            "error": str(e)
        }
