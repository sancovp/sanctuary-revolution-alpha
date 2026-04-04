"""*Log persistence and validation (CogLog, SkillLog, DeliverableLog)."""

import json
import logging
import os
import re

from dragonbones.constants import LOG_STATE_FILE, DELIVERABLE_COUNTER_FILE, SKILLS_DIR, LOG_SYNTAX

logger = logging.getLogger("dragonbones")

# Lazy import for CartON
_add_concept_func = None


def get_add_concept_func():
    global _add_concept_func
    if _add_concept_func is None:
        from carton_mcp.add_concept_tool import add_concept_tool_func
        _add_concept_func = add_concept_tool_func
    return _add_concept_func


def lookup_skill(skill_name: str) -> tuple[bool, list[str]]:
    """Look up a skill by name in SKILLS_DIR. Returns (exact_match, fuzzy_matches)."""
    if not os.path.isdir(SKILLS_DIR):
        return False, []

    normalized = skill_name.lower().replace("_", "-").strip()
    all_skills = [d for d in os.listdir(SKILLS_DIR)
                  if os.path.isdir(os.path.join(SKILLS_DIR, d)) and not d.startswith("_")]

    if normalized in all_skills:
        return True, []

    words = [w for w in normalized.split("-") if len(w) >= 3]
    fuzzy = []
    for s in all_skills:
        if any(w in s for w in words):
            fuzzy.append(s)
    return False, sorted(fuzzy)[:8]


def persist_logs(text: str, session_id: str, line_index: int):
    """Persist *Log entries (CogLog, SkillLog, DeliverableLog) to CartON."""
    add_concept = get_add_concept_func()

    # CogLogs: 🧠 content 🧠
    coglog_pattern = re.compile(r'🧠\s*(.+?)\s*🧠')
    for i, match in enumerate(coglog_pattern.finditer(text)):
        content = match.group(1).strip()
        if not content:
            continue
        name = f"Coglog_{session_id}_{line_index}_{i}"
        try:
            add_concept(
                concept_name=name, description=content,
                relationships=[
                    {"relationship": "is_a", "related": ["General_Coglog"]},
                    {"relationship": "part_of", "related": [
                        f"Conversation_{session_id}",
                        f"Agentmessage_{session_id}_{line_index}",
                    ]},
                ],
                hide_youknow=False,
            )
            logger.info("Persisted CogLog: %s", name)
        except Exception:
            logger.exception("Failed to persist CogLog: %s", name)

    # SkillLogs: 🎯 STATE::domain::skill_name 🎯
    skilllog_pattern = re.compile(r'🎯\s*(.+?)\s*🎯')
    for i, match in enumerate(skilllog_pattern.finditer(text)):
        content = match.group(1).strip()
        if not content:
            continue
        parts = content.split("::", 2)
        state = parts[0].upper() if parts else "UNKNOWN"
        if state not in ("PREDICTING", "MAKING", "USING"):
            state = "PREDICTING"
        name = f"Skilllog_{session_id}_{line_index}_{i}"
        try:
            add_concept(
                concept_name=name, description=content,
                relationships=[
                    {"relationship": "is_a", "related": [f"{state}_Skilllog"]},
                    {"relationship": "part_of", "related": [
                        f"Conversation_{session_id}",
                        f"Agentmessage_{session_id}_{line_index}",
                    ]},
                ],
                hide_youknow=False,
            )
            logger.info("Persisted SkillLog: %s", name)
        except Exception:
            logger.exception("Failed to persist SkillLog: %s", name)

    # DeliverableLogs: 📦 content 📦
    deliverable_pattern = re.compile(r'📦\s*(.+?)\s*📦')
    for i, match in enumerate(deliverable_pattern.finditer(text)):
        content = match.group(1).strip()
        if not content:
            continue
        name = f"Deliverablelog_{session_id}_{line_index}_{i}"
        try:
            add_concept(
                concept_name=name, description=content,
                relationships=[
                    {"relationship": "is_a", "related": ["Deliverable_Idea"]},
                    {"relationship": "part_of", "related": [
                        "Content_Pipeline",
                        f"Conversation_{session_id}",
                        f"Agentmessage_{session_id}_{line_index}",
                    ]},
                ],
                hide_youknow=False,
            )
            logger.info("Persisted DeliverableLog: %s", name)
        except Exception:
            logger.exception("Failed to persist DeliverableLog: %s", name)


