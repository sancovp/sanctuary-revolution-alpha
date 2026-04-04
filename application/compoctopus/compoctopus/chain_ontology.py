"""Chain Ontology — re-exported from SDNA.

The canonical definitions of Link, Chain, EvalChain, ConfigLink, LinkConfig,
LinkResult, LinkStatus live in SDNA's chain_ontology.

Compoctopus adds:
  - FunctionLink: wraps a plain Python function as a Link (for mechanical steps)

SDNAC(Link) is imported from sdna.sdna directly when needed.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

# Re-export everything from SDNA's chain_ontology
from sdna.chain_ontology import (
    Link,
    Chain,
    EvalChain,
    ConfigLink,
    LinkConfig,
    LinkResult,
    LinkStatus,
    Compiler,
)

# Also make DovetailModel available from here for convenience
from sdna.config import DovetailModel, HermesConfigInput


# =============================================================================
# FunctionLink(Link) — mechanical step, no LLM
# =============================================================================

class FunctionLink(Link):
    """A Link that wraps a plain Python function.

    Used for mechanical steps that don't need an LLM:
    - ANNEAL: annealer.anneal() — regex + dedent
    - VERIFY: pytest runner — deterministic check

    The function receives the context dict and returns an updated context dict.
    If it raises, the Link returns ERROR status.

    Usage:
        anneal_link = FunctionLink("anneal", annealer.anneal)
        verify_link = FunctionLink("verify", run_pytest)
    """

    def __init__(self, link_name: str, fn: Callable, description: str = ""):
        self._name = link_name
        self.fn = fn
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Execute the wrapped function with context.

        If fn is async, await it. If sync, call it directly.
        fn(ctx) -> ctx (updated dict) or None (in-place mutation).
        """
        ctx = dict(context) if context else {}

        try:
            if asyncio.iscoroutinefunction(self.fn):
                result_ctx = await self.fn(ctx)
            else:
                result_ctx = self.fn(ctx)

            if result_ctx is not None:
                ctx = result_ctx

            return LinkResult(status=LinkStatus.SUCCESS, context=ctx)
        except Exception as e:
            return LinkResult(
                status=LinkStatus.ERROR,
                context=ctx,
                error=f"FunctionLink '{self.name}' failed: {e}",
            )

    def describe(self, depth: int = 0) -> str:
        indent = "  " * depth
        desc = f'FunctionLink "{self.name}"'
        if self._description:
            desc += f" — {self._description}"
        return f"{indent}{desc}"
