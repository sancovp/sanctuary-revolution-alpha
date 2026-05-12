#!/usr/bin/env python3
"""Milestone C tests: deterministic ABCD grounding in compile packet."""

from youknow_kernel.owl_types import reset_cat
from youknow_kernel.compiler import validate_statement, youknow


def test_unknown_claim_requires_abcd_grounding():
    reset_cat()
    details = validate_statement("Dog is_a Pet")

    assert details["abcd_state"]["required"] is True
    assert details["abcd_state"]["complete"] is False
    assert "mapsTo" in details["abcd_state"]["missing_slots"]
    assert "analogicalPattern" in details["abcd_state"]["missing_slots"]
    assert details["decision"]["admit_to_ont"] is False


def test_known_foundation_claim_has_complete_abcd():
    reset_cat()
    details = validate_statement("Entity is_a Cat_of_Cat")

    assert details["abcd_state"]["required"] is False
    assert details["abcd_state"]["complete"] is True
    assert details["abcd_state"]["missing_slots"] == []


def test_soup_response_surfaces_abcd_missingness():
    reset_cat()
    result = youknow("Dog is_a Pet")
    assert result.startswith("That's SOUP")
    assert "ABCD missing slots:" in result
