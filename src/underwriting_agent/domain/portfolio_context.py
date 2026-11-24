from enum import StrEnum

from pydantic import BaseModel, Field


class PortfolioContextStatus(StrEnum):
    SUCCESS = "SUCCESS"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"


class PortfolioContext(BaseModel):
    status: PortfolioContextStatus = PortfolioContextStatus.NOT_REQUESTED
    scope: str = "PROVINCE_ALL_LINES"
    province: str | None = None
    loss_ratio: float | None = None
    claim_frequency: float | None = None
    average_severity: float | None = None
    policy_count: int | None = None
    premium_per_exposure_unit: float | None = None
    share_of_policies_with_claims: float | None = None
    underwriting_years: list[int] = Field(default_factory=list)
    disclaimer: str = (
        "Contexte de portefeuille synthetique, toutes lignes confondues. "
        "Ce n'est pas un signal cyber et il n'influence ni les regles ni le score."
    )
    failure_reason: str | None = None
