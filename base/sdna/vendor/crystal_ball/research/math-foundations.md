# Crystal Ball - Mathematical Foundations

## Core Concepts

### 1. Basin of Attraction
A **basin of attraction** is the set of initial conditions that lead to a particular attractor.

For Crystal Ball:
- Each locked configuration defines a basin
- Basin Order 1: Input space (initial configurations)
- Basin Order 2: Transition space (possible moves)
- Basin Order 3: Meta-control space (strategies over transitions)

### 2. Attractors
An **attractor** is a set of states toward which a system evolves.

Types:
- **Point attractor**: Single stable state
- **Cycle attractor**: Periodic orbit
- **Strange attractor**: Chaotic, fractal structure

For Crystal Ball:
- Coordinate configurations are attractors
- The DAG structure defines the phase space
- Superposition states are "wild" attractors

### 3. Phase Space
The **phase space** is the space of all possible states.

For Crystal Ball:
- Each node/attribute combination is a dimension
- Coordinates are points in this space
- The topology is induced by the DAG

### 4. Reachability as Basin Exploration

```
Reach(S, depth, policy) = Basin exploration from state S
- depth = how deep to explore
- policy = which transitions allowed
- primacy = ordering of children (which paths preferred)
- kNN = expand to k-nearest neighbors at each step
```

### 5. Basin Orders (from Crystal Ball spec)

| Order | Name | Description |
|-------|------|-------------|
| 1 | Input Space | The base configuration space |
| 2 | Transition Space | Valid transformations between configs |
| 3 | Meta-Control Space | Strategies over transitions (solution space) |

### 6. k-NN in Phase Space

k-NN (k-nearest neighbors) for expansion:
- Start with one point
- Expand to k nearest (by ontology distance)
- "Sense" = similarity metric from DAG structure

### 7. Observers and Attractors

An **observer** in this system is:
- A function that maps states to observations
- Observations are themselves Space-objects
- The "attractor" of observation = what the system converges to

### 8. The Tower as Stratified Dynamics

Each level of the tower is a dynamical system:
- Level 0: Base states (coordinates)
- Level 1: Observations about states (basin mapping)
- Level 2: Observations about observations (meta-basin)
- etc.

## Mathematical Mapping

| Crystal Ball Concept | Math Equivalent |
|---------------------|-----------------|
| Node | State in phase space |
| Coordinate | Point in configuration space |
| Slot selection | State transition |
| Superposition | Quantum-like uncertainty (multiple states) |
| Attribute spectrum | Degree of freedom / dimension |
| Transition | Function f: State → State |
| Policy | Set of allowed transitions |
| Basin | Set of states leading to attractor |
| k-NN expansion | Local exploration operator |
| Observation | Projection / measurement |

## Research Questions

1. How does the DAG topology induce metric on phase space?
2. What's the relationship between slot configuration and basin boundaries?
3. How do we compute attractors in this discrete space?
4. What's the complexity of basin enumeration?
5. How does primacy ordering affect basin structure?

## References

- Dynamical systems theory
- Basin of attraction (Wikipedia)
- Attractors and strange attractors
- Cellular automata phase space
- Graph dynamics
