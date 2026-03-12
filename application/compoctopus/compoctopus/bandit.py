"""Bandit — the SELECT/CONSTRUCT decision layer, implemented as a CA.

The Bandit is a CompoctopusAgent with two states: SELECT and CONSTRUCT.

SELECT state:
  - LLM has tools to browse the registry and golden chains
  - LLM examines what's available for the requested ArmKind
  - Outputs: <SELECT>arm_name</SELECT>  → runtime returns that arm's result
  - Outputs: <SELECT>CONSTRUCT</SELECT> → SM transitions to CONSTRUCT

CONSTRUCT state:
  - Runtime calls the appropriate arm (arm has its own SM)
  - Result comes back as a report
  - SM transitions back to SELECT
  - LLM sees the new result → <SELECT>newly_built</SELECT> → done

The <SELECT> tag is extracted via Heaven's additional_kws mechanism.
Both XML (<SELECT>...</SELECT>) and markdown (```SELECT```) work.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, EvalChain, FunctionLink
from compoctopus.types import ArmKind, PromptSection, SystemPrompt

logger = logging.getLogger(__name__)


# =============================================================================
# Bandit tools — exposed to the LLM via Heaven
# =============================================================================

class BanditTools:
    """Tools the Bandit LLM can call to browse the registry."""

    def __init__(self, registry, rewards, golden_chains):
        self.registry = registry
        self.rewards = rewards
        self.golden_chains = golden_chains

    def query_registry(self, kind: str) -> str:
        """List available arms for an ArmKind."""
        try:
            arm_kind = ArmKind(kind)
        except ValueError:
            return json.dumps({"error": f"Unknown ArmKind: {kind}"})

        arms = self.registry.get_arms_for_kind(arm_kind)
        result = []
        for arm in arms:
            result.append({
                "name": arm.name,
                "description": arm.description,
                "ca_packages": arm.ca_packages,
                "reward": self.rewards.get(arm.name, 0.0),
            })
        return json.dumps({"kind": kind, "arms": result})

    def list_golden_chains(self, kind: str = "") -> str:
        """List cached results in golden chains."""
        chains = {}
        for key, value in self.golden_chains.items():
            if kind and not key.startswith(kind):
                continue
            chains[key] = str(value)[:200]  # truncated preview
        return json.dumps({"golden_chains": chains})

    def list_arm_kinds(self) -> str:
        """List all available ArmKinds."""
        all_arms = self.registry.list_arms()
        result = {}
        for kind, arms in all_arms.items():
            result[kind.value] = [
                {"name": a.name, "reward": self.rewards.get(a.name, 0.0)}
                for a in arms
            ]
        return json.dumps({"arm_kinds": result})


# =============================================================================
# Bandit prompts
# =============================================================================

BANDIT_SYSTEM_PROMPT = """\
You are the Bandit — the head of the Compoctopus. You decide SELECT or CONSTRUCT.

Your job:
1. Look at the task and what ArmKind is needed
2. Browse the registry and golden chains with your tools
3. If a good match exists → SELECT it
4. If nothing exists or nothing is good enough → CONSTRUCT

Output your decision using the <SELECT> tag:
- <SELECT>arm_name_here</SELECT>  → reuse this arm's cached result
- <SELECT>CONSTRUCT</SELECT>      → build a new one

Tools available:
- query_registry(kind) → list arms for an ArmKind
- list_golden_chains(kind) → list cached results
- list_arm_kinds() → overview of everything

