/**
 * swarm-agent.ts — MiniMax swarm via sanctuary-dna
 *
 * When the user invokes "swarm" on a CB kernel, this module:
 * 1. Builds a research prompt from the kernel's current state
 * 2. Calls cb_llm_suggest via docker exec into mind_of_god
 * 3. Parses structured actions and applies them as new CB nodes
 */

import { execSync, spawnSync } from 'child_process';
import type { CrystalBall, OntologyNode } from './index';
import { addNode, freezeNode, setAmplitude, getBornWeight, isInSuperposition } from './index';
import { computeMinePlane, type MineResult } from './mine';
import type { Registry } from './index';
import {
    feedSpaceToYouknow,
    queryLabel,
    type YKBatchResult,
    type YKIdea,
} from './youknow-bridge';

// ── Types ────────────────────────────────────────────────────────

export interface SwarmAction {
    label: string;
    parentId: string;
    attributes?: Array<{ name: string; spectrum: string[]; defaultValue: string }>;
}

export interface SwarmPromptContext {
    scryReadout: string;
    targetNodeLabel: string;
    frozenValues: string;
    modeBoundary: string;
    frontierNodes: string;
    n: number;
    strataDisambiguation: string;
}

export interface SwarmResult {
    actions: SwarmAction[];
    rationale: string;
    confidence: number;
    nodesCreated: number;
    raw: string;
}

/** Born-weighted score for a swarm action (interference result) */
export interface BornScore {
    action: SwarmAction;
    bornWeight: number;     // Born weight of target parent (support mask)
    confidence: number;     // LLM's confidence in this action
    interferenceScore: number; // Combined: bornWeight * confidence
    inSupport: boolean;     // Is the parent in the Born support?
}

// ── Prompt Builder ───────────────────────────────────────────────

function describeFrozenNodes(crystal: CrystalBall): string {
    const frozen: string[] = [];
    for (const [, node] of crystal.nodes) {
        if (node.frozen && node.frozenBy) {
            frozen.push(`${node.label} [${node.frozenBy.surrogate}]`);
        } else if (node.frozen) {
            frozen.push(`${node.label} [frozen]`);
        }
    }
    return frozen.length > 0 ? frozen.join(', ') : 'nothing frozen yet';
}

function describeModeBoundary(crystal: CrystalBall, phase: string): string {
    const unfrozen: string[] = [];
    const childless: string[] = [];
    for (const [, node] of crystal.nodes) {
        if (!node.frozen && node.id !== crystal.rootId) {
            unfrozen.push(node.label);
        }
        if (node.children.length === 0 && node.id !== crystal.rootId) {
            childless.push(node.label);
        }
    }

    switch (phase) {
        case 'bloom':
            return `spectrum edges (${childless.length} leaf nodes: ${childless.slice(0, 5).join(', ')}${childless.length > 5 ? '...' : ''})`;
        case 'fill':
            return `empty slots (${childless.length} unfilled: ${childless.slice(0, 5).join(', ')}${childless.length > 5 ? '...' : ''})`;
        case 'lock':
            return `unlocked nodes (${unfrozen.length} pending: ${unfrozen.slice(0, 5).join(', ')}${unfrozen.length > 5 ? '...' : ''})`;
        default:
            return `open structure (${unfrozen.length} unfrozen nodes)`;
    }
}

function describeStrataFromNode(node: OntologyNode | undefined): string {
    if (!node) return 'ontological node';
    if (node.role) return `${node.role} (${node.formalType || 'untyped'})`;
    if (node.children.length > 0) return 'category with children';
    return 'leaf node';
}

function spaceToText(crystal: CrystalBall): string {
    const lines: string[] = [`=== ${crystal.name} ===`];
    function walk(nodeId: string, depth: number) {
        const node = crystal.nodes.get(nodeId);
        if (!node) return;
        const indent = '  '.repeat(depth);
        const status = node.frozen ? '🧊' : node.locked ? '🔒' : '○';
        const role = node.role ? ` [${node.role}]` : '';
        lines.push(`${indent}${status} ${node.label}${role}`);
        for (const childId of node.children) {
            walk(childId, depth + 1);
        }
    }
    walk(crystal.rootId, 0);
    return lines.join('\n');
}

