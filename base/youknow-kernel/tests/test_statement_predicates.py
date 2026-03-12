#!/usr/bin/env python3
"""Tests for ontology predicate triples in statement grammar."""

import pytest

from youknow_kernel.cat_of_cat import get_cat, reset_cat
from youknow_kernel.core import reset_youknow
from youknow_kernel.compiler import parse_statement, validate_statement, youknow


@pytest.fixture(autouse=True)
def _reset_state():
    reset_youknow()
    reset_cat()
    yield
    reset_cat()
    reset_youknow()


def _add_programs_ready_entity(name: str, declared_bounded: bool) -> None:
    cat = get_cat()
    cat.add(
        name=name,
        is_a=["Entity"],
        part_of=["YOUKNOW"],
        instantiates=["Pattern"],
        y_layer="Y4",
        description=f"{name} triple predicate test entity",
        properties={"python_class": name},
    )
    if declared_bounded:
        cat.declare_bounded(name)


def test_parser_accepts_ontology_predicates_and_normalizes_names():
    parsed = parse_statement(
        "Thing is_a Entity, hasMSC MSC_Thing, justifies is_a, "
        "justifiesEdge Thing:is_a:Entity, catOfCatBounded true, "
        "sesTypedDepth 6, compressionMode strong, reason seeded, programs Reality, "
        "pythonClass ThingClass, template ThingTemplate, yLayer Y4, description \"seed entity\""
    )

    assert parsed is not None
    assert parsed.subject == "Thing"
    assert parsed.predicate == "is_a"
    assert parsed.object == "Entity"
    assert ("has_msc", "MSC_Thing") in parsed.additional
    assert ("justifies", "is_a") in parsed.additional
    assert ("justifies_edge", "Thing:is_a:Entity") in parsed.additional
    assert ("cat_of_cat_bounded", "true") in parsed.additional
    assert ("ses_typed_depth", "6") in parsed.additional
    assert ("compression_mode", "strong") in parsed.additional
    assert ("reason", "seeded") in parsed.additional
    assert ("programs", "Reality") in parsed.additional
    assert ("python_class", "ThingClass") in parsed.additional
    assert ("template", "ThingTemplate") in parsed.additional
    assert ("y_layer", "Y4") in parsed.additional
    assert ("description", "seed entity") in parsed.additional


def test_has_msc_node_triple_satisfies_msc_presence_gate():
    _add_programs_ready_entity("TripleMSC", declared_bounded=True)

    result = youknow("TripleMSC is_a Entity, hasMSC MSC_TripleMSC, justifies is_a")
    details = validate_statement("TripleMSC is_a Entity, hasMSC MSC_TripleMSC, justifies is_a")

    assert result == "OK"
    assert details["compression_report"]["has_msc"] is True
    assert details["compression_report"]["all_required_justified"] is True
    assert details["decision"]["admit_to_ont"] is True


def test_catofcatbounded_triple_can_enable_bounded_gate_and_admission():
    _add_programs_ready_entity("BoundViaTriple", declared_bounded=False)

    result = youknow(
        "BoundViaTriple is_a Entity, hasMSC MSC_BoundViaTriple, "
        "justifies is_a, catOfCatBounded true"
    )
    details = validate_statement(
        "BoundViaTriple is_a Entity, hasMSC MSC_BoundViaTriple, "
        "justifies is_a, catOfCatBounded true"
    )

    assert result == "OK"
    assert details["decision"]["is_catofcat_bounded"] is True
    assert get_cat().is_declared_bounded("BoundViaTriple") is True


def test_non_is_a_predicate_does_not_add_hyperedge_claim_blocking():
    _add_programs_ready_entity("SemNode", declared_bounded=True)

    details = validate_statement("SemNode hasMSC MSC_SemNode")
    blocking = details["diagnostics"]["blocking"]

    assert "No supporting hyperedge evidence" not in " | ".join(blocking)


def test_rich_statement_can_admit_new_entity_without_preseeding():
    result = youknow(
        "FreshRepo is_a Entity, part_of YOUKNOW, instantiates Pattern, "
        "yLayer Y4, description \"fresh repo\", hasMSC MSC_FreshRepo, "
        "justifies is_a, catOfCatBounded true, pythonClass FreshRepo, "
        "analogicalPattern FreshRepo_is_a_Entity_pattern"
    )
    details = validate_statement(
        "FreshRepo is_a Entity, part_of YOUKNOW, instantiates Pattern, "
        "yLayer Y4, description \"fresh repo\", hasMSC MSC_FreshRepo, "
        "justifies is_a, catOfCatBounded true, pythonClass FreshRepo, "
        "analogicalPattern FreshRepo_is_a_Entity_pattern"
    )

    assert result == "OK"
    assert details["decision"]["admit_to_ont"] is True
    assert details["emr_state"] == "programs"
    assert get_cat().get("FreshRepo") is not None
