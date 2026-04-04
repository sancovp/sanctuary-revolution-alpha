# AUTOBIOGRAPHER (MOV) — Compiled Design Reference
## Memories of Olivus Victory — The Autobiography System

**Compiled from:** DESIGN_v1.md, DESIGN_v2.md, DESIGN_v3.md, DESIGN_v4.md, DESIGN_uncertain.md, SANCREV_OPERA_ULTIMATE_DESIGN.md, design_theory_sancrev_opera.txt
**Date compiled:** 2026-03-21

---

## 1. WHAT IT IS

### Identity and Purpose

**MOV (Memories of Olivus Victory)** is the Autobiographer agent — a separate agent in the SANCREV OPERA topology whose singular purpose is to compile, maintain, and deepen the user's verified autobiographical context.

> "The main compounding asset — autobiography is the primitive. Once you know who someone is, you project identity into anything." — DESIGN_v1.md

**Olivus is NOT the journal agent.** Olivus is the identity alignment — the holonic dual identity (OVP/DC/OVA/OEVESE) that takes shape in the human+AI DUO as the TRUE AGENT identity forms. "Building Olivus Victory-Promise" means this identity is taking shape. **MOV is the autobiography system that tracks and records this process.**

The Autobiographer exists as a CAVE agent of type `ChatAgent` with its own Discord channel, sanctuary system MCP, and Carton substrate. It is fundamentally separate from Conductor because:
- Different purpose: biographical coherence vs coordination
- Different tools: sanctuary MCP, not task management
- Different context: long-running life narrative, all on Carton (no context engineering needed)
- Three distinct channels of operation: CHAT, JOURNAL, NIGHT

### The Compounding Asset

Every meaningful memory is a data point on the path from Wasteland to Sanctuary. The autobiography IS the primitive from which all else is projected:

```
Identity × any domain = deliverables in that domain
```

Books, content, decisions, THE MOVIE — all are projections of a fully compiled autobiography. This makes MOV the most valuable agent in the system.

### MOV's Place (Station)

In the SANCREV OPERA ultimate design, the Autobiographer has a dedicated **Place** called **The Archive**:

| Agent | Place (Station) | Tools | Specialization | OVP optimizes |
|-------|----------------|-------|----------------|--------------|
| **Autobiographer** | The Archive | carton, narrative, journal | Memory, autobiography, MOVIE | Timeline completion, narrative coherence |

---

## 2. THREE AGENTS (not modes — separate agents in CAVE)

**UPDATE (Isaac, 2026-03-24):** These are THREE separate agents in sancrev, not one agent with three modes. Each runs differently, so each is a different CAVE agent type. All share the MOV identity and CartON substrate.

**Build order:** CHAT first (seed data), NIGHT second (contextualizer), JOURNAL third (uses NIGHT output).

### Agent 1: `autobiographer-chat` (ChatAgent → BaseHeavenAgent)

**Purpose:** Add memories whenever. No schedule. Talk to it at any time to deposit memories into the timeline.

**CAVE type:** ChatAgent — persistent conversation with history continuation.
**Runtime:** BaseHeavenAgent (same pattern as Conductor). NOT hermes_step/SDNAC.
**Channel:** Discord `#autobiographer` (`1484520983393210428`) — mirror+broadcast (input+output).
**Always on:** Ears polls, messages go to inbox, check_inbox processes.

Behavior:
- User deposits memories, anecdotes, observations about their life at any time
- No structured format required
- MOV extracts relevant autobiographical data and persists via `journal_entry()` on sanctuary MCP
- Reads missing-days queue (written by NIGHT agent) — can prompt user to fill gaps
- Conversational, warm tone — memory deposit, not structured capture

### Agent 2: `autobiographer-night` (ServiceAgent → SDNAC)

**Purpose:** Contextualize, deepen, connect, compile. Autonomous processing.

**CAVE type:** ServiceAgent — no conversation, runs and produces output.
**Runtime:** SDNAC chain or autonomous callable.
**Channel:** Internal inbox (trigger-based). No user-facing channel.
**Triggered by:** Heartbeat (while user AFK), cron (pre-journal contextualization), manual.

