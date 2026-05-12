/**
 * MineSpace Navigator API — /api/mine
 * 
 * No auth required — this is the local dev explorer.
 * Uses teamId=0 by default.
 */

import { NextRequest, NextResponse } from 'next/server';
import { cb } from '@/lib/crystal-ball/engine';

export const maxDuration = 60;

export async function POST(req: NextRequest) {
    const body = await req.json();
    const input = body.input?.trim?.();
    const teamId = 1; // Use existing team

    if (!input) {
        return NextResponse.json({ error: 'No input' }, { status: 400 });
    }

    try {
        const result = await cb(teamId, input);
        return NextResponse.json(result);
    } catch (err: any) {
        return NextResponse.json({ error: err.message }, { status: 500 });
    }
}
