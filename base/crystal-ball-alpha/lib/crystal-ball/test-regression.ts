/**
 * Crystal Ball Regression Test Suite
 * 
 * Tests core coordinate mechanics, scry token resolution, and mine path enumeration.
 * Run with: npx tsx lib/crystal-ball/test-regression.ts
 */

import {
    createRegistry,
    createSpace,
    addNode,
    setSlotCount,
    lockNode,
    parseCoordinate,
    scry,
    computeSpaceHeat,
    isKernelComplete,
    encodeDot,
    decodeDot,
    coordToReal,
    type Registry,
    type Space,
    type CBNode,
} from './index';

import { computeMinePlane, encodeFullCoordinate, fullCoordToReal, mine, declareMineSpace, projectKernel, type KnownPoint } from './mine';

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

function assertThrows(fn: () => void, message: string): void {
    try {
        fn();
        console.log(`  ❌ FAIL (no throw): ${message}`);
        failed++;
    } catch {
        console.log(`  ✅ ${message}`);
        passed++;
    }
}

// Helper: create a BARE space with no default strata (for clean testing)
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
// TEST 1: parseCoordinate — token stream
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 1: parseCoordinate ═══');

{
    const p1 = parseCoordinate('1.2.3');
    assert(p1.levels.length === 3, '"1.2.3" → 3 levels');
    assert(p1.levels[0].tokens[0].type === 'select' && p1.levels[0].tokens[0].value === 1, 'Level 0: select 1');
    assert(p1.levels[1].tokens[0].type === 'select' && p1.levels[1].tokens[0].value === 2, 'Level 1: select 2');
    assert(p1.levels[2].tokens[0].type === 'select' && p1.levels[2].tokens[0].value === 3, 'Level 2: select 3');
    assert(p1.segments[0] === 1, 'Backward compat: segment 0 = 1');
}

{
    const p2 = parseCoordinate('0');
    assert(p2.levels.length === 1, '"0" → 1 level');
    assert(p2.levels[0].tokens[0].type === 'superposition', 'Token is superposition');
}

{
    const p3 = parseCoordinate('1.991');
    assert(p3.levels.length === 2, '"1.991" → 2 levels');
    const lastToken = p3.levels[1].tokens[p3.levels[1].tokens.length - 1];
    assert(lastToken.type === 'select' && lastToken.value === 15, '991 wraps to select 15');
}

{
    const p4 = parseCoordinate('1.28312');
    assert(p4.levels.length === 2, '"1.28312" → 2 levels');
    const tokens = p4.levels[1].tokens;
    assert(tokens.length >= 2, 'Level 1 has multiple tokens');
    assert(tokens.some(t => t.type === 'drill'), 'Contains drill token');
}

{
    // 18288 = select 1, drill(8), select 2, close_drill(88)
    const p5 = parseCoordinate('18288');
    assert(p5.levels.length === 1, '"18288" → 1 level');
    const tokens = p5.levels[0].tokens;
    assert(tokens.some(t => t.type === 'drill'), 'Has drill token');
    assert(tokens.some(t => t.type === 'close_drill'), 'Has close_drill token');
}

// ═══════════════════════════════════════════════════════════
// TEST 2: scry — basic coordinate resolution
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 2: scry — basic ═══');

{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'ScryBasic');

    addNode(space, 'root', 'Alpha');
    addNode(space, 'root', 'Beta');
    addNode(space, 'root', 'Gamma');

    // Scry coordinate 1 → Alpha
    const r1 = scry(reg, 'ScryBasic', '1');
    assert(r1.resolved.length === 1, 'Scry "1" → 1 node');
    assert(r1.resolved[0].label === 'Alpha', 'Scry "1" → Alpha');
    assert(r1.unresolvedZeros === 0, 'No unresolved zeros');

    // Scry 2 → Beta
    const r2 = scry(reg, 'ScryBasic', '2');
    assert(r2.resolved[0].label === 'Beta', 'Scry "2" → Beta');

    // Scry 0 → wildcard all 3
    const r0 = scry(reg, 'ScryBasic', '0');
    assert(r0.resolved.length === 3, 'Scry "0" → all 3');
    assert(r0.unresolvedZeros === 1, 'One unresolved zero');
    assert(r0.slots.length === 1, 'One generation slot');

    // Out of range → throw
    assertThrows(() => scry(reg, 'ScryBasic', '5'), 'Scry "5" out of range throws');
}

// ═══════════════════════════════════════════════════════════
// TEST 3: scry — multi-level (same space)
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 3: scry — multi-level ═══');

