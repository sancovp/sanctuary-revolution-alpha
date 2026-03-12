#!/usr/bin/env python3
"""
Auto-population of default GIINT flight configs.

This module provides default GIINT workflow configurations that are auto-populated
when GIINT detects the flight config registry exists.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Default GIINT flight configs embedded as Python dictionaries
DEFAULT_GIINT_CONFIGS = {
    "giint_blueprint_creation_flight_config": {
        "category": "giint",
        "description": "Workflow for creating and managing GIINT blueprint templates for structured response generation",
        "payload_discovery": {
            "domain": "giint_blueprints",
            "version": "1.0.0",
            "description": "Workflow for creating and managing GIINT blueprint templates for structured response generation",
            "directories": {},
            "root_files": [
                {
                    "sequence_number": 1,
                    "filename": "01_analyze_response_pattern.md",
                    "title": "Analyze Your Response Pattern and Domain",
                    "content": """# Response Pattern Analysis

## What Type of Response Are You Blueprinting?
Identify the specific type of structured response you want to create:
- Technical analysis reports?
- Blog post templates?
- Concept documentation?
- Code review summaries?
- Research methodology guides?
- Project planning documents?

## Current Response Challenges
Document what you want to improve:
1. Do you find yourself recreating similar response structures?
2. Are there quality patterns you want to ensure consistency?
3. What sections do you always include but sometimes forget?
4. Which parts take the most time to structure from scratch?

## Target Domain
Define your blueprint domain:
- **Domain Name**: (e.g., "technical_analysis", "blog_posts", "concepts")
- **Use Cases**: When would this blueprint be most valuable?
- **Audience**: Who will use responses generated from this blueprint?
- **Success Criteria**: How will you know the blueprint is working well?

## Template Variables
Identify the key variables your template will need:
- What information changes between uses of this template?
- Which sections need customization vs. standard structure?
- What context will users need to provide?

**Action**: Document your response pattern analysis above, focusing on the specific structure and variables you want to systematize.""",
                    "piece_type": "instruction",
                    "dependencies": []
                },
                {
                    "sequence_number": 2,
                    "filename": "02_create_template_structure.md",
                    "title": "Design Your Blueprint Template Structure",
                    "content": """# Blueprint Template Design

## Template Structure Guidelines

### Variable Syntax
Use `{{variable_name}}` for template variables:
- `{{title}}` - Main title or heading
- `{{overview}}` - Summary or introduction
- `{{detailed_analysis}}` - Main content section
- `{{next_steps}}` - Action items or conclusions

### Common Template Patterns

**Technical Analysis Template**:
```markdown
# {{title}}

## Overview
{{overview}}

## Current State
{{current_state}}

## Analysis
{{analysis_details}}

## Recommendations
{{recommendations}}

## Next Steps
{{next_steps}}
```

**Concept Documentation Template**:
```markdown
# {{concept_name}}

## Definition
{{clear_definition}}

## Context
{{why_this_matters}}

## How It Works
{{step_by_step_process}}

## Examples
{{concrete_examples}}

## Related Concepts
{{related_links}}
```

## Design Principles
1. **Clear Structure**: Logical flow from introduction to conclusion
2. **Flexible Variables**: Allow customization while maintaining consistency
3. **Actionable Content**: Include sections that drive next steps
4. **Reusable Patterns**: Structure should work across multiple use cases

**Action**: Create your template structure using markdown with {{variable}} placeholders.""",
                    "piece_type": "instruction",
                    "dependencies": [1]
                },
                {
                    "sequence_number": 3,
                    "filename": "03_create_and_save_blueprint.md",
                    "title": "Create Template File and Save Blueprint",
                    "content": """# Create and Save Your Blueprint

## Step 1: Create Template File
Create a markdown file with your template structure:

```bash
# Create your template file
echo "# {{title}}

## Overview
{{overview}}

## Main Content
{{main_content}}

## Conclusion
{{conclusion}}" > /tmp/my_blueprint_template.md
```

## Step 2: Save Blueprint to GIINT
Use the GIINT workshop tools to save your blueprint:

```python
# Save blueprint using GIINT MCP
giint.workshop__save_blueprint(
    blueprint_name="my_domain_template_v1",
    source_file_path="/tmp/my_blueprint_template.md",
    description="Template for [describe your use case]",
    domain="your_domain"  # e.g., "technical_analysis", "concepts"
)
```

## Naming Convention
- Use descriptive names: `technical_analysis_template_v1`
- Include version numbers for iteration: `_v1`, `_v2`, etc.
- Use domain prefixes: `blog_post_`, `concept_`, `analysis_`

## Domain Organization
Choose appropriate domains:
- `technical_analysis` - Technical reports and analysis
- `concepts` - Concept documentation and explanations
- `blog_posts` - Blog content and articles
- `project_planning` - Project management documents
- `code_review` - Code review templates
- `research` - Research methodology and findings

**Action**: Create your template file and save it as a GIINT blueprint.""",
                    "piece_type": "instruction",
                    "dependencies": [2]
                },
                {
                    "sequence_number": 4,
                    "filename": "04_test_blueprint_usage.md",
                    "title": "Test Your Blueprint and Workflow",
                    "content": """# Test Your Blueprint

## Retrieve and Use Blueprint
Test the complete workflow:

### Step 1: List Available Blueprints
```python
# Check your blueprint was saved
giint.workshop__list_blueprints(domain="your_domain")
```

### Step 2: Get Blueprint for Use
```python
# Copy blueprint to working location
giint.workshop__get_blueprint(
    blueprint_name="my_domain_template_v1",
    target_path="/tmp/my_response_draft.md",
    domain="your_domain"
)
```

### Step 3: Fill Template Variables
Open `/tmp/my_response_draft.md` and replace variables:
- Replace `{{title}}` with actual title
- Replace `{{overview}}` with real overview
- Fill in all template variables with content

### Step 4: Use with GIINT Response System
```python
# Use filled template as GIINT response
giint.core__respond(
    qa_id="test_blueprint_session",
    user_prompt_description="Testing my new blueprint",
    one_liner="Blueprint workflow test",
    key_tags=["blueprint", "testing"],
    involved_files=["/tmp/my_response_draft.md"],
    project_id="blueprint_testing",
    feature="template_system",
    component="blueprint_workflow",
    deliverable="working_template",
    subtask="test_usage",
    task="validate_blueprint",
    workflow_id="blueprint_creation",
    response_file_path="/tmp/my_response_draft.md"
)
```

## Validation Checklist
- [ ] Blueprint saves successfully
- [ ] Blueprint appears in list_blueprints()
- [ ] get_blueprint() copies template correctly
- [ ] Template variables are clear and fillable
- [ ] Final response provides value
- [ ] Workflow feels efficient

**Action**: Test your complete blueprint workflow from creation to usage.""",
                    "piece_type": "instruction",
                    "dependencies": [3]
                },
                {
                    "sequence_number": 5,
                    "filename": "05_integrate_with_subagents.md",
                    "title": "Advanced: Subagent Integration and Automation",
                    "content": """# Advanced Blueprint Usage

## Subagent Auto-Fill (Future Enhancement)
While not yet implemented, the GIINT blueprint system is designed for subagent integration:

```python
# Future capability - subagent auto-fill
giint.subagent__autofill(
    subagent="code-security-reviewer",
    blueprint_id="technical_analysis_v1", 
    qa_id="current_session",
    context={"focus": "security_analysis", "codebase": "/path/to/code"}
)
```

## Current Manual Workflow Enhancement
For now, optimize manual usage:

### Context-Rich Instructions
Add guidance in your templates:
```markdown
# {{title}}

<!-- Instructions for filling this template:
- {{overview}}: Provide 2-3 sentence summary
- {{analysis}}: Include specific examples and evidence
- {{recommendations}}: Focus on actionable next steps
-->

## Overview
{{overview}}
```

### Checklist Integration
Add validation checklists to templates:
```markdown
## Quality Checklist
- [ ] All technical claims have supporting evidence
- [ ] Recommendations are specific and actionable
- [ ] Next steps include timeline and ownership
- [ ] Links to relevant documentation included
```

