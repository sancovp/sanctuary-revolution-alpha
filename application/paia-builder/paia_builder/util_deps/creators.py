"""Component creation helpers."""

from typing import Optional, List, Dict

from ..models import (
    SkillSpec, SkillCategory, MCPSpec, HookSpec, HookType,
    SlashCommandSpec, AgentSpec, AgentModel, AgentPermissionMode,
    PersonaSpec, PluginSpec, FlightSpec,
    MetastackSpec, GIINTBlueprintSpec, OperadicFlowSpec,
    FrontendIntegrationSpec, AutomationSpec,
    AgentGANSpec, AgentDUOSpec, AgentGANInitiator,
    SystemPromptSpec, SystemPromptType, SystemPromptSectionType,
    SystemPromptSection, SystemPromptConfig,
)


def create_skill_spec(name: str, domain: str, category: str, description: str,
                      subdomain: Optional[str] = None, **kwargs) -> SkillSpec:
    return SkillSpec(name=name, domain=domain, subdomain=subdomain,
                     category=SkillCategory(category), description=description, **kwargs)


def create_mcp_spec(name: str, description: str, **kwargs) -> MCPSpec:
    return MCPSpec(name=name, description=description,
                   args=kwargs.pop("args", []), env=kwargs.pop("env", {}),
                   tools=kwargs.pop("tools", []), **kwargs)


def create_hook_spec(name: str, hook_type: str, description: str) -> HookSpec:
    return HookSpec(name=name, hook_type=HookType(hook_type), description=description)


def create_command_spec(name: str, description: str, argument_hint: Optional[str] = None) -> SlashCommandSpec:
    return SlashCommandSpec(name=name, description=description, argument_hint=argument_hint)


def create_agent_spec(name: str, description: str, model: str = "sonnet",
                      permission_mode: str = "default", **kwargs) -> AgentSpec:
    return AgentSpec(name=name, description=description, model=AgentModel(model),
                     permission_mode=AgentPermissionMode(permission_mode),
                     tools=kwargs.pop("tools", []), disallowed_tools=kwargs.pop("disallowed_tools", []),
                     skills=kwargs.pop("skills", []), **kwargs)


def create_persona_spec(name: str, domain: str, description: str, frame: str, **kwargs) -> PersonaSpec:
    return PersonaSpec(name=name, domain=domain, description=description, frame=frame, **kwargs)


def create_plugin_spec(name: str, description: str, git_url: Optional[str] = None) -> PluginSpec:
    return PluginSpec(name=name, description=description, git_url=git_url)


def create_flight_spec(name: str, domain: str, description: str, **kwargs) -> FlightSpec:
    return FlightSpec(name=name, domain=domain, description=description, **kwargs)


def create_metastack_spec(name: str, domain: str, description: str, **kwargs) -> MetastackSpec:
    return MetastackSpec(name=name, domain=domain, description=description,
                         fields=kwargs.pop("fields", []), **kwargs)


def create_giint_blueprint_spec(name: str, domain: str, description: str, **kwargs) -> GIINTBlueprintSpec:
    return GIINTBlueprintSpec(name=name, domain=domain, description=description, **kwargs)


def create_operadic_flow_spec(name: str, domain: str, description: str, **kwargs) -> OperadicFlowSpec:
    return OperadicFlowSpec(name=name, domain=domain, description=description,
                            vendored_to=kwargs.pop("vendored_to", []), **kwargs)


def create_frontend_integration_spec(name: str, integration_type: str, description: str, **kwargs) -> FrontendIntegrationSpec:
    return FrontendIntegrationSpec(name=name, integration_type=integration_type, description=description, **kwargs)


def create_automation_spec(name: str, platform: str, description: str, **kwargs) -> AutomationSpec:
    return AutomationSpec(name=name, platform=platform, description=description,
                          triggers=kwargs.pop("triggers", []), **kwargs)


def create_agent_gan_spec(name: str, description: str, initiator: str,
                          agents: List[str], agent_roles: Dict[str, str]) -> AgentGANSpec:
    if len(agents) != 2:
        raise ValueError("Agent GAN requires exactly 2 agents")
    return AgentGANSpec(name=name, description=description, initiator=AgentGANInitiator(initiator),
                        agents=agents, agent_roles=agent_roles)


def create_agent_duo_spec(name: str, description: str, initiator: str,
                          challenger: str, generator: str) -> AgentDUOSpec:
    return AgentDUOSpec(name=name, description=description, initiator=AgentGANInitiator(initiator),
                        challenger=challenger, generator=generator)


def create_system_prompt_spec(name: str, description: str, prompt_type: str, **kwargs) -> SystemPromptSpec:
    return SystemPromptSpec(name=name, description=description, prompt_type=SystemPromptType(prompt_type), **kwargs)


def create_system_prompt_config(name: str, prompt_type: str, required_sections: List[str],
                                optional_sections: Optional[List[str]] = None, **kwargs) -> SystemPromptConfig:
    return SystemPromptConfig(name=name, prompt_type=SystemPromptType(prompt_type),
                              required_sections=[SystemPromptSectionType(s) for s in required_sections],
                              optional_sections=[SystemPromptSectionType(s) for s in (optional_sections or [])], **kwargs)


def create_system_prompt_section(section_type: str, tag_name: str, content: str, order: int = 0) -> SystemPromptSection:
    return SystemPromptSection(section_type=SystemPromptSectionType(section_type),
                               tag_name=tag_name, content=content, order=order)
