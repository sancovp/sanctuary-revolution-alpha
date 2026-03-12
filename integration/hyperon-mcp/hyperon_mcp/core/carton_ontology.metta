;;; CARTON ONTOLOGY - Complete MeTTa Rules
;;;
;;; Three-relationship ontology with DAG cycle detection:
;;; - is_a: Class hierarchy (concept is_a parent_class)
;;; - part_of: Composition (concept part_of whole)
;;; - instantiates: Evidence/witness (concept instantiates class)
;;;
;;; All relationships are validated to prevent cycles before insertion.

;; ============================================================================
;; BASE TYPES
;; ============================================================================

(: Concept Type)
(: Class Type)
(: Instance Type)

(: is_a Relationship)
(: part_of Relationship)
(: instantiates Relationship)
(: auto_related_to Relationship)

;; ============================================================================
;; LIST OPERATIONS (required for Hyperon - not built-in!)
;; ============================================================================

;; car/cdr implementations for different list lengths
;; Hyperon matches patterns based on exact arity, so we need cases for each size

;; Single element
(= (car ($a)) $a)
(= (cdr ($a)) ())

;; Two elements
(= (car ($a $b)) $a)
(= (cdr ($a $b)) ($b))

;; Three elements
(= (car ($a $b $c)) $a)
(= (cdr ($a $b $c)) ($b $c))

;; Four elements
(= (car ($a $b $c $d)) $a)
(= (cdr ($a $b $c $d)) ($b $c $d))

;; Five elements (for safety)
(= (car ($a $b $c $d $e)) $a)
(= (cdr ($a $b $c $d $e)) ($b $c $d $e))

;; ============================================================================
;; REACHABILITY CHECKING (with visited tracking)
;; ============================================================================

;; Check if target is reachable from source via is_a edges
;; Uses visited list to prevent infinite loops
(= (reachable-is-a? $source $target $visited)
   (if (== $source $target)
       True  ;; Found target
       (if (member? $source $visited)
           False  ;; Already visited this node, stop
           (let $new-visited (cons $source $visited)
                (reachable-via-parents-is-a? $source $target $new-visited)))))

;; Check reachability through all parent edges
(= (reachable-via-parents-is-a? $source $target $visited)
   (let $parents (collapse (match &self (is_a $source $p) $p))
        (any-parent-reaches-is-a? $parents $target $visited)))

;; Check if any parent reaches target
(= (any-parent-reaches-is-a? $parents $target $visited)
   (if (== $parents ())
       False
       (if (reachable-is-a? (car $parents) $target $visited)
           True
           (any-parent-reaches-is-a? (cdr $parents) $target $visited))))

;; Check if target is reachable from source via part_of edges
(= (reachable-part-of? $source $target $visited)
   (if (== $source $target)
       True
       (if (member? $source $visited)
           False
           (let $new-visited (cons $source $visited)
                (reachable-via-wholes-part-of? $source $target $new-visited)))))

(= (reachable-via-wholes-part-of? $source $target $visited)
   (let $wholes (collapse (match &self (part_of $source $w) $w))
        (any-whole-reaches-part-of? $wholes $target $visited)))

(= (any-whole-reaches-part-of? $wholes $target $visited)
   (if (== $wholes ())
       False
       (if (reachable-part-of? (car $wholes) $target $visited)
           True
           (any-whole-reaches-part-of? (cdr $wholes) $target $visited))))

;; Check if target is reachable from source via instantiates edges
(= (reachable-instantiates? $source $target $visited)
   (if (== $source $target)
       True
       (if (member? $source $visited)
           False
           (let $new-visited (cons $source $visited)
                (reachable-via-classes-instantiates? $source $target $new-visited)))))

(= (reachable-via-classes-instantiates? $source $target $visited)
   (let $classes (collapse (match &self (instantiates $source $c) $c))
        (any-class-reaches-instantiates? $classes $target $visited)))

(= (any-class-reaches-instantiates? $classes $target $visited)
   (if (== $classes ())
       False
       (if (reachable-instantiates? (car $classes) $target $visited)
           True
           (any-class-reaches-instantiates? (cdr $classes) $target $visited))))

;; ============================================================================
;; CYCLE DETECTION (correct direction)
;; ============================================================================

;; For edge: (is_a $source $target)
;; Cycle exists if: $target is already reachable from $source
;; (adding edge would create: $source → ... → $target → $source)
(= (would-create-cycle-is-a? $source $target)
   (reachable-is-a? $source $target ()))

(= (would-create-cycle-part-of? $source $target)
   (reachable-part-of? $source $target ()))

(= (would-create-cycle-instantiates? $source $target)
   (reachable-instantiates? $source $target ()))

;; ============================================================================
;; VALIDATION PREDICATES
;; ============================================================================

;; Validate is_a relationship before adding
;; For edge (is_a $source $target): $target becomes parent of $source
;; Check if $source is reachable from $target (reversed params)
(= (valid-is-a? $source $target)
   (not (would-create-cycle-is-a? $target $source)))

