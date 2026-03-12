#!/usr/bin/env -S npx tsx

import * as fs from "node:fs";
import * as path from "node:path";
import {
  addAttribute,
  addNode,
  createRegistry,
  fromJSON,
  setSlotCount,
  toJSON,
  type CrystalBall,
  type OntologyNode,
  type SpectrumValue,
} from "../src/index";

interface CliOptions {
  inputPath: string;
  outputPath: string;
}

interface EnrichSummary {
  totalProjectedNodes: number;
  characterNodes: number;
  sceneNodes: number;
  syntaxNodes: number;
  genreNodes: number;
  attributesAdded: number;
  backlogItemsAdded: number;
}

type OptionBundle = Record<string, string[]>;

const CHARACTER_OPTIONS: OptionBundle = {
  option_character_function: [
    "Protagonist",
    "Influence Character",
    "Antagonist",
    "Ally",
    "Mentor",
    "Shadow",
    "Trickster",
    "Guardian",
    "Lover",
    "Skeptic",
    "Foil",
    "Witness",
  ],
  option_identity_state: [
    "Lie-Dominant",
    "Mask-Cracked",
    "Wound-Exposed",
    "Testing-Truth",
    "False-Sword",
    "Sword-Seized",
    "Integrated-Essence",
  ],
  option_need_domain: [
    "Belonging",
    "Autonomy",
    "Competence",
    "Safety",
    "Justice",
    "Recognition",
    "Meaning",
    "Love",
    "Power",
    "Repair",
  ],
  option_conflict_source: [
    "Internal Contradiction",
    "Interpersonal Clash",
    "Systemic Pressure",
    "Resource Scarcity",
    "Moral Ambiguity",
    "Time Compression",
  ],
  option_attachment_pattern: [
    "Secure",
    "Anxious",
    "Avoidant",
    "Disorganized",
  ],
  option_voice_register: [
    "Direct",
    "Deflective",
    "Ironic",
    "Formal",
    "Colloquial",
    "Poetic",
    "Procedural",
  ],
  option_change_outcome: [
    "Growth",
    "Stasis",
    "Corruption",
    "Sacrifice",
    "Reconciliation",
    "Tragic-Fall",
  ],
};

const SCENE_OPTIONS: OptionBundle = {
  option_scene_intent: [
    "Contextualization",
    "Desire Articulation",
    "Pressure Test",
    "Reversal",
    "Reveal",
    "Decision Lock",
    "Transition Setup",
  ],
  option_scene_obstacle: [
    "Social Friction",
    "Physical Barrier",
    "Information Gap",
    "Moral Cost",
    "Time Pressure",
    "Emotional Trigger",
  ],
  option_scene_outcome: [
    "Clean Win",
    "Compromised Win",
    "Costly Loss",
    "Stalemate",
    "Pyrrhic Win",
    "Ambiguous Shift",
  ],
  option_transition_mode: [
    "Escalation",
    "Deflation",
    "Complication",
    "Clarification",
    "Misdirection",
    "Convergence",
  ],
  option_scene_energy: [
    "Stillness",
    "Tension Build",
    "Burst",
    "Spiral",
    "Release",
  ],
};

const SYNTAX_OPTIONS: OptionBundle = {
  option_line_function: [
    "Exposition",
    "Characterization",
    "Subtext",
    "Action Cue",
    "Theme Signal",
    "Setup",
    "Payoff",
  ],
  option_dialogue_force: [
    "Declarative",
    "Interrogative",
    "Imperative",
    "Exclamative",
  ],
  option_subtext_density: [
    "Low",
    "Medium",
    "High",
    "Opaque",
  ],
  option_visual_density: [
    "Minimal",
    "Balanced",
    "Lush",
    "Operatic",
  ],
  option_semantic_mode: [
    "Literal",
    "Metaphoric",
    "Ironic",
    "Symbolic",
    "Allegorical",
  ],
};

