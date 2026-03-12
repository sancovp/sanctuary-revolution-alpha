#!/usr/bin/env python3
"""
Skill RAG Watcher Daemon

Continuously monitors HEAVEN_DATA_DIR/skills/ for changes and updates ChromaDB RAG index.
Provides dogfood feedback loop: create/update skills → auto-reindex → immediately searchable.

Usage:
    python3 skill_watcher_daemon.py

Environment Variables:
    HEAVEN_DATA_DIR: Base directory (default: /tmp/heaven_data)
"""

import os
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class SkillChangeHandler(FileSystemEventHandler):
    """Handles file system events for skill directory changes."""

    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self.last_reindex = 0
        self.debounce_seconds = 2  # Wait 2 seconds after changes before reindexing
        self.pending_reindex = False

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Only care about SKILL.md and _metadata.json
        if event.src_path.endswith('SKILL.md') or event.src_path.endswith('_metadata.json'):
            logger.info(f"Detected change: {event.src_path}")
            self.pending_reindex = True

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        if event.src_path.endswith('SKILL.md') or event.src_path.endswith('_metadata.json'):
            logger.info(f"Detected new file: {event.src_path}")
            self.pending_reindex = True

    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return

        if event.src_path.endswith('SKILL.md') or event.src_path.endswith('_metadata.json'):
            logger.info(f"Detected deletion: {event.src_path}")
            self.pending_reindex = True

    def check_and_reindex(self):
        """Check if reindex is needed and execute with debouncing."""
        if not self.pending_reindex:
            return

        now = time.time()
        if now - self.last_reindex < self.debounce_seconds:
            return  # Still in debounce window

        # Execute reindex
        logger.info("Reindexing skills...")
        try:
            result = self.skill_manager.reindex_all()
            logger.info(f"Reindex complete: {result['reindexed']} skills")
            self.last_reindex = now
            self.pending_reindex = False
        except Exception as e:
            import traceback
            logger.error(f"Reindex failed: {e}")
            logger.error(traceback.format_exc())
            # Keep pending flag so we retry later


def init_skill_manager():
    """Initialize SkillManager with error handling."""
    try:
        from skill_manager.core import SkillManager
        return SkillManager()
    except ImportError as e:
        import traceback
        logger.error(f"Failed to import SkillManager: {e}")
        logger.error(traceback.format_exc())
        logger.error("Make sure skill-manager-mcp is installed: pip install /home/GOD/skill_manager_mcp")
        sys.exit(1)


def validate_skills_dir():
    """Get and validate skills directory."""
    heaven_data = os.environ.get("HEAVEN_DATA_DIR", os.path.expanduser("~/.heaven_data"))
    skills_dir = Path(heaven_data) / "skills"

    if not skills_dir.exists():
        logger.error(f"Skills directory does not exist: {skills_dir}")
        sys.exit(1)

    return skills_dir


def initial_reindex(skill_manager):
    """Perform initial reindex on daemon startup."""
    logger.info("Performing initial reindex...")
    try:
        result = skill_manager.reindex_all()
        logger.info(f"Initial reindex complete: {result['reindexed']} skills")
    except Exception as e:
        import traceback
        logger.error(f"Initial reindex failed: {e}")
        logger.error(traceback.format_exc())


def run_observer_loop(event_handler, observer):
    """Run main observer loop with graceful shutdown."""
    try:
        while True:
            event_handler.check_and_reindex()
            time.sleep(0.5)  # Check every 500ms
    except KeyboardInterrupt:
        import traceback
        logger.info("Shutting down skill watcher daemon...")
        logger.debug(traceback.format_exc())
        observer.stop()
    finally:
        observer.join()
        logger.info("Skill watcher daemon stopped")


def main():
    """Main daemon entry point."""
    skills_dir = validate_skills_dir()
    logger.info(f"Starting skill watcher daemon for: {skills_dir}")

    skill_manager = init_skill_manager()
    logger.info("SkillManager initialized")

    initial_reindex(skill_manager)

    # Set up file system watcher
    event_handler = SkillChangeHandler(skill_manager)
    observer = Observer()
    observer.schedule(event_handler, str(skills_dir), recursive=True)
    observer.start()
    logger.info("File system observer started")

    run_observer_loop(event_handler, observer)


if __name__ == "__main__":
    main()
