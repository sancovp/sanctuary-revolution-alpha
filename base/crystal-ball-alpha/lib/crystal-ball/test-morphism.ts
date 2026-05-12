/**
 * test-morphism.ts — Category Theory Tests for Crystal Ball
 *
 * Verifies:
 *   1. Morphism extraction (source → target via selection index)
 *   2. Composition (dot = morphism composition)
 *   3. Associativity: (f ∘ g) ∘ h = f ∘ (g ∘ h) as real numbers
 *   4. Identity law
 *   5. Path finding (all morphism chains from A to B)
 *   6. Category axiom verification on real spaces
 *
 * Run with: npx tsx lib/crystal-ball/test-morphism.ts
 */

import {
    createRegistry,
    createSpace,
    addNode,
    coordToReal,
    encodeDot,
    type Registry,
    type Space,
} from './index';

import {
    morphismsFrom,
    morphismsTo,
    identity,
    compose,
    composeChain,
    findMorphism,
    findPaths,
    verifyCategory,
    formatMorphism,
    formatComposed,
    spectrum,
    spectrumLabels,
    arity,
    sources,
    isTerminal,
    isInitial,
    hom,
    homSize,
    slice,
    coslice,
    deepCoslice,
    categorySummary,
    type Morphism,
} from './morphism';

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
    if (condition) {
        console.log(`  ✅ ${message}`);
        passed++;
    } else {
        console.log(`  ❌ FAIL: ${message}`);
        failed++;
    }
}

function assertClose(a: number, b: number, msg: string, tol = 1e-12): void {
    assert(Math.abs(a - b) < tol, `${msg} (${a} ≈ ${b})`);
}

// ─── Build Test Spaces ────────────────────────────────────────────

function buildSimpleSpace(): { registry: Registry; space: Space } {
    const registry = createRegistry();
    const space = createSpace(registry, 'Simple');
    // root → A, B, C  (3 morphisms from root)
    const a = addNode(space, 'root', 'A');  // selection 1
    const b = addNode(space, 'root', 'B');  // selection 2
    const c = addNode(space, 'root', 'C');  // selection 3
    // A → A1, A2  (2 morphisms from A)
    addNode(space, a.id, 'A1');  // selection 1 under A
    addNode(space, a.id, 'A2');  // selection 2 under A
    // B → B1  (1 morphism from B)
    addNode(space, b.id, 'B1');  // selection 1 under B
    return { registry, space };
}

function build7x7Space(): { registry: Registry; space: Space } {
    const registry = createRegistry();
    const space = createSpace(registry, 'Septenary');
    const pillars: string[] = [];
    // root → 7 pillars (morphisms)
    for (let i = 0; i < 7; i++) {
        const p = addNode(space, 'root', `P${i + 1}`);
        pillars.push(p.id);
    }
    // Each pillar → 7 targets (morphisms)
    for (const pId of pillars) {
        for (let j = 0; j < 7; j++) {
            addNode(space, pId, `${pId}_T${j + 1}`);
        }
    }
    return { registry, space };
}

function buildDeepSpace(): { registry: Registry; space: Space } {
    const registry = createRegistry();
    const space = createSpace(registry, 'Deep');
    // 4 levels deep: root → L1 → L2 → L3 → L4
    const l1 = addNode(space, 'root', 'L1');
    const l2 = addNode(space, l1.id, 'L2');
    const l3 = addNode(space, l2.id, 'L3');
    addNode(space, l3.id, 'L4');
    // Also add a sibling at each level for richer morphism structure
    addNode(space, 'root', 'L1b');
    addNode(space, l1.id, 'L2b');
    addNode(space, l2.id, 'L3b');
    return { registry, space };
}

// ─── Test Suite ───────────────────────────────────────────────────

console.log('\n══════════════════════════════════════════════════');
console.log('  CRYSTAL BALL: Category Theory Tests');
console.log('══════════════════════════════════════════════════\n');

// ── §1. Morphism Extraction ──────────────────────────────────────

console.log('§1. Morphism Extraction\n');

const { registry: r1, space: s1 } = buildSimpleSpace();

const rootMorphisms = morphismsFrom(s1, 'root');
assert(rootMorphisms.length === 3, `root has 3 outgoing morphisms (got ${rootMorphisms.length})`);
assert(rootMorphisms[0].source === 'root', 'first morphism source is root');
assert(rootMorphisms[0].target === '1', 'first morphism target is "1" (A)');
assert(rootMorphisms[0].selectionIndex === 1, 'first morphism selection index is 1');
assert(rootMorphisms[0].encoded === '1', 'first morphism encoded as "1"');

const aMorphisms = morphismsFrom(s1, '1');
assert(aMorphisms.length === 2, `A has 2 outgoing morphisms (got ${aMorphisms.length})`);
assert(aMorphisms[0].target === '1.1', 'A → A1 target is "1.1"');
assert(aMorphisms[1].target === '1.2', 'A → A2 target is "1.2"');

