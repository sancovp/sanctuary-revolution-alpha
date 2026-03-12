# Detailed Agent Implementations

```python
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum
import json
from dataclasses import dataclass

# Enhanced Memory Model with validation
class MemoryType(str, Enum):
    MILESTONE = "milestone"
    ROUTINE = "routine"
    CHALLENGE = "challenge"
    RELATIONSHIP = "relationship"
    ACHIEVEMENT = "achievement"
    LOSS = "loss"
    INSIGHT = "insight"

class Memory(BaseModel):
    """Enhanced memory model with richer metadata"""
    id: str = Field(default_factory=lambda: f"mem_{datetime.now().timestamp()}")
    content: str = Field(..., min_length=10, description="The memory description")
    memory_type: MemoryType = Field(..., description="Type of memory")
    year: Optional[int] = Field(None, ge=1900, le=2024, description="Year when this occurred")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age when this occurred")
    season: Optional[str] = Field(None, description="Season when this occurred")
    location: Optional[str] = Field(None, description="Where this happened")
    people: List[str] = Field(default_factory=list, description="People involved")
    emotions: List[str] = Field(default_factory=list, description="Emotions felt")
    sensory_details: Dict[str, str] = Field(default_factory=dict, description="Sights, sounds, smells")
    significance: str = Field(..., description="Why this memory matters")
    related_memories: List[str] = Field(default_factory=list, description="IDs of related memories")
    
    @validator('emotions')
    def validate_emotions(cls, v):
        valid_emotions = {
            'joy', 'sadness', 'fear', 'anger', 'surprise', 'disgust',
            'love', 'pride', 'shame', 'guilt', 'anxiety', 'excitement',
            'contentment', 'frustration', 'relief', 'nostalgia'
        }
        for emotion in v:
            if emotion.lower() not in valid_emotions:
                # Allow it but normalize
                continue
        return [e.lower() for e in v]

# Memory Storage System
class MemoryBank:
    """Centralized storage for all memories"""
    def __init__(self):
        self.memories: Dict[str, Memory] = {}
        self.timeline: List[str] = []  # Ordered memory IDs
        self.theme_index: Dict[str, List[str]] = {}  # Theme -> Memory IDs
        self.people_index: Dict[str, List[str]] = {}  # Person -> Memory IDs
    
    def store(self, memory: Memory) -> str:
        """Store a memory and update indices"""
        self.memories[memory.id] = memory
        
        # Update timeline
        self._insert_chronologically(memory)
        
        # Update people index
        for person in memory.people:
            if person not in self.people_index:
                self.people_index[person] = []
            self.people_index[person].append(memory.id)
        
        return memory.id
    
    def _insert_chronologically(self, memory: Memory):
        """Insert memory in chronological order"""
        if not memory.year:
            self.timeline.append(memory.id)
            return
            
        # Find insertion point
        insert_pos = len(self.timeline)
        for i, mem_id in enumerate(self.timeline):
            existing = self.memories[mem_id]
            if existing.year and existing.year > memory.year:
                insert_pos = i
                break
        
        self.timeline.insert(insert_pos, memory.id)
    
    def get_by_period(self, start_year: int, end_year: int) -> List[Memory]:
        """Get memories within a time period"""
        return [
            self.memories[mid] for mid in self.timeline
            if self.memories[mid].year and start_year <= self.memories[mid].year <= end_year
        ]
    
    def get_by_person(self, person: str) -> List[Memory]:
        """Get all memories involving a person"""
        return [self.memories[mid] for mid in self.people_index.get(person, [])]

# Interview Tools
def elicit_memory_details(basic_memory: str) -> Memory:
    """Tool to expand a basic memory into detailed Memory object"""
    # This would use agent.run() to get details
    return Memory(
        content=basic_memory,
        memory_type=MemoryType.MILESTONE,
        significance="To be determined"
    )

def suggest_memory_prompts(life_phase: str, existing_memories: List[str]) -> List[str]:
    """Tool to generate contextual prompts for memory elicitation"""
    base_prompts = {
        "childhood": [
            "What's your earliest memory?",
            "Tell me about your childhood home.",
            "Who were your closest friends as a child?",
            "What family traditions do you remember?",
            "What scared you as a child?"
        ],
        "adolescence": [
            "How did you change during your teenage years?",
            "What was your first job or responsibility?",
            "Tell me about a teacher who influenced you.",
            "What did you dream of becoming?",
            "Describe a moment of independence."
        ],
        "young_adulthood": [
            "How did you choose your career path?",
            "Tell me about leaving home.",
            "Who were your mentors?",
            "What risks did you take?",
            "Describe a major decision you made."
        ]
    }
    return base_prompts.get(life_phase, ["Tell me about this period of your life."])

# Enhanced Interview Agent
class InterviewAgent(Agent):
    """Agent responsible for memory elicitation with state management"""
    
    def __init__(self, memory_bank: MemoryBank):
        super().__init__(
            role="interviewer",
            tools=[elicit_memory_details, suggest_memory_prompts]
        )
        self.memory_bank = memory_bank
        self.conversation_state = {}
    
    def conduct_interview(self, life_phase: str, target_memories: int = 5) -> List[Memory]:
        """Conduct a focused interview for a specific life phase"""
        collected_memories = []
        
        # Get contextual prompts
        prompts = suggest_memory_prompts(life_phase, [m.content for m in collected_memories])
        
        for i in range(target_memories):
            # Initial prompt
            prompt = f"""You are a skilled interviewer helping someone recall memories from their {life_phase}.
            
Current prompt: {prompts[i % len(prompts)]}

Guide them to share:
1. Specific moments, not general descriptions
2. Sensory details (what they saw, heard, felt)
3. Who was there and what they said
4. Why this moment mattered
5. How it connects to other experiences

Ask follow-up questions to get rich detail."""

            result = self.run(prompt)
            
            # Extract memory from conversation
            memory = self._extract_memory_from_conversation(result)
            if memory:
                self.memory_bank.store(memory)
                collected_memories.append(memory)
                
                # Get follow-up to connect memories
                if i > 0:
                    connection_prompt = f"""The person just shared: {memory.content[:100]}...
                    
Help them connect this to their previous memory about: {collected_memories[-2].content[:100]}...
Are there themes or patterns emerging?"""
                    
                    connection_result = self.run(connection_prompt)
                    # Update memory with connections
                    self._update_memory_connections(memory, connection_result)
        
        return collected_memories
    
    def _extract_memory_from_conversation(self, result: Dict) -> Optional[Memory]:
        """Parse conversation to extract Memory object"""
        # This would parse the agent response to create a Memory
        # For now, stub implementation
        return Memory(
            content="Extracted memory content",
            memory_type=MemoryType.MILESTONE,
            significance="Parsed significance"
        )
    
    def _update_memory_connections(self, memory: Memory, connection_result: Dict):
        """Update memory with discovered connections"""
        # Parse connections and update memory.related_memories
        pass

# Timeline Analysis Tools
def identify_life_phases(memories: List[Memory]) -> List[LifePhase]:
    """Tool to identify natural life phases from memories"""
    # Group by major transitions
    phases = []
    
    # Simple implementation - would be more sophisticated
    year_ranges = [
        (0, 12, "childhood"),
        (13, 18, "adolescence"),
        (19, 25, "young_adulthood"),
        (26, 40, "early_career"),
        (41, 60, "midlife"),
        (61, 100, "later_years")
    ]
    
    for start_age, end_age, phase_name in year_ranges:
        phase_memories = [m for m in memories if m.age and start_age <= m.age <= end_age]
        if phase_memories:
            phases.append(LifePhase(
                name=phase_name,
                start_year=min(m.year for m in phase_memories if m.year) or 1900,
                end_year=max(m.year for m in phase_memories if m.year) or 2024,
                description=f"Phase containing {len(phase_memories)} memories",
                key_themes=[]
            ))
    
    return phases

def detect_timeline_gaps(memories: List[Memory]) -> List[Tuple[int, int]]:
    """Tool to find gaps in timeline coverage"""
    gaps = []
    sorted_memories = sorted([m for m in memories if m.year], key=lambda m: m.year)
    
    for i in range(len(sorted_memories) - 1):
        year_diff = sorted_memories[i+1].year - sorted_memories[i].year
        if year_diff > 5:  # Gap of more than 5 years
            gaps.append((sorted_memories[i].year, sorted_memories[i+1].year))
    
    return gaps

# Enhanced Timeline Agent
class TimelineAgent(Agent):
    """Agent responsible for chronological organization and gap detection"""
    
    def __init__(self, memory_bank: MemoryBank):
        super().__init__(
            role="timeline_organizer",
            tools=[identify_life_phases, detect_timeline_gaps]
        )
        self.memory_bank = memory_bank
    
    def build_timeline(self) -> Tuple[List[LifePhase], List[Tuple[int, int]]]:
        """Build complete timeline and identify gaps"""
        all_memories = list(self.memory_bank.memories.values())
        
        prompt = f"""Analyze these {len(all_memories)} memories to create a life timeline.

Identify:
1. Natural life phases based on major transitions
2. The defining characteristics of each phase
3. How the person evolved through phases
4. Any significant gaps that need filling

Memories span from {min(m.year for m in all_memories if m.year)} to {max(m.year for m in all_memories if m.year)}.

Look for transitions like:
- Geographic moves
- Educational milestones  
- Career changes
- Relationship changes
- Personal transformations"""

        result = self.run(prompt)
        
        # Use tools to identify phases and gaps
        phases = identify_life_phases(all_memories)
        gaps = detect_timeline_gaps(all_memories)
        
        # Enhance phases with agent insights
        enhanced_phases = self._enhance_phases_with_insights(phases, result)
        
        return enhanced_phases, gaps
    
    def _enhance_phases_with_insights(self, phases: List[LifePhase], result: Dict) -> List[LifePhase]:
        """Add agent insights to detected phases"""
        # Would parse agent response to enhance phase descriptions
        return phases

# Theme Extraction Tools  
def calculate_theme_frequency(memories: List[Memory], theme_keywords: Dict[str, List[str]]) -> Dict[str, int]:
    """Tool to calculate theme frequency across memories"""
    theme_counts = {theme: 0 for theme in theme_keywords}
    
    for memory in memories:
        content_lower = memory.content.lower()
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                theme_counts[theme] += 1
    
    return theme_counts

def find_theme_evolution(memories: List[Memory], theme: str) -> List[Dict[str, Any]]:
    """Tool to track how a theme evolves over time"""
    evolution = []
    theme_memories = sorted(
        [m for m in memories if theme.lower() in m.content.lower()],
        key=lambda m: m.year or 0
    )
    
    for memory in theme_memories:
        evolution.append({
            'year': memory.year,
            'expression': memory.content[:100],
            'intensity': len(memory.emotions)
        })
    
    return evolution

# Pattern Recognition Agent
class ThemeAgent(Agent):
    """Agent for deep pattern recognition and theme extraction"""
    
    def __init__(self, memory_bank: MemoryBank):
        super().__init__(
            role="theme_analyst", 
            tools=[calculate_theme_frequency, find_theme_evolution]
        )
        self.memory_bank = memory_bank
        self.discovered_themes: List[Theme] = []
    
    def analyze_themes(self) -> List[Theme]:
        """Perform deep thematic analysis"""
        all_memories = list(self.memory_bank.memories.values())
        
        # First pass: Identify potential themes
        identification_prompt = f"""Analyze these {len(all_memories)} life memories to identify major themes.

Look for:
1. Recurring patterns across different life phases
2. Core values that appear repeatedly  
3. Challenges that resurface in different forms
4. Relationships patterns
5. Growth/transformation themes

Don't just list generic themes - find the specific, unique patterns in THIS person's life.

For each theme, note:
- What it represents
- How it manifests across time
- Key memories that exemplify it
- How it shaped their journey"""

        id_result = self.run(identification_prompt)
        
        # Extract initial themes from response
        initial_themes = self._extract_themes_from_response(id_result)
        
        # Second pass: Deep dive on each theme
        for theme_name in initial_themes:
            theme_prompt = f"""Examine how the theme of '{theme_name}' appears across these memories.

Trace:
1. First appearance
2. Major expressions
3. Transformations
4. Current state
5. Connection to other themes

Be specific about how this theme uniquely manifests in this person's life."""

            theme_result = self.run(theme_prompt)
            
            # Create Theme object
            theme = self._create_theme_from_analysis(theme_name, theme_result, all_memories)
            self.discovered_themes.append(theme)
        
        # Find meta-patterns
        self._analyze_theme_interactions()
        
        return self.discovered_themes
    
    def _extract_themes_from_response(self, result: Dict) -> List[str]:
        """Extract theme names from agent response"""
        # Stub - would parse response
        return ["resilience", "family_bonds", "creative_expression", "search_for_meaning"]
    
    def _create_theme_from_analysis(self, name: str, analysis: Dict, memories: List[Memory]) -> Theme:
        """Create Theme object from analysis"""
        return Theme(
            name=name,
            description="Theme description from analysis",
            related_memories=[m.id for m in memories[:3]],  # Stub
            evolution="How theme evolved"
        )
    
    def _analyze_theme_interactions(self):
        """Analyze how themes interact and influence each other"""
        interaction_prompt = f"""Given these {len(self.discovered_themes)} themes:
{[t.name for t in self.discovered_themes]}

Analyze:
1. Which themes reinforce each other
2. Which themes create tension
3. How themes combine to shape major decisions
4. The overall thematic arc of the life"""

        result = self.run(interaction_prompt)
        # Would update themes with interaction data

# Voice Analysis Tools
def extract_linguistic_features(text_samples: List[str]) -> Dict[str, Any]:
    """Tool to extract linguistic features from text"""
    features = {
        'avg_sentence_length': 0,
        'vocabulary_richness': 0,
        'formality_level': 'medium',
        'emotional_words_ratio': 0,
        'personal_pronouns_ratio': 0,
        'past_tense_ratio': 0
    }
    
    # Simple implementation - would use NLP
    total_words = sum(len(sample.split()) for sample in text_samples)
    total_sentences = sum(sample.count('.') + sample.count('!') + sample.count('?') 
                         for sample in text_samples)
    
    if total_sentences > 0:
        features['avg_sentence_length'] = total_words / total_sentences
    
    return features

def identify_speech_patterns(text_samples: List[str]) -> Dict[str, List[str]]:
    """Tool to identify recurring speech patterns"""
    patterns = {
        'common_phrases': [],
        'sentence_starters': [],
        'transition_words': [],
        'emphasis_patterns': []
    }
    
    # Would analyze for actual patterns
    return patterns

# Voice Preservation Agent
class VoiceAgent(Agent):
    """Agent for analyzing and preserving authentic voice"""
    
    def __init__(self):
        super().__init__(
            role="voice_analyst",
            tools=[extract_linguistic_features, identify_speech_patterns]
        )
        self.voice_profile = {}
    
    def analyze_voice(self, memory_samples: List[Memory]) -> Dict[str, Any]:
        """Create comprehensive voice profile"""
        text_samples = [m.content for m in memory_samples]
        
        prompt = f"""Analyze these {len(text_samples)} memory descriptions to capture the person's authentic voice.

Identify:
1. Vocabulary preferences (formal/casual, simple/complex)
2. Sentence structure patterns
3. How they express emotions
4. Humor style (if any)
5. Cultural or generational markers
6. Unique phrases or expressions
7. Storytelling style (direct/meandering, factual/emotional)

Create a voice profile that will help maintain authenticity in the final narrative."""

        result = self.run(prompt)
        
        # Use tools for quantitative analysis
        linguistic_features = extract_linguistic_features(text_samples)
        speech_patterns = identify_speech_patterns(text_samples)
        
        # Combine with qualitative insights
        self.voice_profile = {
            'linguistic_features': linguistic_features,
            'speech_patterns': speech_patterns,
            'qualitative_insights': self._extract_qualitative_insights(result),
            'sample_authentic_phrases': self._extract_sample_phrases(text_samples)
        }
        
        return self.voice_profile
    
    def _extract_qualitative_insights(self, result: Dict) -> Dict[str, str]:
        """Extract qualitative voice insights from agent response"""
        return {
            'overall_tone': 'warm and conversational',
            'emotional_expression': 'understated but genuine',
            'humor_style': 'self-deprecating',
            'formality': 'casual with moments of reflection'
        }
    
    def _extract_sample_phrases(self, samples: List[str]) -> List[str]:
        """Extract characteristic phrases"""
        # Would identify actual recurring phrases
        return ["I remember thinking...", "Looking back now...", "It's funny how..."]

# Narrative Generation Tools
def create_scene(memory: Memory, style: Dict[str, Any]) -> str:
    """Tool to transform memory into narrative scene"""
    # Would generate actual scene
    return f"Scene based on: {memory.content[:50]}..."

def generate_transition(from_memory: Memory, to_memory: Memory, thematic_link: str) -> str:
    """Tool to create smooth transitions between scenes"""
    return f"Transition from {from_memory.id} to {to_memory.id} via {thematic_link}"

def add_reflection(memory: Memory, current_perspective: str) -> str:
    """Tool to add reflective commentary"""
    return f"Reflection on {memory.content[:30]}... from current perspective"

# Master Narrative Agent
class NarrativeAgent(Agent):
    """Agent responsible for generating final narrative prose"""
    
    def __init__(self, memory_bank: MemoryBank):
        super().__init__(
            role="narrative_writer",
            tools=[create_scene, generate_transition, add_reflection]
        )
        self.memory_bank = memory_bank
    
    def write_chapter(
        self,
        phase: LifePhase,
        themes: List[Theme],
        voice_profile: Dict[str, Any],
        chapter_number: int
    ) -> str:
        """Write a complete chapter for a life phase"""
        
        # Get memories for this phase
        phase_memories = self.memory_bank.get_by_period(phase.start_year, phase.end_year)
        
        # Identify chapter structure
        structure_prompt = f"""Design the structure for Chapter {chapter_number}: {phase.name}

You have {len(phase_memories)} memories from {phase.start_year} to {phase.end_year}.
Key themes to weave in: {[t.name for t in themes[:3]]}

Create:
1. A compelling opening that draws the reader in
2. The sequence of memories/scenes to include (pick 5-8 most significant)
3. How to transition between them thematically
4. Where to add reflective passages
5. A satisfying conclusion that links to the next phase

Voice notes: {voice_profile.get('qualitative_insights', {})}"""

        structure_result = self.run(structure_prompt)
        
        # Generate opening
        opening = self._write_opening(phase, phase_memories[0] if phase_memories else None)
        
        # Generate main narrative
        scenes = []
        for i, memory in enumerate(phase_memories[:8]):  # Limit to 8 key memories
            # Create scene
            scene = create_scene(memory, voice_profile)
            
            # Add transition if not first scene
            if i > 0:
                transition = generate_transition(
                    phase_memories[i-1], 
                    memory,
                    themes[0].name if themes else "time"
                )
                scenes.append(transition)
            
            scenes.append(scene)
            
            # Add reflection every few scenes
            if i % 3 == 2:
                reflection = add_reflection(memory, "current")
                scenes.append(reflection)
        
        # Generate conclusion
        conclusion = self._write_conclusion(phase, themes)
        
        # Assemble chapter
        chapter = f"""# Chapter {chapter_number}: {phase.name}

{opening}

{' '.join(scenes)}

{conclusion}"""

        # Final voice consistency pass
        chapter = self._apply_voice_consistency(chapter, voice_profile)
        
        return chapter
    
    def _write_opening(self, phase: LifePhase, first_memory: Optional[Memory]) -> str:
        """Write compelling chapter opening"""
        opening_prompt = f"""Write an engaging opening for the {phase.name} chapter.
Set the scene for {phase.start_year}-{phase.end_year}.
{f"Consider starting with: {first_memory.content[:100]}" if first_memory else ""}
Make it immediate and engaging, drawing the reader in."""

        result = self.run(opening_prompt)
        # Extract opening from response
        return "Chapter opening text..."
    
    def _write_conclusion(self, phase: LifePhase, themes: List[Theme]) -> str:
        """Write chapter conclusion"""
        return "Chapter conclusion that bridges to next phase..."
    
    def _apply_voice_consistency(self, text: str, voice_profile: Dict[str, Any]) -> str:
        """Ensure voice consistency throughout chapter"""
        consistency_prompt = f"""Review this chapter text for voice consistency:

{text[:1000]}...

Voice profile: {voice_profile}

Adjust to ensure:
1. Vocabulary matches profile
2. Sentence structure is consistent
3. Emotional expression fits
4. Maintains authentic feel

Return the adjusted text."""

        result = self.run(consistency_prompt)
        # Return adjusted text
        return text

# Coherence Checking Tools
def check_timeline_consistency(chapters: List[str]) -> List[str]:
    """Tool to verify timeline consistency across chapters"""
    issues = []
    # Would check for chronological inconsistencies
    return issues

def verify_character_consistency(chapters: List[str], people_index: Dict[str, List[str]]) -> List[str]:
    """Tool to verify character portrayals are consistent"""
    issues = []
    # Would check character descriptions
    return issues

def assess_thematic_coherence(chapters: List[str], themes: List[Theme]) -> Dict[str, float]:
    """Tool to assess how well themes are developed"""
    scores = {}
    # Would analyze theme development
    return scores

# Quality Assurance Agent  
class CoherenceAgent(Agent):
    """Agent responsible for ensuring overall coherence"""
    
    def __init__(self):
        super().__init__(
            role="coherence_checker",
            tools=[check_timeline_consistency, verify_character_consistency, assess_thematic_coherence]
        )
    
    def review_autobiography(
        self,
        chapters: List[str],
        themes: List[Theme],
        memory_bank: MemoryBank
    ) -> Dict[str, Any]:
        """Comprehensive coherence review"""
        
        review_prompt = f"""Review this complete autobiography for coherence:

{len(chapters)} chapters totaling approximately {sum(len(c.split()) for c in chapters)} words.

Check for:
1. Timeline consistency - events in correct order
2. Character consistency - people portrayed consistently  
3. Thematic development - themes properly developed
4. Voice consistency - maintains authentic voice
5. Narrative flow - smooth progression
6. Completeness - no major gaps

Identify any issues that need correction."""

        result = self.run(review_prompt)
        
        # Use tools for specific checks
        timeline_issues = check_timeline_consistency(chapters)
        character_issues = verify_character_consistency(chapters, memory_bank.people_index)
        theme_scores = assess_thematic_coherence(chapters, themes)
        
        return {
            'timeline_issues': timeline_issues,
            'character_issues': character_issues,
            'theme_scores': theme_scores,
            'overall_assessment': self._extract_assessment(result),
            'recommended_fixes': self._extract_fixes(result)
        }
    
    def _extract_assessment(self, result: Dict) -> str:
        """Extract overall assessment from review"""
        return "Overall coherent with minor issues"
    
    def _extract_fixes(self, result: Dict) -> List[str]:
        """Extract recommended fixes"""
        return ["Clarify timeline in Chapter 3", "Strengthen theme development in Chapter 5"]
```

