# Experimental Protocol: Workflow Prompt Evolution

## Immediate Experiment Design

### The Control Variables
```python
# These stay constant across all experiments
THREE_PASS_SYSTEM = """
CRITICAL UNDERSTANDING: This workflow should be applied in THREE PASSES:

PASS 1 - CONCEPTUALIZE (Ontological/Universal Level):
- Question: "What IS the thing I'm designing?"
- Focus: Understanding the essential nature, components, and relationships
- Output: Complete ontological model of your domain

PASS 2 - GENERALLY REIFY (General/Class Level):
- Question: "How do I BUILD systems that create these things?"
- Focus: Designing the generator/factory/system that can produce instances
- Output: A system capable of creating domain instances

PASS 3 - SPECIFICALLY REIFY (Specific/Instance Level):
- Question: "How do I create THIS PARTICULAR instance?"
- Focus: Using the system to generate a specific instance
- Output: A concrete, specific instance
"""

TEST_DOMAINS = [
    "task management system",
    "recipe recommendation engine", 
    "workout tracking app",
    "language learning platform",
    "event planning system"
]
```

### Workflow Variations to Test

#### Variation 1: Simplified Linear
```
(0)[Goal]→(1)[Analysis]→(2)[Design]→(3)[Build]→(4)[Test]→(5)[Deploy]
```

#### Variation 2: Expanded Phases
```
(0)[AbstractGoal]→(1)[DomainAnalysis]→(2)[SystemsDesign]→(3)[Architecture]→
(4)[Implementation]→(5)[Testing]→(6)[Deployment]→(7)[Monitoring]→(8)[Evolution]→loop→(0)
```

#### Variation 3: Parallel Paths
```
(0)[Goal]→
├─(1a)[UserNeeds]→(2a)[UXDesign]→(3a)[Frontend]
├─(1b)[DataNeeds]→(2b)[DataDesign]→(3b)[Backend]  
└─(1c)[SystemNeeds]→(2c)[Architecture]→(3c)[Infrastructure]
→(4)[Integration]→(5)[Testing]→(6)[Feedback]→loop→(0)
```

#### Variation 4: Ontology-First
```
(0)[Domain]→(1)[Ontology]→(2)[Relationships]→(3)[Behaviors]→
(4)[Patterns]→(5)[Implementation]→(6)[Validation]→loop→(0)
```

#### Variation 5: Recursive Native
```
(0)[AbstractGoal]→(1)[Decompose→{
    if(Atomic): →(2)[Implement]
    else: →(0)[SubGoal]
}]→(3)[Compose]→(4)[Validate]→(5)[Evolve]→loop→(0)
```

### Evaluation Metrics

#### Quantitative
1. **Time to First Design** - How quickly does coherent design emerge?
2. **Completeness Score** - Coverage of necessary system aspects (0-100)
3. **Code Quality** - Does Pass 2 generate working code?
4. **Abstraction Level** - How well does Pass 1 avoid implementation?

#### Qualitative
1. **Insight Depth** - Novel realizations during process
2. **Recursion Recognition** - Does it discover meta-patterns?
3. **Clarity of Output** - How understandable is the result?
4. **Evolutionary Potential** - Can Pass 3 outputs become new types?

### Experiment Run Protocol

```python
def run_experiment(workflow_variant, domain):
    prompt = f"""
{workflow_variant}

{THREE_PASS_SYSTEM}

Now, begin with Phase 0 of Pass 1 by designing a {domain}.
"""
    
    # Start timer
    start_time = time.now()
    
    # Get Claude's response
    response = claude.complete(prompt, max_tokens=8000)
    
    # Measure results
    results = {
        'time_to_design': measure_design_emergence(response),
        'completeness': score_completeness(response),
        'code_quality': test_generated_code(response),
        'abstraction_maintenance': check_pass1_abstraction(response),
        'insights': extract_insights(response),
        'meta_patterns': find_meta_discoveries(response),
        'clarity': score_clarity(response),
        'evolutionary_potential': assess_evolution(response)
    }
    
    return results
```

### Quick Experiment (Do This First!)

1. Take the baseline workflow
2. Run it on "task management system"
3. Document what happens
4. Try Variation 4 (Ontology-First) on same domain
5. Compare results

### Hypothesis for Each Variation

**Baseline**: Good all-around performance, produces the kind of results we've seen

**Variation 1 (Simplified)**: Faster but less depth, might miss meta-insights

**Variation 2 (Expanded)**: More thorough but might overwhelm or slow down

**Variation 3 (Parallel)**: Better for complex systems but might confuse Pass 1/2 distinction

**Variation 4 (Ontology-First)**: Stronger Pass 1 but might struggle with Pass 2/3 transition

**Variation 5 (Recursive)**: Could discover deeper patterns but might get stuck in loops

### Data Collection Template

```markdown
## Experiment: [Workflow Name] on [Domain]

### Pass 1 Observations
- Time to complete: ___
- Abstraction quality: ___
- Key insights: ___

### Pass 2 Observations  
- Code generated: Y/N
- Code quality: ___
- System completeness: ___

### Pass 3 Observations
- Instance quality: ___
- Configuration depth: ___
- Emergent properties: ___

### Meta-Observations
- Recursive insights: ___
- Self-application: ___
- Unexpected discoveries: ___

### Overall Score: ___/100
```

## Next Experiments

Once we have baseline data:

1. **Hybrid Approaches** - Combine successful elements
2. **Prompt Injection** - Add specific instructions to workflow
3. **Domain-Specific Tuning** - Optimize for particular problem types
4. **Meta-Evolution** - Use results to generate new variations
5. **Cross-Validation** - Test winning variants on new domains

## The Big Question

Will we discover a workflow structure that consistently outperforms the original? Or will we find that different structures excel at different tasks?

Either result advances our understanding of how to augment LLM capabilities.

---

*Start with one experiment. Document everything. The evolution begins now.*