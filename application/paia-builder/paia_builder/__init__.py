"""PAIA Builder - Full GEAR state machine for Personal AI Agents."""

from .models import (
    PAIA, GEAR, GEARDimension, VersionEntry, PAIAForkType,
    AchievementTier, GoldenStatus, GamePhase,
    ComponentStatus, SkillCategory, HookType, AgentModel, AgentPermissionMode,
    SkillSpec, MCPSpec, HookSpec, SlashCommandSpec,
    AgentSpec, AgentForkType, PersonaSpec, PluginSpec, FlightSpec,
    MetastackSpec, GIINTBlueprintSpec, OperadicFlowSpec,
    FrontendIntegrationSpec, AutomationSpec,
    AgentGANSpec, AgentDUOSpec, AgentGANInitiator,
    SystemPromptSpec, SystemPromptType, SystemPromptSectionType,
    SystemPromptSection, SystemPromptConfig,
    TIER_POINTS, LEVEL_THRESHOLDS, calculate_level
)
from .core import PAIABuilder

__all__ = [
    "PAIABuilder",
    "PAIA", "GEAR", "GEARDimension", "VersionEntry", "PAIAForkType",
    "AchievementTier", "GoldenStatus", "GamePhase",
    "ComponentStatus", "SkillCategory", "HookType", "AgentModel", "AgentPermissionMode",
    "SkillSpec", "MCPSpec", "HookSpec", "SlashCommandSpec",
    "AgentSpec", "AgentForkType", "PersonaSpec", "PluginSpec", "FlightSpec",
    "MetastackSpec", "GIINTBlueprintSpec", "OperadicFlowSpec",
    "FrontendIntegrationSpec", "AutomationSpec",
    "AgentGANSpec", "AgentDUOSpec", "AgentGANInitiator",
    "SystemPromptSpec", "SystemPromptType", "SystemPromptSectionType",
    "SystemPromptSection", "SystemPromptConfig",
    "TIER_POINTS", "LEVEL_THRESHOLDS", "calculate_level"
]

__version__ = "0.8.0"
