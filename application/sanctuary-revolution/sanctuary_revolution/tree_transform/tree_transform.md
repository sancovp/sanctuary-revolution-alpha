# Project: tree_transform/

# 1. pyproject.toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tree_transform"
version = "0.1.0"
description = "Tree transformation toolkit with exact-sequence validators"
authors = [ { name="Your Name", email="you@example.com" } ]
readme = "README.md"
license = { file = "LICENSE" }
requires-python = ">=3.8"

[project.scripts]
run-tests = "tree_transform.run_tests:main"

```

```python
# 2. tree_transform/core.py
from typing import Dict
import numpy as np

class PropertyModule:
    """
    Represents a module over the path-algebra of a tree,
    where each vertex carries a 'property' vector space.
    """
    def __init__(self, dims: Dict[str, int]):
        self.dims = dims
        self.total_dim = sum(dims.values())
        self._offsets = self._compute_offsets()

    def _compute_offsets(self) -> Dict[str, int]:
        offsets = {}
        idx = 0
        for v, d in self.dims.items():
            offsets[v] = idx
            idx += d
        return offsets

    def zero_vector(self) -> np.ndarray:
        return np.zeros((self.total_dim, 1))

    def basis_vector(self, vertex: str, index: int) -> np.ndarray:
        vec = np.zeros((self.total_dim, 1))
        start = self._offsets[vertex]
        vec[start + index, 0] = 1
        return vec

class InclusionMap:
    """
    Represents an injective linear map g: S -> T
    between two PropertyModules.
    """
    def __init__(self, source: PropertyModule, target: PropertyModule, matrix: np.ndarray):
        self.S = source
        self.T = target
        self.g = matrix
        self._validate_dimensions()

    def _validate_dimensions(self):
        assert self.g.shape == (self.T.total_dim, self.S.total_dim), \
            "Inclusion map dimensions do not match source/target modules"

    def is_injective(self, tol: float = 1e-8) -> bool:
        rank = np.linalg.matrix_rank(self.g, tol)
        return rank == self.S.total_dim
```

```python
# 3. tree_transform/validators.py
import numpy as np
from tree_transform.core import InclusionMap

class ExactSequenceValidator:
    @staticmethod
    def compute_quotient_projection(inc: InclusionMap, tol: float = 1e-8) -> np.ndarray:
        """
        Computes P: T -> Q = T / im(g) as left nullspace of g.
        P has shape (q_dim, T.total_dim).
        """
        # SVD on g.T to find nullspace
        U, S_vals, Vt = np.linalg.svd(inc.g.T, full_matrices=True)
        rank = np.linalg.matrix_rank(inc.g, tol)
        nullspace = Vt[rank:].copy()
        return nullspace

    @staticmethod
    def check_exactness(inc: InclusionMap, P: np.ndarray, tol: float = 1e-8) -> bool:
        if not inc.is_injective(tol):
            return False
        if not np.allclose(P @ inc.g, 0, atol=tol):
            return False
        if np.linalg.matrix_rank(P, tol) != P.shape[0]:
            return False
        return True
```

```python
# 4. tree_transform/utils.py
import numpy as np

def compute_offsets(dims: Dict[str, int]) -> Dict[str, int]:
    offsets = {}
    idx = 0
    for v, d in dims.items():
        offsets[v] = idx
        idx += d
    return offsets

# Future helpers (e.g., SVD caching) can go here
```

```python
# 5. tests/test_core.py
import numpy as np
import pytest
from tree_transform.core import PropertyModule, InclusionMap


def test_property_module_offsets_and_basis():
    dims = {'A': 2, 'B': 3}
    pm = PropertyModule(dims)
    assert pm.total_dim == 5
    # Basis vector for B, index 2
    vec = pm.basis_vector('B', 2)
    # offset of B is 2
    assert vec[2 + 2, 0] == 1


def test_inclusion_map_injective():
    T = PropertyModule({'A': 2, 'B': 3})
    S = PropertyModule({'A': 2})
    g = np.zeros((T.total_dim, S.total_dim))
    g[:2, :] = np.eye(2)
    inc = InclusionMap(S, T, g)
    assert inc.is_injective()
```

```python
# 6. tests/test_validators.py
import numpy as np
import pytest
from tree_transform.core import PropertyModule, InclusionMap
from tree_transform.validators import ExactSequenceValidator


def test_exact_sequence_validator():
    T = PropertyModule({'A': 2, 'B': 3})
    S = PropertyModule({'A': 2})
    g = np.zeros((T.total_dim, S.total_dim))
    g[:2, :] = np.eye(2)
    inc = InclusionMap(S, T, g)
    P = ExactSequenceValidator.compute_quotient_projection(inc)
    assert ExactSequenceValidator.check_exactness(inc, P)
