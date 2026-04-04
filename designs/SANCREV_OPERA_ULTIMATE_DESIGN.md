# SANCREV OPERA — Ultimate Vision Design
## The Living Meta-Frontend

**Status:** SINGLE CANONICAL DESIGN  
**Date:** 2026-03-20  
**Version:** 1.1

---

## CORE INSIGHT

**Nothing changes. Everything increases.**

The current app — with its spaces, modals, dock, kanban, CaveAgentModal, ConductorChatModal, TreeKanban, Crystal Ball, Sanctum — is the **seed**. It already works. It already has the right structure.

The vision is the **growth trajectory**: over time, the agent's ability to understand and modify the frontend increases until it can build buttons, spaces, commands, styles, routes, and components autonomously. The user watches it happen in real-time through the chat and sees the results in the frontend.

This is not a rewrite. This is not a pivot. The app **increases to the point** where:
- The agents can modify the frontend hot
- The user mostly directs and navigates
- Construction happens through conversation
- The kanban stays current automatically

### The Illusion (which is actually real)

The agent runs on the **backend** (mind_of_god container). The chat lives in the **meta-shell** (toolbar layer, outside the webview). The inner app runs in the **webview** (localhost:5173, Vite dev server).

So from the user's perspective:
- The **chat** is where the agent lives — its voice, its personality
- The **inner app** is what the agent creates — its body, its workspace, its world
- **Place mode** makes this literal: the character IS the agent, the Place IS its domain

The user is not "using an app." The user is **talking to an entity that shapes reality around them.**

They say: *"build me a task tracker"* — and the inner app morphs. Components appear. Styles render. Routes wire up. The agent did it. The user watched.

They say: *"I don't like the layout"* — and it morphs again. Instantly. Because Vite HMR is sub-second.

They say: *"show me my schedule"* — and a new view materializes. Because the agent wrote it. Committed it. The webview hot-reloaded it.

**The app is not a product. The app is a medium. The agent is the artist. The user is the patron.**

And the meta-frontend architecture makes this mechanically real — not a metaphor, not aspirational. The agent literally writes React components and the user literally sees them appear in real-time. The two-layer split (shell vs inner app) means the agent can modify anything in the inner app without ever touching the shell. The git history tracks every change. The user owns everything.

### Places = Stations

A **Place** is an agent's domain. When you enter an agent's Place, you are in their world. The inner app morphs. The aesthetic shifts. The tools change. The personality is different.

In the TOOT railroad allegory (see CAVE_V1_ROADMAP), a Place maps to a **Station**. A Station is a Place that has been wrapped with an **OVP (optimizer agent)** — a DUO pattern where the OVP watches the work happening in that Place, scores it, and improves it over time.

```
Place   = Agents doing work (avatar, voice, tools, aesthetic, psychoblood)
Station = Place + OVP optimizer (watches, scores, improves the Place)
TOOT    = The graph of Stations (optimizers over workflows of agents)
```

**The big idea of the TOOT (railroad allegory) view:** you are adding **optimizers over workflows of agents.** Stations are *places about places* — meta-level optimization layers. The OVP at each Station doesn't route work. It **watches** the work, **scores** the output, and **improves** the process. This is why Stations connect to STARSYSTEM: every Station is a self-improving node because the OVP scores every run.

And because OVPs are themselves agents in Places, they can have their own OVPs. Optimization all the way up.

