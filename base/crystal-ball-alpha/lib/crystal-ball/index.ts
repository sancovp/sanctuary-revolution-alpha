// Crystal Ball - Kernel v2
// Space-chaining coordinate ontology engine
//
// Core idea:
//   - A SPACE is a DAG (tree) of nodes representing a productive chain
//   - Each node in the chain NECESSITATES the nodes below it
//   - A COORDINATE is dot-separated segments crossing between spaces
//   - Each segment selects a node within its respective space
//   - A node can PRODUCE a child space (bloom) for deeper resolution
//   - 0 in any segment means superposition (not yet selected)
//   - INSTANTIATION = collapsing all 0s to specific selections
//
// ONTOLOGY STRATA (enforced by construction):
//   Every space contains 6 mandatory layers under root:
//
//   Object-level ontology:
//   1. Universal          — Domain of Abstract Classes
//      Spectra = requirements that must hold for ANY instance
//      (e.g. "a tweet has: text, character_count, platform")
//
//   2. Subclass           — Subclasses of Abstract Classes
//      Spectra = conditional requirements that distinguish this type
//      (e.g. "a CB marketing tweet must: demonstrate product, use AIDA")
//
//   3. Instance           — Instances of subclasses
//      Spectra = actual concrete values for this instance
//      (e.g. "this tweet: opener = '95 trillion', char_count = 280")
//
//   Meta-level ontology (Instance-as-Class recursion):
//   4. Instance_Universal — Instance becomes a new class; universal types of it
//      Spectra = for all X that have these instance values, what types exist?
//      (e.g. "for all tweets that open with a big number: types are shock, flex, proof")
//
//   5. Instance_Subtype   — Subtypes within that instance-class
//      Spectra = conditional distinctions within the instance-type
//      (e.g. "within 'proof' big-number tweets: must cite source, must show before/after")
//
//   6. Instance_Instance  — Instances of those subtypes → SOLUTION SPACE
//      Spectra = final concrete values; the collapsed solution
//      (e.g. "this specific proof tweet: cites own system, shows 95T number, links repo")
//
//   The output of stratum 6 IS the thing. Not a brief. The thing itself.

// ─── Types ────────────────────────────────────────────────────────

export type NodeId = string;
export type SpaceName = string;
export type SpectrumValue = string | number | boolean;
export type Spectrum = SpectrumValue[];
export type Stratum =
  | "universal"           // 1. Domain of Abstract Classes
  | "subclass"            // 2. Subclasses of Abstract Classes
  | "instance"            // 3. Instances of subclasses
  | "instance_universal"  // 4. Instance-as-Class Universal
  | "instance_subtype"    // 5. Subtypes within instance-class
  | "instance_instance";  // 6. Solution space

export const STRATA: Stratum[] = [
  "universal",
  "subclass",
  "instance",
  "instance_universal",
  "instance_subtype",
  "instance_instance",
];

export const STRATA_LABELS: Record<Stratum, string> = {
  universal: "Universal",
  subclass: "Subclass",
  instance: "Instance",
  instance_universal: "Instance_Universal",
  instance_subtype: "Instance_Subtype",
  instance_instance: "Instance_Instance",
};

/** @deprecated — Attribute map removed. Children ARE the spectrum.
 *  Kept as a type export only for backward compat with demo files pending conversion. */
export interface Attribute {
  name: string;
  spectrum: Spectrum;
  defaultValue?: SpectrumValue;
}

// ─── Proof-encoding types ────────────────────────────────────────

/** Role of a node in the proof structure */
export type ProofRole = 'axiom' | 'definition' | 'lemma' | 'theorem' | 'proof-step' | 'inference-rule';

/** Metadata tracking which external surrogate froze a node (Fischer Inversion) */
export interface FrozenByMetadata {
  surrogate: string;     // e.g. 'lean4', 'youknow', 'manual'
  timestamp: number;     // when it was frozen
  reversible: boolean;   // whether the freeze can be undone
  proof?: string;        // optional proof term or reference
}

export interface CBNode {
  id: NodeId;              // Unique within this space (e.g., "0", "1", "0.3")
  label: string;           // Human-readable name
  children: NodeId[];      // Productive necessitations — children ARE the spectrum
  producedSpace?: SpaceName;  // If this node produces/chains to another space
  stratum?: Stratum;       // Which ontological layer this node lives in
  slotCount?: number;      // How many children this node SHOULD have (class = has slots, instance = filled)
  locked?: boolean;        // If true, no more modifications allowed (instantiation is complete)
  frozen?: boolean;        // If true, pre-locked — kernel mode skips this node during bloom traversal
  terminal?: boolean;      // If true, this level is the end of this view — the space changes beyond this point
  x: number;               // Position on the global plane: coordToReal(id)
  y: number;               // Position on the global plane: coordToReal(id) — symmetric
  kernelRef?: number;      // Global ID of the sub-kernel that defines this slot (null = unfilled)
  tags?: Set<string>;      // View tags (e.g. "blacklist", "favorites") — filtering, not deletion
  // ── Proof-encoding fields ──
  role?: ProofRole;        // What role this node plays in the proof structure
  formalType?: string;     // Lean 4 type string (e.g. "∀ x : G, x * e = x")
  frozenBy?: FrozenByMetadata;  // Which external surrogate froze this node (Fischer Inversion tracking)
  // ── Quantum amplitude ──
  amplitude?: number;      // |ψ|² — LLM confidence (0.0-1.0). 1.0 = fully settled, 0.0 = superposition
  // Derived from ICL, not token logprobs. Human-set nodes default to 1.0.
}

// ─── Views ────────────────────────────────────────────────────────
// Views are FILTERS on spaces, not deletions. The underlying data
// is always complete. Different views of the same space produce
// different symmetry groups — and THAT tells you about the observer.

export type ViewMode = 'all' | 'exclude_tagged' | 'include_tagged_only' | 'tagged_only';

export interface SpaceView {
  name: string;             // e.g. "My Preferences", "What I Avoid"
  mode: ViewMode;           // How to apply the tag filter
  tags: Set<string>;        // Which tags this view filters on
}

// ─── V1 Backward Compatibility ───────────────────────────────────
export type CrystalBall = Space;
export type OntologyNode = CBNode;
export type SerializedCrystalBall = SerializedSpace;

export interface Dot {
  from: NodeId;  // Source node
  to: NodeId;    // Target node
  label?: string; // Optional morphism label
}

export interface Space {
  name: SpaceName;
  rootId: NodeId;
  nodes: Map<NodeId, CBNode>;
  dots: Dot[];   // Explicit morphisms between nodes
  ewsRef?: SpaceName;  // Name of the EWS space (production chain) for this kernel
  isEWS?: boolean;     // True if this space IS an EWS (domain chain), not a content kernel
}

// ─── KernelSpace ─────────────────────────────────────────────────
// A KernelSpace wraps a Space with a monotonic global ID.
// KernelSpaces are the top-level containers. NodeSpaces (slots) exist
// only within a KernelSpace and are defined by sub-kernels.

export interface KernelSpace {
  globalId: number;           // Monotonic creation counter — the ONLY static identifier
  space: Space;               // The underlying Space (DAG of nodes/slots)
  parentKernelId?: number;    // If this is a sub-kernel, which kernel contains it
  parentSlotId?: NodeId;      // Which slot in the parent kernel this fills
  locked: boolean;            // True only when ALL sub-kernels are recursively locked
  createdAt: number;          // Timestamp
}

// ─── Registry ─────────────────────────────────────────────────────
// All spaces and kernels are held in a registry

export interface Registry {
  spaces: Map<SpaceName, Space>;
  kernels: Map<number, KernelSpace>;  // Global ID → KernelSpace
  nextKernelId: number;               // Monotonic counter
}

export function createRegistry(): Registry {
  return { spaces: new Map(), kernels: new Map(), nextKernelId: 1 };
}

// ─── KernelSpace Operations ──────────────────────────────────────

/**
 * Create a new KernelSpace with the next global ID.
 * The kernel gets a Space auto-created with strata.
 */
export function createKernel(
  registry: Registry,
  label: string,
  parentKernelId?: number,
  parentSlotId?: NodeId,
): KernelSpace {
  const globalId = registry.nextKernelId++;
  const spaceName = `kernel_${globalId}_${label}`;
  const space = createSpace(registry, spaceName);

  const kernel: KernelSpace = {
    globalId,
    space,
    parentKernelId,
    parentSlotId,
    locked: false,
    createdAt: Date.now(),
  };

  registry.kernels.set(globalId, kernel);

  // If this is a sub-kernel, link it to the parent slot
  if (parentKernelId !== undefined && parentSlotId !== undefined) {
    const parentKernel = registry.kernels.get(parentKernelId);
    if (parentKernel) {
      const slot = parentKernel.space.nodes.get(parentSlotId);
      if (slot) {
        slot.kernelRef = globalId;
      }
    }
  }

  return kernel;
}

/**
 * Get a kernel by its global ID.
 */
export function getKernel(registry: Registry, globalId: number): KernelSpace {
  const kernel = registry.kernels.get(globalId);
  if (!kernel) throw new Error(`Kernel #${globalId} not found`);
  return kernel;
}

/**
 * List all kernels.
 */
export function listKernels(registry: Registry): KernelSpace[] {
  return Array.from(registry.kernels.values());
}

/**
 * Recursively lock a kernel. Only succeeds if ALL sub-kernels are locked.
 * Returns { success, unlockedSlots } where unlockedSlots lists any slots
 * that don't have locked sub-kernels yet.
 */
export function lockKernel(
  registry: Registry,
  globalId: number,
): { success: boolean; unlockedSlots: { nodeId: NodeId; label: string }[]; insufficientChildren: { nodeId: NodeId; label: string; childCount: number }[] } {
  const kernel = getKernel(registry, globalId);
  const unlockedSlots: { nodeId: NodeId; label: string }[] = [];
  const insufficientChildren: { nodeId: NodeId; label: string; childCount: number }[] = [];

  // Check all nodes with kernelRef — their sub-kernels must be locked
  for (const [nodeId, node] of kernel.space.nodes) {
    if (node.kernelRef !== undefined) {
      const subKernel = registry.kernels.get(node.kernelRef);
      if (!subKernel || !subKernel.locked) {
        unlockedSlots.push({ nodeId, label: node.label });
      }
    }
  }

  // Recursive children check: every non-terminal node with children
  // must have ≥2 children (a spectrum needs a high and a low)
  function checkChildren(nodeId: NodeId, visited: Set<NodeId>) {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);
    const node = kernel.space.nodes.get(nodeId);
    if (!node) return;

    // Terminal nodes and leaf nodes are exempt
    if (!node.terminal && node.children.length > 0 && node.children.length < 2) {
      insufficientChildren.push({
        nodeId,
        label: node.label,
        childCount: node.children.length,
      });
    }

    for (const childId of node.children) {
      checkChildren(childId, visited);
    }
  }

  checkChildren(kernel.space.rootId, new Set());

  if (unlockedSlots.length === 0 && insufficientChildren.length === 0) {
    kernel.locked = true;
    return { success: true, unlockedSlots: [], insufficientChildren: [] };
  }

  return { success: false, unlockedSlots, insufficientChildren };
}

/**
 * Generate the FULL coordinate for a local coordinate within a kernel.
 * Full coordinate = 90[globalId]900[localCoord]
 * This encodes BOTH which kernel and where within it into a single digit string.
 */
