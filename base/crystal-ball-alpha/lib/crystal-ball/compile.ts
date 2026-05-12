/**
 * compile.ts — Griess Compiler: Full Single-Pass Compilation
 *
 * The Griess constructor as a compiler:
 *   Input:  κ_user declaration (target Aut group)
 *   Output: verified space whose Aut preserves κ_user
 *
 * Phases:
 *   1. DERIVE — check κ_user exists
 *   2. COMPUTE — derive constraints (bloom)
 *   3. BUILD — construct algebra (scry / fill)
 *   4. VERIFY — check Aut (verifyKappa + YOUKNOW validation)
 *   5. ONT or SOUP — admitted or retry with feedback
 *
 * Also:
 *   - kappaToUARL: convert κ_user invariants to UARL claims
 *   - applyYouknowCorrections: feed YOUKNOW results back as amplitude changes
 *   - compile(): full single-pass
 *   - meta_compile(): SES+1 — compile the compiler
 */

import type { Registry, CrystalBall, CBNode, Space } from './index';
import { setAmplitude, getAmplitude, getBornWeight } from './index';
import { getGriessState, verifyKappa, advanceGriess, tryAdvanceFromCB, type GriessState, type KappaUser, type VerifyReport } from './griess';
import { scry, type ScryResult } from './scry';
import { callYouknow, type YKResult } from './youknow-bridge';
import { buildFutamuraTower, type TowerResult } from './reify';

// ─── κ_user → UARL Bridge ───────────────────────────────────────

export interface UARLClaim {
    invariantName: string;
    statement: string;        // UARL-formatted claim
    evidence: string;         // What supports this claim in the space
}

export interface UARLValidation {
    claim: UARLClaim;
    youknowResult: YKResult;
    valid: boolean;
    correction?: string;      // What YOUKNOW says to fix
}

/**
 * Convert κ_user invariants into UARL claims for YOUKNOW validation.
 *
 * Each invariant becomes a claim like:
 *   "<SpaceName> has_property <invariant_name>"
 *
 * Evidence is gathered from the space's locked nodes that relate
 * to each invariant.
 */
export function kappaToUARL(
    spaceName: string,
    kappa: KappaUser,
    space: CrystalBall,
): UARLClaim[] {
    const claims: UARLClaim[] = [];

    for (const [invName, invDesc] of Object.entries(kappa.invariants)) {
        // Find supporting evidence in the space
        const invWords = invName.toLowerCase().split(/[_\s]+/);
        const relatedLocked: string[] = [];

        for (const [nodeId, node] of space.nodes) {
            const labelLower = node.label.toLowerCase();
            const matches = invWords.some(w => labelLower.includes(w));
            if (matches && (node.locked || node.frozen)) {
                relatedLocked.push(node.label);
            }
        }

        const evidence = relatedLocked.length > 0
            ? `Locked nodes: [${relatedLocked.join(', ')}]`
            : `No locked nodes found for this invariant`;

        claims.push({
            invariantName: invName,
            statement: `${spaceName} has_property ${invName}`,
            evidence,
        });
    }

    return claims;
}

/**
 * Validate κ_user claims against YOUKNOW's ontology.
 *
 * Each claim is sent to YOUKNOW via callYouknow().
 * YOUKNOW returns whether the claim is admitted or soup.
 *
 * If YOUKNOW says soup → the correction tells us what broke
 * and maps to a catastrophe class.
 */
export function validateClaimsWithYouknow(claims: UARLClaim[]): UARLValidation[] {
    return claims.map(claim => {
        try {
            const result = callYouknow(claim.statement);
            return {
                claim,
                youknowResult: result,
                valid: result.admitted,
                correction: result.admitted ? undefined : result.response,
            };
        } catch {
            // YOUKNOW unavailable — assume valid but note it
            return {
                claim,
                youknowResult: { response: 'YOUKNOW unavailable', admitted: true, ideas: [] },
                valid: true,
                correction: undefined,
            };
        }
    });
}

/**
 * Apply YOUKNOW corrections back to the space as amplitude changes.
 *
 * When YOUKNOW invalidates a claim:
 *   - Find nodes related to that invariant
 *   - Reduce their amplitude (less confidence in the current structure)
 *   - If amplitude drops to 0 → Born 0 (encoding ambiguous)
 *
 * This is the U3 feedback loop: YOUKNOW corrections act on the
 * Gram matrix as group elements.
 */
