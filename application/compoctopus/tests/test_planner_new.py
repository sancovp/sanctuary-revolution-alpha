"""Tests for the Planner agent."""

import pytest
import json
import sys
sys.path.insert(0, "/tmp/compoctopus")

from compoctopus.agents.planner.factory import make_planner
from compoctopus.agents.planner.hierarchy import (
    PlanHierarchy, Feature, Component, Deliverable, Task,
)

def test_make_planner():
    agent = make_planner(task="test task", workspace="/tmp/test")
    assert agent is not None
    assert agent.agent_name == "planner"
    from compoctopus.chain_ontology import Chain
    assert isinstance(agent.chain, Chain)

def test_chain_has_5_links():
    agent = make_planner(task="test task", workspace="/tmp/test")
    assert len(agent.chain.links) == 5

def test_chain_link_names():
    agent = make_planner(task="test task", workspace="/tmp/test")
    link_names = [link.name for link in agent.chain.links]
    assert link_names == ["project", "features", "components", "deliverables", "tasks"]

def test_has_system_prompt():
    agent = make_planner(task="test task", workspace="/tmp/test")
    assert agent.system_prompt is not None
    assert "Planner" in agent.system_prompt.render()

def test_plan_hierarchy_dataclass():
    task = Task(name="write_cli", description="Write cli.py with argparse")
    deliverable = Deliverable(name="cli_module", tasks=[task])
    component = Component(name="cli", deliverables=[deliverable])
    feature = Feature(name="cli_feature", components=[component])
    hierarchy = PlanHierarchy(project_name="test_project", features=[feature])
    assert hierarchy.project_name == "test_project"
    assert len(hierarchy.features) == 1

def test_hierarchy_to_json():
    task = Task(name="test_task", description="Do something")
    deliverable = Deliverable(name="test_deliverable", tasks=[task])
    component = Component(name="test_component", deliverables=[deliverable])
    feature = Feature(name="test_feature", components=[component])
    hierarchy = PlanHierarchy(project_name="my_project", features=[feature])
    json_str = hierarchy.to_json()
    data = json.loads(json_str)
    assert data["project_name"] == "my_project"

def test_hierarchy_from_json():
    task = Task(name="roundtrip_task", description="Test roundtrip")
    deliverable = Deliverable(name="roundtrip_deliverable", tasks=[task])
    component = Component(name="roundtrip_component", deliverables=[deliverable])
    feature = Feature(name="roundtrip_feature", components=[component])
    original = PlanHierarchy(project_name="roundtrip_project", features=[feature])
    json_str = original.to_json()
    restored = PlanHierarchy.from_json(json_str)
    assert restored.project_name == original.project_name

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
