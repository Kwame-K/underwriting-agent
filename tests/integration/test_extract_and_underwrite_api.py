from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from underwriting_agent.api.app import app
from underwriting_agent.api.dependencies import (
    get_decision_repository,
    get_submission_extractor,
    get_underwriting_service,
)
from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.submission import InsuranceSubmission
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


class CompleteCyberExtractor:
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
                "requested_coverages": ["cyber_liability"],
                "insured_name": "Northwind Retail",
                "business_activity": "software",
                "location_province": "QC",
                "annual_revenue_cad": 2_500_000,
                "employee_count": 25,
            },
            review_required=False,
        )


class NonCyberExtractor:
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
                "product_line": "property",
                "requested_coverages": ["property_damage"],
                "insured_name": "Northwind Retail",
                "business_activity": "retail",
                "location_province": "QC",
            },
            review_required=False,
        )


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: list[tuple[InsuranceSubmission, UnderwritingDecision]] = []

    def save_submission_and_decision(
        self,
        submission: InsuranceSubmission,
        decision: UnderwritingDecision,
    ) -> None:
        self.saved.append((submission, decision))


_CONTROL_OVERRIDES: dict[str, Any] = {
    "mfa_enabled": True,
    "prior_cyber_claims": 0,
    "requested_limit_cad": 1_000_000,
    "requested_retention_cad": 25_000,
}


def test_complete_extraction_without_controls_is_pending_and_not_persisted(
    client_with_extractor: Callable[[object], TestClient],
    recording_repository: RecordingRepository,
) -> None:
    client = client_with_extractor(CompleteCyberExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json={**valid_payload(), "persist": True},
        headers={"X-Correlation-ID": "workflow-2026-0002"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["workflow_status"] == "PENDING_INFORMATION"
    assert payload["decision"]["decision"] == "NEED_MORE_INFORMATION"
    assert "mfa_enabled" in payload["missing_fields"]
    assert "country" in payload["inferred_fields"]
    assert payload["persisted"] is False
    assert recording_repository.saved == []
    assert response.headers["X-Correlation-ID"] == "workflow-2026-0002"


def test_overrides_complete_the_submission_without_persisting_by_default(
    client_with_extractor: Callable[[object], TestClient],
    recording_repository: RecordingRepository,
) -> None:
    client = client_with_extractor(CompleteCyberExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json={**valid_payload(), "overrides": _CONTROL_OVERRIDES},
    )

    payload = response.json()

    assert payload["workflow_status"] == "EVALUATED"
    assert payload["decision"]["decision"] != "NEED_MORE_INFORMATION"
    assert sorted(payload["overridden_fields"]) == sorted(_CONTROL_OVERRIDES)
    assert payload["persisted"] is False
    assert recording_repository.saved == []


def test_persist_true_saves_a_complete_evaluation(
    client_with_extractor: Callable[[object], TestClient],
    recording_repository: RecordingRepository,
) -> None:
    client = client_with_extractor(CompleteCyberExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json={**valid_payload(), "overrides": _CONTROL_OVERRIDES, "persist": True},
    )

    payload = response.json()

    assert payload["workflow_status"] == "EVALUATED"
    assert payload["persisted"] is True
    assert len(recording_repository.saved) == 1


def test_unknown_override_field_is_reported(
    client_with_extractor: Callable[[object], TestClient],
) -> None:
    client = client_with_extractor(CompleteCyberExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json={**valid_payload(), "overrides": {"submission_id": "HACK"}},
    )

    payload = response.json()

    assert payload["workflow_status"] == "PENDING_INFORMATION"
    assert payload["decision"] is None
    assert payload["mapping_messages"]


def test_extract_and_underwrite_does_not_underwrite_non_cyber_submission(
    client_with_extractor: Callable[[object], TestClient],
) -> None:
    client = client_with_extractor(NonCyberExtractor())

    response = client.post(
        "/extract-and-underwrite",
        json=valid_payload(),
        headers={"X-Correlation-ID": "workflow-2026-0003"},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["workflow_status"] == "UNSUPPORTED_SUBMISSION"
    assert payload["extraction_status"] == "COMPLETE"
    assert payload["decision"] is None
    assert "cyber" in payload["message"].lower()
    assert response.headers["X-Correlation-ID"] == "workflow-2026-0003"


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
def override_dependency() -> Iterator[Callable[[Callable[..., Any], object], None]]:
    previous: dict[Callable[..., Any], Callable[..., Any] | None] = {}

    def install(dependency: Callable[..., Any], value: object) -> None:
        previous.setdefault(dependency, app.dependency_overrides.get(dependency))
        app.dependency_overrides[dependency] = lambda: value

    yield install

    for dependency, original in previous.items():
        if original is None:
            app.dependency_overrides.pop(dependency, None)
        else:
            app.dependency_overrides[dependency] = original


@pytest.fixture
def recording_repository(
    override_dependency: Callable[[Callable[..., Any], object], None],
) -> RecordingRepository:
    repository = RecordingRepository()
    override_dependency(get_decision_repository, repository)
    return repository


@pytest.fixture
def client_with_extractor(
    override_dependency: Callable[[Callable[..., Any], object], None],
    recording_repository: RecordingRepository,
) -> Callable[[object], TestClient]:
    override_dependency(get_underwriting_service, UnderwritingService())

    def build_client(extractor: object) -> TestClient:
        override_dependency(get_submission_extractor, extractor)

        return TestClient(app)

    return build_client


def test_extract_and_underwrite_routes_partial_extraction_to_review(
    client_with_extractor: Callable[[object], TestClient],
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


def test_extract_and_underwrite_returns_controlled_status_when_extractor_unavailable(
    client_with_extractor: Callable[[object], TestClient],
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
