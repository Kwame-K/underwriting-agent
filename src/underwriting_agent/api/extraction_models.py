from typing import Any

from pydantic import BaseModel, Field

from underwriting_agent.application.extract_and_evaluate_service import (
    ExtractEvaluateResult as ExtractAndUnderwriteResponse,
)
from underwriting_agent.application.extract_and_evaluate_service import (
    WorkflowStatus,
)
from underwriting_agent.integrations.submission_extractor.models import (
    SourceType,
)

__all__ = [
    "ExtractAndUnderwriteRequest",
    "ExtractAndUnderwriteResponse",
    "WorkflowStatus",
]


class ExtractAndUnderwriteRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    document_name: str | None = Field(default=None, max_length=512)
    content: str = Field(min_length=1)
    language: str = Field(default="en", min_length=2, max_length=16)

    overrides: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Caller-supplied values for fields the extractor cannot provide, "
            "e.g. mfa_enabled or requested_limit_cad."
        ),
    )
    persist: bool = Field(
        default=False,
        description="Persist the decision when the evaluation is complete.",
    )
