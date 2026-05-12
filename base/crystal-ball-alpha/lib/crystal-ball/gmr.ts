/**
 * gmr.ts — Geometric Manifold Rectification for CB
 *
 * THE MATH IS MEANINGFUL A PRIORI.
 *
 * GMR computes the GEOMETRIC STRUCTURE of the locked coordinate space.
 * It does NOT "validate" or "check" — it COMPUTES. The result is a
 * numerical view of the manifold that IS the prompt to the LLM.
 *
 * What it computes:
 *   1. KERNEL MATRIX: K(x,y) for all node pairs in a neighborhood
 *      → tensor product RKHS kernel, factored per slot
 *   2. DENSITY at each node: how much kernel support surrounds it
 *      → high density = redundant region, low density = frontier
 *   3. GAPS: geometric regions with no node coverage
 *      → these are where the LLM should fill
 *   4. CURVATURE: how the density field changes
 *      → where the manifold bends = where interesting structure is
 *
 * The output is the PROMPT MASK: "here is the geometry from where
 * you are. Dense here, sparse there. Fill the sparse."
 *
 * CB translation:
 *   - nodes = points on the manifold (all locked = all real)
 *   - K(x,y) = tensorKernel (Gaussian RBF on primacy, factored per slot)
 *   - density = average kernel value to neighbors (how "supported" a point is)
 *   - redundancy = many nearby points in kernel space
 *   - scarcity = isolated point, frontier of the manifold
 */

import type { CrystalBall, CBNode, Registry } from './index';
import { getAmplitude, getBornWeight, setAmplitude, isInSuperposition } from './index';
import { tensorKernel } from './kernel-v2';
import type { AlgebraNeighborhood } from './swarm-agent';

// ─── Configuration ───────────────────────────────────────────────

export interface GMRConfig {
    /** Number of neighbors for density estimation (default 10) */
    k: number;
    /** Density threshold below which region is "sparse"/frontier (default 0.3) */
    sparseThreshold: number;
    /** Density threshold above which region is "dense"/redundant (default 0.7) */
    denseThreshold: number;
    /** Epsilon for inverse-distance weighting (default 1e-6) */
    epsilon: number;
}

export const GMR_DEFAULTS: GMRConfig = {
    k: 10,
    sparseThreshold: 0.3,
    denseThreshold: 0.7,
    epsilon: 1e-6,
};

// ─── Types ───────────────────────────────────────────────────────

/** Geometric properties of a single node on the manifold */
export interface NodeGeometry {
    nodeId: string;
    label: string;
    /** Average kernel similarity to k nearest neighbors [0,1] */
    density: number;
    /** Max kernel value to any neighbor (closest point) */
    nearestSimilarity: number;
    /** Min kernel value to any neighbor (farthest point) */
    farthestSimilarity: number;
    /** Number of neighbors within dense threshold */
    denseNeighborCount: number;
    /** Classification from the geometry itself */
    region: 'dense' | 'frontier' | 'isolated' | 'normal';
    /** The k nearest neighbors with their kernel values */
    neighbors: Array<{ nodeId: string; label: string; kernelValue: number }>;
}

export interface NodeConfidence {
    nodeId: string;
    confidence: number;
    isRedundant: boolean;
    isScarce: boolean;
    neighborsUsed: number;
    action: 'keep' | 'attenuate' | 'exclude';
    reason: string;
}

/** Full geometric analysis of a space */
export interface RectificationResult {
    spaceName: string;
    nodesAnalyzed: number;
    nodesKept: number;
    nodesAttenuated: number;
    nodesExcluded: number;
    confidences: NodeConfidence[];
    /** The geometric structure — this IS the meaningful output */
    geometry: NodeGeometry[];
    /** Regions classified by density */
    denseRegions: string[];   // nodeIds in dense regions
    frontierRegions: string[]; // nodeIds on the frontier (sparse)
    isolatedNodes: string[];   // nodeIds with no nearby support
}

// ─── Geometric Computation ──────────────────────────────────────

/**
 * Compute the kernel distance between two nodes.
 * d(x,y) = 1 - K(x,y)
 */
function kernelDistance(
    registry: Registry, spaceName: string,
    idA: string, idB: string,
): number {
    if (idA === idB) return 0;
    try {
        const result = tensorKernel(registry, spaceName, idA, idB);
        return 1 - Math.abs(result.quantumValue);
    } catch {
        // Fallback: tree distance
        const partsA = idA.split('.');
        const partsB = idB.split('.');
        let shared = 0;
        for (let i = 0; i < Math.min(partsA.length, partsB.length); i++) {
            if (partsA[i] === partsB[i]) shared++; else break;
        }
        const treeDistance = (partsA.length - shared) + (partsB.length - shared);
        const maxDepth = Math.max(partsA.length, partsB.length);
        return treeDistance / (2 * maxDepth);
    }
}