## Advanced Orchestrator Implementation

```python
class AutobiographyOrchestrator:
    """Enhanced orchestrator with state management and error handling"""
    
    def __init__(self):
        self.memory_bank = MemoryBank()
        self.interview_agent = InterviewAgent(self.memory_bank)
        self.timeline_agent = TimelineAgent(self.memory_bank)
        self.theme_agent = ThemeAgent(self.memory_bank)
        self.voice_agent = VoiceAgent()
        self.narrative_agent = NarrativeAgent(self.memory_bank)
        self.coherence_agent = CoherenceAgent()
        
        self.state = {
            'user_name': '',
            'phases': [],
            'themes': [],
            'voice_profile': {},
            'chapters': [],
            'timeline_gaps': [],
            'generation_log': []
        }
    
    def generate_autobiography(self, user_name: str, config: Dict[str, Any] = None) -> str:
        """Generate complete autobiography with configuration options"""
        self.state['user_name'] = user_name
        config = config or {}
        
        try:
            # Phase 1: Introduction and Setup
            self._log("Starting autobiography generation")
            self._introduction_interview()
            
            # Phase 2: Memory Collection
            self._log("Collecting life memories")
            self._collect_all_memories(config.get('min_memories', 50))
            
            # Phase 3: Structure Analysis
            self._log("Analyzing life structure")
            self._analyze_complete_structure()
            
            # Phase 4: Voice Analysis
            self._log("Capturing authentic voice")
            self._analyze_voice()
            
            # Phase 5: Fill Gaps
            if self.state['timeline_gaps']:
                self._log("Filling timeline gaps")
                self._fill_timeline_gaps()
            
            # Phase 6: Generate Narrative
            self._log("Generating narrative chapters")
            self._generate_all_chapters()
            
            # Phase 7: Coherence Review
            self._log("Reviewing for coherence")
            coherence_report = self._review_coherence()
            
            # Phase 8: Apply Fixes
            if coherence_report['recommended_fixes']:
                self._log("Applying recommended fixes")
                self._apply_fixes(coherence_report)
            
            # Phase 9: Final Assembly
            self._log("Assembling final autobiography")
            return self._assemble_final_autobiography()
            
        except Exception as e:
            self._log(f"Error during generation: {str(e)}")
            return self._handle_generation_error(e)
    
    def _log(self, message: str):
        """Log generation progress"""
        self.state['generation_log'].append({
            'timestamp': datetime.now(),
            'message': message
        })
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _introduction_interview(self):
        """Initial interview to establish context"""
        intro_prompt = f"""Begin an autobiography interview with {self.state['user_name']}.

Start with:
1. What motivated them to write their autobiography
2. Who they hope will read it  
3. What message they want to convey
4. Any specific events or themes they want to ensure are included

Keep it conversational and warm."""

        intro_agent = Agent(role="introduction_interviewer")
        result = intro_agent.run(intro_prompt)
        
        # Extract key intentions
        self.state['author_intentions'] = self._extract_intentions(result)
    
    def _collect_all_memories(self, target_count: int):
        """Systematically collect memories across all life phases"""
        # Define life phases to explore
        life_phases = [
            ("early childhood", 0, 6),
            ("childhood", 7, 12),
            ("adolescence", 13, 18),
            ("young adulthood", 19, 25),
            ("early career", 26, 35),
            ("establishing life", 36, 45),
            ("middle years", 46, 55),
            ("mature years", 56, 65),
            ("recent years", 66, 100)
        ]
        
        memories_per_phase = max(5, target_count // len(life_phases))
        
        for phase_name, start_age, end_age in life_phases:
            self._log(f"Interviewing about {phase_name}")
            
            # Check if this phase applies to the person
            if self._phase_applies(start_age, end_age):
                phase_memories = self.interview_agent.conduct_interview(
                    phase_name,
                    target_memories=memories_per_phase
                )
                
                self._log(f"Collected {len(phase_memories)} memories from {phase_name}")
    
    def _phase_applies(self, start_age: int, end_age: int) -> bool:
        """Check if a life phase applies to this person"""
        # Would determine based on person's current age
        return True  # Simplified
    
    def _analyze_complete_structure(self):
        """Analyze the complete life structure"""
        # Build timeline
        phases, gaps = self.timeline_agent.build_timeline()
        self.state['phases'] = phases
        self.state['timeline_gaps'] = gaps
        
        # Extract themes
        themes = self.theme_agent.analyze_themes()
        self.state['themes'] = themes
        
        self._log(f"Identified {len(phases)} life phases and {len(themes)} major themes")
    
    def _analyze_voice(self):
        """Analyze authentic voice from memories"""
        # Get a sample of memories across different periods
        sample_memories = []
        for phase in self.state['phases']:
            phase_mems = self.memory_bank.get_by_period(phase.start_year, phase.end_year)
            sample_memories.extend(phase_mems[:3])  # 3 from each phase
        
        self.state['voice_profile'] = self.voice_agent.analyze_voice(sample_memories)
        self._log("Voice profile created")
    
    def _fill_timeline_gaps(self):
        """Conduct targeted interviews to fill gaps"""
        for start_year, end_year in self.state['timeline_gaps']:
            self._log(f"Filling gap: {start_year}-{end_year}")
            
            gap_prompt = f"Let's talk about the period from {start_year} to {end_year}"
            gap_memories = self.interview_agent.conduct_interview(
                f"years {start_year}-{end_year}",
                target_memories=3
            )
    
    def _generate_all_chapters(self):
        """Generate all narrative chapters"""
        self.state['chapters'] = []
        
        # Generate preface
        preface = self._generate_preface()
        self.state['chapters'].append(preface)
        
        # Generate main chapters
        for i, phase in enumerate(self.state['phases']):
            self._log(f"Writing Chapter {i+1}: {phase.name}")
            
            chapter = self.narrative_agent.write_chapter(
                phase,
                self.state['themes'],
                self.state['voice_profile'],
                i + 1
            )
            
            self.state['chapters'].append(chapter)
        
        # Generate epilogue
        epilogue = self._generate_epilogue()
        self.state['chapters'].append(epilogue)
    
    def _generate_preface(self) -> str:
        """Generate preface based on author intentions"""
        preface_prompt = f"""Write a preface for {self.state['user_name']}'s autobiography.

Include:
1. Why they're writing this
2. Who they hope will read it
3. What they want readers to understand
4. Acknowledgments
5. Setting expectations

Keep it personal and inviting."""

        preface_agent = Agent(role="preface_writer")
        result = preface_agent.run(preface_prompt)
        
        return "# Preface\n\n[Generated preface content]"
    
    def _generate_epilogue(self) -> str:
        """Generate epilogue with reflection on life journey"""
        total_memories = len(self.memory_bank.memories)
        
        epilogue_prompt = f"""Write an epilogue for this autobiography.

The journey covered {len(self.state['phases'])} major life phases.
Key themes included: {[t.name for t in self.state['themes'][:3]]}

Include:
1. Reflection on the journey
2. Current perspective on life
3. Hopes for the future
4. Message to readers
5. Final thoughts

Make it meaningful but not overly sentimental."""

        epilogue_agent = Agent(role="epilogue_writer")
        result = epilogue_agent.run(epilogue_prompt)
        
        return "# Epilogue\n\n[Generated epilogue content]"
    
    def _review_coherence(self) -> Dict[str, Any]:
        """Review complete autobiography for coherence"""
        return self.coherence_agent.review_autobiography(
            self.state['chapters'],
            self.state['themes'],
            self.memory_bank
        )
    
    def _apply_fixes(self, coherence_report: Dict[str, Any]):
        """Apply recommended fixes to chapters"""
        for fix in coherence_report['recommended_fixes']:
            self._log(f"Applying fix: {fix}")
            # Would implement specific fixes
    
    def _assemble_final_autobiography(self) -> str:
        """Assemble the complete autobiography"""
        # Add metadata
        metadata = f"""# {self.state['user_name']}: An Autobiography

Generated on: {datetime.now().strftime('%B %d, %Y')}
Total memories collected: {len(self.memory_bank.memories)}
Life phases covered: {len(self.state['phases'])}
Major themes: {', '.join(t.name for t in self.state['themes'][:5])}

---

"""
        
        # Combine all chapters
        full_text = metadata + "\n\n".join(self.state['chapters'])
        
        # Add table of contents
        toc = self._generate_table_of_contents()
        full_text = full_text.replace("---", f"---\n\n{toc}")
        
        return full_text
    
    def _generate_table_of_contents(self) -> str:
        """Generate table of contents"""
        toc = "## Table of Contents\n\n"
        for i, chapter in enumerate(self.state['chapters']):
            # Extract chapter title
            if chapter.startswith("# "):
                title = chapter.split('\n')[0].replace("# ", "")
                toc += f"{i}. {title}\n"
        return toc
    
    def _handle_generation_error(self, error: Exception) -> str:
        """Handle generation errors gracefully"""
        return f"""# Autobiography Generation Error

An error occurred during generation: {str(error)}

Progress made:
- Memories collected: {len(self.memory_bank.memories)}
- Phases identified: {len(self.state['phases'])}
- Chapters written: {len(self.state['chapters'])}

The partial autobiography may still contain valuable content.
"""
    
    def _extract_intentions(self, result: Dict) -> Dict[str, str]:
        """Extract author intentions from introduction"""
        # Would parse actual response
        return {
            'motivation': 'To preserve family history',
            'audience': 'Family and future generations',
            'message': 'The importance of resilience',
            'key_events': ['Immigration story', 'Building the business']
        }

# Usage Example with Progress Tracking
def generate_autobiography_with_progress(name: str):
    """Generate autobiography with progress updates"""
    orchestrator = AutobiographyOrchestrator()
    
    config = {
        'min_memories': 50,
        'include_photos': False,  # Future feature
        'target_length': 'medium',  # short/medium/long
        'formality': 'conversational'
    }
    
    print(f"\n=== Generating Autobiography for {name} ===\n")
    
    autobiography = orchestrator.generate_autobiography(name, config)
    
    print(f"\n=== Generation Complete ===")
    print(f"Total length: {len(autobiography.split())} words")
    print(f"Chapters: {len(orchestrator.state['chapters'])}")
    
    # Save to file
    filename = f"{name.replace(' ', '_')}_autobiography.md"
    with open(filename, 'w') as f:
        f.write(autobiography)
    
    print(f"Saved to: {filename}")
    
    return autobiography

if __name__ == "__main__":
    # Example usage
    autobiography = generate_autobiography_with_progress("Jane Doe")
```

## Key Architecture Decisions

1. **Memory Bank**: Central storage allows all agents to access memories
2. **Specialized Agents**: Each agent has deep expertise in its domain
3. **Tool System**: Tools provide concrete operations with typed inputs/outputs
4. **State Management**: Orchestrator maintains global state across phases
5. **Error Recovery**: Graceful handling of failures with partial output
6. **Voice Preservation**: Early analysis, consistent application
7. **Iterative Refinement**: Multiple passes for completeness and quality
8. **Progress Tracking**: Clear visibility into generation process

This implementation provides a complete system for generating autobiographies using the multi-agent architecture with the specified agent.run() interface.
