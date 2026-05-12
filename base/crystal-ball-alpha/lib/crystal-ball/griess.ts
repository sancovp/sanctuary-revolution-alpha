/* ═══════════════════════════════════════════════════════════
   griess.ts — Griess Constructor for Crystal Ball
   
   A compiler that takes a declared target automorphism group
   (κ_user) and outputs guarded state machines whose correctness
   criterion is "preserve κ_user under the relevant symmetry
   action(s)."
   
   This is the CB-side state machine. The Python version in
   YOUKNOW handles validation. This one enforces phase transitions
   and tracks κ_user declarations per space.
   
   The state machine is the Universal Instruction Set:
     DERIVE  → create  (declare κ_user — say the thing)
     COMPUTE → bloom   (derive constraints — what must exist)
     BUILD   → fill    (construct algebra — build it)
     VERIFY  → lock+mine (check Aut — does it match κ_user?)
     ONT     → reify   (Aut closes — next Futamura level)
     SOUP    → refill  (Aut fails — fix what VERIFY told you)
   ═══════════════════════════════════════════════════════════ */

// ─── Types ───────────────────────────────────────────────

export type GriessPhase =
    | 'derive'     // Y1: Declare κ_user
    | 'compute'    // Y2: Derive constraints
    | 'build'      // Y3: Construct algebra
    | 'verify'     // Y4: Check Aut
    | 'ont'        // Aut closes → admitted
    | 'soup'       // Aut fails → retry with feedback
    | 'pattern'    // Y5: Class from verified instances
    | 'implement'; // Y6: Meta-compilable pattern

/** κ_user — the target automorphism group for a space */
export interface KappaUser {
    domain: string;
    invariants: Record<string, string>;  // name → description
    // What must be preserved under all valid transformations
}

/** Per-space Griess state */
export interface GriessState {
    spaceName: string;
    phase: GriessPhase;
    kappa: KappaUser | null;
    sesDepth: number;        // Futamura level
    history: string[];
}

// ─── Transition Rules ────────────────────────────────────
// Each phase has exactly ONE valid forward transition (plus failure).
// You CANNOT go BUILD → BUILD. The state machine FORCES measurement.

const TRANSITIONS: Record<GriessPhase, GriessPhase[]> = {
    derive: ['compute'],
    compute: ['build'],
    build: ['verify'],
    verify: ['ont', 'soup'],
    ont: ['pattern'],
    pattern: ['implement'],
    implement: ['derive'],    // SES+1: next Futamura level
    soup: ['derive'],    // Retry with what you learned
};

const PHASE_LABELS: Record<GriessPhase, string> = {
    derive: 'Y1: Declare κ_user — say what you\'re building for',
    compute: 'Y2: Derive constraints — what must exist',
    build: 'Y3: Construct algebra — fill the space',
    verify: 'Y4: Check Aut — does it match κ_user?',
    ont: 'Aut closes — admitted, ready for next level',
    soup: 'Aut fails — fix what broke, retry',
    pattern: 'Y5: Class from verified instances',
    implement: 'Y6: Meta-compilable — SES+1 ready',
};

// ─── Registry ────────────────────────────────────────────

const griessStates = new Map<string, GriessState>();

/** Get or create Griess state for a space */
export function getGriessState(spaceName: string): GriessState {
    let state = griessStates.get(spaceName);
    if (!state) {
        state = {
            spaceName,
            phase: 'derive',
            kappa: null,
            sesDepth: 0,
            history: [`registered at derive`],
        };
        griessStates.set(spaceName, state);
    }
    return state;
}

/** Declare κ_user for a space — the DERIVE step.
 *  This MUST be called before the space can advance past DERIVE.
 *  This is customer interviews. This is saying the thing first. */
export function declareKappa(
    spaceName: string,
    domain: string,
    invariants: Record<string, string>,
): GriessState {
    const state = getGriessState(spaceName);
    state.kappa = { domain, invariants };
    state.history.push(`κ_user declared: ${domain} with ${Object.keys(invariants).length} invariants`);
    return state;
}

