/**
 * demo-foundation.ts — Test Foundation Signature + Symmetry Breaking
 * 
 * Run: npx tsx lib/crystal-ball/demo-foundation.ts
 */

import { createSpace, addNode, type Registry } from './index';
import { analyzeSpace, foundationSignature, detectSymmetryBreaking } from './kernel-function';

// ── Build two spaces: one baseline, one with a broken symmetry ──

const registry: Registry = { spaces: new Map(), kernels: new Map(), nextKernelId: 1 };

// ── Space A: Baseline (S₃ × S₂ structure) ────────────────────
const spaceA = createSpace(registry, 'TweetA');
const toneA = addNode(spaceA, 'root', 'Tone');
const hookA = addNode(spaceA, 'root', 'Hook');
const bodyA = addNode(spaceA, 'root', 'Body');



addNode(spaceA, toneA.id, 'Friendly');
addNode(spaceA, toneA.id, 'Formal');
addNode(spaceA, toneA.id, 'Emotional');

addNode(spaceA, hookA.id, 'OpenQuestion');
addNode(spaceA, hookA.id, 'ShockingStat');

// ── Space B: Symmetry broken — one Tone variant has unique attr ─
const spaceB = createSpace(registry, 'TweetB');
const toneB = addNode(spaceB, 'root', 'Tone');
const hookB = addNode(spaceB, 'root', 'Hook');
const bodyB = addNode(spaceB, 'root', 'Body');



const friendly = addNode(spaceB, toneB.id, 'Friendly');
addNode(spaceB, toneB.id, 'Formal');
addNode(spaceB, toneB.id, 'Emotional');

addNode(spaceB, hookB.id, 'OpenQuestion');
addNode(spaceB, hookB.id, 'ShockingStat');

// BREAK THE SYMMETRY: give Friendly a unique child
addNode(spaceB, friendly.id, 'emoji_on');

// ── Analyze both ─────────────────────────────────────────────
// Strata 1-6 are auto-created. User nodes: Tone=7, Hook=91(8th), Body=92(9th)
// Tone children: 7.1, 7.2, 7.3. Hook children: 91.1, 91.2
const coordsA = ['7', '91', '92', '7.1', '7.2', '7.3', '91.1', '91.2'];
const coordsB = ['7', '91', '92', '7.1', '7.2', '7.3', '91.1', '91.2'];

const analysisA = analyzeSpace(registry, 'TweetA', coordsA);
const analysisB = analyzeSpace(registry, 'TweetB', coordsB);

console.log('═══ SPACE A: Baseline ═══\n');
console.log(`Symmetry group: ${analysisA.symmetryGroup}`);
console.log('Orbits:');
analysisA.orbits.forEach(o => {
    const label = o.size === 1 ? '(fixed)' : `(${o.size} interchangeable)`;
    console.log(`  ${o.members.join(', ')} ${label}`);
});

const sigA = foundationSignature(analysisA);
console.log(`Foundation signature: ${sigA.canonical}`);
console.log('\nLocal groups:');
sigA.localGroups.forEach(g => {
    console.log(`  Orbit ${g.orbitIndex}: ${g.groupName} (center: ${g.fixedCenter ?? 'none'}, leaves: [${g.permutableMembers.join(', ')}])`);
});
console.log('Quotient graph:');
sigA.quotientGraph.forEach(e => {
    console.log(`  Orbit${e.fromOrbit} ↔ Orbit${e.toOrbit} (weight: ${e.weight.toFixed(3)})`);
});
if (sigA.quotientGraph.length === 0) console.log('  (disconnected — all orbits independent)');

console.log('\n═══ SPACE B: Symmetry Broken (Friendly has emoji attr) ═══\n');
console.log(`Symmetry group: ${analysisB.symmetryGroup}`);
console.log('Orbits:');
analysisB.orbits.forEach(o => {
    const label = o.size === 1 ? '(fixed)' : `(${o.size} interchangeable)`;
    console.log(`  ${o.members.join(', ')} ${label}`);
});

const sigB = foundationSignature(analysisB);
console.log(`Foundation signature: ${sigB.canonical}`);
console.log('\nLocal groups:');
sigB.localGroups.forEach(g => {
    console.log(`  Orbit ${g.orbitIndex}: ${g.groupName} (center: ${g.fixedCenter ?? 'none'}, leaves: [${g.permutableMembers.join(', ')}])`);
});

console.log('\n═══ SYMMETRY BREAKING DETECTION ═══\n');
const breaking = detectSymmetryBreaking(sigA, sigB);
console.log(`Relationship: ${breaking.relationship}`);
console.log(`Description: ${breaking.description}`);
console.log(`Changed orbits: [${breaking.changedOrbits.join(', ')}]`);
console.log(`\nA: ${breaking.signatureA}`);
console.log(`B: ${breaking.signatureB}`);
