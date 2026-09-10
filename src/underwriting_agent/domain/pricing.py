from pydantic import BaseModel, Field

from underwriting_agent.domain.enums import RiskBand


class PricingFactor(BaseModel):
    factor_id: str
    factor_name: str
    multiplier: float
    message: str


class PricingIndication(BaseModel):
    base_exposure_premium_cad: float = Field(ge=0)
    indicated_premium_cad: float = Field(ge=0)

    requested_limit_cad: float = Field(gt=0)
    requested_retention_cad: float = Field(gt=0)

    risk_band: RiskBand
    factors: list[PricingFactor]

    pricing_model_version: str
