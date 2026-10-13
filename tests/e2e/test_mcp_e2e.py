"""End-to-end: launch the MCP server over stdio and call extract_and_evaluate.

Needs the Submission Extractor running (insurance-agentic-platform publishes it
on port 8000):
    uv run pytest -m e2e -k mcp -rs -v
Override the address with E2E_EXTRACTOR_URL. Nothing is persisted.
"""

import asyncio
import json
import os
import sys
import urllib.request
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

pytestmark = pytest.mark.e2e

EXTRACTOR_URL = os.environ.get("E2E_EXTRACTOR_URL", "http://127.0.0.1:8000")

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
def extractor_is_up() -> None:
    try:
        urllib.request.urlopen(f"{EXTRACTOR_URL}/health", timeout=3).close()
    except OSError:
        pytest.skip(
            f"Submission Extractor not reachable at {EXTRACTOR_URL}; start the "
            "platform with 'docker compose up --build -d' in insurance-agentic-platform."
        )


async def _call_tool(url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "underwriting_agent.mcp_server.server"],
        env={
            **os.environ,
            "SUBMISSION_EXTRACTOR_BASE_URL": url,
            "SUBMISSION_EXTRACTOR_TIMEOUT_SECONDS": "90",
        },
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        result = await session.call_tool(name, arguments)

    text = "".join(
        block.text for block in result.content if isinstance(block, TextContent)
    )
    assert not result.is_error, text

    data: dict[str, Any]
    if result.structured_content is not None:
        data = result.structured_content
    else:
        data = json.loads(text)
    if set(data) == {"result"} and isinstance(data["result"], dict):
        data = data["result"]

    return data


def _request() -> dict[str, Any]:
    return {
        "source_id": "E2E-MCP-NORTHLAKE-001",
        "source_type": "FREE_TEXT",
        "document_name": "cyber_submission.txt",
        "content": NORTHLAKE_TEXT,
        "language": "en",
    }


def test_mcp_extract_and_evaluate_without_controls_is_pending() -> None:
    payload = asyncio.run(
        _call_tool(
            EXTRACTOR_URL,
            "extract_and_evaluate",
            {"request": _request(), "correlation_id": "e2e-mcp-0001"},
        )
    )

    assert payload["correlation_id"] == "e2e-mcp-0001"
    assert payload["workflow_status"] == "PENDING_INFORMATION"
    assert payload["decision"]["decision"] == "NEED_MORE_INFORMATION"
    assert "mfa_enabled" in payload["missing_fields"]
    assert payload["persisted"] is False


def test_mcp_extract_and_evaluate_with_overrides_is_evaluated() -> None:
    payload = asyncio.run(
        _call_tool(
            EXTRACTOR_URL,
            "extract_and_evaluate",
            {"request": _request(), "overrides": CONTROL_OVERRIDES},
        )
    )

    assert payload["workflow_status"] == "EVALUATED"
    assert payload["decision"]["decision"] not in {"NEED_MORE_INFORMATION", "DECLINE"}
    assert sorted(payload["overridden_fields"]) == sorted(CONTROL_OVERRIDES)
    assert payload["persisted"] is False
