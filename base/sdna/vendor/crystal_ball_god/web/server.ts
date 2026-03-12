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
    stub: true,
    model: "llm-stub-v1",
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
        { name: "source", spectrum: ["llm-stub"], defaultValue: "llm-stub" },
      ],
    },
  };
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

    if (method === "POST" && parts.length === 4 && parts[3] === "llm-stub") {
      const body = await readJsonBody(req);
      const includeNodeIds = Array.isArray(body.includeNodeIds) ? body.includeNodeIds.map(String) : [];
      const prompt = String(body.prompt || "");
      const coordinate = String(body.coordinate || "");
      const resolved = resolveCoordinate(space, coordinate).map((n) => n.label);
      const result = llmStub({
        spaceName,
        coordinate,
        includeNodeIds,
        prompt,
        resolvedLabels: resolved,
      });
      sendJson(res, 200, result);
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
