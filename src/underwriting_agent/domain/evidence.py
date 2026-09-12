from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EvidenceRetrievalStatus(StrEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceCitation(BaseModel):
    citation_id: str = Field(min_length=1)

    source_document_id: str = Field(min_length=1)
    source_document_title: str = Field(min_length=1)
    section_reference: str | None = None

    excerpt: str = Field(min_length=1)
    relevance_score: float = Field(ge=0, le=1)

    supported_finding_id: str = Field(min_length=1)
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


class EvidenceRetrievalResult(BaseModel):
    status: EvidenceRetrievalStatus
    citations: list[EvidenceCitation] = Field(default_factory=list)
    unresolved_finding_ids: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
