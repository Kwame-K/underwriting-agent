from underwriting_agent.domain.policy import UnderwritingPolicy
from underwriting_agent.domain.rules import RuleResult, RuleSeverity
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.rules.policy_loader import load_underwriting_policy


class UnderwritingRulesEngine:
    def __init__(self, policy: UnderwritingPolicy | None = None) -> None:
        self.policy = policy or load_underwriting_policy()

    def evaluate(self, submission: InsuranceSubmission) -> list[RuleResult]:
        return [
            self._evaluate_country(submission),
            self._evaluate_industry(submission),
            self._evaluate_mfa(submission),
            self._evaluate_requested_limit(submission),
            self._evaluate_prior_claims(submission),
            self._evaluate_revenue(submission),
        ]

    def _evaluate_country(self, submission: InsuranceSubmission) -> RuleResult:
        normalized_country = (submission.country or "").strip().lower()

        supported_countries = {
            country.strip().lower() for country in self.policy.supported_countries
        }
        is_supported_country = normalized_country in supported_countries

        return RuleResult(
            rule_id="UW-CYB-001",
            rule_name="Supported territory requirement",
            passed=is_supported_country,
            severity=RuleSeverity.DECLINE,
            message=(
                "The applicant is domiciled in a supported territory."
                if is_supported_country
                else "The applicant is outside the supported underwriting territory."
            ),
        )

    def _evaluate_industry(self, submission: InsuranceSubmission) -> RuleResult:
        normalized_industry = (submission.industry or "").strip().lower()

        excluded_industries = {
            industry.strip().lower() for industry in self.policy.excluded_industries
        }
        is_excluded = normalized_industry in excluded_industries

        return RuleResult(
            rule_id="UW-CYB-002",
            rule_name="Excluded industry screening",
            passed=not is_excluded,
            severity=RuleSeverity.DECLINE,
            message=(
                "The applicant industry is within the current underwriting appetite."
                if not is_excluded
                else "The applicant industry is explicitly excluded from underwriting appetite."
            ),
        )

    def _evaluate_mfa(self, submission: InsuranceSubmission) -> RuleResult:
        mfa_required = (
            self.policy.security_controls.mfa_required_for_automated_underwriting
        )
        mfa_enabled = submission.mfa_enabled is True
        passed = not mfa_required or mfa_enabled

        return RuleResult(
            rule_id="UW-CYB-003",
            rule_name="Multi-factor authentication requirement",
            passed=passed,
            severity=RuleSeverity.REFERRAL,
            message=(
                "Multi-factor authentication is enabled."
                if passed
                else "Multi-factor authentication is not enabled and requires human review."
            ),
        )

    def _evaluate_requested_limit(
        self,
        submission: InsuranceSubmission,
    ) -> RuleResult:
        requested_limit_cad = submission.requested_limit_cad or 0
        max_limit_cad = self.policy.authority.max_automated_limit_cad
        is_within_authority = requested_limit_cad <= max_limit_cad

        return RuleResult(
            rule_id="UW-CYB-004",
            rule_name="Automated capacity authority",
            passed=is_within_authority,
            severity=RuleSeverity.REFERRAL,
            message=(
                "The requested limit is within automated underwriting authority."
                if is_within_authority
                else (
                    "The requested limit exceeds the automated underwriting "
                    f"authority of {max_limit_cad:,.0f} CAD."
                )
            ),
        )

    def _evaluate_prior_claims(
        self,
        submission: InsuranceSubmission,
    ) -> RuleResult:
        prior_claims = submission.prior_cyber_claims or 0
        max_prior_claims = self.policy.authority.max_automated_prior_claims
        is_within_claims_tolerance = prior_claims <= max_prior_claims

        return RuleResult(
            rule_id="UW-CYB-005",
            rule_name="Prior cyber claims review",
            passed=is_within_claims_tolerance,
            severity=RuleSeverity.REFERRAL,
            message=(
                "Prior cyber claims are within automated underwriting tolerance."
                if is_within_claims_tolerance
                else (
                    f"The applicant has more than {max_prior_claims} prior cyber "
                    "claim and requires human review."
                )
            ),
        )

    def _evaluate_revenue(self, submission: InsuranceSubmission) -> RuleResult:
        annual_revenue_cad = submission.annual_revenue_cad or 0
        max_revenue_cad = self.policy.authority.max_automated_revenue_cad
        is_within_sme_authority = annual_revenue_cad <= max_revenue_cad

        return RuleResult(
            rule_id="UW-CYB-006",
            rule_name="SME revenue authority",
            passed=is_within_sme_authority,
            severity=RuleSeverity.REFERRAL,
            message=(
                "Annual revenue is within automated SME underwriting authority."
                if is_within_sme_authority
                else (
                    "Annual revenue exceeds the automated SME underwriting "
                    f"authority of {max_revenue_cad:,.0f} CAD."
                )
            ),
        )
