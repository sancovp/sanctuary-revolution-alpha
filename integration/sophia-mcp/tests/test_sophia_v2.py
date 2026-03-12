"""Sophia V2 unit tests — verify DUOChain migration, mode detection, history_id wiring."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from sophia_mcp.daemon import (
    _build_sdnac_from_config,
    construct_andor_execute_chain,
    SOPHIA_PLAN_SYSTEM,
    OVP_SYSTEM,
)


# === Mock SDNA types ===

@dataclass
class MockSDNACConfig:
    name: str = "test"
    ariadne_elements: list = field(default_factory=list)
    hermes_config: dict = field(default_factory=lambda: {
        "name": "test", "goal": "test goal", "backend": "heaven",
    })


@dataclass
class MockSDNAFlowConfig:
    name: str = "test_flow"
    sdnacs: list = field(default_factory=list)

    def model_dump_json(self, indent=2):
        import json
        return json.dumps({"name": self.name, "sdnacs": []}, indent=indent)

    def model_dump(self):
        return {"name": self.name, "sdnacs": []}


@dataclass
class MockSDNAResult:
    status: MagicMock = field(default_factory=lambda: MagicMock(value="success"))
    context: Dict[str, Any] = field(default_factory=lambda: {"text": "done", "history_id": "h123"})
    error: Optional[str] = None


@dataclass
class MockDUOChainResult:
    status: MagicMock = field(default_factory=lambda: MagicMock(value="success"))
    context: Dict[str, Any] = field(default_factory=lambda: {"text": "duo done", "history_id": "h456"})
    inner_iterations: int = 2
    outer_cycles: int = 1
    error: Optional[str] = None
    ovp_feedback: Optional[str] = "APPROVED"


# === Tests ===

def test_plan_system_prompt_is_planner():
    """SOPHIA_PLAN_SYSTEM should be a planner, not a router."""
    assert "Build Planner" in SOPHIA_PLAN_SYSTEM
    assert "build_plan" in SOPHIA_PLAN_SYSTEM
    assert "build_mode" in SOPHIA_PLAN_SYSTEM
    assert "Wisdom Router" not in SOPHIA_PLAN_SYSTEM
    assert "routing" not in SOPHIA_PLAN_SYSTEM.split("Output JSON:")[1]


def test_ovp_system_has_approval_fields():
    """OVP_SYSTEM should instruct agent to output ovp_approved and ovp_feedback."""
    assert "ovp_approved" in OVP_SYSTEM
    assert "ovp_feedback" in OVP_SYSTEM


@pytest.mark.asyncio
async def test_mode_auto_detect_single():
    """1 SDNAC should auto-detect as single mode."""
    mock_sdnac = MagicMock()
    mock_sdnac.execute = AsyncMock(return_value=MockSDNAResult())

    config = MockSDNAFlowConfig(sdnacs=[MockSDNACConfig()])

    with patch("sophia_mcp.daemon._build_sdnac_from_config", return_value=mock_sdnac):
        result = await construct_andor_execute_chain(
            chain_config=config, execute=True, construct=False,
        )

    assert result["execution"]["status"] == "success"
    mock_sdnac.execute.assert_called_once()


@pytest.mark.asyncio
async def test_mode_auto_detect_duo():
    """2 SDNACs should auto-detect as duo mode."""
    mock_duo = MagicMock()
    mock_duo.execute = AsyncMock(return_value=MockDUOChainResult())

    config = MockSDNAFlowConfig(sdnacs=[MockSDNACConfig(name="a"), MockSDNACConfig(name="p")])

    with patch("sophia_mcp.daemon._build_sdnac_from_config", return_value=MagicMock()), \
         patch("sophia_mcp.daemon.construct_andor_execute_chain.__module__", "sophia_mcp.daemon"), \
         patch("sdna.AutoDUOAgent", return_value=mock_duo), \
         patch("sdna.default_config", return_value=MagicMock()), \
         patch("sdna.sdnac", return_value=MagicMock()), \
         patch("sdna.ariadne", return_value=MagicMock()):
        result = await construct_andor_execute_chain(
            chain_config=config, execute=True, construct=False,
        )

    assert result["execution"]["status"] == "success"
    assert result["execution"]["outer_cycles"] == 1


@pytest.mark.asyncio
async def test_mode_auto_detect_flow():
    """3+ SDNACs should auto-detect as flow mode."""
    mock_flow = MagicMock()
    mock_flow.execute = AsyncMock(return_value=MockSDNAResult())

    config = MockSDNAFlowConfig(sdnacs=[
        MockSDNACConfig(name="a"), MockSDNACConfig(name="b"), MockSDNACConfig(name="c"),
    ])

    with patch("sophia_mcp.daemon._build_sdnac_from_config", return_value=MagicMock()), \
         patch("sdna.sdna_flow", return_value=mock_flow):
        result = await construct_andor_execute_chain(
            chain_config=config, execute=True, construct=False,
        )

    assert result["execution"]["status"] == "success"
    mock_flow.execute.assert_called_once()


@pytest.mark.asyncio
async def test_history_id_flows_to_execution():
    """history_id should be passed through to execution results."""
    mock_sdnac = MagicMock()
    mock_sdnac.execute = AsyncMock(return_value=MockSDNAResult())

    config = MockSDNAFlowConfig(sdnacs=[MockSDNACConfig()])

    with patch("sophia_mcp.daemon._build_sdnac_from_config", return_value=mock_sdnac) as mock_build:
        result = await construct_andor_execute_chain(
            chain_config=config, execute=True, construct=False,
            history_id="prev_h123",
        )

    mock_build.assert_called_once_with(config.sdnacs[0], history_id="prev_h123")
    assert result["execution"]["history_id"] == "h123"


def test_no_duo_agent_v2_import():
    """duo_agent_v2 should NOT be imported anywhere in daemon.py."""
    import inspect
    from sophia_mcp import daemon
    source = inspect.getsource(daemon)
    assert "duo_agent_v2" not in source
