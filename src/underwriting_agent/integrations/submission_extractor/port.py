from typing import Protocol

from underwriting_agent.integrations.submission_extractor.models import (
    SubmissionExtractionRequest,
    SubmissionExtractionResponse,
)


class SubmissionExtractorPort(Protocol):
    """Port used by the underwriting workflow to extract source text."""

    def extract(
        self,
        request: SubmissionExtractionRequest,
        correlation_id: str,
    ) -> SubmissionExtractionResponse:
        """Return a validated response from the extraction service."""