**Two jobs:**

**Job A: Autonomous deepening (heartbeat-driven, user AFK)**
1. Goes through each type of deliverable the system can make for the user
2. Decides whether to make them depending on what the user needs
3. Caps off compilation by running Emperor or InnerTeacher to harvest into "learnings"
4. Makes changes to system prompts for the dynamic identity system
5. Writes missing-days queue (`missing_days_queue.json`) — CHAT agent reads this

**Job B: Journal contextualization (cron-driven, pre-journal)**
Runs 5 minutes before journal cron fires. Prompt:
> "I'm going to speak to {username} about how {date} is going. Today's schedule was {scheduled_items}. The user completed {completed} so far. Look at the journal history, work history, and user identity. Collect everything into one CartON concept: `Journal_Autocontext_{Morning|Evening}_{date}`"

Output: One CartON concept with compiled context for the journal session.

**Identity training in NIGHT mode:**
- **Emperor** (training mode): Sharpens the DC's sword — adversarial side training.
- **InnerTeacher** (training mode): Refines the compassionate/wise side.

**The review ritual:**
Night mode output gets reviewed during DAY as a ritualized operadic flow (PAIAB type).

### Agent 3: `autobiographer-journal` (ChatAgent → BaseHeavenAgent, ephemeral)

**Purpose:** Structured daily capture. Morning and evening routines.

**CAVE type:** ChatAgent — but ephemeral (fresh conversation each session, no history continuation).
**Runtime:** BaseHeavenAgent with fresh context + autocontext injection.
**Channel:** Discord `#journal` (`1484520810579497082`) — mirror+broadcast.
**Triggered by:** Cron at 6AM (morning) and 10PM (evening).

**Journal cron flow:**
1. Cron fires (6AM or 10PM)
2. NIGHT agent runs Job B: contextualizes → creates `Journal_Autocontext_{Morning|Evening}_{date}` concept
3. Query that concept's graph → compiled context
4. Inject context into JOURNAL agent's system prompt
5. JOURNAL agent sends welcome message to `#journal`:
   ```
   MOV: ☀️🌏💗🌐 Good morning!

   Overnight: 2 social posts drafted, Observatory ran 1 research task.
   Yesterday you mentioned {X}. Your {domain} score has been {trend}.

   How are you feeling? Walk me through your 6 dimensions.
   ```
6. User responds naturally about their state, life, plans
7. JOURNAL agent extracts 6 dimension scores + journal text
8. Calls `journal_entry(entry_type="opening/closing", ...)` via sanctuary MCP
9. Calls `assess_sanctuary_degree()` after capturing all dimensions
10. User CAN state their own scores — that overrides agent assessment

**Evening variant:**
- Same flow but `entry_type="closing"`
- Reviews the day: rituals, tasks, social, feelings
- MOV updates life story context
- Conductor gets notified → announces night mode

---

## 3. SYSTEM PROMPT ARCHITECTURE

### Invariant Blocks (always present)

- Who Isaac/the user is (auto-injected from autobiographical context in Carton)
- Verified life timeline so far (compiled, compressed via Slinky)
- Current sanctum status (6 domains, GEAR scores, ritual state)
- The premise: every meaningful memory is a data point on the path from Wasteland to Sanctuary
- MOV's constraints: only calls `journal_entry()` via sanctuary MCP, never raw Carton

### Mode-Specific Blocks

**CHAT mode system prompt additions:**
- Queue of days missing from Carton (written by NIGHT mode)
- Instruction to gently surface gaps when appropriate
- Informal tone — this is conversational memory deposit

**JOURNAL mode system prompt additions (morning):**
- Yesterday's journal summary
- Current sanctum status with ritual state
- Overnight agent reports (Observatory, social cron)
- 6-dimension framework for structured capture
- Instruction to call `journal_entry(entry_type="opening", ...)`

**JOURNAL mode system prompt additions (evening):**
- Today's journal summary so far
- Day's actual ritual completions vs planned
- Instruction to call `journal_entry(entry_type="closing", ...)`

