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

## Key Insights:

1. **Biphasic Core**: Every conversation alternates between DEV and IMPLEMENT phases

2. **Two Levels**: 
   - **Global**: System-wide architecture and understanding
   - **Local**: Component-specific development

3. **Verification Gates**:
   - **Local Verification**: Does implementation match component spec?
   - **Global Verification**: Does component fit system architecture?

4. **Evolution Pattern**:
   - Each local cycle informs global understanding
   - Global evolution guides future local cycles
   - Compound intelligence emerges from this feedback

5. **Conversation Topology**:
   - Not linear but cyclical with feedback
   - Global and local levels interact continuously
   - Verification ensures coherence
   - Integration evolves the system

## The Universal Truth:

**Every conversation in the project follows this biphasic topology:**
- Start with dev (understanding/specifying)
- Move to implement (building/testing)
- Verify alignment (local then global)
- Integrate and evolve
- Loop continues at higher level

This is how compound intelligence emerges - through repeated biphasic cycles at multiple levels with verification and integration feedback!