#!/usr/bin/env -S npx tsx

import * as fs from "node:fs";
import * as path from "node:path";
import {
  addAttribute,
  addNode,
  createCrystalBall,
  setSlotCount,
  toJSON,
  type CrystalBall,
  type SpectrumValue,
} from "../src/index";

type Primitive = string | number | boolean | null;

interface ParsedNode {
  id: string;
  variable: string | null;
  labels: Set<string>;
  properties: Map<string, Primitive>;
  occurrences: number;
}

interface ParsedRelationship {
  id: string;
  type: string;
  from: string;
  to: string;
  properties: Map<string, Primitive>;
}

interface ParseContext {
  nodesById: Map<string, ParsedNode>;
  variableToNodeId: Map<string, string>;
  relationships: ParsedRelationship[];
  anonymousCounter: number;
  relationshipCounter: number;
}

interface NodeParseResult {
  nodeId: string;
  nextIndex: number;
}

interface RelationshipParseResult {
  type: string;
  properties: Map<string, Primitive>;
  direction: "forward" | "backward";
  nextIndex: number;
}

interface CliOptions {
  inputPath: string;
  outputPath: string;
  spaceName: string;
}

function parseArgs(argv: string[]): CliOptions {
  const args = [...argv];
  let inputPath = "";
  let outputPath = "";
  let spaceName = "";

  while (args.length > 0) {
    const token = args.shift() ?? "";
    if (token === "--input" || token === "-i") {
      inputPath = args.shift() ?? "";
      continue;
    }
    if (token === "--output" || token === "-o") {
      outputPath = args.shift() ?? "";
      continue;
    }
    if (token === "--name" || token === "-n") {
      spaceName = args.shift() ?? "";
      continue;
    }
    if (token === "--help" || token === "-h") {
      printUsageAndExit(0);
    }
    if (!inputPath && !token.startsWith("-")) {
      inputPath = token;
      continue;
    }
    throw new Error(`Unknown argument: ${token}`);
  }

  if (!inputPath) {
    printUsageAndExit(1);
  }

  const absInput = path.resolve(inputPath);
  const base = path.basename(absInput, path.extname(absInput));
  const absOutput = outputPath
    ? path.resolve(outputPath)
    : path.join(path.dirname(absInput), `${base}.cb.json`);

  return {
    inputPath: absInput,
    outputPath: absOutput,
    spaceName: spaceName || `CB:${base}`,
  };
}

function printUsageAndExit(code: number): never {
  console.log(
    [
      "Usage:",
      "  npx tsx scripts/map_cypher_to_cb.ts --input <path/to/file.cypher> [--output <path/to/out.cb.json>] [--name <space_name>]",
      "",
      "Examples:",
      "  npx tsx scripts/map_cypher_to_cb.ts --input /Users/isaacwr/Documents/story_machine/story_graph.cleaned.cypher",
      "  npx tsx scripts/map_cypher_to_cb.ts -i graph.cypher -o graph.cb.json -n StoryMachineProjection",
    ].join("\n"),
  );
  process.exit(code);
}

function stripCreateEnvelope(cypherText: string): string {
  const noBom = cypherText.replace(/^\uFEFF/, "");
  let text = noBom.trim();

  const createMatch = text.match(/^\s*CREATE\b/i);
  if (createMatch) {
    text = text.slice(createMatch[0].length);
  }

  text = text.replace(/;\s*$/, "").trim();
  return text;
}

function splitTopLevelEntries(body: string): string[] {
  const entries: string[] = [];
  let start = 0;

  let parenDepth = 0;
  let bracketDepth = 0;
  let braceDepth = 0;
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  for (let i = 0; i < body.length; i++) {
    const ch = body[i];

    if (escaped) {
      escaped = false;
      continue;
    }

    if ((inSingle || inDouble) && ch === "\\") {
      escaped = true;
      continue;
    }

    if (inSingle) {
      if (ch === "'") inSingle = false;
      continue;
    }
    if (inDouble) {
      if (ch === '"') inDouble = false;
      continue;
    }
    if (inBacktick) {
      if (ch === "`") {
        if (body[i + 1] === "`") {
          i += 1;
        } else {
          inBacktick = false;
        }
      }
      continue;
    }

    if (ch === "'") {
      inSingle = true;
      continue;
    }
    if (ch === '"') {
      inDouble = true;
      continue;
    }
    if (ch === "`") {
      inBacktick = true;
      continue;
    }

    if (ch === "(") parenDepth += 1;
    else if (ch === ")") parenDepth -= 1;
    else if (ch === "[") bracketDepth += 1;
    else if (ch === "]") bracketDepth -= 1;
    else if (ch === "{") braceDepth += 1;
    else if (ch === "}") braceDepth -= 1;

    if (
      ch === "," &&
      parenDepth === 0 &&
      bracketDepth === 0 &&
      braceDepth === 0
    ) {
      const segment = body.slice(start, i).trim();
      if (segment) entries.push(segment);
      start = i + 1;
    }
  }

  const tail = body.slice(start).trim();
  if (tail) entries.push(tail);
  return entries;
}