{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'ScryMulti');

    // root → [A, B], A → [A1, A2], B → [B1]
    const nodeA = addNode(space, 'root', 'A');
    const nodeB = addNode(space, 'root', 'B');
    addNode(space, nodeA.id, 'A1');
    addNode(space, nodeA.id, 'A2');
    addNode(space, nodeB.id, 'B1');

    const r1 = scry(reg, 'ScryMulti', '1');
    assert(r1.resolved[0].label === 'A', 'Scry "1" → A');

    // "1.1" — A has children, so next level resolves within same space using subView
    const r11 = scry(reg, 'ScryMulti', '1.1');
    const deepest11 = r11.resolved[r11.resolved.length - 1];
    assert(deepest11.label === 'A1', 'Scry "1.1" → A1');

    const r12 = scry(reg, 'ScryMulti', '1.2');
    const deepest12 = r12.resolved[r12.resolved.length - 1];
    assert(deepest12.label === 'A2', 'Scry "1.2" → A2');

    const r21 = scry(reg, 'ScryMulti', '2.1');
    const deepest21 = r21.resolved[r21.resolved.length - 1];
    assert(deepest21.label === 'B1', 'Scry "2.1" → B1');
}

// ═══════════════════════════════════════════════════════════
// TEST 4: mine — path enumeration (bare space)
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 4: mine — paths ═══');

{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'MineBasic');

    // root → [A, B, C], A → [A1, A2], B → [B1]
    const nodeA = addNode(space, 'root', 'A');
    const nodeB = addNode(space, 'root', 'B');
    addNode(space, 'root', 'C');
    addNode(space, nodeA.id, 'A1');
    addNode(space, nodeA.id, 'A2');
    addNode(space, nodeB.id, 'B1');

    const mine = computeMinePlane(reg, 'MineBasic');

    // Paths: 1(A), 2(B), 3(C), 1.1(A1), 1.2(A2), 2.1(B1) = 6
    assert(mine.totalPaths === 6, `6 paths (got ${mine.totalPaths})`);
    assert(mine.maxDepth === 2, `Max depth 2 (got ${mine.maxDepth})`);

    const coords = mine.points.map(p => p.coordinate);
    assert(coords.includes('1'), 'Path "1" exists');
    assert(coords.includes('2'), 'Path "2" exists');
    assert(coords.includes('3'), 'Path "3" exists');
    assert(coords.includes('1.1'), 'Path "1.1" exists');
    assert(coords.includes('1.2'), 'Path "1.2" exists');
    assert(coords.includes('2.1'), 'Path "2.1" exists');
}

// ═══════════════════════════════════════════════════════════
// TEST 5: mine — empty space
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 5: mine — empty ═══');

{
    const reg = createRegistry();
    createBareSpace(reg, 'Empty');

    const mine = computeMinePlane(reg, 'Empty');
    assert(mine.totalPaths === 0, `Empty → 0 paths (got ${mine.totalPaths})`);
    assert(mine.points.length === 0, 'No points in empty space');
}

// ═══════════════════════════════════════════════════════════
// TEST 6: mine — heat values
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 6: mine — heat ═══');

{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Heat');

    const nodeA = addNode(space, 'root', 'Locked');
    const nodeB = addNode(space, 'root', 'Unlocked');
    // Mark as terminal so it can lock with 0 children (EWS boundary)
    nodeA.terminal = true;
    lockNode(space, nodeA.id);

    const mine = computeMinePlane(reg, 'Heat');

    const locked = mine.points.find(p => p.label === 'Locked');
    const unlocked = mine.points.find(p => p.label === 'Unlocked');

    assert(locked !== undefined, 'Found locked point');
    assert(unlocked !== undefined, 'Found unlocked point');
    if (locked && unlocked) {
        assert(locked.heat < unlocked.heat,
            `Locked (${locked.heat}) < unlocked (${unlocked.heat})`);
    }
}

// ═══════════════════════════════════════════════════════════
// TEST 7: mine — drill navigation
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 7: mine — drill ═══');

{
    const reg = createRegistry();
    const outer = createBareSpace(reg, 'DrillOuter');
    const inner = createBareSpace(reg, 'DrillInner');

    const portal = addNode(outer, 'root', 'Portal');
    portal.producedSpace = 'DrillInner';

    addNode(inner, 'root', 'Deep_A');
    addNode(inner, 'root', 'Deep_B');

    const mine = computeMinePlane(reg, 'DrillOuter');

    // Paths: 1(Portal), 181(Deep_A via drill), 182(Deep_B via drill) = 3
    assert(mine.totalPaths === 3, `Drill: 3 paths (got ${mine.totalPaths})`);

    const coords = mine.points.map(p => p.coordinate);
    assert(coords.includes('1'), 'Portal at "1"');

    // Drill paths: "18" prefix + selection
    const drillPaths = coords.filter(c => c.startsWith('18'));
    assert(drillPaths.length === 2, `2 drill paths (got ${drillPaths.length}: ${drillPaths.join(', ')})`);
}

