"""
FlightSim Core Functions - STARSHIP Flight Config + HEAVEN Prompt System

Core business logic for FlightSim operations without MCP wrapper.
Can be tested independently and imported by MCP wrapper.
"""

import logging
from typing import Dict, Any

from .flight_simulation import FlightSimSystem
from .models import FlightSimVars
from .models import FlightSim, FlightSimError

# Setup logging
logger = logging.getLogger(__name__)

# Create FlightSim system
flightsim_system = FlightSimSystem()

# CORE FUNCTIONS
# ==============

def generate_mission_brief(flightsim_name: str, vars: 'FlightSimVars') -> Dict[str, Any]:
    """Generate mission brief file for subagent delegation."""
    logger.info(f"Generating mission brief for FlightSim: {flightsim_name}")
    
    try:
        result = flightsim_system.generate_mission_brief(flightsim_name, **vars.model_dump())
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to generate mission brief: {e}", exc_info=True)
        return {
            "error": f"Failed to generate mission brief: {str(e)}",
            "flightsim_name": flightsim_name,
            "context": vars.model_dump()
        }

def add_flightsim(
    name: str,
    flight_config_name: str,
    heaven_prompt_step_data: Dict[str, Any],
    description: str = "",
    category: str = "general"
) -> str:
    """Add new FlightSim model."""
    logger.info(f"Adding FlightSim: {name}")
    
    try:
        flightsim = FlightSim(
            name=name,
            flight_config_name=flight_config_name,
            heaven_prompt_step=heaven_prompt_step_data,
            description=description,
            category=category
        )
        
        flightsim_system.add_flightsim(flightsim)
        return f"Successfully added FlightSim: {name}"
        
    except Exception as e:
        logger.error(f"Failed to add FlightSim {name}: {e}", exc_info=True)
        return f"Failed to add FlightSim {name}: {str(e)}"

def get_flightsim(name: str) -> Dict[str, Any]:
    """Get specific FlightSim model."""
    logger.info(f"Getting FlightSim: {name}")
    
    try:
        flightsim = flightsim_system.get_flightsim(name)
        return flightsim.model_dump()
    except Exception as e:
        logger.error(f"Failed to get FlightSim {name}: {e}", exc_info=True)
        return {"error": f"Failed to get FlightSim {name}: {str(e)}"}

def list_flightsims() -> Dict[str, Any]:
    """
    List all FlightSim models.
    
    Returns:
        Dict with available FlightSims and their metadata
    """
    logger.info("Listing FlightSims")
    
    try:
        return flightsim_system.list_flightsims()
    except Exception as e:
        logger.error(f"Failed to list FlightSims: {e}", exc_info=True)
        return {"error": f"Failed to list FlightSims: {str(e)}"}

def update_flightsim(
    name: str,
    flight_config_name: str = None,
    heaven_prompt_step_data: Dict[str, Any] = None,
    description: str = None,
    category: str = None
) -> str:
    """
    Update existing FlightSim model.
    
    Args:
        name: Name of FlightSim to update
        flight_config_name: New flight config name (optional)
        heaven_prompt_step_data: New HEAVEN prompt step (optional)
        description: New description (optional)
        category: New category (optional)
        
    Returns:
        Success/failure message
    """
    logger.info(f"Updating FlightSim: {name}")
    
    try:
        # Get existing FlightSim
        existing_flightsim = flightsim_system.get_flightsim(name)
        
        # Update fields that were provided
        update_data = existing_flightsim.model_dump()
        
        if flight_config_name is not None:
            update_data["flight_config_name"] = flight_config_name
        if heaven_prompt_step_data is not None:
            update_data["heaven_prompt_step"] = heaven_prompt_step_data
        if description is not None:
            update_data["description"] = description
        if category is not None:
            update_data["category"] = category
        
        # Create updated FlightSim
        updated_flightsim = FlightSim(**update_data)
        
        # Save updated FlightSim
        flightsim_system.update_flightsim(updated_flightsim)
        
        return f"Successfully updated FlightSim: {name}"
        
    except Exception as e:
        logger.error(f"Failed to update FlightSim {name}: {e}", exc_info=True)
        return f"Failed to update FlightSim {name}: {str(e)}"

def delete_flightsim(name: str) -> str:
    """
    Delete FlightSim model.
    
    Args:
        name: Name of FlightSim to delete
        
    Returns:
        Success/failure message
    """
    logger.info(f"Deleting FlightSim: {name}")
    
    try:
        flightsim_system.delete_flightsim(name)
        return f"Successfully deleted FlightSim: {name}"
        
    except Exception as e:
        logger.error(f"Failed to delete FlightSim {name}: {e}", exc_info=True)
        return f"Failed to delete FlightSim {name}: {str(e)}"

def get_flightsims_by_category(category: str) -> Dict[str, Any]:
    """
    Get FlightSims filtered by category.
    
    Args:
        category: Category to filter by
        
    Returns:
        Dict with FlightSims in the specified category
    """
    logger.info(f"Getting FlightSims for category: {category}")
    
    try:
        return flightsim_system.get_flightsims_by_category(category)
    except Exception as e:
        logger.error(f"Failed to get FlightSims by category {category}: {e}", exc_info=True)
        return {"error": f"Failed to get FlightSims by category {category}: {str(e)}"}