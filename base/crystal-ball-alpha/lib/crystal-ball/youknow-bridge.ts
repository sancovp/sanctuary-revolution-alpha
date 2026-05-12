/**
 * youknow-bridge.ts — CB ↔ YOUKNOW Integration
 *
 * YOUKNOW is an idea generator. During BLOOM, feed it labels from CB,
 * get back ideas for new nodes. Everything goes in.
 *
 * Uses the REAL youknow() compiler — ONE call does everything:
 *   - Parses statement
 *   - Runs all validators (Cat_of_Cat, HyperedgeValidator, DerivationValidator)
 *   - Checks chain completeness, ABCD, SES depth
 *   - Builds spiral (derivation chain)
 *   - Persists to SOUP or ONT (OWL + Carton mirror)
 *   - Returns string with broken chains + what's missing
 *
 * That string IS the idea list. Parse it. Done.
 */

import { execSync } from 'child_process';
import type {
    Space,
    CBNode,
    NodeId,
    Stratum,
} from './index';

// ─── Types ────────────────────────────────────────────────────────

/** Result from calling youknow() — the string response parsed into actionable parts */
export interface YKResult {
    /** Raw string from youknow() — "OK" or "You said X. Wrong because..." */
    response: string;
    /** Whether youknow() returned "OK" (entity admitted to ONT and persisted) */
    admitted: boolean;
    /** Extracted ideas for new CB nodes */
    ideas: YKIdea[];
}

/** An idea extracted from YOUKNOW's output — becomes a CB node */
export interface YKIdea {
    label: string;             // What to name the new node
    parentLabel?: string;      // Where it should go (parent label)
    relationship: string;      // is_a, part_of, etc.
    source: 'broken_chain' | 'missing_slot' | 'llm_suggest';
    raw: string;               // Original string from YOUKNOW
}

/** Result of feeding a batch of labels to YOUKNOW */
export interface YKBatchResult {
    results: YKResult[];
    allIdeas: YKIdea[];
    admitted: string[];        // Labels that reached ONT
    soup: string[];            // Labels still in SOUP
    convergenceRatio: number;  // admitted / total (1.0 = all done)
}

// ─── Core: Call youknow() ────────────────────────────────────────

/**
 * Call the REAL youknow() compiler via docker exec.
 * ONE call. Does everything. Returns the string. We parse it.
 */