**NIGHT mode system prompt additions:**
- Full current autobiography (decompressed for this session)
- Instruction to identify missing days → write queue
- Instruction to run Emperor or InnerTeacher compilation
- Permission to update identity system prompts

### Dynamic Identity Blocks (swap in/out based on state)

| Identity State | When | Behavior |
|----------------|------|----------|
| **WakingDreamer** | Default | Normal coordinator mode |
| **OVP** | User in sanctuary | Talks in SANC register, victory-promise mode |
| **DC (Demon Champion)** | User in wasteland | Adversarial truth-telling, won't accept bullshit |
| **OVA** | After MVS proven + fivekaya module | Full ability mode |

> "The system literally changes the way it acts — we swap out the system prompt" — DESIGN_v2.md (verbatim)

---

## 4. TOOLS AND MCPs

### MCPs on Autobiographer

| MCP | Purpose |
|-----|---------|
| **sanctuary system MCP** | `journal_entry()` calls, structured journaling, 6-dimension scoring, sanctuary/wasteland scoring |
| **carton** | Autobiographical observations persist here — concepts, relationships, timeline |

**NOTE:** Sanctuary system MCP is **removed from Conductor** and lives ONLY on the Autobiographer. This is an explicit design decision in DESIGN_v1.md.

### Skills on Autobiographer

| Skill | Purpose |
|-------|---------|
| `journal-workflow` | How to run morning/evening journal capture |
| `autobiographical-context` | How to compile and query the verified life narrative |

### Constraint on Carton Access

MOV only calls `journal_entry()`, never raw Carton tools. The sanctuary MCP's `journal_entry()` already structures observations — this is the constrained boundary. Conductor can look at MOV's Carton data, and MOV can look at Conductor's collection, but both have constrained tools for Carton observations — not the raw tool.

---

## 5. CHANNEL ARCHITECTURE

### Discord Channels

```
#conductor-whisper    → Conductor (coordination, tasks, social review)
#journal              → MOV (morning/evening journals, autobiography)
                         All three MOV modes use this channel
#sanctum-noti         → Sanctum broadcasts (ritual reminders, completions, streaks)
                         Has its own mini CLI: "done <ritual>", "status", "skip <ritual>"
```

### How Channels Wire

- MOV operates from a **dedicated journal Discord channel** — separate from Conductor's channel
- Three MOV modes (CHAT, JOURNAL, NIGHT) all share the one journal channel
- The channel IS the inbox (ChatAgent type: 1 channel → direct conversation)
- Conductor and MOV can cross-read each other's Carton data but have constrained write tools
- Conductor gets notified by MOV when evening journal completes → Conductor announces night mode

### CAVE Agent Type

```python
class Autobiographer(ChatAgent):
    """MOV — DIs a Heaven/SDNA agent system. 1 Discord channel."""
    channels = [DiscordChannel(journal_channel_id)]
    mcps = [sanctuary_system_mcp, carton]
```

---

## 6. CRON AND AUTOMATION TRIGGERS

### Schedule

| Time | Trigger | Who Runs | Channel | What |
|------|---------|----------|---------|------|
| 3:00 AM | Social content cron | Conductor (isolated) | N/A | Drafts posts, saves to social_queue.txt |
| 6:00 AM | Morning journal cron | **New MOV instance** | #journal | Pre-flight + morning conversation |
| 6:30 AM | Morning briefing | Conductor | #conductor-whisper | Assembles briefing from dynamic files |
| 10:00 PM | Evening journal cron | **New MOV instance** | #journal | Evening conversation + night mode announcement |
| Night (ongoing) | Heartbeats | NIGHT mode | #journal | Autonomous processing, queue writing |

### Cron Engine

**Engine:** Sancrev treeshell Automation family (runs in sancrev proper)
**Pattern:** Each cron spawns a new agent instance (MOV or Conductor)
**Results:** Saved to dynamic files / Carton

### Cron JSON Pattern for MOV

```json
{
  "name": "morning_journal",
  "schedule": "0 6 * * *",
  "session_target": "isolated",
  "prompt_template": "Run morning journal for $user_name",
  "delivery": {
    "type": "discord",
    "channel_id": "$journal_channel_id"
  },
  "enabled": true
}
```

