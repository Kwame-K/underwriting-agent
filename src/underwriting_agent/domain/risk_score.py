from pydantic import BaseModel, Field

from underwriting_agent.domain.enums import RiskBand


class RiskFactor(BaseModel):
    factor_id: str
    factor_name: str
    points: float
    message: str


class RiskScore(BaseModel):
    score: float = Field(ge=0, le=100)
    risk_band: RiskBand
    factors: list[RiskFactor]
    scoring_model_version: str
