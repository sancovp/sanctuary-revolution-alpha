"""Compilation context — the accumulating state through the pipeline.

The CompilationContext is the "wire" that threads through every arm.
Each arm reads what it needs, writes its output, and passes the context along.
This is the single source of truth during a compilation run.

The context is NOT the final output (CompiledAgent).
It's the mutable working state that gets frozen into a CompiledAgent at the end.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from compoctopus.types import (
    AgentProfile,
    ArmKind,
    ChainPlan,
    CompiledAgent,
    GeometricAlignmentReport,
    InputPrompt,
    SkillBundle,
    SystemPrompt,
    TaskSpec,
    ToolManifest,
)

import logging
logger = logging.getLogger(__name__)

@dataclass
class CompilationStep:
    """Record of one arm's work on the context."""
    arm: ArmKind
    started_at: float = 0.0
    completed_at: float = 0.0
    success: bool = False
    error: Optional[str] = None
    alignment_passed: bool = False

    def __repr__(self) -> str:
        elapsed = (self.completed_at - self.started_at) * 1000 if self.completed_at else 0
        status = "✓" if self.success else "✗"
        return f"Step({self.arm.value} {status} {elapsed:.1f}ms)"


@dataclass
class CompilationContext:
    """Mutable accumulation of compiler arm outputs.

    Usage:
        ctx = CompilationContext(task_spec=TaskSpec(...))
        chain_arm.compile(ctx)     # writes ctx.chain_plan
        agent_arm.compile(ctx)     # reads ctx.chain_plan, writes ctx.agent_profile
        mcp_arm.compile(ctx)       # reads ctx.agent_profile, writes ctx.tool_manifest
        ...
        result = ctx.freeze()      # → CompiledAgent
    """

    # Input
    task_spec: TaskSpec = field(default_factory=TaskSpec)

    # Progressive outputs (filled by arms in order)
    chain_plan: Optional[ChainPlan] = None
    agent_profile: Optional[AgentProfile] = None
    tool_manifest: Optional[ToolManifest] = None
    skill_bundle: Optional[SkillBundle] = None
    system_prompt: Optional[SystemPrompt] = None
    input_prompt: Optional[InputPrompt] = None
    alignment: Optional[GeometricAlignmentReport] = None

    # Compilation trace
    steps: List[CompilationStep] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def begin_step(self, arm: ArmKind) -> CompilationStep:
        """Mark the start of a compilation step."""
        step = CompilationStep(arm=arm, started_at=time.time())
        self.steps.append(step)
        logger.debug("Step started: %s (step %d)", arm.value, len(self.steps))
        return step

    def end_step(self, step: CompilationStep, success: bool, error: Optional[str] = None):
        """Mark the end of a compilation step."""
        step.completed_at = time.time()
        step.success = success
        step.error = error
        elapsed_ms = (step.completed_at - step.started_at) * 1000
        if success:
            logger.debug(
                "Step complete: %s ✓ (%.1fms)", step.arm.value, elapsed_ms,
            )
        else:
            logger.warning(
                "Step failed: %s ✗ (%.1fms) error=%s",
                step.arm.value, elapsed_ms, error or "alignment failure",
            )

    def freeze(self) -> CompiledAgent:
        """Freeze the mutable context into an immutable CompiledAgent."""
        import uuid
        now = time.time()
        elapsed_ms = (now - self.started_at) * 1000
        passed = sum(1 for s in self.steps if s.success)
        logger.info(
            "Context frozen: %d/%d steps passed in %.1fms → CompiledAgent",
            passed, len(self.steps), elapsed_ms,
        )
        return CompiledAgent(
            task_spec=self.task_spec,
            chain_plan=self.chain_plan,
            agent_profile=self.agent_profile,
            tool_manifest=self.tool_manifest,
            skill_bundle=self.skill_bundle,
            system_prompt=self.system_prompt,
            input_prompt=self.input_prompt,
            alignment=self.alignment,
            # Compile metadata
            compiled_at=now,
            compile_duration_ms=elapsed_ms,
            compile_id=uuid.uuid4().hex[:12],
            pipeline_arms=[s.arm.value for s in self.steps],
        )

    @property
    def config_hash(self) -> str:
        """Deterministic hash of the current compilation state.

        Used by the bandit to identify configurations.
        Cached; invalidated when steps change the state.
        """
        cache_key = len(self.steps)
        if not hasattr(self, "_config_hash_cache") or self._config_hash_age != cache_key:
            hashable = {
                "task": self.task_spec.description,
                "model": self.agent_profile.model if self.agent_profile else None,
                "tools": self.tool_manifest.all_tool_names if self.tool_manifest else [],
            }
            self._config_hash_cache = hashlib.sha256(
                json.dumps(hashable, sort_keys=True).encode()
            ).hexdigest()[:16]
            self._config_hash_age = cache_key
        return self._config_hash_cache

    @property
    def completed_arms(self) -> List[ArmKind]:
        """Which arms have successfully run."""
        return [s.arm for s in self.steps if s.success]

    def __str__(self) -> str:
        arms = ", ".join(a.value for a in self.completed_arms)
        status = "aligned" if (self.alignment and self.alignment.aligned) else "in-progress"
        return f"CompilationContext({status}, arms=[{arms}])"