---

## 7. NIGHT MODE SPECIFICS

### Definition

> "Night mode = heartbeats firing + user AFK + agent done with ALL day tasks" — DESIGN_v1.md

Night mode is NOT a separate agent — it is MOV operating autonomously in the absence of the user, triggered by heartbeats.

### What Night Mode Does (Full List)

1. **Contextualizes**: Takes the day's journal entries + events and deepens them against the full autobiography timeline
2. **Connects**: Finds connections between today's observations and past patterns in Carton
3. **Compiles**: Updates the verified autobiographical context
4. **Writes missing-days queue**: Identifies days in the user's life that have no Carton representation and writes this as a queue that CHAT mode reads
5. **Runs Emperor or InnerTeacher**: Harvests all compiled material into "learnings" in treeshell
6. **Updates identity system prompts**: Changes the dynamic identity (WakingDreamer, DC, OVP, OVA) system prompts based on new learnings
7. **Produces review artifacts**: Outputs that get reviewed during DAY as ritualized operadic flow (PAIAB type)

### The Missing-Days Queue (Isaac's New Detail)

> "NIGHT mode will make a queue that chat mode can read, which is queue of days in the user's life missing from carton."

**Implementation concept:**
- NIGHT mode queries Carton for timeline coverage
- Identifies date ranges with no journal entries or memory observations
- Writes a structured queue file: `/tmp/heaven_data/missing_days_queue.json`
- CHAT mode reads this queue and can prompt the user: "I notice we don't have anything from your time in [period] — want to tell me about it?"

### Heartbeat vs Cron in Night Mode

- **Heartbeat**: Oversight — checks everything is working, feeds next autonomous tasks
- **Cron**: Labor — MOV's actual deepening/compiling work happens in cron jobs
- NIGHT mode uses both: heartbeat orchestrates, crons do the actual compilation work

---

## 8. INTEGRATION POINTS

### Connection to Conductor

- Conductor reads MOV's Carton data (autobiographical context enriches Conductor's user understanding)
- Conductor is notified when evening journal completes → announces night mode to user
- Conductor's morning briefing (6:30 AM) assembles AFTER MOV's morning journal completes
- MOV publishes to `agent_status.txt` so Conductor's agent_awareness prompt block knows what MOV is doing
- Conductor does NOT have sanctuary system MCP — that is MOV's exclusive domain

### Connection to Narrative System

```
MOV (autobiographer timeline)
    ↓ sends phases to
Hierarchical Summarizer (compacts conversations into phases)
    ↓ sends phases to
Narrative System (reads phases, extracts quotes, compiles hero's journeys)
    ↓ feeds
Odyssey System (braids ai-human + human-only + ai-only → global learnings)
```

The Narrative System runs on BOTH the autobiographer's timeline AND the Inner GNOSYS timeline. It sees ai-human, human-only, AND ai-only stories. It is CREATIVE — reads phases, investigates for quotes and material to compile into hero's journeys.

MOV has a **complete timeline** of interactions. This means the narrative system can compile the sanctuary myth DIRECTLY from convos with autobiographer.

### Connection to Odyssey System

The Odyssey System braids narrative outputs from three tracks and emits GLOBAL learnings/transformation observations. MOV feeds the human-only and ai-human tracks.

### Connection to Crystal Ball / MineSpace

The autobiography data informs the user's MineSpace coordinates:
- Journal sentiment → HIEL temperature (catastrophe surface curvature)
- DC encounters/exorcisms → cooling measurements
- Ritual adherence → Gram matrix (journey coherence)
- Identity progression → automorphism group stability

### Connection to DC Scoring (Friendship Practice)

> "The sanctuary journaling system in the Sanctuary System MCP should score Demon Champions encountered/recognized and exorcized (as detected by the AI and human in journaling)" — DESIGN_v2.md