export function buildSwarmPrompt(
    crystal: CrystalBall,
    coordinate: string,
    phase: string,
    mineResult: MineResult,
    n: number = 5,
): SwarmPromptContext {
    const targetNode = coordinate === 'root'
        ? crystal.nodes.get(crystal.rootId)
        : crystal.nodes.get(coordinate);

    const scryReadout = spaceToText(crystal);
    const targetNodeLabel = targetNode?.label ?? coordinate;
    const frozenValues = describeFrozenNodes(crystal);
    const modeBoundary = describeModeBoundary(crystal, phase);
    const frontierNodes = mineResult.thermalFrontier.length > 0
        ? mineResult.thermalFrontier.join(', ')
        : 'no thermal frontier (flat)';
    const strataDisambiguation = describeStrataFromNode(targetNode);

    return {
        scryReadout,
        targetNodeLabel,
        frozenValues,
        modeBoundary,
        frontierNodes,
        n,
        strataDisambiguation,
    };
}

export function renderPrompt(ctx: SwarmPromptContext): string {
    return `I'm working on this ontology:
${ctx.scryReadout}

And I'm wondering about ${ctx.targetNodeLabel} specifically...

See how we have this locked at ${ctx.frozenValues} but it stops at ${ctx.modeBoundary}? We want to deepen ${ctx.frontierNodes}.

Can you give the next ${ctx.n} options that are exactly this type, too ${ctx.strataDisambiguation}?`;
}

// ── Docker Exec Caller ───────────────────────────────────────────

