"""Universal Pattern - Semantic Clip Boundaries for Category Membership.

The dynamic enum is a restricted language set.
LOW/HIGH are clip points that define what's valid for a category.
New entries can be added within the clip.

The LLM does the reasoning. YOUKNOW surfaces the constraints.
"""

from typing import Any, Dict, List, Callable, Generic, TypeVar, Optional, Set, Mapping
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from enum import Enum
import json
import re
from pathlib import Path

T = TypeVar("T")

RELATION_TOKENS: Set[str] = {
    "is_a",
    "part_of",
    "has_part",
    "produces",
    "embodies",
    "manifests",
    "reifies",
    "compareFrom",
    "mapsTo",
    "analogicalPattern",
    "intuition",
}


@dataclass
class SESDepthReport:
    """SES typed-depth report computed from constructor argument structure."""
    constructor_name: str
    arg_count_total: int
    arg_count_typed: int
    max_typed_depth: int
    first_arbitrary_string_depth: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "constructor_name": self.constructor_name,
            "arg_count_total": self.arg_count_total,
            "arg_count_typed": self.arg_count_typed,
            "max_typed_depth": self.max_typed_depth,
            "first_arbitrary_string_depth": self.first_arbitrary_string_depth,
        }


def compute_ses_typed_depth(
    constructor_name: str,
    constructor_args: Mapping[str, Any],
    typed_symbols: Optional[Set[str]] = None,
) -> SESDepthReport:
    """Compute SES typed-depth from constructor args via recursive drill-down."""
    typed_symbols = typed_symbols or set()
    args = {
        key: value
        for key, value in constructor_args.items()
        if not _is_empty_constructor_value(value)
    }

    arg_count_total = len(args)
    arg_count_typed = 0
    max_typed_depth = 0
    first_arbitrary: Optional[int] = None

    for value in args.values():
        root_typed = _is_typed_value(value, typed_symbols)
        if root_typed:
            arg_count_typed += 1

        typed_depth, arg_first_arbitrary = _scan_typed_depth(
            value,
            depth=1,
            typed_symbols=typed_symbols,
        )
        max_typed_depth = max(max_typed_depth, typed_depth)
        first_arbitrary = _min_non_none(first_arbitrary, arg_first_arbitrary)

    return SESDepthReport(
        constructor_name=constructor_name,
        arg_count_total=arg_count_total,
        arg_count_typed=arg_count_typed,
        max_typed_depth=max_typed_depth,
        first_arbitrary_string_depth=first_arbitrary,
    )


def _scan_typed_depth(
    value: Any,
    depth: int,
    typed_symbols: Set[str],
) -> tuple[int, Optional[int]]:
    """Return max typed depth and first arbitrary-string depth for value."""
    if _is_empty_constructor_value(value):
        return (depth - 1, None)

    if isinstance(value, Mapping):
        max_depth = depth
        first_arbitrary: Optional[int] = None
        for child in value.values():
            child_depth, child_first = _scan_typed_depth(
                child,
                depth + 1,
                typed_symbols,
            )
            max_depth = max(max_depth, child_depth)
            first_arbitrary = _min_non_none(first_arbitrary, child_first)
        return (max_depth, first_arbitrary)

    if isinstance(value, (list, tuple, set)):
        max_depth = depth
        first_arbitrary = None
        for child in value:
            child_depth, child_first = _scan_typed_depth(
                child,
                depth + 1,
                typed_symbols,
            )
            max_depth = max(max_depth, child_depth)
            first_arbitrary = _min_non_none(first_arbitrary, child_first)
        return (max_depth, first_arbitrary)

    if isinstance(value, BaseModel):
        return _scan_typed_depth(value.model_dump(), depth, typed_symbols)

    if isinstance(value, str):
        if _is_typed_token(value, typed_symbols):
            return (depth, None)
        return (depth - 1, depth)

    if isinstance(value, (int, float, bool)):
        return (depth, None)

    return (depth, None)


def _is_typed_value(value: Any, typed_symbols: Set[str]) -> bool:
    """Whether the top-level constructor arg is typed (non-arbitrary)."""
    if _is_empty_constructor_value(value):
        return False
    if isinstance(value, str):
        return _is_typed_token(value, typed_symbols)
    if isinstance(value, Mapping):
        return len(value) > 0
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, BaseModel):
        return True
    return True


