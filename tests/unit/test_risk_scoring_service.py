from underwriting_agent.domain.enums import RiskBand
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.scoring.risk_score import CyberRiskScoringService


def build_submission(**overrides: object) -> InsuranceSubmission:
    data: dict[str, object] = {
        "submission_id": "SUB-SCORE-001",
        "applicant_name": "Maple Tech Services Inc.",
        "country": "Canada",
        "industry": "Technology services",
        "annual_revenue_cad": 500_000,
        "employee_count": 5,
        "handles_personal_data": False,
        "handles_payment_card_data": False,
        "mfa_enabled": True,
        "endpoint_detection_response": True,
        "offline_backups": True,
        "prior_cyber_claims": 0,
        "requested_limit_cad": 250_000,
        "requested_retention_cad": 10_000,
    }
    data.update(overrides)

    return InsuranceSubmission.model_validate(data)


def test_low_risk_submission_has_low_risk_band() -> None:
    result = CyberRiskScoringService().score(build_submission())

    assert result.score == 15
    assert result.risk_band == RiskBand.LOW
    assert result.scoring_model_version == "0.1.0"
    assert len(result.factors) == 10


def test_score_increases_when_mfa_is_not_enabled() -> None:
    service = CyberRiskScoringService()

    score_with_mfa = service.score(build_submission(mfa_enabled=True))
    score_without_mfa = service.score(build_submission(mfa_enabled=False))

    assert score_without_mfa.score == score_with_mfa.score + 30


def test_high_exposure_submission_is_capped_at_100() -> None:
    submission = build_submission(
        annual_revenue_cad=45_000_000,
        employee_count=500,
        handles_personal_data=True,
        handles_payment_card_data=True,
        mfa_enabled=False,
        endpoint_detection_response=False,
        offline_backups=False,
        prior_cyber_claims=4,
        requested_limit_cad=2_000_000,
    )

    result = CyberRiskScoringService().score(submission)

    assert result.score == 100
    assert result.risk_band == RiskBand.SEVERE


def test_two_prior_claims_add_thirty_risk_points() -> None:
    result = CyberRiskScoringService().score(build_submission(prior_cyber_claims=2))

    claims_factor = next(
        factor for factor in result.factors if factor.factor_id == "RSK-009"
    )

    assert claims_factor.points == 30
