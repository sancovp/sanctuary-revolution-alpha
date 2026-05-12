"""OWL Type Registry — thin wrapper over OWL classes for type lookups.

Replaces cat_of_cat.py. No Python dict shadow of the ontology.
Loads OWL classes once from owl_server /classes endpoint (or direct XML parse).
Provides: is this a known type? Does its chain close? What are the typed symbols?
"""

import json
import logging
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

OWL_NS = "http://www.w3.org/2002/07/owl#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"


class OWLTypeRegistry:
    """Provides type lookups from OWL classes. No entity cache."""

    def __init__(self):
        # name → list of parent names (from rdfs:subClassOf)
        self._classes: Dict[str, List[str]] = {}
        self._load()

    def _load(self):
        """Load classes from OWL files directly (no owlready2, no HTTP)."""
        owl_dir = Path(__file__).parent
        for owl_file in ["uarl.owl", "starsystem.owl"]:
            owl_path = owl_dir / owl_file
            if owl_path.exists():
                self._parse_owl(owl_path)

        # Cat_of_Cat is the terminal axiom — literal self-reference so downstream
        # consumers (core.py:90) see Cat_of_Cat in its own is_a. trace_to_root() and
        # traces_to_root() handle the self-loop and terminate on parent == current.
        self._classes["Cat_of_Cat"] = ["Cat_of_Cat"]

        # Root OWL classes trace to Cat_of_Cat.
        # These have no rdfs:subClassOf in the OWL but must chain-close.
        for root_class in ["Entity", "Soup", "Ont", "Reality"]:
            if root_class in self._classes and not self._classes[root_class]:
                self._classes[root_class] = ["Cat_of_Cat"]
            elif root_class not in self._classes:
                self._classes[root_class] = ["Cat_of_Cat"]

        logger.info(f"OWLTypeRegistry loaded {len(self._classes)} classes")

    def _parse_owl(self, owl_path: Path):
        """Parse OWL/RDF-XML for class names and subClassOf parents."""
        try:
            tree = ET.parse(str(owl_path))
            root = tree.getroot()
            for cls_elem in root.iter(f"{{{OWL_NS}}}Class"):
                about = cls_elem.get(f"{{{RDF_NS}}}about")
                if not about:
                    continue
                name = about.split("#")[-1] if "#" in about else about.split("/")[-1]
                if not name or name.startswith("http"):
                    continue

                parents = []
                for sub in cls_elem.findall(f"{{{RDFS_NS}}}subClassOf"):
                    ref = sub.get(f"{{{RDF_NS}}}resource", "")
                    if ref:
                        parent = ref.split("#")[-1] if "#" in ref else ref.split("/")[-1]
                        if parent and parent != "Thing":
                            parents.append(parent)

                if name not in self._classes:
                    self._classes[name] = parents
                else:
                    # Merge parents from multiple OWL files
                    for p in parents:
                        if p not in self._classes[name]:
                            self._classes[name].append(p)
        except Exception as e:
            logger.warning(f"Could not parse {owl_path}: {e}")

    def add(self, name: str, is_a: List[str] = None, **kwargs) -> None:
        """Register a user-defined concept so it's visible to the walk.

        This is the accumulation mechanism — concepts defined in the shell
        become known to subsequent calls. Stored in memory (dies with daemon).
        Persistent accumulation is via domain OWL files.
        """
        parents = list(is_a) if is_a else []
        self._classes[name] = parents

    def is_known(self, name: str) -> bool:
        """Is this a known OWL class or user-defined concept?"""
        return name in self._classes

    def get_parents(self, name: str) -> List[str]:
        """Get direct parents (subClassOf for OWL classes, is_a for user concepts)."""
        return list(self._classes.get(name, []))

    def trace_to_root(self, name: str) -> List[str]:
        """Trace subClassOf chain to Cat_of_Cat. Returns chain including name."""
        if name not in self._classes:
            return []

        chain = [name]
        current = name
        visited = set()

        while current and current not in visited:
            visited.add(current)
            parents = self._classes.get(current, [])
            if not parents:
                break
            parent = parents[0]  # Primary parent
            if parent == current:  # Self-loop (Cat_of_Cat)
                break
            chain.append(parent)
            current = parent

        return chain

    def traces_to_root(self, name: str) -> bool:
        """Does this class trace to Cat_of_Cat?"""
        chain = self.trace_to_root(name)
        return "Cat_of_Cat" in chain or name == "Cat_of_Cat"

    def typed_symbols(self) -> Set[str]:
        """All known class names — the set of typed symbols."""
        return set(self._classes.keys())

    # --- Compatibility with cat_of_cat interface (used by derivation.py, hyperedge.py) ---

    @property
    def entities(self) -> "_EntitiesProxy":
        """Dict-like proxy: `name in registry.entities` and `registry.entities.get(name)`."""
        return _EntitiesProxy(self)

    def validate_traces_to_root(self, name: str) -> bool:
        """Alias for traces_to_root — matches cat_of_cat interface."""
        return self.traces_to_root(name)

    def is_declared_bounded(self, name: str) -> bool:
        """All OWL classes are bounded by definition (they're code things)."""
        return self.is_known(name)

    def get(self, name: str, default=None):
        """Alias for entities.get() — matches cat_of_cat interface for core.py call sites
        (see Pattern_Cat_Of_Cat_Refactor_Incomplete_2026_05_12)."""
        return self.entities.get(name, default)

    def stats(self) -> Dict[str, Any]:
        """Ontology statistics. by_layer intentionally empty: Y-layer migrated to
        SOMA (soma_y_mesh.pl 2026-04-06); Python Y-layer path deprecated."""
        return {
            "total_entities": len(self._classes),
            "by_layer": {},
            "primitives": 0,
            "declared_bounded": len(self._classes),
        }