const GENRE_OPTIONS: OptionBundle = {
  option_primary_genre: [
    "Myth",
    "Horror",
    "Western",
    "Detective",
    "Thriller",
    "Police Story",
    "Action",
    "Drama/Melodrama",
    "Comedy",
    "Love Story",
    "Historical Drama",
    "Fantasy",
    "Science Fiction",
  ],
  option_secondary_genre: [
    "None",
    "Buddy",
    "Crime",
    "Gangster",
    "Romance",
    "Punk",
    "Opera",
    "Speculative",
  ],
  option_trope_expression: [
    "Literal",
    "Inverted",
    "Subverted",
    "Compressed",
    "Deferred",
    "Layered",
  ],
  option_catharsis_target: [
    "Awe",
    "Terror",
    "Relief",
    "Justice",
    "Recognition",
    "Bittersweet",
  ],
  option_audience_lens: [
    "Personal",
    "Relational",
    "Societal",
    "Metaphysical",
    "Institutional",
  ],
};

const CHARACTER_KEYWORDS = [
  "character",
  "archetype",
  "protagonist",
  "antagonist",
  "mentor",
  "ally",
  "shadow",
  "trickster",
  "romance",
  "influence character",
  "worldview",
  "lie",
  "wound",
  "ghost",
  "need",
  "want",
  "hero",
];

const SCENE_KEYWORDS = [
  "scene",
  "hgs",
  "fresh news",
  "sequence",
  "act",
  "climax",
  "midpoint",
  "finale",
  "denou",
  "bridging",
];

const SYNTAX_KEYWORDS = [
  "syntax",
  "grammar",
  "sentence",
  "dialogue",
  "action line",
  "semantics",
  "declarative",
  "interrogative",
  "imperative",
  "exclamative",
  "slugline",
];

const GENRE_KEYWORDS = [
  "genre",
  "myth",
  "horror",
  "western",
  "detective",
  "thriller",
  "police story",
  "action",
  "drama",
  "melodrama",
  "comedy",
  "love",
  "historical",
  "fantasy",
  "science fiction",
  "sci-fi",
  "crime",
  "gangster",
  "subgenre",
];

function parseArgs(argv: string[]): CliOptions {
  const args = [...argv];
  let inputPath = "";
  let outputPath = "";

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
    : path.join(path.dirname(absInput), `${base}.enriched.cb.json`);

  return { inputPath: absInput, outputPath: absOutput };
}

function printUsageAndExit(code: number): never {
  console.log(
    [
      "Usage:",
      "  npx tsx scripts/enrich_story_machine_cb.ts --input <path/to/story_graph.cb.json> [--output <path/to/out.enriched.cb.json>]",
      "",
      "Example:",
      "  npx tsx scripts/enrich_story_machine_cb.ts --input /Users/isaacwr/Documents/story_machine/story_graph.cb.json",
    ].join("\n"),
  );
  process.exit(code);
}

function ensureParentDirectory(filePath: string): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function getNode(cb: CrystalBall, nodeId: string): OntologyNode {
  const node = cb.nodes.get(nodeId);
  if (!node) {
    throw new Error(`Node not found: ${nodeId}`);
  }
  return node;
}

function findChildByLabel(
  cb: CrystalBall,
  parentId: string,
  label: string,
): OntologyNode | null {
  const parent = getNode(cb, parentId);
  for (const childId of parent.children) {
    const child = cb.nodes.get(childId);
    if (child && child.label === label) return child;
  }
  return null;
}

function ensureChild(
  cb: CrystalBall,
  parentId: string,
  label: string,
): OntologyNode {
  const existing = findChildByLabel(cb, parentId, label);
  if (existing) return existing;
  const created = addNode(cb, parentId, label);
  const parent = getNode(cb, parentId);
  setSlotCount(cb, parentId, parent.children.length);
  return created;
}

