"""Tests for GIINT Bridge — idea → project → agents."""

import pytest

from compoctopus import (
    # Pipeline
    CompilerPipeline,
    CompilationContext,
    # Arms
    ChainCompiler,
    AgentConfigCompiler,
    MCPCompiler,
    SkillCompiler,
    SystemPromptCompiler,
    InputPromptCompiler,
    # Types
    TaskSpec,
    FeatureType,
    TrustLevel,
    PermissionMode,
    CompiledAgent,
    # GIINT Bridge
    GIINTProject,
    GIINTFeature,
    GIINTComponent,
    GIINTDeliverable,
    GIINTTask,
    TaskWaterfall,
    ProjectCompiler,
    ProjectCompilationResult,
)
from compoctopus.giint_bridge import AssigneeType, GIINTStatus


def make_full_pipeline() -> CompilerPipeline:
    return CompilerPipeline(arms=[
        ChainCompiler(),
        AgentConfigCompiler(),
        MCPCompiler(),
        SkillCompiler(),
        SystemPromptCompiler(),
        InputPromptCompiler(),
    ])


class TestTaskWaterfall:
    """Layer 1: GIINT Task → Compoctopus TaskSpec."""

    def test_basic_waterfall(self):
        """Simple task → TaskSpec with description from hierarchy."""
        project = GIINTProject(project_id="sanctuary")
        feature = GIINTFeature(name="auth", description="Authentication system")
        component = GIINTComponent(name="oauth", description="OAuth2 provider")
        deliverable = GIINTDeliverable(name="login", description="Login flow")
        task = GIINTTask(task_id="impl", description="Implement OAuth2 login")

        spec = TaskWaterfall.task_to_taskspec(
            project, feature, component, deliverable, task
        )

        assert "Implement OAuth2 login" in spec.description
        assert "Login flow" in spec.description
        assert spec.parent_task == "sanctuary/auth/oauth/login"

    def test_domain_hints_from_component(self):
        """Component domain hints → TaskSpec domain hints."""
        project = GIINTProject(project_id="kg")
        feature = GIINTFeature(name="query")
        component = GIINTComponent(
            name="core",
            domain_hints=["carton", "chroma"],
        )
        deliverable = GIINTDeliverable(name="search")
        task = GIINTTask(task_id="impl", description="Build search")

        spec = TaskWaterfall.task_to_taskspec(
            project, feature, component, deliverable, task
        )

        assert "carton" in spec.domain_hints
        assert "chroma" in spec.domain_hints

    def test_context_deps_merge_with_domain_hints(self):
        """Task context_deps merge into domain_hints."""
        project = GIINTProject(project_id="p")
        feature = GIINTFeature(name="f")
        component = GIINTComponent(name="c", domain_hints=["carton"])
        deliverable = GIINTDeliverable(name="d")
        task = GIINTTask(
            task_id="t",
            description="do stuff",
            context_deps=["filesystem", "docker"],
        )

        spec = TaskWaterfall.task_to_taskspec(
            project, feature, component, deliverable, task
        )

        assert "carton" in spec.domain_hints
        assert "filesystem" in spec.domain_hints
        assert "docker" in spec.domain_hints

    def test_human_assignee_becomes_observer(self):
        """Human tasks → OBSERVER trust (watch, don't act)."""
        project = GIINTProject(project_id="p")
        feature = GIINTFeature(name="f")
        component = GIINTComponent(name="c")
        deliverable = GIINTDeliverable(name="d")
        task = GIINTTask(task_id="t", description="Review PR", assignee=AssigneeType.HUMAN)

        spec = TaskWaterfall.task_to_taskspec(
            project, feature, component, deliverable, task
        )

        assert spec.trust_level == TrustLevel.OBSERVER

    def test_blocked_task_has_constraint(self):
        """Blocked tasks carry the blocker as a constraint."""
        project = GIINTProject(project_id="p")
        feature = GIINTFeature(name="f")
        component = GIINTComponent(name="c")
        deliverable = GIINTDeliverable(name="d")
        task = GIINTTask(
            task_id="t", description="Wait for API",
            is_blocked=True, blocked_description="API not ready",
        )

        spec = TaskWaterfall.task_to_taskspec(
            project, feature, component, deliverable, task
        )

        assert spec.constraints.get("blocked") == "API not ready"

    def test_feature_type_inference_tool(self):
        """Component with 'tool' domain hint → TOOL feature type."""
        project = GIINTProject(project_id="p")
        feature = GIINTFeature(name="f")
        component = GIINTComponent(name="c", domain_hints=["tool", "mcp"])
        deliverable = GIINTDeliverable(name="d")
        task = GIINTTask(task_id="t", description="make it")

        spec = TaskWaterfall.task_to_taskspec(
            project, feature, component, deliverable, task
        )

        assert spec.feature_type == FeatureType.TOOL

    def test_deliverable_to_taskspecs_skips_done(self):
        """Done and blocked tasks are not compiled."""
        project = GIINTProject(project_id="p")
        feature = GIINTFeature(name="f")
        component = GIINTComponent(name="c")
        deliverable = GIINTDeliverable(
            name="d",
            tasks={
                "done_task": GIINTTask(task_id="done_task", description="a", status=GIINTStatus.DONE),
                "blocked_task": GIINTTask(task_id="blocked_task", description="b", status=GIINTStatus.BLOCKED),
                "ready_task": GIINTTask(task_id="ready_task", description="c", status=GIINTStatus.READY),
            },
        )

        specs = TaskWaterfall.deliverable_to_taskspecs(
            project, feature, component, deliverable
        )

        assert len(specs) == 1
        assert "c" in specs[0].description


