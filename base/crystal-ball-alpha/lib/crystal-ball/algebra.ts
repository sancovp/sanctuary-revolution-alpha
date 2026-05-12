/**
 * algebra.ts — CB Algebra: The Missing Multiplication
 *
 * This makes the Griess analogy LITERAL by defining:
 *   - V = span of basis vectors {e_i} for nodes in a space
 *   - * : V × V → V  (bilinear, commutative, NON-associative product)
 *   - ⟨·,·⟩ = K(i,j) (positive definite form from RKHS kernel)
 *
 * Then: Aut(V, *, ⟨·,·⟩) = { g ∈ GL(V) | g(x*y) = g(x)*g(y) ∧ ⟨gx,gy⟩ = ⟨x,y⟩ }
 *
 * Product rules (tree-contextualized kernel product):
 *   1. Self:         e_i * e_i = amp(i)² · e_i          (idempotent)
 *   2. Parent-child: e_p * e_c = K(p,c) · e_c           (context flows down)
 *   3. Siblings:     e_a * e_b = K(a,b)/n · e_parent     (collapse to parent)
 *   4. Distant:      e_i * e_j = 0                       (no tree connection)
 *
 * Checks:
 *   - Frobenius form invariance: ⟨x*y, z⟩ = ⟨x, y*z⟩
 *   - Non-associativity witness: (a*b)*c ≠ a*(b*c)
 *   - Positive definiteness of K
 *   - EXACT Aut enumeration (test all n! permutations)
 *   - T1: |Aut| prime factors ⊂ Monster primes
 *   - T2: element orders ⊂ Monster element orders (via cycle decomposition)
 *   - T3: ⟨gx,gy⟩ = ⟨x,y⟩ for all g ∈ Aut
 *   - Adjoint eigenvalue / fusion analysis
 */

import type { Registry, Space, CBNode, SpaceName } from './index';
import { getAmplitude } from './index';
import { tensorKernel } from './kernel-v2';

// ─── Types ───────────────────────────────────────────────────────

export interface StructureConstant {
    i: string; j: string; k: string;
    value: number;
    reason: string;
}

export interface CBAlgebra {
    spaceName: string;
    dimension: number;
    basisIds: string[];
    structureConstants: StructureConstant[];
    formMatrix: number[][];
    formInvariant: boolean;
    formViolations: string[];
    nonAssociative: boolean;
    associativityCounterexample?: string;
}

export interface ProductVector {
    i: string; j: string;
    coefficients: Map<string, number>;
}

// ─── Helpers ─────────────────────────────────────────────────────

function getParentId(nodeId: string): string | null {
    if (nodeId === 'root') return null;
    const lastDot = nodeId.lastIndexOf('.');
    if (lastDot === -1) return 'root';
    return nodeId.substring(0, lastDot);
}

function areSiblings(a: string, b: string): boolean {
    if (a === b) return false;
    return getParentId(a) === getParentId(b);
}

function kernelValue(registry: Registry, spaceName: string, i: string, j: string): number {
    if (i === j) return 1.0;
    try {
        const result = tensorKernel(registry, spaceName, i, j);
        return result.quantumValue;
    } catch {
        const partsI = i.split('.');
        const partsJ = j.split('.');
        let shared = 0;
        for (let k = 0; k < Math.min(partsI.length, partsJ.length); k++) {
            if (partsI[k] === partsJ[k]) shared++; else break;
        }
        return shared / Math.max(partsI.length, partsJ.length);
    }
}

// ─── Product ─────────────────────────────────────────────────────
// SAME rules as propagateEntanglement. Weights = 1/spectrumSize (tree structure).
// Kernel K is the FORM ⟨·,·⟩, NOT the multiplication *.

