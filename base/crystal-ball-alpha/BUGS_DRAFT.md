# Crystal Ball — Draft Bug Notes (2026-02-24 session)

> Working notes. Promoted to CRYSTAL_BALL_BUGS.md once confirmed.

---

## 🧠 ARCHITECTURE BREAKTHROUGH (2026-02-24 07:20–09:00)

### What We Discovered

1. **Space IS a DAG with CB coordinate encoding.** That's its definition. It's not "a DAG pretending to be something else" — it's a named concept for "DAG + coordinate grammar + superposition + locking + mining." The base layer is correct as a DAG.

2. **The base language is the DAG.** Fully type it as one. `CBNode` (or just `Node`) with ordered `children`. No attributes. No pretending it's something else.

3. **We build a language of Spaces with the DAG.** The Space language sits on top of the DAG: coordinate addressing, spectrum semantics, locking, mining, reification.

4. **Crystal Ball is implemented with that language.** MCP → engine → Space language → DAG.

5. **scry = eval.** A coordinate IS a program. The DAG IS the data. Resolving a coordinate against a DAG IS evaluation. This was always the intention ("scry was going to be the name of the interpreter").

6. **quote = inverse of scry.** Given a node, produce the coordinate that addresses it. Walk UP from node to root. This function does NOT exist yet.

7. **homoiconic.ts is dead code (667 lines, ZERO imports).** Nothing in the system uses it. Not the engine, not the MCP, not any test. This was discovered via: `rg "from './homoiconic'" lib/crystal-ball/` → no results.

8. **All 15 demo/test files bypass the MCP.** They run with `npx tsx` importing directly from library modules. The MCP is the ONLY valid interpreter entrypoint. These tests prove nothing about the actual system.

9. **The only relationship type is "produces."** Parent produces child. No separate edge types. This is why attributes are wrong — `mood: [casual, professional, sentimental]` is really "Tone produces Casual | Professional | Sentimental." The attribute name was the parent label. The attribute values were the children. The default was primacy 1.

### The Three Layers

```
Layer 0: THE DAG — index.ts
  Node with ordered children. No attributes. Just the tree.
  addNode, lockNode, children traversal.

Layer 1: THE SPACE LANGUAGE — homoiconic.ts (to be rewritten)
  Space = DAG + coordinate grammar + superposition + locking + mining
  eval = scry (resolve coordinate against DAG)
  quote = produce coordinate from node (NEW — does not exist yet)
  This is where math lives (RKHS, orbits, reification)

Layer 2: CRYSTAL BALL — engine.ts + MCP
  The interpreter. The only entrypoint.
  Commands go in, Spaces come out.
  ALL traversal goes through eval/quote.
```

### Reconciliation With Existing Bugs