class TestProjectCompiler:
    """Layer 2: idea → project hierarchy → compiled agents."""

    def test_adhoc_idea(self):
        """Simple idea with no registered project → new ad-hoc project."""
        compiler = ProjectCompiler(pipeline=make_full_pipeline())
        result = compiler.compile_idea("Build a knowledge graph query agent")

        assert result.tasks_compiled == 1
        assert len(result.agents) == 1
        assert isinstance(result.agents[0], CompiledAgent)
        print(result)

    def test_routed_to_existing_project(self):
        """Idea routed to existing project."""
        project = GIINTProject(
            project_id="sanctuary",
            project_dir="/tmp/sanctuary",
            default_trust=TrustLevel.BUILDER,
        )
        compiler = ProjectCompiler(pipeline=make_full_pipeline())
        compiler.register_project(project)

        result = compiler.compile_idea(
            "Add carton integration",
            target_project="sanctuary",
        )

        assert result.project.project_id == "sanctuary"
        assert result.tasks_compiled == 1
        assert result.task_specs[0].constraints.get("project_dir") == "/tmp/sanctuary"

    def test_multi_task_deliverable(self):
        """Deliverable with multiple tasks → multiple agents."""
        project = GIINTProject(project_id="multi")
        feature = GIINTFeature(
            name="search",
            components={
                "indexer": GIINTComponent(
                    name="indexer",
                    domain_hints=["chroma"],
                    deliverables={
                        "impl": GIINTDeliverable(
                            name="impl",
                            tasks={
                                "schema": GIINTTask(task_id="schema", description="Design schema"),
                                "index": GIINTTask(task_id="index", description="Build indexer"),
                                "test": GIINTTask(task_id="test", description="Test indexer"),
                            },
                        ),
                    },
                ),
            },
        )
        project.features["search"] = feature

        compiler = ProjectCompiler(pipeline=make_full_pipeline())
        compiler.register_project(project)

        # Compile the existing project's feature
        result = ProjectCompilationResult(
            idea="Implement search",
            project=project,
            feature=feature,
        )
        for comp in feature.components.values():
            for deliverable in comp.deliverables.values():
                specs = TaskWaterfall.deliverable_to_taskspecs(
                    project, feature, comp, deliverable
                )
                for spec in specs:
                    ctx = CompilationContext(task_spec=spec)
                    compiler.pipeline.compile(ctx)
                    agent = ctx.freeze()
                    result.agents.append(agent)
                    result.tasks_compiled += 1

        assert result.tasks_compiled == 3
        assert len(result.agents) == 3
        # Each agent should have chroma in domain hints
        for agent in result.agents:
            assert "chroma" in agent.task_spec.domain_hints


class TestEndToEnd:
    """Full flow: idea → project → agents → system prompts."""

    def test_idea_to_system_prompt(self):
        """An idea flows all the way to a system prompt with sections."""
        compiler = ProjectCompiler(pipeline=make_full_pipeline())
        result = compiler.compile_idea("Query knowledge graph for patterns")

        agent = result.agents[0]

        # Check the full chain propagated
        assert agent.chain_plan is not None
        assert agent.agent_profile is not None
        assert agent.system_prompt is not None

        # System prompt should mention the idea
        identity = next(s for s in agent.system_prompt.sections if s.tag == "IDENTITY")
        assert "knowledge graph" in identity.content.lower() or "pattern" in identity.content.lower()

        # Input prompt should have the goal
        assert "knowledge graph" in agent.input_prompt.goal.lower()

    def test_executor_lockdown_through_project(self):
        """EXECUTOR trust from project → locked-down agent."""
        project = GIINTProject(
            project_id="prod",
            default_trust=TrustLevel.EXECUTOR,
        )
        compiler = ProjectCompiler(pipeline=make_full_pipeline())
        compiler.register_project(project)

        result = compiler.compile_idea("Run health check", target_project="prod")
        agent = result.agents[0]

        assert agent.agent_profile.permission_mode == PermissionMode.RESTRICTED
        assert agent.agent_profile.max_turns <= 5
