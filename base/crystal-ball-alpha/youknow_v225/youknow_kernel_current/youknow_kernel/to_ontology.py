"""
YOUKNOW @to_ontology decorator

Register Python classes in the YOUKNOW ontology automatically.
Classes decorated with @to_ontology become ONT layer entities.

Usage:
    from youknow_kernel import to_ontology
    
    @to_ontology
    class SkillSpec:
        domain: str
        category: str
        skill_md: Optional[str] = None
        
    # Now SkillSpec is in the ontology
    # Validation is automatic
    spec = SkillSpec(domain="PAIAB", category="understand")
    spec.validate()  # Raises if invalid, with YOUKNOW explanation
"""

from typing import (
    get_type_hints, Any, Dict, List, Optional, 
    Type, TypeVar, Callable, Union
)
from dataclasses import dataclass, field, fields as dataclass_fields
from datetime import datetime
from functools import wraps
import inspect


# Type variable for decorated classes
T = TypeVar('T')


class YouknowValidationError(Exception):
    """Raised when YOUKNOW validation fails."""
    
    def __init__(self, entity_name: str, what_it_is: str, errors: List[str]):
        self.entity_name = entity_name
        self.what_it_is = what_it_is
        self.errors = errors
        
        message = f"""
YOUKNOW Validation Failed for '{entity_name}'

What this IS (according to YOUKNOW):
{what_it_is}

Validation Errors:
{chr(10).join(f'  - {e}' for e in errors)}

To fix: ensure all required fields are present and correctly typed.
"""
        super().__init__(message)


# Global registry of ontology entities
_ONTOLOGY_REGISTRY: Dict[str, Dict[str, Any]] = {}


def get_ontology_entity(name: str) -> Optional[Dict[str, Any]]:
    """Get an ontology entity by name."""
    return _ONTOLOGY_REGISTRY.get(name)


def list_ontology_entities() -> List[str]:
    """List all registered ontology entities."""
    return list(_ONTOLOGY_REGISTRY.keys())


def _python_type_to_owl(python_type: Any) -> str:
    """Convert Python type annotation to OWL type."""
    type_str = str(python_type)
    
    # Handle Optional
    if "Optional" in type_str or "Union" in type_str and "None" in type_str:
        # Extract inner type
        if hasattr(python_type, "__args__"):
            inner = [a for a in python_type.__args__ if a is not type(None)]
            if inner:
                return f"optional:{_python_type_to_owl(inner[0])}"
        return "optional:string"
    
    # Handle List
    if "List" in type_str or "list" in type_str:
        if hasattr(python_type, "__args__") and python_type.__args__:
            return f"list:{_python_type_to_owl(python_type.__args__[0])}"
        return "list:any"
    
    # Handle Dict
    if "Dict" in type_str or "dict" in type_str:
        return "dict"
    
    # Basic types
    if python_type is str or python_type == str:
        return "xsd:string"
    if python_type is int or python_type == int:
        return "xsd:integer"
    if python_type is float or python_type == float:
        return "xsd:float"
    if python_type is bool or python_type == bool:
        return "xsd:boolean"
    
    # Check if it's a registered ontology entity
    if hasattr(python_type, "__name__"):
        if python_type.__name__ in _ONTOLOGY_REGISTRY:
            return f"entity:{python_type.__name__}"
    
    # Fallback
    return "xsd:string"


def _extract_class_schema(cls: Type) -> Dict[str, Any]:
    """Extract schema information from a class."""
    from dataclasses import MISSING
    
    schema = {
        "name": cls.__name__,
        "doc": cls.__doc__ or "",
        "properties": {},
        "required": [],
        "optional": [],
        "parent_classes": [],  # is_a
        "part_of": [],         # what system/module
        "produces": [],    # what it produces
    }
    
    # Get parent classes (for is_a relationships)
    for base in cls.__bases__:
        if base.__name__ != "object":
            schema["parent_classes"].append(base.__name__)
    
    # Get type hints
    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = getattr(cls, "__annotations__", {})
    
    # Determine which fields have defaults (are optional)
    has_default = set()
    
    if hasattr(cls, "__dataclass_fields__"):
        # For dataclasses, check the actual field info
        for fname, finfo in cls.__dataclass_fields__.items():
            # Field has a default if either default or default_factory is not MISSING
            if finfo.default is not MISSING or finfo.default_factory is not MISSING:
                has_default.add(fname)
    else:
        # For regular classes, check class attributes
        for name in dir(cls):
            if not name.startswith("_"):
                val = getattr(cls, name, None)
                if not callable(val):
                    has_default.add(name)
    
    # Process properties
    for name, ptype in hints.items():
        if name.startswith("_"):
            continue
            
        owl_type = _python_type_to_owl(ptype)
        
        # Optional if: has Optional type OR has a default value
        is_optional = "optional:" in owl_type or name in has_default
        
        schema["properties"][name] = {
            "type": owl_type,
            "optional": is_optional,
        }
        
        if is_optional:
            schema["optional"].append(name)
        else:
            schema["required"].append(name)
    
    return schema


