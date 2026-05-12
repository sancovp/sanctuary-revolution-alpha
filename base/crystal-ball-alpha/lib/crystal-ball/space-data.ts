/**
 * Crystal Ball — Space Data Helper
 * 
 * Provides full space data (all nodes) for the visualizer frontend.
 * Uses the engine's internal registry and DB to load complete space state.
 */

import { db } from '@/lib/db/drizzle';
import { spaces } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';
import {
    deserialize,
    isShielded,
    computeShieldRadius,
    computeHeat,
    isSpaceLigated,
    computeSpaceHeat,
    type SerializedCrystalBall,
    type SerializedNode,
} from './index';

interface VizNode {
    id: string;
    label: string;
    children: string[];
    slotCount: number;
    childLabels: string[];
    depth: number;
    producedSpace?: string;
    stratum?: string;
    shielded: boolean;
    shieldRadius: number;
    heat: number;
}

interface VizSpace {
    name: string;
    rootId: string;
    nodes: VizNode[];
    /** Space-level sensors */
    ligated: boolean;     // All slotted nodes fully filled?
    spaceHeat: number;    // Aggregate heat across all nodes
    // towerDepth: number — requires cross-space registry, TODO
}

/**
 * Get full space data suitable for the 3D visualizer.
 * Returns all nodes with depth, stratum, and children.
 */
export async function getFullSpaceData(teamId: number, spaceName: string): Promise<VizSpace> {
    const rows = await db
        .select()
        .from(spaces)
        .where(and(eq(spaces.teamId, teamId), eq(spaces.name, spaceName)));

    if (rows.length === 0) {
        throw new Error(`Space "${spaceName}" not found`);
    }

    const rawData = rows[0].data as SerializedCrystalBall;
    const space = deserialize(rawData);

    // Compute depths via BFS from root
    const depthMap = new Map<string, number>();
    const queue: { id: string; depth: number }[] = [{ id: space.rootId, depth: 0 }];
    while (queue.length > 0) {
        const { id, depth } = queue.shift()!;
        if (depthMap.has(id)) continue;
        depthMap.set(id, depth);
        const node = space.nodes.get(id);
        if (node) {
            for (const childId of node.children) {
                queue.push({ id: childId, depth: depth + 1 });
            }
        }
    }

    // Convert to viz nodes
    const vizNodes: VizNode[] = [];
    for (const [, node] of space.nodes) {
        vizNodes.push({
            id: node.id,
            label: node.label,
            children: [...node.children],
            slotCount: node.slotCount ?? 0,
            childLabels: node.children.map(cid => {
                const child = space.nodes.get(cid);
                return child?.label ?? cid;
            }),
            depth: depthMap.get(node.id) ?? 0,
            producedSpace: node.producedSpace,
            stratum: node.stratum,
            shielded: isShielded(node),
            shieldRadius: computeShieldRadius(node),
            heat: computeHeat(node),
        });
    }

    return {
        name: space.name,
        rootId: space.rootId,
        nodes: vizNodes,
        ligated: isSpaceLigated(space),
        spaceHeat: computeSpaceHeat(space),
    };
}
