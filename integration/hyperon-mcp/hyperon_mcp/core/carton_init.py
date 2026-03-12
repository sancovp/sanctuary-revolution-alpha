"""
Carton Atomspace Initialization

Initializes the 'carton' atomspace with:
1. Ontology rules from carton_ontology.metta
2. Grounded Python I/O operations from carton_hyperon package
"""

import logging
import re
from pathlib import Path
from .atomspace_registry import AtomspaceRegistry

logger = logging.getLogger(__name__)


def _split_metta_expressions(content: str) -> list:
    """
    Split MeTTa file content into individual top-level expressions.

    Args:
        content: MeTTa file content

    Returns:
        List of expression strings
    """
    expressions = []
    current = []
    depth = 0
    in_string = False
    escape_next = False

    for char in content:
        if escape_next:
            current.append(char)
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            current.append(char)
            continue

        if char == '"':
            in_string = not in_string
            current.append(char)
            continue

        if in_string:
            current.append(char)
            continue

        if char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            current.append(char)
            depth -= 1
            if depth == 0:
                expr = ''.join(current).strip()
                if expr and not expr.startswith(';;'):
                    expressions.append(expr)
                current = []
        elif char == ';' and depth == 0:
            # Skip comments at top level
            continue
        else:
            current.append(char)

    return expressions


def initialize_carton_atomspace() -> str:
    """
    Initialize the 'carton' atomspace with ontology rules and grounded Python functions.

    This should be called once when the MCP server starts to set up the default
    carton atomspace that all Carton tools will use.

    Returns:
        Status message
    """
    logger.info("Initializing carton atomspace...")

    try:
        # Get or create the carton atomspace
        carton = AtomspaceRegistry("carton")

        # Load ontology rules from file
        ontology_file = Path(__file__).parent / "carton_ontology.metta"
        if not ontology_file.exists():
            logger.error(f"Ontology file not found: {ontology_file}")
            return f"Error: Ontology file not found at {ontology_file}"

        logger.info(f"Loading ontology from {ontology_file}")
        with open(ontology_file, 'r') as f:
            ontology_content = f.read()

        # Use MeTTa's parse_all to get expressions
        atoms = carton.metta.metta.parse_all(ontology_content)
        logger.info(f"Parsed {len(atoms)} atoms from ontology file")

        # Add atoms to atomspace
        for atom in atoms:
            carton.metta.space.add_atom(atom)

        logger.info(f"Added {len(atoms)} ontology atoms to atomspace")

        # Ground Python I/O operations using OperationAtom
        logger.info("Grounding Python I/O operations...")
        from hyperon import OperationAtom
        from carton_hyperon import hyperon_wrappers as wrappers

        groundings = {
            'py-get-existing-concepts': wrappers.get_existing_concepts,
            'py-auto-link-description': wrappers.auto_link_description,
            'py-find-mentioned-concepts': wrappers.find_mentioned_concepts,
            'py-create-concept-directories': wrappers.create_concept_directories,
            'py-write-description-file': wrappers.write_description_file,
            'py-write-relationship-file': wrappers.write_relationship_file,
            'py-write-main-concept-file': wrappers.write_main_concept_file,
            'py-write-itself-file': wrappers.write_itself_file,
            'py-create-concept-complete': wrappers.create_concept_complete,
        }

        for name, func in groundings.items():
            op_atom = OperationAtom(name, func, unwrap=False)
            carton.metta.metta.register_atom(name, op_atom)

        logger.info(f"Grounded {len(groundings)} Python I/O operations")

        atom_count = carton.rule_count()
        msg = f"Carton atomspace initialized successfully with {atom_count} atoms"
        logger.info(msg)
        return msg

    except Exception as e:
        logger.error(f"Failed to initialize carton atomspace: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error initializing carton atomspace: {str(e)}"


def is_carton_initialized() -> bool:
    """
    Check if carton atomspace is already initialized.

    Returns:
        True if carton atomspace exists and has atoms, False otherwise
    """
    try:
        carton = AtomspaceRegistry("carton")
        return carton.rule_count() > 0
    except Exception:
        return False