export function fullCoordinate(globalId: number, localCoord: string): string {
  return `${KERNEL_OPEN}${globalId}${KERNEL_CLOSE}${localCoord}`;
}

/**
 * Parse a full coordinate into its kernel ID and local coordinate.
 */
export function parseFullCoordinate(full: string): {
  kernelId: number;
  localCoord: string;
} | null {
  // Pattern: 90[digits]900[rest]
  const match = full.match(/^90(\d+)900(.+)$/);
  if (!match) return null;
  return {
    kernelId: parseInt(match[1], 10),
    localCoord: match[2],
  };
}

/**
 * Get the real-number position of a kernel on the global mineSpace plane.
 * This is coordToReal of the kernel prefix alone: 90[id]900
 */
export function kernelPosition(globalId: number): number {
  return coordToReal(`${KERNEL_OPEN}${globalId}${KERNEL_CLOSE}`);
}

// ─── Space Operations ─────────────────────────────────────────────

export function createSpace(registry: Registry, name: SpaceName): Space {
  if (registry.spaces.has(name)) {
    throw new Error(`Space "${name}" already exists`);
  }

  const root: CBNode = {
    id: "root",
    label: name,
    children: [],
    x: 0,  // root = origin
    y: 0,
  };

  const space: Space = {
    name,
    rootId: "root",
    nodes: new Map([["root", root]]),
    dots: [],
  };

  // NOTE: Strata are NOT auto-created as empty leaf nodes.
  // Strata are structural ROLES populated by operations:
  //   - mine → populates Universal (stratum 1) and Subclass (stratum 2)
  //   - lock → populates Instance (stratum 3)
  //   - reify → populates strata 4-6
  // See DESIGN_part4.md §7 for the strata-to-Futamura mapping.

  registry.spaces.set(name, space);
  return space;
}

export function getSpace(registry: Registry, name: SpaceName): Space {
  const space = registry.spaces.get(name);
  if (!space) throw new Error(`Space "${name}" not found`);
  return space;
}

export function listSpaces(registry: Registry): SpaceName[] {
  return Array.from(registry.spaces.keys());
}

export function deleteSpace(registry: Registry, name: SpaceName): void {
  if (!registry.spaces.has(name)) throw new Error(`Space "${name}" not found`);
  registry.spaces.delete(name);
}

/**
 * Add a dot (morphism) between two nodes in a space.
 * Dots are explicit directed edges that represent relationships between slots.
 */
export function addDot(space: Space, from: NodeId, to: NodeId, label?: string): Dot {
  if (!space.nodes.has(from)) throw new Error(`Node "${from}" not found in space "${space.name}"`);
  if (!space.nodes.has(to)) throw new Error(`Node "${to}" not found in space "${space.name}"`);
  const dot: Dot = { from, to, label };
  space.dots.push(dot);
  return dot;
}

/**
 * Add a dot (morphism) between two nodes in a kernel's space.
 */
export function addKernelDot(
  registry: Registry,
  kernelId: number,
  from: NodeId,
  to: NodeId,
  label?: string,
): Dot {
  const kernel = getKernel(registry, kernelId);
  return addDot(kernel.space, from, to, label);
}

// ─── Node Operations ─────────────────────────────────────────────
// "Defining X necessitates following it by defining Y"

/**
 * Encode a 1-based selection index to CB grammar-compliant digit string.
 *
 * CB grammar uses digits 0-9 with specific meanings:
 *   1-7: direct selection
 *   8:   drill (structural, not selection)
 *   9:   wrap (+7, extends selection range)
 *   0:   superposition
 *
 * So selection ≥ 8 must use wrap:
 *   8  → "91"  (9+1 = 7+1 = 8)
 *   9  → "92"  (9+2 = 7+2 = 9)
 *   14 → "97"  (9+7 = 7+7 = 14)
 *   15 → "991" (99+1 = 14+1 = 15)
 *   21 → "997" (99+7 = 14+7 = 21)
 *   22 → "9991" (999+1 = 21+1 = 22)
 */
export function encodeSelectionIndex(selection: number): string {
  if (selection < 1) throw new Error(`Selection must be ≥ 1, got ${selection}`);
  if (selection <= 7) return String(selection);

  // How many wraps do we need? Each wrap adds 7.
  let remaining = selection;
  let wraps = 0;
  while (remaining > 7) {
    remaining -= 7;
    wraps++;
  }

  return '9'.repeat(wraps) + String(remaining);
}

/**
 * Decode a CB selection digit string back to a 1-based selection index.
 */
export function decodeSelectionIndex(encoded: string): number {
  let wraps = 0;
  let i = 0;
  while (i < encoded.length && encoded[i] === '9') {
    wraps++;
    i++;
  }
  const base = parseInt(encoded[i], 10);
  return wraps * 7 + base;
}

export function addNode(
  space: Space,
  parentId: NodeId,
  label: string,
): CBNode {
  const parent = space.nodes.get(parentId);
  if (!parent) throw new Error(`Parent node "${parentId}" not found in space "${space.name}"`);

  // Selection index: 1-based (children.length gives 0-based count, +1 for next)
  const selectionIndex = parent.children.length + 1;
  const selectionEncoded = encodeSelectionIndex(selectionIndex);

  // ID is parent.selectionEncoded (e.g., root.1, root.91, root.1.3)
  const id = parentId === "root"
    ? selectionEncoded
    : `${parentId}.${selectionEncoded}`;

  const r = coordToReal(id);
  const node: CBNode = {
    id,
    label,
    children: [],
    x: r,
    y: r,
  };

  space.nodes.set(id, node);
  parent.children.push(id);

  return node;
}

// ─── Bloom: Space-Chaining ────────────────────────────────────────
// A node can PRODUCE another space. This is how you go deeper.
// 
// Three modes:
//   1. No childSpaceName → create new space named "Parent::NodeLabel"
//   2. childSpaceName that doesn't exist → create new space with that name
//   3. childSpaceName that ALREADY EXISTS → LINK to it (cross-space spiral)
//
// Mode 3 is what enables the tower: AIDA::Action can bloom into
// CrystalBallMarketing::Channel, creating a spiral coordinate path
// through multiple independent spaces.

export function bloom(
  registry: Registry,
  space: Space,
  nodeId: NodeId,
  childSpaceName?: SpaceName,
): Space {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);

  // If the node already produces a space, return it
  if (node.producedSpace) {
    return getSpace(registry, node.producedSpace);
  }

  const name = childSpaceName || `${space.name}::${node.label}`;

  // Check if target space already exists (cross-space link)
  const existing = registry.spaces.get(name);
  if (existing) {
    // LINK to existing space — this creates the spiral
    node.producedSpace = name;
    return existing;
  }

  // Create new child space
  const childSpace = createSpace(registry, name);
  node.producedSpace = name;

  return childSpace;
}

// ─── Attributes — REMOVED ─────────────────────────────────────────
// Children ARE the spectrum. There is no separate attributes map.
// See DESIGN.md §2 and DESIGN_part4.md §1.
//
// addAttribute() and getAttributes() have been deleted.
// All callers now use addNode() and node.children instead.

// ─── Shield Computation ──────────────────────────────────────────
// Shield = ontological boundary around a node with interior content.
// These are kernel-side pure functions. Camera-relative checks
// (distance, "am I inside?") stay in the viz layer.

/** Whether a node has a shield (has interior content to protect) */
export function isShielded(node: CBNode): boolean {
  return node.children.length > 0 || !!node.producedSpace;
}

/** Shield radius — proportional to interior complexity */
export function computeShieldRadius(node: CBNode): number {
  const childCount = node.children.length;
  const hasSubspace = !!node.producedSpace;
  const base = Math.max(2, Math.sqrt(childCount) * 1.5);
  return hasSubspace ? base * 1.5 : base;
}

/** HIEL heat — unfilled ratio. More empty slots = hotter (more stochastic freedom) */
export function computeHeat(node: CBNode): number {
  if (!node.slotCount || node.slotCount <= 0) return 0.5; // unknown capacity = neutral
  const filled = node.children.length;
  return Math.max(0, Math.min(1, 1 - (filled / node.slotCount)));
}

// ─── Tower State Sensor ──────────────────────────────────────────
// Tower depth = compilation stack depth from bottom up.
// "How many layers of fully-ligated sub-kernels justify this node?"
// A node whose bloom chain goes A→B→C where all are ligated has tower=3.
// If B has open slots, tower=1 (only C is proven).

/** Check if a space is fully ligated — all slotted nodes are LOCKED (not just filled) */
export function isSpaceLigated(space: Space): boolean {
  for (const [, node] of space.nodes) {
    if (node.slotCount && node.slotCount > 0) {
      if (!node.locked) return false;
    }
  }
  return true;
}

/** Space-level heat — aggregate across all nodes */
export function computeSpaceHeat(space: Space): number {
  let totalSlots = 0;
  let totalFilled = 0;
  for (const [, node] of space.nodes) {
    if (node.slotCount && node.slotCount > 0) {
      totalSlots += node.slotCount;
      totalFilled += Math.min(node.children.length, node.slotCount);
    }
  }
  if (totalSlots === 0) return 0.5; // no slotted nodes = neutral
  return Math.max(0, Math.min(1, 1 - (totalFilled / totalSlots)));
}

/**
 * Tower depth for a node — walks bloom chain, counts ligated layers from bottom up.
 * Returns { depth, layers } where depth = # of consecutive proven layers,
 * and layers = per-space ligation status for the full chain.
 */
export function computeTowerDepth(
  registry: Registry,
  space: Space,
  nodeId: NodeId,
): { depth: number; layers: { space: SpaceName; ligated: boolean; heat: number }[] } {
  const layers: { space: SpaceName; ligated: boolean; heat: number }[] = [];

  // Walk the bloom chain from this node downward
  let currentNode = space.nodes.get(nodeId);
  let currentSpace = space;

  while (currentNode?.producedSpace) {
    const childSpace = registry.spaces.get(currentNode.producedSpace);
    if (!childSpace) break;

    const ligated = isSpaceLigated(childSpace);
    const heat = computeSpaceHeat(childSpace);
    layers.push({ space: childSpace.name, ligated, heat });

    // Follow the bloom chain deeper — find any node in child space that also blooms
    let nextBloom: CBNode | undefined;
    for (const [, node] of childSpace.nodes) {
      if (node.producedSpace) {
        nextBloom = node;
        break;
      }
    }

    currentNode = nextBloom;
    currentSpace = childSpace;
  }

  // Count consecutive ligated layers from the bottom up
  let depth = 0;
  for (let i = layers.length - 1; i >= 0; i--) {
    if (layers[i].ligated) depth++;
    else break; // first unligated layer stops the count
  }

  return { depth, layers };
}

// ─── Kernel Completeness Check ───────────────────────────────────────

/** Check if a kernel is complete — every slotted node in the space is locked.
 *  Returns { complete, lockedCount, totalSlotted } for progress tracking. */
export function isKernelComplete(space: Space): {
  complete: boolean;
  lockedCount: number;
  totalSlotted: number;
} {
  let lockedCount = 0;
  let totalSlotted = 0;
  for (const [, node] of space.nodes) {
    if (node.slotCount && node.slotCount > 0) {
      totalSlotted++;
      if (node.locked) lockedCount++;
    }
  }
  return {
    complete: totalSlotted > 0 && lockedCount === totalSlotted,
    lockedCount,
    totalSlotted,
  };
}

