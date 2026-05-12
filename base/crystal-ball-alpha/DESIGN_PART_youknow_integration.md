# Crystal Ball ↔ YOUKNOW ↔ LLM Suggest Integration

## Architecture: YOUKNOW as Idea Generator for CB

YOUKNOW is NOT a gating validator. It is a **continuous idea generator**.

Every time you feed it a statement, it tells you everything that's
missing — and every missing thing IS an idea for a new CB node.

```
┌─────────────────────────────────────────────────────────────┐
│  CRYSTAL BALL (CB)                                          │
│  Structural engine — symmetries, orbits, spectra, kernels   │
│  Consumes: ideas (labels, relationships, strata hints)       │
│  Produces: tree structure + symmetry analysis                │
│  Language: TypeScript                                        │
└──────────────────┬──────────────────────────────────────────┘
                   │ current labels                    ▲
                   ▼                                   │ new nodes
┌─────────────────────────────────────────────────────────────┐
│  YOUKNOW (YK)                                               │
│  Ontology compiler — ONE-SHOT, STATELESS                     │
│                                                              │
│  Input:  "X is_a Y"                                          │
│  Output: "Wrong because Z, W, V are missing"                 │
│                                                              │
│  EVERY "missing" IS an idea:                                 │
│   - Broken is_a chain  → new parent node for CB              │
│   - Missing part_of    → new dot/slot for CB                 │
│   - Missing MSC        → new classification node             │
│   - Missing mapsTo     → new cross-reference                 │
│   - llm_suggest string → ready-made prompt for LLM           │
│   - Y-mesh activation  → which stratum needs work            │
│                                                              │
│  YOUKNOW generates ideas ALL THE TIME.                       │
│  The more you feed it, the more ideas it gives back.         │
└──────────────────┬──────────────────────────────────────────┘
                   │ ideas (broken chains = suggestions)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  LLM SUGGEST (Swarm Agent)                                   │
│  Reads YOUKNOW's ideas → materializes them as CB actions     │
│                                                              │
│  YOUKNOW says "X is_a ? — chain breaks"                      │
│  LLM says "X is_a Anime_Domain" → feeds back to YOUKNOW     │
│  YOUKNOW says "Now Anime_Domain is_a ? — chain breaks"       │
│  LLM says "Anime_Domain is_a Narrative" → feeds back         │
│  YOUKNOW says "OK" → that chain closed                       │
│                                                              │
│  Every "OK" and every "Wrong" both produce CB output.        │
│  OK = lock this. Wrong = here are 5 more things to build.    │
└─────────────────────────────────────────────────────────────┘
```

The flow is **generative, not gating**. YOUKNOW never blocks anything.
It just keeps saying "and you also need..." which gives CB more to build.
The system GROWS by feeding YOUKNOW's output back as input.

## How Ideas Become CB Nodes

YOUKNOW's compile packet is a treasure trove of CB actions:

```python
# Feed it one statement...
result = youknow("Spiral_Power is_a GurrenLagann_Concept")

# ...get back MANY ideas:
result = {
  "blocking": [
    "GurrenLagann_Concept is_a ?",     # → CB: add parent node
    "ABCD missing: mapsTo",            # → CB: add cross-reference node  
    "ABCD missing: analogicalPattern", # → CB: add pattern node
  ],
  "llm_suggest": "Try: GurrenLagann_Concept is_a Anime_Ontology",
  "ses_report": {
    "max_typed_depth": 1,              # → CB: this is at stratum 1-2
    "first_arbitrary_string_depth": 2  # → CB: stratum 3+ is free text
  },
  "diagnostics": {
    "controller": {
      "target_layer": "y4",            # → CB: map to instance stratum
      "activation": 0.25,             # → CB: bloom phase
    }
  }
}
# One input → 5+ output ideas for CB to create as nodes
```

## The Generative Loop

```
CB label exists → feed to YOUKNOW → get back ideas → ideas become CB nodes
                                                         ↓
                                          feed NEW labels to YOUKNOW
                                                         ↓
                                                    more ideas...
                                                         ↓
                                              (ideas dry up = convergence)
```

When YOUKNOW returns "OK" for everything — no more ideas — the tower converges.
That IS the fixed point. Not because we gated anything, but because there's
nothing left to generate.

## How CB Operations Become Ontological Claims (Post-Processing)

There is only `cb()`. No separate YOUKNOW call. The MCP layer IS the bridge:

