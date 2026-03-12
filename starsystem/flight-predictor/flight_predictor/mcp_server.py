"""
Flight Predictor MCP Server (OPERA)

MCP server exposing scry_crystal_ball() and build_jit_flight().
Pattern: Library facade → MCP wrapper (no logic in server, pure delegation)

Usage:
    # Add to Claude Code MCP config:
    {
        "flight-predictor": {
            "command": "python",
            "args": ["-m", "flight_predictor.mcp_server"]
        }
    }
"""

import logging
from mcp.server.fastmcp import FastMCP

from .core import (
    CapabilityObservation,
    CapabilityPrediction,
    PlanStep,
    format_capability_prediction,
    predict_capabilities,
)
from .carton_integration import build_jit_flight, list_proto_flights

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("flight-predictor")


@mcp.tool()
def scry_crystal_ball(
    steps: list[dict],
    context_domain: str | None = None,
) -> str:
    """
    Ask Crystal Ball to predict what skills and tools you'll need for a plan.

    Returns markdown-formatted predictions (not JSON) to save tokens.

    Args:
        steps: List of plan steps, each with:
            - step_number: int (1, 2, 3, ...)
            - description: str (what you want to do)
        context_domain: Optional domain context (e.g., "PAIAB", "CAVE", "SANCTUM")

    Returns:
        Markdown with top skills/tools per step and overall recommendations.
    """
    # Convert dict steps to PlanStep models
    plan_steps = [
        PlanStep(step_number=s["step_number"], description=s["description"])
        for s in steps
    ]

    # Create observation
    observation = CapabilityObservation(
        steps=plan_steps,
        context_domain=context_domain,
    )

    # Get prediction via library facade
    prediction = predict_capabilities(observation)

    # Return formatted markdown (not JSON)
    return format_capability_prediction(prediction)


@mcp.tool()
def format_prediction(prediction_dict: dict) -> str:
    """
    Format a CapabilityPrediction as human-readable text.

    Use this after predict_capabilities_for_plan() to get a formatted summary.

    Args:
        prediction_dict: The dict returned by predict_capabilities_for_plan()

    Returns:
        Formatted string showing hierarchical predictions
    """
    # Reconstruct Pydantic model from dict
    prediction = CapabilityPrediction.model_validate(prediction_dict)
    return format_capability_prediction(prediction)


@mcp.tool()
def confirm_jit_flight(observation: str, confirmed_steps: list[dict]) -> dict:
    """
    Build a JIT flight from confirmed step instructions.

    After reviewing predictions from ask_opera_for_prediction(), call this
    to create a confirmed flight with both TEMPLATE and INSTANCE in CartON.

    Args:
        observation: What triggered this flight (the original task)
        confirmed_steps: List of confirmed steps, each with:
            - step_number: int
            - description: str (what to do)
            - capability_type: str (skill, tool, flight)
            - capability_name: str
            - instructions: str (full instructions written by agent)

    Returns:
        Dict with flight_id, flight_concept, steps, carton_synced status
    """
    return build_jit_flight(observation, confirmed_steps)


@mcp.tool()
def get_proto_flights(status: str = "") -> dict:
    """List all proto-flights, optionally filtered by status."""
    flights = list_proto_flights(status)
    return {"flights": flights, "count": len(flights)}


def main():
    """Run the MCP server."""
    logger.info("Starting Flight Predictor MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