/** Advance a space to the next Griess phase.
 *  Enforces transition rules. Refuses invalid moves.
 *  Returns the updated state or throws. */
export function advanceGriess(
    spaceName: string,
    toPhase: GriessPhase,
    reason: string = '',
): GriessState {
    const state = getGriessState(spaceName);
    const valid = TRANSITIONS[state.phase];

    if (!valid.includes(toPhase)) {
        throw new Error(
            `Invalid Griess transition: ${state.phase} → ${toPhase}. ` +
            `Valid: [${valid.join(', ')}]. ${PHASE_LABELS[state.phase]}`
        );
    }

    // Guard: cannot leave DERIVE without κ_user
    if (state.phase === 'derive' && !state.kappa) {
        throw new Error(
            `Cannot leave DERIVE without declaring κ_user. ` +
            `Call declareKappa() first. You must say what you're building for.`
        );
    }

    const oldPhase = state.phase;
    state.phase = toPhase;

    // Track SES depth
    if (oldPhase === 'implement' && toPhase === 'derive') {
        state.sesDepth++;
    }

    let entry = `${oldPhase} → ${toPhase}`;
    if (reason) entry += ` (${reason})`;
    state.history.push(entry);

    return state;
}

/** Map CB operation to the expected Griess transition.
 *  Returns the target phase, or null if no transition applies. */
export function cbOperationToGriess(
    operation: 'create' | 'bloom' | 'fill' | 'lock' | 'mine' | 'reify' | 'unlock',
): GriessPhase | null {
    switch (operation) {
        case 'create': return 'derive';    // Space created → should be in derive
        case 'bloom': return 'compute';   // Blooming → deriving constraints
        case 'fill': return 'build';     // Filling → constructing algebra
        case 'lock': return 'verify';    // Locking → measurement
        case 'mine': return null;        // Mining is PART of verify, not a transition
        case 'reify': return 'ont';       // Reifying → Aut closes
        case 'unlock': return null;        // Unlocking goes back through soup
        default: return null;
    }
}

/** Try to advance a space based on a CB operation.
 *  Returns the new state if transition is valid, null if not applicable.
 *  Does NOT throw — caller decides whether to enforce or advise. */
export function tryAdvanceFromCB(
    spaceName: string,
    operation: 'create' | 'bloom' | 'fill' | 'lock' | 'mine' | 'reify' | 'unlock',
    reason: string = '',
): { state: GriessState; advanced: boolean; message: string } {
    const targetPhase = cbOperationToGriess(operation);
    if (!targetPhase) {
        return {
            state: getGriessState(spaceName),
            advanced: false,
            message: `Operation "${operation}" has no Griess transition`,
        };
    }

    const state = getGriessState(spaceName);
    const valid = TRANSITIONS[state.phase];

    // Already at or past the target phase
    if (state.phase === targetPhase) {
        return { state, advanced: false, message: `Already at ${targetPhase}` };
    }

    // Check if transition is valid
    if (!valid.includes(targetPhase)) {
        // Not an error — just advisory. The user might be doing things out of order.
        return {
            state,
            advanced: false,
            message: `⚠️ Griess: ${operation} wants ${targetPhase}, but current phase is ${state.phase}. ` +
                `Valid next: [${valid.join(', ')}]. ${PHASE_LABELS[state.phase]}`,
        };
    }

    // Check κ_user guard
    if (state.phase === 'derive' && !state.kappa) {
        return {
            state,
            advanced: false,
            message: `⚠️ Griess: Cannot advance past DERIVE — no κ_user declared. ` +
                `Declare what this space is for first.`,
        };
    }

    // Advance
    try {
        const updated = advanceGriess(spaceName, targetPhase, reason || operation);
        return {
            state: updated,
            advanced: true,
            message: `Griess: ${state.phase} → ${targetPhase} ✓`,
        };
    } catch (e) {
        return {
            state,
            advanced: false,
            message: (e as Error).message,
        };
    }
}

