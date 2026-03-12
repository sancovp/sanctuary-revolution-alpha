"""SDNAC factories for the Observatory DUO.

The Observatory IS a DUO:
- Ariadne (A-type) = Researcher — drives the scientific method, sets challenges
- Poimandres (P-type) = Grug — executes code, does the hands-work
- OVP = BigBrain Researcher — reviews output, approves or rejects

All three are SDNACs on MiniMax via Heaven.
System prompts are passed in — not baked here.
"""

from .config import DEFAULT_MODEL


def _patch_heaven():
    """Monkey-patch poimandres to use Heaven runner."""
    try:
        from sdna import poimandres
        from sdna.heaven_runner import heaven_agent_step
        poimandres.agent_step = heaven_agent_step
    except ImportError:
        pass


def _make_heaven_hermes(name, goal, system_prompt, model, tools_list, max_turns=10,
                       target_container=""):
    """Build a HermesConfig for MiniMax/Heaven backend."""
    from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs

    if tools_list is None:
        from heaven_base.tools import BashTool
        tools_list = [BashTool]

    return HermesConfig(
        name=name,
        goal=goal,
        backend="heaven",
        model=model,
        max_turns=max_turns,
        permission_mode="bypassPermissions",
        target_container=target_container,
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=8000,
                tools=tools_list,
                enable_compaction=True,
            ),
        ),
        system_prompt=system_prompt,
    )


def _make_sdnac(name, goal, system_prompt, model, tools_list, max_turns=10,
                target_container=""):
    """Build a single SDNAC on Heaven."""
    from sdna.sdna import SDNAC
    from sdna.ariadne import AriadneChain, InjectConfig

    _patch_heaven()

    ariadne = AriadneChain(
        name=f"{name}_ariadne",
        elements=[
            InjectConfig(
                source="literal",
                inject_as=f"{name}_instructions",
                value=f"Execute as {name}.",
            ),
        ],
    )

    hermes = _make_heaven_hermes(name, goal, system_prompt, model, tools_list, max_turns,
                                target_container=target_container)
    return SDNAC(name=name, ariadne=ariadne, config=hermes)


def make_grug_sdnac(system_prompt: str, model: str = DEFAULT_MODEL, tools_list=None,
                    target_container: str = ""):
    """SmartGrug — Poimandres position. The hands.

    Receives {task} in context, executes code via BashTool.

    Args:
        target_container: Docker container to run in (e.g. "repo-lord").
                         Empty string = local execution.
    """
    return _make_sdnac("grug", "{task}", system_prompt, model, tools_list,
                       target_container=target_container)


def make_researcher_sdnac(system_prompt: str, model: str = DEFAULT_MODEL, tools_list=None):
    """Dr. Randy BrainBrane — Ariadne position. The brain.

    Receives {phase_prompt} in context, drives the scientific method.
    """
    return _make_sdnac("researcher", "{phase_prompt}", system_prompt, model, tools_list)


def make_ovp_sdnac(system_prompt: str, model: str = DEFAULT_MODEL, tools_list=None):
    """BigBrain Observer — OVP position. The reviewer.

    Another Researcher instance that reviews the work and outputs
    OVP_APPROVED: TRUE/FALSE with feedback.
    """
    return _make_sdnac("researcher_ovp", "{phase_prompt}", system_prompt, model, tools_list)


def make_observatory_duo(
    researcher_prompt: str,
    grug_prompt: str,
    ovp_prompt: str,
    model: str = DEFAULT_MODEL,
    tools_list=None,
    max_duo_cycles: int = 3,
    grug_container: str = "",
):
    """Build the Observatory DUO.

    The whole Observatory IS a DUO:
    - Ariadne = Researcher (challenges, drives research phases)
    - Poimandres = Grug (does the work — code execution)
    - OVP = BigBrain Researcher (reviews, approves/rejects)

    The DUO loop:
        Researcher sets the challenge →
        Grug does the work →
        OVP reviews →
        if rejected: loop back to Researcher with feedback
        if approved: done

    Args:
        researcher_prompt: System prompt for the Researcher (Ariadne).
        grug_prompt: System prompt for Grug (Poimandres).
        ovp_prompt: System prompt for the OVP (BigBrain reviewer).
        model: Model for all agents. Default minimax.
        tools_list: Heaven tools. Defaults to [BashTool].
        max_duo_cycles: Max review cycles. Default 3.
        grug_container: Docker container for Grug (e.g. "repo-lord").
                       Empty string = local execution.

    Returns:
        AutoDUOAgent whose .execute(context) runs the full Observatory loop.
    """
    from sdna.duo_chain import auto_duo_agent

    _patch_heaven()

    researcher = make_researcher_sdnac(researcher_prompt, model, tools_list)
    grug = make_grug_sdnac(grug_prompt, model, tools_list,
                           target_container=grug_container)
    ovp = make_ovp_sdnac(ovp_prompt, model, tools_list)

    return auto_duo_agent(
        name="observatory",
        ariadne=researcher,     # A-type: the brain that challenges
        poimandres=grug,        # P-type: the hands that execute
        ovp=ovp,                # OVP: the BigBrain that reviews
        max_n=1,                # 1 A→P step per inner loop
        max_duo_cycles=max_duo_cycles,
    )
