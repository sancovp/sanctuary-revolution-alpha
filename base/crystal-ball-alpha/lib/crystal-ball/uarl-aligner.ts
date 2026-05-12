/**
 * uarl-aligner.ts — ANY → UARL → CB
 *
 * The universal alignment layer. Takes any ontology (RDF triples,
 * OWL classes, plain text definitions) and aligns them through
 * UARL predicates into Crystal Ball coordinates.
 *
 * UARL is the adapter — not CB, not YOUKNOW. UARL.
 *
 * Flow:
 *   ANY ontology
 *     → parse triples (subject, predicate, object)
 *     → align predicates to UARL (is_a / part_of / embodies / manifests / reifies / programs)
 *     → assign strata (Y1-Y6) based on predicate type
 *     → emit CB nodes with coordinates
 *
 * The aligner doesn't need to know what domain the ontology is from.
 * It only needs to know the UARL predicate mapping.
 */

// ── Input: ANY ontology as triples ───────────────────────────────

export interface Triple {
    subject: string;
    predicate: string;
    object: string;
    /** Original source format (ttl, owl, jsonld, text) */
    source?: string;
}

// ── UARL Predicate Alignment ─────────────────────────────────────

/** The 6 UARL predicates that everything maps to */
export type UARLPredicate =
    | 'is_a'       // taxonomy / inheritance
    | 'part_of'    // composition / mereology
    | 'embodies'   // entry point — A with B embodies C wrt D
    | 'manifests'  // pattern lattice building
    | 'reifies'    // instantiates pattern_of_is_a
    | 'programs';  // entry to Reality

/** Aligned triple — the input triple mapped to UARL */
export interface AlignedTriple {
    subject: string;
    uarlPredicate: UARLPredicate;
    object: string;
    /** Y-stratum assigned by the alignment */
    stratum: string;
    /** Confidence of the alignment (0-1) */
    confidence: number;
    /** Original triple */
    original: Triple;
}

/**
 * Predicate alignment rules.
 * Maps common RDF/OWL/domain predicates to UARL predicates.
 * This is the core of the aligner — extend this for new domains.
 */
const PREDICATE_ALIGNMENTS: Array<{
    pattern: RegExp;
    uarl: UARLPredicate;
    stratum: string;
    confidence: number;
}> = [
        // ── is_a family (taxonomy) ──
        {
            pattern: /^(rdf:type|a|is_a|rdfs:subClassOf|type|isa|instanceof)$/i,
            uarl: 'is_a', stratum: 'Y1', confidence: 1.0
        },
        {
            pattern: /^(rdfs:subPropertyOf|subtype|extends|inherits)$/i,
            uarl: 'is_a', stratum: 'Y2', confidence: 0.9
        },

        // ── part_of family (mereology) ──
        {
            pattern: /^(part_of|partOf|hasPart|has_part|contains|member|component)$/i,
            uarl: 'part_of', stratum: 'Y2', confidence: 1.0
        },
        {
            pattern: /^(rdfs:member|includes|belongs_to|within)$/i,
            uarl: 'part_of', stratum: 'Y3', confidence: 0.8
        },

        // ── embodies family (entry point, analogy, bridge) ──
        {
            pattern: /^(embodies|represents|symbolizes|analogous_to|maps_to)$/i,
            uarl: 'embodies', stratum: 'Y2', confidence: 0.9
        },
        {
            pattern: /^(rdfs:label|name|title|label)$/i,
            uarl: 'embodies', stratum: 'Y1', confidence: 0.7
        },

        // ── manifests family (pattern lattice) ──
        {
            pattern: /^(manifests|exhibits|demonstrates|shows|produces|generates)$/i,
            uarl: 'manifests', stratum: 'Y3', confidence: 0.9
        },
        {
            pattern: /^(has_property|property|attribute|value|owl:hasValue)$/i,
            uarl: 'manifests', stratum: 'Y4', confidence: 0.7
        },

        // ── reifies family (instantiation) ──
        {
            pattern: /^(reifies|instantiates|implements|realizes|concretizes)$/i,
            uarl: 'reifies', stratum: 'Y4', confidence: 1.0
        },
        {
            pattern: /^(creates|builds|constructs|makes)$/i,
            uarl: 'reifies', stratum: 'Y5', confidence: 0.6
        },

        // ── programs family (entry to Reality) ──
        {
            pattern: /^(programs|proves|verifies|validates|certifies)$/i,
            uarl: 'programs', stratum: 'Y6', confidence: 1.0
        },
        {
            pattern: /^(zk:proof|proof|witness|signature|certificate)$/i,
            uarl: 'programs', stratum: 'Y6', confidence: 0.9
        },

        // ── Domain-specific: Monster/math ──
        {
            pattern: /^(monster:shard|shard)$/i,
            uarl: 'part_of', stratum: 'Y3', confidence: 0.8
        },
        {
            pattern: /^(monster:level|level|depth)$/i,
            uarl: 'manifests', stratum: 'Y3', confidence: 0.7
        },
        {
            pattern: /^(hecke:eigenvalue|eigenvalue)$/i,
            uarl: 'manifests', stratum: 'Y4', confidence: 0.8
        },
        {
            pattern: /^(monster:order|order|cardinality|size)$/i,
            uarl: 'manifests', stratum: 'Y1', confidence: 0.9
        },
        {
            pattern: /^(monster:factorization|factorization|decomposition)$/i,
            uarl: 'manifests', stratum: 'Y5', confidence: 0.8
        },
    ];