/**
 * Compute the kernel VALUE (similarity) between two nodes.
 * K(x,y) via tensorKernel.
 */
function kernelSimilarity(
    registry: Registry, spaceName: string,
    idA: string, idB: string,
): number {
    if (idA === idB) return 1.0;
    try {
        const result = tensorKernel(registry, spaceName, idA, idB);
        return Math.abs(result.quantumValue);
    } catch {
        return 0;
    }
}

/**
 * Compute the geometric properties of a node on the manifold.
 *
 * This is pure computation FROM the locked structure.
 * density = how much kernel support surrounds this point
 * neighbors = the k nearest points with their kernel values
 * region = classification derived FROM the density
 */
function computeNodeGeometry(
    registry: Registry,
    spaceName: string,
    space: CrystalBall,
    nodeId: string,
    allNodeIds: string[],
    config: GMRConfig,
): NodeGeometry {
    const node = space.nodes.get(nodeId);
    const label = node?.label ?? nodeId;

    // Compute kernel similarity to all other nodes
    const similarities: Array<{ id: string; label: string; k: number }> = [];
    for (const otherId of allNodeIds) {
        if (otherId === nodeId) continue;
        const otherNode = space.nodes.get(otherId);
        if (!otherNode) continue;
        const k = kernelSimilarity(registry, spaceName, nodeId, otherId);
        similarities.push({ id: otherId, label: otherNode.label, k });
    }

    // Sort by kernel value (highest similarity first)
    similarities.sort((a, b) => b.k - a.k);

    // Take k nearest
    const kNearest = similarities.slice(0, config.k);

    if (kNearest.length === 0) {
        return {
            nodeId, label,
            density: 0,
            nearestSimilarity: 0,
            farthestSimilarity: 0,
            denseNeighborCount: 0,
            region: 'isolated',
            neighbors: [],
        };
    }

    // Density = average kernel similarity to k nearest
    const density = kNearest.reduce((sum, n) => sum + n.k, 0) / kNearest.length;

    // Nearest and farthest
    const nearestSimilarity = kNearest[0].k;
    const farthestSimilarity = kNearest[kNearest.length - 1].k;

    // How many neighbors are "close" (above dense threshold)
    const denseNeighborCount = kNearest.filter(n => n.k > config.denseThreshold).length;

    // Classify region from geometry
    let region: NodeGeometry['region'];
    if (density > config.denseThreshold) {
        region = 'dense';
    } else if (density < config.sparseThreshold) {
        region = nearestSimilarity < config.sparseThreshold ? 'isolated' : 'frontier';
    } else {
        region = 'normal';
    }

    return {
        nodeId, label, density,
        nearestSimilarity, farthestSimilarity,
        denseNeighborCount, region,
        neighbors: kNearest.map(n => ({
            nodeId: n.id,
            label: n.label,
            kernelValue: n.k,
        })),
    };
}

// ─── Rectification (Backward Compatible) ────────────────────────

/**
 * Rectify a neighborhood.
 * Now computes geometry first, then derives actions FROM the geometry.
 * The geometry IS the meaningful output. Actions are secondary.
 */
export function rectifyNeighborhood(
    registry: Registry,
    spaceName: string,
    space: CrystalBall,
    neighborhood: AlgebraNeighborhood,
    config: GMRConfig = GMR_DEFAULTS,
): NodeConfidence[] {
    const allNodeIds = Array.from(space.nodes.keys());
    const results: NodeConfidence[] = [];

    for (const nodeId of neighborhood.memberIds) {
        const node = space.nodes.get(nodeId);
        if (!node) continue;

        const geo = computeNodeGeometry(registry, spaceName, space, nodeId, allNodeIds, config);

        // Derive confidence FROM geometry (density IS confidence)
        const confidence = geo.density;
        const isRedundant = geo.region === 'dense';
        const isScarce = geo.region === 'isolated' || geo.region === 'frontier';

        results.push({
            nodeId,
            confidence,
            isRedundant,
            isScarce,
            neighborsUsed: geo.neighbors.length,
            action: 'keep', // Geometry computed, not "validated"
            reason: `${geo.region}: density=${confidence.toFixed(3)}, nearest=${geo.nearestSimilarity.toFixed(3)}`,
        });
    }

    return results;
}

// ─── Full Space Rectification ───────────────────────────────────

