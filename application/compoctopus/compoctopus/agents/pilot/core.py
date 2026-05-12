"""Starship Pilot — entry points for queue-based DuoChain orchestrator.

Usage:
    # Submit work
    from compoctopus.agents.pilot.factory import submit_deliverable, submit_task

    # Drop a deliverable (pilot breaks into tasks)
    submit_deliverable("/home/GOD/carton_mcp", "Add per-domain OWL infrastructure")

    # Drop a task (pilot goes straight to ralph)
    submit_task("/home/GOD/carton_mcp", "Add domain param to get_cat()", "get_cat")

    # Process queue (blocks until all pending items done)
    from compoctopus.agents.pilot.factory import process_queue
    process_queue()

    # Review done items, then respond
    from compoctopus.agents.pilot.factory import list_queue, submit_ovp_response
    done = list_queue("done")
    submit_ovp_response(done[0]["id"], approved=True)
    # or
    submit_ovp_response(done[0]["id"], approved=False, feedback="Tests failing, fix X")

    # Resume after OVP response
    from compoctopus.agents.pilot.factory import resume_from_ovp
    resume_from_ovp(done[0]["id"])
"""

from compoctopus.agents.pilot.factory import (
    submit_deliverable,
    submit_task,
    submit_ovp_response,
    list_queue,
    process_queue,
    resume_from_ovp,
)

__all__ = [
    "submit_deliverable",
    "submit_task",
    "submit_ovp_response",
    "list_queue",
    "process_queue",
    "resume_from_ovp",
]
