/**
 * demo-orbits.ts — Compute mineSpace orbits correctly
 * 
 * Orbit = all mineSpace points that have the SAME SET of global IDs
 * (kernelRefs or node labels) in ANY position.
 * 
 * Run: npx tsx lib/crystal-ball/demo-orbits.ts
 */

import {
    createRegistry,
    createKernel,
    lockKernel,
    addNode,
    addDot,
} from './index';
import { computeMinePlane, type MineResult, type MinedPoint } from './mine';

const registry = createRegistry();

// ── Build compiler with SYMMETRIC sub-kernels ────────────────

// 3-slot kernels (identical shape)
const grammarK = createKernel(registry, 'Grammar');
addNode(grammarK.space, 'root', 'Tokens');
addNode(grammarK.space, 'root', 'Rules');
addNode(grammarK.space, 'root', 'Output');
lockKernel(registry, grammarK.globalId);

const parserK = createKernel(registry, 'Parser');
addNode(parserK.space, 'root', 'Input');
addNode(parserK.space, 'root', 'Transform');
addNode(parserK.space, 'root', 'Output');
lockKernel(registry, parserK.globalId);

const scryK = createKernel(registry, 'Scry');
addNode(scryK.space, 'root', 'Coordinate');
addNode(scryK.space, 'root', 'Resolution');
addNode(scryK.space, 'root', 'Result');
lockKernel(registry, scryK.globalId);

// 2-slot kernels (identical shape)
const encoderK = createKernel(registry, 'Encoder');
addNode(encoderK.space, 'root', 'Input');
addNode(encoderK.space, 'root', 'Encoded');
lockKernel(registry, encoderK.globalId);

const lockerK = createKernel(registry, 'Locker');
addNode(lockerK.space, 'root', 'Target');
addNode(lockerK.space, 'root', 'Locked');
lockKernel(registry, lockerK.globalId);

// 4-slot kernel (unique)
const minerK = createKernel(registry, 'Miner');
addNode(minerK.space, 'root', 'LockedKernel');
addNode(minerK.space, 'root', 'Projection');
addNode(minerK.space, 'root', 'Points');
addNode(minerK.space, 'root', 'Heatmap');
lockKernel(registry, minerK.globalId);

// Compose the compiler
const compilerK = createKernel(registry, 'CB_Compiler');
const subKernels = [grammarK, parserK, scryK, encoderK, lockerK, minerK];
const slotNames = ['Grammar', 'Parser', 'Scry', 'Encoder', 'Locker', 'Miner'];
for (let i = 0; i < subKernels.length; i++) {
    const slot = addNode(compilerK.space, 'root', slotNames[i]);
    slot.kernelRef = subKernels[i].globalId;
}
lockKernel(registry, compilerK.globalId);

// ── Mine the compiler ────────────────────────────────────────

console.log('═══ MINING THE COMPILER ═══\n');
const mine = computeMinePlane(registry, compilerK.space.name);
console.log(`Total paths: ${mine.totalPaths}`);
console.log(`Max depth: ${mine.maxDepth}`);
console.log(`Kernel complete: ${mine.kernelComplete}`);

console.log('\nAll mined points:');
for (const pt of mine.points) {
    if (pt.coordinate === '0') continue; // skip origin
    console.log(`  (${pt.x.toFixed(3)}, ${pt.y.toFixed(3)}) coord=${pt.coordinate} label=${pt.label} depth=${pt.depth}`);
}

// ── Compute orbits by grouping identical label sets ──────────

interface OrbitGroup {
    canonicalKey: string;    // sorted labels
    points: MinedPoint[];
    size: number;
}

function computeOrbits(mine: MineResult, space: any): OrbitGroup[] {
    // For each point, walk the coordinate path and collect the labels
    const groups = new Map<string, MinedPoint[]>();

    for (const pt of mine.points) {
        if (pt.coordinate === '0') continue;

        // Walk the path and collect node IDs/labels at each level
        const segments = pt.coordinate.split('.');
        const ids: string[] = [];
        let currentNode = space.nodes.get(space.rootId);

        for (const seg of segments) {
            if (!currentNode) break;
            const idx = parseInt(seg, 10) - 1; // 0-indexed
            if (idx >= 0 && idx < currentNode.children.length) {
                const childId = currentNode.children[idx];
                const child = space.nodes.get(childId);
                if (child) {
                    // Use kernelRef if available, else label
                    const id = child.kernelRef !== undefined
                        ? `K#${child.kernelRef}`
                        : child.label;
                    ids.push(id);
                    currentNode = child;
                }
            }
        }

        // Sort the IDs → canonical key (unordered set)
        const canonicalKey = [...ids].sort().join('|');

        if (!groups.has(canonicalKey)) {
            groups.set(canonicalKey, []);
        }
        groups.get(canonicalKey)!.push(pt);
    }

    return Array.from(groups.entries())
        .map(([key, pts]) => ({
            canonicalKey: key,
            points: pts,
            size: pts.length,
        }))
        .sort((a, b) => b.size - a.size);
}

console.log('\n═══ MINESPACE ORBITS ═══');
console.log('(points with same unordered set of IDs = same orbit)\n');

const orbits = computeOrbits(mine, compilerK.space);
for (const orbit of orbits) {
    console.log(`Orbit [size ${orbit.size}]: ${orbit.canonicalKey}`);
    for (const pt of orbit.points) {
        console.log(`  (${pt.x.toFixed(3)}, ${pt.y.toFixed(3)}) coord=${pt.coordinate} label=${pt.label}`);
    }
}

console.log(`\nTotal orbits: ${orbits.length}`);
console.log(`Total points: ${mine.points.length - 1}`); // minus origin
console.log(`Largest orbit: ${orbits[0]?.size ?? 0}`);
console.log(`\nAutomorphism group ≈ product of S_n for each orbit of size n`);
const autParts = orbits
    .filter(o => o.size > 1)
    .map(o => `S${o.size}`);
console.log(`Aut(K) ⊇ ${autParts.length > 0 ? autParts.join(' × ') : 'trivial'}`);
