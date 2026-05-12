# DEAD CODE — Commented out 2026-03-29. Not imported by anything. Codegen vendoring not yet wired.
# """
# YOUKNOW Codegen Vendor

# Vendors ontology instances to real code files.

# The flow:
# 1. Instance (e.g., MyBrowserSkill) 
   # → produces → Config (e.g., MyBrowserSkillConfig)
   # → is_a → Class (e.g., SkillSpec)

# 2. Vendor looks up:
   # - The config values
   # - The class template
   
# 3. Renders template with config values

# 4. Writes to output path
# """

# import os
# from pathlib import Path
# from typing import Dict, Any, Optional, List
# from dataclasses import dataclass, field
# from datetime import datetime
# import json

# # Try to import Carton for concept lookup
# try:
    # from carton_mcp import get_concept as carton_get_concept
    # HAS_CARTON = True
# except ImportError:
    # HAS_CARTON = False
    # carton_get_concept = None


# @dataclass
# class CodeObjectConfig:
    # """Configuration for a code object instance."""
    # name: str
    # parent_class: str
    # values: Dict[str, Any] = field(default_factory=dict)
    
    # # Resolved content (concepts → actual content)
    # resolved_values: Dict[str, str] = field(default_factory=dict)


# @dataclass 
# class VendorResult:
    # """Result of vendoring."""
    # success: bool
    # output_path: str
    # files_created: List[str] = field(default_factory=list)
    # errors: List[str] = field(default_factory=list)


# # =============================================================================
# # TEMPLATES - Each CodeObject class has a template
# # =============================================================================

# TEMPLATES = {}

# # SkillSpec template
# TEMPLATES['SkillSpec'] = {
    # 'structure': 'directory',  # Creates a directory
    # 'files': {
        # 'SKILL.md': '''---
# name: {{ name }}
# description: {{ description }}
# ---

# {{ skill_md }}
# ''',
        # 'reference.md': '''# {{ name }} Reference

# {{ reference_md }}
# ''',
    # },
    # 'subdirs': {
        # 'resources': '{{ resources }}',
        # 'scripts': '{{ scripts }}',
    # },
    # 'required_fields': ['name', 'domain', 'category'],
    # 'optional_fields': ['skill_md', 'reference_md', 'resources', 'scripts', 'what', 'when'],
# }

# # MCPSpec template  
# TEMPLATES['MCPSpec'] = {
    # 'structure': 'directory',
    # 'files': {
        # '__init__.py': '''"""{{ name }} MCP Server"""

# from .server import main

# if __name__ == "__main__":
    # main()
# ''',
        # 'server.py': '''"""{{ name }} MCP Server Implementation"""

# import asyncio
# from mcp.server import Server

# server = Server("{{ name }}")

# # Tools defined here
# {{ tools_code }}

# def main():
    # asyncio.run(server.run())
# ''',
    # },
    # 'required_fields': ['name', 'command'],
    # 'optional_fields': ['args', 'env', 'tools', 'package_path'],
# }

# # HookSpec template
# TEMPLATES['HookSpec'] = {
    # 'structure': 'file',
    # 'content': '''#!/usr/bin/env python3
# """{{ name }} Hook - {{ hook_type }}"""

# def hook(context):
    # """Hook implementation.
    
    # {{ description }}
    # """
    # {{ hook_body }}
    # return context
# ''',
    # 'required_fields': ['name', 'hook_type'],
    # 'optional_fields': ['description', 'hook_body'],
# }


# # =============================================================================
# # VENDOR ENGINE
# # =============================================================================

