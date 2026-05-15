# Findings: continuous_emr shape and role

Date: 2026-05-13
Agent: Opus 4.6 (1M context) code-reading research agent

---

## Entry point

`youknow()` function at `compiler.py:392`. This is the one-shot compiler step called by external LLM loops (dragonbones hook). It is NOT `YOUKNOW.add()` in `core.py:109` -- that is an older path through the pipeline. The compiler's `youknow()` is the production entry point per local rules and the module docstring.

---

## Callgraph trace

### Hop 1: youknow() -> _compile_packet()

- Caller: `compiler.py:434` -- `packet = _compile_packet(statement, parsed)`
- Callee: `compiler.py:588` -- `def _compile_packet(statement, parsed)`
- Passed: the raw statement string and the `ParsedStatement` (subject/predicate/object/additional)

### Hop 2: _compile_packet() -> _build_continuous_emr_telemetry()

- Caller: `compiler.py:597-602`
  ```python
  continuous_emr = _build_continuous_emr_telemetry(
      parsed=parsed,
      subject_concept=subject_concept,
      normalized_relations=normalized_relations,
      cat=cat,
  )
  ```
- Callee: `compiler.py:1408` -- `def _build_continuous_emr_telemetry(...)`
- Passed: the ParsedStatement, a dict `subject_concept` (built by `_build_subject_concept`), a dict `normalized_relations`, and the `cat` type registry

### Hop 3: _build_continuous_emr_telemetry() -> ContinuousEMRProcessor.add_concept()

- Caller: `compiler.py:1432-1437`
  ```python
  result = _emr_processor.add_concept(
      name=parsed.subject,
      description=subject_concept.get("description", ""),
      is_a=list(subject_concept.get("is_a", [])),
      relationships=relationships,
  )
  ```
- Callee: `continuous_emr.py:68` -- `def add_concept(self, name, description, is_a, relationships)`
- Passed: concept name (str), description (str), is_a (list of str), relationships (dict of str -> list of str, built by `_concept_relationships_for_emr`)

### Hop 3b: _build_continuous_emr_telemetry() -> ContinuousEMRProcessor.get_emr_gradient()

- Caller: `compiler.py:1438` -- `gradient = _emr_processor.get_emr_gradient(parsed.subject)`
- Callee: `continuous_emr.py:254` -- `def get_emr_gradient(self, concept)`
- Passed: concept name (str)

### Return path

The return value of `_build_continuous_emr_telemetry` is a dict:
```python
{
    "enabled": True,
    "seed_concept_count": len(cat.entities),
    "result": result,          # from add_concept
    "gradient": gradient,      # from get_emr_gradient
    "candidate_count": len(_emr_processor.candidates),
}
```
This dict is stored at `compiler.py:831` as `diagnostics["continuous_emr"]` inside the CompilePacket. It is telemetry only -- it does NOT gate any decision. The promotion gate (`packet.decision`) is built from chain_complete, derivation_state, compression, and system_type_validator. The continuous_emr dict rides along in diagnostics.

---

## continuous_emr top-level signatures

File: `continuous_emr.py` (327 lines, 1 class, 1 dataclass)

### IsomorphismCandidate (dataclass, line 25)
```python
@dataclass
class IsomorphismCandidate:
    thing_a: str
    thing_b: str
    similarity_type: str  # 'name', 'structure', 'relationship', 'pattern'
    confidence: float
    discovered_at: datetime
```

### ContinuousEMRProcessor (class, line 34)

Constructor: `__init__(self, pio_engine: Optional[PIOEngine] = None)`

Public methods:
- `add_concept(self, name, description, is_a, relationships) -> Dict[str, Any]` (line 68)
- `get_emr_gradient(self, concept) -> Dict[str, Any]` (line 254)
- `get_all_auto_potentials(self) -> Dict[str, List[str]]` (line 274)
- `promote_to_reifies(self, concept) -> bool` (line 278)

