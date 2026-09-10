from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.enums import DecisionType
from underwriting_agent.domain.submission import InsuranceSubmission


def test_incomplete_submission_requires_more_information() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-UW-001",
        applicant_name="NorthStar Retail Inc.",
        country="Canada",
        industry="Retail",
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    decision = UnderwritingService().underwrite(submission)

    assert decision.decision == DecisionType.NEED_MORE_INFORMATION
    assert decision.human_review_required is False
    assert decision.missing_information == [
        "annual_revenue_cad",
        "employee_count",
        "mfa_enabled",
        "prior_cyber_claims",
    ]


def test_complete_submission_is_ready_for_underwriting() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-UW-002",
        applicant_name="Acme Distribution Inc.",
        country="Canada",
        industry="Wholesale distribution",
        annual_revenue_cad=12_500_000,
        employee_count=85,
        mfa_enabled=True,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    decision = UnderwritingService().underwrite(submission)

    assert decision.decision == DecisionType.PENDING_UNDERWRITING
    assert decision.human_review_required is False
    assert decision.missing_information == []


def test_excluded_industry_is_declined() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-UW-DECLINE-001",
        applicant_name="Gaming Corp.",
        country="Canada",
        industry="Gambling",
        annual_revenue_cad=12_000_000,
        employee_count=60,
        mfa_enabled=True,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    decision = UnderwritingService().underwrite(submission)

    assert decision.decision == DecisionType.DECLINE
    assert decision.human_review_required is False
    assert len(decision.rule_results) == 6
    assert "explicitly excluded" in decision.reasons[0]


def test_submission_without_mfa_is_referred() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-UW-REFER-001",
        applicant_name="Retail Services Inc.",
        country="Canada",
        industry="Retail",
        annual_revenue_cad=8_000_000,
        employee_count=45,
        mfa_enabled=False,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    decision = UnderwritingService().underwrite(submission)

    assert decision.decision == DecisionType.REFER
    assert decision.human_review_required is True
    assert len(decision.referral_reasons) == 1
    assert "Multi-factor authentication is not enabled" in decision.referral_reasons[0]


def test_decline_has_priority_over_referral() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-UW-PRIORITY-001",
        applicant_name="US Gaming Corp.",
        country="United States",
        industry="Gambling",
        annual_revenue_cad=80_000_000,
        employee_count=200,
        mfa_enabled=False,
        prior_cyber_claims=3,
        requested_limit_cad=5_000_000,
        requested_retention_cad=50_000,
    )

    decision = UnderwritingService().underwrite(submission)

    assert decision.decision == DecisionType.DECLINE
    assert decision.human_review_required is False
    assert len(decision.reasons) == 2


def test_referred_submission_contains_risk_score() -> None:
    submission = InsuranceSubmission(
        submission_id="SUB-UW-SCORE-001",
        applicant_name="Retail Services Inc.",
        country="Canada",
        industry="Retail",
        annual_revenue_cad=8_000_000,
        employee_count=45,
        handles_personal_data=True,
        handles_payment_card_data=True,
        mfa_enabled=False,
        endpoint_detection_response=False,
        offline_backups=False,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )

    decision = UnderwritingService().underwrite(submission)

    assert decision.decision == DecisionType.REFER
    assert decision.risk_score is not None
    assert decision.risk_band is not None
    assert decision.scoring_model_version == "0.1.0"
    assert len(decision.risk_factors) == 10