// Incoming morphisms
const incomingToA = morphismsTo(s1, '1');
assert(incomingToA.length === 1, `A has 1 incoming morphism (got ${incomingToA.length})`);
assert(incomingToA[0].source === 'root', 'incoming to A is from root');

console.log('');

// ── §2. Identity ─────────────────────────────────────────────────

console.log('§2. Identity Morphisms\n');

const idRoot = identity(s1, 'root');
assert(idRoot !== null, 'identity exists for root');
assert(idRoot!.object === 'root', 'identity object is root');

const idA = identity(s1, '1');
assert(idA !== null, 'identity exists for A');
assert(idA!.label === 'A', 'identity label is A');

console.log('');

// ── §3. Composition ──────────────────────────────────────────────

console.log('§3. Morphism Composition\n');

// root --1--> A --1--> A1
const rootToA = rootMorphisms[0]; // root → A (selection 1)
const aToA1 = aMorphisms[0];     // A → A1 (selection 1)

const composed = compose(rootToA, aToA1);
assert(composed !== null, 'root→A and A→A1 are composable');
assert(composed!.source === 'root', 'composed source is root');
assert(composed!.target === '1.1', 'composed target is A1 (1.1)');
assert(composed!.coordinate === '1.1', 'composed coordinate is "1.1"');
assertClose(composed!.real, coordToReal('1.1'), 'composed real matches coordToReal("1.1")');

// Non-composable: root → A and root → B (A.target ≠ B.source)
const rootToB = rootMorphisms[1]; // root → B (selection 2)
const nonComposable = compose(rootToA, rootToB);
assert(nonComposable === null, 'root→A and root→B are NOT composable (source ≠ target)');

// Longer chain: root --1--> A --2--> A2
const aToA2 = aMorphisms[1]; // A → A2 (selection 2)
const chain = composeChain([rootToA, aToA2]);
assert(chain !== null, 'chain root→A→A2 composes');
assert(chain!.coordinate === '1.2', 'chain coordinate is "1.2"');
assertClose(chain!.real, coordToReal('1.2'), 'chain real matches coordToReal("1.2")');

console.log('');

// ── §4. Associativity ────────────────────────────────────────────

console.log('§4. Associativity: (f ∘ g) ∘ h = f ∘ (g ∘ h)\n');

const { space: deep } = buildDeepSpace();
// Chain: root --1--> L1 --1--> L2 --1--> L3
const m_root_L1 = morphismsFrom(deep, 'root')[0]; // root → L1
const m_L1_L2 = morphismsFrom(deep, m_root_L1.target)[0]; // L1 → L2
const m_L2_L3 = morphismsFrom(deep, m_L1_L2.target)[0]; // L2 → L3

// Left association: (root→L1 ∘ L1→L2) ∘ L2→L3
const fg = compose(m_root_L1, m_L1_L2)!;
const leftCoord = `${fg.coordinate}.${m_L2_L3.encoded}`;
const leftReal = coordToReal(leftCoord);

// Right association: root→L1 ∘ (L1→L2 ∘ L2→L3)
const gh = compose(m_L1_L2, m_L2_L3)!;
const rightCoord = `${m_root_L1.encoded}.${gh.coordinate}`;
const rightReal = coordToReal(rightCoord);

assertClose(leftReal, rightReal, `associativity holds: (f∘g)∘h = f∘(g∘h) → ${leftReal}`);

// Full chain both ways
const leftChain = composeChain([m_root_L1, m_L1_L2, m_L2_L3]);
assert(leftChain !== null, 'triple composition succeeds');
assertClose(leftChain!.real, leftReal, 'chain real matches left-association');
assertClose(leftChain!.real, rightReal, 'chain real matches right-association');

console.log('');

// ── §5. Real Number = Composed Morphism ──────────────────────────

console.log('§5. Real Numbers as Composed Morphisms\n');

const { space: sept } = build7x7Space();

// In the 7×7 space, coordinate 3.5 = root --3--> P3 --5--> P3_T5
const rootMorphs = morphismsFrom(sept, 'root');
const p3Morphs = morphismsFrom(sept, rootMorphs[2].target);
const comp35 = compose(rootMorphs[2], p3Morphs[4])!;

assertClose(comp35.real, coordToReal('3.5'), '3.5 composition matches coordToReal');
assert(comp35.coordinate === '3.5', 'coordinate string is "3.5"');

// The real number 0.389885 IS the morphism root→P3→P3_T5
const expectedReal = 0.389885;
assertClose(comp35.real, expectedReal, `composed morphism real = ${expectedReal}`);

