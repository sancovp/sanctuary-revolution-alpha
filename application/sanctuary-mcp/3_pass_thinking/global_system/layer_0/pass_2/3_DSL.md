# Pass 2: GENERALLY REIFY - Domain-Specific Language
## Generator Template Language and Specification Formats

**Pass Question**: How do we BUILD systems that CREATE meta-circular bootstrapping frameworks?
**Layer**: 0 (System-Level Design)
**Date**: 2025-10-15

---

## (3a) Concept Tokenize

### Generator-Specific Concepts

**Template Concepts**:
- `template`: Reusable generation pattern
- `template_id`: Unique template identifier
- `template_version`: Version number (semantic versioning)
- `template_dependencies`: Required prior templates
- `template_variables`: Parameterizable slots
- `template_body`: MeTTa pattern to instantiate

**Domain Specification Concepts**:
- `domain_name`: Human-readable domain identifier
- `domain_concept`: Entity in domain ontology
- `domain_relationship`: Connection between concepts
- `y2_vocabulary`: Domain-specific terms for Y₂
- `y3_operations`: Domain-specific operations for Y₃
- `success_criteria`: What "working" means for this domain

**Blueprint Concepts**:
- `blueprint`: Complete instance specification
- `blueprint_id`: Unique identifier
- `uarl_primitives`: 9 UARL predicates to instantiate
- `dual_chains`: τ and β specifications
- `y_strata`: Y₁-Y₆ level specifications
- `validation_rules`: Checks to run

**Instance Concepts**:
- `instance`: Generated framework
- `instance_id`: Unique identifier
- `atomspace_id`: Associated AtomSpace
- `namespace`: Instance isolation prefix
- `status`: Generation lifecycle state

**Validation Concepts**:
- `validation_rule`: Correctness check
- `validation_checkpoint`: When to validate
- `validation_result`: Pass/fail with details
- `validation_severity`: Error/warning/info

**Generation Concepts**:
- `generation_request`: User initiates generation
- `generation_context`: Current generation state
- `generation_step`: Individual operation
- `generation_result`: Success/failure outcome

**Meta-Circular Concepts**:
- `self_representation`: Generator represents self
- `self_modification`: Generator modifies self
- `self_improvement`: Generator improves self
- `pattern_extraction`: Y₅ activity
- `template_optimization`: Y₆ activity

### Inherited from Pass 1 (UARL)

**Primitive Predicates** (used in templates):
- `is_a`, `part_of`, `instantiates`
- `embodies`, `manifests`, `reifies`
- `programs`, `validates`, `vehicularizes`

**Y-Strata Levels** (template targets):
- `Y1`, `Y2`, `Y3`, `Y4`, `Y5`, `Y6`

**Dual Chain Components** (validation targets):
- `tau_chain`: Top-down (is_a → part_of → instantiates)
- `beta_chain`: Bottom-up (embodies → manifests → reifies)
- `dc_complete`: Both chains present

---

## (3b) Syntax Define

### Template Language Syntax

**Template Definition**:
```yaml
template:
  id: string                          # Unique identifier
  version: semver                     # e.g., "1.2.3"
  target_y_level: Y1 | Y2 | Y3 | Y4 | Y5 | Y6
  dependencies: [template_id*]        # Prerequisites
  variables: {var_name: type}         # Parameterizable slots
  validation: [validation_rule*]      # Pre-instantiation checks
  body: metta_pattern                 # Template content
  metadata:
    author: string
    description: string
    created: timestamp
    last_modified: timestamp
```

**Template Body Syntax** (MeTTa with variables):
```metta
; Variable substitution using ${variable_name}
(${concept_name} is_a ${parent_concept})
(${concept_name} part_of ${system_name})

; Conditional inclusion
@if ${include_validation}
  (validates ${concept_name} ${validator})
@endif

; Iteration over lists
@foreach ${child_concept} in ${child_concepts}
  (${concept_name} is_a ${child_concept})
@endforeach

; Template composition
@include template:${dependency_template_id}
  with {concept: ${concept_name}}
```