export function callYouknow(statement: string): YKResult {
    const fs = require('fs');
    const os = require('os');
    const path = require('path');

    const tmpFile = path.join(os.tmpdir(), `yk_${Date.now()}.py`);
    const containerPath = `/tmp/yk_${Date.now()}.py`;

    const pythonScript = `
import sys, os
os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
os.makedirs('/tmp/heaven_data', exist_ok=True)
sys.path.insert(0, '/tmp/youknow_owl')

# ── Bootstrap UARL v4: register CB structural types into Cat_of_Cat ──
# This gives youknow() derivation chains for CB concepts at runtime.
# Cat_of_Cat source stays clean — these are loaded from v4 foundation.
from youknow_kernel.cat_of_cat import get_cat
cat = get_cat()

# Only add if not already present (idempotent)
if "CB_Concept" not in cat.entities:
    cb_types = [
        # (name, is_a, y_layer)
        ("CB_Concept",    ["Category"], "Y1"),
        ("CB_Space",      ["CB_Concept"], "Y1"),
        ("CB_Node",       ["CB_Concept"], "Y1"),
        ("CB_Coordinate", ["CB_Concept"], "Y1"),
        ("CB_Stratum",    ["CB_Concept"], "Y1"),
        ("CB_Stratum_Universal",        ["CB_Stratum"], "Y1"),
        ("CB_Stratum_Subclass",         ["CB_Stratum"], "Y2"),
        ("CB_Stratum_Instance",         ["CB_Stratum"], "Y3"),
        ("CB_Stratum_Instance_Universal",["CB_Stratum"], "Y4"),
        ("CB_Stratum_Instance_Subtype", ["CB_Stratum"], "Y5"),
        ("CB_Stratum_Instance_Instance",["CB_Stratum"], "Y6"),
        ("CB_Phase",      ["CB_Concept"], "Y1"),
        ("CB_Phase_Create",["CB_Phase"], "Y1"),
        ("CB_Phase_Bloom", ["CB_Phase"], "Y1"),
        ("CB_Phase_Fill",  ["CB_Phase"], "Y1"),
        ("CB_Phase_Lock",  ["CB_Phase"], "Y1"),
        ("CB_Phase_Mine",  ["CB_Phase"], "Y1"),
        ("CB_Kernel",     ["CB_Concept"], "Y4"),
        ("CB_Orbit",      ["CB_Concept"], "Y5"),
        ("CB_Spectrum",   ["CB_Concept"], "Y2"),
        ("CB_View",       ["CB_Concept"], "Y2"),
        ("CB_Classification", ["CB_Concept"], "Y2"),
        ("CB_Domain",     ["CB_Classification"], "Y2"),
        ("CB_Category",   ["CB_Classification"], "Y3"),
        ("CB_Instance",   ["CB_Classification"], "Y4"),
    ]
    for name, is_a, y_layer in cb_types:
        cat.add(name, is_a=is_a, y_layer=y_layer, declared_bounded=True)

# ── Monster mathematical type hierarchy ──
# The chain: MonsterGroup → SporadicGroup → FiniteSimpleGroup → Group → AlgebraicStructure → Category → Entity → Cat_of_Cat
if "AlgebraicStructure" not in cat.entities:
    monster_types = [
        # Foundation: math hierarchy
        ("AlgebraicStructure", ["Category"], "Y1"),
        ("Group",              ["AlgebraicStructure"], "Y1"),
        ("FiniteGroup",        ["Group"], "Y2"),
        ("FiniteSimpleGroup",  ["FiniteGroup"], "Y2"),
        ("SporadicGroup",      ["FiniteSimpleGroup"], "Y2"),
        ("MonsterGroup",       ["SporadicGroup"], "Y3"),
        # Structural types from LMFDB
        ("MonsterObject",      ["Category"], "Y3"),
        ("MonsterPrime",       ["MonsterObject"], "Y3"),
        ("MonsterCollection",  ["MonsterObject"], "Y3"),
        ("MonsterConductor",   ["MonsterObject"], "Y3"),
        ("MonsterGenus",       ["MonsterObject"], "Y3"),
        ("MonsterDimension",   ["MonsterObject"], "Y4"),
        ("MonsterFieldSize",   ["MonsterObject"], "Y4"),
        ("MonsterCoefficient", ["MonsterObject"], "Y4"),
        ("MonsterEigenvalue",  ["MonsterObject"], "Y4"),
        ("MonsterDictKey",     ["MonsterObject"], "Y5"),
        ("MonsterDictValue",   ["MonsterObject"], "Y5"),
        # Properties / predicates
        ("MathProperty",       ["Category"], "Y2"),
        ("Shard",              ["MathProperty"], "Y3"),
        ("Level",              ["MathProperty"], "Y3"),
        ("Eigenvalue",         ["MathProperty"], "Y4"),
        ("Order",              ["MathProperty"], "Y1"),
        ("Proof",              ["MathProperty"], "Y6"),
        ("Factorization",      ["MathProperty"], "Y5"),
        ("SupersingularPrime", ["MathProperty"], "Y2"),
        ("LargestPrime",       ["SupersingularPrime"], "Y2"),
        # Moonshine / representation theory
        ("Representation",     ["AlgebraicStructure"], "Y2"),
        ("CharacterTable",     ["Representation"], "Y3"),
        ("ConjugacyClass",     ["AlgebraicStructure"], "Y3"),
        ("IrreducibleRep",     ["Representation"], "Y3"),
        ("JInvariant",         ["MathProperty"], "Y4"),
        ("MoonshineModule",    ["AlgebraicStructure"], "Y3"),
    ]
    for name, is_a, y_layer in monster_types:
        cat.add(name, is_a=is_a, y_layer=y_layer, declared_bounded=True)

# ── Now call the real compiler ──
from youknow_kernel.compiler import youknow
print(youknow(${JSON.stringify(statement)}))
`.trim();

    try {
        fs.writeFileSync(tmpFile, pythonScript, 'utf-8');
        execSync(`docker cp ${tmpFile} mind_of_god:${containerPath}`, { timeout: 5000 });
        fs.unlinkSync(tmpFile);

        const raw = execSync(
            `docker exec mind_of_god python3 ${containerPath} 2>&1`,
            { timeout: 60_000, encoding: 'utf-8', maxBuffer: 2 * 1024 * 1024 },
        ).trim();

        // Clean up container temp file
        try { execSync(`docker exec mind_of_god rm -f ${containerPath}`, { timeout: 3000 }); } catch { }

        // youknow() prints a single string — might have debug lines before it
        // The response is the last meaningful line
        const lines = raw.split('\n').filter(l => l.trim());
        const response = lines[lines.length - 1] || raw;

        const admitted = response.trim() === 'OK';
        const ideas = parseIdeasFromResponse(response, statement);

        return { response, admitted, ideas };

    } catch (err: any) {
        try { fs.unlinkSync(tmpFile); } catch { }
        return {
            response: `Error: ${err.message?.slice(0, 200) || 'unknown'}`,
            admitted: false,
            ideas: [],
        };
    }
}

// ─── Parse Ideas from youknow() Response ─────────────────────────

/**
 * Parse the string response from youknow() into actionable ideas.
 *
 * youknow() returns things like:
 *   "OK"
 *   "You said X is_a Y. Wrong because Z is_a ?, chain breaks at W"
 *   "SOUP: ... ABCD missing slots: mapsTo, analogicalPattern"
 *   "... llm_suggest: Try GurrenLagann_Concept is_a Anime_Ontology"
 */
