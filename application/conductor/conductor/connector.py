"""Pluggable connector abstraction for code execution agent.

GrugConnector ABC with two implementations:
- SDNACConnector: wraps sdnac.execute() (fully blocking)
- ClaudePConnector: wraps tmux bridge to claude -p container (polls internally)
"""

import asyncio
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict


class GrugConnector(ABC):
    """Pluggable interface for code execution agent."""

    @abstractmethod
    async def send_and_wait(self, task: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Send work, BLOCK until done, return result."""
        ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Health check."""
        ...


class SDNACConnector(GrugConnector):
    """Wraps sdnac.execute() — fully blocking by design.

    SDNA execute() blocks until the agent is completely done.
    No polling needed. Simplest possible implementation.
    """

    def __init__(self, grug_sdnac):
        self.grug = grug_sdnac

    async def send_and_wait(self, task: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        merged = {**ctx, "task": task}
        result = await self.grug.execute(merged)
        return result.context

    def get_status(self) -> Dict[str, Any]:
        return {"type": "sdnac", "status": "ready"}


class ClaudePConnector(GrugConnector):
    """Wraps tmux bridge (claude -p in Docker container).

    Sends task via tmux send-keys, polls capture-pane internally
    until Grug signals done. Caller never sees the polling.
    """

    DONE_SIGNAL = "GRUG_DONE"

    def __init__(
        self,
        container_name: str = "repo-lord",
        tmux_session: str = "lord",
        poll_interval: int = 300,
        timeout: int = 3600,
    ):
        self.container = container_name
        self.tmux_session = tmux_session
        self.poll_interval = poll_interval
        self.timeout = timeout

    async def send_and_wait(self, task: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        self._tmux_send(task)
        elapsed = 0
        while elapsed < self.timeout:
            output = self._tmux_read()
            if self._is_done(output):
                return {"text": output, "status": "done"}
            await asyncio.sleep(self.poll_interval)
            elapsed += self.poll_interval
        return {"text": self._tmux_read(), "status": "timeout"}

    def get_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["docker", "exec", self.container, "tmux", "has-session", "-t", self.tmux_session],
                capture_output=True,
                timeout=10,
            )
            running = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            running = False
        return {"type": "claude_p", "container": self.container, "running": running}

    def _tmux_send(self, text: str) -> None:
        subprocess.run(
            ["docker", "exec", self.container, "tmux", "send-keys", "-t", self.tmux_session, text, "Enter"],
            capture_output=True,
            timeout=10,
        )

    def _tmux_read(self, lines: int = 500) -> str:
        result = subprocess.run(
            ["docker", "exec", self.container, "tmux", "capture-pane", "-t", self.tmux_session, "-p", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout

    def _is_done(self, output: str) -> bool:
        return self.DONE_SIGNAL in output
