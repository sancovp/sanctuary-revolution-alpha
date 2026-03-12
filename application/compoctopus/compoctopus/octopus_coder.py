"""BACKWARD COMPAT SHIM — imports from new locations.

All code has moved to:
    CompoctopusAgent        → compoctopus.agent
    make_octopus_coder      → compoctopus.agents.octopus_coder
    make_planner            → compoctopus.agents.planner
    make_mermaid_maker      → compoctopus.agents.mermaid_maker
    compile                 → compoctopus.compile
    CodeCompiler            → compoctopus.agents.octopus_coder

TODO: Remove this file once all external imports are updated.
"""

# Re-export everything from new locations
from compoctopus.agent import CompoctopusAgent
from compoctopus.agents.octopus_coder.factory import make_octopus_coder, CodeCompiler
from compoctopus.agents.planner.factory import make_planner
from compoctopus.compile import compile

# Prompt constants (if anything imports these directly)
from compoctopus.agents.octopus_coder.prompts import (
    OCTO_SYNTAX_REFERENCE,
    CODER_STATE_INSTRUCTIONS,
)
from compoctopus.agents.planner.prompts import (
    PLANNER_MERMAID,
    PLANNER_SYSTEM_PROMPT,
)

__all__ = [
    "CompoctopusAgent",
    "make_octopus_coder",
    "make_planner",
    "compile",
    "CodeCompiler",
    "OCTO_SYNTAX_REFERENCE",
    "CODER_STATE_INSTRUCTIONS",
    "PLANNER_MERMAID",
    "PLANNER_SYSTEM_PROMPT",
]
