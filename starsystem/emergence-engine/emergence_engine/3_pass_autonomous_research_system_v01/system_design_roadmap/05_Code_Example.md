# Code Example: The Core Concept

## What Makes This Different

### Traditional Approach (Hardcoded Workflow)
```python
class TraditionalSystemBuilder:
    def build_system(self, domain):
        # Workflow is baked into the code
        step1 = self.analyze_requirements(domain)
        step2 = self.design_architecture(step1)
        step3 = self.implement_system(step2)
        step4 = self.test_system(step3)
        return step4
```

### Our Approach (Variable Workflow)
```python
class EvolvingSystemBuilder:
    def __init__(self):
        # Workflow is a variable that can change!
        self.workflow = "(0)[Goal]→(1)[Design]→(2)[Build]→(3)[Test]"
        
    def build_system(self, domain):
        # Parse workflow and execute dynamically
        prompt = f"""
        Using this workflow: {self.workflow}
        
        Build a {domain} system.
        Follow each phase in order.
        """
        return self.llm.complete(prompt)
    
    def evolve_workflow(self):
        # Try different workflows and keep the best
        variants = [
            "(0)[Why]→(1)[What]→(2)[How]→(3)[Build]",
            "(0)[Domain]→(1)[Patterns]→(2)[System]→(3)[Instance]",
            "(0)[Problem]→(1)[Solution]→(2)[Implementation]",
            # ... many more variants
        ]
        
        best_score = 0
        best_workflow = self.workflow
        
        for variant in variants:
            self.workflow = variant
            result = self.build_system("test domain")
            score = self.evaluate_quality(result)
            
            if score > best_score:
                best_score = score
                best_workflow = variant
                
        self.workflow = best_workflow
        return best_workflow
```

## The Three-Pass Wrapper
```python
class ThreePassEvolvingBuilder(EvolvingSystemBuilder):
    def build_with_three_passes(self, domain):
        # Pass 1: Conceptualize
        pass1_prompt = f"""
        {self.workflow}
        
        PASS 1 - CONCEPTUALIZE: What IS a {domain}?
        Focus only on essential nature, not implementation.
        """
        ontology = self.llm.complete(pass1_prompt)
        
        # Pass 2: Generally Reify  
        pass2_prompt = f"""
        {self.workflow}
        
        PASS 2 - GENERALLY REIFY: How do we MAKE {domain} systems?
        Given this ontology: {ontology}
        
        Design a system that can create instances.
        Include actual code.
        """
        generator = self.llm.complete(pass2_prompt)
        
        # Pass 3: Specifically Reify
        pass3_prompt = f"""
        {self.workflow}
        
        PASS 3 - SPECIFICALLY REIFY: Create THIS specific {domain}.
        Using this generator: {generator}
        
        Build a concrete instance.
        """
        instance = self.llm.complete(pass3_prompt)
        
        return {
            'ontology': ontology,
            'generator': generator,
            'instance': instance
        }
```

## Adding the Understanding Loop
```python
class SmartBuilder(ThreePassEvolvingBuilder):
    def build_with_understanding(self, domain):
        # Try to build
        result = self.build_with_three_passes(domain)
        
        # Check for confusion
        if self.detect_confusion(result['ontology']):
            # Correct the confusion
            clarification = self.correct_confusion(domain, result['ontology'])
            
            # Rebuild with better understanding
            result = self.build_with_three_passes(
                domain + f"\nClarification: {clarification}"
            )
            
        return result
    
    def detect_confusion(self, output):
        confusion_markers = ["unclear", "not sure", "could be", "maybe"]
        return any(marker in output.lower() for marker in confusion_markers)
```

## The Complete System in Action
```python
# Initialize
builder = SmartBuilder()

# Generation 0: Use default workflow
print("Generation 0:", builder.workflow)
result = builder.build_with_understanding("task manager")
baseline_score = evaluate(result)

# Evolution loop
for generation in range(10):
    # Evolve to find better workflow
    new_workflow = builder.evolve_workflow()
    
    # Test the new workflow
    result = builder.build_with_understanding("task manager")
    score = evaluate(result)
    
    print(f"Generation {generation + 1}:")
    print(f"  Workflow: {new_workflow}")
    print(f"  Score: {score}")
    print(f"  Improvement: {score - baseline_score}")
    
    if score > baseline_score * 1.2:  # 20% improvement
        print("  🎉 Significant improvement found!")

# The system has now discovered a better way to build systems!
```

## Example Evolution Path
```
Generation 0: (0)[Goal]→(1)[Design]→(2)[Build]→(3)[Test]
  Score: 72

Generation 1: (0)[Goal]→(1)[Analysis]→(2)[Design]→(3)[Build]
  Score: 75 (+3)

Generation 3: (0)[Why]→(1)[What]→(2)[How]→(3)[Build]→(4)[Verify]  
  Score: 81 (+9)

Generation 7: (0)[Domain]→(1)[Ontology]→(2)[Patterns]→(3)[System]→(4)[Instance]
  Score: 89 (+17)
  🎉 Significant improvement found!
```

## The Key Insight

By making the workflow a variable instead of hardcoding it:
1. We can test thousands of variations
2. Evolution finds patterns we didn't think of
3. Different domains might need different workflows
4. The system improves itself over time

This is the power of evolutionary prompt engineering!