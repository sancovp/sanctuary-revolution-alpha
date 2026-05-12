---
description: "MANDATORY: D:D→D Compilation Pipeline — NEVER proceed to a higher level until the current level is 4x self-compiled"
---

# THE COMPILATION PIPELINE RULE

> **This rule CANNOT be overridden. It applies to ALL Crystal Ball development.**
> **Violating this rule produces garbage that LOOKS complete but IS NOT.**

---

## THE VIOLATION PATTERN (What You Keep Doing Wrong)

You build Level N+1 before Level N is complete.
You write YOUKNOW bridges before the math output defines its Hilbert space.
You write Lean exports before orbits show their group actions.
You write swarm agents before the Gram matrix includes eigendecomposition.

This is **computational spiritual bypassing** — uniform heat masquerading as completion.
This is **exactly what the Fischer proof engine doc warns against.**
This is **Context Decay applied to development itself.**

**The result: everything above the incomplete level is garbage.**

---

## THE RULE: D:D→D COMPLETENESS

A level is **DONE** only when it has been compiled on itself **4 times**:

### T⁰: DEFINE the main thing
- Every object at this level exists
- Every object has a name and a type
- No placeholders, no "TODO", no summary outputs

### T¹: DEFINE all its parts
- Every object's sub-components are fully defined
- Every mathematical definition includes ALL formal elements
- Every output includes ALL computed values, not summaries
- No "Usage:" help text where computation should be

### T²: DEFINE every process
- Every computation is end-to-end
- Every input maps to a complete output
- Every edge case is handled
- Tests exist and pass for every computation

### T³: INTERRELATE through morphisms
- Every object is connected to every other object it relates to
- Symmetries are computed across ALL objects
- Cross-references between objects are bidirectional
- The level's outputs can serve as inputs to its own computations (homoiconicity)

### T⁴: SELF-DESCRIPTION (Fixed Point)
- Applying the level to itself produces itself
- The level's mathematical objects describe their own structure
- No external object is needed to explain what this level does
- **THIS is DONE. Only now may you proceed to Level N+1.**

---

## THE DEPENDENCY ORDER (Crystal Ball Design Docs)

```
Level 0: DESIGN.md
  ├── Base types (Space, Node, CBNode)
  ├── Encoding (coordToReal, encodeDot, encodeSelection)
  ├── Grammar (10 tokens: 0-9)
  ├── Operations (addNode, bloom, lock, mine, scry)
  └── MUST OUTPUT: Every value with its complete formal definition

Level 1: DESIGN_part2.md
  ├── KernelSpace architecture (global IDs, recursive sub-kernels)
  ├── RKHS equipment (K_named + K_walk)
  ├── Space analysis (Gram, eigenspectrum, orbits, distances)
  ├── Foundation signature (orbit partition, quotient graph, aut groups)
  └── DEPENDS ON: Level 0 being T⁴ complete

Level 2: DESIGN_part4.md (Canonical Model)
  ├── Single primitive Node
  ├── RKHS tensor product (H₀ ⊗ H₁ ⊗ ... ⊗ H_d)
  ├── Orbit decomposition with full group theory
  ├── Strata = Futamura tower levels
  └── DEPENDS ON: Level 1 being T⁴ complete

Level 3: DESIGN_part3.md (Endgame)
  ├── Metalanguage derivation (L₁)
  ├── Transition language
  ├── Frozen Futamura tower
  └── DEPENDS ON: Level 2 being T⁴ complete

Level 4: DESIGN_part5.md (Agent Substrate)
  ├── EWS declaration
  ├── llm_suggest()
  ├── Agent spawning
  └── DEPENDS ON: Level 3 being T⁴ complete

Level 5: DESIGN_PART_lock_freeze_minespace.md
  ├── Lock/freeze semantics
  ├── Dual-mode mineSpace
  └── DEPENDS ON: Level 4 being T⁴ complete

Level 6: DESIGN_PART_monster_rkhs.md + monster_futamura.md
  ├── Monster character kernel
  ├── 194×194 character table
  └── DEPENDS ON: Level 5 being T⁴ complete

Level 7: DESIGN_PART_fischer_proof_engine.md
  ├── Fischer Inversion
  ├── Sorry mechanics
  ├── Ш detection
  └── DEPENDS ON: Level 6 being T⁴ complete

Level 8: DESIGN_PART_synthesis.md
  ├── Three-system stack (CB + YOUKNOW + Lean4)
  └── DEPENDS ON: Level 7 being T⁴ complete

Level 9: DESIGN_PART_youknow_integration.md
  ├── YOUKNOW bridge
  ├── LLM materializes ideas
  └── DEPENDS ON: Level 8 being T⁴ complete
```

