/* ═══════════════════════════════════════════════════════════
   kernel-v2.ts — RKHS grounded on slot/spectrum semantics
   
   CORRECT foundation:
     - Coordinates decompose into SLOTS (between dots)
     - Each slot is a LEVEL with a spectrum (ordered list of children)
     - Spectrum has PRIMACY: selection 1 is primary, 7 is 7th, 91 is 8th...
     - 0 = superposition = "any spectrum value" = uniform over spectrum
     - The kernel FACTORS per-slot: K(x,y) = ∏ K_k(x_k, y_k)
     - Orbits are found PER-SLOT (which spectrum values are interchangeable)
     - coordToReal already encodes primacy ordering
   
   This replaces the flat kernel in kernel-function.ts with the 
   mathematically correct tensor product RKHS.
   ═══════════════════════════════════════════════════════════ */

import {
    type Registry,
    type SpaceName,
    type Space,
    type CBNode,
    type NodeId,
    coordToReal,
    encodeSelectionIndex,
    decodeSelectionIndex,
    getAmplitude,
} from './index';

// ─── Types ───────────────────────────────────────────────────

/** A parsed slot value within a coordinate */
export interface SlotValue {
    raw: string;           // The raw digit string for this slot (e.g., "3", "91", "0")
    selectionIndex: number;// Decoded 1-based selection index (0 = superposition)
    real: number;          // coordToReal of this slot's digit string
    isSuperposition: boolean;
}

/** Per-slot kernel result */
export interface SlotKernelResult {
    slotIndex: number;
    valueX: SlotValue;
    valueY: SlotValue;
    similarity: number;    // K_k(x_k, y_k) ∈ [0, 1]
}

/** Full tensor product kernel result */
export interface TensorKernelResult {
    coordX: string;
    coordY: string;
    value: number;         // Structural kernel K(x,y)
    quantumValue: number;  // Amplitude-weighted: √(|ψ_x|²·|ψ_y|²) · K(x,y)
    amplitudeWeight: number; // √(|ψ_x|²·|ψ_y|²)
    perSlot: SlotKernelResult[];
    depth: number;         // max(slots_x, slots_y)
}

/** Per-slot orbit: which spectrum values are interchangeable */
export interface SlotOrbit {
    slotIndex: number;
    parentNodeId: NodeId;
    parentLabel: string;
    spectrumSize: number;       // Total children at this level
    orbits: {
        members: number[];      // Selection indices in this orbit
        labels: string[];       // Labels of the corresponding nodes
        size: number;
    }[];
    symmetryGroup: string;      // e.g., "S₃ × S₂" or "trivial"
    superpositionMeaning: string; // What 0 means at this slot
}

/** Full space signature: per-slot decomposition */
export interface SpaceSlotSignature {
    spaceName: string;
    slots: SlotOrbit[];
    totalConfigurations: number;  // Product of spectrum sizes
    totalSymmetry: string;        // Product of per-slot groups
    canonical: string;
}

// ─── Slot Parsing ────────────────────────────────────────────

/**
 * Parse a coordinate string into slot values.
 * Splits on dots, decodes each segment.
 */
export function parseSlots(coordinate: string): SlotValue[] {
    if (coordinate === 'root' || coordinate === '') return [];

    const segments = coordinate.split('.');
    return segments.map(seg => {
        const raw = seg;
        if (raw === '0') {
            return {
                raw,
                selectionIndex: 0,
                real: 0,
                isSuperposition: true,
            };
        }
        const selectionIndex = decodeSelectionIndex(raw);
        return {
            raw,
            selectionIndex,
            real: coordToReal(raw),
            isSuperposition: false,
        };
    });
}

// ─── Per-Slot Kernel ─────────────────────────────────────────

