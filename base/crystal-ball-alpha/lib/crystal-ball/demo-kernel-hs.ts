/**
 * demo-kernel-hs.ts — Test the RKHS kernel function on a space with attributes
 * 
 * Run: npx tsx lib/crystal-ball/demo-kernel-hs.ts
 */

import { createSpace, addNode, type Registry } from './index';
import { kernelFunction, gramMatrix, analyzeSpace } from './kernel-function';

// ── Build a test space with attributes ─────────────────────────
const registry: Registry = { spaces: new Map(), kernels: new Map(), nextKernelId: 1 };

// Create space
const space = createSpace(registry, 'TweetType');

// Add children under root
const tone = addNode(space, 'root', 'Tone');
const hook = addNode(space, 'root', 'Hook');
const body = addNode(space, 'root', 'Body');

// Children under Tone define the spectrum (attributes removed)

// Add children under Tone (subtypes)

// Add children under Tone (subtypes)
addNode(space, tone.id, 'Friendly');
addNode(space, tone.id, 'Formal');
addNode(space, tone.id, 'Emotional');

// Add children under Hook
addNode(space, hook.id, 'OpenQuestion');
addNode(space, hook.id, 'ShockingStat');

// ── Full RKHS Analysis ───────────────────────────────────────
const coords = ['1', '2', '3', '1.1', '1.2', '1.3', '2.1', '2.2'];
const analysis = analyzeSpace(registry, 'TweetType', coords);

console.log('═══ RKHS SPACE ANALYSIS: TweetType ═══\n');

// Eigenspectrum
console.log('Eigenspectrum:');
analysis.eigenspectrum.forEach((e, i) => {
    const bar = '█'.repeat(Math.max(0, Math.round(e * 10)));
    console.log(`  λ${i + 1} = ${e.toFixed(4)} ${bar}`);
});
console.log(`\nEffective dimension: ${analysis.effectiveDimension}`);

// Symmetry orbits
console.log(`\nSymmetry group: ${analysis.symmetryGroup}`);
console.log('\nOrbits:');
analysis.orbits.forEach(o => {
    const label = o.size === 1 ? '(fixed)' : `(${o.size} interchangeable)`;
    console.log(`  ${o.members.join(', ')} ${label}`);
});

// Gram matrix
console.log('\nGram matrix:');
console.log('     ', coords.map(c => c.padStart(6)).join(''));
for (let i = 0; i < coords.length; i++) {
    const row = analysis.gramMatrix[i].map(v => v.toFixed(2).padStart(6)).join('');
    console.log(`${coords[i].padStart(5)} ${row}`);
}

// Distances
console.log('\nDistances (sorted):');
analysis.distances.slice(0, 15).forEach(d => {
    console.log(`  d(${d.from}, ${d.to}) = ${d.distance.toFixed(4)}`);
});

// ── Hybrid Kernel Analysis ───────────────────────────────────
import { hybridKernel } from './kernel-function';

console.log('\n═══ HYBRID KERNEL (named + walk) ═══\n');
const pairs: [string, string][] = [
    ['1', '1'],     // Self
    ['1', '2'],     // Tone vs Hook (siblings under root)
    ['1', '3'],     // Tone vs Body
    ['1.1', '1.2'], // Friendly vs Formal (siblings under Tone)
    ['1.1', '2.1'], // Friendly vs OpenQuestion (cousins)
    ['2.1', '2.2'], // OpenQuestion vs ShockingStat (siblings under Hook)
    ['1.1', '3'],   // Friendly vs Body (distant)
];

for (const [x, y] of pairs) {
    const h = hybridKernel(registry, 'TweetType', x, y);
    console.log(`K(${x.padEnd(3)}, ${y.padEnd(3)}) = ${h.value.toFixed(3).padStart(6)}  (named: ${h.named.toFixed(1)}, walk: ${h.walk.toFixed(3)}, sim: ${h.similarity.toFixed(3)})`);
}
