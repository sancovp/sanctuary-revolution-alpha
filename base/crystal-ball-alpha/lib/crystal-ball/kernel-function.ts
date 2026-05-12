/**
 * kernel-function.ts — RKHS Kernel Function for Crystal Ball
 * 
 * K(x, y) = ⟨ structure(scry(x)), structure(scry(y)) ⟩
 * 
 * Two coordinates are "similar" if they collect similar structural features
 * when scried. This defines an inner product on the mineSpace,
 * turning it into a Hilbert space.
 */

import {
    type Registry,
    type SpaceName,
    scry,
    coordToReal,
} from './index';

// ── Attribute Vector ─────────────────────────────────────────────
// Convert resolved attributes into a sparse numeric vector.
// Key = "attributeName:value", value = 1 if present, 0 if absent.

export interface AttributeVector {
    /** Sparse representation: key = "attrName:spectrumValue" */
    features: Map<string, number>;
    /** The coordinate this vector was computed from */
    coordinate: string;
    /** The real-number encoding of the coordinate */
    real: number;
}

/**
 * Compute the feature vector for a coordinate by scrying it
 * and collecting structural features from all resolved nodes.
 * Children ARE the spectrum — their labels and count define the features.
 */
export function attributeVector(
    registry: Registry,
    space: SpaceName,
    coordinate: string,
): AttributeVector {
    const result = scry(registry, space, coordinate);
    const features = new Map<string, number>();

    for (const resolved of result.resolved) {
        // Feature: which node was visited (structural feature)
        features.set(`node:${resolved.label}`, 1);

        // Feature: child count (structural shape)
        if (resolved.childCount > 0) {
            features.set(`childCount:${resolved.childCount}`, 0.75);
        }
    }

    // Also resolve coordinate segments directly to capture node-specific features
    const spaceData = registry.spaces.get(space);
    if (spaceData) {
        const parts = coordinate.split('.');
        let currentNodeId = 'root';
        for (const part of parts) {
            const sel = parseInt(part, 10);
            if (isNaN(sel)) break;
            const currentNode = spaceData.nodes.get(currentNodeId);
            if (!currentNode || sel < 1 || sel > currentNode.children.length) break;
            currentNodeId = currentNode.children[sel - 1];
        }
        // Collect structural features from the resolved node directly
        const resolvedNode = spaceData.nodes.get(currentNodeId);
        if (resolvedNode) {
            // Feature: each child label as a structural feature
            for (const childId of resolvedNode.children) {
                const child = spaceData.nodes.get(childId);
                if (child) {
                    features.set(`direct:child:${child.label}`, 1.0);
                }
            }
            // Feature: children count (structural shape)
            if (resolvedNode.children.length > 0) {
                features.set(`childCount:${resolvedNode.children.length}`, 0.75);
            }
        }
    }

    return {
        features,
        coordinate,
        real: coordToReal(coordinate),
    };
}

// ── Kernel Function K(x,y) ───────────────────────────────────────

/**
 * Compute the kernel function K(x, y) = inner product of attribute vectors.
 * 
 * This is a valid positive-definite kernel because it's the dot product
 * in the feature space (Mercer's condition satisfied).
 */
export function kernelFunction(
    registry: Registry,
    space: SpaceName,
    coordX: string,
    coordY: string,
): {
    value: number;      // K(x,y) — the inner product
    normX: number;      // ||x|| — norm of x's vector
    normY: number;      // ||y|| — norm of y's vector
    similarity: number; // K(x,y) / (||x|| * ||y||) — cosine similarity
    sharedFeatures: string[];  // Which features both coordinates share
    vecX: AttributeVector;
    vecY: AttributeVector;
} {
    const vecX = attributeVector(registry, space, coordX);
    const vecY = attributeVector(registry, space, coordY);

    // Inner product: sum of products of shared features
    let dotProduct = 0;
    const sharedFeatures: string[] = [];

    for (const [key, valX] of vecX.features) {
        const valY = vecY.features.get(key);
        if (valY !== undefined) {
            dotProduct += valX * valY;
            sharedFeatures.push(key);
        }
    }

    // Norms
    let normXSq = 0;
    for (const v of vecX.features.values()) normXSq += v * v;
    let normYSq = 0;
    for (const v of vecY.features.values()) normYSq += v * v;

    const normX = Math.sqrt(normXSq);
    const normY = Math.sqrt(normYSq);

    const similarity = (normX > 0 && normY > 0)
        ? dotProduct / (normX * normY)
        : 0;

    return {
        value: dotProduct,
        normX,
        normY,
        similarity,
        sharedFeatures,
        vecX,
        vecY,
    };
}