# class VendorEngine:
    # """Vendors ontology instances to real code."""
    
    # def __init__(self, templates: Dict[str, Dict] = None):
        # self.templates = templates or TEMPLATES
        # self._concept_cache: Dict[str, Dict] = {}
    
    # def get_concept(self, name: str) -> Optional[Dict[str, Any]]:
        # """Get concept from Carton or cache."""
        # if name in self._concept_cache:
            # return self._concept_cache[name]
        
        # if HAS_CARTON and carton_get_concept:
            # try:
                # concept = carton_get_concept(name)
                # self._concept_cache[name] = concept
                # return concept
            # except Exception:
                # pass
        
        # return None
    
    # def resolve_config(self, instance_name: str) -> Optional[CodeObjectConfig]:
        # """Resolve an instance to its config.
        
        # Looks up:
        # - instance → produces → config concept
        # - instance → is_a → parent class
        # - config concept → all has_* relationships → values
        # """
        # instance = self.get_concept(instance_name)
        # if not instance:
            # return None
        
        # # Find parent class (is_a)
        # relationships = instance.get('relationships', {})
        # is_a = relationships.get('is_a', [])
        # parent_class = is_a[0] if is_a else 'CodeObject'
        
        # # Find config (produces)
        # produces = relationships.get('produces', [])
        # config_name = produces[0] if produces else None
        
        # # Build values from has_* relationships
        # values = {}
        # for rel_type, targets in relationships.items():
            # if rel_type.startswith('has_'):
                # field_name = rel_type[4:]  # strip 'has_'
                # values[field_name] = targets[0] if len(targets) == 1 else targets
        
        # # Add description
        # values['name'] = instance_name
        # values['description'] = instance.get('description', '')
        
        # # If we have a config concept, merge its values
        # if config_name:
            # config_concept = self.get_concept(config_name)
            # if config_concept:
                # config_rels = config_concept.get('relationships', {})
                # for rel_type, targets in config_rels.items():
                    # if rel_type.startswith('has_'):
                        # field_name = rel_type[4:]
                        # if field_name not in values:
                            # values[field_name] = targets[0] if len(targets) == 1 else targets
        
        # return CodeObjectConfig(
            # name=instance_name,
            # parent_class=parent_class,
            # values=values
        # )
    
    # def resolve_content(self, config: CodeObjectConfig) -> CodeObjectConfig:
        # """Resolve concept references to actual content.
        
        # If a value is a concept name, replace it with the concept's description.
        # """
        # for key, value in config.values.items():
            # if isinstance(value, str):
                # # Check if it's a concept name
                # concept = self.get_concept(value)
                # if concept:
                    # config.resolved_values[key] = concept.get('description', value)
                # else:
                    # config.resolved_values[key] = value
            # elif isinstance(value, list):
                # # List of concept names
                # resolved = []
                # for item in value:
                    # concept = self.get_concept(item)
                    # if concept:
                        # resolved.append(concept.get('description', item))
                    # else:
                        # resolved.append(item)
                # config.resolved_values[key] = resolved
            # else:
                # config.resolved_values[key] = value
        
        # return config
    
    # def render_template(self, template_str: str, values: Dict[str, Any]) -> str:
        # """Simple template rendering ({{ var }} style)."""
        # result = template_str
        # for key, value in values.items():
            # placeholder = '{{ ' + key + ' }}'
            # if isinstance(value, list):
                # value = '\n'.join(str(v) for v in value)
            # result = result.replace(placeholder, str(value) if value else '')
        
        # # Clean up unreplaced placeholders
        # import re
        # result = re.sub(r'\{\{\s*\w+\s*\}\}', '', result)
        
        # return result
    
    # def vendor(
        # self, 
        # instance_name: str, 
        # output_path: str,
        # dry_run: bool = False
    # ) -> VendorResult:
        # """Vendor an instance to real code files.
        
        # Args:
            # instance_name: Name of the concept instance
            # output_path: Where to write the files
            # dry_run: If True, don't write files, just return what would be created
        # """
        # result = VendorResult(success=False, output_path=output_path)
        
        # # 1. Resolve config
        # config = self.resolve_config(instance_name)
        # if not config:
            # result.errors.append(f"Could not resolve config for {instance_name}")
            # return result
        
        # # 2. Resolve content (concept refs → actual content)
        # config = self.resolve_content(config)
        
        # # 3. Get template for parent class
        # template = self.templates.get(config.parent_class)
        # if not template:
            # result.errors.append(f"No template for class {config.parent_class}")
            # return result
        
        # # 4. Check required fields
        # values = {**config.values, **config.resolved_values}
        # for field in template.get('required_fields', []):
            # if field not in values or not values[field]:
                # result.errors.append(f"Missing required field: {field}")
        
        # if result.errors:
            # return result
        
        # # 5. Render and write
        # output_dir = Path(output_path)
        
        # if template['structure'] == 'directory':
            # # Create directory
            # if not dry_run:
                # output_dir.mkdir(parents=True, exist_ok=True)
            
            # # Create files
            # for filename, content_template in template.get('files', {}).items():
                # rendered = self.render_template(content_template, values)
                # file_path = output_dir / filename
                # result.files_created.append(str(file_path))
                
                # if not dry_run:
                    # file_path.write_text(rendered)
            
            # # Create subdirs
            # for subdir, content in template.get('subdirs', {}).items():
                # subdir_path = output_dir / subdir
                # if not dry_run:
                    # subdir_path.mkdir(exist_ok=True)
                # result.files_created.append(str(subdir_path))
        
        # elif template['structure'] == 'file':
            # # Single file
            # rendered = self.render_template(template['content'], values)
            # result.files_created.append(str(output_dir))
            
            # if not dry_run:
                # output_dir.parent.mkdir(parents=True, exist_ok=True)
                # output_dir.write_text(rendered)
        
        # result.success = True
        # return result
    
    # def vendor_from_dict(
        # self,
        # instance_name: str,
        # parent_class: str,
        # values: Dict[str, Any],
        # output_path: str,
        # dry_run: bool = False
    # ) -> VendorResult:
        # """Vendor directly from a dict (no Carton lookup).
        
        # Useful for testing or when concepts aren't in Carton yet.
        # """
        # config = CodeObjectConfig(
            # name=instance_name,
            # parent_class=parent_class,
            # values=values,
            # resolved_values=values
        # )
        
        # # Get template
        # template = self.templates.get(parent_class)
        # if not template:
            # return VendorResult(
                # success=False,
                # output_path=output_path,
                # errors=[f"No template for class {parent_class}"]
            # )
        
        # result = VendorResult(success=False, output_path=output_path)
        
        # # Check required fields
        # for field in template.get('required_fields', []):
            # if field not in values or not values[field]:
                # result.errors.append(f"Missing required field: {field}")
        
        # if result.errors:
            # return result
        
        # # Render
        # output_dir = Path(output_path)
        
        # if template['structure'] == 'directory':
            # if not dry_run:
                # output_dir.mkdir(parents=True, exist_ok=True)
            
            # for filename, content_template in template.get('files', {}).items():
                # rendered = self.render_template(content_template, values)
                # file_path = output_dir / filename
                # result.files_created.append(str(file_path))
                
                # if not dry_run:
                    # file_path.write_text(rendered)
        
        # result.success = True
        # return result


