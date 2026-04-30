"""Pattern fingerprinting — AST extraction, fingerprint building, similarity scoring.

Extracts class/function structure from Python files via AST, builds interface
fingerprints, and computes multi-dimensional similarity between fingerprints.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def _get_string_value(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _get_literal_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _get_name(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _get_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _extract_base_classes(cls_node: ast.ClassDef) -> List[str]:
    return [_get_name(b) for b in cls_node.bases if _get_name(b)]


def _extract_class_attrs(cls_node: ast.ClassDef) -> Dict[str, Any]:
    attrs = {}
    for item in cls_node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    val = _get_literal_value(item.value) or _get_name(item.value)
                    attrs[target.id] = val
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            attrs[item.target.id] = "<annotated>"
    return attrs


def _extract_methods(cls_node: ast.ClassDef) -> List[Dict[str, Any]]:
    methods = []
    for item in cls_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in item.args.args if a.arg not in ("self", "cls")]
            decorators = [_get_name(d) for d in item.decorator_list if _get_name(d)]
            methods.append({
                "name": item.name,
                "params": params,
                "is_async": isinstance(item, ast.AsyncFunctionDef),
                "decorators": decorators,
                "line_range": (item.lineno, item.end_lineno or item.lineno),
            })
    return methods


def _extract_dict_schema(cls_node: ast.ClassDef) -> List[Dict[str, str]]:
    """Extract argument definitions from dict-based schema classes."""
    args = []
    for item in cls_node.body:
        target = None
        if isinstance(item, ast.Assign) and item.targets:
            target = item.targets[0]
        elif isinstance(item, ast.AnnAssign):
            target = item.target

        if target and isinstance(target, ast.Name) and target.id == "arguments":
            value = item.value
            if isinstance(value, ast.Dict):
                for key, val in zip(value.keys, value.values):
                    arg_name = _get_string_value(key) if key else None
                    if arg_name and isinstance(val, ast.Dict):
                        arg_info = {"name": arg_name}
                        for ak, av in zip(val.keys, val.values):
                            k = _get_string_value(ak) if ak else None
                            v = _get_string_value(av)
                            if k and v:
                                arg_info[k] = v
                        args.append(arg_info)
    return args


def analyze_file(file_path: Path) -> Dict[str, Any]:
    """Parse a Python file and extract all class/function definitions."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        source = f.read()

    tree = ast.parse(source, filename=str(file_path))
    classes = {}
    top_functions = []
    import_from = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            classes[node.name] = {
                "bases": _extract_base_classes(node),
                "attrs": _extract_class_attrs(node),
                "methods": _extract_methods(node),
                "dict_schema": _extract_dict_schema(node),
                "line_range": (node.lineno, node.end_lineno or node.lineno),
            }
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            top_functions.append({
                "name": node.name,
                "params": [a.arg for a in node.args.args],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "line_range": (node.lineno, node.end_lineno or node.lineno),
            })
        elif isinstance(node, ast.ImportFrom) and node.module:
            import_from.append(node.module)

    return {
        "file": str(file_path),
        "classes": classes,
        "top_functions": top_functions,
        "import_from": import_from,
    }


def build_fingerprint(cls_name: str, cls_info: Dict, analysis: Dict) -> Dict[str, Any]:
    """Build an interface fingerprint for a class."""
    fp = {
        "class_name": cls_name,
        "file": analysis["file"],
        "bases": cls_info["bases"],
        "attrs": cls_info["attrs"],
        "method_names": [m["name"] for m in cls_info["methods"]],
        "method_params": {m["name"]: m["params"] for m in cls_info["methods"]},
        "has_async_methods": any(m["is_async"] for m in cls_info["methods"]),
        "decorator_set": {d for m in cls_info["methods"] for d in m["decorators"]},
        "dict_schema_args": [a["name"] for a in cls_info["dict_schema"]],
        "dict_schema_types": {a["name"]: a.get("type", "?") for a in cls_info["dict_schema"]},
        "has_classmethod_create": any(
            m["name"] == "create" and "classmethod" in m["decorators"]
            for m in cls_info["methods"]
        ),
    }

    func_ref = cls_info["attrs"].get("func")
    if func_ref:
        for fn in analysis["top_functions"]:
            if fn["name"] == func_ref:
                fp["standalone_func"] = {
                    "name": fn["name"],
                    "params": fn["params"],
                    "is_async": fn["is_async"],
                }
                break

    return fp


def compute_similarity(fp1: Dict, fp2: Dict) -> Dict[str, float]:
    """Compute multi-dimensional similarity between two fingerprints."""
    a1, a2 = set(fp1["attrs"].keys()), set(fp2["attrs"].keys())
    m1, m2 = set(fp1["method_names"]), set(fp2["method_names"])
    s1, s2 = set(fp1["dict_schema_args"]), set(fp2["dict_schema_args"])

    t1, t2 = fp1["dict_schema_types"], fp2["dict_schema_types"]
    common_types = set(t1) & set(t2)

    scores = {
        "attr_overlap": len(a1 & a2) / len(a1 | a2) if (a1 or a2) else 1.0,
        "method_overlap": len(m1 & m2) / len(m1 | m2) if (m1 or m2) else 1.0,
        "async_match": 1.0 if fp1["has_async_methods"] == fp2["has_async_methods"] else 0.0,
        "creation_style": 1.0 if fp1["has_classmethod_create"] == fp2["has_classmethod_create"] else 0.0,
        "schema_arg_overlap": len(s1 & s2) / len(s1 | s2) if (s1 or s2) else 1.0,
        "schema_type_match": (
            sum(1 for a in common_types if t1[a] == t2[a]) / len(common_types)
            if common_types else 0.0
        ),
        "func_style": 1.0 if ("standalone_func" in fp1) == ("standalone_func" in fp2) else 0.0,
    }

    weights = {
        "attr_overlap": 0.15, "method_overlap": 0.15, "async_match": 0.1,
        "creation_style": 0.2, "schema_arg_overlap": 0.15,
        "schema_type_match": 0.1, "func_style": 0.15,
    }
    scores["overall"] = sum(scores[k] * weights[k] for k in weights)
    return scores


def find_breakpoint(scores: List[float]) -> Optional[Dict[str, Any]]:
    """Find the biggest gap in a sorted list of similarity scores."""
    if len(scores) < 2:
        return None
    gaps = sorted(
        [(scores[i] - scores[i + 1], scores[i], scores[i + 1]) for i in range(len(scores) - 1)],
        reverse=True,
    )
    if gaps and gaps[0][0] > 0.05:
        g = gaps[0]
        return {"gap": round(g[0], 4), "above": round(g[1], 4), "below": round(g[2], 4)}
    return None
