"""
Integration Tests for LinusAgent and Strands Agents SDK.
Tests end-to-end audit lifecycle, all 4 scenarios, telemetry events sequence, and autonomous synthesis.
"""

import pytest
from linus.agent import LinusAgent
from linus.scenarios import (
    SCENARIO_CHECKOUT_DISCOUNT,
    SCENARIO_GUEST_SUBSCRIPTION,
    SCENARIO_FINANCIAL_AOV,
    SCENARIO_SOUND_PAYMENT_GATEWAY,
)
from linus.models import TestStatus


# ---------------------------------------------------------------------------
# 1. End-to-End Enterprise Scenario Audits
# ---------------------------------------------------------------------------

def test_audit_pr_104_checkout_discount():
    sc = SCENARIO_CHECKOUT_DISCOUNT
    events = []
    agent = LinusAgent(telemetry_callback=lambda e: events.append(e))
    
    res = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
        baseline_test_code=sc["baseline_test_code"],
        candidate_patch=sc["patched_code"],
        patch_explanation=sc["explanation"],
    )

    assert res.pr_id == "PR-104"
    assert res.status == "VERIFIED_DEFECT"
    assert res.defect_proven is True
    assert res.failing_test.exception_type == "IndexError"
    assert res.dual_verification.verified is True

    # Check telemetry phases
    phases = [e["phase"] for e in events]
    assert "INGRESS" in phases
    assert "AST_ANALYSIS" in phases
    assert "SANDBOX_TEST" in phases
    assert "CRASH_PROVEN" in phases
    assert "PATCH_SYNTHESIS" in phases
    assert "DUAL_VERIFICATION" in phases
    assert "VERIFICATION_SUCCESS" in phases
    assert "RECURSIVE_TEST_COMMITTED" in phases


def test_audit_pr_209_guest_subscription():
    sc = SCENARIO_GUEST_SUBSCRIPTION
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
        baseline_test_code=sc["baseline_test_code"],
        candidate_patch=sc["patched_code"],
        patch_explanation=sc["explanation"],
    )
    assert res.pr_id == "PR-209"
    assert res.status == "VERIFIED_DEFECT"
    assert res.failing_test.exception_type == "TypeError"
    assert res.dual_verification.verified is True


def test_audit_pr_318_financial_aov():
    sc = SCENARIO_FINANCIAL_AOV
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
        baseline_test_code=sc["baseline_test_code"],
        candidate_patch=sc["patched_code"],
        patch_explanation=sc["explanation"],
    )
    assert res.pr_id == "PR-318"
    assert res.status == "VERIFIED_DEFECT"
    assert res.failing_test.exception_type == "ZeroDivisionError"
    assert res.dual_verification.verified is True


def test_audit_pr_401_clean_sound_payment():
    sc = SCENARIO_SOUND_PAYMENT_GATEWAY
    events = []
    agent = LinusAgent(telemetry_callback=lambda e: events.append(e))
    res = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
        baseline_test_code=sc["baseline_test_code"],
    )
    assert res.pr_id == "PR-401"
    assert res.status == "VERIFIED_CLEAN"
    assert res.defect_proven is False
    assert res.failing_test.status == TestStatus.PASS

    phases = [e["phase"] for e in events]
    assert "TEST_PASSED" in phases
    assert "AMBIENT_SILENCE" in phases
    assert "CRASH_PROVEN" not in phases


# ---------------------------------------------------------------------------
# 2. Autonomous Boundary Synthesis in Audit Cycle
# ---------------------------------------------------------------------------

def test_audit_with_autonomous_boundary_synthesis():
    # Code with zero division, but NO adversarial test provided
    code = """def calc_ratio(total, count):
    return total / count
"""
    events = []
    agent = LinusAgent(telemetry_callback=lambda e: events.append(e))
    res = agent.audit_pull_request(
        pr_id="PR-AUTO-1",
        repository="org/repo",
        source_code=code,
        target_filename="ratio.py",
        adversarial_test_code=None,  # Trigger autonomous boundary synthesis
    )
    assert res.defect_proven is True
    assert res.failing_test.exception_type == "ZeroDivisionError"
    
    phases = [e["phase"] for e in events]
    assert "HYPOTHESIS_SYNTHESIS" in phases
    assert "HYPOTHESIS_FORMULATED" in phases


def test_audit_tracks_execution_time():
    sc = SCENARIO_CHECKOUT_DISCOUNT
    agent = LinusAgent()
    res = agent.audit_pull_request(
        pr_id=sc["id"],
        repository=sc["repository"],
        source_code=sc["source_code"],
        target_filename=sc["target_file"],
        adversarial_test_code=sc["adversarial_test_code"],
    )
    assert res.execution_time_seconds > 0.0
    assert len(res.telemetry_trace) > 0
