# DEAD CODE — Commented out 2026-03-29. Not imported by anything. Y-Mesh neuronal architecture not yet wired.
# """
# YOUKNOW Y-Mesh: Neuronal Ontology Architecture

# Y-STRATA (the neurons):
  # Y₁: Upper Ontology - observation types
  # Y₂: Domain Ontology - subject buckets
  # Y₃: Application Ontology - operations per domain
  # Y₄: Instance Ontology - actual things
  # Y₅: Instance Type Ontology - patterns from instances
  # Y₆: Instance Type Application - operations implementing patterns

# O-STRATA (the synapses):
  # IS loop - taxonomic/type flow
  # HAS loop - compositional/part flow

# All layers interact neuronally. Activation propagates.
# When Y₆ activation exceeds threshold → codegen triggers.
# """

# from typing import Dict, List, Set, Optional, Any, Callable
# from dataclasses import dataclass, field
# from enum import Enum
# from datetime import datetime
# import math


# class YLayer(str, Enum):
    # """The six Y-strata layers."""
    # Y1_UPPER = "y1"        # Observation types
    # Y2_DOMAIN = "y2"       # Subject buckets
    # Y3_APPLICATION = "y3"  # Operations per domain
    # Y4_INSTANCE = "y4"     # Actual instances
    # Y5_PATTERN = "y5"      # Patterns from instances
    # Y6_IMPLEMENTATION = "y6"  # Operations implementing patterns


# class OLoop(str, Enum):
    # """The two O-strata loops."""
    # IS = "is"     # Taxonomic (what IS it)
    # HAS = "has"   # Compositional (what does it HAVE)


# @dataclass
# class YNode:
    # """A node in a Y-layer."""
    # name: str
    # layer: YLayer
    # content: Dict[str, Any] = field(default_factory=dict)
    # activation: float = 0.0
    
    # # Connections to other nodes
    # is_a: List[str] = field(default_factory=list)
    # has_part: List[str] = field(default_factory=list)
    # part_of: List[str] = field(default_factory=list)
    # produces: List[str] = field(default_factory=list)
    
    # created: datetime = field(default_factory=datetime.now)
    # updated: datetime = field(default_factory=datetime.now)


# @dataclass
# class Synapse:
    # """Connection between layers (O-strata)."""
    # source_layer: YLayer
    # target_layer: YLayer
    # loop_type: OLoop
    # weight: float = 1.0
    
    # def compute_activation(self, source_activation: float) -> float:
        # """How much activation flows through this synapse."""
        # return source_activation * self.weight


# @dataclass
# class CompileTelemetry:
    # """Controller/telemetry snapshot for compile packet transitions."""
    # concept_name: str
    # emr_state: str
    # target_layer: str
    # activation: float
    # codegen_threshold: float
    # threshold_event: bool
    # transition: str
    # gate_outcome: str

    # def to_dict(self) -> Dict[str, Any]:
        # return {
            # "concept_name": self.concept_name,
            # "emr_state": self.emr_state,
            # "target_layer": self.target_layer,
            # "activation": self.activation,
            # "codegen_threshold": self.codegen_threshold,
            # "threshold_event": self.threshold_event,
            # "transition": self.transition,
            # "gate_outcome": self.gate_outcome,
        # }


# class HeytingLattice:
    # """Heyting algebra for O-strata operations.
    
    # Constructive logic: join, meet, implication.
    # """
    
    # def __init__(self):
        # self.elements: Dict[str, Set[str]] = {}  # element → parents
    
    # def add(self, element: str, parents: List[str] = None):
        # """Add element to lattice."""
        # self.elements[element] = set(parents or [])
    
    # def join(self, a: str, b: str) -> str:
        # """Least upper bound (OR)."""
        # # Find common ancestors
        # a_ancestors = self._ancestors(a)
        # b_ancestors = self._ancestors(b)
        # common = a_ancestors & b_ancestors
        
        # if not common:
            # return f"{a}∨{b}"  # Synthetic join
        
        # # Return lowest common ancestor
        # return min(common, key=lambda x: len(self._ancestors(x)))
    
    # def meet(self, a: str, b: str) -> str:
        # """Greatest lower bound (AND)."""
        # # The meet of a and b is something that implies both
        # return f"{a}∧{b}"  # Synthetic meet
    
    # def implies(self, a: str, b: str) -> bool:
        # """Does a → b? (a is subtype of b)"""
        # if a == b:
            # return True
        # return b in self._ancestors(a)
    
    # def _ancestors(self, element: str) -> Set[str]:
        # """Get all ancestors of element."""
        # if element not in self.elements:
            # return set()
        
        # ancestors = set(self.elements[element])
        # for parent in list(ancestors):
            # ancestors |= self._ancestors(parent)
        # return ancestors