// ═══════════════════════════════════════════════════════════
// TEST 8: mine with full createSpace (6 strata)
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 8: mine — createSpace (no strata) ═══');

{
    const reg = createRegistry();
    const space = createSpace(reg, 'NoStrataTest');

    // createSpace NO LONGER adds strata children automatically.
    // Strata are operational roles populated by mine/lock/reify.
    const mine = computeMinePlane(reg, 'NoStrataTest');
    assert(mine.totalPaths === 0, `Empty createSpace: 0 paths (got ${mine.totalPaths})`);
    assert(space.nodes.get(space.rootId)!.children.length === 0,
        `Root has 0 children (got ${space.nodes.get(space.rootId)!.children.length})`);

    // Add some actual content
    addNode(space, 'root', 'Alpha');
    addNode(space, 'root', 'Beta');

    const mine2 = computeMinePlane(reg, 'NoStrataTest');
    assert(mine2.totalPaths === 2, `With 2 children: 2 paths (got ${mine2.totalPaths})`);
}

// ═══════════════════════════════════════════════════════════
// TEST 9: dot encoding (. → 8988)
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 9: dot encoding ═══');

{
    assert(encodeDot('1') === '1', 'No dots → unchanged');
    assert(encodeDot('1.2') === '189882', '"1.2" → "189882"');
    assert(encodeDot('1.2.3') === '18988289883', '"1.2.3" → "18988289883"');

    // Round-trip
    assert(decodeDot(encodeDot('1.2.3')) === '1.2.3', 'Round-trip "1.2.3"');
    assert(decodeDot(encodeDot('1.991')) === '1.991', 'Round-trip "1.991"');
    assert(decodeDot(encodeDot('3')) === '3', 'Round-trip "3"');

    // coordToReal
    const r1 = coordToReal('1');
    assert(r1 === 0.1, `coordToReal("1") = ${r1}`);

    const r12 = coordToReal('1.2');
    assert(r12 > 0 && r12 < 1, `coordToReal("1.2") is in (0,1): ${r12}`);

    // Different coords → different reals
    const r123 = coordToReal('1.2.3');
    const r124 = coordToReal('1.2.4');
    assert(r123 !== r124, `"1.2.3" (${r123}) ≠ "1.2.4" (${r124})`);

    // Full coordinate encoding with kernel context
    // 90[deliverable]900 + 90[spaceId]900[selection] per segment
    const full1 = encodeFullCoordinate(3, [
        { spaceId: 5, selection: 2 },
        { spaceId: 7, selection: 1 },
    ]);
    assert(full1.startsWith('903900'), `Starts with kernel header: ${full1}`);
    assert(full1.includes('905900'), `Contains space 5 selector: ${full1}`);
    assert(full1.includes('907900'), `Contains space 7 selector: ${full1}`);
    assert(full1.includes('8988'), `Contains dot encoding: ${full1}`);
    console.log(`     Full encoding: ${full1}`);

    // Two different kernels for same deliverable → different reals
    const realA = fullCoordToReal(3, [{ spaceId: 5, selection: 1 }]);
    const realB = fullCoordToReal(3, [{ spaceId: 7, selection: 1 }]);
    assert(realA !== realB,
        `Different spaces → different reals: ${realA} ≠ ${realB}`);

    // Same space, different selection → different reals
    const realC = fullCoordToReal(3, [{ spaceId: 5, selection: 1 }]);
    const realD = fullCoordToReal(3, [{ spaceId: 5, selection: 2 }]);
    assert(realC !== realD,
        `Different selections → different reals: ${realC} ≠ ${realD}`);
}

// ═══════════════════════════════════════════════════════════
// TEST 10: mine() — declare plane, project kernel
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 10: mine() ═══');

