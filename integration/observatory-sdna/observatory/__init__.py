"""Observatory-SDNA: Research system as a DUO on MiniMax/Heaven.

The Observatory IS a DUO:
- Ariadne = Researcher (brain, scientific method)
- Poimandres = Grug (hands, code execution)
- OVP = BigBrain Researcher (reviewer)
"""

from .connector import GrugConnector, SDNACConnector, ClaudePConnector
from .state_machine import StateMachine
from .runner import Runner
from .agents import (
    make_grug_sdnac,
    make_researcher_sdnac,
    make_ovp_sdnac,
    make_observatory_duo,
)
from .config import PHASES, DEFAULT_MODEL

__all__ = [
    "GrugConnector",
    "SDNACConnector",
    "ClaudePConnector",
    "StateMachine",
    "Runner",
    "make_grug_sdnac",
    "make_researcher_sdnac",
    "make_ovp_sdnac",
    "make_observatory_duo",
    "PHASES",
    "DEFAULT_MODEL",
]