**Domain Specification Syntax**:
```yaml
domain:
  name: string                        # Domain identifier
  description: string                 # Human-readable

  concepts:                           # Y₂ vocabulary
    - name: string
      parent: string | null           # Inherits from
      attributes: [string*]
      relationships: [{type, target}*]

  operations:                         # Y₃ operational templates
    - name: string
      inputs: [{name, type}*]
      outputs: [{name, type}*]
      preconditions: [expression*]
      postconditions: [expression*]

  success_criteria:                   # Instance validation
    structural: [check*]
    operational: [check*]
    performance: {metric: threshold}
```

**Blueprint Syntax**:
```yaml
blueprint:
  id: string
  domain: domain_name

  uarl_section:
    primitives: [is_a, part_of, ...]  # All 9 required

  dual_chains:
    - concept: string
      tau: [is_a, part_of, instantiates]
      beta: [embodies, manifests, reifies]
      programs_target: string | null

  y_strata:
    Y1: {templates: [id*], status: complete}
    Y2: {concepts: [name*], injected_from: domain}
    Y3: {operations: [name*], injected_from: domain}
    Y4: {instances: [id*], execution_ready: bool}
    Y5: {patterns: [id*], extraction_active: bool}
    Y6: {implementations: [id*], generation_active: bool}

  validation_checkpoints:
    - after_step: string
      rules: [rule_id*]
```

**Validation Rule Syntax**:
```yaml
validation_rule:
  id: string
  type: structural | semantic | operational | metacircular
  severity: error | warning | info

  condition: expression               # When to check

  check:
    query: metta_query               # What to query
    expected: pattern | value        # What should be true

  on_failure:
    message: string                  # User-facing error
    rollback: bool                   # Rollback instance?
    suggestions: [string*]           # How to fix
```

**Generation Request Syntax**:
```yaml
generation_request:
  domain_spec: path | inline_yaml
  instance_id: string | auto

  options:
    timeout: duration                # e.g., "5m"
    validation_level: strict | normal | permissive
    enable_telemetry: bool

  overrides:                         # Advanced customization
    templates: {id: path}            # Use custom templates
    validation: {id: enabled}        # Enable/disable rules
```

---

## (3c) Semantic Rules

### SR1: Template Dependency Resolution
```
Rule: Templates MUST be instantiated in dependency order
Validation:
  - Build dependency DAG
  - Topological sort
  - Detect cycles (error: circular dependency)
Enforcement: Blueprint Assembler (M3)
```

### SR2: Variable Substitution Completeness
```
Rule: All template variables MUST be bound before instantiation
Validation:
  - Parse template body
  - Extract ${variables}
  - Check all present in variables mapping
  - Error if unbound
Enforcement: Pattern Library Manager (M1)
```

### SR3: Domain Ontology Consistency
```
Rule: Domain concepts MUST form valid ontology
Validation:
  - All parent concepts exist
  - No orphaned concepts (except roots)
  - Relationships reference valid concepts
  - No cycles in is_a hierarchy
Enforcement: Domain Adapter (M2)
```

### SR4: Y-Level Progression
```
Rule: Templates MUST target appropriate Y-level
Validation:
  - Y₁ templates: Only UARL primitives
  - Y₂ templates: Domain concepts + primitives
  - Y₃ templates: Operations using Y₂ concepts
  - Y₄-Y₆ templates: Execution layer
Enforcement: Blueprint Assembler (M3)
```

### SR5: Dual Chain Completeness in Templates
```
Rule: If template creates programs relationship, MUST ensure dual chains
Validation:
  - Check template creates both τ and β
  - Verify DC(x) = τ(x) ∧ β(x) before programs
  - Error if programs without dual chains
Enforcement: Relationship Builder (M5), Validation Suite (M8)
```

### SR6: Fibration Preservation
```
Rule: Templates MUST NOT violate fibration properties
Validation:
  - Y₁-Y₃ templates: No cycles allowed
  - Y₄-Y₆ templates: Cycles permitted
  - Cross-layer relationships: Follow hierarchy
Enforcement: Relationship Builder (M5)
```

### SR7: vehicularizes Structure Preservation
```
Rule: Templates marking vehicularizes MUST preserve structure σ
Validation:
  - Document structure σ in template
  - Verify transformation preserves σ
  - Check subtypes mineable after reification
Enforcement: Relationship Builder (M5)
```

