# Multi-Agent Autobiography Generator Architecture

## Core System Design

```python
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Base Agent Interface
class Agent:
    def __init__(self, role: str, tools: List[callable] = None):
        self.role = role
        self.tools = tools or []
    
    def run(self, prompt: str) -> Dict:
        """
        Stub for LLM call
        Returns: {
            'history_id': str,
            'history': History object with .history_id and .messages,
            'error': Optional[str]
        }
        """
        pass

# Pydantic Models for Tools
class Memory(BaseModel):
    """Represents a single memory/episode"""
    content: str = Field(..., description="The memory description")
    year: Optional[int] = Field(None, description="Year when this occurred")
    age: Optional[int] = Field(None, description="Age when this occurred")
    location: Optional[str] = Field(None, description="Where this happened")
    people: List[str] = Field(default_factory=list, description="People involved")
    emotions: List[str] = Field(default_factory=list, description="Emotions felt")
    significance: str = Field(..., description="Why this memory matters")

class LifePhase(BaseModel):
    """Represents a phase/era of life"""
    name: str = Field(..., description="Name of this life phase")
    start_year: int = Field(..., description="Starting year")
    end_year: int = Field(..., description="Ending year")
    description: str = Field(..., description="Overview of this period")
    key_themes: List[str] = Field(default_factory=list, description="Major themes")

class Theme(BaseModel):
    """Represents a life theme"""
    name: str = Field(..., description="Theme name")
    description: str = Field(..., description="What this theme represents")
    related_memories: List[str] = Field(default_factory=list, description="Memory IDs")
    evolution: str = Field(..., description="How theme evolved over time")

class Relationship(BaseModel):
    """Represents a significant relationship"""
    person: str = Field(..., description="Person's name")
    role: str = Field(..., description="Their role (parent, friend, mentor, etc)")
    impact: str = Field(..., description="Impact on life")
    key_moments: List[str] = Field(default_factory=list, description="Shared memories")

class ChapterOutline(BaseModel):
    """Represents a chapter structure"""
    title: str = Field(..., description="Chapter title")
    theme: str = Field(..., description="Central theme")
    memories: List[str] = Field(..., description="Memory IDs to include")
    opening: str = Field(..., description="How chapter begins")
    arc: str = Field(..., description="Chapter's narrative arc")

# Tool Functions
def store_memory(memory: Memory) -> str:
    """Store a memory and return its ID"""
    # Implementation would store in database/memory
    memory_id = f"mem_{datetime.now().timestamp()}"
    return f"Stored memory {memory_id}: {memory.content[:50]}..."

def organize_timeline(memories: List[Memory]) -> List[LifePhase]:
    """Organize memories into life phases"""
    # Implementation would analyze and group memories
    return []

def extract_themes(memories: List[Memory]) -> List[Theme]:
    """Extract recurring themes from memories"""
    # Implementation would identify patterns
    return []

def identify_relationships(memories: List[Memory]) -> List[Relationship]:
    """Identify key relationships from memories"""
    # Implementation would extract and analyze people
    return []

def create_chapter_outline(
    phase: LifePhase, 
    memories: List[Memory], 
    themes: List[Theme]
) -> ChapterOutline:
    """Create chapter outline for a life phase"""
    # Implementation would structure narrative
    return ChapterOutline(
        title="",
        theme="", 
        memories=[],
        opening="",
        arc=""
    )

def generate_narrative(
    outline: ChapterOutline,
    memories: List[Memory],
    voice_profile: Dict[str, Any]
) -> str:
    """Generate actual narrative text for chapter"""
    # Implementation would create prose
    return ""

# Specialized Agents
class InterviewAgent(Agent):
    """Agent responsible for memory elicitation"""
    def __init__(self):
        super().__init__(
            role="interviewer",
            tools=[store_memory]
        )
    
    def conduct_interview(self, life_phase: str) -> List[Memory]:
        prompt = f"""You are conducting an interview about someone's {life_phase}.
        Ask thoughtful questions to elicit specific memories, including:
        - Specific events and moments
        - People who were important
        - Emotions and significance
        - Sensory details
        
        Guide them to share 3-5 detailed memories from this period."""
        
        result = self.run(prompt)
        # Parse memories from conversation
        return []

class TimelineAgent(Agent):
    """Agent responsible for chronological organization"""
    def __init__(self):
        super().__init__(
            role="timeline_organizer",
            tools=[organize_timeline]
        )
    
    def build_timeline(self, memories: List[Memory]) -> List[LifePhase]:
        prompt = f"""Given these {len(memories)} memories, organize them into 
        coherent life phases. Identify:
        - Major life periods (childhood, education, career, etc)
        - Transition points between phases
        - Approximate date ranges
        - Key characteristics of each phase"""
        
        result = self.run(prompt)
        return []

class ThemeAgent(Agent):
    """Agent responsible for theme extraction"""
    def __init__(self):
        super().__init__(
            role="theme_analyst",
            tools=[extract_themes]
        )
    
    def analyze_themes(self, memories: List[Memory]) -> List[Theme]:
        prompt = f"""Analyze these {len(memories)} memories to identify:
        - Recurring life themes (growth, loss, discovery, etc)
        - How themes evolve over time
        - Connections between different memories
        - The deeper patterns and meanings"""
        
        result = self.run(prompt)
        return []

class NarrativeAgent(Agent):
    """Agent responsible for narrative generation"""
    def __init__(self):
        super().__init__(
            role="narrative_writer",
            tools=[create_chapter_outline, generate_narrative]
        )
    
    def write_chapter(
        self,
        phase: LifePhase,
        memories: List[Memory],
        themes: List[Theme],
        voice_sample: str
    ) -> str:
        prompt = f"""Create a chapter for the {phase.name} period.
        Include these memories and themes, maintaining the author's voice.
        Structure with:
        - Engaging opening
        - Smooth transitions between memories
        - Thematic coherence
        - Reflective insights
        - Satisfying conclusion"""
        
        result = self.run(prompt)
        return ""

class VoiceAgent(Agent):
    """Agent responsible for maintaining authentic voice"""
    def __init__(self):
        super().__init__(
            role="voice_analyst",
            tools=[]
        )
    
    def analyze_voice(self, writing_samples: List[str]) -> Dict[str, Any]:
        prompt = f"""Analyze these writing samples to identify:
        - Vocabulary preferences
        - Sentence structure patterns
        - Emotional expression style
        - Humor/seriousness balance
        - Cultural/generational markers"""
        
        result = self.run(prompt)
        return {}

# Orchestrator
class AutobiographyOrchestrator:
    """Main orchestrator that coordinates all agents"""
    
    def __init__(self):
        self.interview_agent = InterviewAgent()
        self.timeline_agent = TimelineAgent()
        self.theme_agent = ThemeAgent()
        self.narrative_agent = NarrativeAgent()
        self.voice_agent = VoiceAgent()
        
        self.memories: List[Memory] = []
        self.phases: List[LifePhase] = []
        self.themes: List[Theme] = []
        self.relationships: List[Relationship] = []
        self.voice_profile: Dict[str, Any] = {}
        self.chapters: List[str] = []
    
    def generate_autobiography(self, user_name: str) -> str:
        """Main method to generate complete autobiography"""
        
        # Phase 1: Initial Setup
        print(f"Starting autobiography generation for {user_name}")
        
        # Phase 2: Memory Collection
        print("Collecting memories...")
        self.collect_memories()
        
        # Phase 3: Analysis
        print("Analyzing life structure...")
        self.analyze_structure()
        
        # Phase 4: Narrative Generation
        print("Generating narrative...")
        self.generate_narrative()
        
        # Phase 5: Assembly
        print("Assembling final autobiography...")
        return self.assemble_autobiography()
    
    def collect_memories(self):
        """Collect memories through interviews"""
        life_stages = [
            "early childhood",
            "school years", 
            "young adulthood",
            "career development",
            "family life",
            "recent years"
        ]
        
        for stage in life_stages:
            stage_memories = self.interview_agent.conduct_interview(stage)
            self.memories.extend(stage_memories)
    
    def analyze_structure(self):
        """Analyze collected memories for structure"""
        # Build timeline
        self.phases = self.timeline_agent.build_timeline(self.memories)
        
        # Extract themes
        self.themes = self.theme_agent.analyze_themes(self.memories)
        
        # Analyze voice from memory descriptions
        samples = [m.content for m in self.memories[:10]]
        self.voice_profile = self.voice_agent.analyze_voice(samples)
    
    def generate_narrative(self):
        """Generate narrative chapters"""
        for phase in self.phases:
            # Get memories for this phase
            phase_memories = [
                m for m in self.memories 
                if phase.start_year <= (m.year or 0) <= phase.end_year
            ]
            
            # Generate chapter
            chapter = self.narrative_agent.write_chapter(
                phase,
                phase_memories,
                self.themes,
                self.voice_profile.get('sample', '')
            )
            
            self.chapters.append(chapter)
    
    def assemble_autobiography(self) -> str:
        """Assemble final autobiography"""
        # Add preface
        preface = self.generate_preface()
        
        # Combine all chapters
        body = "\n\n".join(self.chapters)
        
        # Add epilogue
        epilogue = self.generate_epilogue()
        
        return f"{preface}\n\n{body}\n\n{epilogue}"
    
    def generate_preface(self) -> str:
        """Generate preface using narrative agent"""
        return "# Preface\n\n[Generated preface content]"
    
    def generate_epilogue(self) -> str:
        """Generate epilogue using narrative agent"""
        return "# Epilogue\n\n[Generated epilogue content]"

# Usage Example
if __name__ == "__main__":
    orchestrator = AutobiographyOrchestrator()
    autobiography = orchestrator.generate_autobiography("Jane Doe")
    print(autobiography)
```

## System Flow

1. **Memory Collection Phase**
   - InterviewAgent conducts structured interviews
   - Memories stored with metadata (time, people, emotions)
   - Covers all major life periods

2. **Analysis Phase**
   - TimelineAgent organizes chronologically
   - ThemeAgent extracts patterns
   - VoiceAgent captures authentic style

3. **Narrative Generation Phase**
   - NarrativeAgent creates chapter outlines
   - Generates prose maintaining voice
   - Integrates themes throughout

4. **Assembly Phase**
   - Orchestrator combines all elements
   - Adds meta-elements (preface, epilogue)
   - Produces complete autobiography

## Key Design Decisions

1. **Agent Specialization**: Each agent has a focused role
2. **Tool Integration**: Tools handle specific operations with typed inputs
3. **Memory Persistence**: All content stored for reference
4. **Voice Preservation**: Analyzed early, applied throughout
5. **Iterative Refinement**: Can loop back for more memories
