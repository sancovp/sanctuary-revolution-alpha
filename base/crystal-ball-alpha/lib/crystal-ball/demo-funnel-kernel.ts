/**
 * Business Funnel × Tweet Kernel Demo
 *
 * The Tweet kernel becomes a SUBSPACE inside a funnel kernel.
 * Now we see: which tweet configurations work at which funnel stages?
 *
 * The mineSpace reveals how tweet-space intersects funnel-space.
 *
 * Run with: npx tsx lib/crystal-ball/demo-funnel-kernel.ts
 */

import {
    createRegistry,
    addNode,
    setSlotCount,
    lockNode,
    type Registry,
    type Space,
    type CBNode,
} from './index';

import {
    mine,
    declareMineSpace,
    projectKernel,
    encodeFullCoordinate,
    fullCoordToReal,
    type KnownPoint,
} from './mine';

import { encodeDot, coordToReal } from './index';

// Helper: bare space
function createBareSpace(reg: Registry, name: string): Space {
    const root: CBNode = {
        id: "root",
        label: name,
        children: [],
        x: 0,
        y: 0,
    };
    const space: Space = {
        name,
        rootId: "root",
        nodes: new Map([["root", root]]),
        dots: [],
    };
    reg.spaces.set(name, space);
    return space;
}

// Helper: build a tweet subspace inside a parent node
function buildTweetSubspace(space: Space, parentId: string) {
    const hook = addNode(space, parentId, 'Hook');
    const hQ = addNode(space, hook.id, 'Question');
    addNode(space, hQ.id, 'Rhetorical');
    addNode(space, hQ.id, 'Provocative');
    addNode(space, hQ.id, 'Genuine');
    const hS = addNode(space, hook.id, 'Statistic');
    addNode(space, hS.id, 'Shocking');
    addNode(space, hS.id, 'Counterintuitive');
    const hC = addNode(space, hook.id, 'Contrarian');
    addNode(space, hC.id, 'HotTake');
    addNode(space, hC.id, 'Reframe');
    const hSt = addNode(space, hook.id, 'Story');
    addNode(space, hSt.id, 'MicroNarrative');
    addNode(space, hSt.id, 'Anecdote');

    const claim = addNode(space, parentId, 'Claim');
    addNode(space, claim.id, 'Bold');
    addNode(space, claim.id, 'Nuanced');
    addNode(space, claim.id, 'Observational');

    const evidence = addNode(space, parentId, 'Evidence');
    addNode(space, evidence.id, 'Personal');
    addNode(space, evidence.id, 'Data');
    addNode(space, evidence.id, 'Social');

    const cta = addNode(space, parentId, 'CTA');
    addNode(space, cta.id, 'Engage');
    addNode(space, cta.id, 'Follow');
    addNode(space, cta.id, 'Act');
    addNode(space, cta.id, 'Think');

    const tone = addNode(space, parentId, 'Tone');
    addNode(space, tone.id, 'Authoritative');
    addNode(space, tone.id, 'Casual');
    addNode(space, tone.id, 'Urgent');
    addNode(space, tone.id, 'Playful');
}

const reg = createRegistry();

// ═══════════════════════════════════════════════════════════
// KERNEL 1: AIDA Funnel (Awareness, Interest, Desire, Action)
// Each stage can be fulfilled by a tweet.
// ═══════════════════════════════════════════════════════════

console.log('═══════════════════════════════════════════════════════');
console.log('🏗️  Building AIDA Funnel Kernel with Tweet subspaces');
console.log('═══════════════════════════════════════════════════════\n');

const aidaSpace = createBareSpace(reg, 'AIDA_Funnel');

// Top-level funnel stages
const awareness = addNode(aidaSpace, 'root', 'Awareness');
const interest = addNode(aidaSpace, 'root', 'Interest');
const desire = addNode(aidaSpace, 'root', 'Desire');
const action = addNode(aidaSpace, 'root', 'Action');

// Each funnel stage gets a full tweet subspace
buildTweetSubspace(aidaSpace, awareness.id);
buildTweetSubspace(aidaSpace, interest.id);
buildTweetSubspace(aidaSpace, desire.id);
buildTweetSubspace(aidaSpace, action.id);

// Lock everything
let lockedCount = 0;
for (const [, node] of aidaSpace.nodes) {
    if (node.id !== 'root') {
        setSlotCount(aidaSpace, node.id, 1);
        lockNode(aidaSpace, node.id);
        lockedCount++;
    }
}
console.log(`   🔒 Locked ${lockedCount} nodes in AIDA Funnel\n`);

// ═══════════════════════════════════════════════════════════
// KERNEL 2: TOFU/MOFU/BOFU (Top/Middle/Bottom of Funnel)
// Different funnel model, same tweet subspaces.
// ═══════════════════════════════════════════════════════════

const tmbSpace = createBareSpace(reg, 'TMB_Funnel');

const tofu = addNode(tmbSpace, 'root', 'TOFU');
const mofu = addNode(tmbSpace, 'root', 'MOFU');
const bofu = addNode(tmbSpace, 'root', 'BOFU');

