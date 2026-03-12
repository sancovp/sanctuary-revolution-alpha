# Harness Emergence Framework

**Type:** PAIAB Library (Harnesses collection)
**Status:** Emergent → Actual
**Derived From:** Conversation Ingestion MCP V2 heat source analysis

---

## Core Insight

A tool becomes an agent harness when it shapes LLM probability toward correct action sequences rather than just executing commands.

**The Formula:**
```
TOOL + state_machine + typed_models + rejection_signals = AGENT_HARNESS
```

---

## Derivation Methodology

This framework was derived by tracing "heat sources" in the Conversation Ingestion MCP V2 - identifying exactly where and how the system constrains and steers LLM behavior.

### What is "Heat"?

Heat = anything that shapes LLM token probability distribution toward desired outcomes.

Sources of heat:
1. **Structure constraints** - Pydantic models with finite, typed fields
2. **Transition guards** - State machine checks that return (allowed, error)
3. **Rejection signals** - BLOCKED messages with `→` guidance arrows
4. **Coherence checking** - Batch simulation before application

### The Analysis Process

1. Identify the typed models (what states exist)
2. Trace the state machine (what transitions are valid)
3. Find rejection points (where operations get blocked)
4. Read the rejection messages (do they STEER or just BLOCK?)

---

## The Four Layers of Agent Harness Design

### Layer 1: Constraint Layer (Typed Models)

**Purpose:** Define the finite space of possible states.

**Implementation:** Pydantic BaseModel classes with typed fields.

```python
class Pair(BaseModel):
    strata: Optional[str] = None      # Constrained to registry values
    evolving: bool = False            # Binary state
    definition: bool = False          # Binary state
    concept_tags: List[str] = Field(default_factory=list)
    emergent_framework: Optional[str] = None
```

**Heat generated:**
- LLM cannot invent arbitrary properties
- Fields have known types and cardinality
- Derived state can be computed from fields

**Key pattern:** Add a method that computes phase/state from fields:
```python
def get_phase(self) -> int:
    if self.emergent_framework: return 4
    if self.concept_tags: return 3
    if self.definition: return 2
    if self.strata or self.evolving: return 1
    return 0
```

### Layer 2: Sequence Layer (State Machine)

**Purpose:** Define what transition sequences are valid.

**Implementation:** Static methods returning `Tuple[bool, Optional[str]]`

```python
class PairStateMachine:
    @staticmethod
    def can_add_definition(pair: Pair, pair_index: int) -> Tuple[bool, Optional[str]]:
        if not pair.strata:
            return False, "BLOCKED: ..."
        return True, None

    @staticmethod
    def apply_definition(pair: Pair) -> Pair:
        return Pair(..., definition=True, ...)
```

**Heat generated:**
- Operations must satisfy guards before execution
- Invalid sequences are rejected before side effects
- State transitions are explicit and auditable

**Key pattern:** Separate `can_X()` (guard) from `apply_X()` (effect):
- Guard checks preconditions, returns error message if blocked
- Apply creates new state (immutable pattern)

### Layer 3: Guidance Layer (Rejection Signals)

**Purpose:** Steer LLM toward correct action when blocked.

**Implementation:** Error messages with explicit next-action guidance.

```python
return False, (
    f"BLOCKED: Cannot add 'definition' to pair {pair_index}.\n"
    f"Current state: No strata assigned.\n"
    f"Required: Pair must have strata before adding definition.\n"
    f"→ First call: tag_pair({pair_index}, 'strata', '<strata_name>')"
)
```

**Heat generated:**
- LLM learns the correct sequence from rejection
- `→` arrows provide explicit next action
- Error messages include current state for debugging

**Key pattern:** Every BLOCKED message must have:
1. What was attempted
2. Current state
3. What is required
4. `→` Exact next action to take

### Layer 4: Optimization Layer (Coherence Checking)

**Purpose:** Allow batching operations that would individually fail.

**Implementation:** Simulate operations before applying.

```python
def check_batch_coherence(pair, pair_index, operations, registry):
    simulated = Pair(...)  # Copy current state

    for op in operations:
        # Check guard against SIMULATED state
        allowed, error = can_add_X(simulated, ...)
        if not allowed:
            return False, error
        # Apply to simulation (not real state)
        simulated = apply_X(simulated, ...)

    return True, None
```

**Heat generated:**
- LLM can batch `[strata, definition, concept]` in one call
- Ratcheting chain satisfied by operation ORDER within batch
- Atomic: all succeed or none applied

**Key pattern:**
- Simulate the full batch against a copy
- Check guards against simulated state (not real state)
- Only apply to real state if all guards pass

---

## Nesting: Multiple State Machines

Complex harnesses have nested state machines at different granularities:

```
PublishingSetStateMachine (cross-conversation)
    ↓ contains
ConversationStateMachine (per-conversation)
    ↓ contains
PairStateMachine (per-pair)
```

