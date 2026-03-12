#!/usr/bin/env python3
"""
GIINT Blueprint System

Simple file copying system that stores template files and copies them on demand.
"""

import logging
import os
import shutil
import ast
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def save_blueprint(blueprint_name: str, source_file_path: str, description: Optional[str] = None, domain: str = "respond") -> Dict[str, Any]:
    """
    Save a blueprint by copying a template file to storage.
    
    Args:
        blueprint_name: Name of the blueprint
        source_file_path: Path to the template file to copy
        description: Optional description of the blueprint
        domain: Blueprint domain (currently only "respond" supported)
        
    Returns:
        Save result with success status
    """
    try:
        # Domain is just a semantic tag - no validation needed
        
        # Validate source file exists
        source_path = Path(source_file_path)
        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source file does not exist: {source_file_path}"
            }
        
        # Create storage directory
        storage_dir = Path("/tmp/heaven_data/giint/blueprints") / domain
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy file to storage
        stored_file_path = storage_dir / blueprint_name
        shutil.copy2(source_path, stored_file_path)
        
        # Set HEAVEN_DATA_DIR for registry access
        os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
        
        # Import HEAVEN registry
        from heaven_base.tools.registry_tool import registry_util_func
        
        # Store metadata in registry
        blueprint_data = {
            "name": blueprint_name,
            "stored_file_path": str(stored_file_path),
            "original_file_path": str(source_path),
            "domain": domain,
            "description": description or f"Blueprint template: {blueprint_name}",
            "created_at": datetime.now().isoformat()
        }
        
        # Save metadata to registry
        result = registry_util_func("add", 
                                  registry_name=f"{domain}_blueprints",
                                  key=blueprint_name,
                                  value_dict=blueprint_data)
        
        logger.info(f"Saved blueprint {blueprint_name} - copied {source_file_path} to {stored_file_path}")
        return {
            "success": True,
            "message": f"Blueprint '{blueprint_name}' saved successfully",
            "blueprint_name": blueprint_name,
            "stored_path": str(stored_file_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to save blueprint {blueprint_name}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to save blueprint: {str(e)}"
        }

def get_blueprint(blueprint_name: str, target_path: str, domain: str = "respond") -> Dict[str, Any]:
    """
    Get a blueprint by copying the stored template file to target location.
    
    Args:
        blueprint_name: Name of the blueprint to retrieve
        target_path: Where to copy the template file
        domain: Blueprint domain (currently only "respond" supported)
        
    Returns:
        Copy result with success status
    """
    try:
        # Domain is just a semantic tag - no validation needed
        
        # Set HEAVEN_DATA_DIR for registry access
        os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
        
        # Import HEAVEN registry
        from heaven_base.tools.registry_tool import registry_util_func
        
        # Get blueprint metadata from registry
        result = registry_util_func("get", 
                                  registry_name=f"{domain}_blueprints",
                                  key=blueprint_name)
        
        if "Key not found" in result:
            return {
                "success": False,
                "error": f"Blueprint '{blueprint_name}' not found"
            }
        
        # Parse the registry result
        import ast
        start_idx = result.find("{")
        if start_idx == -1:
            return {
                "success": False,
                "error": "Failed to parse blueprint metadata"
            }
        
        blueprint_data = ast.literal_eval(result[start_idx:])
        stored_file_path = Path(blueprint_data["stored_file_path"])
        
        # Validate stored file still exists
        if not stored_file_path.exists():
            return {
                "success": False,
                "error": f"Stored template file missing: {stored_file_path}"
            }
        
        # Copy stored file to target location
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stored_file_path, target)
        
        logger.info(f"Copied blueprint {blueprint_name} from {stored_file_path} to {target}")
        return {
            "success": True,
            "message": f"Blueprint '{blueprint_name}' copied to {target_path}",
            "blueprint_name": blueprint_name,
            "target_path": str(target),
            "blueprint_data": blueprint_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get blueprint {blueprint_name}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to get blueprint: {str(e)}"
        }

