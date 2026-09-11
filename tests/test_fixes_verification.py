"""
Unit and Integration Tests for Fixed Issues in Linus.
Verifies tool aliases, environment sanitization, permanent test disk persistence, and cache eviction.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from linus.tools.ast_inspector import inspect_ast_risks, inspect_source_ast
from linus.tools.sandbox_runner import run_test_in_sandbox, SandboxTestRunner
from linus.tools.patch_verifier import verify_patch_dual_suite, commit_permanent_test, DualRegressionVerifier
from linus.models import RiskVectorType, TestStatus
from web_demo.server import app, evict_old_cache, AUDIT_RESULTS, MAX_CACHED_AUDITS

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Tool Compatibility Shims
# ---------------------------------------------------------------------------

def test_inspect_ast_risks_shim_matches_inspect_source_ast():
    code = "def get_first(items): return items[0]"
    res1 = inspect_ast_risks(code, "test.py")
    res2 = inspect_source_ast(code, "test.py")
    assert res1.functions[0].name == res2.functions[0].name
    assert RiskVectorType.EMPTY_COLLECTION_INDEXING in res1.functions[0].risk_vectors


def test_run_test_in_sandbox_top_level_function():
    source = "def add(a, b): return a + b"
    test = """from service import add
def test_ok():
    assert add(1, 2) == 3
"""
    res = run_test_in_sandbox(source, test)
    assert res.status == TestStatus.PASS
    assert res.exit_code == 0


def test_verify_patch_dual_suite_top_level_function():
    orig = "def val(x): return x[0]"
    patched = "def val(x): return x[0] if x else None"
    adv_test = """from service import val
def test_adv():
    assert val([]) is None
"""
    base_test = """from service import val
def test_base():
    assert val([42]) == 42
"""
    res = verify_patch_dual_suite(
        original_code=orig,
        patched_code=patched,
        adversarial_test_code=adv_test,
        baseline_test_code=base_test,
        pr_id="999",
    )
    assert res.verified is True
    assert res.adversarial_test_passed is True
    assert res.baseline_suite_passed is True
    assert "test_linus_pr_999.py" in res.permanent_test_path


# ---------------------------------------------------------------------------
# 2. Subprocess Environment Sanitization
# ---------------------------------------------------------------------------

def test_sandbox_runner_sanitizes_sensitive_env_vars(monkeypatch, tmp_path):
    # Set sensitive mock credentials in current process
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "SECRET_AWS_KEY_12345")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SUPER_SECRET_KEY_XYZ")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_mocktoken123456789")
    monkeypatch.setenv("SAFE_CONFIG_VAR", "visible_safe_value")

    # PR test attempting to read host environment variables
    source = "SAFE_VAR = 1"
    test = """import os

def test_env_exfiltration():
    # Sensitive credentials should NOT be in the sandbox environment
    assert "AWS_ACCESS_KEY_ID" not in os.environ, "AWS key leaked to sandbox!"
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ, "AWS secret leaked to sandbox!"
    assert "GITHUB_TOKEN" not in os.environ, "GitHub token leaked to sandbox!"
    assert os.environ.get("SAFE_CONFIG_VAR") == "visible_safe_value"
"""
    runner = SandboxTestRunner()
    res = runner.execute_test(source, test)
    assert res.status == TestStatus.PASS, f"Test failed: {res.stdout}\n{res.stderr}"


# ---------------------------------------------------------------------------
# 3. Permanent Test Disk Persistence
# ---------------------------------------------------------------------------

def test_commit_permanent_test_writes_to_disk(tmp_path):
    rel_path = "tests/regressions/test_linus_pr_test_77.py"
    test_code = "def test_permanent(): assert True\n"
    
    written = commit_permanent_test(rel_path, test_code, base_dir=tmp_path)
    assert written.exists()
    assert written.read_text(encoding="utf-8") == test_code


def test_api_patch_commit_endpoint(tmp_path, monkeypatch):
    # Run an audit first to generate an audit_id
    audit_res = client.post("/api/audit", json={"scenario_id": "PR-104"})
    assert audit_res.status_code == 200
    audit_id = audit_res.json()["audit_id"]

    # Wait for result to populate
    import time
    for _ in range(30):
        res = client.get(f"/api/audit/result/{audit_id}")
        if res.status_code == 200:
            break
        time.sleep(0.2)

    assert res.status_code == 200

    # Call /api/patch/commit
    commit_res = client.post("/api/patch/commit", json={"audit_id": audit_id})
    assert commit_res.status_code == 200
    commit_data = commit_res.json()
    assert commit_data["status"] == "COMMITTED"
    assert "permanent_test_path" in commit_data
    assert Path(commit_data["written_file"]).exists()

    # Clean up created regression test file if created in main repo
    created_file = Path(commit_data["written_file"])
    if created_file.exists() and "tests" in str(created_file):
        created_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 4. Cache Eviction
# ---------------------------------------------------------------------------

def test_cache_eviction_limits_memory_growth():
    # Artificially populate AUDIT_RESULTS beyond limit
    for i in range(MAX_CACHED_AUDITS + 15):
        AUDIT_RESULTS[f"mock_id_{i}"] = {"dummy": i}
    
    evict_old_cache()
    assert len(AUDIT_RESULTS) <= MAX_CACHED_AUDITS
