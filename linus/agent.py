"""
Linus: Autonomous Adversarial PR Verifier Agent.
Coordinates AST inspection, adversarial hypothesis formulation, isolated sandbox testing,
dual regression verification, and recursive test addition using Strands Agents SDK.
"""

import time
import json
from typing import Dict, Any, List, Optional, Callable
from strands import Agent, tool
from linus.models import (
    ASTAnalysisResult,
    TestExecutionResult,
    TestStatus,
    PatchProposal,
    DualVerificationResult,
    LinusAuditResult,
)
from linus.tools.ast_inspector import inspect_source_ast
from linus.tools.sandbox_runner import SandboxTestRunner
from linus.tools.patch_verifier import DualRegressionVerifier


class LinusAgent:
    """
    Linus Autonomous Verification Engine.
    Executes an empirical adversarial audit on a Pull Request or code diff.
    """

    def __init__(
        self,
        sandbox_runner: Optional[SandboxTestRunner] = None,
        dual_verifier: Optional[DualRegressionVerifier] = None,
        telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.sandbox = sandbox_runner or SandboxTestRunner()
        self.verifier = dual_verifier or DualRegressionVerifier(self.sandbox)
        self.telemetry_callback = telemetry_callback
        self.telemetry_history: List[Dict[str, Any]] = []

    def _emit(self, phase: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Emits structured telemetry for real-time observability."""
        event = {
            "timestamp": time.strftime("%H:%M:%S"),
            "phase": phase,
            "message": message,
            "data": data or {},
        }
        self.telemetry_history.append(event)
        if self.telemetry_callback:
            try:
                self.telemetry_callback(event)
            except Exception:
                pass

    def audit_pull_request(
        self,
        pr_id: str,
        repository: str,
        source_code: str,
        target_filename: str,
        adversarial_test_code: str,
        baseline_test_code: Optional[str] = None,
        candidate_patch: Optional[str] = None,
        patch_explanation: Optional[str] = None,
    ) -> LinusAuditResult:
        """
        Executes an autonomous adversarial verification cycle:
        1. Ingress & AST inspection
        2. Sandbox Adversarial Execution (Proof of Defect)
        3. Assured Execution Gate
        4. Patch Synthesis & Dual-Suite Verification
        5. Recursive Test Addition
        """
        start_time = time.time()
        self.telemetry_history.clear()

        self._emit("INGRESS", f"Received PR {pr_id} on {repository}. Initiating autonomous audit.", {
            "pr_id": pr_id,
            "repository": repository,
            "target_file": target_filename,
        })

        # Step 1: AST & Structural Risk Vector Inspection
        self._emit("AST_ANALYSIS", "Deterministically inspecting source code AST and risk vectors...")
        ast_result = inspect_source_ast(source_code, file_path=target_filename)
        
        flagged_risks = []
        for fn in ast_result.functions:
            for rv in fn.risk_vectors:
                flagged_risks.append(f"{fn.name}: {rv.value}")

        self._emit(
            "AST_COMPLETE",
            f"Parsed {len(ast_result.functions)} function(s). Identified {len(flagged_risks)} structural risk indicator(s).",
            {"functions": [f.name for f in ast_result.functions], "risk_vectors": flagged_risks},
        )

        # Step 2: Adversarial Sandbox Execution
        self._emit("SANDBOX_TEST", "Deploying candidate adversarial test to isolated sandbox...", {
            "test_file": "test_adversarial_linus.py",
        })

        test_result = self.sandbox.execute_test(
            source_code=source_code,
            test_code=adversarial_test_code,
            source_filename=target_filename,
            test_filename="test_adversarial_linus.py",
        )

        # Step 3: Assured Execution Gate
        if test_result.status == TestStatus.UNCAUGHT_EXCEPTION:
            self._emit(
                "CRASH_PROVEN",
                f"EMPIRICAL DEFECT PROVEN! Uncaught {test_result.exception_type} on line {test_result.exception_line or 'unknown'}.",
                {
                    "exception_type": test_result.exception_type,
                    "exception_message": test_result.exception_message,
                    "duration_ms": test_result.duration_ms,
                    "traceback": test_result.stack_trace,
                },
            )
        elif test_result.status == TestStatus.PASS:
            self._emit("TEST_PASSED", "Adversarial test passed. Code successfully handled boundary input.")
            return LinusAuditResult(
                pr_id=pr_id,
                repository=repository,
                status="VERIFIED_CLEAN",
                defect_proven=False,
                ast_summary=ast_result,
                failing_test=test_result,
                telemetry_trace=self.telemetry_history,
                execution_time_seconds=round(time.time() - start_time, 2),
            )
        else:
            self._emit("TEST_INVALID", f"Test yielded non-crash status: {test_result.status.value}")
            return LinusAuditResult(
                pr_id=pr_id,
                repository=repository,
                status="INCONCLUSIVE",
                defect_proven=False,
                ast_summary=ast_result,
                failing_test=test_result,
                telemetry_trace=self.telemetry_history,
                execution_time_seconds=round(time.time() - start_time, 2),
            )

        # Step 4: Patch Synthesis & Dual-Suite Verification
        patch_proposal = None
        dual_result = None

        if candidate_patch:
            self._emit("PATCH_SYNTHESIS", "Synthesizing minimal AST patch and unified diff...", {
                "explanation": patch_explanation or "Guard against boundary condition",
            })
            
            diff_text = self.verifier.generate_unified_diff(source_code, candidate_patch, filename=target_filename)
            patch_proposal = PatchProposal(
                file_path=target_filename,
                original_code=source_code,
                patched_code=candidate_patch,
                diff_patch=diff_text,
                explanation=patch_explanation or "Automated defensive patch",
            )

            self._emit("DUAL_VERIFICATION", "Running dual-suite verification in sandbox: testing fix against both adversarial test and baseline tests...")
            dual_result = self.verifier.verify_patch(
                original_code=source_code,
                patched_code=candidate_patch,
                adversarial_test_code=adversarial_test_code,
                baseline_test_code=baseline_test_code,
                source_filename=target_filename,
                pr_id=pr_id,
            )

            if dual_result.verified:
                self._emit("VERIFICATION_SUCCESS", "Dual verification PASSED! Zero regressions introduced.", {
                    "permanent_test_path": dual_result.permanent_test_path,
                })
                self._emit("RECURSIVE_TEST_COMMITTED", f"Recursive test added to permanent test suite: {dual_result.permanent_test_path}")
            else:
                self._emit("VERIFICATION_FAILED", f"Dual verification failed: {dual_result.details}")

        elapsed = round(time.time() - start_time, 2)
        self._emit("AUDIT_COMPLETE", f"Linus audit complete in {elapsed}s. Surfacing actionable report to PR.")

        return LinusAuditResult(
            pr_id=pr_id,
            repository=repository,
            status="VERIFIED_DEFECT",
            defect_proven=True,
            ast_summary=ast_result,
            failing_test=test_result,
            patch=patch_proposal,
            dual_verification=dual_result,
            telemetry_trace=self.telemetry_history,
            execution_time_seconds=elapsed,
        )
