/**
 * lean-export.ts — Export Crystal Ball spaces to Lean 4 theorem scaffolds
 * 
 * This is the Fischer Inversion side of the proof pipeline:
 *   CB compiles → YOUKNOW labels → Lean verifies → feedback via sorries
 * 
 * Every frozen node becomes a `theorem` with its proof completed.
 * Every unfrozen node becomes a `sorry` — a claim awaiting proof.
 * The space structure maps to Lean's namespace/section system.
 * 
 * Run: npx tsx lib/crystal-ball/lean-export.ts <SpaceName>
 */

import {
    type Registry,
    type Space,
    type SpaceName,
    type CBNode,
    type ProofRole,
} from './index';

// ── Types ──

export interface LeanExportResult {
    spaceName: string;
    leanCode: string;
    totalNodes: number;
    frozenCount: number;
    sorryCount: number;       // Unfrozen non-terminal nodes
    frozenRatio: number;
    proofComplete: boolean;   // True when no sorries remain (Ш)
    nodeMap: Map<string, LeanNodeExport>;
}

export interface LeanNodeExport {
    nodeId: string;
    label: string;
    leanName: string;         // Sanitized Lean 4 identifier
    kind: 'axiom' | 'theorem' | 'def' | 'sorry';
    formalType?: string;
    frozen: boolean;
    frozenBy?: string;
    children: string[];
}

// ── Helpers ──

/** Sanitize a CB label to a valid Lean 4 identifier */
function toLeanName(label: string): string {
    return label
        .replace(/[^a-zA-Z0-9_]/g, '_')    // Replace non-alphanum with _
        .replace(/^(\d)/, '_$1')            // Can't start with digit
        .replace(/__+/g, '_')              // Collapse multiple _
        .replace(/_$/, '');                // Strip trailing _
}

/** Map CB ProofRole to Lean keyword */
function roleToLeanKeyword(role?: ProofRole, frozen?: boolean): string {
    if (role === 'axiom') return 'axiom';
    if (role === 'definition') return 'def';
    if (role === 'inference-rule') return 'axiom';
    // Everything else: theorem if frozen, sorry-theorem if not
    return frozen ? 'theorem' : 'theorem';
}

/** Generate a default formal type from node structure */
function inferFormalType(node: CBNode, space: Space): string {
    if (node.formalType) return node.formalType;

    // If node has children, it's a product type
    if (node.children.length > 0) {
        const childLabels = node.children
            .map(id => space.nodes.get(id))
            .filter(Boolean)
            .map(n => toLeanName(n!.label));
        return `Structure_${toLeanName(node.label)} ${childLabels.join(' ')}`;
    }

    // Leaf node — atomic proposition
    return `Prop_${toLeanName(node.label)}`;
}

// ── Core Export ──

/**
 * Export a CB space to Lean 4 code.
 * 
 * - Frozen nodes → `theorem ... := by exact ...`
 * - Unfrozen nodes → `theorem ... := by sorry`
 * - Nodes with `role` → `axiom` / `def` / `theorem`
 * - Space structure → `namespace` / `section`
 * - Children → product type structure
 */
