/* ═══════════════════════════════════════════════════════════
   Mine — Configuration mineSpace Computation
   
   Given a space (kernel), enumerate all valid coordinate paths
   through its child tree. Each valid path is a POINT in mineSpace —
   a real number whose digit expansion is a CB coordinate string.
   
   This is the configuration mineSpace:
     "Given one locked kernel, what are ALL the valid coordinates?"
   
   The mine does NOT use the attributes Map (that's homoiconic's
   internal bookkeeping). Mine walks CHILDREN — the real structure
   that coordinates navigate.
   
   Output: MinedPoint[] for visualization as a heatmap.
   ═══════════════════════════════════════════════════════════ */

import {
    type Registry,
    type SpaceName,
    type Space,
    type CBNode,
    type SpaceView,
    computeSpaceHeat,
    isKernelComplete,
    encodeDot,
    decodeDot,
    coordToReal,
    getViewChildren,
    DOT_ENCODING,
    KERNEL_OPEN,
    KERNEL_CLOSE,
} from './index';

// ── Types ──

export interface MinedPoint {
    x: number;
    y: number;
    heat: number;       // 0 = cold (fully locked), 1 = hot (unlocked/has slots)
    label: string;
    radius?: number;
    coordinate: string; // The valid coordinate path (e.g., "1.2.3")
    depth: number;      // How deep in the tree this path goes
}

export interface MineResult {
    spaceName: string;
    points: MinedPoint[];
    totalPaths: number;         // Total valid coordinate paths found
    maxDepth: number;           // Deepest path in the tree
    spaceHeat: number;
    kernelComplete: boolean;
    // Sorry/proof awareness
    frozenCount: number;        // How many paths are frozen (sorry resolved)
    frozenRatio: number;        // frozenCount / totalPaths
    shaDetected: boolean;       // Ш = true when frozenRatio === 1.0 (perfect coherence)
    thermalFrontier: string[];  // Coordinates at the warm frontier (adjacent to frozen)
}

// ── Core: Enumerate valid coordinate paths ──

export function computeMinePlane(
    registry: Registry,
    spaceName: SpaceName,
    coordinate: string = '0',
    maxPaths: number = 2000,
    minHeat?: number,           // Thermal reachability filter: hide points below this heat
    view?: SpaceView,           // Optional view filter — different views = different symmetry groups
): MineResult {
    const space = registry.spaces.get(spaceName);
    if (!space) {
        return {
            spaceName,
            points: [],
            totalPaths: 0,
            maxDepth: 0,
            spaceHeat: 1,
            kernelComplete: false,
            frozenCount: 0,
            frozenRatio: 0,
            shaDetected: false,
            thermalFrontier: [],
        };
    }

    const kernel = isKernelComplete(space);
    const spaceHeat = computeSpaceHeat(space);

    // Enumerate all valid coordinate paths through the child tree
    const paths: ValidPath[] = [];
    const root = space.nodes.get(space.rootId);
    if (root) {
        enumeratePaths(
            registry,
            space,
            root,
            '',       // coordinate so far
            [],       // labels so far
            0,        // depth
            paths,
            maxPaths,
            view,     // view filter
        );
    }

    // Project paths onto a 2D plane
    const maxDepth = paths.reduce((max, p) => Math.max(max, p.depth), 0);
    const points = projectPathsToPlane(paths, maxDepth, kernel.complete);

    // Ш detection: count frozen paths
    const frozenCount = paths.filter(p => p.isFrozen).length;
    const frozenRatio = paths.length > 0 ? frozenCount / paths.length : 0;
    const shaDetected = paths.length > 0 && frozenRatio === 1.0;

    // Thermal frontier: unfrozen nodes with at least 1 frozen sibling
    const thermalFrontier = paths
        .filter(p => !p.isFrozen && !p.isLocked && p.frozenSiblingCount > 0)
        .map(p => p.coordinate);

    // Apply thermal reachability filter if requested
    const filteredPoints = minHeat !== undefined
        ? points.filter(p => p.heat >= minHeat)
        : points;

    if (shaDetected) {
        console.warn(`Ш DETECTED in space "${spaceName}": 100% coherence (${frozenCount}/${paths.length} frozen)`);
    }

    return {
        spaceName,
        points: filteredPoints,
        totalPaths: paths.length,
        maxDepth,
        spaceHeat,
        kernelComplete: kernel.complete,
        frozenCount,
        frozenRatio,
        shaDetected,
        thermalFrontier,
    };
}

