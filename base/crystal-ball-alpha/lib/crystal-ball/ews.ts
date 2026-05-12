/* ═══════════════════════════════════════════════════════════
   ews.ts — Emergent Web Structure computation

   Computes the EWS of a locked (or in-progress) kernel:

   Forward:   What was generated (structure, depth, breadth)
   Backward:  What can be recognized (symmetry, orbits, patterns)
   Boundary:  The fiat boundary (interior, frontier, constraints)

   The EWS tells the LLM:
     "Here is what this kernel IS, what it can REACH,
      and where its boundary STOPS."

   This is the dual-homoiconic skeleton of the informatihedron.
   ═══════════════════════════════════════════════════════════ */

import {
    type Registry,
    type Space,
    type SpaceName,
    type CBNode,
    isKernelComplete,
    computeSpaceHeat,
} from './index';

import {
    computeSpaceSlotSignature,
    type SpaceSlotSignature,
    type SlotOrbit,
} from './kernel-v2';

import { computeMinePlane, mine, type MineSpace, type KnownPoint } from './mine';

// ─── Types ───────────────────────────────────────────────────

/** Forward chain: what was GENERATED */
export interface EWSForward {
    /** Total nodes in the space (excluding root) */
    nodeCount: number;
    /** Maximum depth of the tree */
    maxDepth: number;
    /** Children count at each level (breadth profile) */
    breadthProfile: number[];
    /** Number of locked nodes */
    lockedCount: number;
    /** Number of total slotted nodes */
    slottedCount: number;
    /** Whether the kernel is complete (all slots filled + locked) */
    kernelComplete: boolean;
    /** Space heat (0 = fully locked, 1 = fully open) */
    heat: number;
}

/** Backward chain: what can be RECOGNIZED */
export interface EWSBackward {
    /** Per-slot orbit decomposition */
    slotSignature: SpaceSlotSignature;
    /** Total symmetry group (human-readable, e.g. "S₅ × S₃") */
    symmetryGroup: string;
    /** Total configuration count (product of spectra sizes) */
    totalConfigurations: number;
    /** Canonical fingerprint (compact string identifying the shape) */
    canonical: string;
    /** Per-slot symmetry descriptions */
    slotSymmetries: {
        slotIndex: number;
        parentLabel: string;
        spectrumSize: number;
        symmetryGroup: string;
        orbitSizes: number[];
        superpositionMeaning: string;
    }[];
}

/** The fiat boundary: what IS and ISN'T inside this kernel */
export interface EWSBoundary {
    /** Coordinates that exist (valid mineSpace points) */
    interior: string[];
    /** Coordinates one step beyond the boundary (adjacent) */
    frontier: string[];
    /** Number of interior points */
    interiorSize: number;
    /** Number of frontier points */
    frontierSize: number;
    /** Depth constraints at each level */
    depthConstraints: {
        depth: number;
        parentLabel: string;
        currentChildren: number;
        canExpand: boolean;  // true if no slotCount or slotCount > children
    }[];
    /** Human-readable boundary description */
    description: string;
}

/** Complete EWS of a kernel */
export interface EWS {
    spaceName: string;
    forward: EWSForward;
    backward: EWSBackward;
    boundary: EWSBoundary;
    /** Production chain from the kernel's ewsRef (null if no EWS declared) */
    production: ProductionChain | null;
    /** Compact summary for LLM context injection */
    summary: string;
}

// ─── Computation ─────────────────────────────────────────────

/**
 * Compute the full EWS of a space/kernel.
 *
 * This is the function the LLM calls to understand:
 *   - What this kernel IS (forward)
 *   - What patterns it expresses (backward)
 *   - What it can and can't reach (boundary)
 */
export function computeEWS(
    registry: Registry,
    spaceName: SpaceName,
): EWS {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    const forward = computeForward(space);
    const backward = computeBackward(registry, spaceName);
    const boundary = computeBoundary(registry, space);
    const production = getKernelProductionChain(registry, spaceName);
    const summary = buildSummary(spaceName, forward, backward, boundary, production);

    return { spaceName, forward, backward, boundary, production, summary };
}

// ─── Forward Chain ───────────────────────────────────────────

function computeForward(space: Space): EWSForward {
    let nodeCount = 0;
    let lockedCount = 0;
    let slottedCount = 0;
    let maxDepth = 0;
    const breadthByDepth = new Map<number, number>();

    // BFS to compute structure stats
    const queue: { nodeId: string; depth: number }[] = [];
    const root = space.nodes.get(space.rootId);
    if (root) {
        for (const childId of root.children) {
            queue.push({ nodeId: childId, depth: 1 });
        }
    }

    while (queue.length > 0) {
        const { nodeId, depth } = queue.shift()!;
        const node = space.nodes.get(nodeId);
        if (!node) continue;

        nodeCount++;
        if (depth > maxDepth) maxDepth = depth;

        // Count breadth at this depth
        breadthByDepth.set(depth, (breadthByDepth.get(depth) ?? 0) + 1);

        if (node.locked) lockedCount++;
        if ((node.slotCount ?? 0) > 0) slottedCount++;

        for (const childId of node.children) {
            queue.push({ nodeId: childId, depth: depth + 1 });
        }
    }

    // Build breadth profile array
    const breadthProfile: number[] = [];
    for (let d = 1; d <= maxDepth; d++) {
        breadthProfile.push(breadthByDepth.get(d) ?? 0);
    }

    return {
        nodeCount,
        maxDepth,
        breadthProfile,
        lockedCount,
        slottedCount,
        kernelComplete: isKernelComplete(space).complete,
        heat: computeSpaceHeat(space),
    };
}

