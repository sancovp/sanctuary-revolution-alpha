"""Deduction_Chain — the typed CODE thing that, when attached to a code type,
promotes that code type to SYSTEM_TYPE in YOUKNOW.

A DeductionChain is any logical operation (Python function, Prolog rule, SHACL
constraint, callable class) that runs as an EXTRA check whenever a field of an
individual of the target system type is canonically filled in YOUKNOW.

Flow:
    1. This Python class exists in CODE.
    2. observe_codeness reflects it into the YOUKNOW ontology as the OWL class
       Deduction_Chain (one-to-one with the fields here).
    3. A system type's d-chains are DEFINED in YOUKNOW by emitting
       Deduction_Chain INDIVIDUALS through the normal admission path
       (Dragonbones EC → CartON add_concept → YOUKNOW).
    4. The compiler self-assembles those OWL individuals back into executable
       Python at compile time.
    5. When an individual of the system type has its arg canonically filled,
       all attached DeductionChain bodies fire as an extra typing step.

Attaching one or more DeductionChain instances to a code type IS the operation
that promotes that code type to SYSTEM_TYPE state.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class DeductionChain:
    # The system type this d-chain attaches to (e.g. "Claude_Code_Rule").
    target_type: str
    # The specific argument of that type this d-chain governs (e.g. "has_scope").
    # None = the d-chain operates at the type level (cross-arg invariant).
    argument_name: Optional[str]
    # The logic body, interpreted per body_type. Source string.
    body: str
    # How to execute the body.
    body_type: Literal[
        "python_function",
        "prolog_rule",
        "shacl_constraint",
        "callable_class",
    ]
    # Human-readable description of what this chain checks or produces.
    description: str = ""
    # Names of other DeductionChain individuals that must SAT before this one fires.
    depends_on: List[str] = field(default_factory=list)
