"""DeductionChain dispatch — OWL-driven.

In YOUKNOW, Python dicts only READ from the OWL. There is no `register()`
side-effect API. The Deduction_Chain individuals live in domain.owl. This
module:

  1. Reads Deduction_Chain individuals from the active domain.owl on demand
  2. Caches them in memory as a read-cache materialized from OWL
  3. Dispatches each chain's `body` via the `body_type` switch, all of which
     execute through YOUKNOW's Python sub-engines

The four body_types — every body executes through YOUKNOW's Python:
  - "python_function":  dotted path → import → call(arg_value, context)
  - "prolog_rule":      Prolog rule (text or id) → YOUKNOW Prolog runtime
  - "shacl_constraint": parametric check against existing uarl_shapes.ttl
  - "callable_class":   dotted path → import → instantiate → call

All four return one of:
  {"compose_arg": {key: value_list}}  -> fills an arg on the in-flight concept
  {"error": "<reason>"}               -> rejects with reason
  {"unnamed": "<for_arg>"}            -> places _Unnamed placeholder
  {}                                  -> chain contributes nothing
"""

import importlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChainIndividual:
    """In-memory view of a Deduction_Chain OWL individual.

    All fields are read from the OWL. This is the cache shape; the OWL is
    canonical.
    """
    name: str
    target_type: str
    argument_name: Optional[str]
    body: str
    body_type: str
    description: str = ""


_CACHE: Dict[Tuple[str, str], List[ChainIndividual]] = {}
_CACHE_LOADED = False


def _domain_owl_path() -> Path:
    """Resolve the active domain.owl path."""
    heaven_data_dir = os.environ.get("HEAVEN_DATA_DIR", "/tmp/heaven_data")
    return Path(heaven_data_dir) / "ontology" / "domain.owl"


def _chain_from_individual(g, ind, uarl) -> Optional[ChainIndividual]:
    """Build a ChainIndividual from a single OWL individual node."""
    import rdflib
    name = str(ind).split("#")[-1] if "#" in str(ind) else str(ind).split("/")[-1]
    target_type_val = next(g.objects(ind, uarl.hasTargetType), None)
    argument_name_val = next(g.objects(ind, uarl.hasArgumentName), None)
    body_val = next(g.objects(ind, uarl.hasBody), None)
    body_type_val = next(g.objects(ind, uarl.hasBodyType), None)
    desc_val = next(g.objects(ind, rdflib.RDFS.comment), None)
    if not (target_type_val and body_val and body_type_val):
        return None
    return ChainIndividual(
        name=name,
        target_type=str(target_type_val),
        argument_name=str(argument_name_val) if argument_name_val else None,
        body=str(body_val),
        body_type=str(body_type_val),
        description=str(desc_val) if desc_val else "",
    )


def _load_chains_from_owl() -> List[ChainIndividual]:
    """Read Deduction_Chain individuals from domain.owl.

    Best-effort. If domain.owl doesn't exist or rdflib unavailable, returns [].
    """
    chains: List[ChainIndividual] = []
    owl_path = _domain_owl_path()
    if not owl_path.exists():
        return chains
    try:
        import rdflib
        g = rdflib.Graph()
        g.parse(str(owl_path), format="xml")
        uarl = rdflib.Namespace("http://sanctuary.ai/uarl#")
        for ind in g.subjects(rdflib.RDF.type, uarl.Deduction_Chain):
            ci = _chain_from_individual(g, ind, uarl)
            if ci is not None:
                chains.append(ci)
    except Exception:
        logger.exception(f"Could not load Deduction_Chain individuals from {owl_path}")
    return chains


def _build_cache() -> None:
    """Build the (target_type, argument_name) → [chains] cache from OWL."""
    global _CACHE, _CACHE_LOADED
    _CACHE = {}
    for chain in _load_chains_from_owl():
        key = (chain.target_type, chain.argument_name or "__type_level__")
        _CACHE.setdefault(key, []).append(chain)
    _CACHE_LOADED = True
    logger.info(f"Loaded {sum(len(v) for v in _CACHE.values())} Deduction_Chain individuals from OWL")


