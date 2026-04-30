#!/usr/bin/env python3
"""
Canopy Execution Tracker - Records execution sequences for OPERA pattern detection

This tracker captures:
- What work was requested (schedule item)
- How it was executed (steps taken)
- What was delivered (outcomes)
- Session context (STARLOG integration)

Execution data flows to OPERA MCP for pattern detection and goldenization.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Import HEAVEN registry
# PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
try:
    from heaven_base.tools.registry_tool import registry_util_func
except ImportError:
    logger.warning("heaven_base not available - execution tracking will not persist", exc_info=True)
    def registry_util_func(*args, **kwargs):
        return "Registry not available"

# Registry name for execution ledger
EXECUTION_LEDGER_REGISTRY = "canopy_execution_ledger"


class ExecutionTracker:
    """
    Tracks execution of Canopy schedule items for OPERA pattern detection.

    Records execution as it happens, capturing the actual workflow steps
    rather than just the plan. This enables pattern discovery and reuse.
    """

    def __init__(self):
        self.current_tracking: Optional[Dict[str, Any]] = None
        self.tracking_id: Optional[str] = None

    def start_tracking(
        self,
        schedule_item_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Begin tracking execution of a schedule item.

        Args:
            schedule_item_id: The Canopy schedule item being executed
            session_id: Optional STARLOG session ID
            metadata: Optional additional context

        Returns:
            tracking_id: Unique identifier for this execution
        """
        try:
            # Generate tracking ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            tracking_id = f"exec_{schedule_item_id}_{timestamp}"

            # Initialize tracking data
            self.current_tracking = {
                "tracking_id": tracking_id,
                "schedule_item_id": schedule_item_id,
                "session_id": session_id,
                "started_at": datetime.now().isoformat(),
                "steps": [],
                "metadata": metadata or {},
                "status": "in_progress"
            }

            self.tracking_id = tracking_id

            logger.info(f"Started execution tracking: {tracking_id}")
            return tracking_id

        except Exception as e:
            logger.error(f"Error starting execution tracking: {e}", exc_info=True)
            raise

    def record_step(
        self,
        step_type: str,
        description: str,
        tools_used: Optional[List[str]] = None,
        duration_seconds: Optional[float] = None,
        outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record a step in the execution sequence.

        Args:
            step_type: Type of step (e.g., "analysis", "implementation", "testing")
            description: Human-readable description of what happened
            tools_used: List of tools/MCPs used in this step
            duration_seconds: How long the step took
            outcome: Result of the step ("success", "failed", "blocked")
            metadata: Additional step-specific data

        Returns:
            bool: True if step recorded successfully
        """
        try:
            if not self.current_tracking:
                raise ValueError("No active tracking session. Call start_tracking() first.")

            step = {
                "step_number": len(self.current_tracking["steps"]) + 1,
                "step_type": step_type,
                "description": description,
                "tools_used": tools_used or [],
                "duration_seconds": duration_seconds,
                "outcome": outcome,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            self.current_tracking["steps"].append(step)
            logger.debug(f"Recorded step {step['step_number']}: {description}")

            return True

        except Exception as e:
            logger.error(f"Error recording step: {e}", exc_info=True)
            return False

    def complete_tracking(
        self,
        success: bool,
        deliverables: Optional[List[str]] = None,
        summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete execution tracking and persist to ledger.

        Args:
            success: Whether execution completed successfully
            deliverables: List of what was produced/delivered
            summary: Human-readable summary of execution

        Returns:
            Dict with tracking_id and persistence result
        """
        try:
            if not self.current_tracking:
                raise ValueError("No active tracking session. Call start_tracking() first.")

            # Finalize tracking data
            self.current_tracking.update({
                "completed_at": datetime.now().isoformat(),
                "status": "completed" if success else "failed",
                "success": success,
                "deliverables": deliverables or [],
                "summary": summary or "",
                "total_steps": len(self.current_tracking["steps"])
            })

            # Calculate total duration
            started = datetime.fromisoformat(self.current_tracking["started_at"])
            completed = datetime.fromisoformat(self.current_tracking["completed_at"])
            duration = (completed - started).total_seconds()
            self.current_tracking["total_duration_seconds"] = duration

            # Persist to execution ledger registry
            tracking_id = self.current_tracking["tracking_id"]
            if not self._persist_to_ledger(tracking_id):
                logger.warning(f"Failed to persist tracking to ledger: {tracking_id}")

            logger.info(f"Completed execution tracking: {tracking_id} (success={success})")

            result = {
                "tracking_id": tracking_id,
                "success": success,
                "total_steps": self.current_tracking["total_steps"],
                "total_duration": duration,
                "message": f"Execution tracking completed and persisted to ledger"
            }

            # Clear current tracking
            self.current_tracking = None
            self.tracking_id = None

            return result

        except Exception as e:
            logger.error(f"Error completing execution tracking: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def abandon_tracking(self, reason: str) -> Dict[str, Any]:
        """
        Abandon current tracking session (e.g., user cancelled).

        Args:
            reason: Why tracking was abandoned

        Returns:
            Dict with result
        """
        try:
            if not self.current_tracking:
                return {"message": "No active tracking session"}

            tracking_id = self.current_tracking["tracking_id"]
            self.current_tracking.update({
                "status": "abandoned",
                "abandoned_at": datetime.now().isoformat(),
                "abandon_reason": reason
            })

            # Still persist to ledger for analysis
            if not self._persist_to_ledger(tracking_id):
                logger.warning(f"Failed to persist abandoned tracking: {tracking_id}")

            logger.info(f"Abandoned execution tracking: {tracking_id}")

            # Clear current tracking
            self.current_tracking = None
            self.tracking_id = None

            return {
                "tracking_id": tracking_id,
                "message": f"Tracking abandoned: {reason}"
            }

        except Exception as e:
            logger.error(f"Error abandoning tracking: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_current_tracking(self) -> Optional[Dict[str, Any]]:
        """Get current tracking data (for debugging/monitoring)."""
        return self.current_tracking

    def _persist_to_ledger(self, tracking_id: str) -> bool:
        """
        Helper method to persist current tracking data to ledger.

        Args:
            tracking_id: The tracking ID to use as registry key

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            registry_util_func(
                "add",
                registry_name=EXECUTION_LEDGER_REGISTRY,
                key=tracking_id,
                value_dict=self.current_tracking
            )
            return True
        except Exception as e:
            logger.error(f"Error persisting to ledger: {e}", exc_info=True)
            return False


def get_execution_history(
    schedule_item_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Query execution ledger for historical executions.

    Args:
        schedule_item_id: Optional filter by schedule item
        limit: Maximum number of results

    Returns:
        List of execution records
    """
    try:
        result = registry_util_func("get_all", registry_name=EXECUTION_LEDGER_REGISTRY)

        # Parse registry result
        if "Items in registry" in result:
            try:
                start_idx = result.find("{")
                if start_idx != -1:
                    dict_str = result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    all_executions = json.loads(dict_str.replace("'", '"'))

                    executions = list(all_executions.values())

                    # Filter by schedule_item_id if provided
                    if schedule_item_id:
                        executions = [
                            ex for ex in executions
                            if ex.get("schedule_item_id") == schedule_item_id
                        ]

                    # Sort by started_at (most recent first)
                    executions.sort(
                        key=lambda x: x.get("started_at", ""),
                        reverse=True
                    )

                    return executions[:limit]
            except Exception as e:
                logger.warning(f"Failed to parse execution ledger: {e}", exc_info=True)

        return []

    except Exception as e:
        logger.error(f"Error querying execution history: {e}", exc_info=True)
        return []