// ── Path enumeration ──

interface ValidPath {
    coordinate: string;   // e.g., "1.2.3"
    labels: string[];     // e.g., ["Intro", "Topic", "Point"]
    depth: number;
    isLeaf: boolean;      // true if this node has no children
    isLocked: boolean;    // true if all nodes on this path are locked
    isFrozen: boolean;    // true if this node is frozen (sorry resolved)
    hasProducedSpace: boolean;  // true if the endpoint has a producedSpace (can drill)
    frozenSiblingCount: number; // how many siblings of this node are frozen
    totalSiblings: number;      // total siblings at this level
    role?: string;              // proof role of this node
}

function enumeratePaths(
    registry: Registry,
    space: Space,
    node: CBNode,
    coordPrefix: string,
    labelPrefix: string[],
    depth: number,
    paths: ValidPath[],
    maxPaths: number,
    view?: SpaceView,
): void {
    if (paths.length >= maxPaths) return;

    // Apply view filter at THIS level only — once a child passes, its subtree is fully traversed
    const children = view ? getViewChildren(space, node.id, view) : node.children;
    const allChildren = node.children; // For sibling counting, always use full set

    for (let i = 0; i < children.length; i++) {
        if (paths.length >= maxPaths) return;

        const childId = children[i];
        const child = space.nodes.get(childId);
        if (!child) continue;

        // Use the node's own ID to extract the selection segment.
        // For root children, the ID IS the selection (e.g., "1", "91").
        // For deeper nodes, the last segment after the final "." is the selection.
        const lastDot = childId.lastIndexOf('.');
        const selectionSegment = lastDot >= 0 ? childId.slice(lastDot + 1) : childId;
        const coord = coordPrefix ? `${coordPrefix}.${selectionSegment}` : selectionSegment;
        const labels = [...labelPrefix, child.label];
        const childDepth = depth + 1;

        const isLeaf = child.children.length === 0 && !child.producedSpace;
        const isLocked = !!child.locked;
        const isFrozen = !!child.frozen;

        // Count frozen siblings at this level (use full children, not filtered)
        let frozenSiblingCount = 0;
        for (const sibId of allChildren) {
            if (sibId !== childId) {
                const sib = space.nodes.get(sibId);
                if (sib?.frozen) frozenSiblingCount++;
            }
        }

        // This coordinate path is valid — record it
        paths.push({
            coordinate: coord,
            labels,
            depth: childDepth,
            isLeaf,
            isLocked,
            isFrozen,
            hasProducedSpace: !!child.producedSpace,
            frozenSiblingCount,
            totalSiblings: allChildren.length - 1,
            role: child.role,
        });

        // If child has children, recurse (dot = production chain)
        if (child.children.length > 0) {
            // Child passed the view — traverse its subtree fully (no view filter)
            enumeratePaths(
                registry,
                space,
                child,
                coord,
                labels,
                childDepth,
                paths,
                maxPaths,
                // No view: descendants of passing nodes are always included
            );
        }

        // If child has a producedSpace, also enumerate through it (drill-navigable)
        if (child.producedSpace) {
            const drillSpace = registry.spaces.get(child.producedSpace);
            if (drillSpace) {
                const drillRoot = drillSpace.nodes.get(drillSpace.rootId);
                if (drillRoot) {
                    // Drill adds "8" to the coordinate
                    const drillCoord = `${coord}8`;
                    enumeratePaths(
                        registry,
                        drillSpace,
                        drillRoot,
                        drillCoord,
                        labels,
                        childDepth + 1,
                        paths,
                        maxPaths,
                        // No view: drill-through inherits parent's pass
                    );
                }
            }
        }
    }
}

// ── Projection: Map paths onto a 2D plane ──

