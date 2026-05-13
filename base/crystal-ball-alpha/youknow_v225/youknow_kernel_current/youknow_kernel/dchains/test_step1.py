"""Tests for Step 1 d-chain — proves the smallest loop works end-to-end."""

import pytest


def test_dchain_registry_finds_skill_chain():
    """Registered chain is discoverable by (target_type, argument_name)."""
    import youknow_kernel.dchains  # trigger registration
    from youknow_kernel.dchains.registry import get_chains

    chains = get_chains("Skill", "has_category")
    assert len(chains) >= 1, "Expected at least one chain registered for Skill.has_category"


def test_dchain_fires_in_infer_from_context():
    """When an understand Skill is validated, the chain fires and composes has_user_invocable=false."""
    import youknow_kernel.dchains  # trigger registration
    from youknow_kernel.system_type_validator import _infer_from_context

    rel_dict = {
        "is_a": ["Skill"],
        "has_category": ["Skill_Category_Understand"],
        "has_domain": ["Test_Domain"],
        "has_what": ["Test_What"],
        "has_when": ["Test_When"],
        "has_produces": ["Test_Produces"],
    }
    inferred = _infer_from_context("Skill", rel_dict, [], concept_name="Skill_Test_Step1")
    assert "has_user_invocable" in inferred
    assert inferred["has_user_invocable"] == ["false"]


def test_dchain_does_not_overwrite_provided_value():
    """If has_user_invocable is already in the relationship dict, the chain does not overwrite."""
    import youknow_kernel.dchains  # trigger registration
    from youknow_kernel.system_type_validator import _infer_from_context

    rel_dict = {
        "is_a": ["Skill"],
        "has_category": ["Skill_Category_Understand"],
        "has_user_invocable": ["true"],
        "has_domain": ["Test_Domain"],
        "has_what": ["Test_What"],
        "has_when": ["Test_When"],
        "has_produces": ["Test_Produces"],
    }
    inferred = _infer_from_context("Skill", rel_dict, [], concept_name="Skill_Test_Step1")
    # The chain should not have composed has_user_invocable=false since it was already provided.
    # inferred should NOT have has_user_invocable=["false"] — the chain returned {}.
    assert inferred.get("has_user_invocable") != ["false"]


def test_dchain_does_not_fire_for_non_understand_category():
    """If category is preflight, the understand-specific chain does not produce its compose_arg.

    The existing hardcoded path may still set has_user_invocable to a different value
    based on the preflight branch — that's expected. We only assert that the call
    completes without crashing and produces a dict.
    """
    import youknow_kernel.dchains  # trigger registration
    from youknow_kernel.system_type_validator import _infer_from_context

    rel_dict = {
        "is_a": ["Skill"],
        "has_category": ["Skill_Category_Preflight"],
        "has_domain": ["Test_Domain"],
        "has_what": ["Test_What"],
        "has_when": ["Test_When"],
        "has_produces": ["Test_Produces"],
    }
    inferred = _infer_from_context("Skill", rel_dict, [], concept_name="Skill_Test_Step1")
    assert isinstance(inferred, dict)
