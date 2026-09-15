from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from underwriting_agent.integrations.submission_extractor.models import (
    SourceType,
)


class ExtractAndUnderwriteRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    document_name: str | None = Field(default=None, max_length=512)
    content: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2, max_length=16)


class WorkflowStatus(StrEnum):
    READY_FOR_UNDERWRITING = "READY_FOR_UNDERWRITING"
    PENDING_INFORMATION = "PENDING_INFORMATION"
    EXTRACTION_UNAVAILABLE = "EXTRACTION_UNAVAILABLE"
    UNSUPPORTED_SUBMISSION = "UNSUPPORTED_SUBMISSION"


class ExtractAndUnderwriteResponse(BaseModel):
    source_id: str
    correlation_id: str
    workflow_status: WorkflowStatus

    extraction_status: str | None = None
    review_required: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)
    data_quality_flags: list[dict[str, Any]] = Field(default_factory=list)

    message: str