function parseIdeasFromResponse(response: string, statement: string): YKIdea[] {
    if (response.trim() === 'OK') return [];

    const ideas: YKIdea[] = [];

    // Extract subject from the original statement
    const stmtMatch = statement.match(/^(\w+)\s/);
    const subject = stmtMatch ? stmtMatch[1] : 'Unknown';

    // 1. Broken is_a chains: "X is_a ?" or "X is_a ?, chain breaks"
    const chainBreaks = response.matchAll(/(\w+)\s+is_a\s+\?/g);
    for (const match of chainBreaks) {
        ideas.push({
            label: match[1],
            relationship: 'is_a',
            source: 'broken_chain',
            raw: match[0],
        });
    }

    // 2. Missing ABCD slots: "ABCD missing slots: mapsTo, analogicalPattern"
    const abcdMatch = response.match(/ABCD missing slots?:\s*([^.]+)/i);
    if (abcdMatch) {
        const slots = abcdMatch[1].split(',').map(s => s.trim()).filter(Boolean);
        for (const slot of slots) {
            ideas.push({
                label: `${subject}_${slot}`,
                parentLabel: subject,
                relationship: slot,
                source: 'missing_slot',
                raw: `ABCD missing: ${slot}`,
            });
        }
    }

    // 3. LLM suggest: "llm_suggest: Try X is_a Y" or guidance text
    const suggestMatch = response.match(/(?:llm_suggest|Try|Suggest|Missing)[:\s]+(.+?)(?:\.|$)/i);
    if (suggestMatch) {
        const suggestion = suggestMatch[1].trim();
        if (suggestion.length > 3) {
            ideas.push({
                label: suggestion.replace(/\s+/g, '_').slice(0, 60),
                relationship: 'llm_suggest',
                source: 'llm_suggest',
                raw: suggestion,
            });
        }
    }

    // 4. "chain breaks at X" → X needs definition
    const breakMatch = response.match(/chain breaks? at\s+(\w+)/i);
    if (breakMatch) {
        const breakLabel = breakMatch[1];
        if (!ideas.some(i => i.label === breakLabel)) {
            ideas.push({
                label: breakLabel,
                relationship: 'is_a',
                source: 'broken_chain',
                raw: breakMatch[0],
            });
        }
    }

    return ideas;
}

// ─── Batch: Feed a whole space to YOUKNOW ────────────────────────

/**
 * Feed all labels from a CB space to youknow().
 * Each parent-child relationship → "Child is_a Parent".
 * Returns all ideas (broken chains, missing slots, suggestions).
 */
export function feedSpaceToYouknow(space: Space): YKBatchResult {
    const results: YKResult[] = [];
    const allIdeas: YKIdea[] = [];
    const admitted: string[] = [];
    const soup: string[] = [];

    const statements = buildStatementsFromSpace(space);

    for (const stmt of statements) {
        const result = callYouknow(stmt);
        results.push(result);

        if (result.admitted) {
            admitted.push(stmt.split(' ')[0]); // subject
        } else {
            soup.push(stmt.split(' ')[0]);
            allIdeas.push(...result.ideas);
        }
    }

    // Deduplicate ideas by label
    const seen = new Set<string>();
    const uniqueIdeas = allIdeas.filter(idea => {
        if (seen.has(idea.label)) return false;
        seen.add(idea.label);
        return true;
    });

    const total = results.length;
    return {
        results,
        allIdeas: uniqueIdeas,
        admitted,
        soup,
        convergenceRatio: total > 0 ? admitted.length / total : 0,
    };
}

/**
 * Build YOUKNOW statements from a CB space's node tree.
 * Each parent-child relationship → "Child is_a Parent".
 */
export function buildStatementsFromSpace(space: Space): string[] {
    const statements: string[] = [];

    for (const [nodeId, node] of space.nodes) {
        if (nodeId === space.rootId) continue;

        // Find parent
        let parentLabel: string | null = null;
        for (const [, candidate] of space.nodes) {
            if (candidate.children.includes(nodeId)) {
                parentLabel = candidate.label;
                break;
            }
        }

        if (parentLabel && parentLabel !== 'root') {
            const subject = node.label.replace(/\s+/g, '_');
            const object = parentLabel.replace(/\s+/g, '_');
            statements.push(`${subject} is_a ${object}`);
        }
    }

    return statements;
}

// ─── Single Label Query ──────────────────────────────────────────

/**
 * Query youknow() about a single label → get ideas.
 */
export function queryLabel(
    label: string,
    parentLabel?: string,
    relationship: string = 'is_a',
): YKResult {
    const subject = label.replace(/\s+/g, '_');
    const object = (parentLabel || 'Thing').replace(/\s+/g, '_');
    return callYouknow(`${subject} ${relationship} ${object}`);
}