def _is_typed_token(token: str, typed_symbols: Set[str]) -> bool:
    """Token typedness check with registry-aware behavior."""
    token = token.strip()
    if not token:
        return False

    if typed_symbols:
        return token in typed_symbols or token in RELATION_TOKENS

    if token in RELATION_TOKENS:
        return True

    # Fallback heuristic when no typed symbol registry is provided.
    return bool(re.match(r"^[A-Z][A-Za-z0-9_]*$", token))


def _is_empty_constructor_value(value: Any) -> bool:
    """Treat empty slots as absent constructor arguments."""
    return value is None or value == "" or value == [] or value == {} or value == ()


def _min_non_none(left: Optional[int], right: Optional[int]) -> Optional[int]:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


# =============================================================================
# SEMANTIC ATTRIBUTE - Clip Boundaries
# =============================================================================

class SemanticAttribute(BaseModel, Generic[T]):
    """A value with semantic clip boundaries.
    
    low: Entry threshold - minimum to BE this thing
    high: Exit threshold - maximum before it STOPS being this thing
    value: Current value (must be within clip)
    
    The dynamic enum lives between low and high.
    New entries can be added within the clip.
    """
    value: Any = None      # T - current value
    low: Any = None        # T - entry threshold (clip point)
    high: Any = None       # T - exit threshold (clip point)
    
    # The restricted enum - values that have been validated within bounds
    enum_values: List[Any] = Field(default_factory=list)
    
    # Type hint for the spectrum
    type_hint: str = "str"  # What kind of values this holds
    
    model_config = {"arbitrary_types_allowed": True}
    
    def within_clip(self, proposed_value: Any) -> bool:
        """Check if proposed value is within semantic bounds.
        
        This is the method that NEEDS LLM REASONING for semantic comparison.
        Returns True/False but the actual logic requires semantic judgment.
        
        For now: if low/high are None, any value is within bounds.
        When low/high are set, LLM must reason about whether proposed_value
        is between them in the semantic spectrum.
        """
        if self.low is None and self.high is None:
            # Unrestricted - anything goes (but still gets added to enum)
            return True
        
        # If bounds exist, we need semantic comparison
        # For primitive types, we can do it directly
        if isinstance(self.value, (int, float)):
            low_ok = self.low is None or proposed_value >= self.low
            high_ok = self.high is None or proposed_value <= self.high
            return low_ok and high_ok
        
        # For complex types, we return True and let LLM reason
        # The warning system surfaces low/high for LLM to judge
        return True
    
    def add_to_enum(self, value: Any) -> bool:
        """Add a value to the restricted enum if within bounds."""
        if self.within_clip(value):
            if value not in self.enum_values:
                self.enum_values.append(value)
            return True
        return False
    
    def warning_message(self, proposed_value: Any) -> str:
        """Generate YOUKNOW warning for LLM reasoning."""
        return (
            f"YOUKNOW: Checking if '{proposed_value}' is valid.\n"
            f"  Type: {self.type_hint}\n"
            f"  Low (entry threshold): {self.low}\n"
            f"  High (exit threshold): {self.high}\n"
            f"  Current enum values: {self.enum_values[:10]}{'...' if len(self.enum_values) > 10 else ''}\n"
            f"  YOU decide: Is '{proposed_value}' within these bounds?"
        )


# =============================================================================
# PROPERTY NAMING CONVENTION - Progressive Typing
# =============================================================================

# Primitive type hints that require scope prefix
PRIMITIVES = {'str', 'int', 'float', 'bool', 'list', 'dict', 'any'}


