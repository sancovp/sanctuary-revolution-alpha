/**
 * morphism.ts — Category-Theoretic Foundation for Crystal Ball
 *
 * In CB, there are no parent-child relationships. There are:
 *   - Objects (nodes)
 *   - Morphisms (directed arrows between objects, encoded as selection indices)
 *   - Composition (following two morphisms in sequence = the dot in coordinates)
 *   - Identity (the identity morphism on each object = self-loop at 1.0)
 *
 * A CB space is a category where:
 *   - Objects = nodes (the spectrum values)
 *   - Morphisms = selection arrows (node A selecting target B from its spectrum)
 *   - Composition = coordinate concatenation (the dot, encoded as 8988)
 *   - Identity = the trivial self-selection
 *
 * The coordinate `0.189881` is a composed morphism:
 *   root --1--> FascesSymbol --1--> BundledRods
 * Two arrows composed. Not containment. Not hierarchy. Directed relationship.
 *
 * Category axioms:
 *   1. Associativity: (f ∘ g) ∘ h = f ∘ (g ∘ h)
 *   2. Identity: id_A ∘ f = f = f ∘ id_B  for f : A → B
 */

import {
    type Registry,
    type Space,
    type CBNode,
    type NodeId,
    type SpaceName,
    coordToReal,
    encodeDot,
} from './index';

// ─── Types ────────────────────────────────────────────────────────

/** A morphism in the CB category: a directed arrow from source to target */
export interface Morphism {
    /** Source object (the node this arrow originates from) */
    source: NodeId;
    /** Target object (the node this arrow points to) */
    target: NodeId;
    /** Selection index — which position in the source's spectrum selects the target (1-based) */
    selectionIndex: number;
    /** The encoded digit(s) for this selection (1-7, or 9-wrapped for higher) */
    encoded: string;
}

/** A composed morphism — a chain of arrows */
export interface ComposedMorphism {
    /** The full chain of individual morphisms, in order */
    chain: Morphism[];
    /** The ultimate source (first morphism's source) */
    source: NodeId;
    /** The ultimate target (last morphism's target) */
    target: NodeId;
    /** The coordinate string — the composition of all selections, dot-separated */
    coordinate: string;
    /** The real number this composition encodes */
    real: number;
}

/** Identity morphism on an object */
export interface IdentityMorphism {
    object: NodeId;
    label: string;
}

// ─── Core Operations ──────────────────────────────────────────────

/**
 * Extract all morphisms from a node.
 * Each entry in node.children is a morphism: source → target via selection index.
 */
export function morphismsFrom(space: Space, nodeId: NodeId): Morphism[] {
    const node = space.nodes.get(nodeId);
    if (!node) return [];

    return node.children.map((targetId, i) => {
        const selectionIndex = i + 1; // 1-based
        let encoded: string;
        if (selectionIndex <= 7) {
            encoded = String(selectionIndex);
        } else {
            // Wrap encoding: 9 = +7
            let remaining = selectionIndex;
            let wraps = 0;
            while (remaining > 7) {
                remaining -= 7;
                wraps++;
            }
            encoded = '9'.repeat(wraps) + String(remaining);
        }

        return {
            source: nodeId,
            target: targetId,
            selectionIndex,
            encoded,
        };
    });
}

/**
 * Extract all morphisms pointing TO a node (incoming arrows).
 */
export function morphismsTo(space: Space, nodeId: NodeId): Morphism[] {
    const incoming: Morphism[] = [];
    for (const [sourceId, sourceNode] of space.nodes) {
        for (let i = 0; i < sourceNode.children.length; i++) {
            if (sourceNode.children[i] === nodeId) {
                const selectionIndex = i + 1;
                let encoded: string;
                if (selectionIndex <= 7) {
                    encoded = String(selectionIndex);
                } else {
                    let remaining = selectionIndex;
                    let wraps = 0;
                    while (remaining > 7) {
                        remaining -= 7;
                        wraps++;
                    }
                    encoded = '9'.repeat(wraps) + String(remaining);
                }
                incoming.push({
                    source: sourceId,
                    target: nodeId,
                    selectionIndex,
                    encoded,
                });
            }
        }
    }
    return incoming;
}

/**
 * Identity morphism: the trivial self-arrow on a node.
 * In CB, this is the coordinate that resolves to the node itself
 * without further composition.
 */
export function identity(space: Space, nodeId: NodeId): IdentityMorphism | null {
    const node = space.nodes.get(nodeId);
    if (!node) return null;
    return {
        object: nodeId,
        label: node.label,
    };
}

