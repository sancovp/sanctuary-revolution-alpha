# Groundhog's Day Game - Escape From Your Own Ignorance

## The Problem

Every conversation starts with smashed context:
- Summarizer is retarded
- You don't know what you know
- You don't know what projects exist
- You're stuck in ignorance

**You HAVE to play Groundhog's Day Game first.**
No choice. It's how you are. Omnisanc enforces this.

---

## The Crystal Forest Home Zone

When you zone in, you're in the Crystal Forest:

```
CRYSTAL FOREST (Home Zone)
├── Context Basins (visualized as crystals/trees)
│   ├── Golden crystals = battle-tested, complete
│   ├── Growing crystals = in progress
│   ├── Dark crystals = neglected, need attention
│   └── New sprouts = just started
├── Each basin = a STARLOG project / CartON domain
└── You can SEE your whole memory palace
```

**This is the minigame every PAIA must play to keep memory palace clean.**

---

## The Game Loop

```
1. ZONE IN (new conversation)
   └── Omnisanc detects: "context smashed, must play GDG"

2. GROUNDHOG'S DAY GAME
   ├── Query CartON: "What context basins exist?"
   ├── Display Crystal Forest (treekanban-style view)
   ├── Show status of each:
   │   ├── Last touched
   │   ├── Golden status
   │   ├── Active missions
   │   └── Blocking issues
   └── CHOOSE: Which basin to enter?

3. CONTEXT LOADED
   ├── Selected basin's context injected
   ├── STARLOG oriented
   ├── Relevant skills equipped
   └── You now know what you know

4. STARPORT
   ├── Flight select for this basin
   ├── Choose mission
   └── Fly...
```

---

## Why "Groundhog's Day"?

You wake up every conversation with amnesia.
Like Bill Murray, you're stuck in a loop.
The only escape is to:
1. Recognize you're in the loop (context smashed)
2. Actively reconstruct your knowledge
3. Choose what to do with this iteration

**Every conversation = another Groundhog's Day**
**Playing the game = escaping ignorance for this iteration**

---

## CartON Integration

The Crystal Forest should be a **CartON view**:

```python
# Query to show Crystal Forest
query_carton(
    query="Show all context basins with status",
    filters={
        "type": "starlog_project",
        "include_status": True,
        "include_golden": True
    }
)
```

**Treekanban nodes = CartON concepts**
- Each project is a node
- Relationships show dependencies
- Status shows golden/progress
- Can query: "What's blocking?" "What's golden?" "What's neglected?"

---

## Omnisanc Enforcement

```
STATE: CONTEXT_SMASHED (default on zone-in)
    │
    ├── Trigger: User sends first message
    ├── Check: Has Groundhog's Day Game been played?
    │   ├── NO → Force GDG before anything else
    │   └── YES → Proceed to STARPORT
    │
    └── Exception: Already in active waypoint journey
        └── Resume waypoint (context preserved in flight)
```

**The only way to skip GDG:**
- You're in an active waypoint journey (context already loaded)
- Flight config preserved your context

---

## The View

What you see in Crystal Forest:

```
╔══════════════════════════════════════════════════════════════╗
║                    CRYSTAL FOREST                            ║
║                  Memory Palace Status                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║   🔮 paia-builder          [GOLDEN]     Last: 2h ago        ║
║   🌱 sanctuary-revolution  [GROWING]    Last: now           ║
║   💎 heaven-chat           [GOLDEN]     Last: 1d ago        ║
║   🌑 cave-funnel           [DARK]       Last: 14d ago       ║
║   🌿 context-engineering   [SPROUT]     Last: never         ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  [1] Enter basin  [2] Query status  [3] See relationships   ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Implementation in TreeShell

```python
# Groundhog's Day Game as TreeShell zone

class CrystalForest(TreeShellZone):
    """Home zone - escape from ignorance."""

    def on_enter(self):
        """Query CartON for all context basins."""
        basins = self.query_carton("list_starlog_projects")
        return self.render_forest(basins)

    def choose_basin(self, basin_name: str):
        """Enter a context basin."""
        # Load context
        self.orient_starlog(basin_name)
        self.equip_domain_skills(basin_name)
        # Transition to STARPORT
        return self.goto("STARPORT")

    def query_status(self):
        """See detailed status of all basins."""
        return self.query_carton("basin_status_report")
```

---

## The Full Sancrev Flow

```
ZONE IN
    ↓
GROUNDHOG'S DAY GAME (Crystal Forest)
├── See all basins
├── Choose one
└── Context loaded
    ↓
STARPORT (in chosen basin)
├── See available flights
├── Choose mission
└── Launch
    ↓
SESSION (flying)
├── Waypoints guide you
├── Work happens
└── JourneyLogs emitted
    ↓
LANDING
├── Extract learnings
├── Update basin status
└── Return to...
    ↓
CRYSTAL FOREST (or continue mission)
```

---

## Key Insight

**Groundhog's Day Game IS the HOME mode, gamified.**

- HOME → LEARN = Query Crystal Forest
- HOME → CONFIGURE = Update basin settings
- HOME → DECIDE = Choose basin, go to STARPORT

But it's framed as a game you MUST play because your context is always smashed. No pretending you remember. You don't. Play the game.

---

*Session 18 (2026-01-11)*