Each level has its own:
- State enum (what phases exist)
- Guards (what gates must pass)
- Rejection signals (what guidance to give)

**Phase gates between levels:**
- Pair reaches Phase 4 → contributes to Conversation Phase 4
- All pairs at Phase 4 → Conversation can advance to Phase 5
- All conversations at Phase 5 → PublishingSet can advance to Phase 6

---

## Heat Map Template

When analyzing any MCP for harness potential, create a heat map:

| Component | File | Lines | Heat Type |
|-----------|------|-------|-----------|
| Main model | models.py | X-Y | Structure constraint |
| Phase derivation | models.py | X-Y | Computed state |
| Transition guards | state_machine.py | X-Y | can_X methods |
| Phase gates | state_machine.py | X-Y | can_advance methods |
| Rejection messages | various | X-Y | BLOCKED + → guidance |
| Coherence checking | state_machine.py | X-Y | Batch simulation |

---

## Converting a Tool MCP to Agent Harness

### Step 1: Identify State

What are the meaningful states your tool operates on?

- If just CRUD on data → probably stays a tool
- If there's a SEQUENCE of operations → harness candidate
- If operations have PREREQUISITES → definitely harness candidate

### Step 2: Model the State

Create Pydantic models for:
- The entity being operated on (Pair, Task, Document, etc.)
- Any container states (Conversation, Project, Workflow, etc.)
- Any registry/reference data (Registry, Config, etc.)

### Step 3: Define Transitions

For each operation:
1. What state must exist before? (guard)
2. What state results after? (effect)
3. What's the error if guard fails? (rejection)

### Step 4: Write Steering Messages

Every rejection message must answer:
- What did you try?
- What's the current state?
- What's required?
- What should you do next? (the `→` arrow)

### Step 5: Add Batch Support

If users will want to do multiple operations at once:
1. Group operations by entity
2. Simulate in order
3. Check guards against simulation
4. Apply atomically if all pass

---

## Example: Conversation Ingestion MCP Heat Sources

This framework was derived from analyzing:

| Component | File | Lines | Heat Type |
|-----------|------|-------|-----------|
| Pair model | models.py | 19-86 | Structure constraint (finite fields) |
| Phase derivation | models.py | 75-85 | Computed state from tags |
| PairStateMachine guards | state_machine.py | 79-131 | Transition guards (can_add_X) |
| ConversationStateMachine gates | state_machine.py | 218-338 | Phase gates (can_advance) |
| PublishingSetStateMachine gates | state_machine.py | 389-448 | Cross-conversation gates |
| Ratcheting validators | ratcheting.py | 20-144 | Pure validation logic |
| Coherence checking | state_machine.py | 464-518 | Batch simulation |
| Rejection in tag_pair | tagging.py | 71-80, 96-97 | Tool-level blocking |
| Rejection in batch_tag_operations | tagging.py | 266-280, 293-299 | Batch-level blocking |

---

## Anti-Patterns

### Anti-Pattern 1: Blocking Without Steering

```python
# BAD - just blocks
return False, "Operation not allowed"

# GOOD - steers to next action
return False, (
    "BLOCKED: Cannot add concept without definition.\n"
    "→ First call: tag_pair(42, 'definition')"
)
```

### Anti-Pattern 2: Mutable State in Guards

```python
# BAD - guard has side effects
def can_add_X(pair):
    pair.modified = True  # NO! Guards must be pure
    return True, None

# GOOD - guards are pure, apply_ methods create new state
def can_add_X(pair):
    return True, None

def apply_X(pair):
    return Pair(..., modified=True)
```

### Anti-Pattern 3: No Coherence for Batches

```python
# BAD - checks each against CURRENT state
for op in operations:
    allowed, error = can_X(current_pair, ...)  # Always checking real state
    if not allowed:
        return error
    current_pair = apply_X(current_pair)  # Mutating!

# GOOD - checks each against SIMULATED state
simulated = copy(current_pair)
for op in operations:
    allowed, error = can_X(simulated, ...)
    if not allowed:
        return error
    simulated = apply_X(simulated)  # New object each time
# Only now apply to real state
```

---

## Relationship to Other PAIAB Frameworks

- **MCP Development (mcpify):** How to build MCPs in general
- **Harness Emergence (this):** How to convert MCPs into agent harnesses
- **Codenose:** Enforces architecture patterns including harness structure
- **Context Engineering:** How to design system prompts that work with harnesses

---

## Summary

An agent harness is an MCP that shapes LLM behavior through:

1. **Typed models** that constrain possible states
2. **State machines** that define valid sequences
3. **Rejection signals** that steer toward correct actions
4. **Coherence checking** that enables batching

The key insight: rejection messages should STEER, not just BLOCK. The `→` arrow is the probability shaper.