// ── Random Walk Kernel ───────────────────────────────────────────
// K_walk(x,y) = Σ λⁿ · (walks of length n from x to y)
// Captures unnamed structural similarity through DAG connectivity.

/**
 * Build adjacency matrix from a CB Space's DAG structure.
 * Returns {matrix, nodeIds} where matrix[i][j] = 1 if there's an edge i→j.
 * Includes parent→child edges, attribute-structural edges, AND dot (morphism) edges.
 */
function buildAdjacency(registry: Registry, spaceName: SpaceName): {
    matrix: number[][];
    nodeIds: string[];
    nodeIndex: Map<string, number>;
} {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    const nodeIds = Array.from(space.nodes.keys());
    const nodeIndex = new Map<string, number>();
    nodeIds.forEach((id, i) => nodeIndex.set(id, i));

    const n = nodeIds.length;
    const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));

    // Parent → child edges (bidirectional for walk counting)
    for (const [nodeId, node] of space.nodes) {
        const i = nodeIndex.get(nodeId)!;
        for (const childId of node.children) {
            const j = nodeIndex.get(childId);
            if (j !== undefined) {
                matrix[i][j] = 1;  // parent → child
                matrix[j][i] = 1;  // child → parent (walks go both ways)
            }
        }

        // Structural similarity edges: nodes with same children count
        // are connected by an unnamed structural morphism
        if (node.children.length > 0) {
            for (const [otherNodeId, otherNode] of space.nodes) {
                if (otherNodeId === nodeId) continue;
                if (otherNode.children.length > 0 && otherNode.children.length === node.children.length) {
                    const j = nodeIndex.get(otherNodeId)!;
                    matrix[i][j] = 0.5;  // weaker structural edge
                    matrix[j][i] = 0.5;
                }
            }
        }
    }

    // Dot (morphism) edges — explicit directed relationships
    if (space.dots) {
        for (const dot of space.dots) {
            const i = nodeIndex.get(dot.from);
            const j = nodeIndex.get(dot.to);
            if (i !== undefined && j !== undefined) {
                matrix[i][j] = Math.max(matrix[i][j], 1.0);  // dot = strong edge
                matrix[j][i] = Math.max(matrix[j][i], 0.7);  // reverse is weaker (directed)
            }
        }
    }

    return { matrix, nodeIds, nodeIndex };
}

/**
 * Random walk kernel: K_walk(x,y) = Σ λⁿ · Aⁿ[x,y]
 * Converges to (I - λA)⁻¹ for λ < 1/spectral_radius.
 * We approximate by summing up to maxDepth terms.
 */