### SR8: Validation Rule Severity
```
Rule: Validation failures MUST respect severity
Semantics:
  - error: Block generation, rollback
  - warning: Log, continue with user confirmation
  - info: Log only, always continue
Enforcement: Validation Suite (M8)
```

### SR9: Template Versioning
```
Rule: Template updates MUST follow semantic versioning
Semantics:
  - Major: Breaking changes (incompatible)
  - Minor: New features (backward compatible)
  - Patch: Bug fixes only
Enforcement: Pattern Library Manager (M1)
```

### SR10: Blueprint Completeness
```
Rule: Blueprints MUST specify all required sections
Required:
  - domain reference
  - uarl_section with all 9 primitives
  - At least one dual_chain
  - y_strata with all 6 levels
  - validation_checkpoints
Enforcement: Blueprint Assembler (M3)
```

### SR11: Instance Isolation
```
Rule: Instances MUST NOT share state
Enforcement:
  - Separate AtomSpace per instance
  - Namespace prefixing: instance_id/concept_name
  - No cross-instance queries
Enforcement: AtomSpace Provisioner (M4)
```

### SR12: Meta-Circular Consistency
```
Rule: Generator's own representation MUST be valid instance
Validation:
  - Generator structure follows same rules as instances
  - Generator has complete dual chains
  - Generator Y₄-Y₅-Y₆ cycle active
Enforcement: Self-Improvement Engine (M10)
```

---

## (3d) Operator Set

### Template Operators

**O1: template_load(id, version?) → template**
```
Description: Load template from pattern library
Parameters:
  - id: Template identifier
  - version: Optional specific version (default: latest)
Returns: Template object or error
Usage: Pattern Library Manager (M1)
```

**O2: template_instantiate(template, bindings) → atoms**
```
Description: Instantiate template with variable bindings
Parameters:
  - template: Template object
  - bindings: {variable: value} mapping
Returns: MeTTa atoms to add to AtomSpace
Process:
  1. Validate bindings complete (SR2)
  2. Substitute variables in template body
  3. Process directives (@if, @foreach, @include)
  4. Return expanded MeTTa atoms
Usage: Blueprint Assembler (M3), Relationship Builder (M5)
```

**O3: template_compose([template*], bindings) → composite_template**
```
Description: Compose multiple templates respecting dependencies
Parameters:
  - templates: List of template IDs
  - bindings: Shared variable bindings
Returns: Single composed template
Process:
  1. Resolve dependencies (SR1)
  2. Topological sort
  3. Merge bodies in order
  4. Combine validation rules
Usage: Blueprint Assembler (M3)
```

**O4: template_validate(template) → validation_result**
```
Description: Validate template well-formedness
Checks:
  - Syntax valid
  - Dependencies exist
  - Variables typed correctly
  - MeTTa patterns parseable
Returns: Pass/fail with details
Usage: Pattern Library Manager (M1)
```

### Domain Operators

**O5: domain_parse(spec) → domain_model**
```
Description: Parse domain specification into internal model
Parameters:
  - spec: YAML domain specification
Returns: Validated domain model
Process:
  1. Parse YAML syntax
  2. Validate ontology consistency (SR3)
  3. Extract Y₂ vocabulary, Y₃ operations
  4. Build internal representation
Usage: Domain Adapter (M2)
```

**O6: domain_inject(blueprint, domain_model) → enriched_blueprint**
```
Description: Inject domain concepts into blueprint
Parameters:
  - blueprint: Base blueprint
  - domain_model: Validated domain
Returns: Blueprint with domain customizations
Process:
  1. Map domain concepts to Y₂ templates
  2. Map domain operations to Y₃ templates
  3. Update blueprint y_strata section
  4. Preserve Y₁ primitives
Usage: Blueprint Assembler (M3)
```

### Blueprint Operators

**O7: blueprint_assemble(domain_model, templates) → blueprint**
```
Description: Assemble complete blueprint from components
Parameters:
  - domain_model: Domain specification
  - templates: Selected templates
Returns: Complete blueprint ready for instantiation
Process:
  1. Create blueprint structure
  2. Add UARL primitives section
  3. Add dual chain specifications
  4. Add Y-strata sections (Y₁-Y₆)
  5. Add validation checkpoints
  6. Inject domain customizations (O6)
  7. Validate completeness (SR10)
Usage: Blueprint Assembler (M3)
```

