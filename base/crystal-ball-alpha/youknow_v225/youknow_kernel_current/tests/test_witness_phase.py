#!/usr/bin/env python3
"""Milestone E tests: optional post-admission witness behavior."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from youknow_kernel.owl_types import get_cat, reset_cat
from youknow_kernel.compiler import youknow


def _add_admissible_entity(name: str) -> None:
    cat = get_cat()
    cat.add(
        name=name,
        is_a=["Entity"],
        part_of=["YOUKNOW"],
        instantiates=["Pattern"],
        y_layer="Y4",
        description=f"{name} witness entity",
        properties={
            "msc": True,
            "justifies": ["is_a"],
            "python_class": name,
        },
    )
    cat.declare_bounded(name)


def test_post_admission_witness_file_created(tmp_path):
    reset_cat()
    _add_admissible_entity("WitnessPass")

    with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
        result = youknow("WitnessPass is_a Entity")

    assert result == "OK"

    witness_file = Path(tmp_path) / "witness" / "WitnessPass_witness.json"
    assert witness_file.exists()

    data = json.loads(witness_file.read_text())
    assert data["type"] == "PostAdmissionWitness"
    assert data["decision"]["admit_to_ont"] is True
    assert data["simulation"]["mode"] == "codegen_generated"
    artifact = data["simulation"]["artifact"]
    assert artifact["spec_pattern"] == "DataHolder"
    assert artifact["syntax_parse_ok"] is True

    code_file = Path(artifact["code_file"])
    assert code_file.exists()
    code_text = code_file.read_text()
    assert "@dataclass" in code_text
    assert "class WitnessPassWitness" in code_text


def test_soup_path_does_not_create_witness(tmp_path):
    reset_cat()

    with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
        result = youknow("Dog is_a Pet")

    assert result.startswith("That's SOUP")
    witness_dir = Path(tmp_path) / "witness"
    assert not witness_dir.exists() or list(witness_dir.iterdir()) == []
