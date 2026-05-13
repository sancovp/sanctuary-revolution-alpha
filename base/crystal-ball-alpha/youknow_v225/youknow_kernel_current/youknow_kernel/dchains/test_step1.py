"""Tests for OWL-driven d-chain dispatch.

Uses fixture mocking: instead of seeding domain.owl (which would require the
full CartON→YOUKNOW admission pipeline + the OWL class Deduction_Chain to be
declared), we monkeypatch dchains.registry._CACHE to inject test chains.
This validates the dispatcher logic in isolation while the OWL-bootstrap
work happens separately.
"""

import pytest

from youknow_kernel.dchains.registry import ChainIndividual


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the registry cache before each test."""
    from youknow_kernel.dchains import registry as reg
    reg._CACHE = {}
    reg._CACHE_LOADED = True  # treat as already loaded so we don't re-read OWL
    yield
    reg._CACHE = {}
    reg._CACHE_LOADED = False


def _inject(target_type, argument_name, body, body_type="python_function"):
    """Inject a synthetic ChainIndividual into the cache for testing."""
    from youknow_kernel.dchains import registry as reg
    ci = ChainIndividual(
        name=f"Deduction_Chain_{target_type}_{argument_name}",
        target_type=target_type,
        argument_name=argument_name,
        body=body,
        body_type=body_type,
    )
    key = (target_type, argument_name or "__type_level__")
    reg._CACHE.setdefault(key, []).append(ci)


def test_dispatcher_finds_python_function_chain():
    """Dispatcher reads the cache and resolves a python_function chain."""
    from youknow_kernel.dchains.registry import get_chains_for
    _inject(
        "Skill",
        "has_category",
        "youknow_kernel.dchains.skill_chains:deduce_has_user_invocable_for_understand",
    )
    chains = get_chains_for("Skill", "has_category")
    assert len(chains) == 1
    assert chains[0].body_type == "python_function"


def test_dispatcher_fires_python_function_chain_via_infer_from_context():
    """When an understand Skill is validated, the chain fires and composes has_user_invocable=false."""
    from youknow_kernel.system_type_validator import _infer_from_context
    _inject(
        "Skill",
        "has_category",
        "youknow_kernel.dchains.skill_chains:deduce_has_user_invocable_for_understand",
    )
    rel_dict = {
        "is_a": ["Skill"],
        "has_category": ["Skill_Category_Understand"],
        "has_domain": ["Test_Domain"],
        "has_what": ["Test_What"],
        "has_when": ["Test_When"],
        "has_produces": ["Test_Produces"],
    }
    inferred = _infer_from_context("Skill", rel_dict, [], concept_name="Skill_Test_Step1")
    assert inferred.get("has_user_invocable") == ["false"]


def test_chain_does_not_overwrite_explicitly_provided_value():
    """If has_user_invocable is already in the relationship dict, the chain does not overwrite."""
    from youknow_kernel.system_type_validator import _infer_from_context
    _inject(
        "Skill",
        "has_category",
        "youknow_kernel.dchains.skill_chains:deduce_has_user_invocable_for_understand",
    )
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
    # The chain returned compose_arg, but the key is in relationship_dict so
    # the dispatcher should not have copied it into inferred.
    assert inferred.get("has_user_invocable") != ["false"]


def test_chain_does_not_fire_compose_for_non_understand_category():
    """If category is preflight, the understand chain returns {} so no compose_arg."""
    from youknow_kernel.system_type_validator import _infer_from_context
    _inject(
        "Skill",
        "has_category",
        "youknow_kernel.dchains.skill_chains:deduce_has_user_invocable_for_understand",
    )
    rel_dict = {
        "is_a": ["Skill"],
        "has_category": ["Skill_Category_Preflight"],
        "has_domain": ["Test_Domain"],
        "has_what": ["Test_What"],
        "has_when": ["Test_When"],
        "has_produces": ["Test_Produces"],
    }
    inferred = _infer_from_context("Skill", rel_dict, [], concept_name="Skill_Test_Step1")
    # The understand-specific chain produced {}; hardcoded preflight branch
    # below the dispatcher still runs and may set has_user_invocable=true.
    # We just assert no crash + the chain's compose_arg=false did NOT land.
    assert inferred.get("has_user_invocable") != ["false"]


def test_dispatcher_handles_error_result():
    """A chain returning {'error': ...} flips __chain_rejections__."""
    from youknow_kernel.system_type_validator import _infer_from_context
    # Use a body that always errors. Define inline test body via temp module.
    import types, sys
    mod = types.ModuleType("__test_dchain_error_mod")
    def always_error(arg_value, context):
        return {"error": "test rejection"}
    mod.always_error = always_error
    sys.modules["__test_dchain_error_mod"] = mod

    _inject("Skill", "has_category", "__test_dchain_error_mod:always_error")

    rel_dict = {
        "is_a": ["Skill"],
        "has_category": ["Skill_Category_Understand"],
    }
    inferred = _infer_from_context("Skill", rel_dict, [], concept_name="Skill_Test_Step1")
    rejections = inferred.get("__chain_rejections__", [])
    assert any("test rejection" in r for r in rejections)


def test_dispatcher_handles_unknown_body_type_gracefully():
    """An unknown body_type doesn't crash; chain just doesn't fire."""
    from youknow_kernel.dchains.registry import execute_chain
    ci = ChainIndividual(
        name="Test_Unknown",
        target_type="Skill",
        argument_name="has_category",
        body="anything",
        body_type="not_a_real_type",
    )
    result = execute_chain(ci, None, {})
    assert result == {}


def test_get_chains_for_returns_empty_for_unknown_pair():
    """No chain registered for an arg → empty list, not crash."""
    from youknow_kernel.dchains.registry import get_chains_for
    chains = get_chains_for("NonexistentType", "nonexistent_arg")
    assert chains == []
