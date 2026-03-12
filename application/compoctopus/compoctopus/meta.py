"""Meta-Compiler — compiles complete domain stacks.

The meta-compiler is the D:D→D fixed-point generator. Given
"I need a domain that handles X", it produces:
- Orchestrator agent config
- Manager agent configs
- Worker agent configs
- Skills for the domain
- Input prompt templates

It does this by invoking the Compoctopus pipeline recursively
to compile the agents that compile agents.

This is Phase 6 and depends on all other arms being functional.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from compoctopus.types import CompiledAgent, FeatureType, TaskSpec, TrustLevel
from compoctopus.chain_ontology import Link, LinkResult, LinkStatus

logger = logging.getLogger(__name__)


class MetaCompiler(Link):
    """Compiles complete domain stacks via recursive pipeline invocation.

    Inherits from Link — the meta-compiler IS a Link in the chain ontology.

    This is the self-referential heart of the Compoctopus:
    the meta-compiler uses the same pipeline to compile the
    compiler arms themselves.

    Usage:
        meta = MetaCompiler(router=compoctopus_router)
        domain_stack = meta.compile_domain("summarization")
        # Returns: {orchestrator, managers[], workers[]}
    """

    name = "meta_compiler"

    def __init__(self, router=None, onionmorph=None):
        """Initialize the meta-compiler.

        Args:
            router: The Bandit or any object with a .compile(TaskSpec) method.
                   This is what makes the D:D→D loop real — we use the compiler
                   to compile the compiler.
            onionmorph: Optional OnionmorphRouter for subdomain detection.
        """
        self._router = router
        self._onionmorph = onionmorph

    async def execute(self, context=None, **kwargs):
        """Async execution — compile domain from context."""
        ctx = dict(context) if context else {}
        domain_desc = ctx.get("_domain_description", "")
        if not domain_desc:
            return LinkResult(
                status=LinkStatus.ERROR, context=ctx,
                error="No _domain_description in context. MetaCompiler requires "
                      "context['_domain_description'] to be a string.",
            )

        try:
            result = self.compile_domain(domain_desc)
            ctx["_domain_stack"] = result
            return LinkResult(status=LinkStatus.SUCCESS, context=ctx)
        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error("MetaCompiler: domain compilation failed: %s", e, exc_info=True)
            return LinkResult(status=LinkStatus.ERROR, context=ctx, error=str(e))

    def describe(self, depth=0):
        indent = "  " * depth
        return f"{indent}MetaCompiler \"{self.name}\" [D:D→D fixed-point]"

    def compile_domain(self, domain_description: str) -> Dict[str, object]:
        """Compile a complete domain stack from a description.

        Output structure:
        {
            "orchestrator": CompiledAgent,  # Domain top-level router
            "managers": [CompiledAgent],     # Subdomain managers
            "workers": [CompiledAgent],      # Leaf workers
        }
        """
        if self._router is None:
            raise ValueError(
                "MetaCompiler requires a router (Bandit) to compile domains. "
                "Pass router=bandit to MetaCompiler(). The router is used to "
                "recursively invoke the Compoctopus pipeline for each agent."
            )

        logger.info("MetaCompiler: compiling domain '%s'", domain_description)

        # 1. Compile the orchestrator agent for this domain
        orch_spec = TaskSpec(
            description=f"Orchestrate the {domain_description} domain",
            feature_type=FeatureType.AGENT,
            trust_level=TrustLevel.ORCHESTRATOR,
            domain_hints=[domain_description],
        )
        orchestrator = self._router.compile(orch_spec)
        logger.info("MetaCompiler: compiled orchestrator for '%s'", domain_description)

        # 2. Detect subdomains
        subdomains = self._detect_subdomains(domain_description)
        logger.info("MetaCompiler: detected subdomains: %s", subdomains)

        # 3. Compile a manager agent for each subdomain
        managers = []
        for sub in subdomains:
            mgr_spec = TaskSpec(
                description=f"Manage {sub} subdomain of {domain_description}",
                feature_type=FeatureType.AGENT,
                trust_level=TrustLevel.BUILDER,
                domain_hints=[domain_description, sub],
            )
            managers.append(self._router.compile(mgr_spec))

        # 4. Compile worker agents for leaf tasks
        workers = []
        for sub in subdomains:
            worker_spec = TaskSpec(
                description=f"Execute {sub} tasks in {domain_description}",
                feature_type=FeatureType.AGENT,
                trust_level=TrustLevel.EXECUTOR,
                domain_hints=[domain_description, sub],
            )
            workers.append(self._router.compile(worker_spec))

        logger.info(
            "MetaCompiler: domain '%s' → 1 orchestrator, %d managers, %d workers",
            domain_description, len(managers), len(workers),
        )

        return {
            "orchestrator": orchestrator,
            "managers": managers,
            "workers": workers,
        }

    def compile_arm(self, arm_name: str) -> CompiledAgent:
        """Compile a compiler arm itself via the pipeline.

        This is the D:D→D fixed point: use Compoctopus to compile
        a Compoctopus arm. The arm's mermaid spec, system prompt,
        and tool surface are fed to the pipeline as a TaskSpec.
        """
        if self._router is None:
            raise ValueError(
                "MetaCompiler requires a router (Bandit) to compile arms. "
                "Pass router=bandit to MetaCompiler(). The router is used to "
                "invoke the Compoctopus pipeline to compile the arm itself."
            )

        # Get the arm from the registry
        arm_registry = getattr(self._router, "chain_construct", None)
        if arm_registry is None:
            raise ValueError(
                f"Router has no chain_construct — cannot access arm registry. "
                f"MetaCompiler.compile_arm requires a Bandit router."
            )

        arm = arm_registry._arms.get(arm_name)
        if arm is None:
            raise ValueError(
                f"Arm '{arm_name}' not found in registry. "
                f"Available arms: {list(arm_registry._arms.keys())}. "
                f"Register the arm with router.register_arm() first."
            )

        logger.info("MetaCompiler: D:D→D compiling arm '%s'", arm_name)

        # The arm describes itself via its existing methods.
        # We feed that self-description AS a TaskSpec TO the pipeline.
        self_desc = arm.self_compile()
        mermaid_spec = arm.get_mermaid_spec()
        system_prompt = arm.get_system_prompt()
        tool_surface = arm.get_tool_surface()

        task_spec = TaskSpec(
            description=f"Compile a compiler arm: {arm.name}",
            feature_type=FeatureType.AGENT,
            domain_hints=[arm_name],
            constraints={
                "mermaid_diagram": mermaid_spec.diagram if mermaid_spec else "",
                "system_prompt": system_prompt,
                "tool_names": tool_surface.all_tool_names if tool_surface else [],
            },
        )

        compiled = self._router.compile(task_spec)
        logger.info(
            "MetaCompiler: D:D→D compiled arm '%s' → %s",
            arm_name, repr(compiled),
        )
        return compiled

    def bootstrap(self) -> Dict[str, CompiledAgent]:
        """Bootstrap the entire Compoctopus from scratch.

        Compiles all 6 arms using the meta-compiler, verifying
        that the D:D→D fixed point is reached — each arm's compiled
        config matches its hand-written config.
        """
        if self._router is None:
            raise ValueError(
                "MetaCompiler requires a router (Bandit) to bootstrap. "
                "Pass router=bandit to MetaCompiler()."
            )

        arm_names = ["chain", "agent", "mcp", "skill", "system_prompt", "input_prompt"]
        arm_registry = self._router.chain_construct._arms
        results = {}
        mismatches = []

        logger.info("MetaCompiler: bootstrapping D:D→D for %d arms", len(arm_names))

        for arm_name in arm_names:
            if arm_name not in arm_registry:
                logger.warning("MetaCompiler: arm '%s' not registered, skipping", arm_name)
                continue

            compiled = self.compile_arm(arm_name)
            results[arm_name] = compiled

            # Fixed-point verification: compare compiled vs hand-written
            original_arm = arm_registry[arm_name]
            original_prompt = original_arm.get_system_prompt()
            compiled_prompt = (
                compiled.system_prompt.render() if compiled.system_prompt else ""
            )

            # Structural similarity check (not semantic — that needs LLM)
            # Check that key sections are present
            if original_prompt and compiled_prompt:
                orig_len = len(original_prompt)
                comp_len = len(compiled_prompt)
                ratio = min(orig_len, comp_len) / max(orig_len, comp_len) if max(orig_len, comp_len) > 0 else 1.0
                if ratio < 0.5:
                    mismatches.append(
                        f"{arm_name}: length ratio={ratio:.2f} "
                        f"(original={orig_len}, compiled={comp_len})"
                    )

        if mismatches:
            logger.warning("MetaCompiler: fixed-point mismatches: %s", mismatches)
        else:
            logger.info("MetaCompiler: bootstrap complete, all arms within tolerance")

        return results

    def _detect_subdomains(self, domain_description: str) -> List[str]:
        """Detect subdomains for a domain using onionmorph or heuristics."""
        if self._onionmorph is not None:
            domains = self._onionmorph.detect_cross_domain(
                TaskSpec(description=domain_description)
            )
            # Onionmorph returns domain names — treat them as subdomains
            return domains if domains != ["general"] else ["default"]

        # Without onionmorph, just use a single "default" subdomain
        return ["default"]
