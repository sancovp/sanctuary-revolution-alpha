'use client';

import { useState, useEffect, useRef } from 'react';
import { Copy, Check } from 'lucide-react';

// Line types for styling
type LineType = 'cmd' | 'ok' | 'info' | 'data' | 'scry' | 'bloom' | 'attr' | 'blank' | 'comment';

interface TermLine {
  text: string;
  type: LineType;
  /** Delay before this line appears (ms). Lower = faster. */
  delay?: number;
}

/**
 * The real agent session: building a Gordon Ramsay restaurant space
 * from scratch. ~70 tool calls at agent speed.
 */
const SESSION: TermLine[] = [
  // ── Phase 1: Create space ──
  { text: '# Agent connected via MCP — building restaurant ontology', type: 'comment', delay: 600 },
  { text: '', type: 'blank', delay: 100 },
  { text: '$ crystal_ball create_space {"name":"GordonRamsayRestaurant"}', type: 'cmd', delay: 400 },
  { text: '✓ Space "GordonRamsayRestaurant" created', type: 'ok', delay: 120 },
  { text: '', type: 'blank', delay: 80 },

  // ── Phase 2: Six pillars (rapid fire) ──
  { text: '# Defining six top-level pillars...', type: 'comment', delay: 300 },
  { text: '$ add_point  space:GRR  parent:root  label:"Kitchen"', type: 'cmd', delay: 200 },
  { text: '  → Kitchen                    at 1', type: 'ok', delay: 100 },
  { text: '$ add_point  space:GRR  parent:root  label:"Experience"', type: 'cmd', delay: 150 },
  { text: '  → Experience                 at 2', type: 'ok', delay: 100 },
  { text: '$ add_point  space:GRR  parent:root  label:"Brand"', type: 'cmd', delay: 150 },
  { text: '  → Brand                      at 3', type: 'ok', delay: 100 },
  { text: '$ add_point  space:GRR  parent:root  label:"Team"', type: 'cmd', delay: 150 },
  { text: '  → Team                       at 4', type: 'ok', delay: 100 },
  { text: '$ add_point  space:GRR  parent:root  label:"Supply"', type: 'cmd', delay: 150 },
  { text: '  → Supply                     at 5', type: 'ok', delay: 100 },
  { text: '$ add_point  space:GRR  parent:root  label:"Empire"', type: 'cmd', delay: 150 },
  { text: '  → Empire                     at 6', type: 'ok', delay: 100 },
  { text: '', type: 'blank', delay: 80 },

  // ── Phase 3: Kitchen depth (Order 2) ──
  { text: '# Deepening Kitchen → Order 2', type: 'comment', delay: 250 },
  { text: '$ add_point  parent:root.0  label:"Stations"', type: 'cmd', delay: 180 },
  { text: '  → Stations                   at 1.1', type: 'ok', delay: 90 },
  { text: '$ add_point  parent:root.0  label:"Menu"', type: 'cmd', delay: 150 },
  { text: '  → Menu                       at 1.2', type: 'ok', delay: 90 },
  { text: '$ add_point  parent:root.0  label:"Standards"', type: 'cmd', delay: 150 },
  { text: '  → Standards                  at 1.3', type: 'ok', delay: 90 },
  { text: '$ add_point  parent:root.0  label:"Technique"', type: 'cmd', delay: 150 },
  { text: '  → Technique                  at 1.4', type: 'ok', delay: 90 },

  // ── Experience depth ──
  { text: '$ add_point  parent:root.1  label:"Arrival"', type: 'cmd', delay: 130 },
  { text: '  → Arrival                    at 2.1', type: 'ok', delay: 80 },
  { text: '$ add_point  parent:root.1  label:"Atmosphere"', type: 'cmd', delay: 130 },
  { text: '  → Atmosphere                 at 2.2', type: 'ok', delay: 80 },
  { text: '$ add_point  parent:root.1  label:"Service"', type: 'cmd', delay: 130 },
  { text: '  → Service                    at 2.3', type: 'ok', delay: 80 },
  { text: '$ add_point  parent:root.1  label:"Pacing"', type: 'cmd', delay: 130 },
  { text: '  → Pacing                     at 2.4', type: 'ok', delay: 80 },
  { text: '$ add_point  parent:root.1  label:"Departure"', type: 'cmd', delay: 130 },
  { text: '  → Departure                  at 2.5', type: 'ok', delay: 80 },

  // ── Brand + Team + Supply (burst) ──
  { text: '$ add_point  parent:root.2  label:"Persona"', type: 'cmd', delay: 120 },
  { text: '  → Persona                    at 3.1', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.2  label:"Media"', type: 'cmd', delay: 100 },
  { text: '  → Media                      at 3.2', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.2  label:"Reputation"', type: 'cmd', delay: 100 },
  { text: '  → Reputation                 at 3.3', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.3  label:"Executive_Chef"', type: 'cmd', delay: 100 },
  { text: '  → Executive_Chef             at 4.1', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.3  label:"Sous_Chefs"', type: 'cmd', delay: 100 },
  { text: '  → Sous_Chefs                 at 4.2', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.3  label:"Line_Cooks"', type: 'cmd', delay: 100 },
  { text: '  → Line_Cooks                 at 4.3', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.3  label:"Front_of_House"', type: 'cmd', delay: 100 },
  { text: '  → Front_of_House             at 4.4', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.3  label:"Sommelier"', type: 'cmd', delay: 100 },
  { text: '  → Sommelier                  at 4.5', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.4  label:"Protein_Sourcing"', type: 'cmd', delay: 100 },
  { text: '  → Protein_Sourcing           at 5.1', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.4  label:"Produce"', type: 'cmd', delay: 100 },
  { text: '  → Produce                    at 5.2', type: 'ok', delay: 70 },
  { text: '$ add_point  parent:root.4  label:"Wine_Program"', type: 'cmd', delay: 100 },
  { text: '  → Wine_Program               at 5.3', type: 'ok', delay: 70 },
  { text: '', type: 'blank', delay: 60 },

  // ── Phase 4: Order 3 — Kitchen stations (the brigade) ──
  { text: '# Order 3 — kitchen brigade stations', type: 'comment', delay: 200 },
  { text: '$ add_point  parent:root.0.0  label:"Garde_Manger"', type: 'cmd', delay: 120 },
  { text: '  → Garde_Manger               at 1.1.1', type: 'ok', delay: 60 },
  { text: '$ add_point  parent:root.0.0  label:"Saucier"', type: 'cmd', delay: 100 },
  { text: '  → Saucier                    at 1.1.2', type: 'ok', delay: 60 },
  { text: '$ add_point  parent:root.0.0  label:"Rotisseur"', type: 'cmd', delay: 100 },
  { text: '  → Rotisseur                  at 1.1.3', type: 'ok', delay: 60 },
  { text: '$ add_point  parent:root.0.0  label:"Poissonnier"', type: 'cmd', delay: 100 },
  { text: '  → Poissonnier                at 1.1.4', type: 'ok', delay: 60 },
  { text: '$ add_point  parent:root.0.0  label:"Patissier"', type: 'cmd', delay: 100 },
  { text: '  → Patissier                  at 1.1.5', type: 'ok', delay: 60 },
  { text: '$ add_point  parent:root.0.0  label:"Pass"', type: 'cmd', delay: 100 },
  { text: '  → Pass                       at 1.1.6', type: 'ok', delay: 60 },

  // ── Menu items ──
  { text: '$ add_point  parent:root.0.1  label:"Beef_Wellington"', type: 'cmd', delay: 90 },
  { text: '  → Beef_Wellington            at 1.2.1', type: 'ok', delay: 50 },
  { text: '$ add_point  parent:root.0.1  label:"Lobster_Ravioli"', type: 'cmd', delay: 90 },
  { text: '  → Lobster_Ravioli            at 1.2.2', type: 'ok', delay: 50 },
  { text: '$ add_point  parent:root.0.1  label:"Sticky_Toffee_Pudding"', type: 'cmd', delay: 90 },
  { text: '  → Sticky_Toffee_Pudding      at 1.2.3', type: 'ok', delay: 50 },
  { text: '', type: 'blank', delay: 60 },

  // ── Phase 5: Attributes with spectra ──
  { text: '# Adding attribute spectra...', type: 'comment', delay: 200 },
  { text: '$ add_attribute  coord:1.1  name:"brigade_system"', type: 'cmd', delay: 150 },
  { text: '  spectrum: [classical_french, modern_hybrid, open_kitchen]', type: 'attr', delay: 80 },
  { text: '  default: "classical_french"  ✓', type: 'ok', delay: 60 },
  { text: '$ add_attribute  coord:1.3  name:"plating_tolerance"', type: 'cmd', delay: 120 },
  { text: '  spectrum: [zero_tolerance, minor_variance, creative_freedom]', type: 'attr', delay: 80 },
  { text: '  default: "zero_tolerance"  ✓', type: 'ok', delay: 60 },
  { text: '$ add_attribute  coord:2.3  name:"attentiveness"', type: 'cmd', delay: 120 },
  { text: '  spectrum: [invisible, anticipatory, choreographed, theatrical]', type: 'attr', delay: 80 },
  { text: '  default: "anticipatory"  ✓', type: 'ok', delay: 60 },
  { text: '$ add_attribute  coord:3.3  name:"star_count"', type: 'cmd', delay: 120 },
  { text: '  spectrum: [unstarred, 1_star, 2_stars, 3_stars, 7_michelin]', type: 'attr', delay: 80 },
  { text: '  default: "7_michelin_stars"  ✓', type: 'ok', delay: 60 },
  { text: '$ add_attribute  coord:5.1  name:"sourcing_method"', type: 'cmd', delay: 120 },
  { text: '  spectrum: [wholesale, preferred_vendor, direct_farm, foraging]', type: 'attr', delay: 80 },
  { text: '  default: "direct_farm"  ✓', type: 'ok', delay: 60 },
  { text: '', type: 'blank', delay: 80 },

  // ── Phase 6: Bloom (navigation) ──
  { text: '# Blooming into Kitchen to inspect structure', type: 'comment', delay: 250 },
  { text: '$ bloom  space:GRR  coordinate:"1"', type: 'cmd', delay: 200 },
  { text: '  ◉ Inside Kitchen — 4 children defined:', type: 'bloom', delay: 100 },
  { text: '    1.1 Stations  (6 children, 1 attr)', type: 'data', delay: 60 },
  { text: '    1.2 Menu      (3 children)', type: 'data', delay: 60 },
  { text: '    1.3 Standards (0 children, 2 attrs)', type: 'data', delay: 60 },
  { text: '    1.4 Technique (0 children)', type: 'data', delay: 60 },
  { text: '', type: 'blank', delay: 80 },

  // ── Phase 7: Scry with superposition ──
  { text: '# Scrying with superposition — 0 means "all of this order"', type: 'comment', delay: 300 },
  { text: '$ scry  space:GRR  coordinate:"0.0"', type: 'cmd', delay: 250 },
  { text: '  🔮 Superposition across ALL pillars, ALL depth-2 nodes:', type: 'scry', delay: 120 },
  { text: '    1.1 Stations         1.2 Menu            1.3 Standards', type: 'data', delay: 50 },
  { text: '    1.4 Technique        2.1 Arrival          2.2 Atmosphere', type: 'data', delay: 50 },
  { text: '    2.3 Service          2.4 Pacing           2.5 Departure', type: 'data', delay: 50 },
  { text: '    3.1 Persona          3.2 Media            3.3 Reputation', type: 'data', delay: 50 },
  { text: '    4.1 Executive_Chef   4.2 Sous_Chefs       4.3 Line_Cooks', type: 'data', delay: 50 },
  { text: '    4.4 Front_of_House   4.5 Sommelier        5.1 Protein_Sourcing', type: 'data', delay: 50 },
  { text: '    5.2 Produce          5.3 Wine_Program     ...', type: 'data', delay: 50 },
  { text: '', type: 'blank', delay: 100 },
  { text: '  → 28 nodes resolved across 6 pillars in 4ms', type: 'ok', delay: 150 },
  { text: '', type: 'blank', delay: 100 },

  // ── Phase 8: Targeted scry ──
  { text: '$ scry  coordinate:"1.0"   # all children of Kitchen', type: 'cmd', delay: 200 },
  { text: '  🔮 [Stations, Menu, Standards, Technique]', type: 'scry', delay: 100 },
  { text: '$ scry  coordinate:"1.1.0" # all stations in the brigade', type: 'cmd', delay: 180 },
  { text: '  🔮 [Garde_Manger, Saucier, Rotisseur, Poissonnier, Patissier, Pass]', type: 'scry', delay: 100 },
  { text: '', type: 'blank', delay: 80 },

  // ── Finale ──
  { text: '# 50 nodes · 3 orders deep · 5 attribute spectra · built in <8s', type: 'comment', delay: 400 },
  { text: '# That\'s a full restaurant ontology. From zero.', type: 'comment', delay: 600 },
];

// Color map for line types
function lineColor(type: LineType): string {
  switch (type) {
    case 'cmd': return 'text-gray-200';
    case 'ok': return 'text-emerald-400';
    case 'info': return 'text-gray-500';
    case 'data': return 'text-violet-300/80';
    case 'scry': return 'text-violet-400 font-semibold';
    case 'bloom': return 'text-indigo-400 font-semibold';
    case 'attr': return 'text-amber-400/80';
    case 'blank': return '';
    case 'comment': return 'text-gray-600 italic';
    default: return 'text-gray-400';
  }
}

const VISIBLE_LINES = 18;

export function Terminal() {
  const [visibleCount, setVisibleCount] = useState(0);
  const [copied, setCopied] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Progressive reveal
  useEffect(() => {
    if (visibleCount >= SESSION.length) return;

    const nextLine = SESSION[visibleCount];
    const delay = nextLine?.delay ?? 150;

    timerRef.current = setTimeout(() => {
      setVisibleCount((prev) => prev + 1);
    }, delay);

    return () => clearTimeout(timerRef.current);
  }, [visibleCount]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleCount]);

  // Stats counter
  const cmdCount = SESSION.slice(0, visibleCount).filter((l) => l.type === 'cmd').length;
  const totalCmds = SESSION.filter((l) => l.type === 'cmd').length;
  const progress = Math.round((visibleCount / SESSION.length) * 100);

  const copyToClipboard = () => {
    const commands = SESSION
      .filter((l) => l.type === 'cmd')
      .map((l) => l.text.replace('$ ', ''));
    navigator.clipboard.writeText(commands.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full rounded-xl shadow-2xl shadow-violet-500/10 overflow-hidden bg-gray-950 border border-gray-800/50 font-mono text-xs relative">
      {/* Title bar */}
      <div className="flex justify-between items-center px-4 py-3 border-b border-gray-800/50 bg-gray-900/50">
        <div className="flex items-center gap-3">
          <div className="flex space-x-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
            <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
          </div>
          <span className="text-[11px] text-gray-500 font-sans">
            MCP Agent Session
          </span>
        </div>
        <div className="flex items-center gap-4">
          {/* Live stats */}
          <div className="flex items-center gap-3 text-[10px] font-sans">
            <span className="text-gray-600">
              <span className="text-emerald-400 font-medium">{cmdCount}</span>/{totalCmds} calls
            </span>
            <span className="text-gray-700">|</span>
            <span className="text-gray-600">
              {progress < 100 ? (
                <span className="text-violet-400">{progress}%</span>
              ) : (
                <span className="text-emerald-400">done</span>
              )}
            </span>
          </div>
          <button
            onClick={copyToClipboard}
            className="text-gray-600 hover:text-violet-400 transition-colors"
            aria-label="Copy all commands"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Terminal body — fixed height, scrollable */}
      <div
        ref={scrollRef}
        className="p-4 overflow-y-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-800"
        style={{ height: `${VISIBLE_LINES * 1.375}rem` }}
      >
        <div className="space-y-px">
          {SESSION.slice(0, visibleCount).map((line, i) => (
            <div
              key={i}
              className={`${lineColor(line.type)} leading-relaxed whitespace-pre ${i === visibleCount - 1 ? 'animate-fade-in' : ''
                }`}
              style={{
                animation: i === visibleCount - 1 ? 'fadeIn 0.15s ease-out' : undefined,
              }}
            >
              {line.type === 'blank' ? '\u00A0' : line.text}
            </div>
          ))}
          {/* Blinking cursor */}
          {visibleCount < SESSION.length && (
            <span className="inline-block w-2 h-4 bg-violet-400 animate-pulse" />
          )}
        </div>
      </div>

      {/* Bottom bar — progress strip */}
      <div className="h-0.5 bg-gray-900">
        <div
          className="h-full bg-gradient-to-r from-violet-600 to-indigo-500 transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
