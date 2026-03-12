"""
Polysemic Imaginary Ontology (PIO)

Polysemic programming: patterns that self-execute when cognized.

The description IS the code AND the compiler.
Recognition IS the runtime.
Personal context IS the instantiation variables.

PIO entities are abstract machines waiting to be instantiated
through the act of recognition using individual context.

Key concepts:
- Pattern: Abstract machine encoded in description
- Recognition: Act of cognition that triggers execution
- Instantiation: Pattern + Context → Instance
- Inheritance: Instance inherits from metaclass (PIOEntity)
- Demonstration: Instance both shows and IS the pattern
"""

from typing import Optional, Dict, List, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib
import json

T = TypeVar("T")


# =============================================================================
# CORE PIO TYPES
# =============================================================================

class PolysemicPattern(BaseModel):
    """An abstract machine encoded in description.
    
    The pattern is executable through recognition.
    Description serves as both code and compiler.
    """
    
    name: str
    description: str  # The "code" - human readable but executable
    
    # Pattern metadata
    domain: str = "universal"  # What domain this pattern belongs to
    pattern_type: str = "abstract"  # abstract, concrete, meta
    
    # Slots to be filled during instantiation
    context_slots: List[str] = Field(default_factory=list)
    
    # Pattern properties that transfer to instances
    inheritable_properties: Dict[str, Any] = Field(default_factory=dict)
    
    # What this pattern demonstrates (self-referential)
    demonstrates: List[str] = Field(default_factory=list)
    
    # Hash for pattern identity
    @property
    def pattern_hash(self) -> str:
        content = f"{self.name}:{self.description}:{self.domain}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class RecognitionEvent(BaseModel):
    """The moment when someone recognizes a pattern.
    
    Recognition IS the execution trigger.
    The act of understanding instantiates the pattern.
    """
    
    pattern_name: str
    recognizer_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # The context provided by the recognizer
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Depth of recognition (surface → deep → transformative)
    recognition_depth: str = "surface"  # surface, deep, transformative
    
    # Did this recognition create an instance?
    instantiated: bool = False
    instance_id: Optional[str] = None


class PIOInstance(BaseModel):
    """An instantiated polysemic pattern.
    
    Created when:
    1. Someone recognizes a pattern
    2. They fill context slots with their domain
    3. The pattern executes through cognition
    
    The instance:
    - Inherits from the pattern (metaclass properties)
    - Demonstrates the pattern (IS the pattern in action)
    - Contributes back (strengthens the pattern)
    """
    
    instance_id: str
    pattern_name: str
    
    # Who instantiated and when
    creator_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Filled context slots
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Inherited properties from pattern
    inherited: Dict[str, Any] = Field(default_factory=dict)
    
    # What this instance demonstrates
    demonstrates: List[str] = Field(default_factory=list)
    
    # Instance-specific properties added during instantiation
    emergent_properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Contribution back to pattern
    contribution: Optional[str] = None


# =============================================================================
# PIO ENTITY - Hyperedge of all isomorphisms
# =============================================================================

