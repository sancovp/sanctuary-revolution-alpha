"""PAIA operations."""

from typing import Optional
from ..models import PAIA, GEAR, PAIAForkType, AgentSpec, AgentForkType, AchievementTier, GoldenStatus
from .components import get_all_components, golden_summary


def create_paia(name: str, description: str, git_dir: Optional[str] = None,
                source_dir: Optional[str] = None) -> PAIA:
    return PAIA(name=name, description=description, git_dir=git_dir, source_dir=source_dir)


def fork_paia(source: PAIA, new_name: str, fork_type: str = "child",
              description: Optional[str] = None, git_dir: Optional[str] = None) -> PAIA:
    """Fork a PAIA - create new PAIA inheriting components."""
    return PAIA(
        name=new_name,
        description=description or f"Fork of {source.name}",
        forked_from_paia=source.name,
        fork_type=PAIAForkType(fork_type),
        git_dir=git_dir,
        skills=[s.model_copy() for s in source.skills],
        mcps=[m.model_copy() for m in source.mcps],
        hooks=[h.model_copy() for h in source.hooks],
        commands=[c.model_copy() for c in source.commands],
        agents=[a.model_copy() for a in source.agents],
        personas=[p.model_copy() for p in source.personas],
        plugins=[p.model_copy() for p in source.plugins],
        flights=[f.model_copy() for f in source.flights],
        metastacks=[m.model_copy() for m in source.metastacks],
        giint_blueprints=[g.model_copy() for g in source.giint_blueprints],
        operadic_flows=[o.model_copy() for o in source.operadic_flows],
        frontend_integrations=[f.model_copy() for f in source.frontend_integrations],
        automations=[a.model_copy() for a in source.automations],
        agent_gans=[g.model_copy() for g in source.agent_gans],
        agent_duos=[d.model_copy() for d in source.agent_duos],
        system_prompts=[s.model_copy() for s in source.system_prompts],
        system_prompt_configs=[c.model_copy() for c in source.system_prompt_configs],
        gear_state=source.gear_state.model_copy() if fork_type == "child" else GEAR(),
    )


def fork_agent(paia: PAIA, source_name: str, new_name: str, fork_type: str = "child",
               description: Optional[str] = None) -> AgentSpec:
    """Fork an agent within a PAIA."""
    source = None
    for a in paia.agents:
        if a.name == source_name:
            source = a
            break
    if not source:
        raise ValueError(f"[HIEL] Subsystem not found: {source_name}. Check seam.")

    return AgentSpec(
        name=new_name,
        description=description or f"Fork of {source_name}",
        tools=source.tools.copy(),
        disallowed_tools=source.disallowed_tools.copy(),
        model=source.model,
        permission_mode=source.permission_mode,
        skills=source.skills.copy(),
        prompt=source.prompt,
        system_prompt_ref=source.system_prompt_ref,
        forked_from=source_name,
        fork_type=AgentForkType(fork_type),
        tier=source.tier,
        golden=source.golden,
    )


def publish_paia(paia: PAIA) -> str:
    """Generate full Vehicle documentation."""
    lines = [f"# {paia.name}", f"> {paia.description}", "", "## [VEHICLE] Hull Status", "```",
             paia.gear_state.display(), "```", "", "## [VEHICLE] Installed Subsystems"]

    def comp_line(c):
        tier_badge = f"[{c.tier.value}]" if c.tier != AchievementTier.NONE else "[--]"
        gold_badge = {"quarantine": "Q", "crystal": "C", "golden": "G"}[c.golden.value]
        return f"- {tier_badge}[{gold_badge}] **{c.name}** - {c.description}"

    for label, attr in [("Skills", "skills"), ("MCPs", "mcps"), ("Hooks", "hooks"),
                        ("Commands", "commands"), ("Agents", "agents"),
                        ("Personas", "personas"), ("Plugins", "plugins"), ("Flights", "flights"),
                        ("Metastacks", "metastacks"), ("GIINT Blueprints", "giint_blueprints"),
                        ("Operadic Flows", "operadic_flows"), ("Frontend Integrations", "frontend_integrations"),
                        ("Automations", "automations"), ("Agent GANs", "agent_gans"),
                        ("Agent DUOs", "agent_duos"), ("System Prompts", "system_prompts")]:
        comps = getattr(paia, attr)
        if comps:
            lines.append(f"\n### {label}")
            for c in comps:
                lines.append(comp_line(c))

    golden = golden_summary(paia)
    lines.extend(["", "## [VEHICLE] Construction Summary",
                  f"- **Flight Level**: {paia.gear_state.level} ({paia.gear_state.phase.value.upper()})",
                  f"- **Energy**: {paia.gear_state.total_points} pts",
                  f"- **Subsystem Status**: {golden['golden']}G / {golden['crystal']}C / {golden['quarantine']}Q",
                  f"- **Hull**: {'[CROWNING] CONSTRUCTED' if paia.gear_state.is_constructed else '[TOWERING] IN PROGRESS'}"])

    return "\n".join(lines)
