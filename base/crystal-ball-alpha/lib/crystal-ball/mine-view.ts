/**
 * mine-view.ts — The Full Mathematical View From Any Position
 *
 * From any coordinate in a locked space, compute EVERYTHING visible:
 *   1. UARL ontology trees — decoded semantics of every visible node
 *   2. Kernel matrix — K(x,y) between all neighborhood nodes
 *   3. Born distribution — amplitude weights
 *   4. Density field — from GMR geometric computation
 *   5. Slot signatures — per-slot orbit decomposition
 *   6. Y-layer disambiguation — what abstraction level each node is at
 *
 * The output IS the prompt to the LLM.
 * All math. All semantics. From HERE, the LLM sees THIS.
 * "Fill what's missing."
 */

import type { Registry, Space, CBNode, NodeId } from './index';
import {
    buildUARL,
    buildSpaceUARL,
    describeYLayer,
    Y_LAYER_SEMANTICS,
    getAmplitude,
    getBornWeight,
    type UARLStatement,
} from './index';
import { tensorKernel, computeSpaceSlotSignature, parseSlots, type TensorKernelResult } from './kernel-v2';

// ─── Types ───────────────────────────────────────────────────────

/** Kernel similarity between two nodes */
export interface KernelPair {
    nodeA: string;   // coordinate
    nodeB: string;   // coordinate
    labelA: string;
    labelB: string;
    kernelValue: number;     // K(x,y)
    quantumValue: number;    // amplitude-weighted K
    perSlot: Array<{ slot: number; similarity: number }>;
}

/** Full mathematical view of a node */
export interface NodeView {
    id: string;
    label: string;
    coordinate: string;
    /** UARL ontology statement — full decoded semantics */
    uarl: UARLStatement | null;
    /** Y-layer with semantic disambiguation */
    yLayerDescription: string;
    /** Born weight (amplitude squared) */
    bornWeight: number;
    /** Raw amplitude */
    amplitude: number;
    /** Is this node a leaf (no children = frontier) */
    isLeaf: boolean;
    /** Is this node locked */
    locked: boolean;
    /** Is this node frozen */
    frozen: boolean;
    /** Children labels */
    childLabels: string[];
    /** Depth in tree */
    depth: number;
}

/** The full mathematical view from a position */
export interface MineView {
    /** The space name */
    spaceName: string;
    /** The position we're viewing from */
    fromCoordinate: string;
    fromLabel: string;

    /** The node we're at — full view */
    self: NodeView;
    /** Parent node view (if not root) */
    parent: NodeView | null;
    /** Sibling node views (same parent, different selection) */
    siblings: NodeView[];
    /** Children node views */
    children: NodeView[];
    /** All visible nodes (self + parent + siblings + children) */
    allVisible: NodeView[];

    /** Kernel matrix — K(x,y) between all visible nodes */
    kernelMatrix: KernelPair[];
    /** Slot signature of the current space */
    slotSignature: string;

    /** Y-layer semantic key — what each Y layer means */
    yLayerKey: string;

    /** The prompt-ready text view */
    promptView: string;
}

// ─── Compute ────────────────────────────────────────────────────

function buildNodeView(space: Space, nodeId: string): NodeView {
    const node = space.nodes.get(nodeId);
    if (!node) {
        return {
            id: nodeId, label: '?', coordinate: nodeId,
            uarl: null, yLayerDescription: 'unknown',
            bornWeight: 0, amplitude: 0, isLeaf: true,
            locked: false, frozen: false, childLabels: [],
            depth: nodeId.split('.').length,
        };
    }

    const uarl = buildUARL(space, nodeId);
    const stratum = node.stratum || 'instance';
    const yLayer = {
        universal: 'Y1', subclass: 'Y2', instance: 'Y3',
        instance_universal: 'Y4', instance_subtype: 'Y5', instance_instance: 'Y6',
    }[stratum] || 'Y3';

    const childLabels = node.children
        .map(cid => space.nodes.get(cid))
        .filter((n): n is CBNode => !!n)
        .map(n => n.label);

    return {
        id: nodeId,
        label: node.label,
        coordinate: nodeId,
        uarl,
        yLayerDescription: describeYLayer(yLayer),
        bornWeight: getBornWeight(node),
        amplitude: getAmplitude(node),
        isLeaf: node.children.length === 0,
        locked: !!node.locked,
        frozen: !!node.frozen,
        childLabels,
        depth: nodeId === 'root' ? 0 : nodeId.split('.').length,
    };
}