buildTweetSubspace(tmbSpace, tofu.id);
buildTweetSubspace(tmbSpace, mofu.id);
buildTweetSubspace(tmbSpace, bofu.id);

let lockedCount2 = 0;
for (const [, node] of tmbSpace.nodes) {
    if (node.id !== 'root') {
        setSlotCount(tmbSpace, node.id, 1);
        lockNode(tmbSpace, node.id);
        lockedCount2++;
    }
}
console.log(`   🔒 Locked ${lockedCount2} nodes in TMB Funnel\n`);

// ═══════════════════════════════════════════════════════════
// MINE EACH INDEPENDENTLY
// ═══════════════════════════════════════════════════════════

const msAIDA = mine(reg, 'AIDA_Funnel');
const msTMB = mine(reg, 'TMB_Funnel');

const aidaValid = msAIDA.known.filter((p: KnownPoint) => p.status === 'valid');
const aidaAdj = msAIDA.known.filter((p: KnownPoint) => p.status === 'adjacent');
const tmbValid = msTMB.known.filter((p: KnownPoint) => p.status === 'valid');
const tmbAdj = msTMB.known.filter((p: KnownPoint) => p.status === 'adjacent');

console.log('═══════════════════════════════════════════════════════');
console.log('📍 AIDA FUNNEL MINESPACE');
console.log('═══════════════════════════════════════════════════════');
console.log(`   Valid: ${aidaValid.length}, Adjacent: ${aidaAdj.length}`);

console.log('\n═══════════════════════════════════════════════════════');
console.log('📍 TMB FUNNEL MINESPACE');
console.log('═══════════════════════════════════════════════════════');
console.log(`   Valid: ${tmbValid.length}, Adjacent: ${tmbAdj.length}`);

// ═══════════════════════════════════════════════════════════
// PROJECT BOTH ONTO ONE "ContentMarketing" PLANE
// ═══════════════════════════════════════════════════════════

console.log('\n═══════════════════════════════════════════════════════');
console.log('🌐 UNIFIED MINESPACE: "ContentMarketing"');
console.log('   Two funnel models → ONE plane');
console.log('═══════════════════════════════════════════════════════');

const contentPlane = declareMineSpace('ContentMarketing');
projectKernel(contentPlane, reg, 'AIDA_Funnel');
projectKernel(contentPlane, reg, 'TMB_Funnel');

const allValid = contentPlane.known.filter((p: KnownPoint) => p.status === 'valid');
const allAdj = contentPlane.known.filter((p: KnownPoint) => p.status === 'adjacent');
const fromAIDA = allValid.filter((p: KnownPoint) => p.fromKernel === 'AIDA_Funnel');
const fromTMB = allValid.filter((p: KnownPoint) => p.fromKernel === 'TMB_Funnel');

console.log(`\n   Projected: ${contentPlane.projectedKernels.join(', ')}`);
console.log(`   Total valid:    ${allValid.length}`);
console.log(`   Total adjacent: ${allAdj.length}`);
console.log(`   From AIDA:      ${fromAIDA.length} valid`);
console.log(`   From TMB:       ${fromTMB.length} valid`);

// ═══════════════════════════════════════════════════════════
// SHOW THE LANDSCAPE: Where do funnels overlap?
// ═══════════════════════════════════════════════════════════

console.log('\n═══════════════════════════════════════════════════════');
console.log('🗺️  FUNNEL LANDSCAPE');
console.log('═══════════════════════════════════════════════════════');

// Look at depth-1 coordinates from each kernel
console.log('\n   AIDA stages (depth 1):');
for (const p of aidaValid.filter((p: KnownPoint) => !p.coordinate.includes('.'))) {
    const parts = p.coordinate.split('.');
    const idx = parseInt(parts[0], 10) - 1;
    const node = aidaSpace.nodes.get(aidaSpace.nodes.get('root')!.children[idx]);
    console.log(`     ${p.coordinate.padEnd(6)} → ${(node?.label ?? '?').padEnd(15)} @ x=${p.x.toFixed(6)}`);
}

console.log('\n   TMB stages (depth 1):');
for (const p of tmbValid.filter((p: KnownPoint) => !p.coordinate.includes('.'))) {
    const parts = p.coordinate.split('.');
    const idx = parseInt(parts[0], 10) - 1;
    const node = tmbSpace.nodes.get(tmbSpace.nodes.get('root')!.children[idx]);
    console.log(`     ${p.coordinate.padEnd(6)} → ${(node?.label ?? '?').padEnd(15)} @ x=${p.x.toFixed(6)}`);
}

// Show tweet configurations at each funnel stage
console.log('\n   ── Tweet configs per funnel stage ──');

function countNodesByLabel(space: Space, parentLabel: string): Map<string, number> {
    const counts = new Map<string, number>();
    for (const [, node] of space.nodes) {
        if (node.label === parentLabel) {
            counts.set(parentLabel, node.children.length);
        }
    }
    return counts;
}