function getStringSpectrum(node: OntologyNode, attrName: string): string[] {
  const attr = node.attributes.get(attrName);
  if (!attr) return [];
  return attr.spectrum.map((v) => String(v));
}

function getDefaultString(node: OntologyNode, attrName: string): string {
  const attr = node.attributes.get(attrName);
  if (!attr || attr.defaultValue === undefined) return "";
  return String(attr.defaultValue);
}

function containsAnyKeyword(haystack: string, keywords: string[]): boolean {
  const lower = haystack.toLowerCase();
  return keywords.some((k) => lower.includes(k));
}

function upsertAttribute(
  cb: CrystalBall,
  nodeId: string,
  name: string,
  incomingValues: SpectrumValue[],
  preferredDefault?: SpectrumValue,
): boolean {
  const node = getNode(cb, nodeId);
  const existing = node.attributes.get(name);

  if (!existing) {
    const defaultValue =
      preferredDefault !== undefined ? preferredDefault : incomingValues[0];
    addAttribute(cb, nodeId, name, incomingValues, defaultValue);
    return true;
  }

  const merged = [...existing.spectrum];
  for (const value of incomingValues) {
    if (!merged.includes(value)) merged.push(value);
  }

  const defaultValue =
    existing.defaultValue !== undefined
      ? existing.defaultValue
      : preferredDefault !== undefined
        ? preferredDefault
        : merged[0];

  addAttribute(cb, nodeId, name, merged, defaultValue);
  return merged.length > existing.spectrum.length;
}

function applyBundle(
  cb: CrystalBall,
  nodeId: string,
  bundle: OptionBundle,
): number {
  let additions = 0;
  for (const [name, values] of Object.entries(bundle)) {
    const changed = upsertAttribute(cb, nodeId, name, values, values[0]);
    if (changed) additions += 1;
  }
  return additions;
}

function buildBacklogLayers(cb: CrystalBall): number {
  const expansionHub = ensureChild(cb, "root", "expansion_layers");
  let added = 0;

  const characterLayer = ensureChild(cb, expansionHub.id, "character_layer_backlog");
  const psychLayer = ensureChild(cb, expansionHub.id, "psychodynamics_layer_backlog");
  const syntaxLayer = ensureChild(cb, expansionHub.id, "syntax_layer_backlog");
  const genreLayer = ensureChild(cb, expansionHub.id, "genre_layer_backlog");

  const characterItems = [
    "Character Type Matrix",
    "Archetype Relationship Web",
    "Need vs Want Catalog",
    "Lie/Truth Variation Set",
    "Wound/Shield Taxonomy",
    "Voice & Idiolect Matrix",
    "Relational Tension Tracks",
    "Transformation Proof Patterns",
  ];

  const psychItems = [
    "Attachment Dynamics Grid",
    "Defense Mechanism Map",
    "Values Hierarchy Spectrum",
    "Identity Fragmentation States",
    "Belief Revision Triggers",
  ];

  const syntaxItems = [
    "Slugline Pattern Set",
    "Action-Line Density Variants",
    "Dialogue Subtext Modes",
    "Sentence Function Distribution",
    "Illustration vs Highlighting Tuning",
  ];

  const genreItems = [
    "Truby13 x HJ Stage Mapping",
    "Genre Fractal Chain Rules",
    "Trope-to-Symbol Library",
    "Catharsis Target Matrix",
    "Myth Throughline Constraints",
  ];

  const addBacklogItems = (parentId: string, items: string[], lane: string): number => {
    let local = 0;
    for (const item of items) {
      const node = ensureChild(cb, parentId, item);
      const changed1 = upsertAttribute(cb, node.id, "status", ["backlog", "in_progress", "done"], "backlog");
      const changed2 = upsertAttribute(cb, node.id, "lane", [lane], lane);
      const changed3 = upsertAttribute(cb, node.id, "priority", ["P0", "P1", "P2"], "P1");
      const changed4 = upsertAttribute(cb, node.id, "owner", ["story_machine"], "story_machine");
      if (changed1 || changed2 || changed3 || changed4) local += 1;
    }
    const parent = getNode(cb, parentId);
    setSlotCount(cb, parentId, parent.children.length);
    return local;
  };

  added += addBacklogItems(characterLayer.id, characterItems, "character");
  added += addBacklogItems(psychLayer.id, psychItems, "psychodynamics");
  added += addBacklogItems(syntaxLayer.id, syntaxItems, "syntax");
  added += addBacklogItems(genreLayer.id, genreItems, "genre");
  const expansion = getNode(cb, expansionHub.id);
  setSlotCount(cb, expansionHub.id, expansion.children.length);
  return added;
}

