"""
MetaStackRenderer MCP Server - Agent-accessible template rendering via MCP.

This MCP server allows AI agents to:
- List available MetaStack templates
- Render templates with content
- Write rendered output to files
- Compose multiple templates together
"""

import os
import sys
import json
import logging
from importlib import import_module
from typing import Dict, Any, Union, List
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP app
mcp = FastMCP("MetaStackRenderer")

# Add metastack_templates directory to Python path for template imports
_heaven_data_dir = os.getenv("HEAVEN_DATA_DIR")
if _heaven_data_dir:
    _templates_dir = os.path.join(_heaven_data_dir, "metastack_templates")
    os.makedirs(_templates_dir, exist_ok=True)
    if _templates_dir not in sys.path:
        sys.path.insert(0, _templates_dir)
        logger.info(f"Added metastack_templates to path: {_templates_dir}")


# ——— Helper Functions ———

def get_registry():
    """Get registry service from HEAVEN_DATA_DIR."""
    try:
        from heaven_base.registry import RegistryService
        registry_dir = os.getenv("HEAVEN_DATA_DIR")
        if not registry_dir:
            raise RuntimeError("HEAVEN_DATA_DIR not set in environment")
        return RegistryService(registry_dir)
    except ImportError as e:
        logger.warning(f"heaven_base not installed, registry features disabled: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize registry: {e}", exc_info=True)
        return None


def resolve_metastack_class(class_path: str):
    """
    Given a full class path like "pydantic_stack_core.fractal.FractalPattern",
    import it and return the class.
    """
    logger.debug(f"Resolving class: {class_path}")
    module_name, class_name = class_path.rsplit(".", 1)
    module = import_module(module_name)
    cls = getattr(module, class_name)
    logger.info(f"Resolved class: {cls}")
    return cls


def resolve_and_render_metastack(
    metastack_name: str,
    content: Dict[str, Any],
    output_format: str = "render"
) -> Union[str, Dict[str, Any]]:
    """
    Resolve a metastack template by name (via registry),
    instantiate with content, and return either:
     - rendered string (.render())
     - JSON dict (model_dump())
    """
    logger.info(f"Rendering metastack: {metastack_name}, format: {output_format}")

    registry = get_registry()
    if registry is None:
        raise RuntimeError(
            "Registry not available. Install heaven-framework or provide class_path directly."
        )

    # Fetch metadata for metastack
    meta_info = registry.get("metastacks", metastack_name)
    if meta_info is None:
        raise ValueError(f"Metastack '{metastack_name}' not found in registry")

    class_path = meta_info.get("class_path")
    if not class_path:
        raise ValueError(f"Metastack meta for '{metastack_name}' missing class_path")

    # Import the class
    MetaStackClass = resolve_metastack_class(class_path)

    # Merge defaults if present
    defaults = meta_info.get("defaults", {})
    merged_content = {**defaults, **content}

    # Instantiate
    logger.debug(f"Instantiating {MetaStackClass.__name__} with content")
    instance = MetaStackClass(**merged_content)

    if output_format == "render":
        result = instance.render()
        logger.info(f"Rendered {len(result)} characters")
        return result
    elif output_format == "json":
        result = instance.model_dump() if hasattr(instance, "model_dump") else instance.dict()
        logger.info(f"Generated JSON with {len(result)} fields")
        return result
    else:
        raise ValueError(f"Invalid output_format '{output_format}'. Use 'render' or 'json'.")


# ——— MCP Tools ———

@mcp.tool()
def list_metastacks() -> List[str]:
    """List all registered metastack templates."""
    logger.info("Listing metastacks")
    registry = get_registry()
    if registry is None:
        logger.warning("No registry available, returning empty list")
        return []

    result = registry.list_keys("metastacks") or []
    logger.info(f"Found {len(result)} metastacks")
    return result


@mcp.tool()
def describe_metastack(metastack_name: str) -> Dict[str, Any]:
    """Return metadata about a metastack (class_path, defaults, etc.)."""
    logger.info(f"Describing metastack: {metastack_name}")
    registry = get_registry()
    if registry is None:
        raise RuntimeError("Registry not available")

    info = registry.get("metastacks", metastack_name)
    if info is None:
        raise ValueError(f"Metastack '{metastack_name}' not found")

    logger.debug(f"Metastack info: {info}")
    return info


