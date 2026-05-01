#!/bin/bash
# Start the EQEmu MCP server
# Usage:
#   ./start.sh                   — stdio transport (for Claude Desktop, Cursor)
#   ./start.sh --sse [PORT]      — SSE transport (for remote/network access)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${EQEMU_MCP_VENV:-$SCRIPT_DIR/../eqemu-mcp-venv}"

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Activate venv
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

echo "EQEmu MCP Server — mode: ${EQEMU_ACCESS_MODE:-read}"

if [ "$1" = "--sse" ]; then
    PORT="${2:-8888}"
    echo "Starting SSE transport on port $PORT..."
    exec python "$SCRIPT_DIR/server.py" --sse "$PORT"
else
    exec python "$SCRIPT_DIR/server.py"
fi
