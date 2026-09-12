from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status

from underwriting_agent.api.dependencies import (
    get_decision_repository,
    get_underwriting_service,
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
