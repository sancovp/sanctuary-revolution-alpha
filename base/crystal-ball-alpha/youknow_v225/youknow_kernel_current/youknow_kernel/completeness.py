"""
YOUKNOW Complete Validation

EVERY label (non-foundation word) MUST have ALL THREE:
1. is_a - what is it a kind of?
2. part_of - what is it part of?
3. produces - what does it produce?

AND each target must ALSO have all three, recursively back to Cat_of_Cat.

This is the COMPLETENESS requirement for pattern_of_is_a.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


# Foundation relationships that don't need the triplet
FOUNDATION_RELATIONSHIPS = {
    "is_a", "part_of", "has_part", "produces", "instance_of",
    "relates_to", "reifies", "embodies", "manifests", "programs",
}

# Foundation concepts (primitives) that are complete by definition
FOUNDATION_CONCEPTS = {
    "Cat_of_Cat", "Entity", "Category", "Relationship", 
    "Instance", "Pattern", "Implementation", "YOUKNOW",
    "Y_Strata", "O_Strata", "Y1", "Y2", "Y3", "Y4", "Y5", "Y6",
    "IS_Loop", "HAS_Loop",
}


@dataclass
class CompletenessResult:
    """Result of checking triplet completeness."""
    name: str
    complete: bool
    
    # What's present
    has_is_a: bool = False
    has_part_of: bool = False
    has_produces: bool = False
    
    # What each traces to
    is_a_trace: List[str] = field(default_factory=list)
    part_of_trace: List[str] = field(default_factory=list)
    produces_trace: List[str] = field(default_factory=list)
    
    # What's missing
    missing: List[str] = field(default_factory=list)
    
    # Recursive completeness of targets
    incomplete_targets: List[str] = field(default_factory=list)
    
    def explain(self) -> str:
        """Human-readable explanation."""
        lines = [f"Completeness check: {self.name}"]
        lines.append(f"Complete: {self.complete}")
        lines.append("")
        
        lines.append(f"is_a: {'✓' if self.has_is_a else '✗'}")
        if self.is_a_trace:
            lines.append(f"  → {' → '.join(self.is_a_trace)}")
        
        lines.append(f"part_of: {'✓' if self.has_part_of else '✗'}")
        if self.part_of_trace:
            lines.append(f"  → {' → '.join(self.part_of_trace)}")
        
        lines.append(f"produces: {'✓' if self.has_produces else '✗'}")
        if self.produces_trace:
            lines.append(f"  → {' → '.join(self.produces_trace)}")
        
        if self.missing:
            lines.append("")
            lines.append("Missing:")
            for m in self.missing:
                lines.append(f"  - {m}")
        
        if self.incomplete_targets:
            lines.append("")
            lines.append("Incomplete targets:")
            for t in self.incomplete_targets:
                lines.append(f"  - {t}")
        
        return "\n".join(lines)


class CompletenessValidator:
    """
    Validates that every label has the complete triplet.
    
    EVERY label must have:
    - is_a (traces to Cat_of_Cat)
    - part_of (traces to Cat_of_Cat)
    - produces (traces to Cat_of_Cat)
    
    Recursively checks all targets.
    """
    
    def __init__(self, cat=None):
        """
        Args:
            cat: CategoryOfCategories instance
        """
        self.cat = cat
        self._cache: Dict[str, CompletenessResult] = {}
    
    def is_foundation(self, name: str) -> bool:
        """Is this a foundation concept or relationship?"""
        return name in FOUNDATION_CONCEPTS or name in FOUNDATION_RELATIONSHIPS
    
    def check(self, name: str, visited: Optional[Set[str]] = None) -> CompletenessResult:
        """
        Check if a label has the complete triplet.
        
        Args:
            name: The label to check
            visited: Set of already-visited labels (for cycle detection)
        
        Returns:
            CompletenessResult
        """
        # Check cache
        if name in self._cache:
            return self._cache[name]
        
        # Foundation concepts are complete by definition
        if self.is_foundation(name):
            result = CompletenessResult(
                name=name,
                complete=True,
                has_is_a=True,
                has_part_of=True,
                has_produces=True,
            )
            self._cache[name] = result
            return result
        
        # Cycle detection
        if visited is None:
            visited = set()
        if name in visited:
            return CompletenessResult(
                name=name,
                complete=False,
                missing=[f"Cycle detected: {name}"],
            )
        visited = visited | {name}
        
        # Get entity from Cat of Cat
        if not self.cat or name not in self.cat.entities:
            result = CompletenessResult(
                name=name,
                complete=False,
                missing=[f"Not in ontology: {name}"],
            )
            self._cache[name] = result
            return result
        
        entity = self.cat.entities[name]
        result = CompletenessResult(name=name, complete=True)
        
        # Check is_a
        if entity.is_a:
            result.has_is_a = True
            result.is_a_trace = self._trace_to_root(entity.is_a[0], "is_a", visited)
            # Check completeness of is_a target
            for target in entity.is_a:
                if not self.is_foundation(target):
                    target_result = self.check(target, visited)
                    if not target_result.complete:
                        result.incomplete_targets.append(f"is_a target '{target}' is incomplete")
                        result.complete = False
        else:
            result.has_is_a = False
            result.missing.append("is_a: not specified")
            result.complete = False
        
        # Check part_of
        if entity.part_of:
            result.has_part_of = True
            result.part_of_trace = self._trace_to_root(entity.part_of[0], "part_of", visited)
            # Check completeness of part_of target
            for target in entity.part_of:
                if not self.is_foundation(target):
                    target_result = self.check(target, visited)
                    if not target_result.complete:
                        result.incomplete_targets.append(f"part_of target '{target}' is incomplete")
                        result.complete = False
        else:
            result.has_part_of = False
            result.missing.append("part_of: not specified")
            result.complete = False
        
        # Check produces
        if entity.produces:
            result.has_produces = True
            result.produces_trace = self._trace_to_root(entity.produces[0], "produces", visited)
            # Check completeness of produces target
            for target in entity.produces:
                if not self.is_foundation(target):
                    target_result = self.check(target, visited)
                    if not target_result.complete:
                        result.incomplete_targets.append(f"produces target '{target}' is incomplete")
                        result.complete = False
        else:
            result.has_produces = False
            result.missing.append("produces: not specified")
            result.complete = False
        
        self._cache[name] = result
        return result
    
    def _trace_to_root(self, start: str, rel_type: str, visited: Set[str]) -> List[str]:
        """Trace a relationship chain to Cat_of_Cat."""
        trace = [start]
        current = start
        seen = set()
        
        while current and current not in seen:
            seen.add(current)
            
            if current == "Cat_of_Cat":
                break
            
            if not self.cat or current not in self.cat.entities:
                break
            
            entity = self.cat.entities[current]
            
            # Get next in chain based on rel_type
            if rel_type == "is_a" and entity.is_a:
                next_entity = entity.is_a[0]
            elif rel_type == "part_of" and entity.part_of:
                next_entity = entity.part_of[0]
            elif rel_type == "produces" and entity.produces:
                next_entity = entity.produces[0]
            else:
                break
            
            trace.append(next_entity)
            current = next_entity
        
        return trace
    
    def check_all(self) -> Dict[str, CompletenessResult]:
        """Check completeness of all entities in the ontology."""
        results = {}
        if self.cat:
            for name in self.cat.entities:
                results[name] = self.check(name)
        return results
    
    def get_incomplete(self) -> List[str]:
        """Get list of incomplete entities."""
        results = self.check_all()
        return [name for name, r in results.items() if not r.complete]
    
    def get_missing_triplets(self) -> Dict[str, List[str]]:
        """Get what each entity is missing."""
        results = self.check_all()
        missing = {}
        for name, r in results.items():
            if r.missing:
                missing[name] = r.missing
        return missing


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=== COMPLETENESS VALIDATOR ===")
    print()
    
    # Create test without Cat of Cat
    validator = CompletenessValidator()
    
    # Foundation concepts are complete by definition
    print("1. Foundation concept:")
    result = validator.check("Category")
    print(result.explain())
    print()
    
    # Test with Cat of Cat
    print("2. With Cat of Cat:")
    try:
        from .owl_types import get_type_registry as get_cat
        cat = get_cat()
        validator = CompletenessValidator(cat=cat)
        
        # Check Pattern (should be incomplete - no part_of, no produces)
        result = validator.check("Pattern")
        print(result.explain())
        print()
        
        # Add a complete entity
        cat.add(
            "SkillSpec",
            is_a=["Category"],
            part_of=["YOUKNOW"],
            produces=["SkillPackage"],
        )
        
        # But SkillPackage doesn't exist yet...
        print("3. SkillSpec (SkillPackage doesn't exist):")
        # Clear cache
        validator._cache = {}
        result = validator.check("SkillSpec")
        print(result.explain())
        print()
        
        # Add SkillPackage
        cat.add(
            "SkillPackage",
            is_a=["Instance"],
            part_of=["YOUKNOW"],
            produces=["Skill"],
        )
        
        # Skill doesn't exist but is likely a foundation concept...
        # For now, let's add it
        cat.add(
            "Skill",
            is_a=["Entity"],
            part_of=["YOUKNOW"],
            produces=["Capability"],
        )
        
        cat.add(
            "Capability",
            is_a=["Entity"],
            part_of=["YOUKNOW"],
            produces=["Entity"],  # Bootstrap to foundation
        )
        
        print("4. SkillSpec (fully connected):")
        validator._cache = {}
        result = validator.check("SkillSpec")
        print(result.explain())
        
    except ImportError:
        print("   (Cat of Cat not available in standalone mode)")