// ─── Coordinate Parsing ──────────────────────────────────────────
// Coordinates are parsed CHARACTER BY CHARACTER within each dot-separated level.
//
// Digit semantics:
//   0     = SUPERPOSITION — spectrum not chosen
//   1-7   = EXACT SELECTION — primacy of childspace from parent (modulo children.length)
//   8     = DRILL — enter the subspace of the currently selected node
//   88    = CLOSE DRILL — exit back to parent level
//   9     = WRAP — adds +7 to the current selection accumulator
//
// Examples:
//   1.991     → level 0: select 1; level 1: 9(+7)+9(+7)+1 = 15th child
//   1.238812  → level 0: select 1; level 1: select 2, select 3, DRILL(8),
//               (inside subspace) select 1, CLOSE DRILL(88), select 2
//
// A dot separates LEVELS (kernel slots).
// Within a level, each character is a token in the coordinate language.

export type CoordinateTokenType = 'select' | 'superposition' | 'drill' | 'close_drill' | 'also_open' | 'also_close';

export interface CoordinateToken {
  type: CoordinateTokenType;
  value?: number;  // For 'select': the resolved selection (1-based, after wrap accumulation)
}

export interface ParsedLevel {
  tokens: CoordinateToken[];
}

export interface ParsedCoordinate {
  raw: string;
  levels: ParsedLevel[];
  // Backward compat: flat list of resolved selections per level (ignoring drill tokens)
  // Only valid for simple coordinates without drills
  segments: number[];
}

export function parseCoordinate(coord: string): ParsedCoordinate {
  const raw = coord.trim();
  if (raw === "" || raw === "root") {
    return { raw, levels: [], segments: [] };
  }

  const parts = raw.split(".").filter(p => p.length > 0);
  const levels: ParsedLevel[] = [];
  const segments: number[] = [];

  for (const part of parts) {
    const tokens: CoordinateToken[] = [];
    let i = 0;
    let wrapAccumulator = 0;
    let levelPrimarySelection = 0;  // Track the first selection for backward compat
    let drillDepth = 0;  // Track nested drill depth for validation
    let alsoDepth = 0;   // Track nested also depth for validation

    // Helper: check if substring at position matches a multi-digit token
    function matchesAt(pos: number, ...sequences: string[]): string | null {
      // Try longest match first to avoid prefix ambiguity
      const sorted = sequences.sort((a, b) => b.length - a.length);
      for (const seq of sorted) {
        if (part.substring(pos, pos + seq.length) === seq) return seq;
      }
      return null;
    }

    while (i < part.length) {
      // Check for multi-digit impossible tokens FIRST (before single-digit parsing)
      const alsoMatch = matchesAt(i, ALSO_CLOSE, ALSO_OPEN);
      if (alsoMatch) {
        // Flush wrap accumulator
        if (wrapAccumulator > 0) {
          tokens.push({ type: 'select', value: wrapAccumulator });
          if (levelPrimarySelection === 0) levelPrimarySelection = wrapAccumulator;
          wrapAccumulator = 0;
        }
        if (alsoMatch === ALSO_OPEN) {
          tokens.push({ type: 'also_open' });
          alsoDepth++;
        } else {
          if (alsoDepth <= 0) {
            throw new Error(`ALSO close (${ALSO_CLOSE}) without matching ALSO open (${ALSO_OPEN}) in "${part}" at position ${i}`);
          }
          tokens.push({ type: 'also_close' });
          alsoDepth--;
        }
        i += alsoMatch.length;
        continue;
      }

      const char = part[i];
      const digit = parseInt(char, 10);

      if (isNaN(digit)) {
        throw new Error(`Invalid coordinate character: "${char}" in "${part}"`);
      }

      if (digit === 0) {
        // SUPERPOSITION: spectrum not chosen
        // Flush any wrap accumulator as a selection first
        if (wrapAccumulator > 0) {
          tokens.push({ type: 'select', value: wrapAccumulator });
          if (levelPrimarySelection === 0) levelPrimarySelection = wrapAccumulator;
          wrapAccumulator = 0;
        }
        tokens.push({ type: 'superposition' });
        i++;
      } else if (digit === 8) {
        // Flush any wrap accumulator first
        if (wrapAccumulator > 0) {
          tokens.push({ type: 'select', value: wrapAccumulator });
          if (levelPrimarySelection === 0) levelPrimarySelection = wrapAccumulator;
          wrapAccumulator = 0;
        }

        // Check for 88 (close drill) vs 8 (drill)
        if (i + 1 < part.length && part[i + 1] === '8') {
          // 88 = CLOSE DRILL — must have a matching open drill
          if (drillDepth <= 0) {
            throw new Error(`Close drill (88) without matching open drill (8) in "${part}" at position ${i}`);
          }
          tokens.push({ type: 'close_drill' });
          drillDepth--;
          i += 2;
        } else {
          // 8 = DRILL into subspace of current selection
          tokens.push({ type: 'drill' });
          drillDepth++;
          i++;
        }
      } else if (digit === 9) {
        // WRAP: +7 to accumulator
        wrapAccumulator += 7;
        i++;
      } else {
        // 1-7: EXACT SELECTION
        const value = wrapAccumulator + digit;
        wrapAccumulator = 0;
        tokens.push({ type: 'select', value });
        if (levelPrimarySelection === 0) levelPrimarySelection = value;
        i++;
      }
    }

    // Flush trailing wrap accumulator (e.g., "99" at the end without a final digit)
    if (wrapAccumulator > 0) {
      // Trailing wraps without a final selection — treat as the accumulated value
      tokens.push({ type: 'select', value: wrapAccumulator });
      if (levelPrimarySelection === 0) levelPrimarySelection = wrapAccumulator;
    }

    levels.push({ tokens });
    segments.push(levelPrimarySelection);
  }

  return { raw, levels, segments };
}

// ─── Coordinate Encoding ─────────────────────────────────────────
// Three impossible token sequences used as structural delimiters:
//   8988  = DOT (drill + wrap + close_drill — impossible: wrap needs selection, not close)
//   90    = KERNEL_OPEN (wrap + superposition — impossible: can't +7 a non-choice)
//   900   = KERNEL_CLOSE (wrap + double superposition — impossible)

export const DOT_ENCODING = '8988';
export const KERNEL_OPEN = '90';
export const KERNEL_CLOSE = '900';
export const ALSO_OPEN = '90009';
export const ALSO_CLOSE = '9900099';

/** Encode dots to the impossible token sequence 8988 */
export function encodeDot(coordinate: string): string {
  return coordinate.replace(/\./g, DOT_ENCODING);
}

/** Decode dots from a pure digit string */
export function decodeDot(encoded: string): string {
  return encoded.split(DOT_ENCODING).join('.');
}

/** Convert a coordinate to its real number position: 0.{encoded_digits} */
export function coordToReal(coordinate: string): number {
  if (coordinate === 'root') return 0;
  const encoded = encodeDot(coordinate);
  return parseFloat(`0.${encoded}`);
}

// ─── Scry: Coordinate Resolution ─────────────────────────────────
// Given a starting space and a coordinate, resolve it.
//
// Each segment selects within the current space:
//   - 0 means "all children at this level" (wildcard)
//   - N means "select child N" (1-indexed)
//
// After selecting a node, if there are more segments,
// we follow into the node's PRODUCED SPACE and continue resolution.
// If the node has no produced space but there are more segments,
// we go deeper into the node's own children within the same space.

export interface GenerationSlot {
  segmentIndex: number;       // Which segment in the coordinate is 0
  spaceName: string;          // Which space this 0 is in
  parentLabel: string;        // Label of the parent node (context)
  existingOptions: { index: number; label: string; coordinate: string }[];  // What's already there
  action: "select" | "generate" | "select_or_generate";  // What the LLM must do
  prompt: string;             // Human/LLM-readable instruction
}

export interface ScryResult {
  coordinate: string;
  resolved: ResolvedNode[];
  unresolvedZeros: number;  // How many 0s remain (how far from full instantiation)
  slots: GenerationSlot[];  // Generation slots for each 0 — LLM instructions
}

export interface ResolvedNode {
  spaceChain: string[];  // Which spaces we traversed to get here
  nodeId: NodeId;
  label: string;
  coordinate: string;    // The specific coordinate of this node
  childCount: number;
  producedSpace?: SpaceName;
  isZero: boolean;       // Was this reached via a 0-wildcard
}