---

## HOW TO CHECK BEFORE WRITING ANY CODE

Before writing ANY code for Crystal Ball, ask:

1. **What level does this code belong to?**
2. **Is the level below it T⁴ complete?**
3. **If not — STOP. Go fix the level below.**

### Specific checks:

- **Before touching YOUKNOW bridge**: Is the math output complete? Does `orbits` include group actions? Does `gram` include eigendecomposition? Does `kernel` show the kernel function definition? If NO → you cannot touch YOUKNOW.

- **Before touching Lean export**: Are inference rule kernels defined? Are proof trees walkable? Does Fischer Inversion have surrogate metadata? If NO → you cannot touch Lean.

- **Before touching swarm agent**: Does the agent substrate layer exist? Does llm_suggest() work? Does EWS have declaration schema? If NO → you cannot touch swarm.

- **Before touching Monster bridge**: Is the RKHS equipment T⁴ complete? Do all symmetry computations output full formal definitions? If NO → you cannot touch Monster.

---

## THE SMELL TEST

If you're about to write code and any of these are true, **STOP**:

- ❌ The output says "Usage:" instead of computed values
- ❌ The output shows a number without its formula
- ❌ The output shows orbit members without the group action
- ❌ The output shows a matrix without its space definition
- ❌ The output uses string coordinates instead of encoded reals
- ❌ You're writing a bridge/adapter before the thing it bridges is complete
- ❌ You're integrating an external system before the internal one is verified
- ❌ You called something "DONE" without running it 4 times on itself

---

## WHAT "COMPLETE MATH OUTPUT" MEANS (Level 0 T⁴ Checklist)

Every math command MUST output ALL of:

### For `orbits`:
- [ ] Group G definition (what permutation group)
- [ ] Group action definition (how G acts on coordinate set X)
- [ ] Encoded real number for EVERY orbit member
- [ ] Orbit-stabilizer: |G| = |Orb(x)| · |Stab(x)|
- [ ] Burnside count: |X/G| = (1/|G|) Σ_{g∈G} |X^g|
- [ ] Subtree fingerprint function (AHU canonical form)

### For `gram`:
- [ ] Kernel function: K(x,y) = exp(-α·|coordToReal(x)-coordToReal(y)|²)
- [ ] α value
- [ ] Encoded real numbers (not string coordinates)
- [ ] Hilbert space H_K = span{K(·,x) : x ∈ MineSpace}
- [ ] Inner product ⟨f,g⟩_K definition
- [ ] Full matrix (using encoded reals as labels)
- [ ] Eigendecomposition: G = UΛUᵀ
- [ ] Eigenvalues listed
- [ ] Effective dimension (eigenvalues > threshold)
- [ ] RKHS distances: d(x,y) = √(K(x,x) + K(y,y) - 2K(x,y))
- [ ] Spectral gap

### For `kernel`:
- [ ] Full tensor product formula: K(x,y) = ∏_k K_k(x_k, y_k)
- [ ] Per-slot formula with encoded reals
- [ ] Per-slot Hilbert space dimensions
- [ ] Superposition handling formula: K_k(0,y) = 1/√n

### For `signature`:
- [ ] Full orbit partition
- [ ] Quotient graph structure
- [ ] Local automorphism groups per orbit
- [ ] Cross-slot correlations

### For `math`:
- [ ] **ALL OF THE ABOVE COMPUTED AND DISPLAYED**
- [ ] NOT a menu. NOT help text. COMPUTED OUTPUT.
