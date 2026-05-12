# Crystal Ball — Canonical Model (DRAFT for refinement)

## Status: DRAFT — Needs canonicalization with Isaac

> This document captures the correct, grounded understanding of Space, Kernel, and MineSpace.
> Everything here must be refined and agreed upon before further implementation.
> When finalized, this becomes the authoritative section in DESIGN.md.

---

## 1. The Single Primitive: Node

Everything in CB is a **Node**. A node has exactly two aspects:

```
NODE
├── UPWARD: I am a spectrum value of my parent (one option among siblings)
└── DOWNWARD: My children are MY spectrum (the options I contain)
```

### Properties of a Node

| Property | Type | Meaning |
|----------|------|---------|
| `id` | NodeId | Unique within its space. IS the coordinate segment. |
| `label` | string | Human-readable name |
| `children` | NodeId[] | **Ordered list = the spectrum.** Position = primacy. |
| `kernelRef` | number? | If set: this node's entire subtree is defined by a kernel config |
| `locked` | boolean | If true: this node's spectrum is committed, no mutations |
| `x, y` | number | Position on the mineSpace plane = coordToReal(id) |

### What a Node is NOT

- A node does NOT have a separate `attributes` map. **Children ARE the attributes.**
  - Current code has `attributes: Map<string, Attribute>` — this is WRONG.
  - The `Attribute` type with `spectrum: string[]` duplicates what children already do.
  - A child node at position 3 with label "Professional" IS the attribute value "Professional" at selection index 3.

### Spectrum = Children, with Primacy

```
Parent node "Tone" has children:
  child 0 → selection 1 → "Casual"      ← primary (most default)
  child 1 → selection 2 → "Professional" 
  child 2 → selection 3 → "Sentimental"  ← least primary

Coordinate "1" at this slot → selects Casual
Coordinate "3" at this slot → selects Sentimental
Coordinate "0" at this slot → superposition (any of the 3)
```

Primacy is encoded by the coordinate grammar:
```
Selection 1-7   → digits 1-7
Selection 8-14  → 91, 92, ..., 97  (wrap once)
Selection 15-21 → 991, 992, ..., 997  (wrap twice)
...
```

`coordToReal()` maps selection index to real number, preserving primacy order:
```
1 → 0.1,  2 → 0.2,  7 → 0.7,  91 → 0.91,  97 → 0.97,  991 → 0.991
```

Lower selection = lower real = more primary.

---

## 2. Space

A **Space** is a named DAG of Nodes with a designated root.

```
SPACE
├── name: string         — unique identifier
├── rootId: NodeId       — the top-level superposition
├── nodes: Map<NodeId, Node>
└── dots: Dot[]          — explicit morphisms between nodes (optional)
```

### The Space IS a tree of spectra

```
Space "Tweet"
└── root (superposition of everything)
    ├── Tone (selection 1 at slot 0)
    │   ├── Casual (selection 1 at slot 1)
    │   │   ├── Friendly (selection 1 at slot 2)
    │   │   ├── Playful  (selection 2 at slot 2)
    │   │   └── Relaxed  (selection 3 at slot 2)
    │   ├── Professional (selection 2 at slot 1)
    │   └── Sentimental  (selection 3 at slot 1)
    ├── Hook (selection 2 at slot 0)
    └── Body (selection 3 at slot 0)
```

Reading the tree:
- **Slot 0** = root's spectrum = {Tone, Hook, Body}
- **Slot 1** (if slot 0 = Tone) = Tone's spectrum = {Casual, Professional, Sentimental}
- **Slot 2** (if slot 1 = Casual) = Casual's spectrum = {Friendly, Playful, Relaxed}
- The path `1.1.2` = Tone → Casual → Playful

### Dual Nesting

