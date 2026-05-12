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
    addAttribute,
    addDot,
    kernelPosition,
    coordToReal,
    fullCoordinate,
} from './index';
import { foundationSignature, analyzeSpace, detectSymmetryBreaking } from './kernel-function';
import { buildFutamuraTower, reifyMineSpace } from './reify';

const registry = createRegistry();

// ── Build the compiler kernel (same as demo-futamura) ────────

// Component kernels
const grammarK = createKernel(registry, 'Grammar');
const tokNode = addNode(grammarK.space, 'root', 'Tokens');
addAttribute(grammarK.space, tokNode.id, 'cardinality', ['10'], '10');
for (const name of ['Zero', 'Sel_1to7', 'Drill_8', 'Close_88', 'Wrap_9',
    'Dot_8988', 'KOpen_90', 'KClose_900', 'AlsoOpen', 'AlsoClose']) {
    const n = addNode(grammarK.space, tokNode.id, name);
    addAttribute(grammarK.space, n.id, 'role', [name.toLowerCase()], name.toLowerCase());
}
lockKernel(registry, grammarK.globalId);

const parserK = createKernel(registry, 'Parser');
for (const name of ['Input', 'Segments', 'ParsedCoord']) {
    const n = addNode(parserK.space, 'root', name);
    addAttribute(parserK.space, n.id, 'type', [name.toLowerCase()], name.toLowerCase());
}
lockKernel(registry, parserK.globalId);

const scryK = createKernel(registry, 'Scry');
for (const name of ['CoordInput', 'Resolution', 'ResolvedNodes']) {
    const n = addNode(scryK.space, 'root', name);
    addAttribute(scryK.space, n.id, 'type', [name.toLowerCase()], name.toLowerCase());
}
lockKernel(registry, scryK.globalId);

const encoderK = createKernel(registry, 'Encoder');
for (const name of ['CoordString', 'DotEncoding', 'RealNumber']) {
    const n = addNode(encoderK.space, 'root', name);
    addAttribute(encoderK.space, n.id, 'type', [name.toLowerCase()], name.toLowerCase());
}
lockKernel(registry, encoderK.globalId);

const lockerK = createKernel(registry, 'Locker');
for (const name of ['KernelToLock', 'Verification', 'LockResult']) {
    const n = addNode(lockerK.space, 'root', name);
    addAttribute(lockerK.space, n.id, 'type', [name.toLowerCase()], name.toLowerCase());
}
lockKernel(registry, lockerK.globalId);

const minerK = createKernel(registry, 'Miner');
for (const name of ['LockedKernel', 'Projection', 'MinePoints']) {
    const n = addNode(minerK.space, 'root', name);
    addAttribute(minerK.space, n.id, 'type', [name.toLowerCase()], name.toLowerCase());
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
    console.log(`── Level ${level.level}: T${'⁰¹²³⁴⁵⁶⁷⁸⁹'[level.level] ?? level.level}(Compiler) = Kernel #${k.globalId} ──`);
    console.log(`   Name: ${k.space.name}`);
    console.log(`   Locked: ${k.locked ? '🔒' : '🔓'}`);
    console.log(`   Position: ${kernelPosition(k.globalId).toFixed(8)}`);
    console.log(`   Symmetry: ${level.analysis.symmetryGroup}`);
    console.log(`   Effective dim: ${level.analysis.effectiveDimension}`);
    console.log(`   Eigenspectrum: [${level.analysis.eigenspectrum.slice(0, 5).map(e => e.toFixed(3)).join(', ')}${level.analysis.eigenspectrum.length > 5 ? '...' : ''}]`);
    console.log(`   Orbits: ${level.analysis.orbits.length}`);
    for (const orbit of level.analysis.orbits) {
        const g = level.signature.localGroups[level.analysis.orbits.indexOf(orbit)];
        console.log(`     [${orbit.members.join(',')}] ${g?.groupName ?? '?'} (size ${orbit.size})`);
    }
    console.log(`   Foundation: ${level.signature.canonical.substring(0, 80)}${level.signature.canonical.length > 80 ? '...' : ''}`);
    console.log(`   Dots: ${k.space.dots.length}`);
    console.log();
}

// ── Compare levels ──────────────────────────────────────────

console.log('═══ CROSS-LEVEL SYMMETRY COMPARISON ═══\n');

for (let i = 0; i < tower.length - 1; i++) {
    const diff = detectSymmetryBreaking(tower[i].signature, tower[i + 1].signature);
    console.log(`Level ${i} → Level ${i + 1}: ${diff.relationship}`);
    console.log(`  ${diff.description}`);
}

// ── Fixed point detection ───────────────────────────────────

if (tower.length >= 2) {
    const last = tower[tower.length - 1];
    const prev = tower[tower.length - 2];
    const final = detectSymmetryBreaking(prev.signature, last.signature);

    console.log('\n═══ FIXED POINT? ═══\n');
    if (final.relationship === 'identical') {
        console.log('✅ FIXED POINT REACHED');
        console.log(`   The tower stabilized at level ${tower.length - 2}.`);
        console.log(`   T^∞ = ${last.signature.canonical.substring(0, 60)}...`);
    } else if (final.relationship === 'renamed') {
        console.log('≈ NEAR FIXED POINT (same structure, different weights)');
        console.log(`   One more level might converge.`);
    } else {
        console.log(`Still evolving: ${final.relationship}`);
        console.log(`   More levels needed for convergence.`);
    }
}
