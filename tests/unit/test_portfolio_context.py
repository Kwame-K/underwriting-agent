import httpx2
import pytest

from underwriting_agent.application.underwriting_service import UnderwritingService
from underwriting_agent.domain.portfolio_context import (
    PortfolioContext,
    PortfolioContextStatus,
)
from underwriting_agent.domain.submission import InsuranceSubmission
from underwriting_agent.integrations.portfolio_analyst.http_client import (
    HTTPPortfolioAnalyst,
)
from underwriting_agent.settings import Settings


def build_submission() -> InsuranceSubmission:
    return InsuranceSubmission(
        submission_id="SUB-UW-002",
        applicant_name="Acme Distribution Inc.",
        country="Canada",
        industry="Wholesale distribution",
        annual_revenue_cad=12_500_000,
        employee_count=85,
        mfa_enabled=True,
        prior_cyber_claims=0,
        requested_limit_cad=1_000_000,
        requested_retention_cad=25_000,
    )


class FakePortfolioAnalyst:
    def get_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> PortfolioContext:
        return PortfolioContext(
            status=PortfolioContextStatus.SUCCESS,
            loss_ratio=0.95,
            claim_frequency=0.4,
        )


class RaisingPortfolioAnalyst:
    def get_portfolio_context(
        self, submission: InsuranceSubmission
    ) -> PortfolioContext:
        raise RuntimeError("boom")


def test_portfolio_context_is_not_requested_by_default() -> None:
    decision = UnderwritingService().underwrite(build_submission())
    assert decision.portfolio_context.status == PortfolioContextStatus.NOT_REQUESTED


def test_portfolio_context_does_not_change_decision_or_score() -> None:
    submission = build_submission()
    baseline = UnderwritingService().underwrite(submission)
    enriched = UnderwritingService(portfolio_analyst=FakePortfolioAnalyst()).underwrite(
        submission
    )
    assert enriched.portfolio_context.status == PortfolioContextStatus.SUCCESS
    exclude = {"decision_id", "created_at", "portfolio_context"}
    assert enriched.model_dump(exclude=exclude) == baseline.model_dump(exclude=exclude)


def test_portfolio_analyst_failure_does_not_block_decision() -> None:
    submission = build_submission()
    baseline = UnderwritingService().underwrite(submission)
    decision = UnderwritingService(
        portfolio_analyst=RaisingPortfolioAnalyst()
    ).underwrite(submission)
    assert decision.portfolio_context.status == PortfolioContextStatus.UNAVAILABLE
    assert decision.decision == baseline.decision
    assert decision.risk_score == baseline.risk_score


def test_http_client_returns_unavailable_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise httpx2.ConnectError("down")

    monkeypatch.setattr(httpx2.Client, "post", fail)
    client = HTTPPortfolioAnalyst(Settings())
    context = client.get_portfolio_context(build_submission())
    assert context.status == PortfolioContextStatus.UNAVAILABLE
    assert context.failure_reason


def _mock_post(
    monkeypatch: pytest.MonkeyPatch, body: object, status: int = 200
) -> list[dict]:
    sent: list[dict] = []

    def fake_post(self: object, url: str, json: dict) -> httpx2.Response:
        sent.append({"url": url, "json": json})
        return httpx2.Response(
            status, json=body, request=httpx2.Request("POST", "http://test" + url)
        )

    monkeypatch.setattr(httpx2.Client, "post", fake_post)
    return sent


def _province() -> str:
    raw = build_submission().province
    return str(getattr(raw, "value", raw))


def test_http_client_sends_project2_contract_and_parses_province_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = {
        "status": "success",
        "data": {
            "raw_results": [
                {"province": "ZZ", "loss_ratio": 9.9},
                {
                    "province": _province(),
                    "loss_ratio": 0.61,
                    "claim_frequency": 0.12,
                    "average_severity": 25000.0,
                    "premium_per_exposure_unit": 1800.0,
                    "share_of_policies_with_claims": 0.08,
                    "policy_count": 420,
                },
            ]
        },
    }
    sent = _mock_post(monkeypatch, body)
    context = HTTPPortfolioAnalyst(Settings()).get_portfolio_context(build_submission())
    assert sent[0]["url"] == "/v1/portfolio-quality-metrics"
    assert sent[0]["json"]["arguments"]["dimensions"] == ["province"]
    assert context.status == PortfolioContextStatus.SUCCESS
    assert context.loss_ratio == 0.61
    assert context.policy_count == 420


def test_http_client_unavailable_when_province_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_post(monkeypatch, {"data": {"raw_results": [{"province": "ZZ"}]}})
    context = HTTPPortfolioAnalyst(Settings()).get_portfolio_context(build_submission())
    assert context.status == PortfolioContextStatus.UNAVAILABLE


def test_http_client_unavailable_on_422_and_bad_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_post(monkeypatch, {"error": "x"}, status=422)
    client = HTTPPortfolioAnalyst(Settings())
    assert client.get_portfolio_context(build_submission()).status == (
        PortfolioContextStatus.UNAVAILABLE
    )
    _mock_post(monkeypatch, {"unexpected": True})
    assert client.get_portfolio_context(build_submission()).status == (
        PortfolioContextStatus.UNAVAILABLE
    )
