"""CompoctopusAgent — the abstract type for all Compoctopus agents.

A CompoctopusAgent is:
    1. A Chain of SDNA* steps (SDNACs, FunctionLinks) connected by Dovetails
    2. Each SDNAC has its own HermesConfig → its own Heaven agent
    3. Mechanical steps (ANNEAL, VERIFY) are FunctionLinks (no LLM)
    4. execute() runs self.chain.execute(ctx) — Chain handles sequencing
    5. Dovetails validate outputs and map inputs between steps

Architecture:
    CompoctopusAgent (Chain + metadata)
      └── Chain/SDNAFlow/EvalChain
          ├── SDNAC (phase 1: own HermesConfig, own tools, own agent)
          │     ├── Ariadne (context injection)
          │     └── Poimandres (LLM execution via HeavenAgent)
          ├── Dovetail (validates output, maps input)
          ├── SDNAC (phase 2: different agent, different tools)
          ├── Dovetail
          ├── FunctionLink (mechanical step, no LLM)
          └── ...

Agent types use different SDNA primitives:
    - Planner: Chain (sequential, no loops)
    - OctoCoder: EvalChain (annealing loop with verify evaluator)
    - Bandit: EvalChain (SELECT → CONSTRUCT → SELECT loop)

This is Step 0 of the bootstrap: the abstract type that all agents
implement. The 🐙 Coder is the first concrete instance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from compoctopus.base import CompilerArm
from compoctopus.chain_ontology import Link, Chain, EvalChain, LinkResult, LinkStatus
from compoctopus.types import (
    ArmKind,
    CompiledAgent,
    GeometricAlignmentReport,
    MermaidSpec,
    PromptSection,
    SystemPrompt,
    TaskSpec,
    ToolManifest,
)
from compoctopus.context import CompilationContext

logger = logging.getLogger(__name__)


# =============================================================================
# CompoctopusAgent — Chain-based orchestration via SDNA primitives
# =============================================================================

@dataclass
class CompoctopusAgent(CompilerArm):
    """The universal Compoctopus type. Everything is this.

    Inherits CompilerArm (which inherits Link). A CompoctopusAgent
    wraps a Chain of SDNA* steps. Workers, compiler arms, pipeline
    compilers — they're all CompoctopusAgent with different Chains.

    Fields:
    - chain: The SDNA Chain/SDNAFlow/EvalChain that orchestrates this agent
    - system_prompt: the agent's identity and instructions (for describe/freeze)
    - mermaid_spec: the executable sequence diagram (for validation)
    - tool_manifest: equipped tools (union across all phases)
    - arm_kind: which compiler arm this is (if acting as an arm)

    The execute() method just runs self.chain.execute(ctx).
    The Chain handles all sequencing, looping, and dovetailing.
    """
    agent_name: str = ""
    chain: Optional[Union[Chain, EvalChain, Link]] = None
    system_prompt: Optional[SystemPrompt] = None
    mermaid_spec: Optional[MermaidSpec] = None
    tool_manifest: Optional[ToolManifest] = None
    task_spec: Optional[TaskSpec] = None
    arm_kind: Optional[ArmKind] = None  # None = worker; set for compiler arms
    model: str = "minimax"
    modules: List[str] = field(default_factory=list)

    # --- CompilerArm abstract methods (implemented) ---

    @property
    def kind(self) -> ArmKind:
        return self.arm_kind

    def compile(self, ctx: CompilationContext) -> None:
        """Compile by running this agent's chain."""
        import asyncio
        result = asyncio.run(self.execute(ctx.__dict__ if hasattr(ctx, '__dict__') else {}))
        if hasattr(result, 'context') and result.context:
            for k, v in result.context.items():
                if not k.startswith('_'):
                    setattr(ctx, k, v)

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate using geometric alignment."""
        from compoctopus.alignment import GeometricAlignmentValidator
        gav = GeometricAlignmentValidator()
        sp = self.system_prompt or SystemPrompt()
        from compoctopus.types import InputPrompt
        ip = InputPrompt(mermaid=self.mermaid_spec)
        dd = gav.check_dual_description(sp, ip)
        return GeometricAlignmentReport(results=[dd])

    def get_mermaid_spec(self) -> MermaidSpec:
        return self.mermaid_spec or MermaidSpec()

    def get_system_prompt_sections(self) -> List[PromptSection]:
        if self.system_prompt:
            return self.system_prompt.sections
        return []

    def get_tool_surface(self) -> ToolManifest:
        return self.tool_manifest or ToolManifest()

    @property
    def name(self) -> str:
        return self.agent_name or "compoctopus_agent"

    async def execute(self, context=None, **kwargs):
        """Run the agent's chain.

        The chain handles all orchestration:
        - Chain: sequential execution with dovetail validation
        - EvalChain: loop with evaluator (approve/reject/retry)
        """
        ctx = dict(context) if context else {}

        if self.chain is None:
            raise ValueError(
                f"CompoctopusAgent '{self.name}' has no chain. "
                f"Every agent must have a Chain of SDNACs."
            )

        logger.info("Agent '%s': executing chain '%s'",
                    self.name, getattr(self.chain, 'name', 'unnamed'))
        return await self.chain.execute(ctx)

    # --- Convenience methods ---

    def describe(self, depth: int = 0) -> str:
        indent = "  " * depth
        chain_name = getattr(self.chain, 'name', 'unnamed') if self.chain else 'none'
        chain_type = type(self.chain).__name__ if self.chain else 'None'
        n_links = len(self.chain.links) if hasattr(self.chain, 'links') else 0
        n_dovetails = len(self.chain.dovetails) if hasattr(self.chain, 'dovetails') else 0
        return (
            f"{indent}CompoctopusAgent \"{self.name}\" "
            f"[chain={chain_name}, type={chain_type}, "
            f"links={n_links}, dovetails={n_dovetails}, model={self.model}]"
        )

    def to_sdna(self) -> Dict[str, Any]:
        """Serialize to SDNA config."""
        result = {
            "agent_name": self.name,
            "model": self.model,
            "system_prompt": self.system_prompt.render() if self.system_prompt else "",
            "mermaid_spec": self.mermaid_spec.diagram if self.mermaid_spec else "",
            "tools": self.tool_manifest.all_tool_names if self.tool_manifest else [],
            "modules": self.modules,
        }
        if self.chain:
            result["chain"] = {
                "name": getattr(self.chain, 'name', 'unnamed'),
                "type": type(self.chain).__name__,
                "links": [
                    {"name": link.name, "type": type(link).__name__}
                    for link in getattr(self.chain, 'links', [])
                ],
                "dovetails": [
                    {"name": d.name, "expected_outputs": d.expected_outputs}
                    for d in getattr(self.chain, 'dovetails', [])
                ],
            }
        return result

    def to_link(self) -> "CompoctopusAgent":
        """Return self — CompoctopusAgent IS a Link."""
        return self

    def freeze(self) -> CompiledAgent:
        """Freeze to a CompiledAgent dataclass."""
        from compoctopus.types import AgentProfile
        return CompiledAgent(
            task_spec=self.task_spec or TaskSpec(description=self.name),
            agent_profile=AgentProfile(name=self.name, model=self.model),
            system_prompt=self.system_prompt,
            tool_manifest=self.tool_manifest,
        )

    def __repr__(self) -> str:
        chain_name = getattr(self.chain, 'name', 'none') if self.chain else 'none'
        chain_type = type(self.chain).__name__ if self.chain else 'None'
        return (
            f"CompoctopusAgent('{self.name}', "
            f"chain={chain_name}, type={chain_type}, "
            f"model={self.model})"
        )
