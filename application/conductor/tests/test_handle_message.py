"""Tests for Conductor.handle_message with AutoSummarizingAgent + BackgroundEventCapture."""
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from conductor.conductor import Conductor, _build_agent_config, CONDUCTOR_CONVERSATION_STATE
from conductor.connector import ClaudePConnector
from conductor.state_machine import StateMachine


def _make_mock_agent(history_id="hist_001"):
    """Create a mock BaseHeavenAgent that returns a result dict from run()."""
    agent = MagicMock()
    agent.run = AsyncMock(return_value={"history_id": history_id})
    return agent


def _make_mock_capture(response_text="Hello Isaac!"):
    """Create a mock BackgroundEventCapture that returns AGENT_MESSAGE events."""
    capture = MagicMock()
    if response_text is not None:
        capture.get_events_by_type.return_value = [
            {"event_type": "AGENT_MESSAGE", "data": {"content": response_text}}
        ]
    else:
        capture.get_events_by_type.return_value = []
    return capture


@pytest.fixture
def conductor(tmp_path, monkeypatch):
    """Create a Conductor with mocked dependencies and isolated state file."""
    state_file = tmp_path / "conductor_conversation.json"
    monkeypatch.setattr("conductor.conductor.CONDUCTOR_CONVERSATION_STATE", state_file)
    connector = ClaudePConnector()
    state = StateMachine("test")
    return Conductor(
        connector=connector,
        researcher_sdnac=None,
        state=state,
    )


