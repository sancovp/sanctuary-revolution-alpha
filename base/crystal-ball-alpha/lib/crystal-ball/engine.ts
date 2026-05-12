/**
 * Crystal Ball SaaS — Engine Layer
 * 
 * ONE function: cb(teamId, input)
 * 
 * input is a string. That's it.
 * 
 * The kernel is a SHELL. It has state. When you scry something,
 * it either:
 *   1. Returns a VIEW (here's what's at this coordinate)
 *   2. Returns an INTERACTION (fill this slot, select from spectrum)
 *   3. Returns a DELIVERABLE (the final resolved state)
 * 
 * There are no commands. There is only the coordinate space
 * and the state machine that tracks where you are in it.
 */

import { db } from '@/lib/db/drizzle';
import { spaces } from '@/lib/db/schema';
import { execSync } from 'child_process';
import { eq, and } from 'drizzle-orm';
import {
    createCrystalBall,
    createRegistry,
    serialize,
    deserialize,
    addNode,
    setSlotCount,
    getSpace,
    registerSpace,
    deleteSpace,
    lockNode,
    freezeNode,
    buildUARL,
    describeYLayer,
    Y_LAYER_SEMANTICS,
    buildSpaceUARL,
    freezeWithYouknow,
    kernelToMAP,
    isKernelComplete,
    createKernel,
    lockKernel,
    dump as cbDump,
    scry as cbScry,
    propagateEntanglement,
    getAmplitude,
    getBornWeight,
    type CrystalBall,
    type OntologyNode,
    type SerializedCrystalBall,
    type Registry,
    type KernelSpace,
} from './index';
import { cbEvalLocal, cbQuote, verifyInvertibility } from './homoiconic';
import { computeMinePlane, mine as computeMineSpace, mineConfigurations, type MineSpace } from './mine';
import { runSwarm, execSwarmViaDocker, buildSwarmPrompt, renderPrompt, applySwarmActions } from './swarm-agent';
import { computeSpaceSlotSignature, tensorKernel, tensorGramMatrix, findSlotOrbits, takeKernelSnapshot, computeKernelTemperature, type SpaceSlotSignature, type KernelSnapshot, type TemperatureReading } from './kernel-v2';
import { reifyMineSpace, buildFutamuraTower, type ReifyResult, type TowerResult } from './reify';
import { tryAdvanceFromCB, declareKappa, formatGriessState, griessStatus, getGriessState, verifyKappa, formatVerifyReport } from './griess';
import { scry, formatScryResult } from './scry';
import { computeMineView, formatMineView } from './mine-view';
import { compile as griessCompile, formatCompileResult } from './compile';
import { analyzeAlgebra, formatAlgebraAnalysis } from './algebra';
import { rectifySpace, formatRectification, GMR_DEFAULTS } from './gmr';
import { computeAlgebraNeighborhoods } from './swarm-agent';
import { eigenvalues as computeEigenvalues, hybridKernel, analyzeSpace as analyzeSpaceHybrid, foundationSignature as computeFoundationSignature } from './kernel-function';
import { coordToReal, encodeDot, encodeSelectionIndex } from './index';



/**
 * Build FULL mathematical context for fill prompts.
 * Hides NOTHING — includes coordinate, UARL, kernel matrix,
 * Born amplitude, slot signature, Y-layer semantics, parent,
 * siblings. The LLM sees ALL the math before filling.
 */
function buildFillContext(registry: Registry, spaceName: string, nodeId: string): string {
    try {
        const mineView = computeMineView(registry, spaceName, nodeId);
        if (!mineView) return '';
        return '\n' + formatMineView(mineView) + '\n';
    } catch {
        return '';
    }
}

// ─── Types ────────────────────────────────────────────────────────

export interface CBInteraction {
    type: 'select' | 'fill' | 'name';
    prompt: string;
    options?: string[];
    target: string;       // nodeId or attribute name this is about
}

export interface CBCursor {
    space: string | null;
    coordinate: string;
}

export interface CBResponse {
    view: string;         // Human-readable render
    data?: any;           // Machine-readable structured data
    interaction?: CBInteraction;  // What CB needs from you, or null
    cursor: CBCursor;     // Where you are now
    phase?: FlowPhase;    // Current phase in the FLOW pipeline
    temperature?: TemperatureReading; // Kernel heat from this interaction
}

// ─── FLOW Phase Tracking ─────────────────────────────────────────

export type FlowPhase = 'idle' | 'create' | 'bloom' | 'fill' | 'lock' | 'mine' | 'compose';

const PHASE_CONFIG: Record<FlowPhase, {
    prompt: string;
    transition: string;
    validCommands: string[];
}> = {
    idle: {
        prompt: 'Choose a space or create one.',
        transition: 'Enter a space or create one to begin.',
        validCommands: ['list', 'create', '<spacename>'],
    },
    create: {
        prompt: 'Name your space. What deliverable is this for?',
        transition: 'Space created → moves to bloom.',
        validCommands: ['<name>'],
    },
    bloom: {
        prompt: 'Add children to expand the spectrum. Type a label to add a child node. What dimensions matter here? What are the slots?',
        transition: 'Type "done" when the spectrum is complete → moves to fill.',
        validCommands: ['<label>', 'done', '<coordinate>'],
    },
    fill: {
        prompt: 'Navigate slots and select values. Use coordinates to navigate, type labels to fill sub-spectra.',
        transition: 'Type "lock" when all selections are made → moves to lock.',
        validCommands: ['<coordinate>', '<label>', 'lock'],
    },
    lock: {
        prompt: 'Locking commits your selections. Type "lock" to confirm, or go back to fill.',
        transition: 'Lock confirmed → moves to mine.',
        validCommands: ['lock', 'back'],
    },
    mine: {
        prompt: 'Mining enumerates all valid configurations. Type "mine" to see the mineSpace.',
        transition: 'Mine complete → goldenize a config or compose.',
        validCommands: ['mine', 'mine view', 'compose', 'done'],
    },
    compose: {
        prompt: 'Compose this space with others. Composing creates a higher-order kernel.',
        transition: 'Compose complete → back to bloom for the composite.',
        validCommands: ['<spacename>', 'done'],
    },
};

// ─── Per-Team Session State ───────────────────────────────────────

interface SessionState {
    currentSpace: string | null;
    currentCoordinate: string;
    pendingInteraction: CBInteraction | null;
    pendingNodeId: string | null;
    phase: FlowPhase;
    youknowFn?: (statement: string) => Promise<string>;  // Injected YOUKNOW validator
    mapFn?: (source: string) => Promise<string>;          // Injected MAP evaluator
}

const sessions = new Map<number, SessionState>();

const YOUKNOW_CWD = process.env.YOUKNOW_CWD || '/Users/isaacwr/.gemini/antigravity/scratch/crystal-ball-saas/youknow_v225/youknow_kernel_current';
const MAP_CWD = process.env.MAP_CWD || '/Users/isaacwr/.gemini/antigravity/scratch/crystal-ball-saas/MAP';