export function walkKernel(
    registry: Registry,
    spaceName: SpaceName,
    coordX: string,
    coordY: string,
    lambda: number = 0.3,  // Decay factor
    maxDepth: number = 6,  // Max walk length
): number {
    const { matrix, nodeIndex } = buildAdjacency(registry, spaceName);

    // Resolve coordinates to node IDs
    const resolveToNodeId = (coord: string): number | null => {
        // Direct node ID match
        if (nodeIndex.has(coord)) return nodeIndex.get(coord)!;
        // Try as a coordinate segment (e.g., "1" → first child of root)
        const parts = coord.split('.');
        let currentNodeId = 'root';
        const space = registry.spaces.get(spaceName)!;
        for (const part of parts) {
            const sel = parseInt(part, 10);
            if (isNaN(sel)) return null;
            const currentNode = space.nodes.get(currentNodeId);
            if (!currentNode || sel < 1 || sel > currentNode.children.length) return null;
            currentNodeId = currentNode.children[sel - 1];
        }
        return nodeIndex.get(currentNodeId) ?? null;
    };

    const xi = resolveToNodeId(coordX);
    const yi = resolveToNodeId(coordY);
    if (xi === null || yi === null) return 0;

    const n = matrix.length;

    // Compute Aⁿ iteratively, accumulating λⁿ · Aⁿ[x,y]
    // Power = current power of A
    let power = Array.from({ length: n }, (_, i) =>
        Array.from({ length: n }, (_, j) => i === j ? 1 : 0)
    );  // A⁰ = I

    let total = power[xi][yi];  // λ⁰ · I[x,y] (= 1 if x==y, 0 otherwise)

    for (let depth = 1; depth <= maxDepth; depth++) {
        // Multiply power by A
        const newPower = Array.from({ length: n }, () => Array(n).fill(0));
        for (let i = 0; i < n; i++) {
            for (let j = 0; j < n; j++) {
                for (let k = 0; k < n; k++) {
                    newPower[i][j] += power[i][k] * matrix[k][j];
                }
            }
        }
        power = newPower;
        total += Math.pow(lambda, depth) * power[xi][yi];
    }

    return total;
}

// ── Hybrid Kernel ────────────────────────────────────────────────
// K(x,y) = K_named(x,y) + α · K_walk(x,y)

export function hybridKernel(
    registry: Registry,
    space: SpaceName,
    coordX: string,
    coordY: string,
    alpha: number = 0.5,  // Weight of walk kernel vs named kernel
): {
    value: number;      // Total K(x,y)
    named: number;      // K_named component
    walk: number;       // K_walk component
    similarity: number;
} {
    const named = kernelFunction(registry, space, coordX, coordY);
    const walk = walkKernel(registry, space, coordX, coordY);

    const value = named.value + alpha * walk;

    // For similarity, normalize by self-kernel
    const selfX = kernelFunction(registry, space, coordX, coordX).value
        + alpha * walkKernel(registry, space, coordX, coordX);
    const selfY = kernelFunction(registry, space, coordY, coordY).value
        + alpha * walkKernel(registry, space, coordY, coordY);
    const similarity = (selfX > 0 && selfY > 0)
        ? value / Math.sqrt(selfX * selfY)
        : 0;

    return { value, named: named.value, walk, similarity };
}

// ── Gram Matrix ──────────────────────────────────────────────────
// Compute K(xi, xj) for all pairs — this IS the Hilbert space structure

export interface GramMatrixEntry {
    coordI: string;
    coordJ: string;
    realI: number;
    realJ: number;
    kernel: number;
    similarity: number;
}

/**
 * Compute the full Gram matrix for a set of coordinates.
 * The Gram matrix G[i,j] = K(xi, xj) defines the Hilbert space geometry.
 * Uses the hybridKernel (K_named + α·K_walk) to capture both named features
 * AND structural connectivity (parent→child, attribute edges, AND dots).
 */
export function gramMatrix(
    registry: Registry,
    space: SpaceName,
    coordinates: string[],
    alpha: number = 0.5,
): {
    entries: GramMatrixEntry[];
    matrix: number[][];
    coordinates: string[];
    dimension: number;
} {
    const n = coordinates.length;
    const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
    const entries: GramMatrixEntry[] = [];

    for (let i = 0; i < n; i++) {
        for (let j = i; j < n; j++) {
            const h = hybridKernel(registry, space, coordinates[i], coordinates[j], alpha);
            const k = kernelFunction(registry, space, coordinates[i], coordinates[j]);
            matrix[i][j] = h.value;
            matrix[j][i] = h.value; // Symmetric

            entries.push({
                coordI: coordinates[i],
                coordJ: coordinates[j],
                realI: k.vecX.real,
                realJ: k.vecY.real,
                kernel: h.value,
                similarity: h.similarity,
            });
        }
    }

    // Effective dimension = rank of the Gram matrix
    const trace = matrix.reduce((sum, row, i) => sum + row[i], 0);

    return {
        entries,
        matrix,
        coordinates,
        dimension: Math.round(trace),
    };
}

