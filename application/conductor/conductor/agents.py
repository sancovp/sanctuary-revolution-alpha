"""SDNAC factories for Grug and Researcher agents.

Each agent is exactly 1 SDNAC. No inflation.
System prompts are passed in — not baked here.
"""

from sdna import sdnac, ariadne, default_config
from .config import GRUG_MODEL, RESEARCHER_MODEL


def make_grug_sdnac(system_prompt: str, model: str = GRUG_MODEL):
    """SmartGrug as SDNAC. Code execution agent.

    Args:
        system_prompt: Full system prompt for Grug.
        model: Model to use. Default MiniMax.

    Returns:
        SDNAC with goal template expecting {task} in context.
    """
    config = default_config(
        name="grug",
        goal="{task}",
        system_prompt=system_prompt,
        max_turns=10,
        model=model,
        backend="minimax",
    )
    return sdnac("grug", ariadne("grug_prep"), config)


def make_researcher_sdnac(system_prompt: str, model: str = RESEARCHER_MODEL):
    """Dr. Randy BrainBrane as SDNAC. Research orchestration agent.

    Args:
        system_prompt: Full system prompt for Researcher.
        model: Model to use. Default MiniMax.

    Returns:
        SDNAC with goal template expecting {phase_prompt} in context.
    """
    config = default_config(
        name="researcher",
        goal="{phase_prompt}",
        system_prompt=system_prompt,
        max_turns=10,
        model=model,
        backend="minimax",
    )
    return sdnac("researcher", ariadne("researcher_prep"), config)
