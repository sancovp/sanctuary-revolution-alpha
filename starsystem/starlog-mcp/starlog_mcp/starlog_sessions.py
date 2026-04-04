"""Starlog sessions mixin for session management and history."""

import json
import logging
import os
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import StarlogEntry, DebugDiaryEntry, JointSessionEntry

logger = logging.getLogger(__name__)

COURSE_STATE_PATH = os.path.join(
    os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"),
    "omnisanc_core", ".course_state"
)


def _update_course_state_session(session_id: str | None, project_name: str | None) -> None:
    """Write active starlog session ID + project to .course_state for hook discovery."""
    try:
        state = {}
        if os.path.exists(COURSE_STATE_PATH):
            with open(COURSE_STATE_PATH, "r") as f:
                state = json.load(f)
        state["active_starlog_session_id"] = session_id
        state["active_starlog_project"] = project_name
        with open(COURSE_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to update .course_state session: {e}")


def resolve_starsystem_for_file(file_path: str) -> tuple[str | None, str | None]:
    """Walk up from file_path to find nearest starlog.hpi. Returns (project_name, starsystem_path) or (None, None)."""
    current = os.path.abspath(file_path)
    # If it's a file, start from its parent dir
    if os.path.isfile(current):
        current = os.path.dirname(current)
    for _ in range(20):  # max 20 levels up
        hpi = os.path.join(current, "starlog.hpi")
        if os.path.exists(hpi):
            try:
                with open(hpi, "r") as f:
                    data = json.load(f)
                name = data.get("project_name", os.path.basename(current))
                return name, current
            except Exception:
                return os.path.basename(current), current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None, None


def _extract_file_paths(entry_content: str, in_file: str | None) -> list[str]:
    """Extract file paths from diary entry content and in_file field."""
    import re
    paths = []
    if in_file:
        # in_file can be comma-separated
        for p in in_file.split(","):
            p = p.strip()
            if p.startswith("/"):
                paths.append(p)
    # Extract absolute paths from content
    for match in re.findall(r'(/(?:home|tmp|usr|etc|var)\S+\.(?:py|js|ts|md|json|owl|ttl|yaml|yml|toml|cfg|sh))', entry_content):
        paths.append(match)
    return paths


def detect_starsystems_for_entry(entry_content: str, in_file: str | None) -> dict[str, str]:
    """Detect which starsystems are involved in a diary entry.

    Returns dict of {project_name: starsystem_path} for all detected starsystems.
    """
    file_paths = _extract_file_paths(entry_content, in_file)
    starsystems = {}
    for fp in file_paths:
        name, path = resolve_starsystem_for_file(fp)
        if name and path:
            starsystems[name] = path
    return starsystems


def _normalize_name(name: str) -> str:
    """Normalize to Title_Case_With_Underscores."""
    name = name.strip("/").replace("/", "_").replace("-", "_").replace(".", "_")
    return "_".join(seg.title() if seg.islower() else seg for seg in name.split("_"))


def get_joint_starlog_name(project_names: list[str]) -> str:
    """Generate deterministic joint starlog project name from sorted normalized project names."""
    sorted_names = sorted(set(_normalize_name(n) for n in project_names))
    return "Starlog_Project_" + "_X_".join(sorted_names)


class StarlogSessionsMixin:
    """Handles starlog session management and history."""

    def _mirror_typed_list(self, items: List[str], prefix: str, ts: str,
                           parent_concept: str, is_a_type: str,
                           instantiates_type: str, rel_prefix: str,
                           rels: list) -> None:
        """Create typed sub-concepts for each item in a list and accumulate relationships.

        Each item becomes its own concept with is_a + part_of + instantiates.
        Sequential has_X_N relationships get appended to rels.
        """
        for i, item in enumerate(items, 1):
            concept = f"{prefix}_{ts}_{i}"
            rels.append({"relationship": f"{rel_prefix}_{i}", "related": [concept]})
            self.mirror_to_carton(
                concept_name=concept,
                description=item,
                relationships=[
                    {"relationship": "is_a", "related": [is_a_type]},
                    {"relationship": "part_of", "related": [parent_concept]},
                    {"relationship": "instantiates", "related": [instantiates_type]},
                ],
            )

    def _create_start_debug_entry(self, session: StarlogEntry) -> DebugDiaryEntry:
        """Create debug diary entry for session START with stardate."""
        content_parts = [session.session_title, session.start_content]
        if session.session_goals:
            content_parts.append(f"Goals: {', '.join(session.session_goals)}")
        if session.relevant_docs:
            content_parts.append(f"Docs: {', '.join(session.relevant_docs)}")
        captain_log_content = f"Captain's Log, stardate {session.timestamp}: START SESSION {session.id} -- {' | '.join(content_parts)}"
        return DebugDiaryEntry(content=captain_log_content)
    
    def _create_end_debug_entry(self, session: StarlogEntry) -> DebugDiaryEntry:
        """Create debug diary entry for session END with stardate."""  
        content_parts = [session.session_title]
        if session.end_content:
            content_parts.append(session.end_content)
        if session.key_discoveries:
            content_parts.append(f"Discoveries: {', '.join(session.key_discoveries)}")
        if session.files_updated:
            content_parts.append(f"Files: {', '.join(session.files_updated)}")
        if session.challenges_faced:
            content_parts.append(f"Challenges: {', '.join(session.challenges_faced)}")
        captain_log_content = f"Captain's Log, stardate {session.end_timestamp}: END SESSION {session.id} -- {' | '.join(content_parts)}"
        return DebugDiaryEntry(content=captain_log_content)
    
    def _find_active_session(self, project_name: str) -> Optional[StarlogEntry]:
        """Find active session by walking backwards through registry until hitting START or END."""
        try:
            registry_data = self._get_registry_data(project_name, "starlog")
            if not registry_data:
                return None
            
            # Sort entries by timestamp in descending order (newest first)
            sorted_entries = sorted(
                registry_data.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=True
            )
            
            # Walk backwards until we hit START or END
            for session_id, session_data in sorted_entries:
                session = StarlogEntry(**session_data)
                
                # Check if this is START (has start_content but no end_content)
                if session.start_content and not session.end_content:
                    return session  # Found active session
                
                # Check if this is END (has both start_content and end_content)  
                if session.start_content and session.end_content:
                    return None  # No active session (last session was ended)
            
            return None  # No sessions found
            
        except Exception as e:
            logger.error(f"Failed to find active session: {e}")
            return None
    
    def view_starlog(self, path: str, last_n: int = 5) -> str:
        """Get recent session history."""
        try:
            project_name = self._get_project_name_from_path(path)
            starlog_data = self._get_registry_data(project_name, "starlog")

            if not starlog_data:
                return "📋 **STARLOG Sessions** (Empty)\n\nNo sessions found. Use start_starlog to begin a session."

            # Limit to last N sessions if specified
            if last_n and len(starlog_data) > last_n:
                sorted_items = sorted(
                    starlog_data.items(),
                    key=lambda x: x[1].get("timestamp", ""),
                    reverse=True
                )[:last_n]
                starlog_data = dict(sorted_items)

            return self._format_session_history(starlog_data)

        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return f"❌ Error getting session history: {str(e)}"
    
    def start_starlog(self, session_title: str, start_content: str, context_from_docs: str, 
                     session_goals: List[str], path: str) -> str:
        """Begin new session with context."""
        try:
            project_name = self._get_project_name_from_path(path)
            
            # Convert context_from_docs string to relevant_docs list
            relevant_docs = [context_from_docs] if context_from_docs.strip() else []
            
            session = StarlogEntry(
                session_title=session_title,
                start_content=start_content,
                relevant_docs=relevant_docs,
                session_goals=session_goals
            )
            
            self._save_starlog_entry(project_name, session)
            
            # Create START debug diary entry with stardate
            start_entry = self._create_start_debug_entry(session)
            self._save_debug_diary_entry(project_name, start_entry)

            # Mirror to CartON - fully typed (every field → relationship → concept)
            ts = session.timestamp.strftime('%Y%m%d_%H%M%S')
            session_concept = f"Starlog_Session_{ts}"
            rels = [
                {"relationship": "is_a", "related": ["Starlog_Session"]},
                {"relationship": "instantiates", "related": ["Session_Start_Record"]},
            ]
            self._mirror_typed_list(session_goals, "Session_Goal", ts, session_concept,
                                    "Session_Goal", "Goal_Statement", "has_goal", rels)
            self._mirror_typed_list(relevant_docs, "Session_Doc", ts, session_concept,
                                    "Relevant_Document", "Context_Document", "has_relevant_doc", rels)
            self.mirror_to_carton(
                concept_name=session_concept,
                description=f"Session: {session_title}. {start_content}",
                relationships=rels, project_name=project_name,
                starsystem_path=path,
            )

            # Write session ID to .course_state so hooks can discover it
            _update_course_state_session(session.id, project_name)

            logger.info(f"Started starlog session {session.id} in project {project_name}")
            return f"✅ Started session: {session_title} (ID: {session.id})"
            
        except Exception as e:
            logger.error(f"Failed to start starlog session: {e}")
            return f"❌ Error starting session: {str(e)}"
    
    def end_starlog(self, end_content: str, path: str) -> str:
        """End current session with summary."""
        try:
            project_name = self._get_project_name_from_path(path)
            
            # Find active session by walking backwards through registry
            active_session = self._find_active_session(project_name)
            if not active_session:
                return f"❌ No active session found"
            
            # End the session
            active_session.end_session(end_content)
            
            # Save updated session back to registry
            self._update_registry_item(project_name, "starlog", active_session.id, active_session.model_dump(mode='json'))
            
            # Create END debug diary entry with stardate
            end_entry = self._create_end_debug_entry(active_session)
            self._save_debug_diary_entry(project_name, end_entry)
            
            # Mirror end to CartON - fully typed (every field → relationship → concept)
            ts = active_session.timestamp.strftime('%Y%m%d_%H%M%S')
            session_concept = f"Starlog_Session_{ts}"
            rels = [
                {"relationship": "is_a", "related": ["Starlog_Session"]},
                {"relationship": "instantiates", "related": ["Session_End_Record"]},
            ]
            self._mirror_typed_list(active_session.key_discoveries or [], "Session_Discovery", ts,
                                    session_concept, "Key_Discovery", "Discovery_Record", "has_discovery", rels)
            self._mirror_typed_list(active_session.files_updated or [], "Session_File", ts,
                                    session_concept, "Updated_File", "File_Update_Record", "has_file_updated", rels)
            self._mirror_typed_list(active_session.challenges_faced or [], "Session_Challenge", ts,
                                    session_concept, "Challenge_Faced", "Challenge_Record", "has_challenge", rels)
            self.mirror_to_carton(
                concept_name=session_concept,
                description=f"End: {end_content}. Duration: {active_session.duration_minutes}min",
                relationships=rels, project_name=project_name,
                starsystem_path=path,
            )

            # Check for task completion and update GitHub issues
            github_updates = self._process_completed_tasks_github_update(active_session, end_content, path)
            github_status = ""
            if github_updates:
                github_status = f" | GitHub: {github_updates}"

            # Clear session ID from .course_state
            _update_course_state_session(None, None)

            logger.info(f"Ended starlog session {active_session.id} in project {project_name}")
            return f"✅ Ended session: {active_session.session_title} (Duration: {active_session.duration_minutes} minutes){github_status}"
            
        except Exception as e:
            logger.error(f"Failed to end starlog session: {e}")
            return f"❌ Error ending session: {str(e)}"
    
    def _process_completed_tasks_github_update(self, session, end_content: str, path: str) -> str:
        """Process completed tasks and update GitHub issues to in-review status."""
        try:
            # Get GIINT project data from starlog.hpi metadata
            project_name = self._get_project_name_from_path(path)
            hpi_data = self._load_session_hpi_data(path)
            giint_project_id = hpi_data.get("metadata", {}).get("giint_project_id")
            
            if not giint_project_id:
                return "No GIINT project linked"
            
            # Check if end_content indicates task completion
            completion_indicators = ["completed", "finished", "done", "task complete", "ready for review"]
            if not any(indicator in end_content.lower() for indicator in completion_indicators):
                return "No task completion detected"
            
            # Call GIINT to update GitHub issues for completed tasks
            import requests
            import os
            
            # Get GIINT MCP endpoint
            llm_intelligence_dir = os.getenv('LLM_INTELLIGENCE_DIR', '/tmp/llm_intelligence_responses')
            
            # Direct call to GIINT's GitHub update function
            return self._update_giint_task_to_review(giint_project_id)
            
        except Exception as e:
            logger.error(f"Failed to process GitHub updates: {e}")
            return f"GitHub update failed: {str(e)}"
    
    def _load_session_hpi_data(self, path: str) -> dict:
        """Load HPI data from starlog.hpi file."""
        import json
        import os
        hpi_path = os.path.join(path, "starlog.hpi")
        if os.path.exists(hpi_path):
            with open(hpi_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _update_giint_task_to_review(self, giint_project_id: str) -> str:
        """Update GIINT tasks to in-review status via direct function call."""
        try:
            # Import GIINT projects module
            import sys
            sys.path.insert(0, '/tmp/llm_intelligence_mcp/llm_intelligence_package')
            from llm_intelligence.projects import ProjectRegistry
            
            # Create GIINT project registry instance
            giint_manager = ProjectRegistry()
            
            # Get project data
            project_data = giint_manager.get_project(giint_project_id)
            if not project_data.get("success"):
                return f"GIINT project {giint_project_id} not found"
            
            project = project_data["project"]
            
            # Find in-progress tasks and update to in-review
            updated_count = 0
            for feature_name, feature in project.get("features", {}).items():
                for component_name, component in feature.get("components", {}).items():
                    for deliverable_name, deliverable in component.get("deliverables", {}).items():
                        for task_id, task in deliverable.get("tasks", {}).items():
                            # If task has GitHub issue and is ready/in-progress, move to in-review
                            if (task.get("github_issue_id") and 
                                (task.get("is_ready") or task.get("is_done"))):
                                
                                # Update task status to in-review
                                giint_manager.update_task_status(
                                    giint_project_id, feature_name, component_name, 
                                    deliverable_name, task_id, 
                                    is_done=False, is_blocked=False, is_ready=False,
                                    blocked_description=None
                                )
                                updated_count += 1
            
            return f"Updated {updated_count} tasks to in-review"
            
        except Exception as e:
            logger.error(f"Failed to update GIINT tasks: {e}")
            return f"GIINT update failed: {str(e)}"
    
    def _format_session_history(self, starlog_data: dict) -> str:
        """Format session history for display."""
        if not starlog_data:
            return "📋 **STARLOG Sessions** (Empty)\n\nNo sessions found."
        
        formatted = "📋 **STARLOG Sessions**\n\n"
        
        # Sort sessions by timestamp (newest first)
        sessions = []
        for session_id, session_data in starlog_data.items():
            sessions.append((session_id, session_data))
        
        sessions.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
        
        # Format each session
        for session_id, session_data in sessions:
            date = session_data.get("date", "")
            title = session_data.get("session_title", "")
            is_ended = session_data.get("end_content") is not None
            duration = session_data.get("duration_minutes") if is_ended else None
            
            status = "✅ COMPLETE" if is_ended else "🔄 IN PROGRESS"
            duration_str = f" ({duration}min)" if duration else ""
            
            formatted += f"**{date}** - {title} `{session_id}` {status}{duration_str}\n"
            
            # Show goals briefly
            goals = session_data.get("session_goals", [])
            if goals:
                formatted += f"Goals: {', '.join(goals[:2])}{'...' if len(goals) > 2 else ''}\n"
            
            formatted += "\n"
        
        return formatted.strip()

    def start_joint_session(self, session_title: str, member_projects: list[str],
                            session_goals: list[str], start_content: str) -> str:
        """Begin a joint session spanning multiple starsystems."""
        try:
            joint_name = get_joint_starlog_name(member_projects)
            joint = JointSessionEntry(
                session_title=session_title,
                member_projects=member_projects,
                session_goals=session_goals,
                start_content=start_content,
            )

            # Ensure joint registries exist
            try:
                from heaven_base.tools.registry_tool import registry_util_func
                registry_util_func("create_registry", registry_name=f"{joint_name}_starlog")
                registry_util_func("create_registry", registry_name=f"{joint_name}_debug_diary")
            except Exception:
                pass

            # Save joint session entry
            self._save_starlog_entry(joint_name, StarlogEntry(
                session_title=session_title,
                start_content=start_content,
                session_goals=session_goals,
            ))

            # Start child sessions in each member project
            for member in member_projects:
                child_title = f"[Joint: {joint_name}] {session_title}"
                child = StarlogEntry(
                    session_title=child_title,
                    start_content=f"Child session of joint {joint_name}. {start_content}",
                    session_goals=session_goals,
                )
                self._save_starlog_entry(member, child)
                joint.child_session_ids[member] = child.id

                # Create reference diary entry in member
                stardate = self._generate_stardate()
                ref = DebugDiaryEntry(
                    content=f"Captain's Log, stardate {stardate}: Joint session started: {joint_name}. "
                            f"Starsystems: {', '.join(member_projects)}.",
                    entry_type="session_start",
                    source="system",
                )
                self._save_debug_diary_entry(member, ref)

            # Save joint entry to global registry
            try:
                from heaven_base.tools.registry_tool import registry_util_func
                registry_util_func("add", registry_name="joint_sessions",
                                   key=joint.id, value_dict=joint.model_dump(mode='json'))
            except Exception:
                pass

            # Write to .course_state
            _update_course_state_session(joint.id, joint_name)

            # Mirror to CartON
            starsystem_concepts = [f"Starsystem_{n.replace('-', '_').title()}" for n in member_projects]
            self.mirror_to_carton(
                concept_name=joint_name,
                description=f"Joint starlog project: {session_title}. Spanning {' and '.join(starsystem_concepts)}.",
                relationships=[
                    {"relationship": "is_a", "related": ["Starlog_Project"]},
                    {"relationship": "part_of", "related": starsystem_concepts},
                    {"relationship": "instantiates", "related": ["Project_Tracking_Instance"]},
                ],
            )

            logger.info(f"Started joint session {joint.id}: {joint_name}")
            return (f"✅ Joint session started: {joint_name} (ID: {joint.id})\n"
                    f"   Members: {', '.join(member_projects)}\n"
                    f"   Child sessions created in each member starlog.")

        except Exception as e:
            logger.error(f"Failed to start joint session: {e}")
            return f"❌ Error starting joint session: {e}"

    def end_joint_session(self, end_content: str) -> str:
        """End the active joint session and all child sessions."""
        try:
            # Read .course_state to find active joint session
            if not os.path.exists(COURSE_STATE_PATH):
                return "❌ No .course_state found"
            with open(COURSE_STATE_PATH, "r") as f:
                cs = json.load(f)
            session_id = cs.get("active_starlog_session_id")
            project_name = cs.get("active_starlog_project")
            if not session_id or not project_name:
                return "❌ No active session found in .course_state"

            # Load joint session from global registry
            joint_data = None
            try:
                from heaven_base.tools.registry_tool import registry_util_func
                result = registry_util_func("get", registry_name="joint_sessions", key=session_id)
                if result and "Key not found" not in result:
                    import ast
                    start = result.find("{")
                    if start != -1:
                        joint_data = ast.literal_eval(result[start:])
            except Exception:
                pass

            # End child sessions in each member project
            if joint_data and joint_data.get("member_projects"):
                for member in joint_data["member_projects"]:
                    active = self._find_active_session(member)
                    if active:
                        active.end_session(f"Joint session {project_name} ended. {end_content}")
                        self._update_registry_item(member, "starlog", active.id, active.model_dump(mode='json'))

                        stardate = self._generate_stardate()
                        ref = DebugDiaryEntry(
                            content=f"Captain's Log, stardate {stardate}: Joint session ended: {project_name}. {end_content}",
                            entry_type="session_end",
                            source="system",
                        )
                        self._save_debug_diary_entry(member, ref)

            # End the joint session's own starlog entry
            active_joint = self._find_active_session(project_name)
            if active_joint:
                active_joint.end_session(end_content)
                self._update_registry_item(project_name, "starlog", active_joint.id, active_joint.model_dump(mode='json'))

            # Clear .course_state
            _update_course_state_session(None, None)

            duration = active_joint.duration_minutes if active_joint else "?"
            logger.info(f"Ended joint session {session_id}: {project_name}")
            return (f"✅ Joint session ended: {project_name} (Duration: {duration}min)\n"
                    f"   {end_content}")

        except Exception as e:
            logger.error(f"Failed to end joint session: {e}")
            return f"❌ Error ending joint session: {e}"