export function scry(
  registry: Registry,
  startSpace: SpaceName,
  coordinate: string,
  includeNodeIds?: string[],
): ScryResult {
  const parsed = parseCoordinate(coordinate);
  const space = getSpace(registry, startSpace);
  const results: ResolvedNode[] = [];
  const slots: GenerationSlot[] = [];
  let unresolvedZeros = 0;

  // Process levels (dot-separated) with token stream
  // Each level is processed against the current space context.
  // Dot transitions ("." separator) follow into produced spaces.
  function processLevel(
    levelIndex: number,
    currentSpace: Space,
    spaceChain: string[],
    coordinatePrefix: string,
    selectedNode: CBNode | null,
  ): void {
    if (levelIndex >= parsed.levels.length) return;

    const level = parsed.levels[levelIndex];
    const root = currentSpace.nodes.get(currentSpace.rootId);
    if (!root) return;

    // Space stack for drill/close_drill within a single level
    let activeSpace = currentSpace;
    let activeRoot = root;
    const spaceStack: { space: Space; root: CBNode; chain: string[] }[] = [];
    let activeChain = [...spaceChain, currentSpace.name];
    let currentSelected: CBNode | null = null;

    // Also stack for concurrent attribute paths
    // When also_open is hit, we save the current selection context
    // so we can return to it and start a parallel branch
    interface AlsoContext {
      space: Space;
      root: CBNode;
      chain: string[];
      selected: CBNode | null;
      spaceStackDepth: number;  // to validate drill matching within also blocks
    }
    const alsoStack: AlsoContext[] = [];

    for (const token of level.tokens) {
      switch (token.type) {
        case 'superposition': {
          // 0 = wildcard — all children at current position
          unresolvedZeros++;

          const existingOptions = activeRoot.children.map((childId, i) => {
            const child = activeSpace.nodes.get(childId);
            const childCoord = coordinatePrefix
              ? `${coordinatePrefix}.${i + 1}`
              : String(i + 1);
            return {
              index: i + 1,
              label: child?.label || childId,
              coordinate: childCoord,
            };
          });

          const action: "select" | "generate" | "select_or_generate" =
            existingOptions.length === 0 ? "generate" : "select_or_generate";

          const parentLabel = activeRoot.label;
          const prompt = existingOptions.length === 0
            ? `No options defined yet in "${parentLabel}" (space: ${activeSpace.name}). Generate a new option.`
            : `In "${parentLabel}" (space: ${activeSpace.name}), select from [${existingOptions.map(o => `${o.index}:${o.label}`).join(", ")}] OR generate a new option.`;

          slots.push({
            segmentIndex: levelIndex,
            spaceName: activeSpace.name,
            parentLabel,
            existingOptions,
            action,
            prompt,
          });

          // Return all children as resolved nodes
          for (let i = 0; i < activeRoot.children.length; i++) {
            const childId = activeRoot.children[i];
            const child = activeSpace.nodes.get(childId);
            if (!child) continue;

            const childCoord = coordinatePrefix
              ? `${coordinatePrefix}.${i + 1}`
              : String(i + 1);

            results.push({
              spaceChain: activeChain,
              nodeId: child.id,
              label: child.label,
              coordinate: childCoord,
              childCount: child.children.length,
              producedSpace: child.producedSpace,
              isZero: true,
            });

            // Recurse into next level for each child
            if (levelIndex + 1 < parsed.levels.length) {
              if (child.producedSpace) {
                const nextSpace = registry.spaces.get(child.producedSpace);
                if (nextSpace) {
                  processLevel(levelIndex + 1, nextSpace, activeChain, childCoord, child);
                }
              } else if (child.children.length > 0) {
                const subView: Space = {
                  name: `${activeSpace.name}@${child.label}`,
                  rootId: child.id,
                  nodes: activeSpace.nodes,
                  dots: [],
                };
                processLevel(levelIndex + 1, subView, activeChain, childCoord, child);
              }
            }
          }
          return; // Superposition fans out — done with this level
        }

        case 'select': {
          // 1-7 (or wrapped higher) = select child at index (1-based)
          const selectionValue = token.value!;
          const childIndex = selectionValue - 1;
          if (childIndex < 0 || childIndex >= activeRoot.children.length) {
            throw new Error(
              `Coordinate selection ${selectionValue} out of range in space "${activeSpace.name}" ` +
              `(has ${activeRoot.children.length} children)`
            );
          }

          const childId = activeRoot.children[childIndex];
          const child = activeSpace.nodes.get(childId);
          if (!child) return;

          currentSelected = child;

          const childCoord = coordinatePrefix
            ? `${coordinatePrefix}.${selectionValue}`
            : String(selectionValue);

          // Only push result if this is the LAST token in the level
          // (or if we're about to drill — the drill will handle further resolution)
          const isLastToken = token === level.tokens[level.tokens.length - 1];
          if (isLastToken) {
            results.push({
              spaceChain: activeChain,
              nodeId: child.id,
              label: child.label,
              coordinate: childCoord,
              childCount: child.children.length,
              producedSpace: child.producedSpace,
              isZero: false,
            });

            // If there are more levels (dot-separated), continue resolution
            if (levelIndex + 1 < parsed.levels.length) {
              if (child.producedSpace) {
                const nextSpace = registry.spaces.get(child.producedSpace);
                if (nextSpace) {
                  processLevel(levelIndex + 1, nextSpace, activeChain, childCoord, child);
                }
              } else if (child.children.length > 0) {
                const subView: Space = {
                  name: `${activeSpace.name}@${child.label}`,
                  rootId: child.id,
                  nodes: activeSpace.nodes,
                  dots: [],
                };
                processLevel(levelIndex + 1, subView, activeChain, childCoord, child);
              }
            }
          }
          break;
        }

        case 'drill': {
          // 8 = enter the currently selected node's produced space
          if (!currentSelected) {
            throw new Error(`Drill (8) without prior selection in space "${activeSpace.name}"`);
          }
          if (!currentSelected.producedSpace) {
            throw new Error(
              `Drill (8) on node "${currentSelected.label}" which has no produced space`
            );
          }

          const drillSpace = registry.spaces.get(currentSelected.producedSpace);
          if (!drillSpace) {
            throw new Error(
              `Drill (8) target space "${currentSelected.producedSpace}" not found in registry`
            );
          }

          // Push current context onto stack
          spaceStack.push({ space: activeSpace, root: activeRoot, chain: activeChain });

          // Enter the drilled space
          activeSpace = drillSpace;
          const newRoot = drillSpace.nodes.get(drillSpace.rootId);
          if (!newRoot) return;
          activeRoot = newRoot;
          activeChain = [...activeChain, drillSpace.name];
          currentSelected = null;
          break;
        }

        case 'close_drill': {
          // 88 = exit back to parent space
          if (spaceStack.length === 0) {
            throw new Error(`Close drill (88) without matching drill in coordinate`);
          }

          const parent = spaceStack.pop()!;
          activeSpace = parent.space;
          activeRoot = parent.root;
          activeChain = parent.chain;
          currentSelected = null;
          break;
        }

        case 'also_open': {
          // 90009 = open a concurrent attribute path
          // Save current context so we can return to it after also_close
          alsoStack.push({
            space: activeSpace,
            root: activeRoot,
            chain: [...activeChain],
            selected: currentSelected,
            spaceStackDepth: spaceStack.length,
          });
          // Continue processing from the SAME position — the also branch
          // starts from the same node/space context
          break;
        }

        case 'also_close': {
          // 9900099 = close the concurrent attribute path
          if (alsoStack.length === 0) {
            throw new Error(`ALSO close without matching ALSO open in coordinate`);
          }

          const saved = alsoStack.pop()!;
          // Restore context to where the also_open was
          activeSpace = saved.space;
          activeRoot = saved.root;
          activeChain = saved.chain;
          currentSelected = saved.selected;
          // Trim any drills that were opened within the also block
          while (spaceStack.length > saved.spaceStackDepth) {
            spaceStack.pop();
          }
          break;
        }
      }
    }
  }

  processLevel(0, space, [], "", null);

  // Also include explicitly requested nodes
  if (includeNodeIds && includeNodeIds.length > 0) {
    for (const nid of includeNodeIds) {
      const node = space.nodes.get(nid);
      if (node && !results.find((r) => r.nodeId === nid)) {
        results.push({
          spaceChain: [startSpace],
          nodeId: node.id,
          label: node.label,
          coordinate: nid,
          childCount: node.children.length,
          producedSpace: node.producedSpace,
          isZero: false,
        });
      }
    }
  }

  return {
    coordinate,
    resolved: results,
    unresolvedZeros,
    slots,
  };
}

// ─── Instantiate: Collapse spectra into concrete values ──────────
// Given a coordinate, resolve it, collect all attributes,
// and produce concrete instances by selecting spectrum values.
//
// Mode "default": return one instance using default spectrum values
// Mode "all": return cartesian product of all spectra (every valid combination)

export interface AttributeBinding {
  node: string;        // Which node this attribute belongs to
  coordinate: string;  // Coordinate of that node
  attribute: string;   // Attribute name
  value: SpectrumValue; // Selected value
}

export interface Instance {
  coordinate: string;
  bindings: AttributeBinding[];
  summary: Record<string, SpectrumValue>; // Flat key→value for convenience
}

export interface InstantiateResult {
  coordinate: string;
  unresolvedZeros: number;
  spectraCount: number;    // How many attributes have spectra
  combinationCount: number; // Total possible combinations
  instances: Instance[];
}

export function instantiate(
  registry: Registry,
  startSpace: SpaceName,
  coordinate: string,
  mode: "default" | "all" = "default",
  maxCombinations: number = 1000,
): InstantiateResult {
  // First, scry to resolve the coordinate
  const scryResult = scry(registry, startSpace, coordinate);

  // Collect all attributes across resolved nodes
  interface SpectrumSlot {
    node: string;
    coordinate: string;
    attribute: string;
    spectrum: Spectrum;
    defaultValue?: SpectrumValue;
  }

  const slots: SpectrumSlot[] = [];

  // With attributes removed, the spectrum IS the children.
  // instantiate now has no attribute-based slots to iterate.
  // It returns an empty instances list (no spectra to collapse).
  // In the new architecture, the coordinate itself IS the instance.

  // Calculate total combinations
  const combinationCount = slots.length === 0
    ? 0
    : slots.reduce((acc, s) => acc * s.spectrum.length, 1);

  if (mode === "default" || slots.length === 0) {
    // Return single instance with defaults
    const bindings: AttributeBinding[] = slots.map((s) => ({
      node: s.node,
      coordinate: s.coordinate,
      attribute: s.attribute,
      value: s.defaultValue !== undefined ? s.defaultValue : s.spectrum[0],
    }));

    const summary: Record<string, SpectrumValue> = {};
    for (const b of bindings) {
      summary[`${b.node}.${b.attribute}`] = b.value;
    }

    return {
      coordinate,
      unresolvedZeros: scryResult.unresolvedZeros,
      spectraCount: slots.length,
      combinationCount,
      instances: bindings.length > 0 ? [{
        coordinate,
        bindings,
        summary,
      }] : [],
    };
  }

  // Mode "all": cartesian product
  if (combinationCount > maxCombinations) {
    // Return a warning instead of OOMing
    return {
      coordinate,
      unresolvedZeros: scryResult.unresolvedZeros,
      spectraCount: slots.length,
      combinationCount,
      instances: [],
    };
  }

  // Generate cartesian product
  const instances: Instance[] = [];

  function cartesian(slotIdx: number, current: AttributeBinding[]): void {
    if (slotIdx >= slots.length) {
      const summary: Record<string, SpectrumValue> = {};
      for (const b of current) {
        summary[`${b.node}.${b.attribute}`] = b.value;
      }
      instances.push({
        coordinate,
        bindings: [...current],
        summary,
      });
      return;
    }

    const slot = slots[slotIdx];
    for (const val of slot.spectrum) {
      current.push({
        node: slot.node,
        coordinate: slot.coordinate,
        attribute: slot.attribute,
        value: val,
      });
      cartesian(slotIdx + 1, current);
      current.pop();
    }
  }

  cartesian(0, []);

  return {
    coordinate,
    unresolvedZeros: scryResult.unresolvedZeros,
    spectraCount: slots.length,
    combinationCount,
    instances,
  };
}

// ─── Resolve: Fill madlib 0s and commit back to space ─────────────
// This is the growth mechanism. When the LLM fills a madlib:
//   1. The filled value becomes a permanent spectrum option
//   2. The space grows — next time, that option is selectable
//   3. Bad fills get blacklisted (future: blacklist mechanism)
//
// fills: Record<string, SpectrumValue> where key = "nodeCoord.attrName"
//   e.g. { "5.0.tweet": "My new tweet text here" }
//
// Three modes:
//   - All spectra selected, no 0s → complete deliverable (just returns it)
//   - Some 0s with fills provided → instance madlib (fills blanks, commits)
//   - Some 0s without fills → class madlib (returns slots for LLM to fill)

export interface ResolveResult {
  coordinate: string;
  mode: "complete" | "instance_madlib" | "class_madlib";
  output: Record<string, SpectrumValue>;  // The fully resolved key→value pairs
  newValuesCommitted: number;             // How many new values were added to spectra
  remainingSlots: GenerationSlot[];       // Any unfilled 0s (class madlib)
}

