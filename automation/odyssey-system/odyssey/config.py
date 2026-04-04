"""Odyssey config — prompts, MCP servers, agent settings.

EXACTLY matches hierarchical_summarize/flow.py pattern:
- _get_strata_carton_env() for env vars
- HeavenInputs with HeavenHermesArgs(history_id=None)
- MiniMax-M2.7-highspeed as default model
- MCP servers use command strings not shutil.which
"""

import os
from sdna.config import HeavenInputs, HeavenAgentArgs, HeavenHermesArgs
from sdna.defaults import _get_strata_carton_env


def get_odyssey_mcp_servers():
    """CartON + Summarizer MCPs. Pattern: hierarchical_summarize/_get_summarizer_mcp_servers()."""
    strata_env = _get_strata_carton_env()
    def gv(key, default=""):
        return strata_env.get(key) or os.environ.get(key, default)
    return {
        "carton": {
            "command": "carton-mcp", "args": [],
            "env": {
                "GITHUB_PAT": gv("GITHUB_PAT"), "REPO_URL": gv("REPO_URL"),
                "HEAVEN_DATA_DIR": gv("HEAVEN_DATA_DIR", "/tmp/heaven_data"),
                "NEO4J_URI": gv("NEO4J_URI"), "NEO4J_USER": gv("NEO4J_USER"),
                "NEO4J_PASSWORD": gv("NEO4J_PASSWORD"), "OPENAI_API_KEY": gv("OPENAI_API_KEY"),
                "CHROMA_PERSIST_DIR": gv("CHROMA_PERSIST_DIR", "/tmp/carton_chroma_db"),
            }
        },
        "summarizer": {
            "command": "summarizer-mcp", "args": [],
            "env": {
                "GITHUB_PAT": gv("GITHUB_PAT"), "REPO_URL": gv("REPO_URL"),
                "HEAVEN_DATA_DIR": gv("HEAVEN_DATA_DIR", "/tmp/heaven_data"),
                "NEO4J_URI": gv("NEO4J_URI"), "NEO4J_USER": gv("NEO4J_USER"),
                "NEO4J_PASSWORD": gv("NEO4J_PASSWORD"), "OPENAI_API_KEY": gv("OPENAI_API_KEY"),
                "CHROMA_PERSIST_DIR": gv("CHROMA_PERSIST_DIR", "/tmp/carton_chroma_db"),
            }
        }
    }


HEAVEN_INPUTS = HeavenInputs(
    agent=HeavenAgentArgs(provider="ANTHROPIC", max_tokens=8000),
    hermes=HeavenHermesArgs(history_id=None),
)

DEFAULT_MODEL = "MiniMax-M2.7-highspeed"

MEASURE_BUILD_SYSTEM_PROMPT = (
    "You are an adversarial evaluator for the Odyssey ML system. "
    "The BUILD agent just claimed to complete work. Your job is to VERIFY that claim. "
    "Assume the agent might have hallucinated, skipped steps, or claimed false completion. "
    "Use CartON tools to trace concept webs and verify evidence. "
    "Use flag_hallucination from summarizer if you detect fabrication. "
    "Create Odyssey_* prefixed concepts for all your outputs. "
    "Say GOAL ACCOMPLISHED when done."
)

MEASURE_NARRATIVE_SYSTEM_PROMPT = (
    "You are a cross-build narrative analyst for the Odyssey ML system. "
    "You review patterns across MULTIPLE build cycles, not just one. "
    "Look for: stuck loops (same task failing repeatedly), systemic drift, "
    "degrading quality over time, patterns the per-build evaluator misses. "
    "Use CartON tools to query historical Odyssey_Learning_Decision concepts. "
    "Create Odyssey_Narrative_Analysis_* concepts. "
    "Say GOAL ACCOMPLISHED when done."
)

LEARN_BUILD_SYSTEM_PROMPT = (
    "You are a learn-phase decision maker for the Odyssey ML system. "
    "You read the Odyssey measurement analysis and make ONE decision: "
    "CONTINUE (all good, task stays completed) or REDO (problems found, create new task attempt). "
    "Your Odyssey_Learning_Decision_* concept is THE authoritative signal that moves TK cards. "
    "If REDO: create a new GIINT_Task with attempt number and gap list. "
    "Use CartON tools. Say GOAL ACCOMPLISHED when done."
)

LEARN_NARRATIVE_SYSTEM_PROMPT = (
    "You are a narrative-level learn agent for the Odyssey ML system. "
    "You read cross-build analysis and detect Groundhog Day patterns. "
    "If rerun ratio > 50%% with 3+ reruns: ESCALATE to human. "
    "If repeated adaptations fail: create new skill or rule to fix root cause. "
    "Use CartON tools. Say GOAL ACCOMPLISHED when done."
)
