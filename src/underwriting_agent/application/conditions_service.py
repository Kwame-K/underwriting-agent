from underwriting_agent.domain.condition import UnderwritingCondition
from underwriting_agent.domain.enums import RiskBand
from underwriting_agent.domain.policy import (
    ConditionsPolicy,
    SecurityControlsPolicy,
)
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.submission import InsuranceSubmission


class UnderwritingConditionsRecommender:
    def __init__(
        self,
        conditions_policy: ConditionsPolicy,
        security_controls_policy: SecurityControlsPolicy,
    ) -> None:
        self.conditions_policy = conditions_policy
        self.security_controls_policy = security_controls_policy

    def recommend(
        self,
        submission: InsuranceSubmission,
        risk_score: RiskScore,
    ) -> list[UnderwritingCondition]:
        conditions: list[UnderwritingCondition] = []

        annual_revenue_cad = submission.annual_revenue_cad or 0

        if self._mfa_condition_required(
            submission=submission,
            annual_revenue_cad=annual_revenue_cad,
        ):
            conditions.append(self.conditions_policy.mfa_not_enabled)

        if self._edr_condition_required(
            submission=submission,
            annual_revenue_cad=annual_revenue_cad,
        ):
            conditions.append(self.conditions_policy.edr_not_confirmed)

        if self._backup_condition_required(
            submission=submission,
            annual_revenue_cad=annual_revenue_cad,
        ):
            conditions.append(self.conditions_policy.offline_backups_not_confirmed)

        if submission.handles_payment_card_data is True:
            conditions.append(self.conditions_policy.payment_card_data)

        if (submission.prior_cyber_claims or 0) > 0:
            conditions.append(self.conditions_policy.prior_cyber_claims)

        if risk_score.risk_band in {RiskBand.HIGH, RiskBand.SEVERE}:
            conditions.append(self.conditions_policy.enhanced_security_review)

        if (submission.requested_limit_cad or 0) > 1_000_000:
            conditions.append(self.conditions_policy.high_limit_review)

        return self._deduplicate_conditions(conditions)

    def _mfa_condition_required(
        self,
        submission: InsuranceSubmission,
        annual_revenue_cad: float,
    ) -> bool:
        return (
            submission.mfa_enabled is False
            and annual_revenue_cad
            > self.security_controls_policy.mfa_requirement_revenue_threshold_cad
        )

    def _edr_condition_required(
        self,
        submission: InsuranceSubmission,
        annual_revenue_cad: float,
    ) -> bool:
        return (
            submission.endpoint_detection_response is not True
            and annual_revenue_cad
            > self.security_controls_policy.edr_requirement_revenue_threshold_cad
        )

    def _backup_condition_required(
        self,
        submission: InsuranceSubmission,
        annual_revenue_cad: float,
    ) -> bool:
        return (
            submission.offline_backups is not True
            and annual_revenue_cad
            > self.security_controls_policy.backup_requirement_revenue_threshold_cad
        )

    @staticmethod
    def _deduplicate_conditions(
        conditions: list[UnderwritingCondition],
    ) -> list[UnderwritingCondition]:
        unique_conditions: dict[str, UnderwritingCondition] = {}

        for condition in conditions:
            unique_conditions[condition.condition_id] = condition

        return list(unique_conditions.values())
