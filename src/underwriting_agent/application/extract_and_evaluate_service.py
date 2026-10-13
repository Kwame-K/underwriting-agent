"""Extract -> map -> evaluate workflow shared by the REST API and MCP server."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from underwriting_agent.application.completeness_service import CompletenessChecker
from underwriting_agent.application.submission_mapper import (
    MappingStatus,
    SubmissionMapper,
)
from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.decision import UnderwritingDecision
from underwriting_agent.domain.enums import DecisionType
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.submission_extractor.http_client import (
    SubmissionExtractorUnavailableError,
)
from underwriting_agent.integrations.submission_extractor.models import (
    ExtractionStatus,
    SubmissionExtractionRequest,
)
from underwriting_agent.integrations.submission_extractor.port import (
    SubmissionExtractorPort,
)


class WorkflowStatus(StrEnum):
    EVALUATED = "EVALUATED"
    PENDING_INFORMATION = "PENDING_INFORMATION"
    EXTRACTION_UNAVAILABLE = "EXTRACTION_UNAVAILABLE"
    UNSUPPORTED_SUBMISSION = "UNSUPPORTED_SUBMISSION"


class ExtractEvaluateResult(BaseModel):
    source_id: str
    correlation_id: str
    workflow_status: WorkflowStatus

    extraction_status: str | None = None
    review_required: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)
    data_quality_flags: list[dict[str, Any]] = Field(default_factory=list)

    inferred_fields: list[str] = Field(default_factory=list)
    overridden_fields: list[str] = Field(default_factory=list)
    mapping_messages: list[str] = Field(default_factory=list)

    submission: InsuranceSubmission | None = None
    decision: UnderwritingDecision | None = None
    persisted: bool = False

    message: str


class DecisionRecorder(Protocol):
    def save_submission_and_decision(
        self,
        submission: InsuranceSubmission,
        decision: UnderwritingDecision,
    ) -> object: ...


class ExtractAndEvaluateService:
    """Evaluate extracted submissions; persist only complete evaluations on request."""

    def __init__(
        self,
        extractor: SubmissionExtractorPort,
        underwriting_service: UnderwritingService,
        recorder: DecisionRecorder | None = None,
        mapper: SubmissionMapper | None = None,
    ) -> None:
        self.extractor = extractor
        self.underwriting_service = underwriting_service
        self.recorder = recorder
        self.mapper = mapper or SubmissionMapper()
        self.completeness_checker = CompletenessChecker()

    def run(
        self,
        request: SubmissionExtractionRequest,
        correlation_id: str,
        overrides: Mapping[str, Any] | None = None,
        persist: bool = False,
    ) -> ExtractEvaluateResult:
        if persist and self.recorder is None:
            raise ValueError("A decision recorder is required to persist a decision.")

        try:
            extraction = self.extractor.extract(
                request=request,
                correlation_id=correlation_id,
            )
        except SubmissionExtractorUnavailableError as error:
            return ExtractEvaluateResult(
                source_id=request.source_id,
                correlation_id=correlation_id,
                workflow_status=WorkflowStatus.EXTRACTION_UNAVAILABLE,
                message=str(error),
            )

        needs_review = (
            extraction.extraction_status is not ExtractionStatus.COMPLETE
            or extraction.review_required
        )
        if needs_review:
            return ExtractEvaluateResult(
                source_id=request.source_id,
                correlation_id=correlation_id,
                workflow_status=WorkflowStatus.PENDING_INFORMATION,
                extraction_status=extraction.extraction_status.value,
                review_required=extraction.review_required,
                missing_fields=extraction.missing_fields,
                ambiguous_fields=extraction.ambiguous_fields,
                data_quality_flags=extraction.data_quality_flags,
                message=(
                    "Extraction requires additional information or human review "
                    "before underwriting."
                ),
            )

        mapping = self.mapper.map(extraction.submission_data, overrides)

        if mapping.status is MappingStatus.NOT_APPLICABLE:
            return ExtractEvaluateResult(
                source_id=request.source_id,
                correlation_id=correlation_id,
                workflow_status=WorkflowStatus.UNSUPPORTED_SUBMISSION,
                extraction_status=extraction.extraction_status.value,
                mapping_messages=mapping.messages,
                message="The submission does not request cyber coverage.",
            )

        if mapping.status is MappingStatus.INVALID or mapping.submission is None:
            return ExtractEvaluateResult(
                source_id=request.source_id,
                correlation_id=correlation_id,
                workflow_status=WorkflowStatus.PENDING_INFORMATION,
                extraction_status=extraction.extraction_status.value,
                mapping_messages=mapping.messages,
                message="The extracted data could not be mapped to a valid submission.",
            )

        submission = mapping.submission
        decision = self.underwriting_service.underwrite(submission)

        common: dict[str, Any] = {
            "source_id": request.source_id,
            "correlation_id": correlation_id,
            "extraction_status": extraction.extraction_status.value,
            "inferred_fields": mapping.inferred_fields,
            "overridden_fields": mapping.overridden_fields,
            "mapping_messages": mapping.messages,
            "submission": submission,
            "decision": decision,
        }

        if decision.decision is DecisionType.NEED_MORE_INFORMATION:
            completeness = self.completeness_checker.check(submission)
            return ExtractEvaluateResult(
                workflow_status=WorkflowStatus.PENDING_INFORMATION,
                missing_fields=completeness.critical_missing_fields,
                message=(
                    "Critical underwriting information is missing; "
                    "the decision was not persisted."
                ),
                **common,
            )

        persisted = False
        if persist and self.recorder is not None:
            self.recorder.save_submission_and_decision(
                submission=submission,
                decision=decision,
            )
            persisted = True

        return ExtractEvaluateResult(
            workflow_status=WorkflowStatus.EVALUATED,
            missing_fields=mapping.missing_fields,
            persisted=persisted,
            message=(
                "Extraction mapped and evaluated; decision persisted."
                if persisted
                else "Extraction mapped and evaluated; decision not persisted."
            ),
            **common,
        )