**O8: blueprint_validate(blueprint) → validation_result**
```
Description: Validate blueprint completeness and correctness
Checks:
  - All required sections present (SR10)
  - Templates dependencies resolved
  - Y-level progression valid (SR4)
  - Dual chains specified
  - Validation rules complete
Returns: Pass/fail with details
Usage: Validation Suite (M8)
```

### Instance Operators

**O9: instance_create(blueprint) → instance_handle**
```
Description: Create instance from blueprint
Parameters:
  - blueprint: Validated blueprint
Returns: Handle to new instance
Process:
  1. Create isolated AtomSpace (O10)
  2. Initialize with UARL primitives
  3. Establish dual chains (O11)
  4. Scaffold Y-strata (O12)
  5. Mark vehicularizes patterns
  6. Activate cycle (O13)
  7. Enable meta-circular (O14)
  8. Run validation (O15)
Usage: AtomSpace Provisioner (M4), orchestrating M5-M8
```

**O10: atomspace_create(instance_id) → atomspace_handle**
```
Description: Create isolated AtomSpace for instance
Parameters:
  - instance_id: Unique identifier
Returns: AtomSpace handle
Configuration:
  - Namespace: instance_id/
  - Persistence: Enabled
  - Isolation: Full
Usage: AtomSpace Provisioner (M4)
```

**O11: dual_chain_establish(concept, atomspace) → dc_status**
```
Description: Establish dual chains for concept
Parameters:
  - concept: Concept name
  - atomspace: Target AtomSpace
Returns: DC complete status
Process:
  1. Create τ chain: is_a → part_of → instantiates
  2. Create β chain: embodies → manifests → reifies
  3. Verify DC(x) = τ(x) ∧ β(x)
  4. Mark programs if complete
Usage: Relationship Builder (M5)
```

**O12: y_strata_scaffold(blueprint, atomspace) → y_structure**
```
Description: Scaffold complete Y-strata structure
Parameters:
  - blueprint: Contains Y₁-Y₆ specifications
  - atomspace: Target AtomSpace
Returns: Y-strata structure status
Process:
  - Y₁: UARL primitives (already present)
  - Y₂: Inject domain ontology
  - Y₃: Create operational templates
  - Y₄: Initialize instance layer
  - Y₅: Initialize pattern extraction
  - Y₆: Initialize implementation generation
  - Verify fibration (SR6)
Usage: Relationship Builder (M5)
```

**O13: cycle_activate(instance) → cycle_status**
```
Description: Activate Y₄-Y₅-Y₆ perpetual cycle
Parameters:
  - instance: Instance handle
Returns: Cycle status (active/failed)
Process:
  1. Verify relationships complete
  2. Connect Y₄ → Y₅ (manifests)
  3. Connect Y₅ → Y₆ (reifies → programs)
  4. Connect Y₆ → Y₄ (instantiates)
  5. Start monitoring
Usage: Cycle Engine (M6)
```

**O14: metacircular_enable(instance) → capabilities**
```
Description: Enable self-* capabilities
Parameters:
  - instance: Instance handle
Returns: Enabled capabilities list
Process:
  1. Enable self-representation
  2. Enable self-modification
  3. Enable self-query interface
  4. Initialize convergence monitoring
Usage: Meta-Circular Enabler (M7)
```

**O15: instance_validate(instance, rules) → validation_report**
```
Description: Validate instance against rules
Parameters:
  - instance: Instance to validate
  - rules: Validation rules to run
Returns: Complete validation report
Process:
  1. Structural validation (dual chains, Y-strata)
  2. Semantic validation (UARL, vehicularizes)
  3. Operational validation (cycle, convergence)
  4. Meta-circular validation (self-*)
  5. Generate report
Usage: Validation Suite (M8)
```

### Feedback Operators

**O16: feedback_collect(instance) → telemetry**
```
Description: Collect operational telemetry from instance
Parameters:
  - instance: Running instance
Returns: Telemetry data
Collected:
  - Cycle times (Y₄-Y₅-Y₆)
  - Query patterns
  - Convergence measures
  - Anomalies
Usage: Feedback Collector (M9)
```