// ── RKHS Distance Metric ────────────────────────────────────────

/**
 * Distance in the RKHS induced by K:
 * d²(x,y) = K(x,x) - 2K(x,y) + K(y,y)
 */
export function rkhs_distance(
    registry: Registry,
    space: SpaceName,
    coordX: string,
    coordY: string,
): number {
    const kxx = kernelFunction(registry, space, coordX, coordX).value;
    const kyy = kernelFunction(registry, space, coordY, coordY).value;
    const kxy = kernelFunction(registry, space, coordX, coordY).value;
    return Math.sqrt(Math.max(0, kxx - 2 * kxy + kyy));
}

// ── Eigenvalues (Power Iteration) ────────────────────────────────

/**
 * Compute eigenvalues of a symmetric matrix via shifted power iteration.
 * Returns eigenvalues sorted descending.
 * Good enough for small Gram matrices (< 100x100).
 */
export function eigenvalues(matrix: number[][]): number[] {
    const n = matrix.length;
    if (n === 0) return [];

    // Work on a copy
    const M = matrix.map(row => [...row]);
    const eigs: number[] = [];

    for (let iter = 0; iter < n; iter++) {
        // Power iteration to find largest eigenvalue
        let v = Array(n).fill(1 / Math.sqrt(n));
        let lambda = 0;

        for (let step = 0; step < 100; step++) {
            // Multiply: w = M * v
            const w = Array(n).fill(0);
            for (let i = 0; i < n; i++) {
                for (let j = 0; j < n; j++) {
                    w[i] += M[i][j] * v[j];
                }
            }

            // Compute eigenvalue estimate
            let dot = 0, normSq = 0;
            for (let i = 0; i < n; i++) {
                dot += w[i] * v[i];
                normSq += w[i] * w[i];
            }
            lambda = dot;

            // Normalize
            const norm = Math.sqrt(normSq);
            if (norm < 1e-12) break;
            for (let i = 0; i < n; i++) v[i] = w[i] / norm;
        }

        eigs.push(lambda);

        // Deflate: M = M - lambda * v * v^T
        for (let i = 0; i < n; i++) {
            for (let j = 0; j < n; j++) {
                M[i][j] -= lambda * v[i] * v[j];
            }
        }
    }

    return eigs.sort((a, b) => b - a);
}

// ── Symmetry Orbits ──────────────────────────────────────────────

export interface SymmetryOrbit {
    /** Representative coordinate */
    representative: string;
    /** All coordinates in this orbit (structurally interchangeable) */
    members: string[];
    /** Size of the orbit */
    size: number;
}

/**
 * Find symmetry orbits: groups of coordinates that are interchangeable
 * under the kernel function (same row/column pattern in Gram matrix).
 */
export function findOrbits(gram: { matrix: number[][]; coordinates: string[] }): SymmetryOrbit[] {
    const n = gram.coordinates.length;
    const visited = new Set<number>();
    const orbits: SymmetryOrbit[] = [];

    for (let i = 0; i < n; i++) {
        if (visited.has(i)) continue;

        const orbit: number[] = [i];
        visited.add(i);

        for (let j = i + 1; j < n; j++) {
            if (visited.has(j)) continue;

            // Two coordinates are in the same orbit if their Gram rows are identical
            let same = true;
            for (let k = 0; k < n; k++) {
                if (Math.abs(gram.matrix[i][k] - gram.matrix[j][k]) > 1e-10) {
                    same = false;
                    break;
                }
            }
            if (same) {
                orbit.push(j);
                visited.add(j);
            }
        }

        orbits.push({
            representative: gram.coordinates[orbit[0]],
            members: orbit.map(idx => gram.coordinates[idx]),
            size: orbit.length,
        });
    }

    return orbits;
}

