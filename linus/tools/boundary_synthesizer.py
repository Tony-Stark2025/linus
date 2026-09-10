"""
Autonomous Adversarial Boundary Synthesizer for Linus.
Analyzes AST-detected risk vectors and synthesizes candidate adversarial pytest suites
and defensive patches for arbitrary Python functions without requiring pre-scripted tests.
"""

from typing import Optional, List, Dict, Tuple
from linus.models import ASTAnalysisResult, FunctionSignature, RiskVectorType


class BoundarySynthesizer:
    """
    Synthesizes targeted adversarial boundary tests based on AST structural risk vectors.
    """

    def synthesize_boundary_test(
        self,
        ast_summary: ASTAnalysisResult,
        source_filename: str = "service.py",
        target_function_name: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Synthesizes a minimal pytest adversarial reproduction test.
        Returns: (test_code, hypothesis_description)
        """
        module_name = source_filename.replace(".py", "")
        
        # Pick the target function
        target_fn: Optional[FunctionSignature] = None
        if target_function_name:
            for fn in ast_summary.functions:
                if fn.name == target_function_name:
                    target_fn = fn
                    break
        elif ast_summary.functions:
            # Pick the function with the most risk vectors, or the first one
            target_fn = max(ast_summary.functions, key=lambda f: len(f.risk_vectors), default=ast_summary.functions[0])

        if not target_fn:
            # Fallback test if no functions detected
            test_code = f"""import pytest
import {module_name}

def test_ambient_fallback_linus():
    assert hasattr({module_name}, '__name__')
"""
            return test_code, "Fallback module import test"

        fn_name = target_fn.name
        param_names = [p.name for p in target_fn.parameters]
        risk_types = target_fn.risk_vectors

        # Formulate hypothesis and test arguments
        if RiskVectorType.EMPTY_COLLECTION_INDEXING in risk_types:
            hypothesis = f"Empty collection passed to '{fn_name}' triggers unhandled IndexError on direct subscript."
            test_args = []
            for p in param_names:
                p_lower = p.lower()
                if "cart" in p_lower or "order" in p_lower:
                    test_args.append('{"items": []}')
                else:
                    test_args.append("[]")
            args_str = ", ".join(test_args)
            test_code = f"""import pytest
from {module_name} import {fn_name}

def test_empty_collection_boundary_linus():
    \"\"\"Linus Adversarial Test: Verifies empty collection handling.\"\"\"
    # Hypothesis: Direct indexing without length guard raises IndexError
    _ = {fn_name}({args_str})
"""
            return test_code, hypothesis

        elif RiskVectorType.NULLABLE_ATTRIBUTE_ACCESS in risk_types:
            hypothesis = f"Passing None for nullable object in '{fn_name}' triggers unhandled TypeError/AttributeError."
            test_args = []
            for i, p in enumerate(param_names):
                if i == 0:
                    test_args.append("None")
                else:
                    test_args.append("50.0")
            args_str = ", ".join(test_args)
            test_code = f"""import pytest
from {module_name} import {fn_name}

def test_null_object_boundary_linus():
    \"\"\"Linus Adversarial Test: Verifies NoneType attribute resilience.\"\"\"
    # Hypothesis: Unchecked attribute access on None raises TypeError
    _ = {fn_name}({args_str})
"""
            return test_code, hypothesis

        elif RiskVectorType.ZERO_DIVISION in risk_types:
            hypothesis = f"Zero divisor or zero count passed to '{fn_name}' triggers unhandled ZeroDivisionError."
            test_args = []
            for p in param_names:
                p_lower = p.lower()
                if "total" in p_lower or "revenue" in p_lower or "sum" in p_lower:
                    test_args.append("0.0")
                elif "count" in p_lower or "order" in p_lower or "num" in p_lower or "divisor" in p_lower:
                    test_args.append("0")
                else:
                    test_args.append("0")
            args_str = ", ".join(test_args)
            test_code = f"""import pytest
from {module_name} import {fn_name}

def test_zero_division_boundary_linus():
    \"\"\"Linus Adversarial Test: Verifies zero division resilience.\"\"\"
    # Hypothesis: Division by zero divisor triggers ZeroDivisionError
    _ = {fn_name}({args_str})
"""
            return test_code, hypothesis

        elif RiskVectorType.UNCHECKED_DICT_KEY in risk_types:
            hypothesis = f"Missing dictionary key in '{fn_name}' triggers unhandled KeyError."
            test_args = ["{}" for _ in param_names]
            args_str = ", ".join(test_args)
            test_code = f"""import pytest
from {module_name} import {fn_name}

def test_missing_dict_key_boundary_linus():
    \"\"\"Linus Adversarial Test: Verifies missing dictionary key resilience.\"\"\"
    # Hypothesis: Unchecked dictionary key access triggers KeyError
    _ = {fn_name}({args_str})
"""
            return test_code, hypothesis

        # Default boundary test if no explicit risk flagged
        hypothesis = f"Smoke test on '{fn_name}' with minimal arguments."
        args_str = ", ".join(["None" for _ in param_names])
        test_code = f"""import pytest
from {module_name} import {fn_name}

def test_smoke_boundary_linus():
    _ = {fn_name}({args_str})
"""
        return test_code, hypothesis
