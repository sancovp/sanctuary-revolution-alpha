// Crystal Ball - Kernel

export type NodeId = string;
export type SpectrumValue = string | number | boolean;
export type Spectrum = SpectrumValue[];

export interface Attribute {
  name: string;
  spectrum: Spectrum;  // possible values
  defaultValue?: SpectrumValue;
}

export interface OntologyNode {
  id: NodeId;
  label: string;
  children: NodeId[];
  slotCount: number;
  locked: boolean;
  attributes: Map<string, Attribute>;
  subspace?: CrystalBall;  // Reference to another space
}

export interface CrystalBall {
  rootId: NodeId;
  nodes: Map<NodeId, OntologyNode>;
  locked: boolean;
  name: string;
}

export interface ParsedAddress {
  raw: string;
  levels: number[][];
}

export interface CollapseBounds {
  // 1-based inclusive range over child slots when encountering superposition (0).
  start: number;
  end: number;
  // Max candidates to keep per superposition expansion step.
  limit?: number;
  // Collapse strategy when more candidates than limit.
  strategy?: "first" | "random";
}

export type ScoreActor = "agent" | "user";

export interface ScoreEntry {
  entryId: string;
  targetNodeId: NodeId;
  actor: ScoreActor;
  score: number;
  timestamp: string;
  note?: string;
}

// Parse a coordinate string into levels
// Each level is separated by dots
// Each level has multiple slots (digits)
export function parseCoordinate(coord: string): number[][] {
  const parts = coord.split('.').filter(p => p.length > 0);
  
  return parts.map(part => {
    const slots: number[] = [];
    let slotIndex = 0;
    
    for (const char of part) {
      const digit = parseInt(char, 10);
      
      if (digit === 0) {
        // Superposition: add 0, reset slot position
        slots.push(0);
        slotIndex = 0;
      } else if (digit === 9) {
        // Wrap: move to next slot position
        slotIndex++;
      } else {
        // Normal digit: add to current slot
        while (slots.length <= slotIndex) {
          slots.push(0);
        }
        slots[slotIndex] = digit;
        slotIndex++;
      }
    }
    
    return slots;
  });
}

// Parse address string for CLI rendering helpers.
export function parseAddress(address: string): ParsedAddress {
  return {
    raw: address,
    levels: parseCoordinate(address),
  };
}

// Render parsed address as a stable Dewey-like code.
export function toDeweyCode(parsed: ParsedAddress): string {
  return parsed.levels
    .map(level => (level.length === 0 ? "0" : level.join("")))
    .join(".");
}

// Human-readable rendering for debugging/CLI usage.
export function renderHuman(parsed: ParsedAddress): string {
  if (parsed.levels.length === 0) {
    return "root";
  }
  return parsed.levels
    .map((level, index) => `L${index + 1}[${level.join(",")}]`)
    .join(" -> ");
}

// Resolve a coordinate to a SET of nodes
// Returns all possible nodes that match the coordinate
export function resolveCoordinate(cb: CrystalBall, coord: string): OntologyNode[] {
  const levels = parseCoordinate(coord);
  
  if (levels.length === 0) return [];
  
  // Start with root
  const root = cb.nodes.get(cb.rootId);
  if (!root) return [];
  
  // BFS through levels
  let currentNodes: OntologyNode[] = [root];
  
  for (let levelIdx = 0; levelIdx < levels.length; levelIdx++) {
    const slots = levels[levelIdx];
    const nextNodes: OntologyNode[] = [];
    
    for (const node of currentNodes) {
      // If node has no children, skip
      if (node.children.length === 0) continue;
      
      // Check if any slot is 0 (superposition)
      const hasSuperposition = slots.includes(0);
      
      if (hasSuperposition) {
        // Superposition: get ALL children
        for (const childId of node.children) {
          const child = cb.nodes.get(childId);
          if (child) nextNodes.push(child);
        }
      } else {
        // Normal selection: map each slot to a child
        for (const slot of slots) {
          if (slot === 0) continue; // skip
          // Map 1-8 to 0-based index, wrap
          const childIndex = (slot - 1) % node.children.length;
          const childId = node.children[childIndex];
          const child = cb.nodes.get(childId);
          if (child) nextNodes.push(child);
        }
      }
    }
    
    currentNodes = nextNodes;
    if (currentNodes.length === 0) break;
  }
  
  return currentNodes;
}