;; Validate part_of relationship before adding
;; For edge (part_of $source $target): $target becomes whole of $source
;; Check if $source is reachable from $target (reversed params)
(= (valid-part-of? $source $target)
   (not (would-create-cycle-part-of? $target $source)))

;; Validate instantiates relationship before adding
;; For edge (instantiates $source $target): $target becomes template of $source
;; Check if $source is reachable from $target (reversed params)
(= (valid-instantiates? $source $target)
   (not (would-create-cycle-instantiates? $target $source)))

;; ============================================================================
;; SAFE ADD OPERATIONS (with validation)
;; ============================================================================

;; Safely add is_a relationship (validates first)
(= (safe-add-is-a $source $target)
   (if (valid-is-a? $source $target)
       (let $result (add-atom &self (is_a $source $target))
            (Success (is_a $source $target)))
       (Error (format-args "Cycle detected: {} is_a {}" ($source $target)))))

;; Safely add part_of relationship (validates first)
(= (safe-add-part-of $source $target)
   (if (valid-part-of? $source $target)
       (let $result (add-atom &self (part_of $source $target))
            (Success (part_of $source $target)))
       (Error (format-args "Cycle detected: {} part_of {}" ($source $target)))))

;; Safely add instantiates relationship (validates first)
(= (safe-add-instantiates $source $target)
   (if (valid-instantiates? $source $target)
       (let $result (add-atom &self (instantiates $source $target))
            (Success (instantiates $source $target)))
       (Error (format-args "Cycle detected: {} instantiates {}" ($source $target)))))

;; ============================================================================
;; BATCH ADD WITH VALIDATION
;; ============================================================================

;; Add multiple relationships of same type
(= (add-all-is-a $source $targets)
   (if (== $targets ())
       ()
       (let $head (car $targets)
            (let $tail (cdr $targets)
                 (cons (safe-add-is-a $source $head)
                       (add-all-is-a $source $tail))))))

(= (add-all-part-of $source $targets)
   (if (== $targets ())
       ()
       (let $head (car $targets)
            (let $tail (cdr $targets)
                 (cons (safe-add-part-of $source $head)
                       (add-all-part-of $source $tail))))))

(= (add-all-instantiates $source $targets)
   (if (== $targets ())
       ()
       (let $head (car $targets)
            (let $tail (cdr $targets)
                 (cons (safe-add-instantiates $source $head)
                       (add-all-instantiates $source $tail))))))



;; ============================================================================
;; QUERY HELPERS (for transitive closure)
;; ============================================================================

;; Get all direct is_a relationships for a concept
(= (get-is-a $concept)
   (match &self (is_a $concept $parent) $parent))

;; Get all direct part_of relationships for a concept
(= (get-part-of $concept)
   (match &self (part_of $concept $whole) $whole))

;; Get all direct instantiates relationships for a concept
(= (get-instantiates $concept)
   (match &self (instantiates $concept $class) $class))

;; Get all transitive is_a ancestors (with visited tracking)
(= (get-all-ancestors-is-a $concept)
   (get-ancestors-is-a $concept ()))

(= (get-ancestors-is-a $concept $visited)
   (if (member? $concept $visited)
       ()
       (let $new-visited (cons $concept $visited)
            (let $parents (collapse (match &self (is_a $concept $p) $p))
                 (append $parents (collect-ancestors-is-a $parents $new-visited))))))

(= (collect-ancestors-is-a $parents $visited)
   (if (== $parents ())
       ()
       (append (get-ancestors-is-a (car $parents) $visited)
               (collect-ancestors-is-a (cdr $parents) $visited))))

;; Get all transitive part_of ancestors
(= (get-all-ancestors-part-of $concept)
   (get-ancestors-part-of $concept ()))

(= (get-ancestors-part-of $concept $visited)
   (if (member? $concept $visited)
       ()
       (let $new-visited (cons $concept $visited)
            (let $wholes (collapse (match &self (part_of $concept $w) $w))
                 (append $wholes (collect-ancestors-part-of $wholes $new-visited))))))

(= (collect-ancestors-part-of $wholes $visited)
   (if (== $wholes ())
       ()
       (append (get-ancestors-part-of (car $wholes) $visited)
               (collect-ancestors-part-of (cdr $wholes) $visited))))

;; Get all transitive instantiates ancestors
(= (get-all-ancestors-instantiates $concept)
   (get-ancestors-instantiates $concept ()))

(= (get-ancestors-instantiates $concept $visited)
   (if (member? $concept $visited)
       ()
       (let $new-visited (cons $concept $visited)
            (let $classes (collapse (match &self (instantiates $concept $c) $c))
                 (append $classes (collect-ancestors-instantiates $classes $new-visited))))))

(= (collect-ancestors-instantiates $classes $visited)
   (if (== $classes ())
       ()
       (append (get-ancestors-instantiates (car $classes) $visited)
               (collect-ancestors-instantiates (cdr $classes) $visited))))

;; ============================================================================
;; UTILITY FUNCTIONS
;; ============================================================================

;; Check if item is member of list
(= (member? $item $list)
   (if (== $list ())
       False
       (if (== $item (car $list))
           True
           (member? $item (cdr $list)))))

