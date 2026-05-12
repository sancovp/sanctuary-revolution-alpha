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
    addDot,
    type Registry,
    type KernelSpace,
} from './index';
import {
    computeSpaceSlotSignature,
    type SpaceSlotSignature,
} from './kernel-v2';
import { buildFutamuraTower, type ReifyResult } from './reify';

// ─── Helper: compare two slot signatures ────────────────────────

function compareSignatures(a: SpaceSlotSignature, b: SpaceSlotSignature): {
    identical: boolean;
    sameSymmetry: boolean;
    relationship: string;
} {
    const identical = a.canonical === b.canonical;
    const sameSymmetry = a.totalSymmetry === b.totalSymmetry;
    return {
        identical,
        sameSymmetry,
        relationship: identical ? 'identical'
            : sameSymmetry ? 'same symmetry, different canonical'
                : 'DIFFERENT',
    };
}

// ─── Helper: check structural stability ─────────────────────────

function isStructurallyStable(a: SpaceSlotSignature, b: SpaceSlotSignature): {
    stable: boolean;
    sameSlotCount: boolean;
    sameOrbits: boolean;
} {
    const sameSlotCount = a.slots.length === b.slots.length;
    const sameOrbits = sameSlotCount && a.slots.every((slotA, i) => {
        const slotB = b.slots[i];
        return slotA.orbits.length === slotB.orbits.length
            && slotA.orbits.every((oA, j) => oA.size === slotB.orbits[j].size);
    });
    return {
        stable: a.canonical === b.canonical,
        sameSlotCount,
        sameOrbits,
    };
}

// ─── Helper: get orbit partition from signature ─────────────────

function orbitPartition(sig: SpaceSlotSignature): number[] {
    return sig.slots.flatMap(s => s.orbits.map(o => o.size)).sort((a, b) => b - a);
}

// ─── Helper: build a pipeline compiler variant ──────────────────