// Resolve with bounded collapse for superposition coordinates.
// When a level includes 0, instead of expanding to ALL children, we restrict to
// a bounded slot window and optionally cap fanout.
export function resolveCoordinateBounded(
  cb: CrystalBall,
  coord: string,
  bounds: CollapseBounds
): OntologyNode[] {
  const levels = parseCoordinate(coord);
  if (levels.length === 0) return [];

  const root = cb.nodes.get(cb.rootId);
  if (!root) return [];

  const start = Math.max(1, Math.floor(bounds.start));
  const end = Math.max(start, Math.floor(bounds.end));
  const limit = bounds.limit && bounds.limit > 0 ? Math.floor(bounds.limit) : undefined;
  const strategy = bounds.strategy ?? "first";

  let currentNodes: OntologyNode[] = [root];

  for (let levelIdx = 0; levelIdx < levels.length; levelIdx++) {
    const slots = levels[levelIdx];
    const nextNodes: OntologyNode[] = [];

    for (const node of currentNodes) {
      if (node.children.length === 0) continue;

      const hasSuperposition = slots.includes(0);
      if (hasSuperposition) {
        // Restrict child selection to the specified 1-based slot window.
        const lo = Math.min(start, node.children.length);
        const hi = Math.min(end, node.children.length);
        if (lo > hi) continue;

        const candidates: OntologyNode[] = [];
        for (let idx1 = lo; idx1 <= hi; idx1++) {
          const childId = node.children[idx1 - 1];
          const child = cb.nodes.get(childId);
          if (child) candidates.push(child);
        }

        if (limit !== undefined && candidates.length > limit) {
          if (strategy === "random") {
            // Fisher-Yates (partial) to choose a random subset.
            for (let i = candidates.length - 1; i > 0; i--) {
              const j = Math.floor(Math.random() * (i + 1));
              const tmp = candidates[i];
              candidates[i] = candidates[j];
              candidates[j] = tmp;
            }
          }
          nextNodes.push(...candidates.slice(0, limit));
        } else {
          nextNodes.push(...candidates);
        }
      } else {
        // Normal selection as in resolveCoordinate.
        for (const slot of slots) {
          if (slot === 0) continue;
          const childIndex = (slot - 1) % node.children.length;
          const childId = node.children[childIndex];
          const child = cb.nodes.get(childId);
          if (child) nextNodes.push(child);
        }
      }
    }

    // Deduplicate by node id each step to control blowup.
    const uniq = new Map<string, OntologyNode>();
    for (const n of nextNodes) {
      if (!uniq.has(n.id)) uniq.set(n.id, n);
    }
    currentNodes = Array.from(uniq.values());
    if (currentNodes.length === 0) break;
  }

  return currentNodes;
}

// Create a new Crystal Ball with just a root
export function createCrystalBall(name: string = "Root"): CrystalBall {
  const rootId = "root";
  return {
    rootId,
    name,
    nodes: new Map([[rootId, {
      id: rootId,
      label: name,
      children: [],
      slotCount: 0,
      locked: false,
      attributes: new Map()
    }]]),
    locked: false
  };
}

// Add a child node under a parent
export function addNode(
  cb: CrystalBall,
  parentId: NodeId,
  label: string
): OntologyNode {
  const parent = cb.nodes.get(parentId);
  if (!parent) throw new Error(`Parent node ${parentId} not found`);
  
  const id = `${parentId}.${parent.children.length}`;
  const node: OntologyNode = {
    id,
    label,
    children: [],
    slotCount: 0,
    locked: false,
    attributes: new Map()
  };
  
  cb.nodes.set(id, node);
  parent.children.push(id);
  
  return node;
}

export function setSlotCount(cb: CrystalBall, nodeId: NodeId, slots: number): void {
  const node = cb.nodes.get(nodeId);
  if (!node) throw new Error(`Node ${nodeId} not found`);
  if (node.locked) throw new Error(`Node ${nodeId} is locked`);
  node.slotCount = slots;
}

export function lockNode(cb: CrystalBall, nodeId: NodeId): void {
  const node = cb.nodes.get(nodeId);
  if (!node) throw new Error(`Node ${nodeId} not found`);
  node.locked = true;
}

// Attach a subspace to a node (composition)
export function attachSubspace(cb: CrystalBall, nodeId: NodeId, subspace: CrystalBall): void {
  const node = cb.nodes.get(nodeId);
  if (!node) throw new Error(`Node ${nodeId} not found`);
  if (node.locked) throw new Error(`Node ${nodeId} is locked`);
  
  node.subspace = subspace;
}

// Get the subspace of a node (if any)
export function getSubspace(node: OntologyNode): CrystalBall | undefined {
  return node.subspace;
}

// Add an attribute with spectrum to a node
export function addAttribute(
  cb: CrystalBall,
  nodeId: NodeId,
  name: string,
  spectrum: Spectrum,
  defaultValue?: SpectrumValue
): void {
  const node = cb.nodes.get(nodeId);
  if (!node) throw new Error(`Node ${nodeId} not found`);
  if (node.locked) throw new Error(`Node ${nodeId} is locked`);
  
  node.attributes.set(name, { name, spectrum, defaultValue });
}

// Get an attribute from a node
export function getAttribute(node: OntologyNode, name: string): Attribute | undefined {
  return node.attributes.get(name);
}

// Get all attributes from a node
export function getAttributes(node: OntologyNode): Attribute[] {
  return Array.from(node.attributes.values());
}

function ensureScoreHistoryNode(cb: CrystalBall): OntologyNode {
  const root = cb.nodes.get(cb.rootId);
  if (!root) throw new Error("Root node not found");

  for (const childId of root.children) {
    const child = cb.nodes.get(childId);
    if (child?.label === "score_history") return child;
  }

  const history = addNode(cb, cb.rootId, "score_history");
  if (!root.locked) {
    setSlotCount(cb, cb.rootId, root.children.length);
  }
  return history;
}

