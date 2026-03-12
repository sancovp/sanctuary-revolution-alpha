"""
Core functionality for the 3-pass state tracker
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)


class PhasePrompts:
    """Contextual prompts for each phase based on current pass"""
    
    PHASE_NAMES = {
        0: "AbstractGoal",
        1: "SystemsDesign", 
        2: "SystemsArchitecture",
        3: "DSL",
        4: "Topology",
        5: "EngineeredSystem",
        6: "FeedbackLoop"
    }
    
    PASS_NAMES = {
        1: "Conceptualize (What IS)",
        2: "Generally Reify (How MAKE)", 
        3: "Specifically Reify (Make THIS)"
    }
    
    @classmethod
    def _get_pass1_prompts(cls, domain: str) -> dict:
        """Get Pass 1 (Conceptualize) prompts"""
        return {
            0: f"🎯 **Abstract Goal - Pass 1**: What IS the essential nature of {domain}?\n\nFocus on understanding the fundamental ontology. What makes something part of this domain? What are the essential properties and relationships?",
            1: f"🏗️ **Systems Design - Pass 1**: What are the universal characteristics of {domain}?\n\nExplore: Purpose, stakeholders, constraints, concepts, ontology. What exists in this domain universally?",
            2: f"🏛️ **Systems Architecture - Pass 1**: What are the essential functions and structures in {domain}?\n\nIdentify natural groupings, relationships, and patterns that exist conceptually in this domain.",
            3: f"📝 **DSL - Pass 1**: What concepts and vocabulary exist naturally in {domain}?\n\nDefine the core concepts, relationships, and operations that are inherent to this domain.",
            4: f"🌐 **Topology - Pass 1**: What entities and relationships form the natural structure of {domain}?\n\nMap the network of concepts and how they connect in this domain.",
            5: f"⚙️ **Engineered System - Pass 1**: What would constitute a complete instance of {domain}?\n\nDescribe what a fully realized example would look like conceptually.",
            6: f"🔄 **Feedback Loop - Pass 1**: How does {domain} naturally evolve and improve?\n\nUnderstand the inherent learning and adaptation patterns in this domain.",
        }
    
    @classmethod
    def _get_pass2_prompts(cls, domain: str) -> dict:
        """Get Pass 2 (Generally Reify) prompts"""
        return {
            0: f"🎯 **Abstract Goal - Pass 2**: Create a system that can generate {domain} instances.\n\nDefine the goal of building a generator/framework that can create instances of what you understood in Pass 1.",
            1: f"🏗️ **Systems Design - Pass 2**: What does our {domain} generation system need?\n\nDesign requirements for a system that can create instances. Consider stakeholders, constraints, success metrics.",
            2: f"🏛️ **Systems Architecture - Pass 2**: How do components work together to generate {domain}?\n\nDesign the architecture: modules, interfaces, data flow, control flow for your generation system.",
            3: f"📝 **DSL - Pass 2**: What vocabulary does our {domain} system use internally?\n\nDefine the system's internal language, APIs, data structures, and operations.",
            4: f"🌐 **Topology - Pass 2**: How are system components connected?\n\nMap the network of services, APIs, data flows in your generation system.",
            5: f"⚙️ **Engineered System - Pass 2**: Build and deploy the {domain} generation system.\n\nImplement, test, and deploy your system that can create instances.",
            6: f"🔄 **Feedback Loop - Pass 2**: How does the {domain} system learn and improve?\n\nImplement monitoring, learning, and evolution for your generation system.",
        }
    
    @classmethod  
    def _get_pass3_prompts(cls, domain: str) -> dict:
        """Get Pass 3 (Specifically Reify) prompts"""
        return {
            0: f"🎯 **Abstract Goal - Pass 3**: Generate this specific {domain} instance.\n\nDefine the specific instance you want to create using your system.",
            1: f"🏗️ **Systems Design - Pass 3**: What does this specific {domain} instance need?\n\nSpecify requirements, constraints, and success criteria for this particular instance.",
            2: f"🏛️ **Systems Architecture - Pass 3**: How is this specific {domain} instance configured?\n\nConfigure your system architecture for this specific use case.",
            3: f"📝 **DSL - Pass 3**: How do we express this specific {domain} instance?\n\nDefine the specific configuration, parameters, and expressions for this instance.",
            4: f"🌐 **Topology - Pass 3**: What are the specific connections for this {domain} instance?\n\nMap the specific data flows, connections, and network for this instance.",
            5: f"⚙️ **Engineered System - Pass 3**: Create and deploy this specific {domain} instance.\n\nActually generate, configure, and deploy your specific instance.",
            6: f"🔄 **Feedback Loop - Pass 3**: How does this specific {domain} instance perform?\n\nMonitor, evaluate, and improve this specific instance based on its performance."
        }
    
    @classmethod
    def get_phase_prompt(cls, pass_num: int, phase: int, domain: str) -> str:
        """Get specific guidance for current pass and phase"""
        phase_name = cls.PHASE_NAMES.get(phase, f"Phase{phase}")
        pass_name = cls.PASS_NAMES.get(pass_num, f"Pass{pass_num}")
        
        if pass_num == 1:
            prompts = cls._get_pass1_prompts(domain)
        elif pass_num == 2:
            prompts = cls._get_pass2_prompts(domain)
        elif pass_num == 3:
            prompts = cls._get_pass3_prompts(domain)
        else:
            return f"Work on {phase_name} for {pass_name} in domain: {domain}"
        
        return prompts.get(phase, f"Work on {phase_name} for {pass_name} in domain: {domain}")


class ThreePassState(BaseModel):
    """
    State tracking for 3-pass systematic thinking methodology
    
    Uses notation from the System Design DSL:
    L₀P₁W[0](3) = Layer 0, Pass 1, Workflow Phase 3
    """
    
    domain: str = Field(..., description="The domain being analyzed")
    layer: int = Field(default=0, description="Current layer (L₀, L₁, L₂, ...)")
    pass_num: int = Field(default=1, description="Current pass (1=Conceptualize, 2=Generally Reify, 3=Specifically Reify)")
    phase: int = Field(default=0, description="Current workflow phase (0-6)")
    started_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def get_notation(self) -> str:
        """Return current state in DSL notation"""
        return f"L{self.layer}P{self.pass_num}W[{self.layer}]({self.phase})"
    
    def get_phase_name(self) -> str:
        """Return human-readable phase name"""
        phase_names = {
            0: "AbstractGoal",
            1: "SystemsDesign", 
            2: "SystemsArchitecture",
            3: "DSL",
            4: "Topology", 
            5: "EngineeredSystem",
            6: "FeedbackLoop"
        }
        return phase_names.get(self.phase, f"Phase{self.phase}")
    
    def get_pass_name(self) -> str:
        """Return human-readable pass name"""
        pass_names = {
            1: "Conceptualize (What IS)",
            2: "Generally Reify (How MAKE)", 
            3: "Specifically Reify (Make THIS)"
        }
        return pass_names.get(self.pass_num, f"Pass{self.pass_num}")


class ThreePassTracker:
    """
    Manages 3-pass state for multiple journeys using file-based persistence
    """
    
    def __init__(self, base_path: str = "/tmp/three_pass_states"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def _get_state_file(self, starlog_path: str) -> Path:
        """Get state file path for a starlog project"""
        # Use starlog path as unique identifier
        safe_name = starlog_path.replace("/", "_").replace("\\", "_")
        return self.base_path / f"{safe_name}.json"
    
    def _load_state(self, starlog_path: str) -> Optional[ThreePassState]:
        """Load state from file"""
        state_file = self._get_state_file(starlog_path)
        if not state_file.exists():
            logger.debug(f"No state file found at: {state_file}")
            return None
        
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            logger.debug(f"Loaded state from: {state_file}")
            return ThreePassState(**data)
        except Exception as e:
            logger.error(f"Failed to load state from {state_file}: {e}")
            return None
    
    def _save_state(self, starlog_path: str, state: ThreePassState) -> None:
        """Save state to file"""
        state_file = self._get_state_file(starlog_path)
        state.last_updated = datetime.now()
        
        with open(state_file, 'w') as f:
            json.dump(state.model_dump(), f, default=str, indent=2)
    
    def start_journey(self, domain: str, starlog_path: str) -> str:
        """Start a new 3-pass journey"""
        logger.info(f"Starting 3-pass journey for domain '{domain}' at path '{starlog_path}'")
        state = ThreePassState(domain=domain)
        self._save_state(starlog_path, state)
        logger.debug(f"Created initial state: {state.get_notation()}")
        return f"Started 3-pass journey for '{domain}' at {state.get_notation()}"
    
    def get_current_state(self, starlog_path: str) -> str:
        """Get current state in DSL notation"""
        state = self._load_state(starlog_path)
        if not state:
            return "No active 3-pass journey found. Use start_journey() first."
        return state.get_notation()
    
    def next_phase(self, starlog_path: str) -> str:
        """Advance to next phase"""
        state = self._load_state(starlog_path)
        if not state:
            logger.warning(f"Attempted to advance phase but no journey found for path: {starlog_path}")
            return "No active journey found. Use start_journey() first."
        
        old_notation = state.get_notation()
        
        # Advance phase
        if state.phase < 6:
            state.phase += 1
        else:
            # End of workflow phases, advance pass
            if state.pass_num < 3:
                state.pass_num += 1
                state.phase = 0
                logger.info(f"Advanced to next pass: {state.pass_num}")
            else:
                # End of all passes, advance layer (recursive application)
                state.layer += 1
                state.pass_num = 1
                state.phase = 0
                logger.info(f"Advanced to next layer: {state.layer}")
        
        self._save_state(starlog_path, state)
        logger.debug(f"Phase transition: {old_notation} → {state.get_notation()}")
        return f"Advanced to {state.get_notation()}"
    
    def get_instructions(self, starlog_path: str) -> str:
        """Get instructions for current phase"""
        state = self._load_state(starlog_path)
        if not state:
            return "No active journey found. Use start_journey() first."
        
        instructions = f"""