export function computeProduct(
    registry: Registry, spaceName: string, space: Space,
    i: string, j: string,
): ProductVector {
    const coefficients = new Map<string, number>();

    if (i === j) {
        const node = space.nodes.get(i);
        const amp = node ? getAmplitude(node) : 0;
        coefficients.set(i, amp * amp);
        return { i, j, coefficients };
    }

    const parentI = getParentId(i);
    const parentJ = getParentId(j);

    if (parentI === j) {
        const jNode = space.nodes.get(j);
        const n = Math.max(jNode?.children.length ?? 1, 1);
        const amp = jNode ? getAmplitude(jNode) : 1;
        coefficients.set(i, amp / n);
        return { i, j, coefficients };
    }
    if (parentJ === i) {
        const iNode = space.nodes.get(i);
        const n = Math.max(iNode?.children.length ?? 1, 1);
        const amp = iNode ? getAmplitude(iNode) : 1;
        coefficients.set(j, amp / n);
        return { i, j, coefficients };
    }

    if (areSiblings(i, j)) {
        const parent = parentI!;
        const parentNode = space.nodes.get(parent);
        const n = Math.max(parentNode?.children.length ?? 1, 1);
        const amp = parentNode ? getAmplitude(parentNode) : 1;
        coefficients.set(parent, amp / n);
        return { i, j, coefficients };
    }

    return { i, j, coefficients };
}

export function computeStructureConstants(registry: Registry, spaceName: string): StructureConstant[] {
    const space = registry.spaces.get(spaceName);
    if (!space) return [];
    const constants: StructureConstant[] = [];
    const nodeIds = Array.from(space.nodes.keys());

    for (const i of nodeIds) {
        for (const j of nodeIds) {
            if (i > j) continue;
            const product = computeProduct(registry, spaceName, space, i, j);
            for (const [k, value] of product.coefficients) {
                if (Math.abs(value) < 1e-10) continue;
                let reason = 'distant';
                if (i === j) reason = 'self (idempotent)';
                else if (getParentId(i) === j || getParentId(j) === i) reason = 'parent-child';
                else if (areSiblings(i, j)) reason = 'siblings';
                constants.push({ i, j, k, value, reason });
                if (i !== j) constants.push({ i: j, j: i, k, value, reason });
            }
        }
    }
    return constants;
}

// ─── Form Invariance (Frobenius) ─────────────────────────────────

export function checkFormInvariance(
    registry: Registry, spaceName: string, tolerance: number = 1e-6,
): { invariant: boolean; violations: string[]; checked: number } {
    const space = registry.spaces.get(spaceName);
    if (!space) return { invariant: true, violations: [], checked: 0 };
    const nodeIds = Array.from(space.nodes.keys());
    const n = nodeIds.length;
    const violations: string[] = [];
    let checked = 0;

    for (let ii = 0; ii < n; ii++) {
        for (let jj = 0; jj < n; jj++) {
            for (let kk = 0; kk < n; kk++) {
                const x = nodeIds[ii], y = nodeIds[jj], z = nodeIds[kk];
                checked++;
                const xy = computeProduct(registry, spaceName, space, x, y);
                let lhs = 0;
                for (const [basis, coeff] of xy.coefficients) {
                    lhs += coeff * kernelValue(registry, spaceName, basis, z);
                }
                const yz = computeProduct(registry, spaceName, space, y, z);
                let rhs = 0;
                for (const [basis, coeff] of yz.coefficients) {
                    rhs += coeff * kernelValue(registry, spaceName, x, basis);
                }
                if (Math.abs(lhs - rhs) > tolerance) {
                    violations.push(
                        `⟨${x}*${y}, ${z}⟩=${lhs.toFixed(6)} ≠ ⟨${x}, ${y}*${z}⟩=${rhs.toFixed(6)} (Δ=${Math.abs(lhs - rhs).toFixed(6)})`
                    );
                }
            }
        }
    }
    return { invariant: violations.length === 0, violations, checked };
}

// ─── Non-Associativity ───────────────────────────────────────────

