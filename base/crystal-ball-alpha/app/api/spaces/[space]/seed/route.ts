/**
 * Crystal Ball API — /api/spaces/[space]/seed
 * 
 * POST — Seed a space with a deep ontology tree.
 *        Accepts a recursive tree structure and builds it out.
 *        For dev/demo use.
 */

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db/drizzle';
import { spaces } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';
import {
    deserialize,
    serialize,
    addNode,
    setSlotCount,
    type SerializedCrystalBall,
    type Space,
    type CBNode,
} from '@/lib/crystal-ball/index';

const DEV_TEAM_ID = 1;

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
};

interface TreeNode {
    label: string;
    children?: TreeNode[];
    attributes?: { name: string; spectrum: string[]; defaultValue?: string }[];
    stratum?: string;
}

function buildTree(space: Space, parentId: string, children: TreeNode[]) {
    for (const child of children) {
        const node = addNode(space, parentId, child.label);
        if (child.stratum) {
            node.stratum = child.stratum as any;
        }
        if (child.children && child.children.length > 0) {
            buildTree(space, node.id, child.children);
        }
    }
}

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ space: string }> }
) {
    const { space: spaceName } = await params;

    try {
        const body = await req.json();
        const tree: TreeNode[] = body.tree;

        if (!tree || !Array.isArray(tree)) {
            return NextResponse.json(
                { error: 'tree is required (array of {label, children?, attributes?})' },
                { status: 400, headers: CORS_HEADERS }
            );
        }

        // Load the space
        const rows = await db
            .select()
            .from(spaces)
            .where(and(eq(spaces.teamId, DEV_TEAM_ID), eq(spaces.name, spaceName)));

        if (rows.length === 0) {
            return NextResponse.json(
                { error: `Space "${spaceName}" not found` },
                { status: 404, headers: CORS_HEADERS }
            );
        }

        const rawData = rows[0].data as SerializedCrystalBall;
        const space = deserialize(rawData);

        // Build the tree under root
        buildTree(space, space.rootId, tree);

        // Save back
        const serialized = serialize(space);
        await db
            .update(spaces)
            .set({ data: serialized as any, updatedAt: new Date() })
            .where(eq(spaces.id, rows[0].id));

        // Count total nodes
        let totalNodes = 0;
        for (const [,] of space.nodes) totalNodes++;

        return NextResponse.json({
            ok: true,
            space: spaceName,
            totalNodes,
        }, { headers: CORS_HEADERS });
    } catch (err: any) {
        return NextResponse.json(
            { error: err.message },
            { status: 500, headers: CORS_HEADERS }
        );
    }
}

export async function OPTIONS() {
    return new NextResponse(null, { headers: CORS_HEADERS });
}
