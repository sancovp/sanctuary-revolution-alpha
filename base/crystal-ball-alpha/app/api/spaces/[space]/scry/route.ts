/**
 * Crystal Ball API — /api/spaces/[space]/scry
 * 
 * POST — Scry a coordinate in the space.
 *        Used by the visualizer to resolve coordinates.
 */

import { NextRequest, NextResponse } from 'next/server';
import { cb } from '@/lib/crystal-ball/engine';

const DEV_TEAM_ID = 1;

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
};

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ space: string }> }
) {
    const { space: spaceName } = await params;

    try {
        const body = await req.json();
        const { coordinate, includeNodeIds } = body;

        if (!coordinate) {
            return NextResponse.json(
                { error: 'coordinate is required' },
                { status: 400, headers: CORS_HEADERS }
            );
        }

        // Use cb() shell to scry: "SpaceName coordinate"
        const result = await cb(DEV_TEAM_ID, `${spaceName} ${coordinate}`);

        return NextResponse.json({
            coordinate,
            view: result.view,
            data: result.data,
            interaction: result.interaction,
            cursor: result.cursor,
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
