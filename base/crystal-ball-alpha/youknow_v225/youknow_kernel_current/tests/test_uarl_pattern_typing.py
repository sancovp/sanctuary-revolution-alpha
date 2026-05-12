#!/usr/bin/env python3
"""Ontology-level typing checks for PatternOfIsA strong compression semantics."""

import os
from pathlib import Path
from unittest.mock import patch

import rdflib
from rdflib.namespace import OWL

from youknow_kernel.owl_types import get_cat, reset_cat
from youknow_kernel.compiler import youknow


UARL = rdflib.Namespace("http://sanctuary.ai/uarl#")


def _add_admissible_entity(name: str) -> None:
    cat = get_cat()
    cat.add(
        name=name,
        is_a=["Entity"],
        part_of=["YOUKNOW"],
        instantiates=["Pattern"],
        y_layer="Y4",
        description=f"{name} typed pattern entity",
        properties={
            "msc": True,
            "justifies": ["is_a"],
            "python_class": name,
        },
    )
    cat.declare_bounded(name)


def test_uarl_foundation_contains_compression_and_boundedness_terms():
    g = rdflib.Graph()
    g.parse(
        Path("/home/GOD/gnosys-plugin-v2/base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/uarl_v3.owl"),
        format="xml",
    )

    assert (UARL.PIOEntity, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.PIOEntity, rdflib.RDFS.subClassOf, UARL.Hallucination) in g
    assert (UARL.PIOEntity, rdflib.RDFS.subClassOf, UARL.Reality) in g
    assert (UARL.Metaphor, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.PartialIsomorphicPattern, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.ClaimAboutSelf, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.THE_Metaphor, rdflib.RDF.type, UARL.Metaphor) in g

    assert (UARL.hasMSC, rdflib.RDF.type, OWL.ObjectProperty) in g
    assert (UARL.justifies, rdflib.RDF.type, OWL.ObjectProperty) in g
    assert (UARL.hasPartialIsomorphicPattern, rdflib.RDF.type, OWL.ObjectProperty) in g
    assert (UARL.hasSelfClaim, rdflib.RDF.type, OWL.ObjectProperty) in g
    assert (UARL.catOfCatBounded, rdflib.RDF.type, OWL.DatatypeProperty) in g
    assert (UARL.sesTypedDepth, rdflib.RDF.type, OWL.DatatypeProperty) in g
    assert (UARL.reason, rdflib.RDF.type, OWL.DatatypeProperty) in g
    assert (UARL.patternFragment, rdflib.RDF.type, OWL.DatatypeProperty) in g
    assert (UARL.claimText, rdflib.RDF.type, OWL.DatatypeProperty) in g

    assert (UARL.StrongCompressionPattern, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.WeakCompressionPattern, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.MinimumSufficientCompression, rdflib.RDF.type, OWL.Class) in g
    assert (UARL.DerivationJustification, rdflib.RDF.type, OWL.Class) in g


def test_shacl_promotion_shape_targets_pattern_of_isa_gate_terms():
    shapes = Path("/home/GOD/gnosys-plugin-v2/base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/uarl_shapes.ttl").read_text()

    assert "uarl:PIOEntityShape" in shapes
    assert "sh:targetClass uarl:PIOEntity" in shapes
    assert "sh:class uarl:Hallucination" in shapes
    assert "sh:class uarl:Reality" in shapes
    assert "uarl:hasPartialIsomorphicPattern" in shapes
    assert "uarl:hasSelfClaim" in shapes
    assert "uarl:Metaphor" in shapes
    assert "uarl:PromotionReadyShape" in shapes
    assert "sh:targetClass uarl:PatternOfIsA" in shapes
    assert "uarl:hasMSC" in shapes
    assert "uarl:justifies" in shapes
    assert "uarl:catOfCatBounded" in shapes
    assert "uarl:sesTypedDepth" in shapes
    assert "uarl:compressionMode \"strong\"" in shapes
    assert "uarl:programs" in shapes


def test_admitted_pattern_persists_strong_typing_to_domain_owl(tmp_path):
    reset_cat()
    _add_admissible_entity("TypedPass")

    with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
        result = youknow("TypedPass is_a Entity")
    assert result == "OK"

    domain_owl = tmp_path / "ontology" / "domain.owl"
    assert domain_owl.exists()

    g = rdflib.Graph()
    g.parse(domain_owl, format="xml")

    pattern = UARL["TypedPass_PatternOfIsA"]
    assert (pattern, rdflib.RDF.type, UARL.StrongCompressionPattern) in g
    assert (pattern, UARL.hasMSC, UARL["MSC_TypedPass"]) in g
    assert (pattern, UARL.catOfCatBounded, rdflib.Literal(True)) in g
    assert (pattern, UARL.compressionMode, rdflib.Literal("strong")) in g
    assert (pattern, UARL.programs, UARL.Reality) in g

    ses_values = [o for o in g.objects(pattern, UARL.sesTypedDepth)]
    assert ses_values, "sesTypedDepth must be persisted"
    assert int(ses_values[0]) >= 6

    justifications = list(g.objects(pattern, UARL.justifies))
    assert justifications, "justifies links must be persisted"


def test_soup_path_does_not_persist_pattern_of_isa_domain_entry(tmp_path):
    reset_cat()

    with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
        result = youknow("Dog is_a Pet")
    assert result.startswith("That's SOUP")

    domain_owl = tmp_path / "ontology" / "domain.owl"
    if not domain_owl.exists():
        return

    g = rdflib.Graph()
    g.parse(domain_owl, format="xml")
    assert (UARL["Dog_PatternOfIsA"], None, None) not in g
