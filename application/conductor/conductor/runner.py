"""Runner: orchestrates scientific method phases using connector + researcher SDNAC.

Three execution modes (same as original Observatory):
- run_one_step: Execute single phase, advance
- run_with_proposal_gate: Run until PROPOSAL, pause for human approval
- run_autonomous: Full cycle, auto-approve proposals
"""

from typing import Any, Dict

from .connector import GrugConnector
from .state_machine import StateMachine


class Runner:
    """Orchestrates the research loop.

    Researcher SDNAC does thinking (per phase).
    Connector handles code execution (when experiment phase needs Grug).
    State machine tracks phase transitions.
    """

    def __init__(self, connector: GrugConnector, researcher_sdnac, state: StateMachine):
        self.connector = connector
        self.researcher = researcher_sdnac
        self.state = state

    async def run_one_step(self, hint: str = "") -> Dict[str, Any]:
        """Execute single phase and advance state machine.

        Returns dict with completed phase, next phase, and result context.
        """
        phase_prompt = self._build_phase_prompt(hint)
        ctx = {
            "phase": self.state.phase,
            "iteration": self.state.iteration,
            "hint": hint,
            "phase_prompt": phase_prompt,
            "phase_data": self.state.data,
        }

        result = await self.researcher.execute(ctx)

        if self._needs_grug(result):
            experiment_spec = result.context.get("experiment_spec", "")
            grug_output = await self.connector.send_and_wait(experiment_spec, result.context)
            # Forward Grug results back to researcher for analysis
            analysis_prompt = (
                f"Analyze the experiment results:\n\n{grug_output.get('text', '')}\n\n"
                f"Original spec: {experiment_spec}"
            )
            ctx = {
                **result.context,
                "grug_output": grug_output,
                "phase_prompt": analysis_prompt,
            }
            result = await self.researcher.execute(ctx)

        completed_phase = self.state.phase
        # Store any result data the researcher produced
        if result.context.get("phase_data"):
            for k, v in result.context["phase_data"].items():
                self.state.set_data(k, v)

        next_phase = self.state.next()

        return {
            "completed_phase": completed_phase,
            "next_phase": next_phase,
            "iteration": self.state.iteration,
            "result": result.context,
            "status": result.status.value,
        }

    async def run_with_proposal_gate(self, hint: str = "") -> Dict[str, Any]:
        """Run phases until PROPOSAL, then pause for human approval.

        At PROPOSAL phase:
        - hint="accept" → advance to EXPERIMENT
        - hint="retry:feedback" → stay at PROPOSAL, regenerate
        - hint="quit" → reset to OBSERVE
        """
        if self.state.phase == "proposal":
            if hint.startswith("accept"):
                return await self.run_one_step(hint="accept")
            elif hint.startswith("retry"):
                feedback = hint.split(":", 1)[1] if ":" in hint else ""
                return await self.run_one_step(hint=f"retry:{feedback}")
            elif hint == "quit":
                self.state.phase = "observe"
                self.state.data = {}
                return {"phase": "observe", "status": "quit"}

        # Run phases until we hit proposal
        while self.state.phase != "proposal":
            step_result = await self.run_one_step(hint)
            if step_result["status"] != "success":
                return step_result

        # At proposal — return for human review
        return {
            "phase": "proposal",
            "awaiting_approval": True,
            "proposal": self.state.get_data("proposal"),
            "iteration": self.state.iteration,
        }

    async def run_autonomous(self, max_cycles: int = 1) -> Dict[str, Any]:
        """Full cycle(s), auto-approve proposals.

        Runs observe→hypothesize→proposal(auto)→experiment→analyze
        for max_cycles iterations.
        """
        target_iteration = self.state.iteration + max_cycles

        while self.state.iteration < target_iteration:
            result = await self.run_one_step(hint="auto_approve")
            if result["status"] not in ("success", "blocked"):
                return result

        return {
            "status": "cycles_complete",
            "iterations_completed": max_cycles,
            "final_iteration": self.state.iteration,
        }

    def _needs_grug(self, result) -> bool:
        """Check if researcher wants code execution."""
        return (
            self.state.phase == "experiment"
            and result.context.get("needs_grug", False)
        )

    def _build_phase_prompt(self, hint: str) -> str:
        """Build phase-specific prompt for researcher."""
        phase = self.state.phase
        iteration = self.state.iteration

        base = f"You are in the {phase.upper()} phase (iteration {iteration}).\n\n"

        prompts = {
            "observe": "Survey the current state. What do you see? What patterns emerge? Record observations.",
            "hypothesize": "Based on observations, form a testable hypothesis. What do you predict?",
            "proposal": "Write a research proposal for testing this hypothesis. Include methodology and expected results.",
            "experiment": "Design and specify the experiment. Set needs_grug=True in phase_data if code execution is needed.",
            "analyze": "Analyze the results. What worked? What didn't? What's next?",
        }

        prompt = base + prompts.get(phase, "")
        if hint:
            prompt += f"\n\nHint: {hint}"
        return prompt
