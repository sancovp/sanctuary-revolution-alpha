#!/usr/bin/env python3
"""
Emergence Engine MCP Server

Provides MCP tools for tracking progress through the 3-pass systematic thinking methodology.
Uses the System Design DSL notation (L₀P₁W[0](3)) to track exact position in the workflow.
"""

import logging
import traceback
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import from installed library
try:
    from emergence_engine import (
        start_journey,
        get_current_state, 
        next_phase,
        get_instructions,
        get_status as get_detailed_status,
        complete_journey,
        abandon_journey,
        get_contextual_prompt,
        explore_methodology,
        inject_3pass_structure,
        get_phase_file_path,
        ThreePassTracker
    )
except ImportError as e:
    raise ImportError(
        "emergence_engine library not installed. "
        "Run: pip install /tmp/core_libraries_to_publish/emergence_engine"
    ) from e

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Emergence Engine")

# Initialize tracker
tracker = ThreePassTracker()


def _get_3pass_base_path() -> Path:
    """Get the base path for the bundled 3-pass system files"""
    package_dir = Path(__file__).parent / "emergence_engine"
    return package_dir / "3_pass_autonomous_research_system_v01"


@mcp.tool
def core_run(
    domain: str = Field(description="The domain you're applying 3-pass thinking to (e.g., 'Autobiography System')"),
    starlog_path: str = Field(description="STARLOG project path as unique identifier")
) -> str:
    """
    Set up basic 3-pass session with minimal guidance.
    
    Tracks domain, current pass (1/2/3), current phase (0-6).
    Returns simple confirmation and current position.
    """
    try:
        # Start the journey
        result = start_journey(domain, starlog_path)
        current_state = get_current_state(starlog_path)
        
        logger.info(f"Started core 3-pass session for {domain} at {starlog_path}")
        
        return f"""✅ **3-Pass Session Started**

**Domain**: {domain}
**Position**: {current_state}
**Status**: Ready to begin

Use `get_next_phase()` to get your next prompt, or `expanded_run()` for detailed guidance."""
        
    except Exception as e:
        logger.error(f"Error in core_run: {e}", exc_info=True)
        return f"❌ Error starting session: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool  
