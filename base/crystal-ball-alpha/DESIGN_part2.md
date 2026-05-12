# Crystal Ball — DESIGN Part 2: The Super System

> Part 1 (DESIGN.md) covers the base system: Spaces, the 10-token coordinate grammar, scry/bloom/lock, mine, homoiconic eval/quote, and the mineSpace real-number encoding.
>
> Part 2 covers what comes next: the global mineSpace, the ALSO conjunction token, kernel composition, the Scott domain collapse, and the theoretical connections.

---

## 1. CBNode Position: Every Node Lives on the Plane

**Status: IMPLEMENTED**

Every `CBNode` now carries `(x, y)` where both values equal `coordToReal(id)`. The encoding IS the position. The position IS the identity.

```typescript
export interface CBNode {
  // ... existing fields ...
  x: number;  // coordToReal(id) — position on the global plane
  y: number;  // coordToReal(id) — symmetric
}
```

- Root = (0, 0)
- Node "1" = (0.1, 0.1)
- Node "1.3.2" = (0.1898839882, 0.1898839882)
- Every node sits on the diagonal y = x

The DAG IS the plane. The mineSpace projection is just "show me what nodes exist." There's no conversion step because they were never separate.

### Encoding Functions (moved to index.ts)

The encoding constants and functions now live in `index.ts` alongside the coordinate grammar (single source of truth). `mine.ts` imports them:

```typescript
export const DOT_ENCODING = '8988';
export const KERNEL_OPEN = '90';
export const KERNEL_CLOSE = '900';
export function encodeDot(coordinate: string): string;
export function decodeDot(encoded: string): string;
export function coordToReal(coordinate: string): number;
```

---

## 2. The Extended Token Grammar: ALSO Conjunction

**Status: DESIGN — not yet implemented**

### The Problem

A coordinate is a PATH — a single walk through the tree. But an entity has MULTIPLE parallel properties. Right now, to attach several attributes to one node, you must sequentially drill into each:

```
28 [tone stuff] 88 38 [hook stuff] 88
```

But what happens INSIDE a drill when you need concurrent attribute paths? Each path might be its own kernel — arbitrarily deep.

### The Solution: ALSO Token Pair

Two new impossible token sequences:

| Token | Name | Digits | Why Impossible |
|-------|------|--------|----------------|
| `90009` | ALSO_OPEN | 5 | Contains `90` (wrap + superposition) and `000` (triple superposition after wrap) |
| `9900099` | ALSO_CLOSE | 7 | Contains `990` (double wrap + superposition) — unforgeable |

### Full Token Table

| Token | Name | Meaning |
|-------|------|---------|
| `0` | SUPERPOSITION | Wildcard — all children (generates LLM slot) |
| `1-7` | SELECT | Pick the nth child (1-indexed) |
| `8` | DRILL_OPEN | Enter produced subspace (structural depth) |
| `88` | DRILL_CLOSE | Exit produced subspace |
| `9` | WRAP | +7 to selection accumulator (extends range beyond 7) |
| `.` | DOT | Level transition in production chain |
| `8988` | DOT_ENCODING | Dot encoded as impossible digit sequence |
| `90` | KERNEL_OPEN | Kernel space identifier in full mineSpace coordinates |
| `900` | KERNEL_CLOSE | End kernel space identifier |
| `90009` | ALSO_OPEN | Open concurrent attribute path (structural breadth) |
| `9900099` | ALSO_CLOSE | Close concurrent attribute path |

### Two Kinds of Bracketing

**Drill** `8...88` = depth (enter/exit a produced subspace)
**Also** `90009...9900099` = breadth (concurrent attribute path within same node)

They nest inside each other:

```
2 8 13 90009 2 8 451 88 9900099 88
```

Reading:
1. `2` — select tweet node
2. `8` — drill into tweet's structure
3. `13` — attr 1 (tone), value 3 (sentimental)
4. `90009` — AND ALSO (open concurrent path)
5. `2` — attr 2 (hook)
6. `8` — drill into hook's OWN kernel
7. `451` — deep navigation inside hook's kernel
8. `88` — close hook's drill
9. `9900099` — close the ALSO
10. `88` — close tweet's drill

