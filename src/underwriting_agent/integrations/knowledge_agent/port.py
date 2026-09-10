from typing import Protocol

from underwriting_agent.domain.evidence import EvidenceCitation
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.rules import RuleResult
from underwriting_agent.domain.submission import InsuranceSubmission


class InsuranceKnowledgeAgentPort(Protocol):
    def retrieve_evidence(
        self,
        submission: InsuranceSubmission,
        failed_rules: list[RuleResult],
        risk_score: RiskScore | None,
    ) -> list[EvidenceCitation]:
        """Retrieve documentary evidence relevant to underwriting findings."""
