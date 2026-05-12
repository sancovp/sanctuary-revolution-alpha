/**
 * Crystal Ball SaaS — API Key Authentication
 * 
 * Validates API keys from the `api_keys` table.
 * MCP clients send: Authorization: Bearer <key>
 * 
 * Keys are prefixed: cb_live_<random> (production) / cb_test_<random> (test)
 */

import { db } from '@/lib/db/drizzle';
import { apiKeys, teamMembers, teams } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';
import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';

// ─── Types ────────────────────────────────────────────────────────

export interface ApiKeyAuth {
    keyId: number;
    teamId: number;
    userId: number;
    planName: string | null;
}

// ─── Key Validation ───────────────────────────────────────────────

/**
 * Extract API key from request headers
 */
function extractApiKey(req: NextRequest): string | null {
    // Bearer token
    const authHeader = req.headers.get('authorization');
    if (authHeader?.startsWith('Bearer ')) {
        return authHeader.slice(7);
    }

    // X-API-Key header
    const xApiKey = req.headers.get('x-api-key');
    if (xApiKey) return xApiKey;

    // Query param (for convenience/testing)
    const url = new URL(req.url);
    return url.searchParams.get('api_key');
}

/**
 * Validate an API key and return auth context
 */
async function validateApiKey(key: string): Promise<ApiKeyAuth | null> {
    const rows = await db
        .select({
            keyId: apiKeys.id,
            teamId: apiKeys.teamId,
            userId: apiKeys.userId,
            isActive: apiKeys.isActive,
            planName: teams.planName,
        })
        .from(apiKeys)
        .innerJoin(teams, eq(apiKeys.teamId, teams.id))
        .where(and(eq(apiKeys.key, key), eq(apiKeys.isActive, true)));

    if (rows.length === 0) return null;

    // Update last_used_at
    await db
        .update(apiKeys)
        .set({ lastUsedAt: new Date() })
        .where(eq(apiKeys.id, rows[0].keyId));

    return {
        keyId: rows[0].keyId,
        teamId: rows[0].teamId,
        userId: rows[0].userId,
        planName: rows[0].planName,
    };
}

// ─── Middleware ────────────────────────────────────────────────────

type ApiHandler = (
    req: NextRequest,
    auth: ApiKeyAuth,
    params?: any
) => Promise<NextResponse>;

/**
 * Wrap an API route with API key authentication
 */
export function withApiKeyAuth(handler: ApiHandler) {
    return async (req: NextRequest, context?: any) => {
        const key = extractApiKey(req);
        if (!key) {
            return NextResponse.json(
                { error: 'API key required. Send via Authorization: Bearer <key>' },
                { status: 401 }
            );
        }

        const auth = await validateApiKey(key);
        if (!auth) {
            return NextResponse.json(
                { error: 'Invalid or revoked API key' },
                { status: 401 }
            );
        }

        return handler(req, auth, context?.params);
    };
}

// ─── Key Generation ───────────────────────────────────────────────

/**
 * Generate a new API key for a team member
 */
export async function generateApiKey(
    teamId: number,
    userId: number,
    name: string = 'Default'
): Promise<string> {
    const prefix = process.env.NODE_ENV === 'production' ? 'cb_live_' : 'cb_test_';
    const key = prefix + crypto.randomBytes(24).toString('base64url');

    await db.insert(apiKeys).values({
        key,
        teamId,
        userId,
        name,
    });

    return key;
}

/**
 * Revoke an API key
 */
export async function revokeApiKey(keyId: number, teamId: number): Promise<boolean> {
    const result = await db
        .update(apiKeys)
        .set({ isActive: false, revokedAt: new Date() })
        .where(and(eq(apiKeys.id, keyId), eq(apiKeys.teamId, teamId)));

    return true;
}