function projectPathsToPlane(
    paths: ValidPath[],
    maxDepth: number,
    kernelComplete: boolean,
): MinedPoint[] {
    if (paths.length === 0) return [];

    const points: MinedPoint[] = [];

    // Add origin
    points.push({
        x: 0,
        y: 0,
        heat: kernelComplete ? 0 : 0.5,
        label: 'Origin',
        radius: 8,
        coordinate: '0',
        depth: 0,
    });

    // Group paths by depth for layered layout
    const depthGroups = new Map<number, ValidPath[]>();
    for (const path of paths) {
        const group = depthGroups.get(path.depth) || [];
        group.push(path);
        depthGroups.set(path.depth, group);
    }

    for (const path of paths) {
        const group = depthGroups.get(path.depth) || [];
        const indexInGroup = group.indexOf(path);
        const groupSize = group.length;

        // X = spread within depth level (fan out from center)
        // Y = depth (deeper paths are higher/further out)
        const angle = groupSize === 1
            ? 0
            : ((indexInGroup / groupSize) * Math.PI * 2) - Math.PI / 2;

        const radius = path.depth * 2;
        const x = groupSize === 1 ? 0 : Math.cos(angle) * radius;
        const y = path.depth * 2;  // Each depth level gets its own row

        // If many nodes at same depth, use a grid instead of radial
        const useGrid = groupSize > 8;
        let finalX = x;
        let finalY = y;

        if (useGrid) {
            const cols = Math.ceil(Math.sqrt(groupSize));
            const col = indexInGroup % cols;
            const row = Math.floor(indexInGroup / cols);
            finalX = (col - cols / 2) * 1.5;
            finalY = path.depth * 3 + row * 1.2;
        }

        // Heat: sorry-aware propagation
        //   frozen  = proven = cold (0.0)
        //   locked  = instantiated = cool (0.1)
        //   warm    = adjacent to frozen = warm (scales with frozen neighbor ratio)
        //   hot     = unresolved sorry = hot (0.7-0.9)
        let heat: number;
        if (path.isFrozen) {
            heat = 0.0;  // Frozen = proven = cold (sorry resolved)
        } else if (path.isLocked) {
            heat = 0.1;  // Locked = instantiated = cool
        } else {
            // Base heat by position
            const baseHeat = path.isLeaf ? 0.5 : path.hasProducedSpace ? 0.4 : 0.7;
            // Propagation: frozen siblings make this node warmer (closer to resolution)
            const frozenRatio = path.totalSiblings > 0
                ? path.frozenSiblingCount / path.totalSiblings
                : 0;
            // Higher frozenRatio = more context = warmer = closer to provable
            // heat approaches 0.3 as more siblings freeze (warm frontier)
            heat = baseHeat * (1 - frozenRatio * 0.5);
        }

        // Build label
        const shortLabel = path.labels.length > 0
            ? path.labels[path.labels.length - 1]
            : path.coordinate;

        points.push({
            x: finalX,
            y: finalY,
            heat,
            label: shortLabel,
            radius: path.isLeaf ? 5 : 7,
            coordinate: path.coordinate,
            depth: path.depth,
        });
    }

    return points;
}

// Encoding constants and functions (encodeDot, decodeDot, coordToReal,
// DOT_ENCODING, KERNEL_OPEN, KERNEL_CLOSE) are imported from index.ts


// ═══════════════════════════════════════════════════════════
// DIGIT INTERLEAVING: ℝ → ℝ² bijection
//
// A CB real like 0.189883 has digit string "189883".
// Split into odd-index and even-index digits:
//   odd  (0,2,4): 1,9,8 → x = 0.198
//   even (1,3,5): 8,8,3 → y = 0.883
//
// Every (x,y) maps to exactly one CB real. No normalization,
// no information loss. The plane IS the encoding.
// ═══════════════════════════════════════════════════════════

/**
 * Split a CB encoded digit string into (x, y) via digit interleaving.
 * 
 * @param encoded - Pure digit string (e.g., "189883")
 * @returns { x, y, xDigits, yDigits } where x,y are reals in [0,1)
 */
export function realToPlane(encoded: string): { x: number; y: number; xDigits: string; yDigits: string } {
    const xDigits: string[] = [];
    const yDigits: string[] = [];
    for (let i = 0; i < encoded.length; i++) {
        if (i % 2 === 0) {
            xDigits.push(encoded[i]);
        } else {
            yDigits.push(encoded[i]);
        }
    }
    const xStr = xDigits.join('');
    const yStr = yDigits.join('');
    return {
        x: xStr.length > 0 ? parseFloat(`0.${xStr}`) : 0,
        y: yStr.length > 0 ? parseFloat(`0.${yStr}`) : 0,
        xDigits: xStr,
        yDigits: yStr,
    };
}