function skipWhitespace(text: string, startIndex: number): number {
  let i = startIndex;
  while (i < text.length && /\s/.test(text[i])) i += 1;
  return i;
}

function readBalanced(
  text: string,
  startIndex: number,
  openChar: string,
  closeChar: string,
): { content: string; endIndex: number } {
  if (text[startIndex] !== openChar) {
    throw new Error(
      `Expected '${openChar}' at position ${startIndex}, found '${text[startIndex] ?? ""}'`,
    );
  }

  let depth = 1;
  let i = startIndex + 1;
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  while (i < text.length) {
    const ch = text[i];

    if (escaped) {
      escaped = false;
      i += 1;
      continue;
    }

    if ((inSingle || inDouble) && ch === "\\") {
      escaped = true;
      i += 1;
      continue;
    }

    if (inSingle) {
      if (ch === "'") inSingle = false;
      i += 1;
      continue;
    }
    if (inDouble) {
      if (ch === '"') inDouble = false;
      i += 1;
      continue;
    }
    if (inBacktick) {
      if (ch === "`") {
        if (text[i + 1] === "`") {
          i += 2;
          continue;
        }
        inBacktick = false;
      }
      i += 1;
      continue;
    }

    if (ch === "'") {
      inSingle = true;
      i += 1;
      continue;
    }
    if (ch === '"') {
      inDouble = true;
      i += 1;
      continue;
    }
    if (ch === "`") {
      inBacktick = true;
      i += 1;
      continue;
    }

    if (ch === openChar) {
      depth += 1;
    } else if (ch === closeChar) {
      depth -= 1;
      if (depth === 0) {
        return {
          content: text.slice(startIndex + 1, i),
          endIndex: i,
        };
      }
    }

    i += 1;
  }

  throw new Error(
    `Unbalanced '${openChar}${closeChar}' segment starting at position ${startIndex}`,
  );
}

function readToken(
  text: string,
  startIndex: number,
): { value: string; nextIndex: number } | null {
  let i = skipWhitespace(text, startIndex);
  if (i >= text.length) return null;

  if (text[i] === "`") {
    i += 1;
    let value = "";
    while (i < text.length) {
      const ch = text[i];
      if (ch === "`") {
        if (text[i + 1] === "`") {
          value += "`";
          i += 2;
          continue;
        }
        i += 1;
        return { value, nextIndex: i };
      }
      value += ch;
      i += 1;
    }
    throw new Error("Unterminated backtick token");
  }

  let value = "";
  while (i < text.length) {
    const ch = text[i];
    if (ch === ":" || ch === "{" || /\s/.test(ch)) break;
    value += ch;
    i += 1;
  }

  if (!value) return null;
  return { value, nextIndex: i };
}

function splitTopLevelByComma(input: string): string[] {
  const parts: string[] = [];
  let start = 0;
  let parenDepth = 0;
  let bracketDepth = 0;
  let braceDepth = 0;
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;

  for (let i = 0; i < input.length; i++) {
    const ch = input[i];

    if (escaped) {
      escaped = false;
      continue;
    }

    if ((inSingle || inDouble) && ch === "\\") {
      escaped = true;
      continue;
    }

    if (inSingle) {
      if (ch === "'") inSingle = false;
      continue;
    }
    if (inDouble) {
      if (ch === '"') inDouble = false;
      continue;
    }
    if (inBacktick) {
      if (ch === "`") {
        if (input[i + 1] === "`") {
          i += 1;
        } else {
          inBacktick = false;
        }
      }
      continue;
    }

    if (ch === "'") {
      inSingle = true;
      continue;
    }
    if (ch === '"') {
      inDouble = true;
      continue;
    }
    if (ch === "`") {
      inBacktick = true;
      continue;
    }

    if (ch === "(") parenDepth += 1;
    else if (ch === ")") parenDepth -= 1;
    else if (ch === "[") bracketDepth += 1;
    else if (ch === "]") bracketDepth -= 1;
    else if (ch === "{") braceDepth += 1;
    else if (ch === "}") braceDepth -= 1;

    if (
      ch === "," &&
      parenDepth === 0 &&
      bracketDepth === 0 &&
      braceDepth === 0
    ) {
      parts.push(input.slice(start, i));
      start = i + 1;
    }
  }

  parts.push(input.slice(start));
  return parts.map((x) => x.trim()).filter((x) => x.length > 0);
}

