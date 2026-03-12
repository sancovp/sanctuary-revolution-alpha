"""Mock tool generator — typed passthrough tools for bootstrap compilation.

Creates BaseHeavenTool subclasses dynamically from a name + parameter spec.
The generated tools accept typed parameters but pass through to str,
enabling the full pipeline to run end-to-end before any real tool exists.

Pattern: closure over (tool_name, params) -> BaseHeavenTool subclass

Usage:
    # From a simple spec:
    MockEssayTool = make_mock_tool("EssayTool", ["intro", "body1", "body2", "conclusion"])

    # From a MermaidSpec:
    mock_tools = auto_mock_from_mermaid(spec)

    # From a ToolManifest (fill missing tools):
    manifest = auto_mock_manifest(["carton", "filesystem", "git"])

The mock tools:
- Have the same name, description, and args_schema as the real tools would
- Accept all parameters as str (typed passthrough)
- Return a formatted string showing what was called with what
- Are valid BaseHeavenTool subclasses — same transport, same interface
- Can be swapped for real tools without changing the pipeline

This means: design → mock → run → validate → all 5 invariants pass
→ swap real tools → same interface → regression test still passes
→ the system spawns with 100% regression coverage
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


# ─────────────────────────────────────────────────────────────────
# Core: make_mock_tool — the generator function
# ─────────────────────────────────────────────────────────────────

@dataclass
class MockToolSpec:
    """Specification for generating a mock tool.

    Attributes:
        name: Tool name (e.g. "EssayTool", "carton_query")
        params: List of parameter names (all typed as str)
        description: Optional description (auto-generated if not provided)
        returns: What the mock should return format-wise
    """
    name: str
    params: List[str] = field(default_factory=list)
    description: str = ""
    returns: str = "mock_passthrough"


def make_mock_tool(
    tool_name: str,
    params: List[str],
    description: str = "",
) -> "MockHeavenTool":
    """Generate a mock BaseHeavenTool from a name + parameter list.

    The closure captures (tool_name, params) and returns a tool class
    whose func echoes the call as a formatted string.

    Args:
        tool_name: Name for the tool (e.g. "EssayTool")
        params: List of parameter names (all str-typed)
        description: Tool description (auto-generated if empty)

    Returns:
        A MockHeavenTool instance ready for create()
    """
    if not description:
        description = f"Mock tool: {tool_name}({', '.join(params)})"

    # Build the args schema definition
    arguments: Dict[str, Dict[str, Any]] = {}
    for param in params:
        arguments[param] = {
            "name": param,
            "type": "string",
            "description": f"Mock parameter: {param}",
            "required": True,
        }

    # The closure: captures tool_name for the formatted return
    def mock_func(**kwargs) -> str:
        """Mock implementation — echoes call as formatted string."""
        param_strs = [f"{k}={repr(v)}" for k, v in kwargs.items()]
        return f"{tool_name}({', '.join(param_strs)})"

    mock_func.__name__ = tool_name
    mock_func.__doc__ = description

    return MockHeavenTool(
        tool_name=tool_name,
        tool_description=description,
        tool_func=mock_func,
        tool_arguments=arguments,
        tool_params=params,
    )


@dataclass
class MockHeavenTool:
    """A mock tool that mimics BaseHeavenTool's interface.

    This is NOT a BaseHeavenTool subclass (we don't want the dependency),
    but it implements the same interface so it can be used in the pipeline.

    For actual Heaven integration, use to_heaven_tool() which generates
    a real BaseHeavenTool subclass dynamically.
    """
    tool_name: str
    tool_description: str
    tool_func: Callable
    tool_arguments: Dict[str, Dict[str, Any]]
    tool_params: List[str]

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return self.tool_description

    def __call__(self, **kwargs) -> str:
        """Call the mock function."""
        return self.tool_func(**kwargs)

    def to_heaven_tool_class(self) -> type:
        """Generate a real BaseHeavenTool subclass dynamically.

        This is for actual Heaven framework integration.
        Requires heaven_base to be importable.

        Returns a CLASS (not instance) — call .create() on it.
        """
        try:
            from heaven_base.baseheaventool import BaseHeavenTool, ToolArgsSchema
        except ImportError:
            raise ImportError(
                "heaven_base not available. Use MockHeavenTool directly "
                "or install the heaven-framework package."
            )

        # Capture for closure
        func = self.tool_func
        args = self.tool_arguments.copy()
        tool_name = self.tool_name
        desc = self.tool_description

        # Create the ToolArgsSchema subclass
        schema_class = type(
            f"{tool_name}MockArgsSchema",
            (ToolArgsSchema,),
            {"arguments": args},
        )

        # Create the BaseHeavenTool subclass
        tool_class = type(
            f"{tool_name}Mock",
            (BaseHeavenTool,),
            {
                "name": tool_name,
                "description": desc,
                "func": staticmethod(func),
                "args_schema": schema_class,
                "is_async": False,
            },
        )

        return tool_class

    def __repr__(self) -> str:
        return f"MockHeavenTool({self.tool_name}({', '.join(self.tool_params)}))"


# ─────────────────────────────────────────────────────────────────
# Batch generators: from mermaid, from manifest, from empire spec
# ─────────────────────────────────────────────────────────────────

def auto_mock_from_mermaid(
    spec: "MermaidSpec",
    exclude: Optional[set] = None,
) -> List[MockHeavenTool]:
    """Generate mock tools for every tool_reference in a MermaidSpec.

    Each tool gets a single 'input' parameter (generic passthrough).

    Args:
        spec: MermaidSpec with tool_references
        exclude: Tool names to skip (e.g. the agent itself)

    Returns:
        List of MockHeavenTool instances
    """
    from compoctopus.types import MermaidSpec

    exclude = exclude or set()
    mocks = []

    for tool_name in spec.tool_references:
        if tool_name in exclude:
            continue
        mock = make_mock_tool(
            tool_name=tool_name,
            params=["input"],
            description=f"Auto-mocked from mermaid: {tool_name}",
        )
        mocks.append(mock)

    return mocks


def auto_mock_manifest(
    tool_names: List[str],
    params_per_tool: Optional[Dict[str, List[str]]] = None,
) -> "ToolManifest":
    """Generate a ToolManifest with mock tools from just tool names.

    This is the key bootstrap function: you define an empire by naming
    the tools, and the manifest auto-generates with mocked implementations.

    Args:
        tool_names: List of tool names to mock
        params_per_tool: Optional per-tool parameter lists.
                        Default: each tool gets a single 'input' param.

    Returns:
        A ToolManifest ready for pipeline compilation.
    """
    from compoctopus.types import ToolManifest, MCPConfig, ToolSpec

    params_per_tool = params_per_tool or {}
    mcps: Dict[str, MCPConfig] = {}
    mocks: Dict[str, MockHeavenTool] = {}

    for name in tool_names:
        params = params_per_tool.get(name, ["input"])
        mock = make_mock_tool(name, params)
        mocks[name] = mock

        # Create a ToolSpec for the manifest
        mcps[name] = MCPConfig(
            name=name,
            tools=[ToolSpec(name=name, description=mock.description)],
        )

    manifest = ToolManifest(mcps=mcps)
    # Attach mocks for later use
    manifest._mocks = mocks  # type: ignore
    return manifest


def auto_mock_from_empire(
    empire_spec: Dict[str, dict],
) -> Dict[str, "ToolManifest"]:
    """Generate mock ToolManifests for an entire empire spec.

    Args:
        empire_spec: Dict of agent_name → {task, expect_tools, ...}

    Returns:
        Dict of agent_name → ToolManifest (with mocks)
    """
    manifests = {}
    for agent_name, spec in empire_spec.items():
        tool_names = spec.get("expect_tools", [])
        if isinstance(tool_names, set):
            tool_names = sorted(tool_names)
        params = spec.get("tool_params", {})
        manifests[agent_name] = auto_mock_manifest(tool_names, params)
    return manifests
