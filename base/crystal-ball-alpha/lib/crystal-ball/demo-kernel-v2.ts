/**
 * demo-kernel-v2.ts — Test the corrected RKHS (tensor product on slots)
 * 
 * Run: npx tsx lib/crystal-ball/demo-kernel-v2.ts
 */

import {
    createRegistry,
    createSpace,
    addNode,
} from './index';
import {
    parseSlots,
    slotKernel,
    tensorKernel,
    findSlotOrbits,
    computeSpaceSlotSignature,
    tensorGramMatrix,
} from './kernel-v2';

const registry = createRegistry();

// ── Build a Tweet space with real spectrum structure ─────────

const tweet = createSpace(registry, 'Tweet');

// Root children = top-level slots
const tone = addNode(tweet, 'root', 'Tone');       // selection 1
const hook = addNode(tweet, 'root', 'Hook');       // selection 2  
const body = addNode(tweet, 'root', 'Body');       // selection 3

// Tone spectrum (children of Tone = spectrum values at slot 1)
const casual = addNode(tweet, tone.id, 'Casual');         // 1.1
const professional = addNode(tweet, tone.id, 'Professional'); // 1.2
const sentimental = addNode(tweet, tone.id, 'Sentimental');  // 1.3

// Hook spectrum  
const question = addNode(tweet, hook.id, 'Question');      // 2.1
const statistic = addNode(tweet, hook.id, 'Statistic');    // 2.2
const anecdote = addNode(tweet, hook.id, 'Anecdote');      // 2.3

// Body spectrum
const shortBody = addNode(tweet, body.id, 'Short');        // 3.1
const mediumBody = addNode(tweet, body.id, 'Medium');      // 3.2
const longBody = addNode(tweet, body.id, 'Long');          // 3.3

// Sub-spectrum: Casual tone has sub-options
const friendly = addNode(tweet, casual.id, 'Friendly');    // 1.1.1
const playful = addNode(tweet, casual.id, 'Playful');      // 1.1.2
const relaxed = addNode(tweet, casual.id, 'Relaxed');      // 1.1.3

// Sub-spectrum: Professional tone has sub-options  
const formal = addNode(tweet, professional.id, 'Formal');  // 1.2.1
const authoritative = addNode(tweet, professional.id, 'Authoritative'); // 1.2.2

console.log('═══ SLOT PARSING ═══\n');

const coords = ['1.1.1', '1.1.2', '1.2.1', '2.3', '3.1', '0.0.0', '1.0', '0.1'];
for (const c of coords) {
    const slots = parseSlots(c);
    console.log(`  ${c.padEnd(8)} → ${slots.map(s =>
        s.isSuperposition ? '0(super)' : `${s.selectionIndex}(${s.real.toFixed(3)})`
    ).join(' . ')}`);
}

console.log('\n═══ PER-SLOT KERNEL K_k ═══\n');

const testPairs = [
    ['1', '1'],     // identical
    ['1', '2'],     // adjacent primacy
    ['1', '7'],     // far primacy
    ['1', '91'],    // across wrap boundary
    ['0', '3'],     // superposition vs specific
    ['0', '0'],     // both superposition
];

for (const [a, b] of testPairs) {
    const sa = parseSlots(a)[0];
    const sb = parseSlots(b)[0];
    const k = slotKernel(sa, sb, 7);
    console.log(`  K(${a.padEnd(3)}, ${b.padEnd(3)}) = ${k.toFixed(6)}   ${a === b ? '(identical)' :
        sa.isSuperposition || sb.isSuperposition ? '(superposition)' :
            `(primacy dist: ${Math.abs(sa.real - sb.real).toFixed(3)})`
        }`);
}

console.log('\n═══ TENSOR PRODUCT KERNEL K(x,y) = ∏K_k ═══\n');