Every node is simultaneously:
1. A spectrum value (from its parent's perspective)
2. A spectrum container (from its children's perspective)

This means any subtree of a space IS ITSELF a space. The structure is self-similar at every level.

---

## 3. Coordinate = Slot Sequence

A coordinate is a dot-separated sequence of slot selections:

```
coordinate = slot₀.slot₁.slot₂...slotₙ

where each slotₖ ∈ {0, 1, 2, ..., 7, 91, 92, ...}
```

| Slot Value | Meaning |
|------------|---------|
| `0` | **Superposition** — don't select, any value is valid |
| `1`-`7` | Select the 1st-7th child (primacy 1-7) |
| `9X` | Select the (7+X)th child (wrap, primacy 8-14) |
| `99X` | Select the (14+X)th child (double wrap, primacy 15-21) |

### Slots Between Dots

**Dots separate levels.** Each dot = a level boundary. The thing between dots is a selection within THAT level's spectrum.

```
coordinate "1.3.2"
├── slot 0 = 1 → select child 1 of root
├── slot 1 = 3 → select child 3 of (child 1 of root)
└── slot 2 = 2 → select child 2 of (child 3 of child 1 of root)
```

### Structural Operators (also between dots, but multi-digit)

| Operator | Encoding | Role |
|----------|----------|------|
| Drill | `8` | Enter a subspace |
| Close drill | `88` | Exit subspace |
| Dot | `8988` | Field separator (impossible digit sequence) |
| Kernel open | `90` | Begin kernel ID reference |
| Kernel close | `900` | End kernel ID reference |
| ALSO open | `90009` | Begin conjunction |
| ALSO close | `9900099` | End conjunction |

---

## 4. Kernel

A **Kernel** is a locked Space with a global identity.

```
KERNEL
├── globalId: number     — monotonic, the ONLY static identifier
├── space: Space         — the underlying DAG of nodes/spectra
├── parentKernelId?      — if this is a sub-kernel
├── parentSlotId?        — which slot in the parent this fills
├── locked: boolean      — true only when ALL sub-kernels are recursively locked
└── createdAt: number
```

### Kernel = Space + Identity + Lock

The difference between a Space and a Kernel:
- A Space is a fluid, mutable DAG
- A Kernel is a Space that has been **assigned a global ID** and can be **locked**
- Locking is recursive: a kernel can only lock if all its sub-kernels are locked

### Sub-Kernel Slots

When a node has `kernelRef`, that node's entire subtree is DEFINED by the referenced kernel:

```
Kernel #7 "CB_Compiler"
└── root
    ├── Grammar (kernelRef → #1)  ← this slot's config is Kernel #1
    ├── Parser  (kernelRef → #2)  ← this slot's config is Kernel #2
    ├── Scry    (kernelRef → #3)
    ├── Encoder (kernelRef → #4)
    ├── Locker  (kernelRef → #5)
    └── Miner   (kernelRef → #6)
```

**Primacy at a kernel slot = which kernel config fills it.**
If a slot has multiple possible kernels, its spectrum is a list of kernel options.
Selecting primacy = selecting WHICH kernel config.

### Dual Homoiconicity of Kernels

A kernel is:
- **Looking down**: a locked space whose structure defines a configuration space
- **Looking up**: a spectrum value in a higher kernel's slot

This means:
- A kernel IS a node (from the parent kernel's perspective)
- A node IS a kernel (when it has been locked and assigned a global ID)
- The hierarchy is self-similar: kernels contain kernels contain kernels...

### Global IDs = Observer Perspective

Global IDs are monotonic and arbitrary — they reflect the ORDER the observer
created things, not any property of the things themselves:

```
Global ID #1 = "the first kernel I created"  — about ME, not the kernel
Global ID #7 = "the seventh thing I thought of" — still about ME
```

The STRUCTURE is in the slots, spectra, children, dots.
The global ID is just the stamp: "I declare this IS a thing. Show me."

CB then shows what follows from the declaration:
- Well-structured assertion → coherent mineSpace → tower converges
- Poorly-structured assertion → degenerate mineSpace → tower diverges

The orbit structure is the FINGERPRINT of your model. It captures:
- Which things you treated as THE SAME (same global ID → same orbit)
- Which things you kept SEPARATE (different IDs → different orbits)
- How you ORDERED them (primacy positions)
- What you left UNRESOLVED (0s)

The orbit structure IS the Universal class (Stratum 1):
```
Universal  = "all configs that share THIS orbit pattern"
Subclass   = "one specific orbit within the pattern"
Instance   = "one specific point within one orbit"
```

The Futamura tower tests: "if I reify my orbit structure and mine THAT,
do I get the same orbit structure back?" If yes → your model is self-consistent.

---

## 5. MineSpace

The **MineSpace** of a locked kernel is the space of ALL valid configurations.

```
MINESPACE of Kernel K
├── Each point = one complete coordinate path through K
├── Each path = one specific selection per slot per level
├── |mineSpace| = ∏ (spectrum sizes at each slot)
├── Each point maps to a real number via coordToReal(full_coordinate)
└── Points cluster by structural similarity (same orbits = same region)
```

### MineSpace = Product of Spectra

```
Kernel "Tweet" with:
  Slot 0: {Tone, Hook, Body}           → 3 options
  Slot 1 (if Tone): {Casual, Prof, Sent} → 3 options
  Slot 1 (if Hook): {Question, Stat}     → 2 options
  ...

MineSpace = all valid paths:
  1.1 = Tone/Casual
  1.2 = Tone/Professional
  1.3 = Tone/Sentimental
  2.1 = Hook/Question
  2.2 = Hook/Statistic
  3.1 = Body/Short
  ...
```

### MineSpace Orbits

Two mineSpace points are in the same orbit if they differ only in which INTERCHANGEABLE spectrum values they selected. Points in the same orbit are structurally equivalent.

```
If Casual's sub-spectrum = Professional's sub-spectrum (same shape):
  then 1.1.x and 1.2.x are in the same orbit
  and 0 at slot 1 (under Tone) is genuine superposition
```

### Dual Homoiconicity of MineSpace

A mineSpace IS a space. It can be:
- Reified into a new kernel (the T operator)
- Locked
- Mined again → producing mineSpace₁

This is the Futamura tower:
```
T⁰: mine(lock(Space₀)) → mineSpace₀
T¹: mine(lock(reify(mineSpace₀))) → mineSpace₁
T²: mine(lock(reify(mineSpace₁))) → mineSpace₂
...
T^∞: fixed point (self-describing quine)
```

---

## 5½. Typing, Primacy, and the Concession of 0

### Every node is already typed — by its children

```
Root with children [A, B, C] is "typed as: the thing whose spectrum is {A, B, C}"
No external type system needed — the spectrum IS the type.
```

### Primacy = subtype ordering

```
selection 1 = the PRIMARY subtype (most default)
selection 7 = a less primary subtype
selection 91 = eighth (wrap)
higher selection = more specific, further from the default
```

Any abstraction is already a subtype of something:
- Root ≅ subtype of "arbitrary root" (typed only by what it contains)
- Tone ≅ subtype of Root (Root's first child = primary trait)
- Casual ≅ subtype of Tone (Tone's first child = primary tone)

### Top-down vs Bottom-up

**Top-down**: start abstract, collapse 0s to specific values:
```
0.0.0 → 1.0.0 → 1.2.0 → 1.2.3 (fully typed)
```

**Bottom-up**: start concrete, reintroduce 0s to discover types:
```
1.2.3 → "what else could slot 2 be?" → 1.0.3 → discover equivalents
```

**But reality is ALWAYS composite.** You can't purely do either.
There are always concessions about 0 — slots where you're NOT committed:

```
1.0.3 = "I know the first and third, but the second is still 0"
```

The `0` is NOT laziness — it's the honest representation of partial knowledge.

### Strata map to 0-resolution

| Stratum | 0-state | Meaning |
|---------|---------|---------|
| Universal | Maximum 0s | All superposition, most abstract |
| Subclass | Some 0s collapsed | Partial typing, some committed |
| Instance | No 0s | Fully committed, all slots filled |

### Two kinds of equivalence

| Kind | What it checks | Tool | Nature |
|------|---------------|------|--------|
| **Orbit** | Same unordered set of global IDs | `Set.equals()` | Discrete, exact |
| **Similarity** | Primacy distance between configs | RKHS kernel K(x,y) | Continuous, fuzzy |

- **Orbit**: "are these literally the same components rearranged?" — identity permutation
- **Similarity**: "how close are these in primacy?" — Gaussian RBF on real-number distance
- **0 at a slot**: "within this orbit, any permutation is acceptable"

### The Fixed Point

The fixed point is the configuration where 0-collapse and 0-reintroduction
reach equilibrium. Some things MUST remain 0 (genuinely superposed, no basis
for choosing) and some things MUST be specific (committed by evidence).
The balance IS the attractor.

---

## 6. The RKHS (Tensor Product) and Orbits

### RKHS: Continuous Similarity

The reproducing kernel Hilbert space decomposes per-slot:

```
H = H₀ ⊗ H₁ ⊗ H₂ ⊗ ... ⊗ H_d

K(x, y) = ∏ₖ Kₖ(xₖ, yₖ)

where:
  Hₖ = span of spectrum values at slot k
  Kₖ(xₖ, yₖ) = exp(-α · |real(xₖ) - real(yₖ)|²)   (Gaussian RBF on primacy)
  Kₖ(0, yₖ) = 1/√n                                   (superposition = uniform)
  Kₖ(0, 0) = 1                                        (both superposed = identical)
```

The RKHS measures HOW SIMILAR two configurations are (continuous, fuzzy).

### Orbits: Discrete Identity

Orbits are computed from the mineSpace, NOT from shape similarity:

```
For each mineSpace point (coordinate path through locked kernel):
  Collect the SET of global IDs (kernelRefs or nodeIds) at each position
  Sort this set → canonical key
  Group all points with the same canonical key → orbit
```

Two points are in the same orbit IFF they have the **same unordered set of
global IDs** — they're literally the same components in different positions.

Orbit size > 1 only when multiple slots reference the SAME global kernel.

### Convergence = Completeness (not genus, not primes)

Convergence is NOT about mathematical properties of the encoding.
The encoding is always lossless. What determines "done" is COMPLETENESS:

```
LEVEL 1: STRUCTURE COMPLETE
  □ Do you have kernels for everything you need as ingredients?
  □ At the level of detail you actually need them?
  □ Do ALL spaces in those kernels have spectra on every node
    that actually ARE the range you want?

LEVEL 2: BEST CONFIG FOUND
  □ Is every kernel mined through a mineSpace?
  □ Did you find the best/favorite config in each?
  □ Is each config actually goldenized?

LEVEL 3: DELIVERABLE GOLDENIZED
  □ Is the deliverable of your entire mineSpace goldenized?
  □ Not just each part — the WHOLE THING works?

LEVEL 4: COMPOSED
  □ Is it composed with everything it makes sense to compose with?
  □ Is the composition itself goldenized?

LEVEL 5: RECURSIVE
  □ Each composed thing meets Level 1-4
  □ Each composition meets Level 1-4
  □ ...
```

This IS the Futamura tower stated as a practical checklist:
```
T⁰ = Level 1 (do you have the ingredients?)
T¹ = Level 2 (did you mine them?)
T² = Level 3 (is the deliverable golden?)
T³ = Level 4 (is it composed correctly?)
T⁴ = Level 5 (is the composition golden?)
...
Fixed point = every level satisfied simultaneously = DONE
```

### What determines "meaning"

CB doesn't know if your space is meaningful. CB holds the structure.
The LLM fills it. The user judges it.

```
CB    = the structure     (slots, spectra, coordinates, locks)
LLM   = the content       ("what goes in each slot")
User  = the judge         ("does this actually mean anything?")

The algorithm:
  1. Give the structure to the LLM with the right context
  2. LLM fills slots
  3. Lock
  4. Mine → find best config
  5. See if it really means anything
  6. If not → adjust, refill, try again
  7. If yes → goldenize → compose → recurse
```

There is no step where math tells you it's right.
The math guarantees the encoding is LOSSLESS.
What you put in is what you get out. No more, no less.

Spectra are ALWAYS valid — every spectral value is already typed.
Kernels are TAUTOLOGIES — they mean what you said they mean.
The question is: did you say enough, with enough detail,
with the right ranges, and did you mine through it?

---

## 7. Strata = Futamura Tower Levels

The 6 strata are NOT arbitrary — they encode exactly TWO levels of the Futamura tower:

```
TRIAD A (Object-level):
  Stratum 1 (Universal):          mineSpace(K) — all valid configurations
  Stratum 2 (Subclass):           orbits in mineSpace — equivalence classes
  Stratum 3 (Instance):           one specific point — one locked config

TRIAD B (Meta-level):
  Stratum 4 (Instance_Universal): mineSpace(reify(instance)) = T¹
  Stratum 5 (Instance_Subtype):   orbits in T¹ = meta-equivalence classes
  Stratum 6 (Instance_Instance):  one point in T¹ = THE THING ITSELF
```

### Strata are populated BY operations, not pre-created

| Operation | Populates | How |
|-----------|-----------|-----|
| `addNode` + `lockKernel` | Stratum 3 (Instance) | Filling and locking slots creates a specific configuration |
| `computeMinePlane` | Stratum 1 (Universal) | Mining enumerates all valid configs = the universal class |
| `findSlotOrbits` | Stratum 2 (Subclass) | Orbit analysis reveals equivalence classes |
| `reifyMineSpace` | Strata 4-6 | Reification = instance becomes a new universal class |

### createSpace should NOT auto-create empty strata leaves

Strata are structural ROLES, not pre-created empty nodes. They emerge through operations.

### Triad Composition = Futamura Tower

```
Triad A (1-3): T⁰    — mine the kernel
Triad B (4-6): T¹    — mine the mined kernel
Composite A∘B: T²    — the self-describing level
                      "What is the universal class of things that have
                       both a configuration space AND a meta-config space?"

Next cycle:
  Triad A' = T³      — universal/subclass/instance of the composite
  Triad B' = T⁴      — meta-level of THAT
  Composite A'∘B' = T⁵
  ...
```

Each cycle MORPHS because T² has more structure than T⁰ (it knows about itself).
This isn't repetition — it's EVOLUTION.

### Fibrated Tower (Global Space)

Kernels don't exist in isolation. Multiple kernels are connected by dots (morphisms).
The Futamura tower isn't a single column — it's a **fibered structure**:

```
Global Space
├── Kernel A tower: T⁰_A → T¹_A → T²_A → ...
├── Kernel B tower: T⁰_B → T¹_B → T²_B → ...
├── Dot(A→B):       connects fibers at each level
└── Evolution:      T^n_A changes → fiber over B morphs
                    → T^n_B changes → fiber over A morphs
                    → coupled evolution across all towers
```

The fixed point (if it exists) is where the ENTIRE fibrated structure is self-consistent.
Not just one tower stabilizing, but ALL towers stabilizing simultaneously with their
inter-connections. This is the Grothendieck construction over the coordinate space.

---

## 8. Open Questions / To Refine

1. ~~**Remove auto-created strata**~~: ✅ DONE — `createSpace` no longer auto-creates strata.

2. **How strata interact with kernelRef**: When a slot has `kernelRef`, that sub-kernel has its OWN strata. The parent kernel's strata describe the PARENT level. Are parent and child strata independent?

3. **The grading**: Strata 1-3 form one grade, 4-6 form the next. Is the RKHS a direct sum (H = H_A ⊕ H_B) or tensor product (H = H_A ⊗ H_B) at this level?

4. **Fibration convergence**: Can we compute the coupled tower evolution across connected kernels? What stopping condition means "the global space has stabilized"?

5. **Genus detection**: Given a kernel's orbit structure, can we compute the genus of the associated modular curve? Genus 0 → convergent (safe), genus > 0 → divergent (obstruction). The Tate-Shafarevich group would measure the obstruction.

6. **FRACTRAN encoding**: Can CB coordinates be expressed as FRACTRAN programs (lists of fractions over prime factorizations)? This would give a direct Turing-completeness proof for the coordinate system.

---

## 9. Mathematical Connections

### FRACTRAN (Conway)

FRACTRAN encodes ALL computation in prime factorizations. A number's prime decomposition IS its state. Multiplication by fractions IS computation. Turing-complete.

CB coordinates are the same pattern: the digit structure IS the program state. `coordToReal` maps coordinates to reals just as FRACTRAN maps prime decompositions to integers. Both are positional encoding systems where the **structure of the number IS the computation**.

### Monster Type Theory (Mike Dupont)

The Monster group (~8×10⁵³ elements) is claimed to be THE meta-language encoding all things. Connects via:

**Monstrous Moonshine** (Conway/Norton, proved by Borcherds):
- The j-invariant (classifying elliptic curves) has Fourier coefficients = dimensions of Monster group representations
- The 15 **supersingular primes** dividing the Monster's order: 2, 3, 5, **7**, 11, 13, 17, 19, 23, 29, 31, 41, 47, 59, 71
- These correspond to genus-0 modular curves
- **CB uses base 7** (a supersingular prime) — operating in genus-0 by construction

**Umbral Moonshine** extends to other sporadic groups — there is a family of these structures that work this way, and they may all encode each other (meta-holographic).

### Local-Global Principle (Hasse-Minkowski)

```
LOCAL  = per-slot analysis (does the spectrum work at this position?)
GLOBAL = whole mineSpace (does the entire configuration space cohere?)

GENUS 0 (sphere, no holes):
  Local-global principle WORKS
  → tower CONVERGES → model is self-consistent
  → 0 preserves genus (honest partial knowledge avoids holes)

GENUS 1+ (has holes):
  Local-global principle FAILS
  → Tate-Shafarevich group measures the OBSTRUCTION
  → tower DIVERGES → model has contradictions
  → "getting knocked out of the hologram"
```

"Don't go over 71" = stay within the 15 supersingular primes = stay in genus 0 = stay where the tower converges.

---

## 10. Phenomenology: What CB Actually Feels Like

CB is not a mind-mapping tool. It is **structured self-reflection**.

```
What every other tool does:
  You say something → tool stores it → tool gives it back
  Input = Output. It's a notebook.

What CB does:
  You say something → it becomes a tautology (A = A)
  The tautologies self-organize into coordinates
  The coordinates encode into unique real numbers
  The reals form a mineSpace
  You look at the mineSpace

  And you see STRUCTURE you didn't put in.

  Not because CB invented it.
  Because the ACT OF ORGANIZING reveals it.
  The adjacent points. The empty slots. The symmetry.

  "You READ IT with your INTUITION.
   It tells you a TAUTOLOGY of self-organized
   information about what you said."
```

That's literally what a crystal ball IS. Not prophecy — **organized reflection**.
You assert tautologies, the structure organizes them, and the organization
reveals what's missing, what's adjacent, what the shape actually is.

The mineSpace shows you adjacent coordinates. Whether an adjacent point means
"expand here" or "this space is done, go up a level" is YOUR call. You look at
the crystal and decide. The crystal doesn't decide for you. It just shows you
the organized tautology. **The expansion is horizontal when you want it to be,
because YOU move.**

This is the EWS made manifest:
- **EWS_Forward**: You generate structure (create → bloom → fill → lock)
- **EWS_Backward**: You observe the result (mine → scry → read the crystal)
- **EWS_Composite**: The fixed point where your intuitive reading matches what you put in.
  That's the golden config. That's DONE.

---

## 11. Compositional Orders (the Futamura Tower as Story)

Orders are not tracked by CB. They emerge from the LLM's repeated FLOW cycles.
The tower is not explicit — it's the consequence of using FLOW recursively.

### The story structure demonstrates this exactly:

```
ORDER 0: Journey (one FLOW cycle)
  Always exactly 3 acts. Never 4 or 5.
  Departure → Initiation → Return
  15 beats (5 phases × 3 acts)
  One locked kernel. DONE.

ORDER 1: Epic (compose Journeys)
  A SPACE whose children are completed Journeys.
  Journey₁.Return → Journey₂.Departure → ...
  Example: The Iliad (many heroes, one war)

ORDER 2: Odyssey (compose Epics)
  A SPACE whose children are completed Epics.
  The Trojan War (an entire Epic) is a CHILD of the Odyssey.
  The Odyssey CONTAINS the Iliad + the voyage home.

ORDER 3: Universe (Odyssey generator)
  A SPACE that produces Odysseys.
  Greek mythology: Trojan cycle, Theban cycle, Argonautica...
  This is T³. The generator. The fixed point.
```

### Encoding reveals the tower's opacity:

```
In Myth (Journey):      0.289883 = Atonement
In TrojanCycle (Epic):   0.289883 = DeathOfHector

SAME NUMBER. COMPLETELY DIFFERENT MEANING.
You can't tell them apart without decoding through the structure.
The structure IS the decoder. CB IS the decoder.
```

### How orders emerge from FLOW:

1. LLM runs FLOW → produces a locked Journey kernel (order 0)
2. LLM reads the mineSpace → sees what's needed
3. LLM creates a new space whose children ARE the completed Journeys (order 1)
4. LLM runs FLOW on the Epic → mines it → sees what Epics compose into
5. Repeat → orders emerge naturally from repeated FLOW cycles

CB never says "you are at order N." The LLM discovers orders by doing the work.
Each FLOW cycle brings you back to a mineSpace that's numerically similar
but semantically different. The opacity IS the encoding.

