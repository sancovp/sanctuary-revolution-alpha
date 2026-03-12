# Complete Compound Intelligence System Topology

This file contains the complete topology map for navigating the compound intelligence system. Read this to understand where you are in the overall flow and which tools to use next.

---

# Biphasic Conversation Topology: Global/Local Levels

## The Core Pattern: Every Conversation is Dev→Implement

```mermaid
sequenceDiagram
    participant GD as Global Dev
    participant LD as Local Dev
    participant LI as Local Implement
    participant V1 as Verify Local
    participant V2 as Verify Global
    participant GI as Global Integrate
    
    Note over GD,GI: CONVERSATION TOPOLOGY OVER TIME
    
    rect rgb(255, 240, 240)
        Note over GD,GI: GLOBAL LEVEL: Project Architecture
        
        GD->>GD: Global project structure
        Note right of GD: What IS this entire system?<br/>How do we BUILD these systems?<br/>How do we build THIS system?
        
        GD->>LD: Delegate component specification
    end
    
    rect rgb(240, 255, 240)
        Note over GD,GI: LOCAL LEVEL: Component Development
        
        LD->>LD: Component specification
        Note right of LD: What IS this component?<br/>How do we BUILD these?<br/>How do we build THIS one?
        
        LD->>LI: Implement component
        
        LI->>LI: Actual implementation
        Note right of LI: Code writing<br/>Testing<br/>Documentation
        
        LI->>V1: Implementation complete
    end
    
    rect rgb(240, 240, 255)
        Note over GD,GI: VERIFICATION GATES
        
        V1->>V1: Verify meets local dev spec
        Note right of V1: Does implementation<br/>match component spec?
        
        alt Local verification fails
            V1-->>LD: Refine local spec
            LD-->>LI: Re-implement
        else Local verification passes
            V1->>V2: Check global alignment
        end
        
        V2->>V2: Verify meets global dev spec
        Note right of V2: Does component fit<br/>system architecture?
        
        alt Global verification fails
            V2-->>GD: Update global understanding
            GD-->>LD: Cascade to local
        else Global verification passes
            V2->>GI: Ready for integration
        end
    end
    
    rect rgb(255, 255, 240)
        Note over GD,GI: INTEGRATION & EVOLUTION
        
        GI->>GI: Integrate to global system
        Note right of GI: Component becomes<br/>part of system
        
        GI->>GD: Update global dev
        Note right of GD: Global understanding<br/>evolves with new component
        
        GD->>GD: Global dev cycle continues
        Note right of GD: System grows and<br/>understanding deepens
        
        GD->>LD: Next component cycle
        Note right of LD: Pattern repeats with<br/>accumulated wisdom
    end
    
    loop Conversation Sessions Over Time
        GD->>LD: Component N specification
        LD->>LI: Implement component N
        LI->>V1: Verify local
        V1->>V2: Verify global
        V2->>GI: Integrate
        GI->>GD: Evolve global
        Note over GD,GI: Each cycle faster due to accumulated patterns
    end
    
    Note over GD,GI: COMPOUND INTELLIGENCE: Each loop strengthens the system
```

## The Biphasic Pattern at Each Level:

### Global Level Biphasic Loop:
```
Global Dev → Global Implementation (via Local cycles) → Global Dev (evolved)
```

### Local Level Biphasic Loop:
```
Local Dev → Local Implementation → Local Dev (refined)
```

### The Complete Topology:
```
Global Dev
    ↓
Local Dev
    ↓
Local Implement
    ↓
Verify Local Spec
    ↓
Verify Global Spec
    ↓
Integrate to Global
    ↓
Global Dev (evolved)
    ↓
[Loop continues with next component]
```

---

# Tool Activation Sequence: Operating the Biphasic Loop

## How We Actually Execute the Core Biphasic Pattern Using Our Tools