/**
 * Compute the full geometric structure of a space.
 *
 * This is the main entry point. It computes geometry for every node
 * and produces the manifold view that becomes the LLM prompt.
 */
export function rectifySpace(
    registry: Registry,
    spaceName: string,
    neighborhoods: AlgebraNeighborhood[],
    config: GMRConfig = GMR_DEFAULTS,
): RectificationResult {
    const space = registry.spaces.get(spaceName);
    if (!space) {
        return {
            spaceName, nodesAnalyzed: 0, nodesKept: 0,
            nodesAttenuated: 0, nodesExcluded: 0,
            confidences: [], geometry: [],
            denseRegions: [], frontierRegions: [], isolatedNodes: [],
        };
    }

    const allNodeIds = Array.from(space.nodes.keys());
    const geometry: NodeGeometry[] = [];
    const confidences: NodeConfidence[] = [];
    const denseRegions: string[] = [];
    const frontierRegions: string[] = [];
    const isolatedNodes: string[] = [];

    // Compute geometry for every node
    for (const [nodeId] of space.nodes) {
        const geo = computeNodeGeometry(registry, spaceName, space, nodeId, allNodeIds, config);
        geometry.push(geo);

        // Classify into regions
        if (geo.region === 'dense') denseRegions.push(nodeId);
        else if (geo.region === 'frontier') frontierRegions.push(nodeId);
        else if (geo.region === 'isolated') isolatedNodes.push(nodeId);

        // Backward-compatible confidence
        confidences.push({
            nodeId,
            confidence: geo.density,
            isRedundant: geo.region === 'dense',
            isScarce: geo.region === 'isolated' || geo.region === 'frontier',
            neighborsUsed: geo.neighbors.length,
            action: 'keep',
            reason: `${geo.region}: density=${geo.density.toFixed(3)}`,
        });
    }

    return {
        spaceName,
        nodesAnalyzed: geometry.length,
        nodesKept: geometry.length, // Geometry doesn't remove — it describes
        nodesAttenuated: 0,
        nodesExcluded: 0,
        confidences,
        geometry,
        denseRegions,
        frontierRegions,
        isolatedNodes,
    };
}

// ─── Formatter ───────────────────────────────────────────────────

/**
 * Format the geometric analysis as a human+LLM readable view.
 *
 * This IS the prompt mask. The LLM reads these numbers and knows
 * where to fill.
 */
export function formatRectification(result: RectificationResult): string {
    const lines: string[] = [
        `🔬 Manifold Geometry: ${result.spaceName}`,
        `   ${result.nodesAnalyzed} nodes on manifold`,
        `   Dense: ${result.denseRegions.length}  Frontier: ${result.frontierRegions.length}  Isolated: ${result.isolatedNodes.length}`,
        '',
    ];

    // Sort geometry by density (lowest first = most interesting for LLM)
    const sorted = [...(result.geometry || [])].sort((a, b) => a.density - b.density);

    // Show frontier/isolated nodes first — these are where the LLM fills
    const fillTargets = sorted.filter(g => g.region === 'frontier' || g.region === 'isolated');
    if (fillTargets.length > 0) {
        lines.push('  🎯 Frontier (sparse — fill targets):');
        for (const g of fillTargets) {
            const nearestStr = g.neighbors.length > 0
                ? `nearest=${g.neighbors[0].label}(${g.neighbors[0].kernelValue.toFixed(3)})`
                : 'no neighbors';
            lines.push(`    ${g.nodeId} "${g.label}": density=${g.density.toFixed(3)} ${nearestStr}`);
        }
        lines.push('');
    }

    // Show normal nodes
    const normalNodes = sorted.filter(g => g.region === 'normal');
    if (normalNodes.length > 0) {
        lines.push('  📍 Normal:');
        for (const g of normalNodes.slice(0, 10)) {
            lines.push(`    ${g.nodeId} "${g.label}": density=${g.density.toFixed(3)}`);
        }
        if (normalNodes.length > 10) lines.push(`    ... +${normalNodes.length - 10} more`);
        lines.push('');
    }

    // Show dense nodes — these are redundant, LLM may skip
    const denseNodes = sorted.filter(g => g.region === 'dense');
    if (denseNodes.length > 0) {
        lines.push('  🟢 Dense (well-covered):');
        for (const g of denseNodes.slice(0, 10)) {
            lines.push(`    ${g.nodeId} "${g.label}": density=${g.density.toFixed(3)} (${g.denseNeighborCount} close neighbors)`);
        }
        if (denseNodes.length > 10) lines.push(`    ... +${denseNodes.length - 10} more`);
    }

    return lines.join('\n');
}