export function exportToLean(
    registry: Registry,
    spaceName: SpaceName,
): LeanExportResult {
    const maybeSpace = registry.spaces.get(spaceName);
    if (!maybeSpace) throw new Error(`Space "${spaceName}" not found`);
    const space: Space = maybeSpace;

    const lines: string[] = [];
    const nodeMap = new Map<string, LeanNodeExport>();
    let frozenCount = 0;
    let sorryCount = 0;
    let totalNodes = 0;

    // Header
    lines.push(`/-! Crystal Ball export: ${spaceName}`);
    lines.push(`    Generated: ${new Date().toISOString()}`);
    lines.push(`    This file contains theorem scaffolds from CB's proof engine.`);
    lines.push(`    Frozen nodes are proven; sorry nodes await verification. -/`);
    lines.push('');
    lines.push('import Mathlib.Tactic');
    lines.push('');
    lines.push(`namespace CB.${toLeanName(spaceName)}`);
    lines.push('');

    // Walk the tree depth-first
    function emitNode(node: CBNode, depth: number, parentNs: string) {
        totalNodes++;
        const leanName = toLeanName(node.label);
        const fullName = parentNs ? `${parentNs}.${leanName}` : leanName;
        const indent = '  '.repeat(depth);
        const frozen = !!node.frozen;
        const keyword = roleToLeanKeyword(node.role, frozen);
        const formalType = inferFormalType(node, space);

        if (frozen) frozenCount++;
        else if (!node.terminal && !node.locked) sorryCount++;

        const nodeExport: LeanNodeExport = {
            nodeId: node.id,
            label: node.label,
            leanName: fullName,
            kind: frozen ? (node.role === 'axiom' ? 'axiom' : 'theorem')
                : node.role === 'definition' ? 'def'
                    : 'sorry',
            formalType: node.formalType,
            frozen,
            frozenBy: node.frozenBy?.surrogate,
            children: node.children,
        };
        nodeMap.set(node.id, nodeExport);

        // Skip root node as a theorem (it's the namespace)
        if (node.id === space.rootId && node.children.length > 0) {
            lines.push(`${indent}/-- ${node.label} (root) --/`);
            lines.push(`${indent}section ${leanName}`);
            lines.push('');
            for (const childId of node.children) {
                const child = space.nodes.get(childId);
                if (child) emitNode(child, depth + 1, fullName);
            }
            lines.push(`${indent}end ${leanName}`);
            lines.push('');
            return;
        }

        // Emit the node
        if (node.children.length > 0) {
            // Non-leaf: section + children
            lines.push(`${indent}/-- ${node.label} [${frozen ? '✅ proven' : '❌ sorry'}] --/`);
            lines.push(`${indent}section ${leanName}`);

            if (node.role === 'axiom' || (frozen && node.formalType)) {
                lines.push(`${indent}  axiom ${leanName}_ax : ${formalType}`);
            } else if (frozen) {
                lines.push(`${indent}  theorem ${leanName}_thm : ${formalType} := by`);
                lines.push(`${indent}    exact ${node.frozenBy?.proof ?? `CB_proof_${leanName}`}`);
            } else {
                lines.push(`${indent}  theorem ${leanName}_thm : ${formalType} := by`);
                lines.push(`${indent}    sorry -- CB: unfrozen (heat > 0)`);
            }
            lines.push('');

            for (const childId of node.children) {
                const child = space.nodes.get(childId);
                if (child) emitNode(child, depth + 1, fullName);
            }
            lines.push(`${indent}end ${leanName}`);
            lines.push('');
        } else {
            // Leaf node
            if (node.terminal) {
                lines.push(`${indent}/-- ${node.label} (terminal) --/`);
                lines.push(`${indent}axiom ${leanName} : ${formalType}`);
            } else if (frozen) {
                lines.push(`${indent}/-- ${node.label} [✅ proven by ${node.frozenBy?.surrogate ?? 'unknown'}] --/`);
                lines.push(`${indent}theorem ${leanName} : ${formalType} := by`);
                lines.push(`${indent}  exact ${node.frozenBy?.proof ?? `CB_proof_${leanName}`}`);
            } else {
                lines.push(`${indent}/-- ${node.label} [❌ sorry] --/`);
                lines.push(`${indent}theorem ${leanName} : ${formalType} := by`);
                lines.push(`${indent}  sorry -- CB: unfrozen coordinate`);
            }
            lines.push('');
        }
    }

    const root = space.nodes.get(space.rootId);
    if (root) emitNode(root, 0, '');

    lines.push(`end CB.${toLeanName(spaceName)}`);
    lines.push('');

    // Summary comment
    const frozenRatio = totalNodes > 0 ? frozenCount / totalNodes : 0;
    const proofComplete = totalNodes > 0 && sorryCount === 0;
    lines.push(`/- CB PROOF STATUS`);
    lines.push(`   Total nodes: ${totalNodes}`);
    lines.push(`   Frozen (proven): ${frozenCount}`);
    lines.push(`   Sorry (unproven): ${sorryCount}`);
    lines.push(`   Frozen ratio: ${(frozenRatio * 100).toFixed(1)}%`);
    lines.push(`   Status: ${proofComplete ? 'Ш COMPLETE' : `${sorryCount} sorries remaining`} -/`);

    return {
        spaceName,
        leanCode: lines.join('\n'),
        totalNodes,
        frozenCount,
        sorryCount,
        frozenRatio,
        proofComplete,
        nodeMap,
    };
}

// ── CLI ──

if (process.argv[1]?.endsWith('lean-export.ts')) {
    (async () => {
        const { createRegistry, createKernel, addNode, lockKernel, freezeNode } = await import('./index');

        const registry = createRegistry();
        const k = createKernel(registry, 'ProofDemo');

        // Build a small proof structure
        const axiom1 = addNode(k.space, 'root', 'group_identity');
        axiom1.role = 'axiom';
        axiom1.formalType = '∀ (G : Type) [Group G] (e : G), ∀ x : G, x * e = x';

        const lemma1 = addNode(k.space, 'root', 'left_cancel');
        lemma1.role = 'lemma';
        lemma1.formalType = '∀ (G : Type) [Group G] (a b c : G), a * b = a * c → b = c';

        const thm = addNode(k.space, 'root', 'unique_identity');
        thm.role = 'theorem';
        thm.formalType = '∀ (G : Type) [Group G] (e₁ e₂ : G), IsIdentity e₁ → IsIdentity e₂ → e₁ = e₂';

        const sorry1 = addNode(k.space, 'root', 'inverse_unique');
        sorry1.role = 'theorem';
        sorry1.formalType = '∀ (G : Type) [Group G] (a : G), ∃! b : G, a * b = e';

        // Freeze the axiom and lemma (proven)
        freezeNode(k.space, axiom1.id, { surrogate: 'lean4', timestamp: Date.now(), reversible: false, proof: 'Group.mul_one' });
        freezeNode(k.space, lemma1.id, { surrogate: 'lean4', timestamp: Date.now(), reversible: false, proof: 'Group.mul_left_cancel' });
        freezeNode(k.space, thm.id, { surrogate: 'lean4', timestamp: Date.now(), reversible: false, proof: 'Group.identity_unique' });
        // inverse_unique left as sorry

        const result = exportToLean(registry, 'kernel_1_ProofDemo');

        console.log('═══ LEAN 4 EXPORT ═══\n');
        console.log(result.leanCode);
        console.log('\n═══ STATS ═══');
        console.log(`  Frozen: ${result.frozenCount}/${result.totalNodes}`);
        console.log(`  Sorry: ${result.sorryCount}`);
        console.log(`  Proof complete: ${result.proofComplete ? '✅ Ш' : '❌'}`);
    })();
}