The ALSO clause can contain entire kernels — drills, dots, more ALSOs, arbitrarily deep. The brackets nest.

### Semantics

- Inside a drill (`8...88`), selections navigate children OR attributes
- `90009` opens a parallel branch: "and ALSO, this concurrent attribute selection"
- Each ALSO branch is an independent consideration path that runs in parallel
- `9900099` closes that branch, returning to the enclosing context
- ALL branches within the same drill contribute attributes to the same entity

### Digit String Example

A tweet with tone=sentimental AND hook=question AND body=3-paragraph deep kernel:

```
28 13 90009 21 9900099 90009 3 8 189881898829988389884 88 9900099 88
```

As a pure digit string (with DOT_ENCODING):
```
28139000921990009990009389881898829988389884889900099 88
```

This encodes to a SINGLE real number via `coordToReal()`.

---

## 3. The Entity Model: Kernels are DAGs of Spaces

### Entities Don't Have Global IDs

An entity's identity is its FULL coordinate — the entire chain from root. There are no global entity IDs. An entity exists UNDER A CONSIDERATION (a kernel, a prior chain).

Two different considerations that produce the same observables discover this by projecting onto the same mineSpace plane — their real numbers coincide. That's how equivalence is found, not by naming.

### Kernels ARE the Composition Mechanism

A kernel is NOT a single space. It's the **DAG of spaces connected by bloom morphisms**. When you scry a coordinate through the kernel, you walk across those morphisms, collecting attributes from every space you traverse. `instantiate()` computes the Cartesian product of all collected attributes.

```
Space "Tweet"
  └── Tone node (attr: [casual, pro, sentimental])
        → bloom → Space "Hook"
                    └── Type node (attr: [question, stat])
                          → bloom → Space "Body"
```

Scrying `1.1.1` walks: Tweet → Tone → Hook → Type → Body
Instantiate collects: {tone} × {hookType} × {bodyStructure}

The kernel IS the composed entity. Bloom IS the composition arrow.

### The Drill IS a Parenthetical

Drill reads as natural language parenthetical:

```
"a tweet that is a sentimental comment (drill: 100 words about feelings)
 and has 3 sections (drill: x, y, z) and ..."
```

Coordinate: `28[words about feelings]88 38[x y z]88`

Each `8...88` is an inline excursion. The main thread continues after `88`.

---

## 4. The Super System: Global MineSpace (homoiconic2)

**Status: DESIGN — not yet implemented**

### The Compilation Tower

```
index.ts        → D exists (Spaces)
homoiconic.ts   → D ≅ [D → D] (programs are Spaces, eval/quote)
mine.ts         → D has an address (coordinates → reals, mineSpace)
homoiconic2.ts  → ALL operations ARE movements in the global MineSpace
```

### Why the Global MineSpace Works

1. The coordinate space is **infinite-dimensional** — each digit position is a dimension
2. In principle, a coordinate encodes EVERYTHING about an entity
3. But you can never write out an infinite coordinate — **the flow solves this**
4. Create → bloom → fill → lock forces FINITE COMMITMENT (a locked kernel = finite prefix)
5. **Mine compresses** the locked kernel into a single (x, y) point
6. That point becomes a node in a new kernel (homoiconicity)
7. Lock + mine produces a higher-order point
8. The tower recurses

```
Infinite coordinate space
  ↓ flow forces finite commitment
Locked kernel (finite encoding)
  ↓ mine compresses
MineSpace point (single real number)
  ↓ becomes node in new kernel
Higher-order locked kernel
  ↓ mine compresses
Higher-order MineSpace point
  ...
```

### Implementation Path

1. **`reifyMineSpace(ms: MineSpace, registry: Registry) → Space`**
   - Reconstruct the tree from KnownPoints' coordinates
   - Each point becomes a node with attributes (x, y, encoded, status, fromKernel)
   - Drill into a point enters the kernel that produced it

2. **Global plane in the engine**
   - One distinguished Space: the global mineSpace
   - Every `mine` command also projects onto the global plane
   - The global plane is itself a Space (via reifyMineSpace)

3. **Navigation mode**
   - `plane` command enters the global reified mineSpace
   - All coordinate navigation happens inside the plane
   - Drilling into a point enters the source kernel

