# Quick Start: Build This in Stages

## Start Simple: Proof of Concept in 1 Day

### Step 1: Hardcoded 3-Pass System (2 hours)
```python
import openai  # or anthropic

class SimpleThreePass:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.workflow = "(0)[Goal]→(1)[Design]→(2)[Build]→(3)[Test]"
        
    def pass1(self, domain):
        prompt = f"""
        {self.workflow}
        
        Pass 1: CONCEPTUALIZE
        What IS a {domain}? Focus on essential nature, not implementation.
        """
        return self.llm.complete(prompt)
    
    def pass2(self, domain, ontology):
        prompt = f"""
        {self.workflow}
        
        Pass 2: GENERALLY REIFY
        Given this ontology: {ontology}
        
        Design a system that can CREATE {domain} instances.
        Include actual code.
        """
        return self.llm.complete(prompt)
    
    def pass3(self, domain, generator_code):
        prompt = f"""
        {self.workflow}
        
        Pass 3: SPECIFICALLY REIFY
        Given this generator: {generator_code}
        
        Create a SPECIFIC instance of {domain}.
        """
        return self.llm.complete(prompt)

# Test it!
system = SimpleThreePass(llm_client)
ontology = system.pass1("task manager")
generator = system.pass2("task manager", ontology)
instance = system.pass3("task manager", generator)
```

### Step 2: Make Workflow Variable (1 hour)
```python
class VariableThreePass(SimpleThreePass):
    def set_workflow(self, new_workflow):
        self.workflow = new_workflow
        
# Test different workflows
workflows = [
    "(0)[Goal]→(1)[Design]→(2)[Build]→(3)[Test]",
    "(0)[Domain]→(1)[Ontology]→(2)[System]→(3)[Instance]",
    "(0)[What]→(1)[Why]→(2)[How]→(3)[Do]"
]

for w in workflows:
    system.set_workflow(w)
    result = system.pass1("task manager")
    print(f"Workflow: {w}\nResult quality: {score(result)}\n")
```

### Step 3: Add Basic Evolution (2 hours)
```python
import random

def mutate_workflow(workflow):
    # Simple mutations
    variations = [
        workflow.replace("Design", "Analyze"),
        workflow.replace("Build", "Implement"),
        workflow + "→(4)[Evolve]",
        # etc.
    ]
    return random.choice(variations)

def evolve_workflows(initial, generations=10):
    current_best = initial
    best_score = 0
    
    for gen in range(generations):
        # Generate variants
        variants = [mutate_workflow(current_best) for _ in range(5)]
        
        # Test each
        scores = []
        for variant in variants:
            system.set_workflow(variant)
            result = system.pass1("task manager")
            scores.append(score_quality(result))
        
        # Keep best
        if max(scores) > best_score:
            best_idx = scores.index(max(scores))
            current_best = variants[best_idx]
            best_score = max(scores)
            print(f"Gen {gen}: New best! {current_best}")
    
    return current_best
```

## Next: Add Understanding Loop (Day 2)

### Step 4: Confusion Detection
```python
class UnderstandingThreePass(VariableThreePass):
    def detect_confusion(self, output):
        confusion_markers = [
            "I'm not sure",
            "unclear",
            "could mean",
            "ambiguous"
        ]
        return any(marker in output.lower() for marker in confusion_markers)
    
    def correct_confusion(self, domain, confused_output):
        prompt = f"""
        The system seems confused about {domain}.
        
        Output was: {confused_output}
        
        Let's clarify:
        1. What IS a {domain}? (not what it does)
        2. What are its essential properties?
        3. How is it different from similar things?
        """
        return self.llm.complete(prompt)
```

### Step 5: Integration
```python
class SmartThreePass(UnderstandingThreePass):
    def pass1_with_understanding(self, domain):
        output = self.pass1(domain)
        
        if self.detect_confusion(output):
            print("Confusion detected! Correcting...")
            clarification = self.correct_confusion(domain, output)
            # Re-run with clarification
            output = self.pass1(domain + f"\n\nClarification: {clarification}")
        
        return output
```

## Week 1 Milestone: Working Prototype

By end of week 1, you should have:
- ✅ Variable workflow system
- ✅ Basic evolution finding better workflows  
- ✅ Understanding loop handling confusion
- ✅ Measurable improvements over baseline

## The Power of Starting Small

1. **Day 1**: Get basic 3-pass working with variable workflows
2. **Day 2**: Add understanding loop
3. **Day 3**: Add basic evolution
4. **Day 4**: Measure and document findings
5. **Day 5**: Plan next improvements

## Key Insights We're Testing

1. **Do different workflows produce measurably different outputs?**
2. **Can evolution find better workflows automatically?**
3. **Does the understanding loop improve quality?**
4. **What patterns emerge from the best workflows?**

## Quick Experiments to Try

### Experiment 1: Domain Sensitivity
Test the same workflow on different domains:
- Task manager
- Recipe app
- Social network
- Game engine

Do certain workflows work better for certain domains?

### Experiment 2: Workflow Length
Test workflows of different lengths:
- 3 phases: `(0)→(1)→(2)`
- 5 phases: `(0)→(1)→(2)→(3)→(4)`
- 7 phases: `(0)→(1)→(2)→(3)→(4)→(5)→(6)`

Is there an optimal length?

### Experiment 3: Notation Style
Test different notation styles:
- Arrow style: `(0)[Goal]→(1)[Design]`
- Pipe style: `Goal | Design | Build`
- List style: `1. Goal\n2. Design\n3. Build`

Does notation affect LLM understanding?

## Remember

The goal isn't perfection on day 1. It's to:
1. Prove the concept works
2. Find interesting patterns
3. Build foundation for full system
4. Learn what matters most

Start with the simplest possible implementation and evolve from there.

*The system that evolves systems must itself evolve.*