def reload_from_owl() -> None:
    """Force a reload of the cache from OWL. For tests + post-write refresh."""
    _build_cache()


def get_chains_for(target_type: str, argument_name: str) -> List[ChainIndividual]:
    """Return Deduction_Chain individuals attached to (target_type, argument_name)."""
    if not _CACHE_LOADED:
        _build_cache()
    return _CACHE.get((target_type, argument_name), [])


def execute_chain(
    chain: ChainIndividual,
    arg_value: Any,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Dispatch a chain's body through YOUKNOW's Python sub-engine for its body_type.

    All four body_types execute through Python (YOUKNOW is Python). The
    body_type just selects which sub-engine handles the body content.
    """
    bt = chain.body_type
    try:
        if bt == "python_function":
            return _exec_python_function(chain.body, arg_value, context)
        if bt == "callable_class":
            return _exec_callable_class(chain.body, arg_value, context)
        if bt == "prolog_rule":
            return _exec_prolog_rule(chain.body, arg_value, context)
        if bt == "shacl_constraint":
            return _exec_shacl_constraint(chain.body, arg_value, context)
        logger.warning(f"Unknown body_type {bt!r} on chain {chain.name}")
        return {}
    except Exception as e:
        logger.warning(f"Chain {chain.name} body raised: {e}")
        return {}


def _resolve_dotted(path: str) -> Any:
    """Import 'module.sub:attr' and return the attribute."""
    if ":" not in path:
        raise ValueError(f"Expected 'module:attr' dotted path, got {path!r}")
    mod_path, attr = path.split(":", 1)
    mod = importlib.import_module(mod_path)
    return getattr(mod, attr)


def _exec_python_function(body: str, arg_value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    fn = _resolve_dotted(body)
    result = fn(arg_value, context)
    return result if isinstance(result, dict) else {}


def _exec_callable_class(body: str, arg_value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    cls = _resolve_dotted(body)
    instance = cls()
    result = instance(arg_value, context)
    return result if isinstance(result, dict) else {}


def _exec_prolog_rule(body: str, arg_value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Hand off to YOUKNOW's Prolog runtime.

    Body is a rule id or rule text. The runtime returns true/false. False is
    mapped to an error result; true is a passthrough (chain contributes nothing).
    """
    try:
        from ..prolog_runtime import query_rule  # type: ignore
    except Exception:
        logger.warning("Prolog runtime not available; skipping prolog_rule chain")
        return {}
    try:
        passes = bool(query_rule(body, arg_value=arg_value, context=context))
    except Exception as e:
        logger.warning(f"Prolog rule {body!r} raised: {e}")
        return {}
    if not passes:
        return {"error": f"prolog_rule {body!r} returned false"}
    return {}


def _exec_shacl_constraint(body: str, arg_value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Parametric admissibility check against uarl_shapes.ttl machinery.

    Body shape examples:
      "passes_shape:PIOEntityShape"
      "reaches_derivation_level:3"

    Returns error result on fail, empty dict on pass.
    """
    try:
        if body.startswith("reaches_derivation_level:"):
            min_level = int(body.split(":", 1)[1])
            from ..derivation import DerivationValidator  # type: ignore
            from ..owl_types import get_type_registry  # type: ignore
            validator = DerivationValidator(cat=get_type_registry())
            concept = {"name": context.get("__concept_name__", "unknown"), **context}
            state = validator.validate(concept)
            if state.level.value < min_level:
                return {"error": f"reaches_derivation_level:{min_level} fail (got L{state.level.value})"}
            return {}
        if body.startswith("passes_shape:"):
            try:
                from ..uarl_validator import UARLValidator  # type: ignore
                validator = UARLValidator()
                conforms, report = validator.validate_concept(context)
                if not conforms:
                    return {"error": f"passes_shape fail: {report}"}
            except Exception as e:
                logger.warning(f"UARLValidator not available for passes_shape check: {e}")
            return {}
    except Exception as e:
        logger.warning(f"shacl_constraint body {body!r} raised: {e}")
    return {}
