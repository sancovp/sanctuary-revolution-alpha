/**
 * monster-bridge.ts — Bridge between meta-introspector/monster and Crystal Ball
 * 
 * The swarm is a tool you invoke ON a CB kernel.
 * This bridge reads the swarm's outputs and fills the kernel's slots.
 * 
 * Data sources:
 *   - MonsterLean/*.lean  → proven theorems (frozen nodes)
 *   - archive_org_shards/*.json → shard data with ZK proofs
 *   - *.parquet → experiment data (future: parquet reader)
 * 
 * Usage:
 *   npx tsx lib/crystal-ball/monster-bridge.ts [spaceName]
 */

import {
    type Registry,
    type Space,
    type SpaceName,
    type CBNode,
    type ProofRole,
    type FrozenByMetadata,
    createRegistry,
    createKernel,
    addNode,
    freezeNode,
    lockKernel,
} from './index';
import { computeMinePlane } from './mine';
import { exportToLean } from './lean-export';
import * as fs from 'fs';
import * as path from 'path';

// ── Data directory ──
const MONSTER_DATA_DIR = path.join(__dirname, 'monster-data');

// ── Types ──

export interface LeanTheorem {
    name: string;
    statement: string;      // The type/statement
    proofTerm: string;       // The proof term (e.g., "MonsterWalk.monster_starts_with_8080")
    sourceFile: string;      // Which .lean file
    isProven: boolean;       // true if has exact proof, false if sorry
}

export interface ShardMeta {
    content_hash: string;
    shard_id: number;
    rdf_triples: string[];
    zk_proof: string;
    compressed_size: number;
}

export interface SwarmResult {
    spaceName: string;
    nodesCreated: number;
    nodesFrozen: number;
    theorems: LeanTheorem[];
    shards: ShardMeta[];
    frozenRatio: number;
}

// ── Lean Parser ──

/**
 * Parse ProofIndex.lean to extract theorem names and proof terms.
 * Looks for patterns like:
 *   theorem <name> : <statement> := by
 *     exact <proofTerm>
 * or:
 *   theorem <name> : <statement> := by
 *     sorry
 */
export function parseLeanProofIndex(leanContent: string): LeanTheorem[] {
    const theorems: LeanTheorem[] = [];
    const lines = leanContent.split('\n');

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Match theorem declarations
        const theoremMatch = line.match(/^theorem\s+(\w+)\s*:/);
        if (!theoremMatch) continue;

        const name = theoremMatch[1];

        // Collect the full statement until `:= by`
        let statement = line.replace(/^theorem\s+\w+\s*:\s*/, '');
        let j = i + 1;
        while (j < lines.length && !lines[j].includes(':= by')) {
            statement += ' ' + lines[j].trim();
            j++;
        }
        // Remove trailing `:= by`
        statement = statement.replace(/\s*:=\s*by\s*$/, '').trim();

        // Look for the proof on the next line
        const proofLine = (j + 1 < lines.length) ? lines[j + 1]?.trim() ?? '' : '';
        const isProven = proofLine.startsWith('exact ');
        const proofTerm = isProven
            ? proofLine.replace(/^exact\s+/, '').replace(/\s*$/, '')
            : 'sorry';

        theorems.push({
            name,
            statement,
            proofTerm,
            sourceFile: 'ProofIndex.lean',
            isProven,
        });
    }

    return theorems;
}

// ── Shard Parser ──

/**
 * Read all shard meta.json files from the archive_org_shards directory.
 */
export function readShardMetas(shardDir: string): ShardMeta[] {
    const shards: ShardMeta[] = [];

    if (!fs.existsSync(shardDir)) return shards;

    const files = fs.readdirSync(shardDir)
        .filter(f => f.endsWith('_meta.json'))
        .sort();

    for (const file of files) {
        try {
            const content = fs.readFileSync(path.join(shardDir, file), 'utf-8');
            const meta: ShardMeta = JSON.parse(content);
            shards.push(meta);
        } catch {
            // Skip malformed files
        }
    }

    return shards;
}

// ── Core: Fill a kernel with swarm data ──

/**
 * Invoke the swarm on a CB kernel.
 * Reads monster-data outputs and fills the kernel's slots.
 * 
 * Strategy:
 *   1. Parse ProofIndex.lean → create theorem nodes
 *   2. Read shard metas → create shard witness nodes
 *   3. Proven theorems → frozen, experimental axioms → sorry
 *   4. Shards with ZK proofs → frozen witnesses
 */
