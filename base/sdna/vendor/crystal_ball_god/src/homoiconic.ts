// Homoiconic Crystal Ball - TIGHTENED
// All outputs are Spaces. No JS leakage.

declare const process: any;

import {
  CrystalBall,
  OntologyNode,
  NodeId,
  SpectrumValue,
  Spectrum,
  createCrystalBall,
  addNode,
  addAttribute,
  setSlotCount,
  lockNode,
  attachSubspace,
  resolveCoordinate,
  createRegistry,
  registerSpace,
  toJSON,
  Attribute,
  SerializedCrystalBall,
  deserialize
} from './index';

// ============================================================
// PART 1: SPACE-AS-TERM - Everything returns Space
// ============================================================

// Primitives - all return CrystalBall
export function spaceString(value: string): CrystalBall {
  const sb = createCrystalBall(`"${value}"`);
  addAttribute(sb, 'root', 'type', ['string']);
  addAttribute(sb, 'root', 'value', [value], value);
  setSlotCount(sb, 'root', 1);
  lockNode(sb, 'root');
  return sb;
}

export function spaceNumber(value: number): CrystalBall {
  const sb = createCrystalBall(String(value));
  addAttribute(sb, 'root', 'type', ['number']);
  addAttribute(sb, 'root', 'value', [value], value);
  setSlotCount(sb, 'root', 1);
  lockNode(sb, 'root');
  return sb;
}

export function spaceBoolean(value: boolean): CrystalBall {
  const sb = createCrystalBall(String(value));
  addAttribute(sb, 'root', 'type', ['boolean']);
  addAttribute(sb, 'root', 'value', [value], value);
  setSlotCount(sb, 'root', 1);
  lockNode(sb, 'root');
  return sb;
}

export function spaceNull(): CrystalBall {
  const sb = createCrystalBall('null');
  addAttribute(sb, 'root', 'type', ['null']);
  setSlotCount(sb, 'root', 1);
  lockNode(sb, 'root');
  return sb;
}

export function spaceList(items: CrystalBall[]): CrystalBall {
  const sb = createCrystalBall('list');
  addAttribute(sb, 'root', 'type', ['list']);
  
  const itemsNode = addNode(sb, 'root', 'items');
  
  for (let i = 0; i < items.length; i++) {
    const itemNode = addNode(sb, itemsNode.id, String(i));
    attachSubspace(sb, itemNode.id, items[i]);
  }
  
  setSlotCount(sb, 'root', 1);
  setSlotCount(sb, itemsNode.id, items.length);
  lockNode(sb, 'root');
  
  return sb;
}

export function spaceObject(fields: Record<string, CrystalBall>): CrystalBall {
  const sb = createCrystalBall('object');
  addAttribute(sb, 'root', 'type', ['object']);
  
  const fieldsNode = addNode(sb, 'root', 'fields');
  
  for (const name of Object.keys(fields)) {
    const fieldNode = addNode(sb, fieldsNode.id, name);
    attachSubspace(sb, fieldNode.id, fields[name]);
  }
  
  setSlotCount(sb, 'root', 1);
  setSlotCount(sb, fieldsNode.id, Object.keys(fields).length);
  lockNode(sb, 'root');
  
  return sb;
}

export function spaceRef(name: string): CrystalBall {
  const sb = createCrystalBall(`ref:${name}`);
  addAttribute(sb, 'root', 'type', ['space']);
  addAttribute(sb, 'root', 'name', [name], name);
  setSlotCount(sb, 'root', 1);
  lockNode(sb, 'root');
  return sb;
}

// ============================================================
// PART 2: SPACE-AS-STATE - Transitions as Spaces
// ============================================================

// A Transition is a Space describing a state transformation
export interface TransitionSpec {
  name: string;
  from: string;      // coordinate pattern
  to: string;       // coordinate pattern
  conditions?: Record<string, any>;
}

// Transitions are encoded as Spaces, not JS objects
export function spaceTransition(spec: TransitionSpec): CrystalBall {
  const sb = createCrystalBall(`transition:${spec.name}`);
  
  addAttribute(sb, 'root', 'type', ['transition']);
  addAttribute(sb, 'root', 'name', [spec.name], spec.name);
  
  const fromNode = addNode(sb, 'root', 'from');
  const fromSpace = spaceString(spec.from);
  attachSubspace(sb, fromNode.id, fromSpace);
  
  const toNode = addNode(sb, 'root', 'to');
  const toSpace = spaceString(spec.to);
  attachSubspace(sb, toNode.id, toSpace);
  
  setSlotCount(sb, 'root', 2);
  lockNode(sb, 'root');
  
  return sb;
}