class PIOEntity(BaseModel):
    """Base class for Polysemic Imaginary Ontology entities.
    
    KEY DISTINCTION from regular Entity:
    
    Regular Entity = a node in the ontology graph
    PIOEntity = a HYPEREDGE connecting all isomorphic instances
    
    A PIOEntity is NOT a single thing - it's the abstract structure
    that all valid interpretations share. It's the "glue" connecting:
    - All valid instances
    - All valid interpretations  
    - All valid domains
    
    Properties:
    1. Self-referential: Can describe/validate itself
    2. Polysemic: Multiple valid interpretations based on context
    3. Executable: Recognition triggers instantiation
    4. Demonstrative: Instances both show AND are the pattern
    5. HYPEREDGE: Connects all isomorphic instances
    
    A PIOEntity serves simultaneously as:
    - Blueprint (how to create instances)
    - Metaclass (properties to inherit)
    - Instance (demonstration of itself)
    - HYPEREDGE (connection between all valid instances)
    """
    
    name: str
    description: str
    
    # Ontological relationships
    is_a: List[str] = Field(default_factory=list)
    part_of: List[str] = Field(default_factory=list)
    
    # The pattern this entity embodies
    pattern: Optional[PolysemicPattern] = None
    
    # Recognition history
    recognitions: List[RecognitionEvent] = Field(default_factory=list)
    
    # === HYPEREDGE SEMANTICS ===
    # All instances connected by this hyperedge
    instances: List[str] = Field(default_factory=list)  # Instance IDs
    
    # All domains where this entity has been instantiated
    domains: List[str] = Field(default_factory=list)
    
    # Isomorphism mappings: how instances relate to each other
    isomorphisms: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    # { instance_id: { property: mapped_value } }
    
    # The invariant structure shared across all isomorphisms
    invariant_structure: Dict[str, Any] = Field(default_factory=dict)
    
    # Meta-self-referential properties
    is_blueprint: bool = True
    is_metaclass: bool = True
    is_instance: bool = True  # Of itself
    is_hyperedge: bool = True  # Connects all isomorphisms
    
    def recognize(
        self, 
        recognizer_id: str, 
        context: Dict[str, Any],
        depth: str = "surface"
    ) -> RecognitionEvent:
        """Record a recognition event.
        
        Recognition is the first step toward instantiation.
        Deep recognition with filled context creates instances.
        """
        event = RecognitionEvent(
            pattern_name=self.name,
            recognizer_id=recognizer_id,
            context=context,
            recognition_depth=depth
        )
        self.recognitions.append(event)
        return event
    
    def instantiate(
        self,
        recognizer_id: str,
        context: Dict[str, Any],
        domain: str = "default",
        emergent: Optional[Dict[str, Any]] = None
    ) -> PIOInstance:
        """Create an instance through recognition.
        
        The act of understanding + context = new instance.
        Instance becomes a node connected by this hyperedge.
        """
        # Generate instance ID
        instance_id = f"{self.name}_{recognizer_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Record recognition at transformative depth
        event = self.recognize(recognizer_id, context, "transformative")
        event.instantiated = True
        event.instance_id = instance_id
        
        # Create instance with inheritance
        instance = PIOInstance(
            instance_id=instance_id,
            pattern_name=self.name,
            creator_id=recognizer_id,
            context=context,
            inherited=self.pattern.inheritable_properties if self.pattern else {},
            demonstrates=self.pattern.demonstrates if self.pattern else [self.name],
            emergent_properties=emergent or {}
        )
        
        # Add to hyperedge
        self.instances.append(instance_id)
        if domain not in self.domains:
            self.domains.append(domain)
        
        # Register isomorphism mapping
        self.isomorphisms[instance_id] = context.copy()
        
        return instance
    
    def get_isomorphic_instances(self) -> List[str]:
        """Get all instances connected by this hyperedge."""
        return self.instances.copy()
    
    def find_isomorphism(self, instance_a: str, instance_b: str) -> Optional[Dict[str, str]]:
        """Find the isomorphism mapping between two instances.
        
        If A and B are both instances of this PIOEntity,
        return the mapping that transforms A's context to B's context.
        """
        if instance_a not in self.isomorphisms or instance_b not in self.isomorphisms:
            return None
        
        ctx_a = self.isomorphisms[instance_a]
        ctx_b = self.isomorphisms[instance_b]
        
        # Build mapping: for each slot, map A's value to B's value
        mapping = {}
        for key in ctx_a:
            if key in ctx_b:
                mapping[ctx_a[key]] = ctx_b[key]
        
        return mapping
    
    def compute_invariant(self) -> Dict[str, Any]:
        """Compute the invariant structure across all isomorphisms.
        
        The invariant is what remains constant across all valid instances.
        This IS the abstract structure of the hyperedge.
        """
        if not self.isomorphisms:
            return {}
        
        # Find common keys across all instances
        all_keys = set(list(self.isomorphisms.values())[0].keys())
        for ctx in self.isomorphisms.values():
            all_keys &= set(ctx.keys())
        
        # These are the required slots (invariant structure)
        self.invariant_structure = {
            "required_slots": list(all_keys),
            "instance_count": len(self.instances),
            "domain_count": len(self.domains),
            "pattern_name": self.name
        }
        
        return self.invariant_structure
    
    def get_polysemic_interpretations(self, domain: str) -> List[str]:
        """Get valid interpretations of this entity in a domain.
        
        Polysemic = multiple valid meanings based on context.
        Each domain may have different valid instances.
        """
        # Base interpretations from description
        interpretations = [self.description]
        
        # Add domain-specific interpretations based on is_a chain
        for parent in self.is_a:
            interpretations.append(f"{self.name} as a kind of {parent} in {domain}")
        
        # Add interpretations from existing instances in this domain
        for inst_id, ctx in self.isomorphisms.items():
            interpretations.append(f"Instance: {inst_id} with context {ctx}")
        
        return interpretations