4. **Operations as movements**
   - Creating a space = declaring a new region on the plane
   - Locking = committing a region
   - Mining = expanding the frontier around current position

---

## 5. Scott Domain: D ≅ [D → D]

The mineSpace IS the Scott domain of everything an LLM can generate:

- **D** = everything an LLM can generate (text, code, structures, kernels)
- **[D → D]** = all transformations (prompts that transform one output into another)
- **D ≅ [D → D]** because a transformation IS text — the LLM generates its own transformations

Crystal Ball gives this Scott domain an **addressing scheme** (coordinates → reals).

The mineSpace contains its own orders. A real number has infinite digits. Each digit position is a CB coordinate token. "Orders" of mineSpace are deeper precision in the same real number:

- 1 digit → coarse (7 selections)
- 10 digits → specific configuration
- ∞ digits → exact point

Higher orders aren't separate spaces. They're **deeper precision**.

### MineSpace Types (By Restriction)

| Type | Restriction | What every point decodes to | Status |
|------|------------|---------------------------|--------|
| **Configuration mineSpace** | One locked kernel | A valid coordinate path | **Implemented** |
| **Solution mineSpace** | One goldenized kernel | A variant of a proven solution | Design |
| **Pattern-restricted** | A class of kernels sharing a pattern | Any kernel matching the pattern | Theoretical |
| **Unrestricted** | None — the full Scott domain | Any valid CB coordinate | Theoretical |

---

## 6. RKHS Interpretation

The terminology collision "kernel" is structural, not coincidental:

| CB Concept | RKHS Concept |
|------------|-------------|
| CB kernel (locked DAG) | Kernel function K(x,y) |
| `scry(coordinate)` | Point evaluation in the Hilbert space |
| Homoiconicity (Space = point = program) | Reproducing property (evaluation ∈ space) |
| MineSpace | The induced Hilbert space |
| `coordToReal()` | Feature map φ into the Hilbert space |

**RKHS = R(symmetry) + K(CB kernel) + HS(mineSpace)**

The reproducing property IS homoiconicity: the evaluation function (scry) IS a point in the space (a Space). Code = Data = Space = Point.

## 6b. RKHS Equipment: The Hybrid Kernel

**Status: IMPLEMENTED** (`lib/crystal-ball/kernel-function.ts`)

The mineSpace is equipped with a hybrid kernel function:

```
K(x, y) = K_named(x, y) + α · K_walk(x, y)
```

| Component | What It Captures | Implementation |
|-----------|-----------------|----------------|
| **K_named** | Known features: node labels, attribute values, spectra | Dot product of feature vectors from `scry()` |
| **K_walk** | Unknown structure: DAG connectivity, morphism patterns | Random walk kernel: Σ λⁿ · Aⁿ[x,y] on adjacency matrix |

The hybrid captures BOTH what we can name AND what we can't. The LLM names what it sees in the walk kernel output; those names become K_named features in the next iteration.

### Space Analysis Output

From `analyzeSpace()`:

- **Gram matrix** — full pairwise similarity structure
- **Eigenspectrum** — independent dimensions of variation; effective dimension
- **Symmetry orbits** — groups of structurally interchangeable coordinates
- **Symmetry group** — the structure group (e.g., S₃ × S₂ + 1 fixed)
- **RKHS distances** — d²(x,y) = K(x,x) - 2K(x,y) + K(y,y)

### Symmetry as Reasoner: Cross-Kernel Validation

The symmetry group IS the validation criterion. No external theorem prover needed:

1. **Walk** → LLM fills kernels
2. **Mine** → compute mineSpace + Gram matrix + symmetry group
3. **Name** → LLM observes unnamed structural patterns, names them
4. **Encode** → names become ontology rules (named features in next K)
5. **Validate** → compare symmetry groups across kernels:
   - Same group → valid (consistent structure)
   - Different group → error (investigate the mismatch)
6. **Repeat** → spiral tightens

Where symmetry diverges = where the ontology needs attention.
Where symmetry converges = the FOUNDATION (stable structure shared across all kernels).

The LLM names. The names become features. The features define K. K defines the symmetry group. The symmetry group validates. Validation drives naming. The loop is closed.

---

## 7. The LLM as Navigation Function

