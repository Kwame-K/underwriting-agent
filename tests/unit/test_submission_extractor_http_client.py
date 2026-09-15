from typing import Self

import httpx2
import pytest

from underwriting_agent.integrations.submission_extractor.http_client import (
    CORRELATION_ID_HEADER,
    HTTPSubmissionExtractor,
    SubmissionExtractorUnavailableError,
)
from underwriting_agent.integrations.submission_extractor.models import (
    ExtractionStatus,
    SourceType,
    SubmissionExtractionRequest,
)
from underwriting_agent.settings import Settings


def build_request() -> SubmissionExtractionRequest:
    return SubmissionExtractionRequest(
        source_id="SRC-EXTRACT-001",
        source_type=SourceType.FREE_TEXT,
        document_name="broker-email.txt",
        content="Please quote cyber insurance for Northwind Retail.",
        language="en",
    )


def build_response() -> dict[str, object]:
    return {
        "source_id": "SRC-EXTRACT-001",
        "extraction_status": "COMPLETE",
        "submission_data": {
            "submission_id": "SRC-EXTRACT-001",
            "product_line": "cyber",
            "business_activity": "retail",
            "location_city": "Montreal",
            "location_province": "QC",
            "annual_revenue_cad": 1_200_000,
        },
        "missing_fields": [],
        "ambiguous_fields": [],
        "field_confidence": {},
        "source_references": [],
        "data_quality_flags": [],
        "review_required": False,
        "provider": "groq",
        "model": "openai/gpt-oss-120b",
        "processed_at": "2026-09-15T04:45:00Z",
        "extraction_notes": [],
        "error_code": None,
        "error_message": None,
    }


def test_http_submission_extractor_sends_contract_and_correlation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return build_response()

    class FakeClient:
        def __init__(
            self,
            base_url: str,
            timeout: float,
        ) -> None:
            captured["base_url"] = base_url
            captured["timeout"] = timeout

        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            return None

        def post(
            self,
            path: str,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> FakeResponse:
            captured["path"] = path
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(httpx2, "Client", FakeClient)

    settings = Settings(
        submission_extractor_base_url="http://extractor.test:8000",
        submission_extractor_timeout_seconds=27.5,
    )
    client = HTTPSubmissionExtractor(settings=settings)

    result = client.extract(
        request=build_request(),
        correlation_id="workflow-2026-0001",
    )

    assert captured["base_url"] == "http://extractor.test:8000"
    assert captured["timeout"] == 27.5
    assert captured["path"] == "/v1/extract-submission"
    assert captured["headers"] == {
        CORRELATION_ID_HEADER: "workflow-2026-0001",
    }
    assert captured["json"] == {
        "source_id": "SRC-EXTRACT-001",
        "source_type": "FREE_TEXT",
        "document_name": "broker-email.txt",
        "content": "Please quote cyber insurance for Northwind Retail.",
        "language": "en",
    }
    assert result.extraction_status is ExtractionStatus.COMPLETE
    assert result.review_required is False
    assert result.submission_data["product_line"] == "cyber"


def test_http_submission_extractor_raises_controlled_error_on_http_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, path: str, **kwargs: object) -> object:
            request = httpx2.Request(
                method="POST",
                url="http://extractor.test:8000/v1/extract-submission",
            )
            response = httpx2.Response(status_code=503, request=request)
            raise httpx2.HTTPStatusError(
                "Service unavailable.",
                request=request,
                response=response,
            )

    monkeypatch.setattr(httpx2, "Client", FakeClient)

    client = HTTPSubmissionExtractor(
        settings=Settings(
            submission_extractor_base_url="http://extractor.test:8000",
        )
    )

    with pytest.raises(
        SubmissionExtractorUnavailableError,
        match="Insurance Submission Extractor is unavailable",
    ):
        client.extract(
            request=build_request(),
            correlation_id="workflow-2026-0002",
        )


def test_http_submission_extractor_raises_controlled_error_for_invalid_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"source_id": "SRC-EXTRACT-001"}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, path: str, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(httpx2, "Client", FakeClient)

    client = HTTPSubmissionExtractor()

    with pytest.raises(
        SubmissionExtractorUnavailableError,
        match="Insurance Submission Extractor is unavailable",
    ):
        client.extract(
            request=build_request(),
            correlation_id="workflow-2026-0003",
        )