**O17: pattern_extract(feedback_data) → patterns**
```
Description: Extract reusable patterns from feedback (Y₅)
Parameters:
  - feedback_data: Aggregated telemetry
Returns: Candidate patterns
Process:
  1. Identify common generation sequences
  2. Generalize from specific instances
  3. Abstract to templates
  4. Validate extracted patterns
Usage: Self-Improvement Engine (M10)
```

**O18: template_optimize(template, performance_data) → optimized_template**
```
Description: Optimize template based on performance (Y₆)
Parameters:
  - template: Template to improve
  - performance_data: Metrics from usage
Returns: Optimized template
Optimizations:
  - Reduce generation time
  - Improve validation accuracy
  - Better error messages
  - More efficient MeTTa patterns
Usage: Self-Improvement Engine (M10)
```

**O19: self_improve(generator, improvements) → updated_generator**
```
Description: Apply improvements to generator itself (Y₄)
Parameters:
  - generator: Generator instance
  - improvements: Optimized templates
Returns: Updated generator
Process:
  1. Validate improvements
  2. Version old templates
  3. Update pattern library
  4. Test new templates
  5. Measure improvement delta
Usage: Self-Improvement Engine (M10)
```

---

## (3e) Validation Tests

### VT1: Template Syntax Validation
```
Test: template_validate(load("test_template.yaml"))
Expected: Pass if syntax correct, fail with details if not
Validates: O4, SR2
Test Cases:
  - Valid template: Pass
  - Missing required field: Fail("missing 'body'")
  - Invalid MeTTa: Fail("MeTTa parse error")
  - Unbound variables: Fail("variable '${x}' unbound")
```

### VT2: Template Dependency Resolution
```
Test: template_compose(["A", "B", "C"], bindings)
Expected: Topological order respecting dependencies
Validates: O3, SR1
Test Cases:
  - Linear deps (A→B→C): [A, B, C]
  - Parallel deps (A→C, B→C): [A, B, C] or [B, A, C]
  - Circular deps: Error("circular dependency detected")
```

### VT3: Domain Ontology Consistency
```
Test: domain_parse(domain_spec)
Expected: Valid domain model or specific errors
Validates: O5, SR3
Test Cases:
  - Valid ontology: domain_model
  - Missing parent: Error("parent 'X' not defined")
  - Orphaned concept: Error("concept 'Y' unreachable")
  - Cyclic is_a: Error("cycle in is_a hierarchy")
```

### VT4: Blueprint Completeness
```
Test: blueprint_validate(assembled_blueprint)
Expected: Pass if all sections present
Validates: O8, SR10
Test Cases:
  - Complete blueprint: Pass
  - Missing uarl_section: Fail("required section missing")
  - Empty dual_chains: Fail("at least one dual chain required")
  - Missing Y-level: Fail("Y₃ specification missing")
```

### VT5: Dual Chain Establishment
```
Test: dual_chain_establish("TestConcept", atomspace)
  verify: DC(TestConcept) = True
Expected: Both τ and β chains created
Validates: O11, SR5
Test Cases:
  - Create both chains: DC = True
  - Only τ created: DC = False
  - programs without DC: Error("dual chain incomplete")
```

### VT6: Y-Strata Fibration
```
Test: y_strata_scaffold(blueprint, atomspace)
  verify: no_cycles(Y1-Y3) AND cycles_allowed(Y4-Y6)
Expected: Fibration properties maintained
Validates: O12, SR6
Test Cases:
  - Valid Y₁-Y₃ DAG: Pass
  - Cycle in Y₂: Fail("cycle detected in Y₂")
  - Missing Y₄-Y₅-Y₆ cycle: Fail("execution cycle not established")
```

### VT7: vehicularizes Structure Preservation
```
Test: For pattern P with structure σ
  mark: vehicularizes(P)
  reify: P → Class C
  verify: σ preserved in C and subtypes mineable
Expected: Structure preservation validated
Validates: SR7
Test Cases:
  - Structure preserved: Pass
  - Structure lost: Fail("isomorphism broken")
  - Subtypes not mineable: Fail("no subtypes extractable")
```

