#!/usr/bin/env python3
"""Milestone D tests: YMesh telemetry + llm_suggest operational wiring."""

from youknow_kernel.owl_types import get_cat, reset_cat
from youknow_kernel.compiler import validate_statement
from youknow_kernel.utils import build_missingness_payload


def _add_gate_pass_entity() -> None:
    cat = get_cat()
    cat.add(
        name="TelemetryPass",
        is_a=["Entity"],
        part_of=["YOUKNOW"],
        instantiates=["Pattern"],
        y_layer="Y4",
        description="telemetry test entity",
        properties={
            "msc": True,
            "justifies": ["is_a"],
            "python_class": "TelemetryPass",
        },
    )
    cat.declare_bounded("TelemetryPass")


def test_controller_telemetry_tracks_threshold_for_programs_path():
    reset_cat()
    _add_gate_pass_entity()

    details = validate_statement("TelemetryPass is_a Entity")
    controller = details["diagnostics"]["controller"]

    assert details["decision"]["admit_to_ont"] is True
    assert controller["target_layer"] == "y6"
    assert controller["threshold_event"] is True
    assert controller["transition"] == "SOUP_TO_ONT"


def test_controller_telemetry_stays_soup_for_unknown_claim():
    reset_cat()

    details = validate_statement("Dog is_a Pet")
    controller = details["diagnostics"]["controller"]

    assert details["decision"]["admit_to_ont"] is False
    assert controller["target_layer"] == "y4"
    assert controller["threshold_event"] is False
    assert controller["transition"] == "STAY_SOUP"
    assert details["diagnostics"]["llm_suggest"].startswith("YOUKNOW:")


def test_llm_guidance_is_deterministic_for_same_input_and_state():
    reset_cat()
    first = validate_statement("Dog is_a Pet")
    second = validate_statement("Dog is_a Pet")

    assert first["diagnostics"]["llm_suggest"] == second["diagnostics"]["llm_suggest"]
    assert first["diagnostics"]["controller"] == second["diagnostics"]["controller"]


def test_continuous_emr_snapshot_present_in_compile_step():
    reset_cat()
    details = validate_statement("Dog is_a Pet")
    emr = details["diagnostics"]["continuous_emr"]

    assert emr["enabled"] is True
    assert emr["result"]["name"] == "Dog"
    assert "gradient" in emr
    assert emr["seed_concept_count"] >= 1


def test_continuous_emr_is_seeded_from_current_ontology_state():
    reset_cat()
    before = validate_statement("LoopProbe is_a Entity")
    before_seed_count = before["diagnostics"]["continuous_emr"]["seed_concept_count"]

    cat = get_cat()
    cat.add(
        name="LoopSeed",
        is_a=["Entity"],
        part_of=["YOUKNOW"],
        instantiates=["Pattern"],
        y_layer="Y3",
        description="seed for continuous emr",
        properties={},
    )

    after = validate_statement("LoopProbe is_a Entity")
    after_seed_count = after["diagnostics"]["continuous_emr"]["seed_concept_count"]

    assert after_seed_count == before_seed_count + 1


def test_missingness_payload_helper_is_stable_and_sorted():
    payload = build_missingness_payload(
        "Dog is_a Pet",
        ["justifies incomplete", "MSC missing", "justifies incomplete"],
        extras={"phase": "gate"},
    )

    assert payload["source"] == "compiler"
    assert payload["count"] == 2
    assert payload["missingness"] == ["MSC missing", "justifies incomplete"]
    assert payload["extras"]["phase"] == "gate"
