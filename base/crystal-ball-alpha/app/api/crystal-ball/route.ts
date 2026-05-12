/**
 * Crystal Ball API — /api/crystal-ball
 * 
 * ONE route. ONE string input.
 * 
 * POST { input: "AIDA_Tweet 1.2" }
 *   → cb(teamId, "AIDA_Tweet 1.2")
 *   → { view, interaction?, cursor }
 */

import { NextRequest, NextResponse } from 'next/server';
import { withApiKeyAuth, type ApiKeyAuth } from '@/lib/crystal-ball/auth';
import { cb } from '@/lib/crystal-ball/engine';

// Swarm calls to MiniMax can take 45-60s
export const maxDuration = 120;

export const POST = withApiKeyAuth(async (req: NextRequest, auth: ApiKeyAuth) => {
    try {
        let input: string;

        const contentType = req.headers.get('content-type') || '';
        if (contentType.includes('text/plain')) {
            input = await req.text();
        } else {
            const body = await req.json();
            input = body.input || body.cmd || '';
        }

        const result = await cb(auth.teamId, input);
        return NextResponse.json(result);
    } catch (err: any) {
        const status = err.message?.includes('not found') ? 404
            : err.message?.includes('already exists') ? 409
                : 400;
        return NextResponse.json({ error: err.message }, { status });
    }
});
