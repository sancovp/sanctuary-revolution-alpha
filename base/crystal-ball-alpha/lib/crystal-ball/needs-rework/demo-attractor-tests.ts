/**
 * demo-attractor-tests.ts — Is T^∞ a real attractor?
 * 
 * Test 1: Perturbation stability (noisy variants → same T^∞?)
 * Test 2: Basin boundaries / catastrophe set (structural mutations → different T^∞?)
 * Test 3: Approximate symmetries (near-identical → brittle or robust?)
 * Test 4: Idempotence certificate (replayable convergence witness)
 * 
 * Run: npx tsx lib/crystal-ball/demo-attractor-tests.ts
 */

import {
    createRegistry,
    createKernel,
    lockKernel,
    addNode,
    addAttribute,
    addDot,
    type Registry,
    type KernelSpace,
} from './index';
import {
    foundationSignature,
    detectSymmetryBreaking,
    isStructurallyStable,
    type FoundationSignature,
} from './kernel-function';
import { buildFutamuraTower, type ReifyResult } from './reify';

// ─── Helper: build a pipeline compiler variant ──────────────────

function buildCompilerVariant(
    registry: Registry,
    label: string,
    options: {
        slotNames?: string[];      // Override slot names
        attrNoise?: boolean;       // Add random extra attributes
        missingSlot?: number;      // Remove one slot (index)
        extraSlot?: string;        // Add an extra slot
        noDots?: boolean;          // Omit pipeline dots
        reverseDots?: boolean;     // Reverse pipeline direction
        branchAt?: number;         // Add a branch at slot index
    } = {},
): KernelSpace {
    const defaultNames = ['Grammar', 'Parser', 'Scry', 'Encoder', 'Locker', 'Miner'];
    let slotNames = options.slotNames ?? [...defaultNames];

    // Remove a slot if requested
    if (options.missingSlot !== undefined) {
        slotNames.splice(options.missingSlot, 1);
    }

    // Add extra slot if requested  
    if (options.extraSlot) {
        slotNames.push(options.extraSlot);
    }

    // Create sub-kernels
    const subKernels: KernelSpace[] = [];
    for (const name of slotNames) {
        const k = createKernel(registry, `${label}_${name}`);
        for (const nodeName of ['Input', 'Process', 'Output']) {
            const n = addNode(k.space, 'root', nodeName);
            addAttribute(k.space, n.id, 'type', [nodeName.toLowerCase()], nodeName.toLowerCase());
        }
        // Add noise attributes if requested
        if (options.attrNoise) {
            const noiseNode = k.space.nodes.get('root')!;
            addAttribute(k.space, 'root', 'noise',
                [Math.random().toFixed(4), Math.random().toFixed(4)],
                Math.random().toFixed(4));
        }
        lockKernel(registry, k.globalId);
        subKernels.push(k);
    }

    // Compose compiler
    const compiler = createKernel(registry, label);
    const slotIds: string[] = [];
    for (let i = 0; i < slotNames.length; i++) {
        const slot = addNode(compiler.space, 'root', slotNames[i]);
        slot.kernelRef = subKernels[i].globalId;
        slotIds.push(slot.id);
    }

    // Add dots (pipeline structure)
    if (!options.noDots) {
        if (options.reverseDots) {
            for (let i = slotIds.length - 1; i > 0; i--) {
                addDot(compiler.space, slotIds[i], slotIds[i - 1], 'reverse');
            }
        } else {
            for (let i = 0; i < slotIds.length - 1; i++) {
                addDot(compiler.space, slotIds[i], slotIds[i + 1], 'pipeline');
            }
        }
    }

    // Add branch if requested
    if (options.branchAt !== undefined && options.branchAt < slotIds.length) {
        const branchK = createKernel(registry, `${label}_Branch`);
        addNode(branchK.space, 'root', 'BranchNode');
        lockKernel(registry, branchK.globalId);
        const branchSlot = addNode(compiler.space, 'root', 'Branch');
        branchSlot.kernelRef = branchK.globalId;
        addDot(compiler.space, slotIds[options.branchAt], branchSlot.id, 'branch');
        slotIds.push(branchSlot.id);
    }

    lockKernel(registry, compiler.globalId);
    return compiler;
}

