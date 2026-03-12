#!/usr/bin/env python3
"""Compoctopus Daemon — watches for .🪸 files and runs the pipeline.

Usage:
    python -m compoctopus.daemon
    python -m compoctopus.daemon --queue /path/to/queue --interval 5

The daemon polls the queue directory for .🪸 (coral) files.
When found, it runs the pipeline via run_from_prd() and outputs a .🏄 report.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from glob import glob

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-30s %(levelname)-8s %(message)s',
)
logger = logging.getLogger("compoctopus.daemon")

DEFAULT_QUEUE = "/tmp/compoctopus_daemon_queue"
DEFAULT_INTERVAL = 5  # seconds


async def process_coral(coral_path: Path) -> None:
    """Process a single .🪸 file."""
    from compoctopus.run import run_from_prd

    logger.info("🪸 Found coral: %s", coral_path.name)

    try:
        result = await run_from_prd(str(coral_path))
        logger.info(
            "🏄 Build complete: %s → %s (%d files)",
            result["prd_name"],
            result["status"],
            len(result["output_files"]),
        )
    except Exception as e:
        logger.error("❌ Build failed for %s: %s", coral_path.name, e, exc_info=True)

        # Write error report
        import json
        from datetime import datetime
        error_report = {
            "prd_path": str(coral_path),
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
        error_path = coral_path.with_suffix(".🏄")
        error_path.write_text(json.dumps(error_report, indent=2))

    # Move processed coral to done subdir
    done_dir = coral_path.parent / "done"
    done_dir.mkdir(exist_ok=True)
    dest = done_dir / coral_path.name
    coral_path.rename(dest)
    logger.info("📁 Moved %s → done/", coral_path.name)


async def daemon_loop(queue_dir: str, interval: int) -> None:
    """Main daemon loop — poll for .🪸 files."""
    queue = Path(queue_dir)
    queue.mkdir(parents=True, exist_ok=True)

    logger.info("🐙 Compoctopus daemon started")
    logger.info("   Queue: %s", queue)
    logger.info("   Interval: %ds", interval)
    logger.info("   Waiting for .🪸 files...\n")

    while True:
        corals = sorted(queue.glob("*.🪸"))

        for coral in corals:
            await process_coral(coral)

        await asyncio.sleep(interval)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compoctopus build daemon")
    parser.add_argument("--queue", default=DEFAULT_QUEUE, help="Queue directory to watch")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Poll interval in seconds")
    args = parser.parse_args()

    os.environ.setdefault("HEAVEN_DATA_DIR", "/tmp/heaven_data")

    try:
        asyncio.run(daemon_loop(args.queue, args.interval))
    except KeyboardInterrupt:
        logger.info("\n👋 Daemon stopped.")


if __name__ == "__main__":
    main()
