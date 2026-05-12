/**
 * demo-fractran.ts — FRACTRAN lens demonstration
 * 
 * Shows that CB coordinates ARE prime factorizations,
 * dots ARE FRACTRAN fractions, and execution stays in genus 0.
 * 
 * Run: npx tsx lib/crystal-ball/demo-fractran.ts
 */

import {
    createRegistry,
    createKernel,
    lockKernel,
    addNode,
    addDot,
} from './index';

import {
    coordToFactorization,
    factorizationToCoord,
    factorizationToInteger,
    coordToInteger,
    orbitKey,
    dotToFraction,
    spaceToFractranProgram,
    executeFractran,
    traceIsGenus0,
    SUPERSINGULAR_PRIMES,
    MAX_SLOTS,
} from './fractran';

// ── 1. Coordinate ↔ Prime Factorization ──────────────────────

console.log('═══ 1. COORDINATE ↔ PRIME FACTORIZATION ═══\n');
console.log('The 15 supersingular primes (divisors of |Monster|):');
console.log(`  ${SUPERSINGULAR_PRIMES.join(', ')}`);
console.log(`  Max slots: ${MAX_SLOTS}\n`);

const examples = ['1', '2', '3', '1.1', '1.3.2', '0.2.0', '3.1.4', '7.7.7'];
for (const coord of examples) {
    const factors = coordToFactorization(coord);
    const n = factorizationToInteger(factors);
    const roundtrip = factorizationToCoord(factors);
    const factorStr = Array.from(factors.entries())
        .map(([p, e]) => `${p}${e > 1 ? `^${e}` : ''}`)
        .join(' × ') || '1 (empty)';
    console.log(`  coord "${coord}" → N = ${n} = ${factorStr}  (roundtrip: "${roundtrip}")`);
}

// ── 2. Dots → FRACTRAN Fractions ─────────────────────────────

console.log('\n═══ 2. DOTS → FRACTRAN FRACTIONS ═══\n');

const registry = createRegistry();
const pipelineK = createKernel(registry, 'Pipeline');

// Build a simple pipeline: A → B → C
const nodeA = addNode(pipelineK.space, 'root', 'A');
const nodeB = addNode(pipelineK.space, 'root', 'B');
const nodeC = addNode(pipelineK.space, 'root', 'C');

// A → B → C pipeline (dots)
addDot(pipelineK.space, nodeA.id, nodeB.id, 'step1');
addDot(pipelineK.space, nodeB.id, nodeC.id, 'step2');

console.log('Pipeline: A → B → C');
console.log(`  Node A: selection 1, coord "1", N = ${coordToInteger('1')}`);
console.log(`  Node B: selection 2, coord "2", N = ${coordToInteger('2')}`);
console.log(`  Node C: selection 3, coord "3", N = ${coordToInteger('3')}`);
console.log();

// Extract FRACTRAN program from dots
const program = spaceToFractranProgram(pipelineK.space);
console.log(`FRACTRAN program "${program.name}":`);
for (const f of program.fractions) {
    console.log(`  ${f.label}: ${f.numerator}/${f.denominator}`);
}

// Execute!
console.log('\nExecution from A (N = 2):');
const trace1 = executeFractran(program, 2, 10);
for (const state of trace1.states) {
    const factorStr = Array.from(state.factorization.entries())
        .map(([p, e]) => `${p}${e > 1 ? `^${e}` : ''}`)
        .join(' × ') || '1';
    console.log(`  step ${state.step}: N = ${state.integer} = ${factorStr}  coord = "${state.coordinate}"${state.appliedFraction ? `  via ${state.appliedFraction}` : ''}`);
}
console.log(`  ${trace1.halted ? `Halted: ${trace1.haltReason}` : 'Running...'}`);

const genus1 = traceIsGenus0(trace1);
console.log(`  Genus 0: ${genus1.genus0 ? '✅ YES' : `❌ NO (violated at step ${genus1.firstViolation}, rogue prime ${genus1.roguePrime})`}`);

