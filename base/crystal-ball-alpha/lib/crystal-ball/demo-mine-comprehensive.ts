/**
 * ═══════════════════════════════════════════════════════════
 * Episode 1: "Super Ultra Comprehensive MineSpace Test
 *             → GET TO HIGHER ORDER MINESPACE!?!?!!?"
 * ═══════════════════════════════════════════════════════════
 *
 * Three phases:
 *   Phase 1: Exhaustive mineSpace edge-case validation
 *   Phase 2: Encoding integrity (round-trip, uniqueness, markers)
 *
 * Run: npx tsx lib/crystal-ball/demo-mine-comprehensive.ts
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
    type MineSpace,
} from './mine';

import { encodeDot, decodeDot, coordToReal } from './index';

// ── Test harness ──
let passed = 0;
let failed = 0;

function assert(condition: boolean, label: string): void {
    if (condition) {
        passed++;
    } else {
        failed++;
        console.log(`   ❌ FAIL: ${label}`);
    }
}

function section(title: string) {
    console.log(`\n═══ ${title} ═══`);
}

// ── Helper: bare space (no strata) ──
function createBareSpace(reg: Registry, name: string): Space {
    const root: CBNode = {
        id: 'root',
        label: name,
        children: [],
        x: 0,
        y: 0,
    };
    const space: Space = {
        name,
        rootId: 'root',
        nodes: new Map([['root', root]]),
        dots: [],
    };
    reg.spaces.set(name, space);
    return space;
}

// ═══════════════════════════════════════════════════════════
// PHASE 1: Exhaustive MineSpace Validation
// ═══════════════════════════════════════════════════════════

console.log('\n╔═══════════════════════════════════════════════════════╗');
console.log('║   PHASE 1: Exhaustive MineSpace Validation            ║');
console.log('╚═══════════════════════════════════════════════════════╝');

// ── Test 1: Empty kernel ──
section('1.1: Empty kernel → empty mineSpace');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Empty');
    // root only, no children
    const ms = mine(reg, 'Empty');
    assert(ms.deliverable === 'Empty', 'Deliverable is Empty');
    assert(ms.known.length === 0, `Empty kernel → 0 known points (got ${ms.known.length})`);
    assert(ms.projectedKernels.length === 1, '1 kernel projected');
    console.log('  ✅ Empty kernel produces empty mineSpace');
}

// ── Test 2: Single-node kernel ──
section('1.2: Single-node kernel');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Solo');
    const only = addNode(space, 'root', 'OnlyChild');
    setSlotCount(space, only.id, 1);
    lockNode(space, only.id);

    const ms = mine(reg, 'Solo');
    const valid = ms.known.filter(p => p.status === 'valid');
    const adjacent = ms.known.filter(p => p.status === 'adjacent');

    assert(valid.length === 1, `Single node → 1 valid (got ${valid.length})`);
    assert(adjacent.length > 0, `Single node → has adjacent (got ${adjacent.length})`);
    assert(valid[0].coordinate === '1', `Coordinate is "1" (got "${valid[0].coordinate}")`);
    console.log(`  ✅ Solo: ${valid.length} valid, ${adjacent.length} adjacent`);
}

// ── Test 3: Deep chain (depth 5) ──
section('1.3: Deep chain (depth 5)');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'DeepChain');

    let parentId = 'root';
    const labels = ['L1', 'L2', 'L3', 'L4', 'L5'];
    for (const label of labels) {
        const node = addNode(space, parentId, label);
        setSlotCount(space, node.id, 1);
        lockNode(space, node.id);
        parentId = node.id;
    }

    const ms = mine(reg, 'DeepChain');
    const valid = ms.known.filter(p => p.status === 'valid');
    const maxDepth = Math.max(...valid.map(p => p.coordinate.split('.').length));

    assert(valid.length === 5, `5-deep chain → 5 valid (got ${valid.length})`);
    assert(maxDepth === 5, `Max depth is 5 (got ${maxDepth})`);

    // Verify the deepest coordinate
    const deepest = valid.find(p => p.coordinate.split('.').length === 5);
    assert(deepest !== undefined, 'Has a depth-5 point');
    assert(deepest!.coordinate === '1.1.1.1.1', `Deepest is "1.1.1.1.1" (got "${deepest!.coordinate}")`);
    console.log(`  ✅ DeepChain: ${valid.length} valid, max depth ${maxDepth}`);
}

// ── Test 4: Wide kernel (10+ siblings) ──
section('1.4: Wide kernel (10+ siblings)');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Wide');

    for (let i = 0; i < 12; i++) {
        const node = addNode(space, 'root', `Child_${i}`);
        setSlotCount(space, node.id, 1);
        lockNode(space, node.id);
    }

    const ms = mine(reg, 'Wide');
    const valid = ms.known.filter(p => p.status === 'valid');

    assert(valid.length === 12, `12 siblings → 12 valid (got ${valid.length})`);

    // Check no duplicate coordinates
    const coords = new Set(valid.map(p => p.coordinate));
    assert(coords.size === 12, `All 12 coords unique (got ${coords.size} unique)`);

    // With CB-encoded selections (1-7, 91, 92...), no IEEE collisions
    const reals = new Set(valid.map(p => p.x));
    assert(reals.size === valid.length,
        `All reals unique (got ${reals.size} unique of ${valid.length})`);

    console.log(`  ✅ Wide: ${valid.length} valid, ${coords.size} unique coords, ${reals.size} unique reals`);
}

// ── Test 5: Mixed depth ──
section('1.5: Mixed depth (some branches deep, some shallow)');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Mixed');

    // Branch A: deep (3 levels)
    const a = addNode(space, 'root', 'A');
    const a1 = addNode(space, a.id, 'A1');
    const a1x = addNode(space, a1.id, 'A1X');
    setSlotCount(space, a.id, 1); lockNode(space, a.id);
    setSlotCount(space, a1.id, 1); lockNode(space, a1.id);
    setSlotCount(space, a1x.id, 1); lockNode(space, a1x.id);

    // Branch B: shallow (1 level)
    const b = addNode(space, 'root', 'B');
    setSlotCount(space, b.id, 1); lockNode(space, b.id);

    // Branch C: medium (2 levels)
    const c = addNode(space, 'root', 'C');
    const c1 = addNode(space, c.id, 'C1');
    const c2 = addNode(space, c.id, 'C2');
    setSlotCount(space, c.id, 1); lockNode(space, c.id);
    setSlotCount(space, c1.id, 1); lockNode(space, c1.id);
    setSlotCount(space, c2.id, 1); lockNode(space, c2.id);

    const ms = mine(reg, 'Mixed');
    const valid = ms.known.filter(p => p.status === 'valid');
    const depths = valid.map(p => p.coordinate.split('.').length);
    const minDepth = Math.min(...depths);
    const maxDepthVal = Math.max(...depths);

    // 7 valid: A, A.1, A.1.1, B, C, C.1, C.2
    assert(valid.length === 7, `Mixed tree → 7 valid (got ${valid.length})`);
    assert(minDepth === 1, `Min depth 1 (got ${minDepth})`);
    assert(maxDepthVal === 3, `Max depth 3 (got ${maxDepthVal})`);
    console.log(`  ✅ Mixed: ${valid.length} valid, depths ${minDepth}-${maxDepthVal}`);
}

// ── Test 6: Multi-kernel projection (no collision) ──
section('1.6: Multi-kernel projection → no collision');
{
    const reg = createRegistry();

    // Kernel A
    const spA = createBareSpace(reg, 'KernelA');
    const a1 = addNode(spA, 'root', 'A1');
    const a2 = addNode(spA, 'root', 'A2');
    setSlotCount(spA, a1.id, 1); lockNode(spA, a1.id);
    setSlotCount(spA, a2.id, 1); lockNode(spA, a2.id);

    // Kernel B (different structure)
    const spB = createBareSpace(reg, 'KernelB');
    const b1 = addNode(spB, 'root', 'B1');
    const b2 = addNode(spB, 'root', 'B2');
    const b3 = addNode(spB, 'root', 'B3');
    setSlotCount(spB, b1.id, 1); lockNode(spB, b1.id);
    setSlotCount(spB, b2.id, 1); lockNode(spB, b2.id);
    setSlotCount(spB, b3.id, 1); lockNode(spB, b3.id);

    // Project both onto same plane
    const ms = declareMineSpace('Shared');
    projectKernel(ms, reg, 'KernelA');
    projectKernel(ms, reg, 'KernelB');

    const valid = ms.known.filter(p => p.status === 'valid');
    const fromA = valid.filter(p => p.fromKernel === 'KernelA');
    const fromB = valid.filter(p => p.fromKernel === 'KernelB');

    assert(ms.projectedKernels.length === 2, '2 kernels projected');
    assert(fromA.length === 2, `KernelA contributed 2 valid (got ${fromA.length})`);
    assert(fromB.length === 3, `KernelB contributed 3 valid (got ${fromB.length})`);
    assert(valid.length === 5, `Total valid = 5 (got ${valid.length})`);
    console.log(`  ✅ Multi-kernel: ${valid.length} valid from ${ms.projectedKernels.length} kernels`);
}

// ── Test 7: Idempotent projection ──
section('1.7: Idempotent — projecting same kernel twice → same result');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Idem');
    const n = addNode(space, 'root', 'X');
    setSlotCount(space, n.id, 1); lockNode(space, n.id);

    const ms = declareMineSpace('IdemTest');
    projectKernel(ms, reg, 'Idem');
    const countAfterFirst = ms.known.length;

    projectKernel(ms, reg, 'Idem');  // same kernel again
    const countAfterSecond = ms.known.length;

    assert(countAfterFirst === countAfterSecond,
        `Idempotent: ${countAfterFirst} after first, ${countAfterSecond} after second`);
    assert(ms.projectedKernels.length === 1, 'Only 1 projection recorded');
    console.log(`  ✅ Idempotent: ${countAfterFirst} points, unchanged after re-projection`);
}

// ── Test 8: Adjacent depth parameter ──
section('1.8: Adjacent depth parameter');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'AdjTest');
    const n1 = addNode(space, 'root', 'X');
    const n2 = addNode(space, 'root', 'Y');
    setSlotCount(space, n1.id, 1); lockNode(space, n1.id);
    setSlotCount(space, n2.id, 1); lockNode(space, n2.id);

    const ms0 = mine(reg, 'AdjTest', 'AdjTest0', 0);
    const ms2 = mine(reg, 'AdjTest', 'AdjTest2', 2);
    const ms5 = mine(reg, 'AdjTest', 'AdjTest5', 5);

    const adj0 = ms0.known.filter(p => p.status === 'adjacent').length;
    const adj2 = ms2.known.filter(p => p.status === 'adjacent').length;
    const adj5 = ms5.known.filter(p => p.status === 'adjacent').length;

    assert(adj0 === 0, `adjacentDepth=0 → 0 adjacent (got ${adj0})`);
    assert(adj2 > 0, `adjacentDepth=2 → some adjacent (got ${adj2})`);
    assert(adj5 > adj2, `adjacentDepth=5 → more adjacent than depth 2 (${adj5} > ${adj2})`);
    console.log(`  ✅ Adjacent depth: 0→${adj0}, 2→${adj2}, 5→${adj5}`);
}

// ═══════════════════════════════════════════════════════════
// PHASE 2: Encoding Integrity
// ═══════════════════════════════════════════════════════════

console.log('\n╔═══════════════════════════════════════════════════════╗');
console.log('║   PHASE 2: Encoding Integrity                        ║');
console.log('╚═══════════════════════════════════════════════════════╝');

// ── Test 9: Round-trip encoding ──
section('2.1: Round-trip encoding on all valid points');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'RoundTrip');

    // Build a medium-depth kernel
    const a = addNode(space, 'root', 'A');
    const a1 = addNode(space, a.id, 'A1');
    const a2 = addNode(space, a.id, 'A2');
    const b = addNode(space, 'root', 'B');
    const b1 = addNode(space, b.id, 'B1');
    for (const id of [a.id, a1.id, a2.id, b.id, b1.id]) {
        setSlotCount(space, id, 1); lockNode(space, id);
    }

    const ms = mine(reg, 'RoundTrip');
    const valid = ms.known.filter(p => p.status === 'valid');

    let allRoundTrip = true;
    for (const p of valid) {
        const encoded = encodeDot(p.coordinate);
        const decoded = decodeDot(encoded);
        if (decoded !== p.coordinate) {
            allRoundTrip = false;
            console.log(`   ❌ Round-trip failed: "${p.coordinate}" → "${encoded}" → "${decoded}"`);
        }
    }
    assert(allRoundTrip, `All ${valid.length} valid points round-trip through encode/decode`);
    console.log(`  ✅ ${valid.length} coordinates round-trip perfectly`);
}

// ── Test 10: All reals unique ──
section('2.2: All valid reals are unique (no collisions)');
{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Unique');

    // Build a wider kernel with depth
    for (let i = 0; i < 5; i++) {
        const parent = addNode(space, 'root', `P${i}`);
        setSlotCount(space, parent.id, 1); lockNode(space, parent.id);
        for (let j = 0; j < 3; j++) {
            const child = addNode(space, parent.id, `P${i}_C${j}`);
            setSlotCount(space, child.id, 1); lockNode(space, child.id);
        }
    }

    const ms = mine(reg, 'Unique');
    const valid = ms.known.filter(p => p.status === 'valid');
    const reals = valid.map(p => p.x);
    const uniqueReals = new Set(reals);

    assert(uniqueReals.size === reals.length,
        `All ${reals.length} reals unique (got ${uniqueReals.size} unique)`);
    console.log(`  ✅ ${reals.length} valid points → ${uniqueReals.size} unique reals`);
}

// ── Test 11: Full coordinate encoding markers ──
section('2.3: Full coordinate encoding contains 90/900 markers');
{
    const enc1 = encodeFullCoordinate(1, [
        { spaceId: 2, selection: 3 },
        { spaceId: 4, selection: 1 },
    ]);

    assert(enc1.includes('901900'), 'Contains deliverable marker 901900');
    assert(enc1.includes('902900'), 'Contains space 2 marker');
    assert(enc1.includes('904900'), 'Contains space 4 marker');
    assert(enc1.includes('8988'), 'Contains dot encoding');

    // Different deliverables → different prefix
    const encA = encodeFullCoordinate(1, [{ spaceId: 2, selection: 1 }]);
    const encB = encodeFullCoordinate(5, [{ spaceId: 2, selection: 1 }]);
    assert(encA !== encB, 'Different deliverable → different encoding');
    assert(encA.startsWith('901900'), 'Deliverable 1 starts with 901900');
    assert(encB.startsWith('905900'), 'Deliverable 5 starts with 905900');

    // Same deliverable, different space in segment → different real
    const realX = fullCoordToReal(1, [{ spaceId: 2, selection: 1 }]);
    const realY = fullCoordToReal(1, [{ spaceId: 3, selection: 1 }]);
    assert(realX !== realY, `Different spaces → different reals: ${realX} ≠ ${realY}`);

    console.log(`  ✅ Encoding: ${enc1}`);
    console.log(`  ✅ Markers verified, no collision across deliverables/spaces`);
}


// Phase 3 (higher-order mineSpace) will be done via the CB MCP
// interpreter, not by writing code that bypasses it.


// ═══════════════════════════════════════════════════════════
// FINAL REPORT
// ═══════════════════════════════════════════════════════════

console.log('\n═══════════════════════════════════════════════════════');
console.log(`  PASSED: ${passed}`);
console.log(`  FAILED: ${failed}`);
console.log(`  TOTAL:  ${passed + failed}`);
console.log('═══════════════════════════════════════════════════════');

if (failed > 0) {
    process.exit(1);
}
