# Findings: owl_types accumulator structure

Date: 2026-05-13
Source: `/home/GOD/gnosys-plugin-v2/base/crystal-ball-alpha/youknow_v225/youknow_kernel_current/youknow_kernel/`

---

## Entry point

`compile_and_respond()` at `compiler.py:2555` — alias that calls `youknow(statement)` at `compiler.py:392`.

`youknow()` is the public compile entry point. It is also exported via `__init__.py:44` as `from .core import YOUKNOW, get_youknow`.

---

## Callgraph trace

### Hop 1: youknow() -> _compile_packet()

- Caller: `compiler.py:434` — `packet = _compile_packet(statement, parsed)`
- Callee: `compiler.py:588` — `def _compile_packet(statement, parsed)`
- What's passed: the raw `statement` string and the `ParsedStatement` object from `parse_statement()`.

### Hop 2: _compile_packet() -> get_type_registry()

- Caller: `compiler.py:590` — `from .owl_types import get_type_registry as get_cat`
- Callee: `owl_types.py:237` — `def get_type_registry() -> OWLTypeRegistry`
- What's passed: nothing. Returns the module-level singleton.
- The returned registry is stored in local variable `cat` at `compiler.py:594`: `cat = get_cat()`.

### Hop 3: _compile_packet() passes `cat` to internal functions

The `cat` object (the singleton `OWLTypeRegistry` instance) is passed as a positional/keyword argument to:

- `compiler.py:595` — `_build_subject_concept(parsed, cat)` (defined at `compiler.py:1064`)
- `compiler.py:597-601` — `_build_continuous_emr_telemetry(parsed=parsed, ..., cat=cat)` (defined at `compiler.py:1408`)
- `compiler.py:608` — `_build_abcd_state(parsed, cat)` (defined at `compiler.py:1378`)
- `compiler.py:610` — `HyperedgeValidator(cat=cat)` (from `hyperedge.py`)
- `compiler.py:611` — `DerivationValidator(cat=cat)` (from `derivation.py`)

### Hop 4: _compile_packet() also re-imports get_type_registry for restriction walk

- `compiler.py:631` — `from .owl_types import get_type_registry` — used at `compiler.py:633`: `registry = get_type_registry()`. Same singleton. Used inside the recursive restriction walk (`_walk_restrictions` closure) for `registry.is_known()` and `registry.traces_to_root()` calls.

### Additional callgraph branches (all within compiler.py, all calling get_type_registry()):

| Line | Inside function | Usage |
|------|----------------|-------|
| 590 | `_compile_packet()` | Primary: builds cat, passes to validators |
| 631 | `_compile_packet()` | Restriction walk: `registry.is_known()`, `registry.traces_to_root()` |
| 971 | `_admit_to_ontology_state()` | Gets cat for `YOUKNOW.add()` call |
| 1566 | `_build_controller_telemetry()` (inside OWL reasoner block) | Checks `target not in cat.entities` |
| 1637 | `_build_ses_report()` | Passes cat to `HyperedgeValidator` and `DerivationValidator` |
| 1747 | `_get_chain()` | Gets cat for `trace_to_root()` calls |
| 1894 | `_persist()` | **ACCUMULATION**: calls `registry.add(name=parsed.subject, is_a=is_a)` |
| 2224 | `_persist_to_soup()` | **ACCUMULATION**: calls `cat.add(name=..., is_a=..., part_of=..., ...)` |
| 2455 | `_is_known_or_typed()` | Checks `reg.is_known(name)` |

---

## Accumulator definition

**File:** `owl_types.py:22-268`

**Declaration shape: Module-level singleton, lazy-initialized via function.**

```python
# owl_types.py:233-234
# Singleton
_registry: Optional[OWLTypeRegistry] = None

# owl_types.py:237-242
def get_type_registry() -> OWLTypeRegistry:
    """Get the singleton OWL type registry."""
    global _registry
    if _registry is None:
        _registry = OWLTypeRegistry()
    return _registry
```

The `OWLTypeRegistry` class (line 22) holds state in `self._classes: Dict[str, List[str]]` — a dict mapping class name to list of parent names. Initialized in `__init__` -> `_load()` which parses `uarl.owl` and `starsystem.owl` from the same directory via XML ElementTree. No HTTP, no owlready2.

The `add()` method (line 84) is the accumulation mechanism: `self._classes[name] = parents`. This is in-memory only — dies with the process. Comment at line 88: "Stored in memory (dies with daemon). Persistent accumulation is via domain OWL files."

A `reset_type_registry()` function (line 245) sets `_registry = None`, used by tests.

Backward-compat aliases at lines 252-255:
```python
CategoryOfCategories = OWLTypeRegistry
CatEntity = _MinimalEntity
get_cat = get_type_registry
reset_cat = reset_type_registry
```

---

## Import sites

### Within youknow_kernel/ (production code)

