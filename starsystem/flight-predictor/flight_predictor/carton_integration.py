"""
CartON Integration for Flight Predictor.

- Calls CartON add_concept to create concepts
- Writes flight config JSONs with Heaven Ref DSL
- At render time, refs pull from CartON
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

HEAVEN_DATA = Path(os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data"))
FLIGHTS_DIR = HEAVEN_DATA / "jit_flights"
FLIGHTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Heaven Ref DSL - References to CartON concepts
# =============================================================================

def make_carton_ref(concept_name: str) -> dict:
    """Create a Heaven ref that calls CartON at render time."""
    return {
        "type": "reference",
        "content": f'dynamic_call={{"path": "carton_mcp", "func": "get_concept", "args": {{"concept_name": "{concept_name}"}}}}'
    }


def make_freestyle(text: str) -> dict:
    """Create a freestyle block (literal text)."""
    return {"type": "freestyle", "content": text}


def make_instruction_template(what_concept: str, how_concept: str) -> list:
    """Create composed instruction from What and How concepts."""
    return [
        make_freestyle("WHAT: "),
        make_carton_ref(what_concept),
        make_freestyle("\nHOW: "),
        make_carton_ref(how_concept)
    ]


# =============================================================================
# CartON Concept Creation - Import carton library
# =============================================================================

def _get_carton_add_concept():
    """Get carton's add_concept function."""
    try:
        from carton_mcp.core import add_concept
        return add_concept
    except ImportError:
        logger.exception("carton_mcp not available, concepts won't be persisted")
        return None


def create_concept(concept_name: str, description: str, relationships: list[dict]) -> bool:
    """
    Create a concept in CartON.

    Every concept must have: is_a, part_of, has, instantiates
    """
    add_concept = _get_carton_add_concept()
    if not add_concept:
        logger.error(f"Cannot create concept {concept_name}: carton not available")
        return False

    try:
        add_concept(
            concept_name=concept_name,
            concept=description,
            relationships=relationships
        )
        return True
    except Exception as e:
        logger.exception(f"Failed to create concept {concept_name}: {e}")
        return False


# =============================================================================
# JIT Flight Building - Helpers
# =============================================================================

def _create_step_concepts(
    step: dict, flight_id: str, flight_concept: str
) -> tuple[str, list[str], dict]:
    """Create CartON concepts for a single step. Returns (step_concept, concepts_created, step_config)."""
    step_num = step["step_number"]
    step_concept = f"JIT_Step_{flight_id}_{step_num}"
    what_concept = f"JIT_Step_What_{flight_id}_{step_num}"
    how_concept = f"JIT_Step_How_{flight_id}_{step_num}"
    concepts = []

    # WHAT concept
    create_concept(
        concept_name=what_concept,
        description=f"Use {step['capability_type']} {step['capability_name']} for: {step['description']}",
        relationships=[
            {"relationship": "is_a", "related": ["Step_What"]},
            {"relationship": "part_of", "related": [step_concept]},
            {"relationship": "has", "related": [step["capability_name"]]},
            {"relationship": "instantiates", "related": ["Step_What_Pattern"]},
        ]
    )
    concepts.append(what_concept)

    # HOW concept
    create_concept(
        concept_name=how_concept,
        description=step["instructions"],
        relationships=[
            {"relationship": "is_a", "related": ["Step_How"]},
            {"relationship": "part_of", "related": [step_concept]},
            {"relationship": "has", "related": [what_concept]},
            {"relationship": "instantiates", "related": ["Step_How_Pattern"]},
        ]
    )
    concepts.append(how_concept)

    # STEP concept
    create_concept(
        concept_name=step_concept,
        description=f"Step {step_num}: {step['description']}",
        relationships=[
            {"relationship": "is_a", "related": ["JIT_Flight_Step"]},
            {"relationship": "part_of", "related": [flight_concept]},
            {"relationship": "has", "related": [what_concept, how_concept]},
            {"relationship": "instantiates", "related": ["Flight_Step_Pattern"]},
        ]
    )
    concepts.append(step_concept)

    # Step config with refs
    step_config = {
        "name": f"step_{step_num}",
        "description": [make_carton_ref(step_concept)],
        "instructions": make_instruction_template(what_concept, how_concept),
        "capability_type": step["capability_type"],
        "capability_name": step["capability_name"],
    }

    return step_concept, concepts, step_config


def _write_flight_config(
    flight_id: str, flight_concept: str, observation: str, step_configs: list[dict]
) -> Path:
    """Build and write flight config JSON with Heaven Ref DSL."""
    flight_config = {
        "id": flight_id,
        "name": [make_carton_ref(flight_concept)],
        "observation": observation,
        "description": [make_freestyle("JIT Flight: "), make_carton_ref(flight_concept)],
        "domain": "jit_generated",
        "steps": step_configs,
        "created_at": datetime.utcnow().isoformat(),
    }
    config_path = FLIGHTS_DIR / f"{flight_id}.json"
    config_path.write_text(json.dumps(flight_config, indent=2))
    return config_path


# =============================================================================
# JIT Flight Building - Main
# =============================================================================

def build_jit_flight(observation: str, confirmed_steps: list[dict]) -> dict:
    """Build a JIT flight: create CartON concepts + write flight config JSON."""
    flight_id = f"jit_{uuid.uuid4().hex[:8]}"
    flight_concept = f"JIT_Flight_{flight_id}"

    concepts_created = []
    step_configs = []
    step_concepts = []

    # Create concepts for each step
    for step in confirmed_steps:
        step_concept, concepts, step_config = _create_step_concepts(
            step, flight_id, flight_concept
        )
        step_concepts.append(step_concept)
        concepts_created.extend(concepts)
        step_configs.append(step_config)

    # FLIGHT concept
    create_concept(
        concept_name=flight_concept,
        description=f"JIT flight for: {observation}",
        relationships=[
            {"relationship": "is_a", "related": ["JIT_Flight"]},
            {"relationship": "part_of", "related": ["JIT_Flight_Registry"]},
            {"relationship": "has", "related": step_concepts},
            {"relationship": "instantiates", "related": ["Flight_Pattern"]},
        ]
    )
    concepts_created.append(flight_concept)

    # Write flight config
    config_path = _write_flight_config(flight_id, flight_concept, observation, step_configs)

    return {
        "flight_id": flight_id,
        "flight_concept": flight_concept,
        "flight_config_path": str(config_path),
        "concepts_created": concepts_created,
        "step_count": len(confirmed_steps),
    }


def list_proto_flights(status: str = "") -> list[dict]:
    """List all JIT flights from the flights directory."""
    flights = []
    for path in FLIGHTS_DIR.glob("*.json"):
        try:
            config = json.loads(path.read_text())
            flights.append({
                "id": config.get("id"),
                "observation": config.get("observation", "")[:60],
                "step_count": len(config.get("steps", [])),
                "path": str(path),
            })
        except Exception:
            logger.exception(f"Failed to read flight config {path}")
            continue
    return flights


def get_flight_config(flight_id: str) -> dict | None:
    """Get a flight config by ID."""
    path = FLIGHTS_DIR / f"{flight_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None
