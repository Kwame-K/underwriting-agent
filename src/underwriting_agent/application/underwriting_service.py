from underwriting_agent.application.completeness_service import CompletenessChecker
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.enums import DecisionType
from underwriting_agent.domain.rules import RuleResult, RuleSeverity
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.rules.engine import UnderwritingRulesEngine
from underwriting_agent.scoring.risk_score import CyberRiskScoringService


class UnderwritingService:
    def __init__(
        self,
        completeness_checker: CompletenessChecker | None = None,
        rules_engine: UnderwritingRulesEngine | None = None,
        risk_scoring_service: CyberRiskScoringService | None = None,
    ) -> None:
        self.completeness_checker = completeness_checker or CompletenessChecker()
        self.rules_engine = rules_engine or UnderwritingRulesEngine()
        self.risk_scoring_service = risk_scoring_service or CyberRiskScoringService()

    def underwrite(self, submission: InsuranceSubmission) -> UnderwritingDecision:
        completeness_result = self.completeness_checker.check(submission)

        if not completeness_result.is_complete:
            return UnderwritingDecision(
                submission_id=submission.submission_id,
                decision=DecisionType.NEED_MORE_INFORMATION,
                human_review_required=False,
                reasons=[
                    "The submission cannot proceed to underwriting because critical information is missing."
                ],
                missing_information=completeness_result.critical_missing_fields,
                policy_version=self._policy_version(),
            )

        rule_results = self.rules_engine.evaluate(submission)

        decline_results = self._failed_rules_by_severity(
            rule_results=rule_results,
            severity=RuleSeverity.DECLINE,
        )
        if decline_results:
            return UnderwritingDecision(
                submission_id=submission.submission_id,
                decision=DecisionType.DECLINE,
                human_review_required=False,
                reasons=[rule.message for rule in decline_results],
                rule_results=rule_results,
                policy_version=self._policy_version(),
            )

        risk_score = self.risk_scoring_service.score(submission)

        referral_results = self._failed_rules_by_severity(
            rule_results=rule_results,
            severity=RuleSeverity.REFERRAL,
        )
        if referral_results:
            return UnderwritingDecision(
                submission_id=submission.submission_id,
                decision=DecisionType.REFER,
                human_review_required=True,
                risk_score=risk_score.score,
                risk_band=risk_score.risk_band,
                risk_factors=risk_score.factors,
                scoring_model_version=risk_score.scoring_model_version,
                reasons=[
                    "The submission requires review by an authorized underwriter."
                ],
                referral_reasons=[rule.message for rule in referral_results],
                rule_results=rule_results,
                policy_version=self._policy_version(),
            )

        return UnderwritingDecision(
            submission_id=submission.submission_id,
            decision=DecisionType.PENDING_UNDERWRITING,
            human_review_required=False,
            risk_score=risk_score.score,
            risk_band=risk_score.risk_band,
            risk_factors=risk_score.factors,
            scoring_model_version=risk_score.scoring_model_version,
            reasons=[
                "The submission satisfies the current eligibility and appetite rules.",
                "Risk scoring is complete and pricing evaluation is pending.",
            ],
            rule_results=rule_results,
            policy_version=self._policy_version(),
        )

    def _policy_version(self) -> str:
        return self.rules_engine.policy.policy_version

    @staticmethod
    def _failed_rules_by_severity(
        rule_results: list[RuleResult],
        severity: RuleSeverity,
    ) -> list[RuleResult]:
        return [
            rule
            for rule in rule_results
            if rule.severity == severity and not rule.passed
        ]
