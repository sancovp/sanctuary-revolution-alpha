# Crystal Ball Engine — Learning Notes

> Written by Antigravity, exploring the Crystal Ball MCP server directly.
> Date: 2026-02-18
> Method: Using Crystal Ball to learn Crystal Ball (self-referential ontology!)

---

## 1. What Is Crystal Ball?

Crystal Ball is a **multi-order coordinate ontology engine**. It lets you define *things* as *spaces*, where each depth level in the coordinate tree represents a different **ontological order** — properties, subclasses, products, or any semantic layer you choose.

A Space IS the definition of a Thing. Its coordinate system is not just addressing — it's **navigating through layers of meaning**.

---

## 2. The Core Insight: Depth = Ontological Order

Every node in a Crystal Ball space lives at a depth. Each depth level represents a different **order** of reality for that thing:

```
root.{Order 1: Properties}.{Order 2: Subclasses}.{...}.{Order N: Products}
```

### Order 1: Properties (What it IS)
The **first layer of children** under root are the **properties** of the thing. These are its spatial dimensions — the axes along which the thing varies.

All properties live on ONE level. They are siblings. This is the fundamental definition of the thing.

### Order 2+: User-Defined (What refines/classifies it)
Subsequent layers are defined by the space designer. Common patterns:
- **Subclasses** — what kinds of this property exist
- **Instances** — concrete examples
- **Refinements** — further specification

### Final Order: Products (What it MAKES)
The deepest layer represents what the thing ultimately produces or generates.

### Example: Cuisine Space

```
root (Cuisine)
├── 1: flavor          ← Order 1: Properties of Cuisine
│   ├── 1.1: sweet     ← Order 2: Subclasses of flavor
│   │   ├── 1.1.1: honey_cake    ← Order 3: Products
│   │   └── 1.1.2: fruit_tart
│   └── 1.2: savory
│       ├── 1.2.1: roast
│       └── 1.2.2: stew
├── 2: technique       ← Another property
│   ├── 2.1: grilling  ← Subclass of technique
│   └── 2.2: braising
└── 3: ingredient
    ├── 3.1: protein
    └── 3.2: vegetable
```

### Example: HueSpectrum (Pre-existing)

```
root (HueSpectrum)
├── 1: hue_0     ← Order 1: Properties (each hue position IS a property of the color space)
├── 2: hue_30        Each has attrs: hue=[N], family=[warm,cool,neutral]
├── 3: hue_60        The attributes are the SPECTRA — the valid values for that property
├── ...
└── 12: hue_330
```

Here the space only has ONE order — a flat property space defining 12 hue positions, each with its own spectrum of valid values.

---

## 3. The Superposition Operator: `0`

`0` at any coordinate level means **"ALL members of this order."** This is the key mechanic that makes Crystal Ball more than a tree navigator.

```
scry "0"       → all properties (all Order 1 members)
scry "1.0"     → all subclasses of property 1 (all Order 2 under property 1)
scry "0.0"     → all subclasses of ALL properties (cross-cutting across Order 1)
scry "0.0.0"   → all products of all subclasses of all properties (full expansion)
```

**Superposition gives you cross-cutting queries through ontological orders.** You can ask "what are ALL the products across ALL subclasses across ALL properties?" with a single coordinate: `0.0.0`.

This is like a wildcard/glob, but semantically richer — each `0` crosses one ontological order.

---

## 4. Core Primitives

| Primitive | What it is |
|-----------|-----------|
| **Space** | A named definition of a Thing. Has a root node and a name. |
| **Node** | A point at a specific order level. Has id, label, children, attributes, depth. |
| **Attribute** | A property's valid values — its *spectrum*. Can have a default. |
| **Coordinate** | A dot-separated path through ontological orders. `0` = superposition. |

### Coordinate ↔ Node ID Translation (Important!)
- **Coordinates** are 1-indexed: `1`, `1.3`, `2.1.4`
- **Node IDs** are 0-indexed: `root.0`, `root.0.2`, `root.1.0.3`
- Coordinate `1` → node `root.0` (pathDigits `[1]`)
- Coordinate `1.3` → node `root.0.2` (pathDigits `[1, 3]`)
- Coordinate `0` → superposition (ALL siblings at that depth)

---

## 5. What Bloom Really Does

Bloom is NOT "create N copies." Bloom is: **"this thing has N properties/slots at this order — define them."**

```
bloom(coordinate="1", label="aspect", count=3)
```

This says: "The thing at coordinate 1 has 3 aspects. Here are the slots to define them."

Result:
```
node_at_1
├── aspect_1   ← slot for defining aspect 1
├── aspect_2   ← slot for defining aspect 2
└── aspect_3   ← slot for defining aspect 3
```

Each slot is a child at the NEXT ontological order. You then:
1. Rename/relabel them to meaningful names
2. Add attributes (spectra) to define their valid values
3. Bloom THEM to open up the next order deeper

### Bloom = Opening a New Order
- Bloom at depth 0 → creates **properties** (Order 1)
- Bloom at depth 1 → creates **subclasses** (Order 2)
- Bloom at depth 2 → creates **products** (Order 3)
- Each bloom expands the definition space one order deeper

---

## 6. Operations (MCP Commands)

| Command | Parameters | What it does |
|---------|-----------|-------------|
| `list_spaces` | none | Lists all space names |
| `create_space` | `{name}` | Creates a new Thing definition |
| `get_space` | `{space}` | Returns full space structure |
| `add_point` | `{space, parent_coordinate, label}` | Adds a node at a specific order level |
| `add_attribute` | `{space, coordinate, name, spectrum, default}` | Adds a spectrum to a node |
| `scry` | `{space, coordinate, included?}` | Navigates orders via coordinate |
| `bloom` | `{space, coordinate, label, count}` | Opens N slots at the next order |
| `resolve` | `{space, coordinate}` | Alias for scry |