```
crystal_ball(input)
  │
  ├─ 1. Send to CB engine (TypeScript via HTTP)
  │     CB does its thing: bloom, fill, lock, mine
  │     Returns CBResponse with view + data + phase
  │
  ├─ 2. POST-PROCESS: _extract_ontological_claims(cb_result)
  │     Reads what CB just did and generates UARL statements:
  │
  │     bloom "Action" under "Movies"  →  "Action is_a Movies"
  │     fill slot with value           →  "value part_of Space"
  │     mine space                     →  "space is_a CB_MineSpace"
  │     lock space                     →  (future: validate all nodes)
  │
  ├─ 3. Auto-compile each claim via _compile_youknow()
  │     admitted?  →  that coordinate has confirmed semantics
  │     soup?      →  ideas list says what's missing for that position
  │
  └─ 4. Return unified response:
        {
          "view": "...",           // CB's structural view
          "data": {...},           // CB's tree data
          "phase": "bloom",        // CB's lifecycle phase
          "youknow": [             // YOUKNOW's semantic feedback
            {
              "admitted": false,
              "statement": "Action is_a Movies",
              "ideas": [{"type": "broken_chain", "detail": "Movies is_a ?"}]
            }
          ]
        }
```

**Key insight**: YOUKNOW never blocks CB. CB does its structural operation
regardless. YOUKNOW's feedback rides alongside — enriching the response
with semantic status. The "ideas" tell the LLM what to build next.

**The coordinate IS the ontological address**: When CB returns node "Action"
at coordinate `1.3`, that coordinate maps to a real number via `coordToReal()`.
That same real number IS the position in the ontology. The YOUKNOW feedback
tells you what's semantically valid or missing at that exact position.

## Syntax → Semantics: Edges, Hyperedges, Supernodes

CB's tree is **syntax** — positions in a DAG. YOUKNOW **converts** those
positions into **typed semantic structures**:

### Edge = parent → child = `is_a`

Every parent-child relationship in the CB tree IS a UARL `is_a` edge.
When you bloom "Action" under "Movies", that IS `Action is_a Movies`.

### Hyperedge = parent node AS typed container

Every parent node IS a **typed hyperedge** — it groups all its children
as a typed collection. The stratum determines the type:

```
  Movies [stratum: universal]        HYPEREDGE type=CB_Universal
    ├─ Action                        groups {Action, Comedy, Drama}
    ├─ Comedy                        meaning: ALL must satisfy Movies'
    └─ Drama                         universal requirements

  Action [stratum: subclass]         HYPEREDGE type=CB_Subclass
    ├─ Thriller                      groups {Thriller, MA, Heist}
    ├─ Martial_Arts                  meaning: conditional requirements
    └─ Heist                         distinguishing subtypes
```

Stratum typing:
- **universal** → all instances must satisfy this (∀-quantified)
- **subclass** → conditional distinctions (∃-typed)
- **instance** → concrete values (fully determined)
- **instance_universal** → instance became new class (recursion!)
- **instance_subtype** → subtypes within instance-class
- **instance_instance** → solution space (the thing itself)

### Supernode = parent viewed from outside

A supernode represents the **entire collapsed subgraph**. When another
space references "Movies", it references the whole typed hierarchy —
not just one node. The supernode IS the hyperedge parent.

### YOUKNOW derivation maps to supernode completeness

- L0 (soup) → supernode is just a name
- L1 (embodies) → has named children (slots)
- L2 (manifests) → children have types
- L3 (reifies) → structure is concrete
- L4 (promoted) → traces to Cat_of_Cat
- L5 (produces) → the hyperedge generates something
- L6 (programs) → IS the codegen

When all supernodes reach L6 → the tower converges → fixed point.

## Everything Goes In — Filtering Is Views

**LLM outputs ALWAYS add to CB. There is no reason to reject anything.**

Why? Because unselected options DON'T MATTER in the coordinate space.
If they're there and nobody selects them, they don't affect the computation.
But if someone DOES select them later, the data is already there.

### Blacklist / Whitelist = Views, Not Deletions

```
Space "Movies"
├── Action          ← included (default view)
├── Comedy          ← included
├── Horror          ← BLACKLISTED (user doesn't like it)
├── Romance         ← included
└── Documentary     ← included

View: "My Preferences"    = exclude blacklist → 4 items, mine those
View: "What I Avoid"      = blacklist only → 1 item, mine THAT too
View: "Everything"        = no filter → 5 items, full computation
View: "Curated"           = whitelist only [Action, Documentary]
```

The underlying space has ALL the nodes. Views are filters on:
- **What to show** (visualization)
- **What to include in kernels** (computation)
- **What to mine** (symmetry analysis)

### View Modes

| Mode | Description | Use |
|---|---|---|
| `default` | Show everything | Full space exploration |
| `exclude_blacklist` | Hide blacklisted | User preference view |
| `whitelist_only` | Show only whitelisted | Curated/focused view |
| `blacklist_only` | Show only blacklisted | Mine your rejects |

### Why "Mine Your Blacklist" Matters

The blacklist IS data. It has structure. It has symmetries.
Mining your blacklist tells you about the SHAPE of what you rejected —
which is the negative space of your ontology. That's information.

```
Blacklist orbits: {Horror, Thriller} are S2 — they're equivalent in why you reject them
Fixed point: Torture_Porn — unique rejection, no symmetry partner
→ Tells you: you reject SUSPENSE-VIOLENCE as a category, plus one outlier
```

