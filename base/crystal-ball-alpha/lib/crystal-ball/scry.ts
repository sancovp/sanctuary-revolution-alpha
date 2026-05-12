/**
 * scry.ts — The Perturbation Daemon (Quantum Computation on CB Encoding)
 *
 * This is the scrying cycle: while the user isn't looking, the daemon
 * collapses superpositions via LLM, checks catastrophes, and converges
 * toward κ_user (crowning).
 *
 * The loop:
 *   1. Find CB 0 nodes (superposition, Born weight > 0)
 *   2. Select highest Born-weight target
 *   3. Call swarm to collapse it (LLM measurement)
 *   4. Check catastrophe surface
 *   5. If |Ш| increased → mark as Born 0 (encoding ambiguous from here)
 *   6. Born distribution updates automatically
 *   7. Repeat until converged or max iterations
 *   8. Check for crowning (Ш = 0 + lift conditions)
 *
 * This IS the quantum computation: interference (Born weights) guides
 * which paths to take, catastrophe surface constrains navigation,
 * and the system converges on the answer.
 */

import type { Registry, CrystalBall, CBNode } from './index';
import { getBornWeight, isInSuperposition, setAmplitude } from './index';
import { runSwarm, runBatchSwarm, computeAlgebraNeighborhoods, type SwarmResult, type AlgebraNeighborhood } from './swarm-agent';
import { buildFutamuraTower, type TowerResult } from './reify';
import { computeSpaceSlotSignature, takeKernelSnapshot, computeKernelTemperature, type KernelSnapshot, type TemperatureReading } from './kernel-v2';
import { tryAdvanceFromCB, getGriessState } from './griess';
import { rectifySpace, type RectificationResult, GMR_DEFAULTS } from './gmr';

// ─── Types ───────────────────────────────────────────────────────

/** Resolve a space name to a kernel ID for tower operations.
 *  Returns 0 as default if space has no explicit kernel ID. */
function resolveKernelId(registry: Registry, spaceName: string): number {
    // The kernel ID is typically the space's index in the registry
    const names = Array.from(registry.spaces.keys());
    const idx = names.indexOf(spaceName);
    return idx >= 0 ? idx : 0;
}

export interface ScryStep {
    iteration: number;
    targetNodeId: string;
    targetLabel: string;
    bornWeight: number;
    nodesCreated: number;
    nodesExcluded: number;
    temperature: TemperatureReading | null;
    catastrophesBefore: number;  // |Ш| before this step
    catastrophesAfter: number;   // |Ш| after this step
    reverted: boolean;           // Did we revert this step?
    revertReason?: string;
}

export interface ScryResult {
    spaceName: string;
    steps: ScryStep[];
    totalIterations: number;
    superpositionsRemaining: number;
    finalSha: number;
    crowned: boolean;
    converged: boolean;
    reason: string; // why we stopped
}

// ─── Helpers ─────────────────────────────────────────────────────

/** Find all nodes in superposition (CB 0, Born weight > 0). */
function findSuperpositions(space: CrystalBall): CBNode[] {
    const result: CBNode[] = [];
    for (const node of space.nodes.values()) {
        if (isInSuperposition(node)) {
            result.push(node);
        }
    }
    return result;
}

/** Find the superposition node with highest Born weight.
 *  When multiple have the same weight (all 1.0 in uniform prior),
 *  prefer deeper nodes (more constrained by context). */
function selectTarget(superpositions: CBNode[]): CBNode | null {
    if (superpositions.length === 0) return null;

    return superpositions.reduce((best, node) => {
        const bw = getBornWeight(node);
        const bestBw = getBornWeight(best);
        if (bw > bestBw) return node;
        // Tiebreak: deeper nodes are more constrained (more context)
        if (bw === bestBw && node.id.split('.').length > best.id.split('.').length) {
            return node;
        }
        return best;
    });
}

/** Count current |Ш| via a tower check. */
function currentSha(registry: Registry, spaceName: string): number {
    try {
        const kernelId = resolveKernelId(registry, spaceName);
        const tower = buildFutamuraTower(registry, kernelId);
        return tower.sha;
    } catch {
        return 0;
    }
}

// ─── The Scrying Cycle ───────────────────────────────────────────

