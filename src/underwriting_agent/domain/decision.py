from datetime import UTC, datetime

from pydantic import BaseModel, Field

from underwriting_agent.domain.condition import UnderwritingCondition
from underwriting_agent.domain.enums import DecisionType, RiskBand
from underwriting_agent.domain.evidence import EvidenceCitation
from underwriting_agent.domain.pricing import PricingFactor
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

    base_exposure_premium_cad: float | None = Field(default=None, ge=0)
    indicated_premium_cad: float | None = Field(default=None, ge=0)
    pricing_factors: list[PricingFactor] = Field(default_factory=list)
    pricing_model_version: str | None = None

    reasons: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    referral_reasons: list[str] = Field(default_factory=list)
    conditions: list[UnderwritingCondition] = Field(default_factory=list)
    rule_results: list[RuleResult] = Field(default_factory=list)
    evidence: list[EvidenceCitation] = Field(default_factory=list)

    policy_version: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
