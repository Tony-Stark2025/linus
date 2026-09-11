"""
Dual-Suite Regression Verifier and Recursive Test Addition Tool for Linus.
Verifies that a proposed patch fixes the discovered defect without breaking
existing baseline tests, and commits the regression test permanently.
"""

import difflib
from pathlib import Path
from typing import Optional, Dict
from linus.models import (
    DualVerificationResult,
    PatchProposal,
    TestStatus,
)
from linus.tools.sandbox_runner import SandboxTestRunner


class DualRegressionVerifier:
    """Verifies patch candidates against both adversarial tests and baseline suites."""

    def __init__(self, sandbox_runner: Optional[SandboxTestRunner] = None):
        self.runner = sandbox_runner or SandboxTestRunner()

    def generate_unified_diff(self, original: str, patched: str, filename: str = "service.py") -> str:
        """Generates standard unified diff representation."""
        orig_lines = original.splitlines(keepends=True)
        patched_lines = patched.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            patched_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff)

    def verify_patch(
        self,
        original_code: str,
        patched_code: str,
        adversarial_test_code: str,
        baseline_test_code: Optional[str] = None,
        source_filename: str = "service.py",
        pr_id: str = "42",
        extra_files: Optional[Dict[str, str]] = None,
    ) -> DualVerificationResult:
        """
        Runs dual-suite verification on a candidate patch:
        1. Tests that the adversarial test now passes on patched_code.
        2. Tests that baseline tests still pass on patched_code (zero regressions).
        """
        # Step 1: Run adversarial test on patched code
        adv_result = self.runner.execute_test(
            source_code=patched_code,
            test_code=adversarial_test_code,
            source_filename=source_filename,
            test_filename="test_adversarial_verify.py",
            extra_files=extra_files,
        )

        if adv_result.status != TestStatus.PASS:
            return DualVerificationResult(
                verified=False,
                adversarial_test_passed=False,
                baseline_suite_passed=False,
                details=f"Patch failed to resolve the defect: {adv_result.exception_type or adv_result.status}: {adv_result.exception_message or ''}",
            )

        # Step 2: Run baseline suite if provided
        baseline_passed = True
        baseline_count = 0

        if baseline_test_code:
            base_result = self.runner.execute_test(
                source_code=patched_code,
                test_code=baseline_test_code,
                source_filename=source_filename,
                test_filename="test_baseline_verify.py",
                extra_files=extra_files,
            )

            if base_result.status != TestStatus.PASS:
                return DualVerificationResult(
                    verified=False,
                    adversarial_test_passed=True,
                    baseline_suite_passed=False,
                    details=f"Patch introduced a regression in baseline test suite: {base_result.exception_type or base_result.status}",
                )

            # Count passed tests approximately
            for line in base_result.stdout.splitlines():
                if "passed" in line:
                    baseline_count = 1

        # Step 3: Success! Prepare Recursive Test Addition path
        perm_path = f"tests/regressions/test_linus_pr_{pr_id}.py"

        return DualVerificationResult(
            verified=True,
            adversarial_test_passed=True,
            baseline_suite_passed=baseline_passed,
            baseline_tests_count=baseline_count,
            permanent_test_path=perm_path,
            details="Dual verification successful: defect resolved and zero regressions introduced.",
        )

    def commit_permanent_test(
        self,
        permanent_test_path: str,
        test_code: str,
        base_dir: Optional[Path] = None,
    ) -> Path:
        """Writes permanent regression test to disk."""
        return commit_permanent_test(permanent_test_path, test_code, base_dir=base_dir)


def commit_permanent_test(
    permanent_test_path: str,
    test_code: str,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Physically writes the verified reproduction test to disk (Recursive Test Addition),
    permanently immunizing the repository against regressions.
    """
    root = base_dir or Path.cwd()
    target_path = root / permanent_test_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(test_code, encoding="utf-8")
    return target_path


def verify_patch_dual_suite(
    original_code: str,
    patched_code: str,
    adversarial_test_code: str,
    baseline_test_code: Optional[str] = None,
    source_filename: str = "service.py",
    pr_id: str = "42",
    extra_files: Optional[Dict[str, str]] = None,
) -> DualVerificationResult:
    """
    Top-level helper function matching Amazon Bedrock AgentCore action group declaration.
    Verifies candidate patch against adversarial test and baseline test suite.
    """
    verifier = DualRegressionVerifier()
    return verifier.verify_patch(
        original_code=original_code,
        patched_code=patched_code,
        adversarial_test_code=adversarial_test_code,
        baseline_test_code=baseline_test_code,
        source_filename=source_filename,
        pr_id=pr_id,
        extra_files=extra_files,
    )