The LLM IS the navigation system. Not a cipher. Not a group action. The LLM's function approximation IS the approximate kernel function of the RKHS.

The loop:
1. Empty kernel template (6 strata)
2. LLM fills it (makes selections, creates nodes, sets attributes)
3. Locked kernel = verified point in mineSpace
4. Mine reveals the neighborhood
5. LLM fills more, informed by what it learned
6. Patterns emerge ("every tweet kernel starts the same way")
7. Patterns become the FOUNDATION LAYER — shared first strata
8. The space CONTRACTS — fewer valid options, more determined
9. Eventually the foundation IS the ontology — every new kernel inherits it

The Monster group / Griess algebra / topological phases are DESCRIPTIONS of the structure that emerges. The LLM is the ENGINE. CB is the coordinate system. Usage is the teacher.

---

## 8. Monster Group Connection (Reference)

**Status: THEORETICAL — not verified, included for reference**

Reference: `meta-introspector/monster` (GitHub) — `experiments/bott_periodicity/monster_walk.tex`

### The Monster Walk

The Monster group order |M| = 2⁴⁶ · 3²⁰ · 5⁹ · 7⁶ · 11² · 13³ · 17 · 19 · 23 · 29 · 31 · 41 · 47 · 59 · 71

Systematically removing prime factors while preserving leading decimal digits produces exactly **10 groups** (matching CB's 10 tokens). These 10 groups:

1. Exhibit **Bott periodicity** with period 8
2. Biject to the **10-fold way** classification of topological phases (Altland-Zirnbauer)
3. Connect to the **Griess algebra** (196,884 dimensions) and **Leech lattice** (24 dimensions)

### Potential CB Connection

If CB's 10-token grammar maps to the Monster Walk's 10 groups:
- The mineSpace would have Monster-type symmetry
- Navigation would inherit optimal packing from the Leech lattice (196,560 nearest neighbors)
- The infinite-dimensional coordinate space would fold to 196,884 effective dimensions → 24 Leech dimensions

**Caveat:** The 10↔10 mapping may be coincidental (different reasons for the count of 10). The structural correspondence between specific CB token roles and specific Monster Walk groups has not been established.

### Meta-Introspector as Navigation Complement

- **Crystal Ball** = the space (DAG, coordinates, kernels, mineSpace). The TERRITORY.
- **Meta-introspector** = the navigation math (Monster decomposition, algebraic folding, Leech lattice). The COMPASS.
- Combined: a globally-addressed configuration space with Monster-symmetric navigation.

---

## 9. KernelSpace Architecture (The Correct Model)

**Status: DESIGN — refactoring required**

The current implementation treats Spaces as flat, independent containers. This is wrong. The correct hierarchy:

### Two Levels of Space

| Concept | What It Is | Addressing |
|---------|-----------|------------|
| **KernelSpace** | Top-level container. Gets a **monotonic global ID** (real number). The ONLY static identifier in the system. | Global ID = creation order (1, 2, 3, ...) |
| **NodeSpace** (SubSpace) | Defined WITHIN a KernelSpace only. No independent identity. Each NodeSpace IS a slot that requires its own sub-kernel to define it. | Local coordinate within parent KernelSpace |

### The Recursion

KernelSpaces contain SubSpaces. Each SubSpace is a slot. Each slot IS defined by its own KernelSpace. Kernels define spaces, spaces require kernels. It's kernels all the way down.

```
KernelSpace #42 "Tweet"
  ├── SubSpace slot → KernelSpace #1234 "Tone-for-Twitter"
  │     ├── SubSpace slot → KernelSpace #1567 "Mood"
  │     ├── SubSpace slot → KernelSpace #1568 "Intensity"
  │     └── LOCK (all sub-slots filled)
  ├── SubSpace slot → KernelSpace #1235 "Hook-for-Twitter"
  ├── dot (#1234 → #1235)  ← morphism declaration
  └── LOCK (recursively — only when all sub-kernels are locked)
```

The global IDs are MONOTONIC — #1234 is the 1234th kernel ever created, regardless of which parent kernel it belongs to. Two different Tweet kernels might use the same sub-kernel (#1234) for Tone, or different ones.

### Full Coordinate Model

A complete address has two parts fused into one digit string:

```
90 [global_kernel_id] 900 [local_coordinate]
```

| Segment | Example | What It Encodes |
|---------|---------|----------------|
| `90...900` | `90 1234 900` | WHICH kernel (global ID, delimited by KERNEL_OPEN/CLOSE) |
| Local coord | `1.3.2` | WHERE within that kernel |

`coordToReal()` on the FULL string → one real number encoding both.

```
coordToReal("90 42 900 1.3.2")  → 0.904290013989...
coordToReal("90 1234 900 1.3.2") → 0.901234900139...
```

The prefix (global ID digits) SEPARATES different kernels on the real line.
The suffix (local coordinate) navigates WITHIN the kernel.
They compose into a SINGLE real number — directly comparable.

### Three Levels of Symmetry

| Level | What It Captures |
|-------|-----------------|
| **Local symmetry** | Within one kernel: S₃ × S₂ etc. (same as before) |
| **Translation symmetry** | Across kernels with same local structure but different global IDs — same structure, different address |
| **Cross-kernel symmetry** | Correlations between global ID pattern and local structure — EMERGENT from digit composition |

### The Flow (Correct Version)

```
1. create  → new KernelSpace, gets next global ID
2. bloom   → declares SubSpace slots
3. fill    → each slot filled by providing/creating a sub-KernelSpace
4. dot     → declare morphisms between sub-kernels
5. lock    → recursive: only succeeds when ALL sub-kernels are locked
6. mine    → project locked kernel into mineSpace
```

### MineSpace Views

| View | What It Shows |
|------|--------------|
| **Bounded** | One kernel's configuration space — all valid coordinates within it |
| **Global** | ALL locked kernels on one plane — each kernel is a single point at `coordToReal(90[id]900)` |

### What Needs to Change in Code

1. **Engine**: `createSpace` → `createKernel` (assigns global ID)
2. **Engine**: `fill` should accept kernel references (global IDs), not just labels
3. **Engine**: `lock` should verify all sub-slots have locked kernels (recursive)
4. **Index**: Nodes become slots: `{ kernelId: number | null }` (null = unfilled)
5. **Mine**: Full coordinates include `90[id]900` prefix
6. **MineSpace**: Global plane tracks all locked kernels

---

## 10. The Spiral Loop: Walking the Fiber Bundle

**Status: FORMALIZED**

The CB flow IS a spiral loop. Each iteration refines the encoding.

### Variables

| Variable | CB Realization |
|----------|---------------|
| **W** (walker/content) | LLM + spaces + nodes + filled kernels |
| **L** (lens/encoding) | Coordinate grammar, `coordToReal()`, token table |
| **C** (compiler/specializer) | `mine()`, `parseCoordinate()`, `scry()` |
| **T** (trace/provenance) | MineSpace — real-number projection of what happened |

### Phases

| Phase | Operation | Hot | Frozen |
|-------|-----------|-----|--------|
| **Sense-lock** | `create` (fix the lens) | — | L, C |
| **Walk** | `bloom` + `fill` | W | L, C |
| **Trace** | (implicit) coordinates created | T | — |
| **Swap** | `lock` (freeze walk) | L, C | W, T |
| **Recompile** | `mine` + update encoding | L, C | W, T |
| **Diff** | Compare invariants | — | all |
| **Tag** | same / branch / catastrophe | — | — |
| **Repeat** | Next spiral turn | — | — |

### Viz ↔ Spiral Isomorphism

The Viz tuple from DESIGN.md Part 1 was incomplete at 3 elements. T completes it:

```
Viz    = (Space,      Projection, Camera, Trace)
Spiral = (W,          C,          L,      T)
       = (Content,    Compiler,   Lens,   Recursion)
```

| Viz | Spiral | Role |
|-----|--------|------|
| **Space** | **W** (walker) | What you navigate — the content |
| **Projection** | **C** (compiler) | Maps high-dimensional content → viewable form |
| **Camera** | **L** (lens) | Your viewpoint, your frame of reference |
| **Trace** | **T** (trace) | The recursion operator — mine a Space, get a new Space |

T fires every time you lock+mine:

```
Viz₀ = (Space₀, C, L, T)  → T₀ = mine(lock(Space₀)) = mineSpace₀
Viz₁ = (T₀,     C, L, T)  → T₁ = mine(lock(T₀))     = mineSpace₁
Viz₂ = (T₁,     C, L, T)  → T₂ = mine(lock(T₁))     = mineSpace₂
```

Camera modes ARE spiral phases:

| Camera Mode | What It Is |
|------------|-----------|
| **Orbit** | Global view of Viz₀ — all kernels |
| **Fly** | Local navigation within current Viz level |
| **Nested-Dive** | T → descend to Viz₁ (enter locked kernel's mineSpace) |

### Fiber Bundle Interpretation

| Math | CB |
|------|-----|
| **Base space** | Set of all kernels |
| **Fiber** F(k) | MineSpace of kernel k |
| **Total space** | All (kernel, mineSpace-point) pairs |
| **Projection** | (kernel, point) → kernel |
| **Structure group** | The flow: create → bloom → fill → lock → mine |
| **Parallel transport** | Spiral iteration: comparing fibers across iterations |
| **Flat section** | Invariant — point survives transport |
| **Curvature** | Encoding changed what an entity means |

### RKHS Equipment (Hybrid Kernel)

**Status: IMPLEMENTED** (`lib/crystal-ball/kernel-function.ts`)

```
K(x, y) = K_named(x, y) + α · K_walk(x, y)
```

- **K_named**: known features (labels, attributes, spectra)
- **K_walk**: unknown structure (random walk on DAG adjacency)
- **analyzeSpace()**: Gram matrix, eigenspectrum, orbits, distances
- **foundationSignature()**: (orbit partition, quotient graph, local aut groups)
- **detectSymmetryBreaking()**: identical / renamed / broken / enhanced / new

### Symmetry as Reasoner

The symmetry group IS the validation criterion:

1. Walk → fill kernels → mine → compute foundation signature
2. LLM names structural patterns → names become K_named features
3. Compare signatures across kernels:
   - Same → valid (consistent structure)
   - Broken → meaningful mutation (investigate)
4. Repeat → spiral tightens, foundation converges

---

## 11. Priorities (Updated)

### NOW — KernelSpace Architecture

1. **KernelSpace refactor**: Implement global monotonic IDs, sub-kernel slots, recursive lock. This is the foundation everything else depends on.

2. **Full coordinate model**: `90[globalID]900[local]` → `coordToReal()` on the full string. Update mine to use full coordinates.

### NEXT — Complete the Loop

3. **`reifyMineSpace()`**: MineSpace → KernelSpace. Closes the spiral.
4. **Cross-kernel comparison**: Apply `foundationSignature()` + `detectSymmetryBreaking()` across locked kernels to find foundation patterns.
5. **Global mineSpace persistence**: Store locked kernels and their global IDs.

### DONE — From This Session

- ✅ ALSO token (`90009`/`9900099`) — parser + scry
- ✅ Fill mode bypass (coordinates no longer intercepted)
- ✅ CBNode x,y position
- ✅ Hybrid kernel function (K_named + K_walk)
- ✅ Space analysis (Gram matrix, eigenspectrum, orbits, distances)
- ✅ Foundation signature (orbit partition, quotient graph, local aut groups)
- ✅ Symmetry breaking detection

### MAYBE LATER — Speculative / Research

6. **TypeScript ontology encoding**: Encoding TS's AST as CB kernels.
7. **Monster verification**: Check if CB's symmetry groups match Monster Walk groups.
8. **GP posterior sampling**: Treat mineSpace as GP posterior, mine = sample.

---

## Carton Concepts (to create)

- `Crystal_Ball_ALSO_Token`
- `Crystal_Ball_KernelSpace_Architecture`
- `Crystal_Ball_Global_MineSpace`
- `Crystal_Ball_Full_Coordinate_Model`
- `Crystal_Ball_Spiral_Loop`
- `Crystal_Ball_Fiber_Bundle_Interpretation`
- `Crystal_Ball_RKHS_Equipment`
- `Crystal_Ball_Foundation_Signature`
- `Crystal_Ball_Symmetry_Breaking_Detection`
- `Crystal_Ball_Scott_Domain_Collapse`
- `Crystal_Ball_LLM_As_Navigation`
- `Crystal_Ball_Monster_Walk_Connection`

