"""Conductor: Orchestration agent on SDNA substrate, registered in CAVE."""

from .connector import GrugConnector, SDNACConnector, ClaudePConnector
from .state_machine import StateMachine
from .runner import Runner
from .agents import make_grug_sdnac, make_researcher_sdnac
from .config import PHASES
from .conductor import Conductor
from .cave_registration import (
    ConductorConfig,
    register_conductor_in_cave,
    get_conductor_anatomy_access,
    get_conductor_system_prompt,
)

__all__ = [
    "GrugConnector",
    "SDNACConnector",
    "ClaudePConnector",
    "StateMachine",
    "Runner",
    "make_grug_sdnac",
    "make_researcher_sdnac",
    "PHASES",
    "ConductorConfig",
    "register_conductor_in_cave",
    "get_conductor_anatomy_access",
    "get_conductor_system_prompt",
    "Conductor",
]