function getParentId(nodeId: string): string | null {
    if (nodeId === 'root') return null;
    const dot = nodeId.lastIndexOf('.');
    return dot === -1 ? 'root' : nodeId.substring(0, dot);
}

function getSiblingIds(space: Space, nodeId: string): string[] {
    const parentId = getParentId(nodeId);
    if (!parentId) return [];
    const parentNode = space.nodes.get(parentId);
    if (!parentNode) return [];
    return parentNode.children.filter(cid => cid !== nodeId);
}

/**
 * Compute the full mathematical view from a coordinate.
 *
 * This is the core function. It computes EVERYTHING visible from
 * the given position and renders it as a prompt-ready view.
 */
export function computeMineView(
    registry: Registry,
    spaceName: string,
    coordinate: string,
): MineView {
    const space = registry.spaces.get(spaceName);
    if (!space) {
        return {
            spaceName, fromCoordinate: coordinate, fromLabel: '?',
            self: buildNodeView({} as Space, coordinate),
            parent: null, siblings: [], children: [], allVisible: [],
            kernelMatrix: [], slotSignature: '', yLayerKey: '',
            promptView: `Space "${spaceName}" not found.`,
        };
    }

    // Resolve coordinate
    const nodeId = coordinate === 'root' ? space.rootId : coordinate;
    const node = space.nodes.get(nodeId);
    if (!node && nodeId !== space.rootId) {
        // Try as root
    }

    // Build self view
    const self = buildNodeView(space, nodeId);

    // Parent
    const parentId = getParentId(nodeId);
    const parent = parentId ? buildNodeView(space, parentId) : null;

    // Siblings
    const siblingIds = getSiblingIds(space, nodeId);
    const siblings = siblingIds.map(sid => buildNodeView(space, sid));

    // Children
    const childNode = space.nodes.get(nodeId);
    const childIds = childNode ? childNode.children : [];
    const children = childIds.map(cid => buildNodeView(space, cid));

    // All visible nodes
    const allVisible = [self];
    if (parent) allVisible.push(parent);
    allVisible.push(...siblings);
    allVisible.push(...children);

    // Also add grandchildren (1 level deeper) for context
    for (const child of children) {
        const childNode = space.nodes.get(child.id);
        if (childNode) {
            for (const gcId of childNode.children) {
                allVisible.push(buildNodeView(space, gcId));
            }
        }
    }

    // Compute kernel matrix between all visible nodes
    const kernelMatrix: KernelPair[] = [];
    for (let i = 0; i < allVisible.length; i++) {
        for (let j = i + 1; j < allVisible.length; j++) {
            const a = allVisible[i];
            const b = allVisible[j];
            try {
                const kr = tensorKernel(registry, spaceName, a.id, b.id);
                kernelMatrix.push({
                    nodeA: a.id,
                    nodeB: b.id,
                    labelA: a.label,
                    labelB: b.label,
                    kernelValue: kr.value,
                    quantumValue: kr.quantumValue,
                    perSlot: kr.perSlot.map(s => ({
                        slot: s.slotIndex,
                        similarity: s.similarity,
                    })),
                });
            } catch {
                // Skip pairs where kernel computation fails
            }
        }
    }

    // Sort kernel pairs by value (highest similarity first)
    kernelMatrix.sort((a, b) => b.kernelValue - a.kernelValue);

    // Space slot signature
    let slotSignature = '';
    try {
        const sig = computeSpaceSlotSignature(registry, spaceName);
        slotSignature = sig.canonical;
    } catch { }

    // Y-layer key
    const yLayerKey = Object.entries(Y_LAYER_SEMANTICS)
        .map(([k, v]) => `  ${k}: ${v.name} [${v.griessPhase}] (${v.classOrInstance}) — ${v.fillInstruction}`)
        .join('\n');

    // Render prompt
    const promptView = renderPromptView(
        spaceName, self, parent, siblings, children, kernelMatrix, yLayerKey, slotSignature,
    );

    return {
        spaceName, fromCoordinate: coordinate, fromLabel: self.label,
        self, parent, siblings, children, allVisible,
        kernelMatrix, slotSignature, yLayerKey,
        promptView,
    };
}

// ─── Prompt Renderer ─────────────────────────────────────────────