/** Format the Griess state for display */
export function formatGriessState(spaceName: string): string {
    const state = getGriessState(spaceName);
    const lines: string[] = [
        `⚙️ Griess: ${spaceName}`,
        `  Phase: ${state.phase.toUpperCase()} — ${PHASE_LABELS[state.phase]}`,
        `  SES depth: ${state.sesDepth}`,
    ];

    if (state.kappa) {
        lines.push(`  κ_user: ${state.kappa.domain}`);
        for (const [name, desc] of Object.entries(state.kappa.invariants)) {
            lines.push(`    • ${name}: ${desc}`);
        }
    } else {
        lines.push(`  κ_user: ⚠️ NOT DECLARED — say what this space is for`);
    }

    const valid = TRANSITIONS[state.phase];
    lines.push(`  Next valid: [${valid.join(', ')}]`);

    return lines.join('\n');
}

/** Get all spaces and their phases */
export function griessStatus(): {
    total: number;
    byPhase: Record<string, string[]>;
    missingKappa: string[];
    stuckInBuild: string[];
} {
    const byPhase: Record<string, string[]> = {};
    const missingKappa: string[] = [];
    const stuckInBuild: string[] = [];

    for (const [name, state] of griessStates) {
        const phase = state.phase;
        if (!byPhase[phase]) byPhase[phase] = [];
        byPhase[phase].push(name);

        if (!state.kappa) missingKappa.push(name);
        if (state.phase === 'build') stuckInBuild.push(name);
    }

    return {
        total: griessStates.size,
        byPhase,
        missingKappa,
        stuckInBuild,
    };
}

// ─── VERIFY: The Aut Check ───────────────────────────────
// Check if the built algebra's orbits preserve κ_user invariants.
// This is the measurement that determines ONT (success) or SOUP (fail).

export interface InvariantCheck {
    invariantName: string;
    invariantDescription: string;
    satisfied: boolean;
    reason: string;
    /** Nodes in the space whose labels relate to this invariant */
    relatedNodes: { id: string; label: string; locked: boolean; amplitude: number }[];
}

export interface VerifyReport {
    spaceName: string;
    domain: string;
    totalInvariants: number;
    satisfiedCount: number;
    failedCount: number;
    invariants: InvariantCheck[];
    outcome: 'ont' | 'soup';   // Passes → ONT, fails → SOUP
    sha: number;               // |Ш| at time of verify
    summary: string;
}

/**
 * Verify a space against its κ_user invariants.
 *
 * For each κ_user invariant:
 *   1. Find nodes in the space whose labels relate to the invariant
 *      (fuzzy match: label contains invariant name or vice versa)
 *   2. Check if at least one related node is locked (committed)
 *   3. Check if related nodes have amplitude > 0 (not Born 0)
 *   4. If no related nodes found → FAIL (invariant not addressed)
 *   5. If related nodes found but none locked → FAIL (not committed)
 *   6. If related nodes locked and amplitude > 0 → PASS
 *
 * Overall:
 *   All pass → ONT (Aut closes)
 *   Any fail → SOUP (what broke, why, fix suggestions)
 *
 * @param space The CB space to verify
 * @param sha Current |Ш| from tower check
 */