Current Position: {state.get_notation()}
Domain: {state.domain}
Pass: {state.get_pass_name()}
Phase: {state.get_phase_name()}

Instructions:
Apply the 3-pass master prompt methodology to Phase {state.phase} ({state.get_phase_name()}) 
with the mindset of {state.get_pass_name()} for your domain: {state.domain}

Remember:
- Pass 1: Focus on understanding WHAT this domain IS (ontological)
- Pass 2: Focus on HOW to BUILD systems that create these things  
- Pass 3: Focus on creating THIS specific instance

Use the complete workflow notation from the master prompt to guide your work 
through this specific phase.
"""
        return instructions.strip()
    
    def get_status(self, starlog_path: str) -> str:
        """Get detailed status of current journey"""
        state = self._load_state(starlog_path)
        if not state:
            return "No active 3-pass journey found."
        
        total_phases = 7  # 0-6
        current_step = (state.layer * 3 * total_phases) + ((state.pass_num - 1) * total_phases) + state.phase + 1
        
        return f"""
3-Pass Journey Status:
Domain: {state.domain}
Position: {state.get_notation()}
Layer: {state.layer} | Pass: {state.pass_num}/3 | Phase: {state.phase}/6
Current Step: {current_step}
Started: {state.started_at.strftime('%Y-%m-%d %H:%M')}
Last Updated: {state.last_updated.strftime('%Y-%m-%d %H:%M')}