/**
 * Reverse: interleave x and y digit strings back into a CB encoded string.
 * 
 * @param xDigits - Digits from x coordinate
 * @param yDigits - Digits from y coordinate
 * @returns The original CB encoded digit string
 */
export function planeToReal(xDigits: string, yDigits: string): string {
    const result: string[] = [];
    const maxLen = Math.max(xDigits.length, yDigits.length);
    for (let i = 0; i < maxLen; i++) {
        if (i < xDigits.length) result.push(xDigits[i]);
        if (i < yDigits.length) result.push(yDigits[i]);
    }
    return result.join('');
}


/**
 * Encode a full mineSpace coordinate with kernel context.
 *
 * @param deliverableId  Which global space this kernel delivers
 * @param segments       Array of { spaceId, selection } for each level
 * @returns Pure digit string encoding the full semantic coordinate
 */
export function encodeFullCoordinate(
    deliverableId: number,
    segments: Array<{ spaceId: number; selection: number }>,
): string {
    // First: which deliverable this kernel is for
    let encoded = `${KERNEL_OPEN}${deliverableId}${KERNEL_CLOSE}`;

    // Each subsequent segment: which space fills this slot + selection
    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i];
        encoded += `${KERNEL_OPEN}${seg.spaceId}${KERNEL_CLOSE}${seg.selection}`;
        if (i < segments.length - 1) {
            encoded += DOT_ENCODING;  // dot between segments
        }
    }

    return encoded;
}

/** Convert a full mineSpace coordinate to a real number */
export function fullCoordToReal(
    deliverableId: number,
    segments: Array<{ spaceId: number; selection: number }>,
): number {
    return parseFloat(`0.${encodeFullCoordinate(deliverableId, segments)}`);
}


// ═══════════════════════════════════════════════════════════
// MINESPACE: A flat plane equipped with CB encoding.
//
// A mineSpace IS the plane. It exists. It persists.
// It is keyed to a DELIVERABLE, not a kernel.
//
// Locking a kernel projects knowledge onto the plane:
//   valid    — coordinates we have full simulations for
//   adjacent — same dot structure, spectral values need inference
//   invalid  — different dot structure, still encrypted
//
// The plane has origin (0,0). All points are (x, y) reals.
// ═══════════════════════════════════════════════════════════

export type PointStatus = 'valid' | 'adjacent' | 'invalid';

export interface KnownPoint {
    x: number;
    y: number;
    coordinate: string;     // The dot-separated source coordinate
    encoded: string;        // The pure digit encoding
    status: PointStatus;
    fromKernel: string;     // Which kernel projected this knowledge
    label: string;          // Human-readable name (e.g., "Agency", "ThreadGenerator")
    heat: number;           // 0=frozen/cold, 1=hot/unresolved
    depth: number;          // How deep in the tree
}

/**
 * MineSpace: a flat 2D plane equipped with a CB coordinate encoder.
 * Keyed to a deliverable. Persists across kernel projections.
 */
export interface MineSpace {
    deliverable: string;            // What this plane is ABOUT
    origin: { x: 0; y: 0 };
    known: KnownPoint[];            // What we know on this plane
    projectedKernels: string[];     // Which kernels have been projected
}

/**
 * Declare a mineSpace for a deliverable.
 * The plane exists — empty. Nothing known yet.
 */
export function declareMineSpace(deliverable: string): MineSpace {
    return {
        deliverable,
        origin: { x: 0, y: 0 },
        known: [],
        projectedKernels: [],
    };
}

/**
 * Project a locked kernel onto a mineSpace.
 *
 * The kernel's valid coordinate paths become known points.
 * Adjacent spectral values (±N from known, same dot structure)
 * become adjacent points. The rest stays encrypted.
 *
 * Multiple kernels can project onto the same mineSpace.
 */
