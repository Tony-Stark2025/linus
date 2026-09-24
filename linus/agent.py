"""
Linus: Autonomous Adversarial PR Verifier Agent.
Native integration with the official Strands Agents SDK (strands-agents >= 1.55.0).
Coordinates AST inspection, adversarial hypothesis formulation, isolated sandbox testing,
dual regression verification, and recursive test addition.
"""

import os
import re
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
from linus.tools.boundary_synthesizer import BoundarySynthesizer


# =====================================================================
# Official Strands Agent SDK Tools (@tool)
# =====================================================================

@tool
def inspect_code_ast(source_code: str, file_path: str = "service.py") -> str:
    """
    Deterministically parses Python source code AST and returns function signatures
    and structural risk vectors (empty collections, unchecked None, zero division).
    """
    result = inspect_source_ast(source_code, file_path=file_path)
    return result.model_dump_json()


@tool
def execute_sandbox_test(
    source_code: str,
    test_code: str,
    source_filename: str = "service.py",
    test_filename: str = "test_adversarial.py",
) -> str:
    """
    Executes an adversarial or regression test against source code in an isolated
    pytest subprocess sandbox with timeout and resource guards.
    """
    runner = SandboxTestRunner()
    result = runner.execute_test(
        source_code=source_code,
        test_code=test_code,
        source_filename=source_filename,
        test_filename=test_filename,
    )
    return result.model_dump_json()


@tool
def synthesize_defensive_patch_tool(
    source_code: str,
    file_path: str = "service.py",
    exception_type: str = "Exception",
    exception_line: int = 1,
) -> str:
    """
    Autonomously synthesizes a defensive AST patch guarding against a proven boundary crash.
    """
    ast_summary = inspect_source_ast(source_code, file_path=file_path)
    synthesizer = BoundarySynthesizer()
    failing_stub = TestExecutionResult(
        status=TestStatus.UNCAUGHT_EXCEPTION,
        exit_code=1,
        test_code="",
        exception_type=exception_type,
        exception_line=exception_line,
    )
    patched_code, explanation = synthesizer.synthesize_defensive_patch(
        source_code=source_code,
        ast_summary=ast_summary,
        failing_test=failing_stub,
    )
    return json.dumps({"patched_code": patched_code, "explanation": explanation})


@tool
def verify_patch_and_immunize(
    original_code: str,
    patched_code: str,
    adversarial_test_code: str,
    baseline_test_code: str = "",
    source_filename: str = "service.py",
    pr_id: str = "PR-001",
) -> str:
    """
    Dual-suite regression verifier that tests a defensive patch against both the adversarial
    reproduction test and existing baseline developer tests, generating permanent test paths.
    """
    verifier = DualRegressionVerifier()
    result = verifier.verify_patch(
        original_code=original_code,
        patched_code=patched_code,
        adversarial_test_code=adversarial_test_code,
        baseline_test_code=baseline_test_code if baseline_test_code else None,
        source_filename=source_filename,
        pr_id=pr_id,
    )
    return result.model_dump_json()


# =====================================================================
# Linus Agent Core Harness
# =====================================================================

