from underwriting_agent.application.conditions_service import (
    UnderwritingConditionsRecommender,
)
from underwriting_agent.domain.enums import RiskBand
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.rules.policy_loader import load_underwriting_policy


def build_submission(**overrides: object) -> InsuranceSubmission:
    data: dict[str, object] = {
        "submission_id": "SUB-CONDITION-001",
        "applicant_name": "Acme Distribution Inc.",
        "country": "Canada",
        "industry": "Wholesale distribution",
        "annual_revenue_cad": 8_000_000,
        "employee_count": 45,
        "handles_personal_data": True,
        "handles_payment_card_data": False,
        "mfa_enabled": True,
        "endpoint_detection_response": True,
        "offline_backups": True,
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


def test_low_risk_submission_requires_no_conditions() -> None:
    policy = load_underwriting_policy()
    recommender = UnderwritingConditionsRecommender(policy.conditions)

    conditions = recommender.recommend(
        submission=build_submission(),
        risk_score=build_risk_score(RiskBand.LOW),
    )

    assert conditions == []


def test_missing_mfa_generates_mfa_condition() -> None:
    policy = load_underwriting_policy()
    recommender = UnderwritingConditionsRecommender(policy.conditions)

    conditions = recommender.recommend(
        submission=build_submission(mfa_enabled=False),
        risk_score=build_risk_score(RiskBand.HIGH),
    )

    condition_ids = [condition.condition_id for condition in conditions]

    assert "COND-001" in condition_ids
    assert "COND-006" in condition_ids


def test_high_risk_submission_generates_expected_conditions() -> None:
    policy = load_underwriting_policy()
    recommender = UnderwritingConditionsRecommender(policy.conditions)

    conditions = recommender.recommend(
        submission=build_submission(
            handles_payment_card_data=True,
            mfa_enabled=False,
            endpoint_detection_response=False,
            offline_backups=False,
            prior_cyber_claims=2,
            requested_limit_cad=2_000_000,
        ),
        risk_score=build_risk_score(RiskBand.SEVERE),
    )

    condition_ids = {condition.condition_id for condition in conditions}

    assert condition_ids == {
        "COND-001",
        "COND-002",
        "COND-003",
        "COND-004",
        "COND-005",
        "COND-006",
        "COND-007",
    }


def test_duplicate_conditions_are_removed() -> None:
    policy = load_underwriting_policy()
    recommender = UnderwritingConditionsRecommender(policy.conditions)

    conditions = recommender.recommend(
        submission=build_submission(
            mfa_enabled=False,
            endpoint_detection_response=False,
            offline_backups=False,
        ),
        risk_score=build_risk_score(RiskBand.SEVERE),
    )

    condition_ids = [condition.condition_id for condition in conditions]

    assert len(condition_ids) == len(set(condition_ids))