// ═══════════════════════════════════════════════════════════════
//  TEST 1: PERTURBATION STABILITY
// ═══════════════════════════════════════════════════════════════

console.log('═══════════════════════════════════════════════════');
console.log('  TEST 1: PERTURBATION STABILITY');
console.log('  Do noisy variants converge to the same T^∞?');
console.log('═══════════════════════════════════════════════════\n');

const reg1 = createRegistry();

// Baseline
const baseline = buildCompilerVariant(reg1, 'Baseline');
const baselineTower = buildFutamuraTower(reg1, baseline.globalId, 4);

// Variant A: renamed slots
const variantA = buildCompilerVariant(reg1, 'Renamed', {
    slotNames: ['Lexer', 'Tokenizer', 'Resolver', 'Mapper', 'Freezer', 'Extractor'],
});
const towerA = buildFutamuraTower(reg1, variantA.globalId, 4);

// Variant B: noisy attributes
const variantB = buildCompilerVariant(reg1, 'Noisy', { attrNoise: true });
const towerB = buildFutamuraTower(reg1, variantB.globalId, 4);

// Variant C: reversed pipeline
const variantC = buildCompilerVariant(reg1, 'Reversed', { reverseDots: true });
const towerC = buildFutamuraTower(reg1, variantC.globalId, 4);

const variants = [
    { name: 'Baseline', tower: baselineTower },
    { name: 'Renamed', tower: towerA },
    { name: 'Noisy', tower: towerB },
    { name: 'Reversed', tower: towerC },
];

// Compare all T^∞ signatures
const tInfSignatures: { name: string; sig: FoundationSignature }[] = [];
for (const v of variants) {
    const lastLevel = v.tower[v.tower.length - 1];
    if (lastLevel) {
        tInfSignatures.push({ name: v.name, sig: lastLevel.signature });
        const stabilized = v.tower.length >= 2
            ? isStructurallyStable(
                v.tower[v.tower.length - 2].signature,
                lastLevel.signature
            ).stable ? 'YES' : 'NO'
            : '?';
        console.log(`  ${v.name.padEnd(12)} converged: ${stabilized}  levels: ${v.tower.length}  signature: ${lastLevel.signature.canonical.substring(0, 50)}...`);
    }
}

console.log('\n  Cross-comparison of T^∞ signatures:\n');
for (let i = 0; i < tInfSignatures.length; i++) {
    for (let j = i + 1; j < tInfSignatures.length; j++) {
        const diff = detectSymmetryBreaking(tInfSignatures[i].sig, tInfSignatures[j].sig);
        const stable = isStructurallyStable(tInfSignatures[i].sig, tInfSignatures[j].sig, 0.01);
        console.log(`  ${tInfSignatures[i].name} ↔ ${tInfSignatures[j].name}: ${diff.relationship} (maxΔw=${stable.maxWeightDiff.toFixed(4)})`);
    }
}

// ═══════════════════════════════════════════════════════════════
//  TEST 2: BASIN BOUNDARIES / CATASTROPHE SET
// ═══════════════════════════════════════════════════════════════

console.log('\n═══════════════════════════════════════════════════');
console.log('  TEST 2: BASIN BOUNDARIES / CATASTROPHE SET');
console.log('  Structural mutations → same/different/no convergence?');
console.log('═══════════════════════════════════════════════════\n');

const reg2 = createRegistry();

const mutations: { name: string; opts: Parameters<typeof buildCompilerVariant>[2] }[] = [
    { name: 'Baseline', opts: {} },
    { name: 'No_Dots', opts: { noDots: true } },
    { name: 'Missing_1', opts: { missingSlot: 0 } },           // remove Grammar
    { name: 'Missing_3', opts: { missingSlot: 3 } },           // remove Encoder (middle)
    { name: 'Missing_Last', opts: { missingSlot: 5 } },           // remove Miner
    { name: 'Extra_Slot', opts: { extraSlot: 'Optimizer' } },   // 7 slots
    { name: 'Branch_At_2', opts: { branchAt: 2 } },              // branch after Scry
    { name: 'Rev+Branch', opts: { reverseDots: true, branchAt: 1 } },
];