/**
 * K_k(x_k, y_k) — kernel for one slot.
 * 
 * Uses Gaussian RBF on primacy distance:
 *   K_k = exp(-α · |real(x_k) - real(y_k)|²)
 * 
 * Special cases:
 *   K_k(x, x) = 1.0                     (identical selection)
 *   K_k(0, y) = K_k(x, 0) = 1/sqrt(n)  (superposition = uniform over n values)
 *   K_k(0, 0) = 1.0                     (both superposed = both equivalent)
 * 
 * @param alpha Bandwidth parameter (higher = more sensitive to primacy distance)
 * @param spectrumSize Number of spectrum values at this slot (for superposition normalization)
 */
export function slotKernel(
    xSlot: SlotValue,
    ySlot: SlotValue,
    spectrumSize: number = 7,
    alpha: number = 5.0,
): number {
    // Both superposition → identical
    if (xSlot.isSuperposition && ySlot.isSuperposition) return 1.0;

    // One is superposition → uniform over spectrum
    // This is the "expectation" of K_k under the uniform distribution
    if (xSlot.isSuperposition || ySlot.isSuperposition) {
        // Average kernel value: E[K_k(x, U)] where U ~ Uniform(spectrum)
        // For Gaussian RBF, this is approximately 1/sqrt(n) for n values
        return 1.0 / Math.sqrt(spectrumSize);
    }

    // Both specific → Gaussian RBF on primacy distance
    const dist = Math.abs(xSlot.real - ySlot.real);
    return Math.exp(-alpha * dist * dist);
}

// ─── Tensor Product Kernel ───────────────────────────────────

/**
 * K(x, y) = ∏_k K_k(x_k, y_k) — tensor product over all slots.
 * 
 * This is the mathematically correct RKHS kernel for CB coordinates:
 *   - Each slot contributes independently to similarity
 *   - The product ensures that ALL slots must be similar for high K
 *   - 0 at a slot = superposition = that slot doesn't discriminate
 *   - Missing slots (different depth) treated as superposition
 */
export function tensorKernel(
    registry: Registry,
    spaceName: SpaceName,
    coordX: string,
    coordY: string,
    alpha: number = 5.0,
): TensorKernelResult {
    const slotsX = parseSlots(coordX);
    const slotsY = parseSlots(coordY);
    const maxDepth = Math.max(slotsX.length, slotsY.length);

    const perSlot: SlotKernelResult[] = [];
    let product = 1.0;

    // Get spectrum sizes per level by traversing the space
    const space = registry.spaces.get(spaceName);

    for (let k = 0; k < maxDepth; k++) {
        const xk = slotsX[k] ?? { raw: '0', selectionIndex: 0, real: 0, isSuperposition: true };
        const yk = slotsY[k] ?? { raw: '0', selectionIndex: 0, real: 0, isSuperposition: true };

        // Determine spectrum size at this level
        const specSize = getSpectrumSizeAtLevel(space, coordX, k);

        const sim = slotKernel(xk, yk, specSize, alpha);
        product *= sim;

        perSlot.push({
            slotIndex: k,
            valueX: xk,
            valueY: yk,
            similarity: sim,
        });
    }

    // Compute amplitude weight from the nodes at coordX and coordY
    // Walk the space to find the deepest node on each coordinate path
    let ampX = 0.0;
    let ampY = 0.0;
    if (space) {
        const nodeX = space.nodes.get(coordX);
        const nodeY = space.nodes.get(coordY);
        ampX = nodeX ? getAmplitude(nodeX) : 0.0;
        ampY = nodeY ? getAmplitude(nodeY) : 0.0;
    }
    const amplitudeWeight = Math.sqrt(ampX * ampY);

    return {
        coordX,
        coordY,
        value: product,
        quantumValue: amplitudeWeight * product,
        amplitudeWeight,
        perSlot,
        depth: maxDepth,
    };
}

/**
 * Get the number of children (spectrum size) at a given level in a space.
 * Level 0 = root's children, Level 1 = child-of-root's children, etc.
 */
