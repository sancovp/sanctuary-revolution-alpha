"""Treeshell functions for unified persona activation.

These replace the broken equip_persona/deactivate_persona from skill_manager
with versions that actually activate MCP sets.
"""

import asyncio
from typing import Dict, Any
from sanctuary_revolution_treeshell.persona_manager import PersonaManager


# Global persona manager instance
_persona_manager = None


def _get_persona_manager() -> PersonaManager:
    """Get or create global persona manager instance."""
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager()
    return _persona_manager


async def equip_persona_unified(name: str, agent_id: str = "") -> str:
    """Equip a persona WITH MCP set activation.

    This is the FIXED version that actually activates MCP sets.

    Args:
        name: Persona name (e.g., "gnosys")
        agent_id: Optional agent ID (not yet implemented for persona_manager)

    Returns:
        Formatted activation report
    """
    mgr = _get_persona_manager()

    # Await async activation
    result = await mgr.activate_persona(name)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [f"✅ Persona '{name}' FULLY activated:"]
    lines.append(f"   Frame: loaded")
    lines.append(f"   Identity: {result['carton_identity']}")

    # Skillset activation
    if result.get('skillset'):
        skillset_info = result['skillset']
        if isinstance(skillset_info, dict) and 'equipped_skills' in skillset_info:
            skills = ', '.join(skillset_info['equipped_skills'][:5])
            if len(skillset_info['equipped_skills']) > 5:
                skills += f" ... ({len(skillset_info['equipped_skills'])} total)"
            lines.append(f"   Skillset: ✓ {skills}")
        else:
            lines.append(f"   Skillset: {skillset_info}")

    # MCP set activation (THE FIX)
    if result.get('mcp_set'):
        mcp_info = result['mcp_set']
        if mcp_info.get('status') == 'activated':
            lines.append(f"   MCP Set: ✓ '{mcp_info['name']}' ACTIVATED")
        elif mcp_info.get('status') == 'failed':
            lines.append(f"   MCP Set: ✗ '{mcp_info['name']}' FAILED - {mcp_info.get('error', 'unknown error')}")
        else:
            lines.append(f"   MCP Set: {mcp_info}")

    # Missing components
    if result.get('missing'):
        lines.append("\n⚠️  Missing (aspirational):")
        for m in result['missing']:
            lines.append(f"     ✗ {m.get('type', 'unknown')}: {m.get('name', 'unknown')}")

    lines.append(f"\n--- Frame Preview ---")
    frame = result.get('frame_content', '')
    lines.append(frame[:200] + "..." if len(frame) > 200 else frame)

    return "\n".join(lines)


async def deactivate_persona_unified() -> str:
    """Deactivate current persona AND disconnect MCP set.

    This is the FIXED version that actually disconnects MCP sets.
    """
    mgr = _get_persona_manager()

    # Await async deactivation
    result = await mgr.deactivate_persona()

    if result.get('status') == 'no_active_persona':
        return "No active persona to deactivate."

    if result.get('status') == 'partial_deactivation':
        return f"⚠️  Partial deactivation of '{result['persona']}': {result['error']}"

    if result.get('status') == 'deactivated':
        return f"✅ Deactivated persona '{result['persona']}' (skills unequipped, MCP set disconnected)"

    return f"Unknown result: {result}"


def get_active_persona_unified() -> str:
    """Get currently active persona name."""
    mgr = _get_persona_manager()
    persona_name = mgr.get_active_persona()

    if persona_name:
        return f"Active persona: {persona_name}"
    else:
        return "No active persona."
