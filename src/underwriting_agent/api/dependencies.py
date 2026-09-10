from functools import lru_cache

from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.integrations.knowledge_agent.http_client import (
    HTTPInsuranceKnowledgeAgent,
)


@lru_cache
def get_underwriting_service() -> UnderwritingService:
    return UnderwritingService(
        knowledge_agent=HTTPInsuranceKnowledgeAgent(),
    )
