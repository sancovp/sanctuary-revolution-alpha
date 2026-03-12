#!/usr/bin/env python3
"""
FlightSim MCP Server - Thin wrapper around FlightSim core functions
"""

import logging
from fastmcp import FastMCP
import flightsim_mcp as flightsim_lib
from .models import FlightSimVars

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize MCP
app = FastMCP("FLIGHTSIM")

@app.tool()
def generate_mission_brief(flightsim_name: str, vars: dict):
    """Generate mission brief file for subagent delegation."""
    logger.debug(f"MCP: generate_mission_brief called with flightsim_name={flightsim_name}")
    # Convert dict to FlightSimVars
    vars_model = FlightSimVars(**vars)
    return flightsim_lib.generate_mission_brief(flightsim_name, vars_model)

@app.tool()
def add_flightsim(name: str, flight_config_name: str, heaven_prompt_step_data: dict, description: str = "", category: str = "general"):
    """Add new FlightSim model."""
    return flightsim_lib.add_flightsim(name, flight_config_name, heaven_prompt_step_data, description, category)

@app.tool()
def get_flightsim(name: str):
    """Get specific FlightSim model."""
    return flightsim_lib.get_flightsim(name)

@app.tool()
def list_flightsims():
    """List all FlightSim models."""
    return flightsim_lib.list_flightsims()

@app.tool()
def update_flightsim(name: str, flight_config_name: str = None, heaven_prompt_step_data: dict = None, description: str = None, category: str = None):
    """Update existing FlightSim model."""
    return flightsim_lib.update_flightsim(name, flight_config_name, heaven_prompt_step_data, description, category)

@app.tool()
def delete_flightsim(name: str):
    """Delete FlightSim model."""
    return flightsim_lib.delete_flightsim(name)

@app.tool()
def get_flightsims_by_category(category: str):
    """Get FlightSims filtered by category."""
    return flightsim_lib.get_flightsims_by_category(category)

def main():
    """Main entry point for the FlightSim MCP server."""
    app.run()

if __name__ == "__main__":
    main()