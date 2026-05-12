/* ═══════════════════════════════════════════════════════════
   reify.ts — The T Operator (v2, correct RKHS)
   
   Takes a locked kernel, computes its per-slot orbit signature
   (kernel-v2), and creates a NEW KernelSpace whose structure
   encodes it.
   
   Uses children-as-spectrum, NOT the attributes map.
   
   The reified kernel contains:
     - One top-level node per SLOT (each slot in the source)
     - Under each slot node: children = the orbits at that slot
     - Under each orbit node: children = the orbit members (primacy preserved)
     - Dots between slot nodes from the source's dot structure
   
   This closes the loop:
     create → fill → lock → mine → reify → lock → mine → reify → ...
   
   Catastrophe detection uses classes A-E from catastrophe_geometry.md:
     A — "Done" asserted, state not done (false completion)
     B — Inheriting prior wrong frame (shield permeation)
     C — Same label, different referent (binding collision / fold)
     D — Summary erased causal fiber (narrative overwrite)
     E — Each step more generic (Futamura flattening)
   
   Cat(A,R) = cofiber(A → R) = quotient residue + obstruction
              classes + fold structure + alias structure + lift conditions
   
   Ш = 0 means every locally valid transition is globally valid.
   Crowning = Ш = 0 + lift conditions satisfied = Monster-valid.
   ═══════════════════════════════════════════════════════════ */

import {
    type Registry,
    type KernelSpace,
    createKernel,
    addNode,
    addDot,
    lockKernel,
    getKernel,
} from './index';

import {
    computeSpaceSlotSignature,
    type SpaceSlotSignature,
    type SlotOrbit,
} from './kernel-v2';

export interface ReifyResult {
    kernel: KernelSpace;
    slotSignature: SpaceSlotSignature;
    level: number;  // Which Futamura level this reification is at
}

/**
 * Reify a locked kernel's structure into a new KernelSpace.
 * 
 * The T operator: takes a locked kernel, analyzes its per-slot
 * orbit structure, and creates a new kernel whose children ARE
 * the orbit decomposition.
 * 
 * Structure of the reified kernel:
 *   root
 *   ├── SlotNode_0 (represents slot 0 in source)
 *   │   ├── Orbit_0_S3 (3 interchangeable values)
 *   │   │   ├── member_1
 *   │   │   ├── member_2
 *   │   │   └── member_3
 *   │   └── Orbit_1_fixed (1 unique value)
 *   │       └── member_4
 *   ├── SlotNode_1 (represents slot 1 in source)
 *   │   └── ...
 *   └── ...
 * 
 * @param registry - The registry
 * @param sourceKernelId - Global ID of the locked kernel to reify
 * @param level - Futamura level (0 = first reification, etc.)
 */
