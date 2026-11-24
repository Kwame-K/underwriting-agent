from underwriting_agent.application.completeness_service import CompletenessChecker
from underwriting_agent.application.conditions_service import (
    UnderwritingConditionsRecommender,
)
from underwriting_agent.domain.condition import UnderwritingCondition
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.enums import DecisionType
from underwriting_agent.domain.portfolio_context import (
    PortfolioContext,
    PortfolioContextStatus,
)
from underwriting_agent.domain.rules import RuleResult, RuleSeverity
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.knowledge_agent.no_op_client import (
    NoOpInsuranceKnowledgeAgent,
)
from underwriting_agent.integrations.knowledge_agent.port import (
    InsuranceKnowledgeAgentPort,
)
from underwriting_agent.integrations.portfolio_analyst.no_op_client import (
    NoOpPortfolioAnalyst,
)
from underwriting_agent.integrations.portfolio_analyst.port import (
    PortfolioAnalystPort,
)
from underwriting_agent.rules.engine import UnderwritingRulesEngine
from underwriting_agent.scoring.pricing import CyberPricingIndicationService
from underwriting_agent.scoring.risk_score import CyberRiskScoringService


class UnderwritingService:
    def __init__(
        self,
        completeness_checker: CompletenessChecker | None = None,
        rules_engine: UnderwritingRulesEngine | None = None,
        risk_scoring_service: CyberRiskScoringService | None = None,
        pricing_service: CyberPricingIndicationService | None = None,
        conditions_recommender: UnderwritingConditionsRecommender | None = None,
        knowledge_agent: InsuranceKnowledgeAgentPort | None = None,
        portfolio_analyst: PortfolioAnalystPort | None = None,
    ) -> None:
        self.completeness_checker = completeness_checker or CompletenessChecker()
        self.rules_engine = rules_engine or UnderwritingRulesEngine()
        self.risk_scoring_service = risk_scoring_service or CyberRiskScoringService()
        self.pricing_service = pricing_service or CyberPricingIndicationService(
            pricing_policy=self.rules_engine.policy.pricing
        )
        self.conditions_recommender = (
            conditions_recommender
            or UnderwritingConditionsRecommender(
                conditions_policy=self.rules_engine.policy.conditions,
                security_controls_policy=self.rules_engine.policy.security_controls,
            )
        )

        self.knowledge_agent = knowledge_agent or NoOpInsuranceKnowledgeAgent()
        self.portfolio_analyst = portfolio_analyst or NoOpPortfolioAnalyst()

    def underwrite(self, submission: InsuranceSubmission) -> UnderwritingDecision:
        decision = self._underwrite_without_portfolio_context(submission)
        portfolio_context = self._get_portfolio_context(submission)
        return decision.model_copy(update={"portfolio_context": portfolio_context})

    def _get_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> PortfolioContext:
        try:
            return self.portfolio_analyst.get_portfolio_context(submission)
        except Exception as error:  # noqa: BLE001 - context must never block a decision
            return PortfolioContext(
                status=PortfolioContextStatus.UNAVAILABLE,
                failure_reason=str(error),
            )

    def _underwrite_without_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> UnderwritingDecision:
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
        failed_rules = [rule for rule in rule_results if not rule.passed]

        decline_results = self._failed_rules_by_severity(
            rule_results=rule_results,
            severity=RuleSeverity.DECLINE,
        )
        if decline_results:
            evidence_result = self.knowledge_agent.retrieve_evidence(
                submission=submission,
                failed_rules=failed_rules,
                risk_score=None,
            )

            return UnderwritingDecision(
                submission_id=submission.submission_id,
                decision=DecisionType.DECLINE,
                human_review_required=False,
                reasons=[rule.message for rule in decline_results],
                rule_results=rule_results,
                policy_version=self._policy_version(),
                evidence=evidence_result.citations,
                evidence_retrieval_status=evidence_result.status,
                unresolved_evidence_finding_ids=(
                    evidence_result.unresolved_finding_ids
                ),
                evidence_retrieval_failure_reason=(evidence_result.failure_reason),
            )

        risk_score = self.risk_scoring_service.score(submission)
        evidence_result = self.knowledge_agent.retrieve_evidence(
            submission=submission,
            failed_rules=failed_rules,
            risk_score=risk_score,
        )

        pricing_indication = self.pricing_service.calculate(
            submission=submission,
            risk_score=risk_score,
        )
        conditions = self.conditions_recommender.recommend(
            submission=submission,
            risk_score=risk_score,
        )

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
                base_exposure_premium_cad=pricing_indication.base_exposure_premium_cad,
                indicated_premium_cad=pricing_indication.indicated_premium_cad,
                pricing_factors=pricing_indication.factors,
                pricing_model_version=pricing_indication.pricing_model_version,
                conditions=conditions,
                evidence=evidence_result.citations,
                evidence_retrieval_status=evidence_result.status,
                unresolved_evidence_finding_ids=(
                    evidence_result.unresolved_finding_ids
                ),
                evidence_retrieval_failure_reason=(evidence_result.failure_reason),
            )

        decision_type = (
            DecisionType.ACCEPT_WITH_CONDITIONS if conditions else DecisionType.ACCEPT
        )
        reasons = [
            "The submission satisfies the current eligibility and appetite rules."
        ]
        if conditions:
            reasons.append(
                f"Acceptance is subject to {len(conditions)} recommended condition(s)."
            )
        else:
            reasons.append("No additional underwriting condition is required.")

        return UnderwritingDecision(
            submission_id=submission.submission_id,
            decision=decision_type,
            human_review_required=False,
            risk_score=risk_score.score,
            risk_band=risk_score.risk_band,
            risk_factors=risk_score.factors,
            scoring_model_version=risk_score.scoring_model_version,
            reasons=reasons,
            rule_results=rule_results,
            policy_version=self._policy_version(),
            base_exposure_premium_cad=pricing_indication.base_exposure_premium_cad,
            indicated_premium_cad=pricing_indication.indicated_premium_cad,
            pricing_factors=pricing_indication.factors,
            pricing_model_version=pricing_indication.pricing_model_version,
            conditions=conditions,
            evidence=evidence_result.citations,
            evidence_retrieval_status=evidence_result.status,
            unresolved_evidence_finding_ids=(evidence_result.unresolved_finding_ids),
            evidence_retrieval_failure_reason=(evidence_result.failure_reason),
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

    @staticmethod
    def _acceptance_decision(
        conditions: list[UnderwritingCondition],
    ) -> DecisionType:
        if conditions:
            return DecisionType.ACCEPT_WITH_CONDITIONS
        return DecisionType.ACCEPT

    @staticmethod
    def _acceptance_reasons(conditions: list[UnderwritingCondition]) -> list[str]:
        reasons = [
            "The submission satisfies the current eligibility and appetite rules."
        ]
        if conditions:
            reasons.append(
                f"Acceptance is subject to {len(conditions)} recommended condition(s)."
            )
        else:
            reasons.append("No additional underwriting condition is required.")
        return reasons
