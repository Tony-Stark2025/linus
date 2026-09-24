"""
Comprehensive Verification Suite for Project Evaluation Report Remediations.
Tests all architectural, AST, synthesis, sandbox security, and serverless operational fixes.
"""

import ast
import hashlib
import hmac
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from linus.agent import LinusAgent
from linus.models import RiskVectorType, TestStatus
from linus.scenarios import (
    SCENARIO_CHECKOUT_DISCOUNT,
    SCENARIO_GUEST_SUBSCRIPTION,
    SCENARIO_FINANCIAL_AOV,
    SCENARIO_SOUND_PAYMENT_GATEWAY,
)
from linus.tools.ast_inspector import inspect_source_ast
from linus.tools.boundary_synthesizer import BoundarySynthesizer
from linus.tools.patch_verifier import DualRegressionVerifier, commit_permanent_test
from linus.tools.sandbox_runner import SandboxTestRunner
from web_demo.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Class Methods (ast.ClassDef), Nested Functions & Parameter Kinds
# ---------------------------------------------------------------------------

def test_ast_detects_class_methods_and_audits_end_to_end():
    code = """class OrderService:
    def __init__(self):
        self.tax = 0.08

    def checkout(self, items):
        return items[0] * (1 + self.tax)
"""
    ast_res = inspect_source_ast(code, "order_service.py")
    assert len(ast_res.functions) == 1
    fn = ast_res.functions[0]
    assert fn.name == "checkout"
    assert fn.class_name == "OrderService"
    assert [p.name for p in fn.parameters] == ["items"]
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING in fn.risk_vectors

    # End-to-end audit on class method with autonomous test & patch synthesis
    agent = LinusAgent()
    audit_res = agent.audit_pull_request(
        pr_id="PR-CLASS-1",
        repository="acme/orders",
        source_code=code,
        target_filename="order_service.py",
    )
    assert audit_res.defect_proven is True
    assert audit_res.failing_test.exception_type == "IndexError"
    assert audit_res.patch is not None
    assert audit_res.dual_verification is not None
    assert audit_res.dual_verification.verified is True


def test_ast_extracts_posonly_kwonly_vararg_kwarg():
    code = """def advanced_sig(pos_only: int, /, standard: str, *args: int, kw_only: float = 1.5, **kwargs: str) -> bool:
    return True
"""
    res = inspect_source_ast(code, "sig.py")
    assert len(res.functions) == 1
    params = res.functions[0].parameters
    kinds = {p.name: p.kind for p in params}
    assert kinds["pos_only"] == "positional_only"
    assert kinds["standard"] == "positional_or_keyword"
    assert kinds["args"] == "var_positional"
    assert kinds["kw_only"] == "keyword_only"
    assert kinds["kwargs"] == "var_keyword"


# ---------------------------------------------------------------------------
# 2. Control-Flow Guard Awareness & Edge-Case AST Fixes
# ---------------------------------------------------------------------------

def test_ast_control_flow_awareness_on_patched_scenarios():
    """Verifies that guarded code (including Linus's own scenario patches) does not trigger false risk flags."""
    # PR-104: `if not items: return 0.0` eliminates EMPTY_COLLECTION_INDEXING on `items[0]`
    res_104 = inspect_source_ast(SCENARIO_CHECKOUT_DISCOUNT["patched_code"], "checkout_service.py")
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING not in res_104.functions[0].risk_vectors

    # PR-209: `if not user:` and `user.get(...)` eliminates NULLABLE_ATTRIBUTE_ACCESS & UNCHECKED_DICT_KEY
    res_209 = inspect_source_ast(SCENARIO_GUEST_SUBSCRIPTION["patched_code"], "subscription_billing.py")
    assert res_209.functions[0].risk_vectors == []

    # PR-318: `if total_orders <= 0: return 0.0` eliminates ZERO_DIVISION
    res_318 = inspect_source_ast(SCENARIO_FINANCIAL_AOV["patched_code"], "ledger_metrics.py")
    assert res_318.functions[0].risk_vectors == []

    # PR-401: sound payment gateway has zero unguarded risk vectors
    res_401 = inspect_source_ast(SCENARIO_SOUND_PAYMENT_GATEWAY["source_code"], "payment_processor.py")
    assert res_401.functions[0].risk_vectors == []


def test_ast_try_except_guard_suppresses_caught_risk():
    code = """def safe_get_first(items):
    try:
        return items[0]
    except IndexError:
        return None
"""
    res = inspect_source_ast(code, "safe.py")
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING not in res.functions[0].risk_vectors


