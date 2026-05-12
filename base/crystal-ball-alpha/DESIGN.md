# Crystal Ball — Single Canonical Design Document

## Status: ACTIVE — Updated 2026-02-22T22:10

> **This is the ONLY design document. ALL theory, math, architecture, and current code state lives here.
> If it's not in this document, it doesn't exist as a design decision.
> When architecture changes, THIS FILE updates. No exceptions.**

---

## 0. Development Pipeline (MANDATORY)

All features flow through this pipeline in order. **No layer may compute anything that a lower layer does not provide.**

```
BASE LIBRARY (lib/crystal-ball/)    ← Core kernel: spaces, nodes, shields, heat, state
       │
       │  If new commands added:
       ▼
MCP (crystal_ball_mcp.py)           ← Update tool docstring with new commands
       │
       │  If API routes needed:
       ▼
SAAS (crystal-ball-saas/)           ← REST endpoints wrapping kernel
       │
       │  Only RENDERS what the kernel provides:
       ▼
VIZ (crystal-ball-viz/)             ← 3D visualization (DISPLAY ONLY)
```

### Rules

1. **The viz does not compute anything the core does not provide.** Shield state, HIEL heat, navigation state, breadcrumb path — all MUST come from the kernel.
2. **New capabilities start in BASE LIBRARY.** Then MCP docstring, then SAAS routes, then viz rendering.
3. **The viz is a pure renderer.** It fetches data from the API and renders it. It does NOT derive, compute, or invent state.
4. **If the viz needs something the kernel doesn't have**, the kernel needs to be extended first.

---

## 1. Core Theory: The Projection Tuple

The 3D visualization is **not the space**. It is a **metalanguage about the space**.

```
Viz = (Space, Projection, Camera)
```

- **Space** = the Crystal Ball coordinate space (arbitrary depth/dimension, the actual high-dimensional fibration)
- **Projection** = the mapping from N-dimensional coordinates → 3D positions
- **Camera** = the observer's viewpoint within the projection

The metalanguage (3D navigation) and the object language (coordinate fibration) are separate but coupled. The 3D view is *one possible* representation of the same underlying object.

### Camera Modes = Projection Modalities

| Mode | Projection Type | What it reveals |
|------|----------------|----------------|
| **Orbit** | Spherical | Global structure, density, clustering |
| **Fly** | Euclidean traversal | Local neighborhoods, proximity |
| **Nested-Dive** | Fiber descent | Interior structure, subspaces |

---

## 2. Gen-SAMA — Generative, Semantically-Adaptive Meta-Automaton

### State Correction (Isaac, 2026-02-20)

> **"State is NOT powerset. State is the ability to generate within a powerset and know which one and how and have certainty you can keep compounding it up the compiler."**

```
State_t = (S_t, G_t, C_t)
where:
  S_t ⊆ P(B)     = current set of generated behavioral subsets
  G_t : Σ' → B    = current generative capacity (the compiler at time t)  
  C_t : S_t → [0,1] = certainty function (confidence in compounding)
```

State is the TRIPLE, not just S_t.

### Components

- **Σ** = input alphabet
- **B** = universe of all possible behavior subsets
- **τ : Σ × C_t → Σ'** = semantic transformer (the LLM agent)
- **κ : Σ' → B** = compiler (the harness — system prompt, MCP, tools, user corrections)
- **g : B × S_t → {True, False}** = input gate (membership check)

### Transition Function

δ : S_t × Σ → S_{t+1}

