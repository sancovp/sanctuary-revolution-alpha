#!/usr/bin/env python3
"""Milestone A tests: promotion gate correctness."""

import pytest
from unittest.mock import patch

from youknow_kernel.owl_types import get_cat, reset_cat
from youknow_kernel.core import get_youknow, reset_youknow
from youknow_kernel.compiler import validate_statement, youknow


@pytest.fixture(autouse=True)
def _reset_cat_state():
    reset_youknow()
    reset_cat()
    yield
    reset_cat()
    reset_youknow()


def _add_gate_entity(
    name: str,
    *,
    has_msc: bool,
    has_justifies: bool,
    is_programs_ready: bool,
    declared_bounded: bool,
) -> None:
    cat = get_cat()
    properties = {}
    if has_msc:
        properties["msc"] = True
    if has_justifies:
        properties["justifies"] = ["is_a"]
    if is_programs_ready:
        properties["python_class"] = name

    cat.add(
        name=name,
        is_a=["Entity"],
        part_of=["YOUKNOW"],
        instantiates=["Pattern"],
        y_layer="Y4",
        description=f"{name} gate test entity",
        properties=properties,
    )
    if declared_bounded:
        cat.declare_bounded(name)


def test_strong_compression_and_bounded_chain_admits_to_ont():
    _add_gate_entity(
        "GatePass",
        has_msc=True,
        has_justifies=True,
        is_programs_ready=True,
        declared_bounded=True,
    )

    result = youknow("GatePass is_a Entity")
    details = validate_statement("GatePass is_a Entity")

    assert result == "OK"
    assert details["emr_state"] == "programs"
    assert details["decision"]["admit_to_ont"] is True
    assert details["decision"]["is_strong_compression"] is True
    assert details["decision"]["is_catofcat_bounded"] is True


def test_missing_justifies_stays_in_soup():
    _add_gate_entity(
        "NoJustify",
        has_msc=True,
        has_justifies=False,
        is_programs_ready=True,
        declared_bounded=True,
    )

    result = youknow("NoJustify is_a Entity")
    details = validate_statement("NoJustify is_a Entity")

    assert result.startswith("That's SOUP")
    assert "justifies coverage incomplete" in result
    assert details["decision"]["admit_to_ont"] is False


def test_missing_msc_stays_in_soup():
    _add_gate_entity(
        "NoMSC",
        has_msc=False,
        has_justifies=True,
        is_programs_ready=True,
        declared_bounded=True,
    )

    result = youknow("NoMSC is_a Entity")
    details = validate_statement("NoMSC is_a Entity")

    assert result.startswith("That's SOUP")
    assert "MSC missing for target entity" in result
    assert details["decision"]["admit_to_ont"] is False


def test_programs_false_stays_in_soup():
    _add_gate_entity(
        "NoPrograms",
        has_msc=True,
        has_justifies=True,
        is_programs_ready=False,
        declared_bounded=True,
    )

    result = youknow("NoPrograms is_a Entity")
    details = validate_statement("NoPrograms is_a Entity")

    assert result.startswith("That's SOUP")
    assert "programs threshold not reached" in result
    assert details["emr_state"] != "programs"
    assert details["decision"]["is_programs"] is False
    assert details["decision"]["admit_to_ont"] is False


def test_unbounded_chain_stays_in_soup():
    _add_gate_entity(
        "UnboundedGate",
        has_msc=True,
        has_justifies=True,
        is_programs_ready=True,
        declared_bounded=False,
    )

    result = youknow("UnboundedGate is_a Entity")
    details = validate_statement("UnboundedGate is_a Entity")

    assert result.startswith("That's SOUP")
    assert "CatOfCat chain is not declared bounded" in result
    assert details["decision"]["is_catofcat_bounded"] is False
    assert details["decision"]["admit_to_ont"] is False


def test_ont_admission_calls_youknow_add_boundary():
    _add_gate_entity(
        "BoundaryPass",
        has_msc=True,
        has_justifies=True,
        is_programs_ready=True,
        declared_bounded=True,
    )

    yk = get_youknow()
    with patch.object(yk, "add", wraps=yk.add) as add_spy:
        with patch("youknow_kernel.core.get_youknow", return_value=yk):
            result = youknow("BoundaryPass is_a Entity")

    assert result == "OK"
    add_spy.assert_called_once()
    kwargs = add_spy.call_args.kwargs
    assert kwargs["name"] == "BoundaryPass"
    assert kwargs["skip_pipeline"] is True


def test_soup_path_does_not_call_youknow_add_boundary():
    _add_gate_entity(
        "BoundarySoup",
        has_msc=True,
        has_justifies=True,
        is_programs_ready=True,
        declared_bounded=False,
    )

    yk = get_youknow()
    with patch.object(yk, "add", wraps=yk.add) as add_spy:
        with patch("youknow_kernel.core.get_youknow", return_value=yk):
            result = youknow("BoundarySoup is_a Entity")

    assert result.startswith("That's SOUP")
    add_spy.assert_not_called()