### Implementation: Node Tags, Not Deletion

```typescript
interface CrystalBallNode {
  // ... existing fields ...
  tags?: Set<string>;    // e.g. "blacklist", "favorites", "reviewed"
}

interface SpaceView {
  name: string;
  include?: Set<string>;  // whitelist tags — only show nodes with these
  exclude?: Set<string>;  // blacklist tags — hide nodes with these
}
```

Mining runs on the VIEW, not the raw space. Same `mineSpace()` function,
just pre-filtered by the view. Different views of the same space produce
different symmetry groups — and THAT tells you something about the observer.

## Stratum Cross-Reference (CANONICAL)

| CB Stratum | YOUKNOW Y-Layer | Description | CB Lifecycle | YOUKNOW EMR |
|---|---|---|---|---|
| 1. `universal` | **Y₁** Upper Ontology | Observation types | `create` | — |
| 2. `subclass` | **Y₂** Domain Ontology | Subject buckets | `bloom` | `embodies` |
| 3. `instance` | **Y₃** Application Ontology | Operations per domain | `fill` | `manifests` |
| 4. `instance_universal` | **Y₄** Instance Ontology | Actual things | `lock` | `reifies` |
| 5. `instance_subtype` | **Y₅** Instance Type | Patterns from instances | `mine` | `reifies` |
| 6. `instance_instance` | **Y₆** Implementation | Solution space = THE thing | `terminal` | `programs` |

## O-Strata ↔ CB Duality

| O-Strata | YOUKNOW | Crystal Ball |
|---|---|---|
| **IS loop** | `is_a` chain (taxonomic) | Vertical: parent → children (tree) |
| **HAS loop** | `part_of`/`has_part` (compositional) | Horizontal: dots/slots (product) |

## SOUP → ONT Evolution (Shared Semantics)

All three systems share the same evolution protocol:

| State | CB | YOUKNOW | CartON |
|---|---|---|---|
| **SOUP** | Unlocked node, arbitrary label | Chain doesn't close | `requires_evolution` |
| **ONT** | Locked, ≥2 children spectrum | Chain closes to Cat_of_Cat | `REIFIES` relationship |
| **Terminal** | View ends here | `programs` level (codegen) | Fully reified |

## Implementation Status

### ✅ Phase 1: YOUKNOW as persistent MCP engine
- youknow_kernel loaded in-process on Crystal Ball MCP startup
- Cat_of_Cat persistence via `_load_from_domain_ontology()`
- domain.owl at `$HEAVEN_DATA_DIR/ontology/domain.owl`
- 203 entities in Cat_of_Cat (127 primitives + 76 Monster)

### ✅ Phase 2: Unified CB ↔ YOUKNOW entry point
- `crystal_ball()` auto-detects UARL predicates in input
- UARL statements route to YOUKNOW compiler internally
- Non-UARL input routes to CB state machine as before
- Single MCP tool is the only entry point

### ✅ Phase 3: OWL alignment
- `is_a` → `rdfs:subClassOf` (OWL standard)
- `description` → `rdfs:comment` (OWL standard)
- `name` → `rdfs:label` (OWL standard)
- `type` → `rdf:type` (already OWL standard)
- `instantiates` → `uarl:instantiates` (means "produces", UARL-specific)
- `programs` → `uarl:programs` (UARL-specific)
- EMR predicates (embodies/manifests/reifies) → `uarl:*` (UARL-specific)

### ✅ Phase 4: Monster ontology encoded
Full mathematical type hierarchy admitted to ONT:
```
Cat_of_Cat → Entity → Category → Mathematics → AlgebraicStructure
  → Group → FiniteGroup → FiniteSimpleGroup → SporadicGroup → MonsterGroup
    → MonsterObject → MonsterPrime, MonsterCollection, MonsterConductor, ...
    → MathProperty → Shard, Level, Eigenvalue, Proof, Factorization, ...
    → Representation → CharacterTable, IrreducibleRepresentation
    → MoonshineModule, ConjugacyClass, JInvariant, SupersingularPrime
    → 43 LMFDB instance objects
```

### ASPIRATIONAL: Phase 5: CB feeds labels to YOUKNOW continuously
- During tower, every label → auto-compiled as UARL statement
- Parse response to extract ideas (blocking list, suggestions)
- Ideas become new `addNode()` calls in CB
- Convergence = all chains close = tower is complete

### ASPIRATIONAL: Phase 6: LLM materializes ideas
- LLM reads YOUKNOW's ideas as its prompt context
- Generates UARL statements to fill gaps
- Each statement both validates (YOUKNOW) and creates (CB)
- "Wrong" responses generate MORE ideas → system grows

### TODO
- [ ] Clean up `instantiates` semantics in derivation.py (L5 check)
- [ ] Fix justification matching (currently matches on predicate key not target)
- [ ] Remove stale Hallucination entries from domain.owl
- [ ] CB mine → auto-compile mined coordinates as UARL statements
