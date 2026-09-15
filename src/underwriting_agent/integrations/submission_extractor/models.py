from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExtractionStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceType(StrEnum):
    BROKER_EMAIL = "BROKER_EMAIL"
    PDF_TEXT = "PDF_TEXT"
    FREE_TEXT = "FREE_TEXT"
    FORM = "FORM"


class SubmissionExtractionRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    document_name: str | None = Field(default=None, max_length=512)
    content: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2, max_length=16)


class SubmissionExtractionResponse(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    extraction_status: ExtractionStatus

    submission_data: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)

    field_confidence: dict[str, float] = Field(default_factory=dict)
    source_references: list[dict[str, Any]] = Field(default_factory=list)

    data_quality_flags: list[dict[str, Any]] = Field(default_factory=list)
    review_required: bool = False

    provider: str | None = None
    model: str | None = None
    processed_at: datetime | None = None

    extraction_notes: list[str] = Field(default_factory=list)

    error_code: str | None = None
    error_message: str | None = None
