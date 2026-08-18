#!/usr/bin/env python3
"""EQEmu MCP server entry point."""

from __future__ import annotations

import argparse
import os
import secrets
from collections.abc import Sequence

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from eqemu_mcp import (
    __version__,
    development,
    tools_database,
    tools_docs,
    tools_entities,
    tools_lookup,
    tools_quest_api,
    tools_quests,
    tools_server,
    tools_source,
)
from eqemu_mcp.config import ACCESS_MODE, MCP_TOKEN, is_writable
from eqemu_mcp.mcp_server import EQEmuMCPServer


def _server_instructions() -> str:
    mode = "read-write" if is_writable() else "read-only"
    instructions = (
        f"EQEmu MCP server ({mode} mode) for managing EverQuest Emulator servers. "
        "Search C++ source and quest scripts, browse quest APIs and official documentation, "
        "inspect database schema, investigate game entities, and read server logs and config."
    )
    if is_writable():
        instructions += (
            " Write tools are enabled for quests, NPCs, spawns, loot, merchants, "
            "server rules, content flags, data buckets, and SQL mutations."
        )
    return instructions


mcp = EQEmuMCPServer(
    "eqemu",
    title="EQEmu MCP Server",
    description="Development and administration tools for EverQuest Emulator servers.",
    instructions=_server_instructions(),
    version=__version__,
)

# Read-only tools are always available.
tools_source.register(mcp)
development.register(mcp)
tools_quest_api.register(mcp)
tools_quests.register(mcp)
tools_server.register(mcp)
tools_database.register(mcp)
tools_entities.register(mcp)
tools_docs.register(mcp)
tools_lookup.register(mcp)

# Mutating tools are opt-in.
if is_writable():
    from eqemu_mcp import tools_entities_write

    tools_quests.register_write(mcp)
    tools_server.register_write(mcp)
    tools_database.register_write(mcp)
    tools_entities_write.register_write(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> Response:
    """Lightweight unauthenticated health endpoint for container probes."""
    return JSONResponse({"status": "ok", "service": "eqemu-mcp", "version": __version__, "mode": ACCESS_MODE})


class TokenAuthMiddleware:
    """Protect MCP transport routes with the configured static bearer token."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") != "/health":
            request = Request(scope)
            supplied = request.query_params.get("token", "")
            if not supplied:
                authorization = request.headers.get("authorization", "")
                if authorization.lower().startswith("bearer "):
                    supplied = authorization[7:]
            if not supplied or not secrets.compare_digest(supplied, self.token):
                response = JSONResponse({"error": "Unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _csv_env(name: str) -> list[str]:
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


def _transport_security() -> TransportSecuritySettings:
    """Enable host/origin checks when an explicit deployment allowlist is configured."""
    allowed_hosts = _csv_env("EQEMU_MCP_ALLOWED_HOSTS")
    if not allowed_hosts:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=_csv_env("EQEMU_MCP_ALLOWED_ORIGINS"),
    )


def _network_app(transport: str, host: str) -> ASGIApp:
    security = _transport_security()
    if transport == "streamable-http":
        app: ASGIApp = mcp.streamable_http_app(
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
            transport_security=security,
            host=host,
        )
    else:
        app = mcp.sse_app(transport_security=security, host=host)
    return TokenAuthMiddleware(app, MCP_TOKEN) if MCP_TOKEN else app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the EQEmu MCP server")
    transports = parser.add_mutually_exclusive_group()
    transports.add_argument(
        "--http",
        nargs="?",
        const=8888,
        type=int,
        metavar="PORT",
        help="run Streamable HTTP on PORT (default: 8888)",
    )
    transports.add_argument(
        "--sse",
        nargs="?",
        const=8888,
        type=int,
        metavar="PORT",
        help="run legacy HTTP+SSE on PORT (default: 8888)",
    )
    parser.add_argument("--host", default=os.environ.get("EQEMU_MCP_HOST", "0.0.0.0"))
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.http is None and args.sse is None:
        mcp.run("stdio")
        return

    transport = "streamable-http" if args.http is not None else "sse"
    port = args.http if args.http is not None else args.sse
    auth = "token" if MCP_TOKEN else "none"
    endpoint = "/mcp" if transport == "streamable-http" else "/sse"
    print(
        f"EQEmu MCP Server v{__version__} — mode: {ACCESS_MODE}, transport: {transport}, "
        f"auth: {auth}, endpoint: http://{args.host}:{port}{endpoint}"
    )
    uvicorn.run(_network_app(transport, args.host), host=args.host, port=port)


if __name__ == "__main__":
    main()
