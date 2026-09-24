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
            sandbox_path = Path(tmpdir).resolve()

            # Validate source_filename and test_filename against path traversal (SEC-03)
            if ".." in Path(source_filename).parts or not (sandbox_path / source_filename).resolve().is_relative_to(sandbox_path):
                raise ValueError(f"Invalid source_filename path traversal attempt: {source_filename}")
            if ".." in Path(test_filename).parts or not (sandbox_path / test_filename).resolve().is_relative_to(sandbox_path):
                raise ValueError(f"Invalid test_filename path traversal attempt: {test_filename}")

            safe_source_name = Path(source_filename).name or "service.py"
            safe_test_name = Path(test_filename).name or "test_adversarial.py"

            source_file = (sandbox_path / safe_source_name).resolve()
            source_file.write_text(source_code, encoding="utf-8")

            # If source_filename includes valid subdirectory structure (e.g., `services/checkout/pricing.py`),
            # also mirror the file under that relative package path so both `from pricing import ...` and
            # `from services.checkout.pricing import ...` succeed.
            nested_source = (sandbox_path / source_filename).resolve()
            if nested_source != source_file and nested_source.is_relative_to(sandbox_path):
                nested_source.parent.mkdir(parents=True, exist_ok=True)
                cur_dir = nested_source.parent
                while cur_dir != sandbox_path and cur_dir.is_relative_to(sandbox_path):
                    init_py = cur_dir / "__init__.py"
                    if not init_py.exists():
                        init_py.write_text("", encoding="utf-8")
                    cur_dir = cur_dir.parent
                nested_source.write_text(source_code, encoding="utf-8")

            # Write extra auxiliary files if any, enforcing strict sandbox root containment
            if extra_files:
                for fname, fcontent in extra_files.items():
                    if ".." in Path(fname).parts:
                        raise ValueError(f"Path traversal detected in extra_files: {fname}")
                    extra_path = (sandbox_path / fname).resolve()
                    if not extra_path.is_relative_to(sandbox_path):
                        raise ValueError(f"Path traversal detected in extra_files: {fname}")
                    extra_path.parent.mkdir(parents=True, exist_ok=True)
                    extra_path.write_text(fcontent, encoding="utf-8")

            # Write sandbox isolation guard (conftest.py) to block network egress / SSRF & /proc environ exfiltration (SEC-01 & SEC-02)
            conftest_guard = sandbox_path / "conftest.py"
            if not conftest_guard.exists():
                conftest_guard.write_text(
                    """# Linus Sandbox Isolation Guard (Network, Filesystem & Resource Lockdown)
import builtins
import io
import socket

_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
_orig_socketpair = getattr(socket, "socketpair", None)

def _blocked_network(*args, **kwargs):
    raise PermissionError("Network egress is prohibited inside the Linus verification sandbox.")

def _safe_socketpair(*args, **kwargs):
    socket.socket.connect = _orig_connect
    socket.socket.connect_ex = _orig_connect_ex
    try:
        return _orig_socketpair(*args, **kwargs)
    finally:
        socket.socket.connect = _blocked_network
        socket.socket.connect_ex = _blocked_network

socket.socket.connect = _blocked_network
socket.socket.connect_ex = _blocked_network
socket.create_connection = _blocked_network
if _orig_socketpair is not None:
    socket.socketpair = _safe_socketpair

_orig_open = builtins.open

def _guarded_open(file, *args, **kwargs):
    path_str = str(file).replace("\\\\", "/")
    if (
        ("/proc/" in path_str and "environ" in path_str)
        or path_str in ("/etc/shadow", "/etc/gshadow")
        or path_str.endswith("/.env")
    ):
        raise PermissionError(f"Access to sensitive host resource '{path_str}' is prohibited inside the Linus sandbox.")
    return _orig_open(file, *args, **kwargs)

builtins.open = _guarded_open
io.open = _guarded_open

try:
    import resource
    # Limit CPU time to 10s, file size writes to 5MB, and address space to 512MB on POSIX hosts
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (5 * 1024 * 1024, 5 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
except Exception:
    pass
""",
                    encoding="utf-8",
                )

            # Write test code
            test_file = (sandbox_path / safe_test_name).resolve()
            test_file.write_text(test_code, encoding="utf-8")

            # Build execution command using pytest (with optional bubblewrap namespace isolation when available)
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "-s",
                "-v",
                "--tb=short",
                str(test_file.name),
            ]
            if os.environ.get("LINUS_USE_BWRAP") == "1":
                import shutil
                bwrap_bin = shutil.which("bwrap")
                if bwrap_bin:
                    cmd = [
                        bwrap_bin,
                        "--unshare-net",
                        "--die-with-parent",
                        "--bind", str(sandbox_path), str(sandbox_path),
                        "--ro-bind", "/", "/",
                        "--dev", "/dev",
                        "--proc", "/proc",
                        "--",
                        *cmd,
                    ]

            # Build a sanitized execution environment (strip sensitive host credentials & cloud metadata URIs)
            env = {
                k: v for k, v in os.environ.items()
                if not any(
                    s in k.upper()
                    for s in (
                        "AWS_", "GITHUB_", "SECRET", "PASSWORD", "TOKEN",
                        "API_KEY", "PRIVATE_KEY", "CREDENTIALS", "ACCESS_KEY",
                        "ECS_CONTAINER_METADATA", "MSI_ENDPOINT", "IDENTITY_HEADER",
                    )
                )
            }
            env["PYTHONPATH"] = str(sandbox_path)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["NO_PROXY"] = "*"
            env["PIP_NO_INDEX"] = "1"

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
                    exit_code, stdout, stderr, source_filename=safe_source_name
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

    def _parse_pytest_output(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        source_filename: str = "service.py",
    ):
        """Extracts exception type, innermost target line, and classification from pytest output."""
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
        frame_matches = re.findall(r"([^\s:]+):(\d+):\s+in\s+", combined)

        exc_type = None
        exc_msg = None
        exc_line = None

        if exception_match:
            exc_type = exception_match.group(1).strip()
            exc_msg = exception_match.group(2).strip()

        if frame_matches:
            target_basename = Path(source_filename).name
            # Prefer the innermost stack frame inside the target PR source file
            target_frames = [
                int(line_str)
                for fname, line_str in frame_matches
                if Path(fname).name == target_basename and line_str.isdigit()
            ]
            if target_frames:
                exc_line = target_frames[-1]
            else:
                try:
                    exc_line = int(frame_matches[-1][1])
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

