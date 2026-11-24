from underwriting_agent.domain.portfolio_context import (
    PortfolioContext,
    PortfolioContextStatus,
)
from underwriting_agent.domain.submission import InsuranceSubmission


class NoOpPortfolioAnalyst:
    def get_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> PortfolioContext:
        return PortfolioContext(status=PortfolioContextStatus.NOT_REQUESTED)
