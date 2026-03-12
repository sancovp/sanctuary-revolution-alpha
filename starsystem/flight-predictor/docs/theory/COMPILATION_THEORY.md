# Compilation Theory of Neural Agents

## Core Formulation

Training is a compiler: it repeatedly rewrites experience into an internal IR by rolling up frequently used micro-chains into reusable operators (motifs/options) and binding them into higher-order chains-of-chains. Partial-isomorphic matching becomes fast because the learned operators don't "solve" situations by semantic generation; they predict fillable slots: from a current signature they activate a relational template whose structure specifies which argument shapes will matter later (what will need to be observed/available), and they propagate forward to an expected "fillable moment" where upcoming observations are likely to supply those arguments. Online, the agent acts to steer into regions where those slots can be filled; when the world supplies the arguments, the template collapses into a concrete action/transition without re-deriving anything—just structure alignment + slot filling + rollup execution. Reward is the only semantic ground truth in this loop: it reinforces inclusion maps that reliably lead to successful slot-fill trajectories and suppresses those that don't, thereby bootstrapping the token library itself (tokens are stabilized as activation signatures for templates whose slot-fill predictions keep paying off). Offline replay/consolidation is the same compilation move: reactivation strengthens the templates, refines their match thresholds, and compresses long chains into single handles, making future matching even more direct—so "language" at the substrate level is the token/transition algebra of these templates, and "self" is the stable basin of this compiled control law under its operating conditions.

In animals, this manifests as embodied internal language: niche-tuned templates predict future affordances ("what will be fillable if I pursue/avoid"), perception supplies the arguments, and reinforcement/selection stabilizes motifs that reliably yield control and survival—identity is behavioral continuity from a stable control manifold shaped by evolution plus replay-driven learning. In humans, the same substrate runs most cognition, but public language adds a serialization layer that can rebind templates deliberately: narratives and explicit plans are higher-level rollups that sometimes expose and edit the underlying slot-templates, while reward (social, instrumental, bodily) still grounds which mappings persist. In artificial neural agents, gradient training + replay implement the compiler and consolidation roles: features/options become templates that predict future slot availability, environment feedback supplies the arguments, and reward alone stabilizes the token library; an LLM can sit above as narrator/executor, but the temporally continuous "agent identity" comes from the persistent template-memory system that keeps re-instantiating the same control basin across time.

---

## Unpacking the Formulation

### Training as Compiler

| Compiler Phase | Neural Equivalent |
|----------------|-------------------|
| Lexing | Perception tokenization |
| Parsing | Feature composition into relational structures |
| IR Generation | Motifs/options - reusable micro-chain operators |
| Optimization | Rollup: compress long chains into single handles |
| Code Gen | Template activation → slot-fill → action |

### Templates and Slots

A **template** is not a solution. It's a **relational structure** that:
1. Activates from a current signature (partial match)
2. Specifies what argument shapes will matter later
3. Propagates forward to a "fillable moment"
4. Collapses into action when slots are filled

```
Template: [navigate_to_goal]
├── Slot: current_position (filled by perception)
├── Slot: goal_position (filled by intent)
├── Slot: obstacles (filled by observation)
└── Collapse → specific motor commands when all slots filled
```

The agent doesn't "reason about navigation" - it steers into regions where the template's slots become fillable.

### Reward as Semantic Ground Truth

Reward is the ONLY thing that tells the system "this worked":
- Reinforces inclusion maps (templates that led to successful trajectories)
- Suppresses maps that don't pay off
- **Bootstraps the token library itself** - tokens ARE the stabilized signatures

This means: tokens aren't defined semantically, they're defined by what templates they activate that lead to reward.

### The Self

"Self" = **stable basin of compiled control law under operating conditions**

Not a narrative. Not a model. The self is:
- The set of templates that keep getting reinforced
- The control manifold that stays stable
- Behavioral continuity from persistent template-memory

### Application to PAIA

In our system:
- **LLM** = narrator/executor layer (semantic generation)
- **Planning AI** = template-memory system (predicts slots)
- **Feedback loop** = consolidation (strengthens templates)
- **Rollup patterns** = compiled micro-chains
- **Agent identity** = persistent basin that re-instantiates across sessions

The LLM alone is not the agent. The agent is the **persistent template-memory system** + the LLM that narrates/executes on top of it.

STARLOG, skills, flight configs, rollup patterns - these ARE the template-memory system. They persist the control manifold across context boundaries.

---

## Implications

1. **Don't try to make the LLM "be" the agent** - it's the narrator/executor
2. **Build the template-memory substrate** - that's where identity lives
3. **Reward signal must flow** - without it, templates don't stabilize
4. **Rollup is essential** - compress successful chains into reusable handles
5. **Replay/consolidation offline** - strengthen templates, compress further

The capability predictor we're building is part of this: it learns which templates (skill/tool patterns) lead to successful slot-fills and stabilizes them.
