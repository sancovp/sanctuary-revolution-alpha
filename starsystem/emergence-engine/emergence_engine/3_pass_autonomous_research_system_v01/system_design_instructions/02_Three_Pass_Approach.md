# The Three-Pass Approach: From Concept to Instance

## Overview

The systems design workflow becomes truly powerful when applied in three passes, each building on the previous:

1. **Pass 1**: CONCEPTUALIZE (What IS this thing?)
2. **Pass 2**: GENERALLY REIFY (How do we MAKE these things?)
3. **Pass 3**: SPECIFICALLY REIFY (How do we make THIS PARTICULAR one?)

## Understanding the Passes

### Pass 1: CONCEPTUALIZE (Ontological/Universal)

**Core Question**: What IS the thing we're talking about?

**Mindset**: You're a philosopher/scientist studying the essential nature of something.

**Output**: Complete ontological understanding - the "platonic ideal" of your domain.

**Example**: 
- What IS an autobiography? 
- Not how to write one, but what makes something an autobiography
- Its essential components, relationships, purposes

### Pass 2: GENERALLY REIFY (General/Class Level)

**Core Question**: How do we CREATE instances of this type of thing?

**Mindset**: You're an engineer designing a factory that can produce these things.

**Output**: A system/process/framework that can generate instances.

**Example**:
- How do we BUILD autobiography generators?
- What agents/tools/processes are needed?
- How do they work together?

### Pass 3: SPECIFICALLY REIFY (Specific/Instance Level)

**Core Question**: How do we create THIS PARTICULAR instance?

**Mindset**: You're an operator using the system to create one specific thing.

**Output**: An actual, concrete instance.

**Example**:
- How do we generate Jane Doe's specific autobiography?
- What are her particular memories, themes, voice?
- How do we configure the system for her?

## The Power of This Approach

### 1. **Prevents Common Mistakes**

Without Pass 1: You build features without understanding the domain
Without Pass 2: You hard-code solutions instead of building flexible systems
Without Pass 3: You have theory but no practical application

### 2. **Ensures Completeness**

- Pass 1 ensures you understand ALL aspects of the domain
- Pass 2 ensures your system can handle ALL variations
- Pass 3 proves your system actually works

### 3. **Enables Reusability**

- Pass 1 knowledge applies to ANY instance
- Pass 2 system can create MANY instances
- Pass 3 gives you concrete examples and patterns

## How Phases Change Across Passes

### Phase 0: Abstract Goal

**Pass 1**: What is the essential nature of [domain]?
**Pass 2**: Create a system that can generate [domain] instances
**Pass 3**: Generate this specific [instance]

### Phase 1: Systems Design

**Pass 1**: What are the universal characteristics of [domain]?
**Pass 2**: What does our generation system need?
**Pass 3**: What does this specific instance need?

### Phase 3: DSL (Domain-Specific Language)

**Pass 1**: What concepts and relationships exist in [domain]?
**Pass 2**: What vocabulary does our system use internally?
**Pass 3**: How do we express this specific instance?

## Practical Examples

### Example 1: Autobiography System

**Pass 1**: 
- Autobiographies contain memories, themes, chronology, voice
- They serve to preserve and communicate life experiences
- They have narrative structure with beginning, middle, end

**Pass 2**:
- We need InterviewAgent, ThemeAgent, NarrativeAgent
- System must handle memory storage, theme extraction
- Agents coordinate through orchestrator

**Pass 3**:
- Jane is 65, wants to focus on her immigration story
- System configured for longer interviews, family themes
- Generate with emphasis on cultural transition

### Example 2: E-commerce Platform

**Pass 1**:
- Commerce involves buyers, sellers, products, transactions
- Trust, discovery, and exchange are essential
- Money flows opposite to goods

**Pass 2**:
- Need UserService, ProductCatalog, PaymentProcessor
- System handles authentication, inventory, transactions
- Services communicate via API gateway

**Pass 3**:
- Building platform for handmade crafts
- Configure for individual sellers, unique items
- Emphasize story-telling and artisan profiles

## Common Pitfalls and How to Avoid Them

### Pitfall 1: Jumping to Implementation
**Wrong**: "Let's build an autobiography app!"
**Right**: "Let's understand what autobiographies ARE first"

### Pitfall 2: Mixing Passes
**Wrong**: Designing the database schema in Pass 1
**Right**: Understanding data relationships conceptually in Pass 1

### Pitfall 3: Skipping Passes
**Wrong**: Going straight from idea to coding
**Right**: Concept → System → Instance

### Pitfall 4: Over-Abstracting
**Wrong**: Pass 1 becomes philosophical naval-gazing
**Right**: Practical ontology focused on essential characteristics

## The Fractal Nature

This three-pass approach is fractal - you can apply it at any level:

### System Level
1. What IS this system?
2. How do we BUILD systems like this?
3. How do we build THIS system?

### Component Level
1. What IS this component?
2. How do we BUILD these components?
3. How do we build THIS component?

### Feature Level
1. What IS this feature?
2. How do we IMPLEMENT these features?
3. How do we implement THIS feature?

## Practical Tips

1. **Document Each Pass Separately**
   - Keep Pass 1 free of implementation details
   - Keep Pass 2 general and reusable
   - Keep Pass 3 specific and concrete

2. **Review Between Passes**
   - Does Pass 2 fully implement Pass 1's ontology?
   - Does Pass 3 prove Pass 2 works?

3. **Iterate When Needed**
   - If Pass 2 reveals Pass 1 gaps, go back
   - If Pass 3 fails, revise Pass 2

4. **Use the Right Mindset**
   - Pass 1: Think like a domain expert
   - Pass 2: Think like a systems architect
   - Pass 3: Think like an end user

## Conclusion

The three-pass approach transforms the systems design workflow from a checklist into a powerful thinking tool. By separating conceptual understanding from implementation, and implementation from instantiation, we create more robust, flexible, and complete systems.

Remember: 
- **Pass 1** tells us WHAT to build
- **Pass 2** tells us HOW to build it  
- **Pass 3** PROVES we built it right