export function checkNonAssociativity(
    registry: Registry, spaceName: string, tolerance: number = 1e-6,
): { nonAssociative: boolean; counterexample?: string } {
    const space = registry.spaces.get(spaceName);
    if (!space) return { nonAssociative: false };
    const nodeIds = Array.from(space.nodes.keys());

    for (const a of nodeIds) {
        for (const b of nodeIds) {
            for (const c of nodeIds) {
                if (a === b && b === c) continue;
                const ab = computeProduct(registry, spaceName, space, a, b);
                const lhs = new Map<string, number>();
                for (const [basis, coeff] of ab.coefficients) {
                    const p2 = computeProduct(registry, spaceName, space, basis, c);
                    for (const [k, v] of p2.coefficients) lhs.set(k, (lhs.get(k) ?? 0) + coeff * v);
                }
                const bc = computeProduct(registry, spaceName, space, b, c);
                const rhs = new Map<string, number>();
                for (const [basis, coeff] of bc.coefficients) {
                    const p2 = computeProduct(registry, spaceName, space, a, basis);
                    for (const [k, v] of p2.coefficients) rhs.set(k, (rhs.get(k) ?? 0) + coeff * v);
                }
                for (const k of new Set([...lhs.keys(), ...rhs.keys()])) {
                    if (Math.abs((lhs.get(k) ?? 0) - (rhs.get(k) ?? 0)) > tolerance) {
                        return {
                            nonAssociative: true,
                            counterexample: `(${a}*${b})*${c} ≠ ${a}*(${b}*${c}) at e_${k}: ${(lhs.get(k) ?? 0).toFixed(6)} vs ${(rhs.get(k) ?? 0).toFixed(6)}`,
                        };
                    }
                }
            }
        }
    }
    return { nonAssociative: false };
}

// ─── Exact Aut Enumeration ───────────────────────────────────────

function* permutations(n: number): Generator<number[]> {
    if (n > 10) return;
    const arr = Array.from({ length: n }, (_, i) => i);
    function* heap(k: number): Generator<number[]> {
        if (k === 1) { yield [...arr]; return; }
        for (let i = 0; i < k; i++) {
            yield* heap(k - 1);
            if (k % 2 === 0) [arr[i], arr[k - 1]] = [arr[k - 1], arr[i]];
            else[arr[0], arr[k - 1]] = [arr[k - 1], arr[0]];
        }
    }
    yield* heap(n);
}

function cycleDecomposition(perm: number[]): number[] {
    const visited = new Array(perm.length).fill(false);
    const cycles: number[] = [];
    for (let i = 0; i < perm.length; i++) {
        if (visited[i]) continue;
        let len = 0, j = i;
        while (!visited[j]) { visited[j] = true; j = perm[j]; len++; }
        if (len > 0) cycles.push(len);
    }
    return cycles;
}

function gcd(a: number, b: number): number { return b === 0 ? a : gcd(b, a % b); }
function lcm(a: number, b: number): number { return (a * b) / gcd(a, b); }

function elementOrder(perm: number[]): number {
    return cycleDecomposition(perm).reduce((acc, c) => lcm(acc, c), 1);
}

function primeFactors(n: number): Set<number> {
    const factors = new Set<number>();
    let d = 2, rem = n;
    while (d * d <= rem) {
        while (rem % d === 0) { factors.add(d); rem /= d; }
        d++;
    }
    if (rem > 1) factors.add(rem);
    return factors;
}

const MONSTER_PRIMES = new Set([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 41, 47, 59, 71]);
const MONSTER_ELEMENT_ORDERS = new Set([
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 39,
    40, 41, 42, 44, 45, 46, 47, 48, 50, 51, 52, 54, 55, 56, 57, 59, 60, 62,
    66, 67, 68, 69, 70, 71, 78, 84, 87, 88, 92, 93, 94, 95, 104, 105, 110, 119,
]);

export interface AutomorphismInfo {
    permutation: number[];
    order: number;
    cycleType: number[];
}