export function projectKernel(
    mineSpace: MineSpace,
    registry: Registry,
    kernelSpaceName: SpaceName,
    adjacentDepth: number = 2,
): void {
    const space = registry.spaces.get(kernelSpaceName);
    if (!space) return;

    // Don't project the same kernel twice
    if (mineSpace.projectedKernels.includes(kernelSpaceName)) return;
    mineSpace.projectedKernels.push(kernelSpaceName);

    // Mine the kernel — enumerate all valid coordinate paths
    const mine = computeMinePlane(registry, kernelSpaceName);
    const paths = mine.points.filter(p => p.coordinate !== '0');
    if (paths.length === 0) return;

    // (x, y) = digit interleaving of the CB encoded string.
    // This is the ℝ → ℝ² bijection: each point gets a unique (x,y)
    // that round-trips back to its CB real encoding.
    const validCoords = new Set<string>();
    for (const path of paths) {
        const encoded = encodeDot(path.coordinate);
        const { x, y } = realToPlane(encoded);

        mineSpace.known.push({
            x,
            y,
            coordinate: path.coordinate,
            encoded,
            status: 'valid',
            fromKernel: kernelSpaceName,
            label: path.label,
            heat: path.heat,
            depth: path.depth,
        });
        validCoords.add(path.coordinate);
    }

    // Generate adjacent points: same dot structure, ±N spectral values
    const adjacentCoords = new Set<string>();
    for (const path of paths) {
        const parts = path.coordinate.split('.');
        for (let level = 0; level < parts.length; level++) {
            const current = parseInt(parts[level], 10);
            if (isNaN(current)) continue;

            for (let delta = -adjacentDepth; delta <= adjacentDepth; delta++) {
                if (delta === 0) continue;
                const next = current + delta;
                if (next < 1) continue;

                const adjParts = [...parts];
                adjParts[level] = String(next);
                const adjCoord = adjParts.join('.');

                if (validCoords.has(adjCoord)) continue;
                if (adjacentCoords.has(adjCoord)) continue;
                adjacentCoords.add(adjCoord);

                const adjEncoded = encodeDot(adjCoord);
                const { x, y } = realToPlane(adjEncoded);

                mineSpace.known.push({
                    x,
                    y,
                    coordinate: adjCoord,
                    encoded: adjEncoded,
                    status: 'adjacent',
                    fromKernel: kernelSpaceName,
                    label: `~${adjCoord}`,
                    heat: 0.8,
                    depth: adjCoord.split('.').length,
                });
            }
        }
    }
}

/**
 * mine() — the entry point (tree-node version).
 *
 * Declares a mineSpace for the deliverable, projects
 * the locked kernel onto it, returns the plane.
 */
export function mine(
    registry: Registry,
    kernelSpaceName: SpaceName,
    deliverable?: string,
    adjacentDepth?: number,
): MineSpace {
    const name = deliverable ?? kernelSpaceName;
    const ms = declareMineSpace(name);
    projectKernel(ms, registry, kernelSpaceName, adjacentDepth);
    return ms;
}


// ═══════════════════════════════════════════════════════════
// CONFIGURATION-LEVEL MINESPACE
//
// Each point = a COMPLETE configuration (one choice per dimension).
// The "current" config is what's locked. Neighbors differ by one dim.
//
// Encoding: config = [c1, c2, c3, ..., cN] child indices
// CB coordinate = "c1.c2.c3...cN" (dot-separated selections)
// encoded = encodeDot(coordinate) → pure digit string
// (x, y) = realToPlane(encoded) → digit interleaving
// ═══════════════════════════════════════════════════════════

export interface DimInfo {
    dimCoord: string;    // e.g., "1"
    dimLabel: string;    // e.g., "BusinessModel"
    children: Array<{
        coord: string;   // e.g., "1.1"
        label: string;   // e.g., "Agency"
        childIndex: number; // 1-based index within this dimension
        locked: boolean;
    }>;
}

export interface ConfigPoint extends KnownPoint {
    choices: Array<{ dim: string; choice: string; childIdx: number }>;
    configLabel: string;  // e.g., "Agency × ThreadGen × ..."
}

/**
 * Extract dimension structure from a kernel.
 * Returns the list of dimensions, each with their children.
 */
export function extractDimensions(registry: Registry, spaceName: SpaceName): DimInfo[] {
    const mine = computeMinePlane(registry, spaceName);
    const dims: DimInfo[] = [];

    // Depth-1 points are dimensions
    const dimPoints = mine.points.filter(p => p.depth === 1);
    const childPoints = mine.points.filter(p => p.depth === 2);

    for (const dim of dimPoints) {
        const prefix = dim.coordinate + '.';
        const kids = childPoints
            .filter(c => c.coordinate.startsWith(prefix))
            .map((c, i) => ({
                coord: c.coordinate,
                label: c.label,
                childIndex: parseInt(c.coordinate.split('.').pop() || '0', 10),
                locked: c.heat < 0.15,
            }));
        dims.push({
            dimCoord: dim.coordinate,
            dimLabel: dim.label,
            children: kids,
        });
    }

    return dims;
}