const catastropheResults: {
    name: string;
    converged: boolean;
    levels: number;
    sig?: FoundationSignature;
}[] = [];

for (const m of mutations) {
    const k = buildCompilerVariant(reg2, m.name, m.opts);
    const tower = buildFutamuraTower(reg2, k.globalId, 4);
    const last = tower[tower.length - 1];
    const converged = tower.length >= 2 &&
        isStructurallyStable(tower[tower.length - 2].signature, last.signature).stable;
    catastropheResults.push({
        name: m.name,
        converged,
        levels: tower.length,
        sig: last?.signature,
    });
    console.log(`  ${m.name.padEnd(14)} converged: ${converged ? '✅' : '❌'}  levels: ${tower.length}  partition: [${last?.signature.orbitPartition.join(',')}]  dots: ${last?.kernel.space.dots.length ?? 0}`);
}

// Classify into basins
console.log('\n  Basin analysis:\n');
const basins = new Map<string, string[]>();
for (const r of catastropheResults) {
    if (r.converged && r.sig) {
        const key = `[${r.sig.orbitPartition.join(',')}]|${r.sig.localGroups.map(g => g.groupName).join('×')}`;
        if (!basins.has(key)) basins.set(key, []);
        basins.get(key)!.push(r.name);
    }
}
let basinIdx = 0;
for (const [key, members] of basins) {
    console.log(`  Basin ${basinIdx++}: ${key}`);
    console.log(`    Members: ${members.join(', ')}`);
}
const nonConverged = catastropheResults.filter(r => !r.converged);
if (nonConverged.length > 0) {
    console.log(`\n  Non-converged (catastrophe set):`);
    for (const r of nonConverged) {
        console.log(`    ${r.name} — did not stabilize in ${r.levels} levels`);
    }
}

// ═══════════════════════════════════════════════════════════════
//  TEST 3: APPROXIMATE SYMMETRIES
// ═══════════════════════════════════════════════════════════════

console.log('\n═══════════════════════════════════════════════════');
console.log('  TEST 3: APPROXIMATE SYMMETRIES');
console.log('  Is the fixed point brittle-combinatorial or robust-geometric?');
console.log('═══════════════════════════════════════════════════\n');

// Test at various epsilon thresholds
const reg3 = createRegistry();
const exact = buildCompilerVariant(reg3, 'Exact');
const noisy1 = buildCompilerVariant(reg3, 'Noise1', { attrNoise: true });
const noisy2 = buildCompilerVariant(reg3, 'Noise2', { attrNoise: true });

const towerExact = buildFutamuraTower(reg3, exact.globalId, 4);
const towerN1 = buildFutamuraTower(reg3, noisy1.globalId, 4);
const towerN2 = buildFutamuraTower(reg3, noisy2.globalId, 4);

const sigExact = towerExact[towerExact.length - 1]?.signature;
const sigN1 = towerN1[towerN1.length - 1]?.signature;
const sigN2 = towerN2[towerN2.length - 1]?.signature;

if (sigExact && sigN1 && sigN2) {
    const epsilons = [1e-10, 1e-6, 1e-3, 0.01, 0.1, 1.0, 10.0];
    console.log('  ε-stability between Exact and Noisy variants:\n');
    console.log(`  ${'ε'.padEnd(10)} Exact↔N1    Exact↔N2    N1↔N2`);
    console.log('  ' + '─'.repeat(50));
    for (const eps of epsilons) {
        const s1 = isStructurallyStable(sigExact, sigN1, eps);
        const s2 = isStructurallyStable(sigExact, sigN2, eps);
        const s3 = isStructurallyStable(sigN1, sigN2, eps);
        console.log(`  ${eps.toExponential(0).padEnd(10)} ${(s1.stable ? '✅' : '❌').padEnd(12)} ${(s2.stable ? '✅' : '❌').padEnd(12)} ${s3.stable ? '✅' : '❌'}`);
    }

    const maxDiff12 = isStructurallyStable(sigExact, sigN1);
    const maxDiff13 = isStructurallyStable(sigExact, sigN2);
    const maxDiff23 = isStructurallyStable(sigN1, sigN2);
    console.log(`\n  Max weight diffs: Exact↔N1=${maxDiff12.maxWeightDiff.toFixed(6)}, Exact↔N2=${maxDiff13.maxWeightDiff.toFixed(6)}, N1↔N2=${maxDiff23.maxWeightDiff.toFixed(6)}`);

    const robustness = maxDiff12.maxWeightDiff < 0.01 && maxDiff13.maxWeightDiff < 0.01
        ? '🟢 ROBUST GEOMETRIC-SEMANTIC (noise doesn\'t affect structure)'
        : maxDiff12.maxWeightDiff < 1.0
            ? '🟡 MODERATELY ROBUST (small weight perturbation from noise)'
            : '🔴 BRITTLE COMBINATORIAL (noise significantly shifts weights)';
    console.log(`\n  Verdict: ${robustness}`);
}

