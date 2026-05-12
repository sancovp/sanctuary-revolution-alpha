/**
 * demo-futamura.ts — Build the Futamura Projection Space
 * 
 * Reifies CB's own compiler parts as KernelSpaces, then computes
 * the foundation signature of the compiler-as-a-whole.
 * 
 * This IS Phase 2+3: the metalanguage emerges from reified compiler parts.
 * 
 * Run: npx tsx lib/crystal-ball/demo-futamura.ts
 */

import {
    createRegistry,
    createKernel,
    lockKernel,
    addNode,

    addDot,
    fullCoordinate,
    coordToReal,
    kernelPosition,
    listKernels,
    type Registry,
    type KernelSpace,
} from './index';
import {
    analyzeSpace,
    foundationSignature,
    detectSymmetryBreaking,
} from './kernel-function';

const registry = createRegistry();

// ─── STEP 1: Reify the Grammar ──────────────────────────────────
// The 10 tokens as a kernel. Each token IS a slot.

const grammarKernel = createKernel(registry, 'Grammar');
const tokens = addNode(grammarKernel.space, 'root', 'Tokens');

const zeroTok = addNode(grammarKernel.space, tokens.id, 'Zero_Superposition');

const selTok = addNode(grammarKernel.space, tokens.id, 'Selection_1to7');

const drillTok = addNode(grammarKernel.space, tokens.id, 'Drill_8');

const closeTok = addNode(grammarKernel.space, tokens.id, 'CloseDrill_88');

const wrapTok = addNode(grammarKernel.space, tokens.id, 'Wrap_9');

const dotTok = addNode(grammarKernel.space, tokens.id, 'Dot_8988');

const kOpenTok = addNode(grammarKernel.space, tokens.id, 'KernelOpen_90');

const kCloseTok = addNode(grammarKernel.space, tokens.id, 'KernelClose_900');

const alsoOpenTok = addNode(grammarKernel.space, tokens.id, 'AlsoOpen_90009');

const alsoCloseTok = addNode(grammarKernel.space, tokens.id, 'AlsoClose_9900099');

lockKernel(registry, grammarKernel.globalId);

// ─── STEP 2: Reify the Parser ───────────────────────────────────
// parseCoordinate: string → parsed segments

const parserKernel = createKernel(registry, 'Parser');
const input = addNode(parserKernel.space, 'root', 'Input');

const segments = addNode(parserKernel.space, 'root', 'Segments');

const output = addNode(parserKernel.space, 'root', 'ParsedCoordinate');

// Parser depends on Grammar
input.kernelRef = grammarKernel.globalId;

lockKernel(registry, parserKernel.globalId);

// ─── STEP 3: Reify the Evaluator (scry) ─────────────────────────
// scry: (registry, space, coordinate) → resolved nodes

const scryKernel = createKernel(registry, 'Scry');
const scryInput = addNode(scryKernel.space, 'root', 'CoordinateInput');

const resolution = addNode(scryKernel.space, 'root', 'Resolution');

const resolved = addNode(scryKernel.space, 'root', 'ResolvedNodes');

// Scry depends on Parser
scryInput.kernelRef = parserKernel.globalId;

lockKernel(registry, scryKernel.globalId);

// ─── STEP 4: Reify the Encoder (coordToReal) ────────────────────
// coordToReal: coordinate → real number ∈ (0,1)

const encoderKernel = createKernel(registry, 'Encoder');
const encInput = addNode(encoderKernel.space, 'root', 'CoordinateString');

const dotEnc = addNode(encoderKernel.space, 'root', 'DotEncoding');

const realOutput = addNode(encoderKernel.space, 'root', 'RealNumber');

lockKernel(registry, encoderKernel.globalId);

// ─── STEP 5: Reify the Locker ───────────────────────────────────
// lock: kernel → locked kernel (recursive verification)

const lockerKernel = createKernel(registry, 'Locker');
const lockInput = addNode(lockerKernel.space, 'root', 'KernelToLock');

const verification = addNode(lockerKernel.space, 'root', 'RecursiveVerification');

