"""GIINT type injection and validation for entity chains.

Injects GIINT typing based on naming conventions and validates
required relationships for each entity chain shape.
"""

import logging

logger = logging.getLogger("dragonbones")

# GIINT Entity Chain Shape Definitions
# Each shape: (prefix, is_a_type, required_rels, optional_rels, parent_prefix)
# required_rels: relationships that MUST exist (warning if missing)
# optional_rels: relationships that SHOULD exist (info if missing)
# parent_prefix: expected part_of target prefix
# target_prefixes: {rel_name: expected_prefix} — validates relationship targets have correct prefix

GIINT_EC_SHAPES = {
    "GIINT_Project_": {
        "is_a": "GIINT_Project",
        "required_rels": {"has_path"},
        "optional_rels": set(),
        "parent_hint": None,  # Top of hierarchy
        "instantiates": None,  # No template
        "target_prefixes": {},
    },
    "GIINT_Feature_": {
        "is_a": "GIINT_Feature",
        "required_rels": set(),
        "optional_rels": {"has_component", "has_design"},
        "parent_hint": "GIINT_Project_",
        "instantiates": "GIINT_Feature_Template",
        "target_prefixes": {"has_component": "GIINT_Component_", "has_design": "Design_"},
    },
    "GIINT_Component_": {
        "is_a": "GIINT_Component",
        "required_rels": set(),
        "optional_rels": {"has_deliverable"},
        "parent_hint": "GIINT_Feature_",
        "instantiates": "GIINT_Component_Template",
        "target_prefixes": {"has_deliverable": "GIINT_Deliverable_"},
    },
    "GIINT_Deliverable_": {
        "is_a": "GIINT_Deliverable",
        "required_rels": set(),
        "optional_rels": {"has_inclusion_map", "has_task"},
        "parent_hint": "GIINT_Component_",
        "instantiates": "GIINT_Deliverable_Template",
        "target_prefixes": {"has_inclusion_map": "Inclusion_Map_", "has_task": "GIINT_Task_"},
    },
    "GIINT_Task_": {
        "is_a": "GIINT_Task",
        "required_rels": set(),
        "optional_rels": {"has_done_signal"},
        "parent_hint": "GIINT_Deliverable_",
        "instantiates": "GIINT_Task_Template",
        "target_prefixes": {},
    },
    "Bug_": {
        "is_a": "Bug",
        "required_rels": set(),
        "optional_rels": {"has_potential_solution"},
        "parent_hint": "GIINT_Component_",  # or GIINT_Deliverable_
        "instantiates": "Bug_Pattern",
        "target_prefixes": {"has_potential_solution": "Potential_Solution_"},
    },
    "Potential_Solution_": {
        "is_a": "Potential_Solution",
        "required_rels": set(),
        "optional_rels": set(),
        "parent_hint": "Bug_",
        "instantiates": "Potential_Solution_Pattern",
        "target_prefixes": {},
    },
    "Design_": {
        "is_a": "Design",
        "required_rels": set(),
        "optional_rels": set(),
        "parent_hint": "GIINT_Feature_",
        "instantiates": "Design_Pattern",
        "target_prefixes": {},
    },
    "Idea_": {
        "is_a": "Idea",
        "required_rels": set(),
        "optional_rels": set(),
        "parent_hint": "GIINT_Project_",
        "instantiates": "Idea_Pattern",
        "target_prefixes": {},
    },
    "Inclusion_Map_": {
        "is_a": "Inclusion_Map",
        "required_rels": {"proves"},
        "optional_rels": set(),
        "parent_hint": "GIINT_Deliverable_",
        "instantiates": "Inclusion_Map_Pattern",
        "target_prefixes": {"proves": "GIINT_Task_"},
    },
    "Skill_": {
        "is_a": "Skill",
        "required_rels": {
            "has_domain", "has_category", "has_what", "has_when", "has_produces",
            "has_personal_domain", "has_subdomain", "has_content",
            "has_requires", "has_describes_component",
        },
        "optional_rels": {
            "has_allowed_tools", "has_model", "has_context_mode",
            "has_agent_type", "has_user_invocable", "has_starsystem",
        },
        "parent_hint": None,
        "instantiates": None,
        "target_prefixes": {},
    },
    "Pattern_": {
        "is_a": "Pattern",
        "required_rels": set(),
        "optional_rels": set(),
        "parent_hint": None,
        "instantiates": None,
        "target_prefixes": {},
    },
    "Prolog_Rule_": {
        "is_a": "Prolog_Rule",
        "required_rels": {"has_rule_body"},
        "optional_rels": {"operates_on", "produces_type"},
        "parent_hint": None,
        "instantiates": None,
        "target_prefixes": {},
    },
}

