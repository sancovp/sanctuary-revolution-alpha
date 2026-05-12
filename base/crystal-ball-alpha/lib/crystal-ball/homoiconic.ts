/**
 * homoiconic.ts — The Crystal Ball Lisp
 *
 * S-expressions  = coordinates (the code)
 * DAG            = the data
 * eval (cbEval)  = scry — resolve coordinate against DAG
 * quote (cbQuote)= inverse of scry — node → coordinate
 * apply (cbApply)= compose two coordinates
 * walk (cbWalk)  = systematic eval of all valid coordinates
 *
 * This module is the ONLY layer that should interpret coordinates
 * against the DAG. Engine and math modules call these functions.
 *
 * Design invariant: children ARE the spectrum. No attributes.
 */

import {
  type Registry,
  type SpaceName,
  type Space,
  type CBNode,
  type NodeId,
  type ScryResult,
  type ResolvedNode,
  scry,
  coordToReal,
  createRegistry,
} from './index';

// ─── Types ────────────────────────────────────────────────────────

/** Result of evaluating a coordinate against the DAG */
export interface EvalResult {
  /** The nodes resolved by this coordinate */
  nodes: CBNode[];
  /** The coordinate that was evaluated */
  coordinate: string;
  /** The real-number encoding of the coordinate */
  real: number;
  /** Full scry result for advanced consumers */
  scryResult: ScryResult;
}

/** Result of quoting a node — reconstructing its coordinate */
export interface QuoteResult {
  /** The reconstructed coordinate string (1-based Dewey notation) */
  coordinate: string;
  /** The real-number encoding */
  real: number;
  /** The node that was quoted */
  nodeId: NodeId;
  /** Label of the quoted node */
  label: string;
}

/** Result of applying one coordinate to another */
export interface ApplyResult {
  /** Nodes resolved by the composed coordinate */
  nodes: CBNode[];
  /** The composed coordinate string */
  coordinate: string;
  /** The real-number encoding */
  real: number;
}

/** Yielded by cbWalk — a coordinate-node pair */
export interface WalkEntry {
  /** The coordinate path to this node */
  coordinate: string;
  /** The node at this coordinate */
  node: CBNode;
  /** Depth in the walk (0 = root's immediate children) */
  depth: number;
}

// ─── cbEval: coordinate × space → nodes ──────────────────────────
//
// This IS scry. The coordinate is the program. The DAG is the data.
// Given a registry and space name, resolve the coordinate to nodes.
//
// Supports multi-space resolution: if a node has a producedSpace,
// subsequent coordinate segments resolve within that subspace.

export function cbEval(
  registry: Registry,
  spaceName: SpaceName,
  coordinate: string,
): EvalResult {
  const scryResult = scry(registry, spaceName, coordinate);

  // Extract actual CBNode objects from the resolved chain
  const nodes: CBNode[] = [];
  for (const resolved of scryResult.resolved) {
    // Walk the space chain backwards to find the node
    for (let i = resolved.spaceChain.length - 1; i >= 0; i--) {
      const space = registry.spaces.get(resolved.spaceChain[i]);
      if (space) {
        const node = space.nodes.get(resolved.nodeId);
        if (node) {
          nodes.push(node);
          break;
        }
      }
    }
  }

  return {
    nodes,
    coordinate,
    real: coordToReal(coordinate),
    scryResult,
  };
}

/**
 * Convenience: evaluate within a single space (no registry needed).
 * Creates a temporary registry containing just this space.
 */
export function cbEvalLocal(
  space: Space,
  coordinate: string,
): EvalResult {
  const tmpRegistry = createRegistry();
  tmpRegistry.spaces.set(space.name, space);
  return cbEval(tmpRegistry, space.name, coordinate);
}

// ─── cbQuote: node × space → coordinate ──────────────────────────
//
// Walk UP from node to root, recording child index at each level.
// Returns the Dewey-style coordinate that would scry to this node.
//
// This is the inverse of cbEval: if cbEval(space, coord) → node,
// then cbQuote(space, node.id) → coord.

export function cbQuote(
  space: Space,
  nodeId: NodeId,
): QuoteResult | null {
  // Root quotes to empty coordinate
  if (nodeId === space.rootId || nodeId === 'root') {
    const rootNode = space.nodes.get(space.rootId) ?? space.nodes.get('root');
    if (!rootNode) return null;
    return {
      coordinate: '',
      real: 0,
      nodeId: rootNode.id,
      label: rootNode.label,
    };
  }

  // Find path from root to this node using recursive DFS
  const path = findPathFromRoot(space, space.rootId, nodeId);
  if (!path) return null;

  const node = space.nodes.get(nodeId);
  if (!node) return null;

  // Path is array of 1-based selection indices
  const coordinate = path.join('.');

  return {
    coordinate,
    real: coordToReal(coordinate),
    nodeId,
    label: node.label,
  };
}