function renderPromptView(
    spaceName: string,
    self: NodeView,
    parent: NodeView | null,
    siblings: NodeView[],
    children: NodeView[],
    kernelMatrix: KernelPair[],
    yLayerKey: string,
    slotSignature: string,
): string {
    const lines: string[] = [];

    // Header
    lines.push(`═══ MINE VIEW: ${spaceName} from ${self.coordinate} "${self.label}" ═══`);
    lines.push('');

    // Y-Layer Key (disambiguation)
    lines.push('Y-LAYER SEMANTICS (what each abstraction level means):');
    lines.push(yLayerKey);
    lines.push('');

    // Self
    lines.push(`── POSITION: ${self.coordinate} "${self.label}" ──`);
    if (self.uarl) lines.push(`  UARL: ${self.uarl.raw}`);
    lines.push(`  Y-Layer: ${self.yLayerDescription}`);
    lines.push(`  Born: ${self.bornWeight.toFixed(4)}  Amplitude: ${self.amplitude.toFixed(4)}`);
    lines.push(`  Locked: ${self.locked}  Frozen: ${self.frozen}  Leaf: ${self.isLeaf}`);
    if (self.childLabels.length > 0) {
        lines.push(`  Children: [${self.childLabels.join(', ')}]`);
    } else {
        lines.push(`  Children: [EMPTY — this is a FILL TARGET]`);
    }
    lines.push('');

    // Parent context
    if (parent) {
        lines.push(`── PARENT: ${parent.coordinate} "${parent.label}" ──`);
        if (parent.uarl) lines.push(`  UARL: ${parent.uarl.raw}`);
        lines.push(`  Children (siblings + self): [${parent.childLabels.join(', ')}]`);
        lines.push('');
    }

    // Sibling ontology trees
    if (siblings.length > 0) {
        lines.push(`── SIBLINGS (${siblings.length} at same level) ──`);
        for (const sib of siblings) {
            const status = sib.isLeaf ? '🔴 EMPTY' : `🟢 ${sib.childLabels.length} children: [${sib.childLabels.join(', ')}]`;
            lines.push(`  ${sib.coordinate} "${sib.label}": ${status}`);
            if (sib.uarl) lines.push(`    UARL: ${sib.uarl.raw}`);
        }
        lines.push('');
    }

    // Children detail
    if (children.length > 0) {
        lines.push(`── CHILDREN (${children.length}) ──`);
        for (const child of children) {
            const status = child.isLeaf ? '🔴 EMPTY' : `🟢 [${child.childLabels.join(', ')}]`;
            lines.push(`  ${child.coordinate} "${child.label}": ${status}`);
            if (child.uarl) lines.push(`    UARL: ${child.uarl.raw}`);
        }
        lines.push('');
    }

    // Kernel matrix (top 15 pairs by similarity)
    if (kernelMatrix.length > 0) {
        lines.push(`── KERNEL MATRIX (${kernelMatrix.length} pairs, top 15 by K) ──`);
        const topPairs = kernelMatrix.slice(0, 15);
        for (const pair of topPairs) {
            const perSlotStr = pair.perSlot.map(s => `S${s.slot}=${s.similarity.toFixed(2)}`).join(' ');
            lines.push(`  K(${pair.labelA}, ${pair.labelB}) = ${pair.kernelValue.toFixed(4)} [${perSlotStr}]`);
        }
        if (kernelMatrix.length > 15) {
            lines.push(`  ... +${kernelMatrix.length - 15} more pairs`);
        }
        lines.push('');
    }

    // Slot signature
    if (slotSignature) {
        lines.push(`── SLOT SIGNATURE: ${slotSignature} ──`);
        lines.push('');
    }

    // Fill instruction
    const emptyChildren = children.filter(c => c.isLeaf);
    const emptySiblings = siblings.filter(s => s.isLeaf);
    if (self.isLeaf) {
        lines.push('══ FILL TARGET: This node has NO children. ══');
        lines.push(`The Y-layer tells you WHAT to name: ${self.yLayerDescription}`);
        lines.push('Fill this node with its complete spectrum — what are its dimensions?');
    } else if (emptyChildren.length > 0) {
        lines.push(`══ FILL TARGETS: ${emptyChildren.length} empty children ══`);
        for (const ec of emptyChildren) {
            lines.push(`  ${ec.coordinate} "${ec.label}" — needs its spectrum filled`);
        }
    }
    if (emptySiblings.length > 0) {
        lines.push(`══ SIBLING GAPS: ${emptySiblings.length} empty siblings ══`);
        for (const es of emptySiblings) {
            lines.push(`  ${es.coordinate} "${es.label}" — needs its spectrum filled`);
        }
    }

    return lines.join('\n');
}

// ─── Convenience: Format for MCP output ─────────────────────────

export function formatMineView(view: MineView): string {
    return view.promptView;
}
