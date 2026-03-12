"""Unified persona activation: skillset + MCP set + frame.

Personas bundle three things:
1. Skillset (via skillmanager)
2. MCP set (via strata/gnosys)
3. Frame (identity prompt)

Previously equip_persona() only activated skillset. Now we activate ALL components.
"""

from typing import Dict, Any, Optional
from skill_manager.core import SkillManager
from strata.treeshell_functions import manage_servers


class PersonaManager:
    """Unified persona activation manager."""

    def __init__(self):
        self.skillmanager = SkillManager()

    async def activate_persona(self, persona_name: str) -> Dict[str, Any]:
        """Complete persona activation.

        Args:
            persona_name: Name of persona to activate (e.g., "gnosys")

        Returns:
            Activation report with:
            - persona: name
            - frame: loaded status + content
            - skillset: activation result
            - mcp_set: activation result
            - carton_identity: identity name
            - missing: list of missing skills
            - equipped_skills: list of equipped skills
        """
        # 1. Get persona from skillmanager
        persona = self.skillmanager.get_persona(persona_name)
        if not persona:
            return {"error": f"Persona '{persona_name}' not found"}

        report = {
            "persona": persona_name,
            "frame": "loaded",
            "frame_content": persona.frame,
            "mcp_set": None,
            "skillset": None,
            "carton_identity": persona.carton_identity,
            "missing": [],
            "equipped_skills": []
        }

        # 2. Equip skillset via skillmanager
        if persona.skillset:
            skillset_result = self.skillmanager.equip_skillset(persona.skillset)
            report["skillset"] = skillset_result
            if "missing" in skillset_result:
                report["missing"] = skillset_result["missing"]
            if "equipped_skills" in skillset_result:
                report["equipped_skills"] = skillset_result["equipped_skills"]

        # 3. Activate MCP set via strata (NEW - this is the fix)
        if persona.mcp_set:
            try:
                mcp_result = await manage_servers(connect_set=persona.mcp_set)
                report["mcp_set"] = {
                    "name": persona.mcp_set,
                    "status": "activated",
                    "result": mcp_result
                }
            except Exception as e:
                report["mcp_set"] = {
                    "name": persona.mcp_set,
                    "status": "failed",
                    "error": str(e)
                }

        # 4. Set active persona in skillmanager
        self.skillmanager.active_persona = persona

        return report

    def get_active_persona(self) -> Optional[str]:
        """Get currently active persona name."""
        if self.skillmanager.active_persona:
            return self.skillmanager.active_persona.name
        return None

    async def deactivate_persona(self) -> Dict[str, Any]:
        """Deactivate current persona.

        Unequips all skills and disconnects MCP set.
        """
        if not self.skillmanager.active_persona:
            return {"status": "no_active_persona"}

        persona_name = self.skillmanager.active_persona.name
        mcp_set_name = self.skillmanager.active_persona.mcp_set

        # Unequip all skills
        self.skillmanager.unequip_all()

        # Disconnect MCP set if one was active
        if mcp_set_name:
            try:
                await manage_servers(disconnect_set=mcp_set_name)
            except Exception as e:
                return {
                    "status": "partial_deactivation",
                    "persona": persona_name,
                    "error": f"Failed to disconnect MCP set: {e}"
                }

        # Clear active persona
        self.skillmanager.active_persona = None

        return {
            "status": "deactivated",
            "persona": persona_name
        }
