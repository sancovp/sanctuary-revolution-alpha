"""Compoctopus Bandit — ChainSelect vs ChainConstruct.

The Bandit is the head of the octopus. Given a task, it picks:
    - ChainSelect:    reuse a golden chain (exploit)
    - ChainConstruct: assemble a new pipeline (explore)

Both are Compilers. The Bandit is also a Compiler. Everything composes.

Type hierarchy:
    Link → Chain(Link) → Compiler(Chain) → Bandit(Compiler)
                                          → ChainSelect(Compiler)
                                          → ChainConstruct(Compiler)
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from compoctopus.base import CompilerArm, CompilerPipeline
from compoctopus.context import CompilationContext
from compoctopus.golden_chains import GoldenChainStore
from compoctopus.sensors import SensorStore
from compoctopus.chain_ontology import (
    Link, Chain, Compiler, LinkResult, LinkStatus,
)
from compoctopus.types import (
    CompiledAgent,
    FeatureType,
    GoldenChainEntry,
    SensorReading,
    TaskSpec,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ChainSelect(Compiler) — exploit: look up a proven golden chain
# =============================================================================

class ChainSelect(Compiler):
    """Compiler that returns a previously proven golden chain.

    This is the exploit arm of the bandit. If we've seen a task like
    this before AND the config has high enough reward, just reuse it.

    execute() puts the CompiledAgent into context['compiled'].
    """

    def __init__(self, golden_chains: Optional[GoldenChainStore] = None):
        super().__init__(chain_name="chain_select")
        self._golden_chains = golden_chains or GoldenChainStore()

    def select(self, task_spec: TaskSpec) -> Optional[CompiledAgent]:
        """Synchronous golden chain lookup.

        Returns the CompiledAgent from the best matching golden chain,
        or None if no suitable chain exists.
        """
        domain = task_spec.domain_hints[0] if task_spec.domain_hints else "general"
        golden = self._golden_chains.find_for_task(
            domain=domain,
            feature_type=task_spec.feature_type,
        )
        if golden is None:
            logger.debug(
                "ChainSelect: no golden chain for domain='%s' type=%s",
                domain, task_spec.feature_type.value,
            )
            return None

        logger.info(
            "ChainSelect: found golden chain %s (reward=%.3f, count=%d)",
            golden.config_hash[:8], golden.reward_mean, golden.reward_count,
        )
        return golden.compiled_agent

    async def execute(self, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Async execution interface — looks up golden chain."""
        ctx = dict(context) if context else {}
        task_spec = ctx.get("_task_spec")
        if not task_spec:
            return LinkResult(
                status=LinkStatus.ERROR, context=ctx,
                error="No _task_spec in context. ChainSelect requires "
                      "context['_task_spec'] to be a TaskSpec instance.",
            )

        compiled = self.select(task_spec)
        if compiled is None:
            return LinkResult(
                status=LinkStatus.BLOCKED, context=ctx,
                error="No golden chain found for this task.",
            )

        ctx[self.output_key] = compiled
        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)

    def describe(self, depth: int = 0) -> str:
        indent = "  " * depth
        count = len(self._golden_chains.list_chains())
        return f"{indent}ChainSelect \"{self.name}\" [{count} golden chains]"


# =============================================================================
# ChainConstruct(Compiler) — explore: assemble pipeline, compile new chain
# =============================================================================