;; Append two lists
(= (append $list1 $list2)
   (if (== $list1 ())
       $list2
       (cons (car $list1) (append (cdr $list1) $list2))))

;; ============================================================================
;; CONCEPT MANAGEMENT (calls grounded Python)
;; ============================================================================

;; These will be grounded at runtime to call Python I/O operations
;; The MCP server will bind these when loading the carton atomspace:
;;
;; !(bind! carton_io (py-atom "carton_hyperon.carton_io_operations"))
;; !(bind! py-get-existing-concepts (py-dot carton_io "get_existing_concepts"))
;; !(bind! py-auto-link-description (py-dot carton_io "auto_link_description"))
;; !(bind! py-find-mentioned-concepts (py-dot carton_io "find_mentioned_concepts"))
;; !(bind! py-create-concept-directories (py-dot carton_io "create_concept_directories"))
;; !(bind! py-write-description-file (py-dot carton_io "write_description_file"))
;; !(bind! py-write-relationship-file (py-dot carton_io "write_relationship_file"))
;; !(bind! py-write-main-concept-file (py-dot carton_io "write_main_concept_file"))
;; !(bind! py-write-itself-file (py-dot carton_io "write_itself_file"))
;; !(bind! py-string-concat (py-dot carton_io "concat"))

;; Add concept with validation and file I/O
;; Input: (add-concept Name Description RelationshipsDict BasePath)
;; RelationshipsDict format: ((is_a (Parent1 Parent2)) (part_of (Whole1)))
;; Uses nested chain for grounded function execution (chain evaluates before binding)
;; IMPORTANT: All intermediate results MUST be referenced in final expression or chains won't execute (lazy evaluation)
;; Add concept - CORRECT metta-motto pattern
;; MeTTa ONLY validates and adds atoms to atomspace
;; File I/O happens SEPARATELY in Python by reading atomspace
(= (add-concept $name $rels)
   (if (== $rels ())
       (Error "No relationships provided")
       (validate-and-add-all $name $rels)))

;; Merge explicit relationships with auto-discovered ones
;; IMPORTANT: Cannot use 'let' inside functions called from 'chain' - it doesn't evaluate properly
(= (merge-with-auto-rels $rels $auto-mentioned)
   (if (== $auto-mentioned ())
       $rels
       (cons (list auto_related_to $auto-mentioned) $rels)))

;; Check if a result is an Error
(= (is-error? (Error $msg)) True)
(= (is-error? $x) False)

;; Check if a list contains any errors
(= (has-error? $list)
   (if (== $list ())
       False
       (if (is-error? (car $list))
           True
           (has-error? (cdr $list)))))

;; Get first error from a list
(= (get-first-error $list)
   (if (== $list ())
       (Error "Unknown error")
       (if (is-error? (car $list))
           (car $list)
           (get-first-error (cdr $list)))))

;; Validate and add all relationships to atomspace
(= (validate-and-add-all $name $rels)
   (if (== $rels ())
       Valid
       (let $head (car $rels)
            (let $tail (cdr $rels)
                 (let $rel-type (car $head)
                      (let $targets (car (cdr $head))
                           (let $results (add-relationships-by-type $name $rel-type $targets)
                                (if (has-error? $results)
                                    (get-first-error $results)
                                    (validate-and-add-all $name $tail)))))))))

;; Add relationships based on type
(= (add-relationships-by-type $name $rel-type $targets)
   (if (== $rel-type is_a)
       (add-all-is-a $name $targets)
       (if (== $rel-type part_of)
           (add-all-part-of $name $targets)
           (if (== $rel-type instantiates)
               (add-all-instantiates $name $targets)
               ;; For other types like auto_related_to, just add directly
               (add-generic-relationships $name $rel-type $targets)))))

;; Add generic relationships without cycle checking
(= (add-generic-relationships $name $rel-type $targets)
   (if (== $targets ())
       ()
       (let $head (car $targets)
            (let $tail (cdr $targets)
                 (cons (add-atom &self ($rel-type $name $head))
                       (add-generic-relationships $name $rel-type $tail))))))

;; Write all concept files via grounded Python - uses chain for grounded functions
;; IMPORTANT: All intermediate results MUST be referenced in final expression or chains won't execute (lazy evaluation)
(= (write-concept-files $name $linked-desc $merged-rels $base-path)
   (chain (py-create-concept-directories $base-path $name) $concept-path
        (chain (py-write-description-file $base-path $name $linked-desc) $desc-file
             (chain (write-all-relationship-files $name $merged-rels $base-path) $rel-files
                  (chain (py-write-main-concept-file $base-path $name $linked-desc $merged-rels) $main-file
                       (chain (py-write-itself-file $base-path $name $linked-desc $merged-rels) $itself-file
                            (files-written $concept-path $desc-file $main-file $itself-file $rel-files)))))))

;; Write relationship files for each relationship type - uses let bindings
(= (write-all-relationship-files $name $rels $base-path)
   (if (== $rels ())
       ()
       (cons (py-write-relationship-file $base-path $name (car (car $rels)) (car (cdr (car $rels))))
             (write-all-relationship-files $name (cdr $rels) $base-path))))