const tensorPairs = [
    ['1.1.1', '1.1.1'],  // identical: Casual/Friendly
    ['1.1.1', '1.1.2'],  // same tone+style, different sub: Friendly vs Playful
    ['1.1.1', '1.2.1'],  // same tone, different style: Casual/Friendly vs Prof/Formal
    ['1.1.1', '2.1.0'],  // different top-level: Tone vs Hook
    ['0.0.0', '1.1.1'],  // full superposition vs specific
    ['1.0', '1.1'],      // superposition at slot 2 vs specific at slot 2
];

for (const [a, b] of tensorPairs) {
    const result = tensorKernel(registry, 'Tweet', a, b);
    const perSlotStr = result.perSlot.map(s => s.similarity.toFixed(3)).join(' × ');
    console.log(`  K(${a.padEnd(8)}, ${b.padEnd(8)}) = ${result.value.toFixed(6)}  [${perSlotStr}]`);
}

console.log('\n═══ PER-SLOT ORBITS ═══\n');

const root = tweet.nodes.get('root')!;
console.log('Slot 0 (root → top level):');
const rootOrbits = findSlotOrbits(root, tweet, 0);
console.log(`  Spectrum: ${rootOrbits.spectrumSize} values`);
for (const o of rootOrbits.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${rootOrbits.symmetryGroup}`);
console.log(`  0 means: ${rootOrbits.superpositionMeaning}`);

console.log('\nSlot 1 (Tone → style):');
const toneOrbits = findSlotOrbits(tone, tweet, 1);
console.log(`  Spectrum: ${toneOrbits.spectrumSize} values`);
for (const o of toneOrbits.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${toneOrbits.symmetryGroup}`);
console.log(`  0 means: ${toneOrbits.superpositionMeaning}`);

console.log('\nSlot 2 (Casual → sub):');
const casualOrbits = findSlotOrbits(casual, tweet, 2);
console.log(`  Spectrum: ${casualOrbits.spectrumSize} values`);
for (const o of casualOrbits.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${casualOrbits.symmetryGroup}`);
console.log(`  0 means: ${casualOrbits.superpositionMeaning}`);

console.log('\nSlot 2 (Professional → sub):');
const profOrbits = findSlotOrbits(professional, tweet, 2);
console.log(`  Spectrum: ${profOrbits.spectrumSize} values`);
for (const o of profOrbits.orbits) {
    console.log(`  Orbit [${o.members.join(',')}]: ${o.labels.join(', ')} (size ${o.size})`);
}
console.log(`  Symmetry: ${profOrbits.symmetryGroup}`);
console.log(`  0 means: ${profOrbits.superpositionMeaning}`);

// ── Full Space Signature ─────────────────────────────────────

console.log('\n═══ FULL SPACE SLOT SIGNATURE ═══\n');

const sig = computeSpaceSlotSignature(registry, 'Tweet');
console.log(`Space: ${sig.spaceName}`);
console.log(`Total configurations: ${sig.totalConfigurations}`);
console.log(`Total symmetry: ${sig.totalSymmetry}`);
console.log(`Canonical: ${sig.canonical}`);
console.log(`\nPer-slot breakdown:`);
for (const slot of sig.slots) {
    const orbitStr = slot.orbits.map(o => `{${o.labels.join(',')}}`).join(' ');
    console.log(`  Slot ${slot.slotIndex} [${slot.parentLabel}]: spectrum=${slot.spectrumSize}, ${slot.symmetryGroup} — ${orbitStr}`);
    console.log(`    0 means: ${slot.superpositionMeaning}`);
}

// ── Tensor Gram Matrix ───────────────────────────────────────

console.log('\n═══ TENSOR GRAM MATRIX (select coordinate paths) ═══\n');

const sampleCoords = ['1.1.1', '1.1.2', '1.1.3', '1.2.1', '1.2.2', '1.3', '2.1', '2.2', '3.1'];
const gram = tensorGramMatrix(registry, 'Tweet', sampleCoords);

// Print header
console.log('            ' + sampleCoords.map(c => c.padEnd(7)).join(' '));
for (let i = 0; i < sampleCoords.length; i++) {
    const row = gram.matrix[i].map(v => v.toFixed(3).padStart(7)).join(' ');
    console.log(`  ${sampleCoords[i].padEnd(8)}  ${row}`);
}