/**
 * Run the perturbation daemon: collapse superpositions via LLM,
 * guided by Born weights and constrained by the catastrophe surface.
 *
 * This is the quantum computation on a CB encoding. Each step:
 *   - Selects the highest Born-weight superposition
 *   - Calls the swarm (LLM measurement)
 *   - Checks if |Ш| increased
 *   - If yes: marks the affected nodes as Born 0 (reverts)
 *   - If no: keeps the collapse, moves to next
 *
 * Stops when:
 *   - No superpositions remain (fully collapsed)
 *   - Max iterations hit
 *   - Crowned (Ш = 0 + lift conditions)
 *   - Temperature goes critical and stays critical (stuck)
 *
 * @param maxIterations Maximum LLM calls to make (default 10)
 * @param maxCritical Max consecutive critical-temperature steps before stopping
 */
export function scry(
    registry: Registry,
    spaceName: string,
    maxIterations: number = 10,
    maxCritical: number = 3,
): ScryResult {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    const steps: ScryStep[] = [];
    let consecutiveCritical = 0;

    for (let i = 0; i < maxIterations; i++) {
        // 1. Find superpositions
        const superpositions = findSuperpositions(space);
        if (superpositions.length === 0) {
            // Fully collapsed — check for crowning
            const kernelId = resolveKernelId(registry, spaceName);
            const tower = buildFutamuraTower(registry, kernelId);
            return {
                spaceName,
                steps,
                totalIterations: i,
                superpositionsRemaining: 0,
                finalSha: tower.sha,
                crowned: tower.crowned,
                converged: true,
                reason: tower.crowned
                    ? '👑 CROWNED — Ш = 0, all superpositions collapsed, Monster-valid'
                    : `Fully collapsed but Ш = ${tower.sha} (${tower.catastrophes.length} catastrophes remain)`,
            };
        }

        // 2. Compute algebra neighborhoods (group related superpositions)
        const neighborhoods = computeAlgebraNeighborhoods(space);

        if (neighborhoods.length === 0) {
            // Fallback to single-node if neighborhoods empty
            const target = selectTarget(superpositions);
            if (!target) break;

            const snapshotBefore = takeKernelSnapshot(registry, spaceName);
            const shaBefore = currentSha(registry, spaceName);

            const swarmResult = runSwarm(registry, spaceName, target.id, 'fill', 3);

            const snapshotAfter = takeKernelSnapshot(registry, spaceName);
            const temp = computeKernelTemperature(snapshotBefore, snapshotAfter);
            const shaAfter = currentSha(registry, spaceName);

            let reverted = false;
            let revertReason: string | undefined;
            if (shaAfter > shaBefore && swarmResult.nodesCreated > 0) {
                for (const node of space.nodes.values()) {
                    if (node.amplitude !== undefined &&
                        node.amplitude === swarmResult.confidence &&
                        !node.locked && !node.frozen) {
                        setAmplitude(space, node.id, 0);
                    }
                }
                reverted = true;
                revertReason = `Ш: ${shaBefore}→${shaAfter}`;
            }

            steps.push({
                iteration: i,
                targetNodeId: target.id, targetLabel: target.label,
                bornWeight: getBornWeight(target),
                nodesCreated: swarmResult.nodesCreated, nodesExcluded: 0,
                temperature: temp,
                catastrophesBefore: shaBefore, catastrophesAfter: shaAfter,
                reverted, revertReason,
            });

            tryAdvanceFromCB(spaceName, 'fill');
            continue;
        }

        // 3. Use the highest-priority neighborhood for this iteration
        //    (batch fills multiple nodes in one LLM call)
        const hood = neighborhoods[0];

        // Snapshot before
        const snapshotBefore = takeKernelSnapshot(registry, spaceName);
        const shaBefore = currentSha(registry, spaceName);

        // 4. GMR RECTIFICATION: clean the Born support BEFORE calling the swarm
        //    - Compute geometric confidence for each node in the neighborhood
        //    - Apply asymmetric cleaning (strict on redundant, permissive on scarce)
        //    - This makes "Born support" reflect a rectified manifold
        const gmrResult = rectifySpace(registry, spaceName, [hood], GMR_DEFAULTS);

        // 5. Batch swarm on the RECTIFIED support: one call for the neighborhood
        const batchResult = runBatchSwarm(registry, spaceName, 1, 3);
        const totalCreated = batchResult.totalCreated;
        const confidence = batchResult.results[0]?.confidence ?? 0;

        // 5. Snapshot after + temperature
        const snapshotAfter = takeKernelSnapshot(registry, spaceName);
        const temp = computeKernelTemperature(snapshotBefore, snapshotAfter);
        const shaAfter = currentSha(registry, spaceName);

        // 6. Catastrophe check
        let reverted = false;
        let revertReason: string | undefined;

        if (shaAfter > shaBefore && totalCreated > 0) {
            for (const node of space.nodes.values()) {
                if (node.amplitude !== undefined &&
                    node.amplitude === confidence &&
                    !node.locked && !node.frozen) {
                    setAmplitude(space, node.id, 0);
                }
            }
            reverted = true;
            revertReason = `Ш: ${shaBefore}→${shaAfter} (batch: ${hood.memberIds.length} nodes)`;
        }

        // 7. Track critical temperature
        if (temp.phase === 'critical') {
            consecutiveCritical++;
            if (consecutiveCritical >= maxCritical) {
                steps.push({
                    iteration: i,
                    targetNodeId: hood.anchorId, targetLabel: hood.anchorLabel,
                    bornWeight: getBornWeight(space.nodes.get(hood.anchorId) ?? {} as any),
                    nodesCreated: totalCreated, nodesExcluded: 0,
                    temperature: temp,
                    catastrophesBefore: shaBefore, catastrophesAfter: shaAfter,
                    reverted, revertReason,
                });

                const kernelId = resolveKernelId(registry, spaceName);
                const tower = buildFutamuraTower(registry, kernelId);
                return {
                    spaceName, steps,
                    totalIterations: i + 1,
                    superpositionsRemaining: findSuperpositions(space).length,
                    finalSha: tower.sha, crowned: tower.crowned,
                    converged: false,
                    reason: `🔥 Halted: ${maxCritical} critical steps — system stuck`,
                };
            }
        } else {
            consecutiveCritical = 0;
        }

        // 8. Record step
        steps.push({
            iteration: i,
            targetNodeId: hood.anchorId,
            targetLabel: `${hood.anchorLabel} (+${hood.memberIds.length - 1} neighbors)`,
            bornWeight: getBornWeight(space.nodes.get(hood.anchorId) ?? {} as any),
            nodesCreated: totalCreated,
            nodesExcluded: 0,
            temperature: temp,
            catastrophesBefore: shaBefore,
            catastrophesAfter: shaAfter,
            reverted, revertReason,
        });

        // Advance Griess if applicable
        tryAdvanceFromCB(spaceName, 'fill');
    }

    // Max iterations reached
    const kernelId = resolveKernelId(registry, spaceName);
    const tower = buildFutamuraTower(registry, kernelId);
    return {
        spaceName,
        steps,
        totalIterations: maxIterations,
        superpositionsRemaining: findSuperpositions(space).length,
        finalSha: tower.sha,
        crowned: tower.crowned,
        converged: false,
        reason: `Max iterations (${maxIterations}) reached. ${findSuperpositions(space).length} superpositions remain.`,
    };
}

