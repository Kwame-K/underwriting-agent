from underwriting_agent.domain.enums import RiskBand
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.rules.policy_loader import load_underwriting_policy
from underwriting_agent.scoring.pricing import CyberPricingIndicationService


def build_submission(**overrides: object) -> InsuranceSubmission:
    data: dict[str, object] = {
        "submission_id": "SUB-PRICING-001",
        "applicant_name": "Acme Distribution Inc.",
        "country": "Canada",
        "industry": "Wholesale distribution",
        "annual_revenue_cad": 8_000_000,
        "employee_count": 45,
        "mfa_enabled": True,
        "prior_cyber_claims": 0,
        "requested_limit_cad": 1_000_000,
        "requested_retention_cad": 25_000,
    }
    data.update(overrides)

    return InsuranceSubmission.model_validate(data)


def build_risk_score(risk_band: RiskBand) -> RiskScore:
    return RiskScore(
        score=50,
        risk_band=risk_band,
        factors=[],
        scoring_model_version="0.1.0",
    )


def test_medium_risk_reference_submission_has_expected_premium() -> None:
    policy = load_underwriting_policy()
    service = CyberPricingIndicationService(policy.pricing)

    result = service.calculate(
        submission=build_submission(),
        risk_score=build_risk_score(RiskBand.MEDIUM),
    )

    assert result.base_exposure_premium_cad == 24_000
    assert result.indicated_premium_cad == 24_000
    assert result.pricing_model_version == "0.1.0"
    assert len(result.factors) == 4


def test_severe_risk_band_increases_premium() -> None:
    policy = load_underwriting_policy()
    service = CyberPricingIndicationService(policy.pricing)

    medium_result = service.calculate(
        submission=build_submission(),
        risk_score=build_risk_score(RiskBand.MEDIUM),
    )
    severe_result = service.calculate(
        submission=build_submission(),
        risk_score=build_risk_score(RiskBand.SEVERE),
    )

    assert severe_result.indicated_premium_cad == 40_800
    assert severe_result.indicated_premium_cad > medium_result.indicated_premium_cad


def test_higher_retention_reduces_indicated_premium() -> None:
    policy = load_underwriting_policy()
    service = CyberPricingIndicationService(policy.pricing)

    low_retention_result = service.calculate(
        submission=build_submission(requested_retention_cad=10_000),
        risk_score=build_risk_score(RiskBand.MEDIUM),
    )
    high_retention_result = service.calculate(
        submission=build_submission(requested_retention_cad=50_000),
        risk_score=build_risk_score(RiskBand.MEDIUM),
    )

    assert (
        high_retention_result.indicated_premium_cad
        < low_retention_result.indicated_premium_cad
    )


def test_minimum_premium_is_applied() -> None:
    policy = load_underwriting_policy()
    service = CyberPricingIndicationService(policy.pricing)

    result = service.calculate(
        submission=build_submission(
            annual_revenue_cad=100_000,
            requested_limit_cad=100_000,
            requested_retention_cad=100_000,
        ),
        risk_score=build_risk_score(RiskBand.LOW),
    )

    assert result.indicated_premium_cad == 2_500
