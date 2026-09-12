from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(StrEnum):
    SUBMISSION_PERSISTED = "SUBMISSION_PERSISTED"
    DECISION_CREATED = "DECISION_CREATED"
    DECISION_REVIEW_REQUESTED = "DECISION_REVIEW_REQUESTED"
    UNDERWRITER_APPROVED = "UNDERWRITER_APPROVED"
    UNDERWRITER_MODIFIED = "UNDERWRITER_MODIFIED"
    UNDERWRITER_DECLINED = "UNDERWRITER_DECLINED"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"


class AuditEvent(BaseModel):
    event_id: str = Field(
        default_factory=lambda: f"AUD-{uuid4()}",
    )
    decision_id: str
    event_type: AuditEventType
    event_payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