/** Format a ScryResult for display */
export function formatScryResult(result: ScryResult): string {
    const lines: string[] = [
        `🔮 Scry Result: ${result.spaceName}`,
        ``,
        `  Steps: ${result.totalIterations}`,
        `  Superpositions remaining: ${result.superpositionsRemaining}`,
        `  |Ш|: ${result.finalSha}`,
        `  Crowned: ${result.crowned ? '👑 YES' : 'no'}`,
        `  Converged: ${result.converged ? '✓' : '✗'}`,
        `  Reason: ${result.reason}`,
    ];

    if (result.steps.length > 0) {
        lines.push('');
        lines.push('  Steps:');
        for (const step of result.steps) {
            const tempStr = step.temperature
                ? ` T=${step.temperature.temperature.toFixed(3)} (${step.temperature.phase})`
                : '';
            const revertStr = step.reverted ? ` ← REVERTED: ${step.revertReason}` : '';
            lines.push(
                `    ${step.iteration}: ${step.targetLabel} (Born=${step.bornWeight.toFixed(2)})` +
                ` → +${step.nodesCreated} nodes` +
                ` Ш: ${step.catastrophesBefore}→${step.catastrophesAfter}` +
                tempStr + revertStr
            );
        }
    }

    return lines.join('\n');
}