class ChainConstruct(Compiler):
    """Compiler that assembles a pipeline from arms and compiles a new agent.

    This is the explore arm of the bandit. Build a fresh CompilerPipeline
    from the registered arms and run it against the TaskSpec.

    execute() puts the CompiledAgent into context['compiled'].
    """

    def __init__(self, arm_registry: Optional[Dict[str, CompilerArm]] = None):
        super().__init__(chain_name="chain_construct")
        self._arms = arm_registry or {}

    def register_arm(self, name: str, arm: CompilerArm) -> None:
        """Register a compiler arm by name."""
        logger.info("ChainConstruct: registered arm '%s' (%s)", name, type(arm).__name__)
        self._arms[name] = arm

    async def execute(self, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Async execution interface — builds pipeline and compiles."""
        ctx = dict(context) if context else {}
        task_spec = ctx.get("_task_spec")
        if not task_spec:
            return LinkResult(
                status=LinkStatus.ERROR, context=ctx,
                error="No _task_spec in context. ChainConstruct requires "
                      "context['_task_spec'] to be a TaskSpec instance.",
            )

        try:
            # Determine which arms to use
            arm_names = ctx.get("_arm_names") or self._default_pipeline(task_spec.feature_type)
            compiled = self.compile_with_pipeline(task_spec, arm_names)
            ctx[self.output_key] = compiled
            return LinkResult(status=LinkStatus.SUCCESS, context=ctx)
        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error("ChainConstruct: pipeline failed: %s", e, exc_info=True)
            return LinkResult(status=LinkStatus.ERROR, context=ctx, error=str(e))

    def compile_with_pipeline(
        self,
        task_spec: TaskSpec,
        arm_names: Optional[List[str]] = None,
    ) -> CompiledAgent:
        """Compile using an explicit pipeline of arm names.

        Synchronous convenience method that bypasses the async execute().
        Useful for testing and direct invocation.

        Args:
            task_spec: The task to compile.
            arm_names: Names of arms to run, in order.
                      If None, runs the default pipeline for the feature type.
        """
        if arm_names is None:
            arm_names = self._default_pipeline(task_spec.feature_type)

        logger.info(
            "ChainConstruct: compiling task '%s' with arms [%s]",
            task_spec.description[:60], " → ".join(arm_names),
        )

        arms = [self._arms[name] for name in arm_names if name in self._arms]
        pipeline = CompilerPipeline(arms)
        ctx = CompilationContext(task_spec=task_spec)
        ctx = pipeline.compile(ctx)
        compiled = ctx.freeze()

        logger.info(
            "ChainConstruct: compiled '%s' → Link '%s' (model=%s, tools=%d)",
            task_spec.description[:40],
            compiled.agent_profile.name if compiled.agent_profile else "N/A",
            compiled.agent_profile.model if compiled.agent_profile else "N/A",
            len(compiled.tool_manifest.all_tool_names) if compiled.tool_manifest else 0,
        )
        return compiled

    def _default_pipeline(self, feature_type: FeatureType) -> List[str]:
        """Get the default arm sequence for a feature type.

        Standard pipeline:
            Chains → Agents → MCPs → Skills → System Prompts → Input Prompts
        """
        standard = ["chain", "agent", "mcp", "skill", "system_prompt", "input_prompt"]

        skips = {
            FeatureType.TOOL: [],           # Full pipeline
            FeatureType.AGENT: [],           # Full pipeline
            FeatureType.CHAIN: ["chain"],    # Don't re-decompose chains
            FeatureType.SKILL: ["chain"],    # Skills are single-step
        }

        skip_set = set(skips.get(feature_type, []))
        return [a for a in standard if a not in skip_set]

    def describe(self, depth: int = 0) -> str:
        indent = "  " * depth
        arm_names = ", ".join(self._arms.keys()) if self._arms else "none"
        return f"{indent}ChainConstruct \"{self.name}\" [arms={arm_names}]"


# =============================================================================
# Bandit(Compiler) — the head: picks ChainSelect or ChainConstruct
# =============================================================================

class Bandit(Compiler):
    """The Compoctopus Bandit — picks between Select (exploit) and Construct (explore).

    This IS the Compoctopus. It holds a ChainSelect and a ChainConstruct,
    uses reward history to decide which to invoke, and records outcomes
    for future decisions.

    Decision logic:
        1. Try ChainSelect (golden chain lookup)
        2. If no golden chain found → ChainConstruct (build new pipeline)
        3. After execution, record_execution() feeds reward back
        4. When reward threshold met, graduate config to golden chain

    execute() puts the CompiledAgent into context['compiled'].
    """

    def __init__(
        self,
        arm_registry: Optional[Dict[str, CompilerArm]] = None,
        golden_chains: Optional[GoldenChainStore] = None,
        sensors: Optional[SensorStore] = None,
    ):
        super().__init__(chain_name="bandit")
        self._golden_chains = golden_chains or GoldenChainStore()
        self._sensors = sensors or SensorStore()
        self.chain_select = ChainSelect(golden_chains=self._golden_chains)
        self.chain_construct = ChainConstruct(arm_registry=arm_registry)

    def register_arm(self, name: str, arm: CompilerArm) -> None:
        """Register a compiler arm (delegated to ChainConstruct)."""
        logger.info("Bandit: delegating arm registration '%s' to ChainConstruct", name)
        self.chain_construct.register_arm(name, arm)

    async def execute(self, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Async execution interface — select-or-construct decision."""
        ctx = dict(context) if context else {}
        task_spec = ctx.get("_task_spec")
        if not task_spec:
            return LinkResult(
                status=LinkStatus.ERROR, context=ctx,
                error="No _task_spec in context. Bandit requires "
                      "context['_task_spec'] to be a TaskSpec instance.",
            )

        # Try SELECT first (exploit)
        select_result = await self.chain_select.execute(ctx)
        if select_result.status == LinkStatus.SUCCESS:
            ctx = select_result.context
            ctx["_bandit_chose"] = "select"
            logger.info(
                "Bandit: SELECT succeeded for '%s' — reusing golden chain",
                task_spec.description[:40],
            )
            return LinkResult(status=LinkStatus.SUCCESS, context=ctx)

        # No golden chain — CONSTRUCT (explore)
        logger.info(
            "Bandit: SELECT missed, falling back to CONSTRUCT for '%s'",
            task_spec.description[:40],
        )
        construct_result = await self.chain_construct.execute(ctx)
        ctx = construct_result.context
        ctx["_bandit_chose"] = "construct"

        if construct_result.status != LinkStatus.SUCCESS:
            return construct_result

        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)

    def compile(self, task_spec: TaskSpec) -> CompiledAgent:
        """Synchronous compile — the main entry point.

        Tries Select first, falls back to Construct.
        This is how you call Compoctopus.
        """
        # Try golden chain lookup
        domain = task_spec.domain_hints[0] if task_spec.domain_hints else "general"
        golden = self._golden_chains.find_for_task(
            domain=domain,
            feature_type=task_spec.feature_type,
        )
        if golden is not None and golden.reward_count >= 5:
            logger.info(
                "Bandit.compile: SELECT — reusing golden chain %s (reward=%.3f)",
                golden.config_hash[:8], golden.reward_mean,
            )
            return golden.compiled_agent

        # No golden chain — construct
        logger.info(
            "Bandit.compile: CONSTRUCT — building new pipeline for '%s'",
            task_spec.description[:60],
        )
        return self.chain_construct.compile_with_pipeline(task_spec)

    def compile_with_pipeline(
        self,
        task_spec: TaskSpec,
        arm_names: Optional[List[str]] = None,
    ) -> CompiledAgent:
        """Direct compile bypassing the bandit (delegated to ChainConstruct)."""
        logger.info(
            "Bandit: compile_with_pipeline for '%s' (bypassing select/construct decision)",
            task_spec.description[:60],
        )
        return self.chain_construct.compile_with_pipeline(task_spec, arm_names)

    def record_execution(
        self,
        compiled_agent: CompiledAgent,
        success: bool,
        turns_taken: int = 0,
        goal_accomplished: bool = False,
        human_feedback: Optional[float] = None,
    ) -> None:
        """Record an execution outcome for bandit learning.

        After an agent executes, call this with the outcome.
        The bandit uses this to:
        1. Update sensor readings for the config hash
        2. Check if the config should graduate to a golden chain
        3. If so, store it for future Select decisions
        """
        domain = (
            compiled_agent.task_spec.domain_hints[0]
            if compiled_agent.task_spec.domain_hints
            else "general"
        )
        reading = SensorReading(
            config_hash=compiled_agent.compile_id or "unknown",
            success=success,
            turns_taken=turns_taken,
            goal_accomplished=goal_accomplished,
            human_feedback=human_feedback,
        )
        self._sensors.record(reading)

        logger.info(
            "Bandit: recorded execution for %s (success=%s, turns=%d)",
            reading.config_hash[:8], success, turns_taken,
        )

        # Check graduation threshold
        if self._sensors.meets_graduation_threshold(reading.config_hash):
            reward = self._sensors.get_reward(reading.config_hash)
            count = self._sensors.get_count(reading.config_hash)
            self._golden_chains.graduate(
                compiled_agent=compiled_agent,
                reward_mean=reward,
                reward_count=count,
                domain=domain,
            )
            logger.info(
                "Bandit: graduated %s to golden chain (reward=%.3f, count=%d)",
                reading.config_hash[:8], reward, count,
            )

    def describe(self, depth: int = 0) -> str:
        indent = "  " * depth
        lines = [f"{indent}Bandit \"{self.name}\":"]
        lines.append(f"{indent}  ├── {self.chain_select.describe(depth + 1).lstrip()}")
        lines.append(f"{indent}  └── {self.chain_construct.describe(depth + 1).lstrip()}")
        return "\n".join(lines)
