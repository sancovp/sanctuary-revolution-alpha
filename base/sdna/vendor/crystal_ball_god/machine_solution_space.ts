import {
  CrystalBall,
  OntologyNode,
  addAttribute,
  addNode,
  attachSubspace,
  createCrystalBall,
  createTotalSpace,
  dump,
  neighbors,
  resolveCoordinate,
  setSlotCount,
} from "./src/index";

type HueSeed = {
  name: string;
  hueDeg: number;
};

type InvariantReport = {
  ok: boolean;
  typedPointCount: number;
  totalPointCount: number;
  transitionCount: number;
  policyCount: number;
  observerCount: number;
  missing: string[];
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

const REQUIRED_HUE_KEYS = [
  "type",
  "family",
  "hue_deg",
  "saturation_pct",
  "lightness_pct",
  "hsl",
  "hex",
];

const REQUIRED_MACHINE_POINT_KEYS = [
  "type",
  "iteration",
  "digest",
  "invariant_ok",
  "typed_point_count",
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

function isHuePointFullyTyped(point: OntologyNode): boolean {
  for (const key of REQUIRED_HUE_KEYS) {
    const attr = point.attributes.get(key);
    if (!attr || attr.defaultValue === undefined) {
      return false;
    }
  }
  return true;
}

function findChildByLabel(space: CrystalBall, parentId: string, label: string): OntologyNode | undefined {
  const parent = space.nodes.get(parentId);
  if (!parent) {
    return undefined;
  }
  for (const childId of parent.children) {
    const child = space.nodes.get(childId);
    if (child && child.label === label) {
      return child;
    }
  }
  return undefined;
}

function collectHuePoints(hueSpace: CrystalBall): OntologyNode[] {
  const pointsNode = findChildByLabel(hueSpace, "root", "points");
  if (!pointsNode) {
    return [];
  }
  const points: OntologyNode[] = [];
  for (const childId of pointsNode.children) {
    const child = hueSpace.nodes.get(childId);
    if (child) {
      points.push(child);
    }
  }
  return points;
}

function createTransitionSpace(name: string, from: string, to: string): CrystalBall {
  const transition = createCrystalBall(`transition:${name}`);
  addAttribute(transition, "root", "type", ["transition"], "transition");
  addAttribute(transition, "root", "name", [name], name);
  addAttribute(transition, "root", "from", [from], from);
  addAttribute(transition, "root", "to", [to], to);
  setSlotCount(transition, "root", 1);
  return transition;
}

function createPolicySpace(name: string, transitionNames: string[], maxDepth: number): CrystalBall {
  const policy = createCrystalBall(`policy:${name}`);
  addAttribute(policy, "root", "type", ["policy"], "policy");
  addAttribute(policy, "root", "name", [name], name);
  addAttribute(policy, "root", "max_depth", [maxDepth], maxDepth);
  addAttribute(policy, "root", "transitions", transitionNames, transitionNames[0] ?? "");
  setSlotCount(policy, "root", 1);
  return policy;
}

function createObserverSpace(name: string, level: number): CrystalBall {
  const observer = createCrystalBall(`observer:${name}`);
  addAttribute(observer, "root", "type", ["observer"], "observer");
  addAttribute(observer, "root", "name", [name], name);
  addAttribute(observer, "root", "level", [level], level);
  setSlotCount(observer, "root", 1);
  return observer;
}

function observeAttributesSimple(space: CrystalBall): CrystalBall {
  const observation = createCrystalBall(`obs:attributes:${space.name}`);
  let attributeCount = 0;
  for (const [, node] of space.nodes) {
    attributeCount += node.attributes.size;
  }
  addAttribute(observation, "root", "type", ["attribute_observation"], "attribute_observation");
  addAttribute(observation, "root", "subject", [space.name], space.name);
  addAttribute(observation, "root", "node_count", [space.nodes.size], space.nodes.size);
  addAttribute(observation, "root", "attribute_count", [attributeCount], attributeCount);
  setSlotCount(observation, "root", 1);
  return observation;
}

function observeReachabilitySimple(space: CrystalBall): CrystalBall {
  const observation = createCrystalBall(`obs:reach:${space.name}`);
  const near = neighbors(space, "root", { k: 8, strict: false, includeSubspaces: true, depth: 3 });
  addAttribute(observation, "root", "type", ["reachability_observation"], "reachability_observation");
  addAttribute(observation, "root", "subject", [space.name], space.name);
  addAttribute(observation, "root", "neighbor_count", [near.length], near.length);
  setSlotCount(observation, "root", 1);
  return observation;
}

function buildMachineSpace(hueSpace: CrystalBall): CrystalBall {
  const transition = createTransitionSpace("hue_step", "1.1", "1.2");
  const policy = createPolicySpace("hue_policy", ["hue_step"], 4);
  const observer1 = createObserverSpace("attributeObserver", 1);
  const observer2 = createObserverSpace("metaObserver", 2);

  const machine = createTotalSpace(
    [hueSpace],
    [transition],
    [policy],
    [observer1, observer2],
    { HueSolutionSpace: hueSpace },
  );

  const machineMeta = addNode(machine, "root", "machine_meta");
  addAttribute(machine, machineMeta.id, "machine_type", ["recursive_observer"], "recursive_observer");
  addAttribute(machine, machineMeta.id, "state_semantics", ["typed_solution_space_search"], "typed_solution_space_search");
  return machine;
}

function machineInvariant(machine: CrystalBall, hueSpace: CrystalBall): InvariantReport {
  const missing: string[] = [];

  const huePoints = collectHuePoints(hueSpace);
  const typedPointCount = huePoints.filter(isHuePointFullyTyped).length;

  const transitionsNode = findChildByLabel(machine, "root", "transitions");
  const policiesNode = findChildByLabel(machine, "root", "policies");
  const observersNode = findChildByLabel(machine, "root", "observers");

  const transitionCount = transitionsNode ? transitionsNode.children.length : 0;
  const policyCount = policiesNode ? policiesNode.children.length : 0;
  const observerCount = observersNode ? observersNode.children.length : 0;

  if (huePoints.length === 0) {
    missing.push("no hue points");
  }
  if (typedPointCount !== huePoints.length) {
    missing.push("hue points not fully typed");
  }
  if (transitionCount === 0) {
    missing.push("no transitions");
  }
  if (policyCount === 0) {
    missing.push("no policies");
  }
  if (observerCount === 0) {
    missing.push("no observers");
  }

  return {
    ok: missing.length === 0,
    typedPointCount,
    totalPointCount: huePoints.length,
    transitionCount,
    policyCount,
    observerCount,
    missing,
  };
}

function digestInvariant(report: InvariantReport): string {
  return [
    `ok=${report.ok}`,
    `typed=${report.typedPointCount}/${report.totalPointCount}`,
    `t=${report.transitionCount}`,
    `p=${report.policyCount}`,
    `o=${report.observerCount}`,
    `missing=${report.missing.join("|") || "-"}`,
  ].join(";");
}

function getOrCreateObservationLog(machine: CrystalBall): OntologyNode {
  const existing = findChildByLabel(machine, "root", "machine_observations");
  if (existing) {
    return existing;
  }
  const created = addNode(machine, "root", "machine_observations");
  return created;
}

function integrateObservation(machine: CrystalBall, iteration: number, observation: CrystalBall): void {
  const logNode = getOrCreateObservationLog(machine);
  const iterNode = addNode(machine, logNode.id, `iter_${iteration}`);
  addAttribute(machine, iterNode.id, "type", ["MachineObservationPoint"], "MachineObservationPoint");
  addAttribute(machine, iterNode.id, "iteration", [iteration], iteration);
  attachSubspace(machine, iterNode.id, observation);
  setSlotCount(machine, logNode.id, logNode.children.length);
}

function createMachineStateObservation(
  iteration: number,
  digest: string,
  report: InvariantReport,
  attrObs: CrystalBall,
  reachObs: CrystalBall,
): CrystalBall {
  const observation = createCrystalBall(`MachineStateObs_${iteration}`);
  addAttribute(observation, "root", "type", ["MachineStateObservation"], "MachineStateObservation");
  addAttribute(observation, "root", "iteration", [iteration], iteration);
  addAttribute(observation, "root", "digest", [digest], digest);
  addAttribute(observation, "root", "invariant_ok", [report.ok], report.ok);
  addAttribute(observation, "root", "typed_points", [report.typedPointCount], report.typedPointCount);
  addAttribute(observation, "root", "total_points", [report.totalPointCount], report.totalPointCount);

  const attrsNode = addNode(observation, "root", "attribute_observation");
  const reachNode = addNode(observation, "root", "reachability_observation");
  attachSubspace(observation, attrsNode.id, attrObs);
  attachSubspace(observation, reachNode.id, reachObs);

  setSlotCount(observation, "root", 2);
  return observation;
}

function buildMachineSolutionSpace(): {
  machine: CrystalBall;
  solution: CrystalBall;
  fixedAt: number;
  digests: string[];
} {
  const { space: hueSpace } = buildHueSolutionSpace();
  const machine = buildMachineSpace(hueSpace);

  const solution = createCrystalBall("MachineSolutionSpace");
  addAttribute(solution, "root", "space_type", ["machine_solution_space"], "machine_solution_space");
  addAttribute(solution, "root", "point_type", ["MachineStatePoint"], "MachineStatePoint");
  const pointsNode = addNode(solution, "root", "points");
  setSlotCount(solution, "root", 1);

  const seenDigests = new Set<string>();
  const digests: string[] = [];
  let fixedAt = -1;
  const maxIterations = 8;

  for (let iteration = 0; iteration < maxIterations; iteration++) {
    const report = machineInvariant(machine, hueSpace);
    const digest = digestInvariant(report);
    digests.push(digest);

    const attrObs = observeAttributesSimple(machine);
    const reachObs = observeReachabilitySimple(machine);
    const stateObservation = createMachineStateObservation(iteration, digest, report, attrObs, reachObs);
    integrateObservation(machine, iteration, stateObservation);

    if (report.ok) {
      const point = addNode(solution, pointsNode.id, `state_${iteration}`);
      addAttribute(solution, point.id, "type", ["MachineStatePoint"], "MachineStatePoint");
      addAttribute(solution, point.id, "iteration", [iteration], iteration);
      addAttribute(solution, point.id, "digest", [digest], digest);
      addAttribute(solution, point.id, "invariant_ok", [true], true);
      addAttribute(solution, point.id, "typed_point_count", [report.typedPointCount], report.typedPointCount);
      addAttribute(solution, point.id, "total_point_count", [report.totalPointCount], report.totalPointCount);
      attachSubspace(solution, point.id, stateObservation);
    }

    setSlotCount(solution, pointsNode.id, pointsNode.children.length);

    if (seenDigests.has(digest)) {
      fixedAt = iteration;
      break;
    }
    seenDigests.add(digest);
  }

  return { machine, solution, fixedAt, digests };
}

function verifyMachineSolutionPoints(solution: CrystalBall): {
  ok: boolean;
  missing: string[];
} {
  const pointsNode = findChildByLabel(solution, "root", "points");
  if (!pointsNode) {
    return { ok: false, missing: ["points node missing"] };
  }

  const missing: string[] = [];
  for (const pointId of pointsNode.children) {
    const point = solution.nodes.get(pointId);
    if (!point) {
      missing.push(`${pointId}: node missing`);
      continue;
    }
    for (const key of REQUIRED_MACHINE_POINT_KEYS) {
      const attr = point.attributes.get(key);
      if (!attr || attr.defaultValue === undefined) {
        missing.push(`${point.label}: missing ${key}`);
      }
    }
  }
  return { ok: missing.length === 0, missing };
}

function main(): void {
  const { machine, solution, fixedAt, digests } = buildMachineSolutionSpace();
  const verify = verifyMachineSolutionPoints(solution);

  console.log("=== RECURSIVE MACHINE SPACE ===");
  console.log(`Machine: ${machine.name}`);
  console.log(`Fixed point reached: ${fixedAt >= 0 ? `YES @ iteration ${fixedAt}` : "NO (max iteration hit)"}`);
  console.log("Digest trace:");
  digests.forEach((d, i) => console.log(`- i=${i}: ${d}`));

  console.log("\n=== MACHINE SOLUTION SPACE ===");
  console.log(`Name: ${solution.name}`);
  const pointsNode = findChildByLabel(solution, "root", "points");
  console.log(`Point count: ${pointsNode ? pointsNode.children.length : 0}`);
  console.log(`Every solution point fully typed: ${verify.ok ? "YES" : "NO"}`);
  if (!verify.ok) {
    verify.missing.forEach(m => console.log(`- ${m}`));
  }

  console.log("\nCoordinate sample on MachineSolutionSpace:");
  const sample = resolveCoordinate(solution, "1.1");
  if (sample.length === 0) {
    console.log("- 1.1: (no point)");
  } else {
    const labels = sample.map(node => node.label).join(", ");
    console.log(`- 1.1: ${labels}`);
  }

  console.log("\nSolution structure:");
  console.log(dump(solution));
}

main();