const lockResult = addNode(lockerKernel.space, 'root', 'LockResult');

lockKernel(registry, lockerKernel.globalId);

// ─── STEP 6: Reify the Miner ───────────────────────────────────
// mine: locked kernel → mineSpace points

const minerKernel = createKernel(registry, 'Miner');
const mineInput = addNode(minerKernel.space, 'root', 'LockedKernel');

const projection = addNode(minerKernel.space, 'root', 'Projection');

const mineOutput = addNode(minerKernel.space, 'root', 'MineSpacePoints');

// Miner depends on Encoder
mineInput.kernelRef = lockerKernel.globalId;

lockKernel(registry, minerKernel.globalId);

// ─── STEP 7: Compose the Compiler ──────────────────────────────
// The full CB compiler: Grammar → Parser → Scry → Lock → Mine

const compilerKernel = createKernel(registry, 'CB_Compiler');

const grammarSlot = addNode(compilerKernel.space, 'root', 'Grammar');
grammarSlot.kernelRef = grammarKernel.globalId;

const parserSlot = addNode(compilerKernel.space, 'root', 'Parser');
parserSlot.kernelRef = parserKernel.globalId;

const scrySlot = addNode(compilerKernel.space, 'root', 'Scry');
scrySlot.kernelRef = scryKernel.globalId;

const encoderSlot = addNode(compilerKernel.space, 'root', 'Encoder');
encoderSlot.kernelRef = encoderKernel.globalId;

const lockerSlot = addNode(compilerKernel.space, 'root', 'Locker');
lockerSlot.kernelRef = lockerKernel.globalId;

const minerSlot = addNode(compilerKernel.space, 'root', 'Miner');
minerSlot.kernelRef = minerKernel.globalId;

// ─── STEP 8: Add the pipeline dots (morphisms) ─────────────────
// Grammar → Parser → Scry → Encoder → Locker → Miner
addDot(compilerKernel.space, grammarSlot.id, parserSlot.id, 'feeds');
addDot(compilerKernel.space, parserSlot.id, scrySlot.id, 'parses_for');
addDot(compilerKernel.space, scrySlot.id, encoderSlot.id, 'resolves_to');
addDot(compilerKernel.space, encoderSlot.id, lockerSlot.id, 'encodes_for');
addDot(compilerKernel.space, lockerSlot.id, minerSlot.id, 'locks_for');

const compilerLock = lockKernel(registry, compilerKernel.globalId);

// ─── REPORT ─────────────────────────────────────────────────────

console.log('═══ FUTAMURA PROJECTION SPACE ═══\n');
console.log(`Compiler kernel #${compilerKernel.globalId}: ${compilerLock.success ? '🔒 LOCKED' : '❌ FAILED'}\n`);

console.log('Component kernels:');
const compilerParts = [
    { name: 'Grammar', kernel: grammarKernel },
    { name: 'Parser', kernel: parserKernel },
    { name: 'Scry', kernel: scryKernel },
    { name: 'Encoder', kernel: encoderKernel },
    { name: 'Locker', kernel: lockerKernel },
    { name: 'Miner', kernel: minerKernel },
];

for (const part of compilerParts) {
    const pos = kernelPosition(part.kernel.globalId);
    console.log(`  #${part.kernel.globalId} ${part.name.padEnd(12)} pos=${pos.toFixed(8)}`);
}

// ─── RKHS Analysis of the Compiler ──────────────────────────────
console.log('\n═══ RKHS ANALYSIS: Compiler Structure ═══\n');

// Analyze each compiler part's internal structure
for (const part of compilerParts) {
    // Get local coordinates for this kernel's nodes (skip strata 1-6)
    const nodes = Array.from(part.kernel.space.nodes.values())
        .filter(n => n.id !== 'root' && !n.stratum)
        .map(n => n.id);

    if (nodes.length >= 2) {
        const analysis = analyzeSpace(registry, part.kernel.space.name, nodes);
        const sig = foundationSignature(analysis);
        console.log(`${part.name}:`);
        console.log(`  Orbits: ${analysis.orbits.map(o => `[${o.members.join(',')}]`).join(' ')}`);
        console.log(`  Symmetry: ${analysis.symmetryGroup}`);
        console.log(`  Signature: ${sig.canonical}`);
        console.log();
    }
}