// Verify the encoding: 3.5 → "3" + DOT(8988) + "5" = "389885" → 0.389885
const encoded = encodeDot('3.5');
assert(encoded === '389885', `encodeDot("3.5") = "${encoded}" (expected "389885")`);

console.log('');

// ── §6. Path Finding ─────────────────────────────────────────────

console.log('§6. Path Finding (All Morphism Chains)\n');

// In the deep space: how many paths from root to L3?
// Only one: root → L1 → L2 → L3
const paths = findPaths(deep, 'root', m_L2_L3.target);
assert(paths.length === 1, `one path from root to L3 (got ${paths.length})`);
if (paths.length > 0) {
    assert(paths[0].chain.length === 3, `path has 3 morphisms (got ${paths[0].chain.length})`);
    console.log(`    Path: ${formatComposed(deep, paths[0])}`);
}

// From root to L4 (4 morphisms deep)
const m_L3 = morphismsFrom(deep, m_L2_L3.target);
if (m_L3.length > 0) {
    const pathsToL4 = findPaths(deep, 'root', m_L3[0].target);
    assert(pathsToL4.length === 1, `one path from root to L4 (got ${pathsToL4.length})`);
    if (pathsToL4.length > 0) {
        assert(pathsToL4[0].chain.length === 4, `path to L4 has 4 morphisms`);
        console.log(`    Path: ${formatComposed(deep, pathsToL4[0])}`);
    }
}

console.log('');

// ── §7. Full Category Axiom Verification ─────────────────────────

console.log('§7. Category Axiom Verification\n');

// Simple space
const catSimple = verifyCategory(s1);
assert(catSimple.associativity.holds, `Simple space: associativity holds (${catSimple.associativity.tested} triples tested)`);
assert(catSimple.identity.holds, `Simple space: identity holds (${catSimple.identity.tested} morphisms tested)`);
console.log(`    Objects: ${catSimple.totalObjects}, Morphisms: ${catSimple.totalMorphisms}`);

// 7×7 space
const cat7x7 = verifyCategory(sept);
assert(cat7x7.associativity.holds, `7×7 space: associativity holds (${cat7x7.associativity.tested} triples tested)`);
assert(cat7x7.identity.holds, `7×7 space: identity holds (${cat7x7.identity.tested} morphisms tested)`);
console.log(`    Objects: ${cat7x7.totalObjects}, Morphisms: ${cat7x7.totalMorphisms}`);

// Deep space
const catDeep = verifyCategory(deep);
assert(catDeep.associativity.holds, `Deep space: associativity holds (${catDeep.associativity.tested} triples tested)`);
assert(catDeep.identity.holds, `Deep space: identity holds (${catDeep.identity.tested} morphisms tested)`);
console.log(`    Objects: ${catDeep.totalObjects}, Morphisms: ${catDeep.totalMorphisms}`);

if (cat7x7.associativity.failures.length > 0) {
    console.log('\n  Associativity failures:');
    for (const f of cat7x7.associativity.failures.slice(0, 5)) {
        console.log(`    ${f}`);
    }
}

console.log('');

// ── §8. Morphism Display ─────────────────────────────────────────

console.log('§8. Morphism Display (Category View of Fascism-like Structure)\n');

const { space: s7 } = build7x7Space();
const rootArrows = morphismsFrom(s7, 'root');
console.log(`  root has ${rootArrows.length} outgoing morphisms:`);
for (const m of rootArrows.slice(0, 3)) {
    console.log(`    ${formatMorphism(s7, m)}  →  real: ${coordToReal(m.encoded)}`);
}
console.log('    ...');

// Show a composed morphism
const firstTarget = rootArrows[0].target;
const secondLevel = morphismsFrom(s7, firstTarget);
if (secondLevel.length > 0) {
    const comp = compose(rootArrows[0], secondLevel[0])!;
    console.log(`\n  Composed: ${formatComposed(s7, comp)}`);
    console.log(`  This IS the real number ${comp.real}`);
    console.log(`  It is NOT "node 1 contains node 1.1"`);
    console.log(`  It IS "${s7.nodes.get(rootArrows[0].target)?.label} --1--> ${s7.nodes.get(secondLevel[0].target)?.label}"`);
}

console.log('');

// ── §9. Categorical Primitives: spectrum, arity, sources ────────

console.log('§9. Categorical Primitives (spectrum, arity, sources)\n');

const sp1 = spectrum(s1, 'root');
assert(sp1.length === 3, `spectrum(root) = 3 targets (got ${sp1.length})`);
assert(sp1[0] === '1', 'spectrum(root)[0] = "1" (A)');

const spLabels = spectrumLabels(s1, 'root');
assert(spLabels[0] === 'A', 'spectrumLabels(root)[0] = "A"');
assert(spLabels[1] === 'B', 'spectrumLabels(root)[1] = "B"');
assert(spLabels[2] === 'C', 'spectrumLabels(root)[2] = "C"');