Rules:
1. Always query before deciding
2. Prefer arms with positive reward scores
3. If no arms exist for the requested kind → CONSTRUCT
4. After CONSTRUCT completes, you'll be asked to SELECT again
5. One <SELECT> tag per response, always
"""

BANDIT_STATE_INSTRUCTIONS = {
    "SELECT": (
        "Look through the registry and golden chains for the requested ArmKind.\n\n"
        "═══ TASK ═══\n"
        "{original_task}\n\n"
        "═══ ARM KIND NEEDED ═══\n"
        "{arm_kind}\n\n"
        "Use your tools to browse what's available, then output:\n"
        "  <SELECT>arm_name</SELECT>  to reuse an existing arm\n"
        "  <SELECT>CONSTRUCT</SELECT> to build a new one\n"
    ),
    "CONSTRUCT": (
        "Construction in progress. The arm is being built.\n\n"
        "═══ CONSTRUCTION REPORT ═══\n"
        "{construct_report}\n\n"
        "The result has been registered. Transition back to SELECT."
    ),
}


# =============================================================================
# Bandit CA factory
# =============================================================================

def make_bandit(registry, rewards=None, golden_chains=None) -> CompoctopusAgent:
    """Create the Bandit CA.

    Architecture:
        EvalChain(
            flow = Chain([select_sdnac]),
            evaluator = construct_or_done_link,
            max_cycles = 5,
        )

    SELECT SDNAC: LLM browses registry, outputs <SELECT> tag
    construct_or_done: FunctionLink that checks selection:
        - If SELECT → approved=True (done)
        - If CONSTRUCT → run arm, set approved=False (loop)

    Currently: backward-compat SM mode.
    """

    if rewards is None:
        rewards = {}
    if golden_chains is None:
        golden_chains = {}

    # --- Build SELECT SDNAC ---
    try:
        from sdna.sdna import SDNAC
        from sdna.ariadne import AriadneChain, InjectConfig
        from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs

        # Patch poimandres
        try:
            from sdna import poimandres
            from sdna.heaven_runner import heaven_agent_step
            poimandres.agent_step = heaven_agent_step
        except ImportError:
            pass

        select_ariadne = AriadneChain(
            name="bandit_select_ariadne",
            elements=[
                InjectConfig(source="literal", inject_as="instructions",
                             value=BANDIT_STATE_INSTRUCTIONS["SELECT"]),
                InjectConfig(source="context", inject_as="original_task",
                             key="original_task"),
                InjectConfig(source="context", inject_as="arm_kind",
                             key="arm_kind"),
            ],
        )
        select_hermes = HermesConfig(
            name="bandit_select",
            goal=BANDIT_STATE_INSTRUCTIONS["SELECT"],
            backend="heaven",
            model="minimax",
            max_turns=10,
            permission_mode="bypassPermissions",
            heaven_inputs=HeavenInputs(
                agent=HeavenAgentArgs(
                    provider="ANTHROPIC",
                    max_tokens=4000,
                    tools=[],  # BanditTools registered as closured tools
                    additional_kws=["SELECT"],
                    additional_kw_instructions=(
                        "Use the <SELECT> tag to output your selection:\n"
                        "  <SELECT>arm_name</SELECT> to select an existing arm\n"
                        "  <SELECT>CONSTRUCT</SELECT> to build a new one"
                    ),
                ),
            ),
            system_prompt=BANDIT_SYSTEM_PROMPT,
        )
        select_sdnac = SDNAC(name="select", ariadne=select_ariadne, config=select_hermes)
    except ImportError:
        from compoctopus.chain_ontology import ConfigLink, LinkConfig
        select_sdnac = ConfigLink(LinkConfig(
            name="select",
            goal=BANDIT_STATE_INSTRUCTIONS["SELECT"],
            system_prompt=BANDIT_SYSTEM_PROMPT,
            model="minimax",
        ))

    # --- CONSTRUCT evaluator: checks selection, runs arm if needed ---
    def _construct_evaluator(ctx: dict) -> dict:
        """Check the SELECT SDNAC's output and decide done or loop."""
        extracted = ctx.get("extracted_content", {})
        selection = extracted.get("SELECT", "").strip() if extracted else ""
        if not selection:
            # No selection made — loop
            ctx["selection_done"] = False
            return ctx
        if selection == "CONSTRUCT":
            ctx["selection_done"] = False
            ctx["construct_requested"] = True
            return ctx
        # Valid selection
        ctx["selection_done"] = True
        ctx["selected_arm"] = selection
        return ctx

    construct_link = FunctionLink("construct", _construct_evaluator,
                                  "CONSTRUCT/DONE evaluator — checks <SELECT> tag")

    chain = EvalChain(
        chain_name="bandit",
        links=[select_sdnac],
        evaluator=construct_link,
        max_cycles=5,
        approval_key="selection_done",
    )
    return CompoctopusAgent(
        agent_name="bandit",
        chain=chain,
        arm_kind=None,  # Bandit is not an arm — it's the head
        system_prompt=SystemPrompt(sections=[
            PromptSection(
                tag="IDENTITY",
                content="You are the Bandit — the SELECT/CONSTRUCT decision layer.",
            ),
        ]),
    )


# =============================================================================
# Bandit runtime — orchestrates the CA + arm execution
# =============================================================================

@dataclass
class BanditResult:
    """Result of a Bandit run."""
    status: str  # "success", "failed"
    arm_name: str = ""
    arm_kind: Optional[ArmKind] = None
    output: Any = None
    decision: str = ""  # "select" or "construct"


