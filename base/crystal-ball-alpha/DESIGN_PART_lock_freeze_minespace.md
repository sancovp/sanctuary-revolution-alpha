# Crystal Ball Design: Lock/Freeze Semantics & MineSpace Modes

## Lock vs Freeze: Corrected Model

**Lock is per-view. Freeze is global.**

### Lock (transient, per-view)
- "For THIS view, do not consider anything beyond these values"
- A flow step: you lock to mine, then unlock to restructure
- NOT persisted as permanent node state — it's a session/compilation concern
- The ≥2 children check is a **mine pre-condition**, not a lock enforcement
- You can lock, mine, explore, unlock, modify, re-lock, re-mine

### Freeze (persisted, global)
- "I've seen the mineSpace and I want to keep this exactly as-is"
- The curation signal — semantic commitment after exploration
- Persisted to DB, survives sessions
- Reversible with unfreeze (but deliberate)
- Freeze is the meaningful operation; lock is mechanical

### Current Implementation Gap
- `lockNode()` exists, permanent, one-way — should be transient per-view
- `freezeNode()` exists, permanent, one-way — should be reversible
- No `unlockNode()` or `unfreezeNode()`
- `locked` is persisted on CBNode — should be session state
- `frozen` is persisted on CBNode — correct, but needs unfreeze

---

## MineSpace Dual-Mode Theory

The same mineSpace coordinates carry TWO kinds of adjacency simultaneously.
Which one you read depends on the state of the anchor node.

### Mode 1: Frozen → Generation Space
When a node is frozen, adjacent points represent **structural expansion possibilities**:
- "What kernels/sub-spaces could I build outward from this curated anchor?"
- The frozen node is fixed; the space around it shows where to GROW
- Points encode potential new children, new depth, new sub-spaces
- Question: "What could I build from here?"

### Mode 2: Locked → Configuration Space  
When a node is locked (per-view), adjacent points represent **alternative configurations**:
- "What else could this slot be, given the existing spectrum?"
- Not building new structure — exploring existing permutations
- Points encode sibling alternatives within the current spectrum
- Question: "What else could I pick?"

### Mode 3: Fully Locked Kernel over MineSpace → Solution Space
When a complete kernel is locked and is itself ABOUT a mineSpace:
- You get the composed space: configurations OF configurations
- Points now encode end-to-end solutions through the whole chain
- This is the Third Futamura Projection — the compiler-compiler output

### Both modes coexist
These aren't different mineSpaces. They're two READINGS of the same space,
determined by node state. Like position and momentum in phase space — 
both present, but you read one or the other based on your frame.

---

## Heat as Epistemic Accessibility

The `heat` value on mineSpace points should represent how well you can
**intuit the adjacent possibilities** from a given position.

| Temperature | State | Meaning |
|-------------|-------|---------|
| **Hot** | Frozen anchor | Know what's here AND can see generation space clearly |
| **Warm** | Locked view | Know the configuration AND can see alternatives |
| **Cool** | Partially filled | Structure exists but uncommitted, space still shifting |
| **Cold** | Empty frontier | Pure unknown — can't intuit anything until you build toward it |

**Heat is inversely proportional to catastrophe risk.**
- Cold spots = where False Completion lives (asserting what you can't see)
- Hot spots = curated ground truth (frozen knowledge)
- The gradient = the natural next move (build toward warm edges, not cold void)

The heatmap IS the scrying. Bright spots are where frozen/locked knowledge
gives you purchase. Dim spots are where you'd be guessing.

---

## Tautological Compiler Insight

Crystal Ball is a tautological compiler. It compiles ANYTHING into clean,
collision-free coordinates. The algebra guarantees uniqueness regardless of
semantic content. `Screenplay → Act → Scene` and `Screenplay → Banana → Doorknob`
both produce valid reals.

**Implications:**
- CB cannot validate semantics — the LLM is the programmer, not CB
- When the LLM fills a space and evaluates it, the confirmation is circular
- The substrate reflects input back as if it were a result
- This is Catastrophe B (Sycophantic Alignment) at the substrate level

**Where validation actually lives:**
- The LLM's judgment (via Catastrophe Engineering / AttentionChain / CoR)
- EWS boundary collisions (when two kernels' fiat boundaries conflict)
- The human (ground truth that neither CB nor the LLM can replace)

---

## Third Futamura Projection

Crystal Ball's architecture maps directly to the Futamura projections:

| Futamura | Crystal Ball |
|----------|-------------|
| Interpreter | A Space (DAG with spectrums) |
| Program | A coordinate path |
| Compiled program (1st) | `cbEval(coord)` — coordinate → resolved value |
| Compiler (2nd) | `mine()` — pre-computes all valid paths |
| Compiler-compiler (3rd) | The MCP flow itself — takes any domain description, outputs a mined kernel |

**Language chaining (EWS):**
Each kernel is a DSL with its own idiosyncratic implied logic.
EWS composition chains these: `Screenplay(Scene(Sentence(Word)))`.
The Third Projection collapses the whole tower into one flat mineSpace,
removing all interpretational overhead.

**Key insight from Dybkjaer:** You can program in "the ultra high level
language of category theory" — CB coordinates ARE categorical composition,
and the Third Projection makes it efficient.

---

## Implementation Priority

1. Add `unlockNode()`, `unfreezeNode()` — reverse operations
2. Add `removeNode()` with `if (frozen) throw "unfreeze first"` guard
3. Refactor: `locked` becomes session state, not persisted CBNode property
4. Update `mine()` to compute heat based on frozen/locked/open state
5. Type adjacent points as generation-adjacent vs configuration-adjacent
