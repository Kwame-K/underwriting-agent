import pytest
from pydantic import ValidationError

from underwriting_agent.domain.enums import ProductLine
from underwriting_agent.domain.policy import UnderwritingPolicy
from underwriting_agent.rules.policy_loader import load_underwriting_policy


def test_default_underwriting_policy_is_loaded() -> None:
    policy = load_underwriting_policy()

    assert policy.policy_name == "Cyber SME Underwriting Policy"
    assert policy.policy_version == "0.5.0"
    assert policy.product_line == ProductLine.CYBER_SME
    assert policy.supported_countries == ("Canada",)
    assert "gambling" in policy.excluded_industries


def test_default_policy_has_expected_authority_limits() -> None:
    policy = load_underwriting_policy()

    assert policy.authority.max_automated_limit_cad == 2_000_000
    assert policy.authority.max_automated_revenue_cad == 50_000_000
    assert policy.authority.max_automated_prior_claims == 1


def test_default_policy_requires_mfa_for_automated_underwriting() -> None:
    policy = load_underwriting_policy()

    assert policy.security_controls.mfa_required_for_automated_underwriting is True


def test_default_policy_contains_condition_templates() -> None:
    policy = load_underwriting_policy()

    assert policy.conditions.mfa_not_enabled.condition_id == "COND-001"
    assert policy.conditions.enhanced_security_review.category == "SECURITY_REVIEW"


def test_default_policy_has_documented_security_thresholds() -> None:
    policy = load_underwriting_policy()

    assert policy.security_controls.mfa_requirement_revenue_threshold_cad == 5_000_000
    assert (
        policy.security_controls.backup_requirement_revenue_threshold_cad == 5_000_000
    )
    assert policy.security_controls.edr_requirement_revenue_threshold_cad == 10_000_000


def test_default_policy_loads_aliases_for_excluded_industries() -> None:
    policy = load_underwriting_policy()

    assert "casino" in policy.excluded_industry_aliases["gambling"]
    assert set(policy.excluded_industry_aliases) <= set(policy.excluded_industries)


def test_alias_for_unknown_industry_is_rejected() -> None:
    raw = load_underwriting_policy().model_dump()
    raw["excluded_industry_aliases"] = {"unknown industry": ["something"]}

    with pytest.raises(ValidationError, match="not listed in excluded_industries"):
        UnderwritingPolicy.model_validate(raw)
