"""Stdio MCP server exposing underwriting workflow operations."""

import logging
import sys

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from underwriting_agent.mcp_server import tools

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

mcp = MCPServer("underwriting-agent")

_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

_EXTRACT = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)

_SUBMIT = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)

mcp.tool(annotations=_EXTRACT)(tools.extract_submission)
mcp.tool(annotations=_EXTRACT)(tools.extract_and_evaluate)
mcp.tool(annotations=_READ_ONLY)(tools.check_completeness)
mcp.tool(annotations=_READ_ONLY)(tools.evaluate_underwriting)
mcp.tool(annotations=_SUBMIT)(tools.submit_underwriting)
mcp.tool(annotations=_READ_ONLY)(tools.get_decision)
mcp.tool(annotations=_READ_ONLY)(tools.get_audit_trail)
mcp.tool(annotations=_READ_ONLY)(tools.list_pending_reviews)


def main() -> None:
    """Run the MCP server over stdio; stdout is reserved for MCP messages."""
    mcp.run()


if __name__ == "__main__":
    main()
