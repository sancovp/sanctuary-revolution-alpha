"""
PIO-UARL Bridge: Generative Analogical Reach

When you find a compareFrom (bridge), you've discovered a PIOEntity.
That PIOEntity spawns children that become NEW reach paths.

The A-B-C-D structure:
  A (intuition) with B (compareFrom) embodies C (mapsTo) wrt D (analogicalPattern)

PIO fills this in:
1. Notice: A → C needs a bridge
2. Discover: Find B that connects them
3. The connection A-B-C IS a PIOEntity (hyperedge)
4. Spawn: B becomes an entity, D (pattern) becomes learnable
5. Future: B can be compareFrom for other analogies

The more you use PIO, the more reach paths you create.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    from youknow_kernel.pio import PIOEngine, PIOEntity, PolysemicPattern
except ImportError:
    PIOEngine = None


@dataclass
class AnalogicalBridge:
    """The A-B-C-D structure for a valid embodies claim."""
    
    intuition: str          # A - what you're thinking about
    compareFrom: str        # B - the bridge that makes it work
    mapsTo: str             # C - where it maps to
    analogicalPattern: str  # D - the pattern discovered
    
    # Metadata
    discovered_at: datetime = field(default_factory=datetime.now)
    reach_length: int = 0   # How many hops from A to C
    
    def as_dict(self) -> Dict[str, str]:
        return {
            'intuition': self.intuition,
            'compareFrom': self.compareFrom,
            'mapsTo': self.mapsTo,
            'analogicalPattern': self.analogicalPattern
        }


class AnalogicalReachEngine:
    """Engine for discovering and extending analogical reach.
    
    Every bridge discovered creates new reach paths.
    PIOEntities are the hyperedges that connect things.
    Children spawn as we find bridges.
    """
    
    def __init__(self, pio_engine: Optional[PIOEngine] = None):
        self.pio = pio_engine or (PIOEngine() if PIOEngine else None)
        
        # Discovered bridges
        self.bridges: List[AnalogicalBridge] = []
        
        # Reach graph: what can reach what via what bridge
        self.reach_graph: Dict[str, Dict[str, List[str]]] = {}
        # { from: { to: [bridges that connect them] } }
        
        # Spawned entities from bridge discovery
        self.spawned: List[str] = []
        
        # Learned patterns
        self.patterns: Dict[str, List[str]] = {}
        # { pattern_name: [examples] }
    
    def compute_reach(self, from_concept: str, to_concept: str) -> Dict[str, Any]:
        """Compute the reach from A to C.
        
        Returns:
        - direct: True if there's a known bridge
        - bridges: List of known bridges
        - reach_length: Hops needed
        - suggestion: If no bridge, suggest how to find one
        """
        # Check if we have a direct bridge
        if from_concept in self.reach_graph:
            if to_concept in self.reach_graph[from_concept]:
                bridges = self.reach_graph[from_concept][to_concept]
                return {
                    'direct': True,
                    'bridges': bridges,
                    'reach_length': 1,
                    'suggestion': None
                }
        
        # Check reverse
        if to_concept in self.reach_graph:
            if from_concept in self.reach_graph[to_concept]:
                bridges = self.reach_graph[to_concept][from_concept]
                return {
                    'direct': True,
                    'bridges': bridges,
                    'reach_length': 1,
                    'direction': 'reverse',
                    'suggestion': None
                }
        
        # No direct bridge - suggest how to find one
        return {
            'direct': False,
            'bridges': [],
            'reach_length': float('inf'),
            'suggestion': f"To connect {from_concept} → {to_concept}, find a 'compareFrom' (B) that shares properties with both. What does {from_concept} have that could relate to {to_concept}?"
        }
    
    def discover_bridge(
        self,
        intuition: str,      # A
        compareFrom: str,    # B
        mapsTo: str,         # C
        analogicalPattern: str  # D
    ) -> Dict[str, Any]:
        """Discover a new bridge and spawn children.
        
        This is the core operation:
        1. Create the bridge
        2. Register in PIO as hyperedge
        3. Spawn B and D as entities
        4. Add to reach graph
        """
        # Create bridge
        bridge = AnalogicalBridge(
            intuition=intuition,
            compareFrom=compareFrom,
            mapsTo=mapsTo,
            analogicalPattern=analogicalPattern,
            reach_length=1
        )
        self.bridges.append(bridge)
        
        # Add to reach graph
        if intuition not in self.reach_graph:
            self.reach_graph[intuition] = {}
        if mapsTo not in self.reach_graph[intuition]:
            self.reach_graph[intuition][mapsTo] = []
        self.reach_graph[intuition][mapsTo].append(compareFrom)
        
        spawned_entities = []
        
        # === SPAWN CHILDREN VIA PIO ===
        if self.pio:
            # 1. Discover the hyperedge connecting A-B-C
            hyperedge_name = f"{intuition}_{compareFrom}_{mapsTo}_Bridge"
            self.pio.discover_isomorphism(
                thing_a=intuition,
                thing_b=mapsTo,
                name=hyperedge_name,
                discoverer_id='analogical_reach'
            )
            self.pio.add_to_potential(hyperedge_name, compareFrom)
            self.pio.propose_source(
                hyperedge_name,
                analogicalPattern,
                f"{compareFrom} bridges {intuition} to {mapsTo}"
            )
            
            # 2. Reify the hyperedge
            entity = self.pio.reify(
                potential_name=hyperedge_name,
                source_category=analogicalPattern,
                description=f"Bridge from {intuition} to {mapsTo} via {compareFrom}"
            )
            
            if entity:
                spawned_entities.append(entity.name)
                
                # 3. Spawn compareFrom as standalone entity
                compareFrom_entity = PIOEntity(
                    name=compareFrom,
                    description=f"Bridge concept that connects {intuition} to {mapsTo}",
                    is_a=[analogicalPattern, 'Bridge_Concept'],
                    pattern=PolysemicPattern(
                        name=f"{compareFrom}_Pattern",
                        description=f"{compareFrom} as bridge in analogical reasoning",
                        context_slots=['source', 'target'],
                        inheritable_properties={
                            'is_bridge': True,
                            'connects': [intuition, mapsTo]
                        }
                    )
                )
                self.pio.register_entity(compareFrom_entity)
                spawned_entities.append(compareFrom)
                self.spawned.append(compareFrom)
        
        # Learn the pattern
        if analogicalPattern not in self.patterns:
            self.patterns[analogicalPattern] = []
        self.patterns[analogicalPattern].append(f"{intuition}→{compareFrom}→{mapsTo}")
        
        return {
            'bridge': bridge.as_dict(),
            'spawned': spawned_entities,
            'reach_improved': True,
            'pattern_strengthened': analogicalPattern
        }
    
    def suggest_bridges(self, from_concept: str, to_concept: str) -> List[str]:
        """Suggest potential bridges based on learned patterns.
        
        Uses existing bridges and patterns to suggest compareFrom candidates.
        """
        suggestions = []
        
        # Check if either concept has been a bridge before
        for bridge in self.bridges:
            if bridge.intuition == from_concept:
                # This concept has bridged to something else
                suggestions.append(f"Try using '{bridge.compareFrom}' pattern")
            if bridge.mapsTo == to_concept:
                # This was the target of a previous bridge
                suggestions.append(f"Previous bridge to {to_concept} used '{bridge.compareFrom}'")
        
        # Check patterns that might apply
        for pattern, examples in self.patterns.items():
            suggestions.append(f"Pattern '{pattern}' has been used {len(examples)} times")
        
        return suggestions
    
    def get_all_reach_paths(self) -> Dict[str, List[str]]:
        """Get all known reach paths."""
        paths = {}
        for from_c, targets in self.reach_graph.items():
            paths[from_c] = list(targets.keys())
        return paths


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== ANALOGICAL REACH ENGINE ===")
    print()
    
    engine = AnalogicalReachEngine()
    
    # 1. Check reach without bridge
    print("1. CHECK REACH: Dog → Pirate (no bridge)")
    reach = engine.compute_reach('Dog', 'Pirate')
    print(f"   Direct: {reach['direct']}")
    print(f"   Suggestion: {reach['suggestion']}")
    print()
    
    # 2. Discover a bridge
    print("2. DISCOVER BRIDGE: Dog -[Patchy]-> Pirate")
    result = engine.discover_bridge(
        intuition='Dog',
        compareFrom='Patchy',
        mapsTo='Pirate',
        analogicalPattern='Eye_Patch_Accessory'
    )
    print(f"   Bridge: {result['bridge']}")
    print(f"   Spawned: {result['spawned']}")
    print(f"   Pattern: {result['pattern_strengthened']}")
    print()
    
    # 3. Check reach again
    print("3. CHECK REACH: Dog → Pirate (with bridge)")
    reach = engine.compute_reach('Dog', 'Pirate')
    print(f"   Direct: {reach['direct']}")
    print(f"   Bridges: {reach['bridges']}")
    print()
    
    # 4. Add another bridge using similar pattern
    print("4. DISCOVER ANOTHER: Cat -[Hook]-> Pirate")
    result = engine.discover_bridge(
        intuition='Cat',
        compareFrom='Hook',
        mapsTo='Pirate',
        analogicalPattern='Pirate_Accessory'
    )
    print(f"   Spawned: {result['spawned']}")
    print()
    
    # 5. Check suggestions for new analogy
    print("5. SUGGEST BRIDGES: Wolf → Pirate")
    suggestions = engine.suggest_bridges('Wolf', 'Pirate')
    for s in suggestions:
        print(f"   - {s}")
    print()
    
    # 6. All reach paths
    print("6. ALL REACH PATHS:")
    for from_c, targets in engine.get_all_reach_paths().items():
        print(f"   {from_c} → {targets}")
