#!/usr/bin/env python3
"""
EQEmu MCP Server

A comprehensive MCP server for managing and operating EverQuest Emulator servers.
Supports two permission tiers:

  EQEMU_ACCESS_MODE=read       (default) — read-only tools only
  EQEMU_ACCESS_MODE=readwrite  — all tools including database writes, file edits, etc.
"""

from mcp.server.fastmcp import FastMCP

try:
    from mcp.server.transport_security import TransportSecuritySettings
    _security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
except ImportError:
    _security = None

from eqemu_mcp.config import ACCESS_MODE, is_writable, MCP_TOKEN
from eqemu_mcp import (
    tools_source,
    tools_quest_api,
    tools_quests,
    tools_server,
    tools_database,
    tools_entities,
    tools_docs,
    tools_lookup,
)

_mode_desc = "read-only" if not is_writable() else "read-write"

_mcp_kwargs = {}
if _security is not None:
    _mcp_kwargs["transport_security"] = _security

mcp = FastMCP(
    "eqemu",
    **_mcp_kwargs,
    instructions=(
        f"EQEmu MCP server ({_mode_desc} mode) — tools for managing EverQuest "
        f"Emulator servers. Search C++ source code, browse quest APIs, inspect "
        f"database schema, look up NPCs/items/spawns/loot/zones/spells/factions, "
        f"read server logs and config. Search the official EQEmu documentation "
        f"(docs.eqemu.io) including database schema references, quest API docs, "
        f"server operation guides, and more."
        + (
            " Write tools are enabled: edit quests, modify NPCs/spawns/loot, "
            "change server rules and content flags, run write queries."
            if is_writable() else ""
        )
    ),
)

# ----- Read-only tools (always registered) -----
tools_source.register(mcp)
tools_quest_api.register(mcp)
tools_quests.register(mcp)
tools_server.register(mcp)
tools_database.register(mcp)
tools_entities.register(mcp)
tools_docs.register(mcp)
tools_lookup.register(mcp)

# ----- Write tools (only if EQEMU_ACCESS_MODE=readwrite) -----
if is_writable():
    from eqemu_mcp import tools_entities_write

    tools_quests.register_write(mcp)
    tools_server.register_write(mcp)
    tools_database.register_write(mcp)
    tools_entities_write.register_write(mcp)


if __name__ == "__main__":
    import os, sys

    if "--sse" in sys.argv:
        idx = sys.argv.index("--sse")
        port = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 8888

        if MCP_TOKEN:
            # Token auth enabled — wrap the SSE app with middleware
            import uvicorn
            from starlette.middleware import Middleware
            from starlette.requests import Request
            from starlette.responses import JSONResponse
            from starlette.types import ASGIApp, Receive, Scope, Send

            class TokenAuthMiddleware:
                def __init__(self, app: ASGIApp) -> None:
                    self.app = app

                async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                    if scope["type"] == "http":
                        request = Request(scope)
                        token = request.query_params.get("token", "")
                        if not token:
                            auth = request.headers.get("authorization", "")
                            if auth.lower().startswith("bearer "):
                                token = auth[7:]
                        if token != MCP_TOKEN:
                            response = JSONResponse(
                                {"error": "Unauthorized — invalid or missing token"},
                                status_code= 401,
                            )
                            await response(scope, receive, send)
                            return
                    await self.app(scope, receive, send)

            app = mcp.sse_app()
            app = TokenAuthMiddleware(app)
            print(f"EQEmu MCP Server — mode: {ACCESS_MODE}, auth: token, port: {port}")
            uvicorn.run(app, host="0.0.0.0", port=port)
        else:
            # No token — run normally
            os.environ.setdefault("FASTMCP_PORT", str(port))
            os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
            mcp.settings.host = "0.0.0.0"
            mcp.settings.port = port
            print(f"EQEmu MCP Server — mode: {ACCESS_MODE}, auth: none, port: {port}")
            mcp.run(transport="sse")
    else:
        mcp.run()