export function resolve(
  registry: Registry,
  spaceName: SpaceName,
  coordinate: string,
  fills?: Record<string, SpectrumValue>,
): ResolveResult {
  const space = getSpace(registry, spaceName);
  const scryResult = scry(registry, spaceName, coordinate);

  const output: Record<string, SpectrumValue> = {};
  let newValuesCommitted = 0;

  // With attributes removed, resolved nodes no longer carry attribute bindings.
  // The coordinate itself is the output. Children ARE the spectrum.

  // Process fills for generation slots (0s)
  const remainingSlots: GenerationSlot[] = [];

  if (fills) {
    for (const slot of scryResult.slots) {
      // Check if the LLM provided a fill for this slot
      // Fills can be keyed by slot index, space::parentLabel, or coordinate
      const fillKey = Object.keys(fills).find(k =>
        k === String(slot.segmentIndex) ||
        k === `${slot.spaceName}::${slot.parentLabel}` ||
        k.startsWith(`${slot.spaceName}`)
      );

      if (fillKey && fills[fillKey] !== undefined) {
        const fillValue = fills[fillKey];
        output[`slot_${slot.segmentIndex}`] = fillValue;

        // COMMIT BACK: Add the fill value to the space's existing options
        // Find the parent node in the correct space and add as new child or attribute value
        const targetSpace = registry.spaces.get(slot.spaceName);
        if (targetSpace) {
          // If fill is a new node label, add it as a child
          if (typeof fillValue === "string") {
            // Check if this value already exists as a child
            const parentNode = targetSpace.nodes.get("root");
            if (parentNode) {
              const alreadyExists = parentNode.children.some(childId => {
                const child = targetSpace.nodes.get(childId);
                return child?.label === fillValue;
              });

              if (!alreadyExists) {
                // Add as a new node
                const newId = String(parentNode.children.length);
                const nr = coordToReal(newId);
                const newNode: CBNode = {
                  id: newId,
                  label: String(fillValue),
                  children: [],
                  x: nr,
                  y: nr,
                };
                targetSpace.nodes.set(newId, newNode);
                parentNode.children.push(newId);
                newValuesCommitted++;
              }
            }
          }
        }
      } else {
        remainingSlots.push(slot);
      }
    }

    // Also commit fills that target existing attributes (adding new spectrum values)
    for (const [fillKey, fillValue] of Object.entries(fills)) {
      // Format: "coordinate.attributeName" e.g. "5.0.tweet"
      const parts = fillKey.split(".");
      if (parts.length >= 2) {
        const attrName = parts[parts.length - 1];
        const nodeCoord = parts.slice(0, -1).join(".");

        // Find the node in the resolved path
        for (const resolved of scryResult.resolved) {
          if (resolved.coordinate === nodeCoord) {
            // Find this node in its space — try each space in chain until we find it
            let targetSpace: Space | undefined;
            let node: CBNode | undefined;
            for (let i = resolved.spaceChain.length - 1; i >= 0; i--) {
              targetSpace = registry.spaces.get(resolved.spaceChain[i]);
              if (targetSpace) {
                node = targetSpace.nodes.get(resolved.nodeId);
                if (node) break;
              }
            }
            if (targetSpace && node) {
              // With attributes removed, fills that target "coordinate.attrName" format
              // are reinterpreted as adding a new child node with the fill value as label.
              // Check if a child with this label already exists.
              const alreadyExists = node.children.some(childId => {
                const child = targetSpace!.nodes.get(childId);
                return child?.label === String(fillValue);
              });
              if (!alreadyExists) {
                addNode(targetSpace, node.id, String(fillValue));
                newValuesCommitted++;
              }
              output[fillKey] = fillValue;
            }
          }
        }
      }
    }
  } else {
    // No fills provided — return all slots as remaining
    remainingSlots.push(...scryResult.slots);
  }

  // Determine mode
  const mode: ResolveResult["mode"] =
    scryResult.unresolvedZeros === 0 ? "complete" :
      remainingSlots.length === 0 ? "instance_madlib" :
        "class_madlib";

  return {
    coordinate,
    mode,
    output,
    newValuesCommitted,
    remainingSlots,
  };
}

// ─── Dump: Human-readable representation ─────────────────────────

export function dump(space: Space, registry?: Registry): string {
  const lines: string[] = [];

  function dumpNode(nodeId: NodeId, depth: number): void {
    const node = space.nodes.get(nodeId);
    if (!node) return;

    const indent = "  ".repeat(depth);
    const id = nodeId === "root" ? "root" : nodeId;
    const chainStr = node.producedSpace ? ` → ${node.producedSpace}` : "";
    const stratumStr = node.stratum ? ` <${node.stratum}>` : "";
    const slotStr = node.slotCount !== undefined
      ? ` {${node.children.length}/${node.slotCount} slots}`
      : "";
    const lockStr = node.locked ? " 🔒" : "";
    // Class/Instance notation: C if has unfilled slots, I if locked, ^ if has subspace
    const ciStr = node.locked ? " I"
      : (node.slotCount !== undefined && node.children.length < node.slotCount) ? " C"
        : "";
    const subStr = node.producedSpace ? " ^" : "";
    const childStr = node.children.length > 0 ? ` [${node.children.length} children]` : "";

    lines.push(`${indent}${id}: ${node.label}${ciStr}${subStr}${stratumStr}${slotStr}${lockStr}${childStr}${chainStr}`);

    for (const childId of node.children) {
      dumpNode(childId, depth + 1);
    }
  }

  lines.push(`=== Space: ${space.name} ===`);
  dumpNode(space.rootId, 0);

  // If registry provided, also dump produced spaces
  if (registry) {
    const producedSpaces = new Set<SpaceName>();
    for (const [, node] of space.nodes) {
      if (node.producedSpace) producedSpaces.add(node.producedSpace);
    }
    for (const psName of producedSpaces) {
      const ps = registry.spaces.get(psName);
      if (ps) {
        lines.push("");
        lines.push(dump(ps, registry));
      }
    }
  }

  return lines.join("\n");
}

// ─── Serialization ────────────────────────────────────────────────

export interface SerializedNode {
  id: NodeId;
  label: string;
  children: NodeId[];
  producedSpace?: SpaceName;
  stratum?: Stratum;
  slotCount?: number;
  locked?: boolean;
  terminal?: boolean;
  tags?: string[];         // Serialized as array, hydrated to Set
  x: number;
  y: number;
}

export interface SerializedSpace {
  name: SpaceName;
  rootId: NodeId;
  nodes: SerializedNode[];
}

export function serialize(space: Space): SerializedSpace {
  const nodes: SerializedNode[] = [];
  for (const [, node] of space.nodes) {
    const sn: SerializedNode = {
      id: node.id,
      label: node.label,
      children: [...node.children],
      producedSpace: node.producedSpace,
      x: node.x,
      y: node.y,
    };
    if (node.stratum) sn.stratum = node.stratum;
    if (node.slotCount !== undefined) sn.slotCount = node.slotCount;
    if (node.locked) sn.locked = node.locked;
    if (node.terminal) sn.terminal = node.terminal;
    if (node.tags && node.tags.size > 0) sn.tags = [...node.tags];
    nodes.push(sn);
  }
  return { name: space.name, rootId: space.rootId, nodes };
}

export function deserialize(data: SerializedSpace): Space {
  const nodes = new Map<NodeId, CBNode>();
  for (const sn of data.nodes) {
    const r = sn.x ?? coordToReal(sn.id);
    const cbNode: CBNode = {
      id: sn.id,
      label: sn.label,
      children: [...sn.children],
      producedSpace: sn.producedSpace,
      x: r,
      y: r,
    };
    if (sn.stratum) cbNode.stratum = sn.stratum;
    if (sn.slotCount !== undefined) cbNode.slotCount = sn.slotCount;
    if (sn.locked) cbNode.locked = sn.locked;
    if (sn.terminal) cbNode.terminal = sn.terminal;
    if (sn.tags && sn.tags.length > 0) cbNode.tags = new Set(sn.tags);
    nodes.set(sn.id, cbNode);
  }

  // ═══ INVARIANT REPAIR ═══════════════════════════════════════════
  // CB fundamental: if a node has children, it was defined. Defined = locked.
  // A parent having children means its spectrum was committed — that IS a lock.
  // Repair any legacy data where children were added without locking.
  for (const [, node] of nodes) {
    if (node.children.length >= 2 && !node.locked) {
      node.locked = true;
      if (node.amplitude === undefined) node.amplitude = 1.0;
    }
  }

  return { name: data.name, rootId: data.rootId, nodes, dots: [] };
}

export function toJSON(space: Space): string {
  return JSON.stringify(serialize(space), null, 2);
}

export function fromJSON(json: string): Space {
  return deserialize(JSON.parse(json));
}

// ─── Registry Serialization ───────────────────────────────────────

export function serializeRegistry(registry: Registry): SerializedSpace[] {
  return Array.from(registry.spaces.values()).map(serialize);
}

export function deserializeRegistry(data: SerializedSpace[]): Registry {
  const registry = createRegistry();
  for (const sd of data) {
    registry.spaces.set(sd.name, deserialize(sd));
  }
  return registry;
}

// ═══════════════════════════════════════════════════════════════════
// V1 CORE — Re-factored for v2 registry+forest architecture
// ═══════════════════════════════════════════════════════════════════

// ─── Slot Count (Class/Instance mechanism) ───────────────────────
// slotCount > children.length → CLASS (unfilled slots remain)
// slotCount === children.length → FULLY INSTANTIATED
// No slotCount → unconstrained

export function setSlotCount(space: Space, nodeId: NodeId, count: number): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  if (node.locked) throw new Error(`Node "${nodeId}" is locked`);
  node.slotCount = count;
}

// ─── Lock & Freeze (Instantiation) ─────────────────────────────

/** Lock a node — commits the spectrum. Requires ≥2 children unless terminal.
 *  Terminal = this level is the end of this view. The space changes beyond. */
export function lockNode(space: Space, nodeId: NodeId): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  if (node.locked) return; // Idempotent — already locked
  if (!node.terminal && node.children.length < 2) {
    throw new Error(
      `Cannot lock "${node.label}" (${nodeId}): spectrum requires ≥2 children (has ${node.children.length}). ` +
      `A spectrum needs a high and a low. Mark as terminal if this is where this view ends.`
    );
  }
  node.locked = true;
  // Human lock → full confidence (amplitude = 1.0)
  if (node.amplitude === undefined) {
    node.amplitude = 1.0;
  }
}

/** Freeze a node — pre-lock. Kernel mode skips this during bloom traversal. */
export function freezeNode(space: Space, nodeId: NodeId, frozenBy?: FrozenByMetadata): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  if (node.locked) return; // Already locked — freeze is moot
  node.frozen = true;
  // Freeze also gets full confidence if not already set
  if (node.amplitude === undefined) {
    node.amplitude = 1.0;
  }
  if (frozenBy) {
    node.frozenBy = frozenBy;
  }
}

/** Set the quantum amplitude |ψ|² on a node (LLM confidence 0.0-1.0). */
export function setAmplitude(space: Space, nodeId: NodeId, amplitude: number): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  node.amplitude = Math.max(0, Math.min(1, amplitude)); // Clamp to [0,1]
}

/**
 * Get the effective |ψ|² for a node (kernel-level amplitude).
 * Used for quantum kernel weighting: K_q(x,y) = √(|ψ_x|²·|ψ_y|²) · K(x,y)
 *
 *   - Locked/frozen with amplitude set → amplitude
 *   - Locked/frozen without amplitude → 1.0 (human-settled)
 *   - Unlocked with explicit amplitude → amplitude
 *   - Unlocked without amplitude → 0.0 (superposition — zero kernel contribution)
 *
 * NOTE: Kernel amplitude 0 (superposition) is NOT Born weight 0.
 * Superposition nodes contribute zero to K_q but have UNIFORM Born weight.
 * Use getBornWeight() for sampling/selection.
 */
export function getAmplitude(node: CBNode): number {
  if (node.amplitude !== undefined) return node.amplitude;
  if (node.locked || node.frozen) return 1.0;
  return 0.0; // Superposition = zero kernel contribution (NOT Born 0)
}

