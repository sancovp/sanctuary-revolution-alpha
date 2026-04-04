# DESIGN v4 — ASPIRATIONAL: WisdomMaverick as Meta-WD

> WM is a meta-WD system. It DIs the WD and the CAVEHTTPServer and can fully shut it down, evolve it, swap it, and everything — while running.

---

## The Full Stack

```
v1: CAVE library (types, server, channels)
v2: WakingDreamer(CAVEAgent) — runtime god object, hot-reloads config
v3: SDNA DUO re-encoding — TOOTs, Sophia, Compoctopus
v4: WisdomMaverick — meta-WD, hot-swaps the entire WD while running
```

## WisdomMaverick

```python
class WisdomMaverick:
    """Meta-WD. DIs the WD + server.
    Can shut down, evolve, swap — while running."""
    
    def __init__(self):
        self.wd = WakingDreamer()
        self.server = CAVEHTTPServer(8080, self.wd)
    
    def evolve(self, new_wd):
        """Hot-swap the entire WD while running."""
        self.server.pause()
        self.wd = new_wd
        self.server.cave = self.wd
        self.server.resume()
```

## Two Levels of Reflectivity

| Level | What | How |
|-------|------|-----|
| **v2 (WD)** | Changes behavior | Hot-reloads config file |
| **v4 (WM)** | Changes the system itself | Hot-swaps the entire WD |

WD doesn't know it's inside a WM. WM can evolve, test, swap, roll back — the whole WD — while running.

## Sophia's Execution Environment

Sophia runs FROM the WM level, looking DOWN at WD:

```
WisdomMaverick
  └── Sophia (operates here — sees everything from above)
       ├── introspects WD
       ├── decides evolution
       ├── Compoctopus compiles new WD components
       ├── Observatory fork tests them
       └── WM.evolve(new_wd) — hot-swaps
```

## The Fold (v3 → v4)

In v3, WM holds WD + HTTPServer and we code stuff in the space between them (Sophia, Compoctopus, DUO chains, etc.).

In v4, WM folds on itself: it can reconfigure ALL of its internals — agents, chains, workflows, evolution rules — without touching code. The code is complete and fixed. All complexity is added through:
- Config (hot-reload)
- Ontology (SDNA chains)
- TOOTs (compiled DUO workflows)

The code never needs to change to add more complexity. That's the fixed point. Evolution happens through the system's own mechanisms, not through engineering.

- v3 = build the meta-layer (code it)
- v4 = the meta-layer becomes self-modifying (stop coding, start configuring)

## ArtificialWisdomMaverick (AWM)

v4 is not WM itself — it's a subtype: **ArtificialWisdomMaverick**.

An AWM is a system that runs a **Sophia heartbeat** that evolves its underlying CAVEHTTPServer (the runtime of the WD that the WM has). Therefore, an AWM can evolve a WD **without a human**.

```python
class ArtificialWisdomMaverick(WisdomMaverick):
    """Runs Sophia heartbeat. Evolves WD autonomously."""
    
    def __init__(self):
        super().__init__()
        self.sophia = SophiaHeartbeat(wm=self)
        # Sophia continuously:
        #   introspects self.wd
        #   decides evolution
        #   compiles via Compoctopus
        #   tests via Observatory
        #   calls self.evolve(new_wd)
        # No human in the loop.
```

The "artificial" part IS the Sophia heartbeat — it substitutes for the human wisdom that normally drives evolution. A regular WM needs a human (OVP). An AWM has Sophia instead.

```
WisdomMaverick              — needs human OVP to evolve
  └── ArtificialWisdomMaverick  — Sophia IS the OVP, evolves autonomously
```