def test_ast_negative_indexing_and_boolean_key_classification():
    neg_code = "def get_last(items): return items[-1]"
    neg_res = inspect_source_ast(neg_code, "neg.py")
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING in neg_res.functions[0].risk_vectors

    bool_code = "def get_bool_flag(lookup): return lookup[True]"
    bool_res = inspect_source_ast(bool_code, "bool_key.py")
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING not in bool_res.functions[0].risk_vectors


def test_ast_integer_overflow_and_inverted_logic_vectors():
    overflow_code = "def compute_pow(base, exponent): return base ** exponent"
    ov_res = inspect_source_ast(overflow_code, "overflow.py")
    assert RiskVectorType.BOUNDARY_INTEGER_OVERFLOW in ov_res.functions[0].risk_vectors

    inverted_code = """def buggy_guard(items):
    if not items:
        return items[0]
    return items[0]
"""
    inv_res = inspect_source_ast(inverted_code, "inverted.py")
    assert RiskVectorType.INVERTED_LOGIC in inv_res.functions[0].risk_vectors


# ---------------------------------------------------------------------------
# 3. Multi-Risk Boundary Synthesis, Subdirectory Imports & Nullable Positioning
# ---------------------------------------------------------------------------

def test_synthesizer_handles_subdirectory_paths():
    synthesizer = BoundarySynthesizer()
    code = "def calculate(items): return items[0]"
    ast_res = inspect_source_ast(code, "services/checkout/pricing.py")
    test_code, _ = synthesizer.synthesize_boundary_test(ast_res, "services/checkout/pricing.py")
    assert "from pricing import calculate" in test_code
    assert ast.parse(test_code) is not None


def test_multi_risk_synthesis_prevents_masking():
    """
    If a function has two risks (e.g., an index operation on a pre-populated fallback list
    plus an unguarded division by `count`), multi-risk synthesis generates tests for BOTH
    risks and catches the ZeroDivisionError.
    """
    code = """def analyze_batch(items, count):
    safe_list = items or [10]
    first = safe_list[0]
    return first / count
"""
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id="PR-MULTI-RISK",
        repository="acme/analytics",
        source_code=code,
        target_filename="batch.py",
    )
    assert res.defect_proven is True
    assert res.failing_test.exception_type == "ZeroDivisionError"
    assert res.dual_verification is not None
    assert res.dual_verification.verified is True


def test_nullable_second_parameter_targeted():
    code = """from typing import Optional, Dict
def compute_fee(base_amount: float, user: Optional[Dict]) -> float:
    return base_amount + user.discount
"""
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id="PR-SECOND-PARAM",
        repository="acme/billing",
        source_code=code,
        target_filename="fee.py",
    )
    assert res.defect_proven is True
    assert res.failing_test.exception_type in ("AttributeError", "TypeError")
    assert res.dual_verification.verified is True


# ---------------------------------------------------------------------------
# 4. Baseline Test Counter & Innermost Traceback Line Number
# ---------------------------------------------------------------------------

def test_patch_verifier_counts_all_passing_baseline_tests():
    verifier = DualRegressionVerifier()
    orig = "def div(a, b): return a / b\n"
    patch = "def div(a, b): return 0.0 if b == 0 else a / b\n"
    adv = "from service import div\ndef test_zero(): assert div(10, 0) == 0.0\n"
    baseline = """from service import div
def test_one(): assert div(10, 2) == 5.0
def test_two(): assert div(9, 3) == 3.0
def test_three(): assert div(20, 4) == 5.0
"""
    res = verifier.verify_patch(orig, patch, adv, baseline, "service.py", "PR-COUNT")
    assert res.verified is True
    assert res.baseline_tests_count == 3


def test_sandbox_extracts_innermost_source_line_number():
    runner = SandboxTestRunner()
    sc = SCENARIO_CHECKOUT_DISCOUNT
    res = runner.execute_test(
        source_code=sc["source_code"],
        test_code=sc["adversarial_test_code"],
        source_filename=sc["target_file"],
        test_filename="test_adversarial_linus.py",
    )
    assert res.status == TestStatus.UNCAUGHT_EXCEPTION
    assert res.exception_type == "IndexError"
    # Line 11 in checkout_service.py is `primary_category = items[0].get("category", "general")`
    assert res.exception_line == 11


# ---------------------------------------------------------------------------
# 5. Sandbox Security & Serverless Hardening (SEC-01, SEC-02, SEC-03, SEC-04, EROFS)
# ---------------------------------------------------------------------------

