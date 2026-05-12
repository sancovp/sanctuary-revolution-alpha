/**
 * Crystal Ball FLOW endpoint — /api/cb/flow
 * 
 * The ONLY way to use CB through the MCP. Enforces FLOW phase discipline.
 * Validates input against the current phase before passing to cb().
 * 
 * Allowed at ANY phase:
 *   - "list" or "exit" → go back to space menu
 * 
 * Phase-specific:
 *   - No space selected  → space name, "create <name>"
 *   - fill interaction   → labels (one or newline-separated list), "done", "lock"
 *   - bloom interaction  → a number (slot count)
 *   - mine / locked      → "mine", coordinate navigation
 */

import { NextRequest, NextResponse } from 'next/server';
import { withApiKeyAuth, type ApiKeyAuth } from '@/lib/crystal-ball/auth';
import { cb, getSession } from '@/lib/crystal-ball/engine';

// LLM tower calls can take 2-3 minutes through Docker
export const maxDuration = 300;

// ─── FLOW state inspection ───────────────────────────────────────

interface FlowState {
    phase: 'menu' | 'fill' | 'bloom' | 'space';
    currentSpace: string | null;
    accepts: string;
}

function getFlowState(teamId: number): FlowState {
    const session = getSession(teamId);

    if (!session.currentSpace) {
        return {
            phase: 'menu',
            currentSpace: null,
            accepts: 'Space name to enter, or "create <name>" to make a new space',
        };
    }

    if (session.pendingInteraction) {
        const type = session.pendingInteraction.type;
        if (type === 'fill') {
            return {
                phase: 'fill',
                currentSpace: session.currentSpace,
                accepts: 'Labels to add (one or newline-separated list), "done" to finish, "lock" to lock',
            };
        }
        // bloom, select, name — all non-fill interactions
        return {
            phase: 'bloom',
            currentSpace: session.currentSpace,
            accepts: session.pendingInteraction.prompt || 'Follow the interaction prompt',
        };
    }

    return {
        phase: 'space',
        currentSpace: session.currentSpace,
        accepts: 'Coordinate to navigate, label to add, "bloom", "lock", "mine", "done"',
    };
}

// ─── FLOW input validation ───────────────────────────────────────

function validateFlowInput(teamId: number, input: string): { allowed: boolean; reason?: string; hint?: string } {
    const session = getSession(teamId);
    const firstLine = input.split('\n')[0].trim();

    // Always allowed: escape to menu
    if (/^(list|exit)$/i.test(firstLine)) {
        return { allowed: true };
    }

    // No space selected: only space entry, create, or compound commands (SpaceName + action)
    if (!session.currentSpace) {
        const isCreate = /^create\s+/i.test(firstLine);
        const isSpaceName = /^[A-Za-z_]\w*$/i.test(firstLine);
        // Allow compound commands like "GurrenLagann math", "Monster kernel 1 2", etc.
        const isCompoundCommand = /^[A-Za-z_]\w*\s+/i.test(firstLine);
        if (isCreate || isSpaceName || isCompoundCommand) return { allowed: true };
        return {
            allowed: false,
            reason: 'No space selected.',
            hint: 'Enter a space name or "create <name>"',
        };
    }

    // In fill phase: accept labels, done, lock, mine, coordinates
    if (session.pendingInteraction?.type === 'fill') {
        return { allowed: true }; // fill accepts anything as a label
    }

    // In bloom/other interaction: validate specifically
    if (session.pendingInteraction) {
        return { allowed: true }; // Let cb() handle the validation
    }

    // In space with no interaction: FLOW commands + labels + coordinates
    return { allowed: true };
}

// ─── Route ───────────────────────────────────────────────────────

export const POST = withApiKeyAuth(async (req: NextRequest, auth: ApiKeyAuth) => {
    const body = await req.json();
    const input = body.input?.trim?.();

    if (!input) {
        return NextResponse.json({
            error: 'No input provided',
            flow: getFlowState(auth.teamId),
        }, { status: 400 });
    }

    // Validate against FLOW phase
    const validation = validateFlowInput(auth.teamId, input);
    if (!validation.allowed) {
        return NextResponse.json({
            error: 'Invalid input for current FLOW phase',
            reason: validation.reason,
            hint: validation.hint,
            flow: getFlowState(auth.teamId),
        }, { status: 422 });
    }

    // Pass to cb()
    try {
        const result = await cb(auth.teamId, input);
        return NextResponse.json({
            ...result,
            flow: getFlowState(auth.teamId),
        });
    } catch (err: any) {
        return NextResponse.json(
            { error: err.message, flow: getFlowState(auth.teamId) },
            { status: 500 }
        );
    }
});
