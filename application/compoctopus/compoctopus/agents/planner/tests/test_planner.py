"""Tests for the Planner agent."""

import pytest
import json
import sys
import os

# Add workspace to path  
sys.path.insert(0, '/tmp/compoctopus_planner_q7u8tx66')
# Also add compoctopus core
sys.path.insert(0, '/tmp/compoctopus')

# Import directly from local modules
from planner.factory import make_planner
from planner.hierarchy import (
    PlanHierarchy,
    Feature,
    Component,
    Deliverable,
    Task,
)


class TestPlannerFactory:
    """Structural tests for the Planner factory."""
    
    def test_make_planner(self):
        """Verify agent creation, name, chain type."""
        agent = make_planner("Build a web app", "/tmp/test_workspace")
        assert agent is not None
        assert agent.agent_name == "planner"
        assert agent.chain is not None
        # Chain type should be Chain (not EvalChain)
        assert agent.chain.__class__.__name__ == "Chain"
    
    def test_chain_has_5_links(self):
        """Verify 5 SDNACs in the chain."""
        agent = make_planner("Build a web app", "/tmp/test_workspace")
        assert hasattr(agent.chain, "links")
        assert len(agent.chain.links) == 5
    
    def test_chain_link_names(self):
        """Verify link names are project, features, components, deliverables, tasks."""
        agent = make_planner("Build a web app", "/tmp/test_workspace")
        expected_names = ["project", "features", "components", "deliverables", "tasks"]
        link_names = [link.name for link in agent.chain.links]
        assert link_names == expected_names
    
    def test_has_system_prompt(self):
        """Verify system prompt contains Planner."""
        agent = make_planner("Build a web app", "/tmp/test_workspace")
        assert agent.system_prompt is not None
        prompt_text = agent.system_prompt.render()
        assert "Planner" in prompt_text


class TestPlanHierarchy:
    """Behavioral tests for PlanHierarchy dataclass."""
    
    def test_plan_hierarchy_dataclass(self):
        """PlanHierarchy creates, nests correctly."""
        # Create a task
        task = Task(name="implement_login", description="Add login functionality")
        
        # Create a deliverable with tasks
        deliverable = Deliverable(
            name="auth_system",
            tasks=[task],
        )
        
        # Create a component with deliverables
        component = Component(
            name="authentication",
            deliverables=[deliverable],
        )
        
        # Create a feature with components
        feature = Feature(
            name="user_management",
            components=[component],
        )
        
        # Create the hierarchy
        hierarchy = PlanHierarchy(
            project_name="my_webapp",
            features=[feature],
        )
        
        assert hierarchy.project_name == "my_webapp"
        assert len(hierarchy.features) == 1
        assert hierarchy.features[0].name == "user_management"
        assert len(hierarchy.features[0].components) == 1
        assert hierarchy.features[0].components[0].name == "authentication"
        assert len(hierarchy.features[0].components[0].deliverables) == 1
        assert hierarchy.features[0].components[0].deliverables[0].name == "auth_system"
        assert len(hierarchy.features[0].components[0].deliverables[0].tasks) == 1
        assert hierarchy.features[0].components[0].deliverables[0].tasks[0].name == "implement_login"
    
    def test_hierarchy_to_json(self):
        """Serializes to JSON."""
        task = Task(name="test_feature", description="Write tests")
        deliverable = Deliverable(name="tests", tasks=[task])
        component = Component(name="testing", deliverables=[deliverable])
        feature = Feature(name="quality", components=[component])
        hierarchy = PlanHierarchy(project_name="project_x", features=[feature])
        
        json_str = hierarchy.to_json()
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert data["project_name"] == "project_x"
        assert len(data["features"]) == 1
        assert data["features"][0]["name"] == "quality"
    
    def test_hierarchy_from_json(self):
        """Deserializes from JSON roundtrip."""
        original = {
            "project_name": "test_project",
            "features": [
                {
                    "name": "api",
                    "components": [
                        {
                            "name": "endpoints",
                            "deliverables": [
                                {
                                    "name": "user_endpoint",
                                    "tasks": [
                                        {"name": "get_user", "description": "Get user by ID"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        json_str = json.dumps(original)
        hierarchy = PlanHierarchy.from_json(json_str)
        
        assert hierarchy.project_name == "test_project"
        assert len(hierarchy.features) == 1
        assert hierarchy.features[0].name == "api"
        assert hierarchy.features[0].components[0].name == "endpoints"
        assert hierarchy.features[0].components[0].deliverables[0].name == "user_endpoint"
        assert hierarchy.features[0].components[0].deliverables[0].tasks[0].name == "get_user"
        assert hierarchy.features[0].components[0].deliverables[0].tasks[0].description == "Get user by ID"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
