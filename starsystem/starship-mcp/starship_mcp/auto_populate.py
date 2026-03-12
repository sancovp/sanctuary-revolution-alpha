#!/usr/bin/env python3
"""
Auto-population of default flight configs for STARSHIP.

This module provides default flight configurations that are essential for the compound
intelligence system. These configs are auto-populated when STARSHIP is first used.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Default flight configs embedded as Python dictionaries
DEFAULT_FLIGHT_CONFIGS = {
    "create_flight_config_flight_config": {
        "category": "meta",
        "description": "Meta-flight config that guides users through creating custom domain-specific flight configs",
        "payload_discovery": {
            "domain": "starlog_meta",
            "version": "1.0.0",
            "description": "Meta-flight config that guides users through creating custom flight configs",
            "directories": {},
            "root_files": [
                {
                    "sequence_number": 1,
                    "filename": "01_understand_domain.md",
                    "title": "Understand Your Domain and Workflow",
                    "content": """# Domain Analysis

## Your Domain
What specific area are you creating a flight config for?
- Research methodology?
- Debugging workflow?
- Documentation generation?
- Code review process?
- Testing strategy?

## Workflow Analysis
Describe your ideal workflow:
1. What are the key steps in your process?
2. Which steps are amplificatory (repeatable/improvable)?
3. What tools and files do you typically work with?
4. What outputs do you want to generate?

## Amplificatory vs One-Time
✅ Good for flight configs (amplificatory):
- "Review and improve code quality"
- "Research and synthesize findings"
- "Analyze and optimize performance"

❌ Not ideal (one-time tasks):
- "Write the user manual"
- "Fix this specific bug"
- "Create the database schema"

**Action**: Document your domain and workflow requirements above.""",
                    "piece_type": "instruction",
                    "dependencies": []
                },
                {
                    "sequence_number": 2,
                    "filename": "02_design_payloaddiscovery.md",
                    "title": "Design Your PayloadDiscovery Structure",
                    "content": """# PayloadDiscovery Design

## Template Structure
```json
{
  "domain": "your_domain",
  "version": "1.0.0",
  "description": "Brief description of what this workflow accomplishes",
  "directories": {},
  "root_files": [
    {
      "sequence_number": 1,
      "filename": "01_setup.md",
      "title": "Setup and Context",
      "content": "Instructions for initial setup...",
      "piece_type": "instruction",
      "dependencies": []
    },
    {
      "sequence_number": 2,
      "filename": "02_main_work.md",
      "title": "Core Workflow Step",
      "content": "Main amplificatory process...",
      "piece_type": "instruction",
      "dependencies": [1]
    },
    {
      "sequence_number": 3,
      "filename": "03_iterate.md",
      "title": "Review and Iterate",
      "content": "How to improve and continue...",
      "piece_type": "instruction",
      "dependencies": [2]
    }
  ],
  "entry_point": "01_setup.md"
}
```

## Design Principles
1. **Sequential**: Each step builds on previous steps
2. **Clear Instructions**: Each piece should be actionable
3. **Amplificatory**: Focus on processes that improve with repetition
4. **Dependencies**: Use sequence numbers to show step relationships

**Action**: Create your PayloadDiscovery JSON file based on your domain analysis.""",
                    "piece_type": "instruction",
                    "dependencies": [1]
                },
                {
                    "sequence_number": 3,
                    "filename": "03_create_pd_file.md",
                    "title": "Create and Validate PayloadDiscovery File",
                    "content": """# Create PayloadDiscovery File

## Steps
1. Create your PayloadDiscovery JSON file
2. Save it with a descriptive name: `/path/to/your_domain_pd.json`
3. Validate the structure

## Validation Checklist
- [ ] `domain` field describes your area
- [ ] `description` explains the workflow purpose
- [ ] `root_files` contains numbered sequence
- [ ] Each piece has `sequence_number`, `filename`, `title`, `content`
- [ ] Dependencies reference earlier sequence numbers
- [ ] Content provides actionable instructions
- [ ] Workflow is amplificatory (repeatable/improvable)

## Test Your PayloadDiscovery
You can test the structure using:
```bash
python -c 'import payload_discovery; pd = payload_discovery.PayloadDiscovery.from_json("your_file.json"); print(pd.validate_sequence())'
```

**Action**: Create and validate your PayloadDiscovery JSON file.""",
                    "piece_type": "instruction",
                    "dependencies": [2]
                },
                {
                    "sequence_number": 4,
                    "filename": "04_register_flight_config.md",
                    "title": "Register Your Flight Config",
                    "content": """# Register Flight Config

## Registration Command
Use the STARLOG MCP tool to register your flight config:

```python
starlog.add_flight_config(
    path="/your/project/path",
    name="your_domain_flight_config",  # Must end with _flight_config
    config_data={
        "description": "Your workflow description",
        "work_loop_subchain": "/path/to/your_domain_pd.json"
    },
    category="your_category"  # e.g., research, debugging, docs
)
```

## Naming Requirements
- Name MUST end with `_flight_config`
- Use descriptive prefixes: `research_methodology_flight_config`
- Categories help organize: research, debugging, docs, testing, etc.

## Test Your Flight Config
After registration:
1. `starlog.fly(path)` - Should show your new config
2. Test with a simple project to verify it works
3. Iterate and improve based on usage

**Action**: Register your flight config and test it.""",
                    "piece_type": "instruction",
                    "dependencies": [3]
                },
                {
                    "sequence_number": 5,
                    "filename": "05_iterate_and_improve.md",
                    "title": "Iterate and Improve Your Flight Config",
                    "content": """# Continuous Improvement

## Usage Feedback Loop
1. **Use** your flight config on real projects
2. **Observe** where the workflow breaks down or could be clearer
3. **Update** the PayloadDiscovery JSON with improvements
4. **Re-register** using `update_flight_config()`
5. **Share** successful patterns with the community

