# Research System Interface Design

## Core API

```python
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ResearchResult:
    """Results from a single research run"""
    system_id: str
    parent_id: Optional[str]
    timestamp: datetime
    
    # Inputs
    description: str
    workflow: str
    
    # Research process
    hypothesis: str
    methodology: str
    
    # 3-Pass outputs
    pass1_output: str  # Ontology
    pass2_output: str  # Generator code
    pass3_output: str  # Instance
    
    # Analysis
    quality_scores: Dict[str, float]
    conclusions: str
    insights: List[str]
    suggested_next_steps: List[str]
    
    # Evolution tracking
    changes_from_parent: Optional[Dict[str, str]]
    improvement_delta: Optional[float]
    generation: int

class ResearchSystem:
    def __init__(self, llm_client, storage_path="./research_results"):
        self.llm = llm_client
        self.storage = ResearchStorage(storage_path)
        self.three_pass_system = ThreePassSystem(llm_client)
        self.analyzer = ResultAnalyzer(llm_client)
        self.evolver = WorkflowEvolver(llm_client)
    
    def run(self, 
            description: Optional[str] = None,
            workflow: Optional[str] = None,
            system_id: Optional[str] = None) -> ResearchResult:
        """
        Run a research experiment.
        
        Args:
            description: What system to build (required for new systems)
            workflow: Custom workflow to test (optional)
            system_id: ID of existing system to evolve (optional)
            
        Returns:
            ResearchResult with all findings
        """
        
        # Load or initialize
        if system_id:
            parent = self.storage.load(system_id)
            description = description or parent.description
            workflow = workflow or self._evolve_workflow(parent)
            hypothesis = self._generate_evolution_hypothesis(parent)
            generation = parent.generation + 1
        else:
            if not description:
                raise ValueError("Description required for new system")
            parent = None
            workflow = workflow or self._default_workflow()
            hypothesis = self._generate_initial_hypothesis(description, workflow)
            generation = 0
        
        # Execute research
        result = self._execute_research(
            description=description,
            workflow=workflow,
            hypothesis=hypothesis,
            parent=parent,
            generation=generation
        )
        
        # Store and return
        self.storage.save(result)
        return result
    
    def _execute_research(self, **kwargs) -> ResearchResult:
        """Run the actual experiment"""
        # ... implementation
        
    def get_lineage(self, system_id: str) -> List[ResearchResult]:
        """Get full evolution history of a system"""
        return self.storage.get_lineage(system_id)
    
    def compare(self, system_id1: str, system_id2: str) -> Dict:
        """Compare two research results"""
        return self.analyzer.compare(
            self.storage.load(system_id1),
            self.storage.load(system_id2)
        )
    
    def suggest_experiments(self, system_id: str) -> List[Dict]:
        """Suggest next experiments based on results"""
        result = self.storage.load(system_id)
        return self.evolver.suggest_variations(result)
```

## Usage Examples

### Starting Fresh
```python
research = ResearchSystem(llm_client)

# Basic usage
result = research.run(
    description="recipe recommendation system"
)

print(f"System ID: {result.system_id}")
print(f"Hypothesis: {result.hypothesis}")
print(f"Quality Score: {result.quality_scores['overall']}")
print(f"Conclusions: {result.conclusions}")
print(f"Next steps: {result.suggested_next_steps}")
```

### Custom Workflow
```python
# Test a specific workflow structure
result = research.run(
    description="recipe recommendation system",
    workflow="(0)[Users]→(1)[Preferences]→(2)[Recipes]→(3)[Matching]→(4)[System]"
)
```

### Evolution
```python
# Evolve an existing system
result2 = research.run(system_id="recipe_rec_v1")

print(f"Evolution: {result2.parent_id} → {result2.system_id}")
print(f"Changes: {result2.changes_from_parent}")
print(f"Improvement: {result2.improvement_delta}")
```

### Research Analysis
```python
# Get full history
lineage = research.get_lineage("recipe_rec_v5")
for r in lineage:
    print(f"Gen {r.generation}: {r.workflow} (score: {r.quality_scores['overall']})")

# Compare versions
comparison = research.compare("recipe_rec_v3", "recipe_rec_v5")
print(comparison['improvements'])
print(comparison['regressions'])

# Get suggestions
suggestions = research.suggest_experiments("recipe_rec_v5")
for s in suggestions:
    print(f"Try: {s['workflow']} because {s['rationale']}")
```

## Internal Architecture

### Hypothesis Generation
```python
class HypothesisGenerator:
    def generate_initial(self, description: str, workflow: str) -> str:
        prompt = f"""
        We're testing this workflow structure:
        {workflow}
        
        For building: {description}
        
        Generate a hypothesis about how well this workflow will work.
        Consider:
        - Match between workflow phases and domain needs
        - Completeness of the workflow
        - Potential challenges
        """
        return self.llm.complete(prompt)
    
    def generate_evolution(self, parent: ResearchResult) -> str:
        prompt = f"""
        Previous experiment:
        - Workflow: {parent.workflow}
        - Conclusions: {parent.conclusions}
        - Suggested improvements: {parent.suggested_next_steps}
        
        Generate a hypothesis for the next evolution.
        What specific improvement do we expect?
        """
        return self.llm.complete(prompt)
```