### Parameter Aliases (Both Forms Accepted)
The MCP accepts user-friendly names and translates them to the web server's internal names:

| You can say | Server receives | Command |
|-------------|----------------|---------|
| `parent_coordinate` | `parentId` | add_point |
| `label` | `slotLabel` | bloom |
| `coordinate` | `nodeId` | add_attribute |
| `default` | `defaultValue` | add_attribute |
| `included` | `includeNodeIds` | scry |

**Note:** `parent_coordinate` and `nodeId` expect **node IDs** (like `"root.0"`), not coordinates (like `"1"`).

---

## 7. Scry Semantics

Scry resolves a coordinate through the order hierarchy:

```
scry "1"       → [CoreConcepts]              — single node at Order 1
scry "1.1"     → [point_1]                   — single node at Order 2 under property 1
scry "1.0"     → [point_1, point_2, ...]     — SUPERPOSITION: all of Order 2 under property 1
scry "0"       → [all root children]          — SUPERPOSITION: all of Order 1
scry "0.0"     → [all grandchildren]          — cross-cut: all of Order 2 across all of Order 1
```

### How Scry Works
1. Parse coordinate into dot-separated digits
2. Start at root
3. For each digit:
   - `0` → expand to ALL children at this order
   - `N > 0` → navigate to child at index `N-1`
4. Return all resolved nodes

---

## 8. Data Model

```
Space (= Thing Definition)
  └── name: string
  └── rootId: "root"
  └── locked: boolean
  └── nodes: Map<NodeId, Node>

Node (= Point at an Ontological Order)
  └── id: string (e.g. "root.0.1")           — 0-indexed
  └── label: string
  └── children: NodeId[]
  └── slotCount: number                       — bloom-created slot count
  └── locked: boolean
  └── attributes: Map<string, Attribute>
  └── subspace?: CrystalBall                  — nested space (composition)
  └── parentId: NodeId | null
  └── depth: number                           — = which ontological order
  └── pathDigits: number[]                    — 1-indexed coordinate

Attribute (= Spectrum of Valid Values)
  └── name: string
  └── spectrum: (string | number | boolean)[]
  └── defaultValue?: string | number | boolean
```

---

## 9. Design Insights

### Crystal Ball vs. Other Knowledge Systems

| System | Navigates by | Structure |
|--------|-------------|-----------|
| Knowledge Graph | relationship type | flat graph |
| File System | path segments | tree |
| SQL | table + column | relational |
| **Crystal Ball** | **ontological orders** | **multi-order tree** |

Crystal Ball's unique power: **each depth level has semantic meaning defined by the designer.** A coordinate isn't just an address — it's a path through layers of meaning.

### The `0` Superposition as Cross-Cutting Query
Traditional systems need joins/traversals to ask "give me all X across all Y." Crystal Ball does it with one coordinate: `0.0`. Each `0` is a semantic wildcard across one ontological order.

### Bloom as Space-Opening
Bloom isn't data insertion. It's **ontological expansion** — declaring "this thing has N dimensions at the next order." The act of blooming IS the act of defining.

### Why "Crystal Ball"?
- You don't search — you **address**
- You don't query — you **scry** (divine/resolve)
- The knowledge space has **geometry** (orders), not just topology (edges)
- Looking into the crystal ball reveals the structure of the thing itself

---

## 10. Commands Quick Reference

```bash
# List all spaces
crystal_ball cmd=list_spaces

# Create a Thing
crystal_ball cmd=create_space body={"name": "MyConcept"}

# Get full Thing definition
crystal_ball cmd=get_space body={"space": "MyConcept"}

# Add a property (Order 1)
crystal_ball cmd=add_point body={"space": "MyConcept", "parent_coordinate": "root", "label": "Property1"}

# Open up subclasses (Order 2) under property 1
crystal_ball cmd=bloom body={"space": "MyConcept", "coordinate": "1", "label": "subclass", "count": 3}

# Navigate: get property 1
crystal_ball cmd=scry body={"space": "MyConcept", "coordinate": "1"}

# Navigate: get ALL subclasses of property 1
crystal_ball cmd=scry body={"space": "MyConcept", "coordinate": "1.0"}

# Navigate: get ALL subclasses of ALL properties (cross-cut)
crystal_ball cmd=scry body={"space": "MyConcept", "coordinate": "0.0"}

# Add attribute spectrum to a node (use nodeId!)
crystal_ball cmd=add_attribute body={"space": "MyConcept", "coordinate": "root.0", "name": "intensity", "spectrum": ["low", "medium", "high"], "default": "medium"}
```

---

## 11. Open Questions

1. **Can coordinates be used in `parent_coordinate`?** Currently requires node IDs like `"root.0"`. Could the server resolve coordinate `"1"` to `"root.0"` automatically?
2. **What does `included` actually do in scry?** Tested but saw no effect. May compose a coordinate FROM node IDs.
3. **What is `composedCoordinate`?** Scry returns this as empty string. Likely related to `included`.
4. **What is `locked` for?** Both spaces and nodes have it. Presumably prevents modification.
5. **How do subspaces interact with coordinates?** Nodes can hold a nested `CrystalBall` — does scry traverse into them?
6. **What are the kernel's higher-order operations?** The source has `explore()`, `emergentGenerate()`, `neighbors()`, `TotalSpace` — how do these compose?
