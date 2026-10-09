from typing import Any

from underwriting_agent.application.submission_mapper import (
    MappingStatus,
    SubmissionMapper,
)


def _data(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "submission_id": "SRC-001",
        "product_line": "cyber",
        "insured_name": "  Acme Inc. ",
        "business_activity": "Wholesale distribution",
        "location_province": "QC",
        "employee_count": 40,
        "annual_revenue_cad": 8_000_000,
        "requested_coverages": ["cyber_liability"],
        "claims_history": [],
        "claims_history_status": "no_losses_reported",
    }
    data.update(changes)
    return data


def test_maps_extracted_fields_and_infers_country() -> None:
    result = SubmissionMapper().map(_data())

    assert result.status is MappingStatus.MAPPED
    assert result.submission is not None
    assert result.submission.applicant_name == "Acme Inc."
    assert result.submission.industry == "Wholesale distribution"
    assert result.submission.country == "Canada"
    assert result.submission.prior_cyber_claims == 0
    assert result.inferred_fields == ["country"]


def test_never_invents_cyber_controls_or_limits() -> None:
    result = SubmissionMapper().map(_data())

    assert result.submission is not None
    for field in ("mfa_enabled", "requested_limit_cad", "requested_retention_cad"):
        assert getattr(result.submission, field) is None
        assert field in result.missing_fields


def test_overrides_take_precedence_and_are_traced() -> None:
    result = SubmissionMapper().map(
        _data(),
        overrides={"mfa_enabled": True, "requested_limit_cad": 1_000_000},
    )

    assert result.submission is not None
    assert result.submission.mfa_enabled is True
    assert result.overridden_fields == ["mfa_enabled", "requested_limit_cad"]
    assert "mfa_enabled" not in result.missing_fields


def test_unknown_override_is_rejected() -> None:
    result = SubmissionMapper().map(_data(), overrides={"submission_id": "X"})

    assert result.status is MappingStatus.INVALID
    assert result.submission is None


def test_non_cyber_submission_is_not_applicable() -> None:
    result = SubmissionMapper().map(
        _data(
            product_line="commercial_property", requested_coverages=["property_damage"]
        )
    )

    assert result.status is MappingStatus.NOT_APPLICABLE
    assert result.submission is None


def test_unknown_claims_history_stays_unknown() -> None:
    result = SubmissionMapper().map(_data(claims_history_status="not_provided"))

    assert result.submission is not None
    assert result.submission.prior_cyber_claims is None


def test_counts_only_cyber_claims() -> None:
    claims = [
        {"claim_type": "cyber_incident", "year": 2024, "amount_cad": 1000},
        {"claim_type": "fire", "year": 2023, "amount_cad": 5000},
    ]
    result = SubmissionMapper().map(
        _data(claims_history=claims, claims_history_status="losses_reported")
    )

    assert result.submission is not None
    assert result.submission.prior_cyber_claims == 1


def test_non_canadian_province_does_not_infer_country() -> None:
    result = SubmissionMapper().map(_data(location_province="TX"))

    assert result.submission is not None
    assert result.submission.country is None
