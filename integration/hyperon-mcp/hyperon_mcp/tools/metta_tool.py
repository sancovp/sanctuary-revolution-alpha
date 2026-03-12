"""
HEAVEN-compatible MeTTa tools.

These wrap the core persistent MeTTa functionality in BaseHeavenTool interface,
following the heaven-framework-repo pattern.
"""

from typing import Dict, Any, Optional, List
import logging

# Try to import from heaven_base if available, otherwise provide minimal compatibility
try:
    from heaven_base.baseheaventool import BaseHeavenTool, ToolArgsSchema
    HEAVEN_AVAILABLE = True
except ImportError:
    HEAVEN_AVAILABLE = False
    # Minimal compatibility for standalone use
    class ToolArgsSchema:
        arguments: Dict[str, Dict[str, Any]] = {}

    class BaseHeavenTool:
        name = "BaseTool"
        description = ""
        func = None
        args_schema = ToolArgsSchema
        is_async = False

from ..core.atomspace_registry import AtomspaceRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Utility Functions (core logic, called by both tools and MCP)
# ============================================================================

def metta_query_util(
    query: str,
    registry_name: str = "default",
    flat: bool = False
) -> str:
    """
    Query the persistent atomspace with accumulated rules.

    Args:
        query: MeTTa query string like "!(match &self (isa $x mammal) $x)"
        registry_name: Which MeTTa instance to query
        flat: Whether to flatten results

    Returns:
        Query results as string
    """
    logger.info(f"MeTTa query on {registry_name}: {query}")
    registry = AtomspaceRegistry(registry_name)
    return registry.query_with_rules(query, flat=flat)


def metta_add_rule_util(
    rule: str,
    registry_name: str = "default"
) -> str:
    """
    Add a rule to the persistent atomspace.

    Args:
        rule: MeTTa expression like "(= (ancestor $x $z) ...)"
        registry_name: Which MeTTa instance to add to

    Returns:
        Success message
    """
    logger.info(f"Adding rule to {registry_name}: {rule}")
    registry = AtomspaceRegistry(registry_name)
    return registry.add_rule(rule)


def metta_list_rules_util(
    registry_name: str = "default"
) -> str:
    """
    List all rules in the atomspace.

    Args:
        registry_name: Which MeTTa instance to list

    Returns:
        List of rules as string
    """
    logger.info(f"Listing rules from {registry_name}")
    registry = AtomspaceRegistry(registry_name)
    rules = registry.get_all_rules()
    count = len(rules)

    if count == 0:
        return f"No rules in {registry_name}"

    return f"Rules in {registry_name} ({count} total):\n" + "\n".join(rules)


# ============================================================================
# BaseHeavenTool Wrappers (if heaven_base available)
# ============================================================================

if HEAVEN_AVAILABLE:
    class MeTTaQueryToolArgsSchema(ToolArgsSchema):
        arguments: Dict[str, Dict[str, Any]] = {
            'query': {
                'name': 'query',
                'type': 'str',
                'description': 'MeTTa query string',
                'required': True
            },
            'registry_name': {
                'name': 'registry_name',
                'type': 'str',
                'description': 'MeTTa instance name',
                'required': False
            },
            'flat': {
                'name': 'flat',
                'type': 'bool',
                'description': 'Flatten results',
                'required': False
            }
        }

    class MeTTaQueryTool(BaseHeavenTool):
        name = "MeTTaQueryTool"
        description = "Query persistent MeTTa atomspace with accumulated rules"
        func = staticmethod(metta_query_util)
        args_schema = MeTTaQueryToolArgsSchema
        is_async = False

    class MeTTaAddRuleToolArgsSchema(ToolArgsSchema):
        arguments: Dict[str, Dict[str, Any]] = {
            'rule': {
                'name': 'rule',
                'type': 'str',
                'description': 'MeTTa expression to add as rule',
                'required': True
            },
            'registry_name': {
                'name': 'registry_name',
                'type': 'str',
                'description': 'MeTTa instance name',
                'required': False
            }
        }

    class MeTTaAddRuleTool(BaseHeavenTool):
        name = "MeTTaAddRuleTool"
        description = "Add rule to persistent MeTTa atomspace"
        func = staticmethod(metta_add_rule_util)
        args_schema = MeTTaAddRuleToolArgsSchema
        is_async = False

else:
    # Provide stub classes if heaven_base not available
    MeTTaQueryTool = None
    MeTTaAddRuleTool = None
