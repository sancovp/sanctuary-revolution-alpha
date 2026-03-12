"""PAIA Builder Core - LIBRARY FACADE.

Thin wrapper over utils. No logic here - pure delegation.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

# Optional EventRouter support for GEAR events
try:
    from sanctuary_revolution.harness.events.gear_events import (
        emit_gear_state, emit_dimension_update, emit_level_up, emit_tier_advanced,
        GEARDimensionType,
    )
    GEAR_EVENTS_AVAILABLE = True
except ImportError:
    GEAR_EVENTS_AVAILABLE = False

from .models import (
    PAIA, AchievementTier, GoldenStatus, ExperienceEventType,
    SkillSpec, MCPSpec, HookSpec, SlashCommandSpec, AgentSpec, PersonaSpec,
    PluginSpec, FlightSpec, MetastackSpec, GIINTBlueprintSpec, OperadicFlowSpec,
    FrontendIntegrationSpec, AutomationSpec, AgentGANSpec, AgentDUOSpec,
    SystemPromptSpec, SystemPromptSection, SystemPromptConfig, VersionEntry,
    # For field setters
    SkillResourceSpec, OnionLayerSpec, MCPToolSpec, FlightStepSpec, MetastackFieldSpec,
)
from . import utils


class PAIABuilder:
    """Builder for PAIA. LIBRARY FACADE over utils."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = utils.get_storage_dir(storage_dir)
        self._router = None  # Optional EventRouter for GEAR events

    def set_router(self, router) -> None:
        """Set EventRouter for GEAR event emission.

        Args:
            router: EventRouter instance from sanctuary_revolution
        """
        self._router = router

    def _emit_gear_state(self, paia: PAIA) -> None:
        """Emit full GEAR state if router is set."""
        if self._router and GEAR_EVENTS_AVAILABLE:
            emit_gear_state(self._router, paia.name, paia.gear_state)

    def _emit_dimension_update(self, paia: PAIA, dimension: str, old_score: int, new_score: int, note: Optional[str] = None) -> None:
        """Emit dimension update if router is set."""
        if self._router and GEAR_EVENTS_AVAILABLE:
            dim_type = GEARDimensionType(dimension) if dimension in [d.value for d in GEARDimensionType] else None
            if dim_type:
                emit_dimension_update(self._router, paia.name, dim_type, old_score, new_score, note)

    def _emit_level_up(self, paia: PAIA, old_level: int, new_level: int) -> None:
        """Emit level up if router is set."""
        if self._router and GEAR_EVENTS_AVAILABLE:
            emit_level_up(self._router, paia.name, old_level, new_level)

    def _emit_tier_advanced(self, paia: PAIA, comp_type: str, name: str, old_tier: str, new_tier: str) -> None:
        """Emit tier advancement if router is set."""
        if self._router and GEAR_EVENTS_AVAILABLE:
            emit_tier_advanced(self._router, paia.name, comp_type, name, old_tier, new_tier)

    # Selection
    def select(self, name: str) -> str:
        if not utils.get_paia_path(self.storage_dir, name).exists():
            return f"[HIEL] Vehicle '{name}' not found. Check seam."
        utils.save_current_name(self.storage_dir, name)
        return f"[VEHICLE] Pilot aboard {name}."

    def which(self) -> str:
        name = utils.load_current_name(self.storage_dir)
        if not name:
            return "[HIEL] No Vehicle. Pilot not aboard."
        paia = utils.load_paia(self.storage_dir, name)
        if not paia:
            return f"[HIEL] Vehicle '{name}' lost. Seam broken."
        return f"[VEHICLE] {name} | L{paia.gear_state.level} {paia.gear_state.phase.value}"

    def _ensure_current(self) -> PAIA:
        name = utils.load_current_name(self.storage_dir)
        if not name:
            raise ValueError("[HIEL] No Vehicle selected. Pilot must board first.")
        paia = utils.load_paia(self.storage_dir, name)
        if not paia:
            raise ValueError(f"[HIEL] Vehicle '{name}' not found. Seam integrity compromised.")
        return paia

    def _save(self, paia: PAIA, emit_state: bool = False) -> None:
        """Save PAIA and optionally emit gear state event.

        Args:
            paia: PAIA to save
            emit_state: If True, emit full gear state after save (default False to avoid spam)
        """
        utils.save_paia(self.storage_dir, paia)
        if emit_state:
            self._emit_gear_state(paia)

    # PAIA Management
    def new(self, name: str, description: str, git_dir: Optional[str] = None,
            source_dir: Optional[str] = None, init_giint: bool = True) -> str:
        if utils.get_paia_path(self.storage_dir, name).exists():
            return f"[HIEL] Vehicle '{name}' already exists. Choose different hull designation."
        paia = utils.create_paia(name, description, git_dir, source_dir)
        self._save(paia)
        utils.save_current_name(self.storage_dir, name)
        msgs = [f"[VEHICLE] {name} initialized. Hull ready for subsystems."]
        if git_dir:
            Path(git_dir).mkdir(parents=True, exist_ok=True)
            utils.init_project_structure(Path(git_dir), name, description)
            import shutil
            shutil.copy(utils.get_paia_path(self.storage_dir, name), Path(git_dir) / "paia.json")
            msgs.append(f"[VEHICLE] Hangar established: {git_dir}")
            if init_giint and utils.GIINT_AVAILABLE:
                result = utils.init_giint_project(name, git_dir)
                msgs.append("[MISSION CONTROL] GIINT tracking online" if result.get("success") else f"[HIEL] GIINT failed: {result.get('error')}")
        return "\n".join(msgs)

    def list_paias(self) -> List[Dict[str, Any]]:
        return utils.list_all_paias(self.storage_dir)

    def delete(self, name: str) -> str:
        if not utils.delete_paia(self.storage_dir, name):
            return f"[HIEL] Vehicle '{name}' not found. Nothing to decommission."
        if utils.load_current_name(self.storage_dir) == name:
            utils.get_config_path(self.storage_dir).unlink(missing_ok=True)
        return f"[VEHICLE] {name} decommissioned. Hull scrapped."

    def fork_paia(self, source_name: str, new_name: str, fork_type: str = "child",
                  description: Optional[str] = None, git_dir: Optional[str] = None,
                  init_giint: bool = True) -> str:
        source = utils.load_paia(self.storage_dir, source_name)
        if not source:
            return f"[HIEL] Source Vehicle '{source_name}' not found. Cannot clone."
        if utils.get_paia_path(self.storage_dir, new_name).exists():
            return f"[HIEL] Vehicle '{new_name}' already exists. Choose different hull designation."
        forked = utils.fork_paia(source, new_name, fork_type, description, git_dir)
        self._save(forked)
        utils.save_current_name(self.storage_dir, new_name)
        msgs = [f"[VEHICLE] Cloned {source_name} → {new_name} ({fork_type})", f"[VEHICLE] Inherited {len(utils.get_all_components(forked))} subsystems"]
        if git_dir:
            Path(git_dir).mkdir(parents=True, exist_ok=True)
            utils.init_project_structure(Path(git_dir), new_name, forked.description)
            if init_giint and utils.GIINT_AVAILABLE:
                utils.init_giint_project(new_name, git_dir)
        return "\n".join(msgs)

    def tick_version(self, new_version: str, new_description: Optional[str] = None) -> str:
        paia = self._ensure_current()
        paia.version_history.append(VersionEntry(version=paia.version, description=paia.description))
        old = paia.version
        paia.version = new_version
        if new_description:
            paia.description = new_description
        self._save(paia)
        return f"[VEHICLE] {paia.name} upgraded: {old} → {new_version}"

    # Component Management
    def list_components(self, comp_type: str) -> List[Dict[str, Any]]:
        paia = self._ensure_current()
        return [{"name": c.name, "tier": c.tier.value, "golden": c.golden.value,
                 "points": c.points, "description": c.description[:50]} for c in getattr(paia, comp_type, [])]

    def get_component(self, comp_type: str, name: str) -> Dict[str, Any]:
        comp = utils.find_component(self._ensure_current(), comp_type, name)
        if not comp:
            return {"error": f"[HIEL] Subsystem {comp_type}/{name} not found in Vehicle."}
        return {"name": comp.name, "description": comp.description, "tier": comp.tier.value,
                "golden": comp.golden.value, "points": comp.points, "notes": comp.notes}

    def remove_component(self, comp_type: str, name: str) -> str:
        paia = self._ensure_current()
        comps = getattr(paia, comp_type, [])
        for i, c in enumerate(comps):
            if c.name == name:
                comps.pop(i)
                self._save(paia)
                return f"[VEHICLE] Subsystem {comp_type}/{name} removed from hull."
        return f"[HIEL] Subsystem {comp_type}/{name} not found in Vehicle."

    def _after_add(self, paia: PAIA, comp_type: str, name: str, spec: Any = None) -> None:
        # E produces G: log experience event for every component added
        utils.log_experience(
            paia, ExperienceEventType.COMPONENT_ADDED,
            component_type=comp_type, component_name=name,
            details=f"[VEHICLE] Subsystem {comp_type}/{name} installed",
            gear_context=f"{comp_type}:{name}",
            achievement_context="[TOWERING] Working toward COMMON tier",
        )
        if paia.git_dir:
            utils.update_construction_docs(paia, comp_type, name)
            if utils.GIINT_AVAILABLE:
                # Interactive giint building: component + deliverables + spec attachment
                utils.add_component(paia.name, comp_type, name)
                # Add type-specific deliverables
                deliverable_adders = {
                    "skills": utils.add_skill_deliverables,
                    "mcps": utils.add_mcp_deliverables,
                    "hooks": utils.add_hook_deliverables,
                    "commands": utils.add_command_deliverables,
                    "agents": utils.add_agent_deliverables,
                    "personas": utils.add_persona_deliverables,
                    "plugins": utils.add_plugin_deliverables,
                    "flights": utils.add_flight_deliverables,
                    "metastacks": utils.add_metastack_deliverables,
                    "automations": utils.add_automation_deliverables,
                }
                if comp_type in deliverable_adders:
                    deliverable_adders[comp_type](paia.name, name)
                # Attach spec JSON if provided
                if spec:
                    utils.attach_spec_to_component(paia.name, comp_type, name, spec.model_dump(), paia.git_dir)

    # Component Addition (delegated to utils.create_*)
    # Pattern: create spec → append → log experience → save
    def add_skill(self, name: str, domain: str, category: str, description: str, **kw) -> SkillSpec:
        paia = self._ensure_current()
        spec = utils.create_skill_spec(name, domain, category, description, **kw)
        paia.skills.append(spec)
        self._after_add(paia, "skills", name, spec)
        self._save(paia)
        return spec

    def add_mcp(self, name: str, description: str, **kw) -> MCPSpec:
        paia = self._ensure_current()
        spec = utils.create_mcp_spec(name, description, **kw)
        paia.mcps.append(spec)
        self._after_add(paia, "mcps", name, spec)
        self._save(paia)
        return spec

    def add_hook(self, name: str, hook_type: str, description: str) -> HookSpec:
        paia = self._ensure_current()
        spec = utils.create_hook_spec(name, hook_type, description)
        paia.hooks.append(spec)
        self._after_add(paia, "hooks", name, spec)
        self._save(paia)
        return spec

    def add_command(self, name: str, description: str, argument_hint: Optional[str] = None) -> SlashCommandSpec:
        paia = self._ensure_current()
        spec = utils.create_command_spec(name, description, argument_hint)
        paia.commands.append(spec)
        self._after_add(paia, "commands", name, spec)
        self._save(paia)
        return spec

    def add_agent(self, name: str, description: str, **kw) -> AgentSpec:
        paia = self._ensure_current()
        spec = utils.create_agent_spec(name, description, **kw)
        paia.agents.append(spec)
        self._after_add(paia, "agents", name, spec)
        self._save(paia)
        return spec

    def fork_agent(self, source_name: str, new_name: str, fork_type: str = "child",
                   description: Optional[str] = None) -> AgentSpec:
        paia = self._ensure_current()
        spec = utils.fork_agent(paia, source_name, new_name, fork_type, description)
        paia.agents.append(spec)
        self._save(paia)
        return spec

    def add_persona(self, name: str, domain: str, description: str, frame: str, **kw) -> PersonaSpec:
        paia = self._ensure_current()
        spec = utils.create_persona_spec(name, domain, description, frame, **kw)
        paia.personas.append(spec)
        self._after_add(paia, "personas", name, spec)
        self._save(paia)
        return spec

    def add_plugin(self, name: str, description: str, git_url: Optional[str] = None) -> PluginSpec:
        paia = self._ensure_current()
        spec = utils.create_plugin_spec(name, description, git_url)
        paia.plugins.append(spec)
        self._after_add(paia, "plugins", name, spec)
        self._save(paia)
        return spec

    def add_flight(self, name: str, domain: str, description: str, **kw) -> FlightSpec:
        paia = self._ensure_current()
        spec = utils.create_flight_spec(name, domain, description, **kw)
        paia.flights.append(spec)
        self._after_add(paia, "flights", name, spec)
        self._save(paia)
        return spec

    def add_metastack(self, name: str, domain: str, description: str, **kw) -> MetastackSpec:
        paia = self._ensure_current()
        spec = utils.create_metastack_spec(name, domain, description, **kw)
        paia.metastacks.append(spec)
        self._after_add(paia, "metastacks", name, spec)
        self._save(paia)
        return spec

    def add_giint_blueprint(self, name: str, domain: str, description: str, **kw) -> GIINTBlueprintSpec:
        paia = self._ensure_current()
        spec = utils.create_giint_blueprint_spec(name, domain, description, **kw)
        paia.giint_blueprints.append(spec)
        self._after_add(paia, "giint_blueprints", name, spec)
        self._save(paia)
        return spec

    def add_operadic_flow(self, name: str, domain: str, description: str, **kw) -> OperadicFlowSpec:
        paia = self._ensure_current()
        spec = utils.create_operadic_flow_spec(name, domain, description, **kw)
        paia.operadic_flows.append(spec)
        self._after_add(paia, "operadic_flows", name, spec)
        self._save(paia)
        return spec

    def add_frontend_integration(self, name: str, integration_type: str, description: str, **kw) -> FrontendIntegrationSpec:
        paia = self._ensure_current()
        spec = utils.create_frontend_integration_spec(name, integration_type, description, **kw)
        paia.frontend_integrations.append(spec)
        self._after_add(paia, "frontend_integrations", name, spec)
        self._save(paia)
        return spec

    def add_automation(self, name: str, platform: str, description: str, **kw) -> AutomationSpec:
        paia = self._ensure_current()
        spec = utils.create_automation_spec(name, platform, description, **kw)
        paia.automations.append(spec)
        self._after_add(paia, "automations", name, spec)
        self._save(paia)
        return spec

    def add_agent_gan(self, name: str, description: str, initiator: str,
                      agents: List[str], agent_roles: Dict[str, str]) -> AgentGANSpec:
        paia = self._ensure_current()
        spec = utils.create_agent_gan_spec(name, description, initiator, agents, agent_roles)
        paia.agent_gans.append(spec)
        self._after_add(paia, "agent_gans", name)
        self._save(paia)
        return spec

    def add_agent_duo(self, name: str, description: str, initiator: str,
                      challenger: str, generator: str) -> AgentDUOSpec:
        paia = self._ensure_current()
        spec = utils.create_agent_duo_spec(name, description, initiator, challenger, generator)
        paia.agent_duos.append(spec)
        self._after_add(paia, "agent_duos", name)
        self._save(paia)
        return spec

    def add_system_prompt(self, name: str, description: str, prompt_type: str, **kw) -> SystemPromptSpec:
        paia = self._ensure_current()
        spec = utils.create_system_prompt_spec(name, description, prompt_type, **kw)
        paia.system_prompts.append(spec)
        self._after_add(paia, "system_prompts", name)
        self._save(paia)
        return spec

    def add_system_prompt_config(self, name: str, prompt_type: str,
                                 required_sections: List[str], **kw) -> SystemPromptConfig:
        paia = self._ensure_current()
        config = utils.create_system_prompt_config(name, prompt_type, required_sections, **kw)
        paia.system_prompt_configs.append(config)
        self._save(paia)
        return config

    def add_section_to_prompt(self, prompt_name: str, section_type: str,
                              tag_name: str, content: str, order: int = 0) -> SystemPromptSection:
        paia = self._ensure_current()
        prompt = utils.find_component(paia, "system_prompts", prompt_name)
        if not prompt:
            raise ValueError(f"[HIEL] Prompt subsystem '{prompt_name}' not found in Vehicle.")
        section = utils.create_system_prompt_section(section_type, tag_name, content, order)
        prompt.sections.append(section)
        prompt.updated = datetime.now()
        self._save(paia)
        return section

    # Tier/Golden
    def advance_tier(self, comp_type: str, name: str, fulfillment: str) -> str:
        paia = self._ensure_current()
        comp = utils.find_component(paia, comp_type, name)
        if not comp:
            return f"[HIEL] Subsystem {comp_type}/{name} not found in Vehicle."
        old_tier = comp.tier.value
        old_level = paia.gear_state.level
        success, msg = utils.advance_component_tier(comp, fulfillment)
        if success:
            # E produces G: log experience for tier advancement
            utils.log_experience(
                paia, ExperienceEventType.TIER_ADVANCED,
                component_type=comp_type, component_name=name,
                details=f"[TOWERING] Subsystem {comp_type}/{name}: {old_tier} → {comp.tier.value}",
                gear_context=f"{comp_type}:{name}",
                achievement_context=f"[TOWERING] Layer complete: {comp.tier.value}",
                reality_context=fulfillment,
            )
            self._save(paia)
            # Emit tier advanced event
            self._emit_tier_advanced(paia, comp_type, name, old_tier, comp.tier.value)
            # Check for level up from tier change
            if paia.gear_state.level != old_level:
                self._emit_level_up(paia, old_level, paia.gear_state.level)
            if paia.git_dir:
                utils.update_construction_docs(paia, comp_type, name)
                if utils.GIINT_AVAILABLE:
                    utils.update_giint_task_done(paia.name, comp_type, name, comp.tier.value)
        return msg

    def set_tier(self, comp_type: str, name: str, tier: str, note: Optional[str] = None) -> str:
        paia = self._ensure_current()
        comp = utils.find_component(paia, comp_type, name)
        if not comp:
            return f"[HIEL] Subsystem {comp_type}/{name} not found in Vehicle."
        msg = utils.set_component_tier(comp, AchievementTier(tier), note)
        self._save(paia)
        return msg

    def goldify(self, comp_type: str, name: str, note: Optional[str] = None) -> str:
        paia = self._ensure_current()
        comp = utils.find_component(paia, comp_type, name)
        if not comp:
            return f"[HIEL] Subsystem {comp_type}/{name} not found in Vehicle."
        old_golden = comp.golden.value
        success, msg = utils.advance_golden(comp, note)
        if success:
            # E produces G: log experience for golden advancement
            utils.log_experience(
                paia, ExperienceEventType.GOLDEN_ADVANCED,
                component_type=comp_type, component_name=name,
                details=f"[CROWNING] Subsystem {comp_type}/{name}: {old_golden} → {comp.golden.value}",
                gear_context=f"{comp_type}:{name}",
                achievement_context=f"[CROWNING] Reached {comp.golden.value} status",
                reality_context=note or "validated",
            )
            self._save(paia)
            if paia.git_dir:
                utils.update_construction_docs(paia, comp_type, name)
        return msg

    def regress_golden(self, comp_type: str, name: str, reason: str) -> str:
        paia = self._ensure_current()
        comp = utils.find_component(paia, comp_type, name)
        if not comp:
            return f"[HIEL] Subsystem {comp_type}/{name} not found in Vehicle."
        success, msg = utils.regress_golden(comp, reason)
        if success:
            self._save(paia)
        return msg

    # GEAR/Status
    def update_gear(self, dimension: str, score: int, note: Optional[str] = None) -> str:
        paia = self._ensure_current()
        # Capture old score for event emission
        dim = getattr(paia.gear_state, dimension, None)
        old_score = dim.score if dim else 0
        old_level = paia.gear_state.level
        msg = utils.update_gear_dimension(paia, dimension, score, note)
        self._save(paia)
        # Emit events if router set
        self._emit_dimension_update(paia, dimension, old_score, score, note)
        if paia.gear_state.level != old_level:
            self._emit_level_up(paia, old_level, paia.gear_state.level)
        return msg

    def status(self) -> str:
        paia = self._ensure_current()
        gs = paia.gear_state
        # SOSEEH: Pilot/Vehicle/Mission Control/Loops
        pilot_state = "[PILOT] OVA - Capability manifest" if gs.overall >= 50 else "[PILOT] OVP - Promise declared, building Vehicle"
        vehicle_pct = gs.overall
        vehicle_state = f"[VEHICLE] {vehicle_pct}% constructed"
        mc_state = "[MISSION CONTROL] " + ("Online" if paia.frontend_integrations else "Not established")
        loop_state = "[LOOPS] Default chat loop active"
        return f"{paia.name}\n{pilot_state}\n{vehicle_state}\n{mc_state}\n{loop_state}\n\n{gs.display()}"

    def sync_and_emit_gear(self) -> str:
        """Force sync GEAR state and emit to router.

        Useful for initial state broadcast or after batch operations.
        """
        paia = self._ensure_current()
        utils.sync_gear(paia)
        self._save(paia)
        self._emit_gear_state(paia)
        return f"[VEHICLE] GEAR synced and emitted for {paia.name}"

    def validate_system_prompt(self, prompt_file_path: str, config_name: str) -> Dict[str, Any]:
        return utils.validate_system_prompt(self._ensure_current(), prompt_file_path, config_name)

    def render_system_prompt(self, prompt_name: str) -> str:
        return utils.render_system_prompt(self._ensure_current(), prompt_name)

    # =========================================================================
    # FIELD SETTERS - update spec fields + complete giint tasks
    # =========================================================================

    # --- Skill Field Setters ---
    def set_skill_md(self, skill_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "skills", skill_name)
        if not spec:
            return f"[HIEL] Skill '{skill_name}' not found."
        spec.skill_md = content
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "skills", skill_name, "skill_md", "create_skill_md")
        return f"[VEHICLE] Skill '{skill_name}' SKILL.md set."

    def set_skill_reference(self, skill_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "skills", skill_name)
        if not spec:
            return f"[HIEL] Skill '{skill_name}' not found."
        spec.reference_md = content
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "skills", skill_name, "reference_md", "create_reference_md")
        return f"[VEHICLE] Skill '{skill_name}' reference.md set."

    def add_skill_resource(self, skill_name: str, filename: str, content: str, content_type: str = "markdown") -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "skills", skill_name)
        if not spec:
            return f"[HIEL] Skill '{skill_name}' not found."
        resource = SkillResourceSpec(filename=filename, content=content, content_type=content_type)
        spec.resources.append(resource)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.add_skill_resource_deliverable(paia.name, skill_name, filename)
            utils.complete_task(paia.name, "skills", skill_name, f"resource_{filename}", f"create_resource_{filename}")
        return f"[VEHICLE] Resource '{filename}' added to skill '{skill_name}'."

    def add_skill_script(self, skill_name: str, script_name: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "skills", skill_name)
        if not spec:
            return f"[HIEL] Skill '{skill_name}' not found."
        spec.scripts.append(script_name)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.add_skill_script_deliverable(paia.name, skill_name, script_name)
            utils.complete_task(paia.name, "skills", skill_name, f"script_{script_name}", f"create_script_{script_name}")
        return f"[VEHICLE] Script '{script_name}' added to skill '{skill_name}'."

    def add_skill_template(self, skill_name: str, template_name: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "skills", skill_name)
        if not spec:
            return f"[HIEL] Skill '{skill_name}' not found."
        spec.templates.append(template_name)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.add_skill_template_deliverable(paia.name, skill_name, template_name)
            utils.complete_task(paia.name, "skills", skill_name, f"template_{template_name}", f"create_template_{template_name}")
        return f"[VEHICLE] Template '{template_name}' added to skill '{skill_name}'."

    # --- MCP Field Setters ---
    def set_mcp_server(self, mcp_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "mcps", mcp_name)
        if not spec:
            return f"[HIEL] MCP '{mcp_name}' not found."
        spec.server = OnionLayerSpec(filename="mcp_server.py", layer_type="facade", content=content)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "mcps", mcp_name, "mcp_server", "create_mcp_server_py")
        return f"[VEHICLE] MCP '{mcp_name}' server set."

    def add_mcp_tool(self, mcp_name: str, core_function: str, ai_description: Optional[str] = None) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "mcps", mcp_name)
        if not spec:
            return f"[HIEL] MCP '{mcp_name}' not found."
        tool = MCPToolSpec(core_function=core_function, ai_description=ai_description)
        spec.tools.append(tool)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.add_mcp_tool_deliverable(paia.name, mcp_name, core_function)
            utils.complete_task(paia.name, "mcps", mcp_name, f"tool_{core_function}", f"create_tool_{core_function}")
        return f"[VEHICLE] Tool '{core_function}' added to MCP '{mcp_name}'."

    # --- Hook Field Setters ---
    def set_hook_script(self, hook_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "hooks", hook_name)
        if not spec:
            return f"[HIEL] Hook '{hook_name}' not found."
        spec.script_content = content
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "hooks", hook_name, "script", "create_hook_script")
        return f"[VEHICLE] Hook '{hook_name}' script set."

    # --- Command Field Setters ---
    def set_command_prompt(self, cmd_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "commands", cmd_name)
        if not spec:
            return f"[HIEL] Command '{cmd_name}' not found."
        spec.prompt_content = content
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "commands", cmd_name, "prompt_content", "write_prompt_content")
        return f"[VEHICLE] Command '{cmd_name}' prompt set."

    # --- Agent Field Setters ---
    def set_agent_prompt(self, agent_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "agents", agent_name)
        if not spec:
            return f"[HIEL] Agent '{agent_name}' not found."
        spec.system_prompt = content
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "agents", agent_name, "system_prompt", "write_system_prompt")
        return f"[VEHICLE] Agent '{agent_name}' system prompt set."

    # --- Persona Field Setters ---
    def set_persona_frame(self, persona_name: str, content: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "personas", persona_name)
        if not spec:
            return f"[HIEL] Persona '{persona_name}' not found."
        spec.frame = content
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "personas", persona_name, "frame", "write_frame")
        return f"[VEHICLE] Persona '{persona_name}' frame set."

    # --- Flight Field Setters ---
    def add_flight_step(self, flight_name: str, step_number: int, title: str, instruction: str,
                        skills_to_equip: Optional[List[str]] = None) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "flights", flight_name)
        if not spec:
            return f"[HIEL] Flight '{flight_name}' not found."
        step = FlightStepSpec(
            step_number=step_number, title=title, instruction=instruction,
            skills_to_equip=skills_to_equip or []
        )
        spec.steps.append(step)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.add_flight_step_deliverable(paia.name, flight_name, step_number)
            utils.complete_task(paia.name, "flights", flight_name, f"step_{step_number}", f"create_step_{step_number}")
        return f"[VEHICLE] Step {step_number} added to flight '{flight_name}'."

    # --- Metastack Field Setters ---
    def add_metastack_field(self, metastack_name: str, field_name: str, field_type: str,
                            description: Optional[str] = None, default: Optional[str] = None) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "metastacks", metastack_name)
        if not spec:
            return f"[HIEL] Metastack '{metastack_name}' not found."
        field = MetastackFieldSpec(name=field_name, field_type=field_type, description=description, default=default)
        spec.fields.append(field)
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.add_metastack_field_deliverable(paia.name, metastack_name, field_name)
            utils.complete_task(paia.name, "metastacks", metastack_name, f"field_{field_name}", f"define_field_{field_name}")
        return f"[VEHICLE] Field '{field_name}' added to metastack '{metastack_name}'."

    # --- Automation Field Setters ---
    def set_automation_workflow(self, automation_name: str, workflow_id: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "automations", automation_name)
        if not spec:
            return f"[HIEL] Automation '{automation_name}' not found."
        spec.workflow_id = workflow_id
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "automations", automation_name, "workflow", "create_workflow")
        return f"[VEHICLE] Automation '{automation_name}' workflow set."

    def set_automation_webhook(self, automation_name: str, webhook_url: str) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "automations", automation_name)
        if not spec:
            return f"[HIEL] Automation '{automation_name}' not found."
        spec.webhook_url = webhook_url
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "automations", automation_name, "webhook", "configure_webhook")
        return f"[VEHICLE] Automation '{automation_name}' webhook set."

    # --- Plugin Field Setters ---
    def set_plugin_manifest(self, plugin_name: str, manifest: Dict[str, Any]) -> str:
        paia = self._ensure_current()
        spec = utils.find_component(paia, "plugins", plugin_name)
        if not spec:
            return f"[HIEL] Plugin '{plugin_name}' not found."
        spec.manifest = manifest
        spec.updated = datetime.now()
        self._save(paia)
        if utils.GIINT_AVAILABLE and paia.git_dir:
            utils.complete_task(paia.name, "plugins", plugin_name, "manifest", "create_plugin_manifest")
        return f"[VEHICLE] Plugin '{plugin_name}' manifest set."

    def check_win(self) -> bool:
        paia = self._ensure_current()
        if paia.gear_state.is_constructed and paia.git_dir:
            (Path(paia.git_dir) / "CLAUDE.md").write_text(utils.generate_claude_md(paia))
            utils.update_gear_status_doc(paia)
            return True
        return paia.gear_state.is_constructed

    def publish(self) -> str:
        return utils.publish_paia(self._ensure_current())


# Compilation
from .util_deps.compile import (
    compile_deliverable,
    commit_compilation,
    stop_compilation,
    evolution_cycle,
    CompilationResult,
)

