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

## The Key Insight:

The **biphasic loop** (from diagram 01) is the WHAT - the fundamental pattern.

This **tool activation sequence** is the HOW - how we operate that pattern using our tool ecosystem.

Together they show:
1. **The Pattern**: Global/Local Dev → Implement cycles with verification
2. **The Execution**: Which tools activate when to execute the pattern