Current Phase: {state.get_phase_name()}
Current Pass: {state.get_pass_name()}

Next: Use get_instructions() for detailed guidance
"""
    
    def complete_journey(self, starlog_path: str) -> str:
        """Complete and clean up journey state"""
        state = self._load_state(starlog_path)
        if not state:
            return "No active journey found to complete."
        
        # Store completion info before cleanup
        domain = state.domain
        final_notation = state.get_notation()
        
        # Remove state file
        state_file = self._get_state_file(starlog_path)
        if state_file.exists():
            state_file.unlink()
            logger.info(f"Completed and cleaned up journey for domain '{domain}' at {final_notation}")
        
        return f"Journey completed and cleaned up: '{domain}' (final position: {final_notation})"
    
    def abandon_journey(self, starlog_path: str) -> str:
        """Abandon and clean up journey state"""
        state = self._load_state(starlog_path)
        if not state:
            return "No active journey found to abandon."
        
        # Store abandonment info before cleanup
        domain = state.domain
        last_notation = state.get_notation()
        
        # Remove state file
        state_file = self._get_state_file(starlog_path)
        if state_file.exists():
            state_file.unlink()
            logger.info(f"Abandoned and cleaned up journey for domain '{domain}' at {last_notation}")
        
        return f"Journey abandoned and cleaned up: '{domain}' (last position: {last_notation})"


# Convenience functions for direct usage
_default_tracker = ThreePassTracker()

def start_journey(domain: str, starlog_path: str) -> str:
    """Start a new 3-pass journey"""
    return _default_tracker.start_journey(domain, starlog_path)

def get_current_state(starlog_path: str) -> str:
    """Get current state in DSL notation"""
    return _default_tracker.get_current_state(starlog_path)

def next_phase(starlog_path: str) -> str:
    """Advance to next phase"""
    return _default_tracker.next_phase(starlog_path)

def get_instructions(starlog_path: str) -> str:
    """Get instructions for current phase"""
    return _default_tracker.get_instructions(starlog_path)

def get_status(starlog_path: str) -> str:
    """Get detailed status of current journey"""
    return _default_tracker.get_status(starlog_path)

def complete_journey(starlog_path: str) -> str:
    """Complete and clean up journey state"""
    return _default_tracker.complete_journey(starlog_path)

def abandon_journey(starlog_path: str) -> str:
    """Abandon and clean up journey state"""
    return _default_tracker.abandon_journey(starlog_path)

def get_contextual_prompt(pass_num: int, phase: int, domain: str) -> str:
    """Get contextual prompt for specific pass, phase, and domain"""
    return PhasePrompts.get_phase_prompt(pass_num, phase, domain)


class MethodologyExplorer:
    """Simple numbered navigation for 3-pass methodology files"""
    
    def __init__(self, repo_path: Optional[str] = None):
        if repo_path is None:
            # Use bundled files from package
            package_dir = Path(__file__).parent
            repo_path = str(package_dir / "3_pass_autonomous_research_system_v01")
        self.repo_path = Path(repo_path)
        self.current_path = Path("")  # Relative to repo_path
        self._page_size = 10
        
    def explore(self, selection: Optional[int] = None, page: Optional[int] = None) -> str:
        """
        Unified exploration interface with numbered navigation.
        
        Args:
            selection: Select numbered item (navigate if dir, read if file)
            page: Page number for pagination (default 1)
            
        Returns:
            Directory listing with numbers, file content, or error message
        """
        # Check if repo exists
        if not self.repo_path.exists():
            return "❌ 3-pass system not found. Use `update_3pass_system()` first."
        
        full_path = self.repo_path / self.current_path
        
        # If selection provided, handle navigation/reading
        if selection is not None:
            return self._handle_selection(selection)
        
        # Otherwise show current directory with pagination
        return self._show_directory(page)
    
    def _get_directory_items(self, full_path: Path) -> list:
        """Get sorted list of directory items (helper to reduce function size)"""
        items = []
        for item in full_path.iterdir():
            if item.name.startswith('.'):
                continue  # Skip hidden files
            if item.is_dir():
                items.append((item.name, True))  # (name, is_directory)
            else:
                items.append((item.name, False))
        
        # Sort with numbers first (0-9), then letters (a-z)
        def sort_key(item_tuple):
            name = item_tuple[0].lower()
            # If starts with digit, sort by digit value first
            if name[0].isdigit():
                return (0, name)  # Numbers get priority 0
            else:
                return (1, name)  # Letters get priority 1
        
        items.sort(key=sort_key)
        return items
    
    def _build_navigation_help(self, page: int, total_pages: int) -> str:
        """Build navigation help text (helper to reduce function size)"""
        result = "\n**Navigation**:\n"
        result += "• Select by number: `explore_methodology(3)` to select item 3\n"
        if total_pages > 1:
            if page < total_pages:
                result += f"• Next page: `explore_methodology(page={page + 1})`\n"
            if page > 1:
                result += f"• Previous page: `explore_methodology(page={page - 1})`\n"
        if self.current_path:
            result += "• Go up: `explore_methodology(0)` to go up one directory\n"
        return result
    
    def _format_directory_listing(self, page_items: list, start_idx: int, 
                                  page: int, total_pages: int, total_items: int) -> str:
        """Format the directory listing output (helper to reduce function size)"""
        current = str(self.current_path) if self.current_path else "/"
        result = f"📂 **3-Pass Methodology Explorer**\n"
        result += f"**Current Path**: {current}\n\n"
        
        if page == 1 and total_pages == 1:
            result += f"**Contents** ({total_items} items):\n"
        else:
            result += f"**Contents** (page {page}/{total_pages}, {total_items} total):\n"
        
        for i, (name, is_dir) in enumerate(page_items, start_idx + 1):
            icon = "📁" if is_dir else "📄"
            result += f"{i}. {icon} {name}\n"
        
        return result
    
    def _validate_directory_path(self, full_path: Path) -> Optional[str]:
        """Validate directory path and handle edge cases"""
        if not full_path.exists():
            return f"❌ Path not found: {self.current_path}"
        
        if full_path.is_file():
            # If somehow we're at a file, read it
            return self._read_file(full_path)
        
        return None
    
    def _calculate_pagination(self, items: list, page: Optional[int]) -> tuple:
        """Calculate pagination parameters"""
        total_items = len(items)
        total_pages = (total_items + self._page_size - 1) // self._page_size
        
        if page is None:
            page = 1
        
        if page < 1 or page > total_pages:
            return None, f"❌ Page {page} out of range. Available pages: 1-{total_pages}"
        
        start_idx = (page - 1) * self._page_size
        end_idx = min(start_idx + self._page_size, total_items)
        page_items = items[start_idx:end_idx]
        
        return (page, total_pages, start_idx, page_items), None
    
    def _show_directory(self, page: Optional[int]) -> str:
        """Show paginated directory listing with numbers"""
        full_path = self.repo_path / self.current_path
        
        # Validate path
        validation_error = self._validate_directory_path(full_path)
        if validation_error:
            return validation_error
        
        # Get directory items
        items = self._get_directory_items(full_path)
        
        if not items:
            return f"📂 {self.current_path or '/'}: Empty directory"
        
        # Calculate pagination
        pagination_result, error = self._calculate_pagination(items, page)
        if error:
            return error
        
        page, total_pages, start_idx, page_items = pagination_result
        
        # Build output
        result = self._format_directory_listing(page_items, start_idx, page, total_pages, len(items))
        result += self._build_navigation_help(page, total_pages)
        
        return result
    
    def _handle_go_up(self) -> str:
        """Handle going up one directory (helper to reduce function size)"""
        if not self.current_path or self.current_path == Path("."):
            return "📂 Already at root directory"
        self.current_path = self.current_path.parent
        if self.current_path == Path("."):
            self.current_path = Path("")
        return self._show_directory(None)
    
    def _get_selected_item(self, selection: int, full_path: Path) -> Optional[Path]:
        """Get the selected item from directory (helper to reduce function size)"""
        items = []
        for item in full_path.iterdir():
            if item.name.startswith('.'):
                continue
            items.append(item)
        
        # Sort with numbers first (0-9), then letters (a-z) - same as _get_directory_items
        def sort_key(item):
            name = item.name.lower()
            if name[0].isdigit():
                return (0, name)  # Numbers get priority 0
            else:
                return (1, name)  # Letters get priority 1
        
        items.sort(key=sort_key)
        
        if selection < 1 or selection > len(items):
            return None
        
        return items[selection - 1]
    
    def _handle_selection(self, selection: int) -> str:
        """Handle numbered selection - navigate or read"""
        
        # Special case: 0 means go up
        if selection == 0:
            return self._handle_go_up()
        
        # Get directory listing to find selected item
        full_path = self.repo_path / self.current_path
        
        if not full_path.exists() or not full_path.is_dir():
            return "❌ Current path is not a valid directory"
        
        # Get selected item
        selected = self._get_selected_item(selection, full_path)
        if selected is None:
            items_count = len(list(full_path.iterdir()))
            return f"❌ Selection {selection} out of range. Available: 1-{items_count}"
        
        if selected.is_dir():
            # Navigate into directory
            self.current_path = self.current_path / selected.name
            return self._show_directory(None)
        else:
            # Read file
            return self._read_file(selected)
    
    def _read_file(self, file_path: Path) -> str:
        """Read and display file content"""
        import traceback
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            rel_path = file_path.relative_to(self.repo_path)
            file_size = file_path.stat().st_size
            
            result = f"📄 **File**: {rel_path}\n"
            result += f"**Size**: {file_size} bytes\n\n"
            result += "---\n\n"
            result += content
            result += "\n\n---\n\n"
            result += "**Navigation**:\n"
            result += "• Back to directory: `explore_methodology()` to see current directory\n"
            result += "• Go up: `explore_methodology(0)` to go up one directory\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            return f"❌ Error reading file: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


# Global explorer instance
_methodology_explorer = MethodologyExplorer()

def explore_methodology(selection: Optional[int] = None, page: Optional[int] = None) -> str:
    """
    Explore the 3-pass methodology with simple numbered navigation.
    
    Args:
        selection: Number of item to select (navigate/read), or 0 to go up
        page: Page number for pagination
        
    Returns:
        Directory listing, file content, or navigation result
    """
    return _methodology_explorer.explore(selection, page)


def inject_3pass_structure(target_dir: str, run_type: str = "global") -> str:
    """
    Create the proper 3-pass directory structure in target directory.
    
    Args:
        target_dir: Directory path where to create the structure
        run_type: "global" for global_system, "local" for component_specific, or component name
        
    Returns:
        Success message with created structure
    """
    base_path = Path(target_dir)
    
    # Create base 3_pass_thinking directory
    thinking_dir = base_path / "3_pass_thinking"
    thinking_dir.mkdir(parents=True, exist_ok=True)
    
    if run_type == "global":
        # Create global_system structure
        system_dir = thinking_dir / "global_system"
        system_dir.mkdir(exist_ok=True)
        
        # Create layer directories with pass subdirectories
        for layer in range(3):  # layer_0, layer_1, layer_2
            layer_dir = system_dir / f"layer_{layer}"
            layer_dir.mkdir(exist_ok=True)
            
            for pass_num in range(1, 4):  # pass_1, pass_2, pass_3
                pass_dir = layer_dir / f"pass_{pass_num}"
                pass_dir.mkdir(exist_ok=True)
        
        structure_created = "global_system with layer_0/1/2 each containing pass_1/2/3"
        
    elif run_type == "local":
        # Create component_specific directory (for later component additions)
        comp_dir = thinking_dir / "component_specific"
        comp_dir.mkdir(exist_ok=True)
        structure_created = "component_specific directory ready for components"
        
    else:
        # Create specific component structure
        comp_dir = thinking_dir / "component_specific" / run_type
        comp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create layer directories with pass subdirectories for this component
        for layer in range(3):
            layer_dir = comp_dir / f"layer_{layer}"
            layer_dir.mkdir(exist_ok=True)
            
            for pass_num in range(1, 4):
                pass_dir = layer_dir / f"pass_{pass_num}"
                pass_dir.mkdir(exist_ok=True)
        
        structure_created = f"component '{run_type}' with layer_0/1/2 each containing pass_1/2/3"
    
    logger.info(f"Injected 3-pass structure into {target_dir}: {structure_created}")
    
    return f"""✅ **3-Pass Directory Structure Injected**