// ── The Aligner ──────────────────────────────────────────────────

/**
 * Align a single triple to UARL.
 * Returns null if no alignment found (unknown predicate).
 */
export function alignTriple(triple: Triple): AlignedTriple | null {
    for (const rule of PREDICATE_ALIGNMENTS) {
        if (rule.pattern.test(triple.predicate)) {
            return {
                subject: triple.subject,
                uarlPredicate: rule.uarl,
                object: triple.object,
                stratum: rule.stratum,
                confidence: rule.confidence,
                original: triple,
            };
        }
    }

    // Fallback: unknown predicates → embodies at Y3 with low confidence
    return {
        subject: triple.subject,
        uarlPredicate: 'embodies',
        object: triple.object,
        stratum: 'Y3',
        confidence: 0.3,
        original: triple,
    };
}

/**
 * Align a batch of triples.
 */
export function alignTriples(triples: Triple[]): AlignedTriple[] {
    return triples.map(t => alignTriple(t)).filter((a): a is AlignedTriple => a !== null);
}

// ── CB Emission ──────────────────────────────────────────────────

/** A CB node to be created from alignment */
export interface CBEmission {
    /** Node label for CB */
    label: string;
    /** Parent label (from is_a or part_of alignment) */
    parentLabel: string | null;
    /** Suggested stratum */
    stratum: string;
    /** UARL predicate that created this node */
    via: UARLPredicate;
    /** youknow() statement to validate */
    youknowStatement: string;
}

/**
 * Convert aligned triples to CB emissions.
 * Collects all triples per entity, assigns the deepest stratum
 * based on what predicates touch it, and groups by type hierarchy.
 */
export function emitCBNodes(aligned: AlignedTriple[]): CBEmission[] {
    // Phase 1: collect entity info from all triples
    const entityInfo = new Map<string, {
        types: Set<string>;       // is_a targets
        strata: Set<string>;      // all strata touching this entity
        predicates: Set<UARLPredicate>;  // all UARL predicates
        properties: Map<string, string>; // predicate → object for manifests
    }>();

    function getOrCreate(key: string) {
        if (!entityInfo.has(key)) {
            entityInfo.set(key, {
                types: new Set(),
                strata: new Set(),
                predicates: new Set(),
                properties: new Map(),
            });
        }
        return entityInfo.get(key)!;
    }

    for (const a of aligned) {
        const subj = sanitizeLabel(a.subject);
        const obj = sanitizeLabel(a.object);
        const info = getOrCreate(subj);
        info.strata.add(a.stratum);
        info.predicates.add(a.uarlPredicate);

        if (a.uarlPredicate === 'is_a') {
            info.types.add(obj);
            getOrCreate(obj); // ensure type node exists
        } else {
            info.properties.set(a.uarlPredicate + ':' + a.original.predicate, obj);
        }
    }

    // Phase 2: determine stratum per entity
    // Priority: deepest stratum assigned by any touching predicate
    function deepestStratum(strata: Set<string>): string {
        let max = 1;
        for (const s of strata) {
            const n = parseInt(s.replace('Y', ''));
            if (n > max) max = n;
        }
        return `Y${max}`;
    }

    // Phase 3: emit CB nodes
    const emissions: CBEmission[] = [];
    for (const [label, info] of entityInfo) {
        const stratum = deepestStratum(info.strata.size > 0 ? info.strata : new Set(['Y1']));
        const parentLabel = info.types.size > 0 ? [...info.types][0] : null;
        const via = info.predicates.has('is_a') ? 'is_a' as UARLPredicate
            : info.predicates.has('programs') ? 'programs' as UARLPredicate
                : info.predicates.has('manifests') ? 'manifests' as UARLPredicate
                    : 'embodies' as UARLPredicate;

        const ykStmt = parentLabel
            ? `${label} is_a ${parentLabel}`
            : `${label} is_a Entity`;

        emissions.push({
            label,
            parentLabel,
            stratum,
            via,
            youknowStatement: ykStmt,
        });
    }

    return emissions;
}

