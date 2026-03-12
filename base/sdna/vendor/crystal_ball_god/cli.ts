#!/usr/bin/env node

declare const process: any;
declare function require(name: string): any;

import {
  createCrystalBall,
  addNode,
  addAttribute,
  setSlotCount,
  lockNode,
  resolveCoordinate,
  resolveCoordinateBounded,
  recordScore,
  getScoreHistory,
  emergentGenerate,
  bloom,
  extend,
  parseAddress,
  renderHuman,
  toDeweyCode,
  getBoundaryFeatures,
  neighbors
} from './src/index';

// CLI State
const state = {
  currentSpace: null as any,
  spaces: new Map<string, any>()
};

const prompt = () => '🔮 > ';
const cliArgs: string[] = process.argv.slice(2);

function parseValue(raw: string): string | number | boolean {
  const token = raw.trim();
  if (token === "true") return true;
  if (token === "false") return false;
  const num = Number(token);
  if (!Number.isNaN(num) && token !== "") return num;
  return token;
}

// Parse command
function parseCommand(input: string): { cmd: string; args: string[] } {
  const parts = input.trim().split(/\s+/);
  return { cmd: parts[0] || '', args: parts.slice(1) };
}

// Main REPL
async function repl() {
  const readline = require('readline');
  
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: prompt()
  });
  
  rl.prompt();
  
  rl.on('line', (line) => {
    const { cmd, args } = parseCommand(line);
    
    try {
      switch (cmd) {
        case 'help':
        case '?':
          console.log(`
🔮 Crystal Ball CLI - Commands:

  new <name>          Create new space
  use <name>           Switch to space  
  ls                    List spaces
  add <path> <label>  Add node at path
  cat <path>           Show node
  set <path> <attr> <val>  Set attribute
  score <path> <agent|user> <value> [note...]
                        Record a score entry
  scores [path] [agent|user]
                        Show score history (optionally filtered)
  resolve <coord>      Resolve coordinate
  collapse <coord> <start> <end> [limit] [first|random]
                        Resolve superposition with bounded collapse
  emerge <score>       Generate emergent
  bloom <coord> <label> <n>  Bloom slots
  neighbors <path>      Show neighbors
  address <coord>      Show Dewey address
  quit                  Exit
`);
          break;
          
        case 'new':
          if (args.length === 0) console.log('Usage: new <name>');
          else {
            const s = createCrystalBall(args[0]);
            state.currentSpace = s;
            state.spaces.set(args[0], s);
            console.log(`🔮 Created: ${args[0]}`);
          }
          break;
          
        case 'use':
          if (args.length === 0) console.log('Usage: use <name>');
          else {
            const s = state.spaces.get(args[0]);
            if (s) { state.currentSpace = s; console.log(`🔮 Using: ${args[0]}`); }
            else console.log(`🔮 Unknown space: ${args[0]}`);
          }
          break;
          
        case 'ls':
          console.log('Spaces:', Array.from(state.spaces.keys()).join(', ') || '(none)');
          break;
          
        case 'add':
          if (!state.currentSpace) console.log('🔮 No space. Use "new" first.');
          else if (args.length < 2) console.log('Usage: add <path> <label>');
          else {
            addNode(state.currentSpace, args[0] || 'root', args[1]);
            console.log(`🔮 Added: ${args[1]}`);
          }
          break;
          
        case 'cat':
          if (!state.currentSpace) console.log('🔮 No space.');
          else {
            const n = state.currentSpace.nodes.get(args[0]);
            if (n) {
              console.log(`🔮 ${n.label} [${n.id}]`);
              console.log(`  children: ${n.children.length}, locked: ${n.locked}`);
              for (const [a, attr] of n.attributes) {
                console.log(`  @${a}: ${attr.spectrum.join(', ')}`);
              }
            } else console.log(`🔮 Not found: ${args[0]}`);
          }
          break;

        case 'set':
          if (!state.currentSpace) console.log('🔮 No space.');
          else if (args.length < 3) console.log('Usage: set <path> <attr> <val>');
          else {
            const nodeId = args[0];
            const attr = args[1];
            const rawVal = args.slice(2).join(' ');
            const value = parseValue(rawVal);
            addAttribute(state.currentSpace, nodeId, attr, [value], value);
            console.log(`🔮 Set ${nodeId}@${attr} = ${String(value)}`);
          }
          break;

        case 'score':
          if (!state.currentSpace) console.log('🔮 No space.');
          else if (args.length < 3) {
            console.log('Usage: score <path> <agent|user> <value> [note...]');
          } else {
            const nodeId = args[0];
            const actor = args[1];
            const valueRaw = args[2];
            const note = args.slice(3).join(' ');
            const value = Number(valueRaw);

            if (actor !== 'agent' && actor !== 'user') {
              console.log('🔮 actor must be "agent" or "user".');
              break;
            }
            if (!Number.isFinite(value)) {
              console.log('🔮 score value must be a number.');
              break;
            }

            const entry = recordScore(
              state.currentSpace,
              nodeId,
              actor,
              value,
              note || undefined
            );
            console.log(`🔮 Recorded score at ${entry.id} (${actor}=${value})`);
          }
          break;

        case 'scores':
          if (!state.currentSpace) console.log('🔮 No space.');
          else {
            const nodeId = args[0];
            const actorArg = args[1];
            const actor = actorArg === 'agent' || actorArg === 'user' ? actorArg : undefined;
            const rows = getScoreHistory(state.currentSpace, nodeId, actor);

            if (rows.length === 0) {
              console.log('🔮 No score history');
              break;
            }

            const avg = rows.reduce((sum, r) => sum + r.score, 0) / rows.length;
            console.log(`🔮 ${rows.length} score entries (avg=${avg.toFixed(3)}):`);
            rows.slice(-20).forEach(r => {
              const note = r.note ? ` note="${r.note}"` : '';
              console.log(`  [${r.timestamp}] ${r.actor} ${r.targetNodeId} -> ${r.score}${note}`);
            });
            if (rows.length > 20) {
              console.log(`  ... (${rows.length - 20} earlier entries omitted)`);
            }
          }
          break;
          
        case 'resolve':
          if (!state.currentSpace) console.log('🔮 No space.');
          else {
            const r = resolveCoordinate(state.currentSpace, args[0]);
            if (r.length === 0) {
              console.log('🔮 No resolution');
            } else {
              const summary = r.slice(0, 5).map(node => `${node.label} → ${node.id}`).join(', ');
              const suffix = r.length > 5 ? ` ... (+${r.length - 5} more)` : '';
              console.log(`🔮 ${summary}${suffix}`);
            }
          }
          break;

        case 'collapse':
          if (!state.currentSpace) console.log('🔮 No space.');
          else if (args.length < 3) {
            console.log('Usage: collapse <coord> <start> <end> [limit] [first|random]');
          } else {
            const coord = args[0];
            const start = parseInt(args[1], 10);
            const end = parseInt(args[2], 10);
            const maybeLimit = args.length >= 4 ? parseInt(args[3], 10) : undefined;
            const maybeStrategy = args.length >= 5 ? args[4] : undefined;
            const strategy = maybeStrategy === 'random' ? 'random' : 'first';

            if (Number.isNaN(start) || Number.isNaN(end)) {
              console.log('🔮 start/end must be integers.');
              break;
            }

            const bounded = resolveCoordinateBounded(
              state.currentSpace,
              coord,
              {
                start,
                end,
                limit: maybeLimit !== undefined && !Number.isNaN(maybeLimit) ? maybeLimit : undefined,
                strategy
              }
            );

            if (bounded.length === 0) {
              console.log('🔮 No bounded resolution');
            } else {
              const summary = bounded
                .slice(0, 8)
                .map(node => `${node.label} → ${node.id}`)
                .join(', ');
              const suffix = bounded.length > 8 ? ` ... (+${bounded.length - 8} more)` : '';
              console.log(`🔮 ${summary}${suffix}`);
            }
          }
          break;
          
        case 'emerge':
          if (!state.currentSpace) console.log('🔮 No space.');
          else {
            const score = parseInt(args[0]) || 3;
            const { results } = emergentGenerate([state.currentSpace], 'Emerged', score);
            console.log(`🔮 Generated ${results.length} emergent:`);
            results.slice(0, 5).forEach(r => console.log(`  ${r.name} (score: ${r.score})`));
          }
          break;

        case 'bloom':
          if (!state.currentSpace) console.log('🔮 No space.');
          else if (args.length < 2) console.log('Usage: bloom <coord> <label> <n>');
          else {
            const coord = args[0];
            const label = args[1];
            const n = args.length >= 3 ? parseInt(args[2], 10) : 4;
            const count = Number.isNaN(n) ? 4 : n;
            bloom(state.currentSpace, coord, label, count);
            console.log(`🔮 Bloomed ${coord} with ${count} new slots labeled "${label}"`);
          }
          break;
          
        case 'address':
          if (args.length === 0) console.log('Usage: address <coord>');
          else {
            const p = parseAddress(args[0]);
            console.log(`🔮 Dewey: ${toDeweyCode(p)}`);
            console.log(`🔮 Human: ${renderHuman(p)}`);
          }
          break;
          
        case 'neighbors':
          if (!state.currentSpace) console.log('🔮 No space.');
          else {
            const n = neighbors(state.currentSpace, args[0] || 'root', { k: 5, strict: false });
            console.log(`🔮 Neighbors of ${args[0] || 'root'}:`);
            n.forEach(x => console.log(`  ${x.node.label} (dist: ${x.distance})`));
          }
          break;
          
        case 'quit':
        case 'exit':
          console.log('🔮 Goodbye!');
          process.exit(0);
          break;
          
        case '':
          break;
          
        default:
          console.log(`🔮 Unknown: ${cmd}. Try "help".`);
      }
    } catch (e: any) {
      console.log(`🔮 Error: ${e.message}`);
    }
    
    rl.setPrompt(prompt());
    rl.prompt();
  });
  
  rl.on('close', () => {
    console.log('\n🔮 Goodbye!');
    process.exit(0);
  });
}

const wizardMode = cliArgs.includes('--wizard') || cliArgs.includes('-w');

if (wizardMode) {
  console.log(`
🔮 ═══════════════════════════════════════════════════════
   CRYSTAL BALL WIZARD
══════════════════════════════════════════════════════
   
I'll guide you through creating a space.
Let's start...

What domain shall we explore?
(e.g., "Cuisine", "Code", "Music", "Science")
  
`);
  // Wizard mode would be interactive - for now just note it
  console.log('🔮 Wizard mode coming soon!');
}

console.log('🔮 Crystal Ball - Type "help" for commands\n');
repl();