@mcp.tool()
def render_to_file(
    metastack_name: str,
    content: Dict[str, Any],
    file_path: str,
    mode: str = "w",
    output_format: str = "render"
) -> str:
    """
    Render a metastack and write or append to a file.

    Args:
        metastack_name: Name of registered metastack
        content: Data to fill the template
        file_path: Where to write the output
        mode: "w" (overwrite) or "a" (append)
        output_format: "render" for text or "json" for JSON

    Returns:
        Path to the file written
    """
    logger.info(f"Rendering {metastack_name} to file: {file_path}, mode: {mode}")

    result = resolve_and_render_metastack(metastack_name, content, output_format)

    # Convert to string if not already
    if not isinstance(result, str):
        result = json.dumps(result, indent=2)

    # Ensure directory exists
    out_path = Path(file_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write or append
    with open(out_path, mode, encoding="utf-8") as f:
        f.write(result)
        f.write("\n")

    logger.info(f"Wrote {len(result)} characters to {out_path}")
    return str(out_path)


@mcp.tool()
def append_from(
    source_metastack: str,
    source_content: Dict[str, Any],
    target_file: str,
    output_format: str = "render"
) -> str:
    """
    Render a metastack and append its output to a target file.

    Args:
        source_metastack: Name of metastack to render
        source_content: Data for the template
        target_file: File to append to
        output_format: "render" for text or "json" for JSON

    Returns:
        Path to the file appended to
    """
    logger.info(f"Appending {source_metastack} to {target_file}")
    return render_to_file(source_metastack, source_content, target_file, mode="a", output_format=output_format)


@mcp.tool()
def render_metastack(
    metastack_name: str,
    content: Dict[str, Any],
    output_format: str = "render"
) -> Union[str, Dict[str, Any]]:
    """
    Render a metastack and return the output (no file writing).

    Args:
        metastack_name: Name of registered metastack
        content: Data to fill the template
        output_format: "render" for text or "json" for JSON

    Returns:
        Rendered output as string or dict
    """
    logger.info(f"Rendering {metastack_name} in memory")
    return resolve_and_render_metastack(metastack_name, content, output_format)


@mcp.tool()
def register_metastack(
    name: str,
    class_path: str,
    domain: str,
    subdomain: str = "",
    process: str = "",
    tags: List[str] = None,
    defaults: Dict[str, Any] = None,
    description: str = ""
) -> str:
    """
    Register a new metastack template in the registry.

    Args:
        name: Unique name for this metastack template
        class_path: Full Python import path to the MetaStack class (e.g., "my_templates.BlogPost")
        domain: Primary domain category (e.g., "content_creation", "documentation")
        subdomain: More specific subdomain (e.g., "blog_posts", "api_docs")
        process: Process this template serves (e.g., "drafting", "publishing")
        tags: List of searchable tags (e.g., ["marketing", "technical", "tutorial"])
        defaults: Default values for template fields
        description: Human-readable description of what this template does

    Returns:
        Success message with registered name
    """
    logger.info(f"Registering metastack: {name}, class_path: {class_path}")

    registry = get_registry()
    if registry is None:
        raise RuntimeError("Registry not available. Install heaven-framework to register templates.")

    # Build metadata
    metadata = {
        "class_path": class_path,
        "domain": domain,
        "subdomain": subdomain or "",
        "process": process or "",
        "tags": tags or [],
        "defaults": defaults or {},
        "description": description
    }

    # Validate class_path by attempting to import
    try:
        MetaStackClass = resolve_metastack_class(class_path)
        logger.info(f"Validated class: {MetaStackClass.__name__}")
    except Exception as e:
        logger.error(f"Failed to validate class_path: {e}", exc_info=True)
        raise ValueError(f"Invalid class_path '{class_path}': {e}")

    # Add to registry
    registry.add("metastacks", name, metadata)
    logger.info(f"Successfully registered metastack: {name}")

    return f"Successfully registered metastack '{name}' at {class_path}"


@mcp.tool()
def get_help(topic: str = "pydantic_stack_core", list_components: bool = False) -> Union[str, List[str]]:
    """
    Get Python help documentation for pydantic_stack_core or specific classes.

    Args:
        topic: What to get help for. Options:
            - "guide": Just the LLM workflow guide (__init__.py docstring)
            - "pydantic_stack_core": Full module help (includes all class signatures)
            - "RenderablePiece": Help for RenderablePiece base class
            - "MetaStack": Help for MetaStack container
            - "FractalStage": Help for FractalStage class
            - "FractalPattern": Help for FractalPattern class
            - Or any fully-qualified class path like "pydantic_stack_core.fractal.FractalPattern"
        list_components: If True, return list of available help topics instead of help text

    Returns:
        Help text as string, or list of available topics if list_components=True
    """
    import io
    import sys
    from contextlib import redirect_stdout

    # Import pydantic_stack_core
    import pydantic_stack_core

    # Map topic to actual objects
    topic_map = {
        "guide": pydantic_stack_core,  # Special: returns __doc__ only
        "pydantic_stack_core": pydantic_stack_core,
        "RenderablePiece": pydantic_stack_core.RenderablePiece,
        "MetaStack": pydantic_stack_core.MetaStack,
        "FractalStage": pydantic_stack_core.FractalStage,
        "FractalPattern": pydantic_stack_core.FractalPattern,
    }

    # Return list of components if requested
    if list_components:
        logger.info("Listing available help components")
        return list(topic_map.keys())

    logger.info(f"Getting help for: {topic}")

    # Special case: guide returns just the docstring
    if topic == "guide":
        result = pydantic_stack_core.__doc__ or "No docstring available"
        logger.info(f"Returned module __doc__ ({len(result)} characters)")
        return result

    # Get the object to document
    if topic in topic_map:
        obj = topic_map[topic]
    else:
        # Try to resolve as a class path
        try:
            obj = resolve_metastack_class(topic)
        except Exception as e:
            logger.error(f"Failed to resolve topic: {e}", exc_info=True)
            return f"Error: Could not resolve '{topic}'. Valid options: {list(topic_map.keys())} or a fully-qualified class path."

    # Capture help output
    help_buffer = io.StringIO()
    with redirect_stdout(help_buffer):
        help(obj)

    result = help_buffer.getvalue()
    logger.info(f"Generated {len(result)} characters of help text")
    return result


# ——— Main Entrypoint ———

def main():
    """Start the MetaStackRenderer MCP server."""
    logger.info("Starting MetaStackRenderer MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
