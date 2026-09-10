from underwriting_agent.domain.rules import RuleSeverity
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.rules.engine import UnderwritingRulesEngine


def build_submission(**overrides: object) -> InsuranceSubmission:
    data: dict[str, object] = {
        "submission_id": "SUB-RULE-001",
        "applicant_name": "Acme Distribution Inc.",
        "country": "Canada",
        "industry": "Wholesale distribution",
        "annual_revenue_cad": 12_500_000,
        "employee_count": 85,
        "mfa_enabled": True,
        "prior_cyber_claims": 0,
        "requested_limit_cad": 1_000_000,
        "requested_retention_cad": 25_000,
    }
    data.update(overrides)

    return InsuranceSubmission.model_validate(data)


def test_eligible_submission_passes_all_rules() -> None:
    results = UnderwritingRulesEngine().evaluate(build_submission())

    assert len(results) == 6
    assert all(rule.passed for rule in results)


def test_non_canadian_submission_fails_decline_rule() -> None:
    results = UnderwritingRulesEngine().evaluate(
        build_submission(country="United States")
    )

    country_rule = results[0]

    assert country_rule.rule_id == "UW-CYB-001"
    assert country_rule.passed is False
    assert country_rule.severity == RuleSeverity.DECLINE


def test_excluded_industry_fails_decline_rule() -> None:
    results = UnderwritingRulesEngine().evaluate(build_submission(industry="Gambling"))

    industry_rule = results[1]

    assert industry_rule.rule_id == "UW-CYB-002"
    assert industry_rule.passed is False
    assert industry_rule.severity == RuleSeverity.DECLINE


def test_missing_mfa_fails_referral_rule() -> None:
    results = UnderwritingRulesEngine().evaluate(build_submission(mfa_enabled=False))

    mfa_rule = results[2]

    assert mfa_rule.rule_id == "UW-CYB-003"
    assert mfa_rule.passed is False
    assert mfa_rule.severity == RuleSeverity.REFERRAL


def test_limit_above_authority_fails_referral_rule() -> None:
    results = UnderwritingRulesEngine().evaluate(
        build_submission(requested_limit_cad=2_500_000)
    )

    limit_rule = results[3]

    assert limit_rule.rule_id == "UW-CYB-004"
    assert limit_rule.passed is False
    assert limit_rule.severity == RuleSeverity.REFERRAL
