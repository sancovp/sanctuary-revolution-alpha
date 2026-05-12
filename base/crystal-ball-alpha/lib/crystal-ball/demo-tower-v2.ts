/**
 * demo-tower-v2.ts — Futamura Tower with correct RKHS
 * 
 * Uses kernel-v2 (per-slot orbits, children-as-spectrum, no attributes).
 * 
 * Run: npx tsx lib/crystal-ball/demo-tower-v2.ts
 */

import {
    createRegistry,
    createKernel,
    lockKernel,
    addNode,
    addDot,
    kernelPosition,
} from './index';
import { computeSpaceSlotSignature } from './kernel-v2';
import { buildFutamuraTower } from './reify';

const registry = createRegistry();

// ── Build compiler with SYMMETRIC sub-kernels ────────────────
// Give some sub-kernels IDENTICAL structure so orbits emerge

// Grammar: 3-slot kernel (Tokens, Rules, Output)
const grammarK = createKernel(registry, 'Grammar');
addNode(grammarK.space, 'root', 'Tokens');
addNode(grammarK.space, 'root', 'Rules');
addNode(grammarK.space, 'root', 'Output');
lockKernel(registry, grammarK.globalId);

// Parser: SAME 3-slot structure (identical to Grammar → should orbit together)
const parserK = createKernel(registry, 'Parser');
addNode(parserK.space, 'root', 'Input');
addNode(parserK.space, 'root', 'Transform');
addNode(parserK.space, 'root', 'Output');
lockKernel(registry, parserK.globalId);

// Scry: SAME 3-slot structure
const scryK = createKernel(registry, 'Scry');
addNode(scryK.space, 'root', 'Coordinate');
addNode(scryK.space, 'root', 'Resolution');
addNode(scryK.space, 'root', 'Result');
lockKernel(registry, scryK.globalId);

// Encoder: 2-slot kernel (DIFFERENT structure)
const encoderK = createKernel(registry, 'Encoder');
addNode(encoderK.space, 'root', 'Input');
addNode(encoderK.space, 'root', 'Encoded');
lockKernel(registry, encoderK.globalId);

// Locker: 2-slot (same as Encoder → should orbit with Encoder)
const lockerK = createKernel(registry, 'Locker');
addNode(lockerK.space, 'root', 'Target');
addNode(lockerK.space, 'root', 'Locked');
lockKernel(registry, lockerK.globalId);

// Miner: 4-slot (UNIQUE structure)
const minerK = createKernel(registry, 'Miner');
addNode(minerK.space, 'root', 'LockedKernel');
addNode(minerK.space, 'root', 'Projection');
addNode(minerK.space, 'root', 'Points');
addNode(minerK.space, 'root', 'Heatmap');
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

// ── Analyze the compiler BEFORE tower ────────────────────────

console.log('═══════════════════════════════════════════════════');
console.log('  COMPILER SLOT SIGNATURE (before tower)');
console.log('═══════════════════════════════════════════════════\n');

const compilerSig = computeSpaceSlotSignature(registry, compilerK.space.name);
console.log(`Canonical: ${compilerSig.canonical}`);
console.log(`Total configurations: ${compilerSig.totalConfigurations}`);
console.log(`Total symmetry: ${compilerSig.totalSymmetry}\n`);

for (const slot of compilerSig.slots) {
    const orbitStr = slot.orbits.map(o =>
        o.size > 1 ? `{${o.labels.join(',')} = S${o.size}}` : o.labels[0]
    ).join(' | ');
    console.log(`  Slot ${slot.slotIndex} [${slot.parentLabel}]: ${slot.symmetryGroup}`);
    console.log(`    ${orbitStr}`);
    console.log(`    0 = ${slot.superpositionMeaning}`);
}

// ── Build the Tower ──────────────────────────────────────────

console.log('\n═══════════════════════════════════════════════════');
console.log('  FUTAMURA PROJECTION TOWER (v2, correct RKHS)');
console.log('═══════════════════════════════════════════════════\n');

const tower = buildFutamuraTower(registry, compilerK.globalId, 4);

for (const level of tower) {
    const k = level.kernel;
    const sig = level.slotSignature;
    console.log(`── T${'⁰¹²³⁴⁵'[level.level] ?? level.level} = Kernel #${k.globalId} ──`);
    console.log(`   Name: ${k.space.name}`);
    console.log(`   Locked: ${k.locked ? '🔒' : '🔓'}`);
    console.log(`   Position: ${kernelPosition(k.globalId).toFixed(8)}`);
    console.log(`   Canonical: ${sig.canonical.substring(0, 80)}${sig.canonical.length > 80 ? '...' : ''}`);
    console.log(`   Symmetry: ${sig.totalSymmetry.substring(0, 60)}${sig.totalSymmetry.length > 60 ? '...' : ''}`);
    console.log(`   Total configs: ${sig.totalConfigurations}`);
    console.log(`   Slots: ${sig.slots.length}`);
    for (const slot of sig.slots) {
        const orbitStr = slot.orbits.map(o =>
            o.size > 1 ? `S${o.size}(${o.labels.join(',')})` : o.labels[0]
        ).join(' | ');
        console.log(`     [${slot.parentLabel}] ${slot.symmetryGroup} → ${orbitStr}`);
    }
    console.log(`   Dots: ${k.space.dots.length}`);
    console.log();
}

// ── Cross-level comparison ───────────────────────────────────

console.log('═══ CROSS-LEVEL COMPARISON ═══\n');
for (let i = 0; i < tower.length - 1; i++) {
    const sigA = tower[i].slotSignature.canonical;
    const sigB = tower[i + 1].slotSignature.canonical;
    const match = sigA === sigB;
    console.log(`T${i} → T${i + 1}: ${match ? '✅ IDENTICAL' : '❌ DIFFERENT'}`);
    if (!match) {
        console.log(`  A: ${sigA.substring(0, 70)}...`);
        console.log(`  B: ${sigB.substring(0, 70)}...`);
    }
}

if (tower.length >= 2) {
    const lastSig = tower[tower.length - 1].slotSignature.canonical;
    const prevSig = tower[tower.length - 2].slotSignature.canonical;
    console.log(`\n${lastSig === prevSig ? '✅ FIXED POINT REACHED' : '❌ Still evolving'}`);
}