function getSpectrumSizeAtLevel(
    space: Space | undefined,
    coord: string,
    level: number,
): number {
    if (!space) return 7; // default fallback

    const slots = coord.split('.');
    let currentNode: CBNode | undefined = space.nodes.get(space.rootId);

    // Walk to the parent of the requested level
    for (let l = 0; l < level; l++) {
        if (!currentNode) return 7;
        const sel = slots[l];
        if (!sel || sel === '0') {
            // Superposition — take first child as representative
            if (currentNode.children.length > 0) {
                currentNode = space.nodes.get(currentNode.children[0]);
            } else {
                return 1;
            }
        } else {
            const idx = decodeSelectionIndex(sel) - 1; // 0-indexed
            if (idx >= 0 && idx < currentNode.children.length) {
                currentNode = space.nodes.get(currentNode.children[idx]);
            } else {
                return 1;
            }
        }
    }

    // Spectrum size = number of children at this level
    return currentNode ? Math.max(currentNode.children.length, 1) : 1;
}

// ─── Per-Slot Gram Matrix and Orbits ─────────────────────────

/**
 * Compute per-slot Gram matrix.
 * For a given parent node, compute K_k for all pairs of its children.
 * This reveals which spectrum values at this level are interchangeable.
 */
export function slotGramMatrix(
    parentNode: CBNode,
    space: Space,
    alpha: number = 5.0,
): { matrix: number[][]; labels: string[]; selectionIndices: number[] } {
    const n = parentNode.children.length;
    const labels: string[] = [];
    const selectionIndices: number[] = [];
    const childSlots: SlotValue[] = [];

    for (let i = 0; i < n; i++) {
        const childId = parentNode.children[i];
        const child = space.nodes.get(childId);
        const encoded = encodeSelectionIndex(i + 1); // 1-based
        labels.push(child?.label ?? childId);
        selectionIndices.push(i + 1);
        childSlots.push({
            raw: encoded,
            selectionIndex: i + 1,
            real: coordToReal(encoded),
            isSuperposition: false,
        });
    }

    const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
    for (let i = 0; i < n; i++) {
        for (let j = i; j < n; j++) {
            const k = slotKernel(childSlots[i], childSlots[j], n, alpha);
            matrix[i][j] = k;
            matrix[j][i] = k;
        }
    }

    return { matrix, labels, selectionIndices };
}

/**
 * Compute a structural fingerprint for a subtree rooted at a node.
 * Two nodes with the same fingerprint have identical sub-tree shapes.
 * 
 * The fingerprint captures:
 *   - stratum (ontological level — NEVER interchangeable)
 *   - kernelRef (sub-kernel identity — different kernels = different structure)  
 *   - number of children, and recursively their fingerprints
 * This is a tree isomorphism check (Aho-Hopcroft-Ullman canonical form)
 * extended with semantic tags.
 */
function subtreeFingerprint(space: Space, nodeId: NodeId, maxDepth: number = 10): string {
    const node = space.nodes.get(nodeId);
    if (!node) return '()';

    // Semantic tags that break equivalence even with same shape
    const tags: string[] = [];
    if (node.stratum) tags.push(`s:${node.stratum}`);
    if (node.kernelRef !== undefined) tags.push(`k:${node.kernelRef}`);
    const tagStr = tags.length > 0 ? tags.join(',') + '|' : '';

    if (node.children.length === 0 || maxDepth === 0) return `(${tagStr})`;

    // Recursively fingerprint children, then sort for canonical form
    const childFingerprints = node.children
        .map(childId => subtreeFingerprint(space, childId, maxDepth - 1))
        .sort(); // Sort so child ORDER doesn't matter for shape equivalence

    return `(${tagStr}${childFingerprints.join(',')})`;
}

/**
 * Find orbits within one slot (one parent's children).
 * 
 * Orbit = set of spectrum values with IDENTICAL SUB-TREE STRUCTURE.
 * 
 * Two children are in the same orbit if they have the same subtreeFingerprint.
 * This means: same branching pattern, same depth, same shape recursively.
 * 
 * Within an orbit, members are ordered by primacy (selection index).
 * Primacy is a REFINEMENT within orbits, not a breaking criterion.
 */
