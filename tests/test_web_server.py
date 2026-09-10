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
    assert "pricing" in data["PR-104"]["title"].lower()

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
