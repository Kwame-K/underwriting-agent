from pydantic import BaseModel, Field

from underwriting_agent.domain.enums import ProductLine


class InsuranceSubmission(BaseModel):
    submission_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the underwriting submission.",
    )
    product_line: ProductLine = ProductLine.CYBER_SME

    applicant_name: str | None = None
    country: str | None = None
    province: str | None = None
    industry: str | None = None

    annual_revenue_cad: float | None = Field(default=None, ge=0)
    employee_count: int | None = Field(default=None, ge=0)

    handles_personal_data: bool | None = None
    handles_payment_card_data: bool | None = None

    mfa_enabled: bool | None = None
    endpoint_detection_response: bool | None = None
    offline_backups: bool | None = None

    prior_cyber_claims: int | None = Field(default=None, ge=0)

    requested_limit_cad: float | None = Field(default=None, gt=0)
    requested_retention_cad: float | None = Field(default=None, ge=0)