class BanditRuntime:
    """Orchestrates the Bandit CA execution.

    The Bandit CA (LLM) decides SELECT or CONSTRUCT.
    The runtime handles the actual arm execution and Reviewer call.
    """

    def __init__(self, registry):
        self.registry = registry
        self.rewards: Dict[str, float] = {}
        self.golden_chains: Dict[str, Any] = {}

    async def run(self, task: str, kind: ArmKind, ctx: Optional[dict] = None) -> BanditResult:
        """Run the Bandit.

        1. Create the Bandit CA
        2. Run it — LLM browses registry, outputs <SELECT>
        3. If CONSTRUCT → run the arm → Reviewer → register → run Bandit again
        4. If arm_name → return cached/registered result
        """
        ctx = dict(ctx) if ctx else {}
        ctx["original_task"] = task
        ctx["arm_kind"] = kind.value
        ctx["construct_report"] = "(none yet)"

        bandit = make_bandit(self.registry, self.rewards, self.golden_chains)

        # Run the Bandit CA
        result = await bandit.execute(ctx)

        # Extract the <SELECT> tag from the result
        selection = self._extract_selection(result)

        if selection is None:
            return BanditResult(status="failed", arm_kind=kind)

        if selection == "CONSTRUCT":
            # Run the arm
            construct_result = await self._construct(kind, task, ctx)

            if construct_result is not None:
                # Register and run Bandit again (SELECT will find it now)
                task_key = f"{kind.value}:{task[:80]}"
                self.golden_chains[task_key] = construct_result
                return BanditResult(
                    status="success",
                    arm_name=task_key,
                    arm_kind=kind,
                    output=construct_result,
                    decision="construct",
                )
            else:
                return BanditResult(status="failed", arm_kind=kind, decision="construct")

        else:
            # SELECT — look up the result
            if selection in self.golden_chains:
                return BanditResult(
                    status="success",
                    arm_name=selection,
                    arm_kind=kind,
                    output=self.golden_chains[selection],
                    decision="select",
                )
            else:
                logger.warning("Bandit selected '%s' but not in golden chains", selection)
                return BanditResult(status="failed", arm_kind=kind, decision="select")

    def _extract_selection(self, result) -> Optional[str]:
        """Extract <SELECT>...</SELECT> from the Bandit CA's output."""
        import re
        ctx = {}
        if hasattr(result, 'context') and isinstance(result.context, dict):
            ctx = result.context

        # Heaven extracts additional_kws into extracted_content
        extracted = ctx.get("extracted_content", {})
        if "SELECT" in extracted:
            return extracted["SELECT"].strip()

        # Fallback: scan text
        text = ctx.get("text", "")
        match = re.search(r"<SELECT>(.*?)</SELECT>", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return None

    async def _construct(self, kind: ArmKind, task: str, ctx: dict):
        """CONSTRUCT: call an arm, then call the Reviewer arm."""
        candidates = self.registry.get_arms_for_kind(kind)
        if not candidates:
            logger.warning("No arms registered for %s", kind.value)
            return None

        best = max(candidates, key=lambda c: self.rewards.get(c.name, 0.0))
        arm = self._instantiate_arm(best)
        if arm is None:
            return None

        try:
            result = await arm.compile(ctx)
        except Exception as e:
            logger.error("Arm '%s' failed: %s", best.name, e)
            self.rewards[best.name] = self.rewards.get(best.name, 0.0) - 1
            return None

        # Reviewer
        review = await self._review(result, task, kind)

        if review.passed:
            self.rewards[best.name] = self.rewards.get(best.name, 0.0) + 1
            return result
        else:
            self.rewards[best.name] = self.rewards.get(best.name, 0.0) - 1
            return None

    def _instantiate_arm(self, registered_arm):
        """Instantiate a registered arm."""
        if not registered_arm.compiler_class:
            return None
        try:
            module_path, class_name = registered_arm.compiler_class.rsplit(".", 1)
            import importlib
            mod = importlib.import_module(module_path)
            return getattr(mod, class_name)()
        except Exception as e:
            logger.error("Failed to instantiate %s: %s", registered_arm.compiler_class, e)
            return None

    async def _review(self, result, task, kind):
        """Call the Reviewer arm."""
        from compoctopus.arms.reviewer.factory import ReviewerCompiler, ReviewResult
        reviewer = ReviewerCompiler()
        review_ctx = {
            "arm_output": str(result)[:5000],
            "original_task": task,
            "arm_kind": kind.value,
            "attempt": "0",
            "feedback": "(none)",
        }
        try:
            return await reviewer.compile(review_ctx)
        except Exception as e:
            return ReviewResult(passed=True, feedback=f"Reviewer error: {e}")