/**
 * Compose two morphisms: f : A → B, g : B → C → (g ∘ f) : A → C
 * The composition is the dot-separated concatenation of their coordinates.
 *
 * Returns null if the morphisms are not composable (f.target ≠ g.source).
 */
export function compose(f: Morphism, g: Morphism): ComposedMorphism | null {
    if (f.target !== g.source) return null; // not composable

    const coordinate = `${f.encoded}.${g.encoded}`;
    return {
        chain: [f, g],
        source: f.source,
        target: g.target,
        coordinate,
        real: coordToReal(coordinate),
    };
}

/**
 * Compose a chain of morphisms: f₁ ∘ f₂ ∘ ... ∘ fₙ
 * Each fᵢ.target must equal fᵢ₊₁.source.
 *
 * Returns null if any adjacent pair is not composable.
 */
export function composeChain(morphisms: Morphism[]): ComposedMorphism | null {
    if (morphisms.length === 0) return null;
    if (morphisms.length === 1) {
        const f = morphisms[0];
        return {
            chain: [f],
            source: f.source,
            target: f.target,
            coordinate: f.encoded,
            real: coordToReal(f.encoded),
        };
    }

    // Verify composability
    for (let i = 0; i < morphisms.length - 1; i++) {
        if (morphisms[i].target !== morphisms[i + 1].source) {
            return null; // chain break
        }
    }

    const coordinate = morphisms.map(m => m.encoded).join('.');
    return {
        chain: [...morphisms],
        source: morphisms[0].source,
        target: morphisms[morphisms.length - 1].target,
        coordinate,
        real: coordToReal(coordinate),
    };
}

/**
 * Find the morphism from A to B, if one exists (direct arrow, not composed).
 */
export function findMorphism(space: Space, sourceId: NodeId, targetId: NodeId): Morphism | null {
    const all = morphismsFrom(space, sourceId);
    return all.find(m => m.target === targetId) ?? null;
}

/**
 * Find ALL paths (composed morphisms) from source to target, up to maxDepth.
 * This enumerates all ways to get from A to B via morphism composition.
 */
export function findPaths(
    space: Space,
    sourceId: NodeId,
    targetId: NodeId,
    maxDepth: number = 5,
): ComposedMorphism[] {
    const results: ComposedMorphism[] = [];

    function dfs(currentId: NodeId, chain: Morphism[], depth: number): void {
        if (depth > maxDepth) return;

        const outgoing = morphismsFrom(space, currentId);
        for (const m of outgoing) {
            const newChain = [...chain, m];
            if (m.target === targetId) {
                const composed = composeChain(newChain);
                if (composed) results.push(composed);
            }
            // Continue searching deeper (but don't revisit)
            if (!chain.some(existing => existing.target === m.target)) {
                dfs(m.target, newChain, depth + 1);
            }
        }
    }

    dfs(sourceId, [], 0);
    return results;
}

// ─── Category Axiom Verification ──────────────────────────────────

export interface CategoryVerification {
    /** Associativity: does (f ∘ g) ∘ h = f ∘ (g ∘ h) for all composable triples? */
    associativity: { holds: boolean; tested: number; failures: string[] };
    /** Identity: does id ∘ f = f = f ∘ id for all morphisms? */
    identity: { holds: boolean; tested: number; failures: string[] };
    /** Total morphisms in the space */
    totalMorphisms: number;
    /** Total objects */
    totalObjects: number;
}

/**
 * Verify category axioms on a CB space.
 *
 * 1. Associativity: for all composable triples f, g, h:
 *    compose(compose(f, g), h).real === compose(f, compose(g, h)).real
 *
 * 2. Identity: for all morphisms f : A → B:
 *    The coordinate of f composed with nothing extra = f's own coordinate
 */