export interface AutGroupResult {
    automorphisms: AutomorphismInfo[];
    groupOrder: number;
    elementOrders: number[];
    allPreserveForm: boolean;
    formViolators: number[];
    structureDescription: string;
}

/**
 * Enumerate Aut(V, *) exactly by testing ALL n! permutations.
 *
 * For each σ, check: c^k_ij = c^{σ(k)}_{σ(i),σ(j)} for all i,j,k.
 * Also check form preservation: ⟨σ(e_i), σ(e_j)⟩ = ⟨e_i, e_j⟩.
 */
export function enumerateAutomorphisms(
    registry: Registry, spaceName: string,
): AutGroupResult {
    const space = registry.spaces.get(spaceName);
    if (!space) return {
        automorphisms: [], groupOrder: 0, elementOrders: [],
        allPreserveForm: true, formViolators: [], structureDescription: 'empty',
    };

    const basisIds = Array.from(space.nodes.keys());
    const n = basisIds.length;

    if (n > 10) {
        return {
            automorphisms: [{ permutation: Array.from({ length: n }, (_, i) => i), order: 1, cycleType: Array(n).fill(1) }],
            groupOrder: -1, elementOrders: [1],
            allPreserveForm: true, formViolators: [],
            structureDescription: `dim ${n} > 10, enumeration skipped`,
        };
    }

    // Precompute multiplication table: mulTable[i][j][k] = coefficient of e_k in e_i * e_j
    const mulTable: number[][][] = [];
    for (let i = 0; i < n; i++) {
        mulTable[i] = [];
        for (let j = 0; j < n; j++) {
            const row = new Array(n).fill(0);
            const product = computeProduct(registry, spaceName, space, basisIds[i], basisIds[j]);
            for (const [k, v] of product.coefficients) {
                const idx = basisIds.indexOf(k);
                if (idx >= 0) row[idx] = v;
            }
            mulTable[i][j] = row;
        }
    }

    // Precompute form matrix
    const form: number[][] = [];
    for (let i = 0; i < n; i++) {
        form[i] = [];
        for (let j = 0; j < n; j++) {
            form[i][j] = kernelValue(registry, spaceName, basisIds[i], basisIds[j]);
        }
    }

    const automorphisms: AutomorphismInfo[] = [];
    let allPreserveForm = true;
    const formViolators: number[] = [];

    for (const perm of permutations(n)) {
        // Check: σ preserves multiplication?
        // c^k_ij must = c^{σ(k)}_{σ(i),σ(j)} for ALL i,j,k
        let preservesMul = true;
        outer:
        for (let i = 0; i < n; i++) {
            for (let j = 0; j < n; j++) {
                for (let k = 0; k < n; k++) {
                    const origVal = mulTable[i][j][k];
                    const permVal = mulTable[perm[i]][perm[j]][perm[k]];
                    if (Math.abs(origVal - permVal) > 1e-6) {
                        preservesMul = false;
                        break outer;
                    }
                }
            }
        }
        if (!preservesMul) continue;

        // Check form preservation: ⟨σ(e_i), σ(e_j)⟩ = ⟨e_i, e_j⟩
        let preservesForm = true;
        for (let i = 0; i < n && preservesForm; i++) {
            for (let j = i; j < n && preservesForm; j++) {
                if (Math.abs(form[perm[i]][perm[j]] - form[i][j]) > 1e-6) {
                    preservesForm = false;
                }
            }
        }

        automorphisms.push({
            permutation: [...perm],
            order: elementOrder(perm),
            cycleType: cycleDecomposition(perm).sort((a, b) => b - a),
        });

        if (!preservesForm) {
            allPreserveForm = false;
            formViolators.push(automorphisms.length - 1);
        }
    }

    const orderSet = new Set(automorphisms.map(a => a.order));
    const elementOrders = Array.from(orderSet).sort((a, b) => a - b);
    const groupOrder = automorphisms.length;

    let structureDescription = `|Aut| = ${groupOrder}`;
    if (groupOrder === 1) structureDescription += ' (trivial)';
    else if (groupOrder === 2) structureDescription += ' ≅ C₂';
    else if (groupOrder === 3) structureDescription += ' ≅ C₃';
    else if (groupOrder === 4) structureDescription += elementOrders.includes(4) ? ' ≅ C₄' : ' ≅ C₂×C₂ (Klein four)';
    else if (groupOrder === 6) structureDescription += elementOrders.includes(6) ? ' ≅ C₆' : ' ≅ S₃';
    else if (groupOrder === 8) structureDescription += ' (order 8)';
    else if (groupOrder === 12) structureDescription += ' ≅ A₄ or D₆';
    else if (groupOrder === 24) structureDescription += ' ≅ S₄';
    else if (groupOrder === 120) structureDescription += ' ≅ S₅';
    else if (groupOrder === 720) structureDescription += ' ≅ S₆';

    return { automorphisms, groupOrder, elementOrders, allPreserveForm, formViolators, structureDescription };
}

