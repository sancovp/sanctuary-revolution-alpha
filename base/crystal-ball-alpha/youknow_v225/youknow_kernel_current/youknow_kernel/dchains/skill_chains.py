"""D-chain bodies for the Skill system type.

Just Python function bodies. The OWL Deduction_Chain individual carries the
binding (target_type=Skill, argument_name=has_category, body_path pointing
to one of these functions, body_type=python_function). The dispatcher in
youknow_kernel.dchains.registry imports the body via its dotted path at
fire time. No registration side-effects in this module.
"""

from typing import Any, Dict


def deduce_has_user_invocable_for_understand(
    arg_value: Any,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """When Skill.has_category is 'understand', compose has_user_invocable=false.

    Args:
        arg_value: value being filled — has_category list, e.g.
            ['Skill_Category_Understand'].
        context: full relationship_dict for the concept being validated.

    Returns:
        compose_arg with has_user_invocable=['false'] when category is
        understand and no explicit has_user_invocable was provided. Empty
        dict otherwise.
    """
    cats = arg_value or context.get("has_category", [])
    if not cats:
        return {}
    cat0 = cats[0] if isinstance(cats, list) else cats
    cat_norm = str(cat0).lower().replace("skill_category_", "")
    if cat_norm == "understand" and not context.get("has_user_invocable"):
        return {"compose_arg": {"has_user_invocable": ["false"]}}
    return {}
