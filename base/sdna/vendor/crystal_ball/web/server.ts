declare const process: any;
declare const Buffer: any;
declare function require(name: string): any;

import {
  addAttribute,
  addNode,
  bloom,
  createCrystalBall,
  getAttributes,
  resolveCoordinate,
  serialize,
  type CrystalBall,
  type NodeId,
  type SpectrumValue,
} from "../src/index";

const http = require("node:http");
const path = require("node:path");
const fs = require("node:fs");
const cp = require("node:child_process");
const fsp = fs.promises;

type JsonRecord = Record<string, any>;

interface ClientNode {
  id: string;
  label: string;
  children: string[];
  slotCount: number;
  locked: boolean;
  attributes: {
    name: string;
    spectrum: SpectrumValue[];
    defaultValue?: SpectrumValue;
  }[];
  parentId: string | null;
  indexInParent: number | null;
  depth: number;
  pathDigits: number[];
}

interface ClientSpace {
  name: string;
  rootId: string;
  locked: boolean;
  nodes: ClientNode[];
}

interface ComposeResult {
  coordinate: string;
  warnings: string[];
}

const state = {
  spaces: new Map<string, CrystalBall>(),
  activeSpace: "HueSpectrum",
};

function createSeedSpace(name: string): CrystalBall {
  const cb = createCrystalBall(name);
  bloom(cb, "", "hue_point", 12);

  const root = cb.nodes.get("root");
  if (!root) return cb;

  for (let i = 0; i < root.children.length; i++) {
    const childId = root.children[i];
    const hue = (i * 30) % 360;
    const label = `hue_${hue}`;
    const child = cb.nodes.get(childId);
    if (!child) continue;
    child.label = label;
    addAttribute(cb, childId, "hue", [hue], hue);
    addAttribute(cb, childId, "family", ["warm", "cool", "neutral"]);
  }

  return cb;
}

function ensureSeedState(): void {
  if (state.spaces.size > 0) return;
  const seed = createSeedSpace("HueSpectrum");
  state.spaces.set(seed.name, seed);
}

function sendJson(res: any, code: number, payload: JsonRecord): void {
  const body = JSON.stringify(payload, null, 2);
  res.writeHead(code, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
  });
  res.end(body);
}

function sendText(res: any, code: number, text: string, contentType: string): void {
  res.writeHead(code, {
    "content-type": contentType,
    "cache-control": "no-store",
  });
  res.end(text);
}

async function readJsonBody(req: any): Promise<JsonRecord> {
  const chunks: any[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  if (chunks.length === 0) return {};
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw.trim()) return {};
  return JSON.parse(raw);
}

function getParentMap(cb: CrystalBall): Map<string, { parentId: string; index: number }> {
  const parentMap = new Map<string, { parentId: string; index: number }>();
  for (const [parentId, node] of cb.nodes) {
    for (let i = 0; i < node.children.length; i++) {
      parentMap.set(node.children[i], { parentId, index: i });
    }
  }
  return parentMap;
}

function getPathDigits(parentMap: Map<string, { parentId: string; index: number }>, nodeId: string): number[] {
  if (nodeId === "root") return [];
  const digits: number[] = [];
  let cursor: string | undefined = nodeId;
  while (cursor && cursor !== "root") {
    const ref = parentMap.get(cursor);
    if (!ref) break;
    digits.unshift(ref.index + 1);
    cursor = ref.parentId;
  }
  return digits;
}

function getDepth(parentMap: Map<string, { parentId: string; index: number }>, nodeId: string): number {
  return getPathDigits(parentMap, nodeId).length;
}

function toClientSpace(cb: CrystalBall): ClientSpace {
  const parentMap = getParentMap(cb);
  const serial = serialize(cb);

  const nodes: ClientNode[] = serial.nodes.map((node) => {
    const parentRef = parentMap.get(node.id);
    return {
      id: node.id,
      label: node.label,
      children: node.children,
      slotCount: node.slotCount,
      locked: node.locked,
      attributes: node.attributes,
      parentId: parentRef ? parentRef.parentId : null,
      indexInParent: parentRef ? parentRef.index : null,
      depth: getDepth(parentMap, node.id),
      pathDigits: getPathDigits(parentMap, node.id),
    };
  });

  nodes.sort((a, b) => {
    if (a.depth !== b.depth) return a.depth - b.depth;
    return a.id.localeCompare(b.id);
  });

  return {
    name: cb.name,
    rootId: cb.rootId,
    locked: cb.locked,
    nodes,
  };
}

