import { Button } from '@/components/ui/button';
import { ArrowRight, Sparkles, Layers, Eye, Globe, Zap, Shield, Code2, Target, BookOpen, Brain, Telescope, Infinity, FoldVertical, History, GitBranch } from 'lucide-react';
import { Terminal } from './terminal';
import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="text-white">
      {/* ─── Hero ───────────────────────────────────────── */}
      <section className="relative py-24 overflow-hidden">
        {/* Background gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-violet-600/20 rounded-full blur-[120px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] bg-indigo-600/15 rounded-full blur-[100px]" />
          <div className="absolute top-[40%] left-[50%] w-[300px] h-[300px] bg-purple-500/10 rounded-full blur-[80px]" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-12 lg:gap-12 items-center">
            <div className="sm:text-center lg:col-span-6 lg:text-left">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-sm mb-6">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Now available via MCP</span>
              </div>

              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
                <span className="text-white">The semantic lens</span>
                <br />
                <span className="bg-gradient-to-r from-violet-400 via-purple-400 to-indigo-400 bg-clip-text text-transparent">
                  that makes AI precise.
                </span>
              </h1>
              <p className="mt-5 text-lg text-gray-400 max-w-xl sm:mx-auto lg:mx-0">
                What started as a prompt engineering technique for constraining LLM generation became a full coordinate system. Crystal Ball turns any domain into navigable semantic geometry — so your AI generates exactly what you mean, and nothing else.
              </p>
              <div className="mt-8 flex flex-wrap gap-3 sm:justify-center lg:justify-start">
                <Button
                  asChild
                  size="lg"
                  className="rounded-full bg-violet-600 hover:bg-violet-500 text-white border-0 text-base px-6"
                >
                  <Link href="/sign-up">
                    Start Building
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="rounded-full border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white text-base px-6"
                >
                  <a href="https://github.com/sancovp/crystal-ball" target="_blank">
                    <Code2 className="mr-2 h-4 w-4" />
                    View Source
                  </a>
                </Button>
              </div>
            </div>
            <div className="mt-14 relative sm:max-w-lg sm:mx-auto lg:mt-0 lg:max-w-none lg:mx-0 lg:col-span-6 lg:flex lg:items-center">
              <Terminal />
            </div>
          </div>
        </div>
      </section>

      {/* ─── The Three Layers ──────────────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold sm:text-4xl">
              Structure{' '}
              <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
                × Intelligence
              </span>{' '}
              <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                × Intent
              </span>
            </h2>
            <p className="mt-4 text-gray-400 text-lg max-w-3xl mx-auto">
              Before Crystal Ball, there was a prompt called CIG — the Constrained Informatihedron Generator. It described property boundaries in natural language and asked the LLM to stay inside. Crystal Ball is what happens when you make those boundaries <em className="text-violet-300">structural</em> — navigable coordinates instead of verbal instructions.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Layers className="h-6 w-6" />}
              title="Structure (the space)"
              description="CIG described three property levels — instance, domain, class — with 'fiat conceptual boundaries' at each level. Crystal Ball makes them real: each level is a navigable coordinate with attributes that enforce those boundaries as spectra."
            />
            <FeatureCard
              icon={<Brain className="h-6 w-6" />}
              title="Intelligence (the LLM)"
              description="CIG told the model 'generate property descriptions within these boundaries.' Crystal Ball does one better — the coordinate system itself constrains generation. The model can't hallucinate off-axis because off-axis doesn't have an address."
            />
            <FeatureCard
              icon={<Target className="h-6 w-6" />}
              title="Intent (the human)"
              description="CIG's Informadlib pipeline mapped user intent through six stages to reach a constrained output. Crystal Ball replaces that pipeline with a coordinate: you point, the structure constrains, the LLM fills. Your intent becomes addressable geometry."
            />
          </div>
        </div>
      </section>

      {/* ─── Origin Story ──────────────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm mb-6">
                <History className="h-3.5 w-3.5" />
                <span>Origin story</span>
              </div>
              <h2 className="text-3xl font-bold sm:text-4xl mb-6">
                From{' '}
                <span className="bg-gradient-to-r from-rose-400 to-amber-400 bg-clip-text text-transparent">
                  algebra
                </span>{' '}
                to{' '}
                <span className="bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
                  prompt
                </span>{' '}
                to{' '}
                <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
                  structure.
                </span>
              </h2>
              <p className="text-gray-400 text-lg mb-6">
                It started as <strong className="text-rose-300">IIC</strong> — the Instance Instancing Chain. A raw combinatorial algebra that mapped every entity to a four-axis coordinate system (Domain × Class × Process × Instance), with 1-9 positions per digit and 0 as the superordinate of all.
              </p>
              <p className="text-gray-400 text-lg mb-6">
                Then came <strong className="text-amber-300">CIG</strong> — the Constrained Informatihedron Generator. It simplified the algebra into natural language: &ldquo;instance boundaries are flexible, domain boundaries are firm, class boundaries are hard.&rdquo; Verbal confinement — the LLM obeyed because you asked nicely.
              </p>
              <p className="text-gray-400 text-lg mb-6">
                Crystal Ball makes the confinement <em className="text-violet-300">geometric</em>. The boundaries aren&apos;t instructions anymore — they&apos;re coordinates. You can&apos;t generate outside them because outside doesn&apos;t <em>exist</em>.
              </p>
              <p className="text-gray-400 text-lg">
                The proof? When we booted the IIC as a Crystal Ball space, its own rule — &ldquo;positions 1-9 only, 0 is the superordinate&rdquo; — was <em className="text-emerald-300">already enforced by the coordinate system</em>. The grandfather&apos;s algebra is compiled into the grandchild&apos;s runtime.
              </p>
            </div>
            <div className="mt-12 lg:mt-0">
              <div className="bg-gray-900 border border-gray-800/50 rounded-xl overflow-hidden">
                <div className="px-6 py-3 border-b border-gray-800/50 flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  </div>
                  <span className="text-gray-500 text-xs font-mono">evolution</span>
                </div>
                <div className="p-6 font-mono text-sm space-y-3">
                  <div>
                    <div className="text-rose-400/80 text-xs mb-1">// IIC — algebraic confinement</div>
                    <div className="text-rose-300/50 text-xs leading-relaxed">
                      Xid=1.1 Domain [root]<br />
                      Yid=1.2 Class [trunk]<br />
                      Zid=1.3 Process [branch]<br />
                      iid=1.4 Instance [leaf]<br />
                      <span className="text-rose-300/70">&quot;0 = superordinate of 1-9&quot;</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-gray-700">
                    <GitBranch className="h-3 w-3" />
                    <span className="text-xs">simplified into</span>
                  </div>
                  <div>
                    <div className="text-amber-400/80 text-xs mb-1">// CIG — verbal confinement</div>
                    <div className="text-amber-300/50 text-xs leading-relaxed">
                      Instance boundaries: [flexible]<br />
                      Domain boundaries: [firm]<br />
                      Class boundaries: [hard]
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-gray-700">
                    <GitBranch className="h-3 w-3" />
                    <span className="text-xs">compiled into</span>
                  </div>
                  <div>
                    <div className="text-violet-400/80 text-xs mb-1">// Crystal Ball — structural confinement</div>
                    <div className="text-white text-xs leading-relaxed">
                      <span className="text-violet-400">1.2</span> Instance.Boundaries{' '}
                      <span className="text-gray-600">[rigidity:</span>{' '}
                      <span className="text-emerald-400">flexible</span>
                      <span className="text-gray-600">]</span><br />
                      <span className="text-violet-400">2.2</span> Domain.Boundaries{' '}
                      <span className="text-gray-600">[rigidity:</span>{' '}
                      <span className="text-yellow-400">firm</span>
                      <span className="text-gray-600">]</span><br />
                      <span className="text-violet-400">3.2</span> Class.Boundaries{' '}
                      <span className="text-gray-600">[rigidity:</span>{' '}
                      <span className="text-red-400">hard</span>
                      <span className="text-gray-600">]</span>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-gray-800">
                    <div className="text-emerald-400 text-xs">
                      → IIC: &quot;positions 1-9, 0 = superordinate&quot;<br />
                      → CB scry: &quot;index 9+ mapped to 0 (superposition)&quot;<br />
                      <span className="text-emerald-300">→ The algebra was already in the runtime.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Coordinate Explainer ──────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold sm:text-4xl mb-6">
                Coordinates are{' '}
                <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                  semantic paths
                </span>
              </h2>
              <p className="text-gray-400 text-lg mb-6">
                A coordinate like{' '}
                <code className="text-violet-300 bg-violet-500/10 px-1.5 py-0.5 rounded text-sm">
                  3.1.1
                </code>{' '}
                isn&apos;t just an address — it&apos;s a path through layers of meaning.
                Each dot crosses an ontological order.
                And{' '}
                <code className="text-violet-300 bg-violet-500/10 px-1.5 py-0.5 rounded text-sm">
                  0
                </code>
                {' '}means &quot;all members of this order&quot; — a semantic wildcard.
              </p>
              <div className="space-y-4">
                <CoordExample
                  coord="1"
                  description="The first property of this Thing"
                />
                <CoordExample
                  coord="1.3"
                  description="Third subclass of the first property"
                />
                <CoordExample
                  coord="1.0"
                  description="ALL subclasses of the first property"
                />
                <CoordExample
                  coord="0.0"
                  description="Every subclass of every property"
                />
                <CoordExample
                  coord="0.0.0"
                  description="Everything × Everything × Everything"
                />
              </div>
            </div>
            <div className="mt-12 lg:mt-0">
              <div className="bg-gray-900 border border-gray-800/50 rounded-xl p-6 font-mono text-sm">
                <div className="text-gray-500 mb-3">// Space: Restaurant</div>
                <div className="space-y-1">
                  <div className="text-white">
                    <span className="text-gray-500">root</span> — Restaurant
                  </div>
                  <div className="text-white pl-4">
                    <span className="text-violet-400">1</span> — Kitchen
                    <span className="text-gray-600 text-xs ml-2">← properties</span>
                  </div>
                  <div className="text-white pl-8">
                    <span className="text-violet-400">1.1</span> — Saucier
                    <span className="text-gray-600 text-xs ml-2">← subclasses</span>
                  </div>
                  <div className="text-white pl-8">
                    <span className="text-violet-400">1.2</span> — Patissier
                  </div>
                  <div className="text-white pl-8">
                    <span className="text-violet-400">1.3</span> — Grill
                  </div>
                  <div className="text-white pl-4">
                    <span className="text-violet-400">2</span> — Brand
                  </div>
                  <div className="text-white pl-8">
                    <span className="text-violet-400">2.1</span> — Persona
                  </div>
                  <div className="text-white pl-8">
                    <span className="text-violet-400">2.2</span> — Media
                  </div>
                  <div className="text-white pl-4">
                    <span className="text-violet-400">3</span> — Supply
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-gray-800">
                  <div className="text-gray-500 mb-1.5">
                    scry <span className="text-violet-400">&quot;1.0&quot;</span> →{' '}
                    <span className="text-green-400">
                      [Saucier, Patissier, Grill]
                    </span>
                  </div>
                  <div className="text-gray-500 mb-1.5">
                    scry <span className="text-violet-400">&quot;0.0&quot;</span> →{' '}
                    <span className="text-green-400">
                      [Saucier, Patissier, Grill, Persona, Media, ...]
                    </span>
                  </div>
                  <div className="text-gray-500">
                    bloom <span className="text-violet-400">&quot;1&quot;</span> →{' '}
                    <span className="text-emerald-400">
                      Inside &quot;Kitchen&quot; — 3 slots defined
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── The Abstraction Ladder ──────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold sm:text-4xl">
              Spaces{' '}
              <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
                fold into spaces.
              </span>{' '}
              All the way up.
            </h2>
            <p className="mt-4 text-gray-400 text-lg max-w-3xl mx-auto">
              Start with a concrete instance. Compose it into groups. Fold groups into empires. Extract the pattern. Abstract to any category. The template describes how to build templates.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-4 mb-12">
            <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-violet-500/30 transition-colors text-center">
              <div className="text-2xl mb-2">🍳</div>
              <div className="text-sm font-semibold text-white mb-1">Order 1</div>
              <div className="text-xs text-gray-500">A single restaurant</div>
              <div className="text-xs text-violet-400 font-mono mt-2">50 nodes</div>
            </div>
            <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-violet-500/30 transition-colors text-center">
              <div className="text-2xl mb-2">🏢</div>
              <div className="text-sm font-semibold text-white mb-1">Order 2</div>
              <div className="text-xs text-gray-500">Regional group of restaurants</div>
              <div className="text-xs text-violet-400 font-mono mt-2">5 spaces folded</div>
            </div>
            <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-violet-500/30 transition-colors text-center">
              <div className="text-2xl mb-2">👑</div>
              <div className="text-sm font-semibold text-white mb-1">Order 3</div>
              <div className="text-xs text-gray-500">Culinary empire</div>
              <div className="text-xs text-violet-400 font-mono mt-2">16 spaces, 120+ nodes</div>
            </div>
            <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-violet-500/30 transition-colors text-center">
              <div className="text-2xl mb-2">♾️</div>
              <div className="text-sm font-semibold text-white mb-1">Order N</div>
              <div className="text-xs text-gray-500">Template of templates</div>
              <div className="text-xs text-violet-400 font-mono mt-2">the quine</div>
            </div>
          </div>

          <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 max-w-3xl mx-auto font-mono text-sm">
            <div className="text-gray-500 mb-3">// The seven-step abstraction ladder</div>
            <div className="space-y-1.5">
              <div><span className="text-violet-400">1.</span> <span className="text-white">Concrete Instance</span> <span className="text-gray-600">— a restaurant with kitchens, brands, teams</span></div>
              <div><span className="text-violet-400">2.</span> <span className="text-white">Composition</span> <span className="text-gray-600">— group restaurants by region</span></div>
              <div><span className="text-violet-400">3.</span> <span className="text-white">Fold into Empire</span> <span className="text-gray-600">— groups become nodes in a meta-space</span></div>
              <div><span className="text-violet-400">4.</span> <span className="text-white">Solution Space</span> <span className="text-gray-600">— extract the pattern: what makes any empire work?</span></div>
              <div><span className="text-violet-400">5.</span> <span className="text-white">Category Abstraction</span> <span className="text-gray-600">— generalize beyond restaurants to any domain</span></div>
              <div><span className="text-violet-400">6.</span> <span className="text-white">Meta-Composition</span> <span className="text-gray-600">— the pattern of patterns (empire of empires)</span></div>
              <div><span className="text-violet-400">7.</span> <span className="text-white">Governance</span> <span className="text-gray-600">— oversight that governs itself too</span></div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 text-gray-500">
              <span className="text-emerald-400">→ The template describes how to build templates.</span>
              <br />
              <span className="text-emerald-400">→ The solution space of the trajectory IS the trajectory.</span>
              <br />
              <span className="text-violet-300">→ composedCoordinate: &quot;1234567.1&quot;</span>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Use Cases ─────────────────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold sm:text-4xl">
              What people are{' '}
              <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
                building
              </span>
            </h2>
            <p className="mt-4 text-gray-400 text-lg max-w-2xl mx-auto">
              Any domain that has structure has geometry. Crystal Ball gives that geometry coordinates — and your LLM a space it can&apos;t hallucinate outside of.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <UseCaseCard
              emoji="🏢"
              title="Organizational Design"
              example="Departments → Teams → Roles → Skills"
              description="Map an entire org as a space. Fold departments into divisions, divisions into the company. Scry across every role in one coordinate."
            />
            <UseCaseCard
              emoji="🍳"
              title="Restaurant Empires"
              example="Restaurant → Group → Empire → Category King"
              description="We built a 16-space, 120-node, 7-layer hierarchy that produced a genuine quine. In 3 minutes. From a single restaurant."
            />
            <UseCaseCard
              emoji="🧠"
              title="Agent Memory"
              example="Contexts → Concepts → Relations → Actions"
              description="Give your AI agent a coordinate system for knowledge. It can bloom into any concept, scry across relationships, and resolve attributes."
            />
            <UseCaseCard
              emoji="🎮"
              title="Game World Design"
              example="Zones → NPCs → Quests → Rewards"
              description="Each game world is a space. Fold worlds into campaigns, campaigns into universes. The agent generates content within the ontology."
            />
            <UseCaseCard
              emoji="📐"
              title="Product Architecture"
              example="Features → Components → APIs → Tests"
              description="Model your product as a space. The LLM generates implementations constrained by the coordinate structure. No hallucinated APIs."
            />
            <UseCaseCard
              emoji="⚖️"
              title="Governance Frameworks"
              example="Constitution → Authority → Accountability → Coherence"
              description="Self-referential governance: the framework governs the empire that contains the categories that the framework oversees."
            />
          </div>
        </div>
      </section>

      {/* ─── API / Integration ─────────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold sm:text-4xl mb-4">
            Seven primitives.{' '}
            <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
              That&apos;s the whole API.
            </span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto mb-12">
            Create a space. Add points. Bloom inside. Scry coordinates. Add attributes with a spectrum of valid values.
            Connected via MCP or direct HTTP.
          </p>

          <div className="grid sm:grid-cols-4 gap-4 max-w-4xl mx-auto mb-12">
            <ApiCard cmd="create_space" desc="Define a new Thing" />
            <ApiCard cmd="add_point" desc="Add a child at any depth" />
            <ApiCard cmd="bloom" desc="Enter a node's interior" />
            <ApiCard cmd="scry" desc="Navigate by coordinate" />
            <ApiCard cmd="add_attribute" desc="Define a value spectrum" />
            <ApiCard cmd="get_space" desc="Full space structure" />
            <ApiCard cmd="list_spaces" desc="All your spaces" />
            <ApiCard cmd="resolve" desc="Collapse to concrete values" />
          </div>

          <div className="grid sm:grid-cols-4 gap-6 max-w-4xl mx-auto">
            <StatCard number="16" label="Spaces" sublabel="built in one session" />
            <StatCard number="120+" label="Nodes" sublabel="across 7 abstraction layers" />
            <StatCard number="<50ms" label="Latency" sublabel="p95 response time" />
            <StatCard number="1" label="Quine" sublabel="the template describes itself" />
          </div>
        </div>
      </section>

      {/* ─── CTA ───────────────────────────────────────── */}
      <section className="py-20 border-t border-gray-800/50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-violet-500/10 border border-violet-500/20 mb-6">
            <Telescope className="h-8 w-8 text-violet-400" />
          </div>
          <h2 className="text-3xl font-bold sm:text-4xl mb-4">
            CIG was the idea.
            <br className="hidden sm:block" />{' '}
            <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
              Crystal Ball is the machine.
            </span>
          </h2>
          <p className="text-gray-400 text-lg mb-8 max-w-xl mx-auto">
            From prompt-level confinement to structural coordinates. Define the space. Let AI generate within it. Get exactly what you mean.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button
              asChild
              size="lg"
              className="rounded-full bg-violet-600 hover:bg-violet-500 text-white border-0 text-base px-8"
            >
              <Link href="/sign-up">
                Get Your API Key
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="rounded-full border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-white text-base px-8"
            >
              <Link href="/pricing">View Pricing</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ─── Footer ────────────────────────────────────── */}
      <footer className="border-t border-gray-800/50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="text-sm text-gray-500">
            © {new Date().getFullYear()} Crystal Ball. The semantic lens that makes AI precise.
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-500">
            <a href="https://github.com/sancovp/crystal-ball" target="_blank" className="hover:text-gray-300 transition-colors">
              GitHub
            </a>
            <Link href="/pricing" className="hover:text-gray-300 transition-colors">
              Pricing
            </Link>
          </div>
        </div>
      </footer>
    </main >
  );
}

