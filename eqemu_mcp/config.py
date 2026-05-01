"""Centralised configuration loaded from environment variables."""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Permission mode
# ---------------------------------------------------------------------------
# "read" — only read-only tools are registered
# "readwrite" — both read-only AND write tools are registered
ACCESS_MODE: str = os.environ.get("EQEMU_ACCESS_MODE", "read").lower()


def is_writable() -> bool:
    return ACCESS_MODE == "readwrite"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SOURCE_PATH = Path(os.environ.get("EQEMU_SOURCE_PATH", "/opt/akk-stack/code"))
QUESTS_PATH = Path(os.environ.get("EQEMU_QUESTS_PATH", "/opt/akk-stack/server/quests"))
SERVER_PATH = Path(os.environ.get("EQEMU_SERVER_PATH", "/opt/akk-stack/server"))

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.environ.get("EQEMU_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("EQEMU_DB_PORT", "3306")),
    "user": os.environ.get("EQEMU_DB_USER", "eqemu"),
    "password": os.environ.get("EQEMU_DB_PASSWORD", ""),
    "database": os.environ.get("EQEMU_DB_NAME", "peq"),
}

# ---------------------------------------------------------------------------
# Docker / SSH
# ---------------------------------------------------------------------------
DOCKER_CONTAINER = os.environ.get("EQEMU_DOCKER_CONTAINER", "akk-stack-eqemu-server-1")
MARIADB_CONTAINER = os.environ.get("EQEMU_MARIADB_CONTAINER", "akk-stack-mariadb-1")

# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------
DOCS_PATH = Path(os.environ.get("EQEMU_DOCS_PATH", ""))
DOCS_REPO_URL = "https://github.com/EQEmu/eqemu-docs-v2.git"
DOCS_SITE_URL = "https://docs.eqemu.io"

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
MAX_RESULTS = 200
MAX_FILE_SIZE = 500_000  # bytes
MAX_QUERY_ROWS = 500
