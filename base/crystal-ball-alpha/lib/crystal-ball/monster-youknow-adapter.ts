/**
 * monster-youknow-adapter.ts — Align Monster ontology with CB/UARL
 *
 * The adapter maps Monster types → CB types → UARL predicates.
 * When YOUKNOW errors on a Monster type, we GENERATE the missing
 * CB/UARL type automatically.
 *
 * The Monster group has 194 conjugacy classes → 194×194 character table.
 * If 194 = Cat_of_Cat membership requirement, then the foundation needs
 * exactly 194 entity types to be complete. Each error generates one.
 * Convergence = all 194 filled.
 *
 * Architecture:
 *   Monster TTL types → Adapter → CB node labels → youknow() → errors
 *     → errors auto-generate missing UARL types
 *     → feed back → repeat until convergence (no new errors)
 */

// ── Monster → CB Type Adapter ────────────────────────────────────

/** A Monster type from the LMFDB ontology */
export interface MonsterType {
    /** RDF type URI, e.g. "monster:prime" */
    rdfType: string;
    /** Short name, e.g. "prime" */
    name: string;
    /** Properties this type carries */
    properties: string[];
    /** Suggested CB stratum */
    stratum: string;
    /** Y-layer mapping */
    yLayer: string;
}

/** Adapter mapping from Monster → CB → UARL */
export interface AdapterEntry {
    monster: MonsterType;
    /** CB type name, e.g. "CB_Monster_Prime" */
    cbType: string;
    /** UARL parent class */
    uarlParent: string;
    /** is_a chain: this → parent → ... → Entity → Cat_of_Cat */
    chain: string[];
}

// The known Monster types from the TTL ontology
export const MONSTER_TYPES: MonsterType[] = [
    {
        rdfType: 'monster:SporadicGroup',
        name: 'SporadicGroup',
        properties: ['order', 'largestPrime'],
        stratum: 'universal',
        yLayer: 'Y1',
    },
    {
        rdfType: 'monster:LargestPrime',
        name: 'LargestPrime',
        properties: ['value', 'exponent', 'shards'],
        stratum: 'universal',
        yLayer: 'Y1',
    },
    {
        rdfType: 'monster:prime',
        name: 'prime',
        properties: ['shard', 'level', 'eigenvalue', 'proof', 'factorization'],
        stratum: 'instance',
        yLayer: 'Y3',
    },
    {
        rdfType: 'monster:collection',
        name: 'collection',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'subclass',
        yLayer: 'Y2',
    },
    {
        rdfType: 'monster:conductor',
        name: 'conductor',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance',
        yLayer: 'Y3',
    },
    {
        rdfType: 'monster:genus',
        name: 'genus',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance',
        yLayer: 'Y3',
    },
    {
        rdfType: 'monster:dimension',
        name: 'dimension',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance_universal',
        yLayer: 'Y4',
    },
    {
        rdfType: 'monster:field_size',
        name: 'field_size',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance_instance',
        yLayer: 'Y6',
    },
    {
        rdfType: 'monster:coefficient',
        name: 'coefficient',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance_universal',
        yLayer: 'Y4',
    },
    {
        rdfType: 'monster:eigenvalue',
        name: 'eigenvalue',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance_universal',
        yLayer: 'Y4',
    },
    {
        rdfType: 'monster:dict_key',
        name: 'dict_key',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance_instance',
        yLayer: 'Y6',
    },
    {
        rdfType: 'monster:dict_value',
        name: 'dict_value',
        properties: ['shard', 'level', 'eigenvalue', 'proof'],
        stratum: 'instance_instance',
        yLayer: 'Y6',
    },
];

// ── Build Adapter Entries ────────────────────────────────────────

/**
 * Build the adapter set: Monster type → CB type → UARL chain.
 * Each Monster type gets a CB_ prefixed name and an is_a chain
 * through the CB hierarchy to Entity.
 */
export function buildAdapterSet(): AdapterEntry[] {
    return MONSTER_TYPES.map(m => {
        const cbType = `CB_Monster_${capitalize(m.name)}`;
        // Chain: Monster type → CB_Monster → CB_Concept → Entity
        const chain = [cbType, 'CB_Monster', 'CB_Concept', 'Entity'];

        return {
            monster: m,
            cbType,
            uarlParent: 'CB_Monster',
            chain,
        };
    });
}

function capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

// ── Generate YOUKNOW Statements ──────────────────────────────────

/**
 * Generate youknow() statements from the adapter set.
 * Each adapter entry becomes: "CB_Monster_Prime is_a CB_Monster"
 * Plus the Monster → math domain statements from the TTL.
 */
