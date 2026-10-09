"""Business operations exposed by the underwriting MCP server."""

from enum import StrEnum
from typing import Any
from uuid import uuid4

from underwriting_agent.api.dependencies import (
    get_decision_repository,
    get_submission_extractor,
    get_underwriting_service,
)
from underwriting_agent.application.submission_mapper import (
    MappingStatus,
    SubmissionMapper,
)
from underwriting_agent.domain.review import DecisionReviewStatus
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.submission_extractor.http_client import (
    SubmissionExtractorUnavailableError,
)
from underwriting_agent.integrations.submission_extractor.models import (
    ExtractionStatus,
    SubmissionExtractionRequest,
)


class ExtractEvaluateStatus(StrEnum):
    EXTRACTION_UNAVAILABLE = "EXTRACTION_UNAVAILABLE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID_SUBMISSION = "INVALID_SUBMISSION"
    EVALUATED = "EVALUATED"


def extract_submission(
    request: SubmissionExtractionRequest,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Extract candidate insurance-submission data from broker source text.

    This does not underwrite, price, bind, or persist a decision.
    """
    response = get_submission_extractor().extract(
        request=request,
        correlation_id=correlation_id or f"mcp-{uuid4()}",
    )
    return response.model_dump(mode="json")


def check_completeness(submission: InsuranceSubmission) -> dict[str, Any]:
    """Return critical and optional missing fields for an underwriting submission."""
    result = get_underwriting_service().completeness_checker.check(submission)
    return result.model_dump(mode="json")


def evaluate_underwriting(submission: InsuranceSubmission) -> dict[str, Any]:
    """Evaluate a submission without persisting a decision.

    The result includes deterministic rules, risk score, pricing indication,
    and any RAG evidence retrieved through the configured knowledge-agent port.
    """
    decision = get_underwriting_service().underwrite(submission)
    return decision.model_dump(mode="json")


def submit_underwriting(submission: InsuranceSubmission) -> dict[str, Any]:
    """Evaluate and persist an underwriting decision.

    Use only once the user has confirmed that this is the intended submission.
    """
    decision = get_underwriting_service().underwrite(submission)
    get_decision_repository().save_submission_and_decision(
        submission=submission,
        decision=decision,
    )
    return decision.model_dump(mode="json")


def get_decision(decision_id: str) -> dict[str, Any]:
    """Retrieve one persisted underwriting decision by identifier."""
    decision = get_decision_repository().get_decision(decision_id)
    if decision is None:
        raise LookupError(f"Decision '{decision_id}' was not found.")
    return decision.model_dump(mode="json")


def get_audit_trail(decision_id: str) -> list[dict[str, Any]]:
    """Retrieve the immutable audit events for one persisted decision."""
    repository = get_decision_repository()
    if repository.get_decision(decision_id) is None:
        raise LookupError(f"Decision '{decision_id}' was not found.")
    return [
        event.model_dump(mode="json")
        for event in repository.list_audit_events(decision_id)
    ]


def list_pending_reviews() -> list[dict[str, Any]]:
    """List decisions currently waiting for a human underwriter review."""
    decisions = get_decision_repository().list_decisions_by_review_status(
        DecisionReviewStatus.PENDING_REVIEW
    )
    return [decision.model_dump(mode="json") for decision in decisions]


def extract_and_evaluate(
    request: SubmissionExtractionRequest,
    overrides: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Extract, map to the cyber model, and evaluate without persisting.

    Fields the extractor cannot provide (mfa_enabled, requested_limit_cad,
    requested_retention_cad, ...) must be supplied in overrides by the caller,
    otherwise the decision is NEED_MORE_INFORMATION. Nothing is invented.
    """
    correlation = correlation_id or f"mcp-{uuid4()}"

    try:
        extraction = get_submission_extractor().extract(
            request=request,
            correlation_id=correlation,
        )
    except SubmissionExtractorUnavailableError as error:
        return {
            "workflow_status": ExtractEvaluateStatus.EXTRACTION_UNAVAILABLE.value,
            "correlation_id": correlation,
            "message": str(error),
        }

    extraction_summary = {
        "status": extraction.extraction_status.value,
        "review_required": extraction.review_required,
        "missing_fields": extraction.missing_fields,
        "ambiguous_fields": extraction.ambiguous_fields,
        "data_quality_flags": extraction.data_quality_flags,
    }

    if extraction.extraction_status is ExtractionStatus.FAILED:
        return {
            "workflow_status": ExtractEvaluateStatus.EXTRACTION_FAILED.value,
            "correlation_id": correlation,
            "extraction": extraction_summary,
            "message": extraction.error_message or "Extraction failed.",
        }

    mapping = SubmissionMapper().map(extraction.submission_data, overrides)
    mapping_summary = mapping.model_dump(mode="json", exclude={"submission"})

    if mapping.status is not MappingStatus.MAPPED or mapping.submission is None:
        workflow_status = (
            ExtractEvaluateStatus.NOT_APPLICABLE
            if mapping.status is MappingStatus.NOT_APPLICABLE
            else ExtractEvaluateStatus.INVALID_SUBMISSION
        )
        return {
            "workflow_status": workflow_status.value,
            "correlation_id": correlation,
            "extraction": extraction_summary,
            "mapping": mapping_summary,
        }

    decision = get_underwriting_service().underwrite(mapping.submission)
    return {
        "workflow_status": ExtractEvaluateStatus.EVALUATED.value,
        "correlation_id": correlation,
        "extraction": extraction_summary,
        "mapping": mapping_summary,
        "submission": mapping.submission.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
    }