# class YMesh:
    # """The neuronal Y-strata mesh with O-strata synapses."""
    
    # # Codegen activation threshold
    # CODEGEN_THRESHOLD = 0.8
    
    # # Activation decay per propagation step
    # DECAY = 0.1
    
    # def __init__(self):
        # # Y-STRATA: The six layers
        # self.layers: Dict[YLayer, Dict[str, YNode]] = {
            # layer: {} for layer in YLayer
        # }
        
        # # O-STRATA: The two Heyting lattices
        # self.is_loop = HeytingLattice()
        # self.has_loop = HeytingLattice()
        
        # # SYNAPSES: Connections between layers
        # self.synapses: List[Synapse] = self._init_synapses()
        
        # # Propagation hooks
        # self.on_codegen_ready: Optional[Callable[[str], None]] = None
    
    # def _init_synapses(self) -> List[Synapse]:
        # """Initialize the synapse mesh.
        
        # Every layer connects to every other layer.
        # Schema layers (Y1-Y3) constrain instance layers (Y4-Y6).
        # Instance layers feed back to schema layers.
        # """
        # synapses = []
        
        # # Y1 ↔ Y4: Upper ontology ↔ Instances
        # synapses.append(Synapse(YLayer.Y1_UPPER, YLayer.Y4_INSTANCE, OLoop.IS, 1.0))
        # synapses.append(Synapse(YLayer.Y4_INSTANCE, YLayer.Y1_UPPER, OLoop.IS, 0.5))
        
        # # Y2 ↔ Y5: Domain ontology ↔ Patterns
        # synapses.append(Synapse(YLayer.Y2_DOMAIN, YLayer.Y5_PATTERN, OLoop.IS, 1.0))
        # synapses.append(Synapse(YLayer.Y5_PATTERN, YLayer.Y2_DOMAIN, OLoop.IS, 0.5))
        
        # # Y3 ↔ Y6: Application ontology ↔ Implementations
        # synapses.append(Synapse(YLayer.Y3_APPLICATION, YLayer.Y6_IMPLEMENTATION, OLoop.HAS, 1.0))
        # synapses.append(Synapse(YLayer.Y6_IMPLEMENTATION, YLayer.Y3_APPLICATION, OLoop.HAS, 0.5))
        
        # # Y4 → Y5: Instances create patterns
        # synapses.append(Synapse(YLayer.Y4_INSTANCE, YLayer.Y5_PATTERN, OLoop.IS, 0.8))
        
        # # Y5 → Y6: Patterns create implementations
        # synapses.append(Synapse(YLayer.Y5_PATTERN, YLayer.Y6_IMPLEMENTATION, OLoop.HAS, 0.8))
        
        # # Y6 → Y4: Implementations become new instances (recursion)
        # synapses.append(Synapse(YLayer.Y6_IMPLEMENTATION, YLayer.Y4_INSTANCE, OLoop.IS, 0.8))
        
        # # Cross-layer (schema internal)
        # synapses.append(Synapse(YLayer.Y1_UPPER, YLayer.Y2_DOMAIN, OLoop.IS, 0.6))
        # synapses.append(Synapse(YLayer.Y2_DOMAIN, YLayer.Y3_APPLICATION, OLoop.HAS, 0.6))
        
        # # Cross-layer (instance internal)
        # synapses.append(Synapse(YLayer.Y4_INSTANCE, YLayer.Y6_IMPLEMENTATION, OLoop.HAS, 0.3))
        
        # return synapses
    
    # def add_node(self, layer: YLayer, name: str, content: Dict = None, 
                 # is_a: List[str] = None, has_part: List[str] = None) -> YNode:
        # """Add a node to a layer."""
        # node = YNode(
            # name=name,
            # layer=layer,
            # content=content or {},
            # is_a=is_a or [],
            # has_part=has_part or [],
            # activation=1.0  # Full activation on creation
        # )
        
        # self.layers[layer][name] = node

        # # Update Heyting lattices
        # if is_a:
            # self.is_loop.add(name, is_a)
        # if has_part:
            # for part in has_part:
                # self.has_loop.add(part, [name])

        # # Check codegen threshold for direct Y6 adds
        # if (layer == YLayer.Y6_IMPLEMENTATION and
            # node.activation >= self.CODEGEN_THRESHOLD and
            # self.on_codegen_ready):
            # self.on_codegen_ready(name)

        # # Propagate activation
        # self._propagate(layer, name, 1.0)

        # return node
    
    # def _propagate(self, source_layer: YLayer, source_name: str, activation: float, 
                   # visited: Set[str] = None):
        # """Propagate activation through synapses."""
        # if visited is None:
            # visited = set()
        
        # key = f"{source_layer}:{source_name}"
        # if key in visited or activation < 0.01:
            # return
        # visited.add(key)
        
        # # Find all synapses from this layer
        # for synapse in self.synapses:
            # if synapse.source_layer != source_layer:
                # continue
            
            # target_layer = synapse.target_layer
            # output_activation = synapse.compute_activation(activation) * (1 - self.DECAY)
            
            # # Update all nodes in target layer that connect to source
            # for target_name, target_node in self.layers[target_layer].items():
                # # Check if connected via IS or HAS
                # connected = False
                
                # if synapse.loop_type == OLoop.IS:
                    # # Check IS relationship
                    # connected = (source_name in target_node.is_a or
                                # self.is_loop.implies(target_name, source_name))
                # else:
                    # # Check HAS relationship
                    # connected = (source_name in target_node.has_part or
                                # target_name in (self.layers[source_layer].get(source_name) or YNode(name="", layer=source_layer)).has_part)
                
                # if connected:
                    # old_activation = target_node.activation
                    # target_node.activation = min(1.0, target_node.activation + output_activation)
                    # target_node.updated = datetime.now()
                    
                    # # Check codegen threshold
                    # if (target_layer == YLayer.Y6_IMPLEMENTATION and 
                        # target_node.activation >= self.CODEGEN_THRESHOLD and
                        # old_activation < self.CODEGEN_THRESHOLD):
                        # if self.on_codegen_ready:
                            # self.on_codegen_ready(target_name)
                    
                    # # Recurse
                    # self._propagate(target_layer, target_name, output_activation, visited)
    
    # def get_activation(self, layer: YLayer, name: str) -> float:
        # """Get activation level of a node."""
        # if name in self.layers[layer]:
            # return self.layers[layer][name].activation
        # return 0.0
    
    # def codegen_ready(self, name: str) -> bool:
        # """Is this concept ready for codegen?"""
        # return self.get_activation(YLayer.Y6_IMPLEMENTATION, name) >= self.CODEGEN_THRESHOLD
    
    # def get_ready_for_codegen(self) -> List[str]:
        # """Get all concepts ready for codegen."""
        # return [
            # name for name, node in self.layers[YLayer.Y6_IMPLEMENTATION].items()
            # if node.activation >= self.CODEGEN_THRESHOLD
        # ]
    
    # def decay_all(self, amount: float = 0.05):
        # """Decay all activations over time."""
        # for layer in self.layers.values():
            # for node in layer.values():
                # node.activation = max(0, node.activation - amount)
    
    # def get_status(self) -> Dict[str, Any]:
        # """Get current mesh status."""
        # return {
            # "layers": {
                # layer.value: {
                    # "count": len(nodes),
                    # "total_activation": sum(n.activation for n in nodes.values()),
                    # "ready_for_codegen": sum(1 for n in nodes.values() 
                                            # if n.activation >= self.CODEGEN_THRESHOLD)
                    # if layer == YLayer.Y6_IMPLEMENTATION else 0
                # }
                # for layer, nodes in self.layers.items()
            # },
            # "is_loop_size": len(self.is_loop.elements),
            # "has_loop_size": len(self.has_loop.elements),
            # "synapse_count": len(self.synapses),
        # }


