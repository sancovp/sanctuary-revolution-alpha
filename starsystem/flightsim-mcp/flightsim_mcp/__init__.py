"""
FlightSim MCP - Systematic Subagent Delegation System

Provides systematic mission brief generation for subagent delegation using
HEAVEN PIS vX1 templating system and flight simulation templates.
"""

from .flightsim_core import (
    generate_mission_brief,
    add_flightsim,
    get_flightsim,
    list_flightsims,
    update_flightsim,
    delete_flightsim,
    get_flightsims_by_category
)

__version__ = "0.1.0"
__all__ = [
    "generate_mission_brief",
    "add_flightsim", 
    "get_flightsim",
    "list_flightsims",
    "update_flightsim",
    "delete_flightsim",
    "get_flightsims_by_category"
]