/**
 * Crystal Ball API — /api/spaces/[space]
 * 
 * GET — Get full space data for the visualizer.
 *       Returns all nodes with their structure so the 3D scene can render.
 *       No auth required (viz frontend).
 */

import { NextRequest, NextResponse } from 'next/server';
import { cb } from '@/lib/crystal-ball/engine';

// Default team for local dev
const DEV_TEAM_ID = 1;

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
};

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ space: string }> }
) {
    const { space: spaceName } = await params;

    try {
        // Enter the space via cb() to load it and get full data
        const result = await cb(DEV_TEAM_ID, spaceName);

        if (result.cursor?.space !== spaceName) {
            return NextResponse.json(
                { error: `Space "${spaceName}" not found` },
                { status: 404, headers: CORS_HEADERS }
            );
        }

        // Get space list for the response
        const listResult = await cb(DEV_TEAM_ID, 'list');
        const spaces = listResult.data?.spaces || [];

        // The cb() shell returns data for the root node.
        // We need ALL nodes in the space. Use the engine internals.
        // Import serialize and the registry to get the full space.
        const { getFullSpaceData } = await import('@/lib/crystal-ball/space-data');
        const spaceData = await getFullSpaceData(DEV_TEAM_ID, spaceName);

        return NextResponse.json({
            space: spaceData,
            spaces,
            activeSpace: spaceName,
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
