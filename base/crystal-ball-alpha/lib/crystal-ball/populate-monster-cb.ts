#!/usr/bin/env npx tsx
/**
 * populate-monster-cb.ts — Full Monster → UARL → CB pipeline
 *
 * Parses the entire Monster LMFDB ontology, aligns through UARL,
 * and populates a Crystal Ball space via the engine.
 */

import * as fs from 'fs';
import * as path from 'path';
import { parseTTL, alignTriples, emitCBNodes, printAlignmentSummary, type CBEmission } from './uarl-aligner';
import { createRegistry, addSpace, addNode, getSpace, saveToDisk, type Registry, type SpaceName } from './index';

const ttlPath = path.join(__dirname, 'monster-data', 'lmfdb_monster_ontology.ttl');
const ttl = fs.readFileSync(ttlPath, 'utf-8');

console.log('\n🐙 Full Monster → UARL → CB Pipeline');
console.log('═══════════════════════════════════════\n');

// ── Phase 1: Parse & Align ───────────────────────────────────────
const triples = parseTTL(ttl);
const aligned = alignTriples(triples);
const emissions = emitCBNodes(aligned);

console.log(printAlignmentSummary(triples, aligned, emissions));

// ── Phase 2: Build CB Space ──────────────────────────────────────

// Load existing registry
const reg = createRegistry();
// Load existing data if available
const dataDir = path.join(__dirname, '..', '..', 'data');
if (fs.existsSync(path.join(dataDir, 'registry.json'))) {
    const { loadFromDisk } = require('./persistence');
    loadFromDisk(reg, dataDir);
}

const SPACE_NAME = 'MonsterUARL' as SpaceName;

// Create space (or get existing)
let space = getSpace(reg, SPACE_NAME);
if (!space) {
    addSpace(reg, SPACE_NAME);
    space = getSpace(reg, SPACE_NAME)!;
    console.log(`\n✅ Created space: ${SPACE_NAME}`);
} else {
    console.log(`\n📦 Space ${SPACE_NAME} already exists, adding to it`);
}

// ── Phase 3: Organize emissions by type hierarchy ────────────────

// Group by type (parentLabel)
const typeGroups = new Map<string, CBEmission[]>();
const typeNodes = new Set<string>();

for (const e of emissions) {
    const group = e.parentLabel || '_root_types_';
    if (!typeGroups.has(group)) typeGroups.set(group, []);
    typeGroups.get(group)!.push(e);
    if (e.parentLabel) typeNodes.add(e.parentLabel);
}

console.log(`\n📊 Type hierarchy:`);
for (const [type, members] of typeGroups) {
    console.log(`  ${type}: ${members.length} entities`);
}

// ── Phase 4: Add UARL categories as top-level children ───────────
// Structure: root → [is_a, part_of, embodies, manifests, reifies, programs]
// Under each: the type nodes, under those: the instances

const uarlCategories = ['is_a', 'part_of', 'embodies', 'manifests', 'reifies', 'programs'];
for (const cat of uarlCategories) {
    try { addNode(space, 'root', cat); } catch { /* may exist */ }
}

// Add type nodes under is_a
const typeNodesByStratum = new Map<string, CBEmission[]>();
for (const e of emissions) {
    if (typeNodes.has(e.label)) {
        const s = e.stratum;
        if (!typeNodesByStratum.has(s)) typeNodesByStratum.set(s, []);
        typeNodesByStratum.get(s)!.push(e);
    }
}

// Add type hierarchy under is_a
const addedNodes = new Set<string>();
let nodesCreated = 0;

// First: add type nodes as children of "is_a" category
for (const e of emissions) {
    if (typeNodes.has(e.label) && !addedNodes.has(e.label)) {
        try {
            addNode(space, 'is_a', e.label);
            addedNodes.add(e.label);
            nodesCreated++;
        } catch { /* exists */ }
    }
}

// Second: add instances under their type nodes
for (const e of emissions) {
    if (!typeNodes.has(e.label) && !addedNodes.has(e.label)) {
        const parent = e.parentLabel && addedNodes.has(e.parentLabel)
            ? e.parentLabel
            : e.via;  // fallback: add under the UARL category
        try {
            addNode(space, parent, e.label);
            addedNodes.add(e.label);
            nodesCreated++;
        } catch { /* exists */ }
    }
}

// ── Phase 5: Add property nodes under manifests/programs ─────────
// For each entity, add its aligned properties as leaf nodes

for (const a of aligned) {
    if (a.uarlPredicate === 'manifests' || a.uarlPredicate === 'programs') {
        const subj = a.subject.replace(/^[^:]+:/, '')
            .replace(/[^a-zA-Z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
        const pred = a.original.predicate.replace(/^[^:]+:/, '');
        const obj = String(a.object).substring(0, 30); // truncate values
        const label = `${subj}_${pred}_${obj}`.replace(/[^a-zA-Z0-9_]/g, '_').substring(0, 60);

        if (!addedNodes.has(label)) {
            try {
                addNode(space, a.uarlPredicate, label);
                addedNodes.add(label);
                nodesCreated++;
            } catch { /* exists */ }
        }
    }
}

console.log(`\n✅ Created ${nodesCreated} nodes in ${SPACE_NAME}`);

// ── Phase 6: Save ────────────────────────────────────────────────
try {
    const { saveToDisk } = require('./persistence');
    saveToDisk(reg, dataDir);
    console.log(`💾 Saved to ${dataDir}`);
} catch (e) {
    console.log(`⚠️  Could not save: ${e}`);
}

// ── Phase 7: Summary ─────────────────────────────────────────────
const finalSpace = getSpace(reg, SPACE_NAME)!;
console.log(`\n📊 Final Monster UARL Space:`);
console.log(`  Total nodes:    ${finalSpace.nodes.size}`);
console.log(`  Root children:  ${finalSpace.nodes.get('root')?.children.length}`);

// Show tree structure
const rootNode = finalSpace.nodes.get('root')!;
for (const childId of rootNode.children) {
    const child = finalSpace.nodes.get(childId);
    if (child) {
        console.log(`  ${childId}: ${child.label} [${child.children.length} children]`);
        for (const grandId of child.children.slice(0, 5)) {
            const grand = finalSpace.nodes.get(grandId);
            if (grand) {
                console.log(`    ${grandId}: ${grand.label} [${grand.children.length}]`);
            }
        }
        if (child.children.length > 5) {
            console.log(`    ... and ${child.children.length - 5} more`);
        }
    }
}

// youknow() statements for validation
console.log(`\n📋 youknow() validation statements (${emissions.length} total):`);
for (const e of emissions.slice(0, 10)) {
    console.log(`  ${e.youknowStatement}`);
}
console.log(`  ... and ${Math.max(0, emissions.length - 10)} more`);

console.log('\n═══════════════════════════════════════\n');