function enrichProjectedNodes(cb: CrystalBall): EnrichSummary {
  const root = getNode(cb, "root");
  const nodesHub = findChildByLabel(cb, root.id, "nodes");
  if (!nodesHub) {
    throw new Error("Projection hub 'nodes' not found under root.");
  }

  let characterNodes = 0;
  let sceneNodes = 0;
  let syntaxNodes = 0;
  let genreNodes = 0;
  let attributesAdded = 0;

  for (const projectedId of nodesHub.children) {
    const projected = cb.nodes.get(projectedId);
    if (!projected) continue;

    const primaryLabel = getDefaultString(projected, "primary_label");
    const labels = getStringSpectrum(projected, "labels");
    const raw = [projected.label, primaryLabel, ...labels].join(" | ");

    const isCharacter = containsAnyKeyword(raw, CHARACTER_KEYWORDS);
    const isScene = containsAnyKeyword(raw, SCENE_KEYWORDS);
    const isSyntax = containsAnyKeyword(raw, SYNTAX_KEYWORDS);
    const isGenre = containsAnyKeyword(raw, GENRE_KEYWORDS);

    if (isCharacter) {
      characterNodes += 1;
      attributesAdded += applyBundle(cb, projected.id, CHARACTER_OPTIONS);
    }
    if (isScene) {
      sceneNodes += 1;
      attributesAdded += applyBundle(cb, projected.id, SCENE_OPTIONS);
    }
    if (isSyntax) {
      syntaxNodes += 1;
      attributesAdded += applyBundle(cb, projected.id, SYNTAX_OPTIONS);
    }
    if (isGenre) {
      genreNodes += 1;
      attributesAdded += applyBundle(cb, projected.id, GENRE_OPTIONS);
    }
  }

  const backlogItemsAdded = buildBacklogLayers(cb);

  return {
    totalProjectedNodes: nodesHub.children.length,
    characterNodes,
    sceneNodes,
    syntaxNodes,
    genreNodes,
    attributesAdded,
    backlogItemsAdded,
  };
}

function run(): void {
  const options = parseArgs(process.argv.slice(2));
  const raw = fs.readFileSync(options.inputPath, "utf8");

  const registry = createRegistry();
  const cb = fromJSON(raw, registry);
  const summary = enrichProjectedNodes(cb);

  ensureParentDirectory(options.outputPath);
  fs.writeFileSync(options.outputPath, toJSON(cb), "utf8");

  console.log(`Wrote enriched Crystal Ball space: ${options.outputPath}`);
  console.log(`Projected nodes scanned: ${summary.totalProjectedNodes}`);
  console.log(`Character-class nodes enriched: ${summary.characterNodes}`);
  console.log(`Scene-class nodes enriched: ${summary.sceneNodes}`);
  console.log(`Syntax-class nodes enriched: ${summary.syntaxNodes}`);
  console.log(`Genre-class nodes enriched: ${summary.genreNodes}`);
  console.log(`Option attributes added/expanded: ${summary.attributesAdded}`);
  console.log(`Backlog items added: ${summary.backlogItemsAdded}`);
}

run();