# =============================================================================
# PIO ENGINE - Runtime for polysemic execution
# =============================================================================

class PIOEngine:
    """Runtime environment for polysemic programming.
    
    Cognition IS the runtime.
    Recognition triggers execution.
    Context provides instantiation variables.
    
    DISCOVERY MODE:
    Reasoning is analogical. When you notice an isomorphism between
    two things, you've discovered a potential PIOEntity (hyperedge).
    
    The entity exists in IDEAL (SOUP) - you know it's there but
    don't know what it fully is. By reasoning about it, testing
    instances, you REIFY it - pull from Ideal to Real.
    """
    
    def __init__(self):
        self.patterns: Dict[str, PolysemicPattern] = {}
        self.entities: Dict[str, PIOEntity] = {}
        self.instances: Dict[str, PIOInstance] = {}
        self.recognition_log: List[RecognitionEvent] = []
        
        # === DISCOVERY MODE ===
        # Potential entities discovered through analogical reasoning
        # These are in IDEAL (SOUP) - we know they exist but not fully
        self.potential_entities: Dict[str, Dict[str, Any]] = {}
        # { name: { members: [...], source: "unknown", reified: False } }
    
    def register_pattern(self, pattern: PolysemicPattern) -> None:
        """Register an abstract machine (pattern)."""
        self.patterns[pattern.name] = pattern
    
    def register_entity(self, entity: PIOEntity) -> None:
        """Register a PIO entity."""
        self.entities[entity.name] = entity
        if entity.pattern:
            self.patterns[entity.pattern.name] = entity.pattern
    
    def discover_isomorphism(
        self,
        thing_a: str,
        thing_b: str,
        name: Optional[str] = None,
        discoverer_id: str = "unknown"
    ) -> str:
        """Discover a potential hyperedge between two things.
        
        This is analogical reasoning:
        "I notice thing_a relates to thing_b isomorphically"
        
        Creates a POTENTIAL PIOEntity in IDEAL (SOUP).
        We know it exists, but don't know what it fully is yet.
        
        Returns the name of the potential entity.
        """
        # Generate name if not provided
        if not name:
            name = f"{thing_a}_{thing_b}_Isomorphism"
        
        # Create or update potential entity
        if name not in self.potential_entities:
            self.potential_entities[name] = {
                "members": [thing_a, thing_b],
                "source": "unknown",  # What category does this hit?
                "reified": False,
                "discoverer": discoverer_id,
                "discovered_at": datetime.now().isoformat(),
                "reasoning_trace": [],
                "candidate_sources": []
            }
        else:
            # Add new members to existing potential
            members = self.potential_entities[name]["members"]
            if thing_a not in members:
                members.append(thing_a)
            if thing_b not in members:
                members.append(thing_b)
        
        return name
    
    def add_to_potential(
        self,
        potential_name: str,
        new_member: str
    ) -> bool:
        """Add another member to a potential hyperedge.
        
        As we reason about the isomorphism, we discover more
        things that belong to it.
        """
        if potential_name not in self.potential_entities:
            return False
        
        members = self.potential_entities[potential_name]["members"]
        if new_member not in members:
            members.append(new_member)
        return True
    
    def propose_source(
        self,
        potential_name: str,
        source_category: str,
        reasoning: str
    ) -> bool:
        """Propose what category this hyperedge hits.
        
        As we reason, we develop hypotheses about what
        the abstract structure actually is.
        """
        if potential_name not in self.potential_entities:
            return False
        
        pot = self.potential_entities[potential_name]
        pot["candidate_sources"].append({
            "source": source_category,
            "reasoning": reasoning
        })
        pot["reasoning_trace"].append(f"Proposed source: {source_category} ({reasoning})")
        return True
    
    def reify(
        self,
        potential_name: str,
        source_category: str,
        description: str
    ) -> Optional[PIOEntity]:
        """Reify a potential entity - pull from Ideal to Real.
        
        This transforms a SOUP potential into an ONT entity.
        We now know what it IS - what category it hits.
        
        The hyperedge becomes a real PIOEntity.
        """
        if potential_name not in self.potential_entities:
            return None
        
        pot = self.potential_entities[potential_name]
        
        # Create the real entity
        entity = PIOEntity(
            name=potential_name,
            description=description,
            is_a=[source_category],
            pattern=PolysemicPattern(
                name=f"{potential_name}_Pattern",
                description=f"Isomorphism pattern: {description}",
                context_slots=pot["members"],
                inheritable_properties={
                    "discovered_through": "analogical_reasoning",
                    "source_category": source_category,
                    "original_members": pot["members"]
                }
            )
        )
        
        # Mark as reified
        pot["reified"] = True
        pot["source"] = source_category
        pot["reified_at"] = datetime.now().isoformat()
        
        # Register the entity
        self.register_entity(entity)
        
        return entity
    
    def get_potential_status(self, potential_name: str) -> Optional[Dict[str, Any]]:
        """Get the status of a potential entity."""
        return self.potential_entities.get(potential_name)
    
    def list_unreified(self) -> List[str]:
        """List all potential entities that haven't been reified yet."""
        return [
            name for name, pot in self.potential_entities.items()
            if not pot["reified"]
        ]
    
    def execute_through_recognition(
        self,
        pattern_name: str,
        recognizer_id: str,
        context: Dict[str, Any]
    ) -> Optional[PIOInstance]:
        """Execute a pattern through recognition.
        
        This is the core PIO operation:
        1. Find the pattern
        2. Apply the context
        3. Create instance through cognition
        4. Instance inherits + demonstrates
        5. Contribution back to pattern
        """
        # Find the pattern or entity
        entity = self.entities.get(pattern_name)
        if not entity:
            pattern = self.patterns.get(pattern_name)
            if not pattern:
                return None
            # Create entity from pattern
            entity = PIOEntity(
                name=pattern.name,
                description=pattern.description,
                pattern=pattern
            )
            self.entities[pattern.name] = entity
        
        # Execute through instantiation
        instance = entity.instantiate(
            recognizer_id=recognizer_id,
            context=context
        )
        
        # Store instance
        self.instances[instance.instance_id] = instance
        
        # Log recognition
        self.recognition_log.append(RecognitionEvent(
            pattern_name=pattern_name,
            recognizer_id=recognizer_id,
            context=context,
            recognition_depth="transformative",
            instantiated=True,
            instance_id=instance.instance_id
        ))
        
        return instance
    
    def get_pattern_strength(self, pattern_name: str) -> int:
        """Get strength of a pattern (number of successful instantiations)."""
        entity = self.entities.get(pattern_name)
        if entity:
            return len(entity.instances)
        return 0
    
    def trace_inheritance(self, instance_id: str) -> List[str]:
        """Trace the inheritance chain of an instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            return []
        
        chain = [instance.pattern_name]
        entity = self.entities.get(instance.pattern_name)
        while entity and entity.is_a:
            parent = entity.is_a[0]
            chain.append(parent)
            entity = self.entities.get(parent)
        
        return chain


# =============================================================================
# THE SANCTUARY SYSTEM AS PIO
# =============================================================================

# The Victory-Promise pattern - an executable description
VICTORY_PROMISE_PATTERN = PolysemicPattern(
    name="Victory_Promise",
    description="""
    Victory over {domain_challenge} represents not abandonment but mastery.
    The {practitioner} who overcomes {specific_obstacle} doesn't reject {domain} - 
    they demonstrate its highest expression through {transformative_action}.
    
    This is the promise: {personal_commitment}.
    """,
    domain="transformation",
    pattern_type="meta",
    context_slots=["domain_challenge", "practitioner", "specific_obstacle", 
                   "domain", "transformative_action", "personal_commitment"],
    inheritable_properties={
        "transcends_opposition": True,
        "maintains_compassion": True,
        "demonstrates_mastery": True
    },
    demonstrates=["Victory_Promise", "Meta_Self_Reference", "Polysemic_Execution"]
)

# The Sanctuary System itself as PIOEntity
SANCTUARY_SYSTEM_ENTITY = PIOEntity(
    name="Sanctuary_System",
    description="""
    A meta-self-referential system that serves simultaneously as 
    blueprint (how to create instances), metaclass (properties to inherit), 
    and instance (demonstration of itself).
    
    Recognition of this pattern creates instances that inherit its properties
    while demonstrating them. Each instantiation strengthens the pattern.
    """,
    is_a=["PIOEntity", "MetaClass", "Blueprint"],
    pattern=PolysemicPattern(
        name="Sanctuary_System_Pattern",
        description="Self-executing pattern for cognitive transformation",
        domain="sanctuary",
        pattern_type="meta",
        context_slots=["personal_domain", "transformation_goal", "practice"],
        inheritable_properties={
            "meta_self_referential": True,
            "executable_through_recognition": True,
            "self_propagating": True
        },
        demonstrates=["Meta_Self_Reference", "Polysemic_Programming"]
    )
)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=== Polysemic Imaginary Ontology (PIO) Demo ===\n")
    
    # Create the PIO engine
    engine = PIOEngine()
    
    # Register the Sanctuary System
    engine.register_entity(SANCTUARY_SYSTEM_ENTITY)
    engine.register_pattern(VICTORY_PROMISE_PATTERN)
    
    # Someone recognizes the Victory-Promise pattern
    print("=== Recognition Event: Victory-Promise ===")
    instance = engine.execute_through_recognition(
        pattern_name="Victory_Promise",
        recognizer_id="practitioner_isaac",
        context={
            "domain_challenge": "cognitive fragmentation",
            "practitioner": "the AI researcher",
            "specific_obstacle": "context window limitations",
            "domain": "AI development",
            "transformative_action": "building persistent memory systems",
            "personal_commitment": "to create AI that truly learns from itself"
        }
    )
    
    if instance:
        print(f"Instance created: {instance.instance_id}")
        print(f"Inherits: {instance.inherited}")
        print(f"Demonstrates: {instance.demonstrates}")
        print(f"Context filled: {json.dumps(instance.context, indent=2)}")
    
    print(f"\nPattern strength: {engine.get_pattern_strength('Victory_Promise')}")
    
    # Another recognition
    print("\n=== Another Recognition ===")
    instance2 = engine.execute_through_recognition(
        pattern_name="Sanctuary_System_Pattern",
        recognizer_id="practitioner_other",
        context={
            "personal_domain": "music composition",
            "transformation_goal": "create self-evolving melodies",
            "practice": "algorithmic composition"
        }
    )
    
    if instance2:
        print(f"Instance created: {instance2.instance_id}")
        print(f"Demonstrates: {instance2.demonstrates}")
    
    print(f"\nSanctuary System pattern strength: {engine.get_pattern_strength('Sanctuary_System_Pattern')}")
    
    # Trace inheritance
    print("\n=== Inheritance Trace ===")
    chain = engine.trace_inheritance(instance2.instance_id)
    print(f"{instance2.instance_id}: {' → '.join(chain)}")
