"""Observatory-SDNA: Research system on MiniMax/Heaven.

Researcher = SDNAC agent with tools (CartON + bash for docker exec into Grug container).
Processes a research queue. Conductor/user review results externally.

Grug = separate SDNAC in repo-lord container. Researcher reaches it via docker exec.
"""

from .agents import make_researcher_sdnac, make_researcher_compoctopus
from .config import PHASES, DEFAULT_MODEL

__all__ = [
    "make_researcher_sdnac",
    "make_researcher_compoctopus",
    "PHASES",
    "DEFAULT_MODEL",
]