function composeCoordinateFromNodeIds(cb: CrystalBall, nodeIds: string[]): ComposeResult {
  const parentMap = getParentMap(cb);
  const levelSets = new Map<number, Set<number>>();
  const warnings: string[] = [];

  for (const nodeId of nodeIds) {
    const digits = getPathDigits(parentMap, nodeId);
    for (let i = 0; i < digits.length; i++) {
      const rawDigit = digits[i];
      if (!levelSets.has(i)) levelSets.set(i, new Set<number>());
      const level = levelSets.get(i)!;

      if (rawDigit > 8) {
        warnings.push(`Node ${nodeId} uses child index ${rawDigit}; mapped to 0 (superposition) at level ${i + 1}.`);
        level.add(0);
      } else {
        if (!level.has(0)) level.add(rawDigit);
      }
    }
  }

  const levels = Array.from(levelSets.keys())
    .sort((a, b) => a - b)
    .map((levelIdx) => {
      const digits = Array.from(levelSets.get(levelIdx) ?? []).sort((a, b) => a - b);
      if (digits.includes(0)) return "0";
      return digits.join("");
    })
    .filter((token) => token.length > 0);

  return {
    coordinate: levels.join("."),
    warnings,
  };
}

function parseSpectrum(raw: any): SpectrumValue[] {
  if (Array.isArray(raw)) return raw as SpectrumValue[];
  if (typeof raw === "string") {
    return raw
      .split(",")
      .map((x) => x.trim())
      .filter((x) => x.length > 0)
      .map((x) => {
        if (x === "true") return true;
        if (x === "false") return false;
        const maybe = Number(x);
        return Number.isNaN(maybe) ? x : maybe;
      });
  }
  return [];
}

function getSpace(spaceName: string | undefined): CrystalBall | null {
  if (!spaceName) return null;
  return state.spaces.get(spaceName) ?? null;
}

function spaceList(): string[] {
  return Array.from(state.spaces.keys()).sort();
}

function llmStub(input: {
  spaceName: string;
  coordinate: string;
  includeNodeIds: string[];
  prompt: string;
  resolvedLabels: string[];
}): JsonRecord {
  const target = input.resolvedLabels.length > 0 ? input.resolvedLabels.join(", ") : "root context";
  const prompt = input.prompt.trim() || "Generate next typed candidate point";

  return {
    ok: true,
    stub: true,
    model: "llm-fallback-v1",
    guidance: [
      `Space: ${input.spaceName}`,
      `Coordinate: ${input.coordinate || "(none)"}`,
      `Included points: ${input.includeNodeIds.join(", ") || "(none)"}`,
      `Target neighborhood: ${target}`,
      `Prompt: ${prompt}`,
    ],
    suggestedAction: {
      label: `candidate_${Date.now().toString().slice(-4)}`,
      parentId: input.includeNodeIds[0] ?? "root",
      attributes: [
        { name: "status", spectrum: ["draft", "validated"], defaultValue: "draft" },
        { name: "source", spectrum: ["heaven-fallback"], defaultValue: "heaven-fallback" },
      ],
    },
    actions: [
      {
        label: `candidate_${Date.now().toString().slice(-4)}`,
        parentId: input.includeNodeIds[0] ?? "root",
        attributes: [
          { name: "status", spectrum: ["draft", "validated"], defaultValue: "draft" },
          { name: "source", spectrum: ["heaven-fallback"], defaultValue: "heaven-fallback" },
        ],
      },
    ],
    keywords: [],
    confidence: 0,
    rationale: "Fallback response generated locally.",
  };
}

function pickNeighborhood(space: CrystalBall, includeNodeIds: string[], resolvedNodeIds: string[]): JsonRecord[] {
  const seen = new Set<string>();
  const rows: JsonRecord[] = [];

  for (const nodeId of [...includeNodeIds, ...resolvedNodeIds]) {
    if (seen.has(nodeId)) continue;
    seen.add(nodeId);
    const node = space.nodes.get(nodeId);
    if (!node) continue;
    rows.push({
      id: node.id,
      label: node.label,
      slotCount: node.slotCount,
      childCount: node.children.length,
      attributes: getAttributes(node).map((attr) => ({
        name: attr.name,
        spectrum: attr.spectrum,
        defaultValue: attr.defaultValue,
      })),
    });
  }

  return rows.slice(0, 24);
}

