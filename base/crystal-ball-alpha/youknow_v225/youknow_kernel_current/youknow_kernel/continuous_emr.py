"""
Continuous EMR Processor

EMR happens constantly as you use YOUKNOW.
Every addition is checked for isomorphisms.
New PIOEntities emerge automatically.

You're always holographically positioned on the EMR gradient.
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Import PIO components
try:
    from youknow_kernel.pio import PIOEngine, PIOEntity, PolysemicPattern
except ImportError:
    PIOEngine = None
    PIOEntity = None
    PolysemicPattern = None


@dataclass
class IsomorphismCandidate:
    """A potential isomorphism detected automatically."""
    thing_a: str
    thing_b: str
    similarity_type: str  # 'name', 'structure', 'relationship', 'pattern'
    confidence: float
    discovered_at: datetime = field(default_factory=datetime.now)


class ContinuousEMRProcessor:
    """Continuous EMR processing - always discovering isomorphisms.
    
    Every time you add to the ontology:
    1. Check for name similarities (lexical)
    2. Check for structural similarities (same is_a patterns)
    3. Check for relationship similarities (same relationship types)
    4. Auto-discover potential PIOEntities
    
    You're always on the EMR gradient.
    The process is holographic.
    """
    
    def __init__(self, pio_engine: Optional[PIOEngine] = None):
        self.engine = pio_engine or (PIOEngine() if PIOEngine else None)
        
        # All concepts we've seen
        self.concepts: Dict[str, Dict[str, Any]] = {}
        
        # Detected isomorphism candidates
        self.candidates: List[IsomorphismCandidate] = []
        
        # Auto-discovered potential hyperedges
        self.auto_potentials: Dict[str, List[str]] = {}
        # { pattern_key: [member1, member2, ...] }
        
        # EMR state for each concept
        self.emr_state: Dict[str, str] = {}
        # { concept_name: 'embodies' | 'manifests' | 'reifies' }
        
        # Similarity thresholds
        self.name_similarity_threshold = 0.6
        self.structure_similarity_threshold = 0.7
    
    def add_concept(
        self,
        name: str,
        description: str = "",
        is_a: Optional[List[str]] = None,
        relationships: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """Add a concept and automatically check for isomorphisms.
        
        Returns discovered isomorphisms and EMR state.
        """
        is_a = is_a or []
        relationships = relationships or {}
        
        # Store concept
        self.concepts[name] = {
            'description': description,
            'is_a': is_a,
            'relationships': relationships,
            'added_at': datetime.now().isoformat()
        }
        
        # Start in EMBODIES
        self.emr_state[name] = 'embodies'
        
        # === AUTO-DETECT ISOMORPHISMS ===
        discoveries = []
        
        # 1. Check name similarity
        name_matches = self._check_name_similarity(name)
        for match in name_matches:
            candidate = IsomorphismCandidate(
                thing_a=name,
                thing_b=match['name'],
                similarity_type='name',
                confidence=match['score']
            )
            self.candidates.append(candidate)
            discoveries.append(candidate)
            
            # Auto-group into potential hyperedge
            self._add_to_auto_potential(name, match['name'], 'name_similarity')
        
        # 2. Check structural similarity (same is_a chain pattern)
        structure_matches = self._check_structure_similarity(name, is_a)
        for match in structure_matches:
            candidate = IsomorphismCandidate(
                thing_a=name,
                thing_b=match['name'],
                similarity_type='structure',
                confidence=match['score']
            )
            self.candidates.append(candidate)
            discoveries.append(candidate)
            
            # Auto-group
            self._add_to_auto_potential(name, match['name'], 'structure_similarity')
        
        # 3. Check relationship pattern similarity
        rel_matches = self._check_relationship_similarity(name, relationships)
        for match in rel_matches:
            candidate = IsomorphismCandidate(
                thing_a=name,
                thing_b=match['name'],
                similarity_type='relationship',
                confidence=match['score']
            )
            self.candidates.append(candidate)
            discoveries.append(candidate)
            
            self._add_to_auto_potential(name, match['name'], 'relationship_similarity')
        
        # Update EMR state based on discoveries
        if discoveries:
            self.emr_state[name] = 'manifests'  # We see its relations
        
        return {
            'name': name,
            'emr_state': self.emr_state[name],
            'discoveries': len(discoveries),
            'candidates': [
                {'with': c.thing_b, 'type': c.similarity_type, 'confidence': c.confidence}
                for c in discoveries
            ],
            'auto_potentials': self._get_potentials_for(name)
        }
    
    def _check_name_similarity(self, name: str) -> List[Dict]:
        """Check for names that share words/patterns."""
        matches = []
        name_words = set(name.lower().replace('_', ' ').split())
        
        for existing_name in self.concepts:
            if existing_name == name:
                continue
            
            existing_words = set(existing_name.lower().replace('_', ' ').split())
            common = name_words & existing_words
            
            if common:
                score = len(common) / max(len(name_words), len(existing_words))
                if score >= self.name_similarity_threshold:
                    matches.append({'name': existing_name, 'score': score, 'common': list(common)})
        
        return matches
    
    def _check_structure_similarity(self, name: str, is_a: List[str]) -> List[Dict]:
        """Check for concepts with same is_a pattern."""
        matches = []
        
        if not is_a:
            return matches
        
        is_a_set = set(is_a)
        
        for existing_name, data in self.concepts.items():
            if existing_name == name:
                continue
            
            existing_is_a = set(data.get('is_a', []))
            
            if existing_is_a:
                common = is_a_set & existing_is_a
                if common:
                    score = len(common) / max(len(is_a_set), len(existing_is_a))
                    if score >= self.structure_similarity_threshold:
                        matches.append({'name': existing_name, 'score': score, 'common_parents': list(common)})
        
        return matches
    
    def _check_relationship_similarity(self, name: str, relationships: Dict) -> List[Dict]:
        """Check for concepts with same relationship types."""
        matches = []
        
        if not relationships:
            return matches
        
        rel_types = set(relationships.keys())
        
        for existing_name, data in self.concepts.items():
            if existing_name == name:
                continue
            
            existing_rels = set(data.get('relationships', {}).keys())
            
            if existing_rels:
                common = rel_types & existing_rels
                if common:
                    score = len(common) / max(len(rel_types), len(existing_rels))
                    if score >= 0.5:  # Lower threshold for relationships
                        matches.append({'name': existing_name, 'score': score, 'common_rels': list(common)})
        
        return matches
    
    def _add_to_auto_potential(self, thing_a: str, thing_b: str, similarity_type: str):
        """Add to automatic potential hyperedge."""
        key = f"Auto_{similarity_type}"
        
        if key not in self.auto_potentials:
            self.auto_potentials[key] = []
        
        if thing_a not in self.auto_potentials[key]:
            self.auto_potentials[key].append(thing_a)
        if thing_b not in self.auto_potentials[key]:
            self.auto_potentials[key].append(thing_b)
        
        # If PIO engine available, register discovery
        if self.engine and len(self.auto_potentials[key]) >= 2:
            members = self.auto_potentials[key]
            self.engine.discover_isomorphism(
                thing_a=members[0],
                thing_b=members[1],
                name=key,
                discoverer_id='auto_emr'
            )
            for member in members[2:]:
                self.engine.add_to_potential(key, member)
    
    def _get_potentials_for(self, concept: str) -> List[str]:
        """Get all auto-potentials that include this concept."""
        result = []
        for key, members in self.auto_potentials.items():
            if concept in members:
                result.append(f"{key}: {members}")
        return result
    
    def get_emr_gradient(self, concept: str) -> Dict[str, Any]:
        """Get the current EMR gradient position for a concept."""
        if concept not in self.concepts:
            return {'error': 'Concept not found'}
        
        candidates = [c for c in self.candidates if c.thing_a == concept or c.thing_b == concept]
        potentials = self._get_potentials_for(concept)
        
        return {
            'concept': concept,
            'emr_state': self.emr_state.get(concept, 'unknown'),
            'isomorphism_candidates': len(candidates),
            'potential_hyperedges': potentials,
            'gradient': {
                'embodies': len([c for c in candidates if c.confidence < 0.5]),
                'manifests': len([c for c in candidates if 0.5 <= c.confidence < 0.8]),
                'reifies': len([c for c in candidates if c.confidence >= 0.8])
            }
        }
    
    def get_all_auto_potentials(self) -> Dict[str, List[str]]:
        """Get all automatically discovered potential hyperedges."""
        return self.auto_potentials.copy()
    
    def promote_to_reifies(self, concept: str) -> bool:
        """Manually promote a concept to REIFIES state."""
        if concept in self.emr_state:
            self.emr_state[concept] = 'reifies'
            return True
        return False


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("=== CONTINUOUS EMR PROCESSING ===")
    print()
    
    processor = ContinuousEMRProcessor()
    
    # Add concepts - isomorphisms discovered automatically
    concepts_to_add = [
        ("Dog", "A loyal companion", ["Animal", "Pet"]),
        ("Cat", "An independent pet", ["Animal", "Pet"]),
        ("Wolf", "A wild canine", ["Animal", "Canine"]),
        ("Dog_Trainer", "Teaches dogs", ["Trainer"]),
        ("Cat_Trainer", "Teaches cats", ["Trainer"]),
        ("Pet_Store", "Sells pets", ["Store", "Pet_Related"]),
        ("Dog_Food", "Food for dogs", ["Food", "Pet_Related"]),
        ("Cat_Food", "Food for cats", ["Food", "Pet_Related"]),
    ]
    
    for name, desc, is_a in concepts_to_add:
        result = processor.add_concept(name, desc, is_a)
        if result['discoveries'] > 0:
            print(f"ADD: {name}")
            print(f"  EMR: {result['emr_state']}")
            print(f"  Discoveries: {result['discoveries']}")
            for c in result['candidates']:
                print(f"    ~ {c['with']} ({c['type']}, {c['confidence']:.2f})")
            print()
    
    print("=== AUTO-DISCOVERED HYPEREDGES ===")
    for key, members in processor.get_all_auto_potentials().items():
        print(f"  {key}: {members}")
    
    print()
    print("=== EMR GRADIENT FOR 'Dog_Food' ===")
    gradient = processor.get_emr_gradient('Dog_Food')
    print(f"  State: {gradient['emr_state']}")
    print(f"  Candidates: {gradient['isomorphism_candidates']}")
    print(f"  Gradient: {gradient['gradient']}")
