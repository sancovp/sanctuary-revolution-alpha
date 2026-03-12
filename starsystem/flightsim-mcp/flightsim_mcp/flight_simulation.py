"""Core FlightSim business logic."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

from heaven_base.baseheavenagent import HeavenAgentConfig, ProviderEnum
from heaven_base.tool_utils.prompt_injection_system_vX1 import (
    PromptInjectionSystemVX1, PromptInjectionSystemConfigVX1
)
from heaven_base.registry.registry_service import RegistryService

from .models import FlightSim, MissionBriefResult, FlightSimError

logger = logging.getLogger(__name__)


class FlightSimSystem:
    """FlightSim system for systematic subagent delegation."""
    
    def __init__(self):
        self.heaven_data_dir = os.environ.get('HEAVEN_DATA_DIR', '/tmp/heaven_data')
        self.mission_dir = "/tmp/mission_briefs"
        self.registry_name = "flightsims"
        self.registry_service = RegistryService()
        
    def _get_base_agent_config(self) -> HeavenAgentConfig:
        """Create base agent config for PIS reference resolution."""
        return HeavenAgentConfig(
            name="FlightSimAgent",
            system_prompt="",
            provider=ProviderEnum.OPENAI,
            model="gpt-4o-mini",
            temperature=0.0
        )
    
    def _render_heaven_prompt(self, flightsim: FlightSim, context: Dict[str, Any]) -> str:
        """Render the HEAVEN prompt step using PIS."""
        pis_config = PromptInjectionSystemConfigVX1(
            steps=[flightsim.heaven_prompt_step],
            template_vars=context,
            agent_config=self._get_base_agent_config()
        )
        
        pis = PromptInjectionSystemVX1(pis_config)
        rendered_prompt = pis.get_next_prompt()
        
        if not rendered_prompt:
            raise FlightSimError(f"Failed to render HEAVEN prompt for FlightSim: {flightsim.name}")
        
        return rendered_prompt
    
    def _write_mission_file(self, content: str, flightsim_name: str) -> str:
        """Write mission content to file with unique timestamp and return path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        filename = f"{timestamp}_{flightsim_name}_mission_brief.md"
        mission_path = os.path.join(self.mission_dir, filename)
        os.makedirs(self.mission_dir, exist_ok=True)
        
        with open(mission_path, 'w') as f:
            f.write(content)
        
        return mission_path
    
    def generate_mission_brief(self, flightsim_name: str, **context) -> MissionBriefResult:
        """Generate mission brief file combining flight config + rendered HEAVEN prompt."""
        
        # 1. Get FlightSim model
        flightsim = self.get_flightsim(flightsim_name)
        
        # 2. Render the HEAVEN prompt step with context
        rendered_heaven_prompt = self._render_heaven_prompt(flightsim, context)
        
        # 3. Create mission content: flight config instruction + rendered prompt
        starlog_path = context.get('starlog_project_path', 'MISSING_STARLOG_PATH')
        mission_content = f"""start_waypoint_journey(config_path="{flightsim.flight_config_name}", starlog_path="{starlog_path}")

{rendered_heaven_prompt}"""
        
        # 4. Write to file
        mission_path = self._write_mission_file(mission_content, flightsim_name)
        
        logger.info(f"Generated mission brief for FlightSim '{flightsim_name}' at {mission_path}")
        
        # 5. Return result
        return MissionBriefResult(
            mission_file=mission_path,
            instruction=f"Tell the subagent to read the file at {mission_path}",
            flightsim_name=flightsim_name,
            context_vars=context
        )
    
    # CRUD operations for FlightSim models
    
    def _save_flightsim_to_registry(self, operation: str, flightsim: FlightSim):
        """Common logic for saving FlightSim to registry."""
        if operation == "add":
            self.registry_service.add(self.registry_name, flightsim.name, flightsim.model_dump(mode='json'))
        elif operation == "update":
            self.registry_service.update(self.registry_name, flightsim.name, flightsim.model_dump(mode='json'))
    
    def add_flightsim(self, flightsim: FlightSim):
        """Add FlightSim model to registry."""
        self._save_flightsim_to_registry("add", flightsim)
        logger.info(f"Added FlightSim: {flightsim.name}")
    
    def get_flightsim(self, name: str) -> FlightSim:
        """Get FlightSim model from registry."""
        flightsim_data = self.registry_service.get(self.registry_name, name)
        if flightsim_data is None:
            raise FlightSimError(f"FlightSim '{name}' not found")
        return FlightSim(**flightsim_data)
    
    def list_flightsims(self) -> Dict[str, Any]:
        """List all FlightSim models."""
        result = self.registry_service.get_all(self.registry_name)
        if result is None:
            return {}
        return result
    
    def update_flightsim(self, flightsim: FlightSim):
        """Update existing FlightSim model."""
        self._save_flightsim_to_registry("update", flightsim)
        logger.info(f"Updated FlightSim: {flightsim.name}")
    
    def delete_flightsim(self, name: str):
        """Delete FlightSim model from registry."""
        self.registry_service.delete(self.registry_name, name)
        logger.info(f"Deleted FlightSim: {name}")
    
    def get_flightsims_by_category(self, category: str) -> Dict[str, Any]:
        """Get FlightSims filtered by category."""
        all_flightsims = self.list_flightsims()
        return {
            name: flightsim 
            for name, flightsim in all_flightsims.items() 
            if flightsim.get("category") == category
        }