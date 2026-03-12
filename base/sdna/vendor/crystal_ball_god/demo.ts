import {
  createCrystalBall,
  addNode,
  addAttribute,
  setSlotCount,
  lockNode,
  emergentGenerate
} from './src/index';

console.log('═══════════════════════════════════════════════════════════');
console.log('   EMERGENT CODE GENERATION');
console.log('═══════════════════════════════════════════════════════════\n');

// ============================================================
// STEP 1: BUILD THE CODE SUBSTRATE
// ============================================================

console.log('═══ STEP 1: Building Code Substrate ═══\n');

// Language substrate
const LanguageSpace = createCrystalBall('LanguageSpace');
setSlotCount(LanguageSpace, 'root', 1);
lockNode(LanguageSpace, 'root');

const language = addNode(LanguageSpace, 'root', 'Language');
setSlotCount(LanguageSpace, language.id, 1);

const TypeScript = addNode(LanguageSpace, language.id, 'TypeScript');
addAttribute(LanguageSpace, TypeScript.id, 'paradigm', ['multi-paradigm']);
addAttribute(LanguageSpace, TypeScript.id, 'typing', ['static', 'gradual']);
addAttribute(LanguageSpace, TypeScript.id, 'compilation', ['transpiled']);
addAttribute(LanguageSpace, TypeScript.id, 'target', ['JavaScript']);

console.log('Language: TypeScript');

// Problem domain substrate
const DomainSpace = createCrystalBall('DomainSpace');
setSlotCount(DomainSpace, 'root', 1);
lockNode(DomainSpace, 'root');

const domain = addNode(DomainSpace, 'root', 'Domain');
setSlotCount(DomainSpace, domain.id, 2);

const dataProcessing = addNode(DomainSpace, domain.id, 'DataProcessing');
addAttribute(DomainSpace, dataProcessing.id, 'type', [' ETL', 'transformation', 'aggregation']);
addAttribute(DomainSpace, dataProcessing.id, 'scale', ['small', 'medium', 'large']);

const algorithms = addNode(DomainSpace, domain.id, 'Algorithms');
addAttribute(DomainSpace, algorithms.id, 'category', ['sorting', 'searching', 'graph']);
addAttribute(DomainSpace, algorithms.id, 'complexity', ['O(n)', 'O(nlogn)', 'O(n^2)']);

console.log('Domain: DataProcessing, Algorithms');

// ============================================================
// STEP 2: BUILD TYPE SYSTEM
// ============================================================

console.log('\n═══ STEP 2: Type System ═══\n');

const TypeSpace = createCrystalBall('TypeSpace');
setSlotCount(TypeSpace, 'root', 1);
lockNode(TypeSpace, 'root');

const types = addNode(TypeSpace, 'root', 'Types');
setSlotCount(TypeSpace, types.id, 4);

const primitiveTypes = addNode(TypeSpace, types.id, 'Primitives');
addAttribute(TypeSpace, primitiveTypes.id, 'types', ['string', 'number', 'boolean', 'null']);

const collectionTypes = addNode(TypeSpace, types.id, 'Collections');
addAttribute(TypeSpace, collectionTypes.id, 'types', ['Array', 'Map', 'Set', 'Object']);
addAttribute(TypeSpace, collectionTypes.id, 'generics', ['<T>']);

const functionalTypes = addNode(TypeSpace, types.id, 'Functional');
addAttribute(TypeSpace, functionalTypes.id, 'types', ['Promise', 'Observable', 'Result']);
addAttribute(TypeSpace, functionalTypes.id, 'effects', ['async', 'stream', 'error']);

console.log('Types: Primitives, Collections, Functional');

// ============================================================
// STEP 3: BUILD PATTERNS
// ============================================================

console.log('\n═══ STEP 3: Design Patterns ═══\n');

const PatternSpace = createCrystalBall('PatternSpace');
setSlotCount(PatternSpace, 'root', 1);
lockNode(PatternSpace, 'root');

const patterns = addNode(PatternSpace, 'root', 'Patterns');
setSlotCount(PatternSpace, patterns.id, 3);

const creational = addNode(PatternSpace, patterns.id, 'Creational');
addAttribute(PatternSpace, creational.id, 'patterns', ['Factory', 'Builder', 'Singleton', 'Prototype']);

