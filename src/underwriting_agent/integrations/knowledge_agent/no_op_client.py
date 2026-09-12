from underwriting_agent.domain.evidence import (
    EvidenceRetrievalResult,
    EvidenceRetrievalStatus,
)
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.rules import RuleResult
from underwriting_agent.domain.submission import InsuranceSubmission


class NoOpInsuranceKnowledgeAgent:
    def retrieve_evidence(
        self,
        submission: InsuranceSubmission,
        failed_rules: list[RuleResult],
        risk_score: RiskScore | None,
    ) -> EvidenceRetrievalResult:
        return EvidenceRetrievalResult(
            status=EvidenceRetrievalStatus.NOT_REQUESTED,
        )
