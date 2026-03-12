# Ontologize Inputs Pattern

## The Algorithm

When adding ANYTHING to CartON:

```
1. Get all input args
2. Turn each arg into a concept with relationships
3. Connect concepts to each other with typed relationships
4. Add as ONE batch observation
```

That's it. Every piece of data becomes a node. Every node connects to other nodes.

---

## Why This Matters

### Without ontology:
```
add_concept("GIINT_Project_X", "A project", [IS_A GIINT_Project])
```
- Isolated concept
- Can't reason about it
- Errors are just strings: "Error: missing spec"

### With ontology:
```
add_observation_batch({
  GIINT_Project_X: IS_A GIINT_Project, HAS_FEATURE Feature_A, PART_OF Starsystem_Y
  Feature_A: IS_A GIINT_Feature, PART_OF GIINT_Project_X, HAS_COMPONENT Component_B
  Component_B: IS_A GIINT_Component, PART_OF Feature_A, HAS_DELIVERABLE Deliverable_C
  Deliverable_C: IS_A GIINT_Deliverable, PART_OF Component_B, HAS_TASK Task_D
  Task_D: IS_A GIINT_Task, PART_OF Deliverable_C, HAS_STATUS Ready
})
```
- Connected graph
- Full reasoning: "Task_D is blocked because Deliverable_C has no spec, which is required for Components in GIINT_Projects"
- Errors trace the entire path

---

## The Pattern For Any Function

```python
def sync_X_to_carton(x_data: dict) -> dict:
    """
    Sync X to CartON with FULL ontology.

    Every input arg becomes a concept.
    Every concept connects to related concepts.
    """

    concepts = []

    # 1. The main concept
    main_concept = {
        "name": f"X_{x_data['id']}",
        "description": f"X instance: {x_data['id']}",
        "relationships": [
            {"relationship": "is_a", "related": ["X_Type"]},
            {"relationship": "part_of", "related": ["Parent_Container"]},
            # HAS_* for each child
        ]
    }
    concepts.append(main_concept)

    # 2. Each child becomes a concept
    for child_name, child_data in x_data.get('children', {}).items():
        child_concept = {
            "name": f"X_Child_{child_name}",
            "description": f"Child of X: {child_name}",
            "relationships": [
                {"relationship": "is_a", "related": ["X_Child_Type"]},
                {"relationship": "part_of", "related": [main_concept["name"]]},
            ]
        }
        concepts.append(child_concept)

        # Add HAS_CHILD to main concept
        main_concept["relationships"].append({
            "relationship": "has_child",
            "related": [child_concept["name"]]
        })

    # 3. Add ALL concepts in one batch
    observation_data = {
        "implementation": concepts,
        "confidence": 1.0
    }

    return add_observation_batch(observation_data)
```

---

## GIINT Project Example

Input: A Project with Features → Components → Deliverables → Tasks

Output observation batch:

```python
{
    "implementation": [
        # Project
        {
            "name": "GIINT_Project_MyApp",
            "description": "GIINT Project: MyApp at /path/to/myapp",
            "relationships": [
                {"relationship": "is_a", "related": ["GIINT_Project"]},
                {"relationship": "part_of", "related": ["Starsystem_Path_To_Myapp"]},
                {"relationship": "has_feature", "related": ["GIINT_Feature_MyApp_Auth", "GIINT_Feature_MyApp_UI"]}
            ]
        },
        # Feature: Auth
        {
            "name": "GIINT_Feature_MyApp_Auth",
            "description": "Feature: Auth",
            "relationships": [
                {"relationship": "is_a", "related": ["GIINT_Feature"]},
                {"relationship": "part_of", "related": ["GIINT_Project_MyApp"]},
                {"relationship": "has_component", "related": ["GIINT_Component_MyApp_Auth_Login"]}
            ]
        },
        # Component: Login
        {
            "name": "GIINT_Component_MyApp_Auth_Login",
            "description": "Component: Login",
            "relationships": [
                {"relationship": "is_a", "related": ["GIINT_Component"]},
                {"relationship": "part_of", "related": ["GIINT_Feature_MyApp_Auth"]},
                {"relationship": "has_deliverable", "related": ["GIINT_Deliverable_MyApp_Auth_Login_LoginPage"]}
            ]
        },
        # ... and so on for every node in the tree
    ],
    "confidence": 1.0
}
```

---

## Relationship Types

### Hierarchical (PART_OF / HAS_*)
- `PART_OF` - child points to parent
- `HAS_FEATURE` - project points to features
- `HAS_COMPONENT` - feature points to components
- `HAS_DELIVERABLE` - component points to deliverables
- `HAS_TASK` - deliverable points to tasks

### Typing (IS_A)
- Every instance IS_A its type
- `GIINT_Project_X IS_A GIINT_Project`
- `Task_Y IS_A GIINT_Task`

### Cross-cutting
- `DESCRIBES` - skill describes component
- `DEPENDS_ON` - X depends on Y
- `VALIDATES` - test validates component

---

## The Goal: Causal Pushdown

When CartON is **fully reflective**:

1. Every piece of data is ontologized
2. Every concept connects to related concepts
3. Queries can traverse the full graph
4. Errors can explain themselves via graph paths

Then: **Causal Pushdown**

- Add a concept to CartON → System manifests it
- The graph IS the source of truth
- You can THINK things into existence by adding them to CartON
- CartON becomes the generative substrate, not just a record

---

## Functions To Fix

| Function | Location | Status |
|----------|----------|--------|
| `sync_project_to_carton` | llm_intelligence/carton_sync.py | ✅ DONE |
| `sync_feature_to_carton` | llm_intelligence/carton_sync.py | ✅ DONE |
| `sync_component_to_carton` | llm_intelligence/carton_sync.py | ✅ DONE |
| `sync_deliverable_to_carton` | llm_intelligence/carton_sync.py | ✅ DONE |
| `sync_task_to_carton` | llm_intelligence/carton_sync.py | ✅ DONE |
| `update_task_in_carton` | llm_intelligence/carton_sync.py | ✅ DONE |
| `_sync_skill_to_carton` | skill_manager/core.py | ✅ DONE |
| `_sync_kardashev_to_carton` | starlog_mcp/starlog_mcp.py | ✅ DONE |
| `mirror_to_carton` | starlog_mcp/starlog.py | ✅ DONE |
| `_create_starsystem_entity` | starlog_mcp/starlog.py | ✅ DONE |

---

## Note

This doc will become a skill when complete:
- Category: `preflight`
- Name: `ontologize-inputs`
- Points to flight config for ontologizing any function
