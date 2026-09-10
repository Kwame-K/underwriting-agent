from underwriting_agent.domain.enums import ProductLine
from underwriting_agent.rules.policy_loader import load_underwriting_policy


def test_default_underwriting_policy_is_loaded() -> None:
    policy = load_underwriting_policy()

    assert policy.policy_name == "Cyber SME Underwriting Policy"
    assert policy.policy_version == "0.2.0"
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