### GIINT Response Integration
Design templates to work well with GIINT's cognitive separation:
- Templates create structure for thinking
- Filled templates become response files
- Multiple iterations improve quality
- Final responses ready for publishing

## Blueprint Evolution
Plan improvements:
1. **Usage Analytics**: Track which sections work best
2. **Version Control**: Iterate templates based on feedback
3. **Domain Expansion**: Create specialized variants
4. **Community Sharing**: Share successful patterns

**Action**: Plan your blueprint integration strategy and future enhancements.""",
                    "piece_type": "instruction",
                    "dependencies": [4]
                }
            ],
            "entry_point": "01_analyze_response_pattern.md"
        }
    },
    "giint_project_planning_flight_config": {
        "category": "planning",
        "description": "Systematic workflow for GIINT project planning from concept to ready tasks",
        "payload_discovery": {
            "domain": "giint_planning",
            "version": "1.0.0",
            "description": "Systematic workflow for GIINT project planning from concept to ready tasks",
            "directories": {},
            "root_files": [
                {
                    "sequence_number": 1,
                    "filename": "01_understand_giint_hierarchy.md",
                    "title": "Understand GIINT Project Structure",
                    "content": """# GIINT Project Hierarchy

## The 5-Level Structure
GIINT organizes work in a strict hierarchy:
```
Project
├── Feature (major capability)
│   ├── Component (logical grouping)
│   │   ├── Deliverable (concrete output)
│   │   │   ├── Task (actionable work unit)
│   │   │   └── Task
│   │   └── Deliverable
│   └── Component
└── Feature
```

## Real Example
```
Compound Intelligence MVP (Project)
├── Flight Config System (Feature)
│   ├── Config Management (Component)
│   │   ├── Flight Config CRUD (Deliverable)
│   │   │   ├── create_flight_config_implementation (Task)
│   │   │   └── update_flight_config_validation (Task)
│   │   └── Config Discovery (Deliverable)
│   └── Waypoint Integration (Component)
└── GIINT Blueprint System (Feature)
```

## Key Concepts
- **Project**: Overall initiative or product
- **Feature**: Major user-facing capability or system component
- **Component**: Logical grouping of related deliverables
- **Deliverable**: Concrete, testable output (files, APIs, docs)
- **Task**: Single actionable work unit that can be assigned

## Task Readiness
Tasks become "ready" when:
1. All parent levels (project → feature → component → deliverable) have specs
2. Task itself has a rollup spec
3. Dependencies are clear
4. Work can begin immediately

**Action**: Review this hierarchy and think about how your current work maps to this structure.""",
                    "piece_type": "instruction",
                    "dependencies": []
                },
                {
                    "sequence_number": 2,
                    "filename": "02_create_project_foundation.md",
                    "title": "Create GIINT Project and Top-Level Structure",
                    "content": """# Create Your GIINT Project Foundation

## Step 1: Create the Project
```python
# Create the main project
giint.planning__create_project(
    project_id="your_project_name",  # Simple identifier
    project_dir="/path/to/your/project",  # Where files live
    starlog_path="/path/to/starlog",  # Optional STARLOG integration
    github_repo_url="https://github.com/user/repo"  # Optional GitHub integration
)
```

## Step 2: Add Major Features
Identify 2-4 major features (capabilities) your project needs:

```python
# Add each major feature
giint.planning__add_feature_to_project(
    project_id="your_project_name",
    feature_name="user_authentication"  # Major capability
)

giint.planning__add_feature_to_project(
    project_id="your_project_name",
    feature_name="data_processing"
)

giint.planning__add_feature_to_project(
    project_id="your_project_name",
    feature_name="api_endpoints"
)
```

## Design Questions
- **What are the 3-5 major things your system needs to do?**
- **What would a user interact with directly?**
- **What are the main technical capabilities required?**

## Naming Guidelines
- Use snake_case for all identifiers
- Be specific but concise
- Focus on capabilities, not implementation
- Think "what does this enable?" not "how will we build it?"

