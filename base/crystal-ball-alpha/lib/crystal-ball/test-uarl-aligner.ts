#!/usr/bin/env npx tsx
/**
 * test-uarl-aligner.ts — Run the ANY → UARL → CB aligner
 * on the real Monster ontology TTL.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
    parseTTL,
    alignTriples,
    emitCBNodes,
    printAlignmentSummary,
} from './uarl-aligner';

const ttlPath = path.join(__dirname, 'monster-data', 'lmfdb_monster_ontology.ttl');
const ttl = fs.readFileSync(ttlPath, 'utf-8');

console.log('\n🔮 ANY → UARL → CB Aligner');
console.log('   Input: Monster LMFDB Ontology (TTL)\n');

// 1. Parse
const triples = parseTTL(ttl);
console.log(`Parsed ${triples.length} triples from TTL\n`);

// Show first 10 raw triples
console.log('Sample triples:');
for (const t of triples.slice(0, 10)) {
    console.log(`  ${t.subject}  ${t.predicate}  ${t.object}`);
}
console.log('');

// 2. Align
const aligned = alignTriples(triples);

// 3. Emit CB nodes
const emissions = emitCBNodes(aligned);

// 4. Report
console.log(printAlignmentSummary(triples, aligned, emissions));