Private methods:
- `_check_name_similarity(self, name) -> List[Dict]` (line 155)
- `_check_structure_similarity(self, name, is_a) -> List[Dict]` (line 174)
- `_check_relationship_similarity(self, name, relationships) -> List[Dict]` (line 198)
- `_add_to_auto_potential(self, thing_a, thing_b, similarity_type)` (line 222)
- `_get_potentials_for(self, concept) -> List[str]` (line 246)

---

## What it walks / accumulates / returns

### What it walks

Each call to `add_concept` walks **all previously-seen concepts** (stored in `self.concepts: Dict[str, Dict[str, Any]]`). Specifically:

1. **Name similarity** (`_check_name_similarity`): Splits the new name and every existing name into word sets (underscore-delimited), computes Jaccard-like overlap (`len(common) / max(len(a), len(b))`). Threshold: 0.6.

2. **Structure similarity** (`_check_structure_similarity`): Compares the new concept's `is_a` set against every existing concept's `is_a` set. Same overlap metric. Threshold: 0.7.

3. **Relationship similarity** (`_check_relationship_similarity`): Compares the new concept's relationship type keys against every existing concept's relationship type keys. Same overlap metric. Threshold: 0.5.

All three walks are linear scans over `self.concepts`. For N concepts seen so far, each `add_concept` call is O(N).

### What it accumulates (in-memory state)

- `self.concepts: Dict[str, Dict]` -- every concept ever added, with its description, is_a, relationships, and timestamp. Grows monotonically.
- `self.candidates: List[IsomorphismCandidate]` -- every isomorphism candidate ever detected. Grows monotonically. Never pruned.
- `self.auto_potentials: Dict[str, List[str]]` -- groupings of concepts by similarity type key (e.g., `"Auto_name_similarity"`, `"Auto_structure_similarity"`). Members accumulate.
- `self.emr_state: Dict[str, str]` -- per-concept EMR state string: `'embodies'` (default on add) or `'manifests'` (if any isomorphism discovered) or `'reifies'` (only via manual `promote_to_reifies()`).

### Side effects

- If `self.engine` (PIOEngine) is not None and an auto_potential group reaches 2+ members, calls `self.engine.discover_isomorphism()` and `self.engine.add_to_potential()` (line 235-244). These mutate PIOEngine's internal state.
- No OWL writes. No CartON writes. No disk writes. All state is in-memory only.

### What add_concept returns

```python
{
    'name': str,
    'emr_state': str,           # 'embodies' or 'manifests'
    'discoveries': int,         # count of new isomorphism candidates
    'candidates': List[Dict],   # each: {'with': str, 'type': str, 'confidence': float}
    'auto_potentials': List[str] # potential hyperedge group strings containing this concept
}
```

### What get_emr_gradient returns

```python
{
    'concept': str,
    'emr_state': str,
    'isomorphism_candidates': int,
    'potential_hyperedges': List[str],
    'gradient': {
        'embodies': int,   # candidates with confidence < 0.5
        'manifests': int,  # candidates with 0.5 <= confidence < 0.8
        'reifies': int,    # candidates with confidence >= 0.8
    }
}
```

---

## Recursion shape

**Structurally flat. No recursion.**

`add_concept` does three linear scans over `self.concepts` (name, structure, relationship similarity). None of these scans call `add_concept` again or recurse into sub-concepts. The `_add_to_auto_potential` method that fires on each match is also flat -- it appends to a list and optionally calls `PIOEngine.discover_isomorphism()` / `add_to_potential()`, neither of which calls back into `ContinuousEMRProcessor`.

There is no recursion over partials, no recursion over morphisms, no recursive restriction walk. The entire module is a flat accumulate-and-scan pattern.

---

## Import sites

### Site 1: compiler.py:1422 (lazy import inside function)
```python
from .continuous_emr import ContinuousEMRProcessor
```
Access pattern: Instantiates `ContinuousEMRProcessor()` once (module-level singleton `_emr_processor`), then calls `.add_concept()` and `.get_emr_gradient()` on every `youknow()` invocation. The singleton persists across compiler calls within a single process.