### VT8: Cycle Activation
```
Test: cycle_activate(instance)
  verify: cycle_running AND convergence_measurable
Expected: Y₄-Y₅-Y₆ cycle operational
Validates: O13
Test Cases:
  - Cycle starts: cycle_status = active
  - Relationships incomplete: Fail("prerequisites not met")
  - Cycle time decreasing: convergence_progress > 0
```

### VT9: Meta-Circular Capabilities
```
Test: metacircular_enable(instance)
  verify: can_self_query AND can_self_modify
Expected: All self-* capabilities active
Validates: O14
Test Cases:
  - Self-query: instance.query("what am I?") returns description
  - Self-modify: instance.update(atom) affects behavior
  - Self-improve: instance convergence measurable
```

### VT10: Instance Validation Suite
```
Test: instance_validate(generated_instance, all_rules)
Expected: Comprehensive validation report
Validates: O15
Test Cases:
  - Perfect instance: All checks pass
  - Missing dual chain: Structural validation fails
  - Broken fibration: Semantic validation fails
  - Cycle inactive: Operational validation fails
  - No self-*: Meta-circular validation fails
```

### VT11: Pattern Extraction
```
Test: After 10 successful generations
  patterns = pattern_extract(feedback_data)
  verify: patterns.length > 0 AND patterns valid
Expected: Reusable patterns extracted
Validates: O17, generator Y₅ activity
Test Cases:
  - Common pattern found: Extracted successfully
  - Pattern validated: template_validate(pattern) = Pass
  - Pattern reusable: Can generate new instances
```

### VT12: Self-Improvement Cycle
```
Test: Complete generator Y₄-Y₅-Y₆ cycle
  1. Generate instances (Y₄)
  2. Extract patterns (Y₅)
  3. Optimize templates (Y₆)
  4. Apply to generator (Y₄)
  verify: generation_time(after) < generation_time(before)
Expected: Measurable improvement
Validates: O17-O19, SR12
Test Cases:
  - Improvement applied: New template version created
  - Performance better: Generation faster or more correct
  - Bootstrap cycle: Generator generates improved generator
```

---

## (3f) DSL Spec

### Complete Language Specification

**Purpose**: Define languages for generator system operation

**Three Sub-Languages**:

1. **Template Language**: For defining reusable generation patterns
2. **Domain Specification Language**: For describing target domains
3. **Validation Expression Language**: For defining correctness checks

### Template Language Specification

**Grammar** (YAML + MeTTa):
```ebnf
template ::= template_header template_body

template_header ::=
  "id:" STRING
  "version:" SEMVER
  "target_y_level:" Y_LEVEL
  "dependencies:" "[" template_id* "]"
  "variables:" "{" var_binding* "}"
  "validation:" "[" validation_rule* "]"

template_body ::= "body:" metta_with_directives

metta_with_directives ::=
  metta_atom
  | directive

directive ::=
  "@if" expression metta_atom* "@endif"
  | "@foreach" var "in" list metta_atom* "@endforeach"
  | "@include" template_ref "with" bindings

var ::= "${" IDENTIFIER "}"
```

**Type System**:
- `string`: Text values
- `concept`: Domain concept names
- `template_id`: Template identifiers
- `y_level`: Y₁ | Y₂ | Y₃ | Y₄ | Y₅ | Y₆
- `metta_pattern`: Valid MeTTa expression
- `[type]`: List of type

**Semantics**:
- Variable substitution is textual replacement
- Directives processed before MeTTa parsing
- @if evaluates condition, includes body if true
- @foreach iterates, instantiating body each iteration
- @include composes templates

**Validation Rules**:
- All variables must be bound (SR2)
- Dependencies must exist and be acyclic (SR1)
- Target Y-level must be appropriate (SR4)
- MeTTa patterns must parse

### Domain Specification Language

