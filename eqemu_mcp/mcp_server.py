"""Project-specific MCP server defaults."""

from typing import Any

from mcp.server import MCPServer

from .annotations import READ_ONLY


class EQEmuMCPServer(MCPServer):
    """MCPServer that marks tools read-only unless registration says otherwise."""

    def tool(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("annotations", READ_ONLY)
        return super().tool(*args, **kwargs)