{
    const reg = createRegistry();
    const space = createBareSpace(reg, 'Kernel');

    const nodeA = addNode(space, 'root', 'A');
    const nodeB = addNode(space, 'root', 'B');
    const nodeA1 = addNode(space, nodeA.id, 'A1');
    addNode(space, nodeA.id, 'A2');
    addNode(space, nodeB.id, 'B1');
    addNode(space, nodeB.id, 'B2');
    addNode(space, nodeA1.id, 'A1a');
    addNode(space, nodeA1.id, 'A1b');

    setSlotCount(space, nodeA.id, 1);
    setSlotCount(space, nodeB.id, 1);
    setSlotCount(space, nodeA1.id, 1);
    lockNode(space, nodeA.id);
    lockNode(space, nodeB.id);
    lockNode(space, nodeA1.id);

    // mine() declares the plane and projects the kernel
    const ms = mine(reg, 'Kernel');

    assert(ms.deliverable === 'Kernel', 'Deliverable is Kernel');
    assert(ms.origin.x === 0 && ms.origin.y === 0, 'Origin is (0, 0)');
    assert(ms.projectedKernels.length === 1, '1 kernel projected');

    // VALID
    const valid = ms.known.filter((p: KnownPoint) => p.status === 'valid');
    assert(valid.length === 8, `8 valid (got ${valid.length})`);

    // Identity on diagonal
    const identity = valid.find((p: KnownPoint) => p.x === p.y);
    assert(identity !== undefined, 'Identity on diagonal');

    // ADJACENT
    const adjacent = ms.known.filter((p: KnownPoint) => p.status === 'adjacent');
    assert(adjacent.length > 0, `Has adjacent (${adjacent.length})`);

    // No overlap
    const validCoords = new Set(valid.map((p: KnownPoint) => p.coordinate));
    assert(adjacent.every((p: KnownPoint) => !validCoords.has(p.coordinate)),
        'No valid/adjacent overlap');

    console.log(`\n  📍 mineSpace "${ms.deliverable}" (plane):`);
    console.log(`     Projected: ${ms.projectedKernels.join(', ')}`);
    console.log(`     Valid (${valid.length}):`);
    for (const p of valid) {
        console.log(`       ✅ (${p.x.toFixed(6)}, ${p.y.toFixed(6)}) ← ${p.coordinate}`);
    }
    console.log(`     Adjacent (${adjacent.length}):`);
    for (const p of adjacent) {
        console.log(`       ◐ (${p.x.toFixed(6)}, ${p.y.toFixed(6)}) ← ${p.coordinate}`);
    }
}

// ═══════════════════════════════════════════════════════════
// TEST 11: mine() — the plane persists, multi-kernel projection
// ═══════════════════════════════════════════════════════════
console.log('\n═══ TEST 11: persistent plane ═══');

{
    const reg = createRegistry();

    // Kernel A: simple essay
    const spaceA = createBareSpace(reg, 'EssayV1');
    const intro = addNode(spaceA, 'root', 'Intro');
    const body = addNode(spaceA, 'root', 'Body');
    addNode(spaceA, intro.id, 'Hook');
    addNode(spaceA, intro.id, 'Context');
    // Mark leaf nodes as terminal (they're EWS boundaries)
    for (const [, node] of spaceA.nodes) {
        if (node.id !== 'root' && node.children.length === 0) {
            node.terminal = true;
        }
    }
    for (const [, node] of spaceA.nodes) {
        if (node.id !== 'root') {
            setSlotCount(spaceA, node.id, 1);
            lockNode(spaceA, node.id);
        }
    }

    // Kernel B: different essay variant
    const spaceB = createBareSpace(reg, 'EssayV2');
    addNode(spaceB, 'root', 'Opening');
    addNode(spaceB, 'root', 'Argument');
    addNode(spaceB, 'root', 'Closing');
    // Mark leaf nodes as terminal
    for (const [, node] of spaceB.nodes) {
        if (node.id !== 'root' && node.children.length === 0) {
            node.terminal = true;
        }
    }
    for (const [, node] of spaceB.nodes) {
        if (node.id !== 'root') {
            setSlotCount(spaceB, node.id, 1);
            lockNode(spaceB, node.id);
        }
    }

    // Declare ONE plane for the deliverable "Essay"
    const plane = declareMineSpace('Essay');

    // Project both kernels onto the same plane
    projectKernel(plane, reg, 'EssayV1');
    projectKernel(plane, reg, 'EssayV2');

    assert(plane.deliverable === 'Essay', 'Plane is about Essay');
    assert(plane.projectedKernels.length === 2, '2 kernels projected');

    const valid = plane.known.filter((p: KnownPoint) => p.status === 'valid');
    const adjacent = plane.known.filter((p: KnownPoint) => p.status === 'adjacent');

    // Both kernels' paths are valid
    const fromV1 = valid.filter((p: KnownPoint) => p.fromKernel === 'EssayV1');
    const fromV2 = valid.filter((p: KnownPoint) => p.fromKernel === 'EssayV2');
    assert(fromV1.length > 0, `EssayV1 contributed ${fromV1.length} valid`);
    assert(fromV2.length > 0, `EssayV2 contributed ${fromV2.length} valid`);

    console.log(`\n  📍 mineSpace "${plane.deliverable}":`);
    console.log(`     Projected: ${plane.projectedKernels.join(', ')}`);
    console.log(`     Valid: ${valid.length}, Adjacent: ${adjacent.length}`);
    console.log(`     From EssayV1: ${fromV1.length} valid`);
    console.log(`     From EssayV2: ${fromV2.length} valid`);
}

// ═══════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════
console.log('\n═══════════════════════════════════════');
console.log(`  PASSED: ${passed}`);
console.log(`  FAILED: ${failed}`);
console.log(`  TOTAL:  ${passed + failed}`);
console.log('═══════════════════════════════════════\n');

if (failed > 0) {
    process.exit(1);
}