export function recordScore(
  cb: CrystalBall,
  targetNodeId: NodeId,
  actor: ScoreActor,
  score: number,
  note?: string,
  timestamp?: string
): OntologyNode {
  if (!cb.nodes.has(targetNodeId)) {
    throw new Error(`Target node ${targetNodeId} not found`);
  }
  if (!Number.isFinite(score)) {
    throw new Error(`Score must be a finite number, got: ${score}`);
  }

  const history = ensureScoreHistoryNode(cb);
  const entry = addNode(cb, history.id, `score_${history.children.length}`);
  const ts = timestamp ?? new Date().toISOString();

  addAttribute(cb, entry.id, "type", ["score_entry"], "score_entry");
  addAttribute(cb, entry.id, "targetNodeId", [targetNodeId], targetNodeId);
  addAttribute(cb, entry.id, "actor", [actor], actor);
  addAttribute(cb, entry.id, "score", [score], score);
  addAttribute(cb, entry.id, "timestamp", [ts], ts);
  if (note && note.trim().length > 0) {
    addAttribute(cb, entry.id, "note", [note], note);
  }

  if (!history.locked) {
    setSlotCount(cb, history.id, history.children.length);
  }
  return entry;
}

function parseScoreEntry(node: OntologyNode): ScoreEntry | null {
  const target = node.attributes.get("targetNodeId")?.defaultValue;
  const actor = node.attributes.get("actor")?.defaultValue;
  const score = node.attributes.get("score")?.defaultValue;
  const timestamp = node.attributes.get("timestamp")?.defaultValue;
  const note = node.attributes.get("note")?.defaultValue;

  if (typeof target !== "string") return null;
  if (actor !== "agent" && actor !== "user") return null;
  if (typeof score !== "number") return null;
  if (typeof timestamp !== "string") return null;

  return {
    entryId: node.id,
    targetNodeId: target,
    actor,
    score,
    timestamp,
    note: typeof note === "string" ? note : undefined,
  };
}

export function getScoreHistory(
  cb: CrystalBall,
  targetNodeId?: NodeId,
  actor?: ScoreActor
): ScoreEntry[] {
  const root = cb.nodes.get(cb.rootId);
  if (!root) return [];

  let history: OntologyNode | undefined;
  for (const childId of root.children) {
    const child = cb.nodes.get(childId);
    if (child?.label === "score_history") {
      history = child;
      break;
    }
  }
  if (!history) return [];

  const entries: ScoreEntry[] = [];
  for (const entryId of history.children) {
    const node = cb.nodes.get(entryId);
    if (!node) continue;
    const parsed = parseScoreEntry(node);
    if (!parsed) continue;
    if (targetNodeId && parsed.targetNodeId !== targetNodeId) continue;
    if (actor && parsed.actor !== actor) continue;
    entries.push(parsed);
  }

  entries.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  return entries;
}

// Set a specific value for an attribute on a node
export function setAttributeValue(
  cb: CrystalBall,
  nodeId: NodeId,
  name: string,
  value: SpectrumValue
): void {
  const node = cb.nodes.get(nodeId);
  if (!node) throw new Error(`Node ${nodeId} not found`);
  
  const attr = node.attributes.get(name);
  if (!attr) throw new Error(`Attribute ${name} not found on node ${nodeId}`);
  
  if (!attr.spectrum.includes(value)) {
    throw new Error(`Value ${value} not in spectrum for ${name}`);
  }
  
  node.attributes.set(name, { ...attr, defaultValue: value });
}

export function dump(cb: CrystalBall): string {
  const lines: string[] = [];
  
  function dumpNode(nodeId: string, indent: number = 0): void {
    const node = cb.nodes.get(nodeId);
    if (!node) return;
    
    const prefix = '  '.repeat(indent);
    const lockStr = node.locked ? ' [LOCKED]' : '';
    const slotStr = node.slotCount > 0 ? ` slots=${node.slotCount}` : '';
    const childStr = node.children.length > 0 ? ` [${node.children.length} children]` : '';
    lines.push(`${prefix}${node.id}: ${node.label}${slotStr}${lockStr}${childStr}`);
    
    // Dump attributes
    if (node.attributes.size > 0) {
      for (const [name, attr] of node.attributes) {
        const vals = attr.spectrum.join(', ');
        const def = attr.defaultValue !== undefined ? ` = ${attr.defaultValue}` : '';
        lines.push(`${prefix}  @${name}: [${vals}]${def}`);
      }
    }
    
    for (const childId of node.children) {
      dumpNode(childId, indent + 1);
    }
  }
  
  dumpNode(cb.rootId);
  return lines.join('\n');
}

// === Space Registry ===

export interface SerializedAttribute {
  name: string;
  spectrum: Spectrum;
  defaultValue?: SpectrumValue;
}

export interface SerializedNode {
  id: NodeId;
  label: string;
  children: NodeId[];
  slotCount: number;
  locked: boolean;
  attributes: SerializedAttribute[];
  subspaceName?: string;  // Reference to another space by name
}

export interface SerializedCrystalBall {
  name: string;
  rootId: NodeId;
  nodes: SerializedNode[];
  locked: boolean;
}

export interface SpaceRegistry {
  spaces: Map<string, CrystalBall>;
  onSave?: (name: string, data: SerializedCrystalBall) => Promise<void>;
  onLoad?: (name: string) => Promise<SerializedCrystalBall | null>;
  onDelete?: (name: string) => Promise<void>;
}

export function createRegistry(): SpaceRegistry {
  return {
    spaces: new Map()
  };
}

