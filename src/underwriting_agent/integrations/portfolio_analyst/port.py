from typing import Protocol

from underwriting_agent.domain.portfolio_context import PortfolioContext
from underwriting_agent.domain.submission import InsuranceSubmission


class PortfolioAnalystPort(Protocol):
    def get_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> PortfolioContext:
        """Return portfolio context. Must never raise."""
