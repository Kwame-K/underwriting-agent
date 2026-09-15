from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status

from underwriting_agent.api.dependencies import (
    get_decision_repository,
    get_submission_extractor,
    get_underwriting_service,
)
from underwriting_agent.api.extraction_models import (
    ExtractAndUnderwriteRequest,
    ExtractAndUnderwriteResponse,
    WorkflowStatus,
)
from underwriting_agent.application.underwriting_service import (
    UnderwritingService,
)
from underwriting_agent.domain.audit import AuditEvent
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.review import (
    DecisionReview,
    DecisionReviewStatus,
    ReviewDecisionCommand,
)
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.infrastructure.repositories.decision_repository import (
    UnderwritingDecisionRepository,
)
from underwriting_agent.integrations.submission_extractor.http_client import (
    SubmissionExtractorUnavailableError,
)
from underwriting_agent.integrations.submission_extractor.models import (
    ExtractionStatus,
    SubmissionExtractionRequest,
)
from underwriting_agent.integrations.submission_extractor.port import (
    SubmissionExtractorPort,
)

app = FastAPI(
    title="Underwriting Agent API",
    version="0.1.0",
    description="Explainable cyber SME underwriting decision service.",
)

UnderwritingServiceDependency = Annotated[
    UnderwritingService,
    Depends(get_underwriting_service),
]

UnderwritingDecisionRepositoryDependency = Annotated[
    UnderwritingDecisionRepository,
    Depends(get_decision_repository),
]

ReviewStatusQuery = Annotated[
    DecisionReviewStatus,
    Query(alias="status"),
]

SubmissionExtractorDependency = Annotated[
    SubmissionExtractorPort,
    Depends(get_submission_extractor),
]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/underwrite",
    response_model=UnderwritingDecision,
    summary="Evaluate and persist an insurance submission",
)
def underwrite_submission(
    submission: InsuranceSubmission,
    service: UnderwritingServiceDependency,
    repository: UnderwritingDecisionRepositoryDependency,
) -> UnderwritingDecision:
    decision = service.underwrite(submission)

    repository.save_submission_and_decision(
        submission=submission,
        decision=decision,
    )

    return decision


@app.get(
    "/decisions",
    response_model=list[UnderwritingDecision],
    summary="List underwriting decisions by review status",
)
def list_decisions(
    review_status: ReviewStatusQuery,
    repository: UnderwritingDecisionRepositoryDependency,
) -> list[UnderwritingDecision]:
    return repository.list_decisions_by_review_status(review_status)


@app.post(
    "/decisions/{decision_id}/review",
    response_model=DecisionReview,
    summary="Record an underwriter review decision",
)
def review_decision(
    decision_id: str,
    command: ReviewDecisionCommand,
    repository: UnderwritingDecisionRepositoryDependency,
) -> DecisionReview:
    try:
        return repository.review_decision(
            decision_id=decision_id,
            command=command,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@app.get(
    "/decisions/{decision_id}",
    response_model=UnderwritingDecision,
    summary="Retrieve a persisted underwriting decision",
)
def get_decision(
    decision_id: str,
    repository: UnderwritingDecisionRepositoryDependency,
) -> UnderwritingDecision:
    decision = repository.get_decision(decision_id)

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' was not found.",
        )

    return decision


@app.get(
    "/decisions/{decision_id}/audit-trail",
    response_model=list[AuditEvent],
    summary="Retrieve an underwriting decision audit trail",
)
def get_decision_audit_trail(
    decision_id: str,
    repository: UnderwritingDecisionRepositoryDependency,
) -> list[AuditEvent]:
    decision = repository.get_decision(decision_id)

    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision '{decision_id}' was not found.",
        )

    return repository.list_audit_events(decision_id)


@app.post(
    "/extract-and-underwrite",
    response_model=ExtractAndUnderwriteResponse,
    summary="Extract a text submission before underwriting",
)
def extract_and_underwrite(
    payload: ExtractAndUnderwriteRequest,
    extractor: SubmissionExtractorDependency,
    response: Response,
    x_correlation_id: Annotated[
        str | None,
        Header(alias="X-Correlation-ID"),
    ] = None,
) -> ExtractAndUnderwriteResponse:
    correlation_id = x_correlation_id or str(uuid4())
    response.headers["X-Correlation-ID"] = correlation_id

    try:
        extraction = extractor.extract(
            request=SubmissionExtractionRequest(
                source_id=payload.source_id,
                source_type=payload.source_type,
                document_name=payload.document_name,
                content=payload.content,
                language=payload.language,
            ),
            correlation_id=correlation_id,
        )
    except SubmissionExtractorUnavailableError as error:
        return ExtractAndUnderwriteResponse(
            source_id=payload.source_id,
            correlation_id=correlation_id,
            workflow_status=WorkflowStatus.EXTRACTION_UNAVAILABLE,
            message=str(error),
        )

    needs_review = (
        extraction.extraction_status is not ExtractionStatus.COMPLETE
        or extraction.review_required
    )

    if needs_review:
        return ExtractAndUnderwriteResponse(
            source_id=payload.source_id,
            correlation_id=correlation_id,
            workflow_status=WorkflowStatus.PENDING_INFORMATION,
            extraction_status=extraction.extraction_status.value,
            review_required=extraction.review_required,
            missing_fields=extraction.missing_fields,
            ambiguous_fields=extraction.ambiguous_fields,
            data_quality_flags=extraction.data_quality_flags,
            message=(
                "Extraction requires additional information or human review "
                "before underwriting."
            ),
        )

    return ExtractAndUnderwriteResponse(
        source_id=payload.source_id,
        correlation_id=correlation_id,
        workflow_status=WorkflowStatus.UNSUPPORTED_SUBMISSION,
        extraction_status=extraction.extraction_status.value,
        message=(
            "Extraction completed, but automatic mapping to the Project 4 "
            "cyber underwriting model is not implemented yet."
        ),
    )
