"""Ralph — TDD coding agent with context-alignment pre-loading.

Ralph = N independent fresh SDNAC runs over the same workspace.
Each run reads the plan + whatever exists on disk from previous runs.
The fold-over-fold erases pattern violations via MoE lottery.

Entry point: launch_ralph_compoctopus(starsystem_path, code_target, requirements_doc_path)
Direct use: run_ralph(plan_path, workspace, n_runs)
"""

from compoctopus.agents.ralph.factory import run_ralph
from compoctopus.agents.ralph.core import launch_ralph_compoctopus

__all__ = ["run_ralph", "launch_ralph_compoctopus"]