function buildExistingByParent(space: CrystalBall, parentIds: string[]): JsonRecord {
  const uniqueIds = new Set<string>(["root", ...parentIds]);
  const existing: JsonRecord = {};

  for (const parentId of uniqueIds) {
    const parent = space.nodes.get(parentId);
    if (!parent) continue;
    existing[parentId] = parent.children
      .map((childId) => space.nodes.get(childId)?.label)
      .filter((label) => typeof label === "string");
  }
  return existing;
}

function buildSuggestContext(space: CrystalBall, includeNodeIds: string[], coordinate: string): {
  resolvedLabels: string[];
  resolvedNodeIds: string[];
  neighborhood: JsonRecord[];
  existingByParent: JsonRecord;
} {
  const resolvedNodes = coordinate ? resolveCoordinate(space, coordinate) : [];
  const resolvedLabels = resolvedNodes.map((node) => node.label);
  const resolvedNodeIds = resolvedNodes.map((node) => node.id);
  const neighborhood = pickNeighborhood(space, includeNodeIds, resolvedNodeIds);
  const neighborhoodIds = neighborhood.map((row) => String(row.id || ""));
  const existingByParent = buildExistingByParent(space, [...includeNodeIds, ...resolvedNodeIds, ...neighborhoodIds]);
  return {
    resolvedLabels,
    resolvedNodeIds,
    neighborhood,
    existingByParent,
  };
}

function normalizeActionForApply(raw: any, defaultParentId: string): JsonRecord | null {
  if (!raw || typeof raw !== "object") return null;

  const label = String(raw.label || "").trim();
  if (!label) return null;

  const parentId = String(raw.parentId || defaultParentId || "root").trim() || "root";
  const attrsRaw = Array.isArray(raw.attributes) ? raw.attributes : [];
  const attributes = attrsRaw
    .filter((attr) => attr && typeof attr === "object")
    .map((attr) => {
      const name = String(attr.name || "").trim();
      const spectrum = Array.isArray(attr.spectrum) ? attr.spectrum : (attr.defaultValue !== undefined ? [attr.defaultValue] : []);
      const defaultValue = attr.defaultValue !== undefined ? attr.defaultValue : spectrum[0];
      return {
        name,
        spectrum,
        defaultValue,
      };
    })
    .filter((attr) => attr.name.length > 0 && Array.isArray(attr.spectrum) && attr.spectrum.length > 0);

  return {
    label,
    parentId,
    attributes,
  };
}

function actionExists(space: CrystalBall, parentId: string, label: string): boolean {
  const parent = space.nodes.get(parentId);
  if (!parent) return false;
  const target = label.trim().toLowerCase();
  for (const childId of parent.children) {
    const child = space.nodes.get(childId);
    if (!child) continue;
    if (child.label.trim().toLowerCase() === target) {
      return true;
    }
  }
  return false;
}

function applySuggestedActions(
  space: CrystalBall,
  rawActions: any[],
  defaultParentId: string,
  maxAdds: number,
  perParentCap: number
): JsonRecord {
  const result = {
    attempted: 0,
    added: 0,
    skipped: 0,
    errors: 0,
    addedNodeIds: [] as string[],
    perParentAdded: {} as Record<string, number>,
    messages: [] as string[],
  };

  const cap = Math.max(1, Math.min(128, Number.isFinite(maxAdds) ? maxAdds : 32));
  const perCap = Math.max(0, Math.min(32, Number.isFinite(perParentCap) ? perParentCap : 0));
  const parentAdds = new Map<string, number>();
  for (const raw of rawActions.slice(0, cap)) {
    result.attempted += 1;
    const action = normalizeActionForApply(raw, defaultParentId);
    if (!action) {
      result.skipped += 1;
      result.messages.push("Skipped invalid action payload.");
      continue;
    }
    if (!space.nodes.has(action.parentId)) {
      result.errors += 1;
      result.messages.push(`Missing parent node: ${action.parentId}`);
      continue;
    }
    if (actionExists(space, action.parentId, action.label)) {
      result.skipped += 1;
      result.messages.push(`Duplicate skipped: ${action.parentId}/${action.label}`);
      continue;
    }
    if (perCap > 0 && (parentAdds.get(action.parentId) ?? 0) >= perCap) {
      result.skipped += 1;
      result.messages.push(`Per-parent cap reached: ${action.parentId} (${perCap})`);
      continue;
    }

    try {
      const node = addNode(space, action.parentId, action.label);
      for (const attr of action.attributes) {
        try {
          addAttribute(space, node.id, attr.name, attr.spectrum, attr.defaultValue);
        } catch (attrErr: any) {
          result.errors += 1;
          result.messages.push(`Attr error on ${node.id}@${attr.name}: ${attrErr?.message || String(attrErr)}`);
        }
      }
      result.added += 1;
      result.addedNodeIds.push(node.id);
      const nextCount = (parentAdds.get(action.parentId) ?? 0) + 1;
      parentAdds.set(action.parentId, nextCount);
      result.perParentAdded[action.parentId] = nextCount;
    } catch (err: any) {
      result.errors += 1;
      result.messages.push(`Add node failed: ${err?.message || String(err)}`);
    }
  }

  return result;
}

