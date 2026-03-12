# Systems Design Workflow: Master Guide

## The Meta-Framework

This guide explains how to use the systems design workflow prompt - a powerful tool for designing complex systems through ontological thinking and iterative refinement.

## Core Philosophy

The workflow embodies several key principles:

1. **Ontological Thinking First**: Understand WHAT something IS before HOW to build it
2. **Multi-Pass Refinement**: Build understanding in layers from abstract to concrete
3. **Systematic Completeness**: Every aspect gets attention through structured phases
4. **Continuous Evolution**: The system loops back to refine itself

## The Workflow Notation

```
(0)[AbstractGoal]→(1)[SystemsDesign→(1a)...(1l)]→(2)[SystemsArchitecture→(2a)...(2h)]→
(3)[DSL→(3a)...(3f)]→(4)[Topology→(4a)...(4g)]→(5)[EngineeredSystem→(5a)...(5g)]→
(6)[FeedbackLoop→(6a)...(6i)]→loop→(0)
```

### How to Read This:
- **(N)** = Phase number
- **[PhaseName]** = Major phase
- **(Na)...(Nx)** = Sub-steps within phase
- **→** = Sequential flow
- **loop→(0)** = Returns to beginning with new understanding

## The Three-Pass System

### Pass 1: CONCEPTUALIZE (Universal/Ontological)
**Question**: What IS the thing we're designing?
**Output**: Complete ontological understanding of the domain

### Pass 2: GENERALLY REIFY (General/Class)
**Question**: How do we CREATE instances of this thing?
**Output**: System that can generate instances

### Pass 3: SPECIFICALLY REIFY (Specific/Instance)
**Question**: How do we create THIS PARTICULAR instance?
**Output**: Actual concrete instance

## Why This Works

1. **Prevents Premature Implementation**: Can't code what you don't understand
2. **Ensures Completeness**: Systematic coverage of all aspects
3. **Enables Quality**: Know what "good" looks like before building
4. **Supports Evolution**: Built-in feedback and refinement

## How to Use This Guide

1. Read the **Overview** (this file) first
2. Study **How to Read the Workflow** for notation
3. Understand **The Three-Pass Approach** 
4. Work through **Phase-by-Phase Guide**
5. Review **Common Pitfalls**
6. See **Worked Examples**

## Key Insight

The workflow is fractal - you can apply it at any scale:
- Entire system design
- Individual component design  
- Feature implementation
- Even this guide itself!

Remember: The goal is not to rigidly follow steps, but to think systematically about what you're building, ensuring nothing important is missed while maintaining flexibility for creativity and adaptation.
