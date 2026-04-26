"""MCP Server — exposes Rule Repository as tools for AI agents.

Per CLAUDE_ENHANCE.md §2: The MCP layer is an adapter. Every tool
implementation calls into services/ — the same code path used by the REST API.
"""

from __future__ import annotations

import asyncio
import os


def main() -> None:
    """CLI entrypoint for the MCP server.

    Starts the MCP server with the transport configured via MCP_TRANSPORT env var.
    Default is stdio for local agent integration (e.g., Claude Code).
    """
    asyncio.run(_run())


async def _run() -> None:
    from rulerepo_server.mcp.server import create_mcp_server

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp_server = create_mcp_server()

    if transport == "streamable-http":
        port = int(os.environ.get("MCP_PORT", "8001"))
        # Use streamable HTTP for remote agents
        from mcp.server.streamable_http import StreamableHTTPServer

        async with StreamableHTTPServer(mcp_server, host="0.0.0.0", port=port) as server:
            await server.serve_forever()
    else:
        # Default: stdio for local agents (Claude Code, etc.)
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(read_stream, write_stream)