export function reifyMineSpace(
    registry: Registry,
    sourceKernelId: number,
    level: number = 0,
): ReifyResult {
    const sourceKernel = getKernel(registry, sourceKernelId);
    if (!sourceKernel.locked) {
        throw new Error(`Kernel #${sourceKernelId} must be locked before reification`);
    }

    // 1. Compute per-slot orbit signature using kernel-v2
    const slotSignature = computeSpaceSlotSignature(
        registry,
        sourceKernel.space.name,
    );

    if (slotSignature.slots.length === 0) {
        throw new Error(`Kernel #${sourceKernelId} has no slots to reify`);
    }

    // 2. Create the reified kernel
    const reifiedKernel = createKernel(
        registry,
        `T${level}_of_${sourceKernelId}`,
    );

    // Helper: add an orbit under a parent node
    function addOrbitUnder(space: typeof reifiedKernel.space, parentId: string, orbit: { size: number; labels: string[]; members: number[] }) {
        if (orbit.size === 1) {
            // Fixed point — leaf node. Terminal is derived when locked.
            addNode(space, parentId, `fixed_${orbit.labels[0]}`);
        } else {
            const orbitNode = addNode(space, parentId, `S${orbit.size}_orbit`);
            for (let mi = 0; mi < orbit.members.length; mi++) {
                // Orbit members are spectrum values (leaves). Terminal derived on lock.
                addNode(space, orbitNode.id, orbit.labels[mi]);
            }
        }
    }

    // 3. Create reified structure
    const slotNodeIds: string[] = [];
    const singleSlot = slotSignature.slots.length === 1;

    for (const slot of slotSignature.slots) {
        if (!singleSlot) {
            const slotNode = addNode(
                reifiedKernel.space,
                'root',
                `Slot${slot.slotIndex}_${slot.parentLabel}`,
            );
            slotNodeIds.push(slotNode.id);

            for (const orbit of slot.orbits) {
                addOrbitUnder(reifiedKernel.space, slotNode.id, orbit);
            }

            const sourceNode = sourceKernel.space.nodes.get(slot.parentNodeId);
            if (sourceNode?.kernelRef !== undefined) {
                slotNode.kernelRef = sourceNode.kernelRef;
            }
        } else if (slot.orbits.length >= 2) {
            slotNodeIds.push('root');
            for (const orbit of slot.orbits) {
                addOrbitUnder(reifiedKernel.space, 'root', orbit);
            }
        } else if (slot.orbits.length === 1 && slot.orbits[0].size >= 2) {
            slotNodeIds.push('root');
            const orbit = slot.orbits[0];
            for (let mi = 0; mi < orbit.members.length; mi++) {
                addNode(
                    reifiedKernel.space,
                    'root',
                    orbit.labels[mi],
                );
            }
        } else {
            slotNodeIds.push('root');
            for (const orbit of slot.orbits) {
                addOrbitUnder(reifiedKernel.space, 'root', orbit);
            }
        }
    }

    // 4. Recreate dots from the source kernel's dot structure
    const sourceToReified = new Map<string, string>();
    for (let i = 0; i < slotSignature.slots.length; i++) {
        sourceToReified.set(slotSignature.slots[i].parentNodeId, slotNodeIds[i]);
    }

    for (const dot of sourceKernel.space.dots) {
        const fromReified = sourceToReified.get(dot.from);
        const toReified = sourceToReified.get(dot.to);
        if (fromReified && toReified) {
            addDot(reifiedKernel.space, fromReified, toReified, dot.label);
        }
    }

    // 5. Lock the reified kernel
    const lockResult = lockKernel(registry, reifiedKernel.globalId);
    if (!lockResult.success) {
        console.warn(`Warning: reified kernel #${reifiedKernel.globalId} could not auto-lock:`,
            lockResult.unlockedSlots);
    }

    return {
        kernel: reifiedKernel,
        slotSignature,
        level,
    };
}

// ─── Catastrophe Classes ─────────────────────────────────────
// The 5 catastrophe classes from catastrophe_geometry.md.
// Each is a position on the catastrophe surface — not damage,
// but differentiation. Knowing the class tells you the direction
// that resolves it.
//
// asymmetry → class → direction → symmetry

export type CatastropheClass =
    | 'A'   // "Done" asserted, state not done — sheet with no base point
    | 'B'   // Inheriting prior wrong frame — propagated wrong sheet
    | 'C'   // Same label, different referent — binding collision (fold in Cat(A,R))
    | 'D'   // Summary erased causal fiber — quotient lost the thread
    | 'E';  // Each step more generic — Futamura flattening (projection collapse)

export interface CatastropheEvent {
    class: CatastropheClass;
    level: number;
    detail: string;
    severity: number;     // 0.0-1.0
    folds?: number;       // Distinct inputs collapsing to same orbit
    aliases?: number;     // Ambiguous orbit → multiple possible meanings
    liftable: boolean;    // Can this level participate in higher compilation?
}

export interface TowerResult {
    levels: ReifyResult[];
    catastrophes: CatastropheEvent[];
    sha: number;          // |Ш| — count of non-liftable obstructions
    crowned: boolean;     // Ш = 0 AND lift conditions satisfied
    crownLevel?: number;
}

/**
 * Detect catastrophes between two adjacent tower levels.
 * Uses classes A-E from catastrophe_geometry.md.
 */
