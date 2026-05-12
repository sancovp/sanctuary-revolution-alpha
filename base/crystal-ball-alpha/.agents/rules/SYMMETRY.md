# Crystal Ball — Symmetry Dynamics

> **Purpose:** Explain how Crystal Ball works through its symmetries, so agents
> stop breaking the duality between "attribute on a node" and "child in a space."

---

## The Core Duality

In traditional data modeling, an **attribute** is something that sits ON a node:

```
Node "Tweet"
  ├── attribute: tone = [formal, casual, playful]
  ├── attribute: length = [short, long]
  └── children: [Opener, Body, CTA]
```

This creates a broken asymmetry: children are addressable by coordinate, attributes are not.
Children are geometry. Attributes are decoration. Two ontologies stapled together.

**Crystal Ball rejects this.** In CB, everything is a space. There is only ONE structure:

```
Node "Tweet"  (a superposition)
  └── children = spectrum options:
        ├── 1: Opener     (a subspace — bloom into it)
        ├── 2: Body       (a subspace — bloom into it)
        └── 3: CTA        (a subspace — bloom into it)
```

And "Opener" itself is:

```
Node "Opener"  (a superposition)
  └── children = spectrum options:
        ├── 1: formal
        ├── 2: casual
        └── 3: playful
```

**There is no separate "tone" attribute.** The children of "Opener" ARE its spectrum.
The "tone" concept is the SPACE ITSELF — the named subspace you bloom into.

---

## The Bra-Ket Symmetry: ⟨A|B⟩ and ⟨B|A⟩

The confusion arises from TWO valid perspectives on the same structure:

### ⟨A|B⟩ — Looking DOWN from the parent

From "Tweet" looking at its child "Opener":
- "Opener" is a **slot** in Tweet's coordinate space
- Selecting Opener (coordinate segment `1`) is a spectrum selection
- Opener is one of several sibling options at this level
- Opener is an **attribute of Tweet** in the sense that it characterizes Tweet

### ⟨B|A⟩ — Looking UP from the child

From inside "Opener" looking at its own children:
- "formal", "casual", "playful" are the spectrum options
- They are the interior structure of Opener
- Selecting one (coordinate `1.1` = Tweet→Opener→formal) collapses the superposition

**These are the SAME operation viewed from different levels.**

| Perspective | What you see | What "add" means |
|-------------|-------------|-----------------|
| ⟨A\|B⟩ Parent looking at child | Child is a spectrum value | Adding a spectrum option to parent |
| ⟨B\|A⟩ Inside the child space | Children are the interior | Adding a node to this space |

**Bloom is the operator that swaps between these views.**
- Bloom INTO a node: transition from ⟨A|B⟩ to ⟨B|A⟩
- Navigate BACK: transition from ⟨B|A⟩ to ⟨A|B⟩

---

## Why "Add" is One Operation

When you bloom into a node and add a child, you are simultaneously:
1. Adding an interior node to the current space (the ⟨B|A⟩ view)
2. Adding a spectrum value to the parent's slot (the ⟨A|B⟩ view)

These are not two operations. They are one operation observed from two frames.

**The traditional model breaks this by separating them:**
- `add_point` = add a child (⟨B|A⟩ only)
- `add_attribute` = add a spectrum value (⟨A|B⟩ only, but as metadata, not geometry)

This breaks the symmetry. The attribute's values become invisible to coordinates.
They exist in a parallel universe that scry can't see and mine has to read separately.

**The correct model:** `add` is one operation. It creates a child node, which IS a spectrum
value from the parent's perspective. No separate attributes map. No parallel universe.

---

## Coordinate Traversal AS Symmetry Collapse

A coordinate like `1.2.3` is a sequence of symmetry collapses:

```
Segment 1: At the root space, select child 1   → collapses root superposition
Segment 2: In child 1's subspace, select child 2  → collapses that superposition
Segment 3: In child 2's subspace, select child 3  → collapses again
```

Each segment is a ⟨A|B⟩ → specific |B⟩ selection. The coordinate IS the sequence of 
symmetry-breaking choices through the space.

**Special segments:**
- `0` = don't collapse — stay in superposition (the ⟨A| without picking |B⟩)
- `8`, `9` = mechanical operations (not spectrum selections)

---

## Scry = Observe Without Entering

Scry reads the coordinate WITHOUT changing perspective. You stay in ⟨A|B⟩ — you see
what's at a coordinate from the outside. You see the resolved node, its children
(as spectrum options), and how many levels remain unresolved.

## Bloom = Enter = Change Perspective

Bloom switches you FROM ⟨A|B⟩ TO ⟨B|A⟩. Now you're inside. The children are no
longer "spectrum options of the parent" — they're "the nodes in this space." Same
data, different frame.

## Mine = Enumerate All Paths

Mine should traverse ALL possible coordinate paths through the child tree. Each
complete path (every segment resolved, no zeros) is a fully-collapsed configuration.
The set of all such paths IS the configuration space.

**This means mine traverses the same tree that scry does.** It doesn't need a
separate `attributes` map or `instantiate()` function reading from a different
data structure. It just exhaustively explores coordinate paths.

---

## The Symmetry Operations (Summary)

| Operation | Symmetry meaning |
|-----------|-----------------|
| **Scry** | Observe ⟨A\|B⟩ — read the dual without collapsing |
| **Bloom** | Enter: ⟨A\|B⟩ → ⟨B\|A⟩ — switch to interior frame |
| **Add** | Create \|B⟩ — add a basis vector to the current space |
| **Lock** | Fix ⟨A\|B⟩ = specific value — irreversible collapse |
| **Freeze** | Pre-lock: mark for later collapse |
| **Mine** | Enumerate all possible ⟨A\|B₁⟩⟨B₁\|C₁⟩⟨C₁\|...⟩ — full path census |
| **Kernel** | The set of slots being simultaneously collapsed |

---

## Why the Implementation Was Wrong

The `CBNode` type had:

```typescript
interface CBNode {
    children: NodeId[];              // ← the geometry (addressable)
    attributes: Map<string, Attribute>;  // ← the decoration (NOT addressable)
}
```

This is the ⟨A|B⟩ ≠ ⟨B|A⟩ bug. It says "children are geometry but attributes are
metadata." In CB, there is no such distinction. Everything is a child. Everything
is geometry. Everything is addressable by coordinate.

The `Attribute` type with its `spectrum: string[]` is just a node with children
whose labels are the spectrum values. The `attributes` Map is a shadow copy of
what the child tree already does — except invisible to scry and coordinate resolution.

**Fix:** Remove `attributes` from CBNode. If a node needs named dimensions (like "tone"),
those are child nodes you bloom into. The values are their children. All nodes, all the
way down. Mine walks the same tree scry walks.