/**
 * Get the Born weight for a node (measurement-level probability weight).
 * Used for sampling policy: which slots to fill, which swarm outputs to accept.
 *
 * Two different zeroes:
 *   - Superposition (amplitude undefined) → Born weight = 1.0 (UNIFORM PRIOR)
 *     "This slot is unfilled — it's a candidate for filling. Full opportunity."
 *
 *   - Born 0 (amplitude === 0) → Born weight = 0.0 (EXCLUDED)
 *     "The priors that give this value meaning aren't locked.
 *      Starting here, we know nothing — the encoding is ambiguous."
 *
 *   - Partially settled (0 < amplitude < 1) → Born weight = amplitude
 *     "We have some confidence. Weight accordingly."
 *
 *   - Locked/frozen (amplitude 1.0) → Born weight = 1.0
 *     "Fully committed. Definite."
 */
export function getBornWeight(node: CBNode): number {
  // Superposition = uniform prior, NOT zero
  if (node.amplitude === undefined) {
    if (node.locked || node.frozen) return 1.0; // Human-settled
    return 1.0; // Unfilled slot = full Born weight = opportunity
  }
  // Explicit amplitude set
  return node.amplitude;
  // amplitude === 0 → Born weight = 0 → genuinely excluded
  // This means: "the encoding priors aren't locked, so we can't
  //  interpret this value — it could be from any kernel."
}

/**
 * Is this node in superposition?
 * Superposition = amplitude undefined AND not locked/frozen.
 * These nodes are candidates for filling (high Born weight, zero kernel contribution).
 */
export function isInSuperposition(node: CBNode): boolean {
  return node.amplitude === undefined && !node.locked && !node.frozen;
}

// ─── Entanglement Propagation ──────────────────────────────────
// When a measurement (lock) occurs, the algebra product determines
// how amplitudes propagate. Every weight is derived from the tree
// structure and spectrum sizes — not hardcoded.
//
// The product a*x answers: "if I lock a, what amplitude does x get?"
// The result IS the next kernel state = the next prompt.

export interface EntanglementEvent {
  sourceSpace: SpaceName;
  sourceNodeId: NodeId;
  targetSpace: SpaceName;
  targetNodeId: NodeId;
  amplitudeBefore: number;
  amplitudeAfter: number;
  reason: string;
}

function _getParentNodeId(nodeId: string): string | null {
  if (nodeId === 'root') return null;
  const dot = nodeId.lastIndexOf('.');
  return dot === -1 ? 'root' : nodeId.substring(0, dot);
}

function _algebraWeight(space: Space, aId: string, xId: string, srcAmp: number): number {
  if (aId === xId) return srcAmp * srcAmp;
  const aParent = _getParentNodeId(aId);
  const xParent = _getParentNodeId(xId);

  // a is parent of x
  if (xParent === aId) {
    const aNode = space.nodes.get(aId);
    return srcAmp / Math.max(aNode?.children.length ?? 1, 1);
  }
  // x is parent of a
  if (aParent === xId) {
    const xNode = space.nodes.get(xId);
    return srcAmp / Math.max(xNode?.children.length ?? 1, 1);
  }
  // siblings
  if (aParent !== null && aParent === xParent) {
    const parent = space.nodes.get(aParent);
    return srcAmp / Math.max(parent?.children.length ?? 1, 1);
  }
  return 0;
}

export function propagateEntanglement(
  registry: Registry,
  spaceName: SpaceName,
  nodeId: NodeId,
): EntanglementEvent[] {
  const space = registry.spaces.get(spaceName);
  if (!space) return [];
  const node = space.nodes.get(nodeId);
  if (!node) return [];

  const events: EntanglementEvent[] = [];
  const srcAmp = getAmplitude(node);

  // Same-space: algebra product a*x for all x
  for (const [tId, tNode] of space.nodes) {
    if (tId === nodeId || tNode.locked || tNode.frozen) continue;
    const w = _algebraWeight(space, nodeId, tId, srcAmp);
    if (w <= 0) continue;
    const before = getAmplitude(tNode);
    if (tNode.amplitude === undefined) { tNode.amplitude = w; }
    else { tNode.amplitude = (tNode.amplitude + w) / 2; }
    events.push({
      sourceSpace: spaceName, sourceNodeId: nodeId,
      targetSpace: spaceName, targetNodeId: tId,
      amplitudeBefore: before, amplitudeAfter: getAmplitude(tNode),
      reason: `algebra: ${node.label}*${tNode.label} → ${w.toFixed(3)}`,
    });
  }

  // Cross-space: producedSpace
  if (node.producedSpace) {
    const cs = registry.spaces.get(node.producedSpace);
    if (cs) {
      const root = cs.nodes.get(cs.rootId);
      if (root) {
        const before = getAmplitude(root);
        if (root.amplitude === undefined) root.amplitude = srcAmp;
        events.push({
          sourceSpace: spaceName, sourceNodeId: nodeId,
          targetSpace: node.producedSpace, targetNodeId: cs.rootId,
          amplitudeBefore: before, amplitudeAfter: getAmplitude(root),
          reason: `producedSpace: root = "${node.label}"`,
        });
        const n = Math.max(root.children.length, 1);
        for (const cId of root.children) {
          const c = cs.nodes.get(cId);
          if (!c || c.locked || c.frozen) continue;
          const cb = getAmplitude(c);
          const w = srcAmp / n;
          if (c.amplitude === undefined) { c.amplitude = w; }
          else { c.amplitude = (c.amplitude + w) / 2; }
          events.push({
            sourceSpace: spaceName, sourceNodeId: nodeId,
            targetSpace: node.producedSpace, targetNodeId: cId,
            amplitudeBefore: cb, amplitudeAfter: getAmplitude(c),
            reason: `cross: ${node.label} → 1/${n}`,
          });
        }
      }
    }
  }

  // Cross-space: EWS label resonance
  if (space.ewsRef) {
    const es = registry.spaces.get(space.ewsRef);
    if (es) {
      for (const [eId, eNode] of es.nodes) {
        if (eNode.label !== node.label || eNode.locked || eNode.frozen) continue;
        const before = getAmplitude(eNode);
        const ep = _getParentNodeId(eId);
        const eParent = ep ? es.nodes.get(ep) : null;
        const n = Math.max(eParent?.children.length ?? 1, 1);
        const w = srcAmp / n;
        if (eNode.amplitude === undefined) { eNode.amplitude = w; }
        else { eNode.amplitude = (eNode.amplitude + w) / 2; }
        events.push({
          sourceSpace: spaceName, sourceNodeId: nodeId,
          targetSpace: space.ewsRef, targetNodeId: eId,
          amplitudeBefore: before, amplitudeAfter: getAmplitude(eNode),
          reason: `EWS: "${node.label}" 1/${n}`,
        });
      }
    }
  }

  // Cross-space: reverse lookup
  for (const [oName, oSpace] of registry.spaces) {
    if (oName === spaceName) continue;
    for (const [oId, oNode] of oSpace.nodes) {
      if (oNode.producedSpace !== spaceName || oNode.locked || oNode.frozen) continue;
      const before = getAmplitude(oNode);
      const w = srcAmp / Math.max(oSpace.nodes.size, 1);
      if (oNode.amplitude === undefined) oNode.amplitude = w;
      events.push({
        sourceSpace: spaceName, sourceNodeId: nodeId,
        targetSpace: oName, targetNodeId: oId,
        amplitudeBefore: before, amplitudeAfter: getAmplitude(oNode),
        reason: `reverse: 1/${oSpace.nodes.size}`,
      });
    }
  }

  return events;
}

// ─── Tags & Views ────────────────────────────────────────────────
// Tags are metadata on nodes. Views filter which nodes participate
// in computation. Everything goes in — filtering is views, not deletion.

/** Add a tag to a node. */
export function addTag(space: Space, nodeId: NodeId, tag: string): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  if (!node.tags) node.tags = new Set();
  node.tags.add(tag);
}

/** Remove a tag from a node. */
export function removeTag(space: Space, nodeId: NodeId, tag: string): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  node.tags?.delete(tag);
}

/** Check if a node has a specific tag. */
export function hasTag(space: Space, nodeId: NodeId, tag: string): boolean {
  const node = space.nodes.get(nodeId);
  return node?.tags?.has(tag) ?? false;
}

/** Get all nodes with a specific tag. */
export function getNodesWithTag(space: Space, tag: string): CBNode[] {
  const result: CBNode[] = [];
  for (const [, node] of space.nodes) {
    if (node.tags?.has(tag)) result.push(node);
  }
  return result;
}

/** Get all tags used in a space. */
export function getAllTags(space: Space): Set<string> {
  const tags = new Set<string>();
  for (const [, node] of space.nodes) {
    if (node.tags) {
      for (const tag of node.tags) tags.add(tag);
    }
  }
  return tags;
}

/** Create a default view (no filtering). */
export function createView(name: string, mode: ViewMode = 'all', tags: string[] = []): SpaceView {
  return { name, mode, tags: new Set(tags) };
}

/**
 * Test whether a node passes a view filter.
 * Views filter which nodes participate in traversal/computation.
 *
 *  - 'all':                no filtering, every node passes
 *  - 'exclude_tagged':     nodes WITH any of the view's tags are excluded
 *  - 'include_tagged_only': ONLY nodes WITH any of the view's tags pass
 *  - 'tagged_only':        same as include_tagged_only (alias for clarity)
 */
export function nodePassesView(node: CBNode, view: SpaceView): boolean {
  if (view.mode === 'all' || view.tags.size === 0) return true;

  const nodeTags = node.tags ?? new Set<string>();
  const hasMatchingTag = [...view.tags].some(tag => nodeTags.has(tag));

  switch (view.mode) {
    case 'exclude_tagged':
      return !hasMatchingTag;          // Pass if node does NOT have any of the view's tags
    case 'include_tagged_only':
    case 'tagged_only':
      return hasMatchingTag;           // Pass only if node HAS at least one of the view's tags
    default:
      return true;
  }
}

/**
 * Get children of a node that pass a view filter.
 * This is the integration point — mine/enumerate use this instead of raw node.children.
 */
export function getViewChildren(space: Space, nodeId: NodeId, view?: SpaceView): NodeId[] {
  const node = space.nodes.get(nodeId);
  if (!node) return [];
  if (!view || view.mode === 'all') return node.children;

  return node.children.filter(childId => {
    const child = space.nodes.get(childId);
    return child ? nodePassesView(child, view) : false;
  });
}

// ─── Attach Subspace (Recursive Depth via Registry) ──────────────