export function execSwarmViaDocker(
    spaceName: string,
    coordinate: string,
    prompt: string,
    n: number = 5,
): SwarmResult {
    const fs = require('fs');
    const os = require('os');
    const path = require('path');

    // Write python script to a temp file — avoids all shell quoting issues
    const tmpFile = path.join(os.tmpdir(), `cb_swarm_${Date.now()}.py`);
    const containerPath = `/tmp/cb_swarm_${Date.now()}.py`;

    const pyPrompt = prompt.replace(/\\/g, '\\\\').replace(/"""/g, '\\"\\"\\"');

    const pythonScript = `
import json, sys, os
os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
os.makedirs('/tmp/heaven_data', exist_ok=True)

from sdna.crystal_ball import cb_llm_suggest
result = cb_llm_suggest(
    space_name=${JSON.stringify(spaceName)},
    coordinate=${JSON.stringify(coordinate)},
    prompt=${JSON.stringify(prompt)},
    model='MiniMax-M2.5-highspeed',
    mode='batch',
    max_actions=${n},
)
print(json.dumps(result))
`.trim();

    try {
        // Write script, copy to container, execute
        fs.writeFileSync(tmpFile, pythonScript, 'utf-8');
        execSync(`docker cp ${tmpFile} mind_of_god:${containerPath}`, { timeout: 5000 });
        fs.unlinkSync(tmpFile);

        // Merge stdout+stderr — heaven may route output through stderr
        const raw = execSync(
            `docker exec mind_of_god python3 ${containerPath} 2>&1`,
            { timeout: 300_000, encoding: 'utf-8', maxBuffer: 2 * 1024 * 1024 },
        ).trim();

        // Clean up container temp file (best-effort)
        try { execSync(`docker exec mind_of_god rm -f ${containerPath}`, { timeout: 3000 }); } catch { }

        // Find the JSON line — stdout may have debug lines before it
        const jsonLine = raw.split('\n').find(l => l.startsWith('{'));
        if (!jsonLine) {
            return {
                actions: [],
                rationale: 'No JSON in MiniMax response',
                confidence: 0,
                nodesCreated: 0,
                raw: raw.slice(0, 500),
            };
        }

        const parsed = JSON.parse(jsonLine);

        // Parse actions from cb_llm_suggest response format:
        // - actions: pre-parsed array (preferred)
        // - suggested_action_json + batch_actions_json: raw XML extraction
        const actions: SwarmAction[] = [];

        if (parsed.actions && Array.isArray(parsed.actions)) {
            actions.push(...parsed.actions);
        } else {
            if (parsed.suggested_action_json) {
                try {
                    const single = typeof parsed.suggested_action_json === 'string'
                        ? JSON.parse(parsed.suggested_action_json)
                        : parsed.suggested_action_json;
                    if (single && single.label) actions.push(single);
                } catch { /* skip */ }
            }
            if (parsed.batch_actions_json) {
                try {
                    const batch: SwarmAction[] = typeof parsed.batch_actions_json === 'string'
                        ? JSON.parse(parsed.batch_actions_json)
                        : parsed.batch_actions_json;
                    if (Array.isArray(batch)) {
                        actions.push(...batch.filter(a => a && a.label));
                    }
                } catch { /* skip */ }
            }
        }

        const rationale: string = parsed.rationale || '';
        const confidence: number = typeof parsed.confidence === 'number'
            ? parsed.confidence
            : parseFloat(String(parsed.confidence)) || 0.5;

        return { actions, rationale, confidence, nodesCreated: 0, raw: jsonLine };

    } catch (err: any) {
        // Clean up temp file if still around
        try { fs.unlinkSync(tmpFile); } catch { }
        return {
            actions: [],
            rationale: `Swarm call failed: ${err.message?.slice(0, 200) || 'unknown error'}`,
            confidence: 0,
            nodesCreated: 0,
            raw: err.stderr?.slice(0, 500) || '',
        };
    }
}

// ── Action Applier ───────────────────────────────────────────────

export function applySwarmActions(
    crystal: CrystalBall,
    actions: SwarmAction[],
): number {
    let created = 0;

    for (const action of actions) {
        // Resolve parent — default to root if not found
        const parentId = crystal.nodes.has(action.parentId)
            ? action.parentId
            : crystal.rootId;

        // Skip if a child with this label already exists under parent
        const parent = crystal.nodes.get(parentId);
        if (parent) {
            const existingLabels = parent.children
                .map(cid => crystal.nodes.get(cid)?.label)
                .filter(Boolean);
            if (existingLabels.includes(action.label)) continue;
        }

        addNode(crystal, parentId, action.label);
        created++;
    }

    return created;
}

// ── Born-Weighted Interference Engine ────────────────────────────
//
// This is where interference COMPUTES. Swarm actions are scored by:
//   1. Born weight of target parent (support mask — excludes Born 0)
//   2. LLM confidence (amplitude of the measurement)
//   3. Combined: interferenceScore = bornWeight × confidence
//
// Actions targeting Born 0 parents are EXCLUDED (not in the domain).
// Actions targeting superposition parents are FAVORED (high Born weight).
// The highest-scoring actions are applied first.

/** Score swarm actions by Born-weighted interference.
 *  Filters out actions whose target parent is Born 0 (not in support).
 *  Ranks remaining by interference score = Born weight × confidence. */
export function scoreSwarmActions(
    crystal: CrystalBall,
    actions: SwarmAction[],
    swarmConfidence: number,
): BornScore[] {
    return actions.map(action => {
        const parent = crystal.nodes.get(action.parentId) ?? crystal.nodes.get(crystal.rootId);
        if (!parent) {
            return {
                action,
                bornWeight: 0,
                confidence: swarmConfidence,
                interferenceScore: 0,
                inSupport: false,
            };
        }

        const bw = getBornWeight(parent);
        return {
            action,
            bornWeight: bw,
            confidence: swarmConfidence,
            interferenceScore: bw * swarmConfidence,
            inSupport: bw > 0,
        };
    }).sort((a, b) => b.interferenceScore - a.interferenceScore);
}

/** Apply swarm actions filtered by Born support mask.
 *  Only actions whose parent is in the Born support (weight > 0) are applied.
 *  Created nodes receive amplitude = swarm confidence (LLM's measurement).
 *  Returns scored results for diagnostics.
 */
export function applySwarmWithBorn(
    crystal: CrystalBall,
    actions: SwarmAction[],
    swarmConfidence: number,
): { scores: BornScore[]; created: number; excluded: number } {
    const scores = scoreSwarmActions(crystal, actions, swarmConfidence);

    let created = 0;
    let excluded = 0;

    for (const scored of scores) {
        if (!scored.inSupport) {
            // Born 0 — not in domain, skip
            excluded++;
            continue;
        }

        const action = scored.action;
        const parentId = crystal.nodes.has(action.parentId)
            ? action.parentId
            : crystal.rootId;

        // Dedup check
        const parent = crystal.nodes.get(parentId);
        if (parent) {
            const existing = parent.children
                .map(cid => crystal.nodes.get(cid)?.label)
                .filter(Boolean);
            if (existing.includes(action.label)) continue;
        }

        // Create node and set amplitude from LLM confidence
        const node = addNode(crystal, parentId, action.label);
        if (node && swarmConfidence > 0) {
            setAmplitude(crystal, node.id, scored.confidence);
        }
        created++;
    }

    return { scores, created, excluded };
}

// ── Orchestrator ─────────────────────────────────────────────────

export function runSwarm(
    registry: Registry,
    spaceName: string,
    coordinate: string,
    phase: string,
    n: number = 5,
): SwarmResult {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found in registry`);

    // 1. Compute mine to find thermal frontier
    const mineResult = computeMinePlane(registry, spaceName, '0');

    // 2. Build prompt from CB state
    const promptCtx = buildSwarmPrompt(space, coordinate, phase, mineResult, n);
    const prompt = renderPrompt(promptCtx);

    // 3. Call MiniMax via docker exec
    const result = execSwarmViaDocker(spaceName, coordinate, prompt, n);

    // 4. Apply via Born-weighted interference engine
    //    Support mask filters out Born 0 parents (unreachable from this encoding).
    //    Remaining actions ranked by interference score = Born × confidence.
    //    Created nodes receive amplitude = LLM confidence.
    if (result.actions.length > 0) {
        const born = applySwarmWithBorn(space, result.actions, result.confidence);
        result.nodesCreated = born.created;
        // TODO: log born.excluded for diagnostics
        // If born.excluded > 0, some actions targeted Born 0 parents
        // = LLM tried to navigate to unreachable parts of the space
    }

    return result;
}

// ── YOUKNOW-Enriched Swarm ───────────────────────────────────────

export interface SwarmWithYKResult extends SwarmResult {
    youknow: YKBatchResult;
    ideasApplied: number;
}

/**
 * Run the swarm, then feed all labels to YOUKNOW for ideas.
 * Ideas become additional CB nodes. Everything goes in.
 *
 * Flow:
 *   1. Run normal LLM swarm → creates nodes
 *   2. Feed all space labels to YOUKNOW
 *   3. YOUKNOW returns ideas (broken chains, missing slots)
 *   4. Ideas become new CB nodes
 *   5. Return combined result
 */
export function runSwarmWithYouknow(
    registry: Registry,
    spaceName: string,
    coordinate: string,
    phase: string,
    n: number = 5,
): SwarmWithYKResult {
    // 1. Normal swarm (LLM generates nodes)
    const swarmResult = runSwarm(registry, spaceName, coordinate, phase, n);

    // 2. Feed entire space to YOUKNOW
    const space = registry.spaces.get(spaceName);
    if (!space) {
        return {
            ...swarmResult,
            youknow: {
                results: [],
                allIdeas: [],
                admitted: [],
                soup: [],
                convergenceRatio: 0,
            },
            ideasApplied: 0,
        };
    }

    const ykResult = feedSpaceToYouknow(space);

    // 3. Apply YOUKNOW ideas as new CB nodes (everything goes in)
    let ideasApplied = 0;
    for (const idea of ykResult.allIdeas) {
        // Find a suitable parent for this idea
        let parentId = space.rootId;

        if (idea.parentLabel) {
            for (const [nid, node] of space.nodes) {
                if (node.label === idea.parentLabel) {
                    parentId = nid;
                    break;
                }
            }
        }

        // Skip if this label already exists anywhere
        let exists = false;
        for (const [, node] of space.nodes) {
            if (node.label === idea.label) {
                exists = true;
                break;
            }
        }
        if (exists) continue;

        // Add the node — everything goes in
        addNode(space, parentId, idea.label);
        ideasApplied++;
    }

    return {
        ...swarmResult,
        nodesCreated: swarmResult.nodesCreated + ideasApplied,
        youknow: ykResult,
        ideasApplied,
    };
}

// ── Algebra-Neighborhood Batch Swarm ─────────────────────────────
//
// THE REAL TRICK: instead of calling the LLM once per node,
// group related nodes into NEIGHBORHOODS using the algebra product,
// send ONE call per neighborhood with ALL the context,
// and fill MULTIPLE coordinates per call.
//
// The algebra product tells us which nodes are related:
//   non-zero a*x = x is in a's neighborhood.
// Connected neighborhoods get ONE prompt with maximum information.

/** Get parent node ID (shared helper) */
function parentOf(nodeId: string): string | null {
    if (nodeId === 'root') return null;
    const dot = nodeId.lastIndexOf('.');
    return dot === -1 ? 'root' : nodeId.substring(0, dot);
}

/** Compute algebra product weight between two nodes (same logic as index.ts) */
function algebraNeighborWeight(
    space: CrystalBall, aId: string, xId: string,
): number {
    if (aId === xId) return 1;
    const aParent = parentOf(aId);
    const xParent = parentOf(xId);
    if (xParent === aId) {
        const a = space.nodes.get(aId);
        return 1 / Math.max(a?.children.length ?? 1, 1);
    }
    if (aParent === xId) {
        const x = space.nodes.get(xId);
        return 1 / Math.max(x?.children.length ?? 1, 1);
    }
    if (aParent && aParent === xParent) {
        const p = space.nodes.get(aParent);
        return 1 / Math.max(p?.children.length ?? 1, 1);
    }
    return 0;
}

export interface AlgebraNeighborhood {
    /** The "anchor" node — highest Born weight node in this neighborhood */
    anchorId: string;
    anchorLabel: string;
    /** All nodes in this neighborhood (connected by non-zero product) */
    memberIds: string[];
    memberLabels: string[];
    /** Superposition members (unfilled — these are what the LLM should fill) */
    superpositionIds: string[];
    /** Locked/frozen members (these give context) */
    contextIds: string[];
    /** The locked context chain (labels from root to anchor) */
    contextChain: string[];
}

/**
 * Group superposition nodes into algebra neighborhoods.
 *
 * Two nodes are neighbors if they have non-zero algebra product weight.
 * Connected components of the neighborhood graph become one group.
 * Each group gets ONE LLM call with maximum context.
 */
export function computeAlgebraNeighborhoods(
    space: CrystalBall,
): AlgebraNeighborhood[] {
    const nodeIds = Array.from(space.nodes.keys());
    const superIds = nodeIds.filter(id => {
        const n = space.nodes.get(id)!;
        return isInSuperposition(n);
    });

    if (superIds.length === 0) return [];

    // Build adjacency: superposition nodes connected by non-zero product
    const adj = new Map<string, Set<string>>();
    for (const a of superIds) {
        if (!adj.has(a)) adj.set(a, new Set());
        for (const b of superIds) {
            if (a === b) continue;
            if (algebraNeighborWeight(space, a, b) > 0) {
                adj.get(a)!.add(b);
                if (!adj.has(b)) adj.set(b, new Set());
                adj.get(b)!.add(a);
            }
        }
    }

    // Also connect superposition nodes to their locked/frozen neighbors
    // (these provide context but aren't targets)
    const contextFor = new Map<string, string[]>();
    for (const s of superIds) {
        const ctx: string[] = [];
        for (const id of nodeIds) {
            const n = space.nodes.get(id)!;
            if ((n.locked || n.frozen) && algebraNeighborWeight(space, s, id) > 0) {
                ctx.push(id);
            }
        }
        contextFor.set(s, ctx);
    }

    // Find connected components
    const visited = new Set<string>();
    const neighborhoods: AlgebraNeighborhood[] = [];

    for (const start of superIds) {
        if (visited.has(start)) continue;

        // BFS
        const component: string[] = [];
        const queue = [start];
        while (queue.length > 0) {
            const curr = queue.shift()!;
            if (visited.has(curr)) continue;
            visited.add(curr);
            component.push(curr);
            for (const neighbor of (adj.get(curr) ?? [])) {
                if (!visited.has(neighbor)) queue.push(neighbor);
            }
        }

        // Find anchor (highest Born weight in component)
        let anchor = component[0];
        let bestBorn = getBornWeight(space.nodes.get(anchor)!);
        for (const id of component) {
            const bw = getBornWeight(space.nodes.get(id)!);
            if (bw > bestBorn || (bw === bestBorn && id.split('.').length > anchor.split('.').length)) {
                anchor = id;
                bestBorn = bw;
            }
        }

        // Collect context (locked/frozen neighbors of any component member)
        const allContext = new Set<string>();
        for (const id of component) {
            for (const ctx of (contextFor.get(id) ?? [])) {
                allContext.add(ctx);
            }
        }

        // Build context chain from root to anchor
        const chain: string[] = [];
        let curr: string | null = anchor;
        while (curr) {
            const n = space.nodes.get(curr);
            if (n && (n.locked || n.frozen)) chain.unshift(n.label);
            curr = parentOf(curr);
        }

        neighborhoods.push({
            anchorId: anchor,
            anchorLabel: space.nodes.get(anchor)?.label ?? anchor,
            memberIds: component,
            memberLabels: component.map(id => space.nodes.get(id)?.label ?? id),
            superpositionIds: component,
            contextIds: Array.from(allContext),
            contextChain: chain,
        });
    }

    // Sort by total Born weight (highest priority first)
    neighborhoods.sort((a, b) => {
        const bornA = a.superpositionIds.reduce((s, id) =>
            s + getBornWeight(space.nodes.get(id)!), 0);
        const bornB = b.superpositionIds.reduce((s, id) =>
            s + getBornWeight(space.nodes.get(id)!), 0);
        return bornB - bornA;
    });

    return neighborhoods;
}

/**
 * Build a batch prompt for a neighborhood.
 *
 * Instead of asking about ONE node, includes ALL context from the
 * neighborhood so the LLM can reason about related coordinates together.
 */
export function buildBatchPrompt(
    space: CrystalBall,
    neighborhood: AlgebraNeighborhood,
    n: number = 5,
): string {
    const lines: string[] = [];

    // Context: what's already determined
    lines.push(`I'm working on this ontology:`);
    lines.push(spaceToText(space));
    lines.push('');

    // What's locked (the anchor chain)
    if (neighborhood.contextChain.length > 0) {
        lines.push(`We've determined: ${neighborhood.contextChain.join(' → ')}`);
    }

    // Context nodes (locked/frozen neighbors)
    if (neighborhood.contextIds.length > 0) {
        const ctxLabels = neighborhood.contextIds.map(id =>
            space.nodes.get(id)?.label ?? id
        );
        lines.push(`Related locked concepts: ${ctxLabels.join(', ')}`);
    }

    // The ask: fill ALL superposition members
    lines.push('');
    if (neighborhood.superpositionIds.length === 1) {
        lines.push(`What belongs under "${neighborhood.anchorLabel}"?`);
        lines.push(`Give ${n} options.`);
    } else {
        const labels = neighborhood.memberLabels.filter(l => l !== neighborhood.anchorLabel);
        lines.push(`I need to fill these related positions simultaneously:`);
        lines.push(`  Main: "${neighborhood.anchorLabel}"`);
        if (labels.length > 0) {
            lines.push(`  Also related: ${labels.join(', ')}`);
        }
        lines.push('');
        lines.push(`Since you know what ${neighborhood.anchorLabel} is about,`);
        lines.push(`you also know what these related positions should contain.`);
        lines.push(`Give ${n} options for EACH position.`);
        lines.push(`Format: POSITION: option1, option2, ...`);
    }

    return lines.join('\n');
}

/**
 * Run batch swarm: one LLM call per algebra neighborhood.
 *
 * This is the key optimization:
 *   N nodes, K neighborhoods → K calls instead of N
 *   Each call has MORE context → better fills
 *   Neighborhoods are independent → parallelizable
 */
export function runBatchSwarm(
    registry: Registry,
    spaceName: string,
    maxNeighborhoods: number = 5,
    nPerNeighborhood: number = 5,
): { neighborhoods: AlgebraNeighborhood[]; results: SwarmResult[]; totalCreated: number } {
    const space = registry.spaces.get(spaceName);
    if (!space) throw new Error(`Space "${spaceName}" not found`);

    const neighborhoods = computeAlgebraNeighborhoods(space);
    const activeNeighborhoods = neighborhoods.slice(0, maxNeighborhoods);

    const results: SwarmResult[] = [];
    let totalCreated = 0;

    // Each neighborhood gets one swarm call with its batch prompt
    // TODO: make this actually parallel with Promise.all when we have async swarm
    for (const hood of activeNeighborhoods) {
        const prompt = buildBatchPrompt(space, hood, nPerNeighborhood);

        // Call swarm with the batch prompt, anchored at the neighborhood's anchor
        const result = execSwarmViaDocker(spaceName, hood.anchorId, prompt, nPerNeighborhood);

        // Apply results via Born interference
        if (result.actions.length > 0) {
            const born = applySwarmWithBorn(space, result.actions, result.confidence);
            result.nodesCreated = born.created;
        }

        results.push(result);
        totalCreated += result.nodesCreated;
    }

    return { neighborhoods: activeNeighborhoods, results, totalCreated };
}