// ─── Backward Chain ──────────────────────────────────────────

function computeBackward(
    registry: Registry,
    spaceName: SpaceName,
): EWSBackward {
    const sig = computeSpaceSlotSignature(registry, spaceName);

    const slotSymmetries = sig.slots.map(slot => ({
        slotIndex: slot.slotIndex,
        parentLabel: slot.parentLabel,
        spectrumSize: slot.spectrumSize,
        symmetryGroup: slot.symmetryGroup,
        orbitSizes: slot.orbits.map(o => o.size),
        superpositionMeaning: slot.superpositionMeaning,
    }));

    return {
        slotSignature: sig,
        symmetryGroup: sig.totalSymmetry,
        totalConfigurations: sig.totalConfigurations,
        canonical: sig.canonical,
        slotSymmetries,
    };
}

// ─── Boundary ────────────────────────────────────────────────

function computeBoundary(
    registry: Registry,
    space: Space,
): EWSBoundary {
    const ms = mine(registry, space.name);

    const interior = ms.known
        .filter((p: KnownPoint) => p.status === 'valid')
        .map((p: KnownPoint) => p.coordinate);

    const frontier = ms.known
        .filter((p: KnownPoint) => p.status === 'adjacent')
        .map((p: KnownPoint) => p.coordinate);

    // Compute depth constraints — which nodes can still expand
    const depthConstraints: EWSBoundary['depthConstraints'] = [];
    const root = space.nodes.get(space.rootId);

    if (root) {
        // Root level
        const rootSlotCount = root.slotCount ?? 0;
        depthConstraints.push({
            depth: 0,
            parentLabel: root.label,
            currentChildren: root.children.length,
            canExpand: rootSlotCount === 0 || root.children.length < rootSlotCount,
        });

        // Child levels
        for (const childId of root.children) {
            const child = space.nodes.get(childId);
            if (!child) continue;
            const childSlotCount = child.slotCount ?? 0;
            depthConstraints.push({
                depth: 1,
                parentLabel: child.label,
                currentChildren: child.children.length,
                canExpand: childSlotCount === 0 || child.children.length < childSlotCount,
            });
        }
    }

    // Build human-readable description
    const expandable = depthConstraints.filter(d => d.canExpand && d.currentChildren === 0);
    const partial = depthConstraints.filter(d => d.canExpand && d.currentChildren > 0);
    const full = depthConstraints.filter(d => !d.canExpand);

    let desc = `${interior.length} interior, ${frontier.length} frontier. `;
    if (expandable.length > 0) {
        desc += `Empty: ${expandable.map(d => d.parentLabel).join(', ')}. `;
    }
    if (partial.length > 0) {
        desc += `Expandable: ${partial.map(d => `${d.parentLabel}(${d.currentChildren})`).join(', ')}. `;
    }
    if (full.length > 0) {
        desc += `Full: ${full.map(d => d.parentLabel).join(', ')}.`;
    }

    return {
        interior,
        frontier,
        interiorSize: interior.length,
        frontierSize: frontier.length,
        depthConstraints,
        description: desc.trim(),
    };
}

// ─── Summary for LLM Context ────────────────────────────────

function buildSummary(
    spaceName: string,
    forward: EWSForward,
    backward: EWSBackward,
    boundary: EWSBoundary,
    production?: ProductionChain | null,
): string {
    const lines: string[] = [
        `EWS: ${spaceName}`,
        ``,
        `FORWARD (generated):`,
        `  ${forward.nodeCount} nodes, depth ${forward.maxDepth}, breadth [${forward.breadthProfile.join(', ')}]`,
        `  ${forward.lockedCount}/${forward.nodeCount} locked, heat ${forward.heat.toFixed(2)}`,
        `  kernel: ${forward.kernelComplete ? 'COMPLETE' : 'incomplete'}`,
        ``,
        `BACKWARD (recognized):`,
        `  symmetry: ${backward.symmetryGroup}`,
        `  configs: ${backward.totalConfigurations}`,
        `  canonical: ${backward.canonical}`,
    ];

    if (backward.slotSymmetries.length > 0) {
        lines.push(`  per-slot:`);
        for (const s of backward.slotSymmetries) {
            lines.push(`    ${s.parentLabel}: ${s.symmetryGroup} (${s.spectrumSize} options, orbits [${s.orbitSizes.join(',')}])`);
        }
    }

    lines.push(``);
    lines.push(`BOUNDARY (fiat):`);
    lines.push(`  ${boundary.description}`);
    lines.push(`  interior: [${boundary.interior.join(', ')}]`);
    lines.push(`  frontier: [${boundary.frontier.join(', ')}]`);

    if (production) {
        lines.push(``);
        lines.push(`PRODUCTION CHAIN (EWS):`);
        lines.push(`  completeness: ${(production.completeness * 100).toFixed(0)}% (${production.typedCount}/${production.totalDomains} domains typed)`);
        lines.push(`  chain: ${production.domains.map(d => d.typed ? `[${d.label}]` : `(${d.label})`).join(' → ')}`);
        lines.push(`  typed: ${production.domains.filter(d => d.typed).map(d => d.label).join(', ') || 'none'}`);
        lines.push(`  untyped: ${production.domains.filter(d => !d.typed).map(d => d.label).join(', ') || 'none'}`);
        if (production.loops) {
            lines.push(`  ⟳ chain loops (self-sustaining production cycle)`);
        }
    }

    return lines.join('\n');
}

