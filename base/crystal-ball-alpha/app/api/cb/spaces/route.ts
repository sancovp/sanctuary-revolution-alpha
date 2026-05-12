/**
 * Crystal Ball API — /api/cb/spaces
 * 
 * GET  — List all spaces for the team
 * POST — Create a new space
 * 
 * Uses the cb() shell function since engine only exports that.
 */

import { NextRequest, NextResponse } from 'next/server';
import { withApiKeyAuth, type ApiKeyAuth } from '@/lib/crystal-ball/auth';
import { cb } from '@/lib/crystal-ball/engine';

export const GET = withApiKeyAuth(async (req: NextRequest, auth: ApiKeyAuth) => {
    const result = await cb(auth.teamId, 'list');
    return NextResponse.json({ spaces: result.data?.spaces || [], activeSpace: result.cursor?.space });
});

export const POST = withApiKeyAuth(async (req: NextRequest, auth: ApiKeyAuth) => {
    const body = await req.json();
    const { name } = body;

    if (!name || typeof name !== 'string') {
        return NextResponse.json({ error: 'name is required' }, { status: 400 });
    }

    try {
        const result = await cb(auth.teamId, `create ${name}`);
        return NextResponse.json(result);
    } catch (err: any) {
        return NextResponse.json({ error: err.message }, { status: 409 });
    }
});