// ─── Cross-Kernel Symmetry ──────────────────────────────────────
console.log('═══ CROSS-KERNEL SYMMETRY COMPARISON ═══\n');

// Compare pairs of compiler parts
const pairs = [
    [0, 1], [0, 2], [0, 3], [1, 2], [2, 3], [3, 4], [4, 5],
];

for (const [i, j] of pairs) {
    const partA = compilerParts[i];
    const partB = compilerParts[j];

    const nodesA = Array.from(partA.kernel.space.nodes.values())
        .filter(n => n.id !== 'root' && !n.stratum).map(n => n.id);
    const nodesB = Array.from(partB.kernel.space.nodes.values())
        .filter(n => n.id !== 'root' && !n.stratum).map(n => n.id);

    if (nodesA.length >= 2 && nodesB.length >= 2) {
        const analysisA = analyzeSpace(registry, partA.kernel.space.name, nodesA);
        const analysisB = analyzeSpace(registry, partB.kernel.space.name, nodesB);
        const sigA = foundationSignature(analysisA);
        const sigB = foundationSignature(analysisB);
        const breaking = detectSymmetryBreaking(sigA, sigB);

        console.log(`${partA.name} ↔ ${partB.name}: ${breaking.relationship}`);
        if (breaking.relationship !== 'identical') {
            console.log(`  ${breaking.description}`);
        }
    }
}

// ─── The Compiler's Own Signature ───────────────────────────────
console.log('\n═══ THE COMPILER\'S FOUNDATION SIGNATURE ═══\n');

const compilerNodes = Array.from(compilerKernel.space.nodes.values())
    .filter(n => n.id !== 'root' && !n.stratum)
    .map(n => n.id);

const compilerAnalysis = analyzeSpace(registry, compilerKernel.space.name, compilerNodes);
const compilerSig = foundationSignature(compilerAnalysis);

console.log(`Orbits: ${compilerAnalysis.orbits.map(o => `[${o.members.join(',')}](${o.size})`).join(' ')}`);
console.log(`Symmetry group: ${compilerAnalysis.symmetryGroup}`);
console.log(`Eigenspectrum: [${compilerAnalysis.eigenspectrum.map(e => e.toFixed(2)).join(', ')}]`);
console.log(`Effective dimension: ${compilerAnalysis.effectiveDimension}`);
console.log(`Foundation signature: ${compilerSig.canonical}`);

console.log('\nLocal automorphism groups:');
for (const g of compilerSig.localGroups) {
    console.log(`  Orbit ${g.orbitIndex}: ${g.groupName} (order ${g.groupOrder}) — center: ${g.fixedCenter ?? 'none'}`);
}

console.log('\nQuotient graph:');
for (const e of compilerSig.quotientGraph) {
    console.log(`  Orbit${e.fromOrbit} ↔ Orbit${e.toOrbit} (weight: ${e.weight.toFixed(3)})`);
}
if (compilerSig.quotientGraph.length === 0) {
    console.log('  (disconnected)');
}

// ─── Full Coordinates for the Compiler ──────────────────────────
console.log('\n═══ FULL COORDINATES: The Compiler\'s Projection ═══\n');
for (const node of compilerNodes) {
    const full = fullCoordinate(compilerKernel.globalId, node);
    const real = coordToReal(full);
    const cNode = compilerKernel.space.nodes.get(node);
    const subK = cNode?.kernelRef ? `→ #${cNode.kernelRef}` : '';
    console.log(`  ${(cNode?.label ?? node).padEnd(12)} ${full.padEnd(16)} real=${real.toFixed(10)} ${subK}`);
}

console.log('\n═══ THIS IS THE FUTAMURA PROJECTION SPACE ═══');
console.log('The compiler describes itself. Each part is a kernel.');
console.log('The foundation signature IS the algebra.');
console.log(`The algebra: ${compilerSig.canonical}`);