function splitKeyValue(input: string): { key: string; value: string } | null {
  let inSingle = false;
  let inDouble = false;
  let inBacktick = false;
  let escaped = false;
  let parenDepth = 0;
  let bracketDepth = 0;
  let braceDepth = 0;

  for (let i = 0; i < input.length; i++) {
    const ch = input[i];

    if (escaped) {
      escaped = false;
      continue;
    }

    if ((inSingle || inDouble) && ch === "\\") {
      escaped = true;
      continue;
    }

    if (inSingle) {
      if (ch === "'") inSingle = false;
      continue;
    }
    if (inDouble) {
      if (ch === '"') inDouble = false;
      continue;
    }
    if (inBacktick) {
      if (ch === "`") {
        if (input[i + 1] === "`") {
          i += 1;
        } else {
          inBacktick = false;
        }
      }
      continue;
    }

    if (ch === "'") {
      inSingle = true;
      continue;
    }
    if (ch === '"') {
      inDouble = true;
      continue;
    }
    if (ch === "`") {
      inBacktick = true;
      continue;
    }

    if (ch === "(") parenDepth += 1;
    else if (ch === ")") parenDepth -= 1;
    else if (ch === "[") bracketDepth += 1;
    else if (ch === "]") bracketDepth -= 1;
    else if (ch === "{") braceDepth += 1;
    else if (ch === "}") braceDepth -= 1;

    if (
      ch === ":" &&
      parenDepth === 0 &&
      bracketDepth === 0 &&
      braceDepth === 0
    ) {
      return {
        key: input.slice(0, i).trim(),
        value: input.slice(i + 1).trim(),
      };
    }
  }

  return null;
}

function unquoteKey(keyRaw: string): string {
  const key = keyRaw.trim();
  if (key.startsWith("`") && key.endsWith("`") && key.length >= 2) {
    return key.slice(1, -1).replace(/``/g, "`");
  }
  return key;
}

function parsePrimitive(rawValue: string): Primitive {
  const trimmed = rawValue.trim();

  if (trimmed === "null") return null;
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;

  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    const quote = trimmed[0];
    const inner = trimmed.slice(1, -1);
    if (quote === '"') {
      return inner.replace(/\\\\/g, "\\").replace(/\\"/g, '"');
    }
    return inner.replace(/\\\\/g, "\\").replace(/\\'/g, "'");
  }

  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    return Number(trimmed);
  }

  return trimmed;
}

function parsePropertyMap(raw: string): Map<string, Primitive> {
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) return new Map();

  const balanced = readBalanced(trimmed, 0, "{", "}").content;
  const entries = splitTopLevelByComma(balanced);
  const props = new Map<string, Primitive>();

  for (const entry of entries) {
    const kv = splitKeyValue(entry);
    if (!kv) continue;
    const key = unquoteKey(kv.key);
    const value = parsePrimitive(kv.value);
    props.set(key, value);
  }

  return props;
}

function parseNodeHeader(headRaw: string): {
  variable: string | null;
  labels: string[];
} {
  const head = headRaw.trim();
  let i = 0;

  let variable: string | null = null;
  const labels: string[] = [];

  i = skipWhitespace(head, i);

  if (i < head.length && head[i] !== ":") {
    const token = readToken(head, i);
    if (token) {
      const afterToken = skipWhitespace(head, token.nextIndex);
      if (afterToken >= head.length || head[afterToken] === ":") {
        variable = token.value;
        i = afterToken;
      }
    }
  }

  while (i < head.length) {
    i = skipWhitespace(head, i);
    if (i >= head.length) break;
    if (head[i] !== ":") {
      i += 1;
      continue;
    }
    i += 1;
    const token = readToken(head, i);
    if (!token) break;
    labels.push(token.value);
    i = token.nextIndex;
  }

  return { variable, labels };
}

