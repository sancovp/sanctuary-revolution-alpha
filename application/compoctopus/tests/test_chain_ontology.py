"""Tests for Universal Chain Ontology — Link/Chain homoiconic primitives."""

import asyncio
import pytest

from compoctopus.chain_ontology import (
    Link, Chain, EvalChain, ConfigLink, LinkConfig,
    LinkResult, LinkStatus,
)
from compoctopus import (
    CompilerPipeline, CompilationContext,
    ChainCompiler, AgentConfigCompiler, MCPCompiler,
    SkillCompiler, SystemPromptCompiler, InputPromptCompiler,
    TaskSpec, FeatureType, TrustLevel,
)


# Helper: concrete Link for testing
class EchoLink(Link):
    def __init__(self, link_name: str, key: str = "echo", value: str = "hello"):
        self._name = link_name
        self.key = key
        self.value = value

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context=None):
        ctx = dict(context) if context else {}
        ctx[self.key] = self.value
        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)


class FailLink(Link):
    @property
    def name(self): return "fail"
    async def execute(self, context=None):
        return LinkResult(status=LinkStatus.ERROR, context=context or {}, error="boom")


class ApproveLink(Link):
    def __init__(self, approve_on_cycle: int = 1):
        self.approve_on = approve_on_cycle
    @property
    def name(self): return "approver"
    async def execute(self, context=None):
        ctx = dict(context) if context else {}
        ctx["approved"] = ctx.get("cycle", 0) >= self.approve_on
        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestLink:
    def test_link_is_abstract(self):
        with pytest.raises(TypeError):
            Link()

    def test_echo_link(self):
        link = EchoLink("test", key="msg", value="hi")
        result = run(link.execute())
        assert result.status == LinkStatus.SUCCESS
        assert result.context["msg"] == "hi"


class TestChain:
    def test_chain_is_link(self):
        """Homoiconic: Chain IS a Link."""
        chain = Chain("test")
        assert isinstance(chain, Link)

    def test_empty_chain(self):
        result = run(Chain("empty").execute())
        assert result.status == LinkStatus.SUCCESS

    def test_sequential_execution(self):
        chain = Chain("seq", [
            EchoLink("a", "x", "1"),
            EchoLink("b", "y", "2"),
            EchoLink("c", "z", "3"),
        ])
        result = run(chain.execute())
        assert result.status == LinkStatus.SUCCESS
        assert result.context == {"x": "1", "y": "2", "z": "3"}

    def test_stops_on_failure(self):
        chain = Chain("fail_chain", [
            EchoLink("a", "x", "1"),
            FailLink(),
            EchoLink("c", "z", "3"),  # should not execute
        ])
        result = run(chain.execute())
        assert result.status == LinkStatus.ERROR
        assert "x" in result.context
        assert "z" not in result.context
        assert result.resume_path == [1]

    def test_nested_chains(self):
        """Homoiconic composition: Chain in Chain."""
        inner = Chain("inner", [
            EchoLink("i1", "a", "1"),
            EchoLink("i2", "b", "2"),
        ])
        outer = Chain("outer", [
            EchoLink("pre", "pre", "yes"),
            inner,  # Chain IS a Link
            EchoLink("post", "post", "yes"),
        ])
        result = run(outer.execute())
        assert result.status == LinkStatus.SUCCESS
        assert result.context["pre"] == "yes"
        assert result.context["a"] == "1"
        assert result.context["b"] == "2"
        assert result.context["post"] == "yes"

    def test_fluent_add(self):
        chain = Chain("fluent").add(EchoLink("a", "x", "1")).add(EchoLink("b", "y", "2"))
        assert len(chain) == 2

    def test_indexing(self):
        links = [EchoLink("a"), EchoLink("b")]
        chain = Chain("idx", links)
        assert chain[0].name == "a"
        assert chain[1].name == "b"