class _EntitiesProxy:
    """Dict-like proxy so `name in registry.entities` works."""

    def __init__(self, registry: OWLTypeRegistry):
        self._reg = registry

    def __contains__(self, name: str) -> bool:
        return self._reg.is_known(name)

    def get(self, name: str, default=None):
        if not self._reg.is_known(name):
            return default
        parents = self._reg.get_parents(name)
        # Return minimal entity-like object
        return _MinimalEntity(name=name, is_a=parents)

    def __getitem__(self, name: str):
        result = self.get(name)
        if result is None:
            raise KeyError(name)
        return result

    def keys(self):
        return self._reg.typed_symbols()

    def values(self):
        return [self.get(n) for n in self._reg.typed_symbols()]

    def items(self):
        return [(n, self.get(n)) for n in self._reg.typed_symbols()]

    def __iter__(self):
        return iter(self._reg.typed_symbols())

    def __len__(self):
        return len(self._reg.typed_symbols())


class _MinimalEntity:
    """Minimal entity data from OWL class — just name and parents."""

    def __init__(self, name: str, is_a: List[str]):
        self.name = name
        self.is_a = is_a
        self.part_of: List[str] = []
        self.has_part: List[str] = []
        self.produces: List[str] = []
        self.properties: Dict[str, any] = {}
        self.y_layer: Optional[str] = None
        self.description: str = ""
        self.relationships: Dict[str, List[str]] = {}

    def all_targets(self) -> Set[str]:
        targets = set(self.is_a)
        targets.update(self.part_of)
        targets.update(self.has_part)
        targets.update(self.produces)
        for rel_targets in self.relationships.values():
            targets.update(rel_targets)
        return targets


# Singleton
_registry: Optional[OWLTypeRegistry] = None


def get_type_registry() -> OWLTypeRegistry:
    """Get the singleton OWL type registry."""
    global _registry
    if _registry is None:
        _registry = OWLTypeRegistry()
    return _registry


def reset_type_registry():
    """Reset the registry (for testing)."""
    global _registry
    _registry = None


# --- Backward-compat aliases (for core.py / __init__.py exports) ---
CategoryOfCategories = OWLTypeRegistry
CatEntity = _MinimalEntity
get_cat = get_type_registry
reset_cat = reset_type_registry


class PrimitiveCategory:
    ENTITY = "Entity"
    CAT_OF_CAT = "Cat_of_Cat"


class PrimitiveRelationship:
    IS_A = "is_a"
    PART_OF = "part_of"
    HAS_PART = "has_part"
    PRODUCES = "produces"