function parseNodeContent(
  contentRaw: string,
  context: ParseContext,
): ParsedNode {
  const content = contentRaw.trim();
  const propertyStart = (() => {
    let inSingle = false;
    let inDouble = false;
    let inBacktick = false;
    let escaped = false;
    for (let i = 0; i < content.length; i++) {
      const ch = content[i];
      if (escaped) {
        escaped = false;
        continue;
      }
      if ((inSingle || inDouble) && ch === "\\") {
        escaped = true;
        continue;
      }
      if (inSingle) {
        if (ch === "'") inSingle = false;
        continue;
      }
      if (inDouble) {
        if (ch === '"') inDouble = false;
        continue;
      }
      if (inBacktick) {
        if (ch === "`") {
          if (content[i + 1] === "`") {
            i += 1;
          } else {
            inBacktick = false;
          }
        }
        continue;
      }
      if (ch === "'") {
        inSingle = true;
        continue;
      }
      if (ch === '"') {
        inDouble = true;
        continue;
      }
      if (ch === "`") {
        inBacktick = true;
        continue;
      }
      if (ch === "{") return i;
    }
    return -1;
  })();

  const head = propertyStart >= 0 ? content.slice(0, propertyStart).trim() : content;
  const propertyText = propertyStart >= 0 ? content.slice(propertyStart).trim() : "";

  const parsedHead = parseNodeHeader(head);
  const parsedProps = propertyText ? parsePropertyMap(propertyText) : new Map();

  let nodeId: string;

  if (parsedHead.variable) {
    const existing = context.variableToNodeId.get(parsedHead.variable);
    if (existing) {
      nodeId = existing;
    } else {
      nodeId = parsedHead.variable;
      context.variableToNodeId.set(parsedHead.variable, nodeId);
    }
  } else {
    context.anonymousCounter += 1;
    nodeId = `anon_${String(context.anonymousCounter).padStart(6, "0")}`;
  }

  let node = context.nodesById.get(nodeId);
  if (!node) {
    node = {
      id: nodeId,
      variable: parsedHead.variable,
      labels: new Set(parsedHead.labels),
      properties: new Map(parsedProps),
      occurrences: 1,
    };
    context.nodesById.set(nodeId, node);
  } else {
    node.occurrences += 1;
    for (const label of parsedHead.labels) node.labels.add(label);
    for (const [key, value] of parsedProps) {
      if (!node.properties.has(key)) node.properties.set(key, value);
    }
  }

  return node;
}

function parseRelationshipContent(contentRaw: string): {
  type: string;
  properties: Map<string, Primitive>;
} {
  const content = contentRaw.trim();
  if (!content) return { type: "RELATED", properties: new Map() };

  let text = content;
  if (text.startsWith(":")) text = text.slice(1).trim();

  let type = "RELATED";
  let properties = new Map<string, Primitive>();

  const propStart = text.indexOf("{");
  if (propStart >= 0) {
    const head = text.slice(0, propStart).trim();
    const propText = text.slice(propStart).trim();
    if (head) {
      const token = readToken(head, 0);
      if (token?.value) type = token.value;
    }
    properties = parsePropertyMap(propText);
  } else if (text) {
    const token = readToken(text, 0);
    if (token?.value) type = token.value;
  }

  return { type, properties };
}

function parseNodeAt(
  pattern: string,
  startIndex: number,
  context: ParseContext,
): NodeParseResult {
  let i = skipWhitespace(pattern, startIndex);
  if (pattern[i] !== "(") {
    throw new Error(`Expected node '(' at pattern position ${i}: ${pattern.slice(i, i + 40)}`);
  }
  const balanced = readBalanced(pattern, i, "(", ")");
  const node = parseNodeContent(balanced.content, context);
  return {
    nodeId: node.id,
    nextIndex: balanced.endIndex + 1,
  };
}

