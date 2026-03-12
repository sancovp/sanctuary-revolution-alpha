#!/usr/bin/env python3
"""
Hyperon MeTTa MCP Server

MCP tool wrappers ONLY - all logic in core.py
"""

import sys
import logging
from typing import Optional, List
from fastmcp import FastMCP

# Import ALL business logic from core
from ..core.core import (
    internal_metta_exec,
    internal_metta_add_atom,
    internal_metta_add_atoms_batch,
    internal_metta_list_atoms,
    internal_metta_atom_count,
    internal_metta_load_from_file,
    internal_carton_add_concept,
    internal_carton_query_ontology,
    internal_carton_list_concepts,
    internal_carton_validate_relationship
)
from ..core.carton_init import initialize_carton_atomspace

# Setup logging - MUST go to stderr for MCP
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # MCP operates on stderr
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("hyperon-mcp")


@mcp.tool()
async def metta_exec(
    program: str,
    space: str = "default",
    flat: bool = False
) -> str:
    """
    Execute MeTTa program in persistent space.

    MeTTa is a meta-circular interpreter, not a database.
    This executes programs, not queries.

    Args:
        program: MeTTa program to execute (e.g., "!(add-concept X)" or "!(car (A B C))")
        space: Space name containing atoms (default: "default")
        flat: Whether to flatten nested results

    Returns:
        Execution result as string

    Examples:
        Execute function: program="!(car (A B C))"
        Pattern match: program="!(match &self (isa $x mammal) $x)"
    """
    return internal_metta_exec(program, space, flat)


@mcp.tool()
async def metta_add_atom(
    atom: str,
    space: str = "default"
) -> str:
    """
    Add an atom to the persistent space.

    Args:
        atom: MeTTa expression like "(isa dog mammal)" or "(= (car ($a $b)) $a)"
        space: Space name (default: "default")

    Returns:
        Success message with atom count

    Examples:
        Fact: atom="(isa dog mammal)"
        Program: atom="(= (car ($a $b)) $a)"
    """
    return internal_metta_add_atom(atom, space)


@mcp.tool()
async def metta_add_atoms_batch(
    atoms: List[str],
    space: str = "default"
) -> str:
    """
    Add multiple atoms to the persistent space at once.

    Args:
        atoms: List of MeTTa expressions
        space: Space name (default: "default")

    Returns:
        Summary of additions

    Example:
        atoms=["(isa dog mammal)", "(isa cat mammal)", "(isa mammal animal)"]
    """
    return internal_metta_add_atoms_batch(atoms, space)


@mcp.tool()
async def metta_list_atoms(
    space: str = "default"
) -> str:
    """
    List all atoms currently in the persistent space.

    Args:
        space: Space name (default: "default")

    Returns:
        List of all atoms with count
    """
    return internal_metta_list_atoms(space)


@mcp.tool()
async def metta_atom_count(
    space: str = "default"
) -> str:
    """
    Get count of atoms in the space.

    Args:
        space: Space name (default: "default")

    Returns:
        Atom count
    """
    return internal_metta_atom_count(space)


@mcp.tool()
async def metta_load_from_file(
    path: str,
    batch_by: Optional[int] = 100,
    space: Optional[str] = "default"
) -> str:
    """
    Load atoms from file into atomspace.

    Args:
        path: Path to file with one atom per line
        batch_by: Batch size for loading (default: 100)
        space: Atomspace name (default: "default")

    Returns:
        Loading summary
    """
    return internal_metta_load_from_file(path, batch_by, space)


# ============================================================================
# CARTON TOOLS (Ontology Engineering with DAG Validation)
# ============================================================================

@mcp.tool()
async def __carton__add_concept(
    concept_name: str,
    description: str,
    base_path: str,
    relationships: Optional[List[dict]] = None
) -> str:
    """
    Add a concept to Carton knowledge graph with ontology validation.

    Uses MeTTa reasoning engine for:
    - DAG cycle detection (prevents circular is_a, part_of, instantiates)
    - Auto-discovery of concept mentions in description
    - Auto-linking markdown references

    Args:
        concept_name: Name of the concept (will be normalized to Title_Case)
        description: Concept description (mentions of other concepts auto-linked)
        base_path: Path to Carton base directory
        relationships: List of relationship dicts with format:
                      [{"relationship": "is_a", "related": ["Parent1", "Parent2"]},
                       {"relationship": "part_of", "related": ["Whole"]}]

    Returns:
        Success message with created files or error message

    Example:
        relationships=[
            {"relationship": "is_a", "related": ["Machine_Learning", "AI"]},
            {"relationship": "part_of", "related": ["Data_Science"]}
        ]
    """
    return internal_carton_add_concept(concept_name, description, base_path, relationships)


@mcp.tool()
async def __carton__query_ontology(
    query: str
) -> str:
    """
    Query the Carton ontology graph with MeTTa.

    Available query functions:
        get-is-a, get-part-of, get-instantiates
        get-all-ancestors-is-a, get-all-ancestors-part-of, get-all-ancestors-instantiates
        would-create-cycle-is-a?, would-create-cycle-part-of?, would-create-cycle-instantiates?
        match &self (relationship $x Target) $x

    Args:
        query: MeTTa query string

    Returns:
        Query results
    """
    return internal_carton_query_ontology(query)


@mcp.tool()
async def __carton__list_concepts(
    base_path: str
) -> str:
    """
    List all concepts in Carton filesystem.

    Args:
        base_path: Path to Carton base directory

    Returns:
        List of concept names
    """
    return internal_carton_list_concepts(base_path)


@mcp.tool()
async def __carton__validate_relationship(
    source: str,
    rel_type: str,
    target: str
) -> str:
    """
    Validate a relationship before adding (cycle detection).

    Args:
        source: Source concept
        rel_type: Relationship type (is_a, part_of, or instantiates)
        target: Target concept

    Returns:
        "Valid" if relationship is safe to add, error message if would create cycle

    Example:
        source="Neural_Network", rel_type="is_a", target="Machine_Learning"
    """
    return internal_carton_validate_relationship(source, rel_type, target)


if __name__ == "__main__":
    # Initialize carton atomspace on server startup
    logger.info("Initializing carton atomspace on server startup...")
    init_result = initialize_carton_atomspace()
    logger.info(f"Carton initialization: {init_result}")

    # Run the MCP server
    mcp.run()