export function verifyKappa(
    spaceName: string,
    spaceNodes: Map<string, { id: string; label: string; locked?: boolean; frozen?: boolean; amplitude?: number; children: string[] }>,
    sha: number = 0,
): VerifyReport {
    const state = getGriessState(spaceName);

    if (!state.kappa) {
        return {
            spaceName,
            domain: 'unknown',
            totalInvariants: 0,
            satisfiedCount: 0,
            failedCount: 0,
            invariants: [],
            outcome: 'soup',
            sha,
            summary: '⚠️ No κ_user declared — cannot verify. Call declareKappa() first.',
        };
    }

    const { domain, invariants } = state.kappa;
    const checks: InvariantCheck[] = [];

    for (const [invName, invDesc] of Object.entries(invariants)) {
        // Fuzzy search: find nodes whose label relates to this invariant
        // Match if label contains any word from the invariant name (case insensitive)
        const invWords = invName.toLowerCase().split(/[_\s]+/);
        const relatedNodes: InvariantCheck['relatedNodes'] = [];

        for (const [nodeId, node] of spaceNodes) {
            const labelLower = node.label.toLowerCase();
            const matches = invWords.some(w => labelLower.includes(w)) ||
                invWords.some(w => w.includes(labelLower));

            if (matches) {
                relatedNodes.push({
                    id: nodeId,
                    label: node.label,
                    locked: !!(node.locked || node.frozen),
                    amplitude: node.amplitude ?? 0,
                });
            }
        }

        let satisfied = false;
        let reason = '';

        if (relatedNodes.length === 0) {
            reason = `No nodes found matching invariant "${invName}". This invariant has not been addressed.`;
        } else {
            const locked = relatedNodes.filter(n => n.locked);
            const withAmplitude = relatedNodes.filter(n => n.amplitude > 0);

            if (locked.length === 0) {
                reason = `Found ${relatedNodes.length} related node(s) but none are locked. ` +
                    `Invariant "${invName}" is not committed yet.`;
            } else if (withAmplitude.length === 0) {
                reason = `Related nodes exist but all have Born 0 amplitude. ` +
                    `Invariant "${invName}" is uninterpretable from this encoding.`;
            } else {
                satisfied = true;
                reason = `${locked.length} locked node(s) with amplitude > 0. ` +
                    `Invariant "${invName}" is committed and interpretable.`;
            }
        }

        checks.push({
            invariantName: invName,
            invariantDescription: invDesc,
            satisfied,
            reason,
            relatedNodes,
        });
    }

    const satisfiedCount = checks.filter(c => c.satisfied).length;
    const failedCount = checks.length - satisfiedCount;
    const allPass = failedCount === 0 && sha === 0;

    const outcome: 'ont' | 'soup' = allPass ? 'ont' : 'soup';

    let summary: string;
    if (allPass) {
        summary = `✅ Aut(${spaceName}) preserves all ${checks.length} κ_user invariants. ` +
            `|Ш| = 0. → ONT (admitted, ready for next level).`;
    } else {
        const failedNames = checks.filter(c => !c.satisfied).map(c => c.invariantName);
        summary = `❌ ${failedCount}/${checks.length} κ_user invariants NOT preserved: ` +
            `[${failedNames.join(', ')}]. |Ш| = ${sha}. → SOUP (fix these, retry).`;
    }

    // Record in Griess history
    state.history.push(`VERIFY: ${outcome.toUpperCase()} — ${satisfiedCount}/${checks.length} invariants, |Ш|=${sha}`);

    return {
        spaceName,
        domain,
        totalInvariants: checks.length,
        satisfiedCount,
        failedCount,
        invariants: checks,
        outcome,
        sha,
        summary,
    };
}

/** Format a verify report for display */
export function formatVerifyReport(report: VerifyReport): string {
    const lines: string[] = [
        `⚙️ Griess VERIFY: ${report.spaceName}`,
        `  Domain: ${report.domain}`,
        `  Outcome: ${report.outcome === 'ont' ? '✅ ONT' : '❌ SOUP'}`,
        `  Invariants: ${report.satisfiedCount}/${report.totalInvariants} satisfied`,
        `  |Ш|: ${report.sha}`,
        '',
    ];

    for (const check of report.invariants) {
        const icon = check.satisfied ? '✅' : '❌';
        lines.push(`  ${icon} ${check.invariantName}: ${check.invariantDescription}`);
        lines.push(`     ${check.reason}`);
        if (check.relatedNodes.length > 0) {
            for (const n of check.relatedNodes) {
                const lockStr = n.locked ? '🔒' : '○';
                lines.push(`     ${lockStr} ${n.label} (amp=${n.amplitude.toFixed(2)})`);
            }
        }
    }

    lines.push('');
    lines.push(`  ${report.summary}`);

    return lines.join('\n');
}
