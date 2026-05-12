#!/usr/bin/env npx tsx
/**
 * encode-monster.ts — Feed the entire Monster ontology into youknow()
 *
 * Parse the TTL → translate each triple to a UARL predicate statement
 * → call youknow() → admitted to ONT or sent to SOUP
 */

import * as fs from 'fs';
import * as path from 'path';
import { callYouknow } from './youknow-bridge';

const ttlPath = path.join(__dirname, 'monster-data', 'lmfdb_monster_ontology.ttl');
const ttl = fs.readFileSync(ttlPath, 'utf-8');

// ── Parse TTL to youknow statements ──────────────────────────────

function ttlToYouknow(ttl: string): string[] {
    const stmts: string[] = [];
    const lines = ttl.split('\n');
    let subject = '';

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('@prefix')) continue;

        // New subject
        if (!line.startsWith(' ') && !line.startsWith('\t')) {
            const m = trimmed.match(/^(\S+)/);
            if (m) subject = clean(m[1]);
        }

        // Parse predicate-object pairs
        const clean_line = trimmed.replace(/\s*[.;]\s*$/, '').trim();
        // Handle continuation lines
        const poText = line.startsWith(' ') || line.startsWith('\t')
            ? clean_line
            : clean_line.replace(/^\S+\s+/, ''); // strip subject from first line

        const pairs = poText.split(/\s*;\s*/);
        for (const pair of pairs) {
            const parts = pair.trim().split(/\s+/);
            if (parts.length < 2) continue;

            const pred = parts[0];
            const obj = parts.slice(1).join('_');

            // Map RDF predicate → UARL predicate
            const stmt = mapToUARL(subject, pred, clean(obj));
            if (stmt) stmts.push(stmt);
        }
    }

    return stmts;
}

function clean(s: string): string {
    return s
        .replace(/^[^:]+:/, '')              // strip prefix (monster:, zk:, etc.)
        .replace(/"/g, '')                    // strip quotes
        .replace(/[^a-zA-Z0-9_]/g, '_')      // sanitize
        .replace(/_+/g, '_')                  // collapse
        .replace(/^_|_$/g, '');              // trim
}

function mapToUARL(subject: string, predicate: string, object: string): string | null {
    // rdf:type / a → is_a
    if (predicate === 'a' || predicate === 'rdf:type') {
        return `${subject} is_a ${object}`;
    }
    // rdfs:label → embodies
    if (predicate === 'rdfs:label') {
        return `${subject} embodies ${object}`;
    }
    // monster:order → manifests (the order manifests the group)
    if (predicate === 'monster:order') {
        return `${subject} manifests order_${object.substring(0, 20)}`;
    }
    // monster:largestPrime → part_of
    if (predicate === 'monster:largestPrime') {
        return `${subject} part_of ${object}`;
    }
    // monster:value, exponent, shards → manifests
    if (['monster:value', 'monster:exponent', 'monster:shards'].includes(predicate)) {
        const prop = clean(predicate);
        return `${subject} manifests ${prop}_${object}`;
    }
    // monster:shard → part_of
    if (predicate === 'monster:shard') {
        return `${subject} part_of shard_${object}`;
    }
    // monster:level → manifests
    if (predicate === 'monster:level') {
        return `${subject} manifests level_${object}`;
    }
    // hecke:eigenvalue → manifests
    if (predicate === 'hecke:eigenvalue') {
        return `${subject} manifests eigenvalue_${object}`;
    }
    // zk:proof → programs (proof = entry to Reality)
    if (predicate === 'zk:proof') {
        return `${subject} programs proof_${object.substring(0, 16)}`;
    }
    // Anything else → embodies (fallback)
    return `${subject} embodies ${clean(predicate)}_${object}`;
}

// ── Run ──────────────────────────────────────────────────────────

const statements = ttlToYouknow(ttl);

console.log(`\n🐙 Encoding Monster Ontology into YOUKNOW`);
console.log(`   ${statements.length} UARL statements to process\n`);

let admitted = 0;
let souped = 0;
let errors = 0;

for (let i = 0; i < statements.length; i++) {
    const stmt = statements[i];
    try {
        const result = callYouknow(stmt);
        if (result.admitted) {
            admitted++;
            console.log(`  ✅ [${i + 1}/${statements.length}] ${stmt}`);
        } else {
            souped++;
            console.log(`  🍜 [${i + 1}/${statements.length}] ${stmt}`);
            console.log(`     → ${result.response.substring(0, 100)}`);
        }
    } catch (e) {
        errors++;
        const msg = e instanceof Error ? e.message : String(e);
        console.log(`  ❌ [${i + 1}/${statements.length}] ${stmt}`);
        console.log(`     → ${msg.substring(0, 100)}`);
    }
}

console.log(`\n═══════════════════════════════════════`);
console.log(`  ONT admitted:  ${admitted}`);
console.log(`  SOUP:          ${souped}`);
console.log(`  Errors:        ${errors}`);
console.log(`  Total:         ${statements.length}`);
console.log(`═══════════════════════════════════════\n`);
