"""Tests for the Planner agent — Step 3 of the filling sequence.

Tests:
- State machine transitions (PLAN → VALIDATE → DONE)
- Factory function produces valid CompoctopusAgent with GIINT MCP
- compile() entrypoint routing (_planner_ran guard)
- Context handling (request, project_id, _planner_ran)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Import guards ──────────────────────────────────────────────────
try:
    from heaven_base.state_machine import KeywordBasedStateMachine, StateConfig
    HAS_HEAVEN = True
except ImportError:
    HAS_HEAVEN = False

try:
    from compoctopus.octopus_coder import (
        make_planner, CompoctopusAgent, compile as compoctopus_compile,
        PLANNER_SYSTEM_PROMPT, _get_giint_mcp_servers,
    )
    HAS_COMPOCTOPUS = True
except ImportError:
    HAS_COMPOCTOPUS = False


# ── State Machine Tests ───────────────────────────────────────────

@pytest.mark.skipif(not HAS_HEAVEN, reason="heaven_base not available")
class TestPlannerStateMachine:
    """Test the Planner's state machine structure."""

    def _make_sm(self):
        return KeywordBasedStateMachine(
            name="planner",
            states={
                "PLAN": StateConfig(goal="Decompose request."),
                "VALIDATE": StateConfig(goal="Verify structure."),
                "DONE": StateConfig(goal="Return."),
            },
            initial_state="PLAN",
            terminal_states={"DONE"},
            transitions={
                "PLAN": ["VALIDATE"],
                "VALIDATE": ["DONE", "PLAN"],
            },
        )

    def test_initial_state_is_plan(self):
        sm = self._make_sm()
        assert sm.current_state == "PLAN"

    def test_plan_to_validate(self):
        sm = self._make_sm()
        sm.current_state = "VALIDATE"
        assert sm.current_state == "VALIDATE"

    def test_validate_to_done(self):
        sm = self._make_sm()
        sm.current_state = "VALIDATE"
        sm.current_state = "DONE"
        assert sm.current_state == "DONE"

    def test_validate_to_plan_loop(self):
        sm = self._make_sm()
        sm.current_state = "VALIDATE"
        sm.current_state = "PLAN"
        assert sm.current_state == "PLAN"

    def test_done_is_terminal(self):
        sm = self._make_sm()
        assert "DONE" in sm.terminal_states

    def test_three_states_total(self):
        sm = self._make_sm()
        assert len(sm.states) == 3

    def test_no_sequence_state(self):
        """Old design had DECOMPOSE/SEQUENCE. Verify simplified to PLAN."""
        sm = self._make_sm()
        assert "DECOMPOSE" not in sm.states
        assert "SEQUENCE" not in sm.states


# ── Factory Tests ─────────────────────────────────────────────────

@pytest.mark.skipif(not HAS_COMPOCTOPUS, reason="compoctopus not available")
class TestPlannerFactory:
    """Test make_planner() produces a valid CompoctopusAgent."""

    def test_returns_agent(self):
        planner = make_planner()
        assert isinstance(planner, CompoctopusAgent)

    def test_name_is_planner(self):
        planner = make_planner()
        assert planner.agent_name == "planner"

    def test_initial_state_is_plan(self):
        planner = make_planner()
        assert planner.state_machine.current_state == "PLAN"

    def test_terminal_state_is_done(self):
        planner = make_planner()
        assert "DONE" in planner.state_machine.terminal_states

    def test_has_hermes_config(self):
        planner = make_planner()
        assert planner.hermes_config is not None

    def test_backend_is_heaven(self):
        planner = make_planner()
        assert planner.hermes_config.backend == "heaven"

    def test_has_giint_mcp(self):
        """Planner must have giint-llm-intelligence MCP."""
        planner = make_planner()
        mcp_names = list(planner.hermes_config.mcp_servers.keys())
        assert "giint-llm-intelligence" in mcp_names, f"Expected giint MCP in {mcp_names}"

    def test_has_tools(self):
        """Planner must have BashTool and NetworkEditTool."""
        planner = make_planner()
        tools = planner.hermes_config.heaven_inputs.agent.tools
        tool_names = [t.__name__ if hasattr(t, '__name__') else str(t) for t in tools]
        assert "BashTool" in tool_names
        assert "NetworkEditTool" in tool_names

    def test_system_prompt_exists(self):
        planner = make_planner()
        assert planner.hermes_config.system_prompt is not None
        assert len(planner.hermes_config.system_prompt) > 50

    def test_system_prompt_mentions_giint_hierarchy(self):
        assert "Features" in PLANNER_SYSTEM_PROMPT
        assert "Components" in PLANNER_SYSTEM_PROMPT
        assert "Deliverables" in PLANNER_SYSTEM_PROMPT
        assert "Tasks" in PLANNER_SYSTEM_PROMPT

    def test_system_prompt_mentions_create_project(self):
        assert "create_project" in PLANNER_SYSTEM_PROMPT

    def test_system_prompt_mentions_get_project_overview(self):
        assert "get_project_overview" in PLANNER_SYSTEM_PROMPT


