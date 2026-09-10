"""
Comprehensive Unit Tests for DualRegressionVerifier.
Verifies unified diff generation, dual-suite patch validation, regression detection, and permanent immunization paths.
"""

import pytest
from linus.tools.patch_verifier import DualRegressionVerifier
from linus.tools.sandbox_runner import SandboxTestRunner


@pytest.fixture
def verifier():
    return DualRegressionVerifier(SandboxTestRunner(default_timeout_seconds=5))


# ---------------------------------------------------------------------------
# 1. Unified Diff Generation Tests
# ---------------------------------------------------------------------------

def test_unified_diff_identical_strings(verifier):
    code = "def foo(): return 1\n"
    diff = verifier.generate_unified_diff(code, code, filename="foo.py")
    assert diff == ""


def test_unified_diff_added_line(verifier):
    orig = "def foo():\n    return 1\n"
    patch = "def foo():\n    # check\n    return 1\n"
    diff = verifier.generate_unified_diff(orig, patch, filename="service.py")
    assert "--- a/service.py" in diff
    assert "+++ b/service.py" in diff
    assert "+    # check" in diff


def test_unified_diff_removed_line(verifier):
    orig = "def foo():\n    unused_call()\n    return 1\n"
    patch = "def foo():\n    return 1\n"
    diff = verifier.generate_unified_diff(orig, patch, filename="app.py")
    assert "-    unused_call()" in diff


# ---------------------------------------------------------------------------
# 2. Dual-Suite Patch Verification Tests
# ---------------------------------------------------------------------------

def test_verify_patch_success_both_suites(verifier):
    orig_code = """def get_first(items):
    return items[0]
"""
    patched_code = """def get_first(items):
    if not items:
        return None
    return items[0]
"""
    adv_test = """from service import get_first
def test_empty():
    assert get_first([]) is None
"""
    baseline_test = """from service import get_first
def test_normal():
    assert get_first([10, 20]) == 10
"""
    res = verifier.verify_patch(
        original_code=orig_code,
        patched_code=patched_code,
        adversarial_test_code=adv_test,
        baseline_test_code=baseline_test,
        source_filename="service.py",
        pr_id="PR-999",
    )
    assert res.verified is True
    assert res.adversarial_test_passed is True
    assert res.baseline_suite_passed is True
    assert res.permanent_test_path == "tests/regressions/test_linus_pr_PR-999.py"


def test_verify_patch_fails_if_adversarial_not_resolved(verifier):
    orig_code = "def divide(a, b): return a / b"
    # Incomplete patch: still divides by zero
    bad_patch = "def divide(a, b): return a / b # no check"
    adv_test = """from service import divide
def test_zero():
    assert divide(10, 0) == 0
"""
    res = verifier.verify_patch(
        original_code=orig_code,
        patched_code=bad_patch,
        adversarial_test_code=adv_test,
        source_filename="service.py",
        pr_id="PR-001",
    )
    assert res.verified is False
    assert res.adversarial_test_passed is False
    assert "Patch failed to resolve the defect" in res.details


def test_verify_patch_fails_if_baseline_regresses(verifier):
    orig_code = """def process(val):
    return val * 2
"""
    # Bad patch: always returns 0, which breaks baseline tests
    regressive_patch = """def process(val):
    if val is None:
        return 0
    return 0  # Bug introduced!
"""
    adv_test = """from service import process
def test_none():
    assert process(None) == 0
"""
    baseline_test = """from service import process
def test_positive():
    assert process(5) == 10  # This will fail on regressive patch
"""
    res = verifier.verify_patch(
        original_code=orig_code,
        patched_code=regressive_patch,
        adversarial_test_code=adv_test,
        baseline_test_code=baseline_test,
        source_filename="service.py",
        pr_id="PR-REGRESS",
    )
    assert res.verified is False
    assert res.adversarial_test_passed is True
    assert res.baseline_suite_passed is False
    assert "Patch introduced a regression" in res.details


def test_verify_patch_without_baseline_suite(verifier):
    orig = "def get_first(items): return items[0]"
    patch = "def get_first(items): return items[0] if items else None"
    adv = """from service import get_first
def test_empty():
    assert get_first([]) is None
"""
    res = verifier.verify_patch(
        original_code=orig,
        patched_code=patch,
        adversarial_test_code=adv,
        baseline_test_code=None,
        source_filename="service.py",
        pr_id="PR-NO-BASE",
    )
    assert res.verified is True
    assert res.adversarial_test_passed is True
    assert res.baseline_suite_passed is True
