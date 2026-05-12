#!/usr/bin/env python3
"""Milestone B tests: SES typed-depth from constructor arg drill-down."""

from youknow_kernel.owl_types import reset_cat
from youknow_kernel.compiler import validate_statement
from youknow_kernel.universal_pattern import compute_ses_typed_depth


def test_recursive_typed_depth_counts_nested_constructor_args():
    report = compute_ses_typed_depth(
        constructor_name="NestedConstructor",
        constructor_args={
            "node": {
                "left": "Entity",
                "right": {"leaf": "Cat_of_Cat"},
            }
        },
        typed_symbols={"Entity", "Cat_of_Cat"},
    )

    assert report.arg_count_total == 1
    assert report.arg_count_typed == 1
    assert report.max_typed_depth == 3
    assert report.first_arbitrary_string_depth is None


def test_first_arbitrary_string_depth_requires_recursive_drill_down():
    report = compute_ses_typed_depth(
        constructor_name="MixedConstructor",
        constructor_args={
            "node": {
                "left": "Entity",
                "right": {"leaf": "free text"},
            }
        },
        typed_symbols={"Entity", "Cat_of_Cat"},
    )

    assert report.arg_count_total == 1
    assert report.arg_count_typed == 1
    assert report.max_typed_depth == 2
    assert report.first_arbitrary_string_depth == 3


def test_shallow_arbitrary_string_is_untyped_constructor_arg():
    report = compute_ses_typed_depth(
        constructor_name="ShallowMixed",
        constructor_args={
            "label": "raw text",
            "is_a": ["Entity"],
        },
        typed_symbols={"Entity", "Cat_of_Cat"},
    )

    assert report.arg_count_total == 2
    assert report.arg_count_typed == 1
    assert report.max_typed_depth == 2
    assert report.first_arbitrary_string_depth == 1


def test_compiler_ses_report_distinguishes_known_vs_unknown_targets():
    reset_cat()
    known = validate_statement("Entity is_a Cat_of_Cat")
    unknown = validate_statement("Dog is_a Pet")

    assert known["ses_report"]["first_arbitrary_string_depth"] is None
    assert unknown["ses_report"]["first_arbitrary_string_depth"] == 2