def validate_logs(text: str, skill_calls: list[str] = None,
                  tools_called: set[str] = None, line_index: int = 0,
                  has_db_skill_block: bool = False,
                  has_any_db_block: bool = False) -> list[str]:
    """Check for required *logs. Returns list of correction messages."""
    has_coglog = bool(re.search(r'🧠', text)) or has_any_db_block
    has_skilllog = bool(re.search(r'🎯', text))
    has_deliverable = bool(re.search(r'📦', text))

    state = {}
    stash_exists = os.path.exists(LOG_STATE_FILE)
    if stash_exists:
        try:
            with open(LOG_STATE_FILE, 'r') as f:
                state = json.load(f)
        except Exception:
            state = {}

    state["coglog_seen"] = state.get("coglog_seen", False) or has_coglog
    state["deliverable_seen"] = state.get("deliverable_seen", False) or has_deliverable

    skilllog_state = state.get("skilllog_state")
    corrections = []

    if has_skilllog:
        has_db_skill_block = bool(re.search(r'🌟⛓️.*is_a=Skill', text, re.DOTALL))
        skilllog_pattern = re.compile(r'🎯\s*(.+?)\s*🎯')
        for match in skilllog_pattern.finditer(text):
            parts = match.group(1).strip().split("::", 2)
            if len(parts) < 3:
                continue
            claimed_state = parts[0].upper()
            skill_name = parts[2].strip()

            if claimed_state == "PREDICTING":
                if skill_name.lower() in ("none", "sufficient", "homeostasis"):
                    state["skilllog_state"] = "done"
                    continue
                exact, fuzzy = lookup_skill(skill_name)
                if exact:
                    corrections.append(
                        f"Skill '{skill_name}' EXISTS. Call Skill tool for '{skill_name}', "
                        f"then emit: 🎯 USING::{parts[1]}::{skill_name} 🎯"
                    )
                    state["skilllog_state"] = "pending"
                    state["predicted_skill"] = skill_name
                else:
                    fuzzy_str = ", ".join(fuzzy) if fuzzy else "(none)"
                    corrections.append(
                        f"Prediction noted: '{skill_name}' doesn't exist yet. "
                        f"Fuzzy matches: [{fuzzy_str}]. "
                        f"No action required — stashed for Flight Predictor. "
                        f"SkillLog satisfied."
                    )
                    state["skilllog_state"] = "done"
                    state["predicted_skill"] = skill_name

            elif claimed_state == "USING":
                if skill_name not in (skill_calls or []):
                    corrections.append(
                        f"You said USING '{skill_name}' but didn't use it in this turn. "
                        f"Call Skill tool with '{skill_name}' first, then report USING."
                    )
                    break
                state["skilllog_state"] = "done"

            elif claimed_state == "MAKING":
                if not has_db_skill_block:
                    corrections.append(
                        f"REPORTED MAKING A SKILL WITHOUT A DB BLOCK THAT MAKES IT. "
                        f"No 🌟⛓️ EntityChain with is_a=Skill found in turn. INVALID."
                    )
                    break
                state["skilllog_state"] = "done"

    if has_db_skill_block and not has_skilllog:
        state["skilllog_state"] = "done"

    if skilllog_state == "pending" and not has_skilllog:
        predicted = state.get("predicted_skill", "?")
        retry_count = state.get("pending_retries", 0) + 1
        state["pending_retries"] = retry_count
        if retry_count >= 3:
            corrections.append(
                f"Prediction '{predicted}' expired after {retry_count} turns without followup. "
                f"SkillLog auto-resolved. If you still need it, predict again."
            )
            state["skilllog_state"] = "done"
            state.pop("predicted_skill", None)
            state.pop("pending_retries", None)
        else:
            corrections.append(
                f"Skill '{predicted}' EXISTS — call Skill tool for '{predicted}', "
                f"then emit: 🎯 USING::domain::{predicted} 🎯\n"
                f"OR dismiss: 🎯 PREDICTING::domain::sufficient 🎯"
            )

    skilllog_done = state.get("skilllog_state") == "done"

    if state["coglog_seen"] and skilllog_done and not corrections:
        try:
            os.remove(LOG_STATE_FILE)
        except Exception:
            pass

        del_count = 0
        if os.path.exists(DELIVERABLE_COUNTER_FILE):
            try:
                with open(DELIVERABLE_COUNTER_FILE, 'r') as f:
                    del_count = json.load(f).get("count", 0)
            except Exception:
                pass

        del_count = 0 if state["deliverable_seen"] else del_count + 1

        try:
            with open(DELIVERABLE_COUNTER_FILE, 'w') as f:
                json.dump({"count": del_count}, f)
        except Exception:
            pass

        if del_count >= 10:
            corrections.append(
                "Consider a DeliverableLog. What happened that's worth showing people? "
                "Syntax: 📦 type::domain::idea 📦"
            )
            try:
                with open(DELIVERABLE_COUNTER_FILE, 'w') as f:
                    json.dump({"count": 0}, f)
            except Exception:
                pass

        return corrections

    try:
        with open(LOG_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass

    if not state["coglog_seen"]:
        corrections.append(f"Missing CogLog. Syntax: {LOG_SYNTAX['CogLog']}")
    if not skilllog_done and state.get("skilllog_state") is None:
        corrections.append(f"Missing SkillLog. Syntax: {LOG_SYNTAX['SkillLog']}")

    return corrections