// Policy is also a Space
export interface PolicySpec {
  name: string;
  transitions: TransitionSpec[];
  maxDepth: number;
  primacy: number[];    // primacy ordering for selection
  basinOrder: number;   // which basin (1, 2, or 3)
}

export function spacePolicy(spec: PolicySpec): CrystalBall {
  const sb = createCrystalBall(`policy:${spec.name}`);
  
  addAttribute(sb, 'root', 'type', ['policy']);
  addAttribute(sb, 'root', 'name', [spec.name], spec.name);
  addAttribute(sb, 'root', 'maxDepth', [spec.maxDepth], spec.maxDepth);
  addAttribute(sb, 'root', 'basinOrder', [spec.basinOrder], spec.basinOrder);
  
  const transNode = addNode(sb, 'root', 'transitions');
  for (const t of spec.transitions) {
    const tNode = addNode(sb, transNode.id, t.name);
    attachSubspace(sb, tNode.id, spaceTransition(t));
  }
  
  const primacyNode = addNode(sb, 'root', 'primacy');
  const primacyList = spaceList(spec.primacy.map(p => spaceNumber(p)));
  attachSubspace(sb, primacyNode.id, primacyList);
  
  setSlotCount(sb, 'root', 3);
  setSlotCount(sb, transNode.id, spec.transitions.length);
  lockNode(sb, 'root');
  
  return sb;
}

// ============================================================
// PART 3: REACHABILITY - First-class, parameterized
// ============================================================

export interface ReachParams {
  depth: number;        // max depth / fuel
  basinOrder: number;   // which basin (1=input, 2=transition, 3=meta-control)
  primacy: number[];    // primacy ordering for selection
  kNN?: number;         // k-nearest neighbors for expansion
  constraints?: Record<string, any>;
}

// Reachability result is a Space, not JS
export function spaceReachability(
  start: CrystalBall,
  params: ReachParams
): CrystalBall {
  const sb = createCrystalBall(`reach:${start.name}`);
  
  // Parameters
  addAttribute(sb, 'root', 'type', ['reachability']);
  addAttribute(sb, 'root', 'depth', [params.depth], params.depth);
  addAttribute(sb, 'root', 'basinOrder', [params.basinOrder], params.basinOrder);
  
  // Primacy as Space
  const primacyNode = addNode(sb, 'root', 'primacy');
  const primacySpace = spaceList(params.primacy.map(p => spaceNumber(p)));
  attachSubspace(sb, primacyNode.id, primacySpace);
  
  // States as Space (list of references)
  const statesNode = addNode(sb, 'root', 'states');
  const stateRefs = [spaceRef(start.name)]; // Simplified - just reference start
  const statesSpace = spaceList(stateRefs);
  attachSubspace(sb, statesNode.id, statesSpace);
  
  // kNN if specified
  if (params.kNN) {
    addAttribute(sb, 'root', 'kNN', [params.kNN], params.kNN);
  }
  
  setSlotCount(sb, 'root', 3);
  lockNode(sb, 'root');
  
  return sb;
}

// ============================================================
// PART 4: SPACE-AS-OBSERVATION - All outputs are Spaces
// ============================================================

// Observation is a Space that encodes facts about another Space
// Subject is a SPACE REFERENCE, not JSON string

export interface Claim {
  property: string;
  params: Record<string, CrystalBall>;  // params are Spaces
}

export function makeObservation(
  subject: CrystalBall,
  claim: Claim,
  witness?: CrystalBall
): CrystalBall {
  const obs = createCrystalBall(`obs:${claim.property}`);
  
  // Subject: space reference (NOT JSON string)
  const subjectNode = addNode(obs, 'root', 'subject');
  const subjectRef = spaceRef(subject.name);  // Reference by name
  attachSubspace(obs, subjectNode.id, subjectRef);
  
  // Claim: property + params
  const claimNode = addNode(obs, 'root', 'claim');
  addAttribute(obs, claimNode.id, 'property', [claim.property]);
  
  const paramsNode = addNode(obs, claimNode.id, 'params');
  const paramsSpace = spaceObject(claim.params);
  attachSubspace(obs, paramsNode.id, paramsSpace);
  
  // Witness: optional trace (also a Space)
  if (witness) {
    const witnessNode = addNode(obs, 'root', 'witness');
    attachSubspace(obs, witnessNode.id, witness);
  }
  
  setSlotCount(obs, 'root', witness ? 3 : 2);
  lockNode(obs, 'root');
  
  return obs;
}