// ── Full Space Analysis ──────────────────────────────────────────

export interface SpaceAnalysis {
    gramMatrix: number[][];
    eigenspectrum: number[];
    effectiveDimension: number;
    orbits: SymmetryOrbit[];
    symmetryGroup: string;
    distances: { from: string; to: string; distance: number }[];
}

/**
 * Full RKHS analysis of a space: Gram matrix, eigenvalues, orbits, distances.
 */
export function analyzeSpace(
    registry: Registry,
    space: SpaceName,
    coordinates: string[],
): SpaceAnalysis {
    const gram = gramMatrix(registry, space, coordinates);
    const eigs = eigenvalues(gram.matrix);
    const orbits = findOrbits(gram);

    // Effective dimension = number of eigenvalues > threshold
    const threshold = 0.01;
    const effectiveDimension = eigs.filter(e => Math.abs(e) > threshold).length;

    // Symmetry group description from orbit sizes
    const orbitSizes = orbits
        .filter(o => o.size > 1)
        .map(o => `S${o.size - 1}`)  // Star: fixed center + permutable leaves
        .join(' × ');
    const fixedPoints = orbits.filter(o => o.size === 1).length;
    const symmetryGroup = orbitSizes
        ? `${orbitSizes}${fixedPoints > 0 ? ` + ${fixedPoints} fixed` : ''}`
        : `trivial (${fixedPoints} fixed points)`;

    // All pairwise distances
    const distances: { from: string; to: string; distance: number }[] = [];
    for (let i = 0; i < coordinates.length; i++) {
        for (let j = i + 1; j < coordinates.length; j++) {
            const d = Math.sqrt(Math.max(0,
                gram.matrix[i][i] - 2 * gram.matrix[i][j] + gram.matrix[j][j]
            ));
            distances.push({ from: coordinates[i], to: coordinates[j], distance: d });
        }
    }
    distances.sort((a, b) => a.distance - b.distance);

    return {
        gramMatrix: gram.matrix,
        eigenspectrum: eigs,
        effectiveDimension,
        orbits,
        symmetryGroup,
        distances,
    };
}

// ── Foundation Signature ─────────────────────────────────────────
// The canonical triple: (orbit partition, quotient graph, local automorphism groups)
// This is a structural fingerprint that's independent of naming.

export interface QuotientEdge {
    fromOrbit: number;
    toOrbit: number;
    weight: number;  // Average K between orbit members
}

export interface LocalAutGroup {
    orbitIndex: number;
    representative: string;
    orbitSize: number;
    /** Fixed center (parent node) — not permutable */
    fixedCenter: string | null;
    /** Permutable members (leaf orbit) */
    permutableMembers: string[];
    /** The symmetric group acting on the permutable members */
    groupName: string;  // e.g., "S3", "S2", "trivial"
    groupOrder: number; // |Sn| = n!
}

export interface FoundationSignature {
    /** Orbit partition: sizes sorted descending */
    orbitPartition: number[];
    /** Quotient graph: compressed skeleton showing how orbits relate */
    quotientGraph: QuotientEdge[];
    /** Local automorphism group for each orbit */
    localGroups: LocalAutGroup[];
    /** Canonical string representation for comparison */
    canonical: string;
}

function factorial(n: number): number {
    let f = 1;
    for (let i = 2; i <= n; i++) f *= i;
    return f;
}

/**
 * Compute the Foundation Signature for a space analysis.
 * This is the canonical structural fingerprint:
 * (orbit partition, quotient graph, local automorphism groups)
 */