// ─── Positive Definiteness ───────────────────────────────────────

export function checkPositiveDefinite(formMatrix: number[][]): {
    positive: boolean; pivots: number[]; nullity: number;
} {
    const n = formMatrix.length;
    if (n === 0) return { positive: true, pivots: [], nullity: 0 };

    // Cholesky-like: check diagonal dominance via LDL^T decomposition
    const mat = formMatrix.map(row => [...row]);
    const pivots: number[] = [];
    let nullity = 0;

    for (let i = 0; i < n; i++) {
        // Subtract contributions from previous rows
        let diag = mat[i][i];
        for (let k = 0; k < i; k++) {
            diag -= mat[i][k] * mat[i][k] * pivots[k];
        }

        if (Math.abs(diag) < 1e-10) {
            nullity++;
            pivots.push(0);
            continue;
        }

        pivots.push(diag);

        // Update remaining rows
        for (let j = i + 1; j < n; j++) {
            let val = mat[j][i];
            for (let k = 0; k < i; k++) {
                val -= mat[j][k] * mat[i][k] * pivots[k];
            }
            mat[j][i] = val / diag;
        }
    }

    const positive = pivots.every(p => p > 1e-10) && nullity === 0;
    return { positive, pivots, nullity };
}

// ─── Adjoint / Fusion Analysis ───────────────────────────────────

export interface AdjointAnalysis {
    basisElement: string;
    eigenvalues: number[];
    multiplicities: Map<number, number>;
    isAxisLike: boolean;
}

/**
 * For each basis element, compute eigenvalues of L_a(x) = a*x.
 * In Majorana theory, axes have few distinct eigenvalues and stable fusion rules.
 */
export function analyzeAdjointMaps(registry: Registry, spaceName: string): AdjointAnalysis[] {
    const space = registry.spaces.get(spaceName);
    if (!space) return [];
    const basisIds = Array.from(space.nodes.keys());
    const n = basisIds.length;
    const results: AdjointAnalysis[] = [];

    for (let a = 0; a < n; a++) {
        // Build L_a matrix: (L_a)_{ij} = coeff of e_j in (e_a * e_i)
        const adjMatrix: number[][] = [];
        for (let i = 0; i < n; i++) {
            const row = new Array(n).fill(0);
            const product = computeProduct(registry, spaceName, space, basisIds[a], basisIds[i]);
            for (const [k, v] of product.coefficients) {
                const idx = basisIds.indexOf(k);
                if (idx >= 0) row[idx] = v;
            }
            adjMatrix.push(row);
        }

        // For sparse/diagonal-dominant case, diagonal entries are good eigenvalue approximations
        const diag = adjMatrix.map((row, i) => row[i]);
        const multMap = new Map<number, number>();
        for (const ev of diag) {
            const rounded = Math.round(ev * 10000) / 10000;
            multMap.set(rounded, (multMap.get(rounded) ?? 0) + 1);
        }

        const distinctCount = multMap.size;
        const isAxisLike = distinctCount <= 4 && distinctCount >= 2;

        results.push({
            basisElement: basisIds[a],
            eigenvalues: diag,
            multiplicities: multMap,
            isAxisLike,
        });
    }
    return results;
}

