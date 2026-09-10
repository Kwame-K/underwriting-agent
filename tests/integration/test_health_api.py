from fastapi.testclient import TestClient

from underwriting_agent.api.app import app
from underwriting_agent.api.dependencies import get_underwriting_service
from underwriting_agent.application.underwriting_service import UnderwritingService

app.dependency_overrides[get_underwriting_service] = UnderwritingService


client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_underwrite_returns_need_more_information_for_incomplete_submission() -> None:
    response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-API-001",
            "applicant_name": "NorthStar Retail Inc.",
            "country": "Canada",
            "industry": "Retail",
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["decision"] == "NEED_MORE_INFORMATION"
    assert body["missing_information"] == [
        "annual_revenue_cad",
        "employee_count",
        "mfa_enabled",
        "prior_cyber_claims",
    ]


def test_underwrite_returns_pending_for_complete_submission() -> None:
    response = client.post(
        "/underwrite",
        json={
            "submission_id": "SUB-API-002",
            "applicant_name": "Acme Distribution Inc.",
            "country": "Canada",
            "industry": "Wholesale distribution",
            "annual_revenue_cad": 12_500_000,
            "employee_count": 85,
            "mfa_enabled": True,
            "prior_cyber_claims": 0,
            "requested_limit_cad": 1_000_000,
            "requested_retention_cad": 25_000,
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "PENDING_UNDERWRITING"
