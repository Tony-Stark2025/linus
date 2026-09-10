"""
Comprehensive Integration Tests for FastAPI Web Console and Telemetry APIs.
Covers all endpoints, error responses, headers, scenarios, custom code payloads, and GitHub webhooks.
"""

import pytest
from fastapi.testclient import TestClient
from web_demo.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. UI & Static Content Tests
# ---------------------------------------------------------------------------

def test_dashboard_html_structure_and_assets():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    assert "<title>Linus | Autonomous Adversarial PR Verifier</title>" in html
    assert "prism.min.js" in html
    assert "lucide" in html
    assert "scenario-selector" in html
    assert "telemetry-log-container" in html
    assert "btn-run-audit" in html
    assert "PR-401" in html
    assert "Custom PR Playground" in html


# ---------------------------------------------------------------------------
# 2. Scenario Catalog API
# ---------------------------------------------------------------------------

def test_get_scenarios_returns_all_enterprise_scenarios():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    for sc_id in ["PR-104", "PR-209", "PR-318", "PR-401"]:
        assert sc_id in data
        item = data[sc_id]
        assert item["id"] == sc_id
        assert len(item["title"]) > 0
        assert len(item["repository"]) > 0
        assert len(item["source_code"]) > 0
        assert len(item["adversarial_test_code"]) > 0


# ---------------------------------------------------------------------------
# 3. Auditing Preloaded Scenarios via API
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sc_id, expected_status, expected_defect_proven", [
    ("PR-104", "VERIFIED_DEFECT", True),
    ("PR-209", "VERIFIED_DEFECT", True),
    ("PR-318", "VERIFIED_DEFECT", True),
    ("PR-401", "VERIFIED_CLEAN", False),
])
def test_audit_scenarios_via_api(sc_id, expected_status, expected_defect_proven):
    res = client.post("/api/audit", json={"scenario_id": sc_id})
    assert res.status_code == 200
    audit_id = res.json()["audit_id"]

    res_audit = client.get(f"/api/audit/result/{audit_id}")
    assert res_audit.status_code == 200
    data = res_audit.json()
    assert data["status"] == expected_status
    assert data["defect_proven"] == expected_defect_proven


# ---------------------------------------------------------------------------
# 4. Auditing Custom Code via API with Autonomous Boundary Synthesis
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("custom_code, expected_exc", [
    ("def get_first(items):\n    return items[0]\n", "IndexError"),
    ("def calc_avg(total, count):\n    return total / count\n", "ZeroDivisionError"),
    ("def get_user_tier(user):\n    return user.tier\n", "AttributeError"),
])
def test_audit_custom_code_synthesizes_boundary_test(custom_code, expected_exc):
    payload = {
        "scenario_id": "PR-CUSTOM",
        "custom_source": custom_code,
        "custom_filename": "custom.py",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    audit_id = res.json()["audit_id"]

    res_audit = client.get(f"/api/audit/result/{audit_id}")
    assert res_audit.status_code == 200
    data = res_audit.json()
    assert data["defect_proven"] is True
    assert data["failing_test"]["exception_type"] in (expected_exc, "TypeError")


def test_audit_custom_code_with_candidate_patch():
    orig_code = "def get_first(items):\n    return items[0]\n"
    patch_code = "def get_first(items):\n    if not items:\n        return None\n    return items[0]\n"
    payload = {
        "scenario_id": "PR-CUSTOM",
        "custom_source": orig_code,
        "custom_patch": patch_code,
        "custom_filename": "custom.py",
    }
    res = client.post("/api/audit", json=payload)
    assert res.status_code == 200
    audit_id = res.json()["audit_id"]

    res_audit = client.get(f"/api/audit/result/{audit_id}")
    assert res_audit.status_code == 200
    data = res_audit.json()
    assert data["defect_proven"] is True
    assert data["patch"] is not None
    assert data["dual_verification"] is not None
    assert data["dual_verification"]["verified"] is True


# ---------------------------------------------------------------------------
# 5. Download Endpoint Tests
# ---------------------------------------------------------------------------

def test_download_test_endpoint_success():
    # Trigger an audit for PR-104
    res = client.post("/api/audit", json={"scenario_id": "PR-104"})
    audit_id = res.json()["audit_id"]

    dl_res = client.get(f"/api/download/test/{audit_id}")
    assert dl_res.status_code == 200
    assert "attachment" in dl_res.headers.get("content-disposition", "")
    assert "test_empty_cart_boundary_linus" in dl_res.text


def test_download_test_endpoint_404_for_invalid_audit():
    dl_res = client.get("/api/download/test/nonexistent-id-999")
    assert dl_res.status_code == 404


def test_audit_result_endpoint_404_for_invalid_audit():
    res = client.get("/api/audit/result/nonexistent-id-999")
    assert res.status_code == 404


def test_telemetry_stream_endpoint_404_for_invalid_audit():
    res = client.get("/api/audit/stream/nonexistent-id-999")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# 6. GitHub Webhook Ingestion Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("action_name, expected_status", [
    ("opened", "INGESTED"),
    ("synchronize", "INGESTED"),
    ("reopened", "INGESTED"),
    ("closed", "IGNORED"),
    ("labeled", "IGNORED"),
    ("unlabeled", "IGNORED"),
    ("assigned", "IGNORED"),
    ("edited", "IGNORED"),
    ("review_requested", "IGNORED"),
])
def test_github_webhook_actions(action_name, expected_status):
    payload = {
        "action": action_name,
        "pull_request": {"number": 42},
        "repository": {"full_name": "acme-corp/service"},
    }
    res = client.post("/webhook/github", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == expected_status