# # =============================================================================
# # DEMO
# # =============================================================================

# if __name__ == "__main__":
    # print("=== YOUKNOW VENDOR ===")
    # print()
    
    # vendor = VendorEngine()
    
    # # Demo: Vendor a SkillSpec from dict
    # print("1. Vendoring MyBrowserSkill (SkillSpec)...")
    # result = vendor.vendor_from_dict(
        # instance_name="MyBrowserSkill",
        # parent_class="SkillSpec",
        # values={
            # 'name': 'MyBrowserSkill',
            # 'description': 'A skill for browser automation',
            # 'domain': 'PAIAB',
            # 'category': 'single_turn_process',
            # 'skill_md': '''# Browser Automation

# This skill helps you automate browser tasks.

# ## Usage
# Call with a URL and actions to perform.
# ''',
            # 'reference_md': '''## API

# - `navigate(url)` - Go to URL
# - `click(selector)` - Click element
# - `type(selector, text)` - Type into field
# ''',
        # },
        # output_path='/tmp/youknow_vendor_test/my_browser_skill',
        # dry_run=False
    # )
    
    # print(f"   Success: {result.success}")
    # print(f"   Files: {result.files_created}")
    # if result.errors:
        # print(f"   Errors: {result.errors}")
    # print()
    
    # # Show what was created
    # if result.success:
        # print("2. Created files:")
        # for f in result.files_created:
            # if os.path.isfile(f):
                # print(f"\n   📄 {f}:")
                # with open(f) as fh:
                    # for line in fh.read().split('\n')[:10]:
                        # print(f"      {line}")
