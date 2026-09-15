import logging

import httpx2
from pydantic import ValidationError

from underwriting_agent.integrations.submission_extractor.models import (
    SubmissionExtractionRequest,
    SubmissionExtractionResponse,
)
from underwriting_agent.integrations.submission_extractor.port import (
    SubmissionExtractorPort,
)
from underwriting_agent.settings import Settings, get_settings

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class SubmissionExtractorUnavailableError(RuntimeError):
    """Raised when Project 1 cannot provide a valid extraction response."""


class HTTPSubmissionExtractor(SubmissionExtractorPort):
    """HTTP adapter for the Insurance Submission Extractor API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def extract(
        self,
        request: SubmissionExtractionRequest,
        correlation_id: str,
    ) -> SubmissionExtractionResponse:
        try:
            with httpx2.Client(
                base_url=self.settings.submission_extractor_base_url,
                timeout=self.settings.submission_extractor_timeout_seconds,
            ) as client:
                response = client.post(
                    "/v1/extract-submission",
                    json=request.model_dump(mode="json"),
                    headers={CORRELATION_ID_HEADER: correlation_id},
                )
                response.raise_for_status()

            response_data: object = response.json()

            return SubmissionExtractionResponse.model_validate(response_data)

        except (httpx2.HTTPError, ValidationError, ValueError) as error:
            logger.warning(
                "Submission Extractor failed for source %s, correlation %s: %s",
                request.source_id,
                correlation_id,
                error,
            )
            raise SubmissionExtractorUnavailableError(
                "Insurance Submission Extractor is unavailable or returned "
                "an invalid response."
            ) from error
