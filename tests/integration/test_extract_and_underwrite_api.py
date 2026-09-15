import pytest
from fastapi.testclient import TestClient

from underwriting_agent.api.app import app
from underwriting_agent.api.dependencies import get_submission_extractor
from underwriting_agent.integrations.submission_extractor.http_client import (
    SubmissionExtractorUnavailableError,
)
from underwriting_agent.integrations.submission_extractor.models import (
    ExtractionStatus,
    SubmissionExtractionResponse,
)


def valid_payload() -> dict[str, str]:
    return {
        "source_id": "SRC-UW-001",
        "source_type": "FREE_TEXT",
        "document_name": "broker-email.txt",
        "content": "Please quote cyber insurance for Northwind Retail.",
        "language": "en",
    }


class PartialExtractor:
    def extract(
        self,
        request: object,
        correlation_id: str,
    ) -> SubmissionExtractionResponse:
        assert correlation_id == "workflow-2026-0001"

        return SubmissionExtractionResponse(
            source_id="SRC-UW-001",
            extraction_status=ExtractionStatus.PARTIAL,
            submission_data={"submission_id": "SRC-UW-001"},
            missing_fields=["postal_code", "requested_coverages"],
            ambiguous_fields=[],
            data_quality_flags=[
                {
                    "field": "claims_history",
                    "severity": "info",
                    "code": "CLAIMS_HISTORY_NOT_PROVIDED",
                    "message": "No claims history was provided in the submission.",
                }
            ],
            review_required=True,
        )


class CompleteExtractor:
    def extract(
        self,
        request: object,
        correlation_id: str,
    ) -> SubmissionExtractionResponse:
        return SubmissionExtractionResponse(
            source_id="SRC-UW-001",
            extraction_status=ExtractionStatus.COMPLETE,
            submission_data={
                "submission_id": "SRC-UW-001",
                "product_line": "cyber",
                "business_activity": "software",
            },
            review_required=False,
        )


class UnavailableExtractor:
    def extract(
        self,
        request: object,
        correlation_id: str,
    ) -> SubmissionExtractionResponse:
        raise SubmissionExtractorUnavailableError(
            "Insurance Submission Extractor is unavailable or returned "
            "an invalid response."
        )


@pytest.fixture
def client_with_extractor():
    def build_client(extractor: object) -> TestClient:
        app.dependency_overrides[get_submission_extractor] = lambda: extractor

        return TestClient(app)

    yield build_client

    app.dependency_overrides.pop(get_submission_extractor, None)


def test_extract_and_underwrite_routes_partial_extraction_to_review(
    client_with_extractor: object,
) -> None:
    client = client_with_extractor(PartialExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json=valid_payload(),
        headers={"X-Correlation-ID": "workflow-2026-0001"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["source_id"] == "SRC-UW-001"
    assert payload["correlation_id"] == "workflow-2026-0001"
    assert payload["workflow_status"] == "PENDING_INFORMATION"
    assert payload["extraction_status"] == "PARTIAL"
    assert payload["review_required"] is True
    assert payload["missing_fields"] == ["postal_code", "requested_coverages"]
    assert payload["data_quality_flags"][0]["code"] == "CLAIMS_HISTORY_NOT_PROVIDED"
    assert response.headers["X-Correlation-ID"] == "workflow-2026-0001"


def test_extract_and_underwrite_does_not_underwrite_unmapped_complete_extraction(
    client_with_extractor: object,
) -> None:
    client = client_with_extractor(CompleteExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json=valid_payload(),
        headers={"X-Correlation-ID": "workflow-2026-0002"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["workflow_status"] == "UNSUPPORTED_SUBMISSION"
    assert payload["extraction_status"] == "COMPLETE"
    assert payload["review_required"] is False
    assert "mapping" in payload["message"].lower()
    assert response.headers["X-Correlation-ID"] == "workflow-2026-0002"


def test_extract_and_underwrite_returns_controlled_status_when_extractor_unavailable(
    client_with_extractor: object,
) -> None:
    client = client_with_extractor(UnavailableExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json=valid_payload(),
        headers={"X-Correlation-ID": "workflow-2026-0003"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["workflow_status"] == "EXTRACTION_UNAVAILABLE"
    assert payload["correlation_id"] == "workflow-2026-0003"
    assert "unavailable" in payload["message"].lower()
    assert response.headers["X-Correlation-ID"] == "workflow-2026-0003"
