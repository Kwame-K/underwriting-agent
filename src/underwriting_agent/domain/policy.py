from pydantic import BaseModel, ConfigDict, Field

from underwriting_agent.domain.condition import UnderwritingCondition
from underwriting_agent.domain.enums import ProductLine, RiskBand


class UnderwritingAuthority(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_automated_limit_cad: float = Field(gt=0)
    max_automated_revenue_cad: float = Field(gt=0)
    max_automated_prior_claims: int = Field(ge=0)


class SecurityControlsPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mfa_required_for_automated_underwriting: bool


class PricingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    pricing_model_version: str = Field(min_length=1)
    base_rate: float = Field(gt=0)
    minimum_premium_cad: float = Field(gt=0)

    reference_limit_cad: float = Field(gt=0)
    reference_retention_cad: float = Field(gt=0)

    minimum_retention_factor: float = Field(gt=0)
    maximum_retention_factor: float = Field(gt=0)

    risk_band_multipliers: dict[RiskBand, float]


class ConditionsPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mfa_not_enabled: UnderwritingCondition
    edr_not_confirmed: UnderwritingCondition
    offline_backups_not_confirmed: UnderwritingCondition
    payment_card_data: UnderwritingCondition
    prior_cyber_claims: UnderwritingCondition
    enhanced_security_review: UnderwritingCondition
    high_limit_review: UnderwritingCondition


class UnderwritingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_name: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    product_line: ProductLine

    supported_countries: tuple[str, ...] = Field(min_length=1)
    excluded_industries: tuple[str, ...] = Field(default_factory=tuple)

    authority: UnderwritingAuthority
    security_controls: SecurityControlsPolicy
    pricing: PricingPolicy
    conditions: ConditionsPolicy