// Example: Observe attributes - returns Space
export function observeAttributes(space: CrystalBall): CrystalBall {
  // Build attribute list as Space
  const attrs: Record<string, CrystalBall> = {};
  for (const [id, node] of space.nodes) {
    for (const [attrName, attr] of node.attributes) {
      attrs[`${id}.${attrName}`] = spaceString(attrName);
    }
  }
  const attrSpace = spaceObject(attrs);
  
  return makeObservation(space, {
    property: 'hasAttributes',
    params: { count: spaceNumber(Object.keys(attrs).length) }
  }, attrSpace);
}

// Example: Observe reachability
export function observeReachability(
  state: CrystalBall,
  params: ReachParams
): CrystalBall {
  const reachSpace = spaceReachability(state, params);
  
  return makeObservation(state, {
    property: 'reachable',
    params: {
      depth: spaceNumber(params.depth),
      basinOrder: spaceNumber(params.basinOrder)
    }
  }, reachSpace);
}

// ============================================================
// PART 5: THE TOWER - Meta-evaluators as Spaces
// ============================================================

export type EvaluatorLevel = 0 | 1 | 2 | 3;

// Evaluator is itself a Space
export interface EvaluatorSpec {
  level: EvaluatorLevel;
  name: string;
  description: string;
}

export function spaceEvaluator(spec: EvaluatorSpec): CrystalBall {
  const sb = createCrystalBall(`evaluator:${spec.name}`);
  
  addAttribute(sb, 'root', 'type', ['evaluator']);
  addAttribute(sb, 'root', 'level', [spec.level], spec.level);
  addAttribute(sb, 'root', 'name', [spec.name], spec.name);
  addAttribute(sb, 'root', 'description', [spec.description], spec.description);
  
  setSlotCount(sb, 'root', 1);
  lockNode(sb, 'root');
  
  return sb;
}

// Built-in evaluators as Spaces
export const evaluator0 = spaceEvaluator({ level: 0, name: 'identity', description: 'Returns input as-is' });
export const evaluator1 = spaceEvaluator({ level: 1, name: 'attributeObserver', description: 'Observes attributes of input' });
export const evaluator2 = spaceEvaluator({ level: 2, name: 'metaObserver', description: 'Observes the observer' });

// Tower application - returns list of observation Spaces
export function tower(
  base: CrystalBall,
  levels: EvaluatorLevel[]
): CrystalBall[] {
  let current: CrystalBall = base;
  const results: CrystalBall[] = [];
  
  for (const level of levels) {
    let obs: CrystalBall;
    
    switch (level) {
      case 0:
        obs = current;  // Identity - return as-is
        break;
      case 1:
        obs = observeAttributes(current);
        break;
      case 2:
        // Meta: observe the observation
        const level1Obs = observeAttributes(current);
        obs = makeObservation(base, {
          property: 'metaObserved',
          params: { observer: spaceString('attributeObserver') }
        }, level1Obs);
        break;
      default:
        obs = current;
    }
    
    results.push(obs);
    current = obs;
  }
  
  return results;
}

// ============================================================
// PART 6: LLM OBSERVE - External AI observation
// ============================================================

// LLM Observe: Query an external LLM about a Space
// Returns an Observation Space with the LLM's response

export interface LLMObserveOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
}

