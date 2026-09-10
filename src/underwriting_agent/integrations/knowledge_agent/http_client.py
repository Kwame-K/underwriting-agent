import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

import httpx2

from underwriting_agent.domain.evidence import EvidenceCitation
from underwriting_agent.domain.risk_score import RiskScore
from underwriting_agent.domain.rules import RuleResult
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class HTTPInsuranceKnowledgeAgent:
    """HTTP adapter for the Insurance Knowledge Agent API."""

    rule_queries: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "UW-CYB-001": (
                "What territories are supported for cyber insurance underwriting?"
            ),
            "UW-CYB-002": (
                "What industries are excluded from cyber insurance underwriting appetite?"
            ),
            "UW-CYB-003": (
                "What are the multi-factor authentication requirements for cyber "
                "insurance underwriting?"
            ),
            "UW-CYB-004": (
                "What are the referral criteria for requested cyber insurance limits?"
            ),
            "UW-CYB-005": (
                "What prior cyber claims require referral to an underwriter?"
            ),
            "UW-CYB-006": (
                "What revenue thresholds require referral for cyber insurance underwriting?"
            ),
        }
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def retrieve_evidence(
        self,
        submission: InsuranceSubmission,
        failed_rules: list[RuleResult],
        risk_score: RiskScore | None,
    ) -> list[EvidenceCitation]:
        if not failed_rules:
            return []

        payload = self._build_payload(
            submission=submission,
            failed_rules=failed_rules,
        )

        try:
            with httpx2.Client(
                base_url=self.settings.knowledge_agent_base_url,
                timeout=self.settings.knowledge_agent_timeout_seconds,
            ) as client:
                response = client.post(
                    "/v1/retrieve-evidence",
                    json=payload,
                )
                response.raise_for_status()

        except httpx2.HTTPError as error:
            logger.warning(
                "Knowledge Agent retrieval failed for submission %s: %s",
                submission.submission_id,
                error,
            )
            return []

        response_data: dict[str, object] = response.json()

        raw_citations = response_data.get("citations", [])

        if not isinstance(raw_citations, list):
            logger.warning(
                "Knowledge Agent returned an invalid citations payload for %s.",
                submission.submission_id,
            )
            return []

        return [
            EvidenceCitation.model_validate(citation)
            for citation in raw_citations
            if isinstance(citation, dict)
        ]

    def _build_payload(
        self,
        submission: InsuranceSubmission,
        failed_rules: list[RuleResult],
    ) -> dict[str, object]:
        queries = [
            {
                "supported_finding_id": rule.rule_id,
                "query": self.rule_queries.get(
                    rule.rule_id,
                    f"What insurance underwriting guidance applies to: {rule.message}",
                ),
            }
            for rule in failed_rules
        ]

        return {
            "request_id": f"UW-EVIDENCE-{submission.submission_id}",
            "top_k": 3,
            "queries": queries,
        }