```

```python
# 7. tree_transform/run_tests.py
"""
Simple test runner: finds all files matching test_*.py under tests/
Executes any zero-argument functions named test_* as golden or custom tests.
Exits with status 0 only if all tests pass.
"""
import os
import sys
import importlib.util
import inspect

def discover_and_run_tests():
    failures = []
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    for fname in os.listdir(test_dir):
        if fname.startswith('test_') and fname.endswith('.py'):
            path = os.path.join(test_dir, fname)
            spec = importlib.util.spec_from_file_location(fname[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
                # Discover all callables starting with test_ and taking zero args
                for name, obj in inspect.getmembers(mod, inspect.isfunction):
                    if name.startswith('test_'):
                        sig = inspect.signature(obj)
                        if len(sig.parameters) == 0:
                            try:
                                obj()
                            except Exception as e:
                                failures.append((f"{fname}:{name}", str(e)))
            except Exception as e:
                failures.append((fname, f"Module load error: {e}"))
    return failures


def main():
    failures = discover_and_run_tests()
    if failures:
        print("FAILED tests:")
        for loc, err in failures:
            print(f" - {loc}: {err}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)

if __name__ == '__main__':
    main()

## Make everything
```python
from typing import List, Tuple, Dict
import numpy as np
from tree_transform.core import PropertyModule, InclusionMap
from tree_transform.validators import ExactSequenceValidator

class SESLayer:
    """
    Represents a single short exact sequence layer:
      0 → A_{i-1} --f--> A_i --g--> Q_i → 0
    """
    def __init__(
        self,
        source: PropertyModule,
        target: PropertyModule,
        inclusion_matrix: np.ndarray
    ):
        # A_{i-1} and A_i
        self.source = source
        self.target = target

        # f: source → target
        self.inc_map = InclusionMap(source, target, inclusion_matrix)

        # compute g: target → Q_i projection
        self.projection = ExactSequenceValidator.compute_quotient_projection(self.inc_map)
        assert ExactSequenceValidator.check_exactness(self.inc_map, self.projection), \
            "Layer failed exactness"

    @property
    def quotient_dim(self) -> int:
        return self.projection.shape[0]

    def __repr__(self):
        return (f"<SESLayer source_dim={self.source.total_dim} "
                f"target_dim={self.target.total_dim} quotient_dim={self.quotient_dim}>")

class Resolution:
    """
    Chains multiple SESLayer instances into a full filtration.
    Terminates when the last quotient is zero-dimensional.
    """
    def __init__(self, base_dims: Dict[str, int]):
        # Initialize A_0
        self.layers: List[SESLayer] = []
        self.current_module = PropertyModule(base_dims)

    def add_layer(self, next_dims: Dict[str, int], inclusion_matrix: np.ndarray):
        # next_dims defines dims for A_i
        next_module = PropertyModule(next_dims)
        layer = SESLayer(self.current_module, next_module, inclusion_matrix)
        self.layers.append(layer)
        self.current_module = next_module

    def is_complete(self) -> bool:
        # Completed if the latest layer's quotient_dim == 0
        return bool(self.layers and self.layers[-1].quotient_dim == 0)

    def instantiate(self) -> PropertyModule:
        if not self.is_complete():
            raise RuntimeError("Resolution not yet complete; quotient_dim != 0")
        return self.current_module

# -------- Example Usage --------

# 1) Base universal type dims
base_dims = {'Entity': 2, 'Relation': 1}

# 2) First extension: propose dims and matrix
dims1 = {'Entity': 2, 'Relation': 1, 'Attribute': 3, 'Event': 2}
# Build inclusion_matrix f1 of shape (total_dim1, total_dim0)
A0 = PropertyModule(base_dims)
A1 = PropertyModule(dims1)
# For demo, embed A0 as first dims0 coordinates
inc_matrix_1 = np.zeros((A1.total_dim, A0.total_dim))
inc_matrix_1[:A0.total_dim, :A0.total_dim] = np.eye(A0.total_dim)

# 3) Second extension with empty quotient dims to terminate
dims2 = dims1.copy()  # no new properties implies dims same as previous
# inclusion as identity on dims1 space
A2 = PropertyModule(dims2)
inc_matrix_2 = np.eye(A2.total_dim)

# Build resolution
res = Resolution(base_dims)
res.add_layer(dims1, inc_matrix_1)  # SES layer 1
res.add_layer(dims2, inc_matrix_2)  # SES layer 2 (termination)

# Instantiate final module
final_module = res.instantiate()
print("Resolution complete. Final dims:", final_module.dims)
```