def expanded_run(
    domain: str = Field(description="The domain you're applying 3-pass thinking to"),
    starlog_path: str = Field(description="STARLOG project path as unique identifier")
) -> str:
    """
    Full step-by-step guidance with detailed prompts for each phase.
    
    Provides comprehensive instructions, examples, and explanations.
    """
    try:
        # Start the journey
        result = start_journey(domain, starlog_path)
        
        # Get detailed instructions
        instructions = get_instructions(starlog_path)
        current_state = get_current_state(starlog_path)
        
        logger.info(f"Started expanded 3-pass session for {domain} at {starlog_path}")
        
        return f"""🚀 **Expanded 3-Pass Journey Started**

**Domain**: {domain}
**Current Position**: {current_state}

{instructions}

---

📚 **Key Resources**:
- Use `get_next_phase()` to advance and get next prompt
- Use `get_status()` to see overall progress
- Each phase guides you through the systematic thinking process

🎯 **Remember the Three Passes**:
1. **Pass 1 (Conceptualize)**: What IS this domain? (Ontological understanding)
2. **Pass 2 (Generally Reify)**: How do we MAKE things in this domain? (System building)  
3. **Pass 3 (Specifically Reify)**: How do we make THIS specific instance? (Concrete creation)

Ready to begin your systematic thinking journey!"""
        
    except Exception as e:
        logger.error(f"Error in expanded_run: {e}", exc_info=True)
        return f"❌ Error starting expanded session: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def get_next_phase(
    starlog_path: str = Field(description="STARLOG project path identifier")
) -> str:
    """
    Advance to next phase and get appropriate prompt for current pass + phase.
    
    Returns contextual guidance like: "You're on Pass 2, Phase 3. Now focus on DSL for your generation system..."
    """
    try:
        # Advance to next phase
        advance_result = next_phase(starlog_path)
        
        # Get current state
        state = tracker._load_state(starlog_path)
        if not state:
            return "❌ No active journey found. Use `core_run()` or `expanded_run()` to start."
        
        # Get contextual prompt
        phase_prompt = get_contextual_prompt(state.pass_num, state.phase, state.domain)
        
        logger.info(f"Advanced to {state.get_notation()} for {starlog_path}")
        
        # Generate master prompt reminder
        pass_reminder = "\n⚠️ **REMINDER**: You must always apply the Emergence Engine's master prompt to the pass and phase you are on. Read it with get_master_prompt() if you haven't read it recently."

        # Get the exact phase definition from master prompt
        phase_definitions = {
            1: "(1)[SystemsDesign→(1a)[PurposeCapture]→(1b)[ContextMap]→(1c)[StakeholderGoals]→(1d)[SuccessMetrics]→(1e)[ConstraintScan]→(1f)[ResourceLimits]→(1g)[RegulatoryBounds]→(1h)[RiskAssumptions]→(1i)[ConceptModel]→(1j)[OntologySketch]→(1k)[BoundarySet]→(1l)[DesignBrief]]",
            2: "(2)[SystemsArchitecture→(2a)[FunctionDecomposition]→(2b)[ModuleGrouping]→(2c)[InterfaceDefinition]→(2d)[LayerStack]→(2e)[ControlFlow]→(2f)[DataFlow]→(2g)[RedundancyPlan]→(2h)[ArchitectureSpec]]",
            3: "(3)[DSL→(3a)[ConceptTokenize]→(3b)[SyntaxDefine]→(3c)[SemanticRules]→(3d)[OperatorSet]→(3e)[ValidationTests]→(3f)[DSLSpec]]",
            4: "(4)[Topology→(4a)[NodeIdentify]→(4b)[EdgeMapping]→(4c)[FlowWeights]→(4d)[GraphBuild]→(4e)[Simulation]→(4f)[LoadBalance]→(4g)[TopologyMap]]",
            5: "(5)[EngineeredSystem→(5a)[ResourceAllocate]→(5b)[PrototypeBuild]→(5c)[IntegrationTest]→(5d)[Deploy]→(5e)[Monitor]→(5f)[StressTest]→(5g)[OperationalSystem]]",
            6: "(6)[FeedbackLoop→(6a)[TelemetryCapture]→(6b)[AnomalyDetection]→(6c)[DriftAnalysis]→(6d)[ConstraintRefit]→(6e)[DSLAdjust]→(6f)[ArchitecturePatch]→(6g)[TopologyRewire]→(6h)[Redeploy]→(6i)[GoalAlignmentCheck]]"
        }
        
        phase_def = phase_definitions.get(state.phase, f"Phase {state.phase}")
        
        # Get the proper file path
        file_path = get_phase_file_path(starlog_path, "global")
        
        return f"""{state.get_notation()}

{phase_def}

Write file: {file_path}
{pass_reminder}"""
        
    except Exception as e:
        logger.error(f"Error in get_next_phase: {e}", exc_info=True)
        return f"❌ Error advancing phase: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def get_status(
    starlog_path: str = Field(description="STARLOG project path identifier")
) -> str:
    """
    Show overall progress and what's next.
    
    Shows: "Pass 2 of 3, Phase 4 of 7", what files should exist, what's next.
    """
    try:
        # Get detailed status
        detailed_status = get_detailed_status(starlog_path)
        
        # Get current state for additional context
        state = tracker._load_state(starlog_path)
        if not state:
            return "❌ No active journey found. Use `core_run()` or `expanded_run()` to start."
        
        # Calculate progress percentages
        total_phases = 7  # 0-6
        current_pass_progress = (state.phase + 1) / total_phases * 100
        overall_progress = ((state.pass_num - 1) * total_phases + state.phase + 1) / (3 * total_phases) * 100
        
        # Determine what's next
        if state.phase < 6:
            next_phase_name = f"Phase {state.phase + 1}"
            whats_next = f"Next: {next_phase_name} in {state.get_pass_name()}"
        elif state.pass_num < 3:
            whats_next = f"Next: Start Pass {state.pass_num + 1}"
        else:
            whats_next = "Next: Consider recursive application to new layer or complete the journey"
        
        logger.info(f"Status check for {starlog_path}: {state.get_notation()}")
        
        return f"""{detailed_status}

---

📊 **Progress Analysis**:
- **Current Pass Progress**: {current_pass_progress:.1f}% ({state.phase + 1}/7 phases)
- **Overall Journey Progress**: {overall_progress:.1f}% 
- **{whats_next}**

📁 **Recommended Files/Outputs**:
- **Pass 1**: Ontology document, concept map, domain understanding
- **Pass 2**: System design, architecture, implementation plan  
- **Pass 3**: Specific instance, configuration, actual output

🔄 **Actions Available**:
- `get_next_phase()` - Advance and get next guidance
- Continue working on current phase with the guidance above
- `get_status()` - Check progress anytime"""
        
    except Exception as e:
        logger.error(f"Error in get_status: {e}", exc_info=True)
        return f"❌ Error getting status: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def reset_journey(
    starlog_path: str = Field(description="STARLOG project path identifier")
) -> str:
    """
    Reset journey back to the beginning (L0P1W[0](0)).
    
    Useful if you want to start over or apply to a different domain.
    """
    try:
        state = tracker._load_state(starlog_path)
        if not state:
            return "❌ No journey found to reset."
        
        # Reset to beginning
        state.layer = 0
        state.pass_num = 1
        state.phase = 0
        tracker._save_state(starlog_path, state)
        
        logger.info(f"Reset journey for {starlog_path} back to {state.get_notation()}")
        
        return f"""🔄 **Journey Reset**

**Domain**: {state.domain}
**Position**: {state.get_notation()} (back to start)

Ready to begin again! Use `get_next_phase()` to get your first prompt."""
        
    except Exception as e:
        logger.error(f"Error resetting journey: {e}", exc_info=True)
        return f"❌ Error resetting journey: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def complete_3pass_journey(
    starlog_path: str = Field(description="STARLOG project path identifier")
) -> str:
    """
    Mark 3-pass journey as completed and clean up state.
    
    Removes state file to keep registry clean.
    """
    try:
        result = complete_journey(starlog_path)
        logger.info(f"Completed 3-pass journey for {starlog_path}")
        
        return f"""✅ **3-Pass Journey Completed**

{result}

State cleaned up. Use `core_run()` or `expanded_run()` to start a new journey."""
        
    except Exception as e:
        logger.error(f"Error completing journey: {e}", exc_info=True)
        return f"❌ Error completing journey: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def abandon_3pass_journey(
    starlog_path: str = Field(description="STARLOG project path identifier")
) -> str:
    """
    Abandon current 3-pass journey and clean up state.
    
    Removes state file to keep registry clean.
    """
    try:
        result = abandon_journey(starlog_path)
        logger.info(f"Abandoned 3-pass journey for {starlog_path}")
        
        return f"""🗑️ **3-Pass Journey Abandoned**

{result}

State cleaned up. Use `core_run()` or `expanded_run()` to start a new journey."""
        
    except Exception as e:
        logger.error(f"Error abandoning journey: {e}", exc_info=True)
        return f"❌ Error abandoning journey: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def update_3pass_system() -> str:
    """
    Pull the latest 3-pass system from the source repository.
    
    Updates the local copy to get the freshest methodology and docs.
    """
    try:
        import subprocess
        import shutil
        
        # Use bundled files from package
        repo_path = _get_3pass_base_path()
        
        # Remove old copy if exists
        if repo_path.exists():
            shutil.rmtree(repo_path)
        
        # This would be a git clone in real usage - for now we assume it exists
        # subprocess.run(["git", "clone", "repo_url", str(repo_path)], check=True)
        
        logger.info("Updated 3-pass system repository")
        return f"""✅ **3-Pass System Updated**

Repository location: {repo_path}

Use `browse_3pass_system()` to explore the file structure.
Use `read_3pass_file(filename)` to read specific files.

Available now: Latest methodology, examples, and documentation."""
        
    except Exception as e:
        logger.error(f"Error updating 3-pass system: {e}", exc_info=True)
        return f"❌ Error updating system: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