def list_blueprints(domain: str = "respond") -> Dict[str, Any]:
    """
    List all available blueprints in a domain.
    
    Args:
        domain: Blueprint domain to list (currently only "respond" supported)
    
    Returns:
        List of blueprints with metadata
    """
    try:
        # Domain is just a semantic tag - no validation needed
        
        # Set HEAVEN_DATA_DIR for registry access
        os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
        
        # Import HEAVEN registry
        from heaven_base.tools.registry_tool import registry_util_func
        
        # Get all blueprints from registry
        result = registry_util_func("get_all", 
                                  registry_name=f"{domain}_blueprints")
        
        if "Items in registry" not in result:
            return {
                "success": True,
                "blueprints": [],
                "message": "No blueprints found"
            }
        
        # Parse the registry data
        import ast
        start_idx = result.find("{")
        if start_idx != -1:
            registry_data = ast.literal_eval(result[start_idx:])
            
            blueprints = []
            for key, value in registry_data.items():
                # Check if stored file still exists
                stored_path = Path(value.get("stored_file_path", ""))
                file_exists = stored_path.exists() if stored_path else False
                
                blueprints.append({
                    "name": value.get("name", key),
                    "description": value.get("description", "No description"),
                    "domain": value.get("domain", domain),
                    "created_at": value.get("created_at", "Unknown"),
                    "stored_file_path": value.get("stored_file_path", ""),
                    "file_exists": file_exists
                })
            
            return {
                "success": True,
                "blueprints": blueprints,
                "count": len(blueprints)
            }
        else:
            return {
                "success": True,
                "blueprints": [],
                "message": "No blueprints found"
            }
        
    except Exception as e:
        logger.error(f"Failed to list blueprints: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to list blueprints: {str(e)}"
        }

def add_metastack_model(file_path: str, domain: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a MetaStack model Python file to the models directory.
    
    Args:
        file_path: Path to the Python file containing the MetaStack model
        domain: Domain for organizing models (e.g., "greeting", "code_review")
        model_name: Optional name for the model file (defaults to original filename)
        
    Returns:
        Result with success status and storage path
    """
    try:
        source_path = Path(file_path)
        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source file does not exist: {file_path}"
            }
        
        # Validate it's a Python file
        if source_path.suffix != '.py':
            return {
                "success": False,
                "error": "File must be a Python (.py) file"
            }
        
        # Read and validate the file content
        try:
            file_content = source_path.read_text()
        except Exception as e:
            return {
                "success": False,
                "error": f"Cannot read file: {str(e)}"
            }
        
        # Validate file contains MetaStack imports
        validation_result = _validate_metastack_file(file_content)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"]
            }
        
        # Create domain directory structure
        models_dir = Path("/tmp/heaven_data/metastack_models")
        domain_dir = models_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py files if they don't exist
        (models_dir / "__init__.py").touch(exist_ok=True)
        (domain_dir / "__init__.py").touch(exist_ok=True)
        
        # Determine target filename
        if model_name:
            if not model_name.endswith('.py'):
                model_name += '.py'
            target_filename = model_name
        else:
            target_filename = source_path.name
        
        # Copy the file
        target_path = domain_dir / target_filename
        shutil.copy2(source_path, target_path)
        
        logger.info(f"Added MetaStack model {target_filename} to domain {domain}")
        return {
            "success": True,
            "message": f"MetaStack model '{target_filename}' added to domain '{domain}'",
            "domain": domain,
            "model_name": target_filename,
            "stored_path": str(target_path)
        }
        
    except Exception as e:
        logger.error(f"Failed to add MetaStack model: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to add MetaStack model: {str(e)}"
        }

def _validate_metastack_file(file_content: str) -> Dict[str, Any]:
    """
    Validate that a Python file contains proper MetaStack model structure.
    
    Args:
        file_content: Content of the Python file to validate
        
    Returns:
        Dictionary with 'valid' boolean and 'error' message if invalid
    """
    try:
        # Parse the Python file
        tree = ast.parse(file_content)
    except SyntaxError as e:
        return {"valid": False, "error": f"Python syntax error: {str(e)}"}
    
    # Check for pydantic_stack_core import
    has_metastack_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "pydantic_stack_core":
                has_metastack_import = True
                break
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pydantic_stack_core":
                    has_metastack_import = True
                    break
    
    if not has_metastack_import:
        return {"valid": False, "error": "File must import from pydantic_stack_core. For help creating MetaStack models, run: from pydantic_stack_core import help; help()"}
    
    # Find RenderablePiece classes
    renderable_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from RenderablePiece
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "RenderablePiece":
                    renderable_classes.append(node.name)
                elif isinstance(base, ast.Attribute) and base.attr == "RenderablePiece":
                    renderable_classes.append(node.name)
    
    if not renderable_classes:
        return {"valid": False, "error": "File must contain at least one class inheriting from RenderablePiece. For help creating MetaStack models, run: from pydantic_stack_core import help; help()"}
    
    if len(renderable_classes) > 1:
        return {"valid": False, "error": f"File must contain exactly one RenderablePiece class, found: {renderable_classes}"}
    
    # Check for generation function (optional but recommended)
    has_generation_func = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if "generate" in node.name.lower():
                has_generation_func = True
                break
    
    return {
        "valid": True, 
        "class_name": renderable_classes[0],
        "has_generation_func": has_generation_func
    }