// Serialize a CrystalBall to JSON-compatible object
export function serialize(cb: CrystalBall): SerializedCrystalBall {
  const nodes: SerializedNode[] = [];
  
  for (const [id, node] of cb.nodes) {
    const attributes: SerializedAttribute[] = [];
    for (const [name, attr] of node.attributes) {
      attributes.push({
        name: attr.name,
        spectrum: attr.spectrum,
        defaultValue: attr.defaultValue
      });
    }
    
    nodes.push({
      id: node.id,
      label: node.label,
      children: node.children,
      slotCount: node.slotCount,
      locked: node.locked,
      attributes,
      subspaceName: node.subspace?.name
    });
  }
  
  return {
    name: cb.name,
    rootId: cb.rootId,
    nodes,
    locked: cb.locked
  };
}

// Deserialize to CrystalBall (requires registry to resolve subspaces)
export function deserialize(
  data: SerializedCrystalBall,
  registry: SpaceRegistry
): CrystalBall {
  const nodes = new Map<NodeId, OntologyNode>();
  
  // First pass: create all nodes
  for (const nodeData of data.nodes) {
    nodes.set(nodeData.id, {
      id: nodeData.id,
      label: nodeData.label,
      children: nodeData.children,
      slotCount: nodeData.slotCount,
      locked: nodeData.locked,
      attributes: new Map()
    });
  }
  
  // Second pass: restore attributes and subspaces
  for (const nodeData of data.nodes) {
    const node = nodes.get(nodeData.id)!;
    
    // Restore attributes
    for (const attrData of nodeData.attributes) {
      node.attributes.set(attrData.name, {
        name: attrData.name,
        spectrum: attrData.spectrum,
        defaultValue: attrData.defaultValue
      });
    }
    
    // Restore subspace reference
    if (nodeData.subspaceName) {
      const subspace = registry.spaces.get(nodeData.subspaceName);
      if (subspace) {
        node.subspace = subspace;
      }
    }
  }
  
  return {
    name: data.name,
    rootId: data.rootId,
    nodes,
    locked: data.locked
  };
}

// Save to JSON string
export function toJSON(cb: CrystalBall): string {
  return JSON.stringify(serialize(cb), null, 2);
}

// Load from JSON string (requires registry)
export function fromJSON(json: string, registry: SpaceRegistry): CrystalBall {
  const data = JSON.parse(json) as SerializedCrystalBall;
  return deserialize(data, registry);
}

// Registry operations
export function registerSpace(registry: SpaceRegistry, cb: CrystalBall): void {
  registry.spaces.set(cb.name, cb);
  
  // Trigger save hook if present
  if (registry.onSave) {
    registry.onSave(cb.name, serialize(cb)).catch(console.error);
  }
}

export function getSpace(registry: SpaceRegistry, name: string): CrystalBall | undefined {
  return registry.spaces.get(name);
}

export async function loadSpace(registry: SpaceRegistry, name: string): Promise<CrystalBall | null> {
  // Try in-memory first
  const cached = registry.spaces.get(name);
  if (cached) return cached;
  
  // Try load hook
  if (registry.onLoad) {
    const data = await registry.onLoad(name);
    if (data) {
      const cb = deserialize(data, registry);
      registry.spaces.set(name, cb);
      return cb;
    }
  }
  
  return null;
}

export async function deleteSpace(registry: SpaceRegistry, name: string): Promise<void> {
  registry.spaces.delete(name);
  
  if (registry.onDelete) {
    await registry.onDelete(name);
  }
}

// DB Mirror Hook - example implementation
export function createDBMirror(
  saveFn: (name: string, data: SerializedCrystalBall) => Promise<void>,
  loadFn: (name: string) => Promise<SerializedCrystalBall | null>,
  deleteFn: (name: string) => Promise<void>
): SpaceRegistry {
  return {
    spaces: new Map(),
    onSave: saveFn,
    onLoad: loadFn,
    onDelete: deleteFn
  };
}

// ============================================================
// BOUNDARY FEATURES - For neighbor rectification
// ============================================================

export interface BoundaryFeatures {
  ancestry: string[];      // Path from root (e.g., ["root", "root.0", "root.0.1"])
  isLocked: boolean;      // Is this node/space locked?
  slotCount: number;      // Current slot configuration
  attributes: string[];   // Attribute names present
  hasSubspace: boolean;   // Does this node have a subspace?
  depth: number;         // Distance from root
}

// Extract boundary features from a node
export function getBoundaryFeatures(cb: CrystalBall, nodeId: NodeId): BoundaryFeatures {
  const node = cb.nodes.get(nodeId);
  if (!node) {
    return {
      ancestry: [],
      isLocked: cb.locked,
      slotCount: 0,
      attributes: [],
      hasSubspace: false,
      depth: 0
    };
  }
  
  // Compute ancestry from node ID (e.g., "root.0.1" -> ["root", "root.0", "root.0.1"])
  const ancestry: string[] = [];
  const parts = nodeId.split('.');
  let current = '';
  for (const part of parts) {
    current = current ? `${current}.${part}` : part;
    ancestry.push(current);
  }
  
  return {
    ancestry,
    isLocked: node.locked || cb.locked,
    slotCount: node.slotCount,
    attributes: Array.from(node.attributes.keys()),
    hasSubspace: !!node.subspace,
    depth: ancestry.length - 1
  };
}