/**
 * Build a configuration coordinate from child selections.
 * Takes an array of child index per dimension (1-based).
 * Returns a dot-separated coordinate like "1.3.5.2.1.6.4.2"
 */
function configToCoordinate(selections: number[]): string {
    return selections.join('.');
}

/**
 * Build the label for a configuration from dimension info.
 */
function configToLabel(dims: DimInfo[], selections: number[]): string {
    return selections.map((sel, i) => {
        const dim = dims[i];
        if (!dim) return `?${sel}`;
        const child = dim.children.find(c => c.childIndex === sel);
        return child ? child.label : `${dim.dimLabel}=${sel}`;
    }).join(' × ');
}

/**
 * Build choices array for detail display.
 */
function configToChoices(dims: DimInfo[], selections: number[]): ConfigPoint['choices'] {
    return selections.map((sel, i) => {
        const dim = dims[i];
        const child = dim?.children.find(c => c.childIndex === sel);
        return {
            dim: dim?.dimLabel || `dim${i}`,
            choice: child?.label || `${sel}`,
            childIdx: sel,
        };
    });
}

/**
 * mineConfigurations — Configuration-level mineSpace.
 *
 * Shows the current configuration (what's locked or default first-child),
 * plus all adjacent configurations (differ by one dimension choice).
 *
 * This is what mineSpace actually IS: full tuples on the plane.
 */
export function mineConfigurations(
    registry: Registry,
    spaceName: SpaceName,
): { mineSpace: MineSpace; dims: DimInfo[]; currentConfig: number[]; totalConfigs: number } {
    const dims = extractDimensions(registry, spaceName);
    if (dims.length === 0) {
        return {
            mineSpace: declareMineSpace(spaceName),
            dims: [],
            currentConfig: [],
            totalConfigs: 0,
        };
    }

    // Total configurations = product of all dimension child counts
    const totalConfigs = dims.reduce((prod, d) => prod * d.children.length, 1);

    // Current config: use locked children, or default to first child
    const currentConfig = dims.map(d => {
        const locked = d.children.find(c => c.locked);
        return locked ? locked.childIndex : d.children[0]?.childIndex || 1;
    });

    const ms = declareMineSpace(spaceName);

    // 1. Add the current configuration as 'valid' / highlighted
    const currentCoord = configToCoordinate(currentConfig);
    const currentEncoded = encodeDot(currentCoord);
    const currentPos = realToPlane(currentEncoded);

    const currentPoint: ConfigPoint = {
        x: currentPos.x,
        y: currentPos.y,
        coordinate: currentCoord,
        encoded: currentEncoded,
        status: 'valid',
        fromKernel: spaceName,
        label: configToLabel(dims, currentConfig),
        heat: 0.0,  // Current = frozen/chosen
        depth: 0,   // Depth 0 = the chosen config
        choices: configToChoices(dims, currentConfig),
        configLabel: configToLabel(dims, currentConfig),
    };
    ms.known.push(currentPoint);

    // 2. Add adjacent configurations: vary one dimension at a time
    for (let dimIdx = 0; dimIdx < dims.length; dimIdx++) {
        const dim = dims[dimIdx];
        for (const child of dim.children) {
            if (child.childIndex === currentConfig[dimIdx]) continue; // skip current

            const adjConfig = [...currentConfig];
            adjConfig[dimIdx] = child.childIndex;

            const adjCoord = configToCoordinate(adjConfig);
            const adjEncoded = encodeDot(adjCoord);
            const adjPos = realToPlane(adjEncoded);

            const adjPoint: ConfigPoint = {
                x: adjPos.x,
                y: adjPos.y,
                coordinate: adjCoord,
                encoded: adjEncoded,
                status: 'adjacent',
                fromKernel: spaceName,
                label: `${dim.dimLabel}→${child.label}`,
                heat: 0.3 + (dimIdx / dims.length) * 0.4, // Color by which dim changed
                depth: dimIdx + 1,  // Depth = which dimension differs
                choices: configToChoices(dims, adjConfig),
                configLabel: configToLabel(dims, adjConfig),
            };
            ms.known.push(adjPoint);
        }
    }

    return { mineSpace: ms, dims, currentConfig, totalConfigs };
}
