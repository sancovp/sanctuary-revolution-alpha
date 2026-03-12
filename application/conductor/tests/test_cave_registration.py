"""Tests for Conductor CAVE registration."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from conductor.cave_registration import (
    ConductorConfig,
    register_conductor_in_cave,
    get_conductor_anatomy_access,
    get_conductor_system_prompt,
    _default_system_prompt,
    CONDUCTOR_CONFIG_PATH,
    CONDUCTOR_SYSTEM_PROMPT_PATH,
)


# === Mock CAVE objects ===

class MockAgentRegistration:
    """Mimics cave.core.models.AgentRegistration."""
    def __init__(self, agent_id, agent_type="paia", endpoint=None, capabilities=None, registered_at=None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.endpoint = endpoint
        self.capabilities = capabilities or []
        self.registered_at = registered_at

    def model_dump(self):
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
        }


@dataclass
class MockOrgan:
    name: str
    enabled: bool = True

    def status(self):
        return {"organ": self.name, "enabled": self.enabled}


@dataclass
class MockBlood:
    _payload: Dict[str, Any] = field(default_factory=dict)

    def status(self):
        return {"type": "blood", "carrying": list(self._payload.keys())}


class MockCAVEAgent:
    """Minimal mock of CAVEAgent with AgentRegistryMixin + AnatomyMixin behavior."""

    def __init__(self):
        self.agent_registry = {}
        self.heart = MockOrgan(name="main_heart")
        self.blood = MockBlood()
        self.ears = MockOrgan(name="ears")
        self.organs = {
            "heart": self.heart,
            "ears": self.ears,
        }
        self._events = []

    def register_agent(self, agent_id, **kwargs):
        reg = MockAgentRegistration(agent_id=agent_id, **kwargs)
        self.agent_registry[agent_id] = reg
        self._events.append(("agent_registered", {"agent_id": agent_id}))
        return reg

    def checkup(self, domain=None):
        return {"system": {}, "context": {}, "task": {}, "code": {}}

    def get_anatomy_status(self):
        return {
            "organs": {name: organ.status() for name, organ in self.organs.items()},
            "blood": self.blood.status(),
        }


# === Tests ===

class TestConductorConfig:
    def test_defaults(self):
        config = ConductorConfig()
        assert config.agent_id == "conductor"
        assert config.address == "local"
        assert config.carton_identity == "Conductor"
        assert config.grug_container == "repo-lord"

    def test_custom_values(self):
        config = ConductorConfig(agent_id="conductor-v2", cave_port=9090)
        assert config.agent_id == "conductor-v2"
        assert config.cave_port == 9090

    def test_to_dict_roundtrip(self):
        config = ConductorConfig(agent_id="test-conductor")
        d = config.to_dict()
        restored = ConductorConfig(**d)
        assert restored.agent_id == config.agent_id
        assert restored.carton_identity == config.carton_identity

    def test_save_and_load(self, tmp_path, monkeypatch):
        config_path = tmp_path / "conductor_config.json"
        monkeypatch.setattr(
            "conductor.cave_registration.CONDUCTOR_CONFIG_PATH", config_path
        )
        config = ConductorConfig(agent_id="save-test")
        config.save()
        assert config_path.exists()

        loaded = ConductorConfig.load()
        assert loaded.agent_id == "save-test"

    def test_load_returns_default_when_no_file(self, tmp_path, monkeypatch):
        config_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr(
            "conductor.cave_registration.CONDUCTOR_CONFIG_PATH", config_path
        )
        config = ConductorConfig.load()
        assert config.agent_id == "conductor"


class TestRegisterConductorInCave:
    def test_registers_in_agent_registry(self):
        cave = MockCAVEAgent()
        result = register_conductor_in_cave(cave)

        assert result["status"] == "registered"
        assert result["agent_id"] == "conductor"
        assert "conductor" in cave.agent_registry
        assert cave.agent_registry["conductor"].agent_type == "paia"

    def test_capabilities_listed(self):
        cave = MockCAVEAgent()
        result = register_conductor_in_cave(cave)

        caps = result["capabilities"]
        assert "bash" in caps
        assert "carton" in caps
        assert "sophia" in caps
        assert "call_gnosys" in caps
        assert "call_grug" in caps

    def test_custom_config(self):
        cave = MockCAVEAgent()
        config = ConductorConfig(agent_id="conductor-custom")
        result = register_conductor_in_cave(cave, config)

        assert result["agent_id"] == "conductor-custom"
        assert "conductor-custom" in cave.agent_registry

    def test_emits_event(self):
        cave = MockCAVEAgent()
        register_conductor_in_cave(cave)

        assert len(cave._events) == 1
        assert cave._events[0] == ("agent_registered", {"agent_id": "conductor"})

    def test_saves_config(self, tmp_path, monkeypatch):
        config_path = tmp_path / "conductor_config.json"
        monkeypatch.setattr(
            "conductor.cave_registration.CONDUCTOR_CONFIG_PATH", config_path
        )
        cave = MockCAVEAgent()
        register_conductor_in_cave(cave)

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["agent_id"] == "conductor"


class TestGetConductorAnatomyAccess:
    def test_returns_all_organs(self):
        cave = MockCAVEAgent()
        access = get_conductor_anatomy_access(cave)

        assert access["heart"] is cave.heart
        assert access["blood"] is cave.blood
        assert access["ears"] is cave.ears
        assert callable(access["checkup"])

    def test_returns_organs_dict(self):
        cave = MockCAVEAgent()
        access = get_conductor_anatomy_access(cave)

        assert "heart" in access["organs"]
        assert "ears" in access["organs"]

    def test_returns_status(self):
        cave = MockCAVEAgent()
        access = get_conductor_anatomy_access(cave)

        status = access["status"]
        assert "organs" in status
        assert "blood" in status


class TestGetConductorSystemPrompt:
    def test_generates_default_when_no_file(self, tmp_path, monkeypatch):
        prompt_path = tmp_path / "system_prompt.md"
        config = ConductorConfig(system_prompt_path=str(prompt_path))
        prompt = get_conductor_system_prompt(config)

        assert "Conductor" in prompt
        assert "BashTool" in prompt
        assert "Sophia" in prompt
        assert "GNOSYS" in prompt
        assert "CartON Identity" in prompt
        # Should have saved the file
        assert prompt_path.exists()

    def test_loads_existing_file(self, tmp_path):
        prompt_path = tmp_path / "system_prompt.md"
        prompt_path.write_text("Custom conductor prompt")
        config = ConductorConfig(system_prompt_path=str(prompt_path))
        prompt = get_conductor_system_prompt(config)

        assert prompt == "Custom conductor prompt"

    def test_default_prompt_includes_agent_id(self):
        config = ConductorConfig(agent_id="conductor-test")
        prompt = _default_system_prompt(config)
        assert "conductor-test" in prompt

    def test_default_prompt_includes_carton_identity(self):
        config = ConductorConfig(carton_identity="TestConductor")
        prompt = _default_system_prompt(config)
        assert "TestConductor" in prompt
        assert "observe_from_identity_pov" in prompt

    def test_default_prompt_documents_missing_features(self):
        config = ConductorConfig()
        prompt = _default_system_prompt(config)
        assert "Return to Design" in prompt
        assert "Shadow agent" in prompt