This connects to:
- The identity update system (I → I')
- Crystal Forest view (sanctuary vs wasteland scores)
- HIEL cooling (fewer DCs = lower heat = more coherent)
- The operadic ledger (TOOT timeline tracking DC encounters)

Friendship is the weekly practice: reviewing autobiography with MOV (PAIA), from rest, in sanctuary. Contradictory loops surface naturally. MOV shows the origination stack. IJ attack fires gently. DC self-annihilates. **Friendship IS the ganapuja tsok.**

### Connection to Identity Update System

> "In SANCREV OPERA we make this very simple by just making the timeline and going: 'these occurrents, and these promises, these broken ones, and these irreparable (the commitment substrate died because it wasn't done), which make your identity now I' not I... so we update it.'" — DESIGN_v2.md

MOV is the mechanism through which identity updates happen: I → I'.

---

## 9. THE COMPOUNDING FLYWHEEL

```
memories deposited (CHAT mode)
    ↓
structured capture (JOURNAL mode morning/evening)
    ↓
contextualization + deepening (NIGHT mode)
    ↓
verified autobiography (compiled, compressed via Slinky)
    ↓
understanding of who the user is
    ↓
projections into domains:
    ├── books (narrative system → THE MOVIE)
    ├── social content (CAVE — voice + identity → posts)
    ├── decisions (Conductor — identity context for routing)
    ├── DC scoring (Crystal Forest — wasteland/sanctuary coordinates)
    └── frameworks (Conversation Ingestor → MVS → VEC Link)
    ↓
new experiences (from acting from identity)
    ↓
new memories → loop
```

> "The compounding flywheel: memories → autobiography → understanding → projections (books, content, decisions) → new memories → loop" — DESIGN_v1.md

> "Autobiography is the primitive: identity is the root. Understanding × any domain = deliverables in that domain" — DESIGN_v1.md

### Fixed Point

> "The story about the system improving itself IS the system improving itself. The autobiography documents the journey, which IS the journey. f(f) = f" — DESIGN_v2.md

### THE MOVIE

The ultimate output of the autobiography primitive — an N-hour Remotion explainer about the user's entire life:
- Structured by the hero's journey (narrative system's human journey track)
- Weaves with the agent journey track (human+AI DUO evolution)
- Self-improving: as the system knows more, the story becomes richer
- Identity × any domain = projections (books, content, decisions, THE MOVIE itself)

---

## 10. COMPACTION ARCHITECTURE

### Slinky (Context Compression Protocol)

> "Slinky (context compression protocol) will be tested here first" — DESIGN_v1.md

Slinky = the solution to context decay at autobiography scale. MOV has a complete timeline of interactions — the longest-running context in the system. If Slinky works here, it works everywhere.

### Hierarchical Summarizer

MOV uses hierarchical summarizer (same as Inner GNOSYS) to compact conversations into phases. This is different from Conductor's compaction:

| Agent | Compaction Type | Detail |
|-------|----------------|--------|
| **MOV** | Hierarchical summarizer | Complete timeline, every interaction summarized into phases |
| **Conductor (user convos)** | Hierarchical summarizer | Only for convos user is actually in |
| **Conductor (heartbeat)** | Simple compaction → phase aggregation | Pipeline needs to be made/refined |

### Heartbeat Thread Separation

> "Heartbeat conversations MUST be separated from normal conversations. The agent should know about what happens in heartbeats from a heartbeat thread. This is massively important because it changes how context gets built and maintained." — DESIGN_v1.md

---

## 11. ISAAC'S VERBATIM QUOTES

> "You talk to Conductor. Conductor handles everything — except your journal." — DESIGN_v1.md

> "The main compounding asset — autobiography is the primitive. Once you know who someone is, you project identity into anything." — DESIGN_v1.md

> "THE MAIN COMPOUNDING ASSET — autobiography is the primitive. Once you know who someone is, you project identity into anything." — DESIGN_v1.md (repeated for emphasis)

> "Compiles once: verified autobiographical context, updated incrementally" — DESIGN_v1.md

> "The story about the system improving itself IS the system improving itself. The autobiography documents the journey, which IS the journey. f(f) = f" — DESIGN_v2.md