export function foundationSignature(analysis: SpaceAnalysis): FoundationSignature {
    const { orbits, gramMatrix: gram } = analysis;

    // 1. Orbit partition (sizes, sorted descending)
    const orbitPartition = orbits.map(o => o.size).sort((a, b) => b - a);

    // 2. Local automorphism groups
    const localGroups: LocalAutGroup[] = orbits.map((orbit, idx) => {
        // Determine fixed center vs permutable members
        // Fixed center = the member that's NOT interchangeable with others
        // (in a star graph, the center has a different degree)
        // Heuristic: first member is the representative/center if orbit.size > 1
        let fixedCenter: string | null = null;
        let permutableMembers: string[];

        if (orbit.size === 1) {
            fixedCenter = null;
            permutableMembers = [];
        } else {
            // The center is the member with the shortest coordinate (closest to root)
            const sorted = [...orbit.members].sort((a, b) => a.length - b.length);
            fixedCenter = sorted[0];
            permutableMembers = sorted.slice(1);
        }

        const pSize = permutableMembers.length;
        const groupName = pSize === 0 ? 'trivial' : `S${pSize}`;
        const groupOrder = pSize === 0 ? 1 : factorial(pSize);

        return {
            orbitIndex: idx,
            representative: orbit.representative,
            orbitSize: orbit.size,
            fixedCenter,
            permutableMembers,
            groupName,
            groupOrder,
        };
    });

    // 3. Quotient graph — edges between orbits
    const quotientGraph: QuotientEdge[] = [];

    for (let i = 0; i < orbits.length; i++) {
        for (let j = i + 1; j < orbits.length; j++) {
            // Average K between all pairs across orbits i and j
            let sum = 0;
            let count = 0;

            // Find gram indices for orbit members
            const coordList = analysis.orbits[0]?.members
                ? orbits.flatMap(o => o.members)
                : [];
            const coordIndex = new Map<string, number>();
            // Build coordinate → gram index mapping
            // (orbits track coordinates, gram tracks indices in same order)
            let idx = 0;
            for (const orbit of orbits) {
                for (const member of orbit.members) {
                    coordIndex.set(member, idx);
                    // Nope — gram indices follow the original coordinates array
                }
            }

            // Use orbit representative positions from the gram matrix
            // We need to map orbit members to gram matrix indices
            // The gram matrix was built from the coordinates array passed to analyzeSpace
            // Let's compute inter-orbit K from the gram matrix
            for (const mi of orbits[i].members) {
                for (const mj of orbits[j].members) {
                    // Find these in the gram matrix
                    // Since orbits came from findOrbits which uses gram.coordinates,
                    // we can find indices by position
                    const gi = orbits.slice(0, i).reduce((s, o) => s + o.size, 0)
                        + orbits[i].members.indexOf(mi);
                    const gj = orbits.slice(0, j).reduce((s, o) => s + o.size, 0)
                        + orbits[j].members.indexOf(mj);

                    if (gi < gram.length && gj < gram[0].length) {
                        sum += gram[gi][gj];
                        count++;
                    }
                }
            }

            const weight = count > 0 ? sum / count : 0;
            if (Math.abs(weight) > 1e-10) {
                quotientGraph.push({ fromOrbit: i, toOrbit: j, weight });
            }
        }
    }

    // 4. Canonical string representation
    const partStr = orbitPartition.join(',');
    const groupStr = localGroups.map(g => g.groupName).join('×');
    const edgeStr = quotientGraph.length > 0
        ? quotientGraph.map(e => `${e.fromOrbit}-${e.toOrbit}:${e.weight.toFixed(2)}`).join(',')
        : 'disconnected';
    const canonical = `[${partStr}]|${groupStr}|{${edgeStr}}`;

    return { orbitPartition, quotientGraph, localGroups, canonical };
}

// ── Symmetry Breaking Detection ──────────────────────────────────
// Compare two foundation signatures and classify the relationship.