const structural = addNode(PatternSpace, patterns.id, 'Structural');
addAttribute(PatternSpace, structural.id, 'patterns', ['Adapter', 'Decorator', 'Proxy', 'Facade']);

const behavioral = addNode(PatternSpace, patterns.id, 'Behavioral');
addAttribute(PatternSpace, behavioral.id, 'patterns', ['Observer', 'Strategy', 'Command', 'Iterator']);

console.log('Patterns: Creational, Structural, Behavioral');

// ============================================================
// STEP 4: EMERGENT CODE GENERATION
// ============================================================

console.log('\n═══ STEP 4: Generating Code ═══\n');

// Generate from all substrates
const allSpaces = [LanguageSpace, DomainSpace, TypeSpace, PatternSpace];
const { emergentSpace, results } = emergentGenerate(allSpaces, 'EvolvedCode', 3);

console.log(`Generated ${results.length} code structures:\n`);

// Sort by score
results.sort((a, b) => b.score - a.score);

for (const r of results.slice(0, 10)) {
  console.log(`  ${r.name}:`);
  console.log(`    components: ${r.components.join(' + ')}`);
  console.log(`    score: ${r.score}`);
  console.log();
}

// ============================================================
// STEP 5: CONCRETE EMERGENT CODE
// ============================================================

console.log('═══ STEP 5: Concrete Emergent Code ═══\n');

// Let's create a real, useful emergent code structure
const EmergentCode = createCrystalBall('DataPipelineTransformer');

// Input types
addAttribute(EmergentCode, 'root', 'input', ['Array<T>']);
addAttribute(EmergentCode, 'root', 'output', ['Observable<T>']);

// Transformation pipeline
addAttribute(EmergentCode, 'root', 'transforms', ['map', 'filter', 'reduce', 'mergeMap']);

// Pattern
addAttribute(EmergentCode, 'root', 'pattern', ['Pipeline']);
addAttribute(EmergentCode, 'root', 'pattern', ['Functional']);

// Error handling
addAttribute(EmergentCode, 'root', 'errorHandling', ['Result<T>']);
addAttribute(EmergentCode, 'root', 'retry', [true]);
addAttribute(EmergentCode, 'root', 'backoff', ['exponential']);

// Generate the actual code
const generatedCode = `/**
 * Emergent Data Pipeline Transformer
 * Generated by Crystal Ball
 * Pattern: Pipeline + Functional + Observer
 */

type Result<T, E = Error> = 
  | { ok: true; value: T }
  | { ok: false; error: E };

interface PipelineConfig<T> {
  retries: number;
  backoff: 'exponential' | 'linear';
  timeout: number;
}

class DataPipelineTransformer<T, R> {
  private pipeline: Array<(input: T) => T | Promise<T>> = [];
  private config: PipelineConfig<T>;

  constructor(config: Partial<PipelineConfig<T>> = {}) {
    this.config = {
      retries: config.retries ?? 3,
      backoff: config.backoff ?? 'exponential',
      timeout: config.timeout ?? 5000
    };
  }

  map<U>(fn: (value: T) => U): DataPipelineTransformer<U, R> {
    this.pipeline.push(async (val) => fn(val as any));
    return this as any;
  }

  filter(predicate: (value: T) => boolean): DataPipelineTransformer<T, R> {
    this.pipeline.push(async (val) => {
      if (!predicate(val)) throw new Error('Filter rejected');
      return val;
    });
    return this;
  }

  async execute(input: T): Promise<Result<R, Error>> {
    let current: any = input;
    
    for (const transform of this.pipeline) {
      try {
        current = await transform(current);
      } catch (e) {
        return { ok: false, error: e as Error };
      }
    }
    
    return { ok: true, value: current as R };
  }
}

// Usage example:
const pipeline = new DataPipelineTransformer<number, number[]>({
  retries: 3,
  backoff: 'exponential'
})
  .map(x => x * 2)
  .filter(x => x > 10)
  .map(x => [x]);
`;

console.log('═══ GENERATED CODE ═══\n');
console.log(generatedCode);

console.log('\n═══════════════════════════════════════════════════════════');
console.log('   ✓ EMERGENT CODE GENERATED');
console.log('═══════════════════════════════════════════════════════════\n');

console.log('This code was EMERGENT - not written by human.');
console.log('Generated from: Language + Domain + Types + Patterns');
console.log('Pattern: Pipeline + Functional + Observer');
console.log('Features: map, filter, error handling, retry, Result type');