export function llm_observe(
  prompt: string,
  context?: CrystalBall,
  options?: LLMObserveOptions
): CrystalBall {
  // STUB: Returns placeholder until real LLM integration
  const placeholder = "NotYetImplemented LLM call";
  
  // Wrap the placeholder in a Space
  const response = spaceString(placeholder);
  
  // Create observation with LLM response
  const obs = createCrystalBall('LLMObservation');
  
  // Subject: the context space if provided
  if (context) {
    const subjectNode = addNode(obs, 'root', 'subject');
    attachSubspace(obs, subjectNode.id, spaceRef(context.name));
  }
  
  // Claim: the prompt that was asked
  const claimNode = addNode(obs, 'root', 'claim');
  addAttribute(obs, claimNode.id, 'property', ['llm_response']);
  
  const promptNode = addNode(obs, claimNode.id, 'prompt');
  const promptSpace = spaceString(prompt);
  attachSubspace(obs, promptNode.id, promptSpace);
  
  // Witness: the LLM response
  const witnessNode = addNode(obs, 'root', 'witness');
  attachSubspace(obs, witnessNode.id, response);
  
  // Metadata
  if (options?.model) {
    addAttribute(obs, 'root', 'model', [options.model]);
  }
  if (options?.temperature !== undefined) {
    addAttribute(obs, 'root', 'temperature', [options.temperature], options.temperature);
  }
  
  setSlotCount(obs, 'root', 3);
  lockNode(obs, 'root');
  
  return obs;
}

// ============================================================
// PART 7: EVAL & QUOTE - The core homoiconic primitives
// ============================================================

// quote : Space → Space
// Prevents execution - returns the Space as a quoted value
// In our system, this wraps a Space in a "quoted" container
export function quote(space: CrystalBall): CrystalBall {
  const q = createCrystalBall(`quote:${space.name}`);
  
  addAttribute(q, 'root', 'type', ['quoted']);
  addAttribute(q, 'root', 'quotedType', ['space']);
  
  // Embed the quoted Space as a subspace
  const innerNode = addNode(q, 'root', 'inner');
  attachSubspace(q, innerNode.id, space);
  
  setSlotCount(q, 'root', 1);
  lockNode(q, 'root');
  
  return q;
}

// eval : Space → Space
// Executes a quoted Space as a program
// Currently implements: coordinate resolution, attribute access, subspace traversal
export function evalSpace(program: CrystalBall, context?: CrystalBall): CrystalBall {
  const root = program.nodes.get(program.rootId);
  if (!root) return program;
  
  const type = root.attributes.get('type')?.spectrum[0];
  
  // Handle different program types
  switch (type) {
    case 'quoted': {
      // Unwrap and evaluate the inner Space
      const innerNodeId = root.children[0];
      const innerNode = program.nodes.get(innerNodeId);
      if (!innerNode) return program;
      
      // The inner node has a subspace - evaluate it
      if (innerNode.subspace) {
        return evalSpace(innerNode.subspace, context);
      }
      
      return program;
    }
    
    case 'space': {
      // Reference to another space - resolve it
      const name = root.attributes.get('name')?.spectrum[0] as string;
      if (context) {
        // Look up in context's subspaces
        for (const [id, node] of context.nodes) {
          if (node.subspace && node.subspace.name === name) {
            return node.subspace;
          }
        }
      }
      return program;
    }
    
    case 'coordinate': {
      // Coordinate program: resolve against context
      const coord = root.attributes.get('coordinate')?.spectrum[0] as string;
      if (context && coord) {
        const resolved = resolveCoordinate(context, coord);
        if (resolved.length > 0) {
          const labels = resolved.map(node => node.label);
          const result = createCrystalBall(`resolved:${labels.join('|')}`);
          addAttribute(result, 'root', 'type', ['resolved']);
          addAttribute(result, 'root', 'label', labels);
          return result;
        }
      }
      return program;
    }
    
    case 'list': {
      // Evaluate each item in the list
      const itemsNodeId = root.children[0];
      const itemsNode = program.nodes.get(itemsNodeId);
      if (!itemsNode) return program;
      
      const evaluatedItems: CrystalBall[] = [];
      for (const childId of itemsNode.children) {
        const child = program.nodes.get(childId);
        if (child?.subspace) {
          evaluatedItems.push(evalSpace(child.subspace, context));
        }
      }
      return spaceList(evaluatedItems);
    }
    
    case 'object': {
      // Evaluate each field in the object
      const fieldsNodeId = root.children[0];
      const fieldsNode = program.nodes.get(fieldsNodeId);
      if (!fieldsNode) return program;
      
      const fields: Record<string, CrystalBall> = {};
      for (const childId of fieldsNode.children) {
        const child = program.nodes.get(childId);
        if (child?.subspace) {
          fields[child.label] = evalSpace(child.subspace, context);
        }
      }
      return spaceObject(fields);
    }
    
    default: {
      // For primitives or unknown types, just return as-is
      // But if we have context and this is being evaluated, return context
      if (context && type === undefined) {
        return context;
      }
      return program;
    }
  }
}

