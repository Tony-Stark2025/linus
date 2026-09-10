"""
Comprehensive Tests for SandboxTestRunner.
Verifies subprocess isolation, timeout guards, exit codes, and exception tracebacks across various error conditions.
"""

import pytest
from linus.tools.sandbox_runner import SandboxTestRunner
from linus.models import TestStatus


@pytest.fixture
def runner():
    return SandboxTestRunner(default_timeout_seconds=5)


# ---------------------------------------------------------------------------
# 1. Successful Pass Tests
# ---------------------------------------------------------------------------

def test_sandbox_executes_passing_test(runner):
    source = "def add(a, b): return a + b"
    test = """from service import add
def test_add_success():
    assert add(2, 3) == 5
"""
    res = runner.execute_test(source, test)
    assert res.status == TestStatus.PASS
    assert res.exit_code == 0
    assert res.exception_type is None
    assert res.duration_ms > 0


# ---------------------------------------------------------------------------
# 2. Exception Classification & Stack Trace Extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_fn, call_args, expected_exc", [
    ("def bad_index(): return [][0]", "bad_index()", "IndexError"),
    ("def div_zero(): return 1 / 0", "div_zero()", "ZeroDivisionError"),
    ("def null_sub(): return None['key']", "null_sub()", "TypeError"),
    ("def missing_key(): return {}['missing']", "missing_key()", "KeyError"),
    ("def bad_val(): return int('not_a_number')", "bad_val()", "ValueError"),
    ("def no_attr(): return (123).non_existent_method()", "no_attr()", "AttributeError"),
    ("def custom_raise(): raise RuntimeError('system failure')", "custom_raise()", "RuntimeError"),
])
def test_sandbox_captures_specific_runtime_exceptions(runner, source_fn, call_args, expected_exc):
    source = f"{source_fn}\n"
    test = f"""from service import *
def test_trigger_crash():
    {call_args}
"""
    res = runner.execute_test(source, test)
    assert res.status == TestStatus.UNCAUGHT_EXCEPTION
    assert res.exit_code != 0
    assert res.exception_type == expected_exc
    assert res.stack_trace != ""
    assert res.exception_line is not None


# ---------------------------------------------------------------------------
# 3. Assertion Failures vs. Uncaught Exceptions
# ---------------------------------------------------------------------------

def test_sandbox_captures_assertion_failure(runner):
    source = "def multiply(a, b): return a * b"
    test = """from service import multiply
def test_multiply_fail():
    assert multiply(2, 3) == 100  # Will fail assertion
"""
    res = runner.execute_test(source, test)
    assert res.status == TestStatus.FAIL_ASSERTION
    assert res.exit_code != 0


# ---------------------------------------------------------------------------
# 4. Syntax Errors in Source or Test
# ---------------------------------------------------------------------------

def test_sandbox_handles_syntax_error_in_source(runner):
    source = "def broken_syntax( pass"
    test = """from service import *
def test_smoke(): assert True"""
    res = runner.execute_test(source, test)
    assert res.exit_code != 0
    assert res.status in (TestStatus.SYNTAX_ERROR, TestStatus.ERROR)


def test_sandbox_handles_syntax_error_in_test(runner):
    source = "def valid(): return 1"
    test = "def test_invalid_syntax(:"
    res = runner.execute_test(source, test)
    assert res.exit_code != 0
    assert res.status in (TestStatus.SYNTAX_ERROR, TestStatus.ERROR)


# ---------------------------------------------------------------------------
# 5. Timeout & Infinite Loop Handling
# ---------------------------------------------------------------------------

def test_sandbox_enforces_timeout_on_infinite_loop(runner):
    source = """def loop_forever():
    while True:
        pass
"""
    test = """from service import loop_forever
def test_hang():
    loop_forever()
"""
    # Strict 1-second timeout
    res = runner.execute_test(source, test, timeout_seconds=1)
    assert res.status == TestStatus.TIMEOUT
    assert res.exit_code != 0
    assert ("Process killed" in (res.exception_message or "")) or ("Timed out" in (res.exception_message or ""))


# ---------------------------------------------------------------------------
# 6. Auxiliary Extra Files & Imports
# ---------------------------------------------------------------------------

def test_sandbox_supports_auxiliary_files(runner):
    source = """from utils.helper import format_currency
def get_display_price(amount):
    return format_currency(amount)
"""
    extra_files = {
        "utils/helper.py": "def format_currency(val): return f'${val:.2f}'"
    }
    test = """from service import get_display_price
def test_helper_import():
    assert get_display_price(19.5) == '$19.50'
"""
    res = runner.execute_test(source, test, extra_files=extra_files)
    assert res.status == TestStatus.PASS
    assert res.exit_code == 0
