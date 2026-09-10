from datetime import UTC, datetime

from pydantic import BaseModel, Field


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