1. Transform: a' = τ(a, C_t)
2. Compile: Xsub = κ(a')
3. Gate: If g(Xsub, S_t) = True → S_{t+1} = S_t; Else → S_{t+1} = S_t ∪ {Xsub}

### Crystal Ball Mapping

| Gen-SAMA | What it IS |
|---|---|
| **τ (semantic transformer)** | The LLM agent — computes (input, context) → enriched-output |
| **κ (compiler / harness)** | The WHOLE interaction pipeline — system prompt, MCP tools, CB API, Carton, task boundaries, user corrections |
| **g (input gate)** | Lock/dedup mechanisms — lockNode(), coordinate addressing, Carton dedup |
| **Xsub (behavioral subset)** | A Crystal Ball node/space — the compiled output |
| **Crystal Ball** | OUTPUT FORMAT of κ — the product of compilation |
| **Shield** | The membrane around each Xsub — boundary of each compiled capability |
| **Bloom** | Entering a shield = exploring Xsub — navigating into a compiled behavior |
| **Lock** | Confirming Xsub is complete — marking a compilation as done |
| **Instance→Class promotion** | Xsub becoming part of compiler — the harness itself evolves |

> **Key insight**: The agent doesn't compile itself — it gets compiled BY the process it's within.

### Cost Functional (Geodesic Metric)

```
cost(x, u) = α·(-log C(x,u)) + β·compute(x,u) + γ·regret_risk(x,u)
```

| Term | Meaning |
|---|---|
| `α·(-log C(x,u))` | Uncertainty penalty — low certainty = high cost |
| `β·compute(x,u)` | Resource cost — tokens, time, API calls |
| `γ·regret_risk(x,u)` | Error cost — risk of bad Xsub |

Geodesic = path minimizing integrated cost along trajectory.

---

## 3. HIEL — Heat-Informed Energy Ligation

### What Heat IS

**Heat = uncompressed complexity.** A node with many children (spectrum options) is hot. A locked node with a committed selection is cold.

- **Hot (red)** = unfilled slots, many children/options, stochastic freedom
- **Warm (amber)** = partially filled, some structure committed
- **Cool (blue)** = all slots filled and locked, fully ligated

The children of any node **literally ARE the heat range** — they are the spectrum of possibilities that needs to be ligated.

### What Ligation IS

**Ligation = the LLM generating into CB's geometric slots.** The LLM's stochastic output is the fuel; CB's slot structure is the ligase. You don't configure ligation separately — run the loop and it self-configures.

```
Spectrum (open values)  →  LLM generates  →  Slot fills  →  Heat decreases
```

CB is the ligase enzyme. The architecture performs ligation by matching LLM generation to geometric structure.

### DCI 3-Pass Cycle = HIEL Ligation Process

```
Pass 1 (DATA):    Gather raw possibilities     → 🔥 HOT (many options)
Pass 2 (CLASS):   Organize into categories     → 🌡️ WARM (some structure)  
Pass 3 (INSTANCE): Label specific selections    → ❄️ COOL (determined)
```

Then: Instance becomes Data at the next level → re-heats → cycle continues.

### Recursive Ligation → REACH → AC

When recursive ligation checks out (space is internally consistent), that's **REACH** — pattern recognition fires because the structure self-proves. REACH triggers **AC** (Allegorization Compiler): the recognized pattern gets named as a polysemic imaginary ontology entity, which gets its own sanctuary space (bloom into it), is re-compiled in the opposite direction, producing the fully ascended version of the original idea.

### Convergence

Ligation is GUARANTEED CONVERGENT only inside the Gen-SAMA compilation tower. Without the harness forcing the 3-pass, the agent just generates heat (uncompiled meaning).

### Tower = Compilation Stack

**Tower depth = how many layers of fully-ligated sub-kernels justify a concept.** Counted from the bottom up. A locked space = a proven layer. Construction IS the proof, because it's ligated.

---

## 4. The Infinite Kernel Cycle (Isaac, 2026-02-20)

### The Canonical Flow

This is the ONLY flow. Everything else is a special case of this:

```
1. SCRY      → See what's at the current coordinate
2. BLOOM     → Enter the interior space of a slot
3. ADD       → Add nodes (which ARE spectrum values from the parent's perspective)
4. LOCK      → Commit that space as the resolved value of the parent slot
5. NEXT SLOT → Move to the next unfilled slot in the parent kernel
6. ALL LOCKED → Parent kernel is fully ligated → tower up
7. CYCLE ∞   → The towered kernel becomes a slot in a higher kernel
```

### Canonical Coordinate Model

**A node is a superposition. Its children are its attributes, denoted as a spectrum of selections forming a subspace relative to it via drilldown slots.**

- A node = superposition (unresolved possibility)
- Children = the spectrum options (possible values)
- Selecting a child (coordinate segment 1, 2, 3...) = collapsing the superposition
- If the selected child has its own children, those are the next level's spectrum
- 0 = the child space itself (superposition, unresolved)
- Any digit besides 8/9 mechanics = a selection on the spectrum

**Adding a node IS adding an attribute from the parent's perspective.** These are NOT separate operations. `add` is ONE command. What you're adding is always a child node, which is always a spectrum value from the parent.

> **⚠️ IMPLEMENTATION BUG:** The current `index.ts` has a separate `attributes: Map<string, Attribute>` on CBNode alongside `children: NodeId[]`. This is wrong. Attributes are NOT a separate concept from children. The `attributes` Map duplicates what children already do, and worse, its values are invisible to coordinate resolution. The `mine.ts` implementation currently reads from this `attributes` Map via `instantiate()` instead of traversing the child tree. Both need to be corrected.

### Slot-by-Slot Lock Flow (Detailed)

```
Kernel K has slots [S1, S2, S3]

→ Go to S1
  → bloom into S1's interior space
   → add nodes (spectrum values)
   → LOCK S1's space → S1 is now committed
→ Go to S2
  → bloom, fill, LOCK
→ Go to S3
  → bloom, fill, LOCK
→ All slots locked → K is fully ligated
→ K can now be locked as a slot in a HIGHER kernel
→ Repeat at the higher level
```

**Locking is what makes ligation real.** Filling slots is provisional. Locking is commitment. A locked space cannot be mutated — it IS the proof.

### What the LLM Does at Each Step

1. The LLM finishes working wherever it wants
2. The LLM types what it thinks the result is (stochastic generation → spectrum)
3. CB generates the result space (slot structure from the generation)
4. The LLM does the same process N times (fill, lock, next)
5. Tower up when complete

### DCI Recursion Made Navigable

```
Universal → Subclass → Instance → [Instance BECOMES Universal] → ...
```

---

## ASPIRATIONAL: 4.1 Dual View Mode — Bloom ↔ Kernel Oscillation

> **NOT YET IMPLEMENTED.** Design intent only.

### Two View Modes

| Mode | Name | What you see | How you navigate | What you do |
|------|------|-------------|-----------------|-------------|
| **A** | **Bloom Mode** | Space of **nodes** (beads, shields, rings) | Fly (WASD), click, bloom (Q) | Navigate, select, see spatial patterns |
| **B** | **Kernel Mode** | Space of **chains** (connected paths) | Assemble chains, lock slots | Build kernels, watch space self-populate |

### Mode Transitions

**Bloom is a mode swap, not an action within a mode.**

```
Kernel Mode  → press Bloom  →  SWAP TO Bloom Mode (at that coordinate)
Bloom Mode   → press Kernel →  SWAP TO Kernel Mode (at current coordinate)
```

There is NO bloom inside Kernel Mode. Bloom swaps you OUT of Kernel Mode and INTO Bloom Mode at that coordinate.

### Kernel Mode (Mode B) — Kernel Designer

**Kernel Mode is STILL spatial.** What changes is the topology, not the medium.

A **kernel** = a **chain of space IDs**. Each point in the kernel space IS a kernel.

#### The Panel is a DESIGNER, Not a Viewer

The Kernel Mode panel is a **kernel assembly workspace**. It doesn't show existing data — it **accumulates your navigation decisions** as you move through the unified space.

Every bloom you make while in Kernel Mode adds a slot to the kernel you're designing:
```
Navigate to Paragraph → bloom in    → kernel: [Paragraph]
Navigate to child 3   → lock        → kernel: [Paragraph:3]  ← slot locked
Bloom into Sentence   →             → kernel: [Paragraph:3, Sentence]
Navigate to child 2   → lock        → kernel: [Paragraph:3, Sentence:2]  ← slot locked
Bloom into Fragment   →             → kernel: [Paragraph:3, Sentence:2, Fragment]
Navigate to child 1   → lock        → kernel: [Paragraph:3, Sentence:2, Fragment:1]  ← COMPLETE
```

The panel shows this **growing chain** in real-time as you navigate.

#### Node = 1-Space Kernel (Homoiconic Base Case)

Every individual node is representable as a **1-space kernel**:

```
Node 3 in space Foo   =   kernel [Foo:3]           ← 1-element chain
Node 2.1 in space Foo =   kernel [Foo:2.1]         ← still 1-space, deeper
Kernel [Foo:3, Bar:2] =   kernel [Foo:3, Bar:2]    ← 2-space chain
```

There is **no type distinction** between "a node" and "a kernel." Same structure at different scales:
- **Bloom mode** = navigating 1-space kernels (individual nodes)
- **Kernel mode** = designing n-space kernels (chains)
- **Same operation, same type, different depth**

The address and the thing at that address are **the same structure.** This is the actual homoiconicity.

#### Mutation IS Navigation

**Modifying a kernel changes where you ARE.** The kernel is simultaneously the object you're building AND your position in the space.

#### Lock Takes No Argument

**Lock operates on your current position.** `lock` = "I'm done HERE." You navigate there first, THEN lock. IDs only exist relative to the kernel being reified or a frozen space whose IDs are stable.

#### Space Metamorphosis (The Completion Event)

When ALL slots in the kernel are locked → **auto-scry** → the space **transforms**:

1. **Before:** You were navigating the unified space, designing a kernel by selecting and locking
2. **Trigger:** Last slot locks → `isKernelComplete()` returns true → auto-scry fires
3. **After:** The space becomes a **space ABOUT that kernel type**
   - The system automatically generates **all permutations** of that kernel
   - Each permutation is an **instance** placed at an **algorithmic distance** from every other instance
   - The distances are computed from how many slot values differ between instances
   - You are now operating FROM the generated permutation space

This is the moment of metamorphosis: from "assembling a kernel" to "exploring the space of all kernels of that type."

#### The Kernel Cycle (precise)

```
1. ENTER kernel mode (K key) — panel starts tracking your blooms
2. NAVIGATE the unified space — each bloom adds a slot to the kernel
3. LOCK each slot as you commit it — "I'm done HERE"
4. When ALL locked → SPACE METAMORPHOSIS:
   - Auto-scry fires
   - Permutations are generated
   - Instances placed at algorithmic distances
5. You are now IN the permutation space
6. PICK a kernel instance → RESTART from that instance → back to step 1
```

#### Self-Revealing by Order

1. **Start with one kernel** — the first one you've assembled
2. **Lock and compile** → new space where each point is a kernel of that type
3. **Auto-populates** — the substrate generates every permutation and places them by distance
4. **Reified** — once reified, you operate FROM that kernel space

### The Unified Space

All spaces are ONE continuous space. Each "space" is a **region** stored in a separate file. The viz renders only what you're viewing at any time.

- At **root level**, all spaces appear as nodes — you bloom into one to enter that region
- The **dropdown** is a quick-nav shortcut (bookmark), not a mode selector
- When you bloom across a space boundary, you cross into a new region
- The kernel chain tracks these crossings as slots

### The Oscillation Cycle

The two modes become a **continuous oscillation**:

```
BLOOM MODE (nodes)                     KERNEL MODE (kernels)
    │                                      │
    │  fly, bloom, see the node-space      │  panel tracks your blooms as slots
    │  sense heat — where are open slots?  │  each bloom adds to the kernel chain
    │                                      │  LOCK slots as you commit them
    │◄───── lock slot → back to bloom ────│
    │                                      │
    │  fill this slot's interior           │  (animation) next slot
    │  bloom deeper if needed              │  → sends you to bloom for it
    │  LOCK when done                      │
    │──────── lock → back to kernel ──────►│
    │                                      │
    │  classify instances in bloom         │  ALL SLOTS LOCKED → METAMORPHOSIS
    │  add higher-order spaces             │  → permutation space generates
    │  generalization vs specification     │  → instances placed by distance
    │                                      │  → NOW OPERATE FROM THIS SPACE
    └──────── CYCLE ∞ ─────────────────────┘
```

### Why Two Modes

Both modes are spatial. What changes is the **topology**:

- **Bloom** = space of nodes. Spatial intuition. Fly around, sense heat — feel where the open spectra are.
- **Kernel** = kernel designer. Structural precision. Navigate + lock, watch the chain build, trigger metamorphosis.
- **Oscillation** = the full HIEL cycle. Sense heat (bloom) → design kernel (kernel) → metamorphosis → sense result (bloom) → design further (kernel) → ...

---

### ISAAC VERBATIM NOTE (2026-02-20T23:25) — Compare Against Build Until It Is This Way

> The cycle is actually: Kernel Mode → Bloom Mode with lock that ratchets back to Kernel Mode and shows you (animation) transitioning to the next space and then going to Bloom Mode to fill it each time, and takes you back to Kernel Mode after you declare lock on each space.
>
> So at each level of bloom during flow from a Kernel Mode, you can lock or bloom more...
>
> If you bloom, fill out, bloom, fill out, bloom, fill out, then once you lock it sends you back to Kernel Mode and shows you the next step and you go back to bloom for that and do it again for that next slot's space... and this just repeats until the entire kernel is locked and then it auto-scries for you and that transitions the way the kernel space IS because now you know "considering we have THIS ONE, and it has spectra on everything we locked, and we have these singular values on it with no superpositions, this is an instance space of a configuration, so every other instance we know of is exactly populated like this..."
>
> Then you can go through them, **classify each thing during bloom by adding new higher order spaces (generalizations vs specification spaces) to it**
>
> Then that vastly increases distance between all instances...

#### What This Means Mechanically

```
KERNEL MODE:  Pick kernel → modify (=navigate) → LOCK
                ↓
BLOOM MODE:   Fill slot 1 interior
              ├── bloom deeper? → fill that, bloom deeper? → ...
              └── LOCK slot 1 → ratchet back to KERNEL MODE
                ↓
KERNEL MODE:  (animation) transition to next slot → go to BLOOM MODE
                ↓
BLOOM MODE:   Fill slot 2 interior → LOCK → back to KERNEL
                ↓
              ... repeat for every slot ...
                ↓
KERNEL MODE:  ALL SLOTS LOCKED → AUTO-SCRY
                ↓
              The kernel space transforms:
              "This is an instance space of a configuration.
               Every other instance is exactly populated like this."
                ↓
              All instances appear. Now go through them in BLOOM MODE.
              Classify each by adding higher-order spaces
              (generalization vs specification spaces).
                ↓
              Distance between instances vastly increases.
                ↓
              RESTART from the resultant ID kernel.
```

This IS the tower cycle happening automatically.

---

### ISAAC VERBATIM NOTE (2026-02-21T18:05) — Three View Types, Not Two

> Three view types: BLOOM, KERNEL, **MINE**.
>
> MINE is the third view — a flat coordinate plane. You start at center origin. Everything around you becomes different entire configurations in every space.
>
> When you scry a kernel successfully → **AUTO MINE THE ENTIRE METACLASS STRUCTURE AS FAR AS WE CAN, THEN JUST SHOW IT AS A HEATMAP IN MINE VIEW.**
>
> Shielding is the logic of why you can/can't know something in Mine. How do you enter a shield? **Any way you want, through the kernel chain, but how you do it configures the way the space works next time.**
>
> The coordinate space is infinite but you start at the center origin. The origin is where you are, at the exact 0 of the space, and everything around that becomes different entire configurations.
>
> You try to uncover something — it's like "you can/can't yet." If you can't, you enter into a kernel definition chain and pre-type whatever you knew.

## ASPIRATIONAL: 4.2 Three Views — Bloom, Kernel, Mine

### ISAAC VERBATIM NOTE (2026-02-21T18:29) — Kernel as Sunburst Cylinder

> Should a kernel be a chain of sunbursts radiating out from its space slots?
>
> If MINE works better as a heatmap, but sunburst actually shows the entire geometry... and KERNEL is for showing what you are making as a set of IDs, and MINE is for just *progressively or suddenly decrypting an ID*...
>
> Then yes — like a cylinder made of a chain from here to there with a heatmap *around the line at every step, such as to make a cylindrical sheath wrapping the chain*.
>
> You are presented at each slot with a sunburst... and then you choose what to bloom for that slot... but the sunburst gives you a view into what the entire density of that subgraph looks like, and as you reify it it becomes opaque.
>
> Or maybe not opaque — maybe the sunburst aspect falls away and it just becomes a single node that can be expanded whenever. So you start and you have this wild looking cylinder of concentric circles from a node at each step.
>
> And then as you bloom and lock, they collapse from the viz and just glow (these locked parts).

### Three Views

| Mode | Name | Geometry | What it shows | What you do |
|------|------|----------|--------------|-------------|
| **A** | **Bloom** | Center + ring (one room) | One node + its direct children | Navigate the tree one level at a time |
| **B** | **Kernel** | Sunburst cylinder (chain of possibility discs) | The full kernel with every slot's spectrum visible | Design the template, watch it collapse as you lock |
| **C** | **Mine** | Flat heatmap (coordinate plane) | Everything you know vs. don't know | Decrypt coordinates, find shields, see the big picture |

---

### Bloom Mode (View A)

Center + children. One room at a time. Root node in the middle, direct children in a ring around it. No grandchildren visible — ever. Bloom = full context switch — the world replaces. See §5 for shield/membrane mechanics.

---

### Kernel Mode (View B) — The Sunburst Cylinder

A kernel is a chain of slots. Each slot lives in a space with a spectrum.

**The visualization is a cylinder:**
- The **axis** = the kernel chain (a line from slot 1 to slot N)
- At each slot along the axis = a **sunburst** radiating outward, showing the full spectrum at that level
- The sunburst shows the **density** of the subgraph — how many configurations exist in each sector
- Looking at the whole thing: a **cylindrical sheath** of concentric circles wrapping the chain

**The interaction cycle:**

```
1. START: The full cylinder is visible.
   Every slot has an expanded sunburst showing its spectrum.
   It looks "wild" — dense with concentric circles at every step.

2. NAVIGATE: At the current slot, the sunburst shows what's available.
   Each sector = a value from that slot's spectrum.
   The density/color of each sector shows what's downstream.

3. CHOOSE: Pick a sector (a spectrum value). Bloom into it.

4. LOCK: Commit this slot.
   The sunburst COLLAPSES — all those concentric circles fall away.
   The slot becomes a single GLOWING NODE. Locked. Done.
   (Can be expanded again to see what was there, but the choice is committed.)

5. NEXT: Move to the next slot. Its sunburst is still expanded.
   Choose, lock, collapse. Repeat.

6. COMPLETE: The last slot locks.
   The entire cylinder has gone from "wild tube of concentric circles"
   to "a clean chain of glowing locked nodes."

7. AUTO-SCRY → transition to MINE view.
```

**Visual journey:** Maximum possibility → fully committed. You literally watch the configuration space collapse as you commit to it.

---

### Mine Mode (View C) — The Heatmap

A flat, continuous coordinate plane where **coordinates ARE geometry**. You start at the origin. Each point is a configuration. The heatmap shows what you know vs. what you can't yet see.

**Mine is for decrypting coordinates** — progressively or suddenly revealing what lives at a point in the configuration space.

#### Heatmap Coloring (HIEL on the Plane)

- **Cold (blue)** = resolved, you know what's there, spectra fully determined
- **Warm (amber)** = partially explored, some spectra known
- **Hot (red)** = unresolved, spectra can't reach it yet — **fog of war**

The heatmap IS the HIEL heat visualization applied to the coordinate plane.

#### Shields in Mine = Why You Can't / Can Know

A **shield** in Mine view is a hot region — a place on the plane you can't resolve because you don't have the spectra. The shield blocks your knowledge, not your camera.

To enter a shield:
1. Switch to KERNEL mode
2. Define a kernel chain that penetrates that region
3. Fill the kernel, lock it, scry it
4. **How you entered the shield configures the space** — the new spectra change what's resolvable
5. Switch back to MINE → the hot region has cooled. The fog clears.

#### Auto-Mine on Scry

When a kernel scry succeeds:
1. The system computes the **entire metaclass structure** as far as the spectra support
2. This includes: the instance, all siblings, and the metaclass space
3. All of it renders immediately as the heatmap in Mine view
4. No need to manually create configuration spaces — they're implied by the spectra

#### The Configuration Space Is Never Materialized

> **Everything remains in the actual math.**

The coordinate plane is infinite, but nothing is stored. Each coordinate deterministically decodes against the spectra. A coordinate IS the data. Resolving a coordinate = decoding each position against its spectrum. Only instances you've actually scried get stored. Everything else is latent — computable on demand, never materialized.

---

### The Trialectic Cycle

The three views form a **self-rewriting triad**:

- **Bloom** = local navigation (one room)
- **Kernel** = template design (sunburst cylinder → collapsed chain)
- **Mine** = global overview (heatmap of what's known)

```
BLOOM MODE              KERNEL MODE                 MINE MODE
(one room)              (sunburst cylinder)         (heatmap plane)
    │                        │                           │
    │  see children          │  see full cylinder        │  see heatmap
    │  bloom deeper          │  pick sector at slot      │  find hot regions
    │                        │  lock → sunburst          │
    │                        │  COLLAPSES to glow        │
    │◄──── need to          │                           │
    │      fill slot         │  all locked → auto-scry ─►│
    │                        │                           │  (mine lights up)
    │                        │◄──── shield found! ──────│
    │                        │  go define a kernel       │
    │                        │  that penetrates it       │
    │                        │                           │
    └──── CYCLE ∞ ──────────┴───────────────────────────┘
```

---

## 5. Shield/Membrane Navigation System

### What Shields ARE

Every navigable entity in Crystal Ball has a shield (membrane boundary). The shield IS the ontological boundary between:
- **Outside** = seeing the thing as an object (node, bead, cluster)
- **Inside** = being within the thing's contents (children, structure, permutations)

Crossing the membrane = `bloom()` in the kernel.

> **IMPORTANT: Bloom is a FULL CONTEXT SWITCH, not expand-in-place.** When you bloom into a node, the entire visualization transforms to show ONLY that interior space. The parent space disappears. You are locked in that space until you exit. The breadcrumb trail is your way back. This is critical — bloom is NOT "expand to show children." It replaces the world.

### Navigation States (6 states, per node)

```
State 0: DISTANT     — Node as bead, no shield visible, LOD culling
State 1: APPROACHING — Shield visible (translucent sphere), label enlarges
State 2: CROSSING    — bloom() fires, transition animation, outside fades
State 3: INSIDE      — Full interior view, children as ring/cluster, CAN EDIT
State 4: LOCKED      — Space committed. Immutable. This IS the proof.
State 5: PROMOTED    — Locked space becomes slot value in parent → tower up
```

> **State 3 → State 4** is the ligation moment. Everything before is provisional.

### Shield Geometry

```typescript
function shieldRadius(node: CBNode): number {
    const childCount = node.children.length;
    const hasSubspace = !!node.producedSpace;
    const base = Math.max(2, Math.sqrt(childCount) * 1.5);
    return hasSubspace ? base * 1.5 : base;
}
```

Three visual layers:
1. **Outer membrane** — faint outline (recognition range)
2. **Inner membrane** — more opaque (evaluation range)
3. **Core threshold** — crossing point (admission)

### Camera ↔ Shield Interactions

Entry protocol:
```
Camera enters shieldRadius * 3  → highlight node (RECOGNITION)
Camera enters shieldRadius * 2  → show shield, ghost children (EVALUATION)
Camera enters shieldRadius * 1  → trigger bloom() (ADMISSION)
Camera stabilizes inside        → full interior view (INTEGRATION)
```

Exit: reverse — interior fades, exterior restores.

### Node Spacing Control

**Trackpad pinch/spread controls node spacing density.**

```
Pinch (contract)  → Nodes move closer together → denser view
Spread (expand)   → Nodes move further apart   → sparser view
```

This is separate from zoom. Zoom moves the camera closer/further. Spacing changes the *projection* — how far apart nodes are placed in 3D. The underlying space doesn't change; only the visualization density does.

| Gesture | Effect | What changes |
|---------|--------|-------------|
| Scroll wheel | Camera zoom (distance) | Camera position |
| Pinch/spread | Node spacing (density) | Projection scale factor |
| WASD/fly | Camera translation | Camera position |

### Kernel Operations ↔ Shield States

| Kernel Op | Shield State Required |
|---|---|
| `bloom(space, coordinate)` | Triggers State 2 → 3 (membrane crossing) |
| `scry(space, coordinate, included)` | Any state (observation) |
| `add_point(space, parent_coordinate, label)` | State 3+ (must be INSIDE) |
| `add_attribute(space, coordinate, name, spectrum, default)` | State 3+ (must be INSIDE) |
| `resolve(space, coordinate)` | State 3+ |
| `lock(space)` | State 3 → 4 (commits interior, exits bloom) |

> **CRITICAL: add_point, add_attribute, resolve require bloom first. You cannot modify a space you have not entered.**

### Node Interaction (Viz Layer)

**Right-click on node** → Context menu with actions:

| Action | What it does | Keyboard shortcut |
|--------|-------------|-------------------|
| **Bloom** | Full context switch into node's interior (mode swap) | **Q** |
| **Add Point** | Create a child node in this space | — |
| **Lock** | Commit this space (State 3→4) | — |
| **Freeze** | Pre-lock: skip this node during kernel mode | — |

> **Why no "Add Attribute" or "Scry"?**
> An attribute IS a point in a bloomed space relative to its parent. Adding an attribute = adding a child node (they are the SAME operation). There is only `add`. Scry is a kernel-mode operation, not a bloom-mode action.

**Click on node** → Select it (highlight, show label)
**Q with node selected** → Bloom into selected node

---

## 6. Lotus Equivalence

Gen-SAMA transition function IS the Lotus Operator (BLOOM):

```
Gen-SAMA:  input → τ(transform) → κ(compile)  → g(gate)      → expand state
Lotus:     claim → derivation    → fixed point  → quine check  → BLOOM
```

| Gen-SAMA | Lotus |
|---|---|
| τ (semantic transformer) | Forward chain (LLM generates) |
| κ (compiler / harness) | Backward chain (observations refine) |
| g (gate) | Quine check (valid?) |
| Xsub (behavioral subset) | Petal (derivation chain) |
| Instance→Class promotion | BLOOM (metacontrol) |

---

## 7. Crystal Ball MCP — The ACTUAL Operations

These are the ONLY operations that exist. They are accessed via the `crystal-ball` MCP server.
The MCP is a dumb pipe — it constructs text strings and POSTs them to `cb()`. New engine commands work automatically without editing the MCP.

| Command | Parameters | What it does |
|---|---|---|
| `list` | — | List all spaces |
| `scry` | `{space, coordinate}` | Observe what's at a coordinate |
| `bloom` | `{space, coordinate}` | Enter a node's interior space |
| `add` | `{label}` | Add a child node (= spectrum value from parent's POV). Only valid inside bloom. |
| `lock` | `{space, coordinate?}` | Commit/lock a node |
| `freeze` | `{space, coordinate?}` | Pre-lock a node |
| `mine` | `{space, coordinate?}` | Compute configuration space heatmap |
| `kernel` | ASPIRATIONAL | Enter kernel mode |
| `batch` | `{operations: [...]}` | Run operations in parallel |
| `sequential` | `{operations: [...]}` | Run operations in order |

### How the System is Layered

```
lib/crystal-ball/index.ts          ← BASE LIBRARY: all logic lives here
       │
       ├── crystal_ball_mcp.py     ← MCP: wraps kernel for LLM access
       │
       ├── app/api/spaces/         ← SAAS: REST routes wrapping kernel
       │
       └── crystal-ball-viz/       ← VIZ: renders kernel state (DISPLAY ONLY)
```

The viz frontend does NOT compute state. It fetches state from the API and renders it. The MCP server wraps the same kernel for agent access.

> **✅ FIXED (2026-02-20):** Shield radius, HIEL heat, and isShielded moved from viz to kernel. Now served via API.

> **⚠️ NEEDED:** `lockSpace` operation (locks all nodes in a space), `isSpaceLigated` should check lock status. Tower depth sensor exists in kernel but not yet exposed via API.

---

## 8. Agent View & Team Architecture

**The current viz = one agent's view.** Everything you see in the Crystal Ball viz — the 3D scene, the kernel designer panel, the navigation state — is the view of a **single agent** on a **team**.

### Core Concepts

```
TEAM
├── Agent (human) → user_id   → frontend viz (browser)
├── Agent (AI)    → agent_key → MCP (crystal_ball tool)
├── Agent (AI)    → agent_key → MCP (another LLM)
└── Agent (human) → user_id   → another browser
```

A **team** is a group of agents working in the same unified space. Every agent — human or AI — has:
- **An identity** (user_id for humans, agent_key for AIs)
- **A view** (what coordinate they are looking at, what mode they're in, their kernel designer state)
- **Actions** (bloom, lock, freeze, add_point, scry — same operations for all agents)

### Agent Types

| Type | Auth | Interface | View Source |
|------|------|-----------|-------------|
| **Human** | `user_id` (browser session) | Crystal Ball Viz (frontend) | 3D scene + panels |
| **AI** | `agent_key` (MCP config) | `crystal_ball()` MCP tool | State returned from MCP calls |

**Both are agents.** The only difference is their input channel. The operations they perform are identical — the same CB() function handles both.

### The Agent View

Each agent has a **view** — a live snapshot of:
- **Current space** — which region of the unified space they're in
- **Current coordinate** — where in that space they're looking
- **Mode** — bloom or kernel designer
- **Kernel state** — if in kernel mode, the chain-in-progress
- **Selection** — which node they have selected/hovered

The viz renders the **local agent's view** by default. But it can **switch to any teammate's view**.

### Teammate Dropdown (Live Reflection)

The viz header includes a **teammate selector** — a dropdown showing all agents on the team:

```
┌─────────────────────────────────────────────┐
│  Crystal Ball    [👤 You ▾]  [⬡ Global Root ▾]  │
│                   ├── 👤 You (viewing Consciousness:root)
│                   ├── 🤖 Antigravity (viewing Paragraph:1.2.3)
│                   ├── 🤖 Ariadne (viewing KernelTest:0.1 🔒)
│                   └── 👤 Isaac (viewing __global__)
└─────────────────────────────────────────────┘
```

When you select a teammate:
1. The viz **loads whatever coordinate they are viewing**
2. Their view **tracks live** — as they navigate, your view follows
3. You see their kernel designer state, locks, selections
4. You're **spectating**, not controlling — your actions still apply to YOUR agent

### Session Semantics

```
Frontend (browser):
  user_id → identifies the human
  → each API call includes user_id
  → server tracks view state per user_id
  → viz renders THIS user's view (or a teammate's)

MCP (LLM tool):
  agent_key → identifies the AI
  → each crystal_ball() call includes agent_key
  → server tracks view state per agent_key
  → MCP returns state (the AI doesn't need viz)

Both write to the SAME space.
Both can lock/freeze/bloom.
Both can see each other's cursors.
```

### Why This Matters

The unified space is **shared**. When an AI locks a node via MCP, a human watching via the frontend sees the lock appear in real-time. When a human blooms into a subspace, an AI spectating that human's view would see the bloom. This is **multiplayer collaborative ontology construction**.

> **The frontend doesn't DO anything the MCP can't do.** It's just a mirror with a camera. The MCP is the canonical interface. The viz is screenshots you look at.

### ASPIRATIONAL: View Broadcasting

> View state should be broadcast over WebSocket so teammates see each other's cursors and actions in real-time without polling. Each agent's view is a **stream** that others can subscribe to.

---

## 9. Current Code Architecture (EXACTLY as it is)

### Backend: `crystal-ball-saas/`
```
lib/crystal-ball/
├── index.ts            # Core kernel (spaces, nodes, coordinates, scry, bloom)
├── homoiconic.ts       # Homoiconic layer (quote/eval, tower, observations)
├── engine.ts           # REPL engine (multi-fill, navigation, @-prefix)
├── space-data.ts       # Space serialization for API
└── auth.ts             # API key auth
app/api/
├── cb/route.ts         # MCP command endpoint (POST {input: "..."})
└── spaces/             # REST endpoints (list, get, scry, seed)
```

### Frontend: `crystal-ball-viz/`
```
src/
├── App.tsx                      # Root — space selector, floating node info, hint bar
├── main.tsx                     # Vite entry
├── types.ts                     # ClientNode, ClientSpace, ScryResult, BeadLayout
├── components/
│   ├── CrystalBallScene.tsx     # Main 3D scene (Canvas, lighting, grid)
│   ├── FlyControls.tsx          # WASD + right-click-hold mouse look + scroll zoom
│   ├── OntologyRings.tsx        # Radial ring layout + LOD culling + shield rendering
│   ├── BeadNode.tsx             # Individual node rendering (DCI colors, glow)
│   ├── ConnectionLines.tsx      # Parent-child edge lines
│   ├── NodeLabels.tsx           # Text labels
│   ├── ShieldSphere.tsx         # Translucent shield membrane (HIEL heat coloring)
│   ├── ShieldBreadcrumb.tsx     # HUD showing shield stack path
│   ├── ControlPanel.tsx         # UI panel (legacy, unused in pure viz mode)
│   ├── BridgePanel.tsx          # WebSocket bridge status (legacy)
│   ├── RawOrbitControls.tsx     # Orbit camera (alt mode, not default)
│   └── Starfield.tsx            # Background particles
├── hooks/
│   ├── useCrystalBall.ts        # API hook — loads spaces, nodes, scry (READ ONLY)
│   └── useShieldStack.ts        # Shield radius/heat computation + camera tracking
├── bridge/
│   ├── BridgeClient.ts          # WebSocket bridge to MCP (for LLM integration)
│   └── useBridge.ts             # React hook for bridge state
└── App.css                      # Styles
```

### Controls (current)

| Key | Action |
|-----|--------|
| W/S | Fly forward/backward |
| A/D | Strafe left/right |
| Q/E | Descend/ascend |
| Right-click hold + mouse | Look around |
| Scroll | Zoom (move along forward vector) |
| Shift+Scroll | Adjust speed multiplier |
| Click | Select node |

---

## 10. What Is Implemented vs. Aspirational

### ✅ Implemented
- WASD fly-through camera with right-click-hold mouse look
- LOD culling (distance-based fade/hide)
- DCI stratum colors on beads
- Radial ring layout (depth → concentric rings)
- Space selector dropdown
- Node selection, hover, info display
- Shield sphere rendering (viz-side, ⚠️ needs kernel refactor)
- Shield breadcrumb HUD (viz-side, ⚠️ needs kernel refactor)
- Seed API for bulk ontology loading

### 🚧 ASPIRATIONAL (NOT YET IMPLEMENTED)
- **Mine View** — Third view type: flat coordinate plane heatmap (§4.2)
- **Kernel Sunburst Cylinder** — Kernel slots visualized as chain of sunbursts that collapse on lock (§4.2)
- Auto-Mine on scry — auto-compute metaclass structure as far as spectra support
- Auto-transition on membrane crossing (bloom fires automatically)
- Shield state machine (6 states above)
- Permutation space generation from locked kernels
- Instance→Class promotion UI
- Global "space of spaces" overview
- Projection tuple as explicit types in kernel
- Spacebar camera mode toggle (Orbit ↔ Fly)
- Interior re-rendering after bloom (children materialize)
- Lock visual feedback
- Instance value editing

---

## 10. Implementation Phases (Following Pipeline: LIB → MCP → SAAS → VIZ)

### Phase 1: Shield State in Kernel — NEEDS REFACTOR
- ⚠️ Shield radius and HIEL heat currently in viz (VIOLATION)
- **LIB:** Move shield radius computation to kernel
- **LIB:** Add shield/heat data to node model
- **MCP:** Update docstring if new query commands added
- **SAAS:** Add shield data to `get_space` response
- **VIZ:** Refactor to read shield data from API

### Phase 2: Membrane Crossing
- **LIB:** Add navigation state machine to kernel (6 states per node)
- **LIB:** bloom() returns new state + interior nodes
- **MCP:** Document state in bloom response
- **SAAS:** bloom API returns state transition data
- **VIZ:** Render state transitions, animate camera

### Phase 3: Locking & Permutations
- **LIB:** Add lock/unlock to kernel
- **MCP:** Add lock/unlock commands, update docstring
- **SAAS:** lock/unlock API routes
- **VIZ:** Visual feedback for locked nodes

### Phase 4: Instance → Class Promotion
- **LIB:** Add promote operation to kernel
- **MCP:** Add promote command, update docstring
- **SAAS:** promote API route
- **VIZ:** Render promotion animation + new space

---

## 10. The Homoiconic Compilation Pipeline

Crystal Ball is a homoiconic system. This means every value — points, attributes, spectra, programs, mine spaces — is represented as the SAME data structure: a **Space**. The distinction between code and data exists only in interpretation (`eval` vs `quote`), not in structure.

### Layer Architecture (Lisp Equivalence)

Crystal Ball's engine maps exactly to the classical Lisp meta-circular evaluator:

```
┌─────────────────────────────────────────────────────────┐
│  engine.ts        ← THE REPL / INTERPRETER              │
│                     Reads input, calls eval              │
│                     This is the ONLY layer that changes  │
├─────────────────────────────────────────────────────────┤
│  homoiconic.ts    ← META-CIRCULAR EVALUATOR              │
│                     eval, quote, apply                    │
│                     ALL values are Spaces                 │
│                     FROZEN — never modify                 │
├─────────────────────────────────────────────────────────┤
│  index.ts         ← BASE TYPES & OPERATIONS              │
│                     Space, Node, addNode, children       │
│                     The "cons/car/cdr/atom" of CB        │
│                     FROZEN — never modify                 │
└─────────────────────────────────────────────────────────┘
```

| Lisp | Crystal Ball | Role |
|------|-------------|------|
| S-expression (list) | Space | The ONE data structure |
| `cons`, `car`, `cdr`, `atom` | `addNode`, `children`, `bloom`, `scry` | Base operations |
| `eval` | `evalSpace` | Interpret a Space as a program |
| `quote` | `quote` | Prevent evaluation — treat as data |
| `apply` | `apply` | Function application in Space domain |
| REPL | `cb()` in engine.ts | Read input, eval, print result |

### Why Homoiconicity Dissolves the Point/Attribute Distinction

In this system, there is **one data structure: the Space**. Everything is a Space:

- A "point" is a Space (a node with children)
- An "attribute" is a Space (a child that represents a spectrum value)
- A "program" is a Space (a quoted structure that can be eval'd)
- A "mine map" is a Space (the compiled output of a kernel)
- A "kernel" is a Space (a tree of slots to be filled)

The distinction between "adding a point" and "adding an attribute" does not exist. There is only **`add`** — which adds a child Space to a parent Space. From the parent's perspective, that child is a spectrum value. From the child's perspective, it has its own interior (which you can `bloom` into).

This is why homoiconicity must be the foundation, not an optional layer. Without it, the system collapses into "nodes with properties" — the OOP flattening that makes point/attribute look like different things.

### Mine: The Compilation Target

**All Crystal Ball programs compile to verified points in mineSpace.**

#### Definition

> **mineSpace** is any space whose coordinates are encoded by real numbers and decode to Crystal Ball kernels, where at least one kernel has been locked (at least one verified point exists).

There is ONE mineSpace. Not a mine space per kernel. Not a hierarchy of mine spaces. ONE.

#### How It Works

A mineSpace exists because a kernel is an ontological object that exists as a configuration of sequences of addresses inside of a coordinate space decoded a specific way. A mineSpace is a space where there is a volume and within that you can decode some of it.

Because you know everything about what you can decode already (it is instantly decodable through a small operation to cross-reference what is available within the kernel's configuration space), you can verify that you do indeed have an address in the mineSpace. You don't know the top-level label of the mineSpace — you're inside it, looking out.

Because of that, you can explore FROM that origin — because that origin is the exact decoding of a kernel in that mineSpace back to your reality and what you can already fully represent to yourself.

Concretely:

1. There exists a mineSpace with an origin 0
2. Your locked kernel decodes to a **specific point** — a real number whose digit expansion is a CB coordinate string
3. That point is verified because you generated it — it decodes to something real you already know
4. Change one digit slightly → another valid selection → that nearby point is ALSO real IF the kernel validates it
5. These nearby real points are "generable but unsaid" — valid variants you haven't explicitly made
6. Every time you bloom what the kernel is made of (add more internal structure without changing the core), you add more stuff you can know about into the mineSpace
7. When two points' trajectories connect, you unlock an entire chain as a REGION
8. Eventually, one of these points is the one you MEANT to go to
9. When you find it, you goldenize the kernel → the entailment of that operation IS the **solutionSpace** — a mineSpace where every minable point is exactly a variant of your goldenized solution

#### Higher Orders Are INSIDE mineSpace, Not Above It

The mineSpace contains its own orders. This is because a real number has infinite decimal digits. Each digit position is a CB coordinate token (0-9). The "orders" of the mineSpace are how many digits deep you're reading:

- 1 digit precision → coarse view (7 possible selections)
- 2 digits → finer (selections within selections)
- 10 digits → extremely specific configuration
- ∞ digits → the exact point

Higher orders aren't separate spaces. They're **deeper precision** in the same real number. The mineSpace contains its own orders because the reals contain arbitrary depth in their digit expansion.

Mathematical precedents:
- **Scott domains**: `D ≅ [D → D]` — a space isomorphic to its own function space. Foundation of lambda calculus.
- **Cantor space** (2^ω): one space encoding all possible sequences. All computational complexity levels live inside it.
- **Von Neumann universe** (V): one space containing all sets, including sets of sets. The cumulative hierarchy is INSIDE V.

The pattern is known: **a sufficiently rich space doesn't need external higher orders because it encodes them internally.**

### Dot vs Drill — Two Axes of the Same Mechanic

Both dot and drill mean "enter a produced space." But they operate on different axes:

| | Dot (`.`) | Drill (`8`) |
|---|---|---|
| **Direction** | Horizontal — the kernel's production chain | Vertical — a node's interior subspace |
| **Meaning** | "This space PRODUCES the next one in this kernel" | "Open this node's attributes AS a space inline" |
| **Context** | Declaring/building a kernel's structure | Exploring within a single chain step |
| **Example** | `Intro.Body1.Body2.Conclusion` (4-step production chain) | `1238...88` (enter node 3's interior, work, exit) |

Both are "enter the produced space" but at different levels of the hierarchy. Dot moves along the kernel's chain. Drill enters a node's interior.

**Open question:** For mineSpace coordinates to be pure real numbers, dot must be encoded as a digit. Dot and drill are mechanically similar (enter a produced space) but contextually different (kernel chain step vs node interior). This encoding question needs resolution.

### Why This Requires Homoiconicity

The entire structure only works because everything is a Space:
- A locked kernel is a Space → it can be a point in mineSpace
- A mineSpace is a Space → it can be scried, bloomed, mined
- A solutionSpace is a Space → it can be composed, quoted, evaluated

Without homoiconicity, a mine result would be a flat JSON output that cannot be composed. The reals-encoding-CB-tokens trick only works if what the tokens decode to (Spaces) is the same kind of thing that can BE encoded (Spaces). Code = Data = Space.

**Homoiconicity is not a nice-to-have. It is the mechanism that makes mineSpace self-containing.**

### The Complete Crystal Ball Compilation Pipeline

```
BASE (index.ts)                           ← Everything is a Space
    ↓ used by
HOMOICONIC (homoiconic.ts)                ← eval/quote/apply on Spaces
    ↓ used by
ENGINE (engine.ts)                        ← REPL: reads commands, evals, returns Spaces
    ↓ produces
KERNEL (user-created Space with slots)    ← The "source code" — an ontology-preserving functor
    ↓ resolved via
INFINITE KERNEL CYCLE                     ← scry → bloom → add → lock → repeat
    ↓ when fully locked, produces
VERIFIED POINT IN MINESPACE              ← A real number that decodes to this kernel
    ↓ from that origin, probe neighbors
MINESPACE EXPLORATION                     ← k-NN points that also decode to valid kernels
    ↓ when the target point is found
GOLDENIZE → SOLUTION SPACE               ← mineSpace where every point is a variant of the solution
```

### mineSpace Types (By Restriction)

Not all views of mineSpace are equal. Different restrictions produce different types:

| Type | Restriction | What every point decodes to | Status |
|------|------------|---------------------------|--------|
| **Configuration mineSpace** | One locked kernel | A valid coordinate path in that kernel's structure | **MVP — build this first** |
| **Solution mineSpace** | One goldenized kernel | A variant of that specific proven solution | Known, comes after configuration |
| **Pattern-restricted** | A class of kernels sharing a pattern (e.g. "5 paragraph essay") | ANY valid kernel matching the pattern | Intuited, not yet defined |
| **Unrestricted** | None — the full Scott domain | Any valid CB coordinate | Theoretical |

The configuration mineSpace is the implementation target. The others will emerge once we can compute and visualize the first.

### mineSpace as the Scott Domain of LLM-Generable Structures

The mineSpace is the Scott domain D ≅ [D → D] of everything an LLM can generate, equipped with CB coordinates:

- **D** = everything an LLM can generate (text, code, structures, kernels)
- **[D → D]** = all transformations of generated things (prompts that transform one output into another)
- **D ≅ [D → D]** because a transformation IS text — the LLM can generate its own transformation functions

Crystal Ball gives this Scott domain an **addressing scheme** (the 0-9 coordinate system). Instead of the domain being an amorphous blob of "everything an LLM could say," CB imposes structure that lets you ADDRESS specific points and NAVIGATE between them.

- The **kernel** is a finite description of a region in the domain
- **Locking** a kernel = verifying a point exists
- The **heatmap** = a local chart near your verified point
- **Orders of mineSpace** = D ≅ [D → D] — the domain contains functions on itself, which are points, which are inputs to other functions, all inside one space

---

## 11. Why Crystal Ball Is Computationally Tractable (WIP)

> **This section is a work in progress.** The ideas are directionally correct but the formal argument is still being refined.

### Coordinates Are Addresses, Not Semantics

The coordinate system (0/1-7/8/88/9) is an **addressing scheme**, not a semantic language. Like assembly encoding binary, the digits don't carry meaning — they carry LOCATION. Each digit says "go here" within an already-built structure. The semantics are baked into the space's topology by whoever built the kernel.

This is a fundamental separation:

| | Traditional Search | Crystal Ball |
|---|---|---|
| **What expands combinatorially** | The content itself (tokens, symbols) | Addresses into pre-built structures |
| **What carries semantics** | Every generated token | The space structure (built by classifier) |
| **Generator** | Random/exhaustive token emission | Tree traversal (which paths exist?) |
| **Complexity scales with** | Raw possibility space (e.g. 26^n for text) | Tree depth × breadth of the kernel |

### Mine Is an Enumerator, Not a Generator

Because coordinates are semantic-free, mine doesn't need a semantic generator to produce the combinatorial explosion. Mine just walks the tree and asks: **does this address exist?** That's a structural question, not a semantic one.

Shakespeare analogy:
- **Brute force:** Hire an infinite number of monkeys to type random text. Check all outputs for Shakespeare. Cost: O(alphabet^length).
- **Crystal Ball:** Use "extremely high-order monkeys" (LLMs/classifiers) to **identify patterns and build structure** — the acts, the scenes, the characters, the thematic arcs. Each pattern becomes a node. Each node can reference (via drill/8) arbitrarily complex substructure. Then mine just enumerates the valid paths: "Act 1 → Scene 3 → Character 2 → Line 15" — addresses, not text.

The monkeys don't generate tokens. They **classify** — they find the boundaries of the combinatorial explosion, name them, and structure them into a kernel. The enumeration of what's inside those boundaries is mechanical.

### Each Coordinate Digit Can Resolve to Unbounded Complexity

This is the scaling property of the tower. When you select child 3 at level 2 (coordinate `1.3`), child 3 might be:
- A single label ("red")
- A locked kernel with 50 nodes
- A goldenized mine space with 10,000 valid paths
- A Level 3 mine-of-mines referencing hundreds of solved subspaces

The coordinate doesn't know or care. It just says "go to child 3." The drill mechanic (8) enters the subspace, which is itself a Space, navigable by the same 0/1-7/8/88/9 mechanics.

So a single digit in a coordinate can resolve to something of **arbitrarily high complexity** — but the mine enumerator at the current level doesn't unpack that. It only enumerates addresses at ITS level. The complexity is contained within the drilled subspaces, which were already solved at a lower level of the tower.

### The Modulo System as Assembly

The restriction to digits 0-7 (with 9=wrap for extension) works like a modular arithmetic on natural numbers — it constrains what each digit position can represent, creating an "instruction set" for navigation rather than content. Like how assembly doesn't encode meaning in opcodes (MOV, ADD, JMP are structural), the coordinate digits don't encode meaning in their values (1-7 are positional selections, 8 is enter, 88 is exit, 9 is extend range).

This means the coordinate language is **fixed** — it doesn't grow with the complexity of the content. A Level 0 kernel and a Level 5 kernel-of-kernels-of-kernels are navigated with the exact same 10 symbols (0-9). The complexity goes into the STRUCTURE (deeper trees, more subspaces), not into the LANGUAGE.

### Open Questions (WIP)

- What's the formal complexity class of mine enumeration on a CB kernel?
- How does drill depth affect enumeration cost? (Each drill enters a subspace that could itself have drills)
- What's the relationship between kernel "heat" (unfilled slots) and the size of the mine output?
- How do we formally bound the tower's combinatorial expansion at each level?
- What's the connection between this and partial evaluation / supercompilation?

---

## Carton Concepts
- `Crystal_Ball_Infinite_Kernel_Cycle`
- `Crystal_Ball_Viz_Projection_Tuple`
- `Shield_Membrane_Navigation_Pattern`
- `Instance_To_Class_Promotion_Cycle`
- `Crystal_Ball_As_Substrate`
- `Fibration_Structure_Linguistic_Space`
- `Shield_Dynamics_And_Egregore_Compiler`
- `Gen_Sama`
- `Gen_Sama_Lotus_Equivalence`
- `HIEL_Thermodynamics`
- `Crystal_Ball_Homoiconic_Compilation_Pipeline`
- `Mine_As_Compilation_Target`
- `Crystal_Ball_Futamura_Tower`
- `Coordinate_Semantic_Freedom`
- `MineSpace_Scott_Domain`
- `MineSpace_Type_Taxonomy`
- `Dot_Drill_Duality`
- `Kernel_As_Ontology_Preserving_Functor`


