"""Chain Compiler — maps complex multi-stage goals to SDNAC unit sequences.

Arm 1 in the pipeline. Takes a TaskSpec and produces a ChainPlan.

This arm answers: "Given this goal, what sequence of agent steps is needed?"
It decomposes a complex task into a DAG of SDNAC nodes, where each node
is a single agent invocation.

Pattern source: SDNA's SDNAFlowConfig and DUOChainConfig.
Legacy source: Super Orchestrator's multi-agent routing.

Geometric invariants this arm is responsible for:
    5. Polymorphic Dispatch — the decomposition strategy depends on feature_type
"""

from __future__ import annotations

from typing import List

from compoctopus.base import CompilerArm
from compoctopus.context import CompilationContext
from compoctopus.types import (
    ArmKind,
    ChainNode,
    ChainPlan,
    GeometricAlignmentReport,
    MermaidSpec,
    PromptSection,
    ToolManifest,
)


class ChainCompiler(CompilerArm):
    """Decomposes a complex task into a sequence of SDNAC nodes.

    Input from context: ctx.task_spec
    Output to context:  ctx.chain_plan

    Strategies:
    - Single-step:    TaskSpec → [one ChainNode]
    - Sequential:     TaskSpec → [node1 → node2 → node3]
    - DUO (parallel): TaskSpec → [node1 || node2] → node3
    - DAG:            TaskSpec → arbitrary dependency graph

    The chain plan provides HINTS to downstream compilers:
    each ChainNode specifies requires_mcps and requires_skills,
    which the MCP and Skill compilers use as starting points.
    """

    @property
    def kind(self) -> ArmKind:
        return ArmKind.CHAIN

    def compile(self, ctx: CompilationContext) -> None:
        """Decompose ctx.task_spec into ctx.chain_plan.

        Strategy selection (polymorphic dispatch):
        - TOOL feature_type → sequential: analyze→code→test→integrate
        - AGENT feature_type → sequential: design→config→validate
        - CHAIN feature_type → recursive: decompose→sub-chains→compose
        - DOMAIN feature_type → hierarchical: domain→subdomain→workers
        """
        from compoctopus.types import FeatureType

        task = ctx.task_spec
        ft = task.feature_type

        # Polymorphic dispatch: feature_type → decomposition strategy
        if ft == FeatureType.TOOL:
            nodes = [
                ChainNode(name="analyze", description=f"Analyze: {task.description}",
                          requires_mcps=task.domain_hints),
                ChainNode(name="code", description="Implement the tool"),
                ChainNode(name="test", description="Test the implementation"),
                ChainNode(name="integrate", description="Integrate into pipeline"),
            ]
            flow_type = "sequential"
            deps = {"code": ["analyze"], "test": ["code"], "integrate": ["test"]}

        elif ft == FeatureType.AGENT:
            nodes = [
                ChainNode(name="design", description=f"Design: {task.description}",
                          requires_mcps=task.domain_hints),
                ChainNode(name="config", description="Configure agent profile"),
                ChainNode(name="validate", description="Validate alignment"),
            ]
            flow_type = "sequential"
            deps = {"config": ["design"], "validate": ["config"]}

        elif ft == FeatureType.CHAIN:
            nodes = [
                ChainNode(name="decompose", description=f"Decompose: {task.description}"),
                ChainNode(name="sub_chains", description="Build sub-chains"),
                ChainNode(name="compose", description="Compose sub-chain outputs"),
            ]
            flow_type = "sequential"
            deps = {"sub_chains": ["decompose"], "compose": ["sub_chains"]}

        elif ft == FeatureType.DOMAIN:
            nodes = [
                ChainNode(name="domain", description=f"Domain: {task.description}",
                          requires_mcps=task.domain_hints),
                ChainNode(name="subdomain", description="Resolve subdomains"),
                ChainNode(name="workers", description="Spawn domain workers"),
            ]
            flow_type = "sequential"
            deps = {"subdomain": ["domain"], "workers": ["subdomain"]}

        elif ft == FeatureType.SKILL:
            nodes = [
                ChainNode(name="identify", description=f"Identify skills: {task.description}",
                          requires_skills=task.domain_hints),
                ChainNode(name="compile_skills", description="Compile skill context"),
                ChainNode(name="inject", description="Inject into agent"),
            ]
            flow_type = "sequential"
            deps = {"compile_skills": ["identify"], "inject": ["compile_skills"]}

        else:
            # Fallback: single-node chain
            nodes = [ChainNode(name="main", description=task.description,
                               requires_mcps=task.domain_hints)]
            flow_type = "sequential"
            deps = {}

        ctx.chain_plan = ChainPlan(nodes=nodes, flow_type=flow_type, dependencies=deps)

    def validate(self, ctx: CompilationContext) -> GeometricAlignmentReport:
        """Validate the chain plan.

        Checks:
        - At least one node in the chain
        - No circular dependencies
        - All node names are unique
        - Feature type matches decomposition strategy (invariant 5)
        """
        from compoctopus.types import AlignmentResult, GeometricInvariant

        violations = []
        plan = ctx.chain_plan

        if not plan or not plan.nodes:
            violations.append(
                "ChainCompiler produced an empty chain plan (no nodes). "
                "Every compilation needs at least one ChainNode. The compile() step "
                "should have created nodes based on ctx.task_spec.feature_type: "
                "TOOL → [analyze, code, test, integrate], "
                "AGENT → [design, config, validate], "
                "CHAIN → [decompose, sub_chains, compose]."
            )
        else:
            # Check unique names
            names = [n.name for n in plan.nodes]
            if len(names) != len(set(names)):
                dupes = [n for n in names if names.count(n) > 1]
                violations.append(
                    f"Duplicate node names in chain plan: {set(dupes)}. "
                    f"Every ChainNode must have a unique name so the pipeline "
                    f"can address and route to each step independently. "
                    f"Fix: rename the duplicated nodes to be unique."
                )

            # Check DAG acyclicity (simple DFS)
            name_set = set(names)
            for dep_target, dep_sources in plan.dependencies.items():
                for src in dep_sources:
                    if src not in name_set:
                        violations.append(
                            f"Dependency '{dep_target}' references node '{src}' "
                            f"which doesn't exist in the chain plan. "
                            f"Available nodes: {sorted(name_set)}. "
                            f"Fix: either add a node named '{src}' or correct "
                            f"the dependency to reference an existing node."
                        )

            # Simple cycle check: walk from each node
            visited = set()
            path = set()
            has_cycle = False

            def dfs(node: str) -> bool:
                nonlocal has_cycle
                if node in path:
                    has_cycle = True
                    return True
                if node in visited:
                    return False
                visited.add(node)
                path.add(node)
                for dep in plan.dependencies.get(node, []):
                    if dfs(dep):
                        return True
                path.discard(node)
                return False

            for name in names:
                if dfs(name):
                    break
            if has_cycle:
                violations.append(
                    "Chain plan has circular dependencies — the dependency graph "
                    "is not a DAG. This means step A depends on step B which depends "
                    "on step A (or deeper cycles). Fix: remove the cycle by "
                    "reordering dependencies so they only point forward."
                )

        result = AlignmentResult(
            invariant=GeometricInvariant.POLYMORPHIC_DISPATCH,
            passed=len(violations) == 0,
            violations=violations,
            details=f"Chain plan: {len(plan.nodes) if plan else 0} nodes",
        )
        return GeometricAlignmentReport(results=[result])

    def get_mermaid_spec(self) -> MermaidSpec:
        """The mermaid diagram for the Chain Compiler agent itself.

        When this arm runs as an agent (meta-compilation), it follows
        this sequence diagram. Built programmatically so it's introspectable.
        """
        spec = MermaidSpec()
        spec.add_participant("User")
        spec.add_participant("Chain", "Chain Compiler")
        spec.add_participant("Carton")

        spec.add_message("User", "Chain", "TaskSpec (description + feature_type)")
        spec.add_message("Chain", "Chain", "Analyze complexity")
        spec.add_alt([
            ("Simple (single agent)", [
                ("Chain", "Chain", "Create single-node ChainPlan"),
            ]),
            ("Complex (multi-step)", [
                ("Chain", "Carton", "Query domain patterns"),
                ("Carton", "Chain", "Known decomposition templates"),
                ("Chain", "Chain", "Decompose into ChainNodes"),
                ("Chain", "Chain", "Wire dependencies"),
            ]),
        ])
        spec.add_message("Chain", "User", "ChainPlan")
        return spec

    def get_system_prompt_sections(self) -> List[PromptSection]:
        return [
            PromptSection(
                tag="IDENTITY",
                content=(
                    "You are the Chain Compiler. You decompose complex tasks "
                    "into sequences of SDNAC agent nodes."
                ),
            ),
            PromptSection(
                tag="WORKFLOW",
                content=(
                    "1. Analyze the task complexity and feature type\n"
                    "2. Query Carton for known decomposition patterns\n"
                    "3. Create a ChainPlan with appropriately scoped nodes\n"
                    "4. Wire dependencies between nodes\n"
                    "5. Annotate nodes with MCP/skill hints for downstream compilers"
                ),
            ),
            PromptSection(
                tag="CAPABILITY",
                content="You have access to: carton MCP (query domain patterns)",
            ),
            PromptSection(
                tag="CONSTRAINTS",
                content=(
                    "- Each node must be small enough for a single agent\n"
                    "- Dependencies must form a DAG (no cycles)\n"
                    "- Node names must be unique within the chain"
                ),
            ),
        ]

    def get_tool_surface(self) -> ToolManifest:
        return ToolManifest(
            mcps={},  # TODO Phase 2: add carton MCP config
            local_tools=[],
        )

    # ─────────────────────────────────────────────────────────────────
    # Convenience: minimal chain for testing
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def single_node_chain(ctx: CompilationContext) -> ChainPlan:
        """Create a trivial single-node chain for pass-through.

        Useful for Phase 1 testing: skip chain decomposition,
        just create one node that represents the entire task.
        """
        return ChainPlan(
            nodes=[
                ChainNode(
                    name="main",
                    description=ctx.task_spec.description,
                    requires_mcps=ctx.task_spec.domain_hints,
                )
            ],
            flow_type="sequential",
        )
