from fastapi import FastAPI

from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.submission import InsuranceSubmission

app = FastAPI(
    title="Underwriting Agent API",
    version="0.1.0",
    description="Explainable cyber SME underwriting decision service.",
)

underwriting_service = UnderwritingService()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/underwrite",
    response_model=UnderwritingDecision,
    summary="Evaluate an insurance submission",
)
def underwrite_submission(submission: InsuranceSubmission) -> UnderwritingDecision:
    return underwriting_service.underwrite(submission)