# def emr_state_to_layer(emr_state: str) -> YLayer:
    # """Map EMR state to Y-layer for controller telemetry."""
    # layer_map = {
        # "embodies": YLayer.Y4_INSTANCE,
        # "manifests": YLayer.Y5_PATTERN,
        # "reifies": YLayer.Y6_IMPLEMENTATION,
        # "programs": YLayer.Y6_IMPLEMENTATION,
    # }
    # return layer_map.get(emr_state, YLayer.Y4_INSTANCE)


# def build_compile_telemetry(
    # concept_name: str,
    # emr_state: str,
    # admit_to_ont: bool,
# ) -> Dict[str, Any]:
    # """Deterministic controller telemetry for compile packet state transitions."""
    # activation_map = {
        # "embodies": 0.25,
        # "manifests": 0.55,
        # "reifies": 0.75,
        # "programs": 0.95,
    # }

    # layer = emr_state_to_layer(emr_state)
    # activation = activation_map.get(emr_state, 0.25)
    # threshold = YMesh.CODEGEN_THRESHOLD
    # threshold_event = (
        # layer == YLayer.Y6_IMPLEMENTATION and activation >= threshold
    # )

    # if admit_to_ont:
        # transition = "SOUP_TO_ONT"
        # gate_outcome = "admit_to_ont"
    # else:
        # transition = "STAY_SOUP"
        # gate_outcome = "stay_in_soup"

    # telemetry = CompileTelemetry(
        # concept_name=concept_name,
        # emr_state=emr_state,
        # target_layer=layer.value,
        # activation=activation,
        # codegen_threshold=threshold,
        # threshold_event=threshold_event,
        # transition=transition,
        # gate_outcome=gate_outcome,
    # )
    # return telemetry.to_dict()