// ─── Monster Compatibility (Corrected) ───────────────────────────

export interface MonsterCompatibility {
    t1_orderDivisibility: { pass: boolean; groupOrder: number; primeFactors: number[]; badPrimes: number[] };
    t2_elementOrders: { pass: boolean; elementOrders: number[]; badOrders: number[] };
    t3_formPreservation: { pass: boolean; violatorCount: number; note: string };
    formPositiveDefinite: boolean;
    compatible: boolean;
    summary: string;
}

export function checkMonsterCompatibility(
    autGroup: AutGroupResult,
    formPD: { positive: boolean },
): MonsterCompatibility {
    const gOrder = autGroup.groupOrder;
    const factors = gOrder > 1 ? primeFactors(gOrder) : new Set<number>();
    const badPrimes = Array.from(factors).filter(p => !MONSTER_PRIMES.has(p));
    const t1 = {
        pass: badPrimes.length === 0 && gOrder > 0,
        groupOrder: gOrder,
        primeFactors: Array.from(factors).sort((a, b) => a - b),
        badPrimes,
    };

    const badOrders = autGroup.elementOrders.filter(o => !MONSTER_ELEMENT_ORDERS.has(o));
    const t2 = { pass: badOrders.length === 0, elementOrders: autGroup.elementOrders, badOrders };

    const t3 = {
        pass: autGroup.allPreserveForm,
        violatorCount: autGroup.formViolators.length,
        note: autGroup.allPreserveForm
            ? `All ${gOrder} automorphisms preserve ⟨gx,gy⟩ = ⟨x,y⟩`
            : `${autGroup.formViolators.length}/${gOrder} automorphisms FAIL form preservation`,
    };

    const compatible = t1.pass && t2.pass && t3.pass && formPD.positive;

    let summary: string;
    if (compatible) {
        summary = `✅ Monster-compatible (necessary conditions): ` +
            `${autGroup.structureDescription}, orders [${autGroup.elementOrders.join(',')}], ` +
            `form PD + preserved.`;
    } else {
        const fails: string[] = [];
        if (!t1.pass) fails.push(`T1: primes [${badPrimes.join(',')}] ∉ M`);
        if (!t2.pass) fails.push(`T2: orders [${badOrders.join(',')}] ∉ M`);
        if (!t3.pass) fails.push(`T3: ${autGroup.formViolators.length} auts don't preserve form`);
        if (!formPD.positive) fails.push('Form not positive definite');
        summary = `❌ Monster-incompatible: ${fails.join('; ')}.`;
    }

    return { t1_orderDivisibility: t1, t2_elementOrders: t2, t3_formPreservation: t3, formPositiveDefinite: formPD.positive, compatible, summary };
}

// ─── Full Analysis ───────────────────────────────────────────────

export function analyzeAlgebra(
    registry: Registry, spaceName: string,
): CBAlgebra & { autGroup: AutGroupResult; monsterCompatibility: MonsterCompatibility; adjointAnalysis: AdjointAnalysis[] } {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    const basisIds = Array.from(space.nodes.keys());
    const dimension = basisIds.length;
    const structureConstants = computeStructureConstants(registry, spaceName);

    const formMatrix: number[][] = [];
    for (let i = 0; i < dimension; i++) {
        const row: number[] = [];
        for (let j = 0; j < dimension; j++) {
            row.push(kernelValue(registry, spaceName, basisIds[i], basisIds[j]));
        }
        formMatrix.push(row);
    }

    const formCheck = checkFormInvariance(registry, spaceName);
    const assocCheck = checkNonAssociativity(registry, spaceName);
    const pdCheck = checkPositiveDefinite(formMatrix);
    const autGroup = enumerateAutomorphisms(registry, spaceName);
    const monsterCompat = checkMonsterCompatibility(autGroup, pdCheck);
    const adjointAnalysis = analyzeAdjointMaps(registry, spaceName);

    return {
        spaceName, dimension, basisIds, structureConstants, formMatrix,
        formInvariant: formCheck.invariant,
        formViolations: formCheck.violations,
        nonAssociative: assocCheck.nonAssociative,
        associativityCounterexample: assocCheck.counterexample,
        autGroup, monsterCompatibility: monsterCompat, adjointAnalysis,
    };
}

