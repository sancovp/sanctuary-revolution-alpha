"""
YOUKNOW Unified Pipeline

Wires together:
- PIO (discovery + hyperedge)
- Continuous EMR (auto-isomorphism detection)
- Analogical Reach (ABCD bridge)
- OWL Substrate (dual write to OWL + Carton mirror)
- Lifecycle (state machine)
- Hallucination (formal bijective)

One entry point: add_to_youknow()
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

# Import all our modules
from youknow_kernel.pio import PIOEngine, PIOEntity, PolysemicPattern
from youknow_kernel.continuous_emr import ContinuousEMRProcessor
from youknow_kernel.analogical_reach import AnalogicalReachEngine, AnalogicalBridge
from youknow_kernel.owl_substrate import OWLEntity, DualSubstrate
from youknow_kernel.validation_state_machine import (
    ValidationStateMachine, 
    ConceptLifecycle,
    ValidationState,
    get_or_create_lifecycle,
    get_lifecycle
)
from youknow_kernel.uarl_validator import (
    UARLValidator,
    ValidationResult,
    InclusionMapArgument
)


@dataclass
class YouknowResult:
    """Result of adding something to YOUKNOW."""
    
    concept_name: str
    
    # EMR state
    emr_state: str  # embodies, manifests, reifies
    ses_layer: int
    
    # Lifecycle state
    lifecycle_state: str  # SOUP, VIEWED, ONT_LOCAL, etc.
    
    # Validation
    valid: bool
    hallucination_meta: Optional[Dict] = None
    
    # What was discovered
    isomorphisms_found: List[str] = None
    spawned_entities: List[str] = None
    
    # What was written
    owl_written: bool = False
    carton_mirrored: bool = False
    
    def __post_init__(self):
        if self.isomorphisms_found is None:
            self.isomorphisms_found = []
        if self.spawned_entities is None:
            self.spawned_entities = []


class YouknowPipeline:
    """Unified YOUKNOW pipeline.
    
    One entry point for adding concepts that:
    1. Checks for isomorphisms (EMR auto-discovery)
    2. Validates via UARL
    3. Writes to OWL (source of truth)
    4. Mirrors to Carton
    5. Tracks lifecycle state
    6. Spawns children if hyperedge discovered
    """
    
    def __init__(
        self,
        owl_dir: str = "/tmp/youknow_owl",
        domain_file: str = "domain.owl"
    ):
        # Initialize all subsystems
        self.pio = PIOEngine()
        self.emr = ContinuousEMRProcessor(pio_engine=self.pio)
        self.reach = AnalogicalReachEngine(pio_engine=self.pio)
        self.substrate = DualSubstrate(owl_dir, domain_file)
        # Note: lifecycle is per-concept, use get_or_create_lifecycle(name)
        
        # UARL validator (may fail if deps not installed)
        try:
            self.validator = UARLValidator()
        except Exception:
            self.validator = None
    
    def add_concept(
        self,
        name: str,
        description: str,
        is_a: Optional[List[str]] = None,
        relationships: Optional[Dict[str, List[str]]] = None,
        properties: Optional[Dict[str, Any]] = None
    ) -> YouknowResult:
        """Add a concept to YOUKNOW.
        
        This is the main entry point. It:
        1. Registers concept with EMR processor (checks for isomorphisms)
        2. Validates via UARL
        3. If valid: writes to OWL, mirrors to Carton
        4. If invalid: stays in SOUP with hallucination metadata
        5. Spawns any discovered children
        """
        is_a = is_a or []
        relationships = relationships or {}
        properties = properties or {}
        
        # 1. EMR: Check for isomorphisms
        emr_result = self.emr.add_concept(
            name=name,
            description=description,
            is_a=is_a,
            relationships=relationships
        )
        
        isomorphisms_found = [c['with'] for c in emr_result.get('candidates', [])]
        emr_state = emr_result.get('emr_state', 'embodies')
        
        # 2. Lifecycle: Create or update
        lifecycle = get_or_create_lifecycle(name)
        lifecycle.update_uarl_status(
            uarl_valid=True,  # Will be updated by validator
            ses_layer=0
        )
        
        # 3. Validate via UARL (if validator available)
        valid = True
        hallucination_meta = None
        ses_layer = 0
        
        if self.validator:
            concept_data = {
                "name": name,
                "type": is_a[0] if is_a else "Concept",
                **{k: v for k, v in properties.items()}
            }
            # Add ABCD bridge if present
            if 'intuition' in relationships:
                concept_data['intuition'] = relationships['intuition'][0]
            if 'compareFrom' in relationships:
                concept_data['compareFrom'] = relationships['compareFrom'][0]
            if 'mapsTo' in relationships:
                concept_data['mapsTo'] = relationships['mapsTo'][0]
            if 'analogicalPattern' in relationships:
                concept_data['analogicalPattern'] = relationships['analogicalPattern'][0]
            
            result = self.validator.validate_concept(concept_data)
            valid = result.valid
            
            if not valid:
                hallucination_meta = result.hallucination_metadata
                emr_state = 'embodies'  # Stuck in SOUP
            else:
                emr_state = 'reifies'  # Valid = reified
                ses_layer = 3  # Minimum for validation
        
        # Update lifecycle
        lifecycle.update_uarl_status(uarl_valid=valid, ses_layer=ses_layer)
        if valid:
            lifecycle.view(actor='youknow_pipeline')
        
        # 4. Write to OWL + mirror to Carton if valid
        owl_written = False
        carton_mirrored = False
        spawned_entities = []
        
        if valid:
            # Check for hyperedge (if we found isomorphisms)
            is_hyperedge = len(isomorphisms_found) > 0
            
            owl_entity = OWLEntity(
                name=name,
                description=description,
                is_a=is_a,
                properties=properties,
                relationships=relationships,
                is_hyperedge=is_hyperedge,
                isomorphism_members=isomorphisms_found if is_hyperedge else [],
                emr_state=emr_state,
                ses_layer=ses_layer
            )
            
            result = self.substrate.add_entity(owl_entity)
            owl_written = result['owl_success']
            carton_mirrored = 'Carton not available' not in str(result['carton_result'])
            
            # 5. If hyperedge, spawn children
            if is_hyperedge and owl_written:
                for member in isomorphisms_found:
                    if member != name:
                        spawned = self._spawn_child(
                            parent_name=name,
                            child_name=member,
                            parent_is_a=is_a
                        )
                        if spawned:
                            spawned_entities.append(member)
        
        return YouknowResult(
            concept_name=name,
            emr_state=emr_state,
            ses_layer=ses_layer,
            lifecycle_state=lifecycle.concept.current_state.value,
            valid=valid,
            hallucination_meta=hallucination_meta,
            isomorphisms_found=isomorphisms_found,
            spawned_entities=spawned_entities,
            owl_written=owl_written,
            carton_mirrored=carton_mirrored
        )
    
    def _spawn_child(
        self,
        parent_name: str,
        child_name: str,
        parent_is_a: List[str]
    ) -> bool:
        """Spawn a child entity from hyperedge discovery."""
        try:
            child_entity = OWLEntity(
                name=child_name,
                description=f"Child of hyperedge {parent_name}",
                is_a=parent_is_a + [parent_name],
                emr_state='manifests',  # Discovered = manifests
                ses_layer=1
            )
            result = self.substrate.add_entity(child_entity)
            return result['owl_success']
        except Exception:
            return False
    
    def discover_bridge(
        self,
        intuition: str,      # A
        compare_from: str,   # B
        maps_to: str,        # C
        pattern: str         # D
    ) -> YouknowResult:
        """Discover an analogical bridge (ABCD).
        
        This creates:
        1. The bridge as a concept
        2. Spawn children for A, B, C
        3. Register pattern D
        """
        # Use reach engine
        reach_result = self.reach.discover_bridge(
            intuition=intuition,
            compareFrom=compare_from,
            mapsTo=maps_to,
            analogicalPattern=pattern
        )
        
        # Create bridge concept
        bridge_name = f"{intuition}_{compare_from}_{maps_to}_Bridge"
        
        return self.add_concept(
            name=bridge_name,
            description=f"Analogical bridge: {intuition} via {compare_from} to {maps_to}",
            is_a=["Analogical_Bridge", pattern],
            relationships={
                "intuition": [intuition],
                "compareFrom": [compare_from],
                "mapsTo": [maps_to],
                "analogicalPattern": [pattern],
                "embodies": [f"{intuition}_{maps_to}_Connection"]
            }
        )
    
    def get_reach(self, from_concept: str, to_concept: str) -> Dict[str, Any]:
        """Check if there's a known reach path between concepts."""
        result = self.reach.compute_reach(from_concept, to_concept)
        
        # Auto-generate audit sentence if direct reach
        if result.get('direct'):
            bridges = result.get('bridges', [])
            result['audit_sentence'] = self._generate_audit_sentence(
                from_concept, to_concept, bridges
            )
        
        return result
    
    def _generate_audit_sentence(
        self, 
        from_concept: str, 
        to_concept: str, 
        bridges: List[str]
    ) -> str:
        """Generate human-legible audit trace.
        
        Format: "Dog reaches Pirate via Patchy under Eye_Patch_Pattern (Analogical_Bridge, reach_length=1)."
        """
        if not bridges:
            return f"{from_concept} directly maps to {to_concept} (no bridge needed)."
        
        # Get metadata from reach engine
        reach_length = len(bridges)
        bridge_chain = " → ".join(bridges)
        
        # Try to get pattern from the bridge discovery
        pattern = "unknown_pattern"
        bridge_type = "Bridge"
        for bridge in self.reach.bridges:
            if bridge.intuition == from_concept and bridge.mapsTo == to_concept:
                pattern = bridge.analogicalPattern
                break
        
        return (
            f"{from_concept} reaches {to_concept} via {bridge_chain} "
            f"under {pattern} ({bridge_type}, reach_length={reach_length})."
        )
    
    def approve(self, concept_name: str, approver_id: str) -> Dict[str, Any]:
        """Approve a concept for local ontology."""
        lifecycle = get_or_create_lifecycle(concept_name)
        transition = lifecycle.approve(approver_id)
        return {'success': True, 'state': lifecycle.concept.current_state.value}
    
    def reject(
        self,
        concept_name: str,
        reviewer_id: str,
        inclusion_argument: InclusionMapArgument
    ) -> Dict[str, Any]:
        """Reject a concept with formal argument."""
        lifecycle = get_or_create_lifecycle(concept_name)
        transition = lifecycle.reject(
            actor=reviewer_id,
            reason=str(inclusion_argument),
            suggested_rules=[inclusion_argument.missing_morphism]
        )
        
        return {
            'success': True,
            'state': lifecycle.concept.current_state.value,
            'inclusion_argument': inclusion_argument.to_dict()
        }


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== YOUKNOW UNIFIED PIPELINE ===")
    print()
    
    pipeline = YouknowPipeline()
    
    # 1. Add a concept
    print("1. Adding 'Dog' concept...")
    result = pipeline.add_concept(
        name="Dog",
        description="A loyal four-legged companion",
        is_a=["Animal", "Pet"],
        properties={"has_fur": True, "leg_count": 4}
    )
    print(f"   EMR: {result.emr_state}")
    print(f"   Lifecycle: {result.lifecycle_state}")
    print(f"   OWL written: {result.owl_written}")
    print()
    
    # 2. Add another with isomorphism
    print("2. Adding 'Cat' concept (should find isomorphism with Dog)...")
    result = pipeline.add_concept(
        name="Cat",
        description="An independent pet",
        is_a=["Animal", "Pet"],
        properties={"has_fur": True, "leg_count": 4}
    )
    print(f"   Isomorphisms found: {result.isomorphisms_found}")
    print()
    
    # 3. Discover a bridge
    print("3. Discovering Dog→Pirate bridge via Patchy...")
    result = pipeline.discover_bridge(
        intuition="Dog",
        compare_from="Patchy",
        maps_to="Pirate",
        pattern="Eye_Patch_Pattern"
    )
    print(f"   Bridge: {result.concept_name}")
    print(f"   Spawned: {result.spawned_entities}")
    print(f"   Valid: {result.valid}")
    print()
    
    # 4. Check reach
    print("4. Checking reach Dog → Pirate...")
    reach = pipeline.get_reach("Dog", "Pirate")
    print(f"   Direct: {reach.get('direct', False)}")
    print(f"   Bridges: {reach.get('bridges', [])}")
    if reach.get('audit_sentence'):
        print(f"   📝 Audit: {reach['audit_sentence']}")