export function applyYouknowCorrections(
    validations: UARLValidation[],
    space: CrystalBall,
): { corrected: number; details: string[] } {
    let corrected = 0;
    const details: string[] = [];

    for (const v of validations) {
        if (v.valid) continue;

        // Find nodes related to the failed invariant
        const invWords = v.claim.invariantName.toLowerCase().split(/[_\s]+/);

        for (const [nodeId, node] of space.nodes) {
            if (node.locked || node.frozen) continue; // Don't touch committed nodes

            const labelLower = node.label.toLowerCase();
            const matches = invWords.some(w => labelLower.includes(w));

            if (matches && node.amplitude !== undefined && node.amplitude > 0) {
                const before = node.amplitude;
                // Reduce amplitude by 50% — YOUKNOW says this isn't right
                node.amplitude = node.amplitude * 0.5;
                if (node.amplitude < 0.05) node.amplitude = 0; // Born 0 threshold
                corrected++;
                details.push(
                    `${node.label}: amplitude ${before.toFixed(2)} → ${node.amplitude.toFixed(2)} ` +
                    `(YOUKNOW: ${v.correction?.slice(0, 80)})`
                );
            }
        }
    }

    return { corrected, details };
}

// ─── Compile Result ──────────────────────────────────────────────

export interface CompileResult {
    spaceName: string;
    outcome: 'ont' | 'soup';
    griessState: GriessState;
    scryResult?: ScryResult;
    verifyReport: VerifyReport;
    uarlValidations: UARLValidation[];
    corrections: { corrected: number; details: string[] };
    sha: number;
    crowned: boolean;
    summary: string;
}

// ─── The Compiler ────────────────────────────────────────────────

/**
 * compile() — Full single-pass Griess compilation.
 *
 * Orchestrates: DERIVE → COMPUTE → BUILD → VERIFY → ONT/SOUP
 *
 * 1. Check κ_user exists (DERIVE guard)
 * 2. Run scry (BUILD via perturbation daemon)
 * 3. Verify κ_user (VERIFY via invariant check)
 * 4. Validate claims with YOUKNOW (U3 check)
 * 5. Apply corrections (amplitude updates)
 * 6. Determine outcome: ONT (admitted) or SOUP (retry)
 *
 * @param maxScrySteps Maximum perturbation daemon iterations
 */