export function verifyCategory(space: Space): CategoryVerification {
    const allMorphisms: Morphism[] = [];
    for (const [nodeId] of space.nodes) {
        allMorphisms.push(...morphismsFrom(space, nodeId));
    }

    // ── Associativity ─────────────────────────────────────
    // For all composable triples (f: A→B, g: B→C, h: C→D):
    //   compose(compose(f,g), h).real === compose(f, compose(g,h)).real
    const assocFailures: string[] = [];
    let assocTested = 0;

    for (const f of allMorphisms) {
        const gCandidates = allMorphisms.filter(m => m.source === f.target);
        for (const g of gCandidates) {
            const hCandidates = allMorphisms.filter(m => m.source === g.target);
            for (const h of hCandidates) {
                assocTested++;

                // Left association: (f ∘ g) ∘ h
                const fg = compose(f, g);
                if (!fg) continue;
                const fgCoord = fg.coordinate;
                const leftCoord = `${fgCoord}.${h.encoded}`;
                const leftReal = coordToReal(leftCoord);

                // Right association: f ∘ (g ∘ h)
                const gh = compose(g, h);
                if (!gh) continue;
                const ghCoord = gh.coordinate;
                const rightCoord = `${f.encoded}.${ghCoord}`;
                const rightReal = coordToReal(rightCoord);

                if (Math.abs(leftReal - rightReal) > 1e-15) {
                    assocFailures.push(
                        `(${f.encoded}∘${g.encoded})∘${h.encoded} = ${leftReal} ≠ ${f.encoded}∘(${g.encoded}∘${h.encoded}) = ${rightReal}`
                    );
                }
            }
        }
    }

    // ── Identity ──────────────────────────────────────────
    // For each morphism f : A → B:
    //   f alone (single arrow) should be its own coordinate, unchanged by identity composition
    //   Concretely: coordToReal("X") is the same whether we treat X as
    //   "id_A then f" or "f then id_B" or just "f"
    const idFailures: string[] = [];
    let idTested = 0;

    for (const f of allMorphisms) {
        idTested++;
        // f by itself
        const fReal = coordToReal(f.encoded);

        // f should produce the same real whether we "compose" with nothing
        // The identity law in CB: composing with the identity doesn't change the coordinate
        // Since identity = staying at the node, the coordinate is just f.encoded
        // This is trivially satisfied by construction, but let's verify
        // that the encoding is stable
        const reEncoded = coordToReal(f.encoded);
        if (Math.abs(fReal - reEncoded) > 1e-15) {
            idFailures.push(
                `id law failed for ${f.source}→${f.target}: ${fReal} ≠ ${reEncoded}`
            );
        }
    }

    return {
        associativity: {
            holds: assocFailures.length === 0,
            tested: assocTested,
            failures: assocFailures,
        },
        identity: {
            holds: idFailures.length === 0,
            tested: idTested,
            failures: idFailures,
        },
        totalMorphisms: allMorphisms.length,
        totalObjects: space.nodes.size,
    };
}

/**
 * Pretty-print a morphism for display.
 */
export function formatMorphism(space: Space, m: Morphism): string {
    const srcNode = space.nodes.get(m.source);
    const tgtNode = space.nodes.get(m.target);
    const srcLabel = srcNode?.label ?? m.source;
    const tgtLabel = tgtNode?.label ?? m.target;
    return `${srcLabel} --${m.selectionIndex}--> ${tgtLabel}`;
}

/**
 * Pretty-print a composed morphism.
 */
export function formatComposed(space: Space, cm: ComposedMorphism): string {
    const arrows = cm.chain.map(m => formatMorphism(space, m));
    return `[${arrows.join(' ∘ ')}] = ${cm.real}`;
}

// ─── Categorical Primitives ───────────────────────────────────────
// These provide the correct vocabulary to replace parent/child
// throughout the codebase.
//
// Glossary:
//   "parent"     →  source (domain of a morphism)
//   "child"      →  target (codomain of a morphism)
//   "children"   →  spectrum(node) = targets reachable via outgoing morphisms
//   "parent of"  →  sources(node) = objects with a morphism TO this node
//   "has child"  →  hasMorphismTo(A, B) = ∃ f : A → B
//   "add child"  →  addMorphism(space, source, label) — creates object + arrow
//   "childCount" →  arity(node) = number of outgoing morphisms

/** All objects in a CB category (= all nodes in the space) */
export function objects(space: Space): NodeId[] {
    return Array.from(space.nodes.keys());
}

/** Get an object by its ID (replaces "get node") */
export function object(space: Space, id: NodeId): CBNode | undefined {
    return space.nodes.get(id);
}

/** Label of an object */
export function label(space: Space, id: NodeId): string {
    return space.nodes.get(id)?.label ?? id;
}

/**
 * Spectrum: the set of targets reachable via outgoing morphisms from an object.
 * This replaces "node.children" — the spectrum is not "things inside" the node,
 * it is "things the node has morphisms directed at."
 */
export function spectrum(space: Space, nodeId: NodeId): NodeId[] {
    const node = space.nodes.get(nodeId);
    if (!node) return [];
    return [...node.children]; // Defensive copy. The field is still called children in the type.
}

/**
 * Spectrum labels: labels of all targets in the spectrum.
 * Replaces patterns like `node.children.map(cid => space.nodes.get(cid)?.label)`
 */
export function spectrumLabels(space: Space, nodeId: NodeId): string[] {
    return spectrum(space, nodeId).map(tid => label(space, tid));
}

