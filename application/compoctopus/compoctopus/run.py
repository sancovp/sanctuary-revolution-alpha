"""Compoctopus public API — entrypoints for running the pipeline.

run_from_prd(prd_path)   — load a .🪸 PRD, run pipeline, output .🏄 report
run_autonomously()       — meta mode (future)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from compoctopus.prd import PRD
from compoctopus.compoctopus import make_compoctopus

logger = logging.getLogger(__name__)


async def run_from_prd(
    prd_path: str,
    workspace: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a .🪸 PRD file, run the full pipeline, output a .🏄 report.

    Args:
        prd_path: Path to a .🪸 (coral) PRD file.
        workspace: Output directory. Default: /tmp/compoctopus_output/<name>_<timestamp>

    Returns:
        Dict with results: status, workspace, files, report_path
    """
    prd_path = Path(prd_path)
    if not prd_path.exists():
        raise FileNotFoundError(f"PRD not found: {prd_path}")

    # Load PRD
    with open(prd_path) as f:
        prd_dict = json.load(f)
    prd = PRD.from_dict(prd_dict)

    logger.info("🐙 Running pipeline for PRD '%s' from %s", prd.name, prd_path)

    # Workspace
    if workspace is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workspace = f"/tmp/compoctopus_output/{prd.name}_{timestamp}"
    os.makedirs(workspace, exist_ok=True)

    # Build and run
    agent = make_compoctopus(prd=prd, workspace=workspace)
    result = await agent.execute({
        "prd": prd.to_dict(),
        "workspace": workspace,
        "spec": prd.to_spec_string(),
    })

    # Collect output files
    output_files = []
    for root, dirs, files in os.walk(workspace):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), workspace)
            output_files.append(rel)

    # Determine status
    if hasattr(result, 'status'):
        status = str(result.status)
    elif isinstance(result, dict):
        completed = result.get("completed", 0)
        total = result.get("total_tasks", 0)
        status = "success" if completed == total and total > 0 else "partial"
    else:
        status = "unknown"

    # Write .🏄 report
    report = {
        "prd_name": prd.name,
        "prd_path": str(prd_path),
        "status": status,
        "workspace": workspace,
        "output_files": output_files,
        "timestamp": datetime.now().isoformat(),
        "assertions_count": len(prd.behavioral_assertions),
    }

    report_path = prd_path.with_suffix(".🏄")
    report_path.write_text(json.dumps(report, indent=2))

    logger.info("🏄 Report written: %s (%d files, status=%s)",
                report_path, len(output_files), status)

    return {
        "status": status,
        "workspace": workspace,
        "output_files": output_files,
        "report_path": str(report_path),
        "prd_name": prd.name,
    }


def run_from_prd_sync(prd_path: str, workspace: Optional[str] = None) -> Dict[str, Any]:
    """Sync wrapper for run_from_prd."""
    return asyncio.run(run_from_prd(prd_path, workspace))


async def run_autonomously():
    """Meta mode — Compoctopus runs without a PRD. Future."""
    raise NotImplementedError(
        "run_autonomously() is not yet implemented. "
        "Use run_from_prd() with a .🪸 PRD file."
    )