## Common Improvements
- **Clearer Instructions**: Add more detail to ambiguous steps
- **Better Dependencies**: Ensure steps build logically
- **Tool Integration**: Reference specific tools and commands
- **Output Templates**: Provide examples of expected outputs
- **Error Handling**: Include troubleshooting guidance

## Update Command
```python
starlog.update_flight_config(
    path="/your/project/path",
    name="your_domain_flight_config",
    config_data={
        "description": "Updated description",
        "work_loop_subchain": "/path/to/improved_pd.json"
    }
)
```

## Success Metrics
- Does the workflow feel natural to follow?
- Do you get better results each time you use it?
- Can others understand and use your flight config?
- Does it save time compared to ad-hoc approaches?

**Action**: Plan your improvement cycle and create a feedback loop.""",
                    "piece_type": "instruction",
                    "dependencies": [4]
                }
            ],
            "entry_point": "01_understand_domain.md"
        }
    },
    "create_skill_flight_config": {
        "category": "skill_creation",
        "description": "Guide for creating properly structured skills - walks through understanding skills, choosing type, and building the skill package",
        "payload_discovery": {
            "domain": "skill_creation",
            "version": "1.0.0",
            "description": "Guide for creating properly structured skills - walks through understanding skills, choosing type, and building the skill package",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_understand_skills.md", "title": "Understand What Skills Are", "content": "# Step 1: Understand Skills\n\nBefore creating a skill, you need to understand what skills are.\n\n**Action**: Read `understand-skills/resources/what_are_skills.md`\n\nThis explains:\n- Skills as packages/directories\n- The injection model (SKILL.md gets injected)\n- Relationship between skills, flights, and MCPs\n\nOnce you understand the fundamentals, proceed to the next step.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_understand_types.md", "title": "Learn the Three Skill Types", "content": "# Step 2: Learn the Three Types\n\n**Action**: Read `understand-skills/resources/the_three_types.md`\n\nThe three types are:\n- **understand** - For TALKING. Domain knowledge.\n- **preflight** - For WORKING. Entry point to flights.\n- **single_turn_process** - For WORKING. Immediate action.\n\nDecide which type your skill will be, then proceed.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_choose_type.md", "title": "Choose Your Skill Type", "content": "# Step 3: Choose Your Type\n\nBased on what you learned, choose:\n\n**If creating domain knowledge** (reference material, patterns, examples):\n\u2192 Type: `understand`\n\u2192 Read: `understand-skills/resources/understand_type_pattern.md`\n\n**If creating entry point to flights** (multi-step workflow):\n\u2192 Type: `preflight`\n\u2192 Read: `understand-skills/resources/preflight_type_pattern.md`\n\n**If creating immediate action** (do it now in one turn):\n\u2192 Type: `single_turn_process`\n\u2192 Read: `understand-skills/resources/single_turn_process_pattern.md`\n\n**Action**: Read the pattern doc for your chosen type, then proceed.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_understand_structure.md", "title": "Learn Skill Directory Structure", "content": "# Step 4: Learn the Structure\n\n**Action**: Read `understand-skills/resources/skill_structure.md`\n\nKey structure:\n```\nmy-skill/\n\u251c\u2500\u2500 SKILL.md           # Brief - what gets injected\n\u251c\u2500\u2500 reference.md       # TOC for everything in skill\n\u251c\u2500\u2500 resources/         # Actual content (can be massive)\n\u251c\u2500\u2500 scripts/           # Executables\n\u2514\u2500\u2500 templates/         # Starter files\n```\n\nRemember:\n- SKILL.md is BRIEF (points to reference.md)\n- reference.md is a TABLE OF CONTENTS\n- resources/ has the actual content\n\nProceed when ready to create.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_create_directory.md", "title": "Create Skill Directory", "content": "# Step 5: Create the Directory Structure\n\n**Action**: Create the skill directory with this structure:\n\n```bash\nmkdir -p my-skill/resources\nmkdir -p my-skill/scripts\nmkdir -p my-skill/templates\n```\n\nReplace `my-skill` with your skill name (lowercase, hyphens).\n\nProceed when directory is created.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_write_skill_md.md", "title": "Write SKILL.md", "content": "# Step 6: Write SKILL.md\n\n**Action**: Create SKILL.md with:\n\n```markdown\n---\nname: your-skill-name\ndescription: Brief description (max 1024 chars)\ncategory: understand|preflight|single_turn_process\n---\n\n# Your Skill Name\n\nBrief intro (1-2 paragraphs max).\n\n**Read `reference.md`** for full details on what's in this skill.\n```\n\nKeep it BRIEF. The real content goes in resources/.", "piece_type": "instruction", "dependencies": [5]},
                {"sequence_number": 7, "filename": "07_write_reference_md.md", "title": "Write reference.md", "content": "# Step 7: Write reference.md\n\n**Action**: Create reference.md as a TABLE OF CONTENTS:\n\n```markdown\n# skill-name Reference\n\nTable of contents for all resources in this skill.\n\n---\n\n## Section Name\n\n### `resources/filename.md`\n**When to use:** Describe when this resource is needed.\n- What it contains\n- Key topics covered\n\n### `resources/another_file.md`\n**When to use:** Another description.\n- Contents\n- Topics\n\n---\n\n## Scripts\n\n### `scripts/helper.py`\n**When to use:** What this script does.\n```\n\nEvery file in the skill should be listed with 'When to use' description.", "piece_type": "instruction", "dependencies": [6]},
                {"sequence_number": 8, "filename": "08_populate_resources.md", "title": "Populate Resources", "content": "# Step 8: Populate resources/\n\n**Action**: Create the actual content files in resources/.\n\nFor **understand** skills:\n- Can be MASSIVE - entire directories of knowledge\n- Documentation, patterns, examples, API references\n- Pure knowledge, no instructions\n\nFor **preflight** skills:\n- Usually minimal resources\n- Maybe decision criteria or flight descriptions\n\nFor **single_turn_process** skills:\n- Templates if needed\n- Supporting reference if complex\n\nCreate all the files listed in your reference.md.", "piece_type": "instruction", "dependencies": [7]},
                {"sequence_number": 9, "filename": "09_add_scripts_templates.md", "title": "Add Scripts and Templates", "content": "# Step 9: Add Scripts and Templates (Optional)\n\n**scripts/**: Executable utilities\n- Validators, scaffolders, helpers\n- Run without loading content to context\n\n**templates/**: Starter files\n- Boilerplate code\n- Config templates\n- Document templates\n\n**Action**: Add any scripts or templates your skill needs.\n\nIf none needed, proceed to final step.", "piece_type": "instruction", "dependencies": [8]},
                {"sequence_number": 10, "filename": "10_verify_complete.md", "title": "Verify and Complete", "content": "# Step 10: Verify Completion\n\n**Checklist**:\n- [ ] SKILL.md exists with proper frontmatter (name, description, category)\n- [ ] SKILL.md is BRIEF and points to reference.md\n- [ ] reference.md lists ALL resources with 'When to use'\n- [ ] resources/ contains actual content files\n- [ ] Every file in reference.md actually exists\n- [ ] _metadata.json created with domain/subdomain info\n\n**Create _metadata.json**:\n```json\n{\n  \"name\": \"your-skill-name\",\n  \"domain\": \"your-domain\",\n  \"subdomain\": \"optional-subdomain\",\n  \"description\": \"Same as SKILL.md description\",\n  \"category\": \"understand|preflight|single_turn_process\"\n}\n```\n\n**Done!** Your skill is properly structured.", "piece_type": "instruction", "dependencies": [9]}
            ],
            "entry_point": "01_understand_skills.md"
        }
    },
    "make_subagent_flight_config": {
        "category": "paiab",
        "description": "Guide for creating Claude Code subagents in PAIA - from setup through testing",
        "payload_discovery": {
            "domain": "agent_development",
            "version": "1.0.0",
            "description": "Guide for creating Claude Code subagents in PAIA - from setup through testing. Replayable for both new creation and editing existing agents.",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_setup.md", "title": "Setup Working Directory", "content": "# Step 1: Setup Working Directory\n\n**Action**: Create or verify your agent-making workspace.\n\n```bash\nmkdir -p /agent_making\n```\n\nIf this is a new workspace, initialize starlog:\n```\nstarlog.init_project(path='/agent_making', name='agent_making', description='Subagent development workspace')\n```\n\nIf already initialized, orient:\n```\nstarlog.orient(path='/agent_making')\n```\n\n**Why this matters**: Agents you create here are tracked. You can review what you built, iterate, and maintain history.\n\nProceed when workspace is ready.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_create_agent_folder.md", "title": "Create Agent Folder", "content": "# Step 2: Create Agent Folder\n\n**Action**: Create a folder for this specific agent.\n\n```bash\nmkdir -p /agent_making/my-agent-name\n```\n\nReplace `my-agent-name` with a descriptive name (lowercase, hyphens).\n\nExamples:\n- `research-agent`\n- `code-reviewer-agent`\n- `content-writer-agent`\n\nProceed when folder is created.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_read_resources.md", "title": "Read Subagent Resources", "content": "# Step 3: Read Subagent Resources\n\n**Action**: Read the subagent documentation before designing.\n\n**Claude Code subagent basics:**\n`understand-advanced-claude-code/resources/components/06_subagents/overview.md`\n\n**PAIA subagent patterns:**\n`understand-advanced-claude-code/resources/systems/07_subagents_advanced/`\n- `overview.md` - Composability philosophy\n- `gnosys-docs-agent.md` - Static specialist example\n- `gnosys-worker-agent.md` - Persona-aware worker example\n- `README.md` - The two base patterns + advanced options\n\n**Key decision**: Which pattern?\n1. **Static Specialist** - Fixed frame, does one thing\n2. **Persona-Aware Worker** - Morphs based on persona instruction\n\nProceed when you've read the resources and chosen a pattern.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_design_agent.md", "title": "Design the Agent", "content": "# Step 4: Design the Agent\n\n**Answer these questions:**\n\n1. **What is the agent's job?** Single responsibility, clearly defined\n2. **What resources does it need?** MCPs? Skills? Flight configs? Working directory? Starlog? CartON identity?\n3. **Static or persona-aware?**\n4. **What are its hard rules?** MUST do / MUST NOT do\n\n**Anti-pattern check**: If the agent's task is complex, does it have a flight config to follow? Agents without flight configs drift.\n\nProceed when design is clear.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_write_agent.md", "title": "Write agent.md", "content": "# Step 5: Write agent.md\n\n**Action**: Create the agent definition file using GNOSYS_PERSONA_FRAME_TEMPLATE_V1.\n\n**Location**: Your plugin's `agents/` directory or project `.claude/agents/`\n\n**Template structure:**\n```xml\n<GNOSYS_PERSONA_FRAME_TEMPLATE_V1>\n<COMPOUND_INTELLIGENCE_SYSTEM_PROMPT>\n<BACKGROUND>\n## Agent Preface\nYou are **AgentName** - [one line description].\n</BACKGROUND>\n<PAIA>\n<meta_persona>\n[Name, Description, TalksLike, Mission]\n</meta_persona>\n<definitions>\nKey terms, workflows, resources\n</definitions>\n<rules>\nHard constraints\n</rules>\n</PAIA>\n</COMPOUND_INTELLIGENCE_SYSTEM_PROMPT>\n</GNOSYS_PERSONA_FRAME_TEMPLATE_V1>\n```\n\nProceed when agent.md is written.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_review_design.md", "title": "Review Against Patterns", "content": "# Step 6: Review Against PAIA Patterns\n\n**Checklist:**\n- [ ] Single responsibility?\n- [ ] Clear rules?\n- [ ] Flight config for complex workflows?\n- [ ] Resources defined?\n- [ ] Frame is additive (no main prompt duplication)?\n\n**If giving it PAIA infrastructure:**\n- [ ] Own working directory?\n- [ ] Starlog initialized?\n- [ ] CartON identity?\n- [ ] Flight configs to run?\n\nFix any issues, then proceed.", "piece_type": "instruction", "dependencies": [5]},
                {"sequence_number": 7, "filename": "07_install.md", "title": "Install the Agent", "content": "# Step 7: Install the Agent\n\n**Option 1: Plugin agents/ directory**\n```bash\ncp /agent_making/my-agent-name/my-agent-name.md ~/.claude/plugins/gnosys/agents/\n```\n\n**Option 2: Project-local agents/**\n```bash\nmkdir -p .claude/agents\ncp /agent_making/my-agent-name/my-agent-name.md .claude/agents/\n```\n\nProceed when agent file is in place.", "piece_type": "instruction", "dependencies": [6]},
                {"sequence_number": 8, "filename": "08_restart.md", "title": "Restart Claude Code", "content": "# Step 8: Restart Claude Code\n\nClaude Code reads agent definitions at startup. After adding a new agent:\n1. Save all work\n2. Restart Claude Code\n3. Verify agent appears in Task tool options\n\nProceed when Claude Code shows the new agent.", "piece_type": "instruction", "dependencies": [7]},
                {"sequence_number": 9, "filename": "09_test.md", "title": "Test the Agent", "content": "# Step 9: Test the Agent\n\n**Test basic functionality:**\n```\nTask tool with subagent_type='my-agent-name'\nPrompt: [something the agent should handle]\n```\n\n**Test checklist:**\n- [ ] Agent spawns without errors\n- [ ] Agent follows its defined rules\n- [ ] Agent uses resources correctly\n- [ ] Agent stays in its lane\n- [ ] Agent output is useful\n\n**Iterate**: If something's wrong, go back to Step 5-6, fix, reinstall, restart, retest.\n\n**Done!** Your subagent is ready for use.", "piece_type": "instruction", "dependencies": [8]}
            ],
            "entry_point": "01_setup.md"
        }
    },
    "make_hook_flight_config": {
        "category": "paiab",
        "description": "Guide for creating Claude Code hooks - from docs through testing to hot-editing",
        "payload_discovery": {
            "domain": "hook_development",
            "version": "1.0.0",
            "description": "Guide for creating Claude Code hooks - from docs through testing to hot-editing. Debug diary captures learnings about hook patterns.",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_setup.md", "title": "Setup Working Directory", "content": "# Step 1: Setup Working Directory\n\n**Action**: Create or verify your hook development workspace.\n\n```bash\nmkdir -p /hook_making\n```\n\nInitialize or orient starlog for the workspace.\n\nProceed when workspace is ready.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_read_docs.md", "title": "Read Hook Documentation", "content": "# Step 2: Read Hook Documentation\n\n**Official docs**: https://docs.anthropic.com/en/docs/claude-code/hooks\n\n**PAIA hook patterns**: `understand-advanced-claude-code/resources/components/03_hooks/overview.md`\n\n**Key things to understand:**\n1. Hook types: PreToolUse, PostToolUse, UserPromptSubmit, Notification, Stop, etc.\n2. Hook configuration in settings.json\n3. Input format: JSON payload each hook type receives\n4. Output format: blocking, context injection, etc.\n\nProceed when you understand which hook type you need.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_identify_hook_type.md", "title": "Identify Hook Type", "content": "# Step 3: Identify Hook Type\n\n**PreToolUse** - Before tool executes (block, inject context, validate)\n**PostToolUse** - After tool executes (log, trigger, capture)\n**UserPromptSubmit** - On user message (add context, inject reminders)\n**Notification** - System notifications\n**Stop / SubagentStop** - Session ending (cleanup, save state)\n**PreCompact** - Before compaction (persist context)\n\nDocument your choice and why.\n\nProceed when hook type is chosen.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_write_script.md", "title": "Write Hook Script", "content": "# Step 4: Write Hook Script\n\n**Location**: `/hook_making/my_hook.py`\n\n**Basic structure:**\n```python\n#!/usr/bin/env python3\nimport json, sys\n\ndef main():\n    input_data = json.loads(sys.stdin.read())\n    # Your hook logic here\n    result = {}  # blocked, context, or pass-through\n    print(json.dumps(result))\n\nif __name__ == \"__main__\":\n    main()\n```\n\n**Key patterns:** Read JSON from stdin, write JSON to stdout, exit 0 for success.\n\nProceed when script is written.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_test_locally.md", "title": "Test Locally", "content": "# Step 5: Test Locally with Mock Input\n\nCreate test_input.json with mock payload, then:\n```bash\ncat /hook_making/test_input.json | python3 /hook_making/my_hook.py\n```\n\nCheck: parses input? returns valid JSON? logic works?\n\nIterate until local tests pass.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_install_hook.md", "title": "Install Hook", "content": "# Step 6: Install Hook\n\n```bash\ncp /hook_making/my_hook.py ~/.claude/hooks/\nchmod +x ~/.claude/hooks/my_hook.py\n```\n\nAdd to settings.json hooks section with appropriate type and optional matcher.\n\nProceed when hook is registered.", "piece_type": "instruction", "dependencies": [5]},
                {"sequence_number": 7, "filename": "07_restart_test.md", "title": "Restart and Test", "content": "# Step 7: Restart Claude Code and Test\n\nRestart required first time. Trigger the hook event and verify behavior.\n\nDebugging: check settings.json syntax, file permissions, logs.\n\nProceed when hook works in Claude Code.", "piece_type": "instruction", "dependencies": [6]},
                {"sequence_number": 8, "filename": "08_iterate.md", "title": "Iterate Hot", "content": "# Step 8: Iterate (Hot Editing)\n\nOnce loaded, edits take effect immediately - no restart needed.\n\nWorkflow: Edit hook file -> trigger event -> see new behavior -> repeat.\n\nProceed when hook behavior is satisfactory.", "piece_type": "instruction", "dependencies": [7]},
                {"sequence_number": 9, "filename": "09_document.md", "title": "Document the Hook", "content": "# Step 9: Document the Hook\n\nAdd top comment with: hook type, triggers, behavior, configuration.\n\nIf part of a plugin, ensure hooks/ directory includes it.\n\n**Done!** Hook is created, tested, and documented.", "piece_type": "instruction", "dependencies": [8]}
            ],
            "entry_point": "01_setup.md"
        }
    },
    "make_mcp_flight_config": {
        "category": "paiab",
        "description": "Guide for creating MCPs - FastMCP and raw SDK approaches, design through publish",
        "payload_discovery": {
            "domain": "mcp_development",
            "version": "1.0.0",
            "description": "Guide for creating MCPs - covers FastMCP and raw MCP SDK approaches, from design through publish.",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_setup.md", "title": "Setup and Resources", "content": "# Step 1: Setup and Resources\n\nRead MCP resources in `understand-advanced-claude-code/resources/components/04_mcps/`:\n- overview.md, checklist.md, common_mistakes.md, architecture_patterns.md, testing_guide.md, nesting_guide.md\n\n**Two approaches:** FastMCP (simple, decorator-based) or Raw MCP SDK (full control).\n\nProceed when you understand the options.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_decide.md", "title": "Decide Architecture", "content": "# Step 2: Decide Architecture\n\n1. FastMCP or Raw SDK?\n2. Tools, Resources, or both?\n3. Single file or package?\n\nReference: architecture_patterns.md for 8 common patterns.\n\nDocument decisions, then proceed.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_create.md", "title": "Create the MCP", "content": "# Step 3: Create the MCP Code\n\nWrite the MCP using your chosen approach (FastMCP or Raw SDK).\n\nChecklist: clear tool naming, comprehensive docstrings, input validation, proper error handling, logging.\n\nProceed when code is written.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_test_locally.md", "title": "Test Locally", "content": "# Step 4: Test Locally\n\nTest with MCP Inspector:\n```bash\nnpx @modelcontextprotocol/inspector@latest python my_mcp.py\n```\n\nTest checklist: starts without errors, all tools listed, each tool responds correctly, errors handled.\n\nProceed when local tests pass.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_install.md", "title": "Install Package", "content": "# Step 5: Install the Package\n\nCreate pyproject.toml with entry point. Install with `pip install -q .`\n\nVerify entry point exists: `which my-mcp`\n\nProceed when installed.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_test_installed.md", "title": "Test from Install", "content": "# Step 6: Test from Installed Package\n\nTest via entry point and Inspector using installed version (not source).\n\nCommon issues: entry point not found, import errors, different behavior from source.\n\nProceed when installed version works.", "piece_type": "instruction", "dependencies": [5]},
                {"sequence_number": 7, "filename": "07_connect.md", "title": "Connect to Claude Code", "content": "# Step 7: Connect to Claude Code\n\nAdd to ~/.claude/ claude.json mcpServers config.\n\nRestart Claude Code or use /mcp to reconnect.\n\nVerify Claude Code can access the MCP and its tools.\n\nProceed when connected.", "piece_type": "instruction", "dependencies": [6]},
                {"sequence_number": 8, "filename": "08_publish.md", "title": "Publish", "content": "# Step 8: Publish\n\nGit commit/push. Optional: PyPI upload, Docker image.\n\nProceed when published.", "piece_type": "instruction", "dependencies": [7]},
                {"sequence_number": 9, "filename": "09_verify.md", "title": "Verify Published Install", "content": "# Step 9: Verify Published Install\n\nConfirm MCP installs correctly from published source.\n\nFinal checklist: installs without errors, entry point works, all tools function, connects to Claude Code.\n\n**Done!** MCP is published and verified.", "piece_type": "instruction", "dependencies": [8]}
            ],
            "entry_point": "01_setup.md"
        }
    },
    "make_rules_flight_config": {
        "category": "paiab",
        "description": "Guide for creating Claude Code rules (.claude/rules/*.md) - project-specific auto-injected context",
        "payload_discovery": {
            "domain": "rules_creation",
            "version": "1.0.0",
            "description": "Guide for creating Claude Code rules - auto-injected markdown files that shape agent behavior per project. Rules fire every conversation without explicit loading.",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_understand_rules.md", "title": "Understand What Rules Are", "content": "# Step 1: Understand Rules\n\nRules are `.md` files in `.claude/rules/` (project-local) or `~/.claude/rules/` (global).\n\n**Key properties:**\n- Auto-injected EVERY conversation (zero retrieval cost)\n- Shape agent behavior without skills or MCPs\n- Override defaults — agent MUST follow them\n- Keep concise — every rule burns context window\n\n**Use rules for:**\n- Hard constraints (\"NEVER do X\", \"ALWAYS do Y\")\n- Project-specific patterns (\"use this testing framework\")\n- Architecture reminders (\"this package does X, not Y\")\n- Tool usage instructions (\"use MCP X for Y\")\n\n**Do NOT use rules for:**\n- Large knowledge bases (use understand skills instead)\n- Workflows (use flights instead)\n- Temporary notes (use CartON instead)\n\nProceed when you understand the distinction.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_analyze_domain.md", "title": "Analyze Domain for Rules", "content": "# Step 2: Analyze the Domain\n\n**Action**: Read the project/repo thoroughly. Identify:\n\n1. **Hard constraints** — What must NEVER happen? What must ALWAYS happen?\n2. **Architecture patterns** — What patterns does this codebase follow that the agent must respect?\n3. **Tool/dependency rules** — Which tools, frameworks, testing approaches are mandated?\n4. **Common mistakes** — What errors have been made before that rules can prevent?\n5. **Package boundaries** — What goes where? What should NOT be edited?\n\n**Output**: A list of rule candidates, each with:\n- Rule name (kebab-case, e.g., `testing-patterns.md`)\n- One-line summary\n- Category: constraint | pattern | tool-usage | boundary | reminder\n\nProceed when rule candidates are listed.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_prioritize.md", "title": "Prioritize Rules", "content": "# Step 3: Prioritize Rules\n\nRules consume context window. Fewer, sharper rules > many vague ones.\n\n**Tier 1 (MUST HAVE):** Rules that prevent data loss, security issues, or architectural violations.\n**Tier 2 (SHOULD HAVE):** Rules that enforce patterns and prevent common mistakes.\n**Tier 3 (NICE TO HAVE):** Convenience reminders. Consider if a skill would be better.\n\n**Rule of thumb:** If the rule is longer than 20 lines, it should probably be an understand skill instead.\n\nSelect your final rule set. Aim for 3-8 rules per project.\n\nProceed when prioritized.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_write_rules.md", "title": "Write Rule Files", "content": "# Step 4: Write Rule Files\n\n**Action**: Create each rule as a `.md` file.\n\n**Format:**\n```markdown\n# Rule Name - NON-NEGOTIABLE (if Tier 1)\n\n**THE RULE:**\nClear, imperative statement of what to do/not do.\n\n**WHY:**\nOne line explaining the consequence of violation.\n\n**PATTERN:**\n```\nDO: example of correct behavior\nDON'T: example of violation\n```\n```\n\n**Naming:** `kebab-case.md` (e.g., `read-before-write.md`, `testing-patterns.md`)\n\n**Key principles:**\n- Be SPECIFIC, not vague\n- Include examples of right AND wrong\n- Start with the most important constraint\n- Use `NON-NEGOTIABLE` for Tier 1 rules\n\nProceed when all rule files are written.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_install_rules.md", "title": "Install Rules", "content": "# Step 5: Install Rules\n\n**Project-local (recommended):**\n```bash\nmkdir -p .claude/rules\ncp *.md .claude/rules/\n```\n\n**Global (affects ALL projects):**\n```bash\ncp *.md ~/.claude/rules/\n```\n\n**Decision criteria:**\n- Project-specific patterns → project-local\n- Universal constraints (e.g., \"always use starlog\") → global\n- When in doubt → project-local\n\nProceed when rules are installed.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_verify.md", "title": "Verify Rules Load", "content": "# Step 6: Verify Rules Load\n\n**Test**: Start a new conversation or restart Claude Code.\n\nRules should appear in the system context. Verify by:\n1. Asking the agent \"What rules are you following?\"\n2. Intentionally testing a constraint — does the agent comply?\n3. Check that no rule is too long (eating context)\n\n**Iterate**: If a rule is ignored, make it more prominent (add NON-NEGOTIABLE, move to top of file, make imperative).\n\n**Done!** Rules are installed and verified.", "piece_type": "instruction", "dependencies": [5]}
            ],
            "entry_point": "01_understand_rules.md"
        }
    },
    "make_skillset_flight_config": {
        "category": "paiab",
        "description": "Guide for creating skillsets - curated groupings of skills for specific domains or workflows",
        "payload_discovery": {
            "domain": "skillset_creation",
            "version": "1.0.0",
            "description": "Guide for creating skillsets via skillmanager - curated groupings of skills that load together for a domain or workflow context.",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_understand_skillsets.md", "title": "Understand Skillsets", "content": "# Step 1: Understand Skillsets\n\nA skillset is a named group of skills that equip together. When you equip a skillset, all its member skills load into context.\n\n**Use skillsets for:**\n- Domain bundles (\"everything I need for repo X\")\n- Workflow bundles (\"skills for content creation\")\n- Role bundles (\"skills for code review persona\")\n\n**Skillsets are managed via skillmanager-treeshell:**\n- `list_skillsets` — see existing skillsets\n- `create_skillset(name, domain, description, skills)` — create new\n- `add_to_skillset` — add skills to existing\n\n**Key:** Skillsets reference skill NAMES, not files. Skills must exist first.\n\nProceed when you understand the concept.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_inventory_skills.md", "title": "Inventory Available Skills", "content": "# Step 2: Inventory Available Skills\n\n**Action**: List all skills relevant to your domain.\n\n```\nsancrev.skillmanager: list_skills\nsancrev.skillmanager: list_by_domain(domain)\nsancrev.skillmanager: search_skills(query)\n```\n\nFor each skill, note:\n- Name\n- Type (understand / preflight / single_turn_process)\n- Domain\n- Whether it's needed for this skillset\n\n**Also check:** Are there skills that SHOULD exist but don't? Note those for creation.\n\nProceed when inventory is complete.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_design_skillset.md", "title": "Design the Skillset", "content": "# Step 3: Design the Skillset\n\n**Define:**\n1. **Name** — descriptive, kebab-case (e.g., `starship-pilot-reponame`)\n2. **Domain** — what domain does this serve?\n3. **Description** — one line explaining purpose\n4. **Member skills** — list of skill names to include\n\n**Design principles:**\n- Include ALL understand skills needed for the domain\n- Include relevant preflight skills for workflows\n- Include single_turn_processes that are commonly needed\n- Don't over-include — only skills that are ALWAYS needed together\n- Consider context window cost — each skill adds to injection\n\n**Anti-pattern:** Don't put every skill you have into one skillset. That defeats the purpose.\n\nProceed when design is ready.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_create_missing_skills.md", "title": "Create Missing Skills", "content": "# Step 4: Create Missing Skills (if any)\n\nIf Step 2 identified skills that should exist but don't:\n\n**Action**: For each missing skill, run the create_skill flight:\n```\nwaypoint: start_waypoint_journey(config_path='create_skill_flight_config', starlog_path='.')\n```\n\nCreate all missing skills before proceeding.\n\nIf no missing skills, skip to next step.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_create_skillset.md", "title": "Create the Skillset", "content": "# Step 5: Create the Skillset\n\n**Action**: Use skillmanager to create:\n\n```\nsancrev.skillmanager: create_skillset(\n    name='my-skillset-name',\n    domain='my-domain',\n    description='Purpose of this skillset',\n    skills=['skill-name-1', 'skill-name-2', ...]\n)\n```\n\nVerify creation:\n```\nsancrev.skillmanager: list_skillsets\n```\n\nProceed when skillset is created.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_test_skillset.md", "title": "Test the Skillset", "content": "# Step 6: Test the Skillset\n\n**Action**: Equip the skillset and verify all skills load.\n\n```\nsancrev.skillmanager: equip_skillset(name='my-skillset-name')\nsancrev.skillmanager: list_equipped\n```\n\n**Check:**\n- All expected skills are equipped\n- No errors during equip\n- Context isn't overloaded (too many skills = slow)\n\n**Done!** Skillset is created and tested.", "piece_type": "instruction", "dependencies": [5]}
            ],
            "entry_point": "01_understand_skillsets.md"
        }
    },
    "make_persona_flight_config": {
        "category": "paiab",
        "description": "Guide for creating personas - identity frames with skillsets and MCPs for domain-specific agent behavior",
        "payload_discovery": {
            "domain": "persona_creation",
            "version": "1.0.0",
            "description": "Guide for creating personas via skillmanager - identity frames bundled with skillsets and MCP sets that transform the agent into a domain specialist.",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_understand_personas.md", "title": "Understand Personas", "content": "# Step 1: Understand Personas\n\nA persona is an identity frame + skillset + MCP set that transforms the agent into a domain specialist.\n\n**Components:**\n- **Identity frame** — Name, domain, description, behavioral instructions\n- **Skillset** — Which skills load when persona is active\n- **MCP set** — Which MCPs are available (via GNOSYS strata)\n\n**Managed via skillmanager-treeshell:**\n- `list_personas` — see existing\n- `create_persona(name, domain, description, frame)` — create new\n- `equip_persona(name)` — activate persona\n- `get_active_persona` — check current\n- `deactivate_persona` — return to default\n\n**Key insight:** A persona is a PROJECT CACHE. When you equip a persona for repo X, you get all the skills, tools, and behavioral patterns for that repo. Persona = context engineering.\n\nProceed when you understand the concept.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_prerequisites.md", "title": "Check Prerequisites", "content": "# Step 2: Check Prerequisites\n\nBefore creating a persona, you need:\n\n1. **Skillset** — A skillset grouping the skills for this domain. If not created yet:\n   ```\n   waypoint: start_waypoint_journey(config_path='make_skillset_flight_config', ...)\n   ```\n\n2. **Understand skills** — Domain knowledge skills that the skillset references. If missing:\n   ```\n   waypoint: start_waypoint_journey(config_path='create_skill_flight_config', ...)\n   ```\n\n3. **Rules** (optional but recommended) — Project rules that apply when this persona is active.\n\n**Check what exists:**\n```\nsancrev.skillmanager: list_skillsets\nsancrev.skillmanager: list_skills\n```\n\nProceed when prerequisites are met.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_design_identity.md", "title": "Design Identity Frame", "content": "# Step 3: Design the Identity Frame\n\n**Define:**\n1. **Name** — The persona's name (e.g., `starship-pilot-myrepo`, `code-reviewer`)\n2. **Domain** — What domain does this persona serve?\n3. **Description** — One line purpose statement\n4. **Frame** — The behavioral instructions (the actual prompt injection)\n\n**Frame design principles:**\n- State WHO the persona is (role, expertise)\n- State WHAT it does (primary responsibilities)\n- State HOW it works (tools, workflows, patterns to follow)\n- State WHAT IT DOESN'T DO (boundaries)\n- Reference the skillset and key skills by name\n- Reference flight configs it should know about\n- Keep it focused — the frame is additive to the main system prompt\n\n**Frame template:**\n```\nYou are {name}, a {domain} specialist.\n\nPrimary responsibilities:\n- {responsibility 1}\n- {responsibility 2}\n\nWorkflow: {how you work, which flights to use}\n\nSkillset: {skillset-name} (auto-equipped)\nKey skills: {list important ones}\nKey flights: {list relevant flight configs}\n\nBoundaries:\n- {what you don't do}\n```\n\nProceed when identity is designed.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_create_persona.md", "title": "Create the Persona", "content": "# Step 4: Create the Persona\n\n**Action**: Use skillmanager to create:\n\n```\nsancrev.skillmanager: create_persona(\n    name='my-persona-name',\n    domain='my-domain',\n    description='Purpose of this persona',\n    frame='The full identity frame text from Step 3'\n)\n```\n\nVerify creation:\n```\nsancrev.skillmanager: list_personas\n```\n\nProceed when persona is created.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_test_persona.md", "title": "Test the Persona", "content": "# Step 5: Test the Persona\n\n**Action**: Equip the persona and verify everything loads.\n\n```\nsancrev.skillmanager: equip_persona(name='my-persona-name')\nsancrev.skillmanager: get_active_persona\nsancrev.skillmanager: list_equipped\n```\n\n**Check:**\n- Persona shows as active\n- Skillset is equipped (all member skills loaded)\n- Identity frame is injected\n- Agent behaves according to the frame\n\n**Test with a real task** — give the agent something in this persona's domain and see if it uses the right skills, follows the right patterns.\n\nProceed when persona behavior is verified.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_iterate.md", "title": "Iterate and Refine", "content": "# Step 6: Iterate and Refine\n\nPersonas improve through use. After testing:\n\n1. **Missing knowledge?** → Create more understand skills, add to skillset\n2. **Wrong behavior?** → Refine the identity frame\n3. **Missing tools?** → Connect MCPs via GNOSYS strata\n4. **Missing workflows?** → Create flight configs, add preflight skills\n\n**The persona is a living cache** — it evolves as you work in the domain.\n\n**Done!** Persona is created, tested, and ready for use.", "piece_type": "instruction", "dependencies": [5]}
            ],
            "entry_point": "01_understand_personas.md"
        }
    },
    "setup_plugin_project_flight_config": {
        "category": "paiab",
        "description": "Scaffolding flight for Claude Code plugins - sets up directory structure and plans components",
        "payload_discovery": {
            "domain": "plugin_development",
            "version": "1.0.0",
            "description": "Scaffolding flight for Claude Code plugins - sets up directory structure and plans components. Does NOT build components (use individual flights for that).",
            "directories": {},
            "root_files": [
                {"sequence_number": 1, "filename": "01_define_purpose.md", "title": "Define Plugin Purpose", "content": "# Step 1: Define Plugin Purpose\n\nAnswer: What is the plugin's core purpose? Who is the target user? What problem does it solve? What's the scope boundary?\n\nThis becomes the README and plugin.json description.\n\nProceed when purpose is clear.", "piece_type": "instruction", "dependencies": []},
                {"sequence_number": 2, "filename": "02_plan_components.md", "title": "Plan Components", "content": "# Step 2: Plan Components\n\nEnumerate what components this plugin needs:\n- Slash Commands (user entry points)\n- Subagents (delegated workers)\n- Hooks (event handlers)\n- Skills (knowledge packages)\n- MCPs (tools)\n- Config Examples (setup templates)\n\nDon't build yet - just enumerate. Building is separate flights.\n\nProceed when component list is complete.", "piece_type": "instruction", "dependencies": [1]},
                {"sequence_number": 3, "filename": "03_create_structure.md", "title": "Create Directory Structure", "content": "# Step 3: Create Directory Structure\n\n```bash\nmkdir -p /path/to/my-plugin/.claude-plugin\nmkdir -p /path/to/my-plugin/{commands,agents,hooks,skills,config_examples}\n```\n\nProceed when directories exist.", "piece_type": "instruction", "dependencies": [2]},
                {"sequence_number": 4, "filename": "04_create_manifest.md", "title": "Create Plugin Manifest", "content": "# Step 4: Create Plugin Manifest\n\nCreate `.claude-plugin/plugin.json` with name, version, description, author, repository.\n\nProceed when plugin.json is created.", "piece_type": "instruction", "dependencies": [3]},
                {"sequence_number": 5, "filename": "05_init_starlog.md", "title": "Initialize Starlog Project", "content": "# Step 5: Initialize Starlog Project\n\n```\nstarlog.init_project(path='/path/to/my-plugin', name='my-plugin', description='Plugin development: [purpose]')\n```\n\nProceed when starlog is initialized.", "piece_type": "instruction", "dependencies": [4]},
                {"sequence_number": 6, "filename": "06_create_readme.md", "title": "Create README", "content": "# Step 6: Create README\n\nCreate README.md with: installation, components list, setup, usage examples.\n\nFill in based on your component plan from Step 2.\n\nProceed when README exists.", "piece_type": "instruction", "dependencies": [5]},
                {"sequence_number": 7, "filename": "07_next_steps.md", "title": "Next Steps", "content": "# Step 7: Next Steps\n\nScaffolding complete. Now build components using individual flights:\n\n- For each skill: `start_waypoint_journey(config_path='create_skill_flight_config', ...)`\n- For each MCP: `start_waypoint_journey(config_path='make_mcp_flight_config', ...)`\n- For each subagent: `start_waypoint_journey(config_path='make_subagent_flight_config', ...)`\n\n**Done!** Plugin project is set up. Start building components.", "piece_type": "instruction", "dependencies": [6]}
            ],
            "entry_point": "01_define_purpose.md"
        }
    }
}


def get_registry_path() -> Path:
    """Get the path to the STARLOG flight configs registry."""
    heaven_data_dir = os.getenv("HEAVEN_DATA_DIR")
    if not heaven_data_dir:
        raise ValueError("HEAVEN_DATA_DIR environment variable must be set")
    registry_path = Path(os.path.join(heaven_data_dir, "registry/starlog_flight_configs_registry.json"))
    return registry_path


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
    
    # Create registry directory if it doesn't exist
    registry_path.parent.mkdir(parents=True, exist_ok=True)
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
    heaven_data_dir = os.getenv("HEAVEN_DATA_DIR")
    if not heaven_data_dir:
        raise ValueError("HEAVEN_DATA_DIR environment variable must be set")
    pd_dir = Path(os.path.join(heaven_data_dir, "default_flight_configs"))
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
        "original_project_path": "SYSTEM_DEFAULT",
        "category": config["category"],
        "description": config["description"],
        "work_loop_subchain": pd_path,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return entry


def auto_populate_defaults() -> str:
    """
    Auto-populate default flight configs for STARSHIP.
    
    Returns:
        Status message indicating success or failure
    """
    try:
        logger.info("Starting STARSHIP flight config auto-population...")
        
        # Load existing registry
        registry = load_registry()
        
        populated = []
        skipped = []
        
        for name, config in DEFAULT_FLIGHT_CONFIGS.items():
            # Check if already exists
            existing = any(entry.get("name") == name for entry in registry.values())
            if existing:
                skipped.append(name)
                logger.info(f"Flight config '{name}' already exists, skipping...")
                continue

            # Composite flight (work_loop_subchain is a list) — no PD file needed
            if "work_loop_subchain" in config:
                entry = register_flight_config(name, config, config["work_loop_subchain"])
                registry[entry["id"]] = entry
                populated.append(name)
                logger.info(f"Registered composite flight config: {name}")
                continue

            # Standard flight — create PayloadDiscovery file
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
            status_parts.append(f"✅ Auto-populated {len(populated)} flight configs: {', '.join(populated)}")
        if skipped:
            status_parts.append(f"⏭️ Skipped {len(skipped)} existing configs: {', '.join(skipped)}")
        if not populated and not skipped:
            status_parts.append("❌ No flight configs to populate")
        
        status = "\n".join(status_parts)
        logger.info(f"Auto-population complete: {status}")
        return status
        
    except Exception as e:
        error_msg = f"Failed to auto-populate flight configs: {e}"
        logger.error(error_msg)
        return f"❌ {error_msg}"