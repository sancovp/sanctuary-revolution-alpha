"""
Atomspace-based registry for MeTTa rules and atoms.

Replaces the SQLite-based registry with direct atomspace storage,
enabling true metagraph operations instead of text concatenation.
"""

from typing import List, Optional
from .persistent_metta import get_metta_instance
import logging
import traceback as tb

logger = logging.getLogger(__name__)


class AtomspaceRegistry:
    """
    Registry for MeTTa rules stored directly in atomspace.

    Unlike the SQLite approach which stores rules as text and concatenates them,
    this stores rules as actual atoms in the atomspace, enabling:
    - Incremental pattern matching
    - True metagraph queries
    - No reparsing overhead
    """

    def __init__(self, registry_name: str = "default"):
        """
        Initialize atomspace registry.

        Args:
            registry_name: Name of MeTTa instance to use
        """
        self.registry_name = registry_name
        self.metta = get_metta_instance(registry_name)
        logger.info(f"Initialized atomspace registry: {registry_name}")

    def add_rule(self, rule_str: str) -> str:
        """
        Add a MeTTa rule to the atomspace.

        Args:
            rule_str: MeTTa expression like "(= (ancestor $x $z) ...)"

        Returns:
            Success message
        """
        try:
            result = self.metta.add_atom_from_string(rule_str)
            logger.info(f"Added rule to {self.registry_name}: {rule_str}")
            return result
        except Exception as e:
            logger.error(f"Failed to add rule: {e}\n{tb.format_exc()}")
            return f"Error adding rule: {str(e)}"

    def add_rules_batch(self, rules: List[str]) -> str:
        """
        Add multiple rules at once.

        Args:
            rules: List of MeTTa expression strings

        Returns:
            Summary of additions
        """
        try:
            result = self.metta.add_atoms_batch(rules)
            logger.info(f"Added {len(rules)} rules to {self.registry_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to add rules batch: {e}\n{tb.format_exc()}")
            return f"Error adding rules: {str(e)}"

    def query_with_rules(self, query_str: str, flat: bool = False) -> str:
        """
        Query atomspace with all accumulated rules as context.

        This is the key difference from the Docker approach:
        All rules are already in the atomspace, no text concatenation needed.

        Args:
            query_str: MeTTa query
            flat: Whether to flatten results

        Returns:
            Query results
        """
        try:
            result = self.metta.query(query_str, flat=flat)
            logger.debug(f"Query executed on {self.registry_name}")
            return result
        except Exception as e:
            logger.error(f"Query failed: {e}\n{tb.format_exc()}")
            return f"Error executing query: {str(e)}"

    def get_all_rules(self) -> List[str]:
        """
        Get all rules currently in the atomspace.

        Returns:
            List of rule string representations
        """
        return self.metta.get_all_atoms()

    def rule_count(self) -> int:
        """
        Get count of rules/atoms in atomspace.

        Returns:
            Number of atoms
        """
        return self.metta.atom_count()

    def clear_all_rules(self) -> str:
        """
        Clear all rules from atomspace.

        Returns:
            Confirmation message
        """
        result = self.metta.clear()
        logger.info(f"Cleared all rules from {self.registry_name}")
        return result

    def load_from_file(self, path: str, batch_by: int = 100) -> str:
        """
        Load atoms from file into atomspace.

        Args:
            path: Path to file with one atom per line
            batch_by: Batch size for loading (default: 100)

        Returns:
            Loading summary
        """
        try:
            with open(path, 'r') as f:
                atoms = [line.strip() for line in f if line.strip()]

            total = len(atoms)
            loaded = 0

            # Load in batches
            for i in range(0, total, batch_by):
                batch = atoms[i:i+batch_by]
                result = self.metta.add_atoms_batch(batch)
                if "Added" not in result:
                    raise Exception(f"Batch add failed: {result}")
                loaded += len(batch)
                logger.info(f"Batch {i//batch_by + 1}: {loaded}/{total} atoms - {result}")

            msg = f"Successfully loaded {total} atoms from {path}"
            logger.info(msg)
            return msg

        except Exception as e:
            logger.error(f"Failed to load from file: {e}\n{tb.format_exc()}")
            return f"Error loading from file: {str(e)}"
