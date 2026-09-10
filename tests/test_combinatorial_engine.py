"""
Combinatorial & Stress Test Suite for Linus Engine.
Generates over 100+ parameterized combinations across syntax structures, naming conventions,
nested expressions, and edge-case permutations.
"""

import ast
import pytest
from linus.tools.ast_inspector import inspect_source_ast
from linus.tools.boundary_synthesizer import BoundarySynthesizer
from linus.tools.patch_verifier import DualRegressionVerifier
from linus.tools.sandbox_runner import SandboxTestRunner
from linus.models import RiskVectorType


# ---------------------------------------------------------------------------
# 1. Parameterized Subscript & Naming Combinations (30 tests)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("var_name", [
    "items", "data", "records", "orders", "users",
    "cart_items", "_items", "itemList", "ITEMS_DATA", "elements_2"
])
@pytest.mark.parametrize("idx", [0, 1, 99])
def test_combinatorial_subscript_naming(var_name, idx):
    code = f"def handle_{var_name}({var_name}): return {var_name}[{idx}]"
    res = inspect_source_ast(code, "test.py")
    assert len(res.functions) == 1
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING in res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 2. Parameterized Division & Operator Combinations (30 tests)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dividend", ["100", "total", "revenue", "count * 2", "sum(vals)"])
@pytest.mark.parametrize("divisor", ["orders", "users", "items_count", "denominator", "total_days", "batch_size"])
def test_combinatorial_division_expressions(dividend, divisor):
    code = f"def compute({divisor}, vals=[], total=0, revenue=0, count=0): return {dividend} / {divisor}"
    res = inspect_source_ast(code, "calc.py")
    assert len(res.functions) == 1
    assert RiskVectorType.ZERO_DIVISION in res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 3. Parameterized Attribute Dereferencing Combinations (30 tests)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("obj_name", ["user", "account", "profile", "client", "customer", "record"])
@pytest.mark.parametrize("attr_name", ["id", "tier", "role", "email", "metadata"])
def test_combinatorial_attribute_access(obj_name, attr_name):
    code = f"def get_info({obj_name}): return {obj_name}.{attr_name}"
    res = inspect_source_ast(code, "info.py")
    assert len(res.functions) == 1
    assert RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS in res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 4. Synthesizer Combinatorial Validity (20 tests)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fn_name", ["process_cart", "handle_order", "parse_batch", "audit_payment"])
@pytest.mark.parametrize("arg_type", ["items", "user", "count", "data"])
def test_combinatorial_synthesizer_syntax(fn_name, arg_type):
    if arg_type == "items":
        body = f"return {arg_type}[0]"
    elif arg_type == "user":
        body = f"return {arg_type}.tier"
    elif arg_type == "count":
        body = f"return 100 / {arg_type}"
    else:
        body = f"return {arg_type}['id']"

    code = f"def {fn_name}({arg_type}): {body}"
    ast_res = inspect_source_ast(code, "comb.py")
    synthesizer = BoundarySynthesizer()
    test_code, hyp = synthesizer.synthesize_boundary_test(ast_res, "comb.py")
    
    # Must be 100% valid Python syntax
    parsed = ast.parse(test_code)
    assert parsed is not None
    assert fn_name in test_code


# ---------------------------------------------------------------------------
# 5. Multi-Function Module Parsing (10 tests)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("num_funcs", [1, 2, 3, 5, 8])
def test_multi_function_module_parsing(num_funcs):
    func_lines = []
    for i in range(num_funcs):
        func_lines.append(f"def func_{i}(x_{i}):\n    return x_{i}[0]\n")
    code = "\n".join(func_lines)
    res = inspect_source_ast(code, "multi.py")
    assert len(res.functions) == num_funcs
    for i in range(num_funcs):
        assert res.functions[i].name == f"func_{i}"
        assert RiskVectorType.EMPTY_COLLECTION_INDEXING in res.functions[i].risk_vectors
