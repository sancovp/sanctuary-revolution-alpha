"""D-chains for the Skill system type.

A d-chain is a Python callable that fires on an arg value of an individual
of a target system type. The body does extra logic in the web (composes
other args, validates, etc.). Output shape:

    {"compose_arg": {arg_name: value_list}}  -> fills another arg in the entry
    {"error": "<reason>"}                    -> rejects the individual
    {"unnamed": "<for_arg>"}                 -> places _Unnamed placeholder
    {}                                       -> chain has nothing to add

The DeductionChain wrapper binds (target_type, argument_name) -> callable so
the firing dispatcher in system_type_validator can look it up at canonical-fill.
"""

from typing import Any, Dict, List

from ..deduction_chain import DeductionChain
from .registry import register


def deduce_has_user_invocable_for_understand(
    arg_value: Any,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """If the Skill's category is 'understand', has_user_invocable defaults to false.

    Args:
        arg_value: The value being filled (the has_category list, e.g. ['Skill_Category_Understand']).
        context: The full relationship_dict for the concept being validated.

    Returns:
        compose_arg with has_user_invocable=false when category is understand
        and no explicit has_user_invocable was provided. Otherwise empty dict.
    """
    cats = arg_value or context.get("has_category", [])
    if not cats:
        return {}
    cat0 = cats[0] if isinstance(cats, list) else cats
    cat_norm = str(cat0).lower().replace("skill_category_", "")
    if cat_norm == "understand":
        if not context.get("has_user_invocable"):
            return {"compose_arg": {"has_user_invocable": ["false"]}}
    return {}


register(
    DeductionChain(
        target_type="Skill",
        argument_name="has_category",
        body="youknow_kernel.dchains.skill_chains:deduce_has_user_invocable_for_understand",
        body_type="python_function",
        description=(
            "When Skill.has_category is 'understand', sets has_user_invocable=false "
            "if not already provided."
        ),
    ),
    deduce_has_user_invocable_for_understand,
)
