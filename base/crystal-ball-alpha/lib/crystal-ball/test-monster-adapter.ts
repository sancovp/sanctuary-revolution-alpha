#!/usr/bin/env npx tsx
/**
 * test-monster-adapter.ts — Run the Monster→CB→UARL adapter
 *
 * 1. Build the adapter set
 * 2. Generate youknow() statements
 * 3. Feed each through callYouknow()
 * 4. Collect errors → auto-generate missing types
 * 5. Report coverage toward 194×194
 */

import {
    buildAdapterSet,
    generateStatements,
    generateMissingTypes,
    printAdapterSummary,
    type GeneratedType,
} from './monster-youknow-adapter';
import { callYouknow, type YKResult } from './youknow-bridge';

console.log('\n🐙 Monster → CB → YOUKNOW Adapter Test');
console.log('═══════════════════════════════════════\n');

// 1. Build adapter
const adapter = buildAdapterSet();
console.log(printAdapterSummary(adapter));

// 2. Generate statements
const statements = generateStatements(adapter);
console.log(`\n📋 Generated ${statements.length} youknow() statements:\n`);
for (const s of statements) {
    console.log(`  ${s}`);
}

// 3. Feed through YOUKNOW (dry run — show what WOULD happen)
console.log('\n\n🔬 Dry Run — Simulating YOUKNOW feedback:');
console.log('  (To run live, set LIVE=1 environment variable)\n');

const isLive = process.env.LIVE === '1';
const errors: Array<{ statement: string; response: string }> = [];

if (isLive) {
    // Live mode: actually call youknow()
    for (const stmt of statements) {
        try {
            const result: YKResult = callYouknow(stmt);
            console.log(`  ${result.admitted ? '✅' : '❌'} ${stmt}`);
            console.log(`     → ${result.response.substring(0, 100)}`);
            if (!result.admitted) {
                errors.push({ statement: stmt, response: result.response });
            }
        } catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            console.log(`  ⚠️  ${stmt} → ERROR: ${msg.substring(0, 80)}`);
            errors.push({ statement: stmt, response: msg });
        }
    }
} else {
    // Dry run: simulate what WOULD error based on what's NOT in Cat_of_Cat
    const knownInCatOfCat = new Set([
        'Entity', 'Category', 'Relationship', 'Instance',
        'Pattern', 'Implementation', 'Cat_of_Cat', 'YOUKNOW',
    ]);

    for (const stmt of statements) {
        const parts = stmt.split(' is_a ');
        const child = parts[0];
        const parent = parts[1];

        if (knownInCatOfCat.has(parent)) {
            console.log(`  ✅ ${stmt}  (parent known)`);
        } else {
            console.log(`  ❌ ${stmt}  (chain breaks: ${parent} is_a ?)`);
            errors.push({
                statement: stmt,
                response: `SOUP: ${stmt}. Wrong because ${parent} is_a ?, chain breaks`,
            });
        }
    }
}

// 4. Auto-generate missing types
console.log('\n\n🏗️  Auto-Generated Missing Types:');
const generated = generateMissingTypes(errors);

if (generated.length === 0) {
    console.log('  None — all chains resolved! 🎉');
} else {
    for (const g of generated) {
        console.log(`  + ${g.name} is_a ${g.isA}  (from: ${g.source})`);
    }
}

// 5. Coverage report
console.log('\n\n📊 Coverage toward 194×194:');
const totalTypes = adapter.length + generated.length;
const coverage = (totalTypes / 194 * 100).toFixed(1);
console.log(`  Known CB types:      ${adapter.length}`);
console.log(`  Auto-generated:      ${generated.length}`);
console.log(`  Total:               ${totalTypes}`);
console.log(`  Target (194):        194`);
console.log(`  Coverage:            ${coverage}%`);
console.log(`  Remaining:           ${194 - totalTypes}`);

// Show what types would need to go into UARL v4
if (generated.length > 0) {
    console.log('\n\n📝 These need to be added to UARL v4 foundation OWL:');
    for (const g of generated) {
        console.log(`  <owl:Class rdf:about="#${g.name}">`);
        console.log(`      <rdfs:subClassOf rdf:resource="#${g.isA}"/>`);
        console.log(`  </owl:Class>`);
    }
}

console.log('\n═══════════════════════════════════════\n');
