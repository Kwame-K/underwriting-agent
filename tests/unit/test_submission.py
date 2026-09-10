import pytest
from pydantic import ValidationError

from underwriting_agent.domain.submission import InsuranceSubmission


def test_valid_submission_is_created() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-001",
        applicant_name="Acme Distribution Inc.",
        industry="Wholesale distribution",
        annual_revenue_cad=12_500_000,
        employee_count=85,
        mfa_enabled=True,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    assert submission.submission_id == "SUB-001"
    assert submission.annual_revenue_cad == 12_500_000
    assert submission.mfa_enabled is True


def test_negative_revenue_is_rejected() -> None:
    with pytest.raises(ValidationError):
        InsuranceSubmission(
            submission_id="SUB-002",
            annual_revenue_cad=-1,
            requested_limit_cad=1_000_000,
        )
