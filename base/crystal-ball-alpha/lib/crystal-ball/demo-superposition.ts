/**
 * demo-superposition.ts — Test orbits with genuine symmetry
 * 
 * Build a space where spectrum values have IDENTICAL sub-trees,
 * creating real superposition (orbit size > 1), then mine and reify.
 * 
 * Run: npx tsx lib/crystal-ball/demo-superposition.ts
 */

import {
    createRegistry,
    createSpace,
    addNode,
} from './index';
import {
    findSlotOrbits,
    computeSpaceSlotSignature,
    tensorGramMatrix,
} from './kernel-v2';

const registry = createRegistry();

// ── Space WITH genuine symmetry ──────────────────────────────

const mood = createSpace(registry, 'MoodBoard');

// Root spectrum: 3 mood categories
const happy = addNode(mood, 'root', 'Happy');     // 1
const sad = addNode(mood, 'root', 'Sad');         // 2
const angry = addNode(mood, 'root', 'Angry');     // 3

// Happy sub-spectrum: 3 variants with IDENTICAL sub-trees
const joyful = addNode(mood, happy.id, 'Joyful');     // 1.1
const cheerful = addNode(mood, happy.id, 'Cheerful'); // 1.2
const elated = addNode(mood, happy.id, 'Elated');     // 1.3

// Each Happy variant has SAME 2 sub-options (identical structure)
addNode(mood, joyful.id, 'Mild');    // 1.1.1
addNode(mood, joyful.id, 'Intense'); // 1.1.2

addNode(mood, cheerful.id, 'Mild');    // 1.2.1
addNode(mood, cheerful.id, 'Intense'); // 1.2.2

addNode(mood, elated.id, 'Mild');    // 1.3.1
addNode(mood, elated.id, 'Intense'); // 1.3.2

// Sad sub-spectrum: 2 variants, ALSO identical sub-trees
const melancholy = addNode(mood, sad.id, 'Melancholy'); // 2.1
const wistful = addNode(mood, sad.id, 'Wistful');       // 2.2

addNode(mood, melancholy.id, 'Mild');    // 2.1.1
addNode(mood, melancholy.id, 'Intense'); // 2.1.2

addNode(mood, wistful.id, 'Mild');    // 2.2.1
addNode(mood, wistful.id, 'Intense'); // 2.2.2

// Angry sub-spectrum: 2 variants, but with DIFFERENT sub-trees (asymmetric)
const frustrated = addNode(mood, angry.id, 'Frustrated'); // 3.1
const furious = addNode(mood, angry.id, 'Furious');       // 3.2

addNode(mood, frustrated.id, 'Mild');    // 3.1.1
addNode(mood, frustrated.id, 'Intense'); // 3.1.2
addNode(mood, frustrated.id, 'Extreme'); // 3.1.3  ← different!

addNode(mood, furious.id, 'Mild');    // 3.2.1
addNode(mood, furious.id, 'Intense'); // 3.2.2
// No 3.2.3 — Furious only has 2, Frustrated has 3 → ASYMMETRIC

console.log('═══ PER-SLOT ORBITS — MoodBoard ═══\n');

// Slot 0: root level
const root = mood.nodes.get('root')!;
const slot0 = findSlotOrbits(root, mood, 0);
console.log(`Slot 0 [Root → mood category]:`);
console.log(`  Spectrum: ${slot0.spectrumSize} values`);
for (const o of slot0.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${slot0.symmetryGroup}`);
console.log(`  0 means: ${slot0.superpositionMeaning}`);

// Slot 1: Happy variants (should be orbit size 3!)
console.log(`\nSlot 1 [Happy → variant]:`);
const slot1Happy = findSlotOrbits(happy, mood, 1);
console.log(`  Spectrum: ${slot1Happy.spectrumSize} values`);
for (const o of slot1Happy.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${slot1Happy.symmetryGroup}`);
console.log(`  0 means: ${slot1Happy.superpositionMeaning}`);

// Slot 1: Sad variants (should be orbit size 2!)
console.log(`\nSlot 1 [Sad → variant]:`);
const slot1Sad = findSlotOrbits(sad, mood, 1);
console.log(`  Spectrum: ${slot1Sad.spectrumSize} values`);
for (const o of slot1Sad.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${slot1Sad.symmetryGroup}`);
console.log(`  0 means: ${slot1Sad.superpositionMeaning}`);

// Slot 1: Angry variants (should be orbit size 1,1 — asymmetric!)
console.log(`\nSlot 1 [Angry → variant]:`);
const slot1Angry = findSlotOrbits(angry, mood, 1);
console.log(`  Spectrum: ${slot1Angry.spectrumSize} values`);
for (const o of slot1Angry.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${slot1Angry.symmetryGroup}`);
console.log(`  0 means: ${slot1Angry.superpositionMeaning}`);

// ── Full Signature ────────────────────────────────────────────

console.log('\n═══ FULL SPACE SLOT SIGNATURE ═══\n');
const sig = computeSpaceSlotSignature(registry, 'MoodBoard');
console.log(`Canonical: ${sig.canonical}`);
console.log(`Total configurations: ${sig.totalConfigurations}`);
console.log(`Total symmetry: ${sig.totalSymmetry}`);

// ── Gram Matrix showing symmetry ─────────────────────────────

console.log('\n═══ GRAM MATRIX — observe symmetry in similar values ═══\n');

const coords = [
    '1.1.1', '1.1.2',  // Happy/Joyful/Mild, Happy/Joyful/Intense
    '1.2.1', '1.2.2',  // Happy/Cheerful/Mild, Happy/Cheerful/Intense
    '1.3.1', '1.3.2',  // Happy/Elated/Mild, Happy/Elated/Intense
    '2.1.1', '2.2.1',  // Sad/Melancholy/Mild, Sad/Wistful/Mild
    '3.1.1', '3.2.1',  // Angry/Frustrated/Mild, Angry/Furious/Mild
];

const gram = tensorGramMatrix(registry, 'MoodBoard', coords);
console.log('            ' + coords.map(c => c.padEnd(7)).join(' '));
for (let i = 0; i < coords.length; i++) {
    const row = gram.matrix[i].map(v => v.toFixed(3).padStart(7)).join(' ');
    console.log(`  ${coords[i].padEnd(8)}  ${row}`);
}

console.log('\nKey observations:');
console.log('  - Happy variants (1.1.x vs 1.2.x vs 1.3.x): should show high similarity');
console.log('  - Sad variants (2.1.x vs 2.2.x): should show high similarity');
console.log('  - Angry variants (3.1.x vs 3.2.x): should show LESS similarity (asymmetric sub-trees)');
