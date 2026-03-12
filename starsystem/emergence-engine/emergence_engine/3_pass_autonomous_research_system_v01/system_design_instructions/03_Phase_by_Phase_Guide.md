# Phase-by-Phase Guide

## Phase 0: Abstract Goal

**Purpose**: Define the highest-level objective of what you're designing.

**Key Question**: What are we trying to achieve?

### In Each Pass:
- **Pass 1**: What is the essential nature/purpose of [domain]?
- **Pass 2**: What system will create [domain] instances?
- **Pass 3**: What specific instance are we creating?

### Output:
- Clear, concise statement of intent
- No implementation details
- Focus on the "why" and "what" not "how"

### Example:
- Pass 1: "Understand the nature of autobiographies as narrative systems"
- Pass 2: "Create a system that generates autobiographies"
- Pass 3: "Generate Jane Doe's autobiography"

---

## Phase 1: Systems Design

**Purpose**: Translate abstract goal into concrete design requirements.

### Sub-steps:

#### (1a) Purpose Capture
**What**: Document why this system/thing exists
**Pass 1**: Core purposes of the domain concept
**Pass 2**: Purpose of the generation system
**Pass 3**: Purpose of this specific instance

#### (1b) Context Map
**What**: Understand the environment and situation
**Pass 1**: Cultural/historical context of domain
**Pass 2**: Technical/operational context
**Pass 3**: Specific user's context

#### (1c) Stakeholder Goals
**What**: Identify who cares and what they want
**Pass 1**: Universal stakeholders (readers, writers, society)
**Pass 2**: System stakeholders (users, operators, developers)
**Pass 3**: Specific stakeholders (Jane, her family)

#### (1d) Success Metrics
**What**: Define how to measure success
**Pass 1**: What makes a good [domain instance]?
**Pass 2**: What makes a good generation system?
**Pass 3**: What makes this specific instance successful?

#### (1e) Constraint Scan
**What**: Identify limitations and boundaries
**Pass 1**: Inherent constraints of the domain
**Pass 2**: System design constraints
**Pass 3**: Specific instance constraints

#### (1f) Resource Limits
**What**: Understand available resources
**Pass 1**: Universal resource considerations
**Pass 2**: System resource requirements
**Pass 3**: Resources for this instance

#### (1g) Regulatory Bounds
**What**: Legal, ethical, policy constraints
**Pass 1**: Domain-specific regulations
**Pass 2**: System compliance needs
**Pass 3**: Instance-specific requirements

#### (1h) Risk Assumptions
**What**: Identify what could go wrong
**Pass 1**: Inherent domain risks
**Pass 2**: System failure modes
**Pass 3**: Specific instance risks

#### (1i) Concept Model
**What**: Core concepts and relationships
**Pass 1**: Domain ontology basics
**Pass 2**: System concept model
**Pass 3**: Instance data model

#### (1j) Ontology Sketch
**What**: Detailed concept hierarchy
**Pass 1**: Complete domain ontology
**Pass 2**: System component ontology
**Pass 3**: Instance-specific structures

#### (1k) Boundary Set
**What**: Define what's in and out of scope
**Pass 1**: Domain boundaries
**Pass 2**: System boundaries
**Pass 3**: Instance boundaries

#### (1l) Design Brief
**What**: Synthesize everything into clear direction
**Pass 1**: What the domain IS
**Pass 2**: How the system works
**Pass 3**: Instance specifications

---

## Phase 2: Systems Architecture

**Purpose**: Define how components work together to achieve the design.

### Sub-steps:

#### (2a) Function Decomposition
**What**: Break down into discrete functions
**Pass 1**: Essential functions of domain
**Pass 2**: System functions needed
**Pass 3**: Functions for this instance

#### (2b) Module Grouping
**What**: Organize functions into coherent modules
**Pass 1**: Natural domain groupings
**Pass 2**: System modules/services
**Pass 3**: Instance configuration

#### (2c) Interface Definition
**What**: How modules communicate
**Pass 1**: Domain interaction patterns
**Pass 2**: System APIs/interfaces
**Pass 3**: Instance data flows

#### (2d) Layer Stack
**What**: Architectural layers
**Pass 1**: Conceptual layers in domain
**Pass 2**: System architecture layers
**Pass 3**: Instance deployment stack

#### (2e) Control Flow
**What**: How control moves through system
**Pass 1**: Natural domain progressions
**Pass 2**: System orchestration
**Pass 3**: Instance execution flow

#### (2f) Data Flow
**What**: How information moves
**Pass 1**: Information patterns in domain
**Pass 2**: System data pipelines
**Pass 3**: Instance data movement

#### (2g) Redundancy Plan
**What**: Backup and failover strategies
**Pass 1**: Domain resilience patterns
**Pass 2**: System fault tolerance
**Pass 3**: Instance backup needs

#### (2h) Architecture Spec
**What**: Complete architectural documentation
**Pass 1**: Domain structure specification
**Pass 2**: System architecture document
**Pass 3**: Instance configuration spec

---

## Phase 3: Domain-Specific Language (DSL)

**Purpose**: Define the vocabulary and grammar of the domain.

### Sub-steps:

#### (3a) Concept Tokenize
**What**: Identify atomic concepts
**Pass 1**: Core domain concepts
**Pass 2**: System terminology
**Pass 3**: Instance-specific terms

