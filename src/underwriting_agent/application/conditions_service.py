from underwriting_agent.domain.condition import UnderwritingCondition
from underwriting_agent.domain.enums import RiskBand
from underwriting_agent.domain.policy import ConditionsPolicy
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.submission import InsuranceSubmission


class UnderwritingConditionsRecommender:
    def __init__(self, conditions_policy: ConditionsPolicy) -> None:
        self.conditions_policy = conditions_policy

    def recommend(
        self,
        submission: InsuranceSubmission,
        risk_score: RiskScore,
    ) -> list[UnderwritingCondition]:
        conditions: list[UnderwritingCondition] = []

        if submission.mfa_enabled is False:
            conditions.append(self.conditions_policy.mfa_not_enabled)

        if submission.endpoint_detection_response is not True:
            conditions.append(self.conditions_policy.edr_not_confirmed)

        if submission.offline_backups is not True:
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

    @staticmethod
    def _deduplicate_conditions(
        conditions: list[UnderwritingCondition],
    ) -> list[UnderwritingCondition]:
        unique_conditions: dict[str, UnderwritingCondition] = {}

        for condition in conditions:
            unique_conditions[condition.condition_id] = condition

        return list(unique_conditions.values())