class TestHandleMessage:
    """Test Conductor.handle_message with BaseHeavenAgent + BackgroundEventCapture."""

    @pytest.mark.asyncio
    async def test_handle_message_returns_success(self, conductor):
        """handle_message creates agent, runs with callback, returns response."""
        mock_agent = _make_mock_agent("hist_001")
        mock_capture = _make_mock_capture("Hello Isaac!")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent) as mock_bha, \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            result = await conductor.handle_message("hello conductor!")

        assert result["status"] == "success"
        assert result["response"] == "Hello Isaac!"
        mock_agent.run.assert_called_once()
        # Verify CompositeCallback wrapping capture was passed to run()
        call_kwargs = mock_agent.run.call_args
        composite = call_kwargs.kwargs.get("heaven_main_callback")
        from heaven_base.docs.examples.heaven_callbacks import CompositeCallback
        assert isinstance(composite, CompositeCallback)
        assert mock_capture in composite.callbacks

    @pytest.mark.asyncio
    async def test_handle_message_updates_history_id(self, conductor):
        """After agent.run(), history_id is updated from result dict."""
        mock_agent = _make_mock_agent("hist_002")
        mock_capture = _make_mock_capture("response")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            await conductor.handle_message("test")

        assert conductor.history_id == "hist_002"

    @pytest.mark.asyncio
    async def test_handle_message_passes_history_id_on_continuation(self, conductor):
        """When history_id exists, BaseHeavenAgent is constructed with it."""
        conductor.history_id = "hist_existing"
        mock_agent = _make_mock_agent("hist_existing")
        mock_capture = _make_mock_capture("ok")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent) as mock_bha, \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            await conductor.handle_message("continue")

        # Verify history_id was passed to BaseHeavenAgent constructor
        call_kwargs = mock_bha.call_args
        assert call_kwargs.kwargs.get("history_id") == "hist_existing"

    @pytest.mark.asyncio
    async def test_handle_message_no_history_id_on_fresh_start(self, conductor):
        """Fresh start (no history_id) creates agent WITHOUT history_id."""
        assert conductor.history_id is None
        mock_agent = _make_mock_agent("hist_new")
        mock_capture = _make_mock_capture("hi")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent) as mock_bha, \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            await conductor.handle_message("first message")

        # history_id should NOT be in constructor kwargs for fresh call
        call_kwargs = mock_bha.call_args.kwargs
        assert "history_id" not in call_kwargs

    @pytest.mark.asyncio
    async def test_handle_message_accumulates_history(self, conductor):
        """Multiple messages update history_id each time."""
        mock_agent1 = _make_mock_agent("hist_001")
        mock_agent2 = _make_mock_agent("hist_002")
        mock_capture1 = _make_mock_capture("first")
        mock_capture2 = _make_mock_capture("second")

        agents = iter([mock_agent1, mock_agent2])
        captures = iter([mock_capture1, mock_capture2])

        with patch("conductor.conductor.AutoSummarizingAgent", side_effect=lambda *a, **kw: next(agents)), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", side_effect=lambda: next(captures)), \
             patch.object(conductor, "_update_conversation"):

            r1 = await conductor.handle_message("first")
            r2 = await conductor.handle_message("second")

        assert r1["response"] == "first"
        assert r2["response"] == "second"
        assert conductor.history_id == "hist_002"

    @pytest.mark.asyncio
    async def test_handle_message_history_id_flows_between_calls(self, conductor):
        """CRITICAL: Call 1 returns hist_001, call 2 passes hist_001 to agent constructor."""
        assert conductor.history_id is None

        mock_agent1 = _make_mock_agent("hist_001")
        mock_agent2 = _make_mock_agent("hist_002")
        mock_capture1 = _make_mock_capture("first")
        mock_capture2 = _make_mock_capture("second")

        agents = iter([mock_agent1, mock_agent2])
        captures = iter([mock_capture1, mock_capture2])

        with patch("conductor.conductor.AutoSummarizingAgent", side_effect=lambda *a, **kw: next(agents)) as mock_bha, \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", side_effect=lambda: next(captures)), \
             patch.object(conductor, "_update_conversation"):

            await conductor.handle_message("first message")
            await conductor.handle_message("second message")

        # Call 1: no history_id (fresh start)
        call1_kwargs = mock_bha.call_args_list[0].kwargs
        assert "history_id" not in call1_kwargs

        # Call 2: history_id from call 1's result
        call2_kwargs = mock_bha.call_args_list[1].kwargs
        assert call2_kwargs["history_id"] == "hist_001"

    @pytest.mark.asyncio
    async def test_handle_message_passes_metadata(self, conductor):
        """Metadata from Discord (message_id, etc.) flows through."""
        mock_agent = _make_mock_agent("hist_001")
        mock_capture = _make_mock_capture("ok")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            metadata = {"discord_message_id": "12345", "discord_user_id": "67890"}
            result = await conductor.handle_message("test", metadata=metadata)

        assert result["metadata"]["discord_message_id"] == "12345"
        assert result["metadata"]["discord_user_id"] == "67890"

    @pytest.mark.asyncio
    async def test_handle_message_no_metadata_defaults_empty(self, conductor):
        """No metadata argument defaults to empty dict."""
        mock_agent = _make_mock_agent("hist_001")
        mock_capture = _make_mock_capture("ok")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            result = await conductor.handle_message("test")

        assert result["metadata"] == {}

    @pytest.mark.asyncio
    async def test_handle_message_error(self, conductor):
        """Exception during agent.run() returns error status."""
        mock_agent = _make_mock_agent()
        mock_agent.run.side_effect = RuntimeError("MiniMax API down")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=_make_mock_capture()):

            result = await conductor.handle_message("test")

        assert result["status"] == "error"
        assert "MiniMax API down" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_message_empty_response(self, conductor):
        """No AGENT_MESSAGE events returns empty string."""
        mock_agent = _make_mock_agent("hist_001")
        mock_capture = _make_mock_capture(None)  # No events

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            result = await conductor.handle_message("test")

        assert result["status"] == "success"
        assert result["response"] == ""

    @pytest.mark.asyncio
    async def test_handle_message_no_new_history_id(self, conductor):
        """When result has no history_id, history_id stays unchanged."""
        conductor.history_id = "old_hist"
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value={})  # No history_id in result
        mock_capture = _make_mock_capture("ok")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture):

            await conductor.handle_message("test")

        assert conductor.history_id == "old_hist"

    @pytest.mark.asyncio
    async def test_handle_message_calls_update_conversation(self, conductor):
        """When new history_id is returned, _update_conversation is called."""
        mock_agent = _make_mock_agent("hist_new")
        mock_capture = _make_mock_capture("ok")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation") as mock_update:

            await conductor.handle_message("test")

        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_skips_update_when_no_history(self, conductor):
        """When no new history_id, _update_conversation is NOT called."""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value={})
        mock_capture = _make_mock_capture("ok")

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation") as mock_update:

            await conductor.handle_message("test")

        mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_takes_last_agent_message(self, conductor):
        """When multiple AGENT_MESSAGE events, takes the last one."""
        mock_agent = _make_mock_agent("hist_001")
        mock_capture = MagicMock()
        mock_capture.get_events_by_type.return_value = [
            {"event_type": "AGENT_MESSAGE", "data": {"content": "thinking..."}},
            {"event_type": "AGENT_MESSAGE", "data": {"content": "Here's the real answer"}},
        ]

        with patch("conductor.conductor.AutoSummarizingAgent", return_value=mock_agent), \
             patch("conductor.conductor.UnifiedChat"), \
             patch("conductor.conductor.BackgroundEventCapture", return_value=mock_capture), \
             patch.object(conductor, "_update_conversation"):

            result = await conductor.handle_message("test")

        assert result["response"] == "Here's the real answer"