export function findSlotOrbits(
    parentNode: CBNode,
    space: Space,
    slotIndex: number,
): SlotOrbit {
    const n = parentNode.children.length;
    if (n === 0) {
        return {
            slotIndex,
            parentNodeId: parentNode.id,
            parentLabel: parentNode.label,
            spectrumSize: 0,
            orbits: [],
            symmetryGroup: 'empty',
            superpositionMeaning: 'no spectrum (leaf)',
        };
    }

    // Group children by sub-tree shape
    const fingerprintGroups = new Map<string, { members: number[]; labels: string[] }>();

    for (let i = 0; i < n; i++) {
        const childId = parentNode.children[i];
        const child = space.nodes.get(childId);
        const fingerprint = subtreeFingerprint(space, childId);
        const selectionIndex = i + 1; // 1-based

        if (!fingerprintGroups.has(fingerprint)) {
            fingerprintGroups.set(fingerprint, { members: [], labels: [] });
        }
        const group = fingerprintGroups.get(fingerprint)!;
        group.members.push(selectionIndex);
        group.labels.push(child?.label ?? childId);
    }

    // Convert to orbits (sorted by first member's selection index for stability)
    const orbits = Array.from(fingerprintGroups.values())
        .map(g => ({ members: g.members, labels: g.labels, size: g.members.length }))
        .sort((a, b) => a.members[0] - b.members[0]);

    // Compute symmetry group name
    const groupParts = orbits
        .filter(o => o.size > 1)
        .map(o => `S${o.size}`);
    const fixedCount = orbits.filter(o => o.size === 1).length;
    const symmetryGroup = groupParts.length > 0
        ? groupParts.join(' × ') + (fixedCount > 0 ? ` + ${fixedCount} fixed` : '')
        : `trivial (${n} fixed)`;

    // What does 0 mean at this slot?
    const superpositionMeaning = orbits.length === 1
        ? `uniform over ${n} interchangeable values (full ${groupParts[0] ?? 'S' + n} symmetry)`
        : orbits.length === n
            ? `random choice among ${n} DISTINCT values (no symmetry)`
            : `random choice with ${orbits.length} equivalence classes (${groupParts.join(', ')} symmetry)`;

    return {
        slotIndex,
        parentNodeId: parentNode.id,
        parentLabel: parentNode.label,
        spectrumSize: n,
        orbits,
        symmetryGroup,
        superpositionMeaning,
    };
}

// ─── Full Space Slot Signature ───────────────────────────────

/**
 * Compute the slot-decomposed signature for an entire space.
 * 
 * Walks the space level by level (root → children → grandchildren...)
 * and computes per-slot orbits at each level.
 * 
 * This IS the correct foundation signature for CB.
 */
export function computeSpaceSlotSignature(
    registry: Registry,
    spaceName: SpaceName,
    maxDepth: number = 5,
): SpaceSlotSignature {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    const slots: SlotOrbit[] = [];
    let totalConfigs = 1;
    const groupParts: string[] = [];

    // BFS level by level
    let currentLevel: CBNode[] = [];
    const root = space.nodes.get(space.rootId);
    if (root) currentLevel = [root];

    for (let depth = 0; depth < maxDepth && currentLevel.length > 0; depth++) {
        const nextLevel: CBNode[] = [];

        for (const parent of currentLevel) {
            if (parent.children.length === 0) continue;

            const slotOrbit = findSlotOrbits(parent, space, depth);
            slots.push(slotOrbit);
            totalConfigs *= Math.max(parent.children.length, 1);
            if (slotOrbit.symmetryGroup !== 'empty') {
                groupParts.push(slotOrbit.symmetryGroup);
            }

            // Queue next level
            for (const childId of parent.children) {
                const child = space.nodes.get(childId);
                if (child && child.children.length > 0) {
                    nextLevel.push(child);
                }
            }
        }

        currentLevel = nextLevel;
    }

    // Build canonical string
    const slotStrings = slots.map(s => {
        const orbitSizes = s.orbits.map(o => o.size).sort((a, b) => b - a);
        return `[${orbitSizes.join(',')}]`;
    });
    const canonical = slotStrings.join('⊗') + '|' + (groupParts.join(' × ') || 'trivial');

    return {
        spaceName,
        slots,
        totalConfigurations: totalConfigs,
        totalSymmetry: groupParts.join(' × ') || 'trivial',
        canonical,
    };
}