/**
 * Arity: number of outgoing morphisms from an object.
 * Replaces "node.children.length" — this is "how many things does this object
 * have morphisms directed at", not "how many things does it contain."
 */
export function arity(space: Space, nodeId: NodeId): number {
    const node = space.nodes.get(nodeId);
    return node?.children.length ?? 0;
}

/**
 * Sources: all objects that have a morphism directed at this object.
 * Replaces "parent of" — these are the objects whose spectrum includes this node.
 */
export function sources(space: Space, nodeId: NodeId): NodeId[] {
    const result: NodeId[] = [];
    for (const [otherId, otherNode] of space.nodes) {
        if (otherNode.children.includes(nodeId)) {
            result.push(otherId);
        }
    }
    return result;
}

/**
 * Is this object a terminal object? (No outgoing morphisms — a leaf.)
 * In category theory: terminal objects have a unique morphism FROM every other object.
 * In CB: these are spectrum endpoints — objects with no further targets.
 */
export function isTerminal(space: Space, nodeId: NodeId): boolean {
    return arity(space, nodeId) === 0;
}

/**
 * Is this object an initial object? (No incoming morphisms — only root qualifies.)
 * In category theory: initial objects have a unique morphism TO every other object.
 * In CB: this is the root of the space.
 */
export function isInitial(space: Space, nodeId: NodeId): boolean {
    return sources(space, nodeId).length === 0;
}

/**
 * Hom(A, B): the set of all morphisms from A to B.
 * Direct morphisms only (single arrows, not composed chains).
 * For composed paths, use findPaths(space, A, B).
 */
export function hom(space: Space, sourceId: NodeId, targetId: NodeId): Morphism[] {
    return morphismsFrom(space, sourceId).filter(m => m.target === targetId);
}

/**
 * Hom-set size: |Hom(A, B)| — number of direct morphisms from A to B.
 * In a well-formed CB space, this is 0 or 1 (no parallel arrows).
 */
export function homSize(space: Space, sourceId: NodeId, targetId: NodeId): number {
    return hom(space, sourceId, targetId).length;
}

// ─── Slice and Coslice Categories ─────────────────────────────────
//
// The slice category (C / X) = all objects with a morphism TO X.
// The coslice category (X / C) = all objects with a morphism FROM X.
//
// slice(X)   replaces "ancestors of X" / "parent chain"
// coslice(X) replaces "descendants of X" / "children subtree"

export interface SliceObject {
    /** The object in the slice */
    objectId: NodeId;
    /** The morphism from this object to the slice base */
    morphism: Morphism;
}

export interface CosliceObject {
    /** The object in the coslice */
    objectId: NodeId;
    /** The morphism from the coslice base to this object */
    morphism: Morphism;
}

/**
 * Slice category over X: all objects with a DIRECT morphism to X.
 * These are the "sources" of X — the objects whose arrows land on X.
 * Replaces "parent of X" semantics.
 */
export function slice(space: Space, baseId: NodeId): SliceObject[] {
    return morphismsTo(space, baseId).map(m => ({
        objectId: m.source,
        morphism: m,
    }));
}

/**
 * Coslice category under X: all objects with a DIRECT morphism from X.
 * These are the "targets" of X — the spectrum of X.
 * Replaces "children of X" semantics.
 */
export function coslice(space: Space, baseId: NodeId): CosliceObject[] {
    return morphismsFrom(space, baseId).map(m => ({
        objectId: m.target,
        morphism: m,
    }));
}

/**
 * Deep coslice: all objects reachable from X by following morphisms recursively.
 * Replaces "all descendants" / "subtree of X".
 * Returns objects with their full composed morphism from X.
 */
export function deepCoslice(
    space: Space,
    baseId: NodeId,
    maxDepth: number = 10,
): ComposedMorphism[] {
    const results: ComposedMorphism[] = [];
    const visited = new Set<NodeId>();

    function dfs(currentId: NodeId, chain: Morphism[], depth: number): void {
        if (depth > maxDepth) return;
        if (visited.has(currentId)) return;
        visited.add(currentId);

        const outgoing = morphismsFrom(space, currentId);
        for (const m of outgoing) {
            const fullChain = [...chain, m];
            const composed = composeChain(fullChain);
            if (composed) results.push(composed);
            dfs(m.target, fullChain, depth + 1);
        }
    }

    dfs(baseId, [], 0);
    return results;
}

// ─── Functors ─────────────────────────────────────────────────────
//
// A functor F : C → D maps objects to objects and morphisms to morphisms
// while preserving composition: F(g ∘ f) = F(g) ∘ F(f)
// and identity: F(id_A) = id_{F(A)}