export function attachSubspace(
  space: Space,
  nodeId: NodeId,
  childSpace: Space,
): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found in space "${space.name}"`);
  if (node.locked) throw new Error(`Node "${nodeId}" is locked`);
  node.producedSpace = childSpace.name;
}

// ─── Register Space ─────────────────────────────────────────────

export function registerSpace(registry: Registry, space: Space): void {
  registry.spaces.set(space.name, space);
}

// ─── Resolve Coordinate (v1-compat: wraps scry) ─────────────────

export function resolveCoordinate(space: Space, coord: string): CBNode[] {
  const tmpRegistry = createRegistry();
  tmpRegistry.spaces.set(space.name, space);
  const result = scry(tmpRegistry, space.name, coord);
  const nodes: CBNode[] = [];
  for (const resolved of result.resolved) {
    for (let i = resolved.spaceChain.length - 1; i >= 0; i--) {
      const s = tmpRegistry.spaces.get(resolved.spaceChain[i]);
      if (s) {
        const n = s.nodes.get(resolved.nodeId);
        if (n) { nodes.push(n); break; }
      }
    }
  }
  return nodes;
}

// ─── Dewey-Style Addressing DSL ─────────────────────────────────

export interface DeweyAddress {
  raw: string;
  segments: number[];
  levels: ParsedLevel[];
}

export function parseAddress(coord: string): DeweyAddress {
  const parsed = parseCoordinate(coord);
  return { raw: parsed.raw, segments: parsed.segments, levels: parsed.levels };
}

export function renderHuman(addr: DeweyAddress): string {
  if (addr.levels.length === 0) return "(root)";
  return addr.levels.map((level, li) => {
    const parts = level.tokens.map(t => {
      switch (t.type) {
        case 'superposition': return '*';
        case 'select': return String(t.value);
        case 'drill': return '⟨';
        case 'close_drill': return '⟩';
      }
    });
    return `L${li + 1}[${parts.join(",")}]`;
  }).join(" → ");
}

export function toDeweyCode(addr: DeweyAddress): string {
  if (addr.segments.length === 0) return "Ø";
  const parts: string[] = [];
  let i = 0;
  while (i < addr.segments.length) {
    const val = addr.segments[i];
    let count = 1;
    while (i + count < addr.segments.length && addr.segments[i + count] === val) count++;
    parts.push(count > 1 ? `${val}${superscript(count)}` : String(val));
    i += count;
  }
  return parts.join("\u00b7");
}

function superscript(n: number): string {
  const supers: Record<string, string> = {
    "0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074",
    "5": "\u2075", "6": "\u2076", "7": "\u2077", "8": "\u2078", "9": "\u2079",
  };
  return String(n).split("").map(c => supers[c] || c).join("");
}

// ─── Neighbors (Graph Traversal) ────────────────────────────────

export interface NeighborResult {
  node: CBNode;
  distance: number;
  path: NodeId[];
}

export interface NeighborOptions {
  k?: number;
  strict?: boolean;
  includeSubspaces?: boolean;
  depth?: number;
}

export function neighbors(
  space: Space,
  nodeId: NodeId,
  opts: NeighborOptions = {},
): NeighborResult[] {
  const k = opts.k ?? 5;
  const maxDepth = opts.depth ?? 3;
  const results: NeighborResult[] = [];
  const visited = new Set<NodeId>();

  const queue: { id: NodeId; dist: number; path: NodeId[] }[] = [
    { id: nodeId, dist: 0, path: [nodeId] },
  ];

  while (queue.length > 0 && results.length < k) {
    const item = queue.shift()!;
    if (visited.has(item.id)) continue;
    visited.add(item.id);
    const node = space.nodes.get(item.id);
    if (!node) continue;
    if (item.id !== nodeId) {
      results.push({ node, distance: item.dist, path: item.path });
    }
    if (item.dist < maxDepth) {
      for (const childId of node.children) {
        if (!visited.has(childId)) {
          queue.push({ id: childId, dist: item.dist + 1, path: [...item.path, childId] });
        }
      }
      for (const [pid, pnode] of space.nodes) {
        if (pnode.children.includes(item.id) && !visited.has(pid)) {
          queue.push({ id: pid, dist: item.dist + 1, path: [...item.path, pid] });
        }
      }
    }
  }

  return results.sort((a, b) => a.distance - b.distance).slice(0, k);
}

// ─── Boundary Features ──────────────────────────────────────────

export function getBoundaryFeatures(
  space: Space,
  nodeId: NodeId,
): { locked: boolean; hasSlots: boolean; filled: boolean; hasSubspace: boolean } {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found`);
  return {
    locked: !!node.locked,
    hasSlots: node.slotCount !== undefined && node.slotCount > 0,
    filled: node.slotCount !== undefined && node.children.length >= node.slotCount,
    hasSubspace: !!node.producedSpace,
  };
}

// ─── Emergent Generate ──────────────────────────────────────────

export interface EmergentResult {
  name: string;
  components: string[];
  score: number;
  sharedLabels: string[];  // Labels that appear as children in both spaces
}

export function emergentGenerate(
  spaces: Space[],
  outputName: string,
  minScore: number = 1,
): { emergentSpace: Space; results: EmergentResult[] } {
  const tmpRegistry = createRegistry();
  const emergentSpace = createSpace(tmpRegistry, outputName);
  const results: EmergentResult[] = [];

  for (let i = 0; i < spaces.length; i++) {
    for (let j = i + 1; j < spaces.length; j++) {
      const s1 = spaces[i], s2 = spaces[j];

      // Collect all child labels from each space
      const labels1 = new Set<string>();
      const labels2 = new Set<string>();

      for (const [, node] of s1.nodes) {
        for (const childId of node.children) {
          const child = s1.nodes.get(childId);
          if (child) labels1.add(child.label);
        }
      }
      for (const [, node] of s2.nodes) {
        for (const childId of node.children) {
          const child = s2.nodes.get(childId);
          if (child) labels2.add(child.label);
        }
      }

      // Find overlapping labels — shared structure
      const sharedLabels: string[] = [];
      for (const label of labels1) {
        if (labels2.has(label)) sharedLabels.push(label);
      }

      if (sharedLabels.length >= minScore) {
        const name = `${s1.name}\u00d7${s2.name}`;
        results.push({ name, components: [s1.name, s2.name], score: sharedLabels.length, sharedLabels });
        const eNode = addNode(emergentSpace, "root", name);
        for (const label of sharedLabels) {
          addNode(emergentSpace, eNode.id, label);
        }
      }
    }
  }

  return { emergentSpace, results };
}

// ─── Total Space (Composite) ────────────────────────────────────

export function createTotalSpace(
  baseSpaces: Space[],
  transitions: Space[],
  policies: Space[],
  observers: Space[],
  subspaceMap?: Record<string, Space>,
): Space {
  const tmpRegistry = createRegistry();
  const total = createSpace(tmpRegistry, "TotalSpace");

  const basesNode = addNode(total, "root", "spaces");
  setSlotCount(total, basesNode.id, baseSpaces.length);
  for (const bs of baseSpaces) {
    const bNode = addNode(total, basesNode.id, bs.name);
    tmpRegistry.spaces.set(bs.name, bs);
    attachSubspace(total, bNode.id, bs);
  }

  const transNode = addNode(total, "root", "transitions");
  setSlotCount(total, transNode.id, transitions.length);
  for (const t of transitions) {
    const tNode = addNode(total, transNode.id, t.name);
    tmpRegistry.spaces.set(t.name, t);
    attachSubspace(total, tNode.id, t);
  }

  const polNode = addNode(total, "root", "policies");
  setSlotCount(total, polNode.id, policies.length);
  for (const p of policies) {
    const pNode = addNode(total, polNode.id, p.name);
    tmpRegistry.spaces.set(p.name, p);
    attachSubspace(total, pNode.id, p);
  }

  const obsNode = addNode(total, "root", "observers");
  setSlotCount(total, obsNode.id, observers.length);
  for (const o of observers) {
    const oNode = addNode(total, obsNode.id, o.name);
    tmpRegistry.spaces.set(o.name, o);
    attachSubspace(total, oNode.id, o);
  }

  if (subspaceMap) {
    for (const [key, sub] of Object.entries(subspaceMap)) {
      tmpRegistry.spaces.set(key, sub);
    }
  }

  return total;
}

// ─── Extend (Slot Capacity) ─────────────────────────────────────

export function extend(space: Space, nodeId: NodeId, additionalSlots: number): void {
  const node = space.nodes.get(nodeId);
  if (!node) throw new Error(`Node "${nodeId}" not found`);
  if (node.locked) throw new Error(`Node "${nodeId}" is locked`);
  node.slotCount = (node.slotCount || 0) + additionalSlots;
}

// ─── V1-Compatible createCrystalBall ─────────────────────────────

export function createCrystalBall(name: string): Space {
  const registry = createRegistry();
  return createSpace(registry, name);
}

// ─── UARL Builder ────────────────────────────────────────────────
// Construct UARL statements from CB node context.
// Available as preview for any node. On FREEZE, sent to youknow().

/** Map CB Stratum → Y-layer */
const STRATUM_TO_Y: Record<Stratum, string> = {
  universal: 'Y1',          // Upper Ontology
  subclass: 'Y2',           // Domain Ontology
  instance: 'Y3',           // Application Ontology
  instance_universal: 'Y4', // Instance Ontology (fixed point)
  instance_subtype: 'Y5',   // Pattern
  instance_instance: 'Y6',  // Implementation
};

/** Map CB Stratum → Griess phase */
const STRATUM_TO_GRIESS: Record<Stratum, string> = {
  universal: 'derive',
  subclass: 'compute',
  instance: 'build',
  instance_universal: 'verify',
  instance_subtype: 'pattern',
  instance_instance: 'implement',
};

/**
 * Y-Layer Semantic Disambiguation
 *
 * Y strata are ONTOLOGICAL LAYERS — they describe WHAT something IS
 * at different levels of abstraction. They are NOT Griess phases.
 *
 * The Griess constructor (DERIVE→COMPUTE→BUILD→VERIFY) is the
 * CONSTRUCTION PROCESS that runs AT each Y level independently.
 * To reach Y4 (instance), you must have PRODUCED the ontologies
 * at Y1, Y2, Y3 — each with its own mineSpace.
 *
 * VERIFY (Y4) = check that what you have IS a valid instance
 * of Y1×Y2×Y3. You can only verify if you can SEE the mineSpace
 * for each preceding ontology and confirm your instance is a
 * valid point in all of them simultaneously.
 *
 * Y1-Y4 = minimum EWS (every definable thing needs all four)
 * Y5-Y6 = meta-compilation (emerge when Griess VERIFY closes)
 */
