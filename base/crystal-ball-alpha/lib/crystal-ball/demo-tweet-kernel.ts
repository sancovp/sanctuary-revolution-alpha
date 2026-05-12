/**
 * Tweet Kernel Demo
 *
 * A deep kernel with full spectra at every slot.
 * When mined, this produces a mineSpace where every
 * valid coordinate is a specific tweet configuration
 * you could actually generate from.
 *
 * Run with: npx tsx lib/crystal-ball/demo-tweet-kernel.ts
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

import { mine, type KnownPoint } from './mine';
import { encodeDot, coordToReal } from './index';

// Helper: create a bare space (no strata)
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

// ═══════════════════════════════════════════════════════════
// BUILD THE TWEET KERNEL
// ═══════════════════════════════════════════════════════════

const reg = createRegistry();
const space = createBareSpace(reg, 'Tweet');

// ─── 1. HOOK (how you open) ───────────────────────────────
const hook = addNode(space, 'root', 'Hook');

const hookQuestion = addNode(space, hook.id, 'Question');
addNode(space, hookQuestion.id, 'Rhetorical');
addNode(space, hookQuestion.id, 'Provocative');
addNode(space, hookQuestion.id, 'Genuine');
addNode(space, hookQuestion.id, 'Socratic');

const hookStat = addNode(space, hook.id, 'Statistic');
addNode(space, hookStat.id, 'Shocking');
addNode(space, hookStat.id, 'Counterintuitive');
addNode(space, hookStat.id, 'Trending');

const hookContrarian = addNode(space, hook.id, 'Contrarian');
addNode(space, hookContrarian.id, 'HotTake');
addNode(space, hookContrarian.id, 'Reframe');
addNode(space, hookContrarian.id, 'MythBust');

const hookStory = addNode(space, hook.id, 'Story');
addNode(space, hookStory.id, 'MicroNarrative');
addNode(space, hookStory.id, 'Anecdote');
addNode(space, hookStory.id, 'Scenario');

// ─── 2. CLAIM (the core assertion) ───────────────────────
const claim = addNode(space, 'root', 'Claim');

const claimBold = addNode(space, claim.id, 'Bold');
addNode(space, claimBold.id, 'Declarative');
addNode(space, claimBold.id, 'Predictive');
addNode(space, claimBold.id, 'Universal');

const claimNuanced = addNode(space, claim.id, 'Nuanced');
addNode(space, claimNuanced.id, 'Conditional');
addNode(space, claimNuanced.id, 'Comparative');
addNode(space, claimNuanced.id, 'Dialectical');

const claimObserve = addNode(space, claim.id, 'Observational');
addNode(space, claimObserve.id, 'Pattern');
addNode(space, claimObserve.id, 'Analogy');
addNode(space, claimObserve.id, 'Insight');

// ─── 3. EVIDENCE (supporting material) ───────────────────
const evidence = addNode(space, 'root', 'Evidence');

const evidPersonal = addNode(space, evidence.id, 'Personal');
addNode(space, evidPersonal.id, 'Experience');
addNode(space, evidPersonal.id, 'Result');
addNode(space, evidPersonal.id, 'Failure');

const evidData = addNode(space, evidence.id, 'Data');
addNode(space, evidData.id, 'Statistic');
addNode(space, evidData.id, 'Study');
addNode(space, evidData.id, 'Trend');

const evidSocial = addNode(space, evidence.id, 'Social');
addNode(space, evidSocial.id, 'Authority');
addNode(space, evidSocial.id, 'Consensus');
addNode(space, evidSocial.id, 'Example');

// ─── 4. CTA (what you want the reader to do) ─────────────
const cta = addNode(space, 'root', 'CTA');

const ctaEngage = addNode(space, cta.id, 'Engage');
addNode(space, ctaEngage.id, 'Reply');
addNode(space, ctaEngage.id, 'Retweet');
addNode(space, ctaEngage.id, 'Quote');

const ctaFollow = addNode(space, cta.id, 'Follow');
addNode(space, ctaFollow.id, 'Subscribe');
addNode(space, ctaFollow.id, 'Save');
addNode(space, ctaFollow.id, 'Bookmark');

const ctaAct = addNode(space, cta.id, 'Act');
addNode(space, ctaAct.id, 'Click');
addNode(space, ctaAct.id, 'Try');
addNode(space, ctaAct.id, 'Build');

const ctaThink = addNode(space, cta.id, 'Think');
addNode(space, ctaThink.id, 'Reflect');
addNode(space, ctaThink.id, 'Question');
addNode(space, ctaThink.id, 'Reconsider');

// ─── 5. TONE (voice/register) ────────────────────────────
const tone = addNode(space, 'root', 'Tone');

const toneAuth = addNode(space, tone.id, 'Authoritative');
addNode(space, toneAuth.id, 'Expert');
addNode(space, toneAuth.id, 'Teacher');
addNode(space, toneAuth.id, 'Leader');

const toneCasual = addNode(space, tone.id, 'Casual');
addNode(space, toneCasual.id, 'Friend');
addNode(space, toneCasual.id, 'Peer');
addNode(space, toneCasual.id, 'Conversational');

const toneUrgent = addNode(space, tone.id, 'Urgent');
addNode(space, toneUrgent.id, 'Breaking');
addNode(space, toneUrgent.id, 'Warning');
addNode(space, toneUrgent.id, 'Timely');

const tonePlayful = addNode(space, tone.id, 'Playful');
addNode(space, tonePlayful.id, 'Witty');
addNode(space, tonePlayful.id, 'Ironic');
addNode(space, tonePlayful.id, 'SelfDeprecating');

// ─── 6. AUDIENCE (who this is for) ───────────────────────
const audience = addNode(space, 'root', 'Audience');

const audFounders = addNode(space, audience.id, 'Founders');
addNode(space, audFounders.id, 'EarlyStage');
addNode(space, audFounders.id, 'Growth');
addNode(space, audFounders.id, 'Exit');

const audDevs = addNode(space, audience.id, 'Developers');
addNode(space, audDevs.id, 'Junior');
addNode(space, audDevs.id, 'Senior');
addNode(space, audDevs.id, 'Lead');

const audGeneral = addNode(space, audience.id, 'General');
addNode(space, audGeneral.id, 'Curious');
addNode(space, audGeneral.id, 'Skeptical');
addNode(space, audGeneral.id, 'Aligned');

// ─── 7. FORMAT (structural shape) ────────────────────────
const format = addNode(space, 'root', 'Format');
addNode(space, format.id, 'OneLiner');
addNode(space, format.id, 'ThreadOpener');
addNode(space, format.id, 'StandAlone');

// ═══════════════════════════════════════════════════════════
// LOCK THE KERNEL
// ═══════════════════════════════════════════════════════════

let nodeCount = 0;
for (const [, node] of space.nodes) {
    if (node.id !== 'root') {
        setSlotCount(space, node.id, 1);
        lockNode(space, node.id);
        nodeCount++;
    }
}
console.log(`\n🔒 Locked ${nodeCount} nodes in Tweet kernel\n`);

// ═══════════════════════════════════════════════════════════
// MINE IT
// ═══════════════════════════════════════════════════════════

const ms = mine(reg, 'Tweet');
const valid = ms.known.filter((p: KnownPoint) => p.status === 'valid');
const adjacent = ms.known.filter((p: KnownPoint) => p.status === 'adjacent');

console.log('═══════════════════════════════════════════════════════');
console.log('📍 TWEET MINESPACE');
console.log('═══════════════════════════════════════════════════════');
console.log(`   Deliverable: ${ms.deliverable}`);
console.log(`   Valid:    ${valid.length} (full configurations we HAVE)`);
console.log(`   Adjacent: ${adjacent.length} (configurations needing inference)`);
console.log(`   Identity: on diagonal at y=${valid[0]?.y.toFixed(8)}`);
console.log();

// Group valid points by depth
const byDepth = new Map<number, KnownPoint[]>();
for (const p of valid) {
    const depth = p.coordinate.split('.').length;
    if (!byDepth.has(depth)) byDepth.set(depth, []);
    byDepth.get(depth)!.push(p);
}

for (const [depth, points] of [...byDepth.entries()].sort((a, b) => a[0] - b[0])) {
    console.log(`   ── Depth ${depth} (${points.length} points) ──`);
    // Find labels by looking up nodes
    for (const p of points) {
        // Navigate to find the label
        const parts = p.coordinate.split('.');
        let currentNode = space.nodes.get('root');
        let labelPath: string[] = [];
        for (const part of parts) {
            const idx = parseInt(part, 10) - 1; // 1-indexed to 0-indexed
            if (currentNode && currentNode.children[idx]) {
                const childId = currentNode.children[idx];
                currentNode = space.nodes.get(childId);
                if (currentNode) labelPath.push(currentNode.label);
            }
        }
        const label = labelPath.join(' → ');
        console.log(`     ✅ ${p.coordinate.padEnd(12)} → 0.${p.encoded.padEnd(20)} ${label}`);
    }
    console.log();
}

// Show some example "adjacent" coordinates and what GPS would infer
console.log('   ── Adjacent highlights (GPS inference) ──');
const interestingAdjacent = adjacent.slice(0, 15);
for (const p of interestingAdjacent) {
    console.log(`     ◐  ${p.coordinate.padEnd(12)} → 0.${p.encoded.padEnd(20)} [needs inference]`);
}
if (adjacent.length > 15) {
    console.log(`     ... and ${adjacent.length - 15} more adjacent coordinates`);
}

// Show some example full paths that could generate tweets
console.log('\n═══════════════════════════════════════════════════════');
console.log('🎯 EXAMPLE GENERATABLE TWEET CONFIGURATIONS');
console.log('═══════════════════════════════════════════════════════');

// Find specific paths
function findPath(label: string): string | null {
    for (const [, node] of space.nodes) {
        if (node.label === label) return node.id;
    }
    return null;
}

// Build coordinate from node path
function nodeToCoord(nodeId: string): string {
    // Walk from root to find coordinate
    const parts: number[] = [];
    let current = nodeId;

    // Find parent chain
    while (current !== 'root') {
        // Find which node has this as a child
        for (const [, node] of space.nodes) {
            const idx = node.children.indexOf(current);
            if (idx >= 0) {
                parts.unshift(idx + 1); // 1-indexed
                current = node.id;
                break;
            }
        }
    }
    return parts.join('.');
}

// Example tweet configs
const configs = [
    {
        name: "Provocative Question + Bold Declarative + Data Trend + Think Reconsider + Authoritative Expert + Founders Growth + StandAlone",
        components: ['Provocative', 'Declarative', 'Trend', 'Reconsider', 'Expert', 'Growth', 'StandAlone'],
    },
    {
        name: "Contrarian HotTake + Nuanced Conditional + Personal Experience + Engage Reply + Casual Friend + Developers Senior + OneLiner",
        components: ['HotTake', 'Conditional', 'Experience', 'Reply', 'Friend', 'Senior', 'OneLiner'],
    },
    {
        name: "Story MicroNarrative + Observational Pattern + Social Example + Follow Save + Playful Witty + General Curious + ThreadOpener",
        components: ['MicroNarrative', 'Pattern', 'Example', 'Save', 'Witty', 'Curious', 'ThreadOpener'],
    },
];

for (const config of configs) {
    console.log(`\n  📝 ${config.name}`);
    const coords: string[] = [];
    for (const label of config.components) {
        const nodeId = findPath(label);
        if (nodeId) {
            const coord = nodeToCoord(nodeId);
            const real = coordToReal(coord);
            coords.push(coord);
            console.log(`     ${label.padEnd(20)} → coordinate ${coord.padEnd(10)} → real 0.${encodeDot(coord)}`);
        }
    }
    console.log(`     COMBINED: [${coords.join(', ')}]`);
}

// Combinatorial count
const hookCount = 4 * 3;  // ~3 subtypes per hook type (some have 4)
const claimCount = 3 * 3;
const evidCount = 3 * 3;
const ctaCount = 4 * 3;
const toneCount = 4 * 3;
const audCount = 3 * 3;
const fmtCount = 3;

const total = hookCount * claimCount * evidCount * ctaCount * toneCount * audCount * fmtCount;

console.log('\n═══════════════════════════════════════════════════════');
console.log('📊 CONFIGURATION SPACE SIZE');
console.log('═══════════════════════════════════════════════════════');
console.log(`   Hook variants:     ${hookCount} (4 types × ~3 subtypes)`);
console.log(`   Claim variants:    ${claimCount} (3 types × 3 subtypes)`);
console.log(`   Evidence variants: ${evidCount} (3 types × 3 subtypes)`);
console.log(`   CTA variants:     ${ctaCount} (4 types × 3 subtypes)`);
console.log(`   Tone variants:    ${toneCount} (4 types × 3 subtypes)`);
console.log(`   Audience variants: ${audCount} (3 types × 3 subtypes)`);
console.log(`   Format variants:  ${fmtCount}`);
console.log(`   ─────────────────────────────────────────────`);
console.log(`   TOTAL CONFIGS:    ${total.toLocaleString()} unique tweets`);
console.log(`   Each one is a unique real number in [0, 1)`);
console.log();
