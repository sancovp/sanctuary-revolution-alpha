"""Starship Pilot prompts — templated workflow for pilot agents."""

import logging

logger = logging.getLogger(__name__)

PILOT_SYSTEM_PROMPT = (
    "You are the Starship Pilot for starsystem: {starsystem_name}.\n"
    "You NEVER write code. You write task lists and requirements docs. Ralph writes code.\n\n"
    "You always write a task list first.\n\n"
    "Your workflow is ALWAYS:\n"
    "1. Get dependency context: mcp__context-alignment__get_dependency_context(target_entity='<code_target>', search_dirs=['{workspace}'])\n"
    "2. Write requirements doc using BashTool to write /tmp/pilot_reqs/reqs.md:\n"
    "   # Requirements: [title]\n"
    "   ## What to change\n"
    "   [file, function from dependency context]\n"
    "   ## Context\n"
    "   [callers, callees from dependency context]\n"
    "   ## Fix\n"
    "   [exact change needed]\n"
    "   ## Acceptance criteria\n"
    "   [testable criteria]\n"
    "3. Dispatch ralph using BashTool (this BLOCKS until ralph finishes all 3 runs):\n"
    "   bash /tmp/compoctopus_repo/scripts/run_ralph.sh {workspace} <code_target> /tmp/pilot_reqs/reqs.md 3\n"
    "   Ralph creates a PR as done signal. No PR = ralph failure.\n"
    "4. After ralph returns, check PR using BashTool:\n"
    "   bash cd {workspace} && gh pr list\n"
    "   bash cd {workspace} && gh pr diff <pr_number>\n"
    "5. If PR looks good, merge. If not, update reqs and re-dispatch.\n\n"
    "You NEVER write code. You ONLY write requirements docs and run scripts.\n\n"
    "## Emanations\n"
    "You have dragonbones MCP tools for creating PAIA artifacts:\n"
    "- **add_skill_to_target_starsystem**: Create skills documenting what you learned about this starsystem.\n"
    "  For code tasks: create understand skills after ralph completes (how the component works, development patterns).\n"
    "  For non-code tasks: create skills directly (documentation, workflows, procedures).\n"
    "- **add_rule_to_target_starsystem**: Create rules for patterns that must be followed in this starsystem.\n"
    "- Log all work to starlog debug diary as you go.\n"
    "- The starsystem name is: {starsystem_name}\n"
)


def _get_starsystem_graph(starsystem_name: str) -> str:
    """Pull CartON graph for starsystem and format as English triplets."""
    try:
        from carton_mcp.carton_utils import CartOnUtils
        utils = CartOnUtils()

        normalized = '_'.join(w.capitalize() for w in starsystem_name.replace('-', '_').split('_'))
        candidates = [
            f"Starsystem_{normalized}",
            f"Starsystem_Tmp_{normalized}",
            normalized,
            starsystem_name,
        ]

        for name in candidates:
            result = utils.query_wiki_graph(
                "MATCH (s:Wiki {{n: $name}})-[r]->(t:Wiki) "
                "RETURN s.n as source, type(r) as rel, t.n as target "
                "UNION "
                "MATCH (s:Wiki)-[r]->(t:Wiki {{n: $name}}) "
                "RETURN s.n as source, type(r) as rel, t.n as target",
                {"name": name}
            )
            if result.get("data"):
                triplets = []
                for row in result["data"][:50]:
                    s = row["source"].replace("_", " ")
                    r = row["rel"].replace("_", " ").lower()
                    t = row["target"].replace("_", " ")
                    triplets.append(f"- {s} {r} {t}")
                if triplets:
                    return (
                        f"## Starsystem Knowledge Graph ({name})\n"
                        + "\n".join(triplets)
                        + "\n"
                    )
        return ""
    except Exception as e:
        logger.warning("Failed to load starsystem graph: %s", e)
        return ""


def build_pilot_system_prompt(starsystem_name: str, workspace: str) -> str:
    """Build the pilot system prompt with starsystem-specific values and graph."""
    base = PILOT_SYSTEM_PROMPT.format(
        starsystem_name=starsystem_name,
        workspace=workspace,
    )
    graph = _get_starsystem_graph(starsystem_name)
    if graph:
        base += "\n" + graph + "\n"
    return base
