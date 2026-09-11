"""
Isolated Sandbox Test Execution Tool for Linus.
Runs synthesized test suites in an isolated temporary directory with timeout guards,
capturing output, exit codes, and runtime tracebacks.
"""

import os
import sys
import time
import re
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict
from linus.models import TestExecutionResult, TestStatus


class SandboxTestRunner:
    """Executes code and tests inside an isolated subprocess sandbox."""

    def __init__(self, default_timeout_seconds: int = 15):
        self.default_timeout_seconds = default_timeout_seconds

    def execute_test(
        self,
        source_code: str,
        test_code: str,
        source_filename: str = "service.py",
        test_filename: str = "test_adversarial.py",
        timeout_seconds: Optional[int] = None,
        extra_files: Optional[Dict[str, str]] = None,
    ) -> TestExecutionResult:
        """
        Executes test_code against source_code in an isolated temporary environment.
        """
        timeout = timeout_seconds or self.default_timeout_seconds
        start_time = time.time()

        with tempfile.TemporaryDirectory(prefix="linus_sandbox_") as tmpdir:
            sandbox_path = Path(tmpdir)

            # Write source code
            source_file = sandbox_path / source_filename
            source_file.write_text(source_code, encoding="utf-8")

            # Write extra auxiliary files if any
            if extra_files:
                for fname, fcontent in extra_files.items():
                    extra_path = sandbox_path / fname
                    extra_path.parent.mkdir(parents=True, exist_ok=True)
                    extra_path.write_text(fcontent, encoding="utf-8")

            # Write test code
            test_file = sandbox_path / test_filename
            test_file.write_text(test_code, encoding="utf-8")

            # Build execution command using pytest
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "-s",
                "-v",
                "--tb=short",
                str(test_file.name),
            ]

            # Build a sanitized execution environment (strip sensitive host credentials)
            env = {
                k: v for k, v in os.environ.items()
                if not any(
                    s in k.upper()
                    for s in (
                        "AWS_", "GITHUB_", "SECRET", "PASSWORD", "TOKEN",
                        "API_KEY", "PRIVATE_KEY", "CREDENTIALS", "ACCESS_KEY"
                    )
                )
            }
            env["PYTHONPATH"] = str(sandbox_path)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(sandbox_path),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                duration_ms = (time.time() - start_time) * 1000.0
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode

                # Parse status & traceback
                status, exc_type, exc_msg, exc_line, stack_trace = self._parse_pytest_output(
                    exit_code, stdout, stderr
                )

                return TestExecutionResult(
                    status=status,
                    exit_code=exit_code,
                    test_code=test_code,
                    stdout=stdout,
                    stderr=stderr,
                    exception_type=exc_type,
                    exception_message=exc_msg,
                    exception_line=exc_line,
                    stack_trace=stack_trace,
                    duration_ms=round(duration_ms, 2),
                )

            except subprocess.TimeoutExpired as e:
                duration_ms = (time.time() - start_time) * 1000.0
                return TestExecutionResult(
                    status=TestStatus.TIMEOUT,
                    exit_code=124,
                    test_code=test_code,
                    stdout=e.stdout or "",
                    stderr=e.stderr or f"Execution timed out after {timeout} seconds.",
                    exception_type="TimeoutExpired",
                    exception_message=f"Process killed after {timeout}s",
                    stack_trace="",
                    duration_ms=round(duration_ms, 2),
                )
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000.0
                return TestExecutionResult(
                    status=TestStatus.ERROR,
                    exit_code=1,
                    test_code=test_code,
                    stdout="",
                    stderr=str(e),
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    stack_trace="",
                    duration_ms=round(duration_ms, 2),
                )

    def _parse_pytest_output(self, exit_code: int, stdout: str, stderr: str):
        """Extracts exception type, line, and classification from pytest output."""
        combined = f"{stdout}\n{stderr}"

        if exit_code == 0:
            return TestStatus.PASS, None, None, None, ""

        # Check for syntax or import errors in test code
        if "SyntaxError" in combined or "IndentationError" in combined:
            return TestStatus.SYNTAX_ERROR, "SyntaxError", "Syntax or Indentation Error in test", None, combined
        if "ModuleNotFoundError" in combined or "ImportError" in combined:
            return TestStatus.SYNTAX_ERROR, "ImportError", "Failed to import required symbols", None, combined

        # Look for uncaught runtime exceptions (e.g. E   ZeroDivisionError: division by zero)
        exception_match = re.search(r"E\s+([A-Za-z0-9_]+Error|AssertionError|Exception):\s*(.*)", combined)
        line_match = re.search(r":(\d+):\s+in\s+", combined)

        exc_type = None
        exc_msg = None
        exc_line = None

        if exception_match:
            exc_type = exception_match.group(1).strip()
            exc_msg = exception_match.group(2).strip()

        if line_match:
            try:
                exc_line = int(line_match.group(1))
            except ValueError:
                pass

        if "E   assert" in combined or "AssertionError" in combined:
            exc_type = "AssertionError"
            exc_msg = "Assertion failed"
            status = TestStatus.FAIL_ASSERTION
        elif exc_type:
            status = TestStatus.UNCAUGHT_EXCEPTION
        else:
            status = TestStatus.UNCAUGHT_EXCEPTION if exit_code != 0 else TestStatus.PASS

        # Extract cleaner stack trace snippet
        tb_lines = []
        capture = False
        for line in combined.splitlines():
            if "___" in line or "FAILURES" in line or "ERRORS" in line:
                capture = True
            if capture:
                tb_lines.append(line)
            if "short test summary info" in line:
                break
        
        stack_trace = "\n".join(tb_lines) if tb_lines else combined

        return status, exc_type, exc_msg, exc_line, stack_trace


def run_test_in_sandbox(
    source_code: str,
    test_code: str,
    source_filename: str = "service.py",
    test_filename: str = "test_adversarial.py",
    timeout_seconds: Optional[int] = None,
    extra_files: Optional[Dict[str, str]] = None,
) -> TestExecutionResult:
    """
    Top-level helper function matching Amazon Bedrock AgentCore action group declaration.
    Executes test_code against source_code in an isolated temporary sandbox.
    """
    runner = SandboxTestRunner(default_timeout_seconds=timeout_seconds or 15)
    return runner.execute_test(
        source_code=source_code,
        test_code=test_code,
        source_filename=source_filename,
        test_filename=test_filename,
        timeout_seconds=timeout_seconds,
        extra_files=extra_files,
    )

