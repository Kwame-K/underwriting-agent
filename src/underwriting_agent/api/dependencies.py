from functools import lru_cache

from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.infrastructure.persistence.database import (
    SessionFactory,
    initialize_database,
)
from underwriting_agent.infrastructure.repositories.decision_repository import (
    UnderwritingDecisionRepository,
)
from underwriting_agent.integrations.knowledge_agent.http_client import (
    HTTPInsuranceKnowledgeAgent,
)
from underwriting_agent.integrations.submission_extractor.http_client import (
    HTTPSubmissionExtractor,
)
from underwriting_agent.integrations.submission_extractor.port import (
    SubmissionExtractorPort,
)


@lru_cache
def get_underwriting_service() -> UnderwritingService:
    return UnderwritingService(
        knowledge_agent=HTTPInsuranceKnowledgeAgent(),
    )


@lru_cache
def get_decision_repository() -> UnderwritingDecisionRepository:
    initialize_database()

    return UnderwritingDecisionRepository(
        session_factory=SessionFactory,
    )


@lru_cache
def get_submission_extractor() -> SubmissionExtractorPort:
    return HTTPSubmissionExtractor()