#### (3b) Syntax Define
**What**: How concepts combine
**Pass 1**: Domain relationship patterns
**Pass 2**: System expression rules
**Pass 3**: Instance configurations

#### (3c) Semantic Rules
**What**: Meaning and validity rules
**Pass 1**: What makes sense in domain
**Pass 2**: System validation rules
**Pass 3**: Instance constraints

#### (3d) Operator Set
**What**: Actions and transformations
**Pass 1**: Domain operations
**Pass 2**: System capabilities
**Pass 3**: Instance operations

#### (3e) Validation Tests
**What**: Verify correctness
**Pass 1**: Domain validity checks
**Pass 2**: System test cases
**Pass 3**: Instance validation

#### (3f) DSL Spec
**What**: Complete language specification
**Pass 1**: Domain vocabulary
**Pass 2**: System language spec
**Pass 3**: Instance expressions

---

## Phase 4: Topology

**Purpose**: Map out the network of components and their connections.

### Sub-steps:

#### (4a) Node Identify
**What**: Identify key components/nodes
**Pass 1**: Domain entities
**Pass 2**: System components
**Pass 3**: Instance elements

#### (4b) Edge Mapping
**What**: Define connections
**Pass 1**: Domain relationships
**Pass 2**: System integrations
**Pass 3**: Instance connections

#### (4c) Flow Weights
**What**: Quantify flows
**Pass 1**: Importance/frequency in domain
**Pass 2**: System load distribution
**Pass 3**: Instance usage patterns

#### (4d) Graph Build
**What**: Construct complete network
**Pass 1**: Domain relationship graph
**Pass 2**: System architecture diagram
**Pass 3**: Instance data graph

#### (4e) Simulation
**What**: Test the topology
**Pass 1**: Domain scenario modeling
**Pass 2**: System load testing
**Pass 3**: Instance simulation

#### (4f) Load Balance
**What**: Optimize distribution
**Pass 1**: Natural domain balance
**Pass 2**: System scaling strategy
**Pass 3**: Instance optimization

#### (4g) Topology Map
**What**: Final network documentation
**Pass 1**: Domain topology
**Pass 2**: System network map
**Pass 3**: Instance configuration

---

## Phase 5: Engineered System

**Purpose**: Build and deploy the actual system.

### Sub-steps:

#### (5a) Resource Allocate
**What**: Assign resources
**Pass 1**: Domain resource patterns
**Pass 2**: System requirements
**Pass 3**: Instance allocation

#### (5b) Prototype Build
**What**: Create initial version
**Pass 1**: Domain exemplars
**Pass 2**: System prototype
**Pass 3**: Instance creation

#### (5c) Integration Test
**What**: Verify components work together
**Pass 1**: Domain coherence
**Pass 2**: System integration
**Pass 3**: Instance validation

#### (5d) Deploy
**What**: Put into production
**Pass 1**: Domain instantiation
**Pass 2**: System deployment
**Pass 3**: Instance launch

#### (5e) Monitor
**What**: Track performance
**Pass 1**: Domain quality metrics
**Pass 2**: System monitoring
**Pass 3**: Instance tracking

#### (5f) Stress Test
**What**: Test limits
**Pass 1**: Domain edge cases
**Pass 2**: System load testing
**Pass 3**: Instance stress test

#### (5g) Operational System
**What**: Final running system
**Pass 1**: Living domain instance
**Pass 2**: Production system
**Pass 3**: Active instance

---

## Phase 6: Feedback Loop

**Purpose**: Learn from operation and improve continuously.

### Sub-steps:

#### (6a) Telemetry Capture
**What**: Collect operational data
**Pass 1**: Domain evolution tracking
**Pass 2**: System metrics
**Pass 3**: Instance analytics

#### (6b) Anomaly Detection
**What**: Identify unusual patterns
**Pass 1**: Domain irregularities
**Pass 2**: System anomalies
**Pass 3**: Instance issues

#### (6c) Drift Analysis
**What**: Track changes over time
**Pass 1**: Domain evolution
**Pass 2**: System drift
**Pass 3**: Instance changes

#### (6d) Constraint Refit
**What**: Adjust constraints based on learning
**Pass 1**: Domain understanding evolution
**Pass 2**: System tuning
**Pass 3**: Instance optimization

#### (6e) DSL Adjust
**What**: Evolve the language
**Pass 1**: Domain vocabulary growth
**Pass 2**: System language updates
**Pass 3**: Instance expressions

#### (6f) Architecture Patch
**What**: Update architecture
**Pass 1**: Domain model refinement
**Pass 2**: System improvements
**Pass 3**: Instance upgrades

#### (6g) Topology Rewire
**What**: Adjust connections
**Pass 1**: Domain relationship updates
**Pass 2**: System topology changes
**Pass 3**: Instance rewiring

#### (6h) Redeploy
**What**: Deploy improvements
**Pass 1**: Domain model update
**Pass 2**: System upgrade
**Pass 3**: Instance refresh

#### (6i) Goal Alignment Check
**What**: Verify still meeting objectives
**Pass 1**: Domain purpose alignment
**Pass 2**: System goal check
**Pass 3**: Instance success verify

---

## The Loop Back

After Phase 6, the workflow loops back to Phase 0 with:
- Deeper understanding
- Refined goals
- Improved system
- Better instances

Each loop is not repetition but evolution - a spiral of continuous improvement.