class TestEvalChain:
    def test_single_pass_no_evaluator(self):
        chain = EvalChain("no_eval", [EchoLink("a", "x", "1")])
        result = run(chain.execute())
        assert result.status == LinkStatus.SUCCESS

    def test_approved_first_cycle(self):
        chain = EvalChain(
            "eval_ok",
            [EchoLink("a", "x", "1")],
            evaluator=ApproveLink(approve_on_cycle=1),
        )
        result = run(chain.execute())
        assert result.status == LinkStatus.SUCCESS
        assert result.context["approved"]

    def test_approved_second_cycle(self):
        chain = EvalChain(
            "eval_retry",
            [EchoLink("a", "x", "1")],
            evaluator=ApproveLink(approve_on_cycle=2),
            max_cycles=3,
        )
        result = run(chain.execute())
        assert result.status == LinkStatus.SUCCESS
        assert result.context["cycle"] == 2

    def test_max_cycles_reached(self):
        chain = EvalChain(
            "eval_max",
            [EchoLink("a", "x", "1")],
            evaluator=ApproveLink(approve_on_cycle=99),
            max_cycles=3,
        )
        result = run(chain.execute())
        assert result.status == LinkStatus.BLOCKED
        assert "Max cycles" in result.error


class TestConfigLink:
    def test_from_config(self):
        config = LinkConfig(name="test", goal="do stuff", model="claude-sonnet")
        link = ConfigLink(config)
        assert link.name == "test"
        result = run(link.execute({"input": "data"}))
        assert result.status == LinkStatus.SUCCESS
        assert result.context["_link_config"] == config


class TestCompiledAgentToLink:
    """CompiledAgent → Link/Chain bridge."""

    def _compile(self, desc: str, **kw):
        pipeline = CompilerPipeline(arms=[
            ChainCompiler(), AgentConfigCompiler(), MCPCompiler(),
            SkillCompiler(), SystemPromptCompiler(), InputPromptCompiler(),
        ])
        ctx = CompilationContext(task_spec=TaskSpec(description=desc, **kw))
        pipeline.compile(ctx)
        return ctx.freeze()

    def test_to_link_config(self):
        agent = self._compile("Query the KG")
        config = agent.to_link_config()
        assert config.name
        assert "KG" in config.goal or "knowledge" in config.goal.lower()
        assert config.system_prompt  # non-empty
        assert config.model

    def test_to_link(self):
        agent = self._compile("Build a tool", feature_type=FeatureType.TOOL)
        link = agent.to_link()
        assert isinstance(link, Link)
        assert isinstance(link, ConfigLink)
        assert link.config.temperature == 0.3
        result = run(link.execute())
        assert result.status == LinkStatus.SUCCESS

    def test_to_chain(self):
        agent = self._compile("Design system")
        chain = agent.to_chain()
        assert isinstance(chain, Chain)
        assert isinstance(chain, Link)  # homoiconic
        assert len(chain) == 1
        result = run(chain.execute())
        assert result.status == LinkStatus.SUCCESS

    def test_compose_two_agents(self):
        """Two compiled agents → one Chain. This is the composition."""
        a1 = self._compile("Design the API")
        a2 = self._compile("Implement the API", feature_type=FeatureType.TOOL)

        pipeline_chain = Chain("api_pipeline", [
            a1.to_link(),
            a2.to_link(),
        ])

        assert isinstance(pipeline_chain, Link)
        assert len(pipeline_chain) == 2
        result = run(pipeline_chain.execute())
        assert result.status == LinkStatus.SUCCESS

    def test_nested_compilation(self):
        """Chain of Chains — the onionmorph pattern."""
        design = self._compile("Design").to_chain("design")
        impl = self._compile("Implement", feature_type=FeatureType.TOOL).to_chain("impl")
        test = self._compile("Test").to_chain("test")

        meta_chain = Chain("full_pipeline", [design, impl, test])
        assert isinstance(meta_chain, Link)
        assert len(meta_chain) == 3
        # Each element is a Chain which IS a Link
        assert all(isinstance(l, Chain) for l in meta_chain.links)