/**
 * Recursive DFS to find the 1-based path from root to a target node.
 * Returns null if node is not reachable from the root.
 */
function findPathFromRoot(
  space: Space,
  currentId: NodeId,
  targetId: NodeId,
  path: number[] = [],
): number[] | null {
  const node = space.nodes.get(currentId);
  if (!node) return null;

  for (let i = 0; i < node.children.length; i++) {
    const childId = node.children[i];
    if (childId === targetId) {
      return [...path, i + 1]; // 1-based coordinate
    }

    const found = findPathFromRoot(space, childId, targetId, [...path, i + 1]);
    if (found) return found;
  }

  return null;
}

// ─── cbApply: compose two coordinates ────────────────────────────
//
// Evaluate the first coordinate, then continue resolution from
// the resulting context with the second coordinate.
//
// In Lisp terms: (apply fn arg) = eval (concat fn "." arg)
// In CB terms: "1.2" applied to "3" = "1.2.3"
//
// This captures the fundamental composition operation:
// if coordinate A selects a node with a produced subspace,
// then applying coordinate B resolves within that subspace.

export function cbApply(
  registry: Registry,
  spaceName: SpaceName,
  fnCoord: string,
  argCoord: string,
): ApplyResult {
  // Compose by concatenation with dot separator
  const composed = fnCoord && argCoord
    ? `${fnCoord}.${argCoord}`
    : fnCoord || argCoord;

  const result = cbEval(registry, spaceName, composed);

  return {
    nodes: result.nodes,
    coordinate: composed,
    real: result.real,
  };
}

// ─── cbWalk: systematic eval of all valid coordinates ────────────
//
// Generator that yields all reachable coordinate-node pairs
// via depth-first traversal. Used by mine to enumerate the
// configuration space.
//
// The walk follows the natural DAG structure:
// - Each child at depth D gets coordinate segment (index+1)
// - If a node has a producedSpace, the walk continues into it
// - maxDepth limits how deep we go

export function* cbWalk(
  space: Space,
  maxDepth: number = 10,
  registry?: Registry,
): Generator<WalkEntry> {
  const rootNode = space.nodes.get(space.rootId) ?? space.nodes.get('root');
  if (!rootNode) return;

  yield* walkNode(space, rootNode, '', 0, maxDepth, registry);
}

function* walkNode(
  space: Space,
  node: CBNode,
  parentCoord: string,
  depth: number,
  maxDepth: number,
  registry?: Registry,
): Generator<WalkEntry> {
  if (depth > maxDepth) return;

  for (let i = 0; i < node.children.length; i++) {
    const childId = node.children[i];
    const child = space.nodes.get(childId);
    if (!child) continue;

    const segment = String(i + 1); // 1-based
    const coord = parentCoord ? `${parentCoord}.${segment}` : segment;

    yield { coordinate: coord, node: child, depth };

    // If the child has a producedSpace, walk into it
    if (child.producedSpace && registry) {
      const subspace = registry.spaces.get(child.producedSpace);
      if (subspace) {
        const subRoot = subspace.nodes.get(subspace.rootId) ?? subspace.nodes.get('root');
        if (subRoot) {
          yield* walkNode(subspace, subRoot, coord, depth + 1, maxDepth, registry);
        }
      }
    }

    // Also walk the child's own children within this space
    yield* walkNode(space, child, coord, depth + 1, maxDepth, registry);
  }
}

// ─── Utility: check coordinate invertibility ─────────────────────
//
// A key property of homoiconicity: eval and quote should be inverses.
// cbQuote(space, cbEval(space, coord).nodes.at(-1).id) === coord
//
// This function verifies that property for debugging.

export function verifyInvertibility(
  space: Space,
  coordinate: string,
): { invertible: boolean; evalResult: EvalResult; quoteResult: QuoteResult | null } {
  const evalResult = cbEvalLocal(space, coordinate);

  if (evalResult.nodes.length === 0) {
    return { invertible: false, evalResult, quoteResult: null };
  }

  // Use the LAST node — the terminal resolution at the full coordinate depth.
  // nodes[0] would be the first intermediate resolution (e.g., node "1" for coord "1.1"),
  // but we need the deepest resolved node (e.g., node "1.1" for coord "1.1").
  const terminalNode = evalResult.nodes[evalResult.nodes.length - 1];
  const quoteResult = cbQuote(space, terminalNode.id);
  if (!quoteResult) {
    return { invertible: false, evalResult, quoteResult: null };
  }

  return {
    invertible: quoteResult.coordinate === coordinate,
    evalResult,
    quoteResult,
  };
}
