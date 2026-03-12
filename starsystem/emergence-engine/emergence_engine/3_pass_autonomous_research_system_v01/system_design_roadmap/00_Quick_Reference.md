# Research System Quick Reference

## The One-Page Guide

### Core Concept
```
Take any system description
→ Generate hypothesis about workflow effectiveness  
→ Test using 3-pass system (What IS / How MAKE / Make THIS)
→ Analyze results and generate conclusions
→ Evolve workflow based on learnings
→ Repeat until optimal
```

### Basic Usage
```python
# Start fresh
result = research.run(description="chat app")

# Evolve
result2 = research.run(system_id="chat_app_v1")

# Custom workflow
result3 = research.run(
    description="chat app",
    workflow="(0)[Messages]→(1)[Users]→(2)[Rooms]→(3)[System]"
)
```

### What You Get Back
```python
ResearchResult:
  - system_id: "chat_app_v1"
  - score: 82
  - hypothesis: "Standard workflow should handle chat domain"
  - conclusions: "Needs explicit real-time phase"
  - pass1_output: "A chat app IS..."
  - pass2_output: "class ChatSystem:..."
  - pass3_output: "chat = ChatSystem(..."
  - suggested_next_steps: ["Add WebSocket phase", "Split Users/Auth"]
```

### Evolution Magic
```
v1: (0)[Goal]→(1)[Design]→(2)[Build]
    Score: 72
    "Missing real-time considerations"
    ↓
v2: (0)[Goal]→(1)[Design]→(2)[Realtime]→(3)[Build]  
    Score: 81 (+9)
    "Better but auth mixed with users"
    ↓
v3: (0)[Users]→(1)[Auth]→(2)[Messages]→(3)[Realtime]→(4)[Build]
    Score: 89 (+8)
    "Clear separation of concerns!"
```

### Key Commands
```python
# View evolution history
lineage = research.get_lineage("chat_app_v3")

# Compare versions
diff = research.compare("v1", "v3")

# Get suggestions for next experiment
suggestions = research.suggest_experiments("v3")

# Find similar successful patterns
similar = research.find_similar("video chat app")
```

### The 3-Pass System (Always Running)
1. **Pass 1**: What IS a [system]? (Ontology)
2. **Pass 2**: How do we MAKE [system]s? (Generator)
3. **Pass 3**: Create THIS specific [system] (Instance)

### Workflow Evolution Strategies
- **Add Phase**: Insert new step where needed
- **Split Phase**: Break complex phase into parts
- **Reorder**: Change sequence for better flow
- **Rename**: Clarify phase purposes
- **Parallelize**: Run independent phases simultaneously
- **Remove**: Drop redundant phases

### Success Metrics
- **Score**: Overall quality (0-100)
- **Pass Scores**: Quality of each pass output
- **Improvement**: Delta from parent
- **Coherence**: How well passes connect
- **Insights**: Novel discoveries count

### Common Discoveries
```
Generic → Domain-Specific:
"Design" → "User Modeling" (for social apps)
"Build" → "Training" (for ML systems)
"Test" → "Simulation" (for game engines)

Missing Phases Often Found:
- State management for complex apps
- Auth/Security for user systems  
- Learning/Adaptation for AI systems
- Monitoring for production systems
```

### Remember
- Every run generates a real, working system
- Evolution is guided by concrete results
- The system gets smarter with each use
- Discoveries in one domain transfer to others

### Start Now
```python
research = ResearchSystem(llm)
result = research.run(description="your idea here")
# That's it! Check result.system_id to evolve further
```

---

*The system that improves how systems improve systems.*