### Workflow Evolution
```python
class WorkflowEvolver:
    def evolve(self, parent: ResearchResult) -> str:
        """Generate evolved workflow based on parent's conclusions"""
        
        strategies = self._select_evolution_strategies(parent)
        
        # Apply strategies
        new_workflow = parent.workflow
        for strategy in strategies:
            new_workflow = self._apply_strategy(new_workflow, strategy)
            
        return new_workflow
    
    def _select_evolution_strategies(self, parent: ResearchResult) -> List[str]:
        """Pick evolution strategies based on conclusions"""
        if "confusion" in parent.conclusions.lower():
            return ["add_clarification_phase", "simplify_language"]
        elif "missing" in parent.conclusions.lower():
            return ["add_phase", "expand_existing_phase"]
        # ... more rules
```

### Quality Analysis
```python
class ResultAnalyzer:
    def analyze(self, result: ThreePassResult) -> Dict[str, float]:
        """Score the quality of outputs"""
        return {
            'overall': self._score_overall(result),
            'pass1_abstraction': self._score_abstraction_quality(result.pass1),
            'pass2_completeness': self._score_code_completeness(result.pass2),
            'pass3_functionality': self._score_instance_quality(result.pass3),
            'coherence': self._score_cross_pass_coherence(result),
            'insights': self._count_novel_insights(result)
        }
    
    def generate_conclusions(self, 
                           result: ThreePassResult, 
                           scores: Dict[str, float],
                           parent: Optional[ResearchResult]) -> str:
        """Generate research conclusions"""
        prompt = f"""
        Analyze this research result:
        
        Workflow tested: {workflow}
        Scores: {scores}
        
        Pass 1 output: {result.pass1[:500]}...
        Pass 2 output: {result.pass2[:500]}...
        Pass 3 output: {result.pass3[:500]}...
        
        {f"Compared to parent: {parent.scores}" if parent else ""}
        
        Generate conclusions about:
        1. How well the workflow performed
        2. Specific strengths and weaknesses
        3. What could be improved
        4. Surprising findings
        """
        return self.llm.complete(prompt)
```

## Storage Format

```json
{
  "system_id": "recipe_rec_v3",
  "parent_id": "recipe_rec_v2",
  "timestamp": "2024-01-20T10:30:00Z",
  "generation": 3,
  
  "input": {
    "description": "recipe recommendation system",
    "workflow": "(0)[Users]→(1)[Tastes]→(2)[Recipes]→(3)[Matching]→(4)[System]"
  },
  
  "research": {
    "hypothesis": "Adding explicit Tastes phase will improve preference modeling",
    "methodology": "3-pass system with evolved workflow"
  },
  
  "outputs": {
    "pass1": "A recipe recommendation system IS...",
    "pass2": "class RecipeRecommender:...",
    "pass3": "recommender = RecipeRecommender(..."
  },
  
  "analysis": {
    "scores": {
      "overall": 87,
      "pass1_abstraction": 92,
      "pass2_completeness": 85,
      "pass3_functionality": 84
    },
    "conclusions": "The Tastes phase significantly improved...",
    "insights": [
      "Separating user preferences from recipes enabled clearer modeling",
      "The workflow naturally led to a modular architecture"
    ],
    "next_steps": [
      "Consider adding a Learning phase for preference evolution",
      "Try parallel paths for user/recipe processing"
    ]
  },
  
  "evolution": {
    "changes": {
      "added_phases": ["Tastes"],
      "modified_phases": {"Preferences": "Split into Users and Tastes"}
    },
    "improvement": 12
  }
}
```

## CLI Interface

```bash
# Start new research
$ research run --description "social network"

# Evolve existing
$ research evolve recipe_rec_v3

# View lineage
$ research history recipe_rec_v5

# Compare versions
$ research compare recipe_rec_v1 recipe_rec_v5

# Get suggestions
$ research suggest recipe_rec_v5

# Export results
$ research export recipe_rec_v5 --format markdown
```

## Web Dashboard

```
Research Dashboard
├── Active Experiments
│   ├── recipe_rec_v5 [Running...]
│   └── task_mgr_v2 [Complete]
├── Evolution Trees
│   ├── Recipe Recommender
│   │   ├── v1 (score: 75)
│   │   ├── v2 (score: 81) [+6]
│   │   ├── v3 (score: 87) [+6]
│   │   └── v4 (score: 89) [+2]
│   └── Task Manager
│       └── ...
├── Analytics
│   ├── Best Workflows by Domain
│   ├── Common Evolution Patterns
│   └── Success Metrics Over Time
└── Insights
    ├── Discovered Patterns
    ├── Workflow Templates
    └── Domain-Specific Learnings
```

This design gives us:
1. **Clean API** for running experiments
2. **Automatic evolution** based on conclusions
3. **Full tracking** of lineage and improvements
4. **Scientific rigor** with hypotheses and conclusions
5. **Practical insights** that accumulate over time