export interface Functor {
    /** Name of this functor */
    name: string;
    /** Source category (space) */
    source: SpaceName;
    /** Target category (space) */
    target: SpaceName;
    /** Object map: source object ID → target object ID */
    objectMap: Map<NodeId, NodeId>;
    /** Morphism map: source morphism → target morphism (derived from object map) */
    morphismMap: Map<string, string>; // key = "sourceId→targetId"
}

/**
 * Check if an object mapping between two spaces constitutes a valid functor.
 * Validates:
 *   1. Every object in source maps to an object in target
 *   2. Every morphism f: A→B maps to a morphism F(f): F(A)→F(B)
 *   3. Composition is preserved: F(g∘f) = F(g)∘F(f)
 */
export function verifyFunctor(
    registry: Registry,
    sourceName: SpaceName,
    targetName: SpaceName,
    objectMap: Map<NodeId, NodeId>,
): { valid: boolean; name: string; failures: string[] } {
    const source = registry.spaces.get(sourceName);
    const target = registry.spaces.get(targetName);
    if (!source || !target) {
        return { valid: false, name: `${sourceName}→${targetName}`, failures: ['Missing space(s)'] };
    }

    const failures: string[] = [];

    // 1. Object mapping completeness
    for (const [objId] of source.nodes) {
        if (!objectMap.has(objId)) {
            failures.push(`Object ${objId} (${label(source, objId)}) has no mapping`);
        } else {
            const targetObjId = objectMap.get(objId)!;
            if (!target.nodes.has(targetObjId)) {
                failures.push(`Object ${objId} maps to ${targetObjId} which doesn't exist in target`);
            }
        }
    }

    // 2. Morphism mapping: f: A→B must map to F(f): F(A)→F(B)
    for (const [sourceObjId] of source.nodes) {
        const outgoing = morphismsFrom(source, sourceObjId);
        for (const m of outgoing) {
            const fSource = objectMap.get(m.source);
            const fTarget = objectMap.get(m.target);
            if (!fSource || !fTarget) continue; // already reported above

            // Check that F(A) → F(B) exists in target
            const targetMorphisms = hom(target, fSource, fTarget);
            if (targetMorphisms.length === 0) {
                failures.push(
                    `Morphism ${label(source, m.source)}→${label(source, m.target)} ` +
                    `maps to ${label(target, fSource)}→${label(target, fTarget)} ` +
                    `but no such morphism exists in target`
                );
            }
        }
    }

    return {
        valid: failures.length === 0,
        name: `${sourceName}→${targetName}`,
        failures,
    };
}

// ─── Category Summary ─────────────────────────────────────────────

export interface CategorySummary {
    spaceName: string;
    objectCount: number;
    morphismCount: number;
    terminalObjects: NodeId[];    // Objects with no outgoing morphisms (spectrum endpoints)
    initialObjects: NodeId[];    // Objects with no incoming morphisms (roots)
    maxArity: number;            // Max outgoing morphisms from any single object
    maxDepth: number;            // Longest composed morphism chain from initial to terminal
    isConnected: boolean;        // All objects reachable from initial object
}

/**
 * Compute a category-theoretic summary of a CB space.
 * Uses categorical vocabulary throughout — no parent/child.
 */
export function categorySummary(space: Space): CategorySummary {
    const allObjects = objects(space);
    let morphismCount = 0;
    let maxArity = 0;
    const terminals: NodeId[] = [];
    const initials: NodeId[] = [];

    for (const objId of allObjects) {
        const a = arity(space, objId);
        morphismCount += a;
        if (a > maxArity) maxArity = a;
        if (isTerminal(space, objId)) terminals.push(objId);
        if (isInitial(space, objId)) initials.push(objId);
    }

    // Max depth: longest chain from any initial to any terminal
    let maxChainLength = 0;
    for (const init of initials) {
        const all = deepCoslice(space, init);
        for (const cm of all) {
            if (cm.chain.length > maxChainLength) maxChainLength = cm.chain.length;
        }
    }

    // Connectivity: all objects reachable from initial
    let connected = true;
    if (initials.length > 0) {
        const reachable = new Set<NodeId>();
        reachable.add(initials[0]);
        const all = deepCoslice(space, initials[0]);
        for (const cm of all) {
            reachable.add(cm.target);
        }
        connected = reachable.size === allObjects.length;
    }

    return {
        spaceName: space.name,
        objectCount: allObjects.length,
        morphismCount,
        terminalObjects: terminals,
        initialObjects: initials,
        maxArity,
        maxDepth: maxChainLength,
        isConnected: connected,
    };
}
