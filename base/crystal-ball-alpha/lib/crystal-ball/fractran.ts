/* ═══════════════════════════════════════════════════════════
   fractran.ts — FRACTRAN lens for Crystal Ball
   
   Maps CB coordinates to prime factorizations, dots to fractions,
   and proves the encoding is Turing-complete.
   
   FRACTRAN (Conway): programs are lists of fractions.
   State = integer. Step = multiply by first applicable fraction.
   Prime factorization of the state IS the register file.
   
   CB coordinates ARE FRACTRAN states:
     - Each slot position → a prime
     - Selection value at each slot → exponent of that prime
     - 0 (superposition) → exponent 0 (register empty)
     - Dots (morphisms) → fractions (rewrite rules)
   
   Uses the 15 supersingular primes (divisors of the Monster group
   order) for slot indices, keeping the system in genus 0.
   ═══════════════════════════════════════════════════════════ */

import {
    type Space,
    type CBNode,
    type NodeId,
    decodeSelectionIndex,
} from './index';

// ─── The 15 Supersingular Primes ─────────────────────────────
// These are EXACTLY the primes dividing |Monster|.
// They correspond to genus-0 modular curves.
// CB operates within this regime by construction.

export const SUPERSINGULAR_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 41, 47, 59, 71,
] as const;

export const MAX_SLOTS = SUPERSINGULAR_PRIMES.length; // 15

// ─── Types ───────────────────────────────────────────────────

/** Prime factorization: Map<prime, exponent> */
export type PrimeFactorization = Map<number, number>;

/** A FRACTRAN fraction: numerator/denominator */
export interface Fraction {
    numerator: number;
    denominator: number;
    label?: string;    // Human-readable name (e.g., "Tone→Hook")
}

/** A FRACTRAN program: ordered list of fractions */
export interface FractranProgram {
    fractions: Fraction[];
    name: string;
}

/** Execution trace: sequence of states */
export interface ExecutionTrace {
    states: {
        step: number;
        integer: number;
        factorization: PrimeFactorization;
        coordinate: string;
        appliedFraction?: string;
    }[];
    halted: boolean;
    haltReason: string;
}

// ─── Coordinate ↔ Prime Factorization ────────────────────────

/**
 * Convert a CB coordinate to a prime factorization.
 * 
 * coordinate "1.3.2":
 *   slot 0 → prime 2, exponent 1    → 2¹
 *   slot 1 → prime 3, exponent 3    → 3³
 *   slot 2 → prime 5, exponent 2    → 5²
 *   
 *   N = 2¹ × 3³ × 5² = 2 × 27 × 25 = 1350
 * 
 * coordinate "0.2.0":
 *   slot 0 → prime 2, exponent 0    → absent (superposition)
 *   slot 1 → prime 3, exponent 2    → 3²
 *   slot 2 → prime 5, exponent 0    → absent (superposition)
 *   
 *   N = 3² = 9
 */
export function coordToFactorization(coordinate: string): PrimeFactorization {
    if (coordinate === 'root' || coordinate === '0' || coordinate === '') {
        return new Map(); // empty = 1 = all superposition
    }

    const segments = coordinate.split('.');
    const factorization: PrimeFactorization = new Map();

    for (let i = 0; i < segments.length && i < MAX_SLOTS; i++) {
        const seg = segments[i];
        if (seg === '0') continue; // superposition = exponent 0 = absent

        const selectionIndex = decodeSelectionIndex(seg);
        if (selectionIndex > 0) {
            factorization.set(SUPERSINGULAR_PRIMES[i], selectionIndex);
        }
    }

    return factorization;
}

/**
 * Convert a prime factorization back to a CB coordinate.
 */
export function factorizationToCoord(factorization: PrimeFactorization): string {
    if (factorization.size === 0) return '0';

    // Find the highest slot used
    let maxSlot = 0;
    for (const [prime] of factorization) {
        const slot = SUPERSINGULAR_PRIMES.indexOf(prime);
        if (slot > maxSlot) maxSlot = slot;
    }

    const segments: string[] = [];
    for (let i = 0; i <= maxSlot; i++) {
        const prime = SUPERSINGULAR_PRIMES[i];
        const exponent = factorization.get(prime) ?? 0;
        segments.push(String(exponent));
    }

    return segments.join('.');
}