function sanitizeLabel(s: string): string {
    // Remove URI prefixes, replace non-alphanum with _
    return s
        .replace(/^[^:]+:/, '')           // strip prefix
        .replace(/[^a-zA-Z0-9_]/g, '_')   // sanitize
        .replace(/_+/g, '_')              // collapse
        .replace(/^_|_$/g, '');           // trim
}

function lowerStratum(s: string): string {
    const num = parseInt(s.replace('Y', ''));
    return `Y${Math.max(1, num - 1)}`;
}

// ── Parsers ──────────────────────────────────────────────────────

/**
 * Parse Turtle (TTL) into triples.
 * Simple parser — handles the subset used in Monster ontology.
 */
export function parseTTL(ttl: string): Triple[] {
    const triples: Triple[] = [];
    const lines = ttl.split('\n');

    let currentSubject = '';

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('@prefix')) continue;

        // New subject line: "subject a Type ;"
        const subjectMatch = trimmed.match(/^(\S+)\s+(.+)/);
        if (subjectMatch) {
            const firstPart = subjectMatch[1];
            const rest = subjectMatch[2];

            // If it doesn't start with whitespace, it's a new subject
            if (!line.startsWith(' ') && !line.startsWith('\t')) {
                currentSubject = firstPart;
                // Parse the predicate-object pairs from rest
                parsePOPairs(currentSubject, rest, triples);
            } else {
                // Continuation line: "    predicate object ;"
                parsePOPairs(currentSubject, trimmed, triples);
            }
        }
    }

    return triples;
}

function parsePOPairs(subject: string, text: string, triples: Triple[]): void {
    // Remove trailing . or ;
    const clean = text.replace(/\s*[.;]\s*$/, '').trim();
    if (!clean) return;

    // Split on ; for multiple predicate-object pairs
    const pairs = clean.split(/\s*;\s*/);
    for (const pair of pairs) {
        const parts = pair.trim().split(/\s+/);
        if (parts.length >= 2) {
            const predicate = parts[0];
            const object = parts.slice(1).join(' ').replace(/^"(.*)"$/, '$1');
            triples.push({ subject, predicate, object, source: 'ttl' });
        }
    }
}

/**
 * Parse simple "subject predicate object" text lines into triples.
 */
export function parseTextTriples(text: string): Triple[] {
    return text.split('\n')
        .map(l => l.trim())
        .filter(l => l && !l.startsWith('#'))
        .map(line => {
            const parts = line.split(/\s+/);
            if (parts.length >= 3) {
                return {
                    subject: parts[0],
                    predicate: parts[1],
                    object: parts.slice(2).join(' '),
                    source: 'text',
                };
            }
            return null;
        })
        .filter((t): t is Triple => t !== null);
}

// ── Summary ──────────────────────────────────────────────────────

export function printAlignmentSummary(
    triples: Triple[],
    aligned: AlignedTriple[],
    emissions: CBEmission[],
): string {
    const lines: string[] = [
        '═══════════════════════════════════════════════════════════',
        '  ANY → UARL → CB  Alignment Report',
        '═══════════════════════════════════════════════════════════',
        '',
        `  Input triples:     ${triples.length}`,
        `  Aligned triples:   ${aligned.length}`,
        `  CB nodes emitted:  ${emissions.length}`,
        '',
    ];

    // UARL predicate distribution
    const byPredicate: Record<string, number> = {};
    for (const a of aligned) {
        byPredicate[a.uarlPredicate] = (byPredicate[a.uarlPredicate] || 0) + 1;
    }
    lines.push('  UARL Predicate Distribution:');
    for (const [pred, count] of Object.entries(byPredicate).sort()) {
        lines.push(`    ${pred.padEnd(12)} ${count}`);
    }

    // Stratum distribution
    const byStratum: Record<string, number> = {};
    for (const e of emissions) {
        byStratum[e.stratum] = (byStratum[e.stratum] || 0) + 1;
    }
    lines.push('');
    lines.push('  CB Stratum Distribution:');
    for (const [s, count] of Object.entries(byStratum).sort()) {
        lines.push(`    ${s.padEnd(5)} ${count} nodes`);
    }

    // Confidence distribution
    const avgConf = aligned.reduce((s, a) => s + a.confidence, 0) / aligned.length;
    const lowConf = aligned.filter(a => a.confidence < 0.5).length;
    lines.push('');
    lines.push(`  Avg confidence:    ${avgConf.toFixed(2)}`);
    lines.push(`  Low confidence:    ${lowConf} (need review)`);

    // youknow() statements
    lines.push('');
    lines.push('  youknow() statements to validate:');
    for (const e of emissions.slice(0, 20)) {
        lines.push(`    ${e.youknowStatement}`);
    }
    if (emissions.length > 20) {
        lines.push(`    ... and ${emissions.length - 20} more`);
    }

    lines.push('');
    lines.push('═══════════════════════════════════════════════════════════');
    return lines.join('\n');
}