// ── 3. Deeper pipeline ──────────────────────────────────────

console.log('\n═══ 3. COMPILER PIPELINE AS FRACTRAN ═══\n');

const compilerK = createKernel(registry, 'Compiler');
const slots = ['Lex', 'Parse', 'TypeCheck', 'Optimize', 'Codegen', 'Link', 'Emit'];
const slotNodes: string[] = [];
for (const name of slots) {
    slotNodes.push(addNode(compilerK.space, 'root', name).id);
}
// Pipeline dots
for (let i = 0; i < slotNodes.length - 1; i++) {
    addDot(compilerK.space, slotNodes[i], slotNodes[i + 1], `${slots[i]}→${slots[i + 1]}`);
}

const compilerProg = spaceToFractranProgram(compilerK.space);
console.log(`FRACTRAN program "${compilerProg.name}" (${compilerProg.fractions.length} fractions):`);
for (const f of compilerProg.fractions) {
    console.log(`  ${f.label}: ${f.numerator}/${f.denominator}`);
}

// Execute from Lex (selection 1 → N = 2)
console.log('\nExecution from Lex (N = 2):');
const trace2 = executeFractran(compilerProg, 2, 20);
for (const state of trace2.states) {
    const factorStr = Array.from(state.factorization.entries())
        .map(([p, e]) => `${p}${e > 1 ? `^${e}` : ''}`)
        .join(' × ') || '1';
    const slotIdx = SUPERSINGULAR_PRIMES.indexOf(
        Array.from(state.factorization.keys())[0] ?? 0);
    const slotName = slotIdx >= 0 && slotIdx < slots.length ? slots[slotIdx] : '?';
    console.log(`  step ${state.step}: N = ${state.integer.toString().padStart(3)} = ${factorStr.padEnd(5)}  [${slotName}]${state.appliedFraction ? `  via ${state.appliedFraction}` : ''}`);
}
console.log(`  ${trace2.halted ? `Halted: ${trace2.haltReason}` : 'Running...'}`);

const genus2 = traceIsGenus0(trace2);
console.log(`  Genus 0: ${genus2.genus0 ? '✅ YES (all primes supersingular)' : `❌ NO`}`);

// ── 4. Orbit computation via FRACTRAN ────────────────────────

console.log('\n═══ 4. ORBITS VIA PRIME FACTORIZATION ═══\n');

// Two configs with same set of IDs → same orbit key
const configs = [
    '1.2.3',   // A in slot 0, B in slot 1, C in slot 2
    '2.1.3',   // B in slot 0, A in slot 1, C in slot 2
    '3.2.1',   // C in slot 0, B in slot 1, A in slot 2
    '1.1.3',   // A in slot 0, A in slot 1, C in slot 2 (different!)
];

console.log('Orbit key = sorted exponents (ignoring positions):');
for (const coord of configs) {
    const factors = coordToFactorization(coord);
    const key = orbitKey(factors);
    const n = factorizationToInteger(factors);
    console.log(`  coord "${coord}" → N = ${n.toString().padStart(5)} → orbit key: [${key}]`);
}

console.log('\nFirst 3 have orbit key [1,2,3] = same orbit (permutations of {1,2,3})');
console.log('Last one has orbit key [1,1,3] = different orbit (has repeated exponent)');

// ── 5. Summary ───────────────────────────────────────────────

console.log('\n═══ 5. SUMMARY ═══\n');
console.log('CB coordinates ARE FRACTRAN states:');
console.log('  • Slot position → supersingular prime');
console.log('  • Selection value → exponent');
console.log('  • 0 = exponent 0 = register empty (superposition)');
console.log('  • Dots = FRACTRAN fractions (rewrite rules)');
console.log('  • Execution = sequential fraction application');
console.log('  • Orbits = same multiset of exponents');
console.log('  • Genus 0 ⟺ all primes ≤ 71 (supersingular)');
console.log('  • FRACTRAN is Turing-complete → CB is Turing-complete ∎');
