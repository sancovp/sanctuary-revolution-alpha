#!/usr/bin/env python3

import ast
import builtins
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _safe_unparse(node: Optional[ast.AST]) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def _line_range(node: ast.AST) -> Tuple[int, int]:
    start = int(getattr(node, "lineno", 0) or 0)
    end = int(getattr(node, "end_lineno", start) or start)
    return (start, end)


class TargetFinder(ast.NodeVisitor):
    """AST visitor to find a specific function or class in a Python module."""

    def __init__(self, target_name: str):
        self.target_name = target_name
        self.found = False
        self.target_node: Optional[ast.AST] = None
        self.line_range: Optional[Tuple[int, int]] = None

    def _maybe_set(self, node: ast.AST, node_name: str) -> None:
        if node_name == self.target_name and not self.found:
            self.found = True
            self.target_node = node
            self.line_range = _line_range(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._maybe_set(node, node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._maybe_set(node, node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._maybe_set(node, node.name)
        self.generic_visit(node)


class SymbolCollector(ast.NodeVisitor):
    """Collects symbol definitions and fully-qualified aliases for fast lookups."""

    def __init__(self, file_path: Path, module_name: str):
        self.file_path = file_path
        self.module_name = module_name
        self.scope: List[str] = []
        self.symbols: List[Dict[str, Any]] = []

    def _record(self, node: ast.AST, name: str, symbol_type: str) -> None:
        qual_parts = self.scope + [name]
        qualname = ".".join(qual_parts)
        full_names: Set[str] = {name, qualname}
        if self.module_name:
            full_names.add(f"{self.module_name}.{name}")
            full_names.add(f"{self.module_name}.{qualname}")

        self.symbols.append(
            {
                "name": name,
                "qualname": qualname,
                "module": self.module_name,
                "file": self.file_path,
                "line_range": _line_range(node),
                "type": symbol_type,
                "full_names": sorted(full_names),
            }
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._record(node, node.name, "class")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record(node, node.name, "function")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record(node, node.name, "function")
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()


class DependencyCollector(ast.NodeVisitor):
    """Collects target-scoped lineage signals from the target node AST."""

    CONFIG_LOADERS = {
        "json.load",
        "json.loads",
        "yaml.load",
        "yaml.safe_load",
        "yaml.full_load",
        "toml.load",
        "toml.loads",
        "tomllib.load",
        "tomllib.loads",
    }

    def __init__(self, current_file: Path, module_aliases: Optional[Dict[str, str]] = None):
        self.current_file = current_file
        self.aliases: Dict[str, str] = dict(module_aliases or {})

        # Backward-compatible fields
        self.function_calls: List[str] = []
        self.class_refs: List[str] = []
        self.imports: List[str] = []
        self.references: List[str] = []
        self.file_dependencies: List[Dict[str, Any]] = []

        # New lineage fields
        self.call_sites: List[Dict[str, Any]] = []
        self.inferred_dependencies: List[Dict[str, Any]] = []
        self.config_lineage: List[Dict[str, Any]] = []
        self.config_vars: Dict[str, Dict[str, Any]] = {}
        self.dynamic_callable_vars: Dict[str, Dict[str, Any]] = {}
        self.open_handles: Dict[str, str] = {}

        self._file_dep_seen: Set[Tuple[str, str, int, str]] = set()
        self._inferred_seen: Set[Tuple[str, str, int]] = set()
        self._config_seen: Set[Tuple[str, str, str, int]] = set()

    def _assignment_targets(self, target: ast.AST) -> List[str]:
        if isinstance(target, ast.Name):
            return [target.id]
        if isinstance(target, (ast.Tuple, ast.List)):
            names: List[str] = []
            for item in target.elts:
                names.extend(self._assignment_targets(item))
            return names
        return []

    def _extract_string_literal(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            pieces: List[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    pieces.append(value.value)
                else:
                    pieces.append("{expr}")
            return "".join(pieces) if pieces else None
        return None

    def _expr_to_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._expr_to_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        return None

    def _resolve_alias_path(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return name
        if "." not in name:
            return self.aliases.get(name, name)

        first, rest = name.split(".", 1)
        resolved_first = self.aliases.get(first, first)
        return f"{resolved_first}.{rest}"

    def _slice_to_key(self, slice_node: ast.AST) -> Optional[str]:
        if isinstance(slice_node, ast.Constant):
            return str(slice_node.value)
        if isinstance(slice_node, ast.Name):
            return f"${slice_node.id}"
        # Python <3.9 compatibility
        if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):
            return self._slice_to_key(slice_node.value)
        return None

    def _extract_subscript_chain(self, node: ast.Subscript) -> Tuple[Optional[str], List[str]]:
        keys: List[str] = []
        current: ast.AST = node

        while isinstance(current, ast.Subscript):
            key = self._slice_to_key(current.slice)
            if key is None:
                keys.append("<dynamic>")
            else:
                keys.append(key)
            current = current.value

        root = self._expr_to_name(current)
        keys.reverse()
        return root, keys

    def _node_contains_config_var(self, node: Optional[ast.AST]) -> bool:
        if node is None:
            return False
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in self.config_vars:
                return True
            if isinstance(child, ast.Subscript):
                root, _ = self._extract_subscript_chain(child)
                if root in self.config_vars:
                    return True
        return False

    def _first_config_var_in_node(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in self.config_vars:
                return child.id
            if isinstance(child, ast.Subscript):
                root, _ = self._extract_subscript_chain(child)
                if root in self.config_vars:
                    return root
        return None

    def _record_file_dependency(
        self,
        path: str,
        operation: str,
        pattern: str,
        line: int,
        confidence: float,
        why: str,
    ) -> None:
        key = (path, operation, int(line))
        if key in self._file_dep_seen:
            return
        self._file_dep_seen.add(key)
        self.file_dependencies.append(
            {
                "path": path,
                "operation": operation,
                "pattern": pattern,
                "line": int(line),
                "confidence": round(confidence, 3),
                "why": why,
            }
        )

    def _record_inferred(
        self,
        name: str,
        kind: str,
        line: int,
        confidence: float,
        why: str,
        expression: Optional[str] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        key = (name, kind, int(line))
        if key in self._inferred_seen:
            return
        self._inferred_seen.add(key)
        self.inferred_dependencies.append(
            {
                "name": name,
                "kind": kind,
                "line": int(line),
                "confidence": round(confidence, 3),
                "why": why,
                "expression": expression or name,
                "candidates": candidates or [],
                "source_file": str(self.current_file),
            }
        )

    def _record_config_event(
        self,
        kind: str,
        variable: str,
        key_path: str,
        line: int,
        confidence: float,
        why: str,
        source: Optional[str] = None,
    ) -> None:
        key = (kind, variable, key_path, int(line))
        if key in self._config_seen:
            return
        self._config_seen.add(key)
        self.config_lineage.append(
            {
                "kind": kind,
                "variable": variable,
                "key_path": key_path,
                "line": int(line),
                "confidence": round(confidence, 3),
                "why": why,
                "source": source,
            }
        )

    def _resolve_call_name(self, func_node: ast.AST) -> Optional[str]:
        if isinstance(func_node, ast.Name):
            return self._resolve_alias_path(func_node.id)
        if isinstance(func_node, ast.Attribute):
            base = self._expr_to_name(func_node.value)
            if base:
                resolved_base = self._resolve_alias_path(base)
                return f"{resolved_base}.{func_node.attr}" if resolved_base else func_node.attr
            return func_node.attr
        return None

    def _is_config_loader(self, call_name: Optional[str]) -> bool:
        if not call_name:
            return False
        normalized = call_name.lower().lstrip(".")
        if normalized in self.CONFIG_LOADERS:
            return True
        return any(normalized.endswith(f".{loader}") for loader in self.CONFIG_LOADERS)

    def _extract_open_file_path(self, open_call: ast.Call) -> Optional[str]:
        if not open_call.args:
            return None
        return self._extract_string_literal(open_call.args[0])

    def _extract_loader_file_path(self, call_node: ast.Call) -> Optional[str]:
        if not call_node.args:
            return None

        first = call_node.args[0]
        literal = self._extract_string_literal(first)
        if literal:
            return literal

        if isinstance(first, ast.Call) and isinstance(first.func, ast.Name) and first.func.id == "open":
            return self._extract_open_file_path(first)

        if isinstance(first, ast.Name) and first.id in self.open_handles:
            return self.open_handles[first.id]

        return None

    def _infer_open_operation(self, call_node: ast.Call) -> str:
        mode: Optional[str] = None

        if len(call_node.args) > 1:
            mode = self._extract_string_literal(call_node.args[1])

        for kw in call_node.keywords:
            if kw.arg == "mode":
                mode = self._extract_string_literal(kw.value)

        if not mode:
            return "read/write"

        lower_mode = mode.lower()
        if any(flag in lower_mode for flag in ["w", "a", "x", "+"]):
            return "write"
        if "r" in lower_mode:
            return "read"
        return "read/write"

    def _extract_config_source(self, call_node: ast.Call) -> Optional[Dict[str, Any]]:
        call_name = self._resolve_call_name(call_node.func)
        if not self._is_config_loader(call_name):
            return None

        source_path = self._extract_loader_file_path(call_node)
        return {
            "loader": call_name,
            "source": source_path or "dynamic_source",
            "line": int(getattr(call_node, "lineno", 0) or 0),
        }

    def visit_Assign(self, node: ast.Assign) -> None:
        target_names: List[str] = []
        for target in node.targets:
            target_names.extend(self._assignment_targets(target))

        if isinstance(node.value, ast.Name):
            self.references.append(node.value.id)
            resolved = self._resolve_alias_path(node.value.id)
            for name in target_names:
                if resolved:
                    self.aliases[name] = resolved

                if node.value.id in self.config_vars:
                    self.config_vars[name] = dict(self.config_vars[node.value.id])
                    self._record_config_event(
                        kind="propagate",
                        variable=name,
                        key_path="<all>",
                        line=int(getattr(node, "lineno", 0) or 0),
                        confidence=0.82,
                        why=f"`{name}` inherits config lineage from `{node.value.id}`",
                        source=self.config_vars[node.value.id].get("source"),
                    )

        elif isinstance(node.value, ast.Attribute):
            attr_name = self._expr_to_name(node.value)
            resolved = self._resolve_alias_path(attr_name)
            for name in target_names:
                if resolved:
                    self.aliases[name] = resolved

        elif isinstance(node.value, ast.Call):
            config_source = self._extract_config_source(node.value)
            if config_source:
                for name in target_names:
                    self.config_vars[name] = {
                        "source": config_source["source"],
                        "loader": config_source["loader"],
                        "line": config_source["line"],
                    }
                    self._record_config_event(
                        kind="source",
                        variable=name,
                        key_path="<all>",
                        line=int(getattr(node, "lineno", 0) or 0),
                        confidence=0.94,
                        why=(
                            f"`{name}` receives config via `{config_source['loader']}` "
                            f"from `{config_source['source']}`"
                        ),
                        source=config_source["source"],
                    )

        elif isinstance(node.value, ast.Subscript):
            root, keys = self._extract_subscript_chain(node.value)
            if root and root in self.config_vars:
                key_path = ".".join(keys) if keys else "<dynamic>"
                for name in target_names:
                    self.dynamic_callable_vars[name] = {
                        "config_var": root,
                        "key_path": key_path,
                        "line": int(getattr(node, "lineno", 0) or 0),
                    }
                    self._record_config_event(
                        kind="derived_value",
                        variable=name,
                        key_path=key_path,
                        line=int(getattr(node, "lineno", 0) or 0),
                        confidence=0.78,
                        why=f"`{name}` derives from config `{root}[{key_path}]`",
                        source=self.config_vars[root].get("source"),
                    )
            elif self._node_contains_config_var(node.value):
                config_var = self._first_config_var_in_node(node.value) or "<config>"
                key_path = ".".join(keys) if keys else "<dynamic>"
                for name in target_names:
                    self.dynamic_callable_vars[name] = {
                        "config_var": config_var,
                        "key_path": key_path,
                        "line": int(getattr(node, "lineno", 0) or 0),
                    }
                    self._record_config_event(
                        kind="dispatch_source",
                        variable=config_var,
                        key_path=key_path,
                        line=int(getattr(node, "lineno", 0) or 0),
                        confidence=0.8,
                        why=(
                            f"`{name}` is assigned from `{_safe_unparse(node.value)}` "
                            "which depends on config"
                        ),
                        source=self.config_vars.get(config_var, {}).get("source"),
                    )

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        target_names = self._assignment_targets(node.target)

        if isinstance(node.value, ast.Name):
            resolved = self._resolve_alias_path(node.value.id)
            for name in target_names:
                if resolved:
                    self.aliases[name] = resolved

        if isinstance(node.value, ast.Call):
            config_source = self._extract_config_source(node.value)
            if config_source:
                for name in target_names:
                    self.config_vars[name] = {
                        "source": config_source["source"],
                        "loader": config_source["loader"],
                        "line": config_source["line"],
                    }
                    self._record_config_event(
                        kind="source",
                        variable=name,
                        key_path="<all>",
                        line=int(getattr(node, "lineno", 0) or 0),
                        confidence=0.94,
                        why=(
                            f"`{name}` receives config via `{config_source['loader']}` "
                            f"from `{config_source['source']}`"
                        ),
                        source=config_source["source"],
                    )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        line = int(getattr(node, "lineno", 0) or 0)
        expr = _safe_unparse(node)

        if isinstance(node.func, ast.Name):
            raw = node.func.id
            resolved = self._resolve_alias_path(raw) or raw

            self.call_sites.append(
                {
                    "kind": "name_call",
                    "raw_name": raw,
                    "resolved_name": resolved,
                    "module_hint": resolved.rsplit(".", 1)[0] if "." in resolved else None,
                    "line": line,
                    "expr": expr,
                    "resolvable": True,
                }
            )
            self.function_calls.append(resolved)

            if raw in self.dynamic_callable_vars:
                dynamic_info = self.dynamic_callable_vars[raw]
                config_var = dynamic_info.get("config_var", "<unknown>")
                key_path = dynamic_info.get("key_path", "<dynamic>")
                self._record_config_event(
                    kind="dispatch",
                    variable=config_var,
                    key_path=key_path,
                    line=line,
                    confidence=0.82,
                    why=(
                        f"Dynamic callable `{raw}` originates from config-driven "
                        f"subscript `{config_var}[{key_path}]`"
                    ),
                    source=self.config_vars.get(config_var, {}).get("source"),
                )
                self._record_inferred(
                    name=raw,
                    kind="dynamic_config_dispatch_call",
                    line=line,
                    confidence=0.82,
                    why=(
                        f"`{raw}()` is called after being assigned from "
                        f"config-derived dispatch key `{config_var}[{key_path}]`"
                    ),
                    expression=expr,
                )

            if raw == "open":
                file_path = self._extract_open_file_path(node)
                if not file_path:
                    file_path = "<dynamic>"
                operation = self._infer_open_operation(node)
                confidence = 0.92 if file_path != "<dynamic>" else 0.62
                self._record_file_dependency(
                    path=file_path,
                    operation=operation,
                    pattern="open()",
                    line=line,
                    confidence=confidence,
                    why=f"`open()` at line {line} references `{file_path}`",
                )

        elif isinstance(node.func, ast.Attribute):
            base_raw = self._expr_to_name(node.func.value)
            attr_name = node.func.attr
            raw = f"{base_raw}.{attr_name}" if base_raw else attr_name

            base_resolved = self._resolve_alias_path(base_raw) if base_raw else None
            resolved = f"{base_resolved}.{attr_name}" if base_resolved else raw

            self.call_sites.append(
                {
                    "kind": "attribute_call",
                    "raw_name": raw,
                    "resolved_name": resolved,
                    "module_hint": base_resolved or base_raw,
                    "line": line,
                    "expr": expr,
                    "attr": attr_name,
                    "resolvable": bool(
                        base_raw
                        and (
                            (base_raw in self.aliases)
                            or (base_raw.split(".", 1)[0] in self.aliases)
                            or (base_resolved and base_resolved != base_raw)
                        )
                    ),
                }
            )
            self.function_calls.append(resolved)

            if attr_name in {"load", "loads", "safe_load", "full_load", "dump", "dumps", "save"} or attr_name.startswith("read_"):
                file_path = self._extract_loader_file_path(node)
                if file_path:
                    operation = "read" if (attr_name.startswith("read_") or "load" in attr_name) else "write"
                    self._record_file_dependency(
                        path=file_path,
                        operation=operation,
                        pattern=f"{base_raw or '<unknown>'}.{attr_name}()",
                        line=line,
                        confidence=0.9,
                        why=f"`{attr_name}()` at line {line} references `{file_path}`",
                    )

            if attr_name == "get_template" and node.args:
                template_name = self._extract_string_literal(node.args[0])
                if template_name:
                    self._record_file_dependency(
                        path=template_name,
                        operation="read",
                        pattern=f"{base_raw or '<unknown>'}.get_template()",
                        line=line,
                        confidence=0.88,
                        why=f"Template lookup at line {line} references `{template_name}`",
                    )

            if base_raw and base_raw in self.config_vars and attr_name == "get":
                key = "<dynamic>"
                if node.args:
                    literal_key = self._extract_string_literal(node.args[0])
                    if literal_key:
                        key = literal_key

                self._record_config_event(
                    kind="key_access",
                    variable=base_raw,
                    key_path=key,
                    line=line,
                    confidence=0.86,
                    why=f"Config key access via `{base_raw}.get({key})`",
                    source=self.config_vars[base_raw].get("source"),
                )

        elif isinstance(node.func, ast.Subscript):
            root, keys = self._extract_subscript_chain(node.func)
            key_path = ".".join(keys) if keys else "<dynamic>"
            uses_config = root in self.config_vars if root else False

            if uses_config and root:
                self._record_config_event(
                    kind="dispatch",
                    variable=root,
                    key_path=key_path,
                    line=line,
                    confidence=0.8,
                    why=f"Dynamic dispatch uses config-driven subscript `{_safe_unparse(node.func)}`",
                    source=self.config_vars[root].get("source"),
                )

            self._record_inferred(
                name=_safe_unparse(node.func),
                kind="dynamic_subscript_call",
                line=line,
                confidence=0.7 if uses_config else 0.5,
                why="Call target is computed from subscript and cannot be resolved statically",
                expression=expr,
            )

        elif isinstance(node.func, ast.Call):
            inner_call = node.func
            inner_name = self._resolve_call_name(inner_call.func)
            if inner_name and inner_name.split(".")[-1] == "getattr":
                dynamic_name_node = inner_call.args[1] if len(inner_call.args) > 1 else None
                config_var = self._first_config_var_in_node(dynamic_name_node)
                uses_config = config_var is not None

                if uses_config and config_var:
                    self._record_config_event(
                        kind="dispatch",
                        variable=config_var,
                        key_path="<dynamic_attr>",
                        line=line,
                        confidence=0.82,
                        why="Dynamic getattr dispatch uses config-driven attribute name",
                        source=self.config_vars[config_var].get("source"),
                    )

                self._record_inferred(
                    name="getattr_dispatch",
                    kind="dynamic_getattr_call",
                    line=line,
                    confidence=0.72 if uses_config else 0.52,
                    why="Call target is produced via `getattr(...)` and may be runtime-dependent",
                    expression=expr,
                )

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        root, keys = self._extract_subscript_chain(node)
        if root and root in self.config_vars:
            key_path = ".".join(keys) if keys else "<dynamic>"
            self._record_config_event(
                kind="key_access",
                variable=root,
                key_path=key_path,
                line=int(getattr(node, "lineno", 0) or 0),
                confidence=0.84,
                why=f"Config subscript access `{_safe_unparse(node)}`",
                source=self.config_vars[root].get("source"),
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for base in node.bases:
            base_name = self._expr_to_name(base)
            if base_name:
                resolved = self._resolve_alias_path(base_name) or base_name
                self.class_refs.append(resolved)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.aliases[local_name] = alias.name
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        prefix = f"{'.' * node.level}{module}" if node.level else module

        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            resolved = f"{prefix}.{alias.name}" if prefix else alias.name
            self.aliases[local_name] = resolved
            self.imports.append(resolved)

        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            context_expr = item.context_expr
            if isinstance(context_expr, ast.Call) and isinstance(context_expr.func, ast.Name) and context_expr.func.id == "open":
                path = self._extract_open_file_path(context_expr) or "<dynamic>"
                operation = self._infer_open_operation(context_expr)
                self._record_file_dependency(
                    path=path,
                    operation=operation,
                    pattern="with open()",
                    line=int(getattr(context_expr, "lineno", 0) or 0),
                    confidence=0.92 if path != "<dynamic>" else 0.62,
                    why=f"`with open(...)` at line {getattr(context_expr, 'lineno', 0)} references `{path}`",
                )
                if isinstance(item.optional_vars, ast.Name):
                    self.open_handles[item.optional_vars.id] = path

        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            context_expr = item.context_expr
            if isinstance(context_expr, ast.Call) and isinstance(context_expr.func, ast.Name) and context_expr.func.id == "open":
                path = self._extract_open_file_path(context_expr) or "<dynamic>"
                operation = self._infer_open_operation(context_expr)
                self._record_file_dependency(
                    path=path,
                    operation=operation,
                    pattern="async with open()",
                    line=int(getattr(context_expr, "lineno", 0) or 0),
                    confidence=0.92 if path != "<dynamic>" else 0.62,
                    why=f"`async with open(...)` at line {getattr(context_expr, 'lineno', 0)} references `{path}`",
                )
                if isinstance(item.optional_vars, ast.Name):
                    self.open_handles[item.optional_vars.id] = path

        self.generic_visit(node)


class CrossFileDependencyAnalyzer:
    """Analyzes cross-file dependencies for a given function or class."""

    BUILTIN_NAMES = set(dir(builtins))
    SITE_PACKAGE_MARKERS = ("site-packages", "dist-packages")
    STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", set()))
    COMMON_OBJECT_METHODS = {
        "append",
        "clear",
        "copy",
        "count",
        "decode",
        "encode",
        "endswith",
        "extend",
        "format",
        "get",
        "items",
        "join",
        "keys",
        "lower",
        "lstrip",
        "pop",
        "replace",
        "rstrip",
        "setdefault",
        "split",
        "startswith",
        "strip",
        "update",
        "upper",
        "values",
    }

    def __init__(
        self,
        target_name: str,
        search_dirs: List[str],
        include_same_file: bool = False,
        target_scope: bool = True,
        include_external_packages: bool = True,
        external_depth: int = 1,
    ):
        self.target_name = target_name
        self.search_dirs = [Path(d) for d in search_dirs]
        self.include_same_file = include_same_file
        self.target_scope = target_scope
        self.include_external_packages = include_external_packages
        self.external_depth = max(0, int(external_depth))

        self.target_file: Optional[Path] = None
        self.target_line_range: Optional[Tuple[int, int]] = None
        self.target_node: Optional[ast.AST] = None
        self.target_tree: Optional[ast.AST] = None

        self.external_dependencies: List[Dict[str, Any]] = []
        self.file_dependencies: List[Dict[str, Any]] = []
        self.inferred_dependencies: List[Dict[str, Any]] = []
        self.config_lineage: List[Dict[str, Any]] = []

        self._python_files: List[Path] = []
        self._file_trees: Dict[Path, ast.AST] = {}
        self._file_codes: Dict[Path, str] = {}
        self._symbols_by_name: Dict[str, List[Dict[str, Any]]] = {}
        self._symbols_by_full_name: Dict[str, List[Dict[str, Any]]] = {}
        self._external_modules_indexed: Set[str] = set()
        self._external_files_indexed: Set[Path] = set()

    def find_python_files(self) -> List[Path]:
        """Find and cache all Python files in the search directories."""
        if self._python_files:
            return self._python_files

        python_files: List[Path] = []
        for directory in self.search_dirs:
            if not directory.exists():
                continue
            python_files.extend(directory.glob("**/*.py"))

        self._python_files = sorted(set(python_files), key=lambda p: str(p))
        return self._python_files

    def _module_name_for_file(self, file_path: Path) -> str:
        for root in self.search_dirs:
            try:
                relative = file_path.relative_to(root)
                return str(relative.with_suffix("")).replace("/", ".").replace("\\", ".")
            except ValueError:
                continue
        return file_path.stem

    def _parse_python_file(self, file_path: Path) -> Optional[Tuple[str, ast.AST]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            tree = ast.parse(code)
            return code, tree
        except Exception:
            return None

    def _load_file_asts(self) -> None:
        if self._file_trees:
            return

        for file_path in self.find_python_files():
            parsed = self._parse_python_file(file_path)
            if not parsed:
                continue
            code, tree = parsed
            self._file_codes[file_path] = code
            self._file_trees[file_path] = tree

    def _register_symbol(self, symbol: Dict[str, Any]) -> None:
        if "symbol_origin" not in symbol:
            symbol["symbol_origin"] = "internal"

        self._symbols_by_name.setdefault(symbol["name"], []).append(symbol)

        for full_name in symbol.get("full_names", []):
            self._symbols_by_full_name.setdefault(full_name, []).append(symbol)

    def _index_tree_symbols(self, file_path: Path, tree: ast.AST, module_name: str, origin: str) -> None:
        collector = SymbolCollector(file_path=file_path, module_name=module_name)
        collector.visit(tree)
        for symbol in collector.symbols:
            symbol["symbol_origin"] = origin
            self._register_symbol(symbol)

    def _build_symbol_index(self) -> None:
        if self._symbols_by_name:
            return

        self._load_file_asts()

        for file_path, tree in self._file_trees.items():
            module_name = self._module_name_for_file(file_path)
            self._index_tree_symbols(file_path, tree, module_name, origin="internal")

    def _is_external_python_path(self, file_path: Path) -> bool:
        text = str(file_path)
        if file_path.suffix != ".py":
            return False
        return any(marker in text for marker in self.SITE_PACKAGE_MARKERS)

    def _should_index_external_module(self, module_name: str) -> bool:
        if not self.include_external_packages or self.external_depth < 1:
            return False
        if not module_name:
            return False

        normalized = module_name.lstrip(".")
        if not normalized:
            return False

        base = normalized.split(".")[0]
        if base in self.STDLIB_MODULES:
            return False

        parts = normalized.split(".")
        if len(parts) > 1 and parts[-1] in self.COMMON_OBJECT_METHODS:
            return False

        return True

    def _index_external_file(self, file_path: Path, module_name: str) -> None:
        if file_path in self._external_files_indexed:
            return
        if not self._is_external_python_path(file_path):
            return

        parsed = self._parse_python_file(file_path)
        if not parsed:
            return
        _, tree = parsed

        self._external_files_indexed.add(file_path)
        self._index_tree_symbols(file_path=file_path, tree=tree, module_name=module_name, origin="external")

    def _index_external_package_children(self, package_name: str, spec: Any) -> None:
        if self.external_depth < 1:
            return

        locations = getattr(spec, "submodule_search_locations", None) or []
        for location in locations:
            package_dir = Path(location)
            if not package_dir.exists():
                continue

            module_files = sorted(package_dir.glob("*.py"))[:40]
            for module_file in module_files:
                if module_file.name == "__init__.py":
                    continue
                submodule_name = f"{package_name}.{module_file.stem}"
                self._index_external_file(module_file, submodule_name)

            # Non-recursive, one-level subpackage drill.
            subpackages = sorted([p for p in package_dir.iterdir() if p.is_dir()])[:20]
            for subpkg in subpackages:
                init_file = subpkg / "__init__.py"
                if not init_file.exists():
                    continue

                subpkg_name = f"{package_name}.{subpkg.name}"
                self._index_external_file(init_file, subpkg_name)

                for sub_file in sorted(subpkg.glob("*.py"))[:30]:
                    if sub_file.name == "__init__.py":
                        continue
                    submodule_name = f"{subpkg_name}.{sub_file.stem}"
                    self._index_external_file(sub_file, submodule_name)

    def _module_candidates_from_reference(
        self, reference: Optional[str], module_hint: Optional[str]
    ) -> List[str]:
        candidates: List[str] = []
        seen: Set[str] = set()

        def add_candidate(value: Optional[str]) -> None:
            if not value:
                return
            normalized = value.lstrip(".")
            if not normalized:
                return
            if normalized not in seen:
                candidates.append(normalized)
                seen.add(normalized)

        for value in [module_hint, reference]:
            if not value:
                continue
            normalized = value.lstrip(".")
            if not normalized:
                continue

            parts = normalized.split(".")
            for i in range(len(parts), 0, -1):
                add_candidate(".".join(parts[:i]))

            if len(parts) > 1:
                add_candidate(".".join(parts[:-1]))

        return candidates[:12]

    def _index_external_module(self, module_name: str) -> None:
        if module_name in self._external_modules_indexed:
            return
        self._external_modules_indexed.add(module_name)

        if not self._should_index_external_module(module_name):
            return

        try:
            spec = importlib.util.find_spec(module_name)
        except Exception:
            return

        if spec is None:
            return

        origin = getattr(spec, "origin", None)
        if isinstance(origin, str) and origin not in {"built-in", "frozen"}:
            origin_path = Path(origin)
            if origin_path.exists() and self._is_external_python_path(origin_path):
                self._index_external_file(origin_path, module_name)

        self._index_external_package_children(module_name, spec)

    def _index_external_candidates(self, reference: Optional[str], module_hint: Optional[str]) -> None:
        for candidate in self._module_candidates_from_reference(reference, module_hint):
            self._index_external_module(candidate)

    def _collect_module_aliases(self, tree: ast.AST) -> Dict[str, str]:
        aliases: Dict[str, str] = {}

        for node in getattr(tree, "body", []):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname or alias.name.split(".")[0]
                    aliases[local_name] = alias.name

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                prefix = f"{'.' * node.level}{module}" if node.level else module
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local_name = alias.asname or alias.name
                    aliases[local_name] = f"{prefix}.{alias.name}" if prefix else alias.name

        return aliases

    def _find_node_by_name_and_line(self, tree: ast.AST, name: str, start_line: int) -> Optional[ast.AST]:
        class LineFinder(ast.NodeVisitor):
            def __init__(self, target_name: str, target_line: int):
                self.target_name = target_name
                self.target_line = target_line
                self.target: Optional[ast.AST] = None

            def _maybe(self, node: ast.AST, node_name: str) -> None:
                if self.target is not None:
                    return
                if node_name == self.target_name and int(getattr(node, "lineno", -1)) == self.target_line:
                    self.target = node

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._maybe(node, node.name)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._maybe(node, node.name)
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                self._maybe(node, node.name)
                self.generic_visit(node)

        finder = LineFinder(name, start_line)
        finder.visit(tree)
        return finder.target

    def find_target(self) -> bool:
        """Find the target function or class in the indexed codebase."""
        self._build_symbol_index()

        candidates: List[Dict[str, Any]] = []
        candidates.extend(self._symbols_by_name.get(self.target_name, []))
        candidates.extend(self._symbols_by_full_name.get(self.target_name, []))

        if not candidates:
            suffix = f".{self.target_name}"
            for full_name, defs in self._symbols_by_full_name.items():
                if full_name.endswith(suffix):
                    candidates.extend(defs)

        deduped: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
        for candidate in candidates:
            key = (str(candidate["file"]), int(candidate["line_range"][0]), candidate["name"])
            deduped[key] = candidate

        ordered = sorted(deduped.values(), key=lambda c: (str(c["file"]), int(c["line_range"][0])))
        if not ordered:
            return False

        selected = ordered[0]
        self.target_file = selected["file"]
        self.target_line_range = selected["line_range"]
        self.target_tree = self._file_trees.get(self.target_file)

        if self.target_tree is None:
            return False

        self.target_node = self._find_node_by_name_and_line(
            self.target_tree,
            selected["name"],
            int(selected["line_range"][0]),
        )

        if self.target_node is None:
            finder = TargetFinder(self.target_name)
            finder.visit(self.target_tree)
            self.target_node = finder.target_node
            self.target_line_range = finder.line_range

        return self.target_node is not None

    def _dedupe_symbols(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique: Dict[Tuple[str, int, str, str], Dict[str, Any]] = {}
        for symbol in symbols:
            key = (
                str(symbol["file"]),
                int(symbol["line_range"][0]),
                symbol["name"],
                symbol["type"],
            )
            unique[key] = symbol
        return list(unique.values())

    def _candidate_symbols(self, reference: Optional[str], module_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        if not reference:
            return []

        candidates: List[Dict[str, Any]] = []
        normalized = reference.lstrip(".")

        candidates.extend(self._symbols_by_full_name.get(reference, []))
        if normalized != reference:
            candidates.extend(self._symbols_by_full_name.get(normalized, []))

        short_name = normalized.split(".")[-1]
        candidates.extend(self._symbols_by_name.get(short_name, []))

        if not candidates:
            self._index_external_candidates(reference=reference, module_hint=module_hint)
            candidates.extend(self._symbols_by_full_name.get(reference, []))
            if normalized != reference:
                candidates.extend(self._symbols_by_full_name.get(normalized, []))
            candidates.extend(self._symbols_by_name.get(short_name, []))

        return self._dedupe_symbols(candidates)

    def _score_candidate(self, candidate: Dict[str, Any], reference: str, module_hint: Optional[str]) -> float:
        score = 0.0
        full_names = set(candidate.get("full_names", []))
        qualname = str(candidate.get("qualname", "") or "")
        normalized_reference = reference.lstrip(".")

        if reference in full_names or normalized_reference in full_names:
            score += 0.6
        elif qualname and normalized_reference.endswith(qualname):
            score += 0.45
        elif candidate["name"] == normalized_reference:
            score += 0.35
        elif candidate["name"] == normalized_reference.split(".")[-1]:
            score += 0.2

        if module_hint:
            hint = module_hint.lstrip(".")
            if any(name.startswith(f"{hint}.") or name == hint for name in full_names):
                score += 0.3
            elif candidate.get("module", "").endswith(hint):
                score += 0.22
            elif qualname:
                hint_leaf = hint.split(".")[-1]
                if qualname.startswith(f"{hint_leaf}."):
                    score += 0.2

        if self.target_file and Path(candidate["file"]).parent == self.target_file.parent:
            score += 0.08

        if candidate.get("symbol_origin") == "external":
            score -= 0.05
            if module_hint:
                score += 0.08

        return score

    def resolve_symbol_reference(
        self,
        reference: Optional[str],
        module_hint: Optional[str] = None,
        prefer_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not reference:
            return {
                "symbol": None,
                "confidence": 0.0,
                "reason": "empty_reference",
                "candidates": [],
            }

        candidates = self._candidate_symbols(reference, module_hint=module_hint)
        if prefer_type:
            candidates = [c for c in candidates if c["type"] == prefer_type]

        if not candidates:
            return {
                "symbol": None,
                "confidence": 0.0,
                "reason": "not_found",
                "candidates": [],
            }

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for candidate in candidates:
            scored.append((self._score_candidate(candidate, reference, module_hint), candidate))
        scored.sort(key=lambda item: item[0], reverse=True)

        best_score, best = scored[0]
        confidence = 0.55
        if best_score >= 0.95:
            confidence = 0.95
        elif best_score >= 0.8:
            confidence = 0.88
        elif best_score >= 0.65:
            confidence = 0.78
        elif best_score >= 0.5:
            confidence = 0.68

        ambiguity_note = ""
        if len(scored) > 1 and (best_score - scored[1][0]) < 0.12:
            confidence = max(0.4, confidence - 0.15)
            ambiguity_note = f" (ambiguous among {len(scored)} candidates)"

        reason = "name_match"
        if module_hint:
            reason = f"module_hint:{module_hint}"
        if ambiguity_note:
            reason += ambiguity_note

        candidate_summaries: List[Dict[str, Any]] = []
        for score, candidate in scored[:3]:
            candidate_summaries.append(
                {
                    "name": candidate["name"],
                    "type": candidate["type"],
                    "file": str(candidate["file"]),
                    "line_range": candidate["line_range"],
                    "score": round(score, 3),
                }
            )

        return {
            "symbol": best,
            "confidence": round(confidence, 3),
            "reason": reason,
            "candidates": candidate_summaries,
        }

    def _is_builtin_or_internal_noise(self, callsite: Dict[str, Any]) -> bool:
        raw = (callsite.get("raw_name") or "").strip()
        if not raw:
            return True

        if raw.startswith("self.") or raw.startswith("cls."):
            return True

        short = raw.split(".")[-1]
        if short in self.BUILTIN_NAMES:
            return True

        if "." not in raw and short in self.COMMON_OBJECT_METHODS:
            return True

        return False

    def _dependency_key(self, symbol: Dict[str, Any], dep_type: str) -> Tuple[str, int, str, str]:
        return (
            str(symbol["file"]),
            int(symbol["line_range"][0]),
            symbol["name"],
            dep_type,
        )

    def _accumulate_dependency(
        self,
        dep_map: Dict[Tuple[str, int, str, str], Dict[str, Any]],
        symbol: Dict[str, Any],
        dep_type: str,
        confidence: float,
        why: str,
        resolution: str,
        source_line: int,
        source_expr: str,
    ) -> None:
        key = self._dependency_key(symbol, dep_type)

        if key not in dep_map:
            dep_map[key] = {
                "name": symbol["name"],
                "type": dep_type,
                "file": str(symbol["file"]),
                "line_range": symbol["line_range"],
                "symbol_origin": symbol.get("symbol_origin", "internal"),
                "confidence": round(confidence, 3),
                "why_details": [why],
                "why": why,
                "resolution": resolution,
                "evidence": [{"line": int(source_line), "expr": source_expr}],
                "source_line": int(source_line),
                "source_expr": source_expr,
            }
            return

        current = dep_map[key]
        if confidence > current.get("confidence", 0.0):
            current["confidence"] = round(confidence, 3)
            current["resolution"] = resolution
            current["source_line"] = int(source_line)
            current["source_expr"] = source_expr

        if why not in current["why_details"]:
            current["why_details"].append(why)
            if len(current["why_details"]) == 1:
                current["why"] = why

        evidence_entry = {"line": int(source_line), "expr": source_expr}
        if evidence_entry not in current["evidence"]:
            current["evidence"].append(evidence_entry)

    def _should_include_symbol(self, symbol: Dict[str, Any]) -> bool:
        if self.include_same_file:
            return True
        return Path(symbol["file"]) != self.target_file

    def _symbol_display(self, symbol: Dict[str, Any]) -> str:
        module = symbol.get("module")
        qual = symbol.get("qualname")
        if module and qual:
            return f"{module}.{qual}"
        return symbol.get("name", "<unknown>")

    def collect_dependencies(self) -> List[Dict[str, Any]]:
        """Collect target-scoped dependencies and lineage artifacts."""
        if not self.find_target():
            return []

        assert self.target_file is not None
        assert self.target_tree is not None

        module_aliases = self._collect_module_aliases(self.target_tree)
        collector = DependencyCollector(self.target_file, module_aliases)

        node_to_visit = self.target_node if self.target_scope and self.target_node is not None else self.target_tree
        collector.visit(node_to_visit)

        dep_map: Dict[Tuple[str, int, str, str], Dict[str, Any]] = {}
        inferred_from_resolution: List[Dict[str, Any]] = []

        # Resolve class inheritance lineage.
        for class_ref in sorted(set(collector.class_refs)):
            resolution = self.resolve_symbol_reference(class_ref, prefer_type="class")
            symbol = resolution.get("symbol")
            confidence = float(resolution.get("confidence", 0.0) or 0.0)
            if symbol and confidence >= 0.7 and self._should_include_symbol(symbol):
                why = (
                    f"Class lineage references `{class_ref}` and resolves to `{self._symbol_display(symbol)}`"
                )
                self._accumulate_dependency(
                    dep_map,
                    symbol,
                    dep_type="class",
                    confidence=confidence,
                    why=why,
                    resolution=str(resolution.get("reason", "name_match")),
                    source_line=int(self.target_line_range[0]) if self.target_line_range else 0,
                    source_expr=class_ref,
                )
            elif resolution.get("candidates"):
                inferred_from_resolution.append(
                    {
                        "name": class_ref,
                        "kind": "unresolved_class_reference",
                        "line": int(self.target_line_range[0]) if self.target_line_range else 0,
                        "confidence": round(max(0.4, confidence), 3),
                        "why": "Class reference could not be resolved confidently",
                        "expression": class_ref,
                        "candidates": resolution.get("candidates", []),
                        "source_file": str(self.target_file),
                    }
                )

        # Resolve callgraph lineage.
        for callsite in collector.call_sites:
            if not callsite.get("resolvable", True):
                continue

            if self._is_builtin_or_internal_noise(callsite):
                continue

            resolved_name = callsite.get("resolved_name")
            raw_name = callsite.get("raw_name")
            module_hint = callsite.get("module_hint")

            attempts = [resolved_name, raw_name]
            if raw_name and "." in raw_name:
                attempts.append(raw_name.split(".")[-1])

            seen_attempts: Set[str] = set()
            best_resolution: Optional[Dict[str, Any]] = None

            for attempt in attempts:
                if not attempt or attempt in seen_attempts:
                    continue
                seen_attempts.add(attempt)

                resolution = self.resolve_symbol_reference(
                    reference=attempt,
                    module_hint=module_hint,
                    prefer_type=None,
                )
                if best_resolution is None:
                    best_resolution = resolution
                elif float(resolution.get("confidence", 0.0) or 0.0) > float(
                    best_resolution.get("confidence", 0.0) or 0.0
                ):
                    best_resolution = resolution

            if not best_resolution:
                continue

            symbol = best_resolution.get("symbol")
            confidence = float(best_resolution.get("confidence", 0.0) or 0.0)
            source_line = int(callsite.get("line", 0) or 0)
            source_expr = str(callsite.get("expr", callsite.get("raw_name", "")))

            # Same-file edges are intentionally omitted by default for low-noise cross-file context.
            if symbol and not self._should_include_symbol(symbol):
                continue

            if symbol and confidence >= 0.7:
                dep_type = symbol["type"] if symbol["type"] in {"function", "class"} else "reference"
                why = (
                    f"`{source_expr}` at line {source_line} resolves to "
                    f"`{self._symbol_display(symbol)}`"
                )
                self._accumulate_dependency(
                    dep_map,
                    symbol,
                    dep_type=dep_type,
                    confidence=confidence,
                    why=why,
                    resolution=str(best_resolution.get("reason", "name_match")),
                    source_line=source_line,
                    source_expr=source_expr,
                )
            else:
                if not best_resolution.get("candidates"):
                    continue
                if confidence < 0.72:
                    continue
                inferred_from_resolution.append(
                    {
                        "name": str(callsite.get("raw_name") or callsite.get("resolved_name") or "<unknown>"),
                        "kind": "unresolved_call",
                        "line": source_line,
                        "confidence": round(max(0.42, confidence), 3),
                        "why": (
                            "Call target could not be resolved with high confidence; "
                            "recorded as inferred lineage"
                        ),
                        "expression": source_expr,
                        "candidates": best_resolution.get("candidates", []),
                        "source_file": str(self.target_file),
                    }
                )

        self.external_dependencies = sorted(
            dep_map.values(),
            key=lambda dep: (-float(dep.get("confidence", 0.0) or 0.0), dep["file"], dep["line_range"][0]),
        )

        self.file_dependencies = sorted(
            collector.file_dependencies,
            key=lambda dep: (dep.get("line", 0), dep.get("path", "")),
        )

        inferred_combined = collector.inferred_dependencies + inferred_from_resolution
        inferred_seen: Set[Tuple[str, str, int, str]] = set()
        deduped_inferred: List[Dict[str, Any]] = []
        for item in inferred_combined:
            key = (
                str(item.get("name", "")),
                str(item.get("kind", "")),
                int(item.get("line", 0) or 0),
                str(item.get("expression", "")),
            )
            if key in inferred_seen:
                continue
            inferred_seen.add(key)
            deduped_inferred.append(item)

        self.inferred_dependencies = sorted(
            deduped_inferred,
            key=lambda item: (-float(item.get("confidence", 0.0) or 0.0), int(item.get("line", 0) or 0)),
        )

        self.config_lineage = sorted(
            collector.config_lineage,
            key=lambda item: (int(item.get("line", 0) or 0), str(item.get("variable", "")), str(item.get("key_path", ""))),
        )

        return self.external_dependencies

    def analyze(self) -> Dict[str, Any]:
        """Analyze the target and return the results."""
        dependencies = self.collect_dependencies()

        if not self.target_file:
            return {
                "status": "not_found",
                "message": f"Could not find {self.target_name} in the specified directories",
            }

        return {
            "status": "found",
            "target": self.target_name,
            "file": str(self.target_file),
            "line_range": self.target_line_range,
            "dependencies": dependencies,
            "file_dependencies": self.file_dependencies,
            "inferred_dependencies": self.inferred_dependencies,
            "config_lineage": self.config_lineage,
            "analysis_options": {
                "target_scoped": self.target_scope,
                "include_same_file": self.include_same_file,
                "include_external_packages": self.include_external_packages,
                "external_depth": self.external_depth,
            },
        }


def analyze_dependencies(
    target_name: str,
    search_dirs: Optional[List[str]] = None,
    contextualizer: Optional[bool] = False,
    exclude_from_contextualizer: Optional[List[str]] = None,
    target_scope: Optional[bool] = True,
    include_same_file: Optional[bool] = False,
    include_external_packages: Optional[bool] = True,
    external_depth: Optional[int] = 1,
) -> Dict[str, Any]:
    """Analyze dependencies for a given function or class name.

    Args:
        target_name: Name of the function or class to analyze
        search_dirs: List of directories to search in
        contextualizer: Whether to include code snippets for target + dependencies
        exclude_from_contextualizer: Skip files containing these substrings
        target_scope: Analyze only the target node body (default: True)
        include_same_file: Include dependencies in target file (default: False)
        include_external_packages: Resolve external package symbols from site-packages (default: True)
        external_depth: External package drill depth; currently supports 0 or 1 (default: 1)

    Returns:
        Structured dependency context suitable for MCP + Neo4j merge.
    """
    if search_dirs is None:
        search_dirs = [os.getcwd(), "/tmp/"]

    analyzer = CrossFileDependencyAnalyzer(
        target_name=target_name,
        search_dirs=search_dirs,
        include_same_file=bool(include_same_file),
        target_scope=bool(target_scope),
        include_external_packages=bool(include_external_packages),
        external_depth=int(external_depth or 0),
    )
    result = analyzer.analyze()

    if contextualizer:
        result["context"] = {}

        if result.get("status") == "found":
            target_file = result["file"]
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                start, end = result["line_range"]
                target_content = "".join(all_lines[start - 1 : end])
                result["context"][target_file] = {
                    "content": target_content,
                    "line_range": result["line_range"],
                }
            except Exception as exc:
                result["context"][target_file] = {
                    "error": str(exc),
                    "line_range": result.get("line_range"),
                }

            for dep in result.get("dependencies", []):
                dep_file = dep["file"]
                if exclude_from_contextualizer and any(
                    exclude in dep_file for exclude in exclude_from_contextualizer
                ):
                    continue

                try:
                    with open(dep_file, "r", encoding="utf-8") as f:
                        all_lines = f.readlines()
                    start, end = dep["line_range"]
                    dep_content = "".join(all_lines[start - 1 : end])
                    result["context"][dep_file] = {
                        "content": dep_content,
                        "line_range": dep["line_range"],
                    }
                except Exception as exc:
                    result["context"][dep_file] = {
                        "error": str(exc),
                        "line_range": dep.get("line_range"),
                    }

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze cross-file dependencies for a function or class."
    )
    parser.add_argument("target_name", help="Name of the function or class to analyze")
    parser.add_argument("dirs", nargs="+", help="Directories to search in")
    parser.add_argument(
        "--include-same-file",
        action="store_true",
        help="Include same-file symbols in dependency output",
    )
    parser.add_argument(
        "--whole-file",
        action="store_true",
        help="Analyze full file AST instead of target node AST",
    )
    parser.add_argument(
        "--no-external-packages",
        action="store_true",
        help="Disable one-level site-packages symbol resolution",
    )
    parser.add_argument(
        "--external-depth",
        type=int,
        default=1,
        help="External package drill depth (0 disables, 1 indexes package + immediate modules)",
    )

    args = parser.parse_args()

    output = analyze_dependencies(
        target_name=args.target_name,
        search_dirs=args.dirs,
        include_same_file=args.include_same_file,
        target_scope=not args.whole_file,
        include_external_packages=not args.no_external_packages,
        external_depth=args.external_depth,
    )
    print(output)