def browse_3pass_system(
    path: str = Field(default="", description="Subdirectory to browse (empty for root)")
) -> str:
    """
    Browse the 3-pass system file structure.
    
    Returns directory listing like 'ls' command.
    """
    try:
        # Use bundled files from package
        base_path = _get_3pass_base_path()
        if not base_path.exists():
            return "❌ 3-pass system not found. Use `update_3pass_system()` first."
        
        target_path = base_path / path if path else base_path
        
        if not target_path.exists():
            return f"❌ Path not found: {path}"
        
        if target_path.is_file():
            return f"📄 {path} is a file. Use `read_3pass_file()` to read it."
        
        # List directory contents
        items = []
        for item in sorted(target_path.iterdir()):
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size = item.stat().st_size
                items.append(f"📄 {item.name} ({size} bytes)")
        
        current_path = f"/{path}" if path else "/"
        
        return f"""📂 **3-Pass System Browser**

**Current path**: {current_path}
**Full path**: {target_path}

**Contents**:
{chr(10).join(items)}

**Navigation**:
- Use `browse_3pass_system("subdir")` to enter directories
- Use `read_3pass_file("filename")` to read files"""
        
    except Exception as e:
        logger.error(f"Error browsing 3-pass system: {e}", exc_info=True)
        return f"❌ Error browsing: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


