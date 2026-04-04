"""ResearcherAgent — ServiceAgent for Observatory research queue.

Thin CAVE shell. ALL logic lives in observatory.runner.
This agent DIs the runner as its runtime. agent.run() → runner.run_research().

Route /research/run writes to queue file, then calls agent.run().
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from cave.core.agent import ServiceAgent

logger = logging.getLogger(__name__)


class ResearcherAgent(ServiceAgent):
    """Observatory researcher. Thin shell around observatory.runner."""

    def init_runtime(self) -> bool:
        """DI the observatory runner as this agent's runtime."""
        try:
            from observatory.runner import run_research, recover_interrupted

            recover_interrupted()

            # Build notify callback from central_channel
            def _notify(text: str):
                if not self.central_channel:
                    return
                main_ch = self.central_channel.main()
                if not main_ch:
                    return
                try:
                    if len(text) <= 1900:
                        main_ch.deliver({"message": text})
                    else:
                        remaining = text
                        while remaining:
                            chunk = remaining[:1900]
                            remaining = remaining[1900:]
                            main_ch.deliver({"message": chunk})
                except Exception as e:
                    logger.error("ResearcherAgent notify error: %s", e)

            # Build EventBroadcaster for SDNAC turn-by-turn output
            from cave.core.event_broadcaster import EventBroadcaster
            broadcaster = None
            if self.central_channel and self.central_channel.main():
                broadcaster = EventBroadcaster(self.central_channel.main(), label="Researcher")

            # The runtime — called by agent.run()
            async def _run_runtime(message=None):
                return await run_research(on_notify=_notify, on_message=broadcaster)

            self.set_runtime(_run_runtime)
            logger.info("ResearcherAgent: observatory runner DI'd as runtime")
            return True

        except Exception as e:
            logger.error("ResearcherAgent: failed to init runtime: %s", e, exc_info=True)
            return False

    @property
    def status(self) -> Dict[str, Any]:
        """Current researcher status."""
        try:
            from observatory.runner import get_status
            return get_status()
        except Exception:
            return {"error": "observatory.runner not available"}
