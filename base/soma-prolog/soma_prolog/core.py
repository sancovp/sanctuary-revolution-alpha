"""SOMA core — pure thin facade.

ONE function: add_event(source, observations).
ONE janus call: query_once on mi_add_event.

All logic (Prolog booting, observation list building, escaping, decoding)
lives in utils.py per the onion architecture. core.py is pure delegation.
"""

import janus_swi as janus

from soma_prolog.utils import (
    ensure_prolog_booted,
    build_obs_list_string,
    escape_prolog_string,
    decode_prolog_result,
    fire_all_deduction_chains_py,
    build_failure_error_report,
)


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
        if n_unmet > 0:
            failure_report = build_failure_error_report(unmet)
            return f"{prolog_report}\ndeduction_chains_fired={n_fired} unmet={n_unmet}\n{failure_report}"
        else:
            return f"{prolog_report}\ndeduction_chains_fired={n_fired} unmet=0\nall_core_requirements_met"
    except Exception as e:
        return f"{prolog_report}\nDEDUCTION_CHAIN_ERROR: {type(e).__name__}: {e}"