export type StructuralRelationship =
    | 'identical'           // Structurally stable: same partition, groups, topology, weights within ε
    | 'renamed'             // Same partition + groups + topology, weights differ beyond ε
    | 'content_divergent'   // Same partition, different quotient topology 
    | 'symmetry_broken'     // Orbit split — one group became smaller
    | 'symmetry_enhanced'   // Orbit merged — one group became larger
    | 'new_foundation';     // Completely different partition

export interface SymmetryBreaking {
    relationship: StructuralRelationship;
    /** Which orbits changed (by index in signature A) */
    changedOrbits: number[];
    /** Human-readable description of what changed */
    description: string;
    signatureA: string;
    signatureB: string;
    /** Max weight difference across all quotient edges (if applicable) */
    maxWeightDiff?: number;
}

/**
 * Structural convergence predicate.
 * 
 * Stable(A, B) := ISO_FOUNDATION(A, B) ∧ WeightDiff(A, B) < ε
 * 
 * Checks:
 *   - Same orbit partition (exact)
 *   - Same local group names (exact) 
 *   - Same quotient graph topology (exact)
 *   - Maximum weight difference across all quotient edges < epsilon (approximate)
 * 
 * This is robust against:
 *   - Node reordering
 *   - Label differences
 *   - Float noise in edge weights
 */
export function isStructurallyStable(
    sigA: FoundationSignature,
    sigB: FoundationSignature,
    epsilon: number = 1e-6,
): { stable: boolean; maxWeightDiff: number } {
    // 1. Exact: orbit partition must match
    if (JSON.stringify(sigA.orbitPartition) !== JSON.stringify(sigB.orbitPartition)) {
        return { stable: false, maxWeightDiff: Infinity };
    }

    // 2. Exact: local group names must match
    const groupsA = sigA.localGroups.map(g => g.groupName).join('×');
    const groupsB = sigB.localGroups.map(g => g.groupName).join('×');
    if (groupsA !== groupsB) {
        return { stable: false, maxWeightDiff: Infinity };
    }

    // 3. Exact: quotient graph topology must match
    const topoA = sigA.quotientGraph.map(e => `${e.fromOrbit}-${e.toOrbit}`).sort().join(',');
    const topoB = sigB.quotientGraph.map(e => `${e.fromOrbit}-${e.toOrbit}`).sort().join(',');
    if (topoA !== topoB) {
        return { stable: false, maxWeightDiff: Infinity };
    }

    // 4. Approximate: edge weights must be within ε
    // Sort edges by topology key for alignment
    const edgesA = [...sigA.quotientGraph].sort((a, b) =>
        `${a.fromOrbit}-${a.toOrbit}`.localeCompare(`${b.fromOrbit}-${b.toOrbit}`));
    const edgesB = [...sigB.quotientGraph].sort((a, b) =>
        `${a.fromOrbit}-${a.toOrbit}`.localeCompare(`${b.fromOrbit}-${b.toOrbit}`));

    let maxWeightDiff = 0;
    for (let i = 0; i < edgesA.length; i++) {
        const diff = Math.abs(edgesA[i].weight - edgesB[i].weight);
        maxWeightDiff = Math.max(maxWeightDiff, diff);
    }

    return { stable: maxWeightDiff < epsilon, maxWeightDiff };
}

/**
 * Compare two foundation signatures and detect symmetry breaking.
 * This is the automatic validation mechanism:
 * same structure = valid, broken symmetry = meaningful mutation.
 * 
 * Uses structural convergence (isStructurallyStable) for 'identical'
 * classification — robust against float noise, node reordering, and label changes.
 */
