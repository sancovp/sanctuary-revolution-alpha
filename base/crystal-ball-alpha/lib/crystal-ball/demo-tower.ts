/**
 * demo-tower.ts — Build the Futamura Tower
 * 
 * Create the compiler kernel, then apply T repeatedly to build
 * the tower of reified mineSpaces. Watch the symmetry groups
 * at each level.
 * 
 * Run: npx tsx lib/crystal-ball/demo-tower.ts
 */

import {
    createRegistry,
    createKernel,
    lockKernel,
    addNode,
    addDot,
    kernelPosition,
} from './index';
import { buildFutamuraTower, type ReifyResult } from './reify';
import { type SpaceSlotSignature } from './kernel-v2';

const registry = createRegistry();

// ── Build the compiler kernel ────────────────────────────────

// Component kernels — children ARE the spectrum (no addAttribute)
const grammarK = createKernel(registry, 'Grammar');
for (const name of ['Zero', 'Sel_1to7', 'Drill_8', 'Close_88', 'Wrap_9',
    'Dot_8988', 'KOpen_90', 'KClose_900', 'AlsoOpen', 'AlsoClose']) {
    addNode(grammarK.space, 'root', name);
}
lockKernel(registry, grammarK.globalId);

const parserK = createKernel(registry, 'Parser');
for (const name of ['Input', 'Segments', 'ParsedCoord']) {
    addNode(parserK.space, 'root', name);
}
lockKernel(registry, parserK.globalId);

const scryK = createKernel(registry, 'Scry');
for (const name of ['CoordInput', 'Resolution', 'ResolvedNodes']) {
    addNode(scryK.space, 'root', name);
}
lockKernel(registry, scryK.globalId);

const encoderK = createKernel(registry, 'Encoder');
for (const name of ['CoordString', 'DotEncoding', 'RealNumber']) {
    addNode(encoderK.space, 'root', name);
}
lockKernel(registry, encoderK.globalId);

const lockerK = createKernel(registry, 'Locker');
for (const name of ['KernelToLock', 'Verification', 'LockResult']) {
    addNode(lockerK.space, 'root', name);
}
lockKernel(registry, lockerK.globalId);

const minerK = createKernel(registry, 'Miner');
for (const name of ['LockedKernel', 'Projection', 'MinePoints']) {
    addNode(minerK.space, 'root', name);
}
lockKernel(registry, minerK.globalId);

// Compose the compiler
const compilerK = createKernel(registry, 'CB_Compiler');
const slots = [grammarK, parserK, scryK, encoderK, lockerK, minerK];
const slotNames = ['Grammar', 'Parser', 'Scry', 'Encoder', 'Locker', 'Miner'];
const slotNodes: string[] = [];
for (let i = 0; i < slots.length; i++) {
    const slot = addNode(compilerK.space, 'root', slotNames[i]);
    slot.kernelRef = slots[i].globalId;
    slotNodes.push(slot.id);
}
// Pipeline dots
for (let i = 0; i < slotNodes.length - 1; i++) {
    addDot(compilerK.space, slotNodes[i], slotNodes[i + 1], 'pipeline');
}
lockKernel(registry, compilerK.globalId);

// ── Build the Futamura Tower ────────────────────────────────

console.log('═══════════════════════════════════════════════════');
console.log('       THE FUTAMURA PROJECTION TOWER');
console.log('═══════════════════════════════════════════════════\n');

console.log(`Source: CB_Compiler kernel #${compilerK.globalId}\n`);

const tower = buildFutamuraTower(registry, compilerK.globalId, 4);

for (const level of tower) {
    const k = level.kernel;
    const sig = level.slotSignature;
    console.log(`── Level ${level.level}: T${'⁰¹²³⁴⁵⁶⁷⁸⁹'[level.level] ?? level.level}(Compiler) = Kernel #${k.globalId} ──`);
    console.log(`   Name: ${k.space.name}`);
    console.log(`   Locked: ${k.locked ? '🔒' : '🔓'}`);
    console.log(`   Position: ${kernelPosition(k.globalId).toFixed(8)}`);
    console.log(`   Symmetry: ${sig.totalSymmetry}`);
    console.log(`   Slots: ${sig.slots.length}`);
    console.log(`   Total configs: ${sig.totalConfigurations}`);
    for (const slot of sig.slots) {
        const orbitSizes = slot.orbits.map(o => o.size);
        console.log(`     Slot ${slot.slotIndex} (${slot.parentLabel}): ${slot.symmetryGroup} — orbits [${orbitSizes.join(',')}]`);
    }
    console.log(`   Canonical: ${sig.canonical.substring(0, 80)}${sig.canonical.length > 80 ? '...' : ''}`);
    console.log(`   Dots: ${k.space.dots.length}`);
    console.log();
}

// ── Compare levels ──────────────────────────────────────────

console.log('═══ CROSS-LEVEL SYMMETRY COMPARISON ═══\n');

for (let i = 0; i < tower.length - 1; i++) {
    const sigA = tower[i].slotSignature;
    const sigB = tower[i + 1].slotSignature;
    const same = sigA.canonical === sigB.canonical;
    const sameSymmetry = sigA.totalSymmetry === sigB.totalSymmetry;
    console.log(`Level ${i} → Level ${i + 1}: ${same ? 'IDENTICAL' : sameSymmetry ? 'same symmetry, different canonical' : 'DIFFERENT'}`);
    console.log(`  ${sigA.totalSymmetry} → ${sigB.totalSymmetry}`);
}

// ── Fixed point detection ───────────────────────────────────

if (tower.length >= 2) {
    const last = tower[tower.length - 1];
    const prev = tower[tower.length - 2];
    const identical = prev.slotSignature.canonical === last.slotSignature.canonical;

    console.log('\n═══ FIXED POINT? ═══\n');
    if (identical) {
        console.log('✅ FIXED POINT REACHED');
        console.log(`   The tower stabilized at level ${tower.length - 2}.`);
        console.log(`   T^∞ = ${last.slotSignature.canonical.substring(0, 60)}...`);
    } else {
        const sameShape = prev.slotSignature.totalSymmetry === last.slotSignature.totalSymmetry;
        if (sameShape) {
            console.log('≈ NEAR FIXED POINT (same symmetry group, different canonical)');
            console.log(`   One more level might converge.`);
        } else {
            console.log(`Still evolving: ${prev.slotSignature.totalSymmetry} → ${last.slotSignature.totalSymmetry}`);
            console.log(`   More levels needed for convergence.`);
        }
    }
}