assert(arity(s1, 'root') === 3, 'arity(root) = 3');
assert(arity(s1, '1') === 2, 'arity(A) = 2');
assert(arity(s1, '3') === 0, 'arity(C) = 0 (terminal)');

const srcA = sources(s1, '1');
assert(srcA.length === 1, 'A has 1 source');
assert(srcA[0] === 'root', 'A source is root');

const srcRoot = sources(s1, 'root');
assert(srcRoot.length === 0, 'root has 0 sources (initial object)');

assert(isTerminal(s1, '3') === true, 'C is terminal (no outgoing morphisms)');
assert(isTerminal(s1, '1') === false, 'A is NOT terminal (has outgoing morphisms)');
assert(isInitial(s1, 'root') === true, 'root is initial (no incoming morphisms)');
assert(isInitial(s1, '1') === false, 'A is NOT initial (has incoming from root)');

console.log('');

// ── §10. Hom-sets and Slice/Coslice ──────────────────────────────

console.log('§10. Hom-sets and Slice/Coslice\n');

assert(homSize(s1, 'root', '1') === 1, '|Hom(root, A)| = 1');
assert(homSize(s1, '1', '1.1') === 1, '|Hom(A, A1)| = 1');
assert(homSize(s1, 'root', '1.1') === 0, '|Hom(root, A1)| = 0 (no direct morphism)');
assert(homSize(s1, '1', '2') === 0, '|Hom(A, B)| = 0 (no morphism between siblings)');

const sliceA = slice(s1, '1');
assert(sliceA.length === 1, 'slice(A) has 1 object (root has morphism to A)');
assert(sliceA[0].objectId === 'root', 'slice(A) object is root');

const cosliceRoot = coslice(s1, 'root');
assert(cosliceRoot.length === 3, 'coslice(root) has 3 objects (A, B, C)');

const cosliceA = coslice(s1, '1');
assert(cosliceA.length === 2, 'coslice(A) has 2 objects (A1, A2)');

const deepRoot = deepCoslice(s1, 'root');
assert(deepRoot.length === 6, `deepCoslice(root) reaches all 6 non-root objects (got ${deepRoot.length})`);

// Verify deep coslice includes composed morphisms
const a1Path = deepRoot.find(cm => cm.target === '1.1');
assert(a1Path !== null && a1Path !== undefined, 'deepCoslice reaches A1');
assert(a1Path!.chain.length === 2, 'path to A1 is 2 morphisms (root→A→A1)');

console.log('');

// ── §11. Category Summary ────────────────────────────────────────

console.log('§11. Category Summary\n');

const summary = categorySummary(s1);
assert(summary.objectCount === 7, `object count = 7 (got ${summary.objectCount})`);
assert(summary.morphismCount === 6, `morphism count = 6 (got ${summary.morphismCount})`);
assert(summary.initialObjects.length === 1, `1 initial object (got ${summary.initialObjects.length})`);
assert(summary.initialObjects[0] === 'root', 'initial object is root');
assert(summary.terminalObjects.length === 4, `4 terminal objects: C, A1, A2, B1 (got ${summary.terminalObjects.length})`);
assert(summary.maxArity === 3, `max arity = 3 (got ${summary.maxArity})`);
assert(summary.maxDepth === 2, `max depth = 2 (got ${summary.maxDepth})`);
assert(summary.isConnected === true, 'space is connected');

console.log(`  Summary: ${summary.objectCount} objects, ${summary.morphismCount} morphisms`);
console.log(`  Initial: ${summary.initialObjects.map(id => `${id}`).join(', ')}`);
console.log(`  Terminal: ${summary.terminalObjects.map(id => `${id}`).join(', ')}`);
console.log(`  Max arity: ${summary.maxArity}, Max depth: ${summary.maxDepth}`);
console.log(`  Connected: ${summary.isConnected}`);

// 7×7 summary
const sum7 = categorySummary(sept);
assert(sum7.objectCount === 57, `7×7 has 57 objects (got ${sum7.objectCount})`);
assert(sum7.morphismCount === 56, `7×7 has 56 morphisms (got ${sum7.morphismCount})`);
assert(sum7.maxArity === 7, `7×7 max arity = 7 (got ${sum7.maxArity})`);
assert(sum7.maxDepth === 2, `7×7 max depth = 2 (got ${sum7.maxDepth})`);
assert(sum7.terminalObjects.length === 49, `7×7 has 49 terminal objects (got ${sum7.terminalObjects.length})`);

console.log('');

// ── Summary ──────────────────────────────────────────────────────

console.log('══════════════════════════════════════════════════');
console.log(`  Results: ${passed} passed, ${failed} failed`);
console.log('══════════════════════════════════════════════════');

if (failed > 0) {
    process.exit(1);
}
