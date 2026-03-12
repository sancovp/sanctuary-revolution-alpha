"""YOUKNOW Metastack Bridge - Template Generation Helper

This module helps LLMs generate from YOUKNOW templates:

    1. generate_template("Dog") → writes fillable script
    2. LLM fills the script, runs it → gets output
    3. LLM adds to Carton via add_concept/observe_from_identity_pov
    4. Carton triggers YOUKNOW codegen automatically
    5. New Python class exists in YOUKNOW

The bridge does steps 1-2. Carton does the rest.

Usage:
    # Step 1: Generate template
    result = generate_template("BlogPost")
    # Returns: {"script_path": "/tmp/...", "output_path": "/tmp/...", "carton_ready": {...}}
    
    # Step 2: LLM fills script.py variables, runs it
    
    # Step 3: LLM calls Carton
    mcp_carton_add_concept(
        concept_name="My_Blog_Post",
        concept="...",
        relationships=[
            {"relationship": "is_a", "related": ["BlogPost"]},
            {"relationship": "generated_from", "related": ["BlogPost"]}
        ]
    )
    
    # Step 4-5: Carton + YOUKNOW handle codegen automatically
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Type, List
from pydantic import BaseModel


# =============================================================================
# TEMPLATE SCRIPT GENERATION
# =============================================================================

def generate_template(
    concept_name: str,
    fields: Dict[str, str],  # {field_name: field_type_hint}
    output_dir: str = "/tmp",
    description: str = ""
) -> Dict[str, Any]:
    """Generate a fillable template script for a concept.
    
    Args:
        concept_name: Name of the concept to generate
        fields: Dictionary of field_name → type_hint
        output_dir: Where to write the script
        description: Description of what this generates
        
    Returns:
        Dict with script_path, output_path, and carton_ready structure
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = f"youknow_{concept_name.lower()}_{timestamp}.py"
    script_path = Path(output_dir) / script_name
    output_path = Path(output_dir) / f"generated_{concept_name.lower()}_{timestamp}.json"
    
    # Generate the script content
    script_content = f'''#!/usr/bin/env python3
"""YOUKNOW Template: {concept_name}

{description}

Instructions:
1. Fill in the variables below
2. Run: python3 {script_path}
3. Add the result to Carton to make it a generator

Generated: {datetime.now().isoformat()}
"""

import json
from pathlib import Path

# =============================================================================
# FILL THESE VARIABLES
# =============================================================================

'''
    
    for field_name, field_type in fields.items():
        script_content += f'{field_name}: {field_type} = ""  # <-- FILL THIS\n'
    
    script_content += f'''

# =============================================================================
# RENDER (don't edit below unless you know what you're doing)
# =============================================================================

def render() -> dict:
    """Collect filled data into structured output."""
    return {{
'''
    
    for field_name in fields.keys():
        script_content += f'        "{field_name}": {field_name},\n'
    
    script_content += f'''    }}

def to_carton_concept() -> dict:
    """Generate Carton-ready structure for adding to KG."""
    data = render()
    return {{
        "concept_name": "{concept_name}_" + data.get("title", "Instance").replace(" ", "_"),
        "concept": json.dumps(data, indent=2),
        "relationships": [
            {{"relationship": "is_a", "related": ["{concept_name}"]}},
            {{"relationship": "generated_from", "related": ["{concept_name}"]}}
        ]
    }}

if __name__ == "__main__":
    data = render()
    print("=== Rendered Data ===")
    print(json.dumps(data, indent=2))
    
    # Write output
    output_path = Path("{output_path}")
    output_path.write_text(json.dumps(data, indent=2))
    print(f"\\nWritten to: {{output_path}}")
    
    # Show Carton-ready structure
    print("\\n=== To add to Carton ===")
    carton = to_carton_concept()
    print(json.dumps(carton, indent=2))
    print("\\nCall mcp_carton_add_concept with the above to make this a generator.")
'''
    
    # Write the script
    script_path.write_text(script_content)
    os.chmod(script_path, 0o755)
    
    return {
        "script_path": str(script_path),
        "output_path": str(output_path),
        "instructions": [
            f"1. Edit {script_path} to fill in the variables",
            f"2. Run: python3 {script_path}",
            "3. Use the Carton-ready output to call mcp_carton_add_concept",
            "4. Carton + YOUKNOW will codegen the new class automatically"
        ],
        "carton_template": {
            "concept_name": f"{concept_name}_YOUR_INSTANCE_NAME",
            "relationships": [
                {"relationship": "is_a", "related": [concept_name]},
                {"relationship": "generated_from", "related": [concept_name]}
            ]
        }
    }


# =============================================================================
# HELPER: Read YOUKNOW class fields from existing Python class
# =============================================================================

def introspect_class(cls: type) -> Dict[str, str]:
    """Extract field names and types from a Pydantic class."""
    fields = {}
    if hasattr(cls, 'model_fields'):
        for field_name, field_info in cls.model_fields.items():
            type_name = getattr(field_info.annotation, '__name__', str(field_info.annotation))
            fields[field_name] = type_name
    return fields


def generate_from_class(cls: type, output_dir: str = "/tmp") -> Dict[str, Any]:
    """Generate template from an existing YOUKNOW class."""
    fields = introspect_class(cls)
    description = cls.__doc__ or f"Template for {cls.__name__}"
    return generate_template(
        concept_name=cls.__name__,
        fields=fields,
        output_dir=output_dir,
        description=description
    )


# =============================================================================
# EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Example: Generate a BlogPost template
    result = generate_template(
        concept_name="BlogPost",
        fields={
            "title": "str",
            "author": "str", 
            "content": "str",
            "tags": "List[str]"
        },
        description="A blog post for technical content"
    )
    
    print("Generated template:")
    print(json.dumps(result, indent=2))
