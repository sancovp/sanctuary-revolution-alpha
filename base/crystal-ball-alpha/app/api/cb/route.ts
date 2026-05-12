/**
 * Crystal Ball API — /api/cb
 * 
 * ONE route. ONE string input.
 * 
 * POST { input: "AIDA_Tweet 1.2" }
 *   → cb(teamId, "AIDA_Tweet 1.2")
 *   → { view, interaction?, cursor }
 * 
 * Or POST with just text/plain body: "AIDA_Tweet 1.2"
 * 
 * The kernel is a shell. It tracks state. You talk to it.
 */

import { NextRequest, NextResponse } from 'next/server';
import { withApiKeyAuth, type ApiKeyAuth } from '@/lib/crystal-ball/auth';
import { cb } from '@/lib/crystal-ball/engine';
import { cbEventBus } from '@/lib/crystal-ball/event-bus';

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type, authorization',
};

export const POST = withApiKeyAuth(async (req: NextRequest, auth: ApiKeyAuth) => {
    try {
        let input: string;

        const contentType = req.headers.get('content-type') || '';
        if (contentType.includes('text/plain')) {
            input = await req.text();
        } else {
            const body = await req.json();
            // Accept { input: "..." } or { cmd: "..." } for MCP compat
            input = body.input || body.cmd || '';
        }

        const result = await cb(auth.teamId, input);

        // Push to connected frontends via SSE
        console.log(`[EventBus] Publishing cb_result, subscribers: ${cbEventBus.subscriberCount}`);
        cbEventBus.publish({ type: 'cb_result', input, result });

        return NextResponse.json(result, { headers: CORS_HEADERS });
    } catch (err: any) {
        console.error('[CB ERROR]', err.message, err.stack);
        const status = err.message?.includes('not found') ? 404
            : err.message?.includes('already exists') ? 409
                : 400;
        return NextResponse.json({ error: err.message }, { status, headers: CORS_HEADERS });
    }
});

export async function OPTIONS() {
    return new NextResponse(null, { headers: CORS_HEADERS });
}
