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
    """AST visitor to detect structural edge-case risk vectors."""

    def __init__(self):
        self.risk_vectors: List[RiskVectorType] = []

    def visit_Subscript(self, node: ast.Subscript):
        # Check for direct integer indexing, e.g. items[0]
        if isinstance(node.slice, ast.Constant):
            if isinstance(node.slice.value, int):
                if RiskVectorType.EMPTY_COLLECTION_INDEXING not in self.risk_vectors:
                    self.risk_vectors.append(RiskVectorType.EMPTY_COLLECTION_INDEXING)
            elif isinstance(node.slice.value, str):
                if RiskVectorType.UNCHECKED_DICT_KEY not in self.risk_vectors:
                    self.risk_vectors.append(RiskVectorType.UNCHECKED_DICT_KEY)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # Check for division operations, e.g. a / b or a // b
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if RiskVectorType.ZERO_DIVISION not in self.risk_vectors:
                self.risk_vectors.append(RiskVectorType.ZERO_DIVISION)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Check for chained attribute access, e.g. user.profile.tier
        if isinstance(node.value, ast.Attribute):
            if RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS not in self.risk_vectors:
                self.risk_vectors.append(RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS)
        elif isinstance(node.value, ast.Name):
            # Check for common nullable patterns like user.tier
            if node.value.id in ("user", "profile", "customer", "config", "session", "promo", "discount"):
                if RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS not in self.risk_vectors:
                    self.risk_vectors.append(RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS)
        self.generic_visit(node)


def inspect_source_ast(source_code: str, file_path: str = "source.py") -> ASTAnalysisResult:
    """
    Deterministically parses Python source code and extracts function signatures
    and structural risk vectors.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return ASTAnalysisResult(
            file_path=file_path,
            functions=[],
            imported_symbols=[],
            total_lines=len(source_code.splitlines()),
            raw_source=source_code,
        )

    imported_symbols = []
    functions: List[FunctionSignature] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_symbols.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imported_symbols.append(f"{module}.{alias.name}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params: List[FunctionParameter] = []
            
            # Position defaults alignment
            defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + list(node.args.defaults)
            
            for arg, default in zip(node.args.args, defaults):
                type_ann = ast.unparse(arg.annotation) if arg.annotation else None
                default_val = ast.unparse(default) if default else None
                params.append(FunctionParameter(
                    name=arg.arg,
                    type_annotation=type_ann,
                    default_value=default_val,
                ))

            ret_type = ast.unparse(node.returns) if node.returns else None
            docstring = ast.get_docstring(node)

            # Analyze function body for risk vectors
            visitor = RiskVisitor()
            visitor.visit(node)

            functions.append(FunctionSignature(
                name=node.name,
                line_number=node.lineno,
                parameters=params,
                return_type=ret_type,
                risk_vectors=visitor.risk_vectors,
                docstring=docstring,
            ))

    return ASTAnalysisResult(
        file_path=file_path,
        functions=functions,
        imported_symbols=imported_symbols,
        total_lines=len(source_code.splitlines()),
        raw_source=source_code,
    )
