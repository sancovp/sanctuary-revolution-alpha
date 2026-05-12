#!/usr/bin/env python3
"""
Hyperon MeTTa Core Library

ALL business logic for hyperon-mcp.
NO MCP decorators - just plain Python functions.
Server imports these and wraps them.
"""

import os
import sys
import logging
from typing import Optional, List

# Import utility functions
from ..tools.metta_tool import (
    metta_query_util,
    metta_add_rule_util,
    metta_list_rules_util
)
from .carton_init import initialize_carton_atomspace, is_carton_initialized

# Setup logging - MUST go to stderr for MCP
logging.basicConfig(
    level=logging.CRITICAL,  # CRITICAL only - INFO floods stderr and breaks MCP on Antigravity
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # MCP operates on stderr
)
logger = logging.getLogger(__name__)


def internal_metta_exec(
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
    logger.info(f"MeTTa exec request on {space}")
    return metta_query_util(query=program, registry_name=space, flat=flat)



def internal_metta_add_atom(
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
    logger.info(f"Add atom to {space}")
    return metta_add_rule_util(rule=atom, registry_name=space)



def internal_metta_add_atoms_batch(
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
    logger.info(f"Batch add {len(atoms)} atoms to {space}")
    from ..core.atomspace_registry import AtomspaceRegistry
    registry = AtomspaceRegistry(space)
    return registry.add_rules_batch(atoms)



def internal_metta_list_atoms(
    space: str = "default"
) -> str:
    """
    List all atoms currently in the persistent space.

    Args:
        space: Space name (default: "default")

    Returns:
        List of all atoms with count
    """
    logger.info(f"List atoms in {space}")
    return metta_list_rules_util(registry_name=space)



def internal_metta_atom_count(
    space: str = "default"
) -> str:
    """
    Get count of atoms in the space.

    Args:
        space: Space name (default: "default")

    Returns:
        Atom count
    """
    from ..core.atomspace_registry import AtomspaceRegistry
    registry = AtomspaceRegistry(space)
    count = registry.rule_count()
    return f"Space '{space}' contains {count} atoms"



def internal_metta_load_from_file(
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
    logger.info(f"Load from file request: {path} -> {space}")
    from ..core.atomspace_registry import AtomspaceRegistry
    registry = AtomspaceRegistry(space)
    return registry.load_from_file(path, batch_by)


# ============================================================================
# CARTON TOOLS (Ontology Engineering with DAG Validation)
# ============================================================================


def internal_carton_add_concept(
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
    logger.info(f"Carton add_concept: {concept_name} at {base_path}")

    # Initialize carton atomspace if not already done
    if not is_carton_initialized():
        logger.info("Carton atomspace not initialized, initializing now...")
        init_result = initialize_carton_atomspace()
        logger.info(f"Initialization result: {init_result}")

    from ..core.atomspace_registry import AtomspaceRegistry
    carton = AtomspaceRegistry("carton")

    if relationships is None:
        relationships = []

    # Build MeTTa relationship list: ((is_a (Parent1 Parent2)) (part_of (Whole1)))
    def to_metta_list(items):
        return "(" + " ".join(items) + ")"

    metta_rel_strs = []
    for rel in relationships:
        rel_type = rel.get("relationship", "")
        related = rel.get("related", [])
        if rel_type and related:
            related_list = to_metta_list(related)
            metta_rel_strs.append(f"({rel_type} {related_list})")

    metta_rels_str = "(" + " ".join(metta_rel_strs) + ")" if metta_rel_strs else "()"

    # Step 1: Call MeTTa add-concept to validate and add atoms to atomspace
    # CORRECT metta-motto pattern: MeTTa only manages atomspace, no I/O
    query = f'!(add-concept {concept_name} {metta_rels_str})'
    logger.info(f"Calling MeTTa: {query}")

    try:
        metta_result = carton.query_with_rules(query, flat=False)
        logger.info(f"MeTTa result: {metta_result}")
    except Exception as e:
        logger.error(f"MeTTa query failed: {e}", exc_info=True)
        return f"❌ MeTTa validation failed: {str(e)}"

    # Step 2: If MeTTa validation succeeded, write files from atomspace
    # Check if result contains Valid (not Error)
    result_str = str(metta_result)
    if 'Error' in result_str:
        logger.warning(f"MeTTa returned Error: {result_str}")
        return f"❌ Validation failed: {result_str}"

    # Import the I/O function
    from carton_hyperon.carton_io_operations import write_concept_from_atomspace

    # Write files by reading from atomspace
    try:
        files_result = write_concept_from_atomspace(
            concept_name=concept_name,
            description=description,
            base_path=base_path,
            atomspace_registry=carton
        )
        return f"Success: {files_result}"
    except Exception as e:
        logger.error(f"File writing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error writing files: {e}"



def internal_carton_query_ontology(
    query: str
) -> str:
    """
    Query the Carton ontology graph with MeTTa.

    The carton atomspace contains:
    - Ontology rules (is_a, part_of, instantiates with DAG validation)
    - All concept relationships added via add_concept
    - Auto-discovered relationships from concept descriptions

    Args:
        query: MeTTa query string, e.g.:
               "!(get-is-a Neural_Network)" - get direct is_a parents
               "!(get-all-ancestors-is-a Neural_Network)" - get all ancestors
               "!(match &self (is_a $x Machine_Learning) $x)" - find all children

    Returns:
        Query results

    Example queries:
        - Get direct parents: "!(get-is-a Neural_Network)"
        - Get all ancestors: "!(get-all-ancestors-is-a Neural_Network)"
        - Find concepts that are_a ML: "!(match &self (is_a $x Machine_Learning) $x)"
        - Check for cycles: "!(has-cycle-is-a? SomeConcept TargetConcept)"
    """
    logger.info(f"Carton ontology query: {query}")

    # Initialize carton atomspace if not already done
    if not is_carton_initialized():
        logger.info("Carton atomspace not initialized, initializing now...")
        init_result = initialize_carton_atomspace()
        logger.info(f"Initialization result: {init_result}")

    from ..core.atomspace_registry import AtomspaceRegistry
    carton = AtomspaceRegistry("carton")

    result = carton.query_with_rules(query, flat=False)
    logger.info(f"Query result: {result}")
    return result



def internal_carton_list_concepts(
    base_path: str
) -> str:
    """
    List all concepts in Carton filesystem.

    Args:
        base_path: Path to Carton base directory

    Returns:
        List of concept names
    """
    logger.info(f"List concepts at: {base_path}")

    # Initialize carton atomspace if not already done
    if not is_carton_initialized():
        logger.info("Carton atomspace not initialized, initializing now...")
        init_result = initialize_carton_atomspace()
        logger.info(f"Initialization result: {init_result}")

    # Call grounded Python function directly
    from ..core.persistent_metta import get_metta_instance
    carton_metta = get_metta_instance("carton")

    query = f'!(py-get-existing-concepts "{base_path}")'
    result = carton_metta.query(query, flat=False)
    logger.info(f"List concepts result: {result}")
    return result



def internal_carton_validate_relationship(
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
    logger.info(f"Validate: {source} {rel_type} {target}")

    # Initialize carton atomspace if not already done
    if not is_carton_initialized():
        init_result = initialize_carton_atomspace()
        logger.info(f"Initialization result: {init_result}")

    from ..core.atomspace_registry import AtomspaceRegistry
    carton = AtomspaceRegistry("carton")

    # Call appropriate validation function
    validation_funcs = {
        "is_a": "valid-is-a?",
        "part_of": "valid-part-of?",
        "instantiates": "valid-instantiates?"
    }

    if rel_type not in validation_funcs:
        return f"Error: Unknown relationship type '{rel_type}'. Must be is_a, part_of, or instantiates."

    func = validation_funcs[rel_type]
    query = f"!({func} {source} {target})"

    result = carton.query_with_rules(query, flat=False)
    logger.info(f"Validation result: {result}")
    return result


# Core library - no server startup code
# Server imports these functions and wraps them with @mcp.tool()