def _generate_what_it_is(entity_name: str, schema: Dict[str, Any]) -> str:
    """Generate YOUKNOW's explanation of what an entity IS."""
    lines = []
    
    # Is-a chain
    if schema["parent_classes"]:
        chain = " → ".join(schema["parent_classes"])
        lines.append(f"{entity_name} IS_A {chain}")
    else:
        lines.append(f"{entity_name} IS_A OntologyEntity")
    
    # Part-of relationships
    if schema.get("part_of"):
        parts = ", ".join(schema["part_of"])
        lines.append(f"{entity_name} PART_OF {parts}")
    
    # Instantiates relationships  
    if schema.get("produces"):
        prods = ", ".join(schema["produces"])
        lines.append(f"{entity_name} INSTANTIATES {prods}")
    
    # Required properties
    if schema["required"]:
        lines.append(f"\nREQUIRED properties:")
        for prop in schema["required"]:
            pinfo = schema["properties"][prop]
            lines.append(f"  - {prop}: {pinfo['type']}")
    
    # Optional properties
    if schema["optional"]:
        lines.append(f"\nOPTIONAL properties:")
        for prop in schema["optional"]:
            pinfo = schema["properties"][prop]
            lines.append(f"  - {prop}: {pinfo['type']}")
    
    # Doc
    if schema["doc"]:
        lines.append(f"\nDOCUMENTATION: {schema['doc'][:200]}...")
    
    return "\n".join(lines)


