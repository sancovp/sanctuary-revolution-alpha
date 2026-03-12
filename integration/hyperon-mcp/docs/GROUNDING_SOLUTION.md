# Hyperon Grounding Solution: Complete Guide

## The Problem

When grounding Python functions to make them callable from MeTTa, we encountered unevaluated expressions:

```metta
!(py-write-description-file "/tmp/test" "Neural_Network" "A neural network")
; Returns: [[(py-write-description-file ...)]]  ← NOT CALLED!
```

No files were being created, functions weren't executing.

## The Root Causes

### 1. Missing `unwrap=True` Parameter

**Problem**: By default, `OperationAtom` doesn't unwrap Atom arguments to Python values.

**Wrong**:
```python
op = OperationAtom('my-func', my_function)  # Functions receive Atoms!
```

**Correct**:
```python
op = OperationAtom('my-func', my_function, unwrap=True)  # Functions receive Python values!
```

**What `unwrap=True` does**:
- Automatically converts MeTTa Atoms → Python values before calling function
- Automatically converts Python return values → MeTTa Atoms after function returns
- Example: ValueAtom(42) → 42 (Python int) → function runs → returns 84 → ValueAtom(84)

### 2. List Arguments Don't Unwrap to Python Lists

**Problem**: MeTTa list syntax `["a" "b" "c"]` is parsed as **3 separate arguments**, not a single list.

**What we expected**:
```metta
!(my-func ["a" "b" "c"])
; → my_func receives: ["a", "b", "c"] (Python list)
```

**What actually happens**:
```metta
!(my-func ["a" "b" "c"])
; → MeTTa calls: my_func("a", "b", "c")  ← 3 args!
; → Function expecting 1 arg fails!
```

**Solution**: Use **variadic arguments** (`*args`) in Python:

```python
def my_func(*items):
    # items is a Python tuple: ("a", "b", "c")
    item_list = list(items)
    # Now use item_list as normal Python list
```

**MeTTa call**:
```metta
!(my-func "a" "b" "c")  ; Pass args separately, NOT as ["a" "b" "c"]
```

## The Complete Solution

### Step 1: Create Wrapper Functions

File: `/tmp/heaven_data/carton_hyperon_python/carton_hyperon/hyperon_wrappers.py`

```python
"""
Hyperon-specific wrappers that handle MeTTa's calling conventions.
"""
from . import carton_io_operations as io_ops

# Direct pass-through for functions that don't take lists
get_existing_concepts = io_ops.get_existing_concepts
write_description_file = io_ops.write_description_file

# Wrapper for functions that take lists
def write_relationship_file(base_path: str, concept_name: str,
                           rel_type: str, *related_concepts) -> str:
    """
    Accepts variadic args from MeTTa, converts to list for Python function.

    MeTTa:   (py-write-relationship-file "base" "concept" "is_a" "item1" "item2")
    Python:  base_path="base", concept_name="concept", rel_type="is_a",
             *related_concepts=("item1", "item2")
    """
    related_list = list(related_concepts)
    return io_ops.write_relationship_file(base_path, concept_name,
                                         rel_type, related_list)
```

### Step 2: Ground with `unwrap=True`

File: `/tmp/hyperon-mcp/hyperon_mcp/core/carton_init.py`

```python
from hyperon import OperationAtom
from carton_hyperon import hyperon_wrappers as wrappers

groundings = {
    'py-write-description-file': wrappers.write_description_file,
    'py-write-relationship-file': wrappers.write_relationship_file,
}

for name, func in groundings.items():
    op_atom = OperationAtom(name, func, unwrap=True)  # ← CRITICAL!
    metta.register_atom(name, op_atom)
```

### Step 3: Call from MeTTa

```metta
; Create directories
!(py-create-concept-directories "/tmp/test" "Neural_Network")
; Returns: [["/tmp/test/concepts/Neural_Network"]]  ← Path created!

; Write description
!(py-write-description-file "/tmp/test" "Neural_Network" "A neural network")
; Returns: [["/tmp/test/concepts/Neural_Network/components/description.md"]]

; Write relationships - pass items as SEPARATE ARGS, not list
!(py-write-relationship-file "/tmp/test" "Neural_Network" "is_a"
                             "Machine_Learning" "AI_Model")
; ← Two related concepts passed separately
; Returns: [["/tmp/test/concepts/Neural_Network/components/is_a/Neural_Network_is_a.md"]]
```

## Verification

Run tests:
```bash
env PYTHONPATH="/tmp/hyperon-mcp:/tmp/heaven_data/carton_hyperon_python" \
    HEAVEN_DATA_DIR="/tmp/heaven_data" \
    python3 /tmp/hyperon-mcp/tests/test_grounded_io_operations.py
```

Expected result:
```
TEST SUMMARY
Passed: 5/5
Failed: 0/5
```

Check created files:
```bash
ls -la /tmp/test_carton_io/concepts/Neural_Network/components/
# Should show:
# - description.md
# - is_a/Neural_Network_is_a.md
```

## Key Takeaways

1. **Always use `unwrap=True`** when grounding Python functions
   - Without it, functions receive Atoms instead of Python values
   - Functions won't execute properly

2. **Lists must be passed as variadic arguments**
   - MeTTa `["a" "b"]` syntax = 2 separate args, NOT a list
   - Python function must use `*args` to collect them
   - Convert to list inside function: `list(args)`

3. **Create wrapper layer for grounding**
   - Keep core Python functions clean (standard signatures)
   - Create Hyperon-specific wrappers that handle MeTTa conventions
   - Ground the wrappers, not the core functions

4. **Test incrementally**
   - Test basic grounding first (single args)
   - Then test variadic args
   - Then test complete workflows
   - Verify files actually created on disk

## Common Mistakes

### ❌ Wrong: Grounding without `unwrap=True`
```python
op = OperationAtom('my-func', my_function)  # Functions get Atoms!
```

### ✅ Correct:
```python
op = OperationAtom('my-func', my_function, unwrap=True)  # Functions get Python values!
```

### ❌ Wrong: Expecting list argument from MeTTa
```python
def my_func(items: List[str]):  # Won't work from MeTTa!
    ...
```
```metta
!(my-func ["a" "b"])  ; Passes 2 args, not 1 list!
```

### ✅ Correct: Use variadic args
```python
def my_func(*items):  # Collects all args as tuple
    item_list = list(items)  # Convert to list
    ...
```
```metta
!(my-func "a" "b")  ; Pass separately
```

## Architecture Pattern

```
MeTTa Layer:
  !(py-write-relationship-file "base" "concept" "is_a" "item1" "item2")
           ↓ (Hyperon runtime)
Grounding Layer (hyperon_wrappers.py):
  write_relationship_file(base, concept, rel_type, *items)
    → Converts variadic args to list
           ↓
Core Python Layer (carton_io_operations.py):
  write_relationship_file(base, concept, rel_type, related_list: List[str])
    → Standard Python function with proper types
           ↓
File System:
  /base/concepts/concept/components/is_a/concept_is_a.md created
```

## References

- Hyperon SDK: https://github.com/trueagi-io/hyperon-experimental
- MeTTa Spec: https://github.com/trueagi-io/metta-wam
- GROUNDING_REFERENCE in system prompt (this document's examples)