**Target**: {target_dir}
**Type**: {run_type}
**Structure Created**: {structure_created}

**Directory Structure**:
```
{target_dir}/
└── 3_pass_thinking/
    ├── global_system/          # (if global)
    │   ├── layer_0/
    │   │   ├── pass_1/         # Files 0-6 from Pass 1
    │   │   ├── pass_2/         # Files 0-6 from Pass 2
    │   │   └── pass_3/         # Files 0-6 from Pass 3
    │   ├── layer_1/
    │   └── layer_2/
    └── component_specific/     # (if local/component)
        └── {run_type}/         # (if specific component)
            ├── layer_0/
            ├── layer_1/
            └── layer_2/
```

Ready for systematic thinking work!"""


def get_phase_file_path(starlog_path: str, run_type: str = "global", component_name: str = None) -> str:
    """
    Get the correct file path for current phase based on state and run type.
    
    Args:
        starlog_path: STARLOG project path
        run_type: "global" or "local" 
        component_name: Component name if local run
        
    Returns:
        Full file path where the current phase file should be written
    """
    state = _default_tracker._load_state(starlog_path)
    if not state:
        return "No active journey found"
    
    base_path = Path(starlog_path)
    
    if run_type == "global":
        file_dir = base_path / "3_pass_thinking" / "global_system" / f"layer_{state.layer}" / f"pass_{state.pass_num}"
    else:
        if not component_name:
            return "Component name required for local runs"
        file_dir = base_path / "3_pass_thinking" / "component_specific" / component_name / f"layer_{state.layer}" / f"pass_{state.pass_num}"
    
    filename = f"{state.phase}_{state.get_phase_name()}.md"
    return str(file_dir / filename)