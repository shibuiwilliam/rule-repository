"""MCP Server — exposes Rule Repository as tools for AI agents.

The MCP layer is an adapter. Every tool implementation calls into
services/ — the same code path used by the REST API.
"""

from __future__ import annotations

import os


def main() -> None:
    """CLI entrypoint for the MCP server.

    Starts the MCP server with the transport configured via MCP_TRANSPORT env var.
    Default is stdio for local agent integration (e.g., Claude Code).
    Set MCP_TRANSPORT=sse for HTTP-based server-sent events transport.
    """
    from rulerepo_server.mcp.server import create_mcp_server

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp_server = create_mcp_server()

    if transport in ("streamable-http", "sse"):
        port = int(os.environ.get("MCP_PORT", "8001"))
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        mcp_server.settings.host = host
        mcp_server.settings.port = port
        mcp_server.run(transport="sse")
    else:
        mcp_server.run(transport="stdio")