| Bug | Still Valid? | Notes |
|-----|-------------|-------|
| DRAFT-6 (base layer inverted) | **REVISED** — The DAG IS correct as the base layer. We were wrong to say "DAGs should not be in the base layer." What's wrong is: (1) attributes Map duplicating children, (2) homoiconic not wired in, (3) math modules bypassing the Space language. The DAG itself is fine. |
| DRAFT-1 (lock accepts unbloomed) | ✅ Still valid | Lock must require ≥2 children (spectrum rule) unless terminal |
| DRAFT-2 (fill accepts single child) | ✅ Still valid | Same fix — lock enforcement, not fill-time |
| DRAFT-3 (stray node) | ✅ Still valid | Garbage data, needs cleanup |
| DRAFT-4 (FLOW validation skeletal) | ✅ Still valid | Passthrough validation |
| DRAFT-5 (no terminal marker) | ✅ Still valid | Needed for lock enforcement |
| BUG-A (engine bypasses homoiconic) | ✅ CRITICAL | The core problem. engine.ts must import from homoiconic.ts |
| BUG-B (attributes duplicates children) | ✅ CRITICAL | Remove attributes Map entirely |
| BUG-C (scry doesn't use token parsing) | ✅ Still valid | scry must walk token stream |
| BUG-D (instantiate reads attributes) | ✅ Depends on BUG-B | Dies when attributes removed |
| BUG-E (mine does Cartesian product) | **REVISED** | Mine should enumerate coordinate paths. Once attributes gone and scry=eval, mine = "systematically eval all possible coordinates" |
| BUG-F (homoiconic has 9 type errors) | **REVISED** | homoiconic.ts needs full rewrite anyway — it was built on wrong premise (separate lisp layer). New version is thin: eval=scry, quote=inverse, everything through coordinates |
| BUG-G (producedSpace: string) | ⚠️ Revisit | May resolve naturally when homoiconic is rewritten around the coordinate grammar |

### Key Rule Going Forward

**The MCP is the ONLY valid way to test Crystal Ball.** No `npx tsx`. No standalone scripts. No curl. If it can't be tested through the `crystal_ball` MCP tool, it doesn't exist.

### Isaac's verbatim (2026-02-24):

> "the base language is the DAG. we are building a language of spaces with it. so that we can implement crystal ball. pretty simple actually now that we know a lot about what that means"

> "scry was gonna even be the name of the interpreter lmao"

> "the reason we dont have attributes even though thats quite strange tbh is because we assume that every relationship abstraction in your DAG is going to come down to 'produces' because every single relationship is a claim about what X produces"

---

## THE HOLISTIC REASON

Crystal Ball's fundamental operation is **SELECTION from a SPECTRUM**. Every coordinate digit is a selection. Every node is a superposition of its children. Locking is collapsing a superposition.

A coordinate like `1.3.2` means: at level 0, select child 1 (out of N options). At level 1, select child 3. At level 2, select child 2. Each digit's RANGE is determined by how many children exist at that level. The coordinate maps to a real number. The children determine the RESOLUTION of that real number at each level.

### The Spectrum Rule

A spectrum MUST be established with a HIGH and a LOW — minimum 2 values — **every single time**. Nothing can ever be locked without having a spectrum. Without a high and a low, there is no range, there is no selection, there is no coordinate digit.

It does not need to happen all at once. You can build incrementally. But you cannot FINISH flow (lock the kernel) unless every node inside the kernel has at least a spectrum (≥2 children).

### EWS Boundary Exception: Terminal Labels

Defining one kernel can require defining lots of other kernels — the boundaries depend on the EWS (Emergent Web Structure). At these boundaries, **bare labels as terminals are OK.**

Example: A psychology kernel might have a node "NeuralCorrelate" with no children. That's not a violation — it's a terminal. It says "this kernel stops here, another kernel handles what's beyond." The label is meaningful AS a terminal — it marks where the responsibility transfers.

**You get to say when an arbitrary label is meaningful** — that's the EWS boundary decision.

---

## 🔴 DRAFT-6: THE BASE LAYER IS INVERTED — DAGs are implemented where Spaces should be

**Severity:** EXISTENTIAL — nothing works correctly until this is fixed.

**The error:** The code implements DAGs (nodes with children arrays, edges, neighbor traversal) and wraps them in a container called "Space." This is BACKWARDS.

**What the design says:** Space IS the primitive. A Space has slots. Slots get filled with labels. Those labels ARE sub-spaces. The parent-child relationship (which looks like a DAG) is a CONSEQUENCE of how spaces compose. DAGs are EMERGENT — they happen to be there, just like all the other math that was discovered. You do NOT build the base layer out of DAGs.

**What the code does:** `Space` = `{ name, rootId, nodes: Map<NodeId, CBNode>, dots: Dot[] }`. It's a flat graph database. CBNode has `children: NodeId[]` — foreign keys. `Dot` = edges. `neighbors()` = graph traversal. This IS a DAG implementation. Spaces are just a wrapper around it.

**Non-Space types that should not exist in the base layer:**
- `CBNode` — should be Space
- `Attribute` — attributes ARE children (design says explicitly)
- `Dot` — edges/morphisms, DAG semantics
- `Space.dots: Dot[]` — edge list inside a space
- `Space.nodes: Map<NodeId, CBNode>` — flat node map, graph database pattern
- `neighbors()` — graph traversal, kernel-level
- `emergentGenerate()` — cross-references attributes, built on broken Attribute
- `instantiate()` / `resolve()` — built on Attribute Map
- `AttributeBinding`, `Instance`, `InstantiateResult` — all depend on Attribute

**What the base layer SHOULD be:** Space, Spectrum (values), Coordinate (addressing). That's it. Everything else is kernel-level or higher.

**Isaac verbatim (2026-02-24):**
> "STOP MAKING DAGS IN MY HOMOICONIC SPACE SYSTEM. IT IS NOT DAGS. DAGS HAPPEN TO BE THERE JUST LIKE ALL OTHER MATH WE FOUND."
> "NODES ONLY APPEAR BECAUSE OF THE WAY KERNELS HAVE SPACES WITH SLOTS."

---

## DRAFT-1: Lock accepts unbloomed nodes (slotCount 0)

**Symptom:** You can lock a node that has never been bloomed — zero children, zero spectrum.

**Code evidence:**
- `lockNode()` at `index.ts:1626-1631` does ZERO validation. It checks if the node exists and if it's already locked. Then sets `locked = true`. No check for `children.length`, no check for `slotCount`, no check for spectrum existence.
- `isKernelComplete()` at `index.ts:608-626` only counts nodes with `slotCount > 0`. If nothing was bloomed, `totalSlotted = 0`, so `complete` is always `false`. But this is a STATUS REPORTER, not a GATE — it doesn't prevent locking.
- Engine `lock` handler at `engine.ts:660-669` calls `lockNode()` directly. The only check is `if (!node)` — node exists or not. No spectrum/children validation.

**Why this breaks the math:** Locking means "this superposition is collapsed." If there are zero children, there IS no superposition. The node contributes ZERO digits to the coordinate. The mineSpace path doesn't go through it. You've locked an empty box. The tower gets a layer that contains no information.

**What must change:** `lockNode()` must reject nodes with `children.length < 2` UNLESS the node is marked as a terminal (EWS boundary). Currently there is NO terminal marker on CBNode (see DRAFT-5).

---

## DRAFT-2: Fill accepts a single child

**Symptom:** You can add one child and lock.

**Code evidence:**
- `addNode()` in `index.ts` adds a single child with no minimum count check.
- The fill handler in `engine.ts` adds children one at a time. No enforcement that you must add at least 2 before being allowed to lock.
- The enforcement belongs at LOCK TIME (DRAFT-1), not at add time. You should be able to add one thing and come back later. But you cannot LOCK until you have ≥2.

**Why this breaks the math:** 1 child = base-1 coordinate digit. Carries zero bits of information. There's one option. No selection. The digit discriminates nothing.

**Note:** This is the same bug as DRAFT-1 — the fix is in lock enforcement. Fill itself adding one at a time is fine. The problem is that lock doesn't check.

---

## DRAFT-3: Stray node 96: IsaacsStoryMachine

**What:** Garbage data. Node `96: IsaacsStoryMachine` exists as child of root in IsaacsStoryMachine space.

**How it happened:** During testing, the space name was typed as fill input and got added as a child label.

---

## DRAFT-4: FLOW endpoint validation is skeletal

**Symptom:** `/api/cb/flow` `validateFlowInput()` at `app/api/cb/flow/route.ts` returns `{ allowed: true }` for almost everything. Phase enforcement exists as structure but not as real validation.

**What must change:** Once the FLOW rules are confirmed, the validation needs to actually reject invalid input for each phase. Right now it's a passthrough.

---

## DRAFT-5: CBNode has no terminal/EWS boundary marker

**Symptom:** `CBNode` interface at `index.ts:82-95` has: `id, label, children, attributes, producedSpace, stratum, slotCount, locked, frozen, x, y, kernelRef`. There is NO field for marking a node as a terminal (EWS boundary).

**Why this matters:** Lock enforcement (DRAFT-1) needs to distinguish interior nodes (must have ≥2 children) from terminal labels at EWS boundaries (allowed to have 0 children). Without a marker, the engine has no way to know which is which.

**What `producedSpace` does NOT solve:** `producedSpace` chains to another space — it's a drill-through, not a terminal. A terminal is the OPPOSITE: it says "nothing beyond here in THIS kernel." `producedSpace` says "there IS something beyond here."

**Options:**
- Add `terminal?: boolean` to CBNode
- Or infer from structure: leaf nodes without `producedSpace` at the deepest level of a kernel are terminals
- Or: the user explicitly marks nodes as terminals via a FLOW command

---

## Isaac's verbatim notes (2026-02-24):

> "a spectrum MUST BE ESTABLISHED WITH A HIGH AND LOW EVERY SINGLE TIME. NOTHING CAN EVER BE LOCKED WITHOUT HAVING A SPECTRUM. It does not need to happen all at once, but you cannot finish flow unless the kernel has at least a spectrum for everything inside of it."

> "AND that depends on the boundaries of your EWS in lots of different kernels for different stuff because defining one kernel could also require defining lots of different kernels."

> "You get to say when arbitrary label is meaningful. Like if we were doing psychology we might want to strictly disconnect from neuroscience so we just go 'and here it maps to neuro' well those are just labels and all those nodes are violations because they are just labels, but they are only used as terminals in EWS so its actually fine."

---

## Questions:

- Q1: How should terminal nodes be marked? Explicit `terminal: true` on CBNode, or inferred from structure?
- Q2: Should lock check be recursive (every descendant must have a spectrum) or just the node being locked?
- Q3: What happens to existing spaces with degenerate data from tonight's session?

---

## DESIGN-1: Lock Semantics — Two-Tier

**Current code:** `lockNode()` is one-way irreversible. No unlock function exists. DESIGN.md says "irreversible commitment."

**Proposed change:** Lock is a TOGGLE during FLOW, permanent only in mineSpace.

- **Flow-lock (toggle):** During kernel definition, "lock" means "I'm done with this slot for now, move to next." You can unlock, go back, add more children, re-lock. Otherwise development is impossibly rigid.
- **Mine-lock (permanent):** Once you mine a space, the tree that produced the coordinate mapping is frozen. Changing the tree changes the coordinate-to-real mapping, which invalidates every point in the mineSpace. The mine IS the commitment point, not individual node locks.

**If you want to change a mined space:** That creates a branch (see DESIGN-2).

### Isaac's verbatim notes on lock (2026-02-24):

> "a locked space cannot be mutated while you are locking another kernel. it is already locked, so you are locking another kernel you cant go add anything in that space from that kernel... you have to go to it itself and check the whole thing etc..."

> "but that maybe is stupid. maybe you need to be able to edit everything all the time and locking is just a sort of part of how flow works when you are defining stuff u say 'locked' but that isnt a global thing unless you are in mineSpace?"

---

## DESIGN-2: GitHub App for Git-Backed MineSpace Versioning

**The idea:** Use git as the branching/versioning mechanism for mineSpaces. If you unlock and change something that was already mined, it creates a git branch. The old mineSpace lives on the old commit. The new structure lives on the new branch.

**Why GitHub App (not OAuth App):**
- Fine-grained permissions (only Contents R/W on the specific repo)
- Short-lived tokens (secure, auto-refresh)
- Acts as bot — commits show as "Crystal Ball [bot]"
- Can act independently or on behalf of user
- Scales — rate limits increase with repos/users

### CB Operations → Git Operations

| CB Operation | Git Operation |
|---|---|
| `create` space | Create new JSON file |
| `fill` / `bloom` / `lock` | Update JSON file (working tree, no commit yet) |
| `mine` | **Commit** — snapshot the tree that produced the mineSpace |
| Unlock a mined space | **Branch** — create branch from the mine commit |
| Edit on branch | Commits on the branch |
| Re-mine on branch | **Commit on branch** — new mineSpace version |
| Accept changes | **Merge** branch to main |
| Discard changes | **Delete** branch |
| Global mineSpace | `main` branch HEAD |
| Per-kernel mineSpace | Tag or branch per kernel |

### What already exists in the codebase

- `serialize()` / `deserialize()` at `index.ts:1536-1583` — JSON ready
- `saveCb()` / `loadCb()` in `engine.ts` — persistence layer, currently writes to DB. Would need a git adapter
- The SaaS already has team/user concepts with API keys

### What would need to be built

1. GitHub App registration — one-time setup in GitHub developer settings
2. Installation flow — UI for users to install the app on their repo
3. Git adapter for `saveCb`/`loadCb` — instead of (or alongside) DB, serialize to git
4. Auto-branch logic — detect when a mined space is being unlocked, create branch
5. Octokit integration — `@octokit/app` npm package handles auth + API calls

### Isaac's verbatim notes on git branching (2026-02-24):

> "mineSpaces are both global and per kernel... if we remap something globally like if we unlock it and change it, that should just make a branch. If something has already previously entered minespace, it'll have to branch. we should just use git for this. this should literally just involve git and use git directly per user"