Each Place has:
- **Avatar** — the agent's visual representation (character model, image, animation)
- **Voice** — TTS voice profile, speaking style, cadence
- **Specialization** — what the agent is good at, what tools it has access to
- **Constrained tools** — some agents have full access (GNOSYS), others have scoped access (Conductor coordinates but doesn't code)
- **Aesthetic** — background, color scheme, ambient effects, mood
- **Psychoblood flow** — emotion prompts and RNG that pump personality state through the agent, making it feel alive and variable

Each Station adds:
- **OVP** — the optimizer agent that watches this Place and improves it
- **Scoring** — STARSYSTEM metrics for every run (the self-improving loop)

| Agent | Place (Station) | Tools | Specialization | OVP optimizes |
|-------|----------------|-------|----------------|--------------|
| **Conductor** | The Stage | kanban, delegation, scheduling | Coordination, onboarding, task routing | Delegation quality, user satisfaction |
| **GNOSYS / PAIA** | The Forge | treeshell, write/edit, bash, carton | Implementation, code generation | Code quality, build success, HMR latency |
| **Crystal Ball** | The Observatory | crystal-ball MCP, scrying | Ontological navigation | Domain coverage, kernel validity |
| **Sanctum** | The Garden | rituals, schedule, reflection | Personal practice, daily rhythm | Ritual adherence, GEAR progression |
| **Autobiographer** | The Archive | carton, narrative, journal | Memory, autobiography, MOVIE | Timeline completion, narrative coherence |

The user **moves between Places** by talking to different agents (or the Conductor routes them). Each Place has a different feel, different capabilities, different personality. The inner app morphs to match — because the agent at that Station is the one shaping the webview.

At the highest level (v5: FinalGNOSYS), the user doesn't explicitly switch Places. They just talk, and FinalGNOSYS operates the entire TOOT internally. The Places and their OVPs are still there — the user just doesn't have to navigate them manually. The railroad runs itself, and the optimizers keep making it better.

### The Evolution

```
TODAY (seed):
  ├── Static spaces, manually coded components
  ├── Conductor chat modal with SSE events
  ├── CaveAgent modal for CAVE state inspection
  ├── TreeKanban, Crystal Ball, Sanctum — all built by developer
  ├── Dock with fixed icons
  └── User navigates between pre-built views

    ↓ (add Place mode — DONE)

NEAR-TERM (sprout):
  ├── Place mode on conductor modal (character + chat overlay)
  ├── Character configurator
  ├── Emotion-mapped character rendering
  ├── Same existing spaces, now with agent Place layer
  └── Agent can respond with identity-state emotions + psychoblood

    ↓ (add hot frontend iframe)

MID-TERM (growth):
  ├── MetaShell splits screen: Place (chat) + hot frontend (iframe)
  ├── Existing views move into hot frontend iframe
  ├── Agent can write/modify files → iframe hot-reloads
  ├── Dock becomes dynamic (agent adds/removes icons)
  ├── Conductor introduces new views naturally in conversation
  └── Request → kanban card → GNOSYS builds → frontend updates

    ↓ (agent capability increases)

LONG-TERM (tree):
  ├── Agent builds entire new views from conversation
  ├── User says "build me X" → watches it appear
  ├── Frontend is fully agent-hot, continuously deployed
  ├── Multiple agent personalities with different Places (Stations)
  ├── Progressive revelation: new users start with just chat
  └── Full operating system — all grown from the seed
```

**The architecture doesn't change at any point.** The same Electron app. The same React components. The same Vite build. The same Docker bridge to mind_of_god. What changes is the **degree of agent autonomy** over the frontend. Today: zero (developer builds it). Tomorrow: partial (agent can modify some things). Eventually: full (agent builds everything).

---

## THE RESPONSIBILITY SPLIT

> This describes the end-state. Today the developer builds UI manually. 
> The split shifts progressively toward agent autonomy.

### What the AGENT does (increasing over time)

The agent **progressively gains the ability** to build:
- Buttons, controls, interactive elements
- Spaces, views, pages, layouts
- Commands, shortcuts, macros
- Styles, themes, color schemes
- Routes, navigation, dock items
- Data schemas, storage, state management
- Cards, tasks, deliverables on the kanban

It does this using `treeshell`, `write/edit`, `carton`, and `bash`. As its understanding of the system architecture increases, it can modify more of the frontend in real-time. The user watches it happen. Tool calls appear in the chat. Changes appear in the hot frontend. It becomes **mostly automatic** — the user says what they want, the agent builds it.

### What the USER does (constant across all phases)

The user's role stays the same throughout the evolution:
- **Chat** — tell the agent what to do, ask questions, give feedback
- **Navigate** — click dock icons, switch views, browse the frontend
- **Manual edits** — directly edit files when they want precise control (notes, text, data)
- **Review** — read what the agent built, approve or request changes

That's it. The user **directs** and **navigates**. The agent **constructs** and **maintains**. The more capable the agent becomes, the less the user has to touch.

### The Interaction Model (end-state)

```
┌─────────────────────────────────────────────────────────────┐
│                        USER TOUCHES                         │
│                                                             │
│   [Chat input]  [Dock clicks]  [File edits]  [Navigation]  │
│        ↓              ↓             ↓              ↓       │
│    Requests      View switch    Manual data    Browse UI    │
│        ↓              ↓             ↓              ↓       │
│   ┌──────────────────────────────────────────────────────┐  │
│   │                   AGENT CONTROLS                     │  │
│   │                                                      │  │
│   │  Buttons   Spaces   Commands   Styles   Routes       │  │
│   │  Cards     Views    Schemas    Themes   Components   │  │
│   │  Layouts   Icons    Logic      Data     Everything   │  │
│   │                                                      │  │
│   │  == the entire hot frontend is agent-written ==      │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

Key consequence at end-state: **there is no "developer builds the UI" step.** The agent IS the developer. The user is the product owner. The chat is the sprint planning. The kanban is the backlog. The hot frontend is the deployed product — deployed continuously, to a local iframe, in real-time.

---

## ARCHITECTURE: THE META-FRONTEND PATTERN

**Status: IMPLEMENTED** (`meta-shell.html` + `electron/main.ts`)

The meta-frontend is a thin wrapper around the entire existing app. Electron loads `meta-shell.html` which contains:

```
┌──────────────────────────────────────────────────────┐
│  [◀][▶][🔄]  localhost:5173/...    [✓ 0] [🌌 Chat] [🔧] │  ← Toolbar (38px)
├──────────────────────────────────────────────────────┤
│                                                      │
│                   <webview>                           │
│                                                      │
│    The ENTIRE existing app runs here unchanged.      │
│    Spaces, dock, sidebar, modals — everything.       │
│    Loaded from the Vite dev server (dev) or           │
│    file:// dist/index.html (prod).                   │
│                                                      │
│    This is what agents modify via write/edit/bash.   │
│    Vite HMR picks up changes → webview updates.     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

With chat panel open:

```
┌──────────────────────────────────────────────────────┐
│  [◀][▶][🔄]  localhost:5173/...    [✓ 0] [🌌 Chat] [🔧] │
├──────────────────────────────────────────┬───────────┤
│                                          │ 🎼 Agent  │
│                                          │   Chat    │
│              <webview>                   │           │
│           (full app here)                │  [msgs]   │
│                                          │  [msgs]   │
│                                          │           │
│                                          │  [input]  │
└──────────────────────────────────────────┴───────────┘
```

### The Toolbar

- **Navigation:** back, forward, reload (Cmd+R)
- **URL bar:** shows current webview URL + status dot (loading/connected/error)
- **Error badge:** captures JS errors from inside the webview, red when errors exist, click to expand console
- **Chat toggle (Ctrl+\\):** opens/closes agent chat panel on the right
- **DevTools (Cmd+Shift+I):** opens devtools for the inner app

### Implementation Files

| File | Role |
|------|------|
| `meta-shell.html` | Self-contained toolbar + webview shell (inline CSS + JS, no build step) |
| `electron/main.ts` | Loads meta-shell.html, enables `webviewTag`, injects app URL |
| `index.html` + `src/` | The existing app — runs inside the webview, completely unchanged |

### Key Properties

1. **The existing app is untouched.** It runs in a `<webview>` exactly as before.
2. **The toolbar is outside the app.** It has its own error tracking, reload, and devtools control.
3. **The agent chat panel** sits beside the webview, not inside it. Agent and app are separate layers.
4. **Vite HMR works normally.** When agents write files, Vite picks up changes, the webview hot-reloads.

---

## DEPLOYMENT ARCHITECTURE: TWO-LAYER UPDATE MODEL

The system has two independently versioned layers with different update frequencies:

### Layer 1: Electron Shell (the "browser")

**Changes:** Rarely. Only when toolbar, webview container, or Electron/node deps change.

Contains:
- `meta-shell.html` — toolbar + webview container
- `electron/main.ts` — process management (spawns Vite, DockerBridge, Orchestrator)
- `electron/preload.ts` — IPC bridge

**Update mechanism:** CI/CD pipeline

```
Shell code changes pushed to git
    ↓
CI builds SANCREV_v{n+1}.app (or .dmg/.exe)
    ↓
Installed SIDE-BY-SIDE with current v{n}
    ↓
User launches latest version (or auto-switch on next start)
    ↓
Webview connects to same localhost:5173 — inner app unchanged
```

The shell is like a browser: you update Chrome occasionally, but your web apps keep working.

### Layer 2: Inner App (the "website")

**Changes:** Constantly. Agents edit this. Users customize this. It grows.

Contains:
- `src/` — all React components, spaces, modals, styles
- `index.html` — app entry point
- `package.json` — frontend dependencies

**Update mechanism:** Vite HMR (instant, zero-downtime)

```
Agent writes/edits a file in src/
    ↓
Vite dev server (localhost:5173) detects change
    ↓
HMR pushes update to <webview> via WebSocket
    ↓
User sees change instantly — no reload, no rebuild
```

The inner app source lives in a **git repo the user owns**. The agent commits changes. The user can review, rollback, branch, etc. The git history IS the changelog.

### Why This Works

| Concern | Solution |
|---------|----------|
| Shell needs update? | CI/CD builds `_v{n+1}`, installs side-by-side, old version still works |
| Inner app needs update? | Agent edits source → Vite HMR → instant |
| User wants to rollback? | `git revert` on inner app source |
| User wants to customise? | Edit files directly, Vite picks it up |
| New user onboarding? | `git clone` the inner app repo, Electron shell auto-connects |
| Multiple environments? | Different inner app repos, same shell |

### The Three Servers

Electron spawns and manages three localhost services:

| Server | Port | What it does | When to restart |
|--------|------|-------------|-----------------|
| **Vite Dev Server** | 5173 | Serves inner app with HMR | Never (auto-restarts) |
| **Docker Bridge** | 5051 | Host ↔ Container communication | On container changes |
| **Orchestrator** | 8090 | Agent commands, TTS, harness | On agent config changes |

All three are spawned by `electron/main.ts` on app start, health-checked, and auto-restarted on crash. The user never has to think about them.

### Production Hot Mode

In production, the Electron shell ships with the inner app source bundled as `app-source/`. On first launch, it copies this to a user-writable directory (e.g. `~/SANCREV/app-source/`), spawns Vite against it, and the webview connects. From that point on, agents can edit files in that directory, and changes appear live.

The user owns the source. The agent modifies it. Vite keeps it hot. Git tracks the history. The shell just displays it.

---

## USER JOURNEY

### Phase 1: First Contact

User opens SANCREV OPERA for the first time.

They see: **A Place. A character. A chat input.**

Nothing else. No sidebar. No kanban. No settings explosion. Just:

> **Conductor:** Welcome to SANCREV OPERA. I'm your Conductor — I coordinate everything that happens here. What would you like to work on?

The user types something. The Conductor responds. Maybe asks clarifying questions. The character's emotion shifts based on the conversation mode.

### Phase 2: Introduction to Aspects

As the conversation develops, the Conductor **introduces aspects** of the system naturally:

> **Conductor:** I've created a project board to track what we're working on. You can see it below.

The dock gains an icon. The hot frontend iframe shows the TreeKanban board. The kanban has the user's first card on it.

> **Conductor:** I'm handing this task to GNOSYS. GNOSYS is the knowledge and implementation layer — it does the actual work. I stay here to coordinate.

### Phase 3: Direct GNOSYS Chat

The user can choose to chat with GNOSYS directly (switch to GNOSYS's Place). GNOSYS is deeper, more technical, more philosophical. It uses the same tools but has a different personality.

Either way — whether the user talks to Conductor or GNOSYS — **the kanban stays updated.** Every request becomes a card. Every deliverable updates a card. This happens through GNOSYS's normal workflow (TreeShell + Carton + write/edit).

### Phase 4: The Hot Frontend Grows

As the user works more, the hot frontend accumulates views:
- **TreeKanban** — task board (always there after introduction)
- **Crystal Ball** — ontological navigation (introduced when relevant)
- **Sanctum** — ritual/habit tracker (introduced when requested)
- **Day Logger** — schedule view (introduced when relevant)
- **Custom views** — whatever GNOSYS builds on request

Each gets a dock icon. The user clicks dock icons to switch views in the iframe. The agents can also switch the view programmatically.

### Phase 5: Full Operating System

Eventually the user has a full suite of views, all agent-managed, all live, all hot. They can:
- Chat with Conductor for coordination
- Chat with GNOSYS for deep work
- See their kanban updating in real-time
- Navigate Crystal Ball for domain exploration
- Track habits through Sanctum
- Request new features and watch them get built

**This is the product.**

---

## AGENT TOOL ARCHITECTURE

### What the agents use to control everything

```
TOOL LAYER (what makes things happen):
├── TreeShell        — file system operations, directory management
├── write/edit       — create and modify files (components, data, config)
├── Carton           — knowledge graph, persistent memory, card management
├── bash             — system commands, process control, dev server

STATE LAYER (what controls agent behavior):
├── Crystal Ball     — ontological state machine, domain navigation  
├── Skill Manager    — agent capability management
├── YOUKNOW          — validation, UARL, ontology reification
├── Starlog          — session history, context tracking
└── TTS Avatar       — voice output, emotion animation
```

**Key insight:** The TOOL LAYER directly modifies the frontend. The STATE LAYER only changes what the agents know and how they behave. The user sees the results of the TOOL LAYER in the hot frontend. The user talks to the agents through the Place chat.

### Hot Frontend Mechanics

```
Agent writes file → Dev server detects change → iframe hot-reloads
```

The hot frontend runs a Vite dev server (or similar). GNOSYS uses `write` and `edit` tools to create/modify React components, CSS, and data files. Vite's HMR picks up the changes. The iframe shows the update instantly.

This means:
- GNOSYS can create a new dashboard → user sees it appear
- GNOSYS can modify a kanban card → the board updates
- GNOSYS can restyle a component → colors change live
- GNOSYS can add a dock icon → new view becomes available

---

## COMPONENT MAP

### Meta-Frontend Shell (`MetaShell.tsx`)

The outermost container. Manages the split between Agent Place and Hot Frontend.

```typescript
interface MetaShellState {
  // Place
  placePosition: 'top' | 'right' | 'floating' | 'minimized';
  placeSize: number; // percentage of screen for Place
  activeAgent: 'conductor' | 'gnosys' | string; // which agent's Place is active
  
  // Hot Frontend
  hotFrontendUrl: string; // iframe src
  activeView: string;     // which dock view is active
  availableViews: DockView[]; // introduced aspects
  
  // Dock
  dockPosition: 'bottom' | 'left';
}

interface DockView {
  id: string;
  name: string;
  icon: string;
  route: string;       // path within hot frontend
  introduced: boolean; // has the Conductor introduced this?
  visible: boolean;    // show in dock?
}
```

### Agent Place (`RoomView.tsx` — already built, rename to `PlaceView.tsx`)

The character + chat overlay we just created. Extended with:
- Agent switching (Conductor ↔ GNOSYS ↔ custom PAIAs)
- Tool call visibility (show write/edit/treeshell calls inline)
- Kanban card creation from chat (Conductor creates cards from requests)

### Hot Frontend Container (`HotFrontend.tsx`)

```typescript
interface HotFrontendProps {
  url: string;           // dev server URL
  activeRoute: string;   // current view route
  onRouteChange: (route: string) => void;
}
```

Simple iframe with:
- Reload on file change notification (SSE from dev server or polling)
- Route communication (postMessage to change view)
- Error boundary (show friendly error if iframe fails)

### Dock (`Dock.tsx` — already exists, enhance)

Currently shows static icons. Enhance to:
- Start empty (or with just Conductor icon)
- Gain icons as Conductor introduces aspects
- Each icon maps to a route in the hot frontend
- Visual indicator for active view
- Agent can programmatically add/remove/reorder dock items

---

## REQUEST → DELIVERABLE → CARD FLOW

```
User says: "Build me a habit tracker"
         │
         ▼
Conductor receives message
         │
         ├─ Creates kanban card: "Build habit tracker" [STATUS: TODO]
         │  (via Carton + TreeShell write to card data)
         │
         ├─ Routes to GNOSYS: "Build a habit tracker component"
         │
         ▼
GNOSYS works:
  1. treeshell: create component directory
  2. write: HabitTracker.tsx  
  3. write: HabitTracker.css
  4. write: habit data schema
  5. edit: router to include new view
  6. carton: update card status → IN_PROGRESS
         │
         ▼
Hot frontend hot-reloads → user sees habit tracker appear
         │
         ▼
GNOSYS:
  7. carton: update card status → DONE
  8. conductor notification: "Habit tracker is ready"
         │
         ▼
Conductor:
  - Adds dock icon for Habit Tracker
  - Tells user: "Your habit tracker is ready. I've added it to your dock."
  - Character emotion: happy
```

---

## FILE STRUCTURE

```
agent-control-panel/
  src/
    components/
      MetaShell.tsx              ← NEW: outermost container
      MetaShell.css
      RoomView.tsx               ← EXISTS: agent room with character
      RoomView.css
      CharacterDisplay.tsx       ← EXISTS: emotion-mapped character
      CharacterDisplay.css
      CharacterConfigurator.tsx  ← EXISTS: character editor
      CharacterConfigurator.css
      HotFrontend.tsx            ← NEW: iframe container
      HotFrontend.css
      Dock.tsx                   ← EXISTS: enhance with dynamic views
      ConductorChatModal.tsx     ← EXISTS: room mode integrated
      ConductorChatModal.css
    lib/
      characterManager.ts        ← EXISTS: character system
      agentRouter.ts             ← NEW: routes messages to conductor/gnosys
      viewManager.ts             ← NEW: manages introduced views/dock state
      hotReload.ts               ← NEW: SSE listener for frontend changes
    
  hot-frontend/                  ← NEW: separate Vite app served in iframe
    src/
      views/
        TreeKanban/              ← moved from main app
        CrystalBall/             ← moved from main app  
        Sanctum/                 ← moved from main app
        DayLogger/               ← moved from main app
        ... (agent-created views appear here)
      App.tsx                    ← router for views
      main.tsx
    vite.config.ts
    package.json
```

---

## WHAT THIS REPLACES

| Old Pattern | New Pattern |
|-------------|-------------|
| Static sidebar with all features | Dock that grows as Conductor introduces things |
| Modal-based chat windows | Persistent Place with character |
| User navigates to features | Conductor introduces features when relevant |
| Frontend is developer-built only | Frontend is agent-modifiable in real-time |
| Separate admin panel vs product | Single unified experience |
| Multiple disconnected views | Hot frontend with router, all in one iframe |

---

## ASPIRATIONAL: FUTURE EVOLUTION

> These are vision items, not current implementation:

- **ASPIRATIONAL:** Multiple Places — GNOSYS has a different aesthetic/Station than Conductor
- **ASPIRATIONAL:** Place themes change based on identity state (WakingDreamer Place vs DC Place)
- **ASPIRATIONAL:** Social feed in Place (like OpenRoom) showing system activity
- **ASPIRATIONAL:** Voice input/output via TTS Avatar MCP
- **ASPIRATIONAL:** Agent-to-agent conversations visible in Place (Conductor delegating to GNOSYS)
- **ASPIRATIONAL:** User creates their own PAIA agents with custom Places
- **ASPIRATIONAL:** Marketplace for Place themes, characters, and view templates
- **ASPIRATIONAL:** Mobile-responsive Place mode for phone/tablet

---

## IMPLEMENTATION PHASES

### Phase A: Meta-Frontend Shell (current sprint)
- [x] RoomView component (→ PlaceView)
- [x] CharacterDisplay component  
- [x] CharacterConfigurator
- [x] Place mode toggle in ConductorChatModal
- [ ] MetaShell container (Place + iframe split)
- [ ] HotFrontend iframe component
- [ ] Dynamic dock (starts empty, grows)

### Phase B: Hot Frontend
- [ ] Separate Vite app for hot-frontend
- [ ] Move TreeKanban, CrystalBall, Sanctum into hot-frontend/views
- [ ] Router within hot-frontend
- [ ] HMR/hot-reload detection in iframe
- [ ] PostMessage communication (meta-frontend ↔ hot-frontend)

### Phase C: Agent Control Flow
- [ ] Agent router (conductor vs gnosys message routing)
- [ ] Card creation from chat (request → kanban card)
- [ ] View introduction protocol (conductor introduces aspects)
- [ ] GNOSYS file writing → hot-reload → user sees result
- [ ] Tool call visibility in Place chat

### Phase D: Polish
- [ ] Progressive introduction experience (empty → full OS)
- [ ] Place aesthetics per agent (Station theming)
- [ ] Emotion integration with TTS Avatar
- [ ] Keyboard shortcuts (Cmd+K for chat, etc.)
- [ ] Error recovery (iframe failures, agent disconnects)

---

## PRINCIPLES

1. **Chat-first.** Everything starts from conversation. No feature is presented without context.
2. **Agent-hot.** The frontend is a living artifact that agents modify. Not a static build.
3. **Hands-off construction.** The user directs. The agent builds. The user never has to write a component, style a button, or wire a route. They say what they want and watch it happen.
4. **Progressive revelation.** The user discovers features through the Conductor, not through a settings menu.
5. **Kanban is truth.** Every request becomes a card. Every deliverable updates a card. The board is always current.
6. **Two personalities.** Conductor coordinates. GNOSYS implements. User chooses who to talk to.
7. **Place is home.** The character, background, and chat are always there. The Place is the constant. The hot frontend changes. Each agent's Place (Station) has its own aesthetic, voice, and psychoblood.
8. **Manual override always available.** The user can always directly edit files, add notes, tweak data. The agent respects manual edits and incorporates them. The user is never locked out of the filesystem.
9. **Operate through chat, view in frontend.** The chat is the control surface where work happens. The frontend is the render surface where results appear. Same data, two perspectives — one for direction, one for viewing.