// Check if two nodes have boundary interference
export function hasBoundaryInterference(
  f1: BoundaryFeatures,
  f2: BoundaryFeatures,
  strict: boolean = false
): boolean {
  // 1. Different ancestry (diverged region)
  // Only flag as interference if they've diverged at depth > 1 (siblings or deeper)
  // Direct children (depth 1) are always allowed as neighbors
  const minLen = Math.min(f1.ancestry.length, f2.ancestry.length);
  let divergedAt = -1;
  for (let i = 0; i < minLen; i++) {
    if (f1.ancestry[i] !== f2.ancestry[i]) {
      divergedAt = i;
      break;
    }
  }
  
  // If diverged at depth >= 2, that's a real region split (siblings or cousins)
  if (divergedAt >= 2) {
    // They're in different branches (cousins or beyond)
    return true;
  }
  // Divergence at depth 1 (direct child) is fine - they're neighbors
  
  // 2. Locked boundary crossing (DIRECTED membrane)
  // Allow: locked → unlocked (exploration from authoritative)
  // Reject: unlocked → locked (contamination of canon)
  if (f1.isLocked !== f2.isLocked) {
    // If going FROM unlocked TO locked, that's forbidden
    if (!f1.isLocked && f2.isLocked) {
      return true;  // blocked: trying to contaminate locked
    }
    // If going FROM locked TO unlocked, that's allowed (exploration)
    // No boundary crossed in this direction
  }
  
  // 3. Slot regime mismatch (DIRECTED)
  // Allow: higher slots → lower slots (refinement)
  // Reject: lower → higher (can't expand into undefined slots)
  if (strict && f1.slotCount !== f2.slotCount) {
    // If going from more slots to fewer, that's refinement (allowed)
    // If going from fewer to more, that's expansion into unknown (forbidden)
    if (f1.slotCount > 0 && f2.slotCount === 0) {
      // Moving to unslotted region - allowed (refinement)
    } else if (f1.slotCount === 0 && f2.slotCount > 0) {
      // Moving to slotted region from unslotted - forbidden
      return true;
    }
  }
  
  // 4. Attribute spectrum incompatibility
  const attrs1 = new Set(f1.attributes);
  const attrs2 = new Set(f2.attributes);
  const intersection = new Set([...attrs1].filter(x => attrs2.has(x)));
  if (strict && intersection.size === 0 && attrs1.size > 0 && attrs2.size > 0) {
    // No shared attributes
    return true;
  }
  
  // 5. Subspace boundary crossing
  if (f1.hasSubspace !== f2.hasSubspace) {
    return true;
  }
  
  return false;
}

// ============================================================
// NEIGHBORS - With boundary rectification
// ============================================================

export interface NeighborOptions {
  k: number;           // Number of neighbors
  strict: boolean;     // Strict boundary enforcement
  includeSubspaces: boolean;  // Allow subspace jumps
  depth: number;       // Max depth for graph traversal
}

export interface NeighborResult {
  node: OntologyNode;
  distance: number;
  features: BoundaryFeatures;
  boundaryCrossed: string[];
}

// Get neighbors of a node with boundary rectification
export function neighbors(
  cb: CrystalBall,
  nodeId: NodeId,
  options: Partial<NeighborOptions> = {}
): NeighborResult[] {
  const opts: NeighborOptions = {
    k: options.k ?? 5,
    strict: options.strict ?? false,
    includeSubspaces: options.includeSubspaces ?? true,
    depth: options.depth ?? 3
  };
  
  const node = cb.nodes.get(nodeId);
  if (!node) return [];
  
  const sourceFeatures = getBoundaryFeatures(cb, nodeId);
  const candidates: NeighborResult[] = [];
  
  // 1. Graph neighbors (children)
  if (node.children.length > 0) {
    for (const childId of node.children) {
      const child = cb.nodes.get(childId);
      if (child) {
        const features = getBoundaryFeatures(cb, childId);
        const crossed: string[] = [];
        
        // Check interference with strict mode
        const interference = hasBoundaryInterference(sourceFeatures, features, opts.strict);
        if (interference) {
          crossed.push('interference');
        }
        
        candidates.push({
          node: child,
          distance: 1,
          features,
          boundaryCrossed: crossed
        });
      }
    }
  }
  
  // 2. Parent neighbors (siblings)
  for (const [id, n] of cb.nodes) {
    if (n.children.includes(nodeId) && id !== nodeId) {
      const sibling = n;
      for (const sibId of sibling.children) {
        if (sibId === nodeId) continue;
        const sib = cb.nodes.get(sibId);
        if (sib) {
          const features = getBoundaryFeatures(cb, sibId);
          candidates.push({
            node: sib,
            distance: 2,  // sibling = distance 2
            features,
            boundaryCrossed: []
          });
        }
      }
    }
  }
  
  // 3. Subspace neighbors (composition jumps)
  if (opts.includeSubspaces && node.subspace) {
    const subRoot = node.subspace.nodes.get(node.subspace.rootId);
    if (subRoot) {
      const features = getBoundaryFeatures(node.subspace, node.subspace.rootId);
      candidates.push({
        node: subRoot,
        distance: 1,
        features,
        boundaryCrossed: ['subspace']
      });
    }
  }
  
  // Rectify: filter or weight based on boundaries
  const rectified = candidates.filter(c => {
    // If strict mode, reject any boundary crossing
    if (opts.strict && c.boundaryCrossed.length > 0) {
      return false;
    }
    return true;
  });
  
  // Sort by distance and limit to k
  rectified.sort((a, b) => a.distance - b.distance);
  
  return rectified.slice(0, opts.k);
}

// ============================================================
// TOTALSPACE - The universe of all Spaces
// ============================================================