// ─── Sub-components ───────────────────────────────────────────────

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-violet-500/30 transition-colors group">
      <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-violet-500/10 text-violet-400 group-hover:bg-violet-500/20 transition-colors mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm leading-relaxed">{description}</p>
    </div>
  );
}

function CoordExample({
  coord,
  description,
}: {
  coord: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <code className="px-3 py-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-300 font-mono text-sm min-w-[80px] text-center">
        {coord}
      </code>
      <span className="text-gray-400 text-sm">{description}</span>
    </div>
  );
}

function StatCard({
  number,
  label,
  sublabel,
}: {
  number: string;
  label: string;
  sublabel: string;
}) {
  return (
    <div className="p-5 rounded-xl bg-gray-900/50 border border-gray-800/50">
      <div className="text-3xl font-bold bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
        {number}
      </div>
      <div className="text-white font-medium mt-1">{label}</div>
      <div className="text-gray-500 text-xs mt-1">{sublabel}</div>
    </div>
  );
}

function ApiCard({
  cmd,
  desc,
}: {
  cmd: string;
  desc: string;
}) {
  return (
    <div className="p-4 rounded-lg bg-gray-900/50 border border-gray-800/50 text-left">
      <code className="text-violet-300 text-sm font-mono">{cmd}</code>
      <div className="text-gray-500 text-xs mt-1">{desc}</div>
    </div>
  );
}

function UseCaseCard({
  emoji,
  title,
  example,
  description,
}: {
  emoji: string;
  title: string;
  example: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800/50 hover:border-violet-500/30 transition-colors group">
      <div className="text-3xl mb-3">{emoji}</div>
      <h3 className="text-base font-semibold text-white mb-1">{title}</h3>
      <p className="text-violet-400/80 text-xs font-mono mb-2">{example}</p>
      <p className="text-gray-500 text-sm leading-relaxed">{description}</p>
    </div>
  );
}
