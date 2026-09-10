from underwriting_agent.application.completeness_service import CompletenessChecker
from underwriting_agent.domain.submission import InsuranceSubmission


def test_complete_submission_has_no_missing_fields() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-COMPLETE-001",
        applicant_name="Acme Distribution Inc.",
        country="Canada",
        province="Quebec",
        industry="Wholesale distribution",
        annual_revenue_cad=12_500_000,
        employee_count=85,
        handles_personal_data=True,
        handles_payment_card_data=True,
        mfa_enabled=True,
        endpoint_detection_response=True,
        offline_backups=True,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    result = CompletenessChecker().check(submission)

    assert result.is_complete is True
    assert result.critical_missing_fields == []
    assert result.non_critical_missing_fields == []
    assert result.all_missing_fields == []


def test_submission_with_critical_fields_missing_is_incomplete() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-INCOMPLETE-001",
        applicant_name="NorthStar Retail Inc.",
        country="Canada",
        industry="Retail",
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    result = CompletenessChecker().check(submission)

    assert result.is_complete is False
    assert result.critical_missing_fields == [
        "annual_revenue_cad",
        "employee_count",
        "mfa_enabled",
        "prior_cyber_claims",
    ]
    assert result.non_critical_missing_fields == [
        "province",
        "handles_personal_data",
        "handles_payment_card_data",
        "endpoint_detection_response",
        "offline_backups",
    ]


def test_submission_with_only_non_critical_fields_missing_is_complete() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-MINIMAL-001",
        applicant_name="Maple Tech Services Inc.",
        country="Canada",
        industry="Technology services",
        annual_revenue_cad=4_000_000,
        employee_count=24,
        mfa_enabled=True,
        prior_cyber_claims=0,
        requested_limit_cad=500_000,
        requested_retention_cad=10_000,
    )

    result = CompletenessChecker().check(submission)

    assert result.is_complete is True
    assert result.critical_missing_fields == []
    assert result.non_critical_missing_fields == [
        "province",
        "handles_personal_data",
        "handles_payment_card_data",
        "endpoint_detection_response",
        "offline_backups",
    ]


def test_zero_values_are_not_considered_missing() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-ZERO-001",
        applicant_name="Startup Inc.",
        country="Canada",
        industry="Software development",
        annual_revenue_cad=0,
        employee_count=0,
        mfa_enabled=False,
        prior_cyber_claims=0,
        requested_limit_cad=100_000,
        requested_retention_cad=1_000,
    )

    result = CompletenessChecker().check(submission)

    assert result.is_complete is True
    assert result.critical_missing_fields == []
