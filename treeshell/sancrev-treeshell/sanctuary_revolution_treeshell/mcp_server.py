"""Sanctuary Revolution TreeShell MCP Server."""
import json
import logging
import os
import traceback
from enum import Enum
from pathlib import Path
from typing import Sequence, Dict, Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.shared.exceptions import McpError

from sanctuary_revolution_treeshell import SancrevTreeShell
from heaven_tree_repl import render_response

logger = logging.getLogger(__name__)


class TreeShellTools(str, Enum):
    RUN_CONVERSATION_SHELL = "run_conversation_shell"


class SancrevTreeshellMCPServer:
    """MCP Server for Sanctuary Revolution TreeShell."""

    def __init__(self):
        self.shell = None

    def _find_user_config(self, heaven_data_dir: str) -> str:
        """Find user config directory in HEAVEN_DATA_DIR."""
        try:
            if not os.path.exists(heaven_data_dir):
                return None
            for item in os.listdir(heaven_data_dir):
                if item.startswith("sancrev_treeshell"):
                    item_path = os.path.join(heaven_data_dir, item)
                    if os.path.isdir(item_path):
                        configs_path = os.path.join(item_path, 'configs')
                        if os.path.exists(configs_path):
                            return configs_path
            return None
        except Exception:
            return None

    def _generate_boot_skills(self) -> None:
        """Auto-generate understand skills from strata MCP registrations with what/when fields.

        Reads ~/.config/strata/servers.json, finds MCPs with what/when metadata,
        writes SkillSpec-typed concept files to CartON queue dir.
        CartON worker picks them up and creates concepts in Neo4j.
        Substrate projector handles skill package creation separately.
        """
        import uuid
        from datetime import datetime

        strata_path = os.path.expanduser("~/.config/strata/servers.json")
        if not os.path.exists(strata_path):
            logger.info("No strata servers.json found, skipping boot skill generation")
            return

        try:
            with open(strata_path, 'r') as f:
                strata_config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read strata config: {e}")
            return

        # Strata wraps servers under mcp.servers
        servers = strata_config.get("mcp", {}).get("servers", {})
        if not servers:
            servers = strata_config.get("servers", {})

        heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
        queue_dir = os.path.join(heaven_data, "carton_queue")
        os.makedirs(queue_dir, exist_ok=True)

        queued = 0
        for server_name, server_config in servers.items():
            what = server_config.get("what")
            when = server_config.get("when")
            if not what or not when:
                continue

            # Normalize concept name: Mcp_Skill_Carton, Mcp_Skill_Starlog, etc.
            normalized = server_name.replace('-', '_').replace(' ', '_')
            parts = normalized.split('_')
            concept_name = "Mcp_Skill_" + '_'.join(p.capitalize() for p in parts)

            description = (
                f"MCP shim skill for {server_name}. "
                f"WHAT: {what} "
                f"WHEN: {when} "
                f"ACCESS: Via sancrev-treeshell GNOSYS nodes (connect '{server_name}' first) "
                f"or direct MCP tool calls."
            )

            concept_data = {
                "raw_concept": True,
                "concept_name": concept_name,
                "description": description,
                "relationships": [
                    {"relationship": "is_a", "related": ["Mcp_Shim_Skill"]},
                    {"relationship": "part_of", "related": ["Strata_Mcp_Skills"]},
                    {"relationship": "instantiates", "related": ["Mcp_Shim_Skill_Pattern"]},
                    {"relationship": "has_what", "related": [what[:80]]},
                    {"relationship": "has_when", "related": [when[:80]]}
                ],
                "desc_update_mode": "replace",
                "hide_youknow": True
            }

            # Write to queue with _concept.json suffix (worker recognizes this format)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:8]
            filename = f"{timestamp}_{short_uuid}_concept.json"
            filepath = os.path.join(queue_dir, filename)

            with open(filepath, 'w') as f:
                json.dump(concept_data, f, indent=2)
            queued += 1

        if queued:
            logger.info(f"Boot skill generator: queued {queued} MCP concepts to CartON")

    # TODO: Same pattern for family→skill generation:
    # def _generate_family_skills(self) -> None:
    #     """Auto-generate understand skills from loaded family JSONs."""
    #     Read self.shell families → for each family → create understand skill
    #     describing domain coordinates and navigation.

    async def _restore_persona(self):
        """Restore persisted persona on MCP startup."""
        from sanctuary_revolution_treeshell.persona_manager import PersonaManager
        mgr = PersonaManager()
        result = await mgr.restore_on_startup()
        if result:
            logger.info(f"Persona restored on startup: {result.get('persona', '?')} ({len(result.get('equipped_skills', []))} skills)")

    async def run_conversation_shell(self, command: str) -> dict:
        if not self.shell:
            try:
                heaven_data = os.getenv("HEAVEN_DATA_DIR", "/tmp/heaven_data")
                os.environ["HEAVEN_DATA_DIR"] = heaven_data
                os.makedirs(heaven_data, exist_ok=True)
                user_config_path = self._find_user_config(heaven_data)
                self.shell = SancrevTreeShell(user_config_path=user_config_path)
            except Exception as e:
                logger.error(f"Shell initialization failed: {traceback.format_exc()}")
                return {"success": False, "error": f"Shell failed to initialize: {e}"}

            # Boot skill generation — separate from shell init so failures don't crash shell
            try:
                self._generate_boot_skills()
            except Exception as e:
                logger.warning(f"Boot skill generation failed (non-fatal): {e}")

            # Restore persisted persona (skillset + MCP set + mirror to Claude skills dir)
            try:
                await self._restore_persona()
            except Exception as e:
                logger.warning(f"Persona restore failed (non-fatal): {e}")

            # Process management handled by start_sancrev.sh, not treeshell MCP

        try:
            result = await self.shell.handle_command(command)
            rendered_output = render_response(result)

            # Auto-connect retry: if GNOSYS returns "not connected", connect and retry once
            if "not connected" in rendered_output and "manage_servers" in rendered_output:
                import re
                import asyncio
                match = re.search(r"'(\w+)' not connected", rendered_output)
                if match:
                    server_name = match.group(1)
                    logger.info(f"Auto-connecting '{server_name}' and retrying...")
                    await self.shell.handle_command(f'manage_servers.exec {{"connect": "{server_name}"}}')
                    # Wait for connection to establish, then retry once
                    await asyncio.sleep(15)
                    try:
                        result = await self.shell.handle_command(command)
                        rendered_output = render_response(result)
                        if "not connected" in rendered_output:
                            rendered_output = f"Auto-connect '{server_name}' timed out. Try again or connect manually."
                    except Exception:
                        rendered_output = f"Auto-connect '{server_name}' failed. Try again or connect manually."

            return {
                "success": True,
                "command": command,
                "rendered_output": rendered_output,
                "raw_result": result
            }
        except Exception as e:
            logger.error(f"Command execution failed: {traceback.format_exc()}")
            return {"success": False, "error": f"Error executing command '{command}': {str(e)}"}


