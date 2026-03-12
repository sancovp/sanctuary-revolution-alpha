#!/usr/bin/env python3
"""
PublishingPipeline: Automated public branch publishing for SEED v0 Platform

This module handles the complete pipeline from authorized private concepts
to redacted public branch publishing with Git branch-based separation.
"""

import os
import shutil
import subprocess
import tempfile
import requests
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import json

from redaction_manager import RedactionManager
from seed_quarantine_github_v2 import GitHubQuarantineManager, ConceptStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PublishingPipeline:
    """Manages the complete publishing pipeline from private to public branch."""
    
    def __init__(self, redaction_manager: RedactionManager, 
                 quarantine_manager: GitHubQuarantineManager,
                 public_branch: str = "public"):
        """
        Initialize the publishing pipeline.
        
        Args:
            redaction_manager: RedactionManager instance for content redaction
            quarantine_manager: GitHubQuarantineManager for repo operations
            public_branch: Name of the public branch (default: "public")
        """
        self.redaction_manager = redaction_manager
        self.quarantine_manager = quarantine_manager
        self.public_branch = public_branch
        
    def _run_git_command(self, command: List[str], cwd: str) -> Tuple[bool, str]:
        """Run a git command and return success status and output."""
        try:
            result = subprocess.run(
                command, 
                cwd=cwd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(command)}")
            logger.error(f"Error: {e.stderr}")
            return False, e.stderr
    
    def _check_public_branch_exists(self, repo_path: str) -> Tuple[bool, bool]:
        """Check if public branch exists remotely."""
        success, output = self._run_git_command(["git", "branch", "-r"], repo_path)
        if not success:
            return False, False
        
        public_branch_exists = f"origin/{self.public_branch}" in output
        return True, public_branch_exists
    
    def _create_new_public_branch(self, repo_path: str) -> bool:
        """Create a new orphan public branch."""
        logger.info(f"Creating new {self.public_branch} branch")
        
        # Create orphan public branch (no history from main)
        success, _ = self._run_git_command(
            ["git", "checkout", "--orphan", self.public_branch], repo_path
        )
        if not success:
            return False
        
        # Remove all files from staging
        self._run_git_command(["git", "rm", "-rf", "."], repo_path)
        # This command might fail if no files exist, which is OK
        
        return self._create_initial_public_commit(repo_path)
    
    def _create_initial_public_commit(self, repo_path: str) -> bool:
        """Create initial commit for public branch."""
        readme_path = os.path.join(repo_path, "README.md")
        with open(readme_path, 'w') as f:
            f.write("# Public Knowledge Base\n\nAuthorized and redacted concepts from compound intelligence work.\n")
        
        success, _ = self._run_git_command(["git", "add", "README.md"], repo_path)
        if not success:
            return False
        
        success, _ = self._run_git_command(
            ["git", "commit", "-m", "Initial public branch commit"], repo_path
        )
        if not success:
            return False
        
        # Push the new branch
        return self._run_git_command(["git", "push", "origin", self.public_branch], repo_path)[0]
    
    def _switch_to_existing_public_branch(self, repo_path: str) -> bool:
        """Switch to and update existing public branch."""
        logger.info(f"Switching to existing {self.public_branch} branch")
        
        success, _ = self._run_git_command(["git", "checkout", self.public_branch], repo_path)
        if not success:
            return False
        
        # Pull latest changes
        return self._run_git_command(["git", "pull", "origin", self.public_branch], repo_path)[0]
    
    def _ensure_public_branch(self, repo_path: str) -> bool:
        """Ensure the public branch exists and is set up correctly."""
        success, public_branch_exists = self._check_public_branch_exists(repo_path)
        if not success:
            return False
        
        if not public_branch_exists:
            return self._create_new_public_branch(repo_path)
        else:
            return self._switch_to_existing_public_branch(repo_path)
    
    def _get_authorized_concepts(self, existing_repo_dir: str = None) -> List[str]:
        """Get list of concepts with AUTHORIZED status."""
        try:
            if existing_repo_dir:
                # Reuse existing cloned repo instead of re-cloning
                logger.info(f"Reusing existing repo directory: {existing_repo_dir}")
                authorized_data = self.quarantine_manager._load_authorized_json()
                authorized_concepts = []
                for concept_name, concept_data in authorized_data.items():
                    if concept_data.get("status") == "AUTHORIZED":
                        authorized_concepts.append({"concept_name": concept_name})
                return [concept["concept_name"] for concept in authorized_concepts]
            else:
                # Fallback to original method (will clone)
                authorized_concepts = self.quarantine_manager.get_approved_concepts()
                return [concept["concept_name"] for concept in authorized_concepts]
        except Exception as e:
            logger.error(f"Failed to get authorized concepts: {e}", exc_info=True)
            return []
    
    def _get_concept_file_paths(self, concept_name: str, source_path: str, target_path: str) -> Tuple[str, str]:
        """Get source and target file paths for a concept."""
        # Carton uses subdirectories: concepts/Concept_Name/Concept_Name_itself.md
        source_file = os.path.join(source_path, "concepts", concept_name, f"{concept_name}_itself.md")
        target_concepts_dir = os.path.join(target_path, "concepts")
        target_file = os.path.join(target_concepts_dir, f"{concept_name}_itself.md")
        return source_file, target_file
    
    def _ensure_target_directory(self, target_path: str):
        """Ensure target concepts directory exists."""
        target_concepts_dir = os.path.join(target_path, "concepts")
        os.makedirs(target_concepts_dir, exist_ok=True)
    
    def _get_source_concept_path(self, concept_name: str, source_path: str) -> str:
        """Get path to source concept file."""
        return os.path.join(source_path, "concepts", concept_name, f"{concept_name}_itself.md")
    
    def _get_target_concept_path(self, concept_name: str, staging_path: str) -> str:
        """Get path to target concept file in staging."""
        return os.path.join(staging_path, "concepts", f"{concept_name}_itself.md")
    
    def _transform_carton_links(self, content: str) -> str:
        """Transform Carton wiki links to public website format.
        
        Transforms: ../Other_Concept/Other_Concept_itself.md
        To: /concepts/Other_Concept.md
        """
        import re
        
        # Pattern: ../ConceptName/ConceptName_itself.md or variations
        pattern = r'\[([^\]]+)\]\(\.\.\/([^\/]+)\/[^\/]*_itself\.md\)'
        
        def replace_link(match):
            link_text = match.group(1)
            concept_name = match.group(2)
            return f'[{link_text}](/concepts/{concept_name}_itself.md)'
        
        transformed = re.sub(pattern, replace_link, content)
        
        # Also handle any remaining relative concept links that might have different patterns
        # Pattern for any ../Something.md or ../Something/Something.md
        pattern2 = r'\[([^\]]+)\]\(\.\.\/([^\/]+)(?:\/[^\)]*)?\.md\)'
        
        def replace_link2(match):
            link_text = match.group(1)
            concept_name = match.group(2)
            return f'[{link_text}](/concepts/{concept_name}_itself.md)'
        
        # Apply second pattern only if first didn't catch it
        if transformed == content:
            transformed = re.sub(pattern2, replace_link2, content)
        
        return transformed
    
    def _copy_and_redact_concept(self, concept_name: str, 
                                source_path: str, staging_path: str) -> Tuple[bool, int]:
        """Copy a concept file from main branch and apply redactions to staging directory."""
        try:
            source_file = self._get_source_concept_path(concept_name, source_path)
            
            if not os.path.exists(source_file):
                logger.warning(f"Concept file not found: {source_file}")
                return False, 0
            
            # Apply redactions and transform links for staging
            redacted_content, redaction_count = self.redaction_manager.apply_redactions_to_file(source_file)
            
            # Transform Carton wiki links to public website format
            final_content = self._transform_carton_links(redacted_content)
            
            target_file = self._get_target_concept_path(concept_name, staging_path)
            
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            logger.info(f"Copied and redacted {concept_name}: {redaction_count} redactions applied")
            return True, redaction_count
            
        except Exception as e:
            logger.error(f"Failed to copy and redact concept {concept_name}: {e}", exc_info=True)
            return False, 0
    
    def _create_publication_metadata(self, target_path: str, 
                                   concepts: List[str], total_redactions: int):
        """Create metadata file for the publication."""
        metadata = {
            "publication_info": {
                "source": "SEED v0 Publishing Platform",
                "description": "Authorized and redacted concepts from compound intelligence work",
                "branch": self.public_branch,
                "total_concepts": len(concepts),
                "total_redactions": total_redactions,
                "redaction_rules_count": len(self.redaction_manager.get_rules())
            },
            "concepts": concepts,
            "redaction_summary": {
                "rules_applied": list(self.redaction_manager.get_rules().keys()),
                "total_redactions": total_redactions
            }
        }
        
        metadata_file = os.path.join(target_path, "publication_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Created publication metadata with {len(concepts)} concepts")
    
    def _github_api_update_public_branch(self, staging_path: str) -> bool:
        """Update public branch using GitHub API instead of Git commands."""
        try:
            # Extract repo info from quarantine manager
            repo_url = self.quarantine_manager.carton_repo_url
            if "github.com/" not in repo_url:
                logger.error(f"Invalid GitHub repo URL: {repo_url}")
                return False
            
            # Extract owner and repo name from URL
            repo_parts = repo_url.replace("https://github.com/", "").replace(".git", "").split("/")
            if len(repo_parts) != 2:
                logger.error(f"Cannot parse repo owner/name from URL: {repo_url}")
                return False
            
            owner, repo = repo_parts
            github_pat = self.quarantine_manager.github_pat
            
            # Get staging directory files
            staging_concepts = Path(staging_path) / "concepts"
            if not staging_concepts.exists():
                logger.error(f"Staging concepts directory not found: {staging_concepts}")
                return False
            
            # Upload each file to public branch via GitHub API
            files_uploaded = 0
            for file_path in staging_concepts.glob("*.md"):
                rel_path = file_path.relative_to(staging_concepts.parent)
                success = self._upload_file_to_github(owner, repo, github_pat, file_path, str(rel_path))
                if success:
                    files_uploaded += 1
                else:
                    logger.warning(f"Failed to upload {rel_path}")
            
            logger.info(f"Successfully uploaded {files_uploaded} files to public branch")
            return files_uploaded > 0
            
        except Exception as e:
            logger.error(f"GitHub API update failed: {e}", exc_info=True)
            return False
    
    def _upload_file_to_github(self, owner: str, repo: str, token: str, file_path: Path, rel_path: str) -> bool:
        """Upload a single file to GitHub using the Contents API."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Encode content for GitHub API
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # GitHub API URL for file
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{rel_path}"
            
            # Check if file exists on public branch
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get existing file SHA if it exists
            response = requests.get(f"{api_url}?ref=public", headers=headers)
            sha = response.json().get("sha") if response.status_code == 200 else None
            
            # Prepare commit data
            commit_data = {
                "message": f"SEED: Published {rel_path}",
                "content": encoded_content,
                "branch": "public"
            }
            
            if sha:
                commit_data["sha"] = sha
            
            # Upload file
            response = requests.put(api_url, headers=headers, json=commit_data)
            
            if response.status_code in [200, 201]:
                logger.debug(f"Successfully uploaded {rel_path}")
                return True
            else:
                logger.error(f"Failed to upload {rel_path}: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to upload {rel_path}: {e}")
            return False
    
    def _validate_authorized_concepts(self, existing_repo_dir: str = None) -> Tuple[bool, List[str], Dict[str, any]]:
        """Validate that we have authorized concepts to publish."""
        authorized_concepts = self._get_authorized_concepts(existing_repo_dir)
        if not authorized_concepts:
            return False, [], {
                "success": False,
                "error": "No authorized concepts found for publication",
                "concepts_processed": 0,
                "total_redactions": 0
            }
        
        logger.info(f"Found {len(authorized_concepts)} authorized concepts for publication")
        return True, authorized_concepts, {}
    
    
    def _checkout_main_branch(self, repo_path: str) -> Tuple[bool, Dict[str, any]]:
        """Checkout and update main branch."""
        # Ensure we're on main branch first
        success, _ = self._run_git_command(["git", "checkout", "main"], repo_path)
        if not success:
            return False, {
                "success": False,
                "error": "Failed to checkout main branch",
                "concepts_processed": 0,
                "total_redactions": 0
            }
        
        # Pull latest changes from main
        success, _ = self._run_git_command(["git", "pull", "origin", "main"], repo_path)
        if not success:
            logger.warning("Failed to pull latest changes from main, continuing...")
        
        return True, {}
    
    
    def _process_concepts_for_publication(self, authorized_concepts: List[str], 
                                        source_path: str, staging_path: str) -> Tuple[List[str], int]:
        """Process authorized concepts and apply redactions."""
        processed_concepts = []
        total_redactions = 0
        
        for concept_name in authorized_concepts:
            success, redaction_count = self._copy_and_redact_concept(
                concept_name, source_path, staging_path
            )
            if success:
                processed_concepts.append(concept_name)
                total_redactions += redaction_count
        
        return processed_concepts, total_redactions
    
    def _add_changes_to_git(self, repo_path: str, processed_concepts: List[str], 
                           total_redactions: int) -> Tuple[bool, Dict[str, any]]:
        """Add all changes to git staging."""
        success, _ = self._run_git_command(["git", "add", "."], repo_path)
        if not success:
            return False, {
                "success": False,
                "error": "Failed to add changes to git",
                "concepts_processed": len(processed_concepts),
                "total_redactions": total_redactions
            }
        return True, {}
    
    def _check_for_uncommitted_changes(self, repo_path: str, processed_concepts: List[str], 
                                       total_redactions: int) -> Dict[str, any]:
        """Check if there are uncommitted changes and handle appropriately."""
        success, output = self._run_git_command(["git", "status", "--porcelain"], repo_path)
        if success and not output.strip():
            logger.info("No changes to commit - public branch is up to date")
            return {
                "success": True,
                "message": "Public branch is already up to date",
                "concepts_processed": len(processed_concepts),
                "total_redactions": total_redactions,
                "published_concepts": processed_concepts
            }
        else:
            return {
                "success": False,
                "error": "Failed to commit changes",
                "concepts_processed": len(processed_concepts),
                "total_redactions": total_redactions
            }
    
    def _commit_changes(self, repo_path: str, processed_concepts: List[str], 
                       total_redactions: int) -> Tuple[bool, Dict[str, any]]:
        """Commit changes with appropriate message."""
        commit_message = f"SEED: Published {len(processed_concepts)} authorized concepts with {total_redactions} redactions"
        success, _ = self._run_git_command(["git", "commit", "-m", commit_message], repo_path)
        if not success:
            result = self._check_for_uncommitted_changes(repo_path, processed_concepts, total_redactions)
            return False, result
        return True, {}
    
    def _push_to_public_branch(self, repo_path: str, processed_concepts: List[str], 
                              total_redactions: int) -> Dict[str, any]:
        """Push committed changes to public branch."""
        success, _ = self._run_git_command(["git", "push", "origin", self.public_branch], repo_path)
        if not success:
            return {
                "success": False,
                "error": f"Failed to push to {self.public_branch} branch",
                "concepts_processed": len(processed_concepts),
                "total_redactions": total_redactions
            }
        
        logger.info(f"Successfully published {len(processed_concepts)} concepts to {self.public_branch} branch")
        return {
            "success": True,
            "message": f"Successfully published {len(processed_concepts)} concepts to {self.public_branch} branch",
            "concepts_processed": len(processed_concepts),
            "total_redactions": total_redactions,
            "published_concepts": processed_concepts,
            "public_branch": self.public_branch
        }
    
    def _commit_and_push_changes(self, repo_path: str, processed_concepts: List[str], 
                                total_redactions: int) -> Dict[str, any]:
        """Commit and push changes to public branch."""
        # Add all changes to git
        success, error = self._add_changes_to_git(repo_path, processed_concepts, total_redactions)
        if not success:
            return error
        
        # Commit changes
        success, result = self._commit_changes(repo_path, processed_concepts, total_redactions)
        if not success:
            return result  # Could be success (no changes) or error
        
        # Push to public branch
        return self._push_to_public_branch(repo_path, processed_concepts, total_redactions)
    
    def _validate_processed_concepts(self, processed_concepts: List[str]) -> Tuple[bool, Dict[str, any]]:
        """Validate that concepts were successfully processed."""
        if not processed_concepts:
            return False, {
                "success": False,
                "error": "No concepts were successfully processed",
                "concepts_processed": 0,
                "total_redactions": 0
            }
        return True, {}
    
    def _handle_pipeline_exception(self, error: Exception) -> Dict[str, any]:
        """Handle exceptions during pipeline execution."""
        logger.error(f"Publishing pipeline failed: {error}", exc_info=True)
        return {
            "success": False,
            "error": f"Publishing pipeline failed: {str(error)}",
            "concepts_processed": 0,
            "total_redactions": 0
        }
    
    def _setup_staging_directory(self) -> Tuple[bool, str, Dict[str, any]]:
        """Setup public staging directory for redacted files."""
        staging_dir = "/tmp/public_staging"
        
        # Clean up any existing staging directory
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        
        # Create staging directory structure
        os.makedirs(os.path.join(staging_dir, "concepts"), exist_ok=True)
        
        return True, staging_dir, {}
    
    def _copy_staging_to_public_branch(self, repo_path: str, staging_path: str) -> bool:
        """Copy staged files to public branch using GitHub API instead of Git commands."""
        try:
            # Use GitHub API to update the public branch
            success = self._github_api_update_public_branch(staging_path)
            if not success:
                logger.error("Failed to update public branch via GitHub API")
                return False
            
            logger.info("Successfully updated public branch via GitHub API")
            return True
        except Exception as e:
            logger.error(f"Failed to update public branch: {e}", exc_info=True)
            return False
    
    def _process_and_stage_concepts(self, authorized_concepts: List[str], existing_repo_dir: str = None) -> Tuple[bool, List[str], int, str, str, Dict[str, any]]:
        """Process concepts from main branch to staging directory."""
        if existing_repo_dir:
            # Use existing cloned repo directory (convert from concepts dir to repo root)
            repo_root = str(Path(existing_repo_dir).parent)
            source_path = repo_root
            logger.info(f"Using existing repo directory: {source_path}")
        else:
            # Fallback: use quarantine manager's temp directory (will trigger clone)
            source_path = str(self.quarantine_manager.temp_repo_dir)
        
        success, staging_path, error = self._setup_staging_directory()
        if not success:
            return False, [], 0, source_path, staging_path, error
        
        processed_concepts, total_redactions = self._process_concepts_for_publication(
            authorized_concepts, source_path, staging_path
        )
        
        valid, error_result = self._validate_processed_concepts(processed_concepts)
        if not valid:
            return False, processed_concepts, total_redactions, source_path, staging_path, error_result
        
        return True, processed_concepts, total_redactions, source_path, staging_path, {}
    
    def _execute_pipeline_steps(self, authorized_concepts: List[str], existing_repo_dir: str = None) -> Dict[str, any]:
        """Execute the main pipeline steps."""
        # Process and stage concepts (use existing repo if provided)
        success, processed_concepts, total_redactions, source_path, staging_path, error = self._process_and_stage_concepts(authorized_concepts, existing_repo_dir)
        if not success:
            return error
        
        # Copy staging files to public branch and commit
        if not self._copy_staging_to_public_branch(source_path, staging_path):
            return {
                "success": False,
                "error": "Failed to copy files to public branch",
                "concepts_processed": len(processed_concepts),
                "total_redactions": total_redactions
            }
        
        self._create_publication_metadata(source_path, processed_concepts, total_redactions)
        return {
            "success": True,
            "message": f"Successfully published {len(processed_concepts)} concepts to public branch",
            "concepts_processed": len(processed_concepts),
            "total_redactions": total_redactions
        }
    
    def publish_to_public_branch(self, existing_repo_dir: str = None) -> Dict[str, any]:
        """
        Execute the complete publishing pipeline.
        
        Args:
            existing_repo_dir: Path to already-cloned repo directory to reuse
        
        Returns:
            Dictionary with publication results
        """
        logger.info("Starting publication pipeline")
        
        # Validate authorized concepts (reuse existing repo if provided)
        valid, authorized_concepts, error_result = self._validate_authorized_concepts(existing_repo_dir)
        if not valid:
            return error_result
        
        try:
            return self._execute_pipeline_steps(authorized_concepts, existing_repo_dir)
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return self._handle_pipeline_exception(e)


def _create_test_instances() -> Tuple[RedactionManager, GitHubQuarantineManager, PublishingPipeline]:
    """Create test instances for pipeline testing."""
    redaction_manager = RedactionManager("test_redacted.json")
    
    # Get configuration from environment variables  
    github_pat = os.getenv('GITHUB_PAT')
    repo_url = os.getenv('GITHUB_REPO_URL')
    
    if not github_pat or not repo_url:
        raise ValueError("GITHUB_PAT and GITHUB_REPO_URL environment variables are required for testing")
    
    quarantine_manager = GitHubQuarantineManager(
        github_pat=github_pat,
        carton_repo_url=repo_url
    )
    
    # Add some test redaction rules
    redaction_manager.add_rule("secret_key_123", "[SECRET_REDACTED]")
    redaction_manager.add_rule("john.doe@company.com", "[EMAIL_REDACTED]")
    
    # Create publishing pipeline
    pipeline = PublishingPipeline(redaction_manager, quarantine_manager)
    return redaction_manager, quarantine_manager, pipeline

def _run_pipeline_test(pipeline: PublishingPipeline):
    """Run the pipeline test and handle results."""
    try:
        result = pipeline.publish_to_public_branch()
        print("Publication Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Test failed (expected without proper Git configuration): {e}", exc_info=True)
        print(f"Test failed (expected without proper Git configuration): {e}")

def _cleanup_test_files():
    """Clean up test files after testing."""
    if os.path.exists("test_redacted.json"):
        os.remove("test_redacted.json")

def main():
    """Test the PublishingPipeline functionality."""
    print("Publishing Pipeline Test")
    print("=" * 40)
    
    # Create test instances
    _, _, pipeline = _create_test_instances()
    
    # Run test
    _run_pipeline_test(pipeline)
    
    # Clean up
    _cleanup_test_files()
    print("\nTest completed!")


if __name__ == "__main__":
    main()