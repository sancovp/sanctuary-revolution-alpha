# DESIGN v3 — ASPIRATIONAL: The Meta-Compiled Sanctuary System

> If we were gonna code the real sanctuary system, it would be whatever CAVE → SANCREV gives us then RE-ENCODED through SDNA chain ontology using OVP: [A→P] loops in TOOTs (chains of DUO calls).

This is v3. A meta-compiled system.

---

## The Stack

```
v1: CAVE library (CAVEHTTPServer, Agent types, channels, inbox)
v2: WakingDreamer(CAVEAgent) — the runtime, the god object
v3: WM holds WD + HTTPServer as a runtime container. SDNA DUO re-encoding.
    Sophia, Compoctopus, Observatory added here. We code stuff in this space.
v4: WM folds on itself — can reconfigure all internals without touching code.
    All complexity added through config/ontology/chains. Code is fixed.
```

## Core Concept

Every part of the system that v2 implements imperatively (agents, routing, heartbeat, cron, channels) gets re-encoded as SDNA chain ontology:

- Every interaction is a DUO (two agents IO)
- Every workflow is a TOOT (chain of DUOs)
- Compoctopus compiles concepts into TOOTs
- WakingDreamer runs TOOTs
- The top-level DUO is User ↔ WakingDreamer

```
User ↔ WakingDreamer                    (top-level DUO)
         └── runs TOOTs                  (compiled by Compoctopus)
              └── TOOT = chain of DUOs   (SDNA chain ontology)
                   └── each DUO = [A→P]  (Agent → Prompt loop)
```

## What This Means

- **TOOT** is NOT the CAVEAgent. TOOT is the compiled workflow artifact.
- **WakingDreamer** is NOT a TOOT. WakingDreamer runs TOOTs.
- **Compoctopus** produces TOOTs from concepts.
- **WisdomMaverick** is what the system already IS by construction (SDNA = DUOs at every level). You don't code WM — it emerges from using SDNA.
- A compiled WisdomMaverick IS an OVA.
- **Sophia** is the wisdom module of WakingDreamer. She introspects the entire WD system, decides how to evolve it, compiles evolution through Compoctopus, tests via an Observatory fork, and loops. Sophia can queue research on herself. She IS the lucidity of the WakingDreamer — the part that makes it wake up.
- **Compoctopus** is HOW Sophia makes them (the compiler tool).
- Sophia introspects → decides evolution → Compoctopus compiles → Observatory tests → loop. That's the v3 self-improvement cycle.

## DUO Encoding

SDNA chains already implement the DUO pattern. So:

```
v2 (imperative):
  Conductor.handle_message(msg) → response

v3 (SDNA DUO chain):
  DUO(User, Conductor)
    .chain(DUO(Conductor, InnerGNOSYS))
    .chain(DUO(Conductor, OpenClaw))
```

Everything that v2 does with method calls and routing, v3 does with DUO chains. The behavior is the same. The encoding is different. The encoding makes the WisdomMaverick pattern visible at every level.

## OVP Encoding

OVP (Omniscient Viewer Perspective) in v3 is encoded as the [A→P] loop:

- A = Agent (the system acting)
- P = Prompt (the user's perspective/intent)
- The loop: Agent acts → Prompt evaluates → Agent adjusts → ...

Building OVP = encoding the user's oversight perspective into the A→P loops of every TOOT. The system learns how the user sees by running these loops.

## Why This Is v3 (Not Now)

v2 (WakingDreamer) needs to work first. You can't meta-compile what doesn't exist yet. The path is:

1. **v1**: Fix CAVE library (CAVEHTTPServer, ChatAgent, etc.)
2. **v2**: Build WakingDreamer(CAVEAgent) with 3 agents, working system
3. **v3**: Re-encode through SDNA chain ontology → TOOTs → WisdomMaverick by construction

v3 is the endgame. v2 is next. v1 is now.
