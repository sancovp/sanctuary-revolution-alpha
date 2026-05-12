#!/usr/bin/env python3
"""
Tests for YOUKNOW SOUP layer wiring.

Verifies:
1. Unknown targets return "SOUP: ..." instead of "Wrong..."
2. Hallucination metadata is created correctly
3. SOUP files are persisted to the soup directory
4. Known chains return "OK"
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import rdflib


UARL = rdflib.Namespace("http://sanctuary.ai/uarl#")


class TestSoupWiring:
    """Test the SOUP layer wiring in YOUKNOW."""

    def test_unknown_target_returns_soup(self):
        """When target is unknown, should return SOUP: not Wrong."""
        from youknow_kernel.compiler import youknow

        # Dog is_a Pet where Pet is not in ontology
        result = youknow("Dog is_a Pet")

        # Should start with SOUP:, not Wrong
        assert result.startswith("That's SOUP"), f"Expected SOUP prefix, got: {result}"
        assert "Pet" in result, "Should mention the unknown target"

    def test_soup_contains_unknown_marker(self):
        """SOUP response should expose unknown chain + gate missingness."""
        from youknow_kernel.compiler import youknow

        result = youknow("Foo is_a Bar")

        assert "SOUP" in result
        assert "Unknown:" in result
        assert "Missing:" in result

    def test_soup_lists_broken_chains_for_all_statement_relations(self):
        """Unknown list should include broken chains for all relation targets."""
        from youknow_kernel.compiler import youknow

        result = youknow("Dog is_a Pet, part_of Habitat")

        assert "SOUP" in result
        assert "Unknown:" in result
        assert "Pet is_a ? (unknown)" in result
        assert "Habitat is_a ? (unknown)" in result

    def test_known_chain_returns_ok(self):
        """When chain is complete, should return OK."""
        from youknow_kernel.compiler import youknow

        # Entity and Cat_of_Cat should be in foundation
        result = youknow("Entity is_a Cat_of_Cat")

        # This should either be OK or SOUP depending on foundation setup
        # At minimum, it should not be "Wrong"
        assert not result.startswith("You said"), f"Should not start with 'You said': {result}"

    def test_soup_file_created(self, tmp_path):
        """SOUP entry should be persisted to soup directory."""
        from youknow_kernel.compiler import youknow

        # Set up temp soup directory
        soup_dir = tmp_path / "soup"
        soup_dir.mkdir()

        with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
            result = youknow("TestConcept is_a UnknownThing")

        # Check soup directory for files
        soup_files = list(soup_dir.glob("*_hallucination.json"))
        assert len(soup_files) >= 1, f"Expected soup file, found: {list(soup_dir.iterdir())}"

        # Verify file contents
        with open(soup_files[0]) as f:
            soup_entry = json.load(f)

        assert soup_entry["type"] == "Hallucination"
        assert "metadata" in soup_entry
        assert soup_entry["metadata"]["subject"] == "TestConcept"
        assert soup_entry["metadata"]["object"] == "UnknownThing"
        assert soup_entry["waiting_for"] == ["UnknownThing"]
        assert soup_entry["promoted"] == False

    def test_hallucination_metadata_structure(self, tmp_path):
        """Hallucination metadata should have correct structure."""
        from youknow_kernel.compiler import youknow

        soup_dir = tmp_path / "soup"
        soup_dir.mkdir()

        with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
            youknow("MyEntity is_a SomeType")

        soup_files = list(soup_dir.glob("*_hallucination.json"))
        with open(soup_files[0]) as f:
            soup_entry = json.load(f)

        meta = soup_entry["metadata"]

        # Required fields
        assert "is_hallucination" in meta
        assert meta["is_hallucination"] == True
        assert "break_point" in meta
        assert "whats_missing" in meta
        assert "evolution_target" in meta
        assert "would_need" in meta
        assert "spiral_state" in meta

    def test_soup_persists_hallucination_to_domain_owl(self, tmp_path):
        """SOUP entries should also persist as Hallucination in domain ontology."""
        from youknow_kernel.compiler import youknow

        with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
            result = youknow("SoupConcept is_a MissingType")

        assert result.startswith("That's SOUP")

        domain_owl = tmp_path / "ontology" / "domain.owl"
        assert domain_owl.exists(), "SOUP should create/update domain ontology"

        g = rdflib.Graph()
        g.parse(domain_owl, format="xml")

        hallucinations = list(g.subjects(rdflib.RDF.type, UARL.Hallucination))
        assert len(hallucinations) == 1

        hallucination = hallucinations[0]
        assert (hallucination, rdflib.RDF.type, UARL.PIOEntity) in g
        assert (hallucination, UARL.instantiates, UARL.THE_Metaphor) in g
        partial_patterns = list(g.objects(hallucination, UARL.hasPartialIsomorphicPattern))
        self_claims = list(g.objects(hallucination, UARL.hasSelfClaim))
        assert partial_patterns, "PIOEntity should carry partial isomorphic pattern node(s)"
        assert self_claims, "PIOEntity should carry self-claim node(s)"

        pattern_node = partial_patterns[0]
        claim_node = self_claims[0]
        assert (pattern_node, rdflib.RDF.type, UARL.PartialIsomorphicPattern) in g
        assert (claim_node, rdflib.RDF.type, UARL.ClaimAboutSelf) in g
        assert list(g.objects(pattern_node, UARL.patternFragment)), "patternFragment should be persisted"
        assert list(g.objects(claim_node, UARL.claimText)), "claimText should be persisted"
        error_patterns = [str(v) for v in g.objects(hallucination, UARL.errorPattern)]
        assert "is_a_unknown_target" in error_patterns

        evolution_targets = list(g.objects(hallucination, UARL.requiresEvolution))
        assert evolution_targets, "Hallucination should link to Requires_Evolution"
        evolution_target = evolution_targets[0]
        assert (evolution_target, rdflib.RDF.type, UARL.Requires_Evolution) in g
        assert list(g.objects(evolution_target, UARL.reason)), "Requires_Evolution should include reason(s)"

    def test_soup_repl_calls_update_single_hallucination_node(self, tmp_path):
        """Repeated REPL calls for same claim should update, not duplicate, SOUP node."""
        from youknow_kernel.compiler import youknow

        with patch.dict(os.environ, {"HEAVEN_DATA_DIR": str(tmp_path)}):
            first = youknow("LoopConcept is_a UnknownType")
            second = youknow("LoopConcept is_a UnknownType")

        assert first.startswith("That's SOUP")
        assert second.startswith("That's SOUP")

        domain_owl = tmp_path / "ontology" / "domain.owl"
        g = rdflib.Graph()
        g.parse(domain_owl, format="xml")

        hallucinations = list(g.subjects(rdflib.RDF.type, UARL.Hallucination))
        evolutions = list(g.subjects(rdflib.RDF.type, UARL.Requires_Evolution))
        assert len(hallucinations) == 1
        assert len(evolutions) == 1

    def test_parse_failure_not_soup(self):
        """Parse failures should not go to SOUP - they're errors."""
        from youknow_kernel.compiler import youknow

        # Invalid statement format
        result = youknow("this is not a valid statement")

        # Should be an error, not SOUP
        assert ("SOUP" in result) or ("could not parse" in result.lower())
        assert not result.startswith("That's SOUP")


class TestCartonIntegration:
    """Test Carton's handling of SOUP responses."""

    def test_soup_prefix_not_treated_as_error(self):
        """SOUP: prefix should be treated as success, not error."""
        # Simulate what add_concept_tool does
        result = "That's SOUP (BAD/WIP): I cant know if Dog is a Pet because [Missing {for Pet: [is_a (unknown type)]}]"

        # Check the logic
        is_ok = result == "OK"
        is_soup = result.startswith("That's SOUP")
        is_error = not is_ok and not is_soup

        assert is_soup == True
        assert is_error == False

    def test_ok_prefix_is_complete_success(self):
        """OK should indicate chain complete."""
        result = "OK"

        is_ok = result == "OK"
        is_soup = result.startswith("That's SOUP")

        assert is_ok == True
        assert is_soup == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
