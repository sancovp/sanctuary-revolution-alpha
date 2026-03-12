# Research System: Example Flow

## A Complete Research Session

### Run 1: Starting Fresh
```python
research = ResearchSystem(llm_client)

result = research.run(description="recipe recommendation system")
```

**System internally does:**

1. **Generates Initial Hypothesis**
   ```
   "The default workflow (Goal→Design→Build→Test) should work for 
   a recipe system but may need additional phases for user preferences 
   and recipe matching logic"
   ```

2. **Executes 3-Pass System**
   - Pass 1: "A recipe recommendation system IS a bridge between user tastes and available recipes..."
   - Pass 2: Generates RecipeRecommender class with preference modeling
   - Pass 3: Creates instance with sample recipes and user

3. **Analyzes Results**
   ```json
   {
     "scores": {
       "overall": 75,
       "pass1_abstraction": 85,
       "pass2_completeness": 70,
       "pass3_functionality": 70
     }
   }
   ```

4. **Generates Conclusions**
   ```
   "The workflow performed adequately but struggled with:
   - No explicit phase for modeling user preferences
   - Recipe matching logic was embedded in Build phase
   - Testing phase didn't cover recommendation quality
   
   Suggested improvement: Add explicit phases for Users and Matching"
   ```

5. **Returns Result**
   ```python
   ResearchResult(
     system_id="recipe_rec_v1",
     hypothesis="The default workflow should work...",
     conclusions="The workflow performed adequately but...",
     suggested_next_steps=["Add User Preferences phase", "Add Matching phase"],
     score=75
   )
   ```

### Run 2: Evolution
```python
result2 = research.run(system_id="recipe_rec_v1")
```

**System internally does:**

1. **Loads Previous Result** and sees conclusions about missing phases

2. **Generates Evolution Hypothesis**
   ```
   "Adding explicit Users and Matching phases will improve the system by:
   - Separating concerns more clearly
   - Enabling better preference modeling
   - Making matching logic explicit
   Expected improvement: 15-20 points"
   ```

3. **Evolves Workflow**
   ```
   Before: (0)[Goal]→(1)[Design]→(2)[Build]→(3)[Test]
   After:  (0)[Goal]→(1)[Users]→(2)[Recipes]→(3)[Matching]→(4)[Build]→(5)[Test]
   ```

4. **Executes 3-Pass with New Workflow**
   - Pass 1: Much clearer ontology with explicit user/recipe/matching concepts
   - Pass 2: Better structured code with separate modules
   - Pass 3: More sophisticated instance with learning capabilities

5. **Analyzes and Compares**
   ```json
   {
     "scores": {
       "overall": 88,
       "pass1_abstraction": 92,
       "pass2_completeness": 87,
       "pass3_functionality": 85
     },
     "improvement": 13,
     "changes": {
       "added_phases": ["Users", "Recipes", "Matching"],
       "restructured": true
     }
   }
   ```

6. **Returns Evolved Result**
   ```python
   ResearchResult(
     system_id="recipe_rec_v2",
     parent_id="recipe_rec_v1",
     generation=2,
     hypothesis="Adding explicit Users and Matching phases...",
     conclusions="Hypothesis confirmed. The new structure significantly improved all metrics...",
     improvement_delta=13
   )
   ```

### Run 3: Further Evolution
```python
result3 = research.run(system_id="recipe_rec_v2")
```

Now the system might try:
- Adding a Learning phase for preference evolution
- Parallelizing user and recipe processing
- Adding a Personalization phase
- Or something unexpected!

## What Makes This Powerful

### 1. Scientific Method for Prompt Engineering
```
Hypothesis → Experiment → Analysis → Conclusion → New Hypothesis
```

### 2. Automatic Evolution Based on Learning
The system learns what worked and what didn't, then evolves accordingly.

### 3. Complete Audit Trail
```python
# See the full evolution
lineage = research.get_lineage("recipe_rec_v5")

for result in lineage:
    print(f"Gen {result.generation}: {result.workflow}")
    print(f"  Score: {result.quality_scores['overall']}")
    print(f"  Key insight: {result.insights[0]}")
    print()
```

Output:
```
Gen 0: (0)[Goal]→(1)[Design]→(2)[Build]→(3)[Test]
  Score: 75
  Key insight: Need explicit preference modeling

Gen 1: (0)[Goal]→(1)[Users]→(2)[Recipes]→(3)[Matching]→(4)[Build]
  Score: 88
  Key insight: Separating concerns improved architecture

Gen 2: (0)[Users]→(1)[Preferences]→(2)[Recipes]→(3)[Learn]→(4)[Match]→(5)[Build]
  Score: 92
  Key insight: Learning phase enables adaptation

...
```

### 4. Cross-Domain Learning
```python
# The system can suggest workflows based on similar domains
suggestions = research.suggest_from_similar("meal planning system")

# Returns:
[
  {
    "workflow": "(0)[Users]→(1)[Preferences]→(2)[Meals]→(3)[Planning]→(4)[Build]",
    "rationale": "Similar to recipe system but with temporal planning",
    "expected_score": 85
  }
]
```

## The Beautiful Part

Each run is:
1. **A complete experiment** (hypothesis → test → conclusion)
2. **An evolution step** (learns and improves)
3. **A building block** (creates working system)
4. **A knowledge contribution** (adds to collective learning)

The system gets smarter with every use, discovering patterns we haven't imagined yet.