export function generateStatements(adapter: AdapterEntry[]): string[] {
    const stmts: string[] = [];

    // 1. Foundation chain: CB_Monster is_a CB_Concept
    stmts.push('CB_Monster is_a CB_Concept');

    // 2. Each Monster type → CB parent
    for (const entry of adapter) {
        stmts.push(`${entry.cbType} is_a ${entry.uarlParent}`);
    }

    // 3. Math domain cross-references from the Griess mapping
    // The 15 supersingular primes → CB slots
    const supersingularPrimes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 41, 47, 59, 71];
    for (let i = 0; i < supersingularPrimes.length; i++) {
        stmts.push(`CB_Slot_${i} is_a CB_Monster_Prime`);
        stmts.push(`SupersingularPrime_${supersingularPrimes[i]} is_a CB_Monster_LargestPrime`);
    }

    // 4. Moonshine relations
    stmts.push('Moonshine_j_invariant is_a CB_Monster_Coefficient');
    stmts.push('McKay_relation is_a CB_Monster_Eigenvalue');
    stmts.push('Griess_algebra is_a CB_Monster_Dimension');

    // 5. Each math area from the digit decomposition
    const areas = [
        'Complex_K_theory', 'Elliptic_curves', 'Hilbert_modular_forms',
        'Siegel_modular_forms', 'Calabi_Yau_threefolds',
        'Vertex_operator_algebra', 'Generalized_moonshine',
        'String_theory', 'ADE_classification', 'Topological_modular_forms',
    ];
    for (const area of areas) {
        stmts.push(`${area} is_a CB_Monster_Collection`);
    }

    return stmts;
}

// ── Error → Auto-Generate ────────────────────────────────────────

/** A missing type discovered by YOUKNOW errors */
export interface GeneratedType {
    name: string;
    isA: string;
    source: string;  // Which error/statement generated this
    yLayer: string;
}

/**
 * Parse YOUKNOW error responses and generate missing types.
 * When youknow() says "chain breaks at X", generate X.
 * When it says "ABCD missing: mapsTo", generate the mapping.
 */
export function generateMissingTypes(
    errors: Array<{ statement: string; response: string }>,
): GeneratedType[] {
    const generated: GeneratedType[] = [];
    const seen = new Set<string>();

    for (const err of errors) {
        // Chain breaks → generate the missing parent
        const chainBreaks = err.response.matchAll(/(\w+)\s+is_a\s+\?/g);
        for (const match of chainBreaks) {
            const name = match[1];
            if (!seen.has(name)) {
                seen.add(name);
                generated.push({
                    name,
                    isA: 'CB_Concept',  // Default parent
                    source: err.statement,
                    yLayer: 'Y2',  // Default to domain level
                });
            }
        }

        // Missing ABCD slots → generate the cross-references
        const abcdMatch = err.response.match(/ABCD missing slots?:\s*([^.]+)/i);
        if (abcdMatch) {
            const slots = abcdMatch[1].split(',').map(s => s.trim());
            for (const slot of slots) {
                const stmtSubject = err.statement.split(' ')[0];
                const name = `${stmtSubject}_${slot}`;
                if (!seen.has(name)) {
                    seen.add(name);
                    generated.push({
                        name,
                        isA: stmtSubject,
                        source: `ABCD ${slot} for ${err.statement}`,
                        yLayer: 'Y3',
                    });
                }
            }
        }
    }

    return generated;
}

// ── Summary ──────────────────────────────────────────────────────

/**
 * Print adapter alignment summary.
 */
export function printAdapterSummary(adapter: AdapterEntry[]): string {
    const lines: string[] = [
        '═══════════════════════════════════════════════════════════',
        '  Monster → CB → UARL Adapter Set',
        '═══════════════════════════════════════════════════════════',
        '',
        `  Monster types:     ${MONSTER_TYPES.length}`,
        `  Adapter entries:   ${adapter.length}`,
        `  Target (194×194):  194 conjugacy classes`,
        '',
        '  Type Mapping:',
    ];

    for (const entry of adapter) {
        lines.push(`    ${entry.monster.rdfType.padEnd(25)} → ${entry.cbType.padEnd(25)} → ${entry.chain.join(' → ')}`);
    }

    lines.push('');
    lines.push('  Y-Layer Distribution:');
    const byLayer: Record<string, number> = {};
    for (const entry of adapter) {
        byLayer[entry.monster.yLayer] = (byLayer[entry.monster.yLayer] || 0) + 1;
    }
    for (const [layer, count] of Object.entries(byLayer).sort()) {
        lines.push(`    ${layer}: ${count} types`);
    }

    lines.push('═══════════════════════════════════════════════════════════');
    return lines.join('\n');
}