**Action**: Create your GIINT project and add 2-4 major features that represent the core capabilities needed.""",
                    "piece_type": "instruction",
                    "dependencies": [1]
                }
            ],
            "entry_point": "01_understand_giint_hierarchy.md"
        }
    }
}


def get_registry_path() -> Path:
    """Get the path to the STARLOG flight configs registry."""
    registry_path = Path("/tmp/heaven_data/registry/starlog_flight_configs_registry.json")
    return registry_path


def registry_exists() -> bool:
    """Check if the flight config registry exists."""
    return get_registry_path().exists()


def load_registry() -> Dict[str, Any]:
    """Load the existing flight configs registry if it exists."""
    registry_path = get_registry_path()
    
    if registry_path.exists():
        try:
            with open(registry_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load registry: {e}", exc_info=True)
            return {}
    
    return {}


def save_registry(registry: Dict[str, Any]) -> None:
    """Save the registry to disk."""
    registry_path = get_registry_path()
    
    try:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        logger.info(f"Registry saved to {registry_path}")
    except Exception as e:
        logger.exception(f"Failed to save registry: {e}")


def create_payload_discovery_file(name: str, config: Dict[str, Any]) -> str:
    """Create a PayloadDiscovery JSON file and return its path."""
    pd_dir = Path("/tmp/heaven_data/giint_default_configs")
    pd_dir.mkdir(parents=True, exist_ok=True)
    
    pd_file = pd_dir / f"{name}_pd.json"
    
    try:
        with open(pd_file, 'w') as f:
            json.dump(config["payload_discovery"], f, indent=2)
        logger.info(f"Created PayloadDiscovery file: {pd_file}")
        return str(pd_file)
    except Exception as e:
        logger.exception(f"Failed to create PayloadDiscovery file: {e}")
        return None


def register_flight_config(name: str, config: Dict[str, Any], pd_path: str) -> Dict[str, Any]:
    """Create a flight config registry entry."""
    config_id = str(uuid.uuid4())
    
    entry = {
        "id": config_id,
        "name": name,
        "original_project_path": "GIINT_DEFAULT",
        "category": config["category"],
        "description": config["description"],
        "work_loop_subchain": pd_path,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return entry


def auto_populate_giint_defaults() -> str:
    """
    Auto-populate default GIINT flight configs if registry exists.
    
    Returns:
        Status message indicating success or failure
    """
    try:
        # Check if registry exists
        if not registry_exists():
            msg = "Flight config registry not found. GIINT flight configs will not be auto-populated until STARLOG is initialized."
            logger.info(msg)
            return msg
        
        logger.info("Starting GIINT flight config auto-population...")
        
        # Load existing registry
        registry = load_registry()
        
        populated = []
        skipped = []
        
        for name, config in DEFAULT_GIINT_CONFIGS.items():
            # Check if already exists
            existing = any(entry.get("name") == name for entry in registry.values())
            if existing:
                skipped.append(name)
                logger.info(f"Flight config '{name}' already exists, skipping...")
                continue
            
            # Create PayloadDiscovery file
            pd_path = create_payload_discovery_file(name, config)
            if not pd_path:
                logger.error(f"Failed to create PayloadDiscovery file for {name}")
                continue
            
            # Register the flight config
            entry = register_flight_config(name, config, pd_path)
            registry[entry["id"]] = entry
            populated.append(name)
            logger.info(f"Registered flight config: {name}")
        
        # Save updated registry
        if populated:
            save_registry(registry)
        
        # Prepare status message
        status_parts = []
        if populated:
            status_parts.append(f"✅ Auto-populated {len(populated)} GIINT flight configs: {', '.join(populated)}")
        if skipped:
            status_parts.append(f"⏭️ Skipped {len(skipped)} existing configs: {', '.join(skipped)}")
        if not populated and not skipped:
            status_parts.append("ℹ️ All GIINT flight configs already present")
        
        status = "\n".join(status_parts)
        logger.info(f"GIINT auto-population complete: {status}")
        return status
        
    except Exception as e:
        error_msg = f"Failed to auto-populate GIINT flight configs: {e}"
        logger.exception(error_msg)
        return f"❌ {error_msg}"