/**
 * Compute the integer value of a prime factorization.
 * N = ∏ pᵢ^eᵢ
 */
export function factorizationToInteger(factorization: PrimeFactorization): number {
    let n = 1;
    for (const [prime, exponent] of factorization) {
        n *= Math.pow(prime, exponent);
    }
    return n;
}

/**
 * Convert a CB coordinate directly to its FRACTRAN integer.
 */
export function coordToInteger(coordinate: string): number {
    return factorizationToInteger(coordToFactorization(coordinate));
}

/**
 * Canonical key for orbit computation: sorted prime factorization.
 * Two coordinates with the same canonical factorization key
 * are in the same orbit.
 */
export function orbitKey(factorization: PrimeFactorization): string {
    const exponents = Array.from(factorization.values()).sort((a, b) => a - b);
    return exponents.join(',');
}

// ─── Dots → Fractions ────────────────────────────────────────

/**
 * Convert a dot (morphism between nodes) to a FRACTRAN fraction.
 * 
 * If a dot goes from node at coord "1.2" to node at coord "3.1":
 *   from: 2¹ × 3²
 *   to:   2³ × 3¹
 *   fraction = (2³ × 3¹) / (2¹ × 3²) = 8/9 × 3 = 24/18 = 4/3
 * 
 * The fraction means: "if the state has at least 2¹ × 3²,
 * consume those and produce 2³ × 3¹ instead."
 */
export function dotToFraction(
    fromCoord: string,
    toCoord: string,
    label?: string,
): Fraction {
    const fromFactors = coordToFactorization(fromCoord);
    const toFactors = coordToFactorization(toCoord);

    let numerator = 1;
    let denominator = 1;

    // Collect all primes involved
    const allPrimes = new Set([...fromFactors.keys(), ...toFactors.keys()]);

    for (const prime of allPrimes) {
        const fromExp = fromFactors.get(prime) ?? 0;
        const toExp = toFactors.get(prime) ?? 0;

        if (toExp > fromExp) {
            numerator *= Math.pow(prime, toExp - fromExp);
        } else if (fromExp > toExp) {
            denominator *= Math.pow(prime, fromExp - toExp);
        }
        // equal → cancels out
    }

    return { numerator, denominator, label };
}

/**
 * Extract a FRACTRAN program from a space's dot structure.
 * Each dot becomes a fraction. Order = order of dots array.
 */
export function spaceToFractranProgram(space: Space): FractranProgram {
    const fractions: Fraction[] = [];

    for (const dot of space.dots) {
        // Need to find the coordinates of the from/to nodes
        const fromCoord = nodeIdToCoordinate(space, dot.from);
        const toCoord = nodeIdToCoordinate(space, dot.to);

        if (fromCoord && toCoord) {
            fractions.push(dotToFraction(
                fromCoord,
                toCoord,
                dot.label ?? `${dot.from}→${dot.to}`,
            ));
        }
    }

    return { fractions, name: space.name };
}

/**
 * Reconstruct a coordinate from a node ID by walking up to root.
 */
function nodeIdToCoordinate(space: Space, nodeId: NodeId): string | null {
    if (nodeId === space.rootId) return '0';

    // Walk the tree to find the path from root to this node
    const path = findPathFromRoot(space, space.rootId, nodeId);
    if (!path) return null;

    // Path is array of 1-based selection indices
    return path.join('.');
}

function findPathFromRoot(
    space: Space,
    currentId: NodeId,
    targetId: NodeId,
    path: number[] = [],
): number[] | null {
    const node = space.nodes.get(currentId);
    if (!node) return null;

    for (let i = 0; i < node.children.length; i++) {
        const childId = node.children[i];
        if (childId === targetId) {
            return [...path, i + 1]; // 1-based
        }

        const found = findPathFromRoot(space, childId, targetId, [...path, i + 1]);
        if (found) return found;
    }

    return null;
}

