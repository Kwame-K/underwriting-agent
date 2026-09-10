from pydantic import BaseModel, ConfigDict, Field

from underwriting_agent.domain.enums import ProductLine


class UnderwritingAuthority(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_automated_limit_cad: float = Field(gt=0)
    max_automated_revenue_cad: float = Field(gt=0)
    max_automated_prior_claims: int = Field(ge=0)


class SecurityControlsPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mfa_required_for_automated_underwriting: bool


class UnderwritingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_name: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    product_line: ProductLine

    supported_countries: tuple[str, ...] = Field(min_length=1)
    excluded_industries: tuple[str, ...] = Field(default_factory=tuple)

    authority: UnderwritingAuthority
    security_controls: SecurityControlsPolicy
