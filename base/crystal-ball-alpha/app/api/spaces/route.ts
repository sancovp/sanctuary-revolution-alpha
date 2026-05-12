/**
 * Crystal Ball API — /api/spaces
 * 
 * REST endpoints for the visualizer frontend.
 * Uses cb() shell internally but returns structured data.
 */

import { NextRequest, NextResponse } from 'next/server';
import { cb } from '@/lib/crystal-ball/engine';

// Default team for local dev (no auth required for viz)
const DEV_TEAM_ID = 1;

export async function GET() {
    try {
        const result = await cb(DEV_TEAM_ID, 'list');
        return NextResponse.json({
            spaces: result.data?.spaces || [],
            activeSpace: result.cursor?.space || result.data?.spaces?.[0] || '',
        }, {
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'content-type',
            },
        });
    } catch (err: any) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}

export async function OPTIONS() {
    return new NextResponse(null, {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'content-type',
        },
    });
}