# Deprecated prefixes that should error
DEPRECATED_PREFIXES = {
    "Architecture_": "Use GIINT_Project_ instead. Architecture concepts are now GIINT_Project descriptions.",
}


def inject_giint_types(concept: dict) -> tuple[dict, list[str]]:
    """Inject GIINT typing for concepts following naming conventions.

    Injects is_a type and instantiates template based on name prefix.
    Validation is handled by SHACL via the reasoner — not here.

    Returns (modified_concept, errors).
    """
    name = concept["concept_name"]
    rels = concept["relationships"]
    errors = []

    # Check deprecated prefixes first
    for prefix, message in DEPRECATED_PREFIXES.items():
        if name.startswith(prefix):
            errors.append(f"ERROR: {prefix} prefix is deprecated. {message}")
            # Still compile — don't block

    # Get current relationship values
    isa_rels = [r for r in rels if r["relationship"] == "is_a"]
    current_isa = isa_rels[0]["related"] if isa_rels else []

    instantiates_rels = [r for r in rels if r["relationship"] == "instantiates"]
    current_instantiates = instantiates_rels[0]["related"] if instantiates_rels else []

    partof_rels = [r for r in rels if r["relationship"] == "part_of"]
    current_partof = partof_rels[0]["related"] if partof_rels else []

    provided_rels = {r["relationship"] for r in rels}

    # Match against GIINT EC shapes
    matched_shape = None
    for prefix, shape in GIINT_EC_SHAPES.items():
        if name.startswith(prefix):
            matched_shape = shape
            break

    if matched_shape is None:
        # No GIINT shape matched — pass through unchanged
        return concept, errors

    # 1. Inject is_a if not already present
    expected_isa = matched_shape["is_a"]
    if expected_isa not in current_isa:
        current_isa.append(expected_isa)
        logger.info("Injected is_a=%s for %s", expected_isa, name)

    # 2. Inject instantiates if shape defines a template and not already present
    expected_instantiates = matched_shape["instantiates"]
    if expected_instantiates and expected_instantiates not in current_instantiates:
        current_instantiates.append(expected_instantiates)
        logger.info("Injected instantiates=%s for %s", expected_instantiates, name)

