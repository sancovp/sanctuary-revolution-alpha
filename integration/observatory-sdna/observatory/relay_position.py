"""RelayPosition — DUO position that sends work to a remote agent via sancrev relay.

Instead of executing an SDNAC in-process, this position sends the task
to a containerized agent via the parent sancrev's agent relay endpoint.

This is the primitive for cross-container DUO execution.
The remote agent (e.g. Grug in repo-lord) has its own CAVEHTTPServer
with an /execute endpoint. The parent sancrev relays to it.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RelayPosition:
    """DUO position that relays work to a remote containerized agent.

    Implements the DUOPosition protocol (async execute(context) -> PositionResult).
    Sends task to parent_url/agents/{agent_id}/execute and returns the result.
    """

    def __init__(self, parent_url: str, agent_id: str, timeout: float = 300.0):
        self.parent_url = parent_url
        self.agent_id = agent_id
        self.timeout = timeout

    async def execute(self, context: Dict[str, Any]):
        """Send task to remote agent via sancrev relay, return PositionResult."""
        from sdna.duo_chain import PositionResult, PositionStatus
        import httpx

        task = context.get("task", context.get("phase_prompt", ""))
        if not task:
            return PositionResult(
                status=PositionStatus.ERROR,
                context=context,
                error="No task in context (need 'task' or 'phase_prompt' key)",
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.parent_url}/agents/{self.agent_id}/execute",
                    json={"code": task, "timeout": int(self.timeout)},
                )
                resp.raise_for_status()
                result = resp.json()

            if "error" in result:
                return PositionResult(
                    status=PositionStatus.ERROR,
                    context={**context, **result},
                    error=result["error"],
                )

            # Merge remote result into context
            ctx = dict(context)
            ctx["text"] = result.get("response", result.get("output", ""))
            ctx["grug_result"] = result
            ctx["relay_agent"] = self.agent_id

            logger.info("RelayPosition: %s returned (status=%s)",
                        self.agent_id, result.get("status", "?"))

            return PositionResult(
                status=PositionStatus.SUCCESS,
                context=ctx,
            )

        except Exception as e:
            logger.error("RelayPosition: %s relay failed: %s", self.agent_id, e)
            return PositionResult(
                status=PositionStatus.ERROR,
                context=context,
                error=f"Relay to {self.agent_id} failed: {e}",
            )