// Walk AIDA depth 2 to show tweet structure per stage
const stageLabels = ['Awareness', 'Interest', 'Desire', 'Action'];
for (let i = 0; i < stageLabels.length; i++) {
    const stageCoord = String(i + 1);
    const stagePoints = aidaValid.filter((p: KnownPoint) =>
        p.coordinate.startsWith(stageCoord + '.') || p.coordinate === stageCoord
    );
    const deepPoints = stagePoints.filter((p: KnownPoint) =>
        p.coordinate.split('.').length >= 3
    );
    console.log(`     ${stageLabels[i]}: ${stagePoints.length} total, ${deepPoints.length} deep (leaf-level tweet configs)`);
}

// Full coordinate encoding demo
console.log('\n═══════════════════════════════════════════════════════');
console.log('🎯 FULL COORDINATE ENCODING (with 90/900 kernel markers)');
console.log('═══════════════════════════════════════════════════════');

// Simulate: ContentMarketing is global space 1
// AIDA_Funnel is global space 2
// Tweet subspace within AIDA is global space 3
const examples = [
    {
        name: 'Awareness-stage Provocative Question tweet (AIDA)',
        deliverableId: 1,  // ContentMarketing
        segments: [
            { spaceId: 2, selection: 1 },  // AIDA → Awareness
            { spaceId: 3, selection: 1 },  // Tweet → Hook
            { spaceId: 3, selection: 1 },  // Hook → Question
            { spaceId: 3, selection: 2 },  // Question → Provocative
        ],
    },
    {
        name: 'Action-stage HotTake tweet (AIDA)',
        deliverableId: 1,
        segments: [
            { spaceId: 2, selection: 4 },  // AIDA → Action
            { spaceId: 3, selection: 1 },  // Tweet → Hook
            { spaceId: 3, selection: 3 },  // Hook → Contrarian
            { spaceId: 3, selection: 1 },  // Contrarian → HotTake
        ],
    },
    {
        name: 'TOFU Shocking Statistic tweet (TMB)',
        deliverableId: 1,
        segments: [
            { spaceId: 4, selection: 1 },  // TMB → TOFU
            { spaceId: 3, selection: 1 },  // Tweet → Hook
            { spaceId: 3, selection: 2 },  // Hook → Statistic
            { spaceId: 3, selection: 1 },  // Statistic → Shocking
        ],
    },
];

for (const ex of examples) {
    const encoded = encodeFullCoordinate(ex.deliverableId, ex.segments);
    const real = fullCoordToReal(ex.deliverableId, ex.segments);
    console.log(`\n  📝 ${ex.name}`);
    console.log(`     Encoded: ${encoded}`);
    console.log(`     Real:    ${real}`);
    console.log(`     Path:    ${ex.segments.map(s => `space${s.spaceId}→${s.selection}`).join(' / ')}`);
}

// Show that different funnel models produce different reals even for "same" tweet config
console.log('\n═══════════════════════════════════════════════════════');
console.log('🔬 COLLISION-FREE: Same tweet, different funnels');
console.log('═══════════════════════════════════════════════════════');

const tweetInAIDA = fullCoordToReal(1, [
    { spaceId: 2, selection: 1 },  // AIDA → Awareness
    { spaceId: 3, selection: 1 },  // Hook
    { spaceId: 3, selection: 1 },  // Question
    { spaceId: 3, selection: 2 },  // Provocative
]);

const tweetInTMB = fullCoordToReal(1, [
    { spaceId: 4, selection: 1 },  // TMB → TOFU
    { spaceId: 3, selection: 1 },  // Hook
    { spaceId: 3, selection: 1 },  // Question
    { spaceId: 3, selection: 2 },  // Provocative
]);

console.log(`\n   "Provocative Question" in AIDA Awareness:`);
console.log(`     → ${tweetInAIDA}`);
console.log(`   "Provocative Question" in TMB TOFU:`);
console.log(`     → ${tweetInTMB}`);
console.log(`   Same tweet config, different context → ${tweetInAIDA === tweetInTMB ? '❌ COLLISION' : '✅ DIFFERENT REALS'}`);

console.log('\n═══════════════════════════════════════════════════════');
console.log('📊 TOTAL LANDSCAPE SIZE');
console.log('═══════════════════════════════════════════════════════');
// AIDA: 4 stages × tweet configs per stage
// TMB: 3 stages × tweet configs per stage
// Tweet per stage: ~10 hook × 3 claim × 3 evidence × 4 cta × 4 tone = ~1440
const tweetPerStage = 10 * 3 * 3 * 4 * 4;
const aidaTotal = 4 * tweetPerStage;
const tmbTotal = 3 * tweetPerStage;
console.log(`   AIDA funnel: 4 stages × ${tweetPerStage} tweet configs = ${aidaTotal.toLocaleString()}`);
console.log(`   TMB funnel:  3 stages × ${tweetPerStage} tweet configs = ${tmbTotal.toLocaleString()}`);
console.log(`   Combined landscape: ${(aidaTotal + tmbTotal).toLocaleString()} configurations`);
console.log(`   Each one → unique real number, collision-free\n`);
