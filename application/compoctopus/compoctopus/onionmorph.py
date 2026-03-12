"""Onionmorph Router — hierarchical domain routing.

The onionmorph handles multi-domain tasks by routing through layers:
    Domain → Subdomain → Worker

Each layer is itself an ES-compiled agent, creating recursive compilation.

Pattern source: Super Orchestrator + SearchXTool + CallXTool
From DESIGN.md:
    "Compoctopus Router
      └→ Domain Compiler (e.g. 'coding domain')
          └→ Subdomain Compiler (e.g. 'debugging subdomain')
              └→ Worker Compiler (actual agent config output)"
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from compoctopus.context import CompilationContext
from compoctopus.chain_ontology import Link, LinkResult, LinkStatus
from compoctopus.types import (
    CompiledAgent,
    RoutingNode,
    RoutingTree,
    TaskSpec,
)

logger = logging.getLogger(__name__)


class OnionmorphRouter(Link):
    """Routes complex multi-domain tasks through hierarchical layers.

    Inherits from Link — the router IS a Link in the chain ontology.

    The onionmorph peels layers of specificity:
    1. Top level: which domain(s) does this task involve?
    2. Mid level: within that domain, which subdomain?
    3. Bottom level: within that subdomain, which specific worker config?

    Each level can itself be compiled via Compoctopus (D:D→D recursion).
    """

    name = "onionmorph"

    def __init__(self, registry=None):
        """Initialize the onionmorph router.

        Args:
            registry: Optional Registry for domain/MCP/skill lookup.
                     If None, routing relies on TaskSpec.domain_hints only.
        """
        self._registry = registry

    async def execute(self, context=None, **kwargs):
        """Async execution — route and attach routing tree to context."""
        ctx = dict(context) if context else {}
        task_spec = ctx.get("_task_spec")
        if not task_spec:
            return LinkResult(
                status=LinkStatus.ERROR, context=ctx,
                error="No _task_spec in context. OnionmorphRouter requires "
                      "context['_task_spec'] to be a TaskSpec instance.",
            )

        tree = self.route(task_spec)
        ctx["_routing_tree"] = tree
        return LinkResult(status=LinkStatus.SUCCESS, context=ctx)

    def describe(self, depth=0):
        indent = "  " * depth
        return f"{indent}OnionmorphRouter \"{self.name}\" [hierarchical router]"

    def route(self, task_spec: TaskSpec) -> RoutingTree:
        """Route a task through the onionmorph hierarchy.

        Returns a RoutingTree showing the full routing decision:
        which domain → which subdomain → which worker(s).
        """
        domains = self.detect_cross_domain(task_spec)
        logger.info("Onionmorph: detected domains %s for '%s'", domains, task_spec.description[:40])

        if len(domains) == 1:
            root = self.route_single_domain(task_spec, domains[0])
            return RoutingTree(root=root)

        # Multi-domain: create a root that fans out
        children = [self.route_single_domain(task_spec, d) for d in domains]
        root = RoutingNode(
            domain="multi",
            subdomain="orchestrator",
            children=children,
        )
        logger.info(
            "Onionmorph: multi-domain routing → %d children",
            len(children),
        )
        return RoutingTree(root=root)

    def route_single_domain(self, task_spec: TaskSpec, domain: str) -> RoutingNode:
        """Route within a single domain to find subdomains and workers.

        Without a registry, creates a single-node routing tree for the domain.
        With a registry, resolves registered domains and their subdomains.
        """
        # Without registry, simple 1-node route
        if self._registry is None:
            logger.debug("Onionmorph: no registry, simple route for domain '%s'", domain)
            return RoutingNode(domain=domain, subdomain="default", children=[])

        # With registry, look up domain
        from compoctopus.registry import RegisteredDomain
        reg_domain = None
        for d in self._registry.list_domains():
            if d.name == domain:
                reg_domain = d
                break

        if reg_domain is None:
            logger.debug("Onionmorph: domain '%s' not in registry, default route", domain)
            return RoutingNode(domain=domain, subdomain="default", children=[])

        # Match subdomains by keyword overlap with task description
        desc_words = set(task_spec.description.lower().split())
        matched_subs = []
        for sub in (reg_domain.subdomains or []):
            sub_words = set(sub.lower().split("_"))
            if sub_words & desc_words:
                matched_subs.append(sub)

        # If no subdomain matches, use "default"
        if not matched_subs:
            matched_subs = ["default"]

        children = [
            RoutingNode(domain=domain, subdomain=sub, children=[])
            for sub in matched_subs
        ]

        logger.info(
            "Onionmorph: domain '%s' → subdomains %s",
            domain, matched_subs,
        )
        return RoutingNode(domain=domain, subdomain="root", children=children)

    def detect_cross_domain(self, task_spec: TaskSpec) -> List[str]:
        """Detect if a task spans multiple domains.

        Uses domain_hints from TaskSpec first, then falls back to
        registry-based keyword matching if available.
        """
        # Explicit domain hints always take priority
        if task_spec.domain_hints:
            return list(task_spec.domain_hints)

        # Without registry, default to 'general'
        if self._registry is None:
            return ["general"]

        # Score each registered domain by keyword overlap
        desc_words = set(task_spec.description.lower().split())
        scored = []
        for d in self._registry.list_domains():
            domain_words = set(d.description.lower().split()) if d.description else set()
            overlap = len(desc_words & domain_words)
            if overlap > 0:
                scored.append((d.name, overlap))

        # Sort by score descending
        scored.sort(key=lambda x: -x[1])

        if scored:
            logger.debug(
                "Onionmorph: domain scores = %s",
                [(name, score) for name, score in scored[:5]],
            )
            return [name for name, _ in scored]

        return ["general"]