function mergeApplyResults(base: JsonRecord, next: JsonRecord): JsonRecord {
  const merged: JsonRecord = {
    attempted: Number(base.attempted || 0) + Number(next.attempted || 0),
    added: Number(base.added || 0) + Number(next.added || 0),
    skipped: Number(base.skipped || 0) + Number(next.skipped || 0),
    errors: Number(base.errors || 0) + Number(next.errors || 0),
    addedNodeIds: [
      ...(Array.isArray(base.addedNodeIds) ? base.addedNodeIds : []),
      ...(Array.isArray(next.addedNodeIds) ? next.addedNodeIds : []),
    ],
    perParentAdded: { ...(base.perParentAdded || {}) } as Record<string, number>,
    messages: [
      ...(Array.isArray(base.messages) ? base.messages : []),
      ...(Array.isArray(next.messages) ? next.messages : []),
    ],
  };

  const nextPerParent = (next.perParentAdded || {}) as Record<string, number>;
  for (const [parentId, count] of Object.entries(nextPerParent)) {
    merged.perParentAdded[parentId] = Number(merged.perParentAdded[parentId] || 0) + Number(count || 0);
  }
  if (Array.isArray(merged.messages) && merged.messages.length > 300) {
    merged.messages = merged.messages.slice(-300);
  }
  return merged;
}