function parseRelationshipAt(
  pattern: string,
  startIndex: number,
): RelationshipParseResult | null {
  let i = skipWhitespace(pattern, startIndex);
  if (i >= pattern.length) return null;

  if (pattern.startsWith("<-[", i)) {
    const bracketStart = i + 2;
    const balanced = readBalanced(pattern, bracketStart, "[", "]");
    const after = skipWhitespace(pattern, balanced.endIndex + 1);
    if (pattern[after] !== "-") {
      throw new Error(
        `Malformed backward relationship near: ${pattern.slice(i, Math.min(pattern.length, i + 80))}`,
      );
    }
    const parsed = parseRelationshipContent(balanced.content);
    return {
      type: parsed.type,
      properties: parsed.properties,
      direction: "backward",
      nextIndex: after + 1,
    };
  }

  if (pattern.startsWith("-[", i)) {
    const bracketStart = i + 1;
    const balanced = readBalanced(pattern, bracketStart, "[", "]");
    const after = skipWhitespace(pattern, balanced.endIndex + 1);
    if (!pattern.startsWith("->", after)) {
      throw new Error(
        `Malformed forward relationship near: ${pattern.slice(i, Math.min(pattern.length, i + 80))}`,
      );
    }
    const parsed = parseRelationshipContent(balanced.content);
    return {
      type: parsed.type,
      properties: parsed.properties,
      direction: "forward",
      nextIndex: after + 2,
    };
  }

  return null;
}

function parsePatternEntry(pattern: string, context: ParseContext): void {
  let i = 0;
  const firstNode = parseNodeAt(pattern, i, context);
  let currentNodeId = firstNode.nodeId;
  i = firstNode.nextIndex;

  while (true) {
    const relationship = parseRelationshipAt(pattern, i);
    if (!relationship) break;
    i = relationship.nextIndex;

    const nextNode = parseNodeAt(pattern, i, context);
    i = nextNode.nextIndex;

    context.relationshipCounter += 1;
    const relId = `r_${String(context.relationshipCounter).padStart(6, "0")}`;
    const from = relationship.direction === "forward" ? currentNodeId : nextNode.nodeId;
    const to = relationship.direction === "forward" ? nextNode.nodeId : currentNodeId;

    context.relationships.push({
      id: relId,
      type: relationship.type || "RELATED",
      from,
      to,
      properties: relationship.properties,
    });

    currentNodeId = nextNode.nodeId;
  }

  const tail = pattern.slice(i).trim();
  if (tail.length > 0) {
    throw new Error(`Unparsed trailing pattern segment: "${tail.slice(0, 120)}"`);
  }
}

function parseCypherCreate(cypherText: string): ParseContext {
  const body = stripCreateEnvelope(cypherText);
  const entries = splitTopLevelEntries(body);

  const context: ParseContext = {
    nodesById: new Map(),
    variableToNodeId: new Map(),
    relationships: [],
    anonymousCounter: 0,
    relationshipCounter: 0,
  };

  for (const entry of entries) {
    parsePatternEntry(entry, context);
  }

  return context;
}

function primitiveToSpectrum(value: Primitive): {
  spectrum: SpectrumValue[];
  defaultValue: SpectrumValue;
} {
  if (value === null) {
    return { spectrum: ["null"], defaultValue: "null" };
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return { spectrum: [value], defaultValue: value };
  }
  return { spectrum: [String(value)], defaultValue: String(value) };
}

function safeAttributeName(name: string): string {
  return name.replace(/\s+/g, "_");
}

function addPrimitiveAttribute(
  cb: CrystalBall,
  nodeId: string,
  name: string,
  value: Primitive,
): void {
  const converted = primitiveToSpectrum(value);
  addAttribute(cb, nodeId, safeAttributeName(name), converted.spectrum, converted.defaultValue);
}