// ─── Tensor Gram Matrix ──────────────────────────────────────

/**
 * Compute the Gram matrix using the tensor product kernel.
 * 
 * For a set of full coordinates, computes K(x,y) = ∏ K_k(x_k, y_k)
 * for all pairs. This is the correct Gram matrix for the RKHS.
 */
export function tensorGramMatrix(
    registry: Registry,
    spaceName: SpaceName,
    coordinates: string[],
    alpha: number = 5.0,
): { matrix: number[][]; quantumMatrix: number[][]; coordinates: string[] } {
    const n = coordinates.length;
    const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
    const quantumMatrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));

    for (let i = 0; i < n; i++) {
        for (let j = i; j < n; j++) {
            const result = tensorKernel(registry, spaceName, coordinates[i], coordinates[j], alpha);
            matrix[i][j] = result.value;
            matrix[j][i] = result.value;
            quantumMatrix[i][j] = result.quantumValue;
            quantumMatrix[j][i] = result.quantumValue;
        }
    }

    return { matrix, quantumMatrix, coordinates };
}

// ─── Kernel Thermometer ──────────────────────────────────────
// Temperature is a MEASUREMENT of interaction heat, not a setting.
// It reads the delta between kernel states before/after interaction.
//
// High heat = reorganization pressure (orbits shifting, nodes added)
// Low heat = confirmation (locking, settling)
// HIEL = Heat-Induced Energy Ligation — when temp is high enough
//        to collapse Ш elements and bond valid structures.

export interface KernelSnapshot {
    timestamp: number;
    nodeCount: number;
    lockedCount: number;
    frozenCount: number;
    superpositionCount: number;    // Nodes with amplitude === 0 or undefined
    totalAmplitude: number;        // Sum of all amplitudes
    canonical: string;             // Signature canonical form
    orbitCount: number;            // Total orbits across all slots
    symmetryGroups: string[];      // Per-slot symmetry group names
    slotCount: number;
}

export interface TemperatureReading {
    temperature: number;           // 0.0 (frozen) to 1.0+ (max heat)
    // Breakdown by signal
    signals: {
        nodesAdded: number;        // New structure appeared
        nodesLocked: number;       // Structure settled (cooling)
        orbitsChanged: number;     // Symmetry reorganized
        signatureChanged: boolean; // Canonical form shifted
        amplitudeShift: number;    // Net amplitude change
        superpositionsResolved: number; // Zeroes that became non-zero
    };
    hielCondition: boolean;        // Temperature high enough for ligation
    phase: 'frozen' | 'cool' | 'warm' | 'hot' | 'critical';
}

/**
 * Capture a snapshot of the current kernel state.
 * Call before and after an interaction to measure temperature.
 */