# # =============================================================================
# # DEMO
# # =============================================================================

# if __name__ == "__main__":
    # print("=== Y-MESH NEURONAL ONTOLOGY ===")
    # print()
    
    # mesh = YMesh()
    
    # # Callback for codegen ready
    # def on_ready(name):
        # print(f"  🔥 CODEGEN READY: {name}")
    # mesh.on_codegen_ready = on_ready
    
    # # 1. Add schema layer (Y1-Y3)
    # print("1. Adding schema layers (Y1-Y3)...")
    
    # # Y1: Upper ontology - observation types
    # mesh.add_node(YLayer.Y1_UPPER, "InsightMoment", {"type": "observation"})
    # mesh.add_node(YLayer.Y1_UPPER, "Implementation", {"type": "observation"})
    
    # # Y2: Domain ontology
    # mesh.add_node(YLayer.Y2_DOMAIN, "PAIAB", {"domain": "skills"}, is_a=["InsightMoment"])
    # mesh.add_node(YLayer.Y2_DOMAIN, "YOUKNOW", {"domain": "ontology"}, is_a=["Implementation"])
    
    # # Y3: Application ontology - operations
    # mesh.add_node(YLayer.Y3_APPLICATION, "SkillSpec", 
                  # {"fields": ["domain", "category", "skill_md"]},
                  # is_a=["PAIAB"])
    
    # print(f"   Schema: {mesh.get_status()['layers']}")
    # print()
    
    # # 2. Add instance layer (Y4)
    # print("2. Adding instance (Y4)...")
    # mesh.add_node(YLayer.Y4_INSTANCE, "MyBrowserSkill",
                  # {"domain": "PAIAB", "category": "understand"},
                  # is_a=["SkillSpec"])
    
    # print(f"   Y4 activation: {mesh.get_activation(YLayer.Y4_INSTANCE, 'MyBrowserSkill'):.2f}")
    # print()
    
    # # 3. Add pattern (Y5)
    # print("3. Adding pattern (Y5)...")
    # mesh.add_node(YLayer.Y5_PATTERN, "BrowserAutomationPattern",
                  # {"pattern": "playwright + skill"},
                  # is_a=["MyBrowserSkill"])
    
    # print(f"   Y5 activation: {mesh.get_activation(YLayer.Y5_PATTERN, 'BrowserAutomationPattern'):.2f}")
    # print()
    
    # # 4. Add implementation (Y6)
    # print("4. Adding implementation (Y6)...")
    # mesh.add_node(YLayer.Y6_IMPLEMENTATION, "BrowserSkillImpl",
                  # {"code": "class BrowserSkill: ..."},
                  # is_a=["BrowserAutomationPattern"],
                  # has_part=["MyBrowserSkill"])
    
    # print(f"   Y6 activation: {mesh.get_activation(YLayer.Y6_IMPLEMENTATION, 'BrowserSkillImpl'):.2f}")
    # print(f"   Codegen ready: {mesh.codegen_ready('BrowserSkillImpl')}")
    # print()
    
    # # 5. Check what's ready
    # print("5. Checking codegen ready...")
    # ready = mesh.get_ready_for_codegen()
    # print(f"   Ready: {ready}")
    # print()
    
    # # 6. Final status
    # print("6. Mesh status:")
    # status = mesh.get_status()
    # for layer, info in status["layers"].items():
        # print(f"   {layer}: {info['count']} nodes, activation={info['total_activation']:.2f}")
    # print(f"   IS loop: {status['is_loop_size']} elements")
    # print(f"   HAS loop: {status['has_loop_size']} elements")