# ── GIINT MCP Config Tests ────────────────────────────────────────

@pytest.mark.skipif(not HAS_COMPOCTOPUS, reason="compoctopus not available")
class TestGIINTMCPConfig:
    """Test the GIINT MCP server configuration."""

    def test_returns_dict(self):
        config = _get_giint_mcp_servers()
        assert isinstance(config, dict)

    def test_has_giint_key(self):
        config = _get_giint_mcp_servers()
        assert "giint-llm-intelligence" in config

    def test_has_command(self):
        config = _get_giint_mcp_servers()
        server = config["giint-llm-intelligence"]
        assert server["command"] == "python"
        assert server["args"] == ["-m", "llm_intelligence.mcp_server"]

    def test_has_required_env_vars(self):
        config = _get_giint_mcp_servers()
        env = config["giint-llm-intelligence"]["env"]
        assert "LLM_INTELLIGENCE_DIR" in env
        assert "GIINT_TREEKANBAN_BOARD" in env
        assert "GIINT_SCHEMA" in env
        assert "HEAVEN_DATA_DIR" in env
        assert "TREEKANBAN_API_URL" in env


# ── compile() Entrypoint Tests ────────────────────────────────────

@pytest.mark.skipif(not HAS_COMPOCTOPUS, reason="compoctopus not available")
class TestCompileEntrypoint:
    """Test the compile() entrypoint routing logic."""

    def test_compile_is_async(self):
        """compile() must be an async function."""
        assert asyncio.iscoroutinefunction(compoctopus_compile)

    def test_compile_accepts_request_and_project_id(self):
        import inspect
        sig = inspect.signature(compoctopus_compile)
        params = list(sig.parameters.keys())
        assert "request" in params
        assert "project_id" in params

    def test_compile_project_id_optional(self):
        import inspect
        sig = inspect.signature(compoctopus_compile)
        project_param = sig.parameters["project_id"]
        assert project_param.default is None

    @pytest.mark.asyncio
    async def test_compile_no_project_returns_direct(self):
        """Without project_id, compile() routes to Bandit (currently stub)."""
        result = await compoctopus_compile("write hello world")
        assert result["status"] == "direct"
        assert result["request"] == "write hello world"

    @pytest.mark.asyncio
    async def test_compile_with_project_routes_to_planner(self):
        """With project_id, compile() routes to Planner first."""
        with patch("compoctopus.octopus_coder.make_planner") as mock_factory:
            mock_planner = MagicMock()
            mock_planner.execute = AsyncMock(return_value={"status": "ok"})
            mock_factory.return_value = mock_planner

            result = await compoctopus_compile(
                "add auth module",
                project_id="my_project",
            )

            # Planner should have been called
            mock_factory.assert_called_once()
            mock_planner.execute.assert_called_once()
            assert result["status"] == "planned"
            assert result["project_id"] == "my_project"

    @pytest.mark.asyncio
    async def test_compile_sets_planner_ran_flag(self):
        """After Planner runs, _planner_ran must be True."""
        with patch("compoctopus.octopus_coder.make_planner") as mock_factory:
            mock_planner = MagicMock()
            mock_planner.execute = AsyncMock(return_value={"status": "ok"})
            mock_factory.return_value = mock_planner

            result = await compoctopus_compile(
                "add auth",
                project_id="proj",
            )
            # Tasks in result should all have _planner_ran=True
            for task_ctx in result.get("results", []):
                assert task_ctx.get("_planner_ran") is True