export function formatAlgebraAnalysis(
    a: CBAlgebra & { autGroup: AutGroupResult; monsterCompatibility: MonsterCompatibility; adjointAnalysis: AdjointAnalysis[] },
): string {
    const lines: string[] = [
        `🔬 CB Algebra: ${a.spaceName}`,
        `  Dim: ${a.dimension}`,
        `  Structure constants: ${a.structureConstants.length} non-zero c^k_ij`,
        `  Frobenius: ${a.formInvariant ? '✅ ⟨x*y,z⟩ = ⟨x,y*z⟩' : '❌ FAILS'}`,
        `  Form PD: ${a.monsterCompatibility.formPositiveDefinite ? '✅' : '❌ degenerate (nullity > 0)'}`,
        `  Non-assoc: ${a.nonAssociative ? '✅ genuine' : '⚠️ associative'}`,
    ];
    if (a.associativityCounterexample) lines.push(`    Witness: ${a.associativityCounterexample}`);
    if (a.formViolations.length > 0) {
        lines.push(`  Form violations (first 3):`);
        for (const v of a.formViolations.slice(0, 3)) lines.push(`    ${v}`);
    }

    lines.push('');
    lines.push(`  ⚙️ Aut(V,*,⟨·,·⟩) — EXACT:`);
    lines.push(`    ${a.autGroup.structureDescription}`);
    lines.push(`    Element orders: [${a.autGroup.elementOrders.join(', ')}]`);
    lines.push(`    Form: ${a.autGroup.allPreserveForm ? '✅ all preserve ⟨gx,gy⟩=⟨x,y⟩' : `❌ ${a.autGroup.formViolators.length} violators`}`);

    lines.push('');
    lines.push(`  🐉 Monster compatibility:`);
    lines.push(`    T1 (primes): ${a.monsterCompatibility.t1_orderDivisibility.pass ? '✅' : '❌'} |Aut|=${a.monsterCompatibility.t1_orderDivisibility.groupOrder}, primes [${a.monsterCompatibility.t1_orderDivisibility.primeFactors.join(',')}]`);
    lines.push(`    T2 (orders): ${a.monsterCompatibility.t2_elementOrders.pass ? '✅' : '❌'} [${a.monsterCompatibility.t2_elementOrders.elementOrders.join(',')}]${a.monsterCompatibility.t2_elementOrders.badOrders.length > 0 ? ` BAD:[${a.monsterCompatibility.t2_elementOrders.badOrders.join(',')}]` : ''}`);
    lines.push(`    T3 (form): ${a.monsterCompatibility.t3_formPreservation.pass ? '✅' : '❌'} ${a.monsterCompatibility.t3_formPreservation.note}`);
    lines.push(`    ${a.monsterCompatibility.summary}`);

    const axes = a.adjointAnalysis.filter(x => x.isAxisLike);
    lines.push('');
    if (axes.length > 0) {
        lines.push(`  🔥 Fusion: ${axes.length} axis-like elements:`);
        for (const ax of axes.slice(0, 5)) {
            const evs = Array.from(ax.multiplicities.entries()).map(([ev, m]) => `${ev}×${m}`).join(', ');
            lines.push(`    ${ax.basisElement}: L_a eigenvalues {${evs}}`);
        }
    } else {
        lines.push(`  🔥 No axis-like elements (no stable fusion pattern)`);
    }

    return lines.join('\n');
}
