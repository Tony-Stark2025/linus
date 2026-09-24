"""
Deterministic AST Inspector Tool for Linus.
Parses Python source code and AST to extract function signatures, types,
and structural vulnerability risk vectors without LLM hallucination.
"""

import ast
from typing import List, Optional
from linus.models import (
    ASTAnalysisResult,
    FunctionSignature,
    FunctionParameter,
    RiskVectorType,
)


class RiskVisitor(ast.NodeVisitor):
    """Context-aware AST visitor to detect structural edge-case risk vectors while respecting control-flow guards."""

    def __init__(
        self,
        param_names: Optional[List[str]] = None,
        nullable_param_names: Optional[List[str]] = None,
    ):
        self.risk_vectors: List[RiskVectorType] = []
        self.param_names = set(param_names or [])
        self.nullable_param_names = set(nullable_param_names or [])
        # Control-flow guard tracking sets
        self.guarded_non_empty: set[str] = set()
        self.guarded_non_null: set[str] = set()
        self.guarded_non_zero: set[str] = set()
        self.guarded_dict_keys: set[tuple[str, str]] = set()
        self.suppressed_risks: set[RiskVectorType] = set()
        self.inverted_empty_vars: set[str] = set()
        self.inverted_null_vars: set[str] = set()
        self.inverted_zero_vars: set[str] = set()

    def _add_risk(self, risk: RiskVectorType):
        if risk not in self.suppressed_risks and risk not in self.risk_vectors:
            self.risk_vectors.append(risk)

    @staticmethod
    def _has_early_exit(stmts: List[ast.stmt]) -> bool:
        """Returns True if statement block unconditionally exits via return, raise, break, or continue."""
        for stmt in stmts:
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                return True
        return False

    def _extract_guard_targets(self, test: ast.expr):
        """
        Analyzes an `if` condition expression and returns:
        (empty_or_null_if_true, positive_if_true, zero_if_true, nonzero_if_true, dict_key_in, dict_key_not_in)
        """
        empty_or_null_if_true: set[str] = set()
        positive_if_true: set[str] = set()
        zero_if_true: set[str] = set()
        nonzero_if_true: set[str] = set()
        dict_key_in: set[tuple[str, str]] = set()
        dict_key_not_in: set[tuple[str, str]] = set()

        def inspect_expr(expr: ast.expr):
            # e.g. `if not x:`
            if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
                inner = expr.operand
                if isinstance(inner, ast.Name):
                    empty_or_null_if_true.add(inner.id)
                    zero_if_true.add(inner.id)
                elif (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id in ("len", "isinstance", "hasattr")
                    and len(inner.args) >= 1
                    and isinstance(inner.args[0], ast.Name)
                ):
                    empty_or_null_if_true.add(inner.args[0].id)
            # e.g. `if x:`
            elif isinstance(expr, ast.Name):
                positive_if_true.add(expr.id)
                nonzero_if_true.add(expr.id)
            # e.g. `if len(x):`, `if isinstance(x, ...):`, `if hasattr(x, ...):`
            elif (
                isinstance(expr, ast.Call)
                and isinstance(expr.func, ast.Name)
                and expr.func.id in ("len", "isinstance", "hasattr")
                and len(expr.args) >= 1
                and isinstance(expr.args[0], ast.Name)
            ):
                positive_if_true.add(expr.args[0].id)
            # Comparisons: `x is None`, `x is not None`, `count <= 0`, `count == 0`, `len(x) == 0`, `"k" in d`
            elif isinstance(expr, ast.Compare) and len(expr.ops) == 1 and len(expr.comparators) == 1:
                left = expr.left
                op = expr.ops[0]
                right = expr.comparators[0]

                # `x is None` / `x is not None` or `None is x` / `None is not x`
                if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value is None:
                    if isinstance(op, (ast.Is, ast.Eq)):
                        empty_or_null_if_true.add(left.id)
                    elif isinstance(op, (ast.IsNot, ast.NotEq)):
                        positive_if_true.add(left.id)
                elif isinstance(right, ast.Name) and isinstance(left, ast.Constant) and left.value is None:
                    if isinstance(op, (ast.Is, ast.Eq)):
                        empty_or_null_if_true.add(right.id)
                    elif isinstance(op, (ast.IsNot, ast.NotEq)):
                        positive_if_true.add(right.id)

                # `len(x) == 0`, `len(x) <= 0`, `len(x) > 0`
                if (
                    isinstance(left, ast.Call)
                    and isinstance(left.func, ast.Name)
                    and left.func.id == "len"
                    and len(left.args) == 1
                    and isinstance(left.args[0], ast.Name)
                    and isinstance(right, ast.Constant)
                    and isinstance(right.value, (int, float))
                ):
                    target_var = left.args[0].id
                    if isinstance(op, (ast.Eq, ast.LtE)) and right.value == 0:
                        empty_or_null_if_true.add(target_var)
                    elif isinstance(op, ast.Lt) and right.value == 1:
                        empty_or_null_if_true.add(target_var)
                    elif isinstance(op, (ast.Gt, ast.NotEq)) and right.value == 0:
                        positive_if_true.add(target_var)
                    elif isinstance(op, ast.GtE) and right.value >= 1:
                        positive_if_true.add(target_var)

                # `count <= 0`, `count == 0`, `count > 0`, `count != 0`
                if (
                    isinstance(left, ast.Name)
                    and isinstance(right, ast.Constant)
                    and isinstance(right.value, (int, float))
                    and not isinstance(right.value, bool)
                ):
                    if isinstance(op, (ast.Eq, ast.LtE)) and right.value == 0:
                        zero_if_true.add(left.id)
                    elif isinstance(op, ast.Lt) and right.value <= 1:
                        zero_if_true.add(left.id)
                    elif isinstance(op, (ast.Gt, ast.NotEq)) and right.value == 0:
                        nonzero_if_true.add(left.id)
                    elif isinstance(op, ast.GtE) and right.value > 0:
                        nonzero_if_true.add(left.id)
                elif (
                    isinstance(right, ast.Name)
                    and isinstance(left, ast.Constant)
                    and isinstance(left.value, (int, float))
                    and not isinstance(left.value, bool)
                ):
                    if isinstance(op, (ast.Eq, ast.GtE)) and left.value == 0:
                        zero_if_true.add(right.id)
                    elif isinstance(op, (ast.Lt, ast.NotEq)) and left.value == 0:
                        nonzero_if_true.add(right.id)

                # `"key" in d` / `"key" not in d`
                if (
                    isinstance(left, ast.Constant)
                    and isinstance(left.value, str)
                    and isinstance(right, ast.Name)
                ):
                    if isinstance(op, ast.In):
                        dict_key_in.add((right.id, left.value))
                    elif isinstance(op, ast.NotIn):
                        dict_key_not_in.add((right.id, left.value))

            elif isinstance(expr, ast.BoolOp):
                for val in expr.values:
                    inspect_expr(val)

        inspect_expr(test)
        return (
            empty_or_null_if_true,
            positive_if_true,
            zero_if_true,
            nonzero_if_true,
            dict_key_in,
            dict_key_not_in,
        )

    def _visit_stmt_list(self, stmts: List[ast.stmt]):
        """Visits a sequential block of statements, propagating early-return and else-branch guards."""
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                (
                    empty_if_true,
                    pos_if_true,
                    zero_if_true,
                    nonzero_if_true,
                    dk_in,
                    dk_not_in,
                ) = self._extract_guard_targets(stmt.test)

                self.visit(stmt.test)

                # Visit the `if` body with scoped positive guards and inverted-logic detectors
                saved_non_empty = set(self.guarded_non_empty)
                saved_non_null = set(self.guarded_non_null)
                saved_non_zero = set(self.guarded_non_zero)
                saved_dk = set(self.guarded_dict_keys)
                saved_inv_empty = set(self.inverted_empty_vars)
                saved_inv_null = set(self.inverted_null_vars)
                saved_inv_zero = set(self.inverted_zero_vars)

                self.guarded_non_empty.update(pos_if_true)
                self.guarded_non_null.update(pos_if_true)
                self.guarded_non_zero.update(nonzero_if_true)
                self.guarded_dict_keys.update(dk_in)

                self.inverted_empty_vars.update(empty_if_true)
                self.inverted_null_vars.update(empty_if_true)
                self.inverted_zero_vars.update(zero_if_true)

                self._visit_stmt_list(stmt.body)

                # Restore scoped state before visiting orelse
                self.guarded_non_empty = set(saved_non_empty)
                self.guarded_non_null = set(saved_non_null)
                self.guarded_non_zero = set(saved_non_zero)
                self.guarded_dict_keys = set(saved_dk)
                self.inverted_empty_vars = set(saved_inv_empty)
                self.inverted_null_vars = set(saved_inv_null)
                self.inverted_zero_vars = set(saved_inv_zero)

                # Visit orelse (`else:` / `elif:`), where `stmt.test` is guaranteed FALSE
                if stmt.orelse:
                    self.guarded_non_empty.update(empty_if_true)
                    self.guarded_non_null.update(empty_if_true)
                    self.guarded_non_zero.update(zero_if_true)
                    self.guarded_dict_keys.update(dk_not_in)
                    self._visit_stmt_list(stmt.orelse)
                    self.guarded_non_empty = set(saved_non_empty)
                    self.guarded_non_null = set(saved_non_null)
                    self.guarded_non_zero = set(saved_non_zero)
                    self.guarded_dict_keys = set(saved_dk)

                # If the `if` body unconditionally exits (e.g., `if not items: return 0.0`),
                # then all statements AFTER this `if` are guaranteed to have non-empty / non-null / non-zero values!
                if self._has_early_exit(stmt.body):
                    self.guarded_non_empty.update(empty_if_true)
                    self.guarded_non_null.update(empty_if_true)
                    self.guarded_non_zero.update(zero_if_true)
                    self.guarded_dict_keys.update(dk_not_in)
                if stmt.orelse and self._has_early_exit(stmt.orelse):
                    self.guarded_non_empty.update(pos_if_true)
                    self.guarded_non_null.update(pos_if_true)
                    self.guarded_non_zero.update(nonzero_if_true)
                    self.guarded_dict_keys.update(dk_in)
            else:
                self.visit(stmt)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_stmt_list(node.body)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_stmt_list(node.body)

    def visit_For(self, node: ast.For):
        self.visit(node.iter)
        self._visit_stmt_list(node.body)
        if node.orelse:
            self._visit_stmt_list(node.orelse)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.visit(node.iter)
        self._visit_stmt_list(node.body)
        if node.orelse:
            self._visit_stmt_list(node.orelse)

    def visit_While(self, node: ast.While):
        self.visit(node.test)
        self._visit_stmt_list(node.body)
        if node.orelse:
            self._visit_stmt_list(node.orelse)

    def visit_With(self, node: ast.With):
        for item in node.items:
            self.visit(item)
        self._visit_stmt_list(node.body)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        for item in node.items:
            self.visit(item)
        self._visit_stmt_list(node.body)

    def visit_Try(self, node: ast.Try):
        caught_names: set[str] = set()
        for handler in node.handlers:
            if handler.type is None:
                caught_names.add("BaseException")
            elif isinstance(handler.type, ast.Name):
                caught_names.add(handler.type.id)
            elif isinstance(handler.type, ast.Tuple):
                for elt in handler.type.elts:
                    if isinstance(elt, ast.Name):
                        caught_names.add(elt.id)

        newly_suppressed: set[RiskVectorType] = set()
        if caught_names & {"Exception", "BaseException", "LookupError", "IndexError"}:
            newly_suppressed.add(RiskVectorType.EMPTY_COLLECTION_INDEXING)
        if caught_names & {"Exception", "BaseException", "LookupError", "KeyError"}:
            newly_suppressed.add(RiskVectorType.UNCHECKED_DICT_KEY)
        if caught_names & {"Exception", "BaseException", "ArithmeticError", "ZeroDivisionError"}:
            newly_suppressed.add(RiskVectorType.ZERO_DIVISION)
        if caught_names & {"Exception", "BaseException", "TypeError", "AttributeError"}:
            newly_suppressed.add(RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS)
        if caught_names & {"Exception", "BaseException", "ArithmeticError", "OverflowError", "ValueError"}:
            newly_suppressed.add(RiskVectorType.BOUNDARY_INTEGER_OVERFLOW)

        prev_suppressed = set(self.suppressed_risks)
        self.suppressed_risks.update(newly_suppressed)
        self._visit_stmt_list(node.body)
        self.suppressed_risks = prev_suppressed

        for handler in node.handlers:
            self._visit_stmt_list(handler.body)
        if node.orelse:
            self._visit_stmt_list(node.orelse)
        if node.finalbody:
            self._visit_stmt_list(node.finalbody)

    def visit_Subscript(self, node: ast.Subscript):
        target_name = node.value.id if isinstance(node.value, ast.Name) else None

        # Check for inverted logic: indexing a variable inside an `if not var:` or `if len(var) == 0:` branch
        if target_name and (target_name in self.inverted_empty_vars or target_name in self.inverted_null_vars):
            self._add_risk(RiskVectorType.INVERTED_LOGIC)

        # If indexing a known nullable parameter (e.g., `user: Optional[Dict]` -> `user["tier"]`),
        # flag NULLABLE_ATTRIBUTE_ACCESS unless guarded
        if target_name and target_name in self.nullable_param_names and target_name not in self.guarded_non_null:
            self._add_risk(RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS)

        # Check for positive integer indexing (`items[0]`) OR negative integer indexing (`items[-1]`)
        is_int_index = False
        if isinstance(node.slice, ast.Constant):
            # Note: in Python `issubclass(bool, int)` is True, so explicitly exclude `bool`!
            if isinstance(node.slice.value, int) and not isinstance(node.slice.value, bool):
                is_int_index = True
            elif isinstance(node.slice.value, str):
                if not (target_name and (target_name, node.slice.value) in self.guarded_dict_keys):
                    self._add_risk(RiskVectorType.UNCHECKED_DICT_KEY)
        elif (
            isinstance(node.slice, ast.UnaryOp)
            and isinstance(node.slice.op, ast.USub)
            and isinstance(node.slice.operand, ast.Constant)
            and isinstance(node.slice.operand.value, int)
            and not isinstance(node.slice.operand.value, bool)
        ):
            is_int_index = True

        if is_int_index:
            if not (target_name and target_name in self.guarded_non_empty):
                self._add_risk(RiskVectorType.EMPTY_COLLECTION_INDEXING)

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # Check for division operations, e.g. a / b, a // b, a % b
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            divisor_name = node.right.id if isinstance(node.right, ast.Name) else None
            if divisor_name and divisor_name in self.inverted_zero_vars:
                self._add_risk(RiskVectorType.INVERTED_LOGIC)

            # Dividing by a non-zero numeric literal (e.g. `amount / 100.0`) cannot raise ZeroDivisionError
            is_safe_nonzero_constant = (
                isinstance(node.right, ast.Constant)
                and isinstance(node.right.value, (int, float))
                and not isinstance(node.right.value, bool)
                and node.right.value != 0
            )
            is_guarded_divisor = bool(divisor_name and divisor_name in self.guarded_non_zero)

            if not is_safe_nonzero_constant and not is_guarded_divisor:
                self._add_risk(RiskVectorType.ZERO_DIVISION)

        # Check for unbounded exponentiation or bit-shift overflow (BOUNDARY_INTEGER_OVERFLOW)
        elif isinstance(node.op, (ast.Pow, ast.LShift)):
            right_name = node.right.id if isinstance(node.right, ast.Name) else None
            is_overflow_constant = (
                isinstance(node.right, ast.Constant)
                and isinstance(node.right.value, int)
                and not isinstance(node.right.value, bool)
                and node.right.value > 64
            )
            overflow_param_names = {"exp", "exponent", "power", "shift", "bits", "n", "scale", "factor"}
            if is_overflow_constant or (right_name and right_name.lower() in overflow_param_names):
                self._add_risk(RiskVectorType.BOUNDARY_INTEGER_OVERFLOW)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect integer overflow / conversion calls such as math.factorial(n) or int.to_bytes(...)
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        if func_name in ("factorial", "to_bytes", "exp"):
            self._add_risk(RiskVectorType.BOUNDARY_INTEGER_OVERFLOW)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Check for inverted logic: accessing attribute on `x` inside `if x is None:` or `if not x:`
        if isinstance(node.value, ast.Name) and node.value.id in self.inverted_null_vars:
            self._add_risk(RiskVectorType.INVERTED_LOGIC)

        # Check for chained attribute access, e.g. user.profile.tier
        if isinstance(node.value, ast.Attribute):
            root = node.value
            while isinstance(root, ast.Attribute):
                root = root.value
            root_name = root.id if isinstance(root, ast.Name) else None
            if not (root_name and root_name in self.guarded_non_null):
                self._add_risk(RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS)
        elif isinstance(node.value, ast.Name):
            target_id = node.value.id
            if target_id not in self.guarded_non_null:
                if target_id in self.param_names or target_id in (
                    "user", "profile", "customer", "config", "session", "promo",
                    "discount", "account", "record", "data", "client",
                ):
                    self._add_risk(RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS)
        self.generic_visit(node)