// ═══════════════════════════════════════════════════════════════
//  TEST 4: IDEMPOTENCE CERTIFICATE
// ═══════════════════════════════════════════════════════════════

console.log('\n═══════════════════════════════════════════════════');
console.log('  TEST 4: IDEMPOTENCE CERTIFICATE');
console.log('  Replayable convergence witness');
console.log('═══════════════════════════════════════════════════\n');

interface ConvergenceRecord {
    level: number;
    orbitPartition: number[];
    quotientEdges: number;
    symmetryGroup: string;
    eigenTop3: number[];
    canonical: string;
    stableVsPrevious: boolean;
    maxWeightDiffVsPrevious: number;
}

const reg4 = createRegistry();
const certCompiler = buildCompilerVariant(reg4, 'Certificate');
const certTower = buildFutamuraTower(reg4, certCompiler.globalId, 5);

const certificate: ConvergenceRecord[] = [];
let stableAt: number | null = null;

for (let i = 0; i < certTower.length; i++) {
    const t = certTower[i];
    let stableVsPrev = false;
    let maxDiffVsPrev = Infinity;

    if (i > 0) {
        const stability = isStructurallyStable(certTower[i - 1].signature, t.signature);
        stableVsPrev = stability.stable;
        maxDiffVsPrev = stability.maxWeightDiff;
        if (stableVsPrev && stableAt === null) {
            stableAt = i;
        }
    }

    certificate.push({
        level: i,
        orbitPartition: t.signature.orbitPartition,
        quotientEdges: t.signature.quotientGraph.length,
        symmetryGroup: t.analysis.symmetryGroup,
        eigenTop3: t.analysis.eigenspectrum.slice(0, 3),
        canonical: t.signature.canonical,
        stableVsPrevious: stableVsPrev,
        maxWeightDiffVsPrevious: maxDiffVsPrev,
    });
}

console.log('  CONVERGENCE CERTIFICATE\n');
for (const rec of certificate) {
    const marker = rec.stableVsPrevious ? ' ← STABLE' : '';
    console.log(`  T^${rec.level}:`);
    console.log(`    partition:  [${rec.orbitPartition.join(',')}]`);
    console.log(`    quotient:   ${rec.quotientEdges} edges`);
    console.log(`    symmetry:   ${rec.symmetryGroup}`);
    console.log(`    eigenTop3:  [${rec.eigenTop3.map(e => e.toFixed(3)).join(', ')}]`);
    console.log(`    vs prev:    ${rec.level === 0 ? 'n/a' : rec.stableVsPrevious ? `✅ stable (Δw=${rec.maxWeightDiffVsPrevious.toExponential(2)})` : `❌ different (Δw=${rec.maxWeightDiffVsPrevious.toFixed(4)})`}${marker}`);
    console.log();
}

console.log('  ─────────────────────────────────');
if (stableAt !== null) {
    console.log(`  ✅ IDEMPOTENCE VERIFIED`);
    console.log(`     stable_at = ${stableAt}`);
    console.log(`     T^${stableAt} = T^${stableAt + 1} = ... = T^∞`);
    console.log(`     Fixed point: [${certificate[stableAt].orbitPartition.join(',')}]|${certificate[stableAt].symmetryGroup}`);
} else {
    console.log(`  ❌ NOT YET STABLE after ${certTower.length} levels`);
}