| File:Line | Access pattern | Singleton or new instance? |
|-----------|---------------|---------------------------|
| `__init__.py:60` | Top-level: `from .owl_types import CategoryOfCategories, CatEntity, PrimitiveCategory, PrimitiveRelationship, get_cat, reset_cat` | Exports the factory function and class; does NOT call get_cat() at import time |
| `core.py:21-27` | Top-level: `from .owl_types import CategoryOfCategories, CatEntity, PrimitiveCategory, PrimitiveRelationship, get_cat` | Exports factory function. `YOUKNOW` dataclass uses `field(default_factory=get_cat)` at line 75 — calls get_cat() at YOUKNOW instantiation time, gets singleton |
| `compiler.py:590` | Lazy: `from .owl_types import get_type_registry as get_cat` inside `_compile_packet()` | Singleton via `get_cat()` |
| `compiler.py:631` | Lazy: `from .owl_types import get_type_registry` inside `_compile_packet()` | Singleton via `get_type_registry()` |
| `compiler.py:971` | Lazy: inside `_admit_to_ontology_state()` | Singleton |
| `compiler.py:1566` | Lazy: inside `_build_controller_telemetry()` OWL reasoner block | Singleton |
| `compiler.py:1637` | Lazy: inside `_build_ses_report()` | Singleton |
| `compiler.py:1747` | Lazy: inside `_get_chain()` | Singleton |
| `compiler.py:1894` | Lazy: inside `_persist()` | Singleton — **writes to it via `.add()`** |
| `compiler.py:2224` | Lazy: inside `_persist_to_soup()` | Singleton — **writes to it via `.add()`** |
| `compiler.py:2455` | Lazy: inside `_is_known_or_typed()` | Singleton — read only |
| `hyperedge.py:455` | Lazy: inside `if __name__ == "__main__"` test block | Singleton |
| `completeness.py:290` | Lazy: inside `if __name__ == "__main__"` test block | Singleton |

### Outside youknow_kernel/ (consumer code)

| File:Line | Access pattern | Singleton or new instance? |
|-----------|---------------|---------------------------|
| `crystal_ball_mcp.py:682` | Top-level: `from youknow_kernel.owl_types import get_cat` then at line 684: `_cat = get_cat()` | Singleton — called at module load time, stored in module-level `_cat` variable. Comment: "Pre-load Cat_of_Cat so it stays persistent across calls" |

### Test files (all use backward-compat aliases)

| File | Access pattern |
|------|---------------|
| `tests/test_abcd_grounding.py:4` | `from youknow_kernel.owl_types import reset_cat` |
| `tests/test_witness_phase.py:9` | `from youknow_kernel.owl_types import get_cat, reset_cat` |
| `tests/test_operational_wiring.py:4` | `from youknow_kernel.owl_types import get_cat, reset_cat` |
| `tests/test_ses_typed_depth.py:4` | `from youknow_kernel.owl_types import reset_cat` |
| `tests/test_statement_predicates.py:6` | `from youknow_kernel.owl_types import get_cat, reset_cat` |
| `tests/test_uarl_pattern_typing.py:11` | `from youknow_kernel.owl_types import get_cat, reset_cat` |
| `tests/test_promotion_gate.py:7` | `from youknow_kernel.owl_types import get_cat, reset_cat` |

All tests call `reset_cat()` (which sets `_registry = None`) for test isolation, then `get_cat()` to get a fresh singleton.

---

## Singleton vs instantiation verdict

**The accumulator IS a module-level singleton.** It is safe for sharing via Python import caching.

The pattern:
1. `_registry` is a module-level `Optional[OWLTypeRegistry]` initialized to `None`.
2. `get_type_registry()` lazily creates it on first call, returns the same instance thereafter.
3. Every call site in production code (compiler.py, core.py, crystal_ball_mcp.py) calls `get_type_registry()` / `get_cat()` and receives the same object.
4. Mutations happen via `registry.add()` which writes to `self._classes` dict — visible to all holders of the singleton.
5. No locking. No thread safety. Pure single-threaded assumption.

**For SOMA py_calls:** Any Python code that does `from youknow_kernel.owl_types import get_type_registry; reg = get_type_registry()` within the same Python process will receive the same `OWLTypeRegistry` instance, including all accumulated concepts added via `registry.add()` during that process lifetime. Python import system caches the module, so `_registry` is shared. No explicit handle-passing is needed.

---

## Notes / surprises

1. **Two accumulation sites, different richness.** `_persist()` at line 1894 calls `registry.add(name, is_a=is_a)` with only the `is_a` list. `_persist_to_soup()` at line 2224 calls `cat.add(name, is_a, part_of, has_part, produces, y_layer, description, properties)` with the full concept shape. However, the `add()` method at `owl_types.py:84-92` only stores `name -> parents`: `self._classes[name] = parents`. All other kwargs (`part_of`, `has_part`, `produces`, `y_layer`, `description`, `properties`) are accepted via `**kwargs` at line 84 but silently dropped — the method body only uses `is_a`.

2. **system_type_validator.py does NOT use owl_types.** It independently parses the same OWL files (`uarl.owl`, `starsystem.owl`) at import time via its own XML parsing code, building its own `SystemTypeShape` dicts. It has no dependency on or reference to `OWLTypeRegistry`. This means there are two independent OWL parsers loading the same files in the same process.

3. **daemon.py does NOT directly import owl_types.** It imports `compiler.py`'s `youknow` function, which internally reaches `owl_types` via lazy imports. The daemon's `_youknow_compile()` calls pass through the singleton path.

4. **crystal_ball_mcp.py eagerly loads the singleton** at module import time (line 684: `_cat = get_cat()`), storing it in `_cat`. This means if the MCP server process is long-lived, the singleton accumulates across all calls for the lifetime of that process.

5. **No persistence of accumulated state.** The `add()` method comment says "Stored in memory (dies with daemon). Persistent accumulation is via domain OWL files." The in-memory `_classes` dict is the only accumulation surface. Process restart = accumulated concepts lost.

6. **The `_EntitiesProxy` compatibility layer** (lines 171-206) makes the registry look like a dict of `_MinimalEntity` objects. `_MinimalEntity` has fields for `part_of`, `has_part`, `produces`, `properties`, `y_layer`, `description`, `relationships` — but since `add()` only stores the `is_a` parents list, entities created via `add()` always have empty values for these fields when retrieved via the proxy.
