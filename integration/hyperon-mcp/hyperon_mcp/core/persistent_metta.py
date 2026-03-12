"""
Persistent MeTTa instance management with registry-backed persistence.

Provides singleton-style persistent MeTTa instances with atomspace state
that persists across process restarts via HEAVEN registry system.
"""

from typing import Dict, List, Optional, Any
from hyperon import MeTTa, S, V, E, GroundingSpaceRef
import threading
import logging

try:
    from heaven_base.registry.registry_service import RegistryService
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    RegistryService = None

logger = logging.getLogger(__name__)


class PersistentMeTTa:
    """
    Persistent MeTTa instance with atomspace that accumulates state.

    Unlike the Docker-based approach which creates fresh containers each call,
    this maintains a persistent MeTTa() instance and atomspace across operations.
    """

    def __init__(self, name: str = "default"):
        """
        Initialize persistent MeTTa instance with registry persistence.

        Args:
            name: Instance identifier for multiple isolated instances
        """
        self.name = name
        self.metta = MeTTa()
        self.space = self.metta.space()
        self._lock = threading.Lock()

        # Setup registry persistence
        if REGISTRY_AVAILABLE:
            self.registry = RegistryService()
            self.registry_name = f"hyperon_metta_{name}"
            self.registry.create_registry(self.registry_name)
            self._load_from_registry()
        else:
            self.registry = None
            logger.warning("HEAVEN registry not available - persistence disabled")

        logger.info(f"Initialized persistent MeTTa instance: {name}")

    def _load_from_registry(self):
        """Load all atoms from registry into atomspace."""
        if not self.registry:
            return

        atoms_dict = self.registry.get_all(self.registry_name)
        if not atoms_dict:
            logger.info(f"No persisted atoms found for {self.name}")
            return

        loaded = 0
        for key, atom_str in atoms_dict.items():
            try:
                atom = self.metta.parse_single(atom_str)
                self.space.add_atom(atom)
                loaded += 1
            except Exception as e:
                logger.error(f"Failed to load atom {key}: {e}")

        logger.info(f"Loaded {loaded} atoms from registry for {self.name}")

    def _save_to_registry(self, atom_str: str):
        """Save a single atom to registry."""
        if not self.registry:
            return

        # Use hash of atom as key to avoid duplicates
        import hashlib
        key = hashlib.md5(atom_str.encode()).hexdigest()
        self.registry.add(self.registry_name, key, atom_str)

    def add_atom_from_string(self, atom_str: str) -> str:
        """
        Add atom to atomspace from MeTTa string representation.

        Args:
            atom_str: MeTTa expression like "(isa dog mammal)"

        Returns:
            Success message with atom count
        """
        with self._lock:
            # Parse and add atom
            atom = self.metta.parse_single(atom_str)
            self.space.add_atom(atom)
            self._save_to_registry(atom_str)

            count = self.space.atom_count()
            logger.debug(f"Added atom: {atom_str}, total count: {count}")
            return f"Atom added: {atom_str}\nTotal atoms: {count}"

    def add_atoms_batch(self, atoms: List[str]) -> str:
        """
        Add multiple atoms at once.

        Args:
            atoms: List of MeTTa expression strings

        Returns:
            Summary of additions
        """
        with self._lock:
            added = []
            for atom_str in atoms:
                atom = self.metta.parse_single(atom_str)
                self.space.add_atom(atom)
                self._save_to_registry(atom_str)
                added.append(atom_str)

            return f"Added {len(added)} atoms"

    def query(self, query_str: str, flat: bool = False) -> str:
        """
        Query the atomspace using MeTTa.

        Args:
            query_str: MeTTa query like "!(match &self (isa $x mammal) $x)"
            flat: Whether to flatten nested results

        Returns:
            Query results as string
        """
        with self._lock:
            logger.debug(f"Executing query: {query_str}")
            results = self.metta.run(query_str, flat=flat)
            logger.debug(f"Query returned {len(results)} results")
            return str(results)

    def get_all_atoms(self) -> List[str]:
        """
        Get all atoms currently in the atomspace.

        Returns:
            List of atom string representations
        """
        with self._lock:
            atoms = self.space.get_atoms()
            return [str(atom) for atom in atoms]

    def atom_count(self) -> int:
        """
        Get current atom count.

        Returns:
            Number of atoms in atomspace
        """
        with self._lock:
            return self.space.atom_count()

    def clear(self) -> str:
        """
        Clear all atoms from atomspace.

        Returns:
            Confirmation message
        """
        with self._lock:
            # Get all atoms and remove them
            atoms = self.space.get_atoms()
            for atom in atoms:
                self.space.remove_atom(atom)

            return f"Cleared atomspace (was {len(atoms)} atoms)"


# Global instance registry
_instances: Dict[str, PersistentMeTTa] = {}
_instances_lock = threading.Lock()


def get_metta_instance(name: str = "default") -> PersistentMeTTa:
    """
    Get or create a persistent MeTTa instance.

    Args:
        name: Instance identifier

    Returns:
        PersistentMeTTa instance
    """
    with _instances_lock:
        if name not in _instances:
            _instances[name] = PersistentMeTTa(name)
        return _instances[name]