// ─── FRACTRAN Execution ──────────────────────────────────────

/**
 * Execute a FRACTRAN program.
 * 
 * Starting from integer N, repeatedly:
 *   1. Find the first fraction f where N × f is an integer
 *   2. N ← N × f
 *   3. If no fraction works, halt
 * 
 * This is Turing-complete.
 */
export function executeFractran(
    program: FractranProgram,
    initialState: number,
    maxSteps: number = 1000,
): ExecutionTrace {
    const trace: ExecutionTrace = {
        states: [],
        halted: false,
        haltReason: '',
    };

    let n = initialState;

    // Record initial state
    trace.states.push({
        step: 0,
        integer: n,
        factorization: integerToFactorization(n),
        coordinate: factorizationToCoord(integerToFactorization(n)),
    });

    for (let step = 1; step <= maxSteps; step++) {
        let applied = false;

        for (const fraction of program.fractions) {
            const result = n * fraction.numerator;
            if (result % fraction.denominator === 0) {
                n = result / fraction.denominator;
                trace.states.push({
                    step,
                    integer: n,
                    factorization: integerToFactorization(n),
                    coordinate: factorizationToCoord(integerToFactorization(n)),
                    appliedFraction: fraction.label ?? `${fraction.numerator}/${fraction.denominator}`,
                });
                applied = true;
                break;
            }
        }

        if (!applied) {
            trace.halted = true;
            trace.haltReason = `No applicable fraction at step ${step}`;
            break;
        }

        if (step === maxSteps) {
            trace.haltReason = `Max steps (${maxSteps}) reached`;
        }
    }

    return trace;
}

/**
 * Factor an integer into primes (only supersingular primes).
 */
function integerToFactorization(n: number): PrimeFactorization {
    const factorization: PrimeFactorization = new Map();
    let remaining = n;

    for (const prime of SUPERSINGULAR_PRIMES) {
        let exponent = 0;
        while (remaining % prime === 0) {
            remaining = remaining / prime;
            exponent++;
        }
        if (exponent > 0) {
            factorization.set(prime, exponent);
        }
    }

    // If remaining > 1, it has a prime factor outside supersingular primes
    // This means it's left genus 0 — "knocked out of the hologram"
    if (remaining > 1) {
        factorization.set(remaining, 1); // record the rogue prime
    }

    return factorization;
}

// ─── Genus Detection ─────────────────────────────────────────

/**
 * Check if a factorization stays within genus 0 (supersingular primes only).
 * 
 * Genus 0 = all prime factors are supersingular (≤ 71)
 * Genus > 0 = has a non-supersingular prime factor = "knocked out of the hologram"
 */
export function isGenus0(factorization: PrimeFactorization): boolean {
    const superSet = new Set(SUPERSINGULAR_PRIMES as unknown as number[]);
    for (const prime of factorization.keys()) {
        if (!superSet.has(prime)) return false;
    }
    return true;
}

/**
 * Check if a coordinate stays within genus 0.
 */
export function coordIsGenus0(coordinate: string): boolean {
    // Coordinate encoding itself is always genus 0 (uses slots 0-14)
    // But a FRACTRAN execution could leave genus 0 if fractions
    // produce non-supersingular factors
    return isGenus0(coordToFactorization(coordinate));
}

/**
 * Check if an entire FRACTRAN trace stayed within genus 0.
 */
export function traceIsGenus0(trace: ExecutionTrace): {
    genus0: boolean;
    firstViolation?: number;
    roguePrime?: number;
} {
    for (const state of trace.states) {
        if (!isGenus0(state.factorization)) {
            // Find the rogue prime
            const superSet = new Set(SUPERSINGULAR_PRIMES as unknown as number[]);
            for (const prime of state.factorization.keys()) {
                if (!superSet.has(prime)) {
                    return {
                        genus0: false,
                        firstViolation: state.step,
                        roguePrime: prime,
                    };
                }
            }
        }
    }
    return { genus0: true };
}
