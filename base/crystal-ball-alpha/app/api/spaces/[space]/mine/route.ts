/* ═══════════════════════════════════════════════════════════
   GET /api/spaces/[space]/mine
   
   Compute the mine plane for a space — the configuration space
   as a set of heatmap points.
   
   Query params:
     coordinate — root coordinate to mine from (default: "0")
     maxConfigs — maximum configurations to enumerate (default: 500)
   ═══════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from 'next/server';
import { computeMinePlane } from '@/lib/crystal-ball/mine';
import {
    createRegistry,
    type Registry,
    type Space,
    deserialize,
} from '@/lib/crystal-ball/index';
import { db } from '@/lib/db/drizzle';
import { spaces } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';

// Shared registry for cross-space resolution
const registry: Registry = createRegistry();

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ space: string }> },
) {
    const { space: spaceName } = await params;
    const { searchParams } = new URL(request.url);
    const coordinate = searchParams.get('coordinate') || '0';
    const maxConfigs = parseInt(searchParams.get('maxConfigs') || '500', 10);

    // TODO: auth — use teamId from session
    const teamId = 1;

    try {
        // Load space from DB
        const rows = await db
            .select()
            .from(spaces)
            .where(and(eq(spaces.teamId, teamId), eq(spaces.name, spaceName)));

        if (rows.length === 0) {
            return NextResponse.json(
                { error: `Space "${spaceName}" not found` },
                { status: 404 },
            );
        }

        const data = rows[0].data as any;
        if (data) {
            const space: Space = deserialize(data);
            registry.spaces.set(spaceName, space);
        }

        const result = computeMinePlane(registry, spaceName, coordinate, maxConfigs);

        return NextResponse.json(result);
    } catch (err: any) {
        console.error('Mine error:', err);
        return NextResponse.json(
            { error: err.message || 'Mine computation failed' },
            { status: 500 },
        );
    }
}