# DEAD CODE — Commented out 2026-03-29. All validation (required_rels, target_prefixes, parent_hint, Skill category checks) duplicates SHACL shapes in uarl_shapes.ttl. The reasoner handles this via youknow() at compiler.py line 498-553. Only INJECTION (is_a, instantiates above) is kept.
    # # 3. Validate required relationships
    # missing_required = matched_shape["required_rels"] - provided_rels
    # for rel in missing_required:
        # errors.append(
            # f"WARNING: {name} ({expected_isa}) missing required relationship: {rel}"
        # )

    # # 4. Validate target prefixes for relationships that have them
    # target_prefixes = matched_shape.get("target_prefixes", {})
    # for rel in rels:
        # rel_name = rel["relationship"]
        # if rel_name in target_prefixes:
            # expected_prefix = target_prefixes[rel_name]
            # for target in rel.get("related", []):
                # if not target.startswith(expected_prefix):
                    # errors.append(
                        # f"WARNING: {name} relationship '{rel_name}' target '{target}' "
                        # f"should start with '{expected_prefix}'"
                    # )

    # # 5. Check parent_hint for part_of validation
    # parent_hint = matched_shape["parent_hint"]
    # if parent_hint and current_partof:
        # valid_parent = any(p.startswith(parent_hint) for p in current_partof)
        # if not valid_parent:
            # # Bug_ can also be part_of GIINT_Deliverable_
            # if expected_isa == "Bug" and any(
                # p.startswith("GIINT_Deliverable_") or p.startswith("GIINT_Component_")
                # for p in current_partof
            # ):
                # pass  # Valid alternative parent
            # else:
                # errors.append(
                    # f"INFO: {name} part_of targets {current_partof} — "
                    # f"expected parent prefix: {parent_hint}"
                # )

    # # 6. Skill category-dependent GIINT anchor validation
    # if expected_isa == "Skill":
        # category_targets = []
        # for r in rels:
            # if r["relationship"] == "has_category":
                # category_targets = [t.lower().replace("skill_category_", "") for t in r.get("related", [])]
                # break
        # category = category_targets[0] if category_targets else None

        # has_describes = any(r["relationship"] in ("has_describes_component", "describes_component") for r in rels)
        # has_produces = any(r["relationship"] == "has_produces" for r in rels)
        # partof_giint = any(
            # p.startswith("GIINT_Component_") or p.startswith("GIINT_Feature_")
            # for p in current_partof
        # )

        # if category == "understand":
            # if not has_describes:
                # errors.append(
                    # f"❌ ERROR [{name}] understand skill MUST have has_describes_component "
                    # f"pointing to a GIINT_Component_. Skills must be anchored to the GIINT hierarchy."
                # )
            # else:
                # for r in rels:
                    # if r["relationship"] in ("has_describes_component", "describes_component"):
                        # for t in r.get("related", []):
                            # if not t.startswith("GIINT_Component_"):
                                # errors.append(
                                    # f"❌ ERROR [{name}] has_describes_component target '{t}' "
                                    # f"must start with GIINT_Component_"
                                # )

        # elif category == "single_turn_process":
            # if not (partof_giint or has_produces or has_describes):
                # errors.append(
                    # f"❌ ERROR [{name}] STP skill MUST have one of: "
                    # f"part_of a GIINT_Component_/GIINT_Feature_, "
                    # f"has_produces a GIINT_Deliverable_, or "
                    # f"has_describes_component a GIINT_Component_. "
                    # f"Skills must be anchored to the GIINT hierarchy."
                # )

        # elif category == "preflight":
            # if not (partof_giint or has_describes):
                # errors.append(
                    # f"❌ ERROR [{name}] preflight skill MUST have "
                    # f"part_of a GIINT_Component_/GIINT_Feature_ or "
                    # f"has_describes_component a GIINT_Component_. "
                    # f"Skills must be anchored to the GIINT hierarchy."
                # )

        # elif category is None:
            # errors.append(
                # f"❌ ERROR [{name}] Skill MUST have has_category. "
                # f"Use: Skill_Category_Understand, Skill_Category_Single_Turn_Process, or Skill_Category_Preflight"
            # )

    # Update is_a relationship
    if isa_rels and current_isa:
        isa_rels[0]["related"] = current_isa
    elif current_isa and not isa_rels:
        rels.insert(0, {"relationship": "is_a", "related": current_isa})

    # Update instantiates relationship
    if expected_instantiates:
        if instantiates_rels and current_instantiates:
            instantiates_rels[0]["related"] = current_instantiates
        elif current_instantiates and not instantiates_rels:
            rels.append({"relationship": "instantiates", "related": current_instantiates})

    concept["relationships"] = rels
    return concept, errors