// apply : (Space → Space) → Space → Space
// Function application in the Space domain
export function apply(fn: CrystalBall, arg: CrystalBall): CrystalBall {
  // Currently a stub - evaluates the function application
  // In full impl, this would parse fn as a program and apply to arg
  return evalSpace(fn, arg);
}

// ============================================================
// DEMO - All outputs are Spaces
// ============================================================

export function runHomoiconicDemo(): void {
  const registry = createRegistry();
  void registry;

  // Create a state
  const state = createCrystalBall('MyState');
  const attrNode = addNode(state, 'root', 'attrs');
  addNode(state, attrNode.id, 'color');
  addAttribute(state, attrNode.id, 'color', ['red', 'blue', 'green']);
  setSlotCount(state, 'root', 1);

  console.log('=== Tightened Homoiconic Crystal Ball ===\n');

  // Demo: Observation as Space (subject is reference, not JSON)
  console.log('--- Observation (subject as Space reference) ---');
  const obs = observeAttributes(state);
  console.log('Subject type:', obs.nodes.get('root.0')?.subspace?.name);

  // Demo: Reachability as Space
  console.log('\n--- Reachability (parameterized) ---');
  const reach = spaceReachability(state, {
    depth: 3,
    basinOrder: 2,
    primacy: [1, 2, 3],
    kNN: 5
  });
  console.log('Basin order attr:', reach.nodes.get('root')?.attributes.get('basinOrder')?.defaultValue);

  // Demo: The Tower - all observation outputs are Spaces
  console.log('\n--- The Tower (all outputs = Spaces) ---');
  const towerResult = tower(state, [0, 1, 2]);
  console.log('Level 0 type:', towerResult[0].nodes.get('root')?.attributes.get('type')?.spectrum[0]);
  console.log('Level 1 type:', towerResult[1].nodes.get('root')?.attributes.get('type')?.spectrum[0]);
  console.log('Level 2 type:', towerResult[2].nodes.get('root')?.attributes.get('type')?.spectrum[0]);

  // Demo: Policy as Space
  console.log('\n--- Policy as Space ---');
  const policy = spacePolicy({
    name: 'test',
    transitions: [{ name: 'move', from: '1', to: '2' }],
    maxDepth: 5,
    primacy: [1, 2],
    basinOrder: 2
  });
  console.log('Policy type:', policy.nodes.get('root')?.attributes.get('type')?.spectrum[0]);
  console.log('Policy depth:', policy.nodes.get('root')?.attributes.get('maxDepth')?.defaultValue);

  // Demo: LLM Observe (stub)
  console.log('\n--- LLM Observe (stub) ---');
  const llmObs = llm_observe("What attributes does this state have?", state, { model: 'gpt-4' });
  const witnessNode = llmObs.nodes.get('root.2');
  const witnessSubspace = witnessNode?.subspace;
  console.log('LLM Witness type:', witnessSubspace?.nodes.get('root')?.attributes.get('type')?.spectrum[0]);
  console.log('LLM Witness value:', witnessSubspace?.nodes.get('root')?.attributes.get('value')?.defaultValue);

  // Demo: Quote and Eval
  console.log('\n--- Quote and Eval ---');
  const quoted = quote(state);
  console.log('Quoted type:', quoted.nodes.get('root')?.attributes.get('type')?.spectrum[0]);
  console.log('Quoted inner node children:', quoted.nodes.get('root')?.children);
  const innerId = quoted.nodes.get('root')?.children[0];
  console.log('Inner node subspace name:', quoted.nodes.get(innerId || '')?.subspace?.name);

  const evald = evalSpace(quoted, state);
  console.log('Eval result name:', evald.name);
  console.log('Eval result type attr:', evald.nodes.get('root')?.attributes.get('type')?.spectrum[0]);
}

function isDirectExecution(): boolean {
  return Boolean(
    process &&
    Array.isArray(process.argv) &&
    typeof process.argv[1] === "string" &&
    (process.argv[1].endsWith("/homoiconic.ts") || process.argv[1].endsWith("/homoiconic.js"))
  );
}

if (isDirectExecution()) {
  runHomoiconicDemo();
}