// SpaceOfCrystalBalls: a Space containing references to all CrystalBalls
export function createSpaceOfCrystalBalls(registry: SpaceRegistry): CrystalBall {
  const sb = createCrystalBall('SpaceOfCrystalBalls');
  
  addAttribute(sb, 'root', 'type', ['meta']);
  addAttribute(sb, 'root', 'kind', ['spaceOfSpaces']);
  
  const spacesNode = addNode(sb, 'root', 'spaces');
  
  let idx = 0;
  for (const [name, cb] of registry.spaces) {
    const spaceNode = addNode(sb, spacesNode.id, name);
    // Reference by name (cycle-safe)
    const ref = createCrystalBall(`ref:${name}`);
    attachSubspace(sb, spaceNode.id, ref);
    idx++;
  }
  
  addAttribute(sb, 'root', 'count', [idx], idx);
  setSlotCount(sb, 'root', 1);
  setSlotCount(sb, spacesNode.id, idx);
  lockNode(sb, 'root');
  
  return sb;
}

// TotalSpace: The complete runtime as a Space
export function createTotalSpace(
  configurations: CrystalBall[],
  transitions: CrystalBall[],
  policies: CrystalBall[],
  observers: CrystalBall[],
  namedSubspaces: Record<string, CrystalBall>
): CrystalBall {
  const ts = createCrystalBall('TotalSpace');
  
  addAttribute(ts, 'root', 'type', ['totalSpace']);
  
  // configurations
  const configsNode = addNode(ts, 'root', 'configurations');
  for (let i = 0; i < configurations.length; i++) {
    const cNode = addNode(ts, configsNode.id, String(i));
    attachSubspace(ts, cNode.id, configurations[i]);
  }
  
  // transitions
  const transNode = addNode(ts, 'root', 'transitions');
  for (let i = 0; i < transitions.length; i++) {
    const tNode = addNode(ts, transNode.id, String(i));
    attachSubspace(ts, tNode.id, transitions[i]);
  }
  
  // policies
  const policiesNode = addNode(ts, 'root', 'policies');
  for (let i = 0; i < policies.length; i++) {
    const pNode = addNode(ts, policiesNode.id, String(i));
    attachSubspace(ts, pNode.id, policies[i]);
  }
  
  // observers
  const observersNode = addNode(ts, 'root', 'observers');
  for (let i = 0; i < observers.length; i++) {
    const oNode = addNode(ts, observersNode.id, String(i));
    attachSubspace(ts, oNode.id, observers[i]);
  }
  
  // named subspaces
  const namedNode = addNode(ts, 'root', 'namedSubspaces');
  for (const [name, space] of Object.entries(namedSubspaces)) {
    const nNode = addNode(ts, namedNode.id, name);
    attachSubspace(ts, nNode.id, space);
  }
  
  // meta (self-reference - quoted to avoid cycle)
  const metaNode = addNode(ts, 'root', 'meta');
  const selfRef = createCrystalBall('quote:TotalSpace');
  addAttribute(selfRef, 'root', 'type', ['quoted']);
  addAttribute(selfRef, 'root', 'selfRef', ['true']);
  attachSubspace(ts, metaNode.id, selfRef);
  
  setSlotCount(ts, 'root', 6);
  lockNode(ts, 'root');
  
  return ts;
}

// ============================================================
// EXPLORATION LOOP - Prove basin behavior
// ============================================================

export interface ExplorationStep {
  anchor: string;
  step: number;
  candidates: NeighborResult[];
  accepted: NeighborResult[];
  rejected: NeighborResult[];
  observations: CrystalBall[];
}

export interface ExplorationOptions {
  maxSteps: number;
  strict: boolean;
  includeSubspaces: boolean;
  minNeighbors: number;
  recordObservations: boolean;
}

// Explore from an anchor node, generating observations at each step
export function explore(
  cb: CrystalBall,
  anchor: NodeId,
  options: Partial<ExplorationOptions> = {}
): ExplorationStep[] {
  const opts: ExplorationOptions = {
    maxSteps: options.maxSteps ?? 10,
    strict: options.strict ?? true,
    includeSubspaces: options.includeSubspaces ?? true,
    minNeighbors: options.minNeighbors ?? 1,
    recordObservations: options.recordObservations ?? true
  };
  
  const history: ExplorationStep[] = [];
  let currentAnchor = anchor;
  
  for (let step = 0; step < opts.maxSteps; step++) {
    // Get neighbors with current strictness
    const candidates = neighbors(cb, currentAnchor, {
      k: 10,
      strict: opts.strict,
      includeSubspaces: opts.includeSubspaces,
      depth: 3
    });
    
    // Separate accepted vs rejected
    const accepted = candidates.filter(c => c.boundaryCrossed.length === 0);
    const rejected = candidates.filter(c => c.boundaryCrossed.length > 0);
    
    // Generate observations
    const observations: CrystalBall[] = [];
    if (opts.recordObservations) {
      // Observation for accepted neighbors
      if (accepted.length > 0) {
        const obs = makeExplorationObservation(
          currentAnchor,
          step,
          accepted,
          'accepted'
        );
        observations.push(obs);
      }
      
      // Observation for rejected neighbors (with reason)
      if (rejected.length > 0) {
        const obs = makeExplorationObservation(
          currentAnchor,
          step,
          rejected,
          'rejected'
        );
        observations.push(obs);
      }
      
      // Summary observation
      const summary = makeExplorationSummary(
        currentAnchor,
        step,
        candidates.length,
        accepted.length,
        rejected.length
      );
      observations.push(summary);
    }
    
    // Record step
    history.push({
      anchor: currentAnchor,
      step,
      candidates,
      accepted,
      rejected,
      observations
    });
    
    // Stop if no accepted neighbors
    if (accepted.length < opts.minNeighbors) {
      break;
    }
    
    // Move to next anchor (first accepted)
    currentAnchor = accepted[0].node.id;
  }
  
  return history;
}