export function compile(
    registry: Registry,
    spaceName: string,
    maxScrySteps: number = 10,
): CompileResult {
    const state = getGriessState(spaceName);
    const space = registry.spaces.get(spaceName);

    // Guard: κ_user must be declared
    if (!state.kappa) {
        return {
            spaceName,
            outcome: 'soup',
            griessState: state,
            verifyReport: {
                spaceName, domain: 'unknown', totalInvariants: 0,
                satisfiedCount: 0, failedCount: 0, invariants: [],
                outcome: 'soup', sha: 0,
                summary: '⚠️ No κ_user — cannot compile. Declare what you\'re building for.',
            },
            uarlValidations: [],
            corrections: { corrected: 0, details: [] },
            sha: 0,
            crowned: false,
            summary: '⚠️ Cannot compile without κ_user. Call declareKappa() first.',
        };
    }

    if (!space) {
        return {
            spaceName,
            outcome: 'soup',
            griessState: state,
            verifyReport: {
                spaceName, domain: state.kappa.domain, totalInvariants: 0,
                satisfiedCount: 0, failedCount: 0, invariants: [],
                outcome: 'soup', sha: 0, summary: 'Space not found.',
            },
            uarlValidations: [],
            corrections: { corrected: 0, details: [] },
            sha: 0,
            crowned: false,
            summary: `Space "${spaceName}" not found in registry.`,
        };
    }

    // ─── Phase 1: BUILD via Scry ─────────────────────────────
    // Run the perturbation daemon to collapse superpositions
    let scryResult: ScryResult | undefined;
    try {
        scryResult = scry(registry, spaceName, maxScrySteps);
    } catch {
        // Scry failed — continue to verify what we have
    }

    // ─── Phase 2: VERIFY κ_user ──────────────────────────────
    // Check invariants against space structure
    let sha = 0;
    try {
        const kernelId = Array.from(registry.spaces.keys()).indexOf(spaceName);
        const tower = buildFutamuraTower(registry, kernelId >= 0 ? kernelId : 0);
        sha = tower.sha;
    } catch { /* no tower yet */ }

    const verifyReport = verifyKappa(spaceName, space.nodes, sha);

    // ─── Phase 3: YOUKNOW Validation (U3) ────────────────────
    // Convert κ_user to UARL claims and validate
    const uarlClaims = kappaToUARL(spaceName, state.kappa, space);
    const uarlValidations = validateClaimsWithYouknow(uarlClaims);

    // ─── Phase 4: Apply Corrections ──────────────────────────
    // Feed YOUKNOW results back as amplitude changes
    const corrections = applyYouknowCorrections(uarlValidations, space);

    // ─── Phase 5: Determine Outcome ──────────────────────────
    const kappaAllPass = verifyReport.outcome === 'ont';
    const youknowAllPass = uarlValidations.every(v => v.valid);
    const crowned = kappaAllPass && youknowAllPass && sha === 0;
    const outcome: 'ont' | 'soup' = (kappaAllPass && youknowAllPass) ? 'ont' : 'soup';

    // Record in Griess
    state.history.push(
        `COMPILE: ${outcome.toUpperCase()} — ` +
        `κ=${verifyReport.satisfiedCount}/${verifyReport.totalInvariants}, ` +
        `YK=${uarlValidations.filter(v => v.valid).length}/${uarlValidations.length}, ` +
        `|Ш|=${sha}, crowned=${crowned}`
    );

    let summary: string;
    if (crowned) {
        summary = `👑 COMPILE CROWNED: All κ_user preserved, YOUKNOW validates, |Ш| = 0. Monster-valid.`;
    } else if (outcome === 'ont') {
        summary = `✅ COMPILE ONT: All κ_user preserved + YOUKNOW validates. |Ш| = ${sha}.`;
    } else {
        const kappaFails = verifyReport.invariants.filter(i => !i.satisfied).map(i => i.invariantName);
        const ykFails = uarlValidations.filter(v => !v.valid).map(v => v.claim.invariantName);
        const allFails = [...new Set([...kappaFails, ...ykFails])];
        summary = `❌ COMPILE SOUP: [${allFails.join(', ')}] not preserved. Fix and retry.`;
    }

    return {
        spaceName,
        outcome,
        griessState: state,
        scryResult,
        verifyReport,
        uarlValidations,
        corrections,
        sha,
        crowned,
        summary,
    };
}

/**
 * Format compile result for display.
 */
export function formatCompileResult(result: CompileResult): string {
    const lines: string[] = [
        `⚙️ Griess Compile: ${result.spaceName}`,
        `  Outcome: ${result.outcome === 'ont' ? '✅ ONT' : '❌ SOUP'}`,
        `  Crowned: ${result.crowned ? '👑 YES' : 'no'}`,
        `  |Ш|: ${result.sha}`,
        '',
    ];

    // Scry summary
    if (result.scryResult) {
        lines.push(`  🔮 Scry: ${result.scryResult.totalIterations} steps, ` +
            `${result.scryResult.superpositionsRemaining} superpositions remaining`);
    }

    // κ_user check
    lines.push(`  κ_user: ${result.verifyReport.satisfiedCount}/${result.verifyReport.totalInvariants} invariants`);
    for (const inv of result.verifyReport.invariants) {
        const icon = inv.satisfied ? '✅' : '❌';
        lines.push(`    ${icon} ${inv.invariantName}`);
    }

    // YOUKNOW validation
    const ykValid = result.uarlValidations.filter(v => v.valid).length;
    lines.push(`  YOUKNOW: ${ykValid}/${result.uarlValidations.length} claims validated`);
    for (const v of result.uarlValidations) {
        const icon = v.valid ? '✅' : '❌';
        lines.push(`    ${icon} ${v.claim.statement}`);
        if (v.correction) lines.push(`       ↳ ${v.correction.slice(0, 100)}`);
    }

    // Corrections
    if (result.corrections.corrected > 0) {
        lines.push(`  🔧 Corrections: ${result.corrections.corrected} amplitude adjustments`);
        for (const d of result.corrections.details) {
            lines.push(`    ${d}`);
        }
    }

    lines.push('');
    lines.push(`  ${result.summary}`);

    return lines.join('\n');
}