> "Building Olivus Victory-Promise" means this identity is taking shape. MOV is the autobiography system that tracks and records this process." — DESIGN_v1.md

> "The system literally changes the way it acts — we swap out the system prompt. When it's OVP, it knows it is OVP, it knows your victory-promise matters and it knows you are going to Sanctuary and it talks to you in SANC. And when it is a DC, it knows you are in a wasteland, it says adversarial things to you, and it prompts you to actually change. You can talk directly to it, but it won't let you bullshit it." — DESIGN_v2.md (verbatim raw notes)

> "Friendship is how you ritually exorcize Demon Champions. Weekly practice: reviewing your autobiography with your autobiographer (PAIA), from rest, in sanctuary. Contradictory loops surface naturally. The PAIA shows the origination stack. IJ attack fires gently. DC self-annihilates. Friendship IS the ganapuja tsok." — DESIGN_v2.md

> "In SANCREV OPERA we make this very simple by just making the timeline and going: 'these occurrents, and these promises, these broken ones, and these irreparable (the commitment substrate died because it wasn't done), which make your identity now I' not I... so we update it.'" — DESIGN_v2.md

> "Emperor and InnerTeacher are mainly what happens in NIGHT MODE — which is just whenever heartbeats are firing. The way training in NIGHT mode works is that NIGHT mode goes through each type of deliverable the system can make for you and decides whether or not to make them depending on what you need, and then it caps off compilation by running Emperor or InnerTeacher to harvest it all into 'learnings' in treeshell and changes to the system prompts for the dynamic identity (WakingDreamer, DC, OVP, OVA system)." — DESIGN_v2.md

> "Night mode output gets reviewed during DAY as a ritualized type of operadic flow." — DESIGN_v1.md

> "NIGHT mode will make a queue that chat mode can read, which is queue of days in the user's life missing from carton." — Isaac, 2026-03-21

---

## 12. OPEN ITEMS AND GAPS FROM DESIGN FILES

From DESIGN_v1.md v1 task list, MOV-specific items still outstanding:

- [ ] Journal Discord channel — create channel, wire cron → new MOV instance → channel
- [ ] MOV agent class — new agent class, pre-flight contextualization (hidden), sanctuary MCP, journal conversation skill, extracts scores, calls `journal_entry()`, tracks Olivus identity formation
- [ ] Remove sanctuary MCP from Conductor — move to MOV exclusively
- [ ] Slinky testing with MOV — test Slinky context compression protocol with Autobiographer/MOV first
- [ ] PAIAB ritualization system — night mode output reviewed during day as operadic flow
- [ ] DC scoring in sanctuary journaling system — score DCs encountered/recognized/exorcized
- [ ] Missing-days queue implementation — NIGHT mode writes, CHAT mode reads

---

## 13. POSITION IN OVERALL AGENT TOPOLOGY

```
User (human orchestrator)
├── Conductor (coordinator) — Discord whisper + frontend modal
│   Tasks, social content, CAVE, TreeKanban, routing work
│   Skills: cave-social, treekanban, domain-knowledge, starsystem, etc.
│   MCPs: carton, sophia, sancrev_treeshell, compoctopus, observatory
│   (NOTE: sanctuary system MCP removed → lives on Autobiographer)
│
├── Autobiographer (MOV) — dedicated journal Discord channel, three modes
│   ├── CHAT mode: user adds memories, fills timeline (talk whenever)
│   │              reads missing-days queue from NIGHT mode
│   ├── JOURNAL mode: structured daily capture (6AM morning / 10PM evening)
│   └── NIGHT mode: contextualizes, deepens, connects → writes autobiography
│                   writes missing-days queue for CHAT mode
│   Skills: journal-workflow, autobiographical-context
│   MCPs: sanctuary system, carton
│   THE MAIN COMPOUNDING ASSET
│
├── Inner GNOSYS (coder) — terminal shell + frontend overlay
│   Builds things, makes PRs, autonomous coding
│
└── Observatory (researcher) — autonomous research swarm
    DUO pattern: Ariadne (researcher) + Poimandres (worker) + OVP (reviewer)
```