// Make an observation about exploration results
function makeExplorationObservation(
  anchor: string,
  step: number,
  neighbors: NeighborResult[],
  status: 'accepted' | 'rejected'
): CrystalBall {
  const obs = createCrystalBall(`exploration:${status}:${step}`);
  
  addAttribute(obs, 'root', 'type', ['explorationObservation']);
  addAttribute(obs, 'root', 'status', [status]);
  addAttribute(obs, 'root', 'step', [step], step);
  addAttribute(obs, 'root', 'anchor', [anchor], anchor);
  
  // Record neighbor details
  const neighborsNode = addNode(obs, 'root', 'neighbors');
  
  for (let i = 0; i < neighbors.length; i++) {
    const n = neighbors[i];
    const nNode = addNode(obs, neighborsNode.id, String(i));
    addAttribute(obs, nNode.id, 'id', [n.node.id], n.node.id);
    addAttribute(obs, nNode.id, 'label', [n.node.label], n.node.label);
    addAttribute(obs, nNode.id, 'distance', [n.distance], n.distance);
    
    if (n.boundaryCrossed.length > 0) {
      addAttribute(obs, nNode.id, 'boundaryCrossed', n.boundaryCrossed, n.boundaryCrossed.join(','));
    }
  }
  
  setSlotCount(obs, 'root', 3);
  lockNode(obs, 'root');
  
  return obs;
}

// Make a summary observation
function makeExplorationSummary(
  anchor: string,
  step: number,
  total: number,
  accepted: number,
  rejected: number
): CrystalBall {
  const obs = createCrystalBall(`summary:${step}`);
  
  addAttribute(obs, 'root', 'type', ['explorationSummary']);
  addAttribute(obs, 'root', 'step', [step], step);
  addAttribute(obs, 'root', 'anchor', [anchor], anchor);
  addAttribute(obs, 'root', 'totalCandidates', [total], total);
  addAttribute(obs, 'root', 'accepted', [accepted], accepted);
  addAttribute(obs, 'root', 'rejected', [rejected], rejected);
  
  setSlotCount(obs, 'root', 2);
  lockNode(obs, 'root');
  
  return obs;
}