function makeYouknowFn(): (statement: string) => Promise<string> {
    return async (statement: string) => {
        // Escape single quotes in the statement
        const escaped = statement.replace(/'/g, "\\'");
        try {
            const result = execSync(
                `python3 -c "from youknow_kernel.compiler import youknow; print(youknow('${escaped}'))"`,
                { cwd: YOUKNOW_CWD, timeout: 10000, encoding: 'utf-8' }
            );
            return result.trim();
        } catch (err: any) {
            return `YOUKNOW error: ${err.message || err}`;
        }
    };
}

function makeMapFn(): (source: string) => Promise<string> {
    return async (source: string) => {
        const fs = require('fs');
        const os = require('os');
        const path = require('path');
        // Write MAP source to temp file to avoid shell quoting issues
        const tmpFile = path.join(os.tmpdir(), `cb_map_${Date.now()}.map`);
        try {
            fs.writeFileSync(tmpFile, source, 'utf-8');
            const result = execSync(
                `python3 -c "from map.base.eval import run; r, _ = run(open('${tmpFile}').read()); print(r)"`,
                { cwd: MAP_CWD, timeout: 10000, encoding: 'utf-8' }
            );
            return result.trim();
        } catch (err: any) {
            return `MAP error: ${err.message || err}`;
        } finally {
            try { fs.unlinkSync(tmpFile); } catch { }
        }
    };
}

export function getSession(teamId: number): SessionState {
    if (!sessions.has(teamId)) {
        sessions.set(teamId, {
            currentSpace: null,
            currentCoordinate: 'root',
            pendingInteraction: null,
            pendingNodeId: null,
            phase: 'idle',
            youknowFn: makeYouknowFn(),
            mapFn: makeMapFn(),
        });
    }
    return sessions.get(teamId)!;
}

/** Get phase info for a response */
function phaseInfo(session: SessionState): { phase: FlowPhase; phasePrompt: string } {
    const config = PHASE_CONFIG[session.phase];
    return {
        phase: session.phase,
        phasePrompt: `[FLOW ${session.phase.toUpperCase()}] ${config.prompt} (${config.transition})`,
    };
}

// ─── In-Memory Registry ───────────────────────────────────────────

const registry: Registry = createRegistry();

// ─── Persistence ──────────────────────────────────────────────────

// In-memory mineSpace cache: spaceName → MineSpace
const mineSpaceCache = new Map<string, MineSpace>();

function toDbData(cb: CrystalBall, mineSpace?: MineSpace): any {
    const data: any = serialize(cb);
    if (mineSpace) {
        data.mineSpace = mineSpace;
    }
    return data;
}

function toDbDataWithCachedMine(cb: CrystalBall, spaceName: string): any {
    return toDbData(cb, mineSpaceCache.get(spaceName));
}

function fromDbData(data: unknown): CrystalBall {
    return deserialize(data as SerializedCrystalBall);
}

function nodeToView(node: OntologyNode, indent: number = 0): string {
    const pad = '  '.repeat(indent);
    const sc = node.slotCount ?? 0;
    const slots = sc > 0
        ? ` {${node.children.length}/${sc}}`
        : '';
    const complete = (sc > 0 && node.children.length >= sc) ? ' ✓' : '';
    const filling = (sc > 0 && node.children.length < sc) ? ' …' : '';
    const sub = node.producedSpace ? ` →${node.producedSpace}` : '';
    const childStr = node.children.length > 0
        ? ` [${node.children.length} children]`
        : '';
    return `${pad}${node.id}: ${node.label}${complete}${filling}${sub}${slots}${childStr}`;
}

function spaceToView(crystal: CrystalBall): string {
    const lines: string[] = [`=== ${crystal.name} ===`];
    function walk(nodeId: string, depth: number) {
        const node = crystal.nodes.get(nodeId);
        if (!node) return;
        lines.push(nodeToView(node, depth));
        for (const childId of node.children) {
            walk(childId, depth + 1);
        }
    }
    walk(crystal.rootId, 0);
    return lines.join('\n');
}

function nodeToData(node: OntologyNode) {
    return {
        id: node.id,
        label: node.label,
        children: node.children,
        slotCount: node.slotCount ?? 0,
        complete: (node.slotCount ?? 0) > 0 && node.children.length >= (node.slotCount ?? 0),
        childLabels: node.children,
        hasSubspace: !!node.producedSpace,
        locked: !!node.locked,
        frozen: !!node.frozen,
        x: node.x,
        y: node.y,
        // Proof-encoding fields
        role: node.role ?? null,
        formalType: node.formalType ?? null,
        frozenBy: node.frozenBy ?? null,
    };
}

export async function loadCb(teamId: number, spaceName: string): Promise<{ cb: CrystalBall; rowId: number }> {
    const rows = await db
        .select()
        .from(spaces)
        .where(and(eq(spaces.teamId, teamId), eq(spaces.name, spaceName)));
    if (rows.length === 0) throw new Error(`Space "${spaceName}" not found`);

    const rawData = rows[0].data as SerializedCrystalBall;

    // Preload any subspace dependencies into the registry
    await preloadSubspaces(teamId, rawData);

    const cb = deserialize(rawData);
    registry.spaces.set(spaceName, cb); // Cache in registry
    return { cb, rowId: rows[0].id };
}

/** Recursively load spaces referenced as subspaces into the registry */
async function preloadSubspaces(teamId: number, data: SerializedCrystalBall): Promise<void> {
    const subspaceNames = data.nodes
        .map(n => n.producedSpace)
        .filter((name): name is string => !!name && !registry.spaces.has(name));

    for (const name of [...new Set(subspaceNames)]) {
        try {
            const rows = await db
                .select()
                .from(spaces)
                .where(and(eq(spaces.teamId, teamId), eq(spaces.name, name)));
            if (rows.length > 0) {
                const subData = rows[0].data as SerializedCrystalBall;
                // Recurse: load sub-subspaces first
                await preloadSubspaces(teamId, subData);
                const subCb = deserialize(subData);
                registry.spaces.set(name, subCb);
            }
        } catch (e) {
            console.warn(`Could not preload subspace "${name}":`, e);
        }
    }
}

export async function saveCb(rowId: number, cb: CrystalBall): Promise<void> {
    await db
        .update(spaces)
        .set({ data: toDbData(cb) as any, updatedAt: new Date() })
        .where(eq(spaces.id, rowId));
}

async function listAllSpaces(teamId: number): Promise<string[]> {
    const rows = await db
        .select({ name: spaces.name })
        .from(spaces)
        .where(eq(spaces.teamId, teamId));
    return rows.map(r => r.name);
}

/** Show a node in a space and trigger fill prompts if slots are unfilled */
async function enterSpaceAt(
    teamId: number,
    session: SessionState,
    spaceName: string,
    nodeId: string,
    crystal: CrystalBall,
    rowId: number,
): Promise<CBResponse> {
    const node = crystal.nodes.get(nodeId);
    if (!node) {
        return { view: `No node "${nodeId}".`, cursor: { space: spaceName, coordinate: nodeId } };
    }

    // If node has unfilled slots, prompt
    const nsc = node.slotCount ?? 0;
    if (nsc > 0 && node.children.length < nsc) {
        const remaining = nsc - node.children.length;
        session.pendingInteraction = {
            type: 'fill',
            prompt: `${node.label} has ${remaining} slot(s). Name the next:`,
            target: node.id,
        };
        session.pendingNodeId = node.id;
        return {
            view: spaceToView(crystal),
            interaction: session.pendingInteraction,
            data: nodeToData(node),
            cursor: { space: spaceName, coordinate: nodeId },
        };
    }

    // Fill interaction — include mathematical context so LLM choices are GUIDED by the math
    const fillContext = buildFillContext(registry, spaceName, node.id);
    session.pendingInteraction = {
        type: 'fill',
        prompt: node.children.length === 0
            ? `${node.label} is empty. ${fillContext}Add children:`
            : `${node.label} has ${node.children.length} children. ${fillContext}Add more:`,
        target: node.id,
    };
    session.pendingNodeId = node.id;

    return {
        view: spaceToView(crystal),
        interaction: session.pendingInteraction,
        data: nodeToData(node),
        cursor: { space: spaceName, coordinate: nodeId },
    };
}

// ═══════════════════════════════════════════════════════════════════
// THE ONE FUNCTION
// ═══════════════════════════════════════════════════════════════════

export async function cb(teamId: number, input: string): Promise<CBResponse> {
    // ─── List input: FLOW accepts lists at every phase ────────
    // If input has newlines, process each line through FLOW sequentially.
    // This IS batch. There is no separate batch system.
    const lines = input.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length > 1) {
        let lastResult: CBResponse = {
            view: 'No commands executed.',
            cursor: { space: null, coordinate: 'root' },
        };
        for (const line of lines) {
            lastResult = await cb(teamId, line);
        }
        return lastResult;
    }

    const session = getSession(teamId);
    const trimmed = input.trim();

    // ─── Take temperature snapshot before interaction ─────────
    const snapshotBefore = session.currentSpace
        ? takeKernelSnapshot(registry, session.currentSpace)
        : null;

    // ─── STRICT PHASE GATING ─────────────────────────────────
    // The state machine enforces valid commands per phase.
    // If input doesn't match a valid command for the current phase,
    // REJECT it and show what commands ARE valid. No implicit interpretation.
    if (session.pendingInteraction && session.phase === 'fill') {
        // Fill mode: ONLY explicit commands are valid
        const isFillAdd = /^add\s+/i.test(trimmed);
        const isDone = /^done$/i.test(trimmed);
        const isBack = /^back$/i.test(trimmed);
        const isLock = /^lock$/i.test(trimmed);
        const isExit = /^exit$/i.test(trimmed);
        const isBloom = /^bloom/i.test(trimmed);
        const isCoordinate = /^[\d.]+$/.test(trimmed);

        if (isFillAdd) {
            // Extract label and route to fill handler
            const label = trimmed.slice(4).trim();
            return handleInteractionResponse(teamId, session, label);
        }
        if (isDone || isLock || isBack || isExit || isBloom || isCoordinate) {
            // These are valid transition/navigation commands — clear interaction and fall through
            session.pendingInteraction = null;
            // Fall through to normal command parsing below
        } else {
            // REJECT: not a valid fill command
            return {
                view: `❌ Invalid in FILL mode. Valid commands:\n` +
                    `  add <label>  — add a child node\n` +
                    `  bloom        — bloom into current node\n` +
                    `  <coordinate> — navigate (e.g. 1.2)\n` +
                    `  done         — finish filling\n` +
                    `  lock         — lock current node\n` +
                    `  back         — exit fill mode\n` +
                    `  exit         — leave space\n\n` +
                    `You typed: "${trimmed}"`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
                phase: session.phase,
            };
        }
    } else if (session.pendingInteraction) {
        // Other interaction types (select, name) — clear and fall through for now
        session.pendingInteraction = null;
    }

    // ─── Parse input ─────────────────────────────────────────
    // Formats:
    //   ""  or "list"     → show all spaces
    //   "SpaceName"       → enter/show that space
    //   "SpaceName 1.2"   → scry coordinate in space
    //   "1.2"             → scry coordinate in current space
    //   "@nodeId"          → navigate to node by ID in current space
    //   "create SpaceName"→ create new space
    //   "exit"            → go up / exit current space

    // @ prefix = navigate to a node by ID within current space
    if (trimmed.startsWith('@') && session.currentSpace) {
        const coord = trimmed.slice(1).trim();
        return scryCoordinate(teamId, session, session.currentSpace, coord);
    }

    if (trimmed === '' || trimmed === 'list') {
        const names = await listAllSpaces(teamId);
        session.currentSpace = null;
        session.currentCoordinate = 'root';
        return {
            view: names.length === 0
                ? 'No spaces. Type a name to create one.'
                : `Spaces:\n${names.map((n, i) => `  ${i + 1}. ${n}`).join('\n')}`,
            data: { spaces: names },
            cursor: { space: null, coordinate: 'root' },
        };
    }

    if (trimmed === 'exit' || trimmed === '..') {
        if (session.currentSpace) {
            session.currentSpace = null;
            session.currentCoordinate = 'root';
            return cb(teamId, 'list');
        }
        return {
            view: 'Already at top level.',
            cursor: { space: null, coordinate: 'root' },
        };
    }

    // "create X" — explicit creation
    if (trimmed.startsWith('create ')) {
        const name = trimmed.slice(7).trim();
        return createNewSpace(teamId, session, name);
    }

    // "delete X" — delete a space
    if (trimmed.startsWith('delete ')) {
        const name = trimmed.slice(7).trim();
        const rows = await db
            .select()
            .from(spaces)
            .where(and(eq(spaces.teamId, teamId), eq(spaces.name, name)));
        if (rows.length === 0) {
            return { view: `Space "${name}" not found.`, cursor: { space: null, coordinate: 'root' } };
        }
        await db.delete(spaces).where(eq(spaces.id, rows[0].id));
        if (session.currentSpace === name) {
            session.currentSpace = null;
            session.currentCoordinate = 'root';
        }
        return {
            view: `Deleted space "${name}".`,
            cursor: { space: null, coordinate: 'root' },
        };
    }

    // "rename OldName NewName" — rename a space
    if (trimmed.startsWith('rename ')) {
        const parts = trimmed.slice(7).trim().split(/\s+/);
        if (parts.length !== 2) {
            return { view: 'Usage: rename <old-name> <new-name>', cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        const [oldName, newName] = parts;
        const rows = await db
            .select()
            .from(spaces)
            .where(and(eq(spaces.teamId, teamId), eq(spaces.name, oldName)));
        if (rows.length === 0) {
            return { view: `Space "${oldName}" not found.`, cursor: { space: null, coordinate: 'root' } };
        }
        // Check new name doesn't conflict
        const existing = await db
            .select()
            .from(spaces)
            .where(and(eq(spaces.teamId, teamId), eq(spaces.name, newName)));
        if (existing.length > 0) {
            return { view: `Space "${newName}" already exists.`, cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        // Update DB
        await db.update(spaces)
            .set({ name: newName })
            .where(eq(spaces.id, rows[0].id));
        // Update in-memory registry
        const cached = getSpace(registry, oldName);
        if (cached) {
            cached.name = newName;
            registerSpace(registry, cached);
            registry.spaces.delete(oldName); // Don't use deleteSpace — it triggers onDelete callback
        }
        // Update session if user was in the renamed space
        if (session.currentSpace === oldName) {
            session.currentSpace = newName;
        }
        return {
            view: `Renamed "${oldName}" → "${newName}".`,
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "slots N" — set slot count on current node
    if (trimmed.startsWith('slots ') && session.currentSpace) {
        const n = parseInt(trimmed.slice(6).trim(), 10);
        if (isNaN(n) || n < 1) {
            return { view: 'Usage: slots <number>', cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const nodeId = session.currentCoordinate === 'root' ? crystal.rootId : null;
        const node = nodeId ? crystal.nodes.get(nodeId) : cbEvalLocal(crystal, session.currentCoordinate).nodes[0];
        if (!node) {
            return { view: `No node at ${session.currentCoordinate}.`, cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        setSlotCount(crystal, node.id, n);
        await saveCb(rowId, crystal);

        // Now trigger the fill chain
        return enterSpaceAt(teamId, session, session.currentSpace, node.id, crystal, rowId);
    }



    // "add Label" — add child to current node
    if (trimmed.startsWith('add ') && session.currentSpace) {
        const label = trimmed.slice(4).trim();
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const parentId = session.currentCoordinate === 'root' ? crystal.rootId : null;
        const parent = parentId ? crystal.nodes.get(parentId) : cbEvalLocal(crystal, session.currentCoordinate).nodes[0];
        if (!parent) {
            return { view: `No node at ${session.currentCoordinate}.`, cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        const newNode = addNode(crystal, parent.id, label);
        await saveCb(rowId, crystal);
        return {
            view: `Added: ${newNode.id}: ${label}\n\n${spaceToView(crystal)}`,
            data: { ...nodeToData(newNode), parentId: parent.id, parentLabel: parent.label },
            cursor: { space: session.currentSpace, coordinate: newNode.id },
        };
    }

    // "attr" command — DEPRECATED. Attributes removed, children ARE the spectrum.
    if (trimmed.startsWith('attr ') && session.currentSpace) {
        return {
            view: '⚠️ The "attr" command is deprecated. Children ARE the spectrum.\nUse the coordinate system to add children (e.g., "MySpace NodeLabel").',
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "eval <coord>" — evaluate coordinate through homoiconic layer
    if (trimmed.startsWith('eval ') && session.currentSpace) {
        const coord = trimmed.slice(5).trim();
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const result = cbEvalLocal(crystal, coord);
        if (result.nodes.length === 0) {
            return {
                view: `eval(${coord}) → ∅ (no nodes resolved)`,
                cursor: { space: session.currentSpace, coordinate: coord },
            };
        }
        const nodeViews = result.nodes.map(n => `  ${n.id}: ${n.label} [${n.children.length} children]`).join('\n');
        return {
            view: `eval(${coord}) → ${result.nodes.length} node(s):\n${nodeViews}\nreal: ${result.real}`,
            data: nodeToData(result.nodes[0]),
            cursor: { space: session.currentSpace, coordinate: coord },
        };
    }

    // "quote <nodeId>" — inverse of eval: node → coordinate
    if (trimmed.startsWith('quote ') && session.currentSpace) {
        const nodeId = trimmed.slice(6).trim();
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const result = cbQuote(crystal, nodeId);
        if (!result) {
            return {
                view: `quote(${nodeId}) → ∅ (node not found or unreachable from root)`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
            };
        }
        return {
            view: `quote(${nodeId}) → "${result.coordinate}"\nlabel: ${result.label}\nreal: ${result.real}`,
            cursor: { space: session.currentSpace, coordinate: result.coordinate || 'root' },
        };
    }

    // "mine" — compute configuration space for current position
    if (trimmed === 'mine' && session.currentSpace) {
        const mineCoord = session.currentCoordinate === 'root' ? '0' : session.currentCoordinate;
        const mineResult = computeMinePlane(registry, session.currentSpace, mineCoord);

        // Compute configuration-level mineSpace (each point = full configuration tuple)
        const { mineSpace, dims, currentConfig, totalConfigs } = mineConfigurations(registry, session.currentSpace);
        mineSpaceCache.set(session.currentSpace, mineSpace);

        // Persist mineSpace directly to the DB data blob
        try {
            const rows = await db.select().from(spaces).where(and(eq(spaces.teamId, teamId), eq(spaces.name, session.currentSpace)));
            if (rows.length > 0) {
                const existingData = rows[0].data as any;
                existingData.mineSpace = mineSpace;
                await db.update(spaces).set({ data: existingData, updatedAt: new Date() }).where(eq(spaces.id, rows[0].id));
            }
        } catch (e: any) {
            console.error('MineSpace persist error:', e.message);
        }

        const valid = mineSpace.known.filter(p => p.status === 'valid');
        const adjacent = mineSpace.known.filter(p => p.status === 'adjacent');

        return {
            view: `⛏️ Mine: ${session.currentSpace} @ ${mineCoord}\n` +
                `${totalConfigs.toLocaleString()} total configurations across ${dims.length} dimensions\n` +
                `Current config: [${currentConfig.join(', ')}]\n` +
                `Space heat: ${mineResult.spaceHeat.toFixed(2)}\n` +
                `Kernel: ${mineResult.kernelComplete ? 'COMPLETE' : 'incomplete'}\n` +
                `MineSpace: ${valid.length} chosen, ${adjacent.length} adjacent configs`,
            data: { ...mineResult, mineSpace, dims, currentConfig, totalConfigs },
            cursor: { space: session.currentSpace, coordinate: mineCoord },
        };
    }

    // "mine view" — observe persisted mineSpace
    if (trimmed === 'mine view' && session.currentSpace) {
        const ms = mineSpaceCache.get(session.currentSpace);
        if (!ms) {
            // Try loading from DB
            const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
            const dbData = toDbData(crystal) as any;
            if (dbData.mineSpace) {
                mineSpaceCache.set(session.currentSpace, dbData.mineSpace);
                const loaded = dbData.mineSpace as MineSpace;
                const valid = loaded.known.filter((p: any) => p.status === 'valid');
                const adjacent = loaded.known.filter((p: any) => p.status === 'adjacent');
                return {
                    view: `📊 MineSpace: ${session.currentSpace}\n` +
                        `Deliverable: ${loaded.deliverable}\n` +
                        `Valid: ${valid.length}\n` +
                        `Adjacent: ${adjacent.length}\n` +
                        `Kernels: ${loaded.projectedKernels.join(', ')}\n\n` +
                        `Valid points:\n` +
                        valid.map((p: any) => `  ${p.coordinate} → 0.${p.encoded} (ℝ=${p.x})`).join('\n'),
                    data: loaded,
                    cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
                };
            }
            return {
                view: `No mineSpace found for ${session.currentSpace}. Run \"mine\" first.`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
            };
        }
        const valid = ms.known.filter(p => p.status === 'valid');
        const adjacent = ms.known.filter(p => p.status === 'adjacent');
        return {
            view: `📊 MineSpace: ${session.currentSpace}\n` +
                `Deliverable: ${ms.deliverable}\n` +
                `Valid: ${valid.length}\n` +
                `Adjacent: ${adjacent.length}\n` +
                `Kernels: ${ms.projectedKernels.join(', ')}\n\n` +
                `Valid points:\n` +
                valid.map(p => `  ${p.coordinate} → 0.${p.encoded} (ℝ=${p.x})`).join('\n'),
            data: ms,
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "view" — full mathematical-semantic view from current position
    // Computes: kernel matrix, UARL ontology trees, Born distribution,
    // Y-layer disambiguation, fill targets. THE PROMPT for the LLM.
    if (trimmed === 'view' && session.currentSpace) {
        const mineView = computeMineView(registry, session.currentSpace, session.currentCoordinate);
        return {
            view: formatMineView(mineView),
            data: { mineView },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "done" — transition to next phase
    // "instantiate" — convert kernel to MAP program, settle zeroes via LLM
    if (trimmed === 'instantiate' && session.currentSpace) {
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const mapProgram = kernelToMAP(crystal);

        if (mapProgram.zeroes.length > 0) {
            // Build LLM prompt to settle zeroes
            const settlePrompt = `Given this MAP program for kernel "${session.currentSpace}":\n\n` +
                `${mapProgram.source}\n\n` +
                `The following slots are unresolved (NIL):\n` +
                mapProgram.zeroes.map((z: string) => `  - ${z}`).join('\n') + '\n\n' +
                `For each unresolved slot, provide a concrete value that fits the kernel's domain.\n` +
                `Return a JSON object mapping slot names to their values.`;

            return {
                view: `🗺️ MAP instantiation of ${session.currentSpace}\n` +
                    `${Object.keys(mapProgram.bindings).length} settled, ${mapProgram.zeroes.length} zeroes\n\n` +
                    `MAP source:\n${mapProgram.source}\n\n` +
                    `⏳ ${mapProgram.zeroes.length} zeroes need settling via LLM.`,
                data: {
                    map_program: mapProgram,
                    llm_request: {
                        prompt: settlePrompt,
                        space: session.currentSpace,
                        coordinate: session.currentCoordinate,
                        type: 'settle_zeroes',
                        zeroes: mapProgram.zeroes,
                    },
                },
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
            };
        }

        // All settled — return complete MAP program
        return {
            view: `🗺️ MAP instantiation of ${session.currentSpace} — COMPLETE\n` +
                `${Object.keys(mapProgram.bindings).length} bindings, 0 zeroes\n\n` +
                `MAP source:\n${mapProgram.source}`,
            data: { map_program: mapProgram },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "temp" — kernel thermometer: read current interaction heat
    if (trimmed === 'temp' && session.currentSpace) {
        const currentSnapshot = takeKernelSnapshot(registry, session.currentSpace);
        let reading: TemperatureReading | null = null;

        if (snapshotBefore) {
            reading = computeKernelTemperature(snapshotBefore, currentSnapshot);
        }

        const lines: string[] = [
            `🌡️ Kernel Temperature: ${session.currentSpace}`,
            '',
            `  Nodes: ${currentSnapshot.nodeCount} (${currentSnapshot.lockedCount} locked, ${currentSnapshot.frozenCount} frozen)`,
            `  Superpositions: ${currentSnapshot.superpositionCount}`,
            `  Total amplitude: ${currentSnapshot.totalAmplitude.toFixed(2)}`,
            `  Orbits: ${currentSnapshot.orbitCount}`,
            `  Canonical: ${currentSnapshot.canonical || '(not in kernel mode)'}`,
        ];

        if (reading) {
            lines.push('');
            lines.push(`  Phase: ${reading.phase.toUpperCase()} (T = ${reading.temperature.toFixed(3)})`);
            lines.push(`  Signals:`);
            lines.push(`    +${reading.signals.nodesAdded} nodes, ${reading.signals.nodesLocked} locked`);
            lines.push(`    ${reading.signals.orbitsChanged} orbit changes`);
            lines.push(`    Signature: ${reading.signals.signatureChanged ? '⚡ CHANGED' : 'stable'}`);
            lines.push(`    Amplitude shift: ${reading.signals.amplitudeShift >= 0 ? '+' : ''}${reading.signals.amplitudeShift.toFixed(2)}`);
            lines.push(`    Superpositions resolved: ${reading.signals.superpositionsResolved}`);
            if (reading.hielCondition) {
                lines.push('');
                lines.push(`  🔥 HIEL CONDITION MET — heat sufficient for ligation`);
            }
        } else {
            lines.push('');
            lines.push(`  (Initial snapshot — run a command then "temp" again to see delta)`);
        }

        return {
            view: lines.join('\n'),
            data: { snapshot: currentSnapshot, temperature: reading },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "griess" — show Griess construction state for current space
    if (trimmed === 'griess' && session.currentSpace) {
        return {
            view: formatGriessState(session.currentSpace),
            data: { griess: getGriessState(session.currentSpace) },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "griess status" — show all spaces' Griess phases
    if (trimmed === 'griess status') {
        const status = griessStatus();
        const lines: string[] = [
            `⚙️ Griess Constructor Status`,
            `  Total spaces: ${status.total}`,
        ];
        for (const [phase, names] of Object.entries(status.byPhase)) {
            lines.push(`  ${phase.toUpperCase()}: ${names.join(', ')}`);
        }
        if (status.missingKappa.length > 0) {
            lines.push(`  ⚠️ Missing κ_user: ${status.missingKappa.join(', ')}`);
        }
        if (status.stuckInBuild.length > 0) {
            lines.push(`  ⚠️ Stuck in BUILD: ${status.stuckInBuild.join(', ')} — should VERIFY`);
        }
        return {
            view: lines.join('\n'),
            data: { griessStatus: status },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "kappa <domain>: <inv1>=<desc1>, <inv2>=<desc2>, ..." — declare κ_user
    if (/^kappa\s+/i.test(trimmed) && session.currentSpace) {
        // Parse: kappa fitness_app: members_get_stronger=measurable progress, community=people return
        const rest = trimmed.slice(6).trim();
        const colonIdx = rest.indexOf(':');
        if (colonIdx === -1) {
            return {
                view: `Usage: kappa <domain>: <invariant>=<description>, <invariant>=<description>, ...`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
            };
        }
        const domain = rest.slice(0, colonIdx).trim();
        const invStr = rest.slice(colonIdx + 1).trim();
        const invariants: Record<string, string> = {};
        for (const part of invStr.split(',')) {
            const eqIdx = part.indexOf('=');
            if (eqIdx > 0) {
                const key = part.slice(0, eqIdx).trim();
                const val = part.slice(eqIdx + 1).trim();
                invariants[key] = val;
            }
        }

        if (Object.keys(invariants).length === 0) {
            return {
                view: `No invariants parsed. Format: kappa <domain>: <name>=<description>, ...`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
            };
        }

        declareKappa(session.currentSpace, domain, invariants);
        const state = getGriessState(session.currentSpace);

        return {
            view: `κ_user declared for "${session.currentSpace}":\n` +
                `  Domain: ${domain}\n` +
                `  Invariants:\n` +
                Object.entries(invariants).map(([k, v]) => `    • ${k}: ${v}`).join('\n') + '\n\n' +
                `Griess phase: ${state.phase.toUpperCase()} — ready to advance to COMPUTE (bloom)`,
            data: { kappa: state.kappa, griess: state },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "algebra" — show Born distribution from current position (what you can see from here)
    // "algebra meta" — run full Aut/Monster/fusion analysis
    if (/^algebra(\s+meta)?$/i.test(trimmed) && session.currentSpace) {
        const isMeta = /meta/i.test(trimmed);
        const { cb: crystal } = await loadCb(teamId, session.currentSpace);

        if (isMeta) {
            // Full abstract analysis (Aut group, Monster checks, fusion)
            const result = analyzeAlgebra(registry, session.currentSpace);
            return {
                view: formatAlgebraAnalysis(result),
                data: { algebra: result },
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
            };
        }

        // Default: Born distribution from current position
        // For each unlocked node, show what amplitude each other node would get if you locked it
        const nodeIds = Array.from(crystal.nodes.keys());
        const lines: string[] = [
            `🔬 Born Distribution: ${session.currentSpace} @ ${session.currentCoordinate ?? 'root'}`,
            `  "If I lock THIS, what amplitudes propagate?"`,
            '',
        ];

        for (const nId of nodeIds) {
            const n = crystal.nodes.get(nId)!;
            if (n.locked || n.frozen) continue;

            const born = getBornWeight(n);
            if (born <= 0) continue; // Not in support

            // Simulate: what would algebra product do if we locked this?
            const amp = getAmplitude(n) || 1.0;
            const targets: string[] = [];
            for (const oId of nodeIds) {
                if (oId === nId) continue;
                const o = crystal.nodes.get(oId)!;
                if (o.locked || o.frozen) continue;

                // Use the same algebra weight function
                const parentId = (id: string) => {
                    if (id === 'root') return null;
                    const dot = id.lastIndexOf('.');
                    return dot === -1 ? 'root' : id.substring(0, dot);
                };
                const np = parentId(nId), op = parentId(oId);
                let w = 0;
                if (op === nId) { w = amp / Math.max(n.children.length, 1); }
                else if (np === oId) { w = amp / Math.max(o.children.length, 1); }
                else if (np && np === op) {
                    const p = crystal.nodes.get(np);
                    w = amp / Math.max(p?.children.length ?? 1, 1);
                }
                if (w > 0) targets.push(`${o.label}→${w.toFixed(3)}`);
            }

            if (targets.length > 0) {
                lines.push(`  🔒 Lock "${n.label}" (born=${born.toFixed(2)}):`);
                lines.push(`     → ${targets.join(', ')}`);
            }
        }

        lines.push('');
        lines.push(`  Each line = "lock this node → these coordinates get these amplitudes"`);
        lines.push(`  This IS the navigation map. Born > 0 = reachable. Born 0 = excluded.`);

        return {
            view: lines.join('\n'),
            data: { bornDistribution: true },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "gmr" — Geometric Manifold Rectification: clean Born support
    if (trimmed === 'gmr' && session.currentSpace) {
        const { cb: crystal } = await loadCb(teamId, session.currentSpace);
        const neighborhoods = computeAlgebraNeighborhoods(crystal);
        const result = rectifySpace(registry, session.currentSpace, neighborhoods, GMR_DEFAULTS);
        return {
            view: formatRectification(result),
            data: { gmr: result },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "compile" — full Griess compilation pass
    // Orchestrates: scry (BUILD) → verify κ_user → YOUKNOW validation → ONT/SOUP
    if (/^compile(\s+\d+)?$/i.test(trimmed) && session.currentSpace) {
        const maxMatch = trimmed.match(/\d+/);
        const maxSteps = maxMatch ? parseInt(maxMatch[0], 10) : 10;

        const result = griessCompile(registry, session.currentSpace, maxSteps);

        return {
            view: formatCompileResult(result),
            data: { compile: result },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "verify" — Griess VERIFY: check if Aut preserves κ_user
    if (trimmed === 'verify' && session.currentSpace) {
        const { cb: crystal } = await loadCb(teamId, session.currentSpace);

        // Get current |Ш| via tower
        let sha = 0;
        try {
            const tower = buildFutamuraTower(registry, 0);  // TODO: resolve kernel ID
            sha = tower.sha;
        } catch { /* no tower yet */ }

        // Run κ_user verification against space nodes
        const report = verifyKappa(session.currentSpace, crystal.nodes, sha);

        // Auto-advance Griess based on outcome
        if (report.outcome === 'ont') {
            tryAdvanceFromCB(session.currentSpace, 'reify', 'VERIFY passed — all κ_user preserved');
        }

        return {
            view: formatVerifyReport(report),
            data: { verify: report },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "scry" — perturbation daemon: quantum computation on CB encoding
    // Collapses superpositions via Born-weighted LLM calls,
    // constrained by catastrophe surface, converging toward κ_user.
    if (/^scry(\s+\d+)?$/i.test(trimmed) && session.currentSpace) {
        const maxMatch = trimmed.match(/\d+/);
        const maxIterations = maxMatch ? parseInt(maxMatch[0], 10) : 5;

        const result = scry(registry, session.currentSpace, maxIterations);

        return {
            view: formatScryResult(result),
            data: { scry: result },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate ?? 'root' },
        };
    }

    // "ontology" — live UARL DAG preview for current space
    if (trimmed === 'ontology' && session.currentSpace) {
        const { cb: crystal } = await loadCb(teamId, session.currentSpace);
        const statements = buildSpaceUARL(crystal);

        // Build DAG structure: nodes + edges
        const nodeSet = new Set<string>();
        const edges: Array<{ from: string; to: string; predicate: string }> = [];
        for (const s of statements) {
            nodeSet.add(s.subject);
            nodeSet.add(s.object);
            edges.push({ from: s.subject, to: s.object, predicate: s.predicate });
        }

        const dagView = statements.length > 0
            ? statements.map(s => `  ${s.subject} ──${s.predicate}──▶ ${s.object}`).join('\n')
            : '  (no ontological claims yet)';

        return {
            view: `🔮 Ontology DAG: ${session.currentSpace}\n` +
                `${nodeSet.size} concepts, ${edges.length} relations\n\n` +
                dagView,
            data: {
                ontology: {
                    nodes: Array.from(nodeSet),
                    edges,
                    statements,
                },
            },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "swarm [N]" — build research prompt from kernel state → return for MCP to call LLM
    if (trimmed.startsWith('swarm') && session.currentSpace) {
        const nArg = trimmed.split(/\s+/)[1];
        const n = nArg ? parseInt(nArg, 10) || 5 : 5;

        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const mineResult = computeMinePlane(registry, session.currentSpace, '0');
        const promptCtx = buildSwarmPrompt(crystal, session.currentCoordinate, session.phase, mineResult, n);
        const prompt = renderPrompt(promptCtx);

        return {
            view: `🐙 Swarm prompt ready for ${session.currentSpace} (${n} actions requested).\n` +
                `MCP should call LLM with the prompt and pipe results back via "swarm apply".`,
            data: {
                llm_request: {
                    prompt,
                    context: promptCtx,
                    space: session.currentSpace,
                    coordinate: session.currentCoordinate,
                    n,
                },
            },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "done" — transition to next phase
    if (trimmed === 'done' && session.currentSpace) {
        if (session.phase === 'bloom') {
            session.phase = 'fill';
            const pi = phaseInfo(session);
            return {
                view: `✅ Bloom complete. Moving to FILL phase.\n\n${pi.phasePrompt}`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
                phase: session.phase,
            };
        }
        if (session.phase === 'mine') {
            session.phase = 'idle';
            const pi = phaseInfo(session);
            return {
                view: `✅ Mining complete. Space is done.\n\n${pi.phasePrompt}`,
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
                phase: session.phase,
            };
        }
        return {
            view: `"done" is not valid in ${session.phase} phase.`,
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
            phase: session.phase,
        };
    }

    // "lock" — lock current position (no argument — locks HERE)
    if (trimmed === 'lock' && session.currentSpace) {
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const node = session.currentCoordinate === 'root'
            ? crystal.nodes.get(crystal.rootId)
            : cbEvalLocal(crystal, session.currentCoordinate).nodes[0];
        if (!node) {
            return { view: `Nothing to lock at ${session.currentCoordinate}.`, cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        lockNode(crystal, node.id);

        // ═══ ENTANGLEMENT: Propagate measurement across space boundaries ═══
        const entanglementEvents = propagateEntanglement(registry, session.currentSpace, node.id);

        await saveCb(rowId, crystal);

        // Check if kernel is now complete
        const kernel = isKernelComplete(crystal);
        const progress = `[${kernel.lockedCount}/${kernel.totalSlotted} locked]`;

        if (kernel.complete) {
            // ═══ AUTO-SCRY: Kernel complete → scry root coordinate ═══
            const scryResult = cbScry(registry, session.currentSpace, '0');

            // ═══ AUTO-MINE: Compute configuration space ═══
            const mineResult = computeMinePlane(registry, session.currentSpace, '0');

            // ═══ AUTO-YOUKNOW: Send entire kernel structure as UARL batch ═══
            const spaceUarl = buildSpaceUARL(crystal);
            const youknowResults: Array<{ statement: string; result: string }> = [];
            if (session.youknowFn && spaceUarl.length > 0) {
                for (const uarl of spaceUarl) {
                    const result = await session.youknowFn(uarl.raw);
                    youknowResults.push({ statement: uarl.raw, result });
                }
            }

            const accepted = youknowResults.filter(r => r.result === 'OK').length;
            const rejected = youknowResults.filter(r => r.result !== 'OK').length;
            const youknowView = spaceUarl.length > 0
                ? `\n📜 YOUKNOW: ${spaceUarl.length} UARL statements sent → ${accepted} accepted, ${rejected} rejected`
                : '';

            const scryView = `🔒 Locked: ${node.label} — KERNEL COMPLETE ${progress}\n` +
                `\n⚡ AUTO-SCRY: resolving root coordinate...\n` +
                `Resolved ${scryResult.resolved.length} nodes, ${scryResult.unresolvedZeros} unresolved\n` +
                `Slots: ${scryResult.slots.length}\n` +
                `\n⛏️ AUTO-MINE: ${mineResult.totalPaths} configurations, ${mineResult.points.length} points` +
                youknowView +
                `\n\n${spaceToView(crystal)}`;

            session.phase = 'mine';
            const pi = phaseInfo(session);

            return {
                view: scryView + `\n\n${pi.phasePrompt}`,
                data: {
                    ...nodeToData(node),
                    kernelComplete: true,
                    kernelProgress: kernel,
                    autoScry: true,
                    scryResult: {
                        coordinate: scryResult.coordinate,
                        resolved: scryResult.resolved,
                        unresolvedZeros: scryResult.unresolvedZeros,
                        slots: scryResult.slots,
                    },
                    mineResult,
                    youknow: {
                        statements: spaceUarl,
                        results: youknowResults,
                        accepted,
                        rejected,
                    },
                },
                cursor: { space: session.currentSpace, coordinate: '0' },
                phase: session.phase,
            };
        }

        const entanglementStr = entanglementEvents.length > 0
            ? `\n\n🔗 Entanglement: ${entanglementEvents.length} propagation(s)\n` +
            entanglementEvents.map(e =>
                `  ${e.sourceSpace}:${e.sourceNodeId} → ${e.targetSpace}:${e.targetNodeId} (${e.reason})`
            ).join('\n')
            : '';

        return {
            view: `🔒 Locked: ${node.label} ${progress}${entanglementStr}\n\n${spaceToView(crystal)}`,
            data: { ...nodeToData(node), kernelComplete: false, kernelProgress: kernel, entanglement: entanglementEvents },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // "freeze" — freeze current position AND validate via YOUKNOW
    if (trimmed === 'freeze' && session.currentSpace) {
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const node = session.currentCoordinate === 'root'
            ? crystal.nodes.get(crystal.rootId)
            : cbEvalLocal(crystal, session.currentCoordinate).nodes[0];
        if (!node) {
            return { view: `Nothing to freeze at ${session.currentCoordinate}.`, cursor: { space: session.currentSpace, coordinate: session.currentCoordinate } };
        }
        const result = await freezeWithYouknow(crystal, node.id, session.youknowFn);
        await saveCb(rowId, crystal);
        const uarlPreview = result.uarl ? `\n📜 UARL: ${result.uarl.raw}` : '';
        const youknowStatus = result.youknowResult
            ? (result.accepted ? '\n✅ YOUKNOW: accepted' : `\n❌ YOUKNOW: ${result.youknowResult}`)
            : '';
        return {
            view: `🧊 Frozen: ${node.label}${uarlPreview}${youknowStatus}\n\n${spaceToView(crystal)}`,
            data: { ...nodeToData(node), uarl: result.uarl, youknowResult: result.youknowResult, accepted: result.accepted },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // Split into parts: "SpaceName 1.2.3" or just "1.2.3"
    const parts = trimmed.split(/\s+/);
    const firstPart = parts[0];
    const isCoordinate = /^[\d.]+$/.test(firstPart) || firstPart === 'root';

    if (isCoordinate && session.currentSpace) {
        // Scry in current space
        return scryCoordinate(teamId, session, session.currentSpace, firstPart);
    }

    // Coordinate with no space selected — 0 = superposition of all spaces = list
    if (isCoordinate && !session.currentSpace) {
        if (firstPart === '0' || firstPart === 'root') {
            const names = await listAllSpaces(teamId);
            return {
                view: names.length === 0
                    ? 'No spaces. Type a name to create one.'
                    : `⟨0⟩ All spaces:\n${names.map((n, i) => `  ${i + 1}. ${n}`).join('\n')}`,
                data: { spaces: names },
                cursor: { space: null, coordinate: '0' },
            };
        }
        return {
            view: 'No space selected. Type a space name first, or \"0\" to see all spaces.',
            cursor: { space: null, coordinate: 'root' },
        };
    }

    if (!isCoordinate) {
        // First part is a space name
        const spaceName = firstPart;
        const remainingParts = parts.slice(1);

        // ═══ Compound command detection ═══
        // Formats supported:
        //   {Space} {coord} lock
        //   {Space} {coord} freeze
        //   {Space} {coord} add {label...}
        //   {Space} {coord} attr {name} {val1|val2} [default]
        //   {Space} bloom {coord}
        //   {Space} mine [{coord}]

        // Find action keyword position in remaining parts
        const actionIndex = remainingParts.findIndex(p =>
            ['lock', 'freeze', 'add', 'attr', 'bloom', 'mine', 'swarm', 'orbits', 'kernel', 'gram', 'tower', 'reify', 'math', 'all_math', 'signature'].includes(p.toLowerCase())
        );

        if (actionIndex >= 0) {
            const action = remainingParts[actionIndex].toLowerCase();
            const coordParts = remainingParts.slice(0, actionIndex);
            const actionArgs = remainingParts.slice(actionIndex + 1);
            const coord = coordParts.length > 0 ? coordParts.join('.') : 'root';

            // Set session position atomically
            session.currentSpace = spaceName;
            session.currentCoordinate = coord;

            const { cb: crystal, rowId } = await loadCb(teamId, spaceName);
            const node = coord === 'root'
                ? crystal.nodes.get(crystal.rootId)
                : cbEvalLocal(crystal, coord).nodes[0];

            // ─── LOCK ───
            if (action === 'lock') {
                if (!node) {
                    return { view: `Nothing to lock at ${coord}.`, cursor: { space: spaceName, coordinate: coord } };
                }
                lockNode(crystal, node.id);
                await saveCb(rowId, crystal);

                const kernel = isKernelComplete(crystal);
                const progress = `[${kernel.lockedCount}/${kernel.totalSlotted} locked]`;

                if (kernel.complete) {
                    const scryResult = cbScry(registry, spaceName, '0');
                    const mineResult = computeMinePlane(registry, spaceName, '0');
                    return {
                        view: `🔒 Locked: ${node.label} — KERNEL COMPLETE ${progress}\n\n⚡ AUTO-SCRY triggered\n⛏️ AUTO-MINE: ${mineResult.totalPaths} configs, ${mineResult.points.length} points\n\n${spaceToView(crystal)}`,
                        data: { ...nodeToData(node), kernelComplete: true, kernelProgress: kernel, autoScry: true, scryResult, mineResult },
                        cursor: { space: spaceName, coordinate: '0' },
                    };
                }
                return {
                    view: `🔒 Locked: ${node.label} ${progress}\n\n${spaceToView(crystal)}`,
                    data: { ...nodeToData(node), kernelComplete: false, kernelProgress: kernel },
                    cursor: { space: spaceName, coordinate: coord },
                };
            }

            // ─── FREEZE ───
            if (action === 'freeze') {
                if (!node) {
                    return { view: `Nothing to freeze at ${coord}.`, cursor: { space: spaceName, coordinate: coord } };
                }
                const result = await freezeWithYouknow(crystal, node.id, session.youknowFn);
                await saveCb(rowId, crystal);
                const uarlPreview = result.uarl ? `\n📜 UARL: ${result.uarl.raw}` : '';
                const youknowStatus = result.youknowResult
                    ? (result.accepted ? '\n✅ YOUKNOW: accepted' : `\n❌ YOUKNOW: ${result.youknowResult}`)
                    : '';
                return {
                    view: `🧊 Frozen: ${node.label}${uarlPreview}${youknowStatus}\n\n${spaceToView(crystal)}`,
                    data: { ...nodeToData(node), uarl: result.uarl, youknowResult: result.youknowResult, accepted: result.accepted },
                    cursor: { space: spaceName, coordinate: coord },
                };
            }

            // ─── ADD (add child node) ───
            // Format: {Space} {coord} add {label...}
            if (action === 'add') {
                const label = actionArgs.join(' ');
                if (!label) {
                    return { view: 'Usage: {Space} {coord} add {label}', cursor: { space: spaceName, coordinate: coord } };
                }
                if (!node) {
                    return { view: `No node at ${coord}.`, cursor: { space: spaceName, coordinate: coord } };
                }
                const newNode = addNode(crystal, node.id, label);
                await saveCb(rowId, crystal);
                return {
                    view: `Added "${label}" under ${node.label}\n\n${spaceToView(crystal)}`,
                    data: { ...nodeToData(newNode), parentId: node.id, parentLabel: node.label },
                    cursor: { space: spaceName, coordinate: coord },
                };
            }

            // ─── ATTR (add attribute) ───
            // Format: {Space} {coord} attr {name} {val1|val2} [default]
            if (action === 'attr') {
                // DEPRECATED: attributes removed, children ARE the spectrum
                return {
                    view: '⚠️ The "attr" command is deprecated. Children ARE the spectrum.\nUse the coordinate system to add children.',
                    cursor: { space: spaceName, coordinate: coord },
                };
            }

            // ─── BLOOM (navigate into a node's interior) ───
            // Format: {Space} bloom {coord}
            if (action === 'bloom') {
                const bloomTarget = actionArgs[0] || coord;
                const targetNode = bloomTarget === 'root'
                    ? crystal.nodes.get(crystal.rootId)
                    : cbEvalLocal(crystal, bloomTarget).nodes[0];
                if (!targetNode) {
                    return { view: `No node at ${bloomTarget} to bloom into.`, cursor: { space: spaceName, coordinate: coord } };
                }
                // Bloom = enter the node's interior (navigate to it)
                session.currentSpace = spaceName;
                session.currentCoordinate = bloomTarget;
                return {
                    view: `🌸 Bloomed into ${targetNode.label}\n\n${spaceToView(crystal)}`,
                    data: nodeToData(targetNode),
                    cursor: { space: spaceName, coordinate: bloomTarget },
                };
            }

            // ─── MINE (compute configuration space) ───
            // Format: {Space} mine [{coord}]
            if (action === 'mine') {
                // "mine view" subcommand
                if (actionArgs[0] === 'view') {
                    const ms = mineSpaceCache.get(spaceName);
                    if (ms) {
                        const valid = ms.known.filter(p => p.status === 'valid');
                        const adjacent = ms.known.filter(p => p.status === 'adjacent');
                        return {
                            view: `📊 MineSpace: ${spaceName}\n` +
                                `Valid: ${valid.length}, Adjacent: ${adjacent.length}\n` +
                                `Kernels: ${ms.projectedKernels.join(', ')}\n\n` +
                                `Valid points:\n` +
                                valid.map(p => `  ${p.coordinate} → 0.${p.encoded} (ℝ=${p.x})`).join('\n'),
                            data: ms,
                            cursor: { space: spaceName, coordinate: '0' },
                        };
                    }
                    return {
                        view: `No mineSpace for ${spaceName}. Run "${spaceName} mine" first.`,
                        cursor: { space: spaceName, coordinate: '0' },
                    };
                }

                const mineCoord = actionArgs[0] || coord || '0';
                const mineResult = computeMinePlane(registry, spaceName, mineCoord);

                // Compute and persist the full mineSpace
                let mineSpace: MineSpace;
                try {
                    mineSpace = computeMineSpace(registry, spaceName);
                } catch (e: any) {
                    console.error('computeMineSpace error:', e.message, e.stack);
                    return {
                        view: `Mine viz OK, but mineSpace computation failed: ${e.message}`,
                        data: mineResult,
                        cursor: { space: spaceName, coordinate: mineCoord },
                    };
                }
                mineSpaceCache.set(spaceName, mineSpace);

                // Persist mineSpace by updating the existing data blob directly
                try {
                    const rows = await db.select().from(spaces).where(and(eq(spaces.teamId, teamId), eq(spaces.name, spaceName)));
                    if (rows.length > 0) {
                        const existingData = rows[0].data as any;
                        existingData.mineSpace = mineSpace;
                        await db.update(spaces).set({ data: existingData, updatedAt: new Date() }).where(eq(spaces.id, rows[0].id));
                    }
                } catch (e: any) {
                    console.error('MineSpace persist error:', e.message);
                }

                const valid = mineSpace.known.filter(p => p.status === 'valid');
                const adjacent = mineSpace.known.filter(p => p.status === 'adjacent');

                return {
                    view: `⛏️ Mine: ${spaceName} @ ${mineCoord}\n` +
                        `${mineResult.totalPaths} configurations, ${mineResult.points.length} points\n` +
                        `Space heat: ${mineResult.spaceHeat.toFixed(2)}\n` +
                        `Kernel: ${mineResult.kernelComplete ? 'COMPLETE' : 'incomplete'}\n` +
                        `Max depth: ${mineResult.maxDepth}\n` +
                        `MineSpace: ${valid.length} valid, ${adjacent.length} adjacent (persisted)`,
                    data: { ...mineResult, mineSpace },
                    cursor: { space: spaceName, coordinate: mineCoord },
                };
            }

            // ─── SWARM ───
            if (action === 'swarm') {
                const n = actionArgs[0] ? parseInt(actionArgs[0], 10) || 5 : 5;

                // If first arg is "apply" → apply LLM results
                if (actionArgs[0] === 'apply') {
                    const actionsJson = actionArgs.slice(1).join(' ');
                    try {
                        const actions = JSON.parse(actionsJson);
                        const nodesCreated = applySwarmActions(crystal, actions);
                        await saveCb(rowId, crystal);
                        return {
                            view: `🐙 Swarm applied: ${nodesCreated} nodes created\n\n${spaceToView(crystal)}`,
                            data: { nodesCreated, actions },
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    } catch (e: any) {
                        return {
                            view: `❌ Swarm apply failed: ${e.message}`,
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    }
                }

                // Otherwise → build prompt, return for MCP to call LLM
                const mineResult = computeMinePlane(registry, spaceName, '0');
                const promptCtx = buildSwarmPrompt(crystal, coord, session.phase, mineResult, n);
                const prompt = renderPrompt(promptCtx);

                return {
                    view: `🐙 Swarm prompt ready for ${spaceName} (${n} actions requested).`,
                    data: {
                        llm_request: {
                            prompt,
                            context: promptCtx,
                            space: spaceName,
                            coordinate: coord,
                            n,
                        },
                    },
                    cursor: { space: spaceName, coordinate: coord },
                };
            }

            // ─── ORBITS (per-slot orbit decomposition) ───
            // Format: {Space} orbits
            if (action === 'orbits') {
                try {
                    const sig = computeSpaceSlotSignature(registry, spaceName);
                    const lines: string[] = [
                        `🔮 Orbit Decomposition: ${spaceName}`,
                        `Canonical: ${sig.canonical}`,
                        `Total symmetry: ${sig.totalSymmetry}`,
                        `Total configurations: ${sig.totalConfigurations}`,
                        '',
                    ];
                    for (const slot of sig.slots) {
                        lines.push(`  Slot ${slot.slotIndex} (${slot.parentLabel}):`);
                        lines.push(`    Spectrum size: ${slot.spectrumSize}`);
                        lines.push(`    Symmetry: ${slot.symmetryGroup}`);
                        lines.push(`    Superposition meaning: ${slot.superpositionMeaning}`);
                        for (const orbit of slot.orbits) {
                            lines.push(`    Orbit [${orbit.labels.join(', ')}] size=${orbit.size}`);
                        }
                        lines.push('');
                    }
                    return {
                        view: lines.join('\n'),
                        data: sig,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                } catch (e: any) {
                    return {
                        view: `Orbit computation failed: ${e.message}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── SIGNATURE (canonical signature string) ───
            // Format: {Space} signature
            if (action === 'signature') {
                try {
                    const sig = computeSpaceSlotSignature(registry, spaceName);
                    return {
                        view: `📐 ${spaceName}: ${sig.canonical}`,
                        data: { canonical: sig.canonical, totalSymmetry: sig.totalSymmetry, totalConfigurations: sig.totalConfigurations },
                        cursor: { space: spaceName, coordinate: coord },
                    };
                } catch (e: any) {
                    return {
                        view: `Signature failed: ${e.message}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── KERNEL (tensor product kernel between two coordinates) ───
            // Format: {Space} kernel {coordX} {coordY}
            if (action === 'kernel') {
                const coordX = actionArgs[0];
                const coordY = actionArgs[1];
                if (!coordX || !coordY) {
                    return {
                        view: `Usage: ${spaceName} kernel {coordX} {coordY}\nComputes K(x,y) = ∏ K_k(x_k, y_k) — tensor product RKHS kernel.`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
                try {
                    const result = tensorKernel(registry, spaceName, coordX, coordY);
                    const lines: string[] = [
                        `🧮 K(${coordX}, ${coordY}) = ${result.value.toFixed(6)}`,
                        `Depth: ${result.depth}`,
                        '',
                        'Per-slot breakdown:',
                    ];
                    for (const slot of result.perSlot) {
                        const xLabel = slot.valueX.isSuperposition ? '0(superposition)' : `${slot.valueX.selectionIndex}`;
                        const yLabel = slot.valueY.isSuperposition ? '0(superposition)' : `${slot.valueY.selectionIndex}`;
                        lines.push(`  Slot ${slot.slotIndex}: K_k(${xLabel}, ${yLabel}) = ${slot.similarity.toFixed(6)}`);
                    }
                    return {
                        view: lines.join('\n'),
                        data: result,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                } catch (e: any) {
                    return {
                        view: `Kernel computation failed: ${e.message}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── GRAM (Gram matrix of all valid mine coordinates) ───
            // Format: {Space} gram
            if (action === 'gram') {
                try {
                    // Get coordinates from mine
                    const mineResult = computeMinePlane(registry, spaceName);
                    const coords = mineResult.points
                        .filter(p => p.coordinate !== '0')
                        .map(p => p.coordinate);

                    if (coords.length === 0) {
                        return {
                            view: `No coordinates to compute Gram matrix for ${spaceName}.`,
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    }

                    // Cap at 20 coordinates to avoid explosion
                    const cappedCoords = coords.slice(0, 20);
                    const result = tensorGramMatrix(registry, spaceName, cappedCoords);
                    const n = cappedCoords.length;

                    const lines: string[] = [
                        `📊 Gram Matrix: ${spaceName} (${n}×${n})`,
                        cappedCoords.length < coords.length
                            ? `(showing first ${n} of ${coords.length} coordinates)`
                            : '',
                        '',
                        // Header row
                        '     ' + cappedCoords.map(c => c.padStart(6)).join(' '),
                    ];
                    for (let i = 0; i < n; i++) {
                        const row = result.matrix[i].map(v => v.toFixed(3).padStart(6)).join(' ');
                        lines.push(`${cappedCoords[i].padStart(4)} ${row}`);
                    }

                    // Find near-identical pairs (K > 0.9 and not identity)
                    const similar: string[] = [];
                    for (let i = 0; i < n; i++) {
                        for (let j = i + 1; j < n; j++) {
                            if (result.matrix[i][j] > 0.9) {
                                similar.push(`  ${cappedCoords[i]} ≈ ${cappedCoords[j]} (K=${result.matrix[i][j].toFixed(4)})`);
                            }
                        }
                    }
                    if (similar.length > 0) {
                        lines.push('', 'Near-identical pairs (K > 0.9):');
                        lines.push(...similar);
                    }

                    return {
                        view: lines.join('\n'),
                        data: result,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                } catch (e: any) {
                    return {
                        view: `Gram matrix failed: ${e.message}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── TOWER (build Futamura tower) ───
            // Format: {Space} tower [levels]       — structural only
            //         {Space} tower llm [levels]    — LLM-backed (decrypts at each level)
            if (action === 'tower') {
                const useLLM = actionArgs[0]?.toLowerCase() === 'llm';
                const levelArg = useLLM ? actionArgs[1] : actionArgs[0];
                const levels = levelArg ? parseInt(levelArg, 10) || 4 : 4;
                try {
                    // Auto-wrap space as kernel if needed
                    let kernelId: number | undefined;
                    for (const [id, k] of registry.kernels) {
                        if (k.space.name === spaceName) {
                            kernelId = id;
                            break;
                        }
                    }
                    if (kernelId === undefined) {
                        // Create kernel from existing space
                        const kernel = createKernel(registry, spaceName);
                        // Copy nodes from the existing space into the kernel's space
                        const existingSpace = registry.spaces.get(spaceName);
                        if (existingSpace) {
                            kernel.space = existingSpace;
                        }
                        // Auto-lock: set slot counts and lock all nodes with >= 2 children
                        for (const [nodeId, node] of kernel.space.nodes) {
                            if (nodeId !== 'root' && node.children.length >= 2) {
                                setSlotCount(kernel.space, nodeId, 1);
                                lockNode(kernel.space, nodeId);
                            }
                        }
                        const lockResult = lockKernel(registry, kernel.globalId);
                        if (!lockResult.success) {
                            return {
                                view: `Cannot build tower: space "${spaceName}" couldn't auto-lock.\n` +
                                    `Unlocked: ${lockResult.unlockedSlots.map(s => s.label).join(', ')}\n` +
                                    `Insufficient children: ${lockResult.insufficientChildren.map(s => `${s.label}(${s.childCount})`).join(', ')}`,
                                cursor: { space: spaceName, coordinate: coord },
                            };
                        }
                        kernelId = kernel.globalId;
                    }

                    if (useLLM) {
                        // ═══ LLM-BACKED TOWER ═══
                        // At each level: reify → LLM decrypts orbits → apply → iterate
                        const towerLevels: Array<{ level: number; canonical: string; symmetry: string; llmDecryption?: string }> = [];
                        let currentKernelId = kernelId;
                        let stableAt: number | null = null;
                        const lines: string[] = [
                            `🗼🧠 LLM-Backed Futamura Tower: ${spaceName} (max ${levels} levels)`,
                            '',
                        ];

                        for (let i = 0; i < levels; i++) {
                            // Step 1: Compute orbit signature at current level
                            const currentKernel = registry.kernels.get(currentKernelId);
                            if (!currentKernel) break;

                            const sig = computeSpaceSlotSignature(registry, currentKernel.space.name);
                            const partition = sig.slots
                                .flatMap(s => s.orbits.map(o => o.size))
                                .sort((a, b) => b - a);
                            const canonical = sig.canonical;

                            // Check stability
                            const isStable = i > 0 && towerLevels[i - 1].canonical === canonical;
                            if (isStable && stableAt === null) stableAt = i;

                            lines.push(`  T^${i}:`);
                            lines.push(`    partition:  [${partition.join(',')}]`);
                            lines.push(`    symmetry:   ${sig.totalSymmetry}`);

                            if (isStable) {
                                lines.push(`    vs prev:    ✅ STABLE`);
                                towerLevels.push({ level: i, canonical, symmetry: sig.totalSymmetry });
                                lines.push('');
                                break; // Converged!
                            }
                            if (i > 0) {
                                lines.push(`    vs prev:    ❌ different`);
                            }

                            // Step 2: Build LLM prompt — describe ALL nodes, ask for sub-elements
                            // Include orbits AND fixed points — every node needs >= 2 children
                            const nodeDescriptions: string[] = [];
                            let nodeCount = 0;
                            for (const slot of sig.slots) {
                                for (const orbit of slot.orbits) {
                                    nodeCount++;
                                    if (orbit.size > 1) {
                                        nodeDescriptions.push(
                                            `Node ${nodeCount} — orbit (${orbit.size} equivalent items) under "${slot.parentLabel}": [${orbit.labels.join(', ')}]`
                                        );
                                    } else {
                                        nodeDescriptions.push(
                                            `Node ${nodeCount} — fixed point under "${slot.parentLabel}": "${orbit.labels[0]}"`
                                        );
                                    }
                                }
                            }

                            // Ask for LOTS of sub-elements — every node needs at least 2 children
                            const prompt = `I have this ontology "${spaceName}" and I need to DEEPEN every part of it. Here are the structural groups I've found:

${nodeDescriptions.join('\n')}

For EACH node above, I need you to generate sub-elements — the things that COMPOSE it or DIFFERENTIATE it. Each node needs AT LEAST 2 sub-elements, ideally 5-10.

For orbits (groups of equivalent items): name the group, then generate sub-categories that distinguish the members. What makes them different within the group? What are the axes of variation?

For fixed points (unique items): what are the internal aspects, components, or dimensions of this concept? Break it down.

Generate many actions. Each action's parentId should be "Node_1", "Node_2" etc matching the node numbers above. Give me as many sub-elements as you can see — at least ${nodeCount * 3} total.`;

                            // Step 3: Call LLM — request 100+ actions
                            let llmResult: any;
                            try {
                                llmResult = execSwarmViaDocker(spaceName, 'tower', prompt, Math.max(nodeCount * 5, 100));
                                lines.push(`    🧠 LLM: ${llmResult.rationale?.slice(0, 120) || '(decrypting...)'}`);

                                const actions = llmResult.actions || [];
                                lines.push(`    📊 ${actions.length} actions returned for ${nodeCount} nodes`);

                                // Step 4: Reify, rename nodes, and add LLM-generated children
                                try {
                                    const reified = reifyMineSpace(registry, currentKernelId, i);

                                    // Map node indices to reified node IDs
                                    const reifiedNodes: Array<{ nodeId: string; node: any; orbitLabels: string[] }> = [];
                                    let nodeIdx = 0;
                                    for (const slot of sig.slots) {
                                        for (const orbit of slot.orbits) {
                                            // Find the matching reified node
                                            for (const [nId, n] of reified.kernel.space.nodes) {
                                                if (nId !== 'root' && !reifiedNodes.some(r => r.nodeId === nId)) {
                                                    reifiedNodes.push({ nodeId: nId, node: n, orbitLabels: orbit.labels });
                                                    break;
                                                }
                                            }
                                            nodeIdx++;
                                        }
                                    }

                                    // Apply LLM actions as children — match by parentId "Node_N"
                                    for (const act of actions) {
                                        const nodeMatch = act.parentId?.match(/Node_(\d+)/);
                                        if (nodeMatch) {
                                            const idx = parseInt(nodeMatch[1], 10) - 1;
                                            if (idx >= 0 && idx < reifiedNodes.length) {
                                                addNode(reified.kernel.space, reifiedNodes[idx].nodeId, act.label);
                                            }
                                        } else if (act.parentId === 'root') {
                                            // Fallback: distribute actions across nodes that need children
                                            for (const rn of reifiedNodes) {
                                                if (rn.node.children.length < 2) {
                                                    addNode(reified.kernel.space, rn.nodeId, act.label);
                                                    break;
                                                }
                                            }
                                        }
                                    }

                                    // Also add original orbit members as children for orbit nodes
                                    for (let ri = 0; ri < reifiedNodes.length; ri++) {
                                        const rn = reifiedNodes[ri];
                                        if (rn.orbitLabels.length > 1) {
                                            // Orbit — add original members as children
                                            for (const member of rn.orbitLabels) {
                                                addNode(reified.kernel.space, rn.nodeId, member);
                                            }
                                        }
                                    }

                                    // Report what we got
                                    for (const rn of reifiedNodes) {
                                        const childCount = rn.node.children.length;
                                        lines.push(`    📎 "${rn.node.label}": ${childCount} children${childCount < 2 ? ' ⚠️ NEEDS MORE' : ''}`);
                                    }

                                    // Lock nodes with >= 2 children (the rule)
                                    for (const [nodeId, node] of reified.kernel.space.nodes) {
                                        if (nodeId !== 'root' && node.children.length >= 2) {
                                            setSlotCount(reified.kernel.space, nodeId, 1);
                                            lockNode(reified.kernel.space, nodeId);
                                        }
                                    }
                                    lockKernel(registry, reified.kernel.globalId);

                                    currentKernelId = reified.kernel.globalId;
                                    towerLevels.push({
                                        level: i,
                                        canonical,
                                        symmetry: sig.totalSymmetry,
                                        llmDecryption: llmResult.rationale?.slice(0, 200),
                                    });
                                } catch (reifyErr: any) {
                                    lines.push(`    ⚠️ Reify failed: ${reifyErr.message}`);
                                    towerLevels.push({ level: i, canonical, symmetry: sig.totalSymmetry });
                                    break;
                                }
                            } catch (llmErr: any) {
                                lines.push(`    ⚠️ LLM call failed: ${llmErr.message?.slice(0, 100)}`);
                                towerLevels.push({ level: i, canonical, symmetry: sig.totalSymmetry });
                                break;
                            }

                            lines.push('');
                        }

                        lines.push('  ─────────────────────────────────');
                        if (stableAt !== null) {
                            lines.push(`  ✅ IDEMPOTENCE VERIFIED (LLM-backed)`);
                            lines.push(`     stable_at = ${stableAt}`);
                            lines.push(`     T^${stableAt} = T^∞`);
                            lines.push(`     Fixed point: ${towerLevels[stableAt]?.canonical}`);
                            lines.push(`     SOLUTION SPACE: LLM naming became idempotent`);
                        } else {
                            lines.push(`  ❌ NOT YET STABLE after ${towerLevels.length} levels`);
                            if (towerLevels.length > 0) {
                                lines.push(`     Last: ${towerLevels[towerLevels.length - 1].canonical}`);
                            }
                        }

                        return {
                            view: lines.join('\n'),
                            data: { tower: towerLevels, stableAt, llmBacked: true },
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    } else {
                        // ═══ STRUCTURAL TOWER (no LLM) ═══
                        const towerResult = buildFutamuraTower(registry, kernelId, levels);
                        const lines: string[] = [
                            `🗼 Futamura Tower: ${spaceName} (${towerResult.levels.length} levels)`,
                            '',
                        ];

                        let stableAt: number | null = null;
                        for (let i = 0; i < towerResult.levels.length; i++) {
                            const t = towerResult.levels[i];
                            const partition = t.slotSignature.slots
                                .flatMap(s => s.orbits.map(o => o.size))
                                .sort((a, b) => b - a);
                            const isStable = i > 0 && t.slotSignature.canonical === towerResult.levels[i - 1].slotSignature.canonical;
                            if (isStable && stableAt === null) stableAt = i;

                            lines.push(`  T^${i}:`);
                            lines.push(`    partition:  [${partition.join(',')}]`);
                            lines.push(`    symmetry:   ${t.slotSignature.totalSymmetry}`);
                            if (i > 0) {
                                lines.push(`    vs prev:    ${isStable ? '✅ STABLE' : '❌ different'}`);
                            }
                            lines.push('');
                        }

                        // Catastrophe events
                        if (towerResult.catastrophes.length > 0) {
                            lines.push('  ⚡ CATASTROPHE EVENTS:');
                            for (const c of towerResult.catastrophes) {
                                lines.push(`    T^${c.level} [Class ${c.class}] (severity: ${(c.severity * 100).toFixed(0)}%${c.liftable ? '' : ' ⛔ non-liftable'}): ${c.detail}`);
                            }
                            lines.push(`  |Ш| = ${towerResult.sha} (non-liftable obstructions)`);
                            lines.push('');
                        }

                        lines.push('  ─────────────────────────────────');
                        if (towerResult.crowned) {
                            lines.push(`  👑 CROWNED — McKay-Thompson convergence at T^${towerResult.crownLevel}`);
                            lines.push(`     Tower is self-hosting: meta-circular fixed point reached`);
                            lines.push(`     Fixed point: ${towerResult.levels[towerResult.crownLevel!].slotSignature.canonical}`);
                        } else if (stableAt !== null) {
                            lines.push(`  ✅ IDEMPOTENCE VERIFIED`);
                            lines.push(`     stable_at = ${stableAt}`);
                            lines.push(`     T^${stableAt} = T^${stableAt + 1} = ... = T^∞`);
                            lines.push(`     Fixed point: ${towerResult.levels[stableAt].slotSignature.canonical}`);
                            lines.push(`     SOLUTION SPACE: all remaining choice is symmetric`);
                        } else {
                            lines.push(`  ❌ NOT YET STABLE after ${towerResult.levels.length} levels`);
                        }

                        return {
                            view: lines.join('\n'),
                            data: {
                                tower: towerResult.levels.map(t => ({ level: t.level, canonical: t.slotSignature.canonical, symmetry: t.slotSignature.totalSymmetry })),
                                catastrophes: towerResult.catastrophes,
                                sha: towerResult.sha,
                                crowned: towerResult.crowned,
                                crownLevel: towerResult.crownLevel,
                                stableAt,
                            },
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    }
                } catch (e: any) {
                    return {
                        view: `Tower failed: ${e.message}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── REIFY (one T-operator step) ───
            // Format: {Space} reify
            if (action === 'reify') {
                try {
                    let kernelId: number | undefined;
                    for (const [id, k] of registry.kernels) {
                        if (k.space.name === spaceName) {
                            kernelId = id;
                            break;
                        }
                    }
                    if (kernelId === undefined) {
                        const kernel = createKernel(registry, spaceName);
                        const existingSpace = registry.spaces.get(spaceName);
                        if (existingSpace) {
                            kernel.space = existingSpace;
                        }
                        for (const [nodeId, node] of kernel.space.nodes) {
                            if (nodeId !== 'root' && node.children.length >= 2) {
                                setSlotCount(kernel.space, nodeId, 1);
                                lockNode(kernel.space, nodeId);
                            }
                        }
                        lockKernel(registry, kernel.globalId);
                        kernelId = kernel.globalId;
                    }

                    const result = reifyMineSpace(registry, kernelId);
                    const sig = result.slotSignature;
                    return {
                        view: `♻️ Reified ${spaceName} → ${result.kernel.space.name}\n` +
                            `Canonical: ${sig.canonical}\n` +
                            `Symmetry: ${sig.totalSymmetry}\n` +
                            `Nodes in reified kernel: ${result.kernel.space.nodes.size}`,
                        data: { reifiedSpace: result.kernel.space.name, canonical: sig.canonical, symmetry: sig.totalSymmetry, level: result.level },
                        cursor: { space: result.kernel.space.name, coordinate: 'root' },
                    };
                } catch (e: any) {
                    return {
                        view: `Reify failed: ${e.message}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── ALL_MATH (complete formal mathematical output) ───
            // Format: {Space} all_math
            // Outputs EVERY mathematical definition and computed value
            // with full formal definitions using the CB encoding system.
            // NO summaries. NO help menus. COMPLETE math.
            if (action === 'all_math') {
                try {
                    const space = registry.spaces.get(spaceName);
                    if (!space) {
                        return {
                            view: `Space "${spaceName}" not found.`,
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    }

                    const alpha = 5.0;
                    const nodeCount = space.nodes.size - 1; // exclude root
                    const root = space.nodes.get(space.rootId);
                    const rootChildren = root?.children ?? [];

                    // ── Collect all mineable coordinates ──
                    const mineResult = computeMinePlane(registry, spaceName);
                    const allCoords = mineResult.points
                        .filter(p => p.coordinate !== '0' && p.coordinate !== 'root')
                        .map(p => p.coordinate);
                    const cappedCoords = allCoords.slice(0, 20); // cap for matrix sanity
                    const n = cappedCoords.length;

                    // Real-number coordinates: THE actual coordinate is 0.{encoded_digits}
                    // The Dewey path (e.g., "1.1") is just human shorthand.
                    // In the encoding, dots become 8988, so "1.1" → "189881" → 0.189881
                    const realCoords = cappedCoords.map(c => coordToReal(c));
                    // Display helper: show coord as its real number
                    const R = (c: string) => coordToReal(c).toString();

                    const lines: string[] = [];

                    // ══════════════════════════════════════════════════════
                    // §0. SPACE IDENTITY
                    // ══════════════════════════════════════════════════════
                    lines.push(`═══════════════════════════════════════════════════════`);
                    lines.push(`  COMPLETE MATHEMATICAL OUTPUT: ${spaceName}`);
                    lines.push(`  ${nodeCount} nodes, ${rootChildren.length} top-level spectrum values`);
                    lines.push(`  ${n} mineable coordinates${n < allCoords.length ? ` (${allCoords.length} total, showing ${n})` : ''}`);
                    lines.push(`═══════════════════════════════════════════════════════`);
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §1. ENCODING SYSTEM
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §1. ENCODING SYSTEM ───────────────────────────────`);
                    lines.push(`Crystal Ball uses a 10-token coordinate grammar {0,1,2,3,4,5,6,7,8,9}`);
                    lines.push(`where each position encodes structure, not semantics.`);
                    lines.push('');
                    lines.push(`  Token   Meaning`);
                    lines.push(`  0       Superposition (not yet selected)`);
                    lines.push(`  1-7     Select child at position 1-7`);
                    lines.push(`  8       Drill (enter subspace)`);
                    lines.push(`  88      Close drill (exit subspace)`);
                    lines.push(`  9       Wrap (+7 to selection accumulator)`);
                    lines.push(`  8988    Dot separator (level boundary)`);
                    lines.push(`  90...900  Kernel ID delimiter`);
                    lines.push(`  90009   ALSO_OPEN (concurrent path)`);
                    lines.push(`  9900099 ALSO_CLOSE (end concurrent path)`);
                    lines.push('');
                    lines.push(`  Encoding: coordToReal(c) = parseFloat("0." + encodeDot(c))`);
                    lines.push(`  encodeDot replaces "." with "8988" to produce an impossible digit string.`);
                    lines.push('');

                    // Show actual encoding for each coordinate
                    lines.push(`  Coordinate → Encoded → Real Number`);
                    for (const c of cappedCoords) {
                        const encoded = encodeDot(c);
                        const real = coordToReal(c);
                        lines.push(`  ${c.padEnd(12)} → ${encoded.padEnd(20)} → ${real}`);
                    }
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §2. RKHS KERNEL FUNCTION DEFINITION
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §2. REPRODUCING KERNEL HILBERT SPACE (RKHS) ──────`);
                    lines.push('');
                    lines.push(`  The RKHS is defined by the tensor product kernel:`);
                    lines.push('');
                    lines.push(`    K(x, y) = ∏ₖ Kₖ(xₖ, yₖ)`);
                    lines.push('');
                    lines.push(`  where k ranges over SLOTS (levels between dots),`);
                    lines.push(`  and each per-slot kernel is a Gaussian RBF on primacy distance:`);
                    lines.push('');
                    lines.push(`    Kₖ(xₖ, yₖ) = exp(-α · |real(xₖ) - real(yₖ)|²)`);
                    lines.push('');
                    lines.push(`  Parameters:`);
                    lines.push(`    α = ${alpha} (bandwidth — higher = more sensitive to primacy distance)`);
                    lines.push('');
                    lines.push(`  Special cases:`);
                    lines.push(`    Kₖ(x, x) = 1.0                               (identical selection)`);
                    lines.push(`    Kₖ(0, y) = Kₖ(x, 0) = 1/√n                  (superposition = uniform over n values)`);
                    lines.push(`    Kₖ(0, 0) = 1.0                               (both superposed = both equivalent)`);
                    lines.push('');
                    lines.push(`  Hilbert Space:`);
                    lines.push(`    H = H₀ ⊗ H₁ ⊗ H₂ ⊗ ... ⊗ H_d`);
                    lines.push(`    Hₖ = span of spectrum values at slot k`);
                    lines.push(`    H_K = span{K(·,x) : x ∈ MineSpace}           (the RKHS induced by K)`);
                    lines.push('');
                    lines.push(`  Inner Product:`);
                    lines.push(`    ⟨f, g⟩_K = Σᵢ Σⱼ aᵢ bⱼ K(xᵢ, xⱼ)`);
                    lines.push(`    where f = Σᵢ aᵢ K(·,xᵢ) and g = Σⱼ bⱼ K(·,xⱼ)`);
                    lines.push('');
                    lines.push(`  Reproducing Property:`);
                    lines.push(`    f(x) = ⟨f, K(·,x)⟩_K    for all f ∈ H_K`);
                    lines.push(`    This IS homoiconicity: evaluation (scry) IS an element of the space.`);
                    lines.push('');

                    if (n === 0) {
                        lines.push(`  [No coordinates to compute — mine the space first]`);
                        return {
                            view: lines.join('\n'),
                            data: { spaceName, nodeCount, coordCount: 0 },
                            cursor: { space: spaceName, coordinate: coord },
                        };
                    }

                    // ══════════════════════════════════════════════════════
                    // §3. PAIRWISE KERNEL VALUES
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §3. PAIRWISE KERNEL VALUES ────────────────────────`);
                    lines.push('');

                    // Compute a few representative kernel values with full detail
                    const showPairs = Math.min(5, Math.floor(n * (n - 1) / 2));
                    let pairCount = 0;
                    for (let i = 0; i < n && pairCount < showPairs; i++) {
                        for (let j = i + 1; j < n && pairCount < showPairs; j++) {
                            const result = tensorKernel(registry, spaceName, cappedCoords[i], cappedCoords[j], alpha);
                            const realX = coordToReal(cappedCoords[i]);
                            const realY = coordToReal(cappedCoords[j]);
                            lines.push(`  K(${realX}, ${realY}):`);
                            lines.push(`    x = ${realX}  (path: ${cappedCoords[i]} → encoded: ${encodeDot(cappedCoords[i])})`);
                            lines.push(`    y = ${realY}  (path: ${cappedCoords[j]} → encoded: ${encodeDot(cappedCoords[j])})`);
                            lines.push(`    K(x,y) = ${result.value.toFixed(10)}`);
                            if (result.amplitudeWeight > 0) {
                                lines.push(`    Quantum K(x,y) = √(|ψ_x|²·|ψ_y|²) · K = ${result.amplitudeWeight.toFixed(6)} · ${result.value.toFixed(6)} = ${result.quantumValue.toFixed(10)}`);
                            }
                            lines.push(`    Per-slot decomposition (K = ∏ Kₖ):`);
                            for (const slot of result.perSlot) {
                                const xLabel = slot.valueX.isSuperposition ? '0 (superposition)' : `${slot.valueX.selectionIndex} (real=${slot.valueX.real})`;
                                const yLabel = slot.valueY.isSuperposition ? '0 (superposition)' : `${slot.valueY.selectionIndex} (real=${slot.valueY.real})`;
                                if (slot.valueX.isSuperposition || slot.valueY.isSuperposition) {
                                    const specSize = root?.children.length ?? 7;
                                    lines.push(`      Slot ${slot.slotIndex}: Kₖ(${xLabel}, ${yLabel}) = 1/√${specSize} = ${slot.similarity.toFixed(10)}`);
                                } else {
                                    lines.push(`      Slot ${slot.slotIndex}: Kₖ(${xLabel}, ${yLabel}) = exp(-${alpha} · |${slot.valueX.real} - ${slot.valueY.real}|²) = ${slot.similarity.toFixed(10)}`);
                                }
                            }
                            lines.push('');
                            pairCount++;
                        }
                    }

                    // ══════════════════════════════════════════════════════
                    // §4. GRAM MATRIX
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §4. GRAM MATRIX G ─────────────────────────────────`);
                    lines.push('');
                    lines.push(`  G[i,j] = K(xᵢ, xⱼ) = ∏ₖ exp(-α · |real(xᵢ_k) - real(xⱼ_k)|²)`);
                    lines.push(`  α = ${alpha}, n = ${n}`);
                    lines.push('');

                    const gramResult = tensorGramMatrix(registry, spaceName, cappedCoords, alpha);

                    // Header: encoded reals
                    const realLabels = cappedCoords.map(c => coordToReal(c).toFixed(4));
                    lines.push('  ' + ''.padStart(10) + realLabels.map(r => r.padStart(8)).join(' '));
                    for (let i = 0; i < n; i++) {
                        const row = gramResult.matrix[i].map(v => v.toFixed(4).padStart(8)).join(' ');
                        lines.push(`  ${realLabels[i].padStart(10)} ${row}`);
                    }
                    lines.push('');

                    // Near-identical pairs
                    const similar: string[] = [];
                    for (let i = 0; i < n; i++) {
                        for (let j = i + 1; j < n; j++) {
                            if (gramResult.matrix[i][j] > 0.9) {
                                similar.push(`    ${R(cappedCoords[i])} ≈ ${R(cappedCoords[j])}  (K=${gramResult.matrix[i][j].toFixed(6)}, d=${Math.sqrt(Math.max(0, gramResult.matrix[i][i] - 2 * gramResult.matrix[i][j] + gramResult.matrix[j][j])).toFixed(6)})`);
                            }
                        }
                    }
                    if (similar.length > 0) {
                        lines.push(`  Near-identical pairs (K > 0.9):`);
                        lines.push(...similar);
                        lines.push('');
                    }

                    // ══════════════════════════════════════════════════════
                    // §5. EIGENDECOMPOSITION
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §5. EIGENDECOMPOSITION ────────────────────────────`);
                    lines.push('');
                    lines.push(`  G = UΛUᵀ where Λ = diag(λ₁, λ₂, ..., λₙ)`);
                    lines.push('');

                    const eigs = computeEigenvalues(gramResult.matrix);
                    const threshold = 0.01;
                    const effectiveDim = eigs.filter(e => Math.abs(e) > threshold).length;

                    lines.push(`  Eigenvalues (sorted descending):`);
                    for (let i = 0; i < eigs.length; i++) {
                        const marker = Math.abs(eigs[i]) > threshold ? '●' : '○';
                        lines.push(`    λ${i + 1} = ${eigs[i].toFixed(8)}  ${marker}`);
                    }
                    lines.push('');
                    lines.push(`  Effective dimension: ${effectiveDim} (eigenvalues with |λ| > ${threshold})`);
                    lines.push(`  Trace(G) = Σλᵢ = ${eigs.reduce((s, e) => s + e, 0).toFixed(8)}`);

                    // Spectral gap
                    if (eigs.length >= 2) {
                        const gap = eigs[0] - eigs[1];
                        lines.push(`  Spectral gap: λ₁ - λ₂ = ${eigs[0].toFixed(8)} - ${eigs[1].toFixed(8)} = ${gap.toFixed(8)}`);
                        lines.push(`  Spectral gap ratio: (λ₁ - λ₂)/λ₁ = ${(gap / Math.max(eigs[0], 1e-12)).toFixed(8)}`);
                    }
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §6. RKHS METRIC (DISTANCES)
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §6. RKHS METRIC ───────────────────────────────────`);
                    lines.push('');
                    lines.push(`  d(x, y) = √(K(x,x) + K(y,y) - 2K(x,y))`);
                    lines.push(`          = √(1 + 1 - 2K(x,y))               [since K(x,x) = 1 for non-superposed]`);
                    lines.push(`          = √(2(1 - K(x,y)))`);
                    lines.push('');
                    lines.push(`  Pairwise distances (sorted by distance):`);

                    const distances: { from: string; to: string; d: number; k: number }[] = [];
                    for (let i = 0; i < n; i++) {
                        for (let j = i + 1; j < n; j++) {
                            const kval = gramResult.matrix[i][j];
                            const d = Math.sqrt(Math.max(0, gramResult.matrix[i][i] - 2 * kval + gramResult.matrix[j][j]));
                            distances.push({ from: cappedCoords[i], to: cappedCoords[j], d, k: kval });
                        }
                    }
                    distances.sort((a, b) => a.d - b.d);

                    for (const dist of distances) {
                        lines.push(`    d(${R(dist.from)}, ${R(dist.to)}) = √(2(1 - ${dist.k.toFixed(6)})) = ${dist.d.toFixed(8)}`);
                    }
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §6b. QUANTUM KERNEL AMPLITUDES
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §6b. QUANTUM KERNEL AMPLITUDES ────────────────────`);
                    lines.push('');
                    lines.push(`  Each node carries a kernel amplitude |ψ|² and a Born weight:`);
                    lines.push('');
                    lines.push(`  |ψ|² (amplitude):`);
                    lines.push(`    locked/frozen with amplitude set → amplitude`);
                    lines.push(`    locked/frozen without amplitude → 1.0 (human-settled)`);
                    lines.push(`    unlocked with explicit amplitude → amplitude`);
                    lines.push(`    unlocked without amplitude → 0.0 (superposition)`);
                    lines.push('');
                    lines.push(`  Born weight w(x):`);
                    lines.push(`    w(x) = |ψ_x|² / Σ|ψ_i|²  (normalized probability for sampling)`);
                    lines.push('');
                    lines.push(`  Quantum kernel:`);
                    lines.push(`    K_q(x, y) = √(|ψ_x|² · |ψ_y|²) · K(x, y)`);
                    lines.push(`    Amplitude-weighted: superposition nodes (|ψ|²=0) contribute zero.`);
                    lines.push(`    Locked nodes (|ψ|²=1) pass K through unchanged.`);
                    lines.push('');

                    // Per-node amplitude table
                    lines.push(`  Per-node amplitudes:`);
                    lines.push(`  ${'Coord'.padEnd(12)} ${'Label'.padEnd(30)} ${'|ψ|²'.padEnd(8)} ${'Born w'.padEnd(10)} State`);
                    const amplitudes: { coord: string; amp: number; born: number; label: string; state: string }[] = [];
                    let ampSum = 0;
                    for (const c of cappedCoords) {
                        const node = space.nodes.get(c);
                        const amp = node ? getAmplitude(node) : 0;
                        ampSum += amp;
                        const state = node?.frozen ? 'frozen' : node?.locked ? 'locked' : amp > 0 ? 'explicit' : 'superposition';
                        const label = node?.label ?? c;
                        amplitudes.push({ coord: c, amp, born: 0, label, state });
                    }
                    // Compute Born weights
                    for (const a of amplitudes) {
                        a.born = ampSum > 0 ? a.amp / ampSum : 1 / amplitudes.length;
                    }
                    for (const a of amplitudes) {
                        lines.push(`  ${a.coord.padEnd(12)} ${a.label.padEnd(30)} ${a.amp.toFixed(4).padEnd(8)} ${a.born.toFixed(6).padEnd(10)} ${a.state}`);
                    }
                    lines.push('');

                    // Quantum Gram Matrix G_q
                    lines.push(`  Quantum Gram Matrix G_q[i,j] = √(|ψ_i|²·|ψ_j|²) · G[i,j]:`);
                    lines.push('');
                    const quantumGram: number[][] = [];
                    for (let i = 0; i < n; i++) {
                        quantumGram[i] = [];
                        for (let j = 0; j < n; j++) {
                            const ampWeight = Math.sqrt(amplitudes[i].amp * amplitudes[j].amp);
                            quantumGram[i][j] = ampWeight * gramResult.matrix[i][j];
                        }
                    }

                    // Check if quantum matrix is trivially identical to classical (all amps = 1)
                    const allAmpsOne = amplitudes.every(a => a.amp === 1.0);
                    if (allAmpsOne) {
                        lines.push(`  All nodes have |ψ|² = 1.0 (all locked/settled).`);
                        lines.push(`  G_q = G (quantum matrix equals classical Gram matrix).`);
                    } else {
                        const allAmpsZero = amplitudes.every(a => a.amp === 0.0);
                        if (allAmpsZero) {
                            lines.push(`  All nodes have |ψ|² = 0.0 (all in superposition).`);
                            lines.push(`  G_q = 0 (quantum matrix is zero — no collapsed state).`);
                        } else {
                            // Show the quantum gram matrix
                            const qRealLabels = cappedCoords.map(c => coordToReal(c).toFixed(4));
                            lines.push(`              ${qRealLabels.map(r => r.padStart(9)).join(' ')}`);
                            for (let i = 0; i < n; i++) {
                                const row = quantumGram[i].map(v => v.toFixed(4).padStart(9)).join(' ');
                                lines.push(`      ${qRealLabels[i].padStart(9)}   ${row}`);
                            }
                            lines.push('');

                            // Quantum eigendecomposition
                            try {
                                const qEigs = computeEigenvalues(quantumGram);
                                const qEffDim = qEigs.filter(e => Math.abs(e) > 0.01).length;
                                lines.push(`  Quantum eigenvalues (sorted descending):`);
                                for (let i = 0; i < qEigs.length; i++) {
                                    const marker = Math.abs(qEigs[i]) > 0.01 ? '●' : '○';
                                    lines.push(`    λ_q${i + 1} = ${qEigs[i].toFixed(8)}  ${marker}`);
                                }
                                lines.push(`  Quantum effective dimension: ${qEffDim}`);
                            } catch {
                                lines.push(`  (Quantum eigendecomposition skipped — matrix too sparse)`);
                            }
                        }
                    }
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §7. ORBIT DECOMPOSITION
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §7. ORBIT DECOMPOSITION ───────────────────────────`);
                    lines.push('');
                    lines.push(`  Orbits are computed per-slot via subtree fingerprinting`);
                    lines.push(`  (Aho-Hopcroft-Ullman canonical form).`);
                    lines.push('');
                    lines.push(`  Two nodes x, y are in the same orbit iff:`);
                    lines.push(`    subtreeFingerprint(x) = subtreeFingerprint(y)`);
                    lines.push(`  meaning they have IDENTICAL sub-tree structure`);
                    lines.push(`  (same branching, same depth, same shape recursively).`);
                    lines.push('');

                    const sig = computeSpaceSlotSignature(registry, spaceName);

                    // Group action definition
                    lines.push(`  Group action: G = ${sig.totalSymmetry}`);
                    lines.push(`  G acts on the set of mineSpace coordinates by permuting`);
                    lines.push(`  structurally equivalent spectrum values within each slot.`);
                    lines.push('');
                    lines.push(`  Total configurations: |X| = ${sig.totalConfigurations} (product of spectrum sizes)`);
                    lines.push('');

                    let totalOrbits = 0;
                    let totalGroupOrder = 1;

                    for (const slot of sig.slots) {
                        lines.push(`  ┌── Slot ${slot.slotIndex} — Parent: "${slot.parentLabel}" ──`);
                        lines.push(`  │   Spectrum size: ${slot.spectrumSize}`);
                        lines.push(`  │   Symmetry group: ${slot.symmetryGroup}`);
                        lines.push(`  │   Superposition (0) meaning: ${slot.superpositionMeaning}`);
                        lines.push(`  │`);

                        // Compute slot group order
                        let slotGroupOrder = 1;
                        for (const orbit of slot.orbits) {
                            // Factorial of orbit size
                            let factorial = 1;
                            for (let i = 2; i <= orbit.size; i++) factorial *= i;
                            slotGroupOrder *= factorial;
                        }
                        totalGroupOrder *= slotGroupOrder;

                        for (const orbit of slot.orbits) {
                            totalOrbits++;
                            const memberReals = orbit.members.map(m => {
                                const encoded = encodeSelectionIndex(m);
                                return { index: m, real: coordToReal(encoded) };
                            });

                            lines.push(`  │   Orbit {${orbit.labels.join(', ')}}:`);
                            lines.push(`  │     Size: ${orbit.size}`);
                            lines.push(`  │     Members (selection → real):`);
                            for (const mr of memberReals) {
                                const label = orbit.labels[orbit.members.indexOf(mr.index)] || '?';
                                lines.push(`  │       ${mr.index} → ${mr.real}  "${label}"`);
                            }

                            // Orbit-stabilizer
                            let orbitFact = 1;
                            for (let i = 2; i <= orbit.size; i++) orbitFact *= i;
                            const stabSize = slotGroupOrder / orbit.size;
                            lines.push(`  │     Orbit-Stabilizer: |G| = |Orb(x)| · |Stab(x)| → ${slotGroupOrder} = ${orbit.size} · ${stabSize}`);
                            lines.push(`  │`);
                        }
                        lines.push(`  └────────────────────────────────`);
                        lines.push('');
                    }

                    // Burnside
                    lines.push(`  Burnside's Lemma:`);
                    lines.push(`    |X/G| = (1/|G|) · Σ_{g∈G} |Fix(g)|`);
                    lines.push(`    |G| = ${totalGroupOrder}`);
                    lines.push(`    Total orbits: ${totalOrbits}`);
                    lines.push(`    Distinct configurations (up to symmetry): ${totalOrbits}`);
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §8. CANONICAL SIGNATURE
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §8. CANONICAL SIGNATURE ───────────────────────────`);
                    lines.push('');
                    lines.push(`  ${sig.canonical}`);
                    lines.push('');
                    lines.push(`  Reading: [orbit_sizes]⊗[orbit_sizes]⊗...|symmetry_groups`);
                    lines.push(`  Each ⊗ = tensor product of per-slot Hilbert spaces`);
                    lines.push(`  The signature IS the structural fingerprint of this space.`);
                    lines.push('');

                    // ══════════════════════════════════════════════════════
                    // §9. HYBRID KERNEL (K_named + α·K_walk)
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §9. HYBRID KERNEL (DESIGN_part2 §6b) ─────────────`);
                    lines.push('');
                    lines.push(`  K(x,y) = K_named(x,y) + α · K_walk(x,y)`);
                    lines.push('');
                    lines.push(`  K_named: dot product of attribute feature vectors from scry()`);
                    lines.push(`  K_walk:  random walk kernel Σ λⁿ · Aⁿ[x,y] on DAG adjacency`);
                    lines.push(`  α = 0.5 (relative weight of structure vs named features)`);
                    lines.push('');
                    lines.push(`  The hybrid captures BOTH what we can name AND what we can't.`);
                    lines.push(`  LLM names what it sees in K_walk output → those names become`);
                    lines.push(`  K_named features in the next iteration (the spiral).`);
                    lines.push('');

                    try {
                        const hybridAlpha = 0.5;
                        const showHybridPairs = Math.min(5, Math.floor(n * (n - 1) / 2));
                        let hybridPairCount = 0;

                        for (let i = 0; i < n && hybridPairCount < showHybridPairs; i++) {
                            for (let j = i + 1; j < n && hybridPairCount < showHybridPairs; j++) {
                                const hk = hybridKernel(registry, spaceName, cappedCoords[i], cappedCoords[j], hybridAlpha);
                                lines.push(`  K_hybrid(${R(cappedCoords[i])}, ${R(cappedCoords[j])}):`);  // real-number coords
                                lines.push(`    K_named  = ${hk.named.toFixed(8)}`);
                                lines.push(`    K_walk   = ${hk.walk.toFixed(8)}`);
                                lines.push(`    K_hybrid = K_named + ${hybridAlpha} · K_walk = ${hk.named.toFixed(4)} + ${(hybridAlpha * hk.walk).toFixed(4)} = ${hk.value.toFixed(8)}`);
                                lines.push(`    cosine   = ${hk.similarity.toFixed(8)}`);
                                lines.push('');
                                hybridPairCount++;
                            }
                        }
                    } catch (e: any) {
                        lines.push(`  (Hybrid kernel computation failed: ${e.message})`);
                        lines.push('');
                    }

                    // ══════════════════════════════════════════════════════
                    // §10. FOUNDATION SIGNATURE (orbit partition + quotient graph + local aut)
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §10. FOUNDATION SIGNATURE ─────────────────────────`);
                    lines.push('');
                    lines.push(`  The canonical triple: (orbit partition, quotient graph, local aut groups)`);
                    lines.push(`  Computed via the HYBRID kernel (K_named + α·K_walk),`);
                    lines.push(`  which captures both named and unnamed structural similarity.`);
                    lines.push('');

                    try {
                        const hybridAnalysis = analyzeSpaceHybrid(registry, spaceName, cappedCoords);
                        const foundSig = computeFoundationSignature(hybridAnalysis);

                        lines.push(`  Orbit partition: [${foundSig.orbitPartition.join(', ')}]`);
                        lines.push(`  Symmetry group: ${hybridAnalysis.symmetryGroup}`);
                        lines.push('');

                        lines.push(`  Local automorphism groups:`);
                        for (const lg of foundSig.localGroups) {
                            lines.push(`    Orbit ${lg.orbitIndex}: |orbit| = ${lg.orbitSize}, Aut = ${lg.groupName} (order ${lg.groupOrder})`);
                            lines.push(`      Representative: ${lg.representative}`);
                            if (lg.fixedCenter) {
                                lines.push(`      Fixed center: ${lg.fixedCenter}`);
                                lines.push(`      Permutable: [${lg.permutableMembers.join(', ')}]`);
                            }
                        }
                        lines.push('');

                        if (foundSig.quotientGraph.length > 0) {
                            lines.push(`  Quotient graph (edges between orbits):`);
                            for (const edge of foundSig.quotientGraph) {
                                lines.push(`    Orbit ${edge.fromOrbit} ↔ Orbit ${edge.toOrbit}: avg K = ${edge.weight.toFixed(6)}`);
                            }
                        } else {
                            lines.push(`  Quotient graph: disconnected (no inter-orbit edges)`);
                        }
                        lines.push('');

                        lines.push(`  Canonical: ${foundSig.canonical}`);
                        lines.push('');

                        // Compare with tensor signature
                        lines.push(`  Compare with tensor (slot-based) signature:`);
                        lines.push(`    Tensor:     ${sig.canonical}`);
                        lines.push(`    Foundation: ${foundSig.canonical}`);
                        lines.push(`  (Tensor uses per-slot subtree fingerprinting;`);
                        lines.push(`   Foundation uses hybrid kernel Gram-matrix row patterns)`);
                        lines.push('');
                    } catch (e: any) {
                        lines.push(`  (Foundation signature computation failed: ${e.message})`);
                        lines.push('');
                    }

                    // ══════════════════════════════════════════════════════
                    // §11. ALGEBRA (structure constants, Frobenius, Aut, Monster)
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §11. CB ALGEBRA ───────────────────────────────────`);
                    lines.push('');
                    lines.push(`  V = span{eᵢ} where eᵢ are basis vectors for nodes`);
                    lines.push(`  * : V × V → V  (bilinear, commutative, NON-associative product)`);
                    lines.push(`  ⟨·,·⟩ = K(eᵢ, eⱼ)  (the bilinear form from the kernel)`);
                    lines.push('');

                    try {
                        // Guard: algebra is expensive for large spaces
                        if (nodeCount > 30) {
                            lines.push(`  ⚠ Space has ${nodeCount} nodes — algebra analysis capped.`);
                            lines.push(`  Structure constants: O(n³) = O(${nodeCount ** 3}) — computing...`);
                            lines.push('');
                        }

                        const algebra = analyzeAlgebra(registry, spaceName);

                        lines.push(`  Dimension: ${algebra.dimension}`);
                        lines.push(`  Structure constants (non-zero cᵏᵢⱼ): ${algebra.structureConstants.length}`);
                        lines.push('');

                        // Show a sample of structure constants
                        const sampleConstants = algebra.structureConstants.slice(0, 15);
                        if (sampleConstants.length > 0) {
                            lines.push(`  Representative structure constants:`);
                            for (const sc of sampleConstants) {
                                const nodeI = space.nodes.get(sc.i);
                                const nodeJ = space.nodes.get(sc.j);
                                const nodeK = space.nodes.get(sc.k);
                                const labelI = nodeI?.label ?? sc.i;
                                const labelJ = nodeJ?.label ?? sc.j;
                                const labelK = nodeK?.label ?? sc.k;
                                lines.push(`    c(${labelI}, ${labelJ}) → ${labelK}: ${sc.value.toFixed(6)}  [${sc.reason}]`);
                            }
                            if (algebra.structureConstants.length > 15) {
                                lines.push(`    ... (${algebra.structureConstants.length - 15} more)`);
                            }
                            lines.push('');
                        }

                        // Frobenius form invariance
                        lines.push(`  Frobenius form invariance ⟨x*y, z⟩ = ⟨x, y*z⟩:`);
                        lines.push(`    ${algebra.formInvariant ? '✓ SATISFIED' : '✗ VIOLATED'}`);
                        if (algebra.formViolations.length > 0) {
                            for (const v of algebra.formViolations.slice(0, 5)) {
                                lines.push(`      ${v}`);
                            }
                        }
                        lines.push('');

                        // Non-associativity
                        lines.push(`  Non-associativity (x*(y*z) ≠ (x*y)*z):`);
                        lines.push(`    ${algebra.nonAssociative ? '✓ CONFIRMED non-associative (Griess algebra property)' : '✗ Associative (not Griess-like)'}`);
                        if (algebra.associativityCounterexample) {
                            lines.push(`    Counterexample: ${algebra.associativityCounterexample}`);
                        }
                        lines.push('');

                        // Automorphism group
                        lines.push(`  Automorphism group Aut(V, *):`);
                        lines.push(`    ${algebra.autGroup.structureDescription}`);
                        if (algebra.autGroup.groupOrder > 0) {
                            lines.push(`    Element orders: {${algebra.autGroup.elementOrders.join(', ')}}`);
                            lines.push(`    All preserve form: ${algebra.autGroup.allPreserveForm ? '✓ yes' : `✗ no (${algebra.autGroup.formViolators.length} violators)`}`);
                        }
                        lines.push('');

                        // Monster compatibility
                        const mc = algebra.monsterCompatibility;
                        lines.push(`  Monster compatibility:`);
                        lines.push(`    T1 (order divisibility): ${mc.t1_orderDivisibility.pass ? '✓' : '✗'} — |Aut| = ${mc.t1_orderDivisibility.groupOrder}, primes: {${mc.t1_orderDivisibility.primeFactors.join(',')}}`);
                        if (mc.t1_orderDivisibility.badPrimes.length > 0) {
                            lines.push(`       Bad primes (not in Monster): {${mc.t1_orderDivisibility.badPrimes.join(',')}}`);
                        }
                        lines.push(`    T2 (element orders): ${mc.t2_elementOrders.pass ? '✓' : '✗'} — orders: {${mc.t2_elementOrders.elementOrders.join(',')}}`);
                        if (mc.t2_elementOrders.badOrders.length > 0) {
                            lines.push(`       Bad orders (not in Monster): {${mc.t2_elementOrders.badOrders.join(',')}}`);
                        }
                        lines.push(`    T3 (form preservation): ${mc.t3_formPreservation.pass ? '✓' : '✗'} — ${mc.t3_formPreservation.note}`);
                        lines.push(`    Form PD: ${mc.formPositiveDefinite ? '✓' : '✗'}`);
                        lines.push(`    Overall: ${mc.compatible ? '✓ COMPATIBLE' : '✗ NOT COMPATIBLE'}`);
                        lines.push(`    ${mc.summary}`);
                        lines.push('');

                        // Adjoint analysis (Majorana)
                        if (algebra.adjointAnalysis.length > 0) {
                            lines.push(`  Adjoint eigenvalue analysis (Lₐ(x) = a*x):`);
                            const showAdj = algebra.adjointAnalysis.slice(0, 5);
                            for (const adj of showAdj) {
                                const node = space.nodes.get(adj.basisElement);
                                const label = node?.label ?? adj.basisElement;
                                const eigenStr = adj.eigenvalues.map(e => e.toFixed(4)).join(', ');
                                lines.push(`    L(${label}): eigenvalues = [${eigenStr}]${adj.isAxisLike ? ' ← AXIS-LIKE' : ''}`);
                            }
                            if (algebra.adjointAnalysis.length > 5) {
                                lines.push(`    ... (${algebra.adjointAnalysis.length - 5} more basis elements)`);
                            }
                            lines.push('');
                        }
                    } catch (e: any) {
                        lines.push(`  (Algebra computation failed: ${e.message})`);
                        lines.push('');
                    }

                    // ══════════════════════════════════════════════════════
                    // §12. HOMOICONICITY: eval∘quote = id
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §12. HOMOICONICITY VERIFICATION ──────────────────`);
                    lines.push('');
                    lines.push(`  The reproducing property of the RKHS IS homoiconicity:`);
                    lines.push(`    f(x) = ⟨f, K(·,x)⟩_K   for all f ∈ H_K`);
                    lines.push(`  In CB terms: eval(quote(node)) = node (code = data = space = point)`);
                    lines.push('');
                    lines.push(`  Verification: cbEval(space, coord) → node → cbQuote(space, node.id) =? coord`);
                    lines.push('');

                    try {
                        let invertibleCount = 0;
                        let failedCount = 0;
                        const failures: string[] = [];

                        for (const c of cappedCoords) {
                            const result = verifyInvertibility(space, c);
                            if (result.invertible) {
                                invertibleCount++;
                            } else {
                                failedCount++;
                                const quoteCoord = result.quoteResult?.coordinate ?? '(null)';
                                failures.push(`    ✗ eval∘quote(${R(c)}) = ${R(quoteCoord)} ≠ ${R(c)}`);
                            }
                        }

                        lines.push(`  Results: ${invertibleCount}/${cappedCoords.length} invertible`);
                        if (failedCount === 0) {
                            lines.push(`  ✓ ALL coordinates satisfy eval∘quote = id`);
                            lines.push(`  Homoiconicity VERIFIED on this coordinate set.`);
                        } else {
                            lines.push(`  ✗ ${failedCount} failures:`);
                            for (const f of failures.slice(0, 10)) {
                                lines.push(f);
                            }
                        }
                        lines.push('');
                    } catch (e: any) {
                        lines.push(`  (Homoiconicity verification failed: ${e.message})`);
                        lines.push('');
                    }

                    // ══════════════════════════════════════════════════════
                    // §13. GMR GEOMETRY (manifold structure)
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §13. GMR GEOMETRY ─────────────────────────────────`);
                    lines.push('');
                    lines.push(`  Geometric Manifold Rectification: THE MATH IS MEANINGFUL A PRIORI.`);
                    lines.push(`  Computes manifold structure from locked coordinate space.`);
                    lines.push('');

                    try {
                        const neighborhoods = computeAlgebraNeighborhoods(space);
                        const gmrResult = rectifySpace(registry, spaceName, neighborhoods, GMR_DEFAULTS);

                        lines.push(`  Nodes analyzed: ${gmrResult.nodesAnalyzed}`);
                        lines.push(`  Nodes kept: ${gmrResult.nodesKept}`);
                        lines.push(`  Nodes attenuated: ${gmrResult.nodesAttenuated}`);
                        lines.push(`  Nodes excluded: ${gmrResult.nodesExcluded}`);
                        lines.push('');

                        if (gmrResult.denseRegions.length > 0) {
                            lines.push(`  Dense regions (high kernel support):`);
                            for (const d of gmrResult.denseRegions) {
                                const node = space.nodes.get(d);
                                lines.push(`    ${d} "${node?.label ?? ''}"`);
                            }
                            lines.push('');
                        }

                        if (gmrResult.frontierRegions.length > 0) {
                            lines.push(`  Frontier regions (boundary of manifold):`);
                            for (const f of gmrResult.frontierRegions) {
                                const node = space.nodes.get(f);
                                lines.push(`    ${f} "${node?.label ?? ''}"`);
                            }
                            lines.push('');
                        }

                        if (gmrResult.isolatedNodes.length > 0) {
                            lines.push(`  Isolated nodes (low kernel support — potential outliers):`);
                            for (const iso of gmrResult.isolatedNodes) {
                                const node = space.nodes.get(iso);
                                lines.push(`    ${iso} "${node?.label ?? ''}"`);
                            }
                            lines.push('');
                        }

                        // Per-node geometry summary
                        lines.push(`  Per-node geometry:`);
                        lines.push(`  ${'Node'.padEnd(8)} ${'Label'.padEnd(30)} ${'Density'.padEnd(8)} ${'Region'.padEnd(10)} NearK    FarK`);
                        const showGeom = gmrResult.geometry.slice(0, 20);
                        for (const g of showGeom) {
                            lines.push(`  ${g.nodeId.padEnd(8)} ${g.label.padEnd(30)} ${g.density.toFixed(4).padEnd(8)} ${g.region.padEnd(10)} ${g.nearestSimilarity.toFixed(4).padEnd(8)} ${g.farthestSimilarity.toFixed(4)}`);
                        }
                        if (gmrResult.geometry.length > 20) {
                            lines.push(`  ... (${gmrResult.geometry.length - 20} more nodes)`);
                        }
                        lines.push('');
                    } catch (e: any) {
                        lines.push(`  (GMR computation failed: ${e.message})`);
                        lines.push('');
                    }

                    // ══════════════════════════════════════════════════════
                    // §14. COORDINATE TABLE
                    // ══════════════════════════════════════════════════════
                    lines.push(`─── §14. COORDINATE TABLE ─────────────────────────────`);
                    lines.push('');
                    lines.push(`  ${'Coordinate (ℝ)'.padEnd(16)} ${'Path'.padEnd(8)} ${'Encoded'.padEnd(16)} ${'|ψ|²'.padEnd(6)} ${'Born'.padEnd(8)} Label`);
                    for (let ci = 0; ci < cappedCoords.length; ci++) {
                        const c = cappedCoords[ci];
                        const encoded = encodeDot(c);
                        const real = coordToReal(c);
                        const amp = amplitudes[ci];
                        lines.push(`  ${String(real).padEnd(16)} ${c.padEnd(8)} ${encoded.padEnd(16)} ${amp.amp.toFixed(2).padEnd(6)} ${amp.born.toFixed(4).padEnd(8)} ${amp.label}`);
                    }
                    lines.push('');

                    lines.push(`═══════════════════════════════════════════════════════`);
                    lines.push(`  END MATHEMATICAL OUTPUT`);
                    lines.push(`═══════════════════════════════════════════════════════`);

                    return {
                        view: lines.join('\n'),
                        data: {
                            spaceName,
                            nodeCount,
                            coordCount: n,
                            totalCoords: allCoords.length,
                            alpha,
                            gramMatrix: gramResult.matrix,
                            quantumGramMatrix: quantumGram,
                            amplitudes: amplitudes.map(a => ({ coord: a.coord, amplitude: a.amp, bornWeight: a.born, state: a.state })),
                            eigenvalues: eigs,
                            effectiveDimension: effectiveDim,
                            signature: sig,
                            distances,
                        },
                        cursor: { space: spaceName, coordinate: coord },
                    };
                } catch (e: any) {
                    return {
                        view: `all_math computation failed: ${e.message}\n${e.stack}`,
                        cursor: { space: spaceName, coordinate: coord },
                    };
                }
            }

            // ─── MATH (context-dependent menu) ───
            // Format: {Space} math
            if (action === 'math') {
                const space = registry.spaces.get(spaceName);
                const nodeCount = space ? space.nodes.size - 1 : 0; // exclude root
                const rootChildren = space ? (space.nodes.get(space.rootId)?.children.length ?? 0) : 0;

                // Get mine data if available
                const ms = mineSpaceCache.get(spaceName);
                const validCount = ms ? ms.known.filter(p => p.status === 'valid').length : 0;
                const adjacentCount = ms ? ms.known.filter(p => p.status === 'adjacent').length : 0;

                const lines: string[] = [
                    `🔬 Math available for ${spaceName} (${nodeCount} nodes, ${rootChildren} top-level):`,
                    '',
                    `  ${spaceName} all_math         → ★ COMPLETE mathematical output (all definitions + computations)`,
                    '',
                    `  ${spaceName} orbits          → Orbit decomposition & symmetry groups`,
                    `  ${spaceName} signature        → Canonical signature string`,
                    `  ${spaceName} kernel {x} {y}   → RKHS tensor kernel K(x,y)`,
                    `  ${spaceName} gram             → Gram matrix of all coordinates`,
                    `  ${spaceName} tower [N]        → Build N-level Futamura tower`,
                    `  ${spaceName} reify            → One T-operator step`,
                ];

                if (ms) {
                    lines.push('', `  MineSpace: ${validCount} valid, ${adjacentCount} adjacent`);
                }

                return {
                    view: lines.join('\n'),
                    cursor: { space: spaceName, coordinate: coord },
                };
            }
        }

        // No compound action — treat as navigation: "Space" or "Space coord"
        const coord = remainingParts.length > 0 ? remainingParts.join(' ') : null;

        try {
            if (coord) {
                return scryCoordinate(teamId, session, spaceName, coord);
            } else {
                return enterSpace(teamId, session, spaceName);
            }
        } catch (err: any) {
            if (err.message.includes('not found')) {
                // Space doesn't exist — offer to create it
                session.pendingInteraction = {
                    type: 'name',
                    prompt: `Space "${spaceName}" doesn't exist. Create it? (yes/no)`,
                    options: ['yes', 'no'],
                    target: spaceName,
                };
                return {
                    view: `Space "${spaceName}" not found.`,
                    interaction: session.pendingInteraction,
                    cursor: { space: null, coordinate: 'root' },
                };
            }
            throw err;
        }
    }

    // Bare coordinate with no current space
    return {
        view: 'No space selected. Type a space name first, or "list" to see spaces.',
        cursor: { space: null, coordinate: 'root' },
    };
}


// ─── Enter a Space ───────────────────────────────────────────────

async function enterSpace(
    teamId: number,
    session: SessionState,
    spaceName: string,
): Promise<CBResponse> {
    const { cb: crystal } = await loadCb(teamId, spaceName);
    const root = crystal.nodes.get(crystal.rootId)!;

    session.currentSpace = spaceName;
    session.currentCoordinate = 'root';

    // Fill interaction is ALWAYS available — adding children is a constant option
    const rsc = root.slotCount ?? 0;
    const hasSlots = rsc > 0;
    const remaining = hasSlots ? rsc - root.children.length : undefined;
    const prompt = root.children.length === 0
        ? `${root.label} is empty. Add first child:`
        : hasSlots && remaining! > 0
            ? `${root.label} has ${remaining} slot(s) to fill. Name the next:`
            : `${root.label} has ${root.children.length} children. Add another:`;

    session.pendingInteraction = {
        type: 'fill',
        prompt,
        target: root.id,
    };
    session.pendingNodeId = root.id;

    return {
        view: spaceToView(crystal),
        interaction: session.pendingInteraction,
        data: nodeToData(root),
        cursor: { space: spaceName, coordinate: 'root' },
    };
}

// ─── Scry a Coordinate ──────────────────────────────────────────

async function scryCoordinate(
    teamId: number,
    session: SessionState,
    spaceName: string,
    coordinate: string,
): Promise<CBResponse> {
    const { cb: crystal, rowId } = await loadCb(teamId, spaceName);

    session.currentSpace = spaceName;
    session.currentCoordinate = coordinate;

    // Handle 'root' as a coordinate — kernel only understands numeric coords
    if (coordinate === 'root') {
        const root = crystal.nodes.get(crystal.rootId);
        if (root) {
            // Delegate to enterSpace logic (which handles fill prompts)
            return enterSpace(teamId, session, spaceName);
        }
        return { view: 'Empty space.', cursor: { space: spaceName, coordinate: 'root' } };
    }
    // Try direct node ID lookup first (e.g. "root.0", "1", "2")
    const directNode = crystal.nodes.get(coordinate);
    if (directNode) {
        session.currentCoordinate = coordinate;
        return enterSpaceAt(teamId, session, spaceName, coordinate, crystal, rowId);
    }

    const scryResult = cbScry(registry, spaceName, coordinate);

    // Show resolved nodes
    if (scryResult.resolved.length === 0) {
        return {
            view: `Nothing at coordinate ${coordinate}.`,
            cursor: { space: spaceName, coordinate },
        };
    }

    // Has generation slots (0s)?
    if (scryResult.slots.length > 0) {
        const lines: string[] = [`=== ${spaceName} ${coordinate} === [${scryResult.slots.length} slots]`, ''];
        for (const slot of scryResult.slots) {
            lines.push(`  [slot ${slot.segmentIndex}] ${slot.spaceName}::${slot.parentLabel} (${slot.existingOptions.length} options)`);
        }
        return {
            view: lines.join('\n'),
            data: {
                type: 'assembly',
                space: spaceName,
                coordinate,
                resolved: scryResult.resolved,
                slots: scryResult.slots,
                unresolvedZeros: scryResult.unresolvedZeros,
            },
            cursor: { space: spaceName, coordinate },
        };
    }

    // Superposition: multiple nodes resolved — show all
    if (scryResult.resolved.length > 1) {
        const nodeLines = scryResult.resolved.map((r: any, i: number) => `  ${i + 1}. ${r.label} (${r.coordinate})`);
        return {
            view: `\u27E80\u27E9 Superposition \u2014 ${scryResult.resolved.length} nodes:\n${nodeLines.join('\n')}`,
            data: scryResult.resolved,
            cursor: { space: spaceName, coordinate },
        };
    }

    // Single resolved node
    const resolved = scryResult.resolved[0];
    const node = crystal.nodes.get(resolved.nodeId);
    if (!node) {
        return {
            view: `Resolved ${resolved.label} but node not found in space.`,
            cursor: { space: spaceName, coordinate },
        };
    }


    // If node is a class (has unfilled slots), show what needs filling
    const nsc2 = node.slotCount ?? 0;
    if (nsc2 > 0 && node.children.length < nsc2) {
        const nodeRemaining = nsc2 - node.children.length;
        const childLines = node.children.map((cid: string) => {
            const child = crystal.nodes.get(cid);
            return child ? `  ${nodeToView(child)}` : `  ${cid}: ???`;
        });
        for (let i = 0; i < nodeRemaining; i++) {
            childLines.push(`  [empty slot ${node.children.length + i + 1}]`);
        }

        session.pendingInteraction = {
            type: 'fill',
            prompt: `${nodeRemaining} slot(s) to fill. Name the next node:`,
            target: node.id,
        };
        session.pendingNodeId = node.id;

        return {
            view: `${nodeToView(node)}\n${childLines.join('\n')}`,
            interaction: session.pendingInteraction,
            data: nodeToData(node),
            cursor: { space: spaceName, coordinate },
        };
    }

    // Attributes removed — children ARE the spectrum.
    // Show children as the node's content instead.

    // Fully resolved leaf — show it with children, always offer fill
    const childViews = node.children.map((cid: string) => {
        const child = crystal.nodes.get(cid);
        return child ? nodeToView(child, 1) : `  ${cid}: ???`;
    });

    // Always keep fill available — with mathematical context
    const fillCtx = buildFillContext(registry, spaceName, node.id);
    session.pendingInteraction = {
        type: 'fill',
        prompt: node.children.length === 0
            ? `${node.label} is empty. ${fillCtx}Add children:`
            : `${node.label} has ${node.children.length} children. ${fillCtx}Add more:`,
        target: node.id,
    };
    session.pendingNodeId = node.id;

    return {
        view: nodeToView(node) + (childViews.length > 0 ? '\n' + childViews.join('\n') : ''),
        interaction: session.pendingInteraction,
        data: nodeToData(node),
        cursor: { space: spaceName, coordinate },
    };
}

// ─── Handle Interaction Response ─────────────────────────────────

async function handleInteractionResponse(
    teamId: number,
    session: SessionState,
    input: string,
): Promise<CBResponse> {
    const interaction = session.pendingInteraction!;

    // Clear pending state
    session.pendingInteraction = null;

    // Exit / cancel
    if (input === 'exit' || input === 'cancel' || input === 'no') {
        return cb(teamId, session.currentSpace || 'list');
    }

    // Handle "yes" for space creation confirmation
    if (interaction.type === 'name' && interaction.prompt.includes('Create it?')) {
        if (input === 'yes' || input === 'y') {
            return createNewSpace(teamId, session, interaction.target);
        }
        return cb(teamId, 'list');
    }

    // Handle fill — add child node(s). Comma-separated = multiple siblings.
    if (interaction.type === 'fill' && session.currentSpace) {
        // Guard: intercept known commands that should NOT create nodes
        const FILL_ESCAPE_COMMANDS = /^(done|lock|back|list|mine|bloom|freeze|eval|quote|exit|cancel|slots|help)(\s|$)/i;
        const IS_COORDINATE = /^\d+(\.\d+)*$/;
        if (FILL_ESCAPE_COMMANDS.test(input) || IS_COORDINATE.test(input)) {
            // Re-route to main handler instead of treating as node label
            session.pendingInteraction = null;
            return cb(teamId, input);
        }

        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const parentId = session.pendingNodeId || crystal.rootId;

        // Split on commas or newlines to support multi-fill (MCP sends newline-separated)
        const labels = input.split(/[,\n]/).map(s => s.trim()).filter(s => s.length > 0);
        const addedNodes: { id: string; label: string }[] = [];

        for (const label of labels) {
            const newNode = addNode(crystal, parentId, label);
            addedNodes.push({ id: newNode.id, label });
        }
        await saveCb(rowId, crystal);

        const parent = crystal.nodes.get(parentId);
        const psc = parent?.slotCount ?? 0;
        const addedSummary = addedNodes.map(n => `${n.id}: ${n.label}`).join(', ');

        // Check if parent is now fully filled
        if (parent && psc > 0 && parent.children.length >= psc) {
            return {
                view: `Added ${addedNodes.length} node(s): ${addedSummary}. ${parent.label} is now complete ✓\n\n${spaceToView(crystal)}`,
                data: { ...nodeToData(parent), addedLabels: addedNodes.map(n => n.label) },
                cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
            };
        }

        // Always keep fill interaction open
        const prompt = psc > 0
            ? `Added ${addedNodes.length}. ${psc - parent!.children.length} slot(s) remaining. Add more:`
            : `Added ${addedNodes.length} node(s). ${parent!.label} now has ${parent!.children.length} children. Add more:`;
        session.pendingInteraction = {
            type: 'fill',
            prompt,
            target: parentId,
        };
        session.pendingNodeId = parentId;

        return {
            view: `Added ${addedNodes.length} node(s): ${addedSummary}\n\n${spaceToView(crystal)}`,
            interaction: session.pendingInteraction,
            data: { ...nodeToData(parent!), addedLabels: addedNodes.map(n => n.label) },
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // Handle select — pick or add to a spectrum
    if (interaction.type === 'select' && session.currentSpace) {
        const { cb: crystal, rowId } = await loadCb(teamId, session.currentSpace);
        const nodeId = session.pendingNodeId!;
        const attrName = interaction.target;

        if (input.startsWith('add ')) {
            // Add new child node
            const newLabel = input.slice(4).trim();
            const node = crystal.nodes.get(nodeId);
            if (node) {
                addNode(crystal, nodeId, newLabel);
            }
            await saveCb(rowId, crystal);

            return {
                view: `Added "${newLabel}" as child of ${nodeId}.\n\n${spaceToView(crystal)}`,
                cursor: { space: session.currentSpace, coordinate: nodeId },
            };
        }

        // Numeric selection — with attributes gone, this is a no-op
        // (attribute-based selection is deprecated)
        return {
            view: `Attribute-based selection is no longer supported. Children ARE the spectrum.\nUse the coordinate system to navigate.`,
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };

        return {
            view: `Invalid selection. Type a number (1-${interaction.options?.length}) or "add <value>".`,
            interaction,
            cursor: { space: session.currentSpace, coordinate: session.currentCoordinate },
        };
    }

    // Fallback — re-enter normal flow
    return cb(teamId, input);
}

// ─── Create Space ────────────────────────────────────────────────

async function createNewSpace(
    teamId: number,
    session: SessionState,
    name: string,
): Promise<CBResponse> {
    const existing = await db
        .select({ id: spaces.id })
        .from(spaces)
        .where(and(eq(spaces.teamId, teamId), eq(spaces.name, name)));

    if (existing.length > 0) {
        return enterSpace(teamId, session, name);
    }

    const crystal = createCrystalBall(name);
    await db.insert(spaces).values({
        teamId,
        name,
        data: toDbData(crystal) as any,
    });

    // Get the row ID of the just-created space
    const [row] = await db
        .select({ id: spaces.id })
        .from(spaces)
        .where(and(eq(spaces.teamId, teamId), eq(spaces.name, name)));
    const rowId = row.id;

    session.currentSpace = name;
    session.currentCoordinate = 'root';
    session.phase = 'bloom';

    // Register with Griess constructor
    const griessResult = tryAdvanceFromCB(name, 'create');

    // Enter the space to set up pending interaction
    const response = await enterSpaceAt(teamId, session, name, 'root', crystal, rowId);

    const pi = phaseInfo(session);
    response.view = `Created space "${name}"\n\n${response.view}\n\n${pi.phasePrompt}` +
        `\n\n⚙️ Griess: Space registered at DERIVE.\n   Declare κ_user with: kappa <domain>: <invariant>=<description>, ...`;
    response.phase = session.phase;

    return response;
}