function buildCompilerVariant(
    registry: Registry,
    label: string,
    options: {
        slotNames?: string[];
        extraChildren?: boolean;    // Add extra child nodes (noise)
        missingSlot?: number;
        extraSlot?: string;
        noDots?: boolean;
        reverseDots?: boolean;
        branchAt?: number;
    } = {},
): KernelSpace {
    const defaultNames = ['Grammar', 'Parser', 'Scry', 'Encoder', 'Locker', 'Miner'];
    let slotNames = options.slotNames ?? [...defaultNames];

    if (options.missingSlot !== undefined) {
        slotNames.splice(options.missingSlot, 1);
    }
    if (options.extraSlot) {
        slotNames.push(options.extraSlot);
    }

    // Create sub-kernels — children ARE the spectrum
    const subKernels: KernelSpace[] = [];
    for (const name of slotNames) {
        const k = createKernel(registry, `${label}_${name}`);
        for (const nodeName of ['Input', 'Process', 'Output']) {
            addNode(k.space, 'root', nodeName);
        }
        // Add noise children if requested (structural perturbation)
        if (options.extraChildren) {
            addNode(k.space, 'root', `Noise_${Math.random().toFixed(4)}`);
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

const baseline = buildCompilerVariant(reg1, 'Baseline');
const baselineTower = buildFutamuraTower(reg1, baseline.globalId, 4);

const variantA = buildCompilerVariant(reg1, 'Renamed', {
    slotNames: ['Lexer', 'Tokenizer', 'Resolver', 'Mapper', 'Freezer', 'Extractor'],
});
const towerA = buildFutamuraTower(reg1, variantA.globalId, 4);

const variantB = buildCompilerVariant(reg1, 'Noisy', { extraChildren: true });
const towerB = buildFutamuraTower(reg1, variantB.globalId, 4);

const variantC = buildCompilerVariant(reg1, 'Reversed', { reverseDots: true });
const towerC = buildFutamuraTower(reg1, variantC.globalId, 4);

const variants = [
    { name: 'Baseline', tower: baselineTower },
    { name: 'Renamed', tower: towerA },
    { name: 'Noisy', tower: towerB },
    { name: 'Reversed', tower: towerC },
];

const tInfSignatures: { name: string; sig: SpaceSlotSignature }[] = [];
for (const v of variants) {
    const lastLevel = v.tower[v.tower.length - 1];
    if (lastLevel) {
        tInfSignatures.push({ name: v.name, sig: lastLevel.slotSignature });
        const stabilized = v.tower.length >= 2
            ? isStructurallyStable(
                v.tower[v.tower.length - 2].slotSignature,
                lastLevel.slotSignature
            ).stable ? 'YES' : 'NO'
            : '?';
        console.log(`  ${v.name.padEnd(12)} converged: ${stabilized}  levels: ${v.tower.length}  signature: ${lastLevel.slotSignature.canonical.substring(0, 50)}...`);
    }
}

console.log('\n  Cross-comparison of T^∞ signatures:\n');
for (let i = 0; i < tInfSignatures.length; i++) {
    for (let j = i + 1; j < tInfSignatures.length; j++) {
        const diff = compareSignatures(tInfSignatures[i].sig, tInfSignatures[j].sig);
        console.log(`  ${tInfSignatures[i].name} ↔ ${tInfSignatures[j].name}: ${diff.relationship}`);
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
    { name: 'Missing_1', opts: { missingSlot: 0 } },
    { name: 'Missing_3', opts: { missingSlot: 3 } },
    { name: 'Missing_Last', opts: { missingSlot: 5 } },
    { name: 'Extra_Slot', opts: { extraSlot: 'Optimizer' } },
    { name: 'Branch_At_2', opts: { branchAt: 2 } },
    { name: 'Rev+Branch', opts: { reverseDots: true, branchAt: 1 } },
];

const catastropheResults: {
    name: string;
    converged: boolean;
    levels: number;
    sig?: SpaceSlotSignature;
}[] = [];

for (const m of mutations) {
    const k = buildCompilerVariant(reg2, m.name, m.opts);
    const tower = buildFutamuraTower(reg2, k.globalId, 4);
    const last = tower[tower.length - 1];
    const converged = tower.length >= 2 &&
        isStructurallyStable(tower[tower.length - 2].slotSignature, last.slotSignature).stable;
    catastropheResults.push({
        name: m.name,
        converged,
        levels: tower.length,
        sig: last?.slotSignature,
    });
    const partition = last ? orbitPartition(last.slotSignature) : [];
    console.log(`  ${m.name.padEnd(14)} converged: ${converged ? '✅' : '❌'}  levels: ${tower.length}  partition: [${partition.join(',')}]  dots: ${last?.kernel.space.dots.length ?? 0}`);
}

// Classify into basins
console.log('\n  Basin analysis:\n');
const basins = new Map<string, string[]>();
for (const r of catastropheResults) {
    if (r.converged && r.sig) {
        const partition = orbitPartition(r.sig);
        const key = `[${partition.join(',')}]|${r.sig.totalSymmetry}`;
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

const reg3 = createRegistry();
const exact = buildCompilerVariant(reg3, 'Exact');
const noisy1 = buildCompilerVariant(reg3, 'Noise1', { extraChildren: true });
const noisy2 = buildCompilerVariant(reg3, 'Noise2', { extraChildren: true });

const towerExact = buildFutamuraTower(reg3, exact.globalId, 4);
const towerN1 = buildFutamuraTower(reg3, noisy1.globalId, 4);
const towerN2 = buildFutamuraTower(reg3, noisy2.globalId, 4);

const sigExact = towerExact[towerExact.length - 1]?.slotSignature;
const sigN1 = towerN1[towerN1.length - 1]?.slotSignature;
const sigN2 = towerN2[towerN2.length - 1]?.slotSignature;

if (sigExact && sigN1 && sigN2) {
    console.log('  Structural comparison:\n');
    const c1 = compareSignatures(sigExact, sigN1);
    const c2 = compareSignatures(sigExact, sigN2);
    const c3 = compareSignatures(sigN1, sigN2);
    console.log(`  Exact ↔ N1: ${c1.relationship}`);
    console.log(`  Exact ↔ N2: ${c2.relationship}`);
    console.log(`  N1 ↔ N2:    ${c3.relationship}`);

    const s1 = isStructurallyStable(sigExact, sigN1);
    const s2 = isStructurallyStable(sigExact, sigN2);

    const robustness = s1.sameOrbits && s2.sameOrbits
        ? '🟢 ROBUST GEOMETRIC-SEMANTIC (noise doesn\'t affect orbit structure)'
        : s1.sameSlotCount && s2.sameSlotCount
            ? '🟡 MODERATELY ROBUST (same slot count, different orbit decom)'
            : '🔴 BRITTLE COMBINATORIAL (noise changes slot structure)';
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
    symmetry: string;
    canonical: string;
    stableVsPrevious: boolean;
}

const reg4 = createRegistry();
const certCompiler = buildCompilerVariant(reg4, 'Certificate');
const certTower = buildFutamuraTower(reg4, certCompiler.globalId, 5);

const certificate: ConvergenceRecord[] = [];
let stableAt: number | null = null;

for (let i = 0; i < certTower.length; i++) {
    const t = certTower[i];
    let stableVsPrev = false;

    if (i > 0) {
        const stability = isStructurallyStable(certTower[i - 1].slotSignature, t.slotSignature);
        stableVsPrev = stability.stable;
        if (stableVsPrev && stableAt === null) {
            stableAt = i;
        }
    }

    certificate.push({
        level: i,
        orbitPartition: orbitPartition(t.slotSignature),
        symmetry: t.slotSignature.totalSymmetry,
        canonical: t.slotSignature.canonical,
        stableVsPrevious: stableVsPrev,
    });
}

console.log('  CONVERGENCE CERTIFICATE\n');
for (const rec of certificate) {
    const marker = rec.stableVsPrevious ? ' ← STABLE' : '';
    console.log(`  T^${rec.level}:`);
    console.log(`    partition:  [${rec.orbitPartition.join(',')}]`);
    console.log(`    symmetry:   ${rec.symmetry}`);
    console.log(`    vs prev:    ${rec.level === 0 ? 'n/a' : rec.stableVsPrevious ? '✅ stable' : '❌ different'}${marker}`);
    console.log();
}

console.log('  ─────────────────────────────────');
if (stableAt !== null) {
    console.log(`  ✅ IDEMPOTENCE VERIFIED`);
    console.log(`     stable_at = ${stableAt}`);
    console.log(`     T^${stableAt} = T^${stableAt + 1} = ... = T^∞`);
    console.log(`     Fixed point: [${certificate[stableAt].orbitPartition.join(',')}]|${certificate[stableAt].symmetry}`);
} else {
    console.log(`  ❌ NOT YET STABLE after ${certTower.length} levels`);
}