// ─── Production Chain (EWS Declaration) ──────────────────────

/** One domain in the production chain */
export interface DomainLink {
    /** Label of this domain node in the EWS space */
    label: string;
    /** Node ID in the EWS space */
    nodeId: string;
    /** Position in the production chain (0-based) */
    position: number;
    /** Whether this domain has a kernelRef (typed) or not (untyped/0) */
    typed: boolean;
    /** Global kernel ID if typed */
    kernelId?: number;
    /** Space name if typed */
    spaceName?: string;
}

/** The full production chain extracted from an EWS space */
export interface ProductionChain {
    /** Name of the EWS space */
    ewsSpaceName: string;
    /** Ordered list of domains in the chain */
    domains: DomainLink[];
    /** Total number of domains */
    totalDomains: number;
    /** Number of typed domains (have kernelRef) */
    typedCount: number;
    /** Number of untyped domains (0s — LLM fills) */
    untypedCount: number;
    /** Completeness ratio (0-1) */
    completeness: number;
    /** Whether the chain loops (last domain dots back to first) */
    loops: boolean;
}

/**
 * Extract the production chain from an EWS space.
 *
 * Follows dots from the first child to build the ordered chain.
 * If no dots exist, uses children order.
 * Checks kernelRef on each domain node to determine typed vs untyped.
 */
export function getProductionChain(
    registry: Registry,
    ewsSpaceName: SpaceName,
): ProductionChain {
    const space = registry.spaces.get(ewsSpaceName);
    if (!space) throw new Error(`EWS space "${ewsSpaceName}" not found`);

    const root = space.nodes.get(space.rootId);
    if (!root) throw new Error(`EWS space "${ewsSpaceName}" has no root`);

    // Build adjacency from dots
    const dotAdj = new Map<string, string>();
    for (const dot of space.dots) {
        dotAdj.set(dot.from, dot.to);
    }

    // Try to follow dots for ordering; fall back to children order
    let orderedIds: string[];

    if (space.dots.length > 0 && root.children.length > 0) {
        // Find the start of the chain (a node that no other node dots TO)
        const targets = new Set(space.dots.map(d => d.to));
        let start = root.children.find(id => !targets.has(id));
        if (!start) start = root.children[0]; // cycle — pick any start

        // Follow the chain
        orderedIds = [];
        const visited = new Set<string>();
        let current: string | undefined = start;
        while (current && !visited.has(current)) {
            orderedIds.push(current);
            visited.add(current);
            current = dotAdj.get(current);
        }

        // Add any children not in the chain
        for (const childId of root.children) {
            if (!visited.has(childId)) {
                orderedIds.push(childId);
            }
        }
    } else {
        orderedIds = [...root.children];
    }

    // Build domain links
    const domains: DomainLink[] = orderedIds.map((nodeId, i) => {
        const node = space.nodes.get(nodeId);
        const typed = node?.kernelRef !== undefined;
        let spaceName: string | undefined;

        if (typed && node?.kernelRef !== undefined) {
            const kernel = registry.kernels.get(node.kernelRef);
            spaceName = kernel?.space.name;
        }

        return {
            label: node?.label ?? nodeId,
            nodeId,
            position: i,
            typed,
            kernelId: node?.kernelRef,
            spaceName,
        };
    });

    // Check if chain loops
    const lastId = orderedIds[orderedIds.length - 1];
    const firstId = orderedIds[0];
    const loops = dotAdj.get(lastId) === firstId;

    const typedCount = domains.filter(d => d.typed).length;

    return {
        ewsSpaceName,
        domains,
        totalDomains: domains.length,
        typedCount,
        untypedCount: domains.length - typedCount,
        completeness: domains.length > 0 ? typedCount / domains.length : 0,
        loops,
    };
}

/**
 * Get the production chain for a content kernel via its ewsRef.
 * Returns null if the kernel has no EWS declared.
 */
export function getKernelProductionChain(
    registry: Registry,
    spaceName: SpaceName,
): ProductionChain | null {
    const space = registry.spaces.get(spaceName);
    if (!space?.ewsRef) return null;
    return getProductionChain(registry, space.ewsRef);
}
