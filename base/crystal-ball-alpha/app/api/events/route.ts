/**
 * Crystal Ball API — /api/events
 * 
 * Server-Sent Events endpoint.
 * Frontends connect here and receive live updates when /api/cb processes commands.
 * 
 * GET /api/events → SSE stream of cb results
 */

import { NextResponse } from 'next/server';
import { cbEventBus } from '@/lib/crystal-ball/event-bus';

const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type, authorization',
};

export const dynamic = 'force-dynamic';

export async function GET() {
    const encoder = new TextEncoder();
    let unsubscribe: (() => void) | null = null;
    let keepalive: ReturnType<typeof setInterval> | null = null;

    const stream = new ReadableStream({
        start(controller) {
            // Send initial keepalive
            controller.enqueue(encoder.encode(': connected\n\n'));

            // Subscribe to cb events
            unsubscribe = cbEventBus.subscribe((data) => {
                try {
                    const payload = `data: ${JSON.stringify(data)}\n\n`;
                    controller.enqueue(encoder.encode(payload));
                } catch {
                    // Stream closed by client
                }
            });

            // Keepalive every 15s to prevent timeout
            keepalive = setInterval(() => {
                try {
                    controller.enqueue(encoder.encode(': keepalive\n\n'));
                } catch {
                    // Stream closed
                }
            }, 15000);
        },
        cancel() {
            // Client disconnected — clean up
            if (keepalive) clearInterval(keepalive);
            if (unsubscribe) unsubscribe();
        },
    });

    return new NextResponse(stream, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Connection': 'keep-alive',
            ...CORS_HEADERS,
        },
    });
}

export async function OPTIONS() {
    return new NextResponse(null, { headers: CORS_HEADERS });
}
