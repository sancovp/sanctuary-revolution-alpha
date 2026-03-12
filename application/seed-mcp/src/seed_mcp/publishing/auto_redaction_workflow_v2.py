#!/usr/bin/env python3
"""
Auto-Redaction Workflow v2: Uses ContentDiffer v2 with mirror directory structure

This module orchestrates the complete workflow:
1. ContentDiffer v2 compares current files vs published cache (Overview-only changes)
2. RedactorAgent processes concepts needing redaction
3. PublishingPipeline publishes to #public branch
4. ContentDiffer v2 cache is updated ONLY after successful publication
"""

import os
import logging
import tempfile
from typing import Dict, List, Tuple, Any
from pathlib import Path

from content_differ_v2 import ContentDifferV2
from redaction_manager import RedactionManager
from publishing_pipeline import PublishingPipeline
from seed_quarantine_github_v2 import GitHubQuarantineManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoRedactionWorkflowV2:
    """Orchestrates the complete auto-redaction and publishing workflow using ContentDiffer v2."""
    
    def __init__(self, concepts_dir: str = "./concepts", 
                 github_pat: str = None, carton_repo_url: str = None,
                 published_cache_dir: str = "/tmp/published_cache"):
        """
        Initialize the auto-redaction workflow v2.
        
        Args:
            concepts_dir: Directory containing concept markdown files
            github_pat: GitHub personal access token
            carton_repo_url: URL of the Carton repository
            published_cache_dir: Directory for published content mirror
        """
        self.concepts_dir = concepts_dir
        self.content_differ = ContentDifferV2(published_cache_dir)
        self.redaction_manager = RedactionManager("redacted.json")
        self.quarantine_manager = GitHubQuarantineManager(
            github_pat=github_pat,
            carton_repo_url=carton_repo_url
        )
        self.publishing_pipeline = PublishingPipeline(
            self.redaction_manager, 
            self.quarantine_manager
        )
    
    def _setup_and_get_concepts_directory(self) -> Tuple[bool, str]:
        """Setup git repo and get concepts directory path."""
        # Check if repo is already cloned, if not clone it
        repo_concepts_dir = os.path.join(self.quarantine_manager.temp_repo_dir, "concepts")
        
        if not os.path.exists(repo_concepts_dir):
            # Setup the git repository (clones from GitHub)
            setup_result = self.quarantine_manager._setup_git_repo()
            if "error" in setup_result:
                logger.error(f"Failed to setup git repo: {setup_result['error']}")
                return False, ""
        
        if not os.path.exists(repo_concepts_dir):
            logger.error(f"Concepts directory not found in cloned repo: {repo_concepts_dir}")
            return False, ""
        
        logger.info(f"Using concepts directory from cloned repo: {repo_concepts_dir}")
        return True, repo_concepts_dir
    
    def _get_authorized_concept_names(self) -> List[str]:
        """Get list of authorized concept names from quarantine system."""
        try:
            authorized_data = self.quarantine_manager._load_authorized_json()
            authorized_concepts = []
            
            for concept_name, concept_data in authorized_data.items():
                if concept_data.get("status") == "AUTHORIZED":
                    authorized_concepts.append(concept_name)
            
            logger.info(f"Found {len(authorized_concepts)} authorized concepts")
            return authorized_concepts
            
        except Exception as e:
            logger.error(f"Failed to get authorized concepts: {e}", exc_info=True)
            return []
    
    async def _run_redactor_agent_on_file(self, file_path: str) -> Tuple[bool, int]:
        """
        Run RedactorAgent on a single file to add redaction rules.
        
        Returns:
            Tuple of (success, redaction_rules_added)
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create wrapped content for RedactorAgent
            wrapped_content = f"<maybe_redact>\n{content}\n</maybe_redact>\n\nPlease analyze this content and identify any sensitive information that should be redacted before publication."
            
            # Get current rule count
            initial_rules_count = len(self.redaction_manager.get_rules())
            
            # Import HEAVEN framework components
            os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
            
            from heaven_base import BaseHeavenAgent, UnifiedChat
            from heaven_base.agents.redactor_agent_config import redactor_agent_config
            from heaven_base.memory.history import History
            
            # Create and run RedactorAgent
            history = History(messages=[])
            agent = BaseHeavenAgent(redactor_agent_config, UnifiedChat, history=history)
            
            logger.info(f"Running RedactorAgent on {os.path.basename(file_path)}")
            result = await agent.run(prompt=wrapped_content)
            
            # Get new rule count
            final_rules_count = len(self.redaction_manager.get_rules())
            rules_added = final_rules_count - initial_rules_count
            
            logger.info(f"RedactorAgent completed: {rules_added} rules added")
            return True, rules_added
                
        except Exception as e:
            logger.error(f"RedactorAgent failed on {file_path}: {e}", exc_info=True)
            return False, 0
    
    async def _process_concepts_needing_redaction(self, concepts_needing_redaction: List[str], 
                                                current_concepts_dir: str) -> Tuple[int, int]:
        """
        Process concepts through RedactorAgent.
        
        Returns:
            Tuple of (files_processed, total_rules_added)
        """
        files_processed = 0
        total_rules_added = 0
        
        for concept_name in concepts_needing_redaction:
            file_path = os.path.join(current_concepts_dir, concept_name, f"{concept_name}_itself.md")
            
            if not os.path.exists(file_path):
                logger.warning(f"Concept file not found: {file_path}")
                continue
            
            logger.info(f"Processing concept needing redaction: {concept_name}")
            success, rules_added = await self._run_redactor_agent_on_file(file_path)
            
            if success:
                files_processed += 1
                total_rules_added += rules_added
            else:
                logger.error(f"Failed to process {concept_name}")
        
        return files_processed, total_rules_added
    
    async def execute_auto_redaction_workflow(self) -> Dict[str, Any]:
        """
        Execute the complete auto-redaction workflow using ContentDiffer v2.
        
        Returns:
            Results dictionary with workflow status
        """
        logger.info("Starting auto-redaction workflow v2")
        
        try:
            # Setup git repo and get concepts directory
            success, repo_concepts_dir = self._setup_and_get_concepts_directory()
            if not success:
                return {
                    "success": False,
                    "error": "Failed to setup git repository or find concepts directory",
                    "files_processed": 0,
                    "rules_added": 0
                }
            
            # Update concepts_dir to use the cloned repo directory
            self.concepts_dir = repo_concepts_dir
            
            # Get authorized concept names
            authorized_concepts = self._get_authorized_concept_names()
            if not authorized_concepts:
                return {
                    "success": True,
                    "message": "No authorized concepts found",
                    "files_processed": 0,
                    "rules_added": 0,
                    "publication_result": None
                }
            
            # Use ContentDiffer v2 to find concepts needing redaction (Overview changes only)
            concepts_needing_redaction = self.content_differ.get_concepts_needing_redaction(
                authorized_concepts, repo_concepts_dir
            )
            
            if not concepts_needing_redaction:
                logger.info("No concepts need redaction - skipping auto-redaction")
                return {
                    "success": True,
                    "message": "No concepts needed redaction",
                    "files_processed": 0,
                    "rules_added": 0,
                    "publication_result": None
                }
            
            # Process concepts through RedactorAgent
            files_processed, rules_added = await self._process_concepts_needing_redaction(
                concepts_needing_redaction, repo_concepts_dir
            )
            logger.info(f"Processed {files_processed} concepts, added {rules_added} redaction rules")
            
            # Execute publishing pipeline (reuse the cloned repo)
            logger.info("Starting publication to public branch")
            publication_result = self.publishing_pipeline.publish_to_public_branch(
                existing_repo_dir=repo_concepts_dir
            )
            
            # Update ContentDiffer v2 cache ONLY after successful publication
            if publication_result.get("success", False):
                published_concepts = publication_result.get("published_concepts", [])
                if published_concepts:
                    self.content_differ.update_all_published_content(published_concepts, repo_concepts_dir)
                    logger.info(f"Updated published content cache for {len(published_concepts)} concepts")
            
            return {
                "success": True,
                "message": f"Auto-redaction workflow v2 completed: {files_processed} concepts processed, {rules_added} rules added",
                "files_processed": files_processed,
                "rules_added": rules_added,
                "concepts_needing_redaction": concepts_needing_redaction,
                "publication_result": publication_result
            }
            
        except Exception as e:
            logger.error(f"Auto-redaction workflow v2 failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Workflow failed: {str(e)}",
                "files_processed": 0,
                "rules_added": 0
            }


def main():
    """Test the auto-redaction workflow v2."""
    print("Auto-Redaction Workflow v2 Test")
    print("=" * 50)
    
    # Create workflow instance
    workflow = AutoRedactionWorkflowV2("./concepts")
    
    # Execute workflow
    import asyncio
    result = asyncio.run(workflow.execute_auto_redaction_workflow())
    
    print("Workflow Result:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print(f"  Files Processed: {result.get('files_processed', 0)}")
    print(f"  Rules Added: {result.get('rules_added', 0)}")
    
    concepts_needing_redaction = result.get('concepts_needing_redaction', [])
    if concepts_needing_redaction:
        print(f"  Concepts Needing Redaction: {concepts_needing_redaction}")
    
    if result.get('error'):
        print(f"  Error: {result['error']}")
    
    publication_result = result.get('publication_result')
    if publication_result:
        print(f"  Publication Success: {publication_result.get('success', False)}")
        if publication_result.get('error'):
            print(f"  Publication Error: {publication_result['error']}")


if __name__ == "__main__":
    main()