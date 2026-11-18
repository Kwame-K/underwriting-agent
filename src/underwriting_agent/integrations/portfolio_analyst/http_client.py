import logging
import re
from typing import Any

import httpx2

from underwriting_agent.domain.portfolio_context import (
    PortfolioContext,
    PortfolioContextStatus,
)
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.portfolio_analyst.port import (
    PortfolioAnalystPort,
)
from underwriting_agent.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class HTTPPortfolioAnalyst(PortfolioAnalystPort):
    """HTTP adapter for POST /v1/portfolio-quality-metrics (Data Analyst Agent).

    The endpoint has no province filter: it is asked for the province dimension
    and the row of the submission province is selected here.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> PortfolioContext:
        province = self._province_code(submission)
        years = list(self.settings.portfolio_analyst_underwriting_years)
        payload = {
            "arguments": {"underwriting_years": years, "dimensions": ["province"]},
            "request_id": re.sub(r"[^A-Za-z0-9._:-]", "-", submission.submission_id)[
                :128
            ],
        }
        try:
            with httpx2.Client(
                base_url=self.settings.portfolio_analyst_base_url,
                timeout=self.settings.portfolio_analyst_timeout_seconds,
            ) as client:
                response = client.post("/v1/portfolio-quality-metrics", json=payload)
                response.raise_for_status()
            rows: list[dict[str, Any]] = response.json()["data"]["raw_results"]
            row = next(
                (
                    r
                    for r in rows
                    if str(r.get("province", "")).upper() == province.upper()
                ),
                None,
            )
            if row is None:
                raise ValueError(f"province {province} not found in portfolio")
            return PortfolioContext(
                status=PortfolioContextStatus.SUCCESS,
                province=province,
                underwriting_years=years,
                loss_ratio=row.get("loss_ratio"),
                claim_frequency=row.get("claim_frequency"),
                average_severity=row.get("average_severity"),
                premium_per_exposure_unit=row.get("premium_per_exposure_unit"),
                share_of_policies_with_claims=row.get("share_of_policies_with_claims"),
                policy_count=row.get("policy_count"),
            )
        except (
            httpx2.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as error:
            logger.warning(
                "Portfolio analyst failed for %s: %s", submission.submission_id, error
            )
            return PortfolioContext(
                status=PortfolioContextStatus.UNAVAILABLE,
                province=province,
                failure_reason=str(error),
            )

    @staticmethod
    def _province_code(submission: InsuranceSubmission) -> str:
        raw = submission.province
        return str(getattr(raw, "value", raw))