class TestConversationState:
    """Test conversation state persistence."""

    def test_new_conversation_clears_state(self, conductor):
        """new_conversation() resets history and conversation IDs."""
        conductor.history_id = "old_hist"
        conductor.conversation_id = "old_conv"
        conductor.new_conversation()
        assert conductor.history_id is None
        assert conductor.conversation_id is None

    def test_load_conversation_state_from_disk(self, conductor, tmp_path):
        """Conversation state can be loaded from disk."""
        state_file = tmp_path / "conductor_conversation.json"
        state_file.write_text(json.dumps({
            "conversation_id": "conv_123",
            "history_id": "hist_456",
        }))
        with patch("conductor.conductor.CONDUCTOR_CONVERSATION_STATE", state_file):
            connector = ClaudePConnector()
            state = StateMachine("test")
            c = Conductor(connector=connector, researcher_sdnac=None, state=state)

        assert c.conversation_id == "conv_123"
        assert c.history_id == "hist_456"

    def test_save_conversation_state(self, conductor, tmp_path):
        """Conversation state is saved to disk."""
        state_file = tmp_path / "conductor_conversation.json"
        with patch("conductor.conductor.CONDUCTOR_CONVERSATION_STATE", state_file):
            conductor.history_id = "hist_saved"
            conductor.conversation_id = "conv_saved"
            conductor._save_conversation_state()

        data = json.loads(state_file.read_text())
        assert data["history_id"] == "hist_saved"
        assert data["conversation_id"] == "conv_saved"

    def test_save_then_load_round_trip(self, conductor, tmp_path):
        """CRITICAL: Save state, create new Conductor, verify recovery."""
        state_file = tmp_path / "conductor_conversation.json"
        with patch("conductor.conductor.CONDUCTOR_CONVERSATION_STATE", state_file):
            conductor.history_id = "hist_round_trip"
            conductor.conversation_id = "conv_round_trip"
            conductor._save_conversation_state()

            connector = ClaudePConnector()
            state = StateMachine("test")
            c2 = Conductor(connector=connector, researcher_sdnac=None, state=state)

        assert c2.history_id == "hist_round_trip"
        assert c2.conversation_id == "conv_round_trip"

    def test_corrupted_state_file_starts_fresh(self, conductor, tmp_path):
        """Corrupted state file doesn't crash — starts fresh."""
        state_file = tmp_path / "conductor_conversation.json"
        state_file.write_text("NOT JSON")
        with patch("conductor.conductor.CONDUCTOR_CONVERSATION_STATE", state_file):
            connector = ClaudePConnector()
            state = StateMachine("test")
            c = Conductor(connector=connector, researcher_sdnac=None, state=state)

        assert c.history_id is None
        assert c.conversation_id is None


class TestUpdateConversation:
    """Test conversation tracking via ConversationManager."""

    @pytest.mark.asyncio
    async def test_update_conversation_starts_new(self, conductor):
        """First update calls start_chat."""
        conductor.history_id = "hist_001"
        conductor.conversation_id = None

        with patch("heaven_base.memory.conversations.start_chat", return_value={"conversation_id": "conv_new"}) as mock_start, \
             patch("heaven_base.memory.conversations.continue_chat") as mock_continue:

            conductor._update_conversation()

        mock_start.assert_called_once_with(
            title="Conductor — Isaac's Interface",
            first_history_id="hist_001",
            agent_name="conductor",
            tags=["conductor", "isaac"],
        )
        mock_continue.assert_not_called()
        assert conductor.conversation_id == "conv_new"

    @pytest.mark.asyncio
    async def test_update_conversation_continues_existing(self, conductor):
        """Subsequent updates call continue_chat."""
        conductor.history_id = "hist_002"
        conductor.conversation_id = "conv_existing"

        with patch("heaven_base.memory.conversations.start_chat") as mock_start, \
             patch("heaven_base.memory.conversations.continue_chat") as mock_continue:

            conductor._update_conversation()

        mock_start.assert_not_called()
        mock_continue.assert_called_once_with("conv_existing", "hist_002")

    @pytest.mark.asyncio
    async def test_update_conversation_noop_without_history(self, conductor):
        """No update if history_id is None."""
        conductor.history_id = None

        with patch("heaven_base.memory.conversations.start_chat") as mock_start, \
             patch("heaven_base.memory.conversations.continue_chat") as mock_continue:

            conductor._update_conversation()

        mock_start.assert_not_called()
        mock_continue.assert_not_called()


class TestBuildAgentConfig:
    """Test _build_agent_config helper."""

    def test_builds_correct_config(self):
        """Config has correct model, tools, and flags."""
        from heaven_base.tools.bash_tool import BashTool
        from heaven_base.tools.network_edit_tool import NetworkEditTool

        config = _build_agent_config("You are the Conductor.")
        assert config.name == "conductor"
        assert config.system_prompt == "You are the Conductor."
        assert BashTool in config.tools
        assert NetworkEditTool in config.tools
        assert config.model == "MiniMax-M2.5-highspeed"
        assert config.use_uni_api is False
        assert config.max_tokens == 8000
        assert config.extra_model_kwargs["anthropic_api_url"] == "https://api.minimax.io/anthropic"
        assert "carton" in config.mcp_servers
        assert "sophia" in config.mcp_servers
        assert "sancrev_treeshell" in config.mcp_servers
        assert config.mcp_servers["carton"]["transport"] == "stdio"
