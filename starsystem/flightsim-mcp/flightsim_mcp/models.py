"""FlightSim MCP data models using Pydantic."""

from typing import Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from heaven_base.tool_utils.prompt_injection_system_vX1 import PromptStepDefinitionVX1


class FlightSim(BaseModel):
    """FlightSim model: combines STARSHIP flight config with HEAVEN prompt step"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = Field(description="Unique name for this FlightSim")
    flight_config_name: str = Field(description="STARSHIP flight config to execute")
    heaven_prompt_step: PromptStepDefinitionVX1 = Field(description="Additional PIS prompt step")
    description: str = Field(default="", description="Human-readable description")
    category: str = Field(default="general", description="Category for organization")


class MissionBriefResult(BaseModel):
    """Result of mission brief file generation"""
    
    mission_file: str = Field(description="Path to generated mission brief file")
    instruction: str = Field(description="Standardized instruction for subagent delegation")
    flightsim_name: str = Field(description="Name of FlightSim used")
    context_vars: Dict[str, Any] = Field(description="Context variables used")
    
    
class FlightSimVars(BaseModel):
    """Flexible model for FlightSim template variables"""
    
    model_config = ConfigDict(extra="allow")
    
    starlog_project_path: str = Field(description="Required STARLOG project path for subagent operations")
        

class FlightSimInput(BaseModel):
    """Input model for generate_mission_brief with typed context variables"""
    
    flightsim_name: str = Field(description="Name of the FlightSim to use")
    vars: FlightSimVars = Field(default_factory=FlightSimVars, description="Template variables for the HEAVEN prompt")


class FlightSimError(Exception):
    """Custom exception for FlightSim operations"""
    pass