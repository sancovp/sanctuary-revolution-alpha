"""Tests for GrugConnector ABC and implementations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, Any

from observatory.connector import GrugConnector, SDNACConnector, ClaudePConnector


@dataclass
class MockSDNAResult:
    status: MagicMock = field(default_factory=lambda: MagicMock(value="success"))
    context: Dict[str, Any] = field(default_factory=lambda: {"text": "grug output", "code": "print('hi')"})
    error: str = None


class TestGrugConnectorABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            GrugConnector()

    def test_subclass_must_implement_send_and_wait(self):
        class Incomplete(GrugConnector):
            def get_status(self):
                return {}

        with pytest.raises(TypeError):
            Incomplete()

    def test_subclass_must_implement_get_status(self):
        class Incomplete(GrugConnector):
            async def send_and_wait(self, task, ctx):
                return {}

        with pytest.raises(TypeError):
            Incomplete()


class TestSDNACConnector:
    @pytest.mark.asyncio
    async def test_send_and_wait_calls_execute(self):
        mock_sdnac = MagicMock()
        mock_sdnac.execute = AsyncMock(return_value=MockSDNAResult())
        connector = SDNACConnector(mock_sdnac)

        result = await connector.send_and_wait("build feature X", {"repo": "test"})

        mock_sdnac.execute.assert_called_once_with({"repo": "test", "task": "build feature X"})
        assert result == {"text": "grug output", "code": "print('hi')"}

    @pytest.mark.asyncio
    async def test_send_and_wait_merges_context(self):
        mock_sdnac = MagicMock()
        mock_sdnac.execute = AsyncMock(return_value=MockSDNAResult())
        connector = SDNACConnector(mock_sdnac)

        await connector.send_and_wait("task", {"a": 1, "b": 2})

        call_ctx = mock_sdnac.execute.call_args[0][0]
        assert call_ctx["a"] == 1
        assert call_ctx["b"] == 2
        assert call_ctx["task"] == "task"

    def test_get_status(self):
        connector = SDNACConnector(MagicMock())
        status = connector.get_status()
        assert status["type"] == "sdnac"
        assert status["status"] == "ready"


class TestClaudePConnector:
    def test_default_config(self):
        connector = ClaudePConnector()
        assert connector.container == "repo-lord"
        assert connector.tmux_session == "lord"
        assert connector.poll_interval == 300
        assert connector.timeout == 3600

    def test_custom_config(self):
        connector = ClaudePConnector(
            container_name="my-container",
            tmux_session="my-session",
            poll_interval=60,
            timeout=600,
        )
        assert connector.container == "my-container"
        assert connector.tmux_session == "my-session"
        assert connector.poll_interval == 60
        assert connector.timeout == 600

    @pytest.mark.asyncio
    async def test_send_and_wait_returns_on_done_signal(self):
        connector = ClaudePConnector(poll_interval=0)
        connector._tmux_send = MagicMock()
        connector._tmux_read = MagicMock(return_value=f"some output\n{ClaudePConnector.DONE_SIGNAL}\nmore")

        result = await connector.send_and_wait("do stuff", {})

        connector._tmux_send.assert_called_once_with("do stuff")
        assert result["status"] == "done"
        assert ClaudePConnector.DONE_SIGNAL in result["text"]

    @pytest.mark.asyncio
    async def test_send_and_wait_timeout(self):
        connector = ClaudePConnector(poll_interval=0, timeout=0)
        connector._tmux_send = MagicMock()
        connector._tmux_read = MagicMock(return_value="still working...")

        result = await connector.send_and_wait("do stuff", {})

        assert result["status"] == "timeout"

    def test_is_done_detects_signal(self):
        connector = ClaudePConnector()
        assert connector._is_done(f"output\n{ClaudePConnector.DONE_SIGNAL}\n") is True
        assert connector._is_done("just normal output") is False

    @patch("observatory.connector.subprocess.run")
    def test_get_status_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        connector = ClaudePConnector()
        status = connector.get_status()
        assert status["type"] == "claude_p"
        assert status["running"] is True

    @patch("observatory.connector.subprocess.run")
    def test_get_status_not_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        connector = ClaudePConnector()
        status = connector.get_status()
        assert status["running"] is False