export function fillKernelWithSwarm(
    registry: Registry,
    spaceName: SpaceName,
): SwarmResult {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    let nodesCreated = 0;
    let nodesFrozen = 0;

    // ── 1. Import Lean theorems ──
    const proofIndexPath = path.join(
        MONSTER_DATA_DIR, 'MonsterLean', 'MonsterLean', 'ProofIndex.lean'
    );

    let theorems: LeanTheorem[] = [];
    if (fs.existsSync(proofIndexPath)) {
        const leanContent = fs.readFileSync(proofIndexPath, 'utf-8');
        theorems = parseLeanProofIndex(leanContent);

        for (const thm of theorems) {
            // Create the node under root
            const node = addNode(space, space.rootId, thm.name);
            node.role = thm.isProven ? 'theorem' : 'axiom';
            node.formalType = thm.statement;
            nodesCreated++;

            if (thm.isProven) {
                freezeNode(space, node.id, {
                    surrogate: 'lean4',
                    timestamp: Date.now(),
                    reversible: false,
                    proof: thm.proofTerm,
                });
                nodesFrozen++;
            }
        }
    }

    // ── 2. Import shard witnesses ──
    const shardDir = path.join(MONSTER_DATA_DIR, 'archive_org_shards');
    const shards = readShardMetas(shardDir);

    for (const shard of shards) {
        const label = `shard_${String(shard.shard_id).padStart(2, '0')}`;
        const node = addNode(space, space.rootId, label);
        node.role = 'proof-step';
        node.formalType = `ZK_witness(${shard.content_hash.slice(0, 16)})`;
        nodesCreated++;

        // Shards with ZK proofs are frozen witnesses
        if (shard.zk_proof) {
            freezeNode(space, node.id, {
                surrogate: 'zk-proof',
                timestamp: Date.now(),
                reversible: false,
                proof: shard.zk_proof,
            });
            nodesFrozen++;
        }
    }

    const frozenRatio = nodesCreated > 0 ? nodesFrozen / nodesCreated : 0;

    return {
        spaceName,
        nodesCreated,
        nodesFrozen,
        theorems,
        shards,
        frozenRatio,
    };
}

// ── CLI ──

if (process.argv[1]?.endsWith('monster-bridge.ts')) {
    (async () => {
        const targetSpace = process.argv[2] || 'MonsterSwarm';

        console.log(`🐙 Monster Swarm Bridge`);
        console.log(`═══════════════════════\n`);
        console.log(`Target: ${targetSpace}`);
        console.log(`Data dir: ${MONSTER_DATA_DIR}\n`);

        // Create registry and kernel
        const registry = createRegistry();
        const k = createKernel(registry, targetSpace);
        const internalName = `kernel_1_${targetSpace}`;

        // Fill
        const result = fillKernelWithSwarm(registry, internalName);

        console.log(`\n📊 Swarm Results:`);
        console.log(`  Nodes created: ${result.nodesCreated}`);
        console.log(`  Nodes frozen:  ${result.nodesFrozen}`);
        console.log(`  Frozen ratio:  ${(result.frozenRatio * 100).toFixed(1)}%`);
        console.log(`  Theorems:      ${result.theorems.length}`);
        console.log(`  Shards:        ${result.shards.length}`);

        // Show theorem status
        console.log(`\n📐 Theorems:`);
        for (const thm of result.theorems) {
            const status = thm.isProven ? '✅' : '❌';
            console.log(`  ${status} ${thm.name}`);
        }

        // Mine the space
        const mine = computeMinePlane(registry, internalName);
        console.log(`\n⛏️  Mine Result:`);
        console.log(`  Total paths:   ${mine.totalPaths}`);
        console.log(`  Frozen ratio:  ${(mine.frozenRatio * 100).toFixed(1)}%`);
        console.log(`  Ш detected:    ${mine.shaDetected ? '✅ YES' : '❌ no'}`);
        console.log(`  Thermal frontier: ${mine.thermalFrontier.length} nodes`);

        // Export to Lean
        const lean = exportToLean(registry, internalName);
        console.log(`\n📝 Lean Export:`);
        console.log(`  Sorry count: ${lean.sorryCount}`);
        console.log(`  Proof complete: ${lean.proofComplete ? '✅ Ш' : '❌'}`);
    })();
}
