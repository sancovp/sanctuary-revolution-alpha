"""SOMA core — thin facade. Two functions: add_event + add_rule."""

import logging
import traceback

import janus_swi as janus

logger = logging.getLogger(__name__)

from soma_prolog.utils import (
    ensure_prolog_booted,
    build_obs_list_string,
    escape_prolog_string,
    decode_prolog_result,
    fire_all_deduction_chains_py,
    build_failure_error_report,
)


def add_rule(rule_body: str) -> str:
    """Route a Prolog rule through add_event as a PrologRule observation.

    This ensures every rule becomes an OWL PrologRule individual that
    persists in soma.owl and reloads on boot. ONE entrypoint: add_event.
    """
    if ":-" in rule_body:
        head, body = rule_body.split(":-", 1)
        head = head.strip()
        body = body.strip()
    else:
        head = rule_body.strip()
        body = "true"

    safe_name = "prolog_rule_" + "".join(
        c if c.isalnum() or c == "_" else "_" for c in head[:60]
    ).strip("_").lower()

    obs = [{
        "name": safe_name,
        "source": "soma_add_rule",
        "description": rule_body[:200],
        "relationships": [
            {"relationship": "is_a", "related": ["prolog_rule"]},
            {"relationship": "has_rule_head", "related": [head]},
            {"relationship": "has_rule_body", "related": [body]},
        ],
    }]

    return ingest_event("soma_add_rule", obs)


def ingest_event(source: str, observations, domain: str = "default") -> str:
    """Forward an event to Prolog via the MI. Then run deduction chains
    from Python (janus can't serialize the chain results through solve/3).
    Return combined report."""
    ensure_prolog_booted()
    obs_list_str = build_obs_list_string(observations)
    safe_source = escape_prolog_string(str(source))
    if domain and domain != "default":
        safe_source = f"{safe_source}@{escape_prolog_string(str(domain))}"
    try:
        r = janus.query_once(
            f'mi_add_event("{safe_source}", "{obs_list_str}", R)'
        )
        prolog_report = decode_prolog_result(r["R"])
    except Exception as e:
        return f"INGEST_ERROR: {type(e).__name__}: {e}"

    # Run deduction chains from Python — the MI can't serialize the
    # py_call return list through solve/3 variable binding.
    try:
        # Clear prior unmet_requirement facts
        janus.query_once("retractall(unmet_requirement(_))")
        fired = fire_all_deduction_chains_py()
        n_fired = len(fired)
        # Collect unmet requirements
        unmet = []
        for r in janus.query("unmet_requirement(R)"):
            unmet.append(str(r["R"]))
        n_unmet = len(unmet)
        # Collect unnamed slots (SOUP gaps) with details
        soup_lines = []
        for s in janus.query("unnamed_slot(C, P, T)"):
            c, p, t = str(s["C"]), str(s["P"]), str(s["T"])
            soup_lines.append(f"  - {c} needs {p} (type: {t}). Observe it via add_event to fix.")
        n_soup = len(soup_lines)
        soup_report = ""
        if n_soup > 0:
            soup_report = f"\nsoup_gaps={n_soup}\n" + "\n".join(soup_lines)
        if n_unmet > 0:
            failure_report = build_failure_error_report(unmet)
            return f"{prolog_report}\ndeduction_chains_fired={n_fired} unmet={n_unmet}\n{failure_report}{soup_report}"
        else:
            return f"{prolog_report}\ndeduction_chains_fired={n_fired} unmet=0\nall_core_requirements_met{soup_report}"
    except Exception as e:
        return f"{prolog_report}\nDEDUCTION_CHAIN_ERROR: {type(e).__name__}: {e}"
