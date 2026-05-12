#!/usr/bin/env python3
"""
Mission Types - Reusable mission templates with variable substitution

Uses HEAVEN registries to store mission type templates by domain.
Similar pattern to flight configs but for entire missions.
"""

import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# PARALLEL: uses heaven_base.registry — should migrate to CartON/YOUKNOW
# LAZY IMPORT: heaven_base pulls langchain_core -> transformers -> torch (~800MB)
_registry_func = None

def registry_util_func(*args, **kwargs):
    global _registry_func
    if _registry_func is None:
        try:
            from heaven_base.tools.registry_tool import registry_util_func as _real
            _registry_func = _real
        except ImportError:
            logger.warning("heaven_base not available - mission types will not persist")
            _registry_func = lambda *a, **kw: "Registry not available"
    return _registry_func(*args, **kwargs)


def create_mission_type(
    mission_type_id: str,
    name: str,
    domain: str,
    subdomain: str,
    description: str,
    session_sequence: List[Dict[str, str]],
    required_variables: List[str],
    category: Optional[str] = None,
    optional_variables: Optional[List[str]] = None,
    defaults: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a new mission type template in HEAVEN registry

    Args:
        mission_type_id: Unique identifier for this mission type
        name: Human-readable name
        domain: Mission domain (used for registry naming)
        subdomain: Subdomain value or template with ${variables}
        description: Description template with ${variables}
        session_sequence: List of session dicts with ${variables} in values
        required_variables: List of variable names that must be provided
        category: Optional category for organization (defaults to domain)
        optional_variables: List of variable names with defaults
        defaults: Default values for optional variables

    Returns:
        Creation result with mission_type_id
    """
    try:
        # Registry name based on domain
        registry_name = f"mission_types_{domain}"
        category = category or domain

        # Create mission type data
        mission_type_data = {
            "mission_type_id": mission_type_id,
            "name": name,
            "category": category,
            "domain": domain,
            "subdomain": subdomain,
            "description": description,
            "session_sequence": session_sequence,
            "required_variables": required_variables,
            "optional_variables": optional_variables or [],
            "defaults": defaults or {}
        }

        # Ensure registry exists
        registry_util_func("create_registry", registry_name=registry_name)

        # Delete existing key if present (upsert pattern)
        registry_util_func("delete", registry_name=registry_name, key=mission_type_id)

        # Add to registry
        result = registry_util_func(
            "add",
            registry_name=registry_name,
            key=mission_type_id,
            value_dict=mission_type_data
        )

        if "Error" in result:
            return {
                "success": False,
                "error": f"Registry add failed: {result}"
            }

        logger.info(f"Saved mission type {mission_type_id} to registry {registry_name}")

        return {
            "success": True,
            "mission_type_id": mission_type_id,
            "message": f"Created mission type: {name}",
            "domain": domain,
            "session_count": len(session_sequence)
        }

    except Exception as e:
        logger.error(f"Error creating mission type: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_mission_type(mission_type_id: str, domain: str) -> Optional[Dict[str, Any]]:
    """
    Load mission type from HEAVEN registry

    Args:
        mission_type_id: Mission type to load
        domain: Domain to search in

    Returns:
        Mission type data or None
    """
    try:
        registry_name = f"mission_types_{domain}"
        result = registry_util_func(
            "get",
            registry_name=registry_name,
            key=mission_type_id
        )

        # Parse registry result (format: "Item 'key' in registry 'name': {data}")
        if "Item '" in result and "' in registry '" in result:
            try:
                start_idx = result.find("{")
                if start_idx != -1:
                    dict_str = result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    return json.loads(dict_str.replace("'", '"'))
            except Exception:
                logger.warning(f"Failed to parse mission type result", exc_info=True)

        return None

    except Exception as e:
        logger.error(f"Error loading mission type: {e}", exc_info=True)
        return None


def get_all_mission_types(domain: str) -> Dict[str, Any]:
    """
    Get all mission types from a domain registry

    Args:
        domain: Domain to get mission types from

    Returns:
        Dictionary of mission_type_id -> mission_type_data
    """
    try:
        registry_name = f"mission_types_{domain}"
        result = registry_util_func("get_all", registry_name=registry_name)

        # Parse registry result
        if "Items in registry" in result:
            try:
                start_idx = result.find("{")
                if start_idx != -1:
                    dict_str = result[start_idx:]
                    dict_str = dict_str.replace("None", "null").replace("True", "true").replace("False", "false")
                    return json.loads(dict_str.replace("'", '"'))
            except Exception:
                logger.warning(f"Failed to parse mission types registry result", exc_info=True)

        return {}

    except Exception as e:
        logger.error(f"Failed to get mission types: {e}", exc_info=True)
        return {}


def list_domains() -> List[str]:
    """
    Get list of available mission type domains

    Returns:
        List of domain names that have mission types
    """
    try:
        # Get all registries and filter for mission_types_*
        result = registry_util_func("list_registries")

        if "Available registries:" in result:
            lines = result.split('\n')
            domains = []
            for line in lines:
                if "mission_types_" in line:
                    # Extract domain from registry name
                    domain = line.replace("mission_types_", "").strip()
                    if domain:
                        domains.append(domain)
            return sorted(domains)

        return []

    except Exception as e:
        logger.error(f"Error listing domains: {e}", exc_info=True)
        return []


def substitute_variables(template: str, variables: Dict[str, str]) -> str:
    """
    Substitute ${variable} placeholders in template string

    Args:
        template: String with ${variable} placeholders
        variables: Dict of variable_name -> value

    Returns:
        Template with variables substituted
    """
    result = template
    for var_name, var_value in variables.items():
        placeholder = f"${{{var_name}}}"
        result = result.replace(placeholder, var_value)
    return result


def render_mission_type(mission_type_id: str, domain: str, variables: Dict[str, str]) -> Dict[str, Any]:
    """
    Render a mission type template with provided variables

    Args:
        mission_type_id: Mission type to render
        domain: Domain containing the mission type
        variables: Variable values to substitute

    Returns:
        Rendered mission data ready for create_mission(), or error
    """
    try:
        mission_type = get_mission_type(mission_type_id, domain)
        if not mission_type:
            return {
                "success": False,
                "error": f"Mission type '{mission_type_id}' not found in domain '{domain}'. Search through mission_select_menu()"
            }

        # Merge with defaults
        all_variables = {}
        if mission_type.get("defaults"):
            all_variables.update(mission_type["defaults"])
        all_variables.update(variables)

        # Validate required variables
        required = mission_type.get("required_variables", [])
        missing = [v for v in required if v not in all_variables]
        if missing:
            return {
                "success": False,
                "error": f"Missing required variables: {missing}",
                "required_variables": required
            }

        # Substitute variables in all fields
        rendered_domain = substitute_variables(mission_type["domain"], all_variables)
        rendered_subdomain = substitute_variables(mission_type["subdomain"], all_variables)
        rendered_description = substitute_variables(mission_type["description"], all_variables)

        # Substitute in session sequence
        rendered_sessions = []
        for session in mission_type["session_sequence"]:
            rendered_session = {
                "project_path": substitute_variables(session["project_path"], all_variables),
                "flight_config": substitute_variables(session["flight_config"], all_variables)
            }
            rendered_sessions.append(rendered_session)

        return {
            "success": True,
            "rendered_mission": {
                "name": mission_type["name"],
                "domain": rendered_domain,
                "subdomain": rendered_subdomain,
                "description": rendered_description,
                "session_sequence": rendered_sessions
            }
        }

    except Exception as e:
        logger.error(f"Error rendering mission type: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def mission_select_menu(domain: Optional[str] = None, page: int = 1) -> str:
    """
    Browse available mission types with pagination (like starship.fly())

    Args:
        domain: Optional domain filter (shows domains if None)
        page: Page number for pagination (default 1)

    Returns:
        Formatted mission type listing
    """
    try:
        # If no domain specified, show available domains
        if domain is None:
            domains = list_domains()

            if not domains:
                return """🎯 No mission types available

Create one with:
  create_mission_type(
    mission_type_id='...',
    name='...',
    domain='feature_development',
    subdomain='${subdomain}',
    description='Implement ${feature_name}',
    session_sequence=[...],
    required_variables=['project_path', 'feature_name']
  )"""

            domains_list = '\n'.join(f"  - {d}" for d in domains)
            return f"""🎯 Mission Type Domains

Available domains:
{domains_list}

Use mission_select_menu(domain='...') to browse mission types in that domain"""

        # Domain specified - get mission types
        mission_types = get_all_mission_types(domain)

        if not mission_types:
            return f"""🎯 No mission types in domain '{domain}'

Create one with create_mission_type() using domain='{domain}'"""

        # Convert to list for pagination
        types_list = list(mission_types.items())

        # Paginate (10 per page)
        page_size = 10
        total_pages = (len(types_list) + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_types = types_list[start_idx:end_idx]

        # Format output
        output = [f"🎯 Mission Types - Domain: {domain} (Page {page}/{total_pages})\n"]

        for type_id, type_data in page_types:
            sessions_count = len(type_data.get("session_sequence", []))
            required_vars = ", ".join(type_data.get("required_variables", []))

            output.append(f"""
{type_data.get('name', type_id)}
  ID: {type_id}
  Sessions: {sessions_count}
  Required Variables: {required_vars}
  Description: {type_data.get('description', 'N/A')}
""")

        output.append(f"\nTotal mission types: {len(types_list)}")

        if page < total_pages:
            output.append(f"\nNext page: mission_select_menu(domain='{domain}', page={page + 1})")

        output.append(f"""
To create mission from type:
  mission_create(
    mission_id='my_mission',
    mission_type='{page_types[0][0]}',
    variables={{'project_path': '/path', ...}}
  )""")

        return '\n'.join(output)

    except Exception as e:
        logger.error(f"Error browsing mission types: {e}", exc_info=True)
        return f"❌ Error browsing mission types: {str(e)}"
