from typing import Annotated

from fastapi import Depends, FastAPI

from underwriting_agent.api.dependencies import get_underwriting_service
from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.submission import InsuranceSubmission

app = FastAPI(
    title="Underwriting Agent API",
    version="0.1.0",
    description="Explainable cyber SME underwriting decision service.",
)

UnderwritingServiceDependency = Annotated[
    UnderwritingService,
    Depends(get_underwriting_service),
]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/underwrite",
    response_model=UnderwritingDecision,
    summary="Evaluate an insurance submission",
)
def underwrite_submission(
    submission: InsuranceSubmission,
    service: UnderwritingServiceDependency,
) -> UnderwritingDecision:
    return service.underwrite(submission)