### Site 2: pipeline.py:21 (top-level import)
```python
from youknow_kernel.continuous_emr import ContinuousEMRProcessor
```
Access pattern: `YouknowPipeline.__init__` creates `self.emr = ContinuousEMRProcessor(pio_engine=self.pio)` at line 89. Pipeline's `add_concept` calls `self.emr.add_concept(...)` at line 122. This is the older path through `YOUKNOW.add()` -> `pipeline.add_concept()`, which is NOT the production path (production goes through `compiler.py:youknow()`).

### Site 3: tests/test_operational_wiring.py:62,73 (test consumer)
Tests read `diagnostics["continuous_emr"]` from compiler output to verify the telemetry dict is present and has expected shape. No direct import of the class.

---

## Relation to EMR principle

Per the global rule `emr-reifies-is-result-not-input.md`, EMR means:
- **Embodies** = pre-linguistic having (something exists at all)
- **Manifests** = explicit declaring (relationships added)
- **Reifies** = the system's record labeled knowledge or hallucination (chain closure check)

`ContinuousEMRProcessor` does NOT implement reifies-as-knowledge chain closure. It implements a **similarity-based isomorphism detector** that uses the EMR labels as state tags:

- A concept starts as `'embodies'` (line 91 -- always, unconditionally on add).
- If any isomorphism candidate is discovered, it moves to `'manifests'` (line 142).
- `'reifies'` is only reachable via `promote_to_reifies()` (line 278), which is a manual flag flip. No automatic chain closure check triggers it.

The `get_emr_gradient` method (line 254) bins candidates by confidence into embodies/manifests/reifies buckets, but this is a confidence-band labeling of similarity scores, not a derivation chain closure check.

**In summary:** `continuous_emr.py` uses EMR terminology as state labels for an isomorphism detection system. It is NOT the runtime implementation of reifies-as-knowledge chain closure. The actual chain closure logic lives in the compiler's `_walk_restrictions` (compiler.py:700) and `system_type_validator.py`. The continuous_emr module is a telemetry/discovery side-channel that rides alongside the real validation path.

---

## Notes / surprises

1. **Two independent ContinuousEMRProcessor instances exist.** The compiler path (`_emr_processor` singleton at compiler.py:1405) and the pipeline path (`YouknowPipeline.emr` at pipeline.py:89) each create their own instance. They do not share state. In production (compiler path), only the compiler's singleton is used.

2. **The pipeline path is dead in production.** `YOUKNOW.add()` in core.py calls `_get_pipeline()` which creates a `YouknowPipeline`. But `youknow()` in compiler.py does NOT go through `YOUKNOW.add()`. It builds its own `_compile_packet` and calls `_build_continuous_emr_telemetry` directly. The pipeline's EMR processor is only reachable if something calls `YOUKNOW.add(skip_pipeline=False)`, which the production dragonbones hook path does not do.

3. **continuous_emr output is telemetry only -- it gates nothing.** The `continuous_emr` dict ends up in `diagnostics` (compiler.py:831) but is never read by any decision logic. The promotion gate, SOUP/CODE decision, and artifact generation all ignore it entirely. It is pure instrumentation.

4. **O(N) per call, no pruning.** `self.concepts` and `self.candidates` grow monotonically. In a long-running daemon process, every `youknow()` call scans all previously-seen concepts. For the typical dragonbones hook usage (one call per LLM turn), N stays small. But in a batch scenario, this would degrade.

5. **PIOEngine integration is conditional.** The `try/except ImportError` at line 16-21 means if `pio.py` fails to import, `PIOEngine` is `None`, and `ContinuousEMRProcessor.__init__` creates `self.engine = None`. The `_add_to_auto_potential` method guards on `if self.engine` (line 235), so PIO integration silently degrades to no-op.

6. **No persistence.** All state is in-memory. Process restart loses all accumulated isomorphism candidates and EMR state. The module has no save/load, no disk serialization, no CartON writes.

7. **Migration sequencing implication (per dispatch prompt question):** Since continuous_emr is structurally flat (no recursion over partials or morphisms), it does NOT require reifies-terminal to be in place before migration. It can migrate as a simple py_call wrapper. Its EMR state labels are string tags, not chain closure computations.