// Integration: store observations in a space's observation log
export function integrateObservations(
  cb: CrystalBall,
  observations: CrystalBall[]
): CrystalBall {
  // Add observations to a log node
  let logNode = cb.nodes.get('root.observations');
  
  if (!logNode) {
    logNode = addNode(cb, 'root', 'observations');
    setSlotCount(cb, 'root', 2);
  }
  
  for (const obs of observations) {
    const obsId = `observation_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    addNode(cb, logNode.id, obsId);
    // Store observation reference (would attach subspace in full impl)
  }
  
  return cb;
}

// ============================================================
// ORDER 3: EMERGENT GENERATION (Pure emergence)
// Given mappings and spaces, compute all possible combinations
// ============================================================

export interface EmergentResult {
  name: string;
  score: number;
  techniques: string[];
  components: string[];
}

// Emergent generation: compute all possible fusions from mappings
// The only input is the target region - everything else is derived from existing mappings
export function emergentGenerate(
  sourceSpaces: CrystalBall[],      // The spaces to combine
  targetName: string,               // Name for emergent space
  minScore: number = 5,             // Minimum match score threshold
  regionKey: string = 'label'       // Key to differentiate regions within space
): { emergentSpace: CrystalBall; results: EmergentResult[] } {
  
  // Extract all ingredients and their attributes from source spaces
  interface Ingredient {
    name: string;
    region: string;  // Use label to differentiate regions (Proteins, Vegetables)
    flavors: string[];
    techniques: string[];
  }
  
  const ingredients: Ingredient[] = [];
  
  for (const space of sourceSpaces) {
    // Walk the space and collect all items with attributes
    // Use the parent node's label as "region" to create fusion potential
    for (const [nodeId, node] of space.nodes) {
      if (node.children.length === 0) {  // Leaf node = ingredient
        // Find parent to get region
        let region = 'default';
        const parentId = nodeId.split('.').slice(0, -1).join('.');
        if (parentId) {
          const parent = space.nodes.get(parentId);
          region = parent?.label || 'default';
        }
        
        const flavorAttr = node.attributes.get('flavor');
        const techniqueAttr = node.attributes.get('techniques');
        
        const flavors = (flavorAttr?.spectrum ?? []).map(v => String(v));
        const techniques = (techniqueAttr?.spectrum ?? []).map(v => String(v));

        ingredients.push({
          name: node.label,
          region: region,
          flavors,
          techniques,
        });
      }
    }
  }
  
  // Generate all pairwise combinations (fusion)
  // Different regions within the same space = fusion opportunity
  const results: EmergentResult[] = [];
  
  for (let i = 0; i < ingredients.length; i++) {
    for (let j = i + 1; j < ingredients.length; j++) {
      const a = ingredients[i];
      const b = ingredients[j];
      
      // Different regions = fusion (e.g., Proteins + Vegetables)
      if (a.region === b.region) continue;
      
      // Compute compatibility score (overlap)
      const flavorOverlap = a.flavors.filter(f => b.flavors.includes(f)).length;
      const techniqueOverlap = a.techniques.filter(t => b.techniques.includes(t)).length;
      const score = (flavorOverlap * 3) + (techniqueOverlap * 2);
      
      if (score >= minScore) {
        // Generate emergent name
        const emergentName = `${a.name}${b.name}`;
        
        results.push({
          name: emergentName,
          score,
          techniques: [...new Set([...a.techniques, ...b.techniques])],
          components: [a.name, b.name]
        });
      }
    }
  }
  
  // Sort by score descending
  results.sort((a, b) => b.score - a.score);
  
  // Build emergent space
  const emergentSpace = createCrystalBall(targetName);
  setSlotCount(emergentSpace, 'root', 1);
  lockNode(emergentSpace, 'root');
  
  const recipesNode = addNode(emergentSpace, 'root', 'EmergentRecipes');
  
  for (const result of results) {
    const recipeNode = addNode(emergentSpace, recipesNode.id, result.name);
    addAttribute(emergentSpace, recipeNode.id, 'score', [result.score], result.score);
    addAttribute(emergentSpace, recipeNode.id, 'components', result.components);
    addAttribute(emergentSpace, recipeNode.id, 'techniques', result.techniques);
  }
  
  setSlotCount(emergentSpace, recipesNode.id, results.length);
  
  return { emergentSpace, results };
}

// ============================================================
// ============================================================
// BLOOM: Extend slot capacity at a coordinate
// Bloom = traverse to coordinate, then expand its slotCount
// ============================================================

// Bloom: given a coordinate, expand the slot capacity at that point
// This "opens up" the coordinate to allow more selections
// Each new slot gets a label representing what entity it is
export function bloom(
  cb: CrystalBall,
  coordinate: string,  // e.g., "1.2" to select slot 1, then slot 2
  slotLabel: string,  // what these new slots represent (e.g., "ingredient", "technique")
  additionalSlots: number = 4  // how many new slots to add
): CrystalBall {
  // Parse the coordinate to find the target node
  const parts = coordinate.split('.').filter(p => p.length > 0);
  
  let currentId = cb.rootId;
  
  // Navigate to the target node
  for (const part of parts) {
    const current = cb.nodes.get(currentId);
    if (!current) throw new Error(`Node ${currentId} not found`);
    
    // Parse the coordinate part to get index (slot selection)
    const index = parseInt(part, 10) - 1;  // 1-based to 0-based
    if (index < 0 || index >= current.children.length) {
      throw new Error(` Invalid coordinate: ${part} at node ${currentId}`);
    }
    
    currentId = current.children[index];
  }
  
  // Now currentId is the target node
  const targetNode = cb.nodes.get(currentId);
  if (!targetNode) throw new Error(`Target node not found`);
  
  // Expand slot capacity and add children for each new slot
  const oldSlots = targetNode.slotCount;
  targetNode.slotCount = oldSlots + additionalSlots;
  
  // Add child nodes for each new slot, with the label representing what they are
  for (let i = oldSlots; i < oldSlots + additionalSlots; i++) {
    const childLabel = `${slotLabel}_${i + 1}`;
    const childId = `${targetNode.id}.${i}`;
    const childNode: OntologyNode = {
      id: childId,
      label: childLabel,
      children: [],
      slotCount: 0,
      locked: false,
      attributes: new Map()
    };
    cb.nodes.set(childId, childNode);
    targetNode.children.push(childId);
  }
  
  return cb;
}

// Extend: add more slots to a node directly, with labels
export function extend(
  cb: CrystalBall,
  nodeId: NodeId,
  slotLabel: string,  // what these slots represent
  additionalSlots: number
): CrystalBall {
  const node = cb.nodes.get(nodeId);
  if (!node) throw new Error(`Node ${nodeId} not found`);
  
  const oldSlots = node.slotCount;
  node.slotCount = oldSlots + additionalSlots;
  
  // Add children for each new slot
  for (let i = oldSlots; i < oldSlots + additionalSlots; i++) {
    const childLabel = `${slotLabel}_${i + 1}`;
    const childId = `${node.id}.${i}`;
    const childNode: OntologyNode = {
      id: childId,
      label: childLabel,
      children: [],
      slotCount: 0,
      locked: false,
      attributes: new Map()
    };
    cb.nodes.set(childId, childNode);
    node.children.push(childId);
  }
  
  return cb;
}

// Configure at: set values at a coordinate
export function configureAt(
  cb: CrystalBall,
  coordinate: string,
  values: any[]
): CrystalBall {
  const parts = coordinate.split('.').filter(p => p.length > 0);
  
  let currentId = cb.rootId;
  
  // Navigate to target
  for (const part of parts) {
    const current = cb.nodes.get(currentId);
    if (!current) break;
    
    const index = parseInt(part, 10) - 1;
    if (index >= 0 && index < current.children.length) {
      currentId = current.children[index];
    }
  }
  
  // Set values at target
  const node = cb.nodes.get(currentId);
  if (node) {
    values.forEach((v, i) => {
      addAttribute(cb, node.id, `slot${i + 1}`, [v], v);
    });
  }
  
  return cb;
}
