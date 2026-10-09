"""Deterministic mapping from extractor output to the cyber underwriting model."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from underwriting_agent.domain.submission import InsuranceSubmission

CANADIAN_PROVINCES = frozenset(
    {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
)
SUPPORTED_COUNTRY_LABEL = "Canada"
CYBER_PRODUCT_LINE = "cyber"
CYBER_COVERAGE = "cyber_liability"
CYBER_CLAIM_TYPE = "cyber_incident"

NON_MAPPED_FIELDS = frozenset({"submission_id", "product_line"})
OVERRIDABLE_FIELDS = frozenset(InsuranceSubmission.model_fields) - NON_MAPPED_FIELDS


class MappingStatus(StrEnum):
    MAPPED = "MAPPED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INVALID = "INVALID"


class MappingResult(BaseModel):
    status: MappingStatus
    submission: InsuranceSubmission | None = None
    inferred_fields: list[str] = Field(default_factory=list)
    overridden_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class SubmissionMapper:
    """Map candidate extraction data without inventing missing information.

    Fields that the extractor cannot provide (security controls, requested
    limit and retention) stay None unless supplied through explicit overrides.
    """

    def map(
        self,
        submission_data: Mapping[str, Any],
        overrides: Mapping[str, Any] | None = None,
    ) -> MappingResult:
        overrides = dict(overrides or {})

        unknown_overrides = sorted(set(overrides) - OVERRIDABLE_FIELDS)
        if unknown_overrides:
            return MappingResult(
                status=MappingStatus.INVALID,
                messages=[f"Unsupported override fields: {unknown_overrides}."],
            )

        if not self._is_cyber_submission(submission_data):
            return MappingResult(
                status=MappingStatus.NOT_APPLICABLE,
                messages=["The extracted submission does not request cyber coverage."],
            )

        submission_id = self._clean(submission_data.get("submission_id"))
        if submission_id is None:
            return MappingResult(
                status=MappingStatus.INVALID,
                messages=["The extracted submission has no submission_id."],
            )

        province = self._clean(submission_data.get("location_province"))
        values: dict[str, Any] = {
            "applicant_name": self._clean(submission_data.get("insured_name")),
            "province": province,
            "industry": self._clean(submission_data.get("business_activity")),
            "annual_revenue_cad": submission_data.get("annual_revenue_cad"),
            "employee_count": submission_data.get("employee_count"),
            "prior_cyber_claims": self._prior_cyber_claims(submission_data),
        }

        inferred_fields: list[str] = []
        if province is not None and province.upper() in CANADIAN_PROVINCES:
            values["country"] = SUPPORTED_COUNTRY_LABEL
            inferred_fields.append("country")

        overridden_fields = sorted(overrides)
        values.update(overrides)
        inferred_fields = [f for f in inferred_fields if f not in overrides]

        try:
            submission = InsuranceSubmission(submission_id=submission_id, **values)
        except ValidationError as error:
            return MappingResult(
                status=MappingStatus.INVALID,
                messages=[
                    f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                    for item in error.errors()
                ],
            )

        missing_fields = [
            name
            for name in InsuranceSubmission.model_fields
            if name not in NON_MAPPED_FIELDS and getattr(submission, name) is None
        ]

        return MappingResult(
            status=MappingStatus.MAPPED,
            submission=submission,
            inferred_fields=inferred_fields,
            overridden_fields=overridden_fields,
            missing_fields=missing_fields,
        )

    @staticmethod
    def _clean(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _is_cyber_submission(data: Mapping[str, Any]) -> bool:
        coverages = data.get("requested_coverages") or []
        return data.get("product_line") == CYBER_PRODUCT_LINE or (
            CYBER_COVERAGE in coverages
        )

    @staticmethod
    def _prior_cyber_claims(data: Mapping[str, Any]) -> int | None:
        status = data.get("claims_history_status")
        claims = data.get("claims_history") or []

        if status == "no_losses_reported":
            return 0
        if status == "losses_reported" and claims:
            return sum(
                1 for claim in claims if claim.get("claim_type") == CYBER_CLAIM_TYPE
            )
        return None