export const Y_LAYER_SEMANTICS: Record<string, {
  /** The ontological name of this layer */
  name: string;
  /** What Griess needs you to PRODUCE at this level */
  griessProduces: string;
  /** What mineSpace you need to see to proceed past this level */
  griessRequirement: string;
  /** What to fill at this ontological level */
  fillInstruction: string;
  /** Class (0) or Instance (1-7) */
  classOrInstance: 'class' | 'instance';
}> = {
  Y1: {
    name: 'Upper Ontology',
    griessProduces: 'The TYPE structure — WHAT KIND of thing this is. All dimensions that define the kind.',
    griessRequirement: 'You need a mineSpace showing ALL possible configurations of this kind. Lock when dimensions are complete.',
    fillInstruction: 'WHAT KIND of thing is this? Name ALL the dimensions that define it as a type. Example: EtsyShop has dimensions Product, Branding, Marketing, Operations, Pricing, CustomerExperience, SEO.',
    classOrInstance: 'class',
  },
  Y2: {
    name: 'Domain Ontology',
    griessProduces: 'The DOMAIN — WHERE this thing lives. The specific domain within the Y1 type.',
    griessRequirement: 'You need a mineSpace showing ALL possible configurations within this domain. Choose ONE configuration from Y1 mineSpace to instantiate here.',
    fillInstruction: 'WHERE does this live? Choose a specific configuration from the Y1 mineSpace and define its domain. Example: HandmadeJewelryShop is a specific domain within EtsyShop.',
    classOrInstance: 'class',
  },
  Y3: {
    name: 'Application Ontology',
    griessProduces: 'The OPERATIONS — WHAT you DO with this thing. Concrete actions within the domain.',
    griessRequirement: 'You need a mineSpace showing ALL possible operations within this domain. Choose ONE configuration from Y2 mineSpace to instantiate here.',
    fillInstruction: 'WHAT do you DO with this? Name the concrete operations/applications. Example: StackingRings is a specific application within HandmadeJewelryShop.',
    classOrInstance: 'instance',
  },
  Y4: {
    name: 'Instance Ontology',
    griessProduces: 'The POSITION in mineSpace — produced AUTOMATICALLY when a kernel with Y1+Y2+Y3 is fully locked. The locked kernel IS the instance.',
    griessRequirement: 'A fully locked kernel whose Y1, Y2, Y3 are all defined. Locking produces Y4 = the kernel\'s coordinate in mineSpace. This IS the real thing.',
    fillInstruction: 'You do NOT fill Y4 directly. Y4 is the RESULT of locking a complete Y1+Y2+Y3 kernel. Its position in mineSpace IS the instance.',
    classOrInstance: 'instance',
  },
  Y5: {
    name: 'Instance Type (Next MineSpace Order)',
    griessProduces: 'The NEXT mineSpace — takes Y4 (the locked position) as SEED and opens a new Y1+Y2+Y3 cycle at the next order.',
    griessRequirement: 'A verified Y4 instance. Y5 treats Y4 as a point and asks: what is the mineSpace FROM this point? New dimensions emerge.',
    fillInstruction: 'From the Y4 position: what NEW mineSpace opens up? What are the next-order dimensions? This is the seed for the next recursive cycle.',
    classOrInstance: 'class',
  },
  Y6: {
    name: 'Instance Type Application (Order +2)',
    griessProduces: 'The order AFTER Y5 — another mineSpace from the Y5 structure. Completes the meta-compilation pair.',
    griessRequirement: 'A Y5 mineSpace. Y6 instantiates within that mineSpace, producing a 2-Y4 level position. Then the whole thing recurses infinitely.',
    fillInstruction: 'Instantiate within the Y5 mineSpace. This gives a 2-Y4 level position. The recursion is: Y4→Y5→Y6→(new Y4)→(new Y5)→... infinite.',
    classOrInstance: 'instance',
  },
};

/**
 * Get the semantic description of a Y layer for prompt construction.
 * Returns a human+LLM readable string that disambiguates the Y layer.
 */
export function describeYLayer(yLayer: string): string {
  const sem = Y_LAYER_SEMANTICS[yLayer];
  if (!sem) return `${yLayer} (unknown)`;
  return `${yLayer} ${sem.name} (${sem.classOrInstance}): ${sem.fillInstruction}`;
}

/** Sanitize a label into a valid UARL token */
function sanitizeLabel(label: string): string {
  return label.replace(/[^a-zA-Z0-9_]/g, '_').replace(/^_+|_+$/g, '') || 'unnamed';
}

/** Get the parent node of a given node by parsing its coordinate */
function getParentNode(space: Space, nodeId: NodeId): CBNode | null {
  if (nodeId === 'root' || !nodeId.includes('.')) {
    // Root-level node — parent is root
    return space.nodes.get(space.rootId) || null;
  }
  const parentId = nodeId.substring(0, nodeId.lastIndexOf('.'));
  return space.nodes.get(parentId) || space.nodes.get(space.rootId) || null;
}

export interface UARLStatement {
  subject: string;            // The concept being described
  predicate: string;          // is_a, part_of, produces, etc.
  object: string;             // What it relates to
  additionalPredicates: Record<string, string>;  // y_layer, griess_phase, etc.
  raw: string;                // Full UARL string for youknow()
}

/**
 * Build a UARL statement from a CB node.
 * Always available as a preview. On FREEZE, the raw string goes to youknow().
 */
export function buildUARL(space: Space, nodeId: NodeId): UARLStatement | null {
  const node = space.nodes.get(nodeId);
  if (!node) return null;

  const subject = sanitizeLabel(node.label);
  const stratum = node.stratum || 'instance';
  const yLayer = STRATUM_TO_Y[stratum] || 'Y3';
  const griessPhase = STRATUM_TO_GRIESS[stratum] || 'build';

  // Determine predicate and object from context
  const parent = getParentNode(space, nodeId);
  const parentLabel = parent ? sanitizeLabel(parent.label) : 'Entity';

  // Primary claim: is_a parent
  const predicate = 'is_a';
  const object = parentLabel;

  // Additional predicates
  const additional: Record<string, string> = {
    y_layer: yLayer,
    griess_phase: griessPhase,
  };

  // Add Y-layer semantic disambiguation for LLM consumption
  const ySem = Y_LAYER_SEMANTICS[yLayer];
  if (ySem) {
    additional['y_layer_meaning'] = ySem.name;
    additional['abstraction'] = ySem.classOrInstance;
    additional['griess_produces'] = ySem.griessProduces;
  }

  // If node has children → it has parts (O-strata)
  if (node.children.length > 0) {
    const childLabels = node.children
      .map(cid => space.nodes.get(cid))
      .filter((n): n is CBNode => !!n)
      .map(n => sanitizeLabel(n.label));
    if (childLabels.length > 0) {
      additional['has_part'] = childLabels.join(', ');
    }
  }

  // If node produces a space → produces claim
  if (node.producedSpace) {
    additional['produces'] = sanitizeLabel(node.producedSpace);
  }

  // If node is at coordinate 0 (class) vs 1-7 (instance)
  const coordSegments = nodeId.split('.');
  const lastSegment = coordSegments[coordSegments.length - 1];
  if (lastSegment === '0') {
    additional['class_instance'] = 'class';
  } else {
    additional['class_instance'] = 'instance';
  }

  // Build raw UARL string
  const additionalStr = Object.entries(additional)
    .map(([k, v]) => `${k} ${v}`)
    .join(', ');
  const raw = `${subject} ${predicate} ${object}, ${additionalStr}`;

  return { subject, predicate, object, additionalPredicates: additional, raw };
}

/**
 * Build UARL statements for ALL nodes in a space.
 * Useful for previewing the entire ontology a kernel represents.
 */
export function buildSpaceUARL(space: Space): UARLStatement[] {
  const statements: UARLStatement[] = [];
  for (const [nodeId] of space.nodes) {
    if (nodeId === space.rootId) continue; // Skip root
    const stmt = buildUARL(space, nodeId);
    if (stmt) statements.push(stmt);
  }
  return statements;
}

export interface FreezeResult {
  frozen: boolean;
  uarl: UARLStatement | null;
  youknowResult: string | null;  // null if youknow not available
  accepted: boolean;             // did youknow accept?
}

/**
 * Freeze a node AND validate via YOUKNOW.
 *
 * This is the ONLY CB operation that triggers YOUKNOW validation.
 * - Constructs the UARL statement from the node context
 * - Calls youknow() for validation
 * - If accepted → freezes the node with 'youknow' surrogate
 * - If rejected → does NOT freeze, returns the rejection reason
 *
 * @param youknowFn - The youknow() compiler function. Injected so the
 *   library doesn't depend on Python directly. The engine/MCP provides it.
 */
export async function freezeWithYouknow(
  space: Space,
  nodeId: NodeId,
  youknowFn?: (statement: string) => Promise<string>,
): Promise<FreezeResult> {
  const node = space.nodes.get(nodeId);
  if (!node) return { frozen: false, uarl: null, youknowResult: 'Node not found', accepted: false };
  if (node.locked) return { frozen: false, uarl: null, youknowResult: 'Already locked', accepted: false };

  // Build the UARL statement
  const uarl = buildUARL(space, nodeId);
  if (!uarl) return { frozen: false, uarl: null, youknowResult: 'Could not build UARL', accepted: false };

  // If no youknow function provided, just freeze (legacy behavior)
  if (!youknowFn) {
    freezeNode(space, nodeId);
    return { frozen: true, uarl, youknowResult: null, accepted: true };
  }

  // Call youknow() for validation
  try {
    const result = await youknowFn(uarl.raw);
    const accepted = result === 'OK';

    if (accepted) {
      freezeNode(space, nodeId, {
        surrogate: 'youknow',
        timestamp: Date.now(),
        reversible: true,
        proof: uarl.raw,
      });
    }

    return { frozen: accepted, uarl, youknowResult: result, accepted };
  } catch (err) {
    // YOUKNOW error — freeze anyway but mark as unvalidated
    freezeNode(space, nodeId, {
      surrogate: 'youknow_error',
      timestamp: Date.now(),
      reversible: true,
      proof: `Error: ${err}`,
    });
    return { frozen: true, uarl, youknowResult: `Error: ${err}`, accepted: false };
  }
}

// ─── Kernel → MAP Builder ────────────────────────────────────────
// Convert a CB kernel's state into a MAP (Lisp) program.
// Locked nodes = bound values. Unlocked = zeroes (superpositions).

export interface MAPProgram {
  source: string;
  bindings: Record<string, string>;
  zeroes: string[];
  spaceName: string;
}

/**
 * Convert a kernel's current state into a MAP program.
 *
 * Each node becomes a MAP binding:
 *   - Locked/frozen nodes → {bind NAME ~NAME}
 *   - Unlocked nodes → {bind NAME NIL} (zero, needs settling)
 *
 * Children become list members of their parent.
 * The MAP program can be executed to produce the instantiation.
 */
export function kernelToMAP(space: Space): MAPProgram {
  const bindings: Record<string, string> = {};
  const zeroes: string[] = [];
  const lines: string[] = [];

  lines.push(`; MAP instantiation of kernel: ${space.name}`);
  lines.push(`; Generated from Crystal Ball`);
  lines.push('');

  function walk(nodeId: NodeId, depth: number) {
    const node = space.nodes.get(nodeId);
    if (!node) return;

    const name = sanitizeLabel(node.label).toUpperCase();
    const isSettled = node.locked || node.frozen;

    if (node.children.length > 0) {
      const childLabels = node.children
        .map(cid => space.nodes.get(cid))
        .filter((n): n is CBNode => !!n)
        .map(n => sanitizeLabel(n.label).toUpperCase());

      const listExpr = `{list ${childLabels.map(c => `~${c}`).join(' ')}}`;

      if (isSettled) {
        lines.push(`{bind ${name} ${listExpr}}`);
        bindings[name] = listExpr;
      } else {
        lines.push(`{bind ${name} ${listExpr}}  ; zero`);
        zeroes.push(name);
      }

      for (const childId of node.children) {
        walk(childId, depth + 1);
      }
    } else {
      if (isSettled) {
        lines.push(`{bind ${name} ~${name}}`);
        bindings[name] = name;
      } else {
        lines.push(`{bind ${name} NIL}  ; zero — needs settling`);
        zeroes.push(name);
      }
    }
  }

  const root = space.nodes.get(space.rootId);
  if (root) {
    for (const childId of root.children) {
      walk(childId, 0);
    }
  }

  lines.push('');
  if (zeroes.length > 0) {
    lines.push(`; ${zeroes.length} zeroes need settling: ${zeroes.join(', ')}`);
  } else {
    lines.push('; All slots filled — ready to instantiate');
  }

  if (root && root.children.length > 0) {
    const topLabels = root.children
      .map(cid => space.nodes.get(cid))
      .filter((n): n is CBNode => !!n)
      .map(n => sanitizeLabel(n.label).toUpperCase());
    lines.push(`{list ${topLabels.join(' ')}}`);
  }

  return {
    source: lines.join('\n'),
    bindings,
    zeroes,
    spaceName: space.name,
  };
}
