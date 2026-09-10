import pytest
from fastapi.testclient import TestClient
from web_demo.server import app

client = TestClient(app)

def test_dashboard_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "LINUS" in response.text
    assert "Autonomous Adversarial PR Verifier" in response.text


def test_scenarios_endpoint():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "PR-104" in data
    assert "PR-209" in data
    assert "PR-318" in data
    assert "PR-401" in data
    assert "pricing" in data["PR-104"]["title"].lower()
    assert "payments" in data["PR-401"]["title"].lower()


def test_github_webhook_endpoint():
    payload = {
        "action": "opened",
        "pull_request": {"number": 104},
        "repository": {"full_name": "acme-corp/ecommerce-service"}
    }
    response = client.post("/webhook/github", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "INGESTED"


def test_audit_endpoint_and_result():
    req = {"scenario_id": "PR-104"}
    response = client.post("/api/audit", json=req)
    assert response.status_code == 200
    audit_id = response.json().get("audit_id")
    assert audit_id is not None

    res = client.get(f"/api/audit/result/{audit_id}")
    assert res.status_code == 200
    result_data = res.json()
    assert result_data["defect_proven"] is True
    assert result_data["failing_test"]["exception_type"] == "IndexError"
    assert result_data["dual_verification"]["verified"] is True
    assert result_data["dual_verification"]["adversarial_test_passed"] is True
    assert result_data["dual_verification"]["baseline_suite_passed"] is True

    # Test download endpoint
    dl_res = client.get(f"/api/download/test/{audit_id}")
    assert dl_res.status_code == 200
    assert "test_empty_cart_boundary_linus" in dl_res.text


def test_audit_clean_pr_endpoint():
    req = {"scenario_id": "PR-401"}
    response = client.post("/api/audit", json=req)
    assert response.status_code == 200
    audit_id = response.json().get("audit_id")

    res = client.get(f"/api/audit/result/{audit_id}")
    assert res.status_code == 200
    result_data = res.json()
    assert result_data["defect_proven"] is False
    assert result_data["status"] == "VERIFIED_CLEAN"


def test_audit_custom_code_with_synthesizer():
    custom_code = "def divide(a, b):\n    return a / b\n"
    req = {
        "scenario_id": "PR-CUSTOM",
        "custom_source": custom_code,
        "custom_filename": "math_ops.py",
    }
    response = client.post("/api/audit", json=req)
    assert response.status_code == 200
    audit_id = response.json().get("audit_id")

    res = client.get(f"/api/audit/result/{audit_id}")
    assert res.status_code == 200
    result_data = res.json()
    assert result_data["defect_proven"] is True
    assert result_data["failing_test"]["exception_type"] == "ZeroDivisionError"