function detectCatastrophes(
    prev: SpaceSlotSignature,
    curr: SpaceSlotSignature,
    level: number,
): CatastropheEvent[] {
    const events: CatastropheEvent[] = [];

    const prevOrbitCount = prev.slots.reduce((sum, s) => sum + s.orbits.length, 0);
    const currOrbitCount = curr.slots.reduce((sum, s) => sum + s.orbits.length, 0);

    // Class E — Futamura flattening: orbit count decreases (projection loses dimension)
    if (currOrbitCount < prevOrbitCount) {
        events.push({
            class: 'E',
            level,
            detail: `Orbits: ${prevOrbitCount} → ${currOrbitCount} (lost ${prevOrbitCount - currOrbitCount} dimensions)`,
            severity: (prevOrbitCount - currOrbitCount) / prevOrbitCount,
            liftable: false,
        });
    }

    // Class B — Propagated wrong sheet: new orbits appear from nowhere
    if (currOrbitCount > prevOrbitCount) {
        events.push({
            class: 'B',
            level,
            detail: `Orbits: ${prevOrbitCount} → ${currOrbitCount} (${currOrbitCount - prevOrbitCount} inherited from outside)`,
            severity: (currOrbitCount - prevOrbitCount) / Math.max(currOrbitCount, 1),
            liftable: true,
        });
    }

    // Class D — Quotient lost the thread: configurations decrease
    if (curr.totalConfigurations < prev.totalConfigurations) {
        const ratio = 1 - (curr.totalConfigurations / prev.totalConfigurations);
        events.push({
            class: 'D',
            level,
            detail: `Configurations: ${prev.totalConfigurations} → ${curr.totalConfigurations} (${(ratio * 100).toFixed(1)}% causal fiber erased)`,
            severity: ratio,
            liftable: ratio < 0.5,
        });
    }

    // Class C — Binding collision: same slot count but symmetry groups changed
    // This is fold structure in Cat(A,R) — distinct inputs → same orbit
    if (prev.slots.length === curr.slots.length) {
        let foldCount = 0;
        for (let i = 0; i < prev.slots.length; i++) {
            if (prev.slots[i].symmetryGroup !== curr.slots[i]?.symmetryGroup) {
                foldCount++;
            }
        }
        if (foldCount > 0) {
            events.push({
                class: 'C',
                level,
                detail: `${foldCount} slot(s) changed symmetry group — same label, different referent`,
                severity: foldCount / prev.slots.length,
                folds: foldCount,
                liftable: true,
            });
        }
    }

    return events;
}

/**
 * Apply T repeatedly — build N levels of the Futamura tower.
 *
 * Detects catastrophes (classes A-E), computes |Ш|, and detects
 * crowning (Ш = 0 + lift conditions = Monster-valid fixed point).
 *
 * Crowning = McKay-Thompson convergence. The tower becomes
 * self-hosting as a meta-circular meta-interpreter.
 */
export function buildFutamuraTower(
    registry: Registry,
    sourceKernelId: number,
    levels: number = 3,
): TowerResult {
    const tower: ReifyResult[] = [];
    const catastrophes: CatastropheEvent[] = [];
    let currentKernelId = sourceKernelId;
    let crowned = false;
    let crownLevel: number | undefined;

    for (let level = 0; level < levels; level++) {
        try {
            const result = reifyMineSpace(registry, currentKernelId, level);
            tower.push(result);

            if (tower.length >= 2) {
                const prev = tower[tower.length - 2].slotSignature;
                const curr = result.slotSignature;

                const events = detectCatastrophes(prev, curr, level);
                catastrophes.push(...events);

                // Crowning check: canonical signatures match = potential fixed point
                if (prev.canonical === curr.canonical) {
                    if (prev.totalConfigurations === curr.totalConfigurations &&
                        prev.slots.length === curr.slots.length) {
                        // Check lift conditions: no non-liftable catastrophes
                        const nonLiftable = catastrophes.filter(c => !c.liftable);
                        if (nonLiftable.length === 0) {
                            crowned = true;
                            crownLevel = level;
                            break; // Ш = 0, tower is self-hosting
                        }
                    } else {
                        // Class A — "Done" asserted but state not done
                        catastrophes.push({
                            class: 'A',
                            level,
                            detail: `Canonical matches but configs differ: ${prev.totalConfigurations} vs ${curr.totalConfigurations} — false completion`,
                            severity: 0.8,
                            liftable: false,
                        });
                    }
                }
            }

            currentKernelId = result.kernel.globalId;
        } catch (e) {
            console.warn(`Tower stopped at level ${level}: ${(e as Error).message}`);
            break;
        }
    }

    // |Ш| = count of non-liftable catastrophe events
    const sha = catastrophes.filter(c => !c.liftable).length;

    return { levels: tower, catastrophes, sha, crowned, crownLevel };
}