def test_sandbox_blocks_network_egress():
    runner = SandboxTestRunner()
    source = """import socket
def try_connect():
    s = socket.socket()
    s.connect(("169.254.169.254", 80))
"""
    test = """from service import try_connect
def test_ssrf_blocked():
    try_connect()
"""
    res = runner.execute_test(source, test)
    assert res.exit_code != 0
    assert res.exception_type == "PermissionError"


def test_sandbox_rejects_extra_files_path_traversal():
    runner = SandboxTestRunner()
    with pytest.raises(ValueError, match="Path traversal"):
        runner.execute_test(
            source_code="x = 1",
            test_code="def test_x(): assert True",
            extra_files={"../../outside_escape.py": "pwn = True"},
        )


def test_commit_permanent_test_falls_back_on_readonly_filesystem(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(os, "access", lambda path, mode: False)
    written = commit_permanent_test(
        permanent_test_path="tests/regressions/test_linus_erofs.py",
        test_code="def test_erofs(): assert True\n",
        base_dir=Path("/app_readonly_mock"),
    )
    assert written.exists()
    assert "linus_regressions" in str(written)
    written.unlink(missing_ok=True)


def test_github_webhook_hmac_verification(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "top_secret_webhook_key")
    payload_bytes = json.dumps({
        "action": "opened",
        "pull_request": {"number": 77},
        "repository": {"full_name": "acme/secure-repo"},
    }).encode("utf-8")

    # 1. Missing or wrong signature -> 401 Unauthorized
    res_unauth = client.post(
        "/webhook/github",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=invalid"},
    )
    assert res_unauth.status_code == 401

    # 2. Valid HMAC-SHA256 signature -> 200 INGESTED
    valid_sig = "sha256=" + hmac.new(
        b"top_secret_webhook_key",
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    res_ok = client.post(
        "/webhook/github",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_sig},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "INGESTED"


# ---------------------------------------------------------------------------
# 6. Deep Edge Cases: Class __init__ Dependencies, Async Coroutines, If/Else & IsInstance Guards
# ---------------------------------------------------------------------------

def test_class_with_required_init_dependencies_audits_and_verifies():
    code = """class OrderService:
    def __init__(self, db_client, tax_rate: float):
        self.db = db_client
        self.tax_rate = tax_rate

    def checkout(self, items):
        return items[0] * (1 + self.tax_rate)
"""
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id="PR-CLASS-INIT-DEPS",
        repository="acme/orders",
        source_code=code,
        target_filename="order_service.py",
    )
    assert res.defect_proven is True
    assert res.failing_test.exception_type == "IndexError"
    assert res.dual_verification is not None
    assert res.dual_verification.verified is True


def test_async_function_end_to_end_audit_and_patch_verification():
    code = """async def fetch_first_record(items):
    return items[0]
"""
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id="PR-ASYNC-DEF",
        repository="acme/async-service",
        source_code=code,
        target_filename="async_service.py",
    )
    assert res.defect_proven is True
    assert res.failing_test.exception_type == "IndexError"
    assert res.dual_verification is not None
    assert res.dual_verification.verified is True


def test_ast_if_else_and_isinstance_guards_prevent_false_positives():
    if_else_code = """def safe_divide(a, b):
    if b == 0:
        return 0.0
    else:
        return a / b
"""
    res_if_else = inspect_source_ast(if_else_code, "div.py")
    assert res_if_else.functions[0].risk_vectors == []

    isinstance_code = """def safe_user_name(user):
    if isinstance(user, object) and hasattr(user, "name"):
        return user.name
    return "guest"
"""
    res_isinst = inspect_source_ast(isinstance_code, "user.py")
    assert res_isinst.functions[0].risk_vectors == []


def test_integer_overflow_end_to_end_audit_and_verification():
    code = """def compute_pow(base, exponent):
    return base ** exponent
"""
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id="PR-OVERFLOW-E2E",
        repository="acme/math",
        source_code=code,
        target_filename="math_utils.py",
    )
    assert res.defect_proven is True
    assert res.failing_test.exception_type == "OverflowError"
    assert res.dual_verification is not None
    assert res.dual_verification.verified is True


def test_sandbox_source_filename_traversal_and_proc_environ_lockdown():
    runner = SandboxTestRunner()
    with pytest.raises(ValueError, match="Invalid source_filename path traversal"):
        runner.execute_test(
            source_code="x = 1",
            test_code="def test_x(): assert True",
            source_filename="../../etc/passwd",
        )

    res_proc = runner.execute_test(
        source_code="def leak():\n    return open('/proc/1/environ').read()\n",
        test_code="from service import leak\ndef test_leak():\n    leak()\n",
    )
    assert res_proc.exit_code != 0
    assert res_proc.exception_type == "PermissionError"