async function runPythonSuggest(payload: JsonRecord): Promise<JsonRecord> {
  const repoRoot = process.env.SDNA_REPO_ROOT || path.resolve(process.cwd(), "..", "..");
  const pythonBin = process.env.CB_PYTHON || "python";
  const pyPath = process.env.PYTHONPATH
    ? `${repoRoot}${path.delimiter}${process.env.PYTHONPATH}`
    : repoRoot;

  return await new Promise((resolve, reject) => {
    const child = cp.spawn(pythonBin, ["-m", "sdna.crystal_ball_suggest_cli"], {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONPATH: pyPath,
      },
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk: any) => {
      stdout += String(chunk);
    });
    child.stderr.on("data", (chunk: any) => {
      stderr += String(chunk);
    });
    child.on("error", (err: any) => reject(err));
    child.on("close", (code: number) => {
      if (code !== 0) {
        reject(new Error(`python suggest exited ${code}: ${stderr || stdout || "unknown error"}`));
        return;
      }

      const trimmed = stdout.trim();
      if (!trimmed) {
        reject(new Error("python suggest returned empty output"));
        return;
      }

      try {
        resolve(JSON.parse(trimmed));
        return;
      } catch (_err) {
        const lastLine = trimmed.split("\n").pop() || "";
        try {
          resolve(JSON.parse(lastLine));
          return;
        } catch (err2: any) {
          reject(new Error(`python suggest returned non-JSON output: ${err2?.message || "parse error"}`));
        }
      }
    });

    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

async function llmSuggest(input: {
  space: CrystalBall;
  spaceName: string;
  coordinate: string;
  includeNodeIds: string[];
  prompt: string;
  resolvedLabels: string[];
  resolvedNodeIds: string[];
  mode: "single" | "batch";
  maxActions: number;
  perParentCap: number;
  retryAttempts: number;
  existingByParent: JsonRecord;
  neighborhood: JsonRecord[];
}): Promise<JsonRecord> {
  const fallback = llmStub({
    spaceName: input.spaceName,
    coordinate: input.coordinate,
    includeNodeIds: input.includeNodeIds,
    prompt: input.prompt,
    resolvedLabels: input.resolvedLabels,
  });

  try {
    const result = await runPythonSuggest({
      space_name: input.spaceName,
      coordinate: input.coordinate,
      include_node_ids: input.includeNodeIds,
      prompt: input.prompt,
      resolved_labels: input.resolvedLabels,
      neighborhood: input.neighborhood,
      mode: input.mode,
      max_actions: input.maxActions,
      per_parent_cap: input.perParentCap,
      existing_by_parent: input.existingByParent,
      retry_attempts: input.retryAttempts,
      model: process.env.CB_MODEL || "MiniMax-M2.5-highspeed",
      max_turns: Number(process.env.CB_MAX_TURNS || "1"),
    });

    if (!result || typeof result !== "object") {
      return {
        ...fallback,
        warning: "llm_suggest returned invalid payload shape; fallback used.",
      };
    }

    return {
      ...result,
      stub: Boolean(result.stub),
    };
  } catch (err: any) {
    return {
      ...fallback,
      warning: `llm_suggest failed: ${err?.message || String(err)}`,
    };
  }
}

async function serveStatic(req: any, res: any): Promise<void> {
  const publicDir = path.join(process.cwd(), "web", "public");
  const url = new URL(req.url || "/", "http://localhost");
  const requested = url.pathname === "/" ? "index.html" : url.pathname.replace(/^\/+/, "");
  const normalized = path.normalize(requested).replace(/^(\.\.[/\\]?)+/, "");
  const safeRoot = path.resolve(publicDir);
  const filePath = path.resolve(safeRoot, normalized);

  if (!(filePath === safeRoot || filePath.startsWith(`${safeRoot}${path.sep}`))) {
    sendText(res, 403, "Forbidden", "text/plain; charset=utf-8");
    return;
  }

  try {
    const content = await fsp.readFile(filePath, "utf8");
    const ext = path.extname(filePath).toLowerCase();
    const contentType =
      ext === ".html"
        ? "text/html; charset=utf-8"
        : ext === ".css"
          ? "text/css; charset=utf-8"
          : ext === ".js"
            ? "application/javascript; charset=utf-8"
            : "text/plain; charset=utf-8";
    sendText(res, 200, content, contentType);
  } catch (_err) {
    sendText(res, 404, "Not found", "text/plain; charset=utf-8");
  }
}

function routeSegments(pathname: string): string[] {
  return pathname.split("/").filter((x) => x.length > 0).map((x) => decodeURIComponent(x));
}

async function handleApi(req: any, res: any): Promise<void> {
  const method = req.method || "GET";
  const url = new URL(req.url || "/", "http://localhost");
  const parts = routeSegments(url.pathname);

  if (method === "GET" && url.pathname === "/api/health") {
    sendJson(res, 200, { ok: true, spaces: spaceList(), activeSpace: state.activeSpace });
    return;
  }

  if (method === "GET" && url.pathname === "/api/spaces") {
    sendJson(res, 200, { spaces: spaceList(), activeSpace: state.activeSpace });
    return;
  }

  if (method === "POST" && url.pathname === "/api/spaces") {
    const body = await readJsonBody(req);
    const requestedName = String(body.name || "").trim();
    const name = requestedName || `Space_${state.spaces.size + 1}`;
    if (state.spaces.has(name)) {
      sendJson(res, 409, { error: `Space '${name}' already exists.` });
      return;
    }
    const space = createCrystalBall(name);
    state.spaces.set(name, space);
    state.activeSpace = name;
    sendJson(res, 201, { space: toClientSpace(space), spaces: spaceList(), activeSpace: state.activeSpace });
    return;
  }

  if (parts.length >= 3 && parts[0] === "api" && parts[1] === "spaces") {
    const spaceName = parts[2];
    const space = getSpace(spaceName);
    if (!space) {
      sendJson(res, 404, { error: `Unknown space '${spaceName}'.` });
      return;
    }

    if (method === "GET" && parts.length === 3) {
      sendJson(res, 200, { space: toClientSpace(space), spaces: spaceList(), activeSpace: state.activeSpace });
      return;
    }

    if (method === "POST" && parts.length === 4 && parts[3] === "activate") {
      state.activeSpace = spaceName;
      sendJson(res, 200, { ok: true, activeSpace: state.activeSpace });
      return;
    }

    if (method === "POST" && parts.length === 4 && parts[3] === "points") {
      const body = await readJsonBody(req);
      const parentId = String(body.parentId || "root");
      const label = String(body.label || "").trim();
      if (!label) {
        sendJson(res, 400, { error: "Missing point label." });
        return;
      }
      try {
        const node = addNode(space, parentId, label);
        sendJson(res, 201, {
          node: {
            id: node.id,
            label: node.label,
            children: node.children,
            slotCount: node.slotCount,
            locked: node.locked,
            attributes: getAttributes(node),
          },
          space: toClientSpace(space),
        });
      } catch (err: any) {
        sendJson(res, 400, { error: err?.message || "Failed to add point." });
      }
      return;
    }

    if (method === "POST" && parts.length === 4 && parts[3] === "attributes") {
      const body = await readJsonBody(req);
      const nodeId = String(body.nodeId || "");
      const name = String(body.name || "").trim();
      const spectrum = parseSpectrum(body.spectrum);
      const defaultValue = body.defaultValue;

      if (!nodeId || !name || spectrum.length === 0) {
        sendJson(res, 400, { error: "nodeId, name, and non-empty spectrum are required." });
        return;
      }

      try {
        addAttribute(space, nodeId, name, spectrum, defaultValue);
        sendJson(res, 201, { ok: true, nodeId, attribute: { name, spectrum, defaultValue }, space: toClientSpace(space) });
      } catch (err: any) {
        sendJson(res, 400, { error: err?.message || "Failed to add attribute." });
      }
      return;
    }

    if (method === "POST" && parts.length === 4 && parts[3] === "scry") {
      const body = await readJsonBody(req);
      const includeNodeIds = Array.isArray(body.includeNodeIds) ? body.includeNodeIds.map(String) : [];
      const incomingCoord = String(body.coordinate || "").trim();
      const compose = composeCoordinateFromNodeIds(space, includeNodeIds);
      const coordinate = incomingCoord || compose.coordinate;

      if (!coordinate) {
        sendJson(res, 200, {
          coordinate: "",
          composedCoordinate: compose.coordinate,
          warnings: compose.warnings,
          resolved: [],
          note: "No coordinate provided. Include points or type a coordinate to scry.",
        });
        return;
      }

      const resolved = resolveCoordinate(space, coordinate).map((node) => ({
        id: node.id,
        label: node.label,
        slotCount: node.slotCount,
        children: node.children.length,
        attributes: getAttributes(node).map((attr) => ({
          name: attr.name,
          spectrum: attr.spectrum,
          defaultValue: attr.defaultValue,
        })),
      }));

      sendJson(res, 200, {
        coordinate,
        composedCoordinate: compose.coordinate,
        warnings: compose.warnings,
        includeNodeIds,
        resolved,
      });
      return;
    }

    if (method === "POST" && parts.length === 4 && (parts[3] === "llm-suggest" || parts[3] === "llm-stub")) {
      const body = await readJsonBody(req);
      const includeNodeIds = Array.isArray(body.includeNodeIds) ? body.includeNodeIds.map(String) : [];
      const prompt = String(body.prompt || "");
      const autoApply = Boolean(body.autoApply);
      const dumpNeighborhood = Boolean(body.dumpNeighborhood);
      const saturateRequested = Boolean(body.saturate);
      const maxActionsRaw = Number(body.maxActions ?? 8);
      const maxActions = Number.isFinite(maxActionsRaw) ? Math.max(1, Math.min(64, maxActionsRaw)) : 8;
      const perParentCapRaw = Number(body.perParentCap ?? 0);
      const perParentCap = Number.isFinite(perParentCapRaw) ? Math.max(0, Math.min(16, perParentCapRaw)) : 0;
      const maxCyclesRaw = Number(body.maxCycles ?? 3);
      const maxCycles = Number.isFinite(maxCyclesRaw) ? Math.max(1, Math.min(12, maxCyclesRaw)) : 3;
      const retryAttemptsRaw = Number(body.retryAttempts ?? 2);
      const retryAttempts = Number.isFinite(retryAttemptsRaw) ? Math.max(0, Math.min(4, retryAttemptsRaw)) : 2;
      const mode = dumpNeighborhood ? "batch" : "single";
      const saturate = autoApply && saturateRequested;
      const incomingCoord = String(body.coordinate || "").trim();
      const compose = composeCoordinateFromNodeIds(space, includeNodeIds);
      const coordinate = incomingCoord || compose.coordinate;

      const cycleLimit = saturate ? maxCycles : 1;
      let finalResult: JsonRecord = {};
      let applyResult: JsonRecord | null = autoApply
        ? {
            attempted: 0,
            added: 0,
            skipped: 0,
            errors: 0,
            addedNodeIds: [] as string[],
            perParentAdded: {} as Record<string, number>,
            messages: [] as string[],
          }
        : null;
      const cycleSummaries: JsonRecord[] = [];
      let stopReason = saturate ? "max_cycles_reached" : "single_cycle";

      for (let cycle = 1; cycle <= cycleLimit; cycle++) {
        const context = buildSuggestContext(space, includeNodeIds, coordinate);
        const cycleResult = await llmSuggest({
          space,
          spaceName,
          coordinate,
          includeNodeIds,
          prompt,
          resolvedLabels: context.resolvedLabels,
          resolvedNodeIds: context.resolvedNodeIds,
          mode,
          maxActions,
          perParentCap,
          retryAttempts,
          existingByParent: context.existingByParent,
          neighborhood: context.neighborhood,
        });

        const defaultParentId = includeNodeIds[0] || context.resolvedNodeIds[0] || "root";
        const actionList = Array.isArray(cycleResult.actions)
          ? cycleResult.actions
          : (cycleResult.suggestedAction ? [cycleResult.suggestedAction] : []);

        let cycleApply: JsonRecord | null = null;
        if (autoApply) {
          cycleApply = applySuggestedActions(space, actionList, defaultParentId, maxActions, perParentCap);
          if (applyResult) {
            applyResult = mergeApplyResults(applyResult, cycleApply);
          }
        }

        finalResult = cycleResult;
        cycleSummaries.push({
          cycle,
          suggested: actionList.length,
          stub: Boolean(cycleResult.stub),
          status: cycleResult.status || null,
          warning: cycleResult.warning || null,
          applied: cycleApply,
        });

        if (!saturate) {
          stopReason = "single_cycle";
          break;
        }

        const addedThisCycle = Number(cycleApply?.added || 0);
        if (addedThisCycle <= 0) {
          stopReason = "no_new_nodes";
          break;
        }
      }

      sendJson(res, 200, {
        coordinate,
        composedCoordinate: compose.coordinate,
        warnings: compose.warnings,
        mode,
        autoApply,
        dumpNeighborhood,
        saturate,
        maxCycles,
        maxActions,
        perParentCap,
        retryAttempts,
        applied: applyResult,
        space: autoApply ? toClientSpace(space) : undefined,
        saturation: {
          requested: saturateRequested,
          enabled: saturate,
          maxCycles,
          cyclesRun: cycleSummaries.length,
          totalAdded: Number(applyResult?.added || 0),
          stopReason,
          cycles: cycleSummaries,
        },
        ...finalResult,
      });
      return;
    }

    if (method === "POST" && parts.length === 4 && parts[3] === "bloom") {
      const body = await readJsonBody(req);
      const coordinate = String(body.coordinate || "");
      const slotLabel = String(body.slotLabel || "point");
      const count = Number(body.count ?? 4);
      try {
        bloom(space, coordinate, slotLabel, Number.isFinite(count) ? count : 4);
        sendJson(res, 200, { ok: true, space: toClientSpace(space) });
      } catch (err: any) {
        sendJson(res, 400, { error: err?.message || "Failed to bloom." });
      }
      return;
    }
  }

  sendJson(res, 404, { error: "API route not found." });
}

async function requestHandler(req: any, res: any): Promise<void> {
  const url = new URL(req.url || "/", "http://localhost");
  if (url.pathname.startsWith("/api/")) {
    try {
      await handleApi(req, res);
    } catch (err: any) {
      sendJson(res, 500, { error: err?.message || "Unhandled server error." });
    }
    return;
  }
  await serveStatic(req, res);
}

async function main(): Promise<void> {
  ensureSeedState();
  const port = Number(process.env.PORT || 7344);

  const server = http.createServer((req: any, res: any) => {
    requestHandler(req, res).catch((err) => {
      sendJson(res, 500, { error: String(err) });
    });
  });

  server.listen(port, () => {
    console.log(`Crystal Ball Space UI running at http://localhost:${port}`);
    console.log(`Active space: ${state.activeSpace}`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