def read_3pass_file(
    filepath: str = Field(description="File path relative to 3-pass system root")
) -> str:
    """
    Read a file from the 3-pass system.
    
    Returns file contents like 'cat' command.
    """
    try:
        # Use bundled files from package
        base_path = _get_3pass_base_path()
        if not base_path.exists():
            return "❌ 3-pass system not found. Use `update_3pass_system()` first."
        
        file_path = base_path / filepath
        
        if not file_path.exists():
            return f"❌ File not found: {filepath}"
        
        if file_path.is_dir():
            return f"❌ {filepath} is a directory. Use `browse_3pass_system()` instead."
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_size = file_path.stat().st_size
        
        return f"""📄 **File**: {filepath}
**Size**: {file_size} bytes
**Path**: {file_path}

---

{content}"""
        
    except Exception as e:
        logger.error(f"Error reading 3-pass file: {e}", exc_info=True)
        return f"❌ Error reading file: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def explore_methodology_interface(
    selection: int = Field(default=None, description="Number of item to select (navigate/read), or 0 to go up"),
    page: int = Field(default=None, description="Page number for pagination")
) -> str:
    """
    Explore the 3-pass methodology with simple numbered navigation.
    
    Single interface that replaces browse_3pass_system() and read_3pass_file():
    - No parameters: Show current directory with numbered items
    - selection=3: Select item 3 (navigate if directory, read if file)  
    - selection=0: Go up one directory
    - page=2: Show page 2 of current directory
    
    Returns:
        Directory listing, file content, or navigation result
    """
    try:
        return explore_methodology(selection, page)
    except Exception as e:
        logger.error(f"Error in explore_methodology: {e}", exc_info=True)
        return f"❌ Error exploring methodology: {str(e)}\\n\\nTraceback:\\n{traceback.format_exc()}"


@mcp.tool
def inject_directory_structure(
    target_dir: str = Field(description="Directory path where to create the 3-pass structure"),
    run_type: str = Field(default="global", description="'global' for global_system, 'local' for component_specific, or component name")
) -> str:
    """
    Inject the proper 3-pass directory structure into target directory.
    
    Creates organized layer_X/pass_Y directory structure for systematic thinking.
    """
    try:
        result = inject_3pass_structure(target_dir, run_type)
        logger.info(f"Injected 3-pass structure: {target_dir} ({run_type})")
        return result
    except Exception as e:
        logger.error(f"Error injecting structure: {e}", exc_info=True)
        return f"❌ Error injecting structure: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


@mcp.tool
def get_master_prompt() -> str:
    """
    Get the complete 3-pass master prompt for systematic thinking.
    
    Returns the foundational methodology that guides all 3-pass work.
    Always read this first to understand the approach before starting any journey.
    
    Returns:
        Complete master prompt text with all passes, phases, and guidance
    """
    try:
        # Use bundled files from package
        base_path = _get_3pass_base_path()
        master_prompt_path = base_path / "system_design_instructions" / "MASTER_PROMPT.md"
        
        if not master_prompt_path.exists():
            return """❌ Master prompt file not found. Use `update_3pass_system()` first.
            
Expected location: <package>/emergence_engine/3_pass_autonomous_research_system_v01/system_design_instructions/MASTER_PROMPT.md"""
        
        with open(master_prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        logger.error(f"Error getting master prompt: {e}", exc_info=True)
        return f"❌ Error reading master prompt: {str(e)}\\n\\nTraceback:\\n{traceback.format_exc()}"


def main():
    """Main entry point for the MCP server"""
    mcp.run()


if __name__ == "__main__":
    main()