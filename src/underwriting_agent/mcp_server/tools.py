"""Business operations exposed by the underwriting MCP server."""

from typing import Any
from uuid import uuid4

from underwriting_agent.api.dependencies import (
    get_decision_repository,
    get_submission_extractor,
    get_underwriting_service,
)
from underwriting_agent.application.extract_and_evaluate_service import (
    ExtractAndEvaluateService,
)
from underwriting_agent.domain.review import DecisionReviewStatus
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.submission_extractor.models import (
    SubmissionExtractionRequest,
)


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

    Fields the extractor cannot provide (mfa_enabled, prior_cyber_claims,
    requested_limit_cad, requested_retention_cad, ...) must be supplied in
    overrides, otherwise workflow_status is PENDING_INFORMATION and
    missing_fields lists what to ask. Nothing is invented or persisted.
    """
    workflow = ExtractAndEvaluateService(
        extractor=get_submission_extractor(),
        underwriting_service=get_underwriting_service(),
    )
    result = workflow.run(
        request=request,
        correlation_id=correlation_id or f"mcp-{uuid4()}",
        overrides=overrides,
        persist=False,
    )
    return result.model_dump(mode="json")