def _extract_function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    class_name: Optional[str] = None,
    class_init_params: Optional[List[FunctionParameter]] = None,
) -> FunctionSignature:
    """Extracts FunctionSignature (including posonly, standard, vararg, kwonly, kwarg) and runs RiskVisitor."""
    params: List[FunctionParameter] = []

    # 1. Positional-only + positional-or-keyword arguments with right-aligned defaults
    pos_args = list(node.args.posonlyargs) + list(node.args.args)
    num_posonly = len(node.args.posonlyargs)
    defaults = [None] * (len(pos_args) - len(node.args.defaults)) + list(node.args.defaults)

    for idx, (arg, default) in enumerate(zip(pos_args, defaults)):
        # Skip `self` or `cls` on class/instance methods so callers see the real business parameters
        if class_name and idx == 0 and arg.arg in ("self", "cls"):
            continue
        type_ann = ast.unparse(arg.annotation) if arg.annotation else None
        default_val = ast.unparse(default) if default else None
        kind = "positional_only" if idx < num_posonly else "positional_or_keyword"
        params.append(FunctionParameter(
            name=arg.arg,
            type_annotation=type_ann,
            default_value=default_val,
            kind=kind,
        ))

    # 2. *args (vararg)
    if node.args.vararg:
        arg = node.args.vararg
        type_ann = ast.unparse(arg.annotation) if arg.annotation else None
        params.append(FunctionParameter(
            name=arg.arg,
            type_annotation=type_ann,
            default_value=None,
            kind="var_positional",
        ))

    # 3. Keyword-only arguments (kwonlyargs)
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        type_ann = ast.unparse(arg.annotation) if arg.annotation else None
        default_val = ast.unparse(default) if default else None
        params.append(FunctionParameter(
            name=arg.arg,
            type_annotation=type_ann,
            default_value=default_val,
            kind="keyword_only",
        ))

    # 4. **kwargs (kwarg)
    if node.args.kwarg:
        arg = node.args.kwarg
        type_ann = ast.unparse(arg.annotation) if arg.annotation else None
        params.append(FunctionParameter(
            name=arg.arg,
            type_annotation=type_ann,
            default_value=None,
            kind="var_keyword",
        ))

    ret_type = ast.unparse(node.returns) if node.returns else None
    docstring = ast.get_docstring(node)

    param_names = [p.name for p in params]
    nullable_param_names = [
        p.name for p in params
        if (p.type_annotation and ("Optional" in p.type_annotation or "None" in p.type_annotation))
        or (p.default_value == "None")
    ]
    visitor = RiskVisitor(param_names=param_names, nullable_param_names=nullable_param_names)
    visitor.visit(node)

    return FunctionSignature(
        name=node.name,
        line_number=node.lineno,
        parameters=params,
        return_type=ret_type,
        risk_vectors=visitor.risk_vectors,
        docstring=docstring,
        class_name=class_name,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        class_init_params=list(class_init_params or []),
    )


