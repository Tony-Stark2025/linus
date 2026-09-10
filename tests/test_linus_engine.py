"""
Unit and Integration Tests for Linus Engine.
"""

import pytest
from linus.agent import LinusAgent
from linus.scenarios import SCENARIO_CHECKOUT_DISCOUNT, SCENARIO_GUEST_SUBSCRIPTION, SCENARIO_FINANCIAL_AOV
from linus.tools.ast_inspector import inspect_source_ast
from linus.models import RiskVectorType, TestStatus


def test_ast_inspector_detects_empty_indexing():
    """Verify AST inspector identifies items[0] as an empty collection risk."""
    source = SCENARIO_CHECKOUT_DISCOUNT["source_code"]
    res = inspect_source_ast(source, "checkout_service.py")
    assert len(res.functions) == 1
    fn = res.functions[0]
    assert fn.name == "calculate_order_total"
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING in fn.risk_vectors


def test_ast_inspector_detects_zero_division():
    """Verify AST inspector identifies division operations."""
    source = SCENARIO_FINANCIAL_AOV["source_code"]
    res = inspect_source_ast(source, "ledger.py")
    fn = res.functions[0]
    assert RiskVectorType.ZERO_DIVISION in fn.risk_vectors


def test_linus_audit_proves_defect_and_dual_verification():
    """Verify full end-to-end Linus audit on Scenario 1."""
    sc = SCENARIO_CHECKOUT_DISCOUNT
    agent = LinusAgent()
    
    result = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
        baseline_test_code=sc["baseline_test_code"],
        candidate_patch=sc["patched_code"],
        patch_explanation=sc["explanation"],
    )

    # Assured Execution Gate checks
    assert result.defect_proven is True
    assert result.status == "VERIFIED_DEFECT"
    assert result.failing_test is not None
    assert result.failing_test.status == TestStatus.UNCAUGHT_EXCEPTION
    assert result.failing_test.exception_type == "IndexError"

    # Dual verification checks
    assert result.dual_verification is not None
    assert result.dual_verification.verified is True
    assert result.dual_verification.adversarial_test_passed is True
    assert result.dual_verification.baseline_suite_passed is True
    assert "test_linus_pr_PR-104.py" in (result.dual_verification.permanent_test_path or "")


def test_linus_audit_scenario_guest_subscription():
    """Verify full Linus audit on Scenario 2 (Guest Subscription null check)."""
    sc = SCENARIO_GUEST_SUBSCRIPTION
    agent = LinusAgent()
    
    result = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
        baseline_test_code=sc["baseline_test_code"],
        candidate_patch=sc["patched_code"],
        patch_explanation=sc["explanation"],
    )

    assert result.defect_proven is True
    assert result.failing_test.exception_type == "TypeError"
    assert result.dual_verification.verified is True