**Grammar** (YAML):
```ebnf
domain_spec ::= domain_header concepts operations criteria

domain_header ::=
  "domain:"
  "  name:" STRING
  "  description:" STRING

concepts ::=
  "  concepts:"
  concept_def*

concept_def ::=
  "    - name:" STRING
  "      parent:" STRING | "null"
  "      attributes:" "[" STRING* "]"
  "      relationships:" "[" relationship* "]"

operations ::=
  "  operations:"
  operation_def*

operation_def ::=
  "    - name:" STRING
  "      inputs:" "[" typed_param* "]"
  "      outputs:" "[" typed_param* "]"
  "      preconditions:" "[" expression* "]"
  "      postconditions:" "[" expression* "]"

criteria ::=
  "  success_criteria:"
  "    structural:" "[" check* "]"
  "    operational:" "[" check* "]"
  "    performance:" "{" metric_threshold* "}"
```

**Type System**:
- All types from template language
- Plus domain-specific: `attribute`, `relationship`, `operation`, `check`

**Semantics**:
- Concepts form ontology for Y₂
- Operations become templates for Y₃
- Success criteria become validation rules
- Parent relationships create is_a hierarchy

**Validation Rules**:
- Ontology must be consistent (SR3)
- All referenced concepts must exist
- No cycles in is_a hierarchy
- Operations must be well-typed

### Validation Expression Language

**Grammar**:
```ebnf
validation_rule ::= rule_header rule_check

rule_header ::=
  "validation_rule:"
  "  id:" STRING
  "  type:" RULE_TYPE
  "  severity:" SEVERITY

rule_check ::=
  "  check:"
  "    query:" metta_query
  "    expected:" pattern | value

metta_query ::= "(match &self" pattern variables ")"

pattern ::= metta_atom with holes

RULE_TYPE ::= "structural" | "semantic" | "operational" | "metacircular"
SEVERITY ::= "error" | "warning" | "info"
```

**Semantics**:
- Queries executed against instance AtomSpace
- Expected pattern matched against query results
- Severity determines failure handling (SR8)

**Validation Rules**:
- Query must be valid MeTTa
- Expected must be checkable
- Type must match validation category

### Operator Semantics (Formal)

**Template Instantiation**:
```
⟦template⟧(bindings) =
  let body' = substitute(template.body, bindings) in
  parse_metta(body')

where substitute(body, bindings) =
  for each ${var} in body:
    replace with bindings[var]
```

**Domain Injection**:
```
⟦domain_inject⟧(blueprint, domain) =
  blueprint' where:
    blueprint'.y_strata.Y2 += domain.concepts
    blueprint'.y_strata.Y3 += domain.operations
    blueprint'.validation += domain.success_criteria
```

**Dual Chain Verification**:
```
DC(x) = τ(x) ∧ β(x)

where:
  τ(x) = ∃ path: x →(is_a)→ ... →(part_of)→ ... →(instantiates)→ ...
  β(x) = ∃ path: x →(embodies)→ ... →(manifests)→ ... →(reifies)→ ...

programs(x, y) iff DC(x) = True
```

**Fibration Enforcement**:
```
For Y-level L:
  if L ∈ {Y1, Y2, Y3}: graph(L) must be DAG
  if L ∈ {Y4, Y5, Y6}: graph(L) may have cycles

Verify:
  topological_sort(Y1 ∪ Y2 ∪ Y3) succeeds
  Y4 → Y5 → Y6 → Y4 cycle exists
```

### Error Handling

**Error Categories**:
1. **Syntax Error**: Invalid language syntax
2. **Semantic Error**: Valid syntax, invalid meaning
3. **Runtime Error**: Error during generation
4. **Validation Error**: Generated instance invalid

**Error Reporting Format**:
```yaml
error:
  category: syntax | semantic | runtime | validation
  severity: error | warning | info
  message: string                    # User-facing
  location:                          # Where error occurred
    file: string
    line: number
    column: number
  context: string                    # Relevant code snippet
  suggestions: [string*]             # How to fix
  related: [error_id*]               # Related errors
```

---

## Document Status

**Pass 2 Phase 3 Complete**: ✅ Complete DSL specification for generator system
**Ready For**: Phase 4 (Topology - Generator component relationships and flows)
**Languages Defined**: Template language, domain specification language, validation expression language
**Operators**: 19 operators (O1-O19) fully specified
**Validation Tests**: 12 comprehensive test specifications
**Key Innovation**: Composable template language with meta-circular self-improvement expressions