async def serve() -> None:
    server = Server("sanctuary-revolution-treeshell")
    shell_server = SancrevTreeshellMCPServer()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=TreeShellTools.RUN_CONVERSATION_SHELL.value,
                description="""Sanctuary Revolution TreeShell - Unified interface (Game + Builders + GNOSYS + Skills).

Navigation:
- 'nav' — Full tree with coordinates
- 'jump <node_name>' — Go to node by full name or numeric coordinate
- 'back' — Go up one level
- 'menu' — Show current position menu

Execution:
- '<node>.exec {"arg": "val"}' — Jump + execute (e.g., 'equip.exec {"name": "my-skill"}')
- 'exec {"args"}' — Execute at current position

Addressing (valid inputs only):
- Full node name: 'agent_management_equipment'
- Numeric coordinate: '0.2.1'
- Registered shortcut: 'nav', 'lang', 'brain', etc.
- Bare words that aren't any of the above are INVALID

Chains (sequential execution with data flow):
- 'chain step1 {} -> step2 {"data": "$step1_result"}' — pipe results between steps
- Data variables: $step1_result, $step2_result, $last_result

Control flow:
- 'and' — also execute with existing data
- 'or' — alternative execute
- 'if condition then ... else ...' — conditional
- 'while condition x body' — loop
- 'for variable in collection x body' — iterate

Shortcuts:
- 'lang' — Full language reference + active shortcuts
- 'shortcut <alias> <coordinate>' — Create jump shortcut
- 'shortcut <alias> "<chain>"' — Create chain shortcut

=== Game (jump game) ===
new_game(player_name) | select_player(player_name) | game_status | list_players | stack_status

=== SANCTUM Builder (jump sanctum) - Life Architecture ===
sanctum_new(name, description) | sanctum_select(name) | sanctum_which | sanctum_list | sanctum_status
sanctum_add_ritual(name, description, domain, frequency, duration_minutes)
sanctum_add_goal(name, description, domain) | sanctum_add_boundary(name, description, domain, rule)
sanctum_update_domain(domain, score) | sanctum_gear_status | sanctum_check_complete
sanctum_create_mvs(mvs_name) | sanctum_create_journey(journey_name) | sanctum_check_vec

=== PAIAB Builder (jump paiab) - AI Agent Components ===
paiab_new(name, description) | paiab_select(name) | paiab_which | paiab_list
paiab_add_skill(name, domain, category, description) | paiab_add_mcp(name, description)
paiab_add_hook(name, hook_type, description) | paiab_add_agent(name, description)
paiab_add_flight(name, domain, description) | paiab_add_persona(name, domain, description, frame)
paiab_list_components(comp_type) | paiab_advance_tier(comp_type, name, fulfillment) | paiab_gear_status

=== CAVE Builder (jump cave) - Business System ===
cave_new(name, description) | cave_select(name) | cave_which | cave_list | cave_status
cave_set_identity(who_am_i, cta, twitter_bio, linkedin_bio, about_short, brand_name)
cave_init_value_ladder(name, description) | cave_add_offer(name, description, stage, price)
cave_list_offers | cave_add_journey(title, domain, obstacle, solution, transformation)
cave_list_journeys(domain) | cave_add_framework(name, domain, problem_pattern, solution_pattern, implementation)
cave_list_frameworks(domain) | cave_update_metrics(mrr, subscribers)

=== Journey/MVS/VEC (jump journey | mvs | vec) ===
create_journey(name, description, origin_situation, revelation, stages)
create_mvs(name, journey_name, description, rituals, boundaries, structures)
create_vec(name, journey_name, mvs_name, agent_name, description)
list_journeys | list_mvs | list_vecs | complete_journey | mark_mvs_viable | deploy_agent

=== Skills (jump skills) ===
list_skills | list_domains | list_by_domain(domain) | get_skill(name) | search_skills(query)
create_skill → [MENU] choose type:
  create_understand(name, domain, content, what, when) - UNDERSTAND: pure context for discussion/recall
  create_single_turn(name, domain, content, what, when) - SINGLE_TURN: context + immediate action
  create_preflight(name, domain, content, what, when) - PREFLIGHT: primes for work, points to flight
equip(name) | unequip(name) | unequip_all | list_equipped | get_equipped_content
list_skillsets | create_skillset(name, domain, description, skills) | add_to_skillset
match_skilllog(prediction)

=== Personas ===
list_personas | create_persona(name, domain, description, frame) | equip_persona(name)
get_active_persona | deactivate_persona

=== GNOSYS MCP Router (jump gnosys) ===
discover_server_actions(user_query) | execute_action(server_name, action_name, body_schema)
get_action_details(server_name, action_name) | manage_servers | search_mcp_catalog(query)""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "TreeShell command: 'nav' to see tree, 'jump <id>' to navigate, '<id>.exec {\"arg\": \"value\"}' to execute"
                        }
                    },
                    "required": ["command"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
        try:
            match name:
                case TreeShellTools.RUN_CONVERSATION_SHELL.value:
                    command = arguments.get("command", "")
                    result = await shell_server.run_conversation_shell(command)

                    if result.get("success"):
                        output_text = result.get("rendered_output", "No output available")
                    else:
                        output_text = f"Error: {result.get('error', 'Unknown error')}"

                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=output_text)]

        except Exception as e:
            logger.error(f"Tool call failed: {traceback.format_exc()}")
            raise ValueError(f"Error processing TreeShell operation: {str(e)}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    import asyncio
    asyncio.run(serve())