def inspect_source_ast(source_code: str, file_path: str = "source.py") -> ASTAnalysisResult:
    """
    Deterministically parses Python source code and extracts function signatures
    (including top-level functions, class methods, and nested functions) and structural risk vectors.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return ASTAnalysisResult(
            file_path=file_path,
            functions=[],
            imported_symbols=[],
            total_lines=len(source_code.splitlines()),
            raw_source=source_code,
        )

    imported_symbols: List[str] = []
    functions: List[FunctionSignature] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_symbols.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imported_symbols.append(f"{module}.{alias.name}")

    def collect_functions(
        stmts: List[ast.stmt],
        enclosing_class: Optional[str] = None,
        enclosing_init_params: Optional[List[FunctionParameter]] = None,
    ):
        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = _extract_function_signature(
                    stmt,
                    class_name=enclosing_class,
                    class_init_params=enclosing_init_params,
                )
                if not (enclosing_class and stmt.name == "__init__" and not sig.risk_vectors):
                    functions.append(sig)
                # Also inspect nested functions inside this function body
                collect_functions(stmt.body, enclosing_class=None, enclosing_init_params=None)
            elif isinstance(stmt, ast.ClassDef):
                init_params: List[FunctionParameter] = []
                for body_item in stmt.body:
                    if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)) and body_item.name == "__init__":
                        init_sig = _extract_function_signature(body_item, class_name=stmt.name)
                        init_params = init_sig.parameters
                        break
                collect_functions(stmt.body, enclosing_class=stmt.name, enclosing_init_params=init_params)

    collect_functions(tree.body)

    return ASTAnalysisResult(
        file_path=file_path,
        functions=functions,
        imported_symbols=imported_symbols,
        total_lines=len(source_code.splitlines()),
        raw_source=source_code,
    )


# Compatibility alias for Amazon Bedrock AgentCore action groups and documentation
inspect_ast_risks = inspect_source_ast

