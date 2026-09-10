from datetime import UTC, datetime

from pydantic import BaseModel, Field

from underwriting_agent.domain.enums import DecisionType, RiskBand
from underwriting_agent.domain.risk_score import RiskFactor
from underwriting_agent.domain.rules import RuleResult


class UnderwritingDecision(BaseModel):
    submission_id: str
    decision: DecisionType
    human_review_required: bool

    risk_score: float | None = Field(default=None, ge=0, le=100)
    risk_band: RiskBand | None = None
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    scoring_model_version: str | None = None

    reasons: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    referral_reasons: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    rule_results: list[RuleResult] = Field(default_factory=list)

    policy_version: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
