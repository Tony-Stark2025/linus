"""
Comprehensive Unit Tests for BoundarySynthesizer.
Verifies test synthesis across varied parameter signatures, risk types, and guarantees syntactic validity.
"""

import ast
import pytest
from linus.tools.ast_inspector import inspect_source_ast
from linus.tools.boundary_synthesizer import BoundarySynthesizer
from linus.models import RiskVectorType


@pytest.fixture
def synthesizer():
    return BoundarySynthesizer()


# ---------------------------------------------------------------------------
# 1. Syntactic Validity Guarantee
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_snippet, mod_name", [
    ("def process(items): return items[0]", "proc"),
    ("def divide(a, b): return a / b", "math_ops"),
    ("def fetch_tier(user): return user.tier", "auth_svc"),
    ("def get_val(data): return data['key']", "kv_store"),
    ("def no_risk(x): return x + 1", "safe_mod"),
    ("def multi(items, user, count): return items[0] + user.id + (1 / count)", "combo"),
])
def test_synthesized_test_is_always_syntactically_valid(synthesizer, source_snippet, mod_name):
    ast_res = inspect_source_ast(source_snippet, f"{mod_name}.py")
    test_code, hypothesis = synthesizer.synthesize_boundary_test(ast_res, f"{mod_name}.py")
    
    # Must be parseable by Python AST with zero SyntaxError
    parsed_ast = ast.parse(test_code)
    assert isinstance(parsed_ast, ast.Module)
    assert len(parsed_ast.body) > 0
    assert "pytest" in test_code
    assert mod_name in test_code
    assert len(hypothesis) > 0


# ---------------------------------------------------------------------------
# 2. Risk Vector Targeting Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("param_name, expected_snippet", [
    ("items", "[]"),
    ("cart", '{"items": []}'),
    ("order", '{"items": []}'),
    ("arr", "[]"),
    ("elements", "[]"),
])
def test_empty_collection_synthesis_arguments(synthesizer, param_name, expected_snippet):
    code = f"def handle_{param_name}({param_name}): return {param_name}[0]"
    ast_res = inspect_source_ast(code, "service.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "service.py")
    assert "test_empty_collection_boundary_linus" in test_code
    assert expected_snippet in test_code
    assert "IndexError" in hyp


@pytest.mark.parametrize("div_param", ["count", "orders", "total_orders", "divisor", "b"])
def test_zero_division_synthesis_arguments(synthesizer, div_param):
    code = f"def compute_metric(revenue, {div_param}): return revenue / {div_param}"
    ast_res = inspect_source_ast(code, "analytics.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "analytics.py")
    assert "test_zero_division_boundary_linus" in test_code
    assert "ZeroDivisionError" in hyp


@pytest.mark.parametrize("user_param", ["user", "account", "profile", "customer", "session"])
def test_null_attribute_synthesis_arguments(synthesizer, user_param):
    code = f"def get_status({user_param}): return {user_param}.status"
    ast_res = inspect_source_ast(code, "auth.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "auth.py")
    assert "test_null_object_boundary_linus" in test_code
    assert "None" in test_code
    assert "TypeError" in hyp or "AttributeError" in hyp


@pytest.mark.parametrize("dict_param", ["data", "config", "payload", "record"])
def test_unchecked_dict_key_synthesis_arguments(synthesizer, dict_param):
    code = f"def read_{dict_param}({dict_param}): return {dict_param}['secret_key']"
    ast_res = inspect_source_ast(code, "keys.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "keys.py")
    assert "test_missing_dict_key_boundary_linus" in test_code
    assert "{}" in test_code
    assert "KeyError" in hyp


# ---------------------------------------------------------------------------
# 3. Multi-Function Modules & Target Selection
# ---------------------------------------------------------------------------

def test_synthesizer_selects_highest_risk_function(synthesizer):
    code = """def safe_helper(x):
    return x + 1

def risky_processor(items, count):
    # Two risks: empty indexing and zero division
    return items[0] / count

def minor_risky(a, b):
    return a / b
"""
    ast_res = inspect_source_ast(code, "multi.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "multi.py")
    # Should target risky_processor as it has 2 risk vectors
    assert "risky_processor" in test_code


def test_synthesizer_explicit_function_target(synthesizer):
    code = """def fn_one(a, b): return a / b
def fn_two(items): return items[0]
"""
    ast_res = inspect_source_ast(code, "multi.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "multi.py", target_function_name="fn_two")
    assert "fn_two" in test_code
    assert "test_empty_collection_boundary_linus" in test_code


def test_synthesizer_fallback_on_empty_ast(synthesizer):
    code = "# Just comments"
    ast_res = inspect_source_ast(code, "empty.py")
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "empty.py")
    assert "test_ambient_fallback_linus" in test_code
    assert ast.parse(test_code) is not None