function buildCrystalBallProjection(
  parseResult: ParseContext,
  spaceName: string,
  sourcePath: string,
): CrystalBall {
  const cb = createCrystalBall(spaceName);

  addPrimitiveAttribute(cb, "root", "projection_type", "cypher_create_projection");
  addPrimitiveAttribute(cb, "root", "source_path", sourcePath);
  addPrimitiveAttribute(cb, "root", "node_count", parseResult.nodesById.size);
  addPrimitiveAttribute(cb, "root", "relationship_count", parseResult.relationships.length);

  const nodesHub = addNode(cb, "root", "nodes");
  const relationshipsHub = addNode(cb, "root", "relationships");
  const relationshipTypesHub = addNode(cb, "root", "relationship_types");
  const labelsHub = addNode(cb, "root", "labels");
  setSlotCount(cb, "root", 4);

  const nodeIds = Array.from(parseResult.nodesById.keys()).sort();
  for (const nodeId of nodeIds) {
    const graphNode = parseResult.nodesById.get(nodeId);
    if (!graphNode) continue;

    const projected = addNode(cb, nodesHub.id, graphNode.id);
    addPrimitiveAttribute(cb, projected.id, "graph_id", graphNode.id);
    addPrimitiveAttribute(cb, projected.id, "kind", graphNode.variable ? "variable" : "anonymous");
    addPrimitiveAttribute(cb, projected.id, "occurrences", graphNode.occurrences);

    if (graphNode.variable) {
      addPrimitiveAttribute(cb, projected.id, "variable", graphNode.variable);
    }

    const labels = Array.from(graphNode.labels).sort();
    if (labels.length > 0) {
      addAttribute(cb, projected.id, "labels", labels, labels[0]);
      addPrimitiveAttribute(cb, projected.id, "primary_label", labels[0]);
    }

    for (const [key, value] of Array.from(graphNode.properties.entries()).sort(([a], [b]) =>
      a.localeCompare(b),
    )) {
      addPrimitiveAttribute(cb, projected.id, `prop_${key}`, value);
    }
  }
  setSlotCount(cb, nodesHub.id, nodeIds.length);

  const relTypeCounts = new Map<string, number>();
  for (const rel of parseResult.relationships) {
    relTypeCounts.set(rel.type, (relTypeCounts.get(rel.type) ?? 0) + 1);

    const projected = addNode(cb, relationshipsHub.id, rel.id);
    addPrimitiveAttribute(cb, projected.id, "edge_id", rel.id);
    addPrimitiveAttribute(cb, projected.id, "type", rel.type);
    addPrimitiveAttribute(cb, projected.id, "from", rel.from);
    addPrimitiveAttribute(cb, projected.id, "to", rel.to);

    for (const [key, value] of Array.from(rel.properties.entries()).sort(([a], [b]) =>
      a.localeCompare(b),
    )) {
      addPrimitiveAttribute(cb, projected.id, `prop_${key}`, value);
    }
  }
  setSlotCount(cb, relationshipsHub.id, parseResult.relationships.length);

  const relTypes = Array.from(relTypeCounts.entries()).sort(([a], [b]) => a.localeCompare(b));
  for (const [type, count] of relTypes) {
    const projected = addNode(cb, relationshipTypesHub.id, type);
    addPrimitiveAttribute(cb, projected.id, "type", type);
    addPrimitiveAttribute(cb, projected.id, "count", count);
  }
  setSlotCount(cb, relationshipTypesHub.id, relTypes.length);

  const labelCounts = new Map<string, number>();
  for (const node of parseResult.nodesById.values()) {
    for (const label of node.labels) {
      labelCounts.set(label, (labelCounts.get(label) ?? 0) + 1);
    }
  }

  const labelRows = Array.from(labelCounts.entries()).sort(([a], [b]) => a.localeCompare(b));
  for (const [label, count] of labelRows) {
    const projected = addNode(cb, labelsHub.id, label);
    addPrimitiveAttribute(cb, projected.id, "label", label);
    addPrimitiveAttribute(cb, projected.id, "count", count);
  }
  setSlotCount(cb, labelsHub.id, labelRows.length);

  return cb;
}

function ensureParentDirectory(filePath: string): void {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
}

function run(): void {
  const options = parseArgs(process.argv.slice(2));
  const cypherText = fs.readFileSync(options.inputPath, "utf8");
  const parsed = parseCypherCreate(cypherText);
  const projection = buildCrystalBallProjection(parsed, options.spaceName, options.inputPath);

  ensureParentDirectory(options.outputPath);
  fs.writeFileSync(options.outputPath, toJSON(projection), "utf8");

  const anonymousNodeCount = Array.from(parsed.nodesById.values()).filter(
    (node) => !node.variable,
  ).length;

  console.log(`Wrote Crystal Ball projection to: ${options.outputPath}`);
  console.log(`Space name: ${projection.name}`);
  console.log(`Nodes: ${parsed.nodesById.size} (${anonymousNodeCount} anonymous)`);
  console.log(`Relationships: ${parsed.relationships.length}`);
  console.log(`Relationship types: ${new Set(parsed.relationships.map((r) => r.type)).size}`);
}

run();