export function detectSymmetryBreaking(
    sigA: FoundationSignature,
    sigB: FoundationSignature,
    epsilon: number = 1e-6,
): SymmetryBreaking {
    const changedOrbits: number[] = [];

    // Check if partitions match
    const partMatch = JSON.stringify(sigA.orbitPartition) === JSON.stringify(sigB.orbitPartition);

    // Check if local groups match
    const groupsA = sigA.localGroups.map(g => g.groupName).join('×');
    const groupsB = sigB.localGroups.map(g => g.groupName).join('×');
    const groupMatch = groupsA === groupsB;

    // Check if quotient graph topology matches  
    const topoA = sigA.quotientGraph.map(e => `${e.fromOrbit}-${e.toOrbit}`).sort().join(',');
    const topoB = sigB.quotientGraph.map(e => `${e.fromOrbit}-${e.toOrbit}`).sort().join(',');
    const topoMatch = topoA === topoB;

    // Structural convergence check (replaces raw string equality)
    const stability = isStructurallyStable(sigA, sigB, epsilon);
    if (stability.stable) {
        return {
            relationship: 'identical',
            changedOrbits: [],
            description: `Structurally stable (max weight diff: ${stability.maxWeightDiff.toExponential(2)}).`,
            signatureA: sigA.canonical,
            signatureB: sigB.canonical,
            maxWeightDiff: stability.maxWeightDiff,
        };
    }

    if (partMatch && groupMatch && topoMatch) {
        return {
            relationship: 'renamed',
            changedOrbits: [],
            description: `Same structure, weights differ (max diff: ${stability.maxWeightDiff.toFixed(4)}).`,
            signatureA: sigA.canonical,
            signatureB: sigB.canonical,
            maxWeightDiff: stability.maxWeightDiff,
        };
    }

    if (partMatch && !groupMatch) {
        // Same orbit sizes but different groups — internal structure changed
        for (let i = 0; i < sigA.localGroups.length && i < sigB.localGroups.length; i++) {
            if (sigA.localGroups[i].groupName !== sigB.localGroups[i].groupName) {
                changedOrbits.push(i);
            }
        }
        return {
            relationship: 'content_divergent',
            changedOrbits,
            description: `Same orbit sizes but internal group structure changed at orbit(s) ${changedOrbits.join(', ')}.`,
            signatureA: sigA.canonical,
            signatureB: sigB.canonical,
        };
    }

    if (!partMatch) {
        // Partitions differ — check if it's breaking or enhancement
        const totalA = sigA.orbitPartition.reduce((s, x) => s + x, 0);
        const totalB = sigB.orbitPartition.reduce((s, x) => s + x, 0);

        // More orbits in B = symmetry broken (orbits split)
        // Fewer orbits in B = symmetry enhanced (orbits merged)
        if (sigB.orbitPartition.length > sigA.orbitPartition.length) {
            // Find which orbit in A split
            for (let i = 0; i < sigA.orbitPartition.length; i++) {
                if (i >= sigB.orbitPartition.length || sigA.orbitPartition[i] !== sigB.orbitPartition[i]) {
                    changedOrbits.push(i);
                }
            }
            return {
                relationship: 'symmetry_broken',
                changedOrbits,
                description: `Symmetry broken: partition ${sigA.orbitPartition.join(',')} → ${sigB.orbitPartition.join(',')}. ` +
                    `An orbit split — one variant became distinguishable.`,
                signatureA: sigA.canonical,
                signatureB: sigB.canonical,
            };
        }

        if (sigB.orbitPartition.length < sigA.orbitPartition.length) {
            return {
                relationship: 'symmetry_enhanced',
                changedOrbits: [],
                description: `Symmetry enhanced: partition ${sigA.orbitPartition.join(',')} → ${sigB.orbitPartition.join(',')}. ` +
                    `Orbits merged — previously distinct variants became interchangeable.`,
                signatureA: sigA.canonical,
                signatureB: sigB.canonical,
            };
        }

        return {
            relationship: 'new_foundation',
            changedOrbits: [],
            description: `New foundation: partition ${sigA.orbitPartition.join(',')} → ${sigB.orbitPartition.join(',')}. Completely different structure.`,
            signatureA: sigA.canonical,
            signatureB: sigB.canonical,
        };
    }

    return {
        relationship: 'content_divergent',
        changedOrbits: [],
        description: `Quotient topology changed: ${topoA} → ${topoB}.`,
        signatureA: sigA.canonical,
        signatureB: sigB.canonical,
    };
}
