/**
 * demo-kernelspace.ts — Test KernelSpace architecture
 * 
 * Run: npx tsx lib/crystal-ball/demo-kernelspace.ts
 */

import {
    createRegistry,
    createKernel,
    getKernel,
    listKernels,
    lockKernel,
    addNode,
    fullCoordinate,
    parseFullCoordinate,
    coordToReal,
    kernelPosition,
} from './index';

// ── Create Registry ──────────────────────────────────────────
const registry = createRegistry();

// ── Create Kernels (backwards, need-driven) ──────────────────

// Start: "I want to make a tweet"
// Need: Tone → create Tone kernel first
const toneKernel = createKernel(registry, 'Tone');
console.log(`Created Tone kernel #${toneKernel.globalId}`);

// Define Tone's internal structure
const mood = addNode(toneKernel.space, 'root', 'Mood');
addNode(toneKernel.space, mood.id, 'Friendly');
addNode(toneKernel.space, mood.id, 'Formal');
addNode(toneKernel.space, mood.id, 'Emotional');

// Tone has no sub-kernels, so we can lock it
const toneLock = lockKernel(registry, toneKernel.globalId);
console.log(`Lock Tone: ${toneLock.success ? '🔒 LOCKED' : '❌ FAILED'}`);

// Need: Hook → create Hook kernel
const hookKernel = createKernel(registry, 'Hook');
console.log(`Created Hook kernel #${hookKernel.globalId}`);

const hookType = addNode(hookKernel.space, 'root', 'HookType');
addNode(hookKernel.space, hookType.id, 'OpenQuestion');
addNode(hookKernel.space, hookType.id, 'ShockingStat');

const hookLock = lockKernel(registry, hookKernel.globalId);
console.log(`Lock Hook: ${hookLock.success ? '🔒 LOCKED' : '❌ FAILED'}`);

// Need: Body → create Body kernel
const bodyKernel = createKernel(registry, 'Body');
console.log(`Created Body kernel #${bodyKernel.globalId}`);

const bodyLen = addNode(bodyKernel.space, 'root', 'Length');

const bodyLock = lockKernel(registry, bodyKernel.globalId);
console.log(`Lock Body: ${bodyLock.success ? '🔒 LOCKED' : '❌ FAILED'}`);

// NOW: create Tweet kernel with sub-kernel slots
const tweetKernel = createKernel(registry, 'Tweet');
console.log(`\nCreated Tweet kernel #${tweetKernel.globalId}`);

// Add slots that reference sub-kernels
const toneSlot = addNode(tweetKernel.space, 'root', 'ToneSlot');
const hookSlot = addNode(tweetKernel.space, 'root', 'HookSlot');
const bodySlot = addNode(tweetKernel.space, 'root', 'BodySlot');

// Link slots to sub-kernels
toneSlot.kernelRef = toneKernel.globalId;
hookSlot.kernelRef = hookKernel.globalId;
bodySlot.kernelRef = bodyKernel.globalId;

// Try locking Tweet — should succeed because all sub-kernels are locked
const tweetLock = lockKernel(registry, tweetKernel.globalId);
console.log(`Lock Tweet: ${tweetLock.success ? '🔒 LOCKED' : '❌ FAILED'}`);

// ── Show All Kernels ─────────────────────────────────────────
console.log('\n═══ ALL KERNELS ═══\n');
for (const k of listKernels(registry)) {
    const pos = kernelPosition(k.globalId);
    const status = k.locked ? '🔒' : '🔓';
    const parent = k.parentKernelId ? ` (sub of #${k.parentKernelId})` : '';
    console.log(`#${k.globalId} ${status} ${k.space.name.padEnd(20)} pos=${pos.toFixed(8)}${parent}`);
}

// ── Full Coordinates ─────────────────────────────────────────
console.log('\n═══ FULL COORDINATES ═══\n');

// Local coordinate "7.1" within Tone kernel #1
const fullTone = fullCoordinate(toneKernel.globalId, '7.1');
console.log(`Tone/Friendly: ${fullTone}`);
console.log(`  → real: ${coordToReal(fullTone).toFixed(12)}`);

// Local coordinate "7.1" within Hook kernel #2
const fullHook = fullCoordinate(hookKernel.globalId, '7.1');
console.log(`Hook/OpenQ:    ${fullHook}`);
console.log(`  → real: ${coordToReal(fullHook).toFixed(12)}`);

// Same local coord, different kernels → DIFFERENT reals!
console.log(`\n  Same local "7.1" but different kernels:`);
console.log(`    Tone real: ${coordToReal(fullTone).toFixed(12)}`);
console.log(`    Hook real: ${coordToReal(fullHook).toFixed(12)}`);
console.log(`    Difference shows kernel identity is encoded!`);

// Parse full coordinates back
console.log('\n═══ PARSING FULL COORDINATES ═══\n');
const parsed = parseFullCoordinate(fullTone);
if (parsed) {
    console.log(`Parsed: kernelId=${parsed.kernelId}, localCoord=${parsed.localCoord}`);
    const kernel = getKernel(registry, parsed.kernelId);
    console.log(`  → Kernel: ${kernel.space.name} (${kernel.locked ? 'locked' : 'unlocked'})`);
}

// ── Test Recursive Lock Failure ──────────────────────────────
console.log('\n═══ RECURSIVE LOCK TEST ═══\n');
const outerKernel = createKernel(registry, 'Outer');
const slot1 = addNode(outerKernel.space, 'root', 'Slot1');

// Create a sub-kernel but DON'T lock it
const innerKernel = createKernel(registry, 'Inner');
slot1.kernelRef = innerKernel.globalId;

// Try locking outer — should fail because inner isn't locked
const outerLock = lockKernel(registry, outerKernel.globalId);
console.log(`Lock Outer (inner unlocked): ${outerLock.success ? '🔒 LOCKED' : '❌ FAILED'}`);
if (!outerLock.success) {
    console.log(`  Unlocked slots: ${outerLock.unlockedSlots.map(s => `${s.label} (${s.nodeId})`).join(', ')}`);
}

// Now lock inner and try again
lockKernel(registry, innerKernel.globalId);
const outerLock2 = lockKernel(registry, outerKernel.globalId);
console.log(`Lock Outer (inner locked):   ${outerLock2.success ? '🔒 LOCKED' : '❌ FAILED'}`);

// ── Global MineSpace Positions ───────────────────────────────
console.log('\n═══ GLOBAL MINESPACE POSITIONS ═══\n');
console.log('All locked kernels on one plane:\n');
for (const k of listKernels(registry)) {
    if (k.locked) {
        const pos = kernelPosition(k.globalId);
        const bar = '█'.repeat(Math.round(pos * 100));
        console.log(`  #${k.globalId} ${k.space.name.padEnd(20)} ${pos.toFixed(8)} ${bar}`);
    }
}