def validate_property_name(prop_name: str, type_hint: str) -> tuple:
    """Validate property name follows progressive typing convention.
    
    Rule: Properties with primitive types need {scope}_{hint} pattern.
    This enables: dog_name: str → dog_name: DogName
    
    Args:
        prop_name: The property name (e.g., "dog_name")
        type_hint: The type hint (e.g., "str")
    
    Returns:
        (is_valid, error_message, suggested_type_name)
    """
    type_lower = type_hint.lower()
    
    # If not a primitive, naming is flexible
    if type_lower not in PRIMITIVES:
        return (True, None, type_hint)
    
    # For primitives, require underscore prefix
    if '_' not in prop_name:
        return (
            False,
            f"Property '{prop_name}' with primitive type '{type_hint}' needs scope prefix. "
            f"Use '{prop_name}_value: {type_hint}' or similar pattern like 'dog_name', 'fang_count'.",
            None
        )
    
    # Check it's not just underscore prefix (like _name)
    parts = prop_name.split('_')
    if len(parts) < 2 or parts[0] == '' or parts[-1] == '':
        return (
            False,
            f"Property '{prop_name}' needs format '{{scope}}_{{hint}}' like 'dog_name', 'fang_count'.",
            None
        )
    
    # Generate the future type name from the property name
    # dog_name → DogName, fang_count → FangCount
    suggested_type = ''.join(word.capitalize() for word in parts)
    
    return (True, None, suggested_type)


def property_to_type_name(prop_name: str) -> str:
    """Convert property name to its future type name.
    
    dog_name → DogName
    fang_count → FangCount
    scariness_level → ScarinessLevel
    """
    parts = prop_name.split('_')
    return ''.join(word.capitalize() for word in parts)


@dataclass
class SemanticProperty(Generic[T]):
    """Named attribute with listeners for change tracking.
    
    Property names must follow progressive typing convention:
    - Primitives need scope prefix: dog_name, fang_count
    - This enables: dog_name: str → dog_name: DogName
    """
    name: str
    attr: SemanticAttribute
    listeners: List[Callable[[T], None]] = field(default_factory=list)
    _validated: bool = field(default=False, init=False)
    _future_type: Optional[str] = field(default=None, init=False)
    
    def __post_init__(self):
        """Validate naming convention."""
        is_valid, error, future_type = validate_property_name(self.name, self.attr.type_hint)
        if not is_valid:
            # Warn but don't block - SOUP can have invalid names
            print(f"[YOUKNOW NAMING] ⚠ {error}")
        self._validated = is_valid
        self._future_type = future_type
    
    @property
    def future_type_name(self) -> Optional[str]:
        """What type this property will become when fully typed."""
        return self._future_type
    
    def set(self, new_val: T, llm_approved: bool = True) -> str:
        """Set new value. Returns warning message if bounds might be exceeded."""
        warning = self.attr.warning_message(new_val)
        
        if llm_approved:
            # LLM has reasoned this is valid
            self.attr.add_to_enum(new_val)
            self.attr.value = new_val
            for cb in self.listeners:
                cb(new_val)
            return f"Set {self.name} = {new_val} (added to enum)"
        else:
            return warning
    
    def on_change(self, cb: Callable[[T], None]) -> None:
        self.listeners.append(cb)


# =============================================================================
# UNIVERSAL PATTERN - Base for all semantic templates
# =============================================================================