export function takeKernelSnapshot(
    registry: Registry,
    spaceName: SpaceName,
): KernelSnapshot {
    const space = registry.spaces.get(spaceName);
    if (!space) {
        return {
            timestamp: Date.now(),
            nodeCount: 0, lockedCount: 0, frozenCount: 0,
            superpositionCount: 0, totalAmplitude: 0,
            canonical: '', orbitCount: 0, symmetryGroups: [], slotCount: 0,
        };
    }

    let lockedCount = 0;
    let frozenCount = 0;
    let superpositionCount = 0;
    let totalAmplitude = 0;

    for (const [id, node] of space.nodes) {
        if (id === 'root') continue;
        if (node.locked) lockedCount++;
        if (node.frozen) frozenCount++;
        const amp = node.amplitude;
        if (amp === undefined || amp === 0) {
            superpositionCount++;
        }
        totalAmplitude += amp ?? 0;
    }

    // Get signature if possible
    let canonical = '';
    let orbitCount = 0;
    let symmetryGroups: string[] = [];
    let slotCount = 0;
    try {
        const sig = computeSpaceSlotSignature(registry, spaceName);
        canonical = sig.canonical;
        orbitCount = sig.slots.reduce((sum, s) => sum + s.orbits.length, 0);
        symmetryGroups = sig.slots.map(s => s.symmetryGroup);
        slotCount = sig.slots.length;
    } catch { /* space may not be in kernel mode */ }

    return {
        timestamp: Date.now(),
        nodeCount: space.nodes.size - 1, // exclude root
        lockedCount,
        frozenCount,
        superpositionCount,
        totalAmplitude,
        canonical,
        orbitCount,
        symmetryGroups,
        slotCount,
    };
}

/**
 * Compute kernel temperature from the delta between two snapshots.
 *
 * Temperature is the heat of the interaction — how much reorganization
 * pressure was applied to the kernel between the two snapshots.
 *
 * Phase thresholds:
 *   frozen   < 0.05  (no change)
 *   cool     < 0.2   (minor additions, confirmations)
 *   warm     < 0.5   (significant new structure)
 *   hot      < 0.8   (orbits reorganizing)
 *   critical >= 0.8  (catastrophe conditions — HIEL possible)
 */
export function computeKernelTemperature(
    before: KernelSnapshot,
    after: KernelSnapshot,
): TemperatureReading {
    const nodesAdded = Math.max(0, after.nodeCount - before.nodeCount);
    const nodesLocked = Math.max(0, after.lockedCount - before.lockedCount);
    const superpositionsResolved = Math.max(0, before.superpositionCount - after.superpositionCount);
    const amplitudeShift = after.totalAmplitude - before.totalAmplitude;
    const signatureChanged = before.canonical !== after.canonical && before.canonical !== '';
    const orbitsChanged = Math.abs(after.orbitCount - before.orbitCount);

    // Weights for each signal (tuned by what matters)
    const heatFromNodes = nodesAdded * 0.05;           // Each new node adds a little heat
    const heatFromOrbits = orbitsChanged * 0.15;       // Orbit changes are significant
    const heatFromSignature = signatureChanged ? 0.3 : 0; // Signature change is a big deal
    const coolingFromLocks = nodesLocked * -0.03;      // Locking cools
    const coolingFromAmplitude = amplitudeShift > 0 ? amplitudeShift * -0.02 : 0; // Rising amplitude = settling

    const rawTemp = Math.max(0,
        heatFromNodes +
        heatFromOrbits +
        heatFromSignature +
        coolingFromLocks +
        coolingFromAmplitude
    );

    // Normalize: cap at ~1.5 for extreme interactions, typical range 0-1
    const temperature = Math.min(1.5, rawTemp);

    // HIEL condition: temperature >= 0.8 AND signature changed
    // This means enough heat was applied to potentially collapse Ш elements
    const hielCondition = temperature >= 0.8 && signatureChanged;

    const phase: TemperatureReading['phase'] =
        temperature < 0.05 ? 'frozen' :
            temperature < 0.2 ? 'cool' :
                temperature < 0.5 ? 'warm' :
                    temperature < 0.8 ? 'hot' :
                        'critical';

    return {
        temperature,
        signals: {
            nodesAdded,
            nodesLocked,
            orbitsChanged,
            signatureChanged,
            amplitudeShift,
            superpositionsResolved,
        },
        hielCondition,
        phase,
    };
}
