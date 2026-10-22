from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.submission_extractor.models import (
    ExtractionStatus,
    SourceType,
    SubmissionExtractionRequest,
    SubmissionExtractionResponse,
)
from underwriting_agent.mcp_server import tools


def _submission() -> InsuranceSubmission:
    return InsuranceSubmission(submission_id="SUB-MCP-001")


def test_check_completeness_returns_serialized_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_checker = SimpleNamespace(
        check=lambda submission: SimpleNamespace(
            model_dump=lambda mode: {"complete": False}
        )
    )
    monkeypatch.setattr(
        tools,
        "get_underwriting_service",
        lambda: SimpleNamespace(completeness_checker=fake_checker),
    )

    assert tools.check_completeness(_submission()) == {"complete": False}


def test_submit_underwriting_evaluates_then_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved: list[tuple[InsuranceSubmission, object]] = []
    decision = SimpleNamespace(model_dump=lambda mode: {"decision": "REFER"})
    service = SimpleNamespace(underwrite=lambda submission: decision)
    repository = SimpleNamespace(
        save_submission_and_decision=lambda submission, decision: saved.append(
            (submission, decision)
        )
    )
    monkeypatch.setattr(tools, "get_underwriting_service", lambda: service)
    monkeypatch.setattr(tools, "get_decision_repository", lambda: repository)

    submission = _submission()

    assert tools.submit_underwriting(submission) == {"decision": "REFER"}
    assert saved == [(submission, decision)]


def test_get_decision_raises_when_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tools,
        "get_decision_repository",
        lambda: SimpleNamespace(get_decision=lambda decision_id: None),
    )

    with pytest.raises(ToolError, match="was not found"):
        tools.get_decision("missing")


class _FakeExtractor:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data

    def extract(
        self, request: SubmissionExtractionRequest, correlation_id: str
    ) -> SubmissionExtractionResponse:
        return SubmissionExtractionResponse(
            source_id=request.source_id,
            extraction_status=ExtractionStatus.COMPLETE,
            submission_data=self.data,
        )


def _extraction_request() -> SubmissionExtractionRequest:
    return SubmissionExtractionRequest(
        source_id="SRC-1", source_type=SourceType.FREE_TEXT, content="text"
    )


_CYBER_DATA: dict[str, object] = {
    "submission_id": "SRC-1",
    "product_line": "cyber",
    "insured_name": "Acme Inc.",
    "business_activity": "Wholesale distribution",
    "location_province": "QC",
    "employee_count": 40,
    "annual_revenue_cad": 2_000_000,
    "claims_history_status": "no_losses_reported",
}

_CONTROL_OVERRIDES: dict[str, object] = {
    "mfa_enabled": True,
    "requested_limit_cad": 1_000_000,
    "requested_retention_cad": 25_000,
}


def _install(monkeypatch: pytest.MonkeyPatch, data: dict[str, object]) -> None:
    monkeypatch.setattr(tools, "get_submission_extractor", lambda: _FakeExtractor(data))
    monkeypatch.setattr(
        tools, "get_underwriting_service", lambda: UnderwritingService()
    )


def test_extract_and_evaluate_is_pending_without_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, {**_CYBER_DATA, "claims_history_status": "not_provided"})

    result = tools.extract_and_evaluate(_extraction_request())

    assert result["workflow_status"] == "PENDING_INFORMATION"
    assert result["decision"]["decision"] == "NEED_MORE_INFORMATION"
    assert "mfa_enabled" in result["missing_fields"]
    assert result["persisted"] is False


def test_extract_and_evaluate_with_overrides_is_evaluated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, _CYBER_DATA)

    result = tools.extract_and_evaluate(
        _extraction_request(), overrides=_CONTROL_OVERRIDES
    )

    assert result["workflow_status"] == "EVALUATED"
    assert result["decision"]["decision"] != "NEED_MORE_INFORMATION"
    assert result["overridden_fields"] == [
        "mfa_enabled",
        "requested_limit_cad",
        "requested_retention_cad",
    ]
    assert result["persisted"] is False


def test_extract_and_evaluate_skips_non_cyber_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, {**_CYBER_DATA, "product_line": "commercial_property"})

    result = tools.extract_and_evaluate(_extraction_request())

    assert result["workflow_status"] == "UNSUPPORTED_SUBMISSION"
    assert result["decision"] is None
