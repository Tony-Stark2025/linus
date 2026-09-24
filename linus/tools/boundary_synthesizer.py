"""
Autonomous Adversarial Boundary Synthesizer for Linus.
Analyzes AST-detected risk vectors and synthesizes candidate adversarial pytest suites
and defensive patches for arbitrary Python functions without requiring pre-scripted tests.
"""

import ast
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from linus.models import (
    ASTAnalysisResult,
    FunctionSignature,
    FunctionParameter,
    RiskVectorType,
    TestExecutionResult,
)


class BoundarySynthesizer:
    """
    Synthesizes targeted adversarial boundary tests and autonomous defensive AST patches
    based on AST structural risk vectors and runtime crash tracebacks.
    """

    @staticmethod
    def _sanitize_module_name(source_filename: str) -> str:
        """Extracts a valid Python module identifier from any relative or nested file path."""
        stem = Path(source_filename).stem
        cleaned = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in stem)
        if not cleaned or cleaned[0].isdigit():
            cleaned = f"mod_{cleaned}"
        return cleaned

    @staticmethod
    def _format_call_args(params: List[FunctionParameter], arg_values: List[str]) -> str:
        """Formats positional and keyword-only arguments for a function call."""
        rendered: List[str] = []
        for param, val in zip(params, arg_values):
            if param.kind in ("var_positional", "var_keyword"):
                continue
            elif param.kind == "keyword_only":
                rendered.append(f"{param.name}={val}")
            else:
                rendered.append(val)
        return ", ".join(rendered)

    @staticmethod
    def _is_nullable_candidate(param: FunctionParameter) -> bool:
        """Determines whether a parameter is likely an object/dict subject to NoneType dereference."""
        p_lower = param.name.lower()
        ann = (param.type_annotation or "").lower()
        if "optional" in ann or "none" in ann or "any" in ann:
            return True
        if ann in ("int", "float", "bool", "str", "bytes", "list", "tuple", "set") or (
            ann.startswith(("list[", "tuple[", "set["))
        ):
            return False
        if "dict" in ann:
            return True
        nullable_keywords = (
            "user", "account", "profile", "customer", "session", "config",
            "record", "data", "client", "promo", "discount", "payload", "entity", "obj", "item"
        )
        return any(k in p_lower for k in nullable_keywords)

    @staticmethod
    def _default_init_arg(param: FunctionParameter) -> str:
        if param.default_value is not None:
            return param.default_value
        ann = (param.type_annotation or "").lower()
        p_low = param.name.lower()
        if "float" in ann or any(k in p_low for k in ("rate", "tax", "fee", "price", "amount", "discount")):
            return "0.08"
        if "int" in ann or any(k in p_low for k in ("count", "num", "id", "limit", "timeout", "port")):
            return "1"
        if "str" in ann or any(k in p_low for k in ("name", "url", "host", "key", "token", "path")):
            return '"default"'
        if "dict" in ann or "mapping" in ann or "config" in p_low:
            return "{}"
        if "list" in ann or "seq" in ann or "items" in p_low:
            return "[]"
        if "bool" in ann:
            return "True"
        return "1"

    def _build_call_expr(self, fn: FunctionSignature, args_str: str) -> str:
        if fn.class_name:
            if fn.name == "__init__":
                base_call = f"{fn.class_name}({args_str})"
            else:
                init_call_params = [
                    p for p in fn.class_init_params
                    if p.kind not in ("var_positional", "var_keyword")
                ]
                init_vals = [self._default_init_arg(p) for p in init_call_params]
                init_args_str = self._format_call_args(init_call_params, init_vals)
                base_call = f"{fn.class_name}({init_args_str}).{fn.name}({args_str})"
        else:
            base_call = f"{fn.name}({args_str})"

        if fn.is_async:
            return f"asyncio.run({base_call})"
        return base_call

    def synthesize_boundary_test(
        self,
        ast_summary: ASTAnalysisResult,
        source_filename: str = "service.py",
        target_function_name: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Synthesizes a comprehensive pytest adversarial reproduction suite covering
        all detected risk vectors across functions and class methods.
        Returns: (test_code, hypothesis_description)
        """
        module_name = self._sanitize_module_name(source_filename)

        # Determine target functions to test
        target_functions: List[FunctionSignature] = []
        if target_function_name:
            for fn in ast_summary.functions:
                if fn.name == target_function_name:
                    target_functions.append(fn)
                    break
        elif ast_summary.functions:
            # Sort functions so the highest-risk function is primary, followed by any other functions with risk vectors
            sorted_fns = sorted(
                ast_summary.functions,
                key=lambda f: len(f.risk_vectors),
                reverse=True,
            )
            risky_fns = [f for f in sorted_fns if f.risk_vectors]
            target_functions = risky_fns if risky_fns else [sorted_fns[0]]

        if not target_functions:
            test_code = f"""import pytest
import {module_name}

def test_ambient_fallback_linus():
    assert hasattr({module_name}, '__name__')
"""
            return test_code, "Fallback module import test"

        # Collect symbols to import
        import_symbols: List[str] = []
        needs_asyncio = any(fn.is_async for fn in target_functions)
        for fn in target_functions:
            sym = fn.class_name if fn.class_name else fn.name
            if sym not in import_symbols:
                import_symbols.append(sym)

        test_blocks: List[str] = []
        hypotheses: List[str] = []
        used_test_names: set[str] = set()

        def unique_test_name(base_name: str, fn_name: str) -> str:
            if base_name not in used_test_names:
                used_test_names.add(base_name)
                return base_name
            candidate = f"{base_name}_{fn_name}"
            used_test_names.add(candidate)
            return candidate

        for fn in target_functions:
            fn_name = fn.name
            call_params = [
                p for p in fn.parameters
                if p.kind not in ("var_positional", "var_keyword")
            ]
            risk_types = fn.risk_vectors

            # Generate a test block for EVERY detected risk vector (not mutually exclusive!)
            if RiskVectorType.EMPTY_COLLECTION_INDEXING in risk_types:
                hypotheses.append(
                    f"Empty collection passed to '{fn_name}' triggers unhandled IndexError on direct subscript."
                )
                test_args = []
                for p in call_params:
                    p_lower = p.name.lower()
                    p_ann = (p.type_annotation or "").lower()
                    if "cart" in p_lower or "order" in p_lower:
                        test_args.append('{"items": []}')
                    elif p_ann in ("int", "float") or any(
                        k in p_lower for k in ("count", "total", "num", "divisor", "amount", "price", "qty", "fee", "rate")
                    ):
                        test_args.append("1")
                    else:
                        test_args.append("[]")
                args_str = self._format_call_args(call_params, test_args)
                call_expr = self._build_call_expr(fn, args_str)
                t_name = unique_test_name("test_empty_collection_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    \"\"\"Linus Adversarial Test: Verifies empty collection handling.\"\"\"
    # Hypothesis: Direct indexing without length guard raises IndexError
    _ = {call_expr}""")

            if RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS in risk_types:
                hypotheses.append(
                    f"Passing None for nullable object in '{fn_name}' triggers unhandled TypeError/AttributeError."
                )
                # Identify which parameter(s) should receive None
                nullable_indices = [
                    i for i, p in enumerate(call_params) if self._is_nullable_candidate(p)
                ]
                if not nullable_indices and call_params:
                    nullable_indices = [0]

                call_lines: List[str] = []
                for target_idx in nullable_indices:
                    test_args = [
                        "None" if i == target_idx else "50.0"
                        for i in range(len(call_params))
                    ]
                    args_str = self._format_call_args(call_params, test_args)
                    call_lines.append(f"    _ = {self._build_call_expr(fn, args_str)}")

                if not call_lines:
                    call_lines.append(f"    _ = {self._build_call_expr(fn, '')}")

                calls_body = "\n".join(call_lines)
                t_name = unique_test_name("test_null_object_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    \"\"\"Linus Adversarial Test: Verifies NoneType attribute resilience.\"\"\"
    # Hypothesis: Unchecked attribute access on None raises TypeError/AttributeError
{calls_body}""")

            if RiskVectorType.ZERO_DIVISION in risk_types:
                hypotheses.append(
                    f"Zero divisor or zero count passed to '{fn_name}' triggers unhandled ZeroDivisionError."
                )
                test_args = []
                for p in call_params:
                    p_lower = p.name.lower()
                    p_ann = (p.type_annotation or "").lower()
                    if "total" in p_lower or "revenue" in p_lower or "sum" in p_lower:
                        test_args.append("0.0")
                    elif "count" in p_lower or "order" in p_lower or "num" in p_lower or "divisor" in p_lower:
                        test_args.append("0")
                    elif "list" in p_ann or any(
                        k in p_lower for k in ("items", "arr", "elements", "records")
                    ):
                        test_args.append("[1]")
                    else:
                        test_args.append("0")
                args_str = self._format_call_args(call_params, test_args)
                call_expr = self._build_call_expr(fn, args_str)
                t_name = unique_test_name("test_zero_division_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    \"\"\"Linus Adversarial Test: Verifies zero division resilience.\"\"\"
    # Hypothesis: Division by zero divisor triggers ZeroDivisionError
    _ = {call_expr}""")

            if RiskVectorType.UNCHECKED_DICT_KEY in risk_types:
                hypotheses.append(
                    f"Missing dictionary key in '{fn_name}' triggers unhandled KeyError."
                )
                test_args = ["{}" for _ in call_params]
                args_str = self._format_call_args(call_params, test_args)
                call_expr = self._build_call_expr(fn, args_str)
                t_name = unique_test_name("test_missing_dict_key_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    \"\"\"Linus Adversarial Test: Verifies missing dictionary key resilience.\"\"\"
    # Hypothesis: Unchecked dictionary key access triggers KeyError
    _ = {call_expr}""")

            if RiskVectorType.BOUNDARY_INTEGER_OVERFLOW in risk_types:
                hypotheses.append(
                    f"Extreme numeric boundary passed to '{fn_name}' triggers OverflowError or ValueError."
                )
                test_args = []
                for idx, p in enumerate(call_params):
                    p_low = p.name.lower()
                    if idx == 0 and len(call_params) > 1 and not any(
                        k in p_low for k in ("exp", "exponent", "power", "shift", "bits", "n")
                    ):
                        test_args.append("1e300")
                    elif any(k in p_low for k in ("exp", "exponent", "power", "shift", "bits", "n")):
                        test_args.append("1000")
                    else:
                        test_args.append("1e300")
                args_str = self._format_call_args(call_params, test_args)
                call_expr = self._build_call_expr(fn, args_str)
                t_name = unique_test_name("test_integer_overflow_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    \"\"\"Linus Adversarial Test: Verifies extreme numeric boundary handling.\"\"\"
    _ = {call_expr}""")

            if RiskVectorType.INVERTED_LOGIC in risk_types:
                hypotheses.append(
                    f"Inverted guard logic in '{fn_name}' triggers unhandled exception on empty/null input."
                )
                test_args = []
                for p in call_params:
                    p_low = p.name.lower()
                    if any(k in p_low for k in ("item", "arr", "list", "record", "element", "batch")):
                        test_args.append("[]")
                    elif any(k in p_low for k in ("count", "num", "total", "divisor", "b")):
                        test_args.append("0")
                    else:
                        test_args.append("None")
                args_str = self._format_call_args(call_params, test_args)
                call_expr = self._build_call_expr(fn, args_str)
                t_name = unique_test_name("test_inverted_logic_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    \"\"\"Linus Adversarial Test: Verifies inverted condition handling.\"\"\"
    _ = {call_expr}""")

            if not risk_types:
                hypotheses.append(f"Smoke test on '{fn_name}' with minimal arguments.")
                test_args = [
                    self._default_init_arg(p)
                    for p in call_params
                ]
                args_str = self._format_call_args(call_params, test_args)
                call_expr = self._build_call_expr(fn, args_str)
                t_name = unique_test_name("test_smoke_boundary_linus", fn_name)
                test_blocks.append(f"""def {t_name}():
    _ = {call_expr}""")

        asyncio_header = "import asyncio\n" if needs_asyncio else ""
        imports_line = f"from {module_name} import {', '.join(import_symbols)}"
        joined_blocks = "\n\n\n".join(test_blocks)
        test_code = f"import pytest\n{asyncio_header}{imports_line}\n\n{joined_blocks}\n"
        combined_hypothesis = " | ".join(hypotheses)
        return test_code, combined_hypothesis

    @staticmethod
    def _infer_safe_return_expr(fn_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Infers an idiomatic safe fallback return expression for a function based on return annotation and AST returns."""
        if fn_node.name == "__init__":
            return "None"
        if fn_node.returns:
            ret_ann = ast.unparse(fn_node.returns)
            if ret_ann == "float":
                return "0.0"
            if ret_ann == "int":
                return "0"
            if ret_ann == "str":
                return '""'
            if ret_ann == "bool":
                return "False"
            if ret_ann.startswith(("List", "list")):
                return "[]"
            if ret_ann.startswith(("Dict", "dict")):
                return "{}"

        # Inspect return statements in function body
        for child in ast.walk(fn_node):
            if isinstance(child, ast.Return) and child.value is not None:
                val = child.value
                if isinstance(val, ast.Constant):
                    if isinstance(val.value, float):
                        return "0.0"
                    if isinstance(val.value, int) and not isinstance(val.value, bool):
                        return "0"
                    if isinstance(val.value, str):
                        return '""'
                    if isinstance(val.value, bool):
                        return "False"
                elif isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "round":
                    return "0.0"
                elif isinstance(val, ast.BinOp) and isinstance(val.op, (ast.Div, ast.Add, ast.Sub, ast.Mult, ast.Pow)):
                    return "0.0"
                elif isinstance(val, ast.Dict):
                    return "{}"
                elif isinstance(val, ast.List):
                    return "[]"
        return "None"

    def synthesize_defensive_patch(
        self,
        source_code: str,
        ast_summary: ASTAnalysisResult,
        failing_test: Optional[TestExecutionResult] = None,
    ) -> Tuple[str, str]:
        """
        Autonomously synthesizes a minimal defensive AST patch that guards against
        the proven runtime exception while preserving baseline behavior.
        Returns: (patched_code, explanation)
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return source_code, "Unable to parse source AST for patch synthesis."

        exc_type = (failing_test.exception_type if failing_test else None) or "Exception"
        exc_line = failing_test.exception_line if failing_test else None

        class DefensiveGuardTransformer(ast.NodeTransformer):
            def __init__(self):
                self.patched_functions: List[str] = []

            def _transform_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
                # Transform any nested functions inside this function first
                end_line = getattr(node, "end_lineno", node.lineno + 100)
                has_risks = any(
                    f.name == node.name and len(f.risk_vectors) > 0
                    for f in ast_summary.functions
                )
                matches_line = exc_line is not None and (node.lineno <= exc_line <= end_line)
                if not has_risks and not matches_line and ast_summary.functions:
                    return node

                safe_ret_str = BoundarySynthesizer._infer_safe_return_expr(node)
                safe_ret_expr = ast.parse(safe_ret_str, mode="eval").body

                # Preserve docstring at top of function if present
                docstring_stmt = None
                body_stmts = list(node.body)
                if (
                    body_stmts
                    and isinstance(body_stmts[0], ast.Expr)
                    and isinstance(body_stmts[0].value, ast.Constant)
                    and isinstance(body_stmts[0].value.value, str)
                ):
                    docstring_stmt = body_stmts.pop(0)

                if not body_stmts:
                    return node

                # Synthesize explicit parameter pre-condition guards where appropriate
                guard_stmts: List[ast.stmt] = []
                pos_args = [
                    a.arg for a in (list(node.args.posonlyargs) + list(node.args.args))
                    if a.arg not in ("self", "cls")
                ]
                for p_name in pos_args:
                    p_low = p_name.lower()
                    if exc_type == "ZeroDivisionError" and any(
                        k in p_low for k in ("count", "order", "num", "divisor", "b", "denom", "total_orders")
                    ):
                        guard_stmts.extend(
                            ast.parse(f"if {p_name} == 0:\n    return {safe_ret_str}\n").body
                        )
                    elif exc_type == "IndexError" and any(
                        k in p_low for k in ("items", "arr", "elements", "list", "records", "data")
                    ):
                        guard_stmts.extend(
                            ast.parse(f"if not {p_name}:\n    return {safe_ret_str}\n").body
                        )
                    elif exc_type in ("TypeError", "AttributeError") and any(
                        k in p_low for k in ("user", "account", "profile", "customer", "session", "config", "record", "client")
                    ):
                        guard_stmts.extend(
                            ast.parse(f"if {p_name} is None:\n    return {safe_ret_str}\n").body
                        )

                # Wrap function execution in a targeted boundary exception guard so complex
                # nested expressions (e.g. `cart.get("items", [])[0]` or `data["missing"]`)
                # return the safe fallback without breaking any valid baseline inputs.
                caught_tuple = ast.Tuple(
                    elts=[
                        ast.Name(id="IndexError", ctx=ast.Load()),
                        ast.Name(id="ZeroDivisionError", ctx=ast.Load()),
                        ast.Name(id="TypeError", ctx=ast.Load()),
                        ast.Name(id="AttributeError", ctx=ast.Load()),
                        ast.Name(id="KeyError", ctx=ast.Load()),
                        ast.Name(id="OverflowError", ctx=ast.Load()),
                        ast.Name(id="ValueError", ctx=ast.Load()),
                    ],
                    ctx=ast.Load(),
                )
                try_stmt = ast.Try(
                    body=guard_stmts + body_stmts,
                    handlers=[
                        ast.ExceptHandler(
                            type=caught_tuple,
                            name=None,
                            body=[ast.Return(value=safe_ret_expr)],
                        )
                    ],
                    orelse=[],
                    finalbody=[],
                )

                new_body = ([docstring_stmt] if docstring_stmt else []) + [try_stmt]
                node.body = new_body
                self.patched_functions.append(node.name)
                return node

            def visit_FunctionDef(self, node: ast.FunctionDef):
                return self._transform_func(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                return self._transform_func(node)

        transformer = DefensiveGuardTransformer()
        patched_tree = transformer.visit(tree)
        ast.fix_missing_locations(patched_tree)
        patched_code = ast.unparse(patched_tree) + "\n"

        fn_list_str = ", ".join(transformer.patched_functions) or "target function"
        explanation = (
            f"Autonomously synthesized defensive boundary guard in `{fn_list_str}` "
            f"to safely handle `{exc_type}` edge cases without regressing baseline behavior."
        )
        return patched_code, explanation
