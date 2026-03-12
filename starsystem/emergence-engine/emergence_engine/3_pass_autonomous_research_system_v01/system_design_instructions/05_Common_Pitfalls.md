# Common Pitfalls and How to Avoid Them

## Overview

Even with a structured workflow, certain mistakes appear repeatedly. This guide identifies the most common pitfalls and provides strategies to avoid them.

## Pitfall 1: Starting with Implementation

### The Mistake
Jumping straight to "how to build it" without understanding "what it is."

### Why It Happens
- Excitement to start coding
- Pressure to show progress
- Assumption that the domain is "obvious"

### The Consequences
- Building features that don't belong
- Missing essential components
- Rework when assumptions prove wrong

### How to Avoid
1. Force yourself to complete Pass 1 without any implementation details
2. Write "An X is..." statements before any "An X has..." statements
3. If you find yourself thinking about databases or APIs in Pass 1, stop

### Example
❌ Wrong: "An autobiography needs a database schema for memories"
✅ Right: "An autobiography contains memories as fundamental units of experience"

## Pitfall 2: Confusing DSL with Programming Language

### The Mistake
Creating syntax and parsers when you should be defining concepts.

### Why It Happens
- The term "language" is misleading
- Programming background biases toward syntax
- Easier to define syntax than semantics

### The Consequences
- Huge technical debt from custom parsers
- Users forced to learn new syntax
- Focus on form over meaning

### How to Avoid
1. Think "vocabulary" not "syntax"
2. Define concepts and relationships, not grammar
3. Express the DSL as natural language patterns

### Example
❌ Wrong: `MEMORY @year{1975} @age{5} { content: "...", emotions: [...] }`
✅ Right: "A Memory has temporal location (year/age), content, and emotional context"

## Pitfall 3: Over-Engineering Early Phases

### The Mistake
Making Pass 1 or early phases too complex and detailed.

### Why It Happens
- Desire to be thorough
- Fear of missing something
- Confusion about appropriate detail level

### The Consequences
- Analysis paralysis
- Lost in philosophical debates
- Never reaching implementation

### How to Avoid
1. Time-box each phase
2. Focus on "good enough" understanding
3. Remember you'll loop back with refinements
4. Keep Pass 1 conceptual, not detailed

### Example
❌ Wrong: Spending weeks defining every possible type of memory in an autobiography
✅ Right: Identifying major categories (milestone, routine, traumatic) and moving forward

## Pitfall 4: Ignoring the Feedback Loop

### The Mistake
Treating the workflow as linear rather than cyclical.

### Why It Happens
- Waterfall mindset
- Desire to "get it right" the first time
- Not planning for iteration

### The Consequences
- Rigid systems that can't evolve
- Missing improvement opportunities
- Systems that drift from their purpose

### How to Avoid
1. Plan for multiple loops from the start
2. Build in telemetry and monitoring
3. Schedule regular review cycles
4. Embrace "good enough" initial versions

### Example
❌ Wrong: "We've finished the design, now we just maintain it"
✅ Right: "Our first loop gave us v1, let's see what v2 should address"

## Pitfall 5: Mixing Passes

### The Mistake
Thinking about implementation during conceptualization or vice versa.

### Why It Happens
- Hard to maintain mental separation
- Excitement about specific solutions
- Lack of discipline in thinking modes

### The Consequences
- Polluted ontology with implementation concerns
- Constrained implementation by premature decisions
- Confused documentation

### How to Avoid
1. Use different documents for each pass
2. Explicitly state which pass you're in
3. Review each pass for contamination
4. Use different mental models for each pass

### Example
❌ Wrong: "An autobiography is a MongoDB document with chapters as subdocuments"
✅ Right: "An autobiography contains chapters" (Pass 1) → "We'll store chapters as subdocuments" (Pass 2)

## Pitfall 6: Skipping Substeps

### The Mistake
Jumping over substeps that seem irrelevant or obvious.

### Why It Happens
- Some substeps seem inapplicable
- Time pressure
- Overconfidence

### The Consequences
- Missing important constraints
- Incomplete understanding
- Problems discovered late

### How to Avoid
1. At least consider each substep briefly
2. Document why you're skipping if you do
3. Return to skipped steps if problems arise
4. Use substeps as a checklist

### Example
❌ Wrong: Skipping "Regulatory Bounds" because "it's just a personal project"
✅ Right: Considering privacy laws, copyright, and ethical bounds even for personal projects

## Pitfall 7: Losing Domain Focus

### The Mistake
Letting technical concerns overshadow domain understanding.

### Why It Happens
- Technical background of designers
- Excitement about technology
- Easier to discuss concrete tech than abstract domains

### The Consequences
- Technically excellent but domain-inappropriate solutions
- Missing the real user needs
- Building a platform instead of solving problems

### How to Avoid
1. Keep domain experts involved
2. Use domain language, not technical jargon
3. Test understanding with non-technical stakeholders
4. Prioritize domain integrity over technical elegance

### Example
❌ Wrong: "Our distributed microservice architecture ensures scalability"
✅ Right: "Our system helps people preserve their life stories"

## Pitfall 8: Insufficient Abstraction

### The Mistake
Staying too concrete in early phases, missing general patterns.

### Why It Happens
- Easier to think in specifics
- Lack of experience with abstraction
- Fear of being "too theoretical"

### The Consequences
- Systems that only work for one use case
- Missed opportunities for reuse
- Inflexible architectures

### How to Avoid
1. Always ask "what's the general case?"
2. Look for patterns across examples
3. Test abstractions with multiple instances
4. Balance abstraction with practicality

### Example
❌ Wrong: "The system interviews Jane about her childhood"
✅ Right: "The system elicits memories about life phases"

## Pitfall 9: Analysis Paralysis

### The Mistake
Getting stuck in endless analysis without moving to action.

### Why It Happens
- Fear of making mistakes
- Perfectionism
- Enjoyment of theoretical work

### The Consequences
- Nothing gets built
- Stakeholders lose faith
- Opportunity windows close

### How to Avoid
1. Set strict time limits for each phase
2. Embrace "good enough" for first loop
3. Remember you can refine in future loops
4. Value learning from implementation

### Example
❌ Wrong: Spending 6 months on the perfect ontology
✅ Right: 2-week Pass 1, then learn from building

## Pitfall 10: Forgetting the Human Element

### The Mistake
Focusing on systems and forgetting about users and stakeholders.

### Why It Happens
- Technical focus
- Abstract thinking disconnected from reality
- Assumption that good design is self-evident

### The Consequences
- Technically correct but unusable systems
- Missing real user needs
- Systems that require extensive training

### How to Avoid
1. Include user perspectives in every phase
2. Test understanding with real stakeholders
3. Design for actual, not theoretical users
4. Prioritize usability over elegance

### Example
❌ Wrong: "Users will express memories in our DSL format"
✅ Right: "Users share memories naturally; our system structures them"

## Meta-Pitfall: Not Adapting the Workflow

### The Mistake
Following the workflow too rigidly without adaptation to context.

### Why It Happens
- Treating the workflow as dogma
- Fear of "doing it wrong"
- Lack of confidence to adapt

### The Consequences
- Inefficient process
- Missing domain-specific needs
- Frustrated team members

### How to Avoid
1. Understand the workflow's intent, not just steps
2. Adapt depth and focus to your context
3. Document your adaptations and why
4. Keep the spirit while adjusting the letter

### Example
❌ Wrong: "We must do all 6 phases with all substeps exactly as specified"
✅ Right: "Given our domain and constraints, we'll emphasize these phases and streamline those"

## Summary: Keys to Success

1. **Maintain Pass Discipline**: Keep conceptual and implementation thinking separate
2. **Embrace Iteration**: Plan for multiple loops from the start
3. **Stay Domain-Focused**: Technology serves the domain, not vice versa
4. **Balance Theory and Practice**: Don't get lost in either extreme
5. **Remember the Humans**: Design for real people, not abstract users
6. **Adapt Thoughtfully**: Use the workflow as a guide, not a straightjacket

The workflow is a powerful tool, but like any tool, its effectiveness depends on skillful use. By avoiding these pitfalls, you can harness its full potential to create robust, well-designed systems that truly serve their purpose.
