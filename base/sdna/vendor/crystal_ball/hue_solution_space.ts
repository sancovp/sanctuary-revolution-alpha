import {
  CrystalBall,
  OntologyNode,
  addAttribute,
  addNode,
  createCrystalBall,
  resolveCoordinate,
  setSlotCount,
  dump,
} from "./src/index";

type HueSeed = {
  name: string;
  hueDeg: number;
};

const HUE_SEEDS: HueSeed[] = [
  { name: "Red", hueDeg: 0 },
  { name: "Orange", hueDeg: 30 },
  { name: "Yellow", hueDeg: 60 },
  { name: "Chartreuse", hueDeg: 90 },
  { name: "Green", hueDeg: 120 },
  { name: "SpringGreen", hueDeg: 150 },
  { name: "Cyan", hueDeg: 180 },
  { name: "Azure", hueDeg: 210 },
  { name: "Blue", hueDeg: 240 },
  { name: "Violet", hueDeg: 270 },
  { name: "Magenta", hueDeg: 300 },
  { name: "Rose", hueDeg: 330 },
];

const REQUIRED_TYPE_KEYS = [
  "type",
  "family",
  "hue_deg",
  "saturation_pct",
  "lightness_pct",
  "hsl",
  "hex",
];

function hslToHex(h: number, s: number, l: number): string {
  const hh = ((h % 360) + 360) % 360;
  const ss = s / 100;
  const ll = l / 100;

  const c = (1 - Math.abs(2 * ll - 1)) * ss;
  const x = c * (1 - Math.abs(((hh / 60) % 2) - 1));
  const m = ll - c / 2;

  let r = 0;
  let g = 0;
  let b = 0;

  if (hh < 60) {
    r = c;
    g = x;
  } else if (hh < 120) {
    r = x;
    g = c;
  } else if (hh < 180) {
    g = c;
    b = x;
  } else if (hh < 240) {
    g = x;
    b = c;
  } else if (hh < 300) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }

  const toHex = (v: number): string => {
    const n = Math.round((v + m) * 255);
    return n.toString(16).padStart(2, "0");
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function buildHueSolutionSpace(): {
  space: CrystalBall;
  pointsNode: OntologyNode;
} {
  const space = createCrystalBall("HueSolutionSpace");
  addAttribute(space, "root", "space_type", ["solution_space"], "solution_space");
  addAttribute(space, "root", "point_type", ["HuePoint"], "HuePoint");

  const pointsNode = addNode(space, "root", "points");
  setSlotCount(space, "root", 1);
  setSlotCount(space, pointsNode.id, HUE_SEEDS.length);

  for (const seed of HUE_SEEDS) {
    const point = addNode(space, pointsNode.id, seed.name);
    const h = seed.hueDeg;
    const s = 100;
    const l = 50;
    const hsl = `hsl(${h}, ${s}%, ${l}%)`;
    const hex = hslToHex(h, s, l);

    addAttribute(space, point.id, "type", ["HuePoint"], "HuePoint");
    addAttribute(space, point.id, "family", [seed.name], seed.name);
    addAttribute(space, point.id, "hue_deg", [h], h);
    addAttribute(space, point.id, "saturation_pct", [s], s);
    addAttribute(space, point.id, "lightness_pct", [l], l);
    addAttribute(space, point.id, "hsl", [hsl], hsl);
    addAttribute(space, point.id, "hex", [hex], hex);
  }

  return { space, pointsNode };
}

function verifyFullyTyped(space: CrystalBall, pointsNode: OntologyNode): {
  ok: boolean;
  violations: string[];
} {
  const violations: string[] = [];

  for (const pointId of pointsNode.children) {
    const point = space.nodes.get(pointId);
    if (!point) {
      violations.push(`${pointId}: missing node`);
      continue;
    }

    for (const key of REQUIRED_TYPE_KEYS) {
      const attr = point.attributes.get(key);
      if (!attr) {
        violations.push(`${point.label}: missing ${key}`);
        continue;
      }
      if (attr.defaultValue === undefined) {
        violations.push(`${point.label}: ${key} has no default`);
      }
    }
  }

  return { ok: violations.length === 0, violations };
}

function demoCoordinates(space: CrystalBall): string[] {
  // root slot 1 -> points node, then 1..12 pick hue points
  const coords = ["1.1", "1.4", "1.8", "1.12"];
  const lines: string[] = [];

  for (const coord of coords) {
    const resolved = resolveCoordinate(space, coord);
    if (resolved.length === 0) {
      lines.push(`${coord}: (no result)`);
      continue;
    }
    const labels = resolved.map(node => {
      const hue = node.attributes.get("hue_deg")?.defaultValue;
      const hex = node.attributes.get("hex")?.defaultValue;
      return `${node.label}[h=${hue}, hex=${hex}]`;
    });
    lines.push(`${coord}: ${labels.join(", ")}`);
  }

  return lines;
}

function main(): void {
  const { space, pointsNode } = buildHueSolutionSpace();
  const check = verifyFullyTyped(space, pointsNode);

  console.log("=== HUE SOLUTION SPACE ===");
  console.log(`Name: ${space.name}`);
  console.log(`Point count: ${pointsNode.children.length}`);
  console.log(`Fully typed: ${check.ok ? "YES" : "NO"}`);

  if (!check.ok) {
    console.log("Violations:");
    for (const v of check.violations) {
      console.log(`- ${v}`);
    }
  }

  console.log("\nCoordinate samples:");
  for (const line of demoCoordinates(space)) {
    console.log(`- ${line}`);
  }

  console.log("\nStructure:");
  console.log(dump(space));
}

main();