def _validate_instance(instance: Any, schema: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate an instance against its schema."""
    errors = []
    
    # Check required properties
    for prop in schema["required"]:
        if not hasattr(instance, prop):
            errors.append(f"Missing required property: {prop}")
        else:
            val = getattr(instance, prop)
            if val is None:
                errors.append(f"Required property '{prop}' is None")
    
    # Check types (basic)
    for prop, pinfo in schema["properties"].items():
        if hasattr(instance, prop):
            val = getattr(instance, prop)
            if val is not None:
                owl_type = pinfo["type"]
                
                # Type validation
                if owl_type == "xsd:string" and not isinstance(val, str):
                    errors.append(f"Property '{prop}' should be string, got {type(val).__name__}")
                elif owl_type == "xsd:integer" and not isinstance(val, int):
                    errors.append(f"Property '{prop}' should be int, got {type(val).__name__}")
                elif owl_type == "xsd:boolean" and not isinstance(val, bool):
                    errors.append(f"Property '{prop}' should be bool, got {type(val).__name__}")
    
    return len(errors) == 0, errors


def to_ontology(cls: Type[T] = None, *, 
                name: str = None,
                is_a: List[str] = None,
                part_of: List[str] = None,
                produces: List[str] = None,
                validate_on_init: bool = False) -> Union[Type[T], Callable[[Type[T]], Type[T]]]:
    """
    Decorator to register a class in the YOUKNOW ontology.
    
    Args:
        cls: The class to register
        name: Optional custom name (defaults to class name)
        is_a: Additional is_a relationships (inheritance)
        part_of: What system/module this belongs to
        produces: What this produces/creates when called
        validate_on_init: If True, validate on __init__
        
    Returns:
        Decorated class with .validate() method
        
    Example:
        @to_ontology(
            is_a=["ComponentBase"],
            part_of=["PAIAB_System"],
            produces=["SkillPackage"],
        )
        class SkillSpec:
            domain: str
            category: str
            skill_md: Optional[str] = None
            
        spec = SkillSpec(domain="PAIAB", category="understand")
        spec.validate()  # Raises YouknowValidationError if invalid
    """
    
    def decorator(cls: Type[T]) -> Type[T]:
        entity_name = name or cls.__name__
        
        # Extract schema
        schema = _extract_class_schema(cls)
        schema["name"] = entity_name
        
        # Add extra relationships
        if is_a:
            schema["parent_classes"].extend(is_a)
        if part_of:
            schema["part_of"].extend(part_of)
        if produces:
            schema["produces"].extend(produces)
        
        # Register in ontology
        _ONTOLOGY_REGISTRY[entity_name] = schema
        
        # Generate what_it_is
        what_it_is = _generate_what_it_is(entity_name, schema)
        
        # Add validate method
        def validate(self) -> bool:
            """Validate this instance against YOUKNOW ontology.
            
            Returns:
                True if valid
                
            Raises:
                YouknowValidationError: If validation fails
            """
            valid, errors = _validate_instance(self, schema)
            
            if not valid:
                raise YouknowValidationError(
                    entity_name=entity_name,
                    what_it_is=what_it_is,
                    errors=errors
                )
            
            return True
        
        cls.validate = validate
        
        # Add _youknow_schema attribute
        cls._youknow_schema = schema
        cls._youknow_what_it_is = what_it_is
        
        # Optionally wrap __init__ to validate
        if validate_on_init:
            original_init = cls.__init__ if hasattr(cls, "__init__") else lambda self: None
            
            @wraps(original_init)
            def validating_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                self.validate()
            
            cls.__init__ = validating_init
        
        return cls
    
    # Handle both @to_ontology and @to_ontology()
    if cls is not None:
        return decorator(cls)
    return decorator


# =============================================================================
# OWL GENERATION — Code → Ontology
# =============================================================================

def schema_to_owl_xml(schema: Dict[str, Any], parent_class: str = "Entity") -> str:
    """Generate OWL class XML from an extracted schema.

    Converts required fields to minCardinality restrictions,
    entity-typed fields to someValuesFrom restrictions.

    Args:
        schema: Output from _extract_class_schema()
        parent_class: OWL parent class (default: Entity)

    Returns:
        OWL XML string for this class definition
    """
    name = schema["name"]
    lines = []

    # Open class
    lines.append(f'    <owl:Class rdf:about="#{name}">')
    lines.append(f'        <rdfs:subClassOf rdf:resource="#{parent_class}"/>')
    lines.append(f'        <rdfs:label>{name}</rdfs:label>')

    if schema.get("doc"):
        doc = schema["doc"].strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:200]
        lines.append(f'        <rdfs:comment>{doc}</rdfs:comment>')

    # Required properties → minCardinality 1
    for prop_name in schema.get("required", []):
        prop_info = schema["properties"].get(prop_name, {})
        owl_type = prop_info.get("type", "xsd:string")
        # Convert snake_case to camelCase for OWL property name
        camel = _snake_to_camel(prop_name)

        if owl_type.startswith("entity:"):
            # Entity reference → someValuesFrom
            target = owl_type.split(":", 1)[1]
            lines.append(
                f'        <rdfs:subClassOf><owl:Restriction>'
                f'<owl:onProperty rdf:resource="#{camel}"/>'
                f'<owl:someValuesFrom rdf:resource="#{target}"/>'
                f'</owl:Restriction></rdfs:subClassOf>'
            )
        else:
            # Primitive type → minCardinality 1
            lines.append(
                f'        <rdfs:subClassOf><owl:Restriction>'
                f'<owl:onProperty rdf:resource="#{camel}"/>'
                f'<owl:minCardinality rdf:datatype="http://www.w3.org/2001/XMLSchema#nonNegativeInteger">1</owl:minCardinality>'
                f'</owl:Restriction></rdfs:subClassOf>'
            )

    # Close class
    lines.append(f'    </owl:Class>')

    return "\n".join(lines)


def schema_to_owl_properties(schema: Dict[str, Any]) -> List[str]:
    """Generate OWL property declarations for all properties in a schema.

    Returns list of OWL XML strings for each property.
    Only generates properties not already common (is_a, part_of, etc.)
    """
    common = {
        "name", "description", "doc", "is_a", "part_of", "instantiates",
        "has_part", "has_domain", "has_category",
    }

    prop_lines = []
    for prop_name in schema.get("properties", {}):
        if prop_name in common:
            continue
        camel = _snake_to_camel(prop_name)
        label = prop_name
        prop_lines.append(
            f'    <owl:ObjectProperty rdf:about="#{camel}">'
            f'<rdfs:label>{label}</rdfs:label>'
            f'</owl:ObjectProperty>'
        )

    return prop_lines


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def generate_owl_from_modules(*modules) -> str:
    """Scan Python modules for classes and generate OWL XML for all of them.

    Args:
        *modules: Python modules to scan (e.g., paia_builder.models)

    Returns:
        OWL XML fragment with all class definitions and property declarations
    """
    all_schemas = []
    all_properties = []
    seen_props = set()

    for module in modules:
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if not isinstance(obj, type):
                continue
            if attr_name.startswith("_"):
                continue

            try:
                schema = _extract_class_schema(obj)
                if schema["properties"]:  # Only include classes with typed fields
                    all_schemas.append(schema)

                    for prop_xml in schema_to_owl_properties(schema):
                        prop_key = prop_xml.split('"#')[1].split('"')[0] if '"#' in prop_xml else prop_xml
                        if prop_key not in seen_props:
                            seen_props.add(prop_key)
                            all_properties.append(prop_xml)
            except Exception:
                continue

    # Build output
    parts = []
    parts.append("    <!-- AUTO-GENERATED from Python types -->")
    parts.append("")

    # Properties first
    if all_properties:
        parts.append("    <!-- Properties -->")
        parts.extend(all_properties)
        parts.append("")

    # Then classes
    parts.append("    <!-- Classes -->")
    for schema in all_schemas:
        parent = schema["parent_classes"][0] if schema["parent_classes"] else "Entity"
        parts.append(schema_to_owl_xml(schema, parent_class=parent))

    return "\n".join(parts)


# =============================================================================
# INTEGRATION WITH Y-MESH (if available)
# =============================================================================

def sync_to_ymesh(ymesh=None):
    """Sync all registered ontology entities to YO-strata (or legacy Y-mesh)."""
    if ymesh is None:
        try:
            from .yo_strata import YOStrata, YLayer
            ymesh = YOStrata()
        except ImportError:
            return None
    
    from .yo_strata import YLayer
    
    for entity_name, schema in _ONTOLOGY_REGISTRY.items():
        ymesh.add_node(
            layer=YLayer.Y3_APPLICATION,
            name=entity_name,
            content={
                "properties": schema["properties"],
                "required": schema["required"],
                "doc": schema["doc"],
            },
            is_a=schema["parent_classes"]
        )
    
    return ymesh


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    from dataclasses import dataclass
    from typing import Optional, List
    
    print("=== YOUKNOW @to_ontology ===")
    print()
    
    # Define some ontology entities
    
    @to_ontology
    @dataclass
    class ComponentBase:
        """Base class for all components."""
        name: str
        description: str = ""
    
    @to_ontology(
        is_a=["ComponentBase"],
        part_of=["PAIAB_System", "Sanctuary_Revolution"],
        produces=["SkillPackage", "SkillDirectory"],
    )
    @dataclass
    class SkillSpec:
        """Specification for a PAIA skill."""
        name: str
        domain: str
        category: str
        description: str = ""
        skill_md: Optional[str] = None
        reference_md: Optional[str] = None
        scripts: List[str] = field(default_factory=list)
    
    @to_ontology
    @dataclass
    class MCPSpec:
        """Specification for an MCP server."""
        name: str
        command: str
        description: str = ""
        args: List[str] = field(default_factory=list)
        env: Optional[dict] = None
    
    # List registered entities
    print("1. Registered ontology entities:")
    for name in list_ontology_entities():
        entity = get_ontology_entity(name)
        print(f"   - {name}: {len(entity['properties'])} properties")
    print()
    
    # Create valid instance
    print("2. Creating valid SkillSpec...")
    skill = SkillSpec(
        name="BrowserAutomation",
        description="A skill for browser tasks",
        domain="PAIAB",
        category="single_turn_process",
        skill_md="# Browser Automation\n\nDoes browser stuff."
    )
    
    try:
        skill.validate()
        print("   ✅ Valid!")
    except YouknowValidationError as e:
        print(f"   ❌ {e}")
    print()
    
    # Create invalid instance
    print("3. Creating INVALID SkillSpec (missing required fields)...")
    invalid_skill = SkillSpec(
        name="Broken",
        description="",
        domain="",  # Empty string for required field
        category="",
    )
    invalid_skill.domain = None  # Force None
    
    try:
        invalid_skill.validate()
        print("   ✅ Valid!")
    except YouknowValidationError as e:
        print(f"   ❌ Caught expected error:")
        print(e)
    print()
    
    # Show what_it_is
    print("4. What YOUKNOW knows about SkillSpec:")
    print(SkillSpec._youknow_what_it_is)