class LinusAgent:
    """
    Linus Autonomous Verification Engine.
    Powered by Strands Agents SDK and Amazon Bedrock AgentCore.
    """

    def __init__(
        self,
        sandbox_runner: Optional[SandboxTestRunner] = None,
        dual_verifier: Optional[DualRegressionVerifier] = None,
        boundary_synthesizer: Optional[BoundarySynthesizer] = None,
        telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        use_bedrock_llm: Optional[bool] = None,
    ):
        self.sandbox = sandbox_runner or SandboxTestRunner()
        self.verifier = dual_verifier or DualRegressionVerifier(self.sandbox)
        self.synthesizer = boundary_synthesizer or BoundarySynthesizer()
        self.telemetry_callback = telemetry_callback
        self.telemetry_history: List[Dict[str, Any]] = []
        self.use_bedrock_llm = (
            use_bedrock_llm
            if use_bedrock_llm is not None
            else (os.environ.get("LINUS_ENABLE_BEDROCK_LLM") == "1")
        )

        # Initialize official Strands Agent with registered @tool functions
        self.strands_agent = Agent(
            name="LinusAdversarialVerifier",
            tools=[
                inspect_code_ast,
                execute_sandbox_test,
                synthesize_defensive_patch_tool,
                verify_patch_and_immunize,
            ],
            system_prompt=(
                "You are Linus, an autonomous adversarial PR verifier. "
                "Your mission is to formulate boundary hypotheses against AST-identified "
                "risk vectors, execute them in an isolated sandbox, and only surface if an "
                "unhandled runtime crash is empirically proven with zero false positives."
            ),
        )

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

    def _invoke_strands_llm_code(self, prompt: str) -> Optional[str]:
        """
        Invokes the underlying Strands Agent (`self.strands_agent(prompt)`) when Bedrock LLM
        execution is enabled and extracts a fenced Python code block from the response.
        Gracefully returns None if offline or if credentials are not configured.
        """
        if not self.use_bedrock_llm:
            return None
        try:
            self._emit("STRANDS_LLM_REASONING", "Invoking Strands Agent loop with Amazon Bedrock foundation model...")
            response = self.strands_agent(prompt)
            resp_text = str(response)
            code_match = re.search(r"```(?:python)?\s*\n(.*?)```", resp_text, re.DOTALL)
            if code_match:
                return code_match.group(1).strip() + "\n"
            return None
        except Exception as exc:
            self._emit(
                "STRANDS_LLM_FALLBACK",
                f"Bedrock LLM unavailable ({type(exc).__name__}); using deterministic AST synthesizer.",
            )
            return None

    def audit_pull_request(
        self,
        pr_id: str,
        repository: str,
        source_code: str,
        target_filename: str = "service.py",
        adversarial_test_code: Optional[str] = None,
        baseline_test_code: Optional[str] = None,
        candidate_patch: Optional[str] = None,
        patch_explanation: Optional[str] = None,
    ) -> LinusAuditResult:
        """
        Executes an autonomous adversarial verification cycle:
        1. Ingress & AST inspection (via Strands inspect_code_ast tool)
        2. Boundary Hypothesis Formulation / Synthesis (via Strands LLM or deterministic BoundarySynthesizer)
        3. Sandbox Adversarial Execution (via Strands execute_sandbox_test tool)
        4. Assured Execution Gate
        5. Autonomous Patch Synthesis & Dual-Suite Verification (via Strands synthesize_defensive_patch_tool & verify_patch_and_immunize)
        6. Recursive Test Addition
        """
        start_time = time.time()
        self.telemetry_history.clear()

        self._emit("INGRESS", f"Received PR {pr_id} on {repository}. Initiating autonomous audit.", {
            "pr_id": pr_id,
            "repository": repository,
            "target_file": target_filename,
            "strands_tools": self.strands_agent.tool_names,
        })

        # Step 1: AST Inspection via Strands inspect_code_ast tool
        self._emit("AST_ANALYSIS", "Deterministically inspecting source code AST and risk vectors via Strands SDK...")
        ast_tool_res = self.strands_agent.tool.inspect_code_ast(
            source_code=source_code,
            file_path=target_filename,
        )
        
        if ast_tool_res.get("status") == "success":
            ast_data = json.loads(ast_tool_res["content"][0]["text"])
            ast_result = ASTAnalysisResult.model_validate(ast_data)
        else:
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

        # Step 2: Boundary Hypothesis Formulation
        actual_test_code = adversarial_test_code
        if not actual_test_code:
            self._emit("HYPOTHESIS_SYNTHESIS", "No pre-scripted test provided. Autonomous boundary synthesizer formulating adversarial test...")
            llm_test = self._invoke_strands_llm_code(
                f"Synthesize a minimal pytest boundary test for module `{target_filename}` against these AST risks: {flagged_risks}.\n"
                f"Source code:\n```python\n{source_code}\n```"
            )
            if llm_test:
                actual_test_code = llm_test
                hypothesis = f"Strands LLM synthesized adversarial boundary suite for {target_filename}."
            else:
                actual_test_code, hypothesis = self.synthesizer.synthesize_boundary_test(
                    ast_summary=ast_result,
                    source_filename=target_filename,
                )
            self._emit("HYPOTHESIS_FORMULATED", f"Synthesized boundary hypothesis: {hypothesis}")

        # Step 3: Adversarial Sandbox Execution via Strands execute_sandbox_test tool
        self._emit("SANDBOX_TEST", "Deploying candidate adversarial test to isolated sandbox via Strands SDK...", {
            "test_file": "test_adversarial_linus.py",
        })

        test_tool_res = self.strands_agent.tool.execute_sandbox_test(
            source_code=source_code,
            test_code=actual_test_code,
            source_filename=target_filename,
            test_filename="test_adversarial_linus.py",
        )

        if test_tool_res.get("status") == "success":
            test_data = json.loads(test_tool_res["content"][0]["text"])
            test_result = TestExecutionResult.model_validate(test_data)
        else:
            test_result = self.sandbox.execute_test(
                source_code=source_code,
                test_code=actual_test_code,
                source_filename=target_filename,
                test_filename="test_adversarial_linus.py",
            )

        # Step 4: Assured Execution Gate
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
            self._emit("TEST_PASSED", "Adversarial test passed. Code successfully handled boundary input with zero exceptions.")
            self._emit("AMBIENT_SILENCE", "Zero defects proven. Linus shuts down cleanly without generating PR noise.")
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

        # Step 5: Autonomous Patch Synthesis & Dual-Suite Verification
        patch_proposal = None
        dual_result = None

        if not candidate_patch:
            # Autonomously synthesize a defensive patch via Strands LLM or deterministic AST guard synthesizer
            llm_patch = self._invoke_strands_llm_code(
                f"Synthesize a minimal defensive Python patch for `{target_filename}` to fix `{test_result.exception_type}` "
                f"at line {test_result.exception_line} without breaking existing functionality.\n"
                f"Source code:\n```python\n{source_code}\n```"
            )
            if llm_patch:
                candidate_patch = llm_patch
                patch_explanation = patch_explanation or f"Strands LLM defensive patch for {test_result.exception_type}"
            else:
                synth_res = self.strands_agent.tool.synthesize_defensive_patch_tool(
                    source_code=source_code,
                    file_path=target_filename,
                    exception_type=test_result.exception_type or "Exception",
                    exception_line=test_result.exception_line or 1,
                )
                if synth_res.get("status") == "success":
                    synth_data = json.loads(synth_res["content"][0]["text"])
                    candidate_patch = synth_data.get("patched_code")
                    patch_explanation = patch_explanation or synth_data.get("explanation")
                else:
                    candidate_patch, auto_expl = self.synthesizer.synthesize_defensive_patch(
                        source_code=source_code,
                        ast_summary=ast_result,
                        failing_test=test_result,
                    )
                    patch_explanation = patch_explanation or auto_expl

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
            
            verify_tool_res = self.strands_agent.tool.verify_patch_and_immunize(
                original_code=source_code,
                patched_code=candidate_patch,
                adversarial_test_code=actual_test_code,
                baseline_test_code=baseline_test_code or "",
                source_filename=target_filename,
                pr_id=pr_id,
            )

            if verify_tool_res.get("status") == "success":
                v_data = json.loads(verify_tool_res["content"][0]["text"])
                dual_result = DualVerificationResult.model_validate(v_data)
            else:
                dual_result = self.verifier.verify_patch(
                    original_code=source_code,
                    patched_code=candidate_patch,
                    adversarial_test_code=actual_test_code,
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
