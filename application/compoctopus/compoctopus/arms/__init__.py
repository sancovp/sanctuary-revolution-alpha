"""Compiler arms — the 7 arms of the Compoctopus.

Each arm is a CA (CompoctopusAgent) with its own SM.
Each arm package has the invariant shape:
    __init__.py   ← exports the make_*() factory
    prompts.py    ← per-state goal prompts + system prompt
    factory.py    ← make_*() factory that returns a CompoctopusAgent

Every arm CALLS worker CAs (from agents/) to do the LLM work.
Every arm IS what the Bandit CONSTRUCTs.
"""

from compoctopus.arms.chain_compiler import make_chain_compiler
from compoctopus.arms.agent_config import make_agent_config_compiler
from compoctopus.arms.mcp_compiler import make_mcp_compiler
from compoctopus.arms.skill import make_skill_compiler
from compoctopus.arms.system_prompt import make_system_prompt_compiler
from compoctopus.arms.input_prompt import make_input_prompt_compiler
from compoctopus.arms.reviewer import ReviewerCompiler

__all__ = [
    "make_chain_compiler",
    "make_agent_config_compiler",
    "make_mcp_compiler",
    "make_skill_compiler",
    "make_system_prompt_compiler",
    "make_input_prompt_compiler",
    "ReviewerCompiler",
]