class UniversalPattern:
    """Base class for semantic templates with clip boundaries.
    
    Stores as JSON config. Loads on demand.
    Each property has low/high clip boundaries.
    """
    
    def __init__(self, name: str, **props: SemanticProperty):
        self.name = name
        self._props: Dict[str, SemanticProperty] = props
        self.ses_layer: int = 0  # How many layers typed
        self.is_ont: bool = False  # In ONT? (fully typed, generatable)
    
    def prop(self, name: str) -> SemanticProperty:
        return self._props[name]
    
    def values(self) -> Dict[str, Any]:
        return {k: p.attr.value for k, p in self._props.items()}
    
    def bounds(self) -> Dict[str, Dict[str, Any]]:
        """Get all bounds for all properties."""
        return {
            k: {"low": p.attr.low, "high": p.attr.high, "type": p.attr.type_hint}
            for k, p in self._props.items()
        }
    
    def enums(self) -> Dict[str, List[Any]]:
        """Get all dynamic enums."""
        return {k: p.attr.enum_values for k, p in self._props.items()}
    
    def to_json(self) -> Dict[str, Any]:
        """Serialize to JSON config for storage."""
        return {
            "name": self.name,
            "ses_layer": self.ses_layer,
            "is_ont": self.is_ont,
            "properties": {
                k: {
                    "value": p.attr.value,
                    "low": p.attr.low,
                    "high": p.attr.high,
                    "type_hint": p.attr.type_hint,
                    "enum_values": p.attr.enum_values
                }
                for k, p in self._props.items()
            }
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "UniversalPattern":
        """Load from JSON config."""
        props = {}
        for k, v in data.get("properties", {}).items():
            attr = SemanticAttribute(
                value=v.get("value"),
                low=v.get("low"),
                high=v.get("high"),
                type_hint=v.get("type_hint", "str"),
                enum_values=v.get("enum_values", [])
            )
            props[k] = SemanticProperty(name=k, attr=attr)
        
        pattern = cls(name=data["name"], **props)
        pattern.ses_layer = data.get("ses_layer", 0)
        pattern.is_ont = data.get("is_ont", False)
        return pattern
    
    def youknow_warning(self) -> str:
        """Generate full YOUKNOW warning with all bounds."""
        lines = [f"YOUKNOW: Pattern '{self.name}'"]
        lines.append(f"  SES Layer: {self.ses_layer}")
        lines.append(f"  In ONT: {self.is_ont}")
        lines.append("  Properties:")
        for k, p in self._props.items():
            lines.append(f"    {k}:")
            lines.append(f"      Type: {p.attr.type_hint}")
            lines.append(f"      Low: {p.attr.low}")
            lines.append(f"      High: {p.attr.high}")
            lines.append(f"      Enum: {p.attr.enum_values[:5]}{'...' if len(p.attr.enum_values) > 5 else ''}")
        return "\n".join(lines)


# =============================================================================
# PATTERN REGISTRY - JSON storage, lazy loading
# =============================================================================

class PatternRegistry:
    """Registry of UniversalPatterns stored as JSON.
    
    Lazy loading - patterns loaded on demand.
    Scales to millions of patterns.
    """
    
    def __init__(self, storage_dir: str = "/tmp/youknow_patterns"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, UniversalPattern] = {}
    
    def save(self, pattern: UniversalPattern) -> str:
        """Save pattern to JSON file."""
        path = self.storage_dir / f"{pattern.name}.json"
        path.write_text(json.dumps(pattern.to_json(), indent=2))
        self._cache[pattern.name] = pattern
        return str(path)
    
    def load(self, name: str) -> Optional[UniversalPattern]:
        """Load pattern from JSON (cached)."""
        if name in self._cache:
            return self._cache[name]
        
        path = self.storage_dir / f"{name}.json"
        if not path.exists():
            return None
        
        data = json.loads(path.read_text())
        pattern = UniversalPattern.from_json(data)
        self._cache[name] = pattern
        return pattern
    
    def exists(self, name: str) -> bool:
        """Check if pattern exists."""
        return name in self._cache or (self.storage_dir / f"{name}.json").exists()
    
    def list_ont(self) -> List[str]:
        """List all ONT patterns (generatable)."""
        result = []
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text())
            if data.get("is_ont", False):
                result.append(data["name"])
        return result
    
    def list_soup(self) -> List[str]:
        """List all SOUP patterns (not yet generatable)."""
        result = []
        for path in self.storage_dir.glob("*.json"):
            data = json.loads(path.read_text())
            if not data.get("is_ont", False):
                result.append(data["name"])
        return result


# Global registry
PATTERN_REGISTRY = PatternRegistry()


# =============================================================================
# EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Create a Barney pattern
    barney = UniversalPattern(
        name="Barney",
        fang_ness=SemanticProperty(
            name="fang_ness",
            attr=SemanticAttribute(
                value=0,
                low=0,
                high=2,
                type_hint="int",
                enum_values=[0, 1, 2]
            )
        ),
        scariness=SemanticProperty(
            name="scariness",
            attr=SemanticAttribute(
                value="gentle",
                low="gentle",
                high="playful_chase",
                type_hint="str",
                enum_values=["gentle", "silly", "playful_chase"]
            )
        )
    )
    
    print(barney.youknow_warning())
    
    # Save to JSON
    path = PATTERN_REGISTRY.save(barney)
    print(f"\nSaved to: {path}")
    
    # Load back
    loaded = PATTERN_REGISTRY.load("Barney")
    print(f"\nLoaded: {loaded.name}, SES Layer: {loaded.ses_layer}")
