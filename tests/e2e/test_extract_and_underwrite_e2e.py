"""Black-box end-to-end tests against the running platform.

Start the stack first (insurance-agentic-platform):
    docker compose up --build -d
Then run:
    uv run pytest -m e2e -rs -v

The Underwriting Agent API is called over HTTP (default http://127.0.0.1:8002,
override with E2E_API_URL); the real Submission Extractor and its LLM provider
are used. Nothing is persisted. Assertions target stable invariants because a
real LLM may word free-text fields differently.
"""

import json
import os
import urllib.request
from typing import Any

import pytest

pytestmark = pytest.mark.e2e

API_URL = os.environ.get("E2E_API_URL", "http://127.0.0.1:8002")

NORTHLAKE_TEXT = (
    "NorthLake Analytics Inc. is a Montreal-based data consulting firm with "
    "approximately 35 employees and annual revenue of CAD 4,200,000.\n\n"
    "The company is seeking cyber liability coverage. Its office is located in "
    "Montreal, Quebec, postal code H3B 2Y5. No prior cyber incidents were "
    "reported in the submission.\n"
)

CONTROL_OVERRIDES: dict[str, Any] = {
    "mfa_enabled": True,
    "requested_limit_cad": 1_000_000,
    "requested_retention_cad": 25_000,
}


@pytest.fixture(scope="module", autouse=True)
def platform_is_up() -> None:
    try:
        urllib.request.urlopen(f"{API_URL}/health", timeout=3).close()
    except OSError:
        pytest.skip(
            f"Underwriting Agent not reachable at {API_URL}; start the platform with "
            "'docker compose up --build -d' in insurance-agentic-platform."
        )


def _post_extract_and_underwrite(
    body: dict[str, Any], correlation_id: str | None = None
) -> tuple[str | None, dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    if correlation_id is not None:
        headers["X-Correlation-ID"] = correlation_id

    request = urllib.request.Request(
        f"{API_URL}/extract-and-underwrite",
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload: dict[str, Any] = json.loads(response.read())
        return response.headers.get("X-Correlation-ID"), payload


def _body(**extra: Any) -> dict[str, Any]:
    return {
        "source_id": "E2E-NORTHLAKE-001",
        "source_type": "FREE_TEXT",
        "document_name": "cyber_submission.txt",
        "content": NORTHLAKE_TEXT,
        "language": "en",
        **extra,
    }


def test_real_extraction_without_controls_is_pending() -> None:
    correlation_id, payload = _post_extract_and_underwrite(
        _body(), correlation_id="e2e-northlake-0001"
    )

    assert correlation_id == "e2e-northlake-0001"
    assert payload["workflow_status"] == "PENDING_INFORMATION"
    assert payload["decision"]["decision"] == "NEED_MORE_INFORMATION"
    assert "mfa_enabled" in payload["missing_fields"]
    assert payload["persisted"] is False

    submission = payload["submission"]

    assert submission["employee_count"] == 35
    assert submission["annual_revenue_cad"] == 4_200_000
    assert submission["country"] == "Canada"


def test_real_extraction_with_overrides_is_evaluated() -> None:
    _, payload = _post_extract_and_underwrite(_body(overrides=CONTROL_OVERRIDES))

    assert payload["workflow_status"] == "EVALUATED"
    assert payload["decision"]["decision"] not in {"NEED_MORE_INFORMATION", "DECLINE"}
    assert sorted(payload["overridden_fields"]) == sorted(CONTROL_OVERRIDES)
    assert payload["persisted"] is False
