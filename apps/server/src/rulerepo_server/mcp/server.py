"""MCP server setup — creates the FastMCP server with all tools, resources, and prompts.

Per CLAUDE_ENHANCE.md §2.3: reuses existing services. The MCP server
is a thin adapter layer, not a parallel implementation.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all tools and resources.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP(
        "Rule Repository",
        description=(
            "Search, evaluate, and manage natural-language rules — "
            "laws, contracts, policies, engineering guidelines. "
            "Use these tools to check compliance, find applicable rules, "
            "and understand rule relationships."
        ),
    )

    # Register tools, resources, and prompts
    from rulerepo_server.mcp.prompts import register_prompts
    from rulerepo_server.mcp.resources import register_resources
    from rulerepo_server.mcp.tools import register_tools

    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    logger.info("mcp_server_created", tools=len(mcp._tool_manager._tools))
    return mcp
