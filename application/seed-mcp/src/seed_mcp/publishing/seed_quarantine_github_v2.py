"""
SEED v0 Publishing Platform - Single authorized.json Architecture
Corrected implementation using single authorized.json with status enum.
"""

import json
import os
import logging
import traceback
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ConceptStatus(Enum):
    """Status enum for concepts in authorized.json"""
    QUARANTINED = "QUARANTINED"
    AUTHORIZED = "AUTHORIZED" 
    REJECTED = "REJECTED"
    NEEDS_REVISION = "NEEDS_REVISION"
    NEEDS_REDACT = "NEEDS_REDACT"


@dataclass
class ConceptEntry:
    """Represents a concept in authorized.json"""
    concept_name: str
    status: ConceptStatus
    timestamp: str
    reviewer: Optional[str] = None
    reason: Optional[str] = None


class GitHubQuarantineManager:
    """Single authorized.json architecture for quarantine management."""
    
    def __init__(self, 
                 github_pat: str = None,
                 carton_repo_url: str = None,
                 carton_branch: str = "main"):
        """Initialize GitHub-based quarantine manager."""
        # GitHub configuration
        self.github_pat = github_pat or os.environ.get('GITHUB_PAT')
        self.carton_repo_url = carton_repo_url or os.environ.get('CARTON_REPO_URL')
        self.carton_branch = carton_branch or os.environ.get('CARTON_BRANCH', 'main')
        
        # Temporary directory for cloning Carton repo
        self.temp_repo_dir = Path('/tmp/carton_clone')
        
        if not self.github_pat or not self.carton_repo_url:
            logger.warning("GitHub PAT or Carton repo URL not configured - operations will fail")
    
    def _run_git_command(self, cmd: list[str], cwd: str) -> Dict[str, str]:
        """Run a git command synchronously."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return {"output": result.stdout.strip()}
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.error(f"Error: {e.stderr}")
            logger.debug(traceback.format_exc())
            return {"error": e.stderr.strip()}
    
    def _cleanup_existing_repo(self) -> None:
        """Remove existing repo directory."""
        if self.temp_repo_dir.exists():
            shutil.rmtree(self.temp_repo_dir, ignore_errors=True)
            logger.info(f"Removed existing repo at {self.temp_repo_dir}")
    
    def _setup_git_credentials(self) -> None:
        """Set up git credentials for authentication."""
        auth_url = f"https://{self.github_pat}@github.com"
        credentials_path = Path.home() / ".git-credentials"
        credentials_path.write_text(auth_url + "\n")
        logger.debug("Set up Git credentials")
    
    def _clone_repo(self) -> Dict[str, str]:
        """Clone the repository."""
        repo_url = self.carton_repo_url
        if not repo_url.endswith(".git"):
            repo_url += ".git"

        result = self._run_git_command(["git", "clone", repo_url, str(self.temp_repo_dir)], ".")
        if "error" in result:
            return {"error": f"Git clone failed: {result['error']}"}
        
        logger.info(f"Cloned Carton repo to {self.temp_repo_dir}")
        return {"output": "Clone successful"}
    
    def _run_git_commands_sequence(self, commands: List[List[str]], error_prefix: str = "Git command failed") -> Dict[str, str]:
        """Run a sequence of git commands, stopping on first error."""
        for cmd in commands:
            result = self._run_git_command(cmd, str(self.temp_repo_dir))
            if "error" in result:
                return {"error": f"{error_prefix}: {result['error']}"}
        return {"output": "All commands executed successfully"}
    
    def _configure_git_identity(self) -> Dict[str, str]:
        """Configure git user identity."""
        commands = [
            ["git", "config", "user.email", "seed-bot@example.com"],
            ["git", "config", "user.name", "SEED Publishing Bot"],
            ["git", "config", "credential.helper", "store"],
        ]
        result = self._run_git_commands_sequence(commands, "Git config failed")
        if "error" in result:
            return result
        return {"output": "Git identity configured"}
    
    def _setup_git_repo(self) -> Dict[str, str]:
        """Clone fresh repo from GitHub."""
        self._cleanup_existing_repo()
        self._setup_git_credentials()
        
        clone_result = self._clone_repo()
        if "error" in clone_result:
            return clone_result
        
        config_result = self._configure_git_identity()
        if "error" in config_result:
            return config_result
        
        # Ensure we're on main branch and pull latest
        checkout_result = self._run_git_command(["git", "checkout", self.carton_branch], str(self.temp_repo_dir))
        if "error" in checkout_result:
            return {"error": f"Failed to checkout {self.carton_branch} branch: {checkout_result['error']}"}
        
        pull_result = self._run_git_command(["git", "pull", "origin", self.carton_branch], str(self.temp_repo_dir))
        if "error" in pull_result:
            # Pull failure is not fatal - we can continue with cloned content
            logger.warning(f"Failed to pull latest changes: {pull_result['error']}")
        
        return {"output": "Git repo setup successful"}
    
    def _commit_and_push(self, commit_msg: str) -> Dict[str, str]:
        """Commit and push changes to remote repository."""
        commands = [
            ["git", "add", "."],
            ["git", "commit", "-m", commit_msg],
            ["git", "push", "origin", self.carton_branch],
        ]

        result = self._run_git_commands_sequence(commands, "Git command failed")
        if "error" in result:
            return result
        
        logger.info(f"Committed and pushed: {commit_msg}")
        return {"output": "Changes pushed successfully"}
    
    def _scan_all_concepts(self) -> List[str]:
        """Scan repo for ALL existing concepts."""
        concepts_dir = self.temp_repo_dir / "concepts"
        if not concepts_dir.exists():
            logger.warning("No concepts directory found in repo")
            return []
        
        concept_names = []
        for item in concepts_dir.iterdir():
            if item.is_dir():
                concept_names.append(item.name)
        
        logger.info(f"Found {len(concept_names)} concepts in repo")
        return concept_names
    
    def _load_authorized_json(self) -> Dict[str, Dict[str, Any]]:
        """Load authorized.json from cloned repo."""
        authorized_file = self.temp_repo_dir / "authorized.json"
        if authorized_file.exists():
            try:
                with open(authorized_file, 'r') as f:
                    data = json.load(f)
                    # Convert to dict keyed by concept_name for easy lookup
                    if isinstance(data, list):
                        return {item['concept_name']: item for item in data}
                    return data
            except Exception as e:
                logger.error(f"Failed to load authorized.json: {e}")
                logger.debug(traceback.format_exc())
                return {}
        return {}
    
    def _save_authorized_json(self, data: Dict[str, Dict[str, Any]]) -> bool:
        """Save authorized.json to cloned repo as dict format with concept names as keys."""
        authorized_file = self.temp_repo_dir / "authorized.json"
        try:
            # Save as dict format with concept names as keys (NOT as list)
            with open(authorized_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved authorized.json with {len(data)} entries")
            return True
        except Exception as e:
            logger.error(f"Failed to save authorized.json: {e}")
            logger.debug(traceback.format_exc())
            return False
    
    def _add_missing_concepts(self, all_concepts: List[str], authorized_data: Dict[str, Dict[str, Any]]) -> int:
        """Add missing concepts to authorized_data with QUARANTINED status."""
        added_count = 0
        for concept_name in all_concepts:
            if concept_name not in authorized_data:
                authorized_data[concept_name] = {
                    "concept_name": concept_name,
                    "status": ConceptStatus.QUARANTINED.value,
                    "timestamp": datetime.now().isoformat(),
                    "reviewer": None,
                    "reason": None
                }
                added_count += 1
        return added_count
    
    def _ensure_all_concepts_tracked(self) -> Dict[str, str]:
        """Ensure ALL concepts in repo are tracked in authorized.json."""
        all_concepts = self._scan_all_concepts()
        authorized_data = self._load_authorized_json()
        
        added_count = self._add_missing_concepts(all_concepts, authorized_data)
        
        if added_count > 0:
            if self._save_authorized_json(authorized_data):
                logger.info(f"Added {added_count} new concepts to authorized.json")
                return {"output": f"Added {added_count} concepts with QUARANTINED status"}
            else:
                return {"error": "Failed to save updated authorized.json"}
        
        return {"output": "All concepts already tracked"}
    
    def _format_entry_for_display(self, concept_name: str, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format entry for webserver display."""
        return {
            "concept_name": concept_name,
            "status": entry_data.get("status"),
            "timestamp": entry_data.get("timestamp"),
            "reviewer": entry_data.get("reviewer"),
            "reason": entry_data.get("reason"),
            # Add dummy fields for webserver compatibility
            "qa_id": f"concept_{concept_name}",
            "created_at": entry_data.get("timestamp"),
            "concept_type": "existing_concept"
        }
    
    def _filter_quarantined_entries(self, authorized_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter entries for QUARANTINED status only."""
        quarantined_entries = []
        for concept_name, entry_data in authorized_data.items():
            if entry_data.get("status") == ConceptStatus.QUARANTINED.value:
                display_entry = self._format_entry_for_display(concept_name, entry_data)
                quarantined_entries.append(display_entry)
        return quarantined_entries
    
    def _filter_authorized_entries(self, authorized_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter entries for AUTHORIZED status only."""
        authorized_entries = []
        for concept_name, entry_data in authorized_data.items():
            if entry_data.get("status") == ConceptStatus.AUTHORIZED.value:
                display_entry = self._format_entry_for_display(concept_name, entry_data)
                authorized_entries.append(display_entry)
        return authorized_entries
    
    def publishing_review_quarantine(self) -> List[Dict[str, Any]]:
        """Get ALL concepts with QUARANTINED status for review (pulls fresh data from GitHub)."""
        refresh_result = self.refresh_from_github()
        if not refresh_result:
            logger.error("Failed to refresh from GitHub")
            return []
        
        authorized_data = self._load_authorized_json()
        quarantined_entries = self._filter_quarantined_entries(authorized_data)
        
        logger.info(f"Found {len(quarantined_entries)} concepts with QUARANTINED status")
        return quarantined_entries
    
    def get_approved_concepts(self) -> List[Dict[str, Any]]:
        """Get ALL concepts with AUTHORIZED status for publishing."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return []
        
        authorized_data = self._load_authorized_json()
        approved_entries = self._filter_authorized_entries(authorized_data)
        
        logger.info(f"Found {len(approved_entries)} concepts with AUTHORIZED status")
        return approved_entries
    
    def _update_concept_status(self, concept_name: str, status: ConceptStatus, reviewer: str = None, reason: str = None) -> bool:
        """Update concept status in authorized.json."""
        authorized_data = self._load_authorized_json()
        
        # If concept doesn't exist, create it (because quarantined by default)
        if concept_name not in authorized_data:
            authorized_data[concept_name] = {}
        
        authorized_data[concept_name]["status"] = status.value
        authorized_data[concept_name]["timestamp"] = datetime.now().isoformat()
        if reviewer:
            authorized_data[concept_name]["reviewer"] = reviewer
        if reason:
            authorized_data[concept_name]["reason"] = reason
        
        return self._save_authorized_json(authorized_data)
    
    def publishing_authorize_for_publishing(self, concept_name: str, reviewer: str = "isaac") -> bool:
        """Change concept status from QUARANTINED to AUTHORIZED."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return False
        
        if not self._update_concept_status(concept_name, ConceptStatus.AUTHORIZED, reviewer, "Approved for publication"):
            return False
        
        commit_result = self._commit_and_push(f"SEED: Authorized {concept_name} for publication")
        if "error" in commit_result:
            logger.error(f"Failed to commit authorization: {commit_result['error']}")
            return False
        
        logger.info(f"Successfully authorized {concept_name}")
        return True
    
    def publishing_reject_concept(self, concept_name: str, reason: str = "Not suitable for publication") -> bool:
        """Change concept status from QUARANTINED to REJECTED."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return False
        
        if not self._update_concept_status(concept_name, ConceptStatus.REJECTED, reason=reason):
            return False
        
        commit_result = self._commit_and_push(f"SEED: Rejected {concept_name}: {reason}")
        if "error" in commit_result:
            logger.error(f"Failed to commit rejection: {commit_result['error']}")
            return False
        
        logger.info(f"Successfully rejected {concept_name}")
        return True
    
    def publishing_needs_revision_concept(self, concept_name: str, reason: str = "Requires content revision") -> bool:
        """Change concept status from QUARANTINED to NEEDS_REVISION."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return False
        
        if not self._update_concept_status(concept_name, ConceptStatus.NEEDS_REVISION, reason=reason):
            return False
        
        commit_result = self._commit_and_push(f"SEED: Marked {concept_name} as needs revision: {reason}")
        if "error" in commit_result:
            logger.error(f"Failed to commit needs revision status: {commit_result['error']}")
            return False
        
        logger.info(f"Successfully marked {concept_name} as needs revision")
        return True
    
    def publishing_needs_redact_concept(self, concept_name: str, reason: str = "Requires redaction") -> bool:
        """Change concept status from QUARANTINED to NEEDS_REDACT."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return False
        
        if not self._update_concept_status(concept_name, ConceptStatus.NEEDS_REDACT, reason=reason):
            return False
        
        commit_result = self._commit_and_push(f"SEED: Marked {concept_name} as needs redaction: {reason}")
        if "error" in commit_result:
            logger.error(f"Failed to commit needs redaction status: {commit_result['error']}")
            return False
        
        logger.info(f"Successfully marked {concept_name} as needs redaction")
        return True
    
    def _find_concept_file(self, concept_name: str) -> Optional[Path]:
        """Find concept file in various possible locations."""
        concept_paths = [
            self.temp_repo_dir / "concepts" / concept_name / f"{concept_name}_itself.md",
            self.temp_repo_dir / "concepts" / concept_name / f"{concept_name}.md",
            self.temp_repo_dir / concept_name / f"{concept_name}_itself.md",
            self.temp_repo_dir / concept_name / f"{concept_name}.md",
        ]
        
        for concept_path in concept_paths:
            if concept_path.exists():
                return concept_path
        return None
    
    def get_concept_content(self, concept_name: str) -> Dict[str, Any]:
        """Get concept content from cloned repo."""
        if not self.temp_repo_dir.exists():
            setup_result = self._setup_git_repo()
            if "error" in setup_result:
                return {"error": f"Failed to setup repo: {setup_result['error']}"}
        
        concept_path = self._find_concept_file(concept_name)
        if concept_path:
            try:
                content = concept_path.read_text(encoding='utf-8')
                logger.info(f"Found concept content at {concept_path}")
                return {"content": content, "path": str(concept_path)}
            except Exception as e:
                logger.error(f"Failed to read concept file {concept_path}: {e}")
                logger.debug(traceback.format_exc())
                return {"error": f"Failed to read concept file: {e}"}
        
        logger.warning(f"Concept file not found for {concept_name}")
        return {"error": f"Concept file not found for {concept_name}"}
    
    def get_authorization_status(self, concept_name: str) -> Optional[str]:
        """Get current status of a concept."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return None
        
        authorized_data = self._load_authorized_json()
        if concept_name in authorized_data:
            return authorized_data[concept_name].get("status")
        return None
    
    def refresh_from_github(self) -> bool:
        """Pull fresh data from GitHub and ensure all concepts tracked."""
        setup_result = self._setup_git_repo()
        if "error" in setup_result:
            logger.error(f"Failed to setup repo: {setup_result['error']}")
            return False
        
        track_result = self._ensure_all_concepts_tracked()
        if "error" in track_result:
            logger.error(f"Failed to track concepts: {track_result['error']}")
            return False
        
        logger.info("Successfully refreshed from GitHub")
        return True
    
    def sync_authorization_file(self) -> bool:
        """Push current authorized.json back to GitHub."""
        if not self.temp_repo_dir.exists():
            logger.error("No local repo - call refresh_from_github first")
            return False
        
        # Load current authorized data (should already exist from previous operations)
        authorized_data = self._load_authorized_json()
        if not authorized_data:
            logger.error("No authorized.json data to push")
            return False
        
        # Commit and push the current authorized.json
        commit_result = self._commit_and_push("SEED: Sync authorized.json status updates")
        if "error" in commit_result:
            logger.error(f"Failed to push authorized.json: {commit_result['error']}")
            return False
        
        logger.info("Successfully pushed authorized.json to GitHub")
        return True


# Convenience functions maintaining same interface
def publishing_review_quarantine() -> List[Dict[str, Any]]:
    """List all concepts with QUARANTINED status."""
    manager = GitHubQuarantineManager()
    return manager.publishing_review_quarantine()


def publishing_authorize_for_publishing(concept_name: str, reviewer: str = "isaac") -> bool:
    """Approve a concept for public publishing."""
    manager = GitHubQuarantineManager()
    return manager.publishing_authorize_for_publishing(concept_name, reviewer)


def publishing_reject_concept(concept_name: str, reason: str = "Not suitable for publication") -> bool:
    """Reject a concept from being published."""
    manager = GitHubQuarantineManager()
    return manager.publishing_reject_concept(concept_name, reason)


def get_authorization_status(concept_name: str) -> Optional[str]:
    """Check concept status."""
    manager = GitHubQuarantineManager()
    return manager.get_authorization_status(concept_name)


def refresh_from_github() -> bool:
    """Pull fresh data from GitHub and ensure all concepts tracked."""
    manager = GitHubQuarantineManager()
    return manager.refresh_from_github()


def sync_authorization_file() -> bool:
    """Push current authorized.json back to GitHub."""
    manager = GitHubQuarantineManager()
    return manager.sync_authorization_file()


def get_concept_content(concept_name: str) -> Dict[str, Any]:
    """Get concept content from GitHub repo."""
    manager = GitHubQuarantineManager()
    return manager.get_concept_content(concept_name)


def publishing_needs_revision_concept(concept_name: str, reason: str = "Requires content revision") -> bool:
    """Mark a concept as needs revision."""
    manager = GitHubQuarantineManager()
    return manager.publishing_needs_revision_concept(concept_name, reason)


def publishing_needs_redact_concept(concept_name: str, reason: str = "Requires redaction") -> bool:
    """Mark a concept as needs redaction."""
    manager = GitHubQuarantineManager()
    return manager.publishing_needs_redact_concept(concept_name, reason)