```mermaid
sequenceDiagram
    participant U as User
    participant SS as STARSHIP
    participant SL as STARLOG
    participant TP as 3-Pass
    participant G as GIINT
    participant I as Implementation
    participant D as Documentation
    
    Note over U,D: TOOL ACTIVATION FOR BIPHASIC LOOP OPERATION
    
    rect rgb(255, 240, 240)
        Note over U,D: GLOBAL DEV PHASE - Tool Activation
        
        U->>SS: Project request
        SS->>SS: launch_routine()
        SS->>SS: fly() - Present flight configs
        U->>SS: Select development flight config
        
        SS->>SL: Initialize/load project context
        SL->>SL: init_project() or orient()
        SL->>SS: Context ready
        
        SS->>TP: Activate 3-pass thinking (Global)
        TP->>TP: Layer 0: Ontological understanding
        TP->>TP: Layer 1: System patterns
        TP->>TP: Layer 2: Specific approach
        TP->>SS: Global specification complete
        
        SS->>G: Transform to project structure
        G->>G: create_project() or update
        G->>G: add_feature_to_project()
        G->>SS: Global GIINT structure ready
    end
    
    rect rgb(240, 255, 240)
        Note over U,D: LOCAL DEV PHASE - Tool Activation
        
        SS->>G: Query component priorities
        G->>SS: Next component to develop
        
        SS->>TP: Activate 3-pass thinking (Local)
        TP->>TP: Component Layer 0: What IS this?
        TP->>TP: Component Layer 1: How BUILD these?
        TP->>TP: Component Layer 2: Build THIS one
        TP->>SS: Component specification complete
        
        SS->>G: Update component structure
        G->>G: add_component_to_feature()
        G->>G: add_deliverable_to_component()
        G->>G: add_task_to_deliverable()
        G->>SS: Local GIINT structure ready
    end
    
    rect rgb(240, 240, 255)
        Note over U,D: LOCAL IMPLEMENT PHASE - Tool Activation
        
        SS->>I: Begin implementation
        I->>G: Query current tasks
        G->>I: Task list and specifications
        
        I->>I: Execute implementation
        Note right of I: Code writing<br/>Testing<br/>Debugging
        
        I->>D: Update documentation
        D->>D: Code docs, README, etc.
        
        I->>SS: Implementation complete
        SS->>SL: update_debug_diary()
    end
    
    rect rgb(255, 255, 240)
        Note over U,D: VERIFICATION & INTEGRATION - Tool Activation
        
        SS->>G: Verify local spec alignment
        G->>G: Check task completion
        G->>SS: Local verification result
        
        SS->>TP: Verify global alignment
        TP->>TP: Check architectural fit
        TP->>SS: Global verification result
        
        alt Verification passed
            SS->>G: Mark component complete
            G->>G: Update project state
            SS->>SL: Log integration
        else Verification failed
            SS->>SS: Loop back to appropriate phase
        end
        
        SS->>SS: landing_routine()
        SS->>U: Session complete
    end
    
    loop Conversation Sessions Over Time
        Note over U,D: Each session follows this tool activation pattern
        Note over U,D: Context accumulates through STARLOG
        Note over U,D: Patterns emerge through repeated cycles
        Note over U,D: Tools become more efficient over time
    end
```

## Tool Responsibilities in the Biphasic Loop:

### **STARSHIP** - Orchestration
- `launch_routine()` - Start sessions
- `fly()` - Present flight configs (workflows)
- Route between phases
- `landing_routine()` - End sessions

### **STARLOG** - Context Management
- `init_project()` - New projects
- `orient()` - Load context
- `update_debug_diary()` - Capture discoveries
- Maintain continuity across sessions

### **3-Pass** - Systematic Thinking
- Global level: Project ontology
- Local level: Component design
- Verification: Architecture alignment
- Output: Specifications

### **GIINT** - Project Structure
- `create_project()` - Initialize structure
- `add_*()` functions - Build hierarchy
- Task management
- Progress tracking

### **Implementation** - Building
- Execute GIINT tasks
- Write actual code
- Run tests
- Debug issues

### **Documentation** - Knowledge Capture
- Code documentation
- README files
- API docs
- Pattern documentation

---

# Traditional 3-Pass System: The Full 9-Pass Nested Structure

## The Complete 3-Layer System (9 Total Passes)

```mermaid
flowchart TD
    subgraph "LAYER 0: CONCEPTUALIZE (What IS it?)"
        L0_Title["Layer 0: Ontological Understanding"]
        
        subgraph "Pass 1 of Layer 0"
            L0P1["Pass 1: What IS 'What IS it?'<br/>Understanding the nature of ontological inquiry"]
        end
        
        subgraph "Pass 2 of Layer 0"
            L0P2["Pass 2: How do we DETERMINE 'What IS it?'<br/>Methods for ontological analysis"]
        end
        
        subgraph "Pass 3 of Layer 0"
            L0P3["Pass 3: Determine what THIS SPECIFIC THING IS<br/>Apply ontological analysis to our target"]
        end
        
        L0P1 --> L0P2 --> L0P3
    end
    
    subgraph "LAYER 1: GENERALLY REIFY (How to BUILD?)"
        L1_Title["Layer 1: System Architecture"]
        
        subgraph "Pass 1 of Layer 1"
            L1P1["Pass 1: What IS 'system building'?<br/>Understanding the nature of construction"]
        end
        
        subgraph "Pass 2 of Layer 1"
            L1P2["Pass 2: How do we BUILD systems that BUILD?<br/>Meta-architecture patterns"]
        end
        
        subgraph "Pass 3 of Layer 1"
            L1P3["Pass 3: Build THIS system architecture<br/>Apply patterns to create our builder"]
        end
        
        L1P1 --> L1P2 --> L1P3
    end
    
    subgraph "LAYER 2: SPECIFICALLY REIFY (Build THIS)"
        L2_Title["Layer 2: Concrete Implementation"]
        
        subgraph "Pass 1 of Layer 2"
            L2P1["Pass 1: What IS 'this implementation'?<br/>Understanding our specific instance"]
        end
        
        subgraph "Pass 2 of Layer 2"
            L2P2["Pass 2: How do we BUILD implementations?<br/>Implementation methodology"]
        end
        
        subgraph "Pass 3 of Layer 2"
            L2P3["Pass 3: Build THIS exact implementation<br/>Create the actual instance"]
        end
        
        L2P1 --> L2P2 --> L2P3
    end
    
    L0P3 --> L1P1
    L1P3 --> L2P1
    L2P3 --> Output["Generator System Complete"]
    
    style L0P1 fill:#ffe6e6
    style L0P2 fill:#ffe6e6
    style L0P3 fill:#ffe6e6
    style L1P1 fill:#e6ffe6
    style L1P2 fill:#e6ffe6
    style L1P3 fill:#e6ffe6
    style L2P1 fill:#e6e6ff
    style L2P2 fill:#e6e6ff
    style L2P3 fill:#e6e6ff
```

## The Crucial Mechanic: Layer 2 Creates a Generator

### Example: Task Management System

```mermaid
flowchart LR
    subgraph "Layer 0 Output"
        L0Out["Complete ontological understanding:<br/>What IS a task management system"]
    end
    
    subgraph "Layer 1 Output"
        L1Out["General patterns:<br/>How to BUILD task management systems"]
    end
    
    subgraph "Layer 2 Output"
        L2Out["A task management system<br/>FOR managing task management<br/>system generator work<br/>(and executing it)"]
    end
    
    L0Out --> L1Out
    L1Out --> L2Out
    
    L2Out --> Gen1["Can generate: Task Management System 1"]
    L2Out --> Gen2["Can generate: Task Management System 2"]
    L2Out --> Gen3["Can generate: Task Management System 3"]
    L2Out --> GenN["Can generate: Task Management System N..."]
    
    L2Out --> ManagesSelf["Manages its own<br/>generator work"]
    
    style L2Out fill:#ffff99
    style ManagesSelf fill:#99ff99
```

## The Pattern Explained:

When you complete all 9 passes for any domain:

**Layer 0** produces:
- Complete ontological understanding of the domain
- What IS [domain concept]?

**Layer 1** produces:
- General patterns for building systems in this domain
- How do we BUILD [domain] systems?

**Layer 2** produces:
- A [domain] system FOR managing [domain] system generator work
- It's opinionated to the Layer 1 scope
- It can generate other [domain] systems
- It manages the work of generating those systems

## The Key Insight:

The output of Layer 2 is **not just an instance** but a **generator that creates instances**.

Furthermore, this generator:
- Is itself an instance of what it generates
- Manages the work of generating other instances
- Is opinionated to the architectural patterns from Layer 1

---

# Complete System Integration

The three topology views work together:

1. **Biphasic Topology**: The fundamental pattern all conversations follow
2. **Tool Activation**: How to execute the pattern using our tool ecosystem  
3. **9-Pass System**: The systematic thinking method that creates generators

Together they provide the navigation map for compound intelligence system operation.