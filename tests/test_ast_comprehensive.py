"""
Comprehensive Unit Tests for Deterministic AST Inspector.
Covers dozens of syntax variations, edge cases, parameter types, operators, and risk vectors.
"""

import pytest
from linus.tools.ast_inspector import inspect_source_ast, RiskVisitor
from linus.models import RiskVectorType


# ---------------------------------------------------------------------------
# 1. Subscript and Indexing Tests (EMPTY_COLLECTION_INDEXING & UNCHECKED_DICT_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index_val", [0, 1, 2, 5, 99])
def test_ast_subscript_integer_constants(index_val):
    code = f"def process(items): return items[{index_val}]"
    res = inspect_source_ast(code, "test.py")
    assert len(res.functions) == 1
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING in res.functions[0].risk_vectors


@pytest.mark.parametrize("key_name", ["id", "token", "email", "username", "tier", "created_at", "total_price"])
def test_ast_subscript_string_keys(key_name):
    code = f"def lookup(data): return data['{key_name}']"
    res = inspect_source_ast(code, "test.py")
    assert len(res.functions) == 1
    assert RiskVectorType.UNCHECKED_DICT_KEY in res.functions[0].risk_vectors


@pytest.mark.parametrize("slice_expr", [":", "1:", ":5", "1:5", "::2", "1:10:2"])
def test_ast_subscript_slices_no_empty_collection_flag(slice_expr):
    # Slicing a list in Python never raises IndexError on empty collections (e.g. [][0:1] == [])
    code = f"def safe_slice(items): return items[{slice_expr}]"
    res = inspect_source_ast(code, "test.py")
    assert len(res.functions) == 1
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING not in res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 2. Binary Operations & Division Tests (ZERO_DIVISION)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("op_str", ["/", "//", "%"])
def test_ast_division_operators(op_str):
    code = f"def calc(a, b): return a {op_str} b"
    res = inspect_source_ast(code, "calc.py")
    assert len(res.functions) == 1
    assert RiskVectorType.ZERO_DIVISION in res.functions[0].risk_vectors


@pytest.mark.parametrize("op_str", ["+", "-", "*", "**", "@", "&", "|", "^", ">>", "<<"])
def test_ast_non_division_operators(op_str):
    code = f"def calc(a, b): return a {op_str} b"
    res = inspect_source_ast(code, "calc.py")
    assert len(res.functions) == 1
    assert RiskVectorType.ZERO_DIVISION not in res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 3. Attribute Access Tests (NULLABLE_ATTRIBUTE_ACCESS)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("param_name", ["user", "account", "profile", "customer", "session", "record", "payload", "entity"])
def test_ast_parameter_attribute_access(param_name):
    code = f"def handle({param_name}): return {param_name}.status"
    res = inspect_source_ast(code, "handler.py")
    assert len(res.functions) == 1
    assert RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS in res.functions[0].risk_vectors


@pytest.mark.parametrize("chained_attr", ["user.profile.tier", "order.customer.id", "config.database.port"])
def test_ast_chained_attribute_access(chained_attr):
    code = f"def check(data): return {chained_attr}"
    res = inspect_source_ast(code, "check.py")
    assert len(res.functions) == 1
    assert RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS in res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 4. Multi-Risk Functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("func_body, expected_risks", [
    ("return items[0] / count", [RiskVectorType.EMPTY_COLLECTION_INDEXING, RiskVectorType.ZERO_DIVISION]),
    ("return user.tier + data['id']", [RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS, RiskVectorType.UNCHECKED_DICT_KEY]),
    ("return items[0]['price'] / total", [RiskVectorType.EMPTY_COLLECTION_INDEXING, RiskVectorType.UNCHECKED_DICT_KEY, RiskVectorType.ZERO_DIVISION]),
    ("return user.profile.name + str(items[0])", [RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS, RiskVectorType.EMPTY_COLLECTION_INDEXING]),
])
def test_ast_multi_risk_combinations(func_body, expected_risks):
    code = f"def complex_fn(items, user, data, count, total): {func_body}"
    res = inspect_source_ast(code, "complex.py")
    fn = res.functions[0]
    for risk in expected_risks:
        assert risk in fn.risk_vectors


# ---------------------------------------------------------------------------
# 5. Function Signatures, Arguments & Return Types
# ---------------------------------------------------------------------------

def test_ast_function_no_args():
    code = "def get_pi() -> float: return 3.14159"
    res = inspect_source_ast(code, "math.py")
    assert len(res.functions) == 1
    assert len(res.functions[0].parameters) == 0
    assert res.functions[0].return_type == "float"


def test_ast_function_with_defaults_and_types():
    code = """def create_order(item_id: str, qty: int = 1, discount: float = 0.0) -> dict:
    return {'id': item_id, 'qty': qty, 'discount': discount}
"""
    res = inspect_source_ast(code, "order.py")
    fn = res.functions[0]
    assert len(fn.parameters) == 3
    assert fn.parameters[0].name == "item_id"
    assert fn.parameters[0].type_annotation == "str"
    assert fn.parameters[0].default_value is None

    assert fn.parameters[1].name == "qty"
    assert fn.parameters[1].type_annotation == "int"
    assert fn.parameters[1].default_value == "1"

    assert fn.parameters[2].name == "discount"
    assert fn.parameters[2].type_annotation == "float"
    assert fn.parameters[2].default_value == "0.0"


def test_ast_async_function():
    code = "async def fetch_data(client, url: str) -> str: return await client.get(url)"
    res = inspect_source_ast(code, "fetch.py")
    assert len(res.functions) == 1
    assert res.functions[0].name == "fetch_data"
    assert RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS in res.functions[0].risk_vectors


def test_ast_function_docstring():
    code = '''def calculate(x):
    """Computes square of x with high precision."""
    return x * x
'''
    res = inspect_source_ast(code, "doc.py")
    assert res.functions[0].docstring == "Computes square of x with high precision."


# ---------------------------------------------------------------------------
# 6. Syntax Errors, Malformed Code, and Edge Cases
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("invalid_code", [
    "def unclosed_fn(x: return x",
    "class 123InvalidName: pass",
    "def foo(x)): pass",
    "for while if else",
    "<<< >>> === !!!",
])
def test_ast_gracefully_handles_syntax_errors(invalid_code):
    res = inspect_source_ast(invalid_code, "broken.py")
    assert res.functions == []
    assert res.imported_symbols == []


@pytest.mark.parametrize("empty_code", [
    "",
    "   ",
    "\n\n\n",
    "# Only a comment line\n# Second comment line\n",
])
def test_ast_handles_empty_or_comment_files(empty_code):
    res = inspect_source_ast(empty_code, "empty.py")
    assert len(res.functions) == 0


# ---------------------------------------------------------------------------
# 7. Import Extraction
# ---------------------------------------------------------------------------

def test_ast_extracts_imports():
    code = """import os
import sys as system
from pathlib import Path
from typing import Dict, List, Optional
def run(): pass
"""
    res = inspect_source_ast(code, "script.py")
    assert "os" in res.imported_symbols
    assert "sys" in res.imported_symbols
    assert "pathlib.Path" in res.imported_symbols
    assert "typing.Dict" in res.imported_symbols
    assert "typing.List" in res.imported_symbols
    assert "typing.Optional" in res.imported_symbols
