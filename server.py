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

from eqemu_mcp.config import ACCESS_MODE, is_writable
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
        # Set host/port via environment (FastMCP reads these)
        os.environ.setdefault("FASTMCP_PORT", str(port))
        os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
        # Also set directly on settings object
